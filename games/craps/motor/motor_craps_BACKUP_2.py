# games/craps/motor/motor_craps.py
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from games.craps.eventos.bus_eventos import BridgeEventosCraps
from games.craps.estadisticas.craps_stats_masivo import EstadisticasCrapsMasivo

# ------------------ Utilidades ------------------

def redondear_500(valor: int | float) -> int:
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

# ------------------ Config mínima (línea + enganche) ------------------

@dataclass
class ConfigLinea:
    min_bet: int = 5000
    max_bet: int = 200000

@dataclass
class ConfigEnganche:
    modo: int = 1  # 1 o 2
    min_bet: int = 5000
    # true odds para Buena (por Punto)
    pago_buena_4_10: float = 2.0     # 2:1
    pago_buena_5_9: float = 1.5      # 3:2
    pago_buena_6_8: float = 1.2      # 6:5
    # true reverse para Mala (por Punto)
    pago_mala_4_10: float = 0.5      # 1:2
    pago_mala_5_9: float = 2.0/3.0   # 2:3 ≈ 0.6667
    pago_mala_6_8: float = 5.0/6.0   # 5:6 ≈ 0.8333
    # multiplicadores extra del Modo 2
    factor_4_10: int = 2
    factor_5_9: int = 3
    factor_6_8: int = 4

@dataclass
class ConfigMotor:
    linea: ConfigLinea = field(default_factory=ConfigLinea)
    enganche: ConfigEnganche = field(default_factory=ConfigEnganche)

# ------------------ Tipos de apuesta ------------------

@dataclass
class ApuestaLinea:
    id_apuesta: int
    id_jugador: int
    tipo: str          # "Buena" | "Mala"
    monto: int
    enganche: int = 0  # monto de enganche asociado (si corresponde)

# ------------------ Motor ------------------

