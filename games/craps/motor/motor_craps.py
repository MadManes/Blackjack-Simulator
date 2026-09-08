# games/craps/motor/motor_craps.py
# -*- coding: utf-8 -*-
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from games.craps.eventos.bus_eventos import BridgeEventosCraps
from games.craps.estadisticas.craps_stats import EstadisticasCraps

# ---------- util ----------
def redondear_500(valor: float) -> int:
    v = float(valor)
    resto = v % 500
    abajo = v - resto
    arriba = abajo + 500
    if resto >= 250:
        return int(arriba)
    return int(abajo)

def clamp_multiplo_500(monto: int, minimo: int, maximo: int) -> int:
    m = max(minimo, min(maximo, monto))
    return (m // 500) * 500

# ---------- configs ----------
@dataclass
class ConfigLinea:
    min_bet: int = 5000
    max_bet: int = 200000

@dataclass
class ConfigEnganche:
    modo: int = 1
    min_bet: int = 5000
    pago_buena_4_10: float = 2.0
    pago_buena_5_9: float = 1.5
    pago_buena_6_8: float = 1.2
    pago_mala_4_10: float = 0.5
    pago_mala_5_9: float = 2.0/3.0
    pago_mala_6_8: float = 5.0/6.0
    factor_4_10: int = 2
    factor_5_9: int = 3
    factor_6_8: int = 4

@dataclass
class ConfigMotor:
    linea: ConfigLinea = field(default_factory=ConfigLinea)
    enganche: ConfigEnganche = field(default_factory=ConfigEnganche)

# ---------- apuesta ----------
@dataclass
class ApuestaLinea:
    id_apuesta: int
    id_jugador: int
    tipo: str          # "Buena" | "Mala"
    monto: int
    enganche: int = 0

# ---------- motor ----------
class MotorCraps:
    puntos_validos = {4,5,6,8,9,10}

    def __init__(self,
                 config: Optional[ConfigMotor] = None,
                 estadisticas: Optional[EstadisticasCraps] = None,
                 semilla: Optional[int] = None) -> None:

        self.cfg = config or ConfigMotor()
        # stats engine compatible (si se pasa, será actualizado por el bus)
        self.stats = estadisticas or EstadisticasCraps()
        self.bus = BridgeEventosCraps(self.stats)
        self.rng = random.Random(semilla)

        # jugadores y tirador
        self._setup_players: Optional[List[dict]] = None
        self._shooters_list: List[int] = []
        self._shooters_idx: int = 0

        # estado mesa
        self.fase = "OFF"        # "OFF" o "ON"
        self.punto: Optional[int] = None

        # tirador
        self.tirador_id: int = 1
        self.tirador_apuesta: str = "Buena"
        self.tirador_tiene_vidas: bool = True
        self.tirador_vidas: int = 3
        self.max_jugadores_en_mesa: int = 12
        self._modo_masivo = True

        # apuestas
        self._next_apuesta_id: int = 1
        self.apuestas_linea: List[ApuestaLinea] = []

        # Control para no re-colocar apuestas repetidamente
        self._bets_placed: bool = False

        # paso a paso (tick)
        self._pase_in_progress: bool = False   # True mientras dura un pase (desde PASE_INICIADO hasta FIN_DE_PASE)
        self._step_waiting_for_on_phase: bool = False

        # estado por tirador (vidas / modo 'sin vidas' cuando consigue run)
        # estructura: { jugador_id: {"vidas": int, "tiene_vidas": bool, "linea": "Buena"|"Mala"} }
        self._shooter_state: Dict[int, Dict[str, object]] = {}


    # ---------- PARA DEBUG DESPUES BORRO ----------- #

    def _debug_snapshot(self, tag: str = ""):
        """
        Imprime en consola (y publica) la foto del estado relevante para debugging.
        Llamar desde puntos clave: after start_pase, after resolver tiro, after rotar tirador, after fin_pase.
        """
        try:
            shooters = list(self._shooters_list)
            idx = int(self._shooters_idx) if hasattr(self, "_shooters_idx") else None
            st = {
                "tag": tag,
                "tirador_id": self.tirador_id,
                "tirador_apuesta": self.tirador_apuesta,
                "tirador_vidas": getattr(self, "tirador_vidas", None),
                "tirador_tiene_vidas": getattr(self, "tirador_tiene_vidas", None),
                "shooters_list": shooters,
                "shooters_idx": idx,
                "fase": self.fase,
                "punto": self.punto,
                "bets_placed": self._bets_placed,
                "pase_in_progress": self._pase_in_progress,
                "apuestas_count": len(self.apuestas_linea),
                "_shooter_state": getattr(self, "_shooter_state", {}).copy(),
            }
            print("[MOTOR DEBUG SNAPSHOT]", st)
            # publicar evento debug para quien quiera suscribirse
            self.bus.publicar("DEBUG_SNAPSHOT", **st)
        except Exception as e:
            print("[MOTOR DEBUG ERROR]", e)


    def _publish_lives(self, jugador_id: int):
        st = self._shooter_state.get(jugador_id, {"vidas": 0, "tiene_vidas": True})
        try:
            self.bus.publicar("LIVES_UPDATED", jugador=jugador_id, vidas=int(st.get("vidas", 0)), tiene_vidas=bool(st.get("tiene_vidas", True)))
        except Exception:
            # fallback print
            print(f"[MOTOR DEBUG] LIVES_UPDATED: jugador={jugador_id} vidas={st.get('vidas')} tiene_vidas={st.get('tiene_vidas')}")


    ## FIN METODOS DEBUG ..............   -------------------


    # ---------- observadores UI ----------
    def registrar_observador(self, fn):
        self.bus.registrar_observador(fn)

    def suscribir(self, tipo_evento: str, handler):
        """Proxy para pruebas — permite suscribir handlers al bus"""
        self.bus.suscribir(tipo_evento, handler)

    # ---------- setup players ----------
    def set_setup_players(self, setup_players: Optional[List[dict]]) -> None:
        self._setup_players = setup_players or []

        # construir nueva lista de shooters respetando 'puede_tirar' y 'linea'
        new_shooters = []
        for p in self._setup_players:
            try:
                jid = int(p.get("jugador", 0))
            except Exception:
                continue
            if p.get("puede_tirar", True) and str(p.get("linea","")).strip().lower() != "no":
                new_shooters.append(jid)

        # si no quedaron shooters explícitos, usar el rango por defecto
        if not new_shooters:
            new_shooters = list(range(1, self.max_jugadores_en_mesa + 1))

        # intentar preservar índice/turno actual si es posible
        prev_tirador = getattr(self, "tirador_id", None)
        prev_idx = getattr(self, "_shooters_idx", None)

        self._shooters_list = new_shooters

        if prev_tirador is not None and prev_tirador in self._shooters_list:
            # mantener tirador actual ajustando _shooters_idx al nuevo índice del id
            self._shooters_idx = self._shooters_list.index(prev_tirador)
        elif isinstance(prev_idx, int) and 0 <= prev_idx < len(self._shooters_list):
            # si el índice previo es válido dentro de la nueva lista, lo conservamos
            self._shooters_idx = prev_idx
        else:
            # fallback: empezar en 0 (solo si no hay otra alternativa)
            self._shooters_idx = 0

        # inicializar / actualizar estado de vidas por tirador sin borrar si ya existía
        existing = getattr(self, "_shooter_state", {}) or {}
        for p in self._setup_players:
            try:
                jid = int(p.get("jugador", 0))
            except Exception:
                continue
            if jid in self._shooters_list:
                linea = "Buena" if str(p.get("linea","Buena")).strip().lower() == "buena" else "Mala"
                if jid not in existing:
                    existing[jid] = {"vidas": 3, "tiene_vidas": True, "linea": linea}
                else:
                    # no sobrescribimos vidas/tiene_vidas si ya existen
                    existing[jid].setdefault("vidas", existing[jid].get("vidas", 3))
                    existing[jid].setdefault("tiene_vidas", existing[jid].get("tiene_vidas", True))
                    existing[jid]["linea"] = linea
        # asegurar que cualquier id en shooters_list tiene estado
        for jid in self._shooters_list:
            if jid not in existing:
                existing[jid] = {"vidas": 3, "tiene_vidas": True, "linea": "Buena"}
        self._shooter_state = existing

        # sincronizar tirador público con el índice final decidido
        try:
            self._sync_tirador_from_idx()
        except Exception:
            pass

    # ---------- apuestas ----------
    def colocar_apuesta(self, id_jugador: int, tipo: str, monto: int) -> int:
        if str(tipo).lower() == "buena": tipo = "Buena"
        elif str(tipo).lower() == "mala": tipo = "Mala"
        else: tipo = "No"
        if tipo == "No": m = 0
        else: m = clamp_multiplo_500(monto, self.cfg.linea.min_bet, self.cfg.linea.max_bet)
        ap = ApuestaLinea(self._next_apuesta_id, id_jugador, tipo, m, 0)
        self.apuestas_linea.append(ap)

        # publicar evento para que stats lo registre
        self.bus.publicar("APUESTA_COLOCADA",
                          id_jugador=id_jugador,
                          tipo_apuesta=tipo,
                          monto=m,
                          id_apuesta=ap.id_apuesta)
        self._next_apuesta_id += 1
        return ap.id_apuesta

    def adjuntar_enganche_si_corresponde(self, probabilidad: float = 0.5) -> None:
        if not (self.fase == "ON" and self.punto in self.puntos_validos):
            return
        for ap in self.apuestas_linea:
            if ap.enganche > 0:
                continue
            if self.rng.random() > probabilidad:
                continue
            minimo = self.cfg.enganche.min_bet
            maximo = self._max_enganche_para(ap)
            if maximo < minimo:
                continue
            base = self.rng.randrange(minimo // 500, (maximo // 500) + 1)
            monto_elegido = max(minimo, base * 500)
            ap.enganche = monto_elegido
            self.bus.publicar("APUESTA_COLOCADA",
                              id_jugador=ap.id_jugador,
                              tipo_apuesta=f"Enganche {ap.tipo}",
                              monto=monto_elegido,
                              id_apuesta=ap.id_apuesta)

    def tirar_dados(self):
        d1 = self.rng.randint(1, 6)
        d2 = self.rng.randint(1, 6)
        suma = d1 + d2
        es_doble = d1 == d2
        # publicar evento de tiro (UI)
        self.bus.publicar("TIRO_INICIADO", d1=d1, d2=d2, suma=suma, es_doble=es_doble)
        # publicar "TIRADA_REALIZADA" con formato que usabas en UI
        self.bus.publicar("TIRADA_REALIZADA",
                          dado1=d1, dado2=d2, suma=suma, es_doble=es_doble,
                          d1=d1, d2=d2)
        return d1, d2, suma, es_doble

    # ---------- resolver tiro (helper usado por step) ----------
    def resolver_tiro_result(self, suma: int):
        # OFF (come-out)
        if self.fase == "OFF":
            if suma in (7, 11):
                self.bus.publicar("COMEOUT_GANA", suma=suma)
                return "GANA", None, "come-out", "come-out gana"
            if suma in (2, 3):
                self.bus.publicar("COMEOUT_PIERDE", suma=suma)
                return "PIERDE", None, "come-out", "come-out pierde"
            if suma == 12:
                self.bus.publicar("COMEOUT_PUSH", suma=suma)
                return "SIGUE", None, "come-out", "come-out push"
            # punto establecido
            self.fase = "ON"
            self.punto = suma
            self.bus.publicar("PUNTO_FIJADO", valor=suma)
            return "SIGUE", None, "point", "punto establecido"

        # ON (point)
        if suma == self.punto:
            self.bus.publicar("PUNTO_LOGRADO", punto=suma)
            self.fase = "OFF"
            self.punto = None
            return "GANA", None, "point", "punto logrado"
        if suma == 7:
            self.bus.publicar("SEVEN_OUT")
            self.fase = "OFF"
            self.punto = None
            return "PIERDE", None, "point", "seven-out"
        self.bus.publicar("SIN_CAMBIO", suma=suma)
        return "SIGUE", None, "point", "sin cambio"

    # ---------- paso a paso: start_pase + step() ----------
    def start_pase(self,
                   num_jugadores: int = 8,
                   p_buena: float = 0.7,
                   pases_linea_min: int = 5000,
                   pases_linea_max: int = 200000,
                   prob_enganche: float = 0.5,
                   setup_players: Optional[List[dict]] = None) -> None:
        """
        Prepara un pase (coloca apuestas *una sola vez*) y publica PASE_INICIADO.
        Luego queda en modo _pase_in_progress para usar step().
        """
        # configurar jugadores/tirador si vienen
        if setup_players is not None:
            self.set_setup_players(setup_players)

        # si ya colocamos apuestas para este pase, no volver a colocarlas
        if not self._bets_placed:
            # limpiar apuestas previas y colocar nuevas
            self.apuestas_linea = []
            if setup_players is not None:
                for pl in setup_players[:num_jugadores]:
                    jid = int(pl.get("jugador", 0)) or (len(self.apuestas_linea) + 1)
                    linea = str(pl.get("linea", "Buena")).strip()
                    if linea.lower() == "no":
                        continue
                    tipo = "Buena" if linea.lower() == "buena" else "Mala"
                    monto = int(pl.get("monto", pases_linea_min))
                    monto = clamp_multiplo_500(monto, self.cfg.linea.min_bet, self.cfg.linea.max_bet)
                    self.colocar_apuesta(jid, tipo, monto)
            else:
                for j in range(1, num_jugadores+1):
                    tipo = "Buena" if self.rng.random() < p_buena else "Mala"
                    base = self.rng.randrange(pases_linea_min // 500, (pases_linea_max // 500) + 1)
                    monto = base * 500
                    self.colocar_apuesta(j, tipo, monto)

            self._bets_placed = True

        # publish PASE_INICIADO (snapshot seguro)
        snap = {}
        try:
            snap = self.stats.snapshot() if self.stats else {}
        except Exception:
            snap = {}
        self.bus.publicar("PASE_INICIADO",
                          tirador=self.tirador_id,
                          apuesta=self.tirador_apuesta,
                          vidas=self.tirador_vidas,
                          stats=snap)
        # sincronizar tirador con el índice actual por si quedó desincronizado
        self._sync_tirador_from_idx()
        # DEBUG: snapshot inicial del pase
        self._debug_snapshot("start_pase")
        # publish current lives for the tirador
        self._publish_lives(self.tirador_id)

        # preparar estado interno para step()
        self._pase_in_progress = True
        self._session_prob_enganche = prob_enganche
        # si punto se fija en este pase, lo manejamos en step
        self.fase = "OFF"
        self.punto = None


    def step(self) -> None:
        """
        Ejecuta un solo tiro dentro del pase en curso.
        Si no hay pase en curso, no hace nada (usar start_pase antes).
        """
        if not self._pase_in_progress:
            return

        # Come-out / OFF
        d1, d2, suma, es_doble = self.tirar_dados()
        self._debug_snapshot("after_tirar_dados")


        if self.fase == "OFF":
            # resolver inmediatamente en OFF
            if suma in (7, 11):
                self._resolver_linea_final("come-out 7/11", buena_gana=True)
                self._rotacion_por_resultado_en_off(ganador="Buena")
                self._fin_pase(ganador="Buena", punto=None, motivo="come-out 7/11")
                self._bets_placed = False
                self._pase_in_progress = False
                self._debug_snapshot("before_fin_pase")
                return
            elif suma in (2, 3):
                self._resolver_linea_final("come-out 2/3", buena_gana=False)
                self._rotacion_por_resultado_en_off(ganador="Mala")
                self._fin_pase(ganador="Mala", punto=None, motivo="come-out 2/3")
                self._bets_placed = False
                self._pase_in_progress = False
                self._debug_snapshot("before_fin_pase")
                return
            elif suma == 12:
                self._resolver_linea_final_12()
                self._rotacion_por_resultado_en_off(ganador="Empate12")
                self._fin_pase(ganador="Empate12", punto=None, motivo="come-out 12")
                self._bets_placed = False
                self._pase_in_progress = False
                self._debug_snapshot("before_fin_pase")
                return
            else:
                # punto fijado -> pasar a ON, no termina el pase
                self.punto = suma
                self.fase = "ON"
                self.bus.publicar("PUNTO_FIJADO", valor=self.punto)
                # posibl. enganchar (si corresponde)

                ## Volver a activar cuando haga enganches
                #self.adjuntar_enganche_si_corresponde(probabilidad=getattr(self, "_session_prob_enganche", 0.5))
                self._debug_snapshot("before_fin_pase")
                return

        # ON
        if self.fase == "ON":
            # tirar hasta punto o 7 (un tiro por step)
            if suma == self.punto:
                self._resolver_linea_punto_logrado()
                self._rotacion_por_resultado_en_on(ganador="Buena")
                self._fin_pase(ganador="Buena", punto=self.punto, motivo="punto logrado")
                self._bets_placed = False
                self._pase_in_progress = False
                self._debug_snapshot("before_fin_pase")
                return
            elif suma == 7:
                self._resolver_linea_seven_out()
                self._rotacion_por_resultado_en_on(ganador="Mala")
                self._fin_pase(ganador="Mala", punto=self.punto, motivo="seven-out")
                self._bets_placed = False
                self._pase_in_progress = False
                self._debug_snapshot("before_fin_pase")
                return
            else:
                # sin cambio: seguir en ON
                self.bus.publicar("SIN_CAMBIO", suma=suma)
                self._debug_snapshot("before_fin_pase")
                return


    # ---------- ciclo de pase - compatibilidad para masivo ----------
    def jugar_pase_random(self,
                          num_jugadores: int = 8,
                          p_buena: float = 0.7,
                          pases_linea_min: int = 5000,
                          pases_linea_max: int = 200000,
                          prob_enganche: float = 0.5,
                          setup_players: Optional[List[dict]] = None) -> None:
        """
        Compatibilidad con la versión previa: ejecuta el pase completo (bloqueante).
        Implementado usando start_pase() + múltiples step() llamadas internamente.
        """
        # almacenar params para posible reuso y permitir start via step
        self._session_num_jug = num_jugadores
        self._session_p_buena = p_buena
        self._session_min_line = pases_linea_min
        self._session_max_line = pases_linea_max
        self._session_prob_enganche = prob_enganche
        self._session_setup_players = setup_players

        # iniciar pase y ejecutar hasta su fin
        self.start_pase(num_jugadores=num_jugadores,
                        p_buena=p_buena,
                        pases_linea_min=pases_linea_min,
                        pases_linea_max=pases_linea_max,
                        prob_enganche=prob_enganche,
                        setup_players=setup_players)

        # ejecutar pasos hasta que pase termine
        while self._pase_in_progress:
            self.step()

    # ---------- internals tirador ----------
    def _player_line_by_id(self, jid: int) -> Optional[str]:
        if not self._setup_players:
            return None
        for p in self._setup_players:
            try:
                if int(p.get("jugador", 0)) == int(jid):
                    return p.get("linea")
            except Exception:
                continue
        return None

    # ---------- internals tirador ----------
    def _configurar_tirador_inicial(self, p_buena: float):
        # seleccionar primer tirador usando la lista preparada, y cargar su estado de vidas
        if self._shooters_list:
            self._shooters_idx = 0
            self.tirador_id = self._shooters_list[self._shooters_idx % len(self._shooters_list)]
            # preferir la linea del setup si existe
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                # fallback random
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"

            # inicializar estado si no existe
            if self.tirador_id not in self._shooter_state:
                self._shooter_state[self.tirador_id] = {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta}
            # cargar vidas/tiene_vidas desde el dict
            st = self._shooter_state[self.tirador_id]
            self.tirador_vidas = int(st.get("vidas", 3))
            self.tirador_tiene_vidas = bool(st.get("tiene_vidas", True))

            # sincronizar posible linea almacenada
            st["linea"] = self.tirador_apuesta
            self._publish_lives(self.tirador_id)
            self._debug_snapshot("configurar_tirador_inicial")

            return

        # si no hay shooters_list
        self.tirador_id = 1
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"
        self.tirador_tiene_vidas = True
        self.tirador_vidas = 3
        if self.tirador_id not in self._shooter_state:
            self._shooter_state[self.tirador_id] = {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta}

    def _sync_tirador_from_idx(self) -> None:
        """
        Alinea tirador_id / tirador_vidas / tirador_tiene_vidas con _shooters_idx.
        Usar cuando haya riesgo de desincronización (start_pase, fin_pase, después de set_setup_players).
        """
        if not self._shooters_list:
            # fallback: si no hay lista, mantener comportamiento por defecto
            return

        # asegurarnos índice válido
        if self._shooters_idx is None:
            self._shooters_idx = 0
        self._shooters_idx = int(self._shooters_idx) % len(self._shooters_list)
        jid = self._shooters_list[self._shooters_idx]
        self.tirador_id = jid

        # preferir la linea guardada en setup si existe, sino mantener tirador_apuesta actual
        line = self._player_line_by_id(jid)
        if line is not None and str(line).strip().lower() != "no":
            self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"

        # asegurar registro en _shooter_state sin reiniciar vidas si ya existe
        if jid not in self._shooter_state:
            self._shooter_state[jid] = {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta}

        st = self._shooter_state[jid]
        st["linea"] = self.tirador_apuesta
        # sincronizar atributos públicos
        self.tirador_vidas = int(st.get("vidas", 3))
        self.tirador_tiene_vidas = bool(st.get("tiene_vidas", True))

        # publicar estado para UI/debug
        self._publish_lives(self.tirador_id)
        self._debug_snapshot("sync_tirador_from_idx")



    def _rotar_tirador(self, p_buena_para_proximo: Optional[float] = None) -> None:
        """
        Mueve el índice al siguiente tirador y sincroniza self.tirador_* con el estado guardado.
        """
        if self._shooters_list:
            # avanzar índice circular
            self._shooters_idx = (self._shooters_idx + 1) % len(self._shooters_list)
            self.tirador_id = self._shooters_list[self._shooters_idx]
            # preferir linea del setup
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                if p_buena_para_proximo is None:
                    p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"

            # asegurarse que existe estado y cargarlo
            if self.tirador_id not in self._shooter_state:
                self._shooter_state[self.tirador_id] = {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta}
            st = self._shooter_state[self.tirador_id]
            st["linea"] = self.tirador_apuesta
            self.tirador_tiene_vidas = bool(st.get("tiene_vidas", True))
            self.tirador_vidas = int(st.get("vidas", 3))

            # publicar debug de vidas
            self.bus.publicar("LIVES_UPDATED", jugador=self.tirador_id, vidas=self.tirador_vidas, tiene_vidas=self.tirador_tiene_vidas)
            return

        # fallback cuando no hay lista explícita
        self.tirador_id = (self.tirador_id % self.max_jugadores_en_mesa) + 1
        if p_buena_para_proximo is None:
            p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"

        if self.tirador_id not in self._shooter_state:
            self._shooter_state[self.tirador_id] = {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta}
        st = self._shooter_state[self.tirador_id]
        st["linea"] = self.tirador_apuesta
        self.tirador_tiene_vidas = bool(st.get("tiene_vidas", True))
        self.tirador_vidas = int(st.get("vidas", 3))
        self.bus.publicar("LIVES_UPDATED", jugador=self.tirador_id, vidas=self.tirador_vidas, tiene_vidas=self.tirador_tiene_vidas)

        # publicar debug de vidas        
        self.bus.publicar("LIVES_UPDATED", jugador=self.tirador_id, vidas=self.tirador_vidas, tiene_vidas=self.tirador_tiene_vidas)
        self._debug_snapshot("after_rotar_tirador")
        return



    def _fin_pase(self, ganador=None, punto=None, motivo=""):
        # publicar punto libre y fin de pase con snapshot básico
        self.bus.publicar("PUNTO_LIBRE")
        snapshot = {}
        try:
            snapshot = self.stats.snapshot()
        except:
            pass
        self.bus.publicar("FIN_DE_PASE",
                          tirador=self.tirador_id,
                          ganador=ganador,
                          punto=punto,
                          motivo=motivo,
                          stats=snapshot)
        
        self._debug_snapshot("fin_pase")

        
        self.fase = "OFF"
        self.punto = None
        self.apuestas_linea = []
        self._bets_placed = False
        self._pase_in_progress = False 

        # Tras fin de pase aseguramos que tirador y idx estén consistentes para el siguiente start_pase
        try:
            self._sync_tirador_from_idx()
        except Exception:
            # no queremos que un fallo aquí rompa la rutina general
            pass

    # ---------- rotaciones por resultado ----------
    def _rotacion_por_resultado_en_off(self, ganador: str) -> None:
        jid = self.tirador_id
        st = self._shooter_state.setdefault(jid, {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta})

        # === 1) TIRADOR BUENA ===
        if self.tirador_apuesta == "Buena":

            # Tirador Buena gana come-out con 7 u 11
            if ganador == "Buena":
                # Se vuelve RUN mode (vidas infinito hasta que muera por 2/3/12 o 7 ON)
                st["tiene_vidas"] = False
                st["vidas"] = 0
                self.tirador_tiene_vidas = False
                self.tirador_vidas = 0
                # NO rota
                pass

            # Empate 12 en OFF
            elif ganador == "Empate12":
                # pierde una vida si tenía, si estaba en RUN se rota
                if st.get("tiene_vidas", True):
                    st["vidas"] -= 1
                    self.tirador_vidas = st["vidas"]
                    if st["vidas"] <= 0:
                        self._rotar_tirador()
                else:
                    # estaba en RUN y pierde por 12 => rotar
                    self._rotar_tirador()

            # Pierde contra MALA (2 o 3)
            elif ganador == "Mala":
                if st.get("tiene_vidas", True):
                    st["vidas"] -= 1
                    self.tirador_vidas = st["vidas"]
                    if st["vidas"] <= 0:
                        self._rotar_tirador()
                else:
                    self._rotar_tirador()


        # === 2) TIRADOR MALA ===
        else:  # tirador juega por MALA

            # Tirador MALA gana con 2 o 3
            if ganador == "Mala":
                # SIEMPRE rota
                self._rotar_tirador()

            # Empate con 12
            elif ganador == "Empate12":
                # NO pasa nada
                pass

            # Tirador MALA pierde con 7 u 11
            elif ganador == "Buena":
                if st.get("tiene_vidas", True):
                    st["vidas"] -= 1
                    self.tirador_vidas = st["vidas"]
                    if st["vidas"] <= 0:
                        self._rotar_tirador()
                else:
                    self._rotar_tirador()

        # publicar estado actualizado de vidas
        st2 = self._shooter_state.get(jid, {})
        self.bus.publicar("LIVES_UPDATED", jugador=jid, vidas=st2.get("vidas", 0), tiene_vidas=st2.get("tiene_vidas", True))



    def _rotacion_por_resultado_en_on(self, ganador: str) -> None:
        """
        Reglas en ON (point):
         - Buena:
             * si gana el punto -> mantiene (no rota)
             * si pierde por 7 -> rota
         - Mala:
             * en ON rota siempre (sea que gane o pierda)
        """
        jid = self.tirador_id
        st = self._shooter_state.setdefault(jid, {"vidas": 3, "tiene_vidas": True, "linea": self.tirador_apuesta})

        if self.tirador_apuesta == "Buena":
            if ganador == "Buena":
                # ganó el punto, sigue en mesa; aseguramos que está en modo 'run' (sigue hasta muerte)
                st["tiene_vidas"] = False
                st["vidas"] = 0
                self.tirador_tiene_vidas = False
                self.tirador_vidas = 0
            else:
                # perdió en ON (7) -> rotar
                self._rotar_tirador()
        else:
            # tirador Mala -> rotar siempre en ON
            self._rotar_tirador()

        # publicar debug
        st2 = self._shooter_state.get(jid, {})
        self.bus.publicar("LIVES_UPDATED", jugador=jid, vidas=st2.get("vidas", 0), tiene_vidas=st2.get("tiene_vidas", True))


    # ---------- resoluciones / pagos ----------
    def _resolver_linea_final(self, motivo: str, buena_gana: bool) -> None:
        for ap in list(self.apuestas_linea):
            if (ap.tipo == "Buena" and buena_gana) or (ap.tipo == "Mala" and not buena_gana):
                self._pagar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
            else:
                self._cobrar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)

    def _resolver_linea_final_12(self) -> None:
        for ap in list(self.apuestas_linea):
            if ap.tipo == "Buena":
                self._cobrar(ap.id_jugador, ap.monto, "come-out 12", tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
            else:
                self.bus.publicar("APUESTA_RESUELTA",
                                  id_jugador=ap.id_jugador,
                                  resultado="EMPATE",
                                  pago_jugador=0,
                                  pago_casino=0,
                                  motivo="come-out 12",
                                  tipo_apuesta=ap.tipo,
                                  id_apuesta=ap.id_apuesta,
                                  monto_apuesta=ap.monto)

    def _resolver_linea_punto_logrado(self) -> None:
        for ap in list(self.apuestas_linea):
            if ap.tipo == "Buena":
                self._pagar(ap.id_jugador, ap.monto, "punto logrado", tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
                if ap.enganche > 0:
                    mult = self._true_odds_buena()
                    bruto = ap.enganche * mult
                    pago = redondear_500(bruto)
                    self._pagar(ap.id_jugador, pago, "enganche Buena (true odds)", tipo="Enganche Buena", id_apuesta=ap.id_apuesta, monto_apuesta=ap.enganche)
            else:
                self._cobrar(ap.id_jugador, ap.monto, "punto logrado", tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
                if ap.enganche > 0:
                    self._cobrar(ap.id_jugador, ap.enganche, "enganche Mala pierde", tipo="Enganche Mala", id_apuesta=ap.id_apuesta, monto_apuesta=ap.enganche)

    def _resolver_linea_seven_out(self) -> None:
        for ap in list(self.apuestas_linea):
            if ap.tipo == "Buena":
                self._cobrar(ap.id_jugador, ap.monto, "seven-out", tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
                if ap.enganche > 0:
                    self._cobrar(ap.id_jugador, ap.enganche, "enganche Buena pierde", tipo="Enganche Buena", id_apuesta=ap.id_apuesta, monto_apuesta=ap.enganche)
            else:
                self._pagar(ap.id_jugador, ap.monto, "seven-out", tipo=ap.tipo, id_apuesta=ap.id_apuesta, monto_apuesta=ap.monto)
                if ap.enganche > 0:
                    mult = self._true_reverse_mala()
                    bruto = ap.enganche * mult
                    pago = redondear_500(bruto)
                    self._pagar(ap.id_jugador, pago, "enganche Mala (reverse odds)", tipo="Enganche Mala", id_apuesta=ap.id_apuesta, monto_apuesta=ap.enganche)

    # ---------- pagos / cobros (con campos claros para stats) ----------
    def _pagar(self, id_jugador: int, monto: float, motivo: str, tipo: str, id_apuesta: Optional[int] = None, monto_apuesta: Optional[int] = 0) -> None:
        # pago al jugador -> pago_jugador = monto, pago_casino = 0
        self.bus.publicar("APUESTA_RESUELTA",
                          id_jugador=id_jugador,
                          resultado="GANA",
                          pago_jugador=int(monto),
                          pago_casino=0,
                          motivo=motivo,
                          tipo_apuesta=tipo,
                          id_apuesta=id_apuesta,
                          monto_apuesta=int(monto_apuesta or 0))

    def _cobrar(self, id_jugador: int, monto: float, motivo: str, tipo: str, id_apuesta: Optional[int] = None, monto_apuesta: Optional[int] = 0) -> None:
        # jugador pierde -> pago_jugador = 0, pago_casino = monto
        self.bus.publicar("APUESTA_RESUELTA",
                          id_jugador=id_jugador,
                          resultado="PIERDE",
                          pago_jugador=0,
                          pago_casino=int(monto),
                          motivo=motivo,
                          tipo_apuesta=tipo,
                          id_apuesta=id_apuesta,
                          monto_apuesta=int(monto_apuesta or 0))

    # ---------- odds ----------
    def _true_odds_buena(self) -> float:
        if self.punto in (4, 10): return 2.0
        if self.punto in (5, 9): return 1.5
        if self.punto in (6, 8): return 1.2
        return 0.0

    def _true_reverse_mala(self) -> float:
        if self.punto in (4, 10): return 0.5
        if self.punto in (5, 9): return 2/3
        if self.punto in (6, 8): return 5/6
        return 0.0

    def _factor_modo2(self) -> int:
        if self.punto in (4, 10): return self.cfg.enganche.factor_4_10
        if self.punto in (5, 9): return self.cfg.enganche.factor_5_9
        if self.punto in (6, 8): return self.cfg.enganche.factor_6_8
        return 1

    def _max_enganche_para(self, ap: ApuestaLinea) -> int:
        if self.punto not in self.puntos_validos:
            return 0
        modo = self.cfg.enganche.modo
        if ap.tipo == "Buena":
            base = ap.monto
            if modo == 2:
                base *= self._factor_modo2()
            return redondear_500(base)
        else:
            base = ap.monto * self._true_odds_buena()
            if modo == 2:
                base *= self._factor_modo2()
            return redondear_500(base)