class MotorCraps:
    """
    Motor unificado y coherente (versión "fija").

    Usa BridgeEventosCraps como bus central y además notifica directamente
    a EstadisticasCrapsMasivo (compatibilidad con la API de hooks previa).
    """

    puntos_validos = {4,5,6,8,9,10}

    def __init__(self,
                 config: Optional[ConfigMotor] = None,
                 estadisticas: Optional[EstadisticasCrapsMasivo] = None,
                 semilla: Optional[int] = None) -> None:
        self.cfg = config or ConfigMotor()
        # si nos pasan un objeto Estadisticas, lo usamos; si no, creamos uno
        self.stats = estadisticas or EstadisticasCrapsMasivo()
        # bus de eventos (UI / handlers)
        self.bus = BridgeEventosCraps(self.stats)
        self.rng = random.Random(semilla)

        # setup players
        self._setup_players: Optional[List[dict]] = None
        self._shooters_list: List[int] = []
        self._shooters_idx: int = 0

        # estado mesa
        self.fase = "OFF"          # 'OFF' o 'ON'
        self.boton_on: bool = False  # coherente con fase
        self.punto: Optional[int] = None

        # estado del tirador
        self.tirador_id: int = 1
        self.tirador_apuesta: str = "Buena"
        self.tirador_tiene_vidas: bool = True
        self.tirador_vidas: int = 3

        # rotación y control
        self.max_jugadores_en_mesa: int = 12
        self._modo_masivo = True

        # apuestas
        self._next_apuesta_id: int = 1
        self.apuestas_linea: List[ApuestaLinea] = []

    # ----------------- API de integración -----------------
    def suscribir(self, tipo_evento: str, handler) -> None:
        """Permite que un handler sea suscripto al bus (handler debe aceptar un dict evento)."""
        self.bus.suscribir(tipo_evento, handler)

    def registrar_observador(self, fn):
        """Registrar un observador UI (función que recibe evento dict)."""
        self.bus.registrar_observador(fn)

    # ----------------- Traductor de eventos -> stats (compatibilidad) -----------------
    def _notify_stats_from_event(self, tipo: str, data: dict):
        """Mapea eventos publicados a los hooks existentes del objeto EstadisticasCrapsMasivo."""
        # mantener compatibilidad con la versión antigua de Bridge que llamaba hooks específicos
        try:
            if tipo == "NUEVO_TIRADOR":
                if hasattr(self.stats, "on_nuevo_tirador"):
                    self.stats.on_nuevo_tirador()
            elif tipo == "APUESTA_COLOCADA":
                if hasattr(self.stats, "on_apuesta"):
                    self.stats.on_apuesta(float(data.get("monto", 0)))
            elif tipo == "TIRO_INICIADO":
                if hasattr(self.stats, "on_tiro"):
                    self.stats.on_tiro(int(data.get("d1", 0)), int(data.get("d2", 0)), int(data.get("suma", 0)), bool(data.get("es_doble", False)))
            elif tipo == "PUNTO_FIJADO":
                if hasattr(self.stats, "on_punto_fijado"):
                    valor = data.get("valor", data.get("punto", 0))
                    self.stats.on_punto_fijado(int(valor))
            elif tipo == "APUESTA_RESUELTA":
                if hasattr(self.stats, "on_resolucion"):
                    self.stats.on_resolucion(str(data.get("resultado", "")).upper(), float(data.get("pago", 0)), str(data.get("tipo_apuesta", "")), str(data.get("motivo", "")))
            elif tipo == "PUNTO_LIBRE" or tipo == "FIN_DE_PASE":
                if hasattr(self.stats, "on_fin_pase"):
                    # si el caller proporciona buenagana, la pasamos; si no, None
                    buena = data.get("buena_gana", None)
                    self.stats.on_fin_pase(buena)
        except Exception:
            # nunca dejar que stats rompa el motor
            pass

    # ----------------- Publicadores auxiliares -----------------
    def _publicar(self, tipo: str, **kwargs):
        """Publica en el bus y además notifica al stats por compatibilidad."""
        evento_data = kwargs or {}
        try:
            self.bus.publicar(tipo, **kwargs)
        except Exception:
            # si el bus falla, no rompemos el flujo; igualmente notificamos a stats
            pass
        # notificar a stats mediante los hooks antiguos
        try:
            self._notify_stats_from_event(tipo, evento_data)
        except Exception:
            pass

    # ----------------- Apuestas -----------------
    def set_setup_players(self, setup_players: Optional[List[dict]]) -> None:
        self._setup_players = setup_players or []
        self._shooters_list = []
        for p in self._setup_players:
            try:
                jid = int(p.get("jugador", 0))
            except Exception:
                continue
            if p.get("puede_tirar", True) and str(p.get("linea", "")).strip().lower() != "no":
                self._shooters_list.append(jid)
        if not self._shooters_list:
            self._shooters_list = list(range(1, self.max_jugadores_en_mesa + 1))
        self._shooters_idx = 0

    def colocar_apuesta(self, id_jugador: int, tipo: str, monto: int) -> int:
        if str(tipo).lower() == "buena": tipo = "Buena"
        elif str(tipo).lower() == "mala": tipo = "Mala"
        else: tipo = "No"
        if tipo == "No": m = 0
        else: m = clamp_multiplo_500(monto, self.cfg.linea.min_bet, self.cfg.linea.max_bet)
        ap = ApuestaLinea(self._next_apuesta_id, id_jugador, tipo, m, 0)
        self.apuestas_linea.append(ap)
        # publicar evento
        self._publicar("APUESTA_COLOCADA",
                       id_jugador=id_jugador,
                       tipo_apuesta=tipo,
                       monto=m,
                       id_apuesta=ap.id_apuesta)
        self._next_apuesta_id += 1
        return ap.id_apuesta

    def adjuntar_enganche_si_corresponde(self, probabilidad: float = 0.5) -> None:
        if not self.boton_on or self.punto not in self.puntos_validos:
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
            self._publicar("APUESTA_COLOCADA",
                           id_jugador=ap.id_jugador,
                           tipo_apuesta=f"Enganche {ap.tipo}",
                           monto=monto_elegido,
                           id_apuesta=ap.id_apuesta)

    # ----------------- Dados -----------------
    def tirar_dados(self, forzar: Optional[Tuple[int,int]] = None) -> Tuple[int,int,int,bool]:
        if forzar is not None:
            d1, d2 = forzar
        else:
            d1, d2 = self.rng.randint(1,6), self.rng.randint(1,6)
        suma = d1 + d2
        es_doble = (d1 == d2)
        # publicar tiro
        self._publicar("TIRO_INICIADO", d1=d1, d2=d2, suma=suma, es_doble=es_doble)
        # evento extra recomendado por el simulador gráfico
        self._publicar("TIRADA_REALIZADA", dado1=d1, dado2=d2, suma=suma, es_doble=es_doble)
        return d1, d2, suma, es_doble

    # ----------------- Ciclo de un pase (random) -----------------
    def jugar_pase_random(self,
                          num_jugadores: int = 8,
                          p_buena: float = 0.7,
                          pases_linea_min: int = 5000,
                          pases_linea_max: int = 200000,
                          prob_enganche: float = 0.5,
                          setup_players: Optional[List[dict]] = None) -> None:
        # 1) apuestas de línea
        if setup_players is not None:
            self.set_setup_players(setup_players)
            # iniciar pase
            self._inicio_pase(p_buena)
            # reemplazar lista de apuestas
            self.apuestas_linea = []
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
            self._inicio_pase(p_buena)
            self.apuestas_linea.clear()
            for j in range(1, num_jugadores+1):
                tipo = "Buena" if self.rng.random() < p_buena else "Mala"
                base = self.rng.randrange(pases_linea_min // 500, (pases_linea_max // 500) + 1)
                monto = base * 500
                self.colocar_apuesta(j, tipo, monto)

        # 2) come-out
        _, _, suma, _ = self.tirar_dados()
        if suma in (7,11):
            self._resolver_linea_final("come-out 7/11", buena_gana=True)
            self._rotacion_por_resultado_en_off(ganador="Buena")
            self._fin_pase()
            return
        elif suma in (2,3):
            self._resolver_linea_final("come-out 2/3", buena_gana=False)
            self._rotacion_por_resultado_en_off(ganador="Mala")
            self._fin_pase()
            return
        elif suma == 12:
            self._resolver_linea_final_12()
            self._rotacion_por_resultado_en_off(ganador="Empate12")
            self._fin_pase()
            return
        else:
            # establecer Punto
            self.punto = suma
            self.boton_on = True
            self.fase = "ON"
            self._publicar("PUNTO_FIJADO", valor=self.punto)

        # 3) Enganches
        if setup_players is None:
            self.adjuntar_enganche_si_corresponde(probabilidad=prob_enganche)

        # 4) tirar hasta punto o 7
        while True:
            _, _, s2, _ = self.tirar_dados()
            if s2 == self.punto:
                self._resolver_linea_punto_logrado()
                self._rotacion_por_resultado_en_on(ganador="Buena")
                self._fin_pase()
                return
            elif s2 == 7:
                self._resolver_linea_seven_out()
                self._rotacion_por_resultado_en_on(ganador="Mala")
                self._fin_pase()
                return

    # --------- Internos de pase y tirador ---------
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

    def _inicio_pase(self, p_buena: float = 0.7) -> None:
        # publicar NUEVO_TIRADOR -> incluye estado actual del tirador
        self._publicar("NUEVO_TIRADOR",
                       id=self.tirador_id,
                       apuesta_tirador=self.tirador_apuesta,
                       tiros_restantes=(self.tirador_vidas if self.tirador_tiene_vidas else 0),
                       contabiliza_tiros=self.tirador_tiene_vidas)

        # estado de mesa
        self.boton_on = False
        self.fase = "OFF"
        self.punto = None

        # configurar tirador inicial si hace falta
        if not hasattr(self, "_sesion_iniciada"):
            self._sesion_iniciada = True
            self._configurar_tirador_inicial(p_buena)

        # publicar PASE_INICIADO para UI (con resumen de stats)
        try:
            self._publicar("PASE_INICIADO",
                           tirador=self.tirador_id,
                           apuesta=self.tirador_apuesta,
                           vidas=(self.tirador_vidas if self.tirador_tiene_vidas else 0),
                           stats=self.stats.resumen_estado_actual())
        except Exception:
            pass

    def _inicio_pase_forzado(self) -> None:
        self._publicar("NUEVO_TIRADOR",
                       id=self.tirador_id,
                       apuesta_tirador=self.tirador_apuesta,
                       tiros_restantes=0,
                       contabiliza_tiros=False)
        self.boton_on = False
        self.fase = "OFF"
        self.punto = None

    def _configurar_tirador_inicial(self, p_buena: float) -> None:
        if self._shooters_list:
            self._shooters_idx = 0
            self.tirador_id = self._shooters_list[self._shooters_idx % len(self._shooters_list)]
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"
            self.tirador_tiene_vidas = True
            self.tirador_vidas = 3
            return
        self.tirador_id = 1
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"
        self.tirador_tiene_vidas = True
        self.tirador_vidas = 3

    def _rotar_tirador(self, p_buena_para_proximo: Optional[float] = None) -> None:
        if self._shooters_list:
            self._shooters_idx = (self._shooters_idx + 1) % len(self._shooters_list)
            self.tirador_id = self._shooters_list[self._shooters_idx]
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                if p_buena_para_proximo is None:
                    p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"
            self.tirador_tiene_vidas = True
            self.tirador_vidas = 3
            return
        self.tirador_id = (self.tirador_id % self.max_jugadores_en_mesa) + 1
        if p_buena_para_proximo is None:
            p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"
        self.tirador_tiene_vidas = True
        self.tirador_vidas = 3

    def _fin_pase(self, buena_gana: Optional[bool] = None) -> None:
        # publicar PUNTO_LIBRE y FIN_DE_PASE con resumen
        try:
            self._publicar("PUNTO_LIBRE")
        except Exception:
            pass
        # publicar FIN_DE_PASE con info resumida
        try:
            self._publicar("FIN_DE_PASE",
                           tirador=self.tirador_id,
                           ganador=("Buena" if buena_gana else ("Mala" if buena_gana is False else "Empate")),
                           punto=self.punto,
                           stats=self.stats.resumen_estado_actual())
        except Exception:
            pass
        print(f"[MOTOR] Pase completado. Pases acumulados: {self.stats.pases_simulados if self.stats else 'N/A'}")

    # ---- Decisión de rotación según el resultado del pase ----
    def _rotacion_por_resultado_en_off(self, ganador: str) -> None:
        if self.tirador_apuesta == "Buena":
            if ganador == "Buena":
                self.tirador_tiene_vidas = False
            elif ganador in ("Mala", "Empate12"):
                if self.tirador_tiene_vidas:
                    if ganador != "Empate12":
                        self.tirador_vidas -= 1
                    if self.tirador_vidas <= 0:
                        self._rotar_tirador()
                else:
                    self._rotar_tirador()
        else:
            if ganador == "Mala":
                self._rotar_tirador()
            elif ganador == "Empate12":
                pass
            else:
                if self.tirador_tiene_vidas:
                    self.tirador_vidas -= 1
                    if self.tirador_vidas <= 0:
                        self._rotar_tirador()
                else:
                    self._rotar_tirador()

    def _rotacion_por_resultado_en_on(self, ganador: str) -> None:
        if self.tirador_apuesta == "Buena":
            if ganador == "Buena":
                self.tirador_tiene_vidas = False
            else:
                self._rotar_tirador()
        else:
            if ganador == "Mala":
                self._rotar_tirador()
            else:
                self._rotar_tirador()

    # --------- Resoluciones y pagos ---------
    def _resolver_linea_final(self, motivo: str, buena_gana: bool) -> None:
        for ap in self.apuestas_linea:
            if (ap.tipo == "Buena" and buena_gana) or (ap.tipo == "Mala" and not buena_gana):
                self._pagar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo)
            else:
                self._cobrar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo)

    def _resolver_linea_final_12(self) -> None:
        for ap in self.apuestas_linea:
            if ap.tipo == "Buena":
                self._cobrar(ap.id_jugador, ap.monto, "come-out 12", tipo=ap.tipo)
            else:
                self._publicar("APUESTA_RESUELTA",
                               id_jugador=ap.id_jugador,
                               resultado="EMPATE",
                               pago=0,
                               motivo="come-out 12",
                               tipo_apuesta=ap.tipo)

    def _resolver_linea_punto_logrado(self) -> None:
        for ap in self.apuestas_linea:
            if ap.tipo == "Buena":
                self._pagar(ap.id_jugador, ap.monto, "punto logrado", tipo=ap.tipo)
                if ap.enganche > 0:
                    mult = self._true_odds_buena()
                    bruto = ap.enganche * mult
                    pago = redondear_500(bruto)
                    self._pagar(ap.id_jugador, pago, "enganche Buena (true odds)", tipo="Enganche Buena")
            else:
                self._cobrar(ap.id_jugador, ap.monto, "punto logrado", tipo=ap.tipo)
                if ap.enganche > 0:
                    self._cobrar(ap.id_jugador, ap.enganche, "enganche Mala pierde", tipo="Enganche Mala")

    def _resolver_linea_seven_out(self) -> None:
        for ap in self.apuestas_linea:
            if ap.tipo == "Buena":
                self._cobrar(ap.id_jugador, ap.monto, "seven-out", tipo=ap.tipo)
                if ap.enganche > 0:
                    self._cobrar(ap.id_jugador, ap.enganche, "enganche Buena pierde", tipo="Enganche Buena")
            else:
                self._pagar(ap.id_jugador, ap.monto, "seven-out", tipo=ap.tipo)
                if ap.enganche > 0:
                    mult = self._true_reverse_mala()
                    bruto = ap.enganche * mult
                    pago = redondear_500(bruto)
                    self._pagar(ap.id_jugador, pago, "enganche Mala (reverse odds)", tipo="Enganche Mala")

    # pagos y cobros -> publican APUESTA_RESUELTA
    def _pagar(self, id_jugador: int, monto: int, motivo: str, tipo: str) -> None:
        # paga al jugador (disminuye ganancia casino)
        self._publicar("APUESTA_RESUELTA",
                       id_jugador=id_jugador,
                       resultado="GANA",
                       pago=int(monto),
                       motivo=motivo,
                       tipo_apuesta=tipo)

    def _cobrar(self, id_jugador: int, monto: int, motivo: str, tipo: str) -> None:
        # cobra al jugador (aumenta ganancia casino)
        self._publicar("APUESTA_RESUELTA",
                       id_jugador=id_jugador,
                       resultado="PIERDE",
                       pago=int(monto),
                       motivo=motivo,
                       tipo_apuesta=tipo)

    # --------- Odds / límites enganche ---------
    def _true_odds_buena(self) -> float:
        if self.punto in (4, 10):
            return 2.0
        if self.punto in (5, 9):
            return 1.5
        if self.punto in (6, 8):
            return 1.2
        return 0.0

    def _true_odds_mala(self) -> float:
        if self.punto in (4, 10):
            return 0.5
        if self.punto in (5, 9):
            return 2/3
        if self.punto in (6, 8):
            return 5/6
        return 0.0

    def _factor_modo2(self) -> int:
        if self.punto in (4, 10):
            return self.cfg.enganche.factor_4_10
        if self.punto in (5, 9):
            return self.cfg.enganche.factor_5_9
        if self.punto in (6, 8):
            return self.cfg.enganche.factor_6_8
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
