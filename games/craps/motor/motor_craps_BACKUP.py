

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
    Motor mínimo funcional con reglas del tirador:
      - Botón OFF: tirador tiene 3 "vidas" (tiros perdidos permitidos) SOLO hasta su primera victoria.
      - Si el tirador juega **Buena** y GANA un pase, mantiene los dados; desde ahí, ante la PRÓXIMA derrota, pasa los dados.
      - Si el tirador juega **Mala** y GANA un pase, pasa los dados inmediatamente.
      - En Botón ON no se contabilizan vidas: el resultado del pase decide retener/pasar según reglas del tirador.
    """

    puntos_validos = {4,5,6,8,9,10}

    def __init__(self,
                 config: Optional[ConfigMotor] = None,
                 estadisticas: Optional[EstadisticasCrapsMasivo] = None,
                 semilla: Optional[int] = None) -> None:
        
        self.cfg = config or ConfigMotor()
        self.stats = estadisticas or EstadisticasCrapsMasivo()
        self.bus = BridgeEventosCraps(self.stats)        
        self.rng = random.Random(semilla)

        # tiradores validos
        self._setup_players: Optional[List[dict]] = None
        self._shooters_list: List[int] = [] # Lista de ids de jugadores que pueden arrojar dados
        self._shooters_idx: int = 0         # indice circular en _shooters_list

        # estado mesa
        #self.boton_on: bool = False
        self.fase = "OFF"
        #self.punto: int = 0
        self.punto = None
        self.observadores = []

        # estado del tirador
        self.tirador_id: int = 1
        self.tirador_apuesta: str = "Buena"  # "Buena" | "Mala"
        self.tirador_tiene_vidas: bool = True   # mientras no gane un pase (y solo en OFF)
        self.tirador_vidas: int = 3            # vidas disponibles en OFF
        # rotación configurable
        self.max_jugadores_en_mesa: int = 12
        # random off o sea
        self._modo_masivo = True
        # apuestas línea por pase
        self._next_apuesta_id: int = 1
        self.apuestas_linea: List[ApuestaLinea] = []

    ## OBSERVADORES
    def registrar_observador(self, fn):
        """Recibe funciones que reciben un diccionario evento"""
        self.observadores.append(fn)
    
    def notificar_evento(self, evento: dict):
        """Llama a todos los observadores registrados"""
        for obs in self.observadores:
            obs(evento)

    # -------- API de eventos (proxy) --------
    def suscribir(self, tipo_evento: str, handler) -> None:
        self.bus.suscribir(tipo_evento, handler)

    # -------- API pública --------
    def set_setup_players(self, setup_players: Optional[List[dict]]) -> None:
        """
        Registrar la lista completa de players que viene del setup.
        Construye internamente la lista de ids que SÍ pueden tirar (linea != "No").
        """
        self._setup_players = setup_players or []
        # construir lista de shooters: solo los jugadores cuyo campo 'puede_tirar' sea True
        self._shooters_list = []
        for p in self._setup_players:
            try:
                jid = int(p.get("jugador", 0))
            except Exception:
                continue
            if p.get("puede_tirar", True) and str(p.get("linea","")).strip().lower() != "no":
                self._shooters_list.append(jid)
        # si no hay shooters (por ejemplo no llegó setup), mantenemos el fallback por ids 1..max_jugadores_en_mesa
        if not self._shooters_list:
            self._shooters_list = list(range(1, self.max_jugadores_en_mesa + 1))
        self._shooters_idx = 0
        # si queremos, configurar tirador inicial ya:
        # no forzamos tirador_apuesta aquí (se hace en _configurar_tirador_inicial cuando arranque sesión)


    def colocar_apuesta(self, id_jugador: int, tipo: str, monto: int) -> int:
        if str(tipo).lower() == "buena": tipo = "Buena"
        elif str(tipo).lower() == "mala": tipo = "Mala"
        else: tipo == "No"
        if tipo == "No": m = 0
        else: m = clamp_multiplo_500(monto, self.cfg.linea.min_bet, self.cfg.linea.max_bet)
        ap = ApuestaLinea(self._next_apuesta_id, id_jugador, tipo, m, 0)
        self.apuestas_linea.append(ap)
        print(f'Antes de publicar en el bus, tenemos:\nTipo: {tipo}\nid_jugador: {id_jugador}\nMonto: {m}\nid_apuesta: {ap.id_apuesta}')
        self.bus.publicar("APUESTA_COLOCADA",
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
            self.bus.publicar("APUESTA_COLOCADA",
                              id_jugador=ap.id_jugador,
                              tipo_apuesta=f"Enganche {ap.tipo}",
                              monto=monto_elegido,
                              id_apuesta=ap.id_apuesta)

    def tirar_dados(self):
        import random
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        suma = d1 + d2
        es_doble = d1 == d2
        return d1, d2, suma, es_doble
    
    def resolver_tiro(self, suma):
        """
        Devuelve:
        resultado: "GANA" | "PIERDE" | "SIGUE"
        pago: monto que se paga positivo/cobra negativo (lo manejará stats)
        tipo: "come-out" | "point"
        motivo: descripción textual
        """

        # -----------------------
        # FASE OFF (COME OUT)
        # -----------------------
        if self.fase == "OFF":

            if suma in (7, 11):
                self.notificar_evento({
                    "tipo": "comeout_gana",
                    "suma": suma
                })
                return "GANA", None, "come-out", "come-out gana"

            if suma in (2, 3):
                self.notificar_evento({
                    "tipo": "comeout_pierde",
                    "suma": suma
                })
                return "PIERDE", None, "come-out", "come-out pierde"

            if suma == 12:
                self.notificar_evento({
                    "tipo": "comeout_push",
                    "suma": suma
                })
                return "SIGUE", None, "come-out", "come-out push"

            # Se establece punto
            self.fase = "ON"
            self.punto = suma
            self.notificar_evento({
                "tipo": "punto_establecido",
                "punto": suma
            })
            return "SIGUE", None, "point", "punto establecido"

        # -----------------------
        # FASE ON (POINT)
        # -----------------------
        if suma == self.punto:
            self.notificar_evento({
                "tipo": "punto_ganado",
                "punto": suma
            })
            self.fase = "OFF"
            self.punto = None
            return "GANA", None, "point", "punto logrado"

        if suma == 7:
            self.notificar_evento({
                "tipo": "seven_out",
            })
            self.fase = "OFF"
            self.punto = None
            return "PIERDE", None, "point", "seven-out"

        # Sigue tirando
        self.notificar_evento({
            "tipo": "sin_cambio",
            "suma": suma
        })
        return "SIGUE", None, "point", "sin cambio"

    # -------- Ciclo de un pase (random) --------
    def jugar_pase_random(self,
                          num_jugadores: int = 8,
                          p_buena: float = 0.7,
                          pases_linea_min: int = 5000,
                          pases_linea_max: int = 200000,
                          prob_enganche: float = 0.5,
                          setup_players: Optional[List[dict]] = None) -> None:
        
        """
        Simula 1 pase completo con:
        - Si setup_player es None (apuestas aleatorias que voy a aplicar luego en simulacion grafica)
        - Si setup_player es lista de dicts entonces utiliza esas apuestas y en ese orden
          {
            "jugador": int,
            "linea": "Buena"|"Mala",
            "monto": int (monto exacto)
          }            
        """

                

        # 1) apuestas de línea
        # Si se recibieron apuestas desde setup -> respetarlas tal cual
        if setup_players is not None:
            # registrar setup local y lista de shooters
            self.set_setup_players(setup_players)
            # comenzar el pase (ahora _inicio_pase usará self.tirador_id ya existente)
            self._inicio_pase(p_buena)  # para mantener el flujo de NUEVO_TIRADOR / reset de boton
            # no limpiamos para respetar posible estado, pero vamos a reemplazar la lista de apuestas de línea
            self.apuestas_linea = []
            for pl in setup_players[:num_jugadores]:
                jid = int(pl.get("jugador", 0)) or (len(self.apuestas_linea) + 1)
                linea = str(pl.get("linea", "Buena")).strip()
                if linea.lower() == "no":
                    # este jugador NO coloca apuesta de línea — saltamos colocar_apuesta
                    continue
                tipo = "Buena" if linea.lower() == "buena" else "Mala"
                monto = int(pl.get("monto", pases_linea_min))
                monto = clamp_multiplo_500(monto, self.cfg.linea.min_bet, self.cfg.linea.max_bet)
                self.colocar_apuesta(jid, tipo, monto)
        else:
            # crear apuestas aleatorias
            # --- inicio del pase aleatorio
            self._inicio_pase(p_buena)
            self.apuestas_linea.clear()
            for j in range(1, num_jugadores+1):
                tipo = "Buena" if self.rng.random() < p_buena else "Mala"
                base = self.rng.randrange(pases_linea_min // 500, (pases_linea_max // 500) + 1)
                monto = base * 500
                self.colocar_apuesta(j, tipo, monto)        

        # 2) Fase 1 — come-out
        _, _, suma, _ = self.tirar_dados()
        if suma in (7, 11):
            # Gana Buena, pierde Mala
            self._resolver_linea_final("come-out 7/11", buena_gana=True)
            self._rotacion_por_resultado_en_off(ganador="Buena")
            self._fin_pase()
            return
        elif suma in (2, 3):
            # Pierde Buena, gana Mala
            self._resolver_linea_final("come-out 2/3", buena_gana=False)
            self._rotacion_por_resultado_en_off(ganador="Mala")
            self._fin_pase()
            return
        elif suma == 12:
            # Buena pierde, Mala empata
            self._resolver_linea_final_12()
            self._rotacion_por_resultado_en_off(ganador="Empate12")  # empata Mala
            self._fin_pase()
            return
        else:
            # establecer Punto → Fase 2
            self.punto = suma
            self.boton_on = True
            self.bus.publicar("PUNTO_FIJADO", valor=self.punto)

        # 3) Enganches
        if setup_players is None:            
            self.adjuntar_enganche_si_corresponde(probabilidad=prob_enganche)

        # 4) Fase 2 — tirar hasta Punto o 7
        while True:
            _, _, s2, _ = self.tirar_dados()
            if s2 == self.punto:
                # Buena gana, Mala pierde
                self._resolver_linea_punto_logrado()
                self._rotacion_por_resultado_en_on(ganador="Buena")
                self._fin_pase()
                return
            elif s2 == 7:
                # seven-out: Mala gana, Buena pierde
                self._resolver_linea_seven_out()
                self._rotacion_por_resultado_en_on(ganador="Mala")
                self._fin_pase()
                return
            # otros números: sin accesorios en esta versión
        
            

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

    def _inicio_pase(self, p_buena: float) -> None:
        """
        Decide si es tirador nuevo o continuidad, prepara estado y emite NUEVO_TIRADOR.
        Regla: si recién pasaron los dados en el pase anterior, configuramos nuevo tirador
               con 3 vidas en OFF y su apuesta (Buena/Mala).
        """
        # Si venimos de fin de pase anterior, self.boton_on ya se resetea en _fin_pase
        # pero la rotación del tirador la resolvemos ya en _fin_pase.
        # Acá solo publicamos el “estado actual del tirador” al iniciar el pase.
        self.bus.publicar("NUEVO_TIRADOR",
                          id=self.tirador_id,
                          apuesta_tirador=self.tirador_apuesta,
                          tiros_restantes=(self.tirador_vidas if self.tirador_tiene_vidas else 0),
                          contabiliza_tiros=self.tirador_tiene_vidas)

        # estado de mesa al inicio del pase
        self.boton_on = False
        self.punto = 0

        # Si acabamos de rotar en el _fin_pase anterior, quizá queremos randomizar apuesta del nuevo tirador:
        # Heurística simple: cuando cambiamos de tirador, seteamos su apuesta ahora.
        # (Detectamos "tirador recién configurado" si en el pase previo se marcó tirador_tiene_vidas=True y vidas=3)
        # Para evitar branch complejo, si vidas == 3 y contabiliza_tiros True, dejamos como está.
        # Si fue rotado en _fin_pase por victoria/perdida, ya se setea en esa función.

        # Pero si este es el primer pase de la sesión (arranque del proceso),
        # aseguramos estado consistente: tirador nuevo con 3 vidas y apuesta random.
        if not hasattr(self, "_sesion_iniciada"):
            self._sesion_iniciada = True
            self._configurar_tirador_inicial(p_buena)

    def _inicio_pase_forzado(self) -> None:
        self.bus.publicar("NUEVO_TIRADOR",
                          id=self.tirador_id,
                          apuesta_tirador=self.tirador_apuesta,
                          tiros_restantes=0,
                          contabiliza_tiros=False)
        self.boton_on = False
        self.punto = 0



    def _configurar_tirador_inicial(self, p_buena: float) -> None:
        # Si tenemos lista explícita de shooters desde el setup, usala.
        if self._shooters_list:
            # poner como tirador el primer de la lista
            self._shooters_idx = 0
            self.tirador_id = self._shooters_list[self._shooters_idx % len(self._shooters_list)]
            # si el setup trae la linea del jugador, respetarla; si no, fallback a random por p_buena
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"
            self.tirador_tiene_vidas = True
            self.tirador_vidas = 3
            return

        # fallback: comportamiento anterior (sin setup)
        self.tirador_id = 1
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena else "Mala"
        self.tirador_tiene_vidas = True
        self.tirador_vidas = 3

    def _rotar_tirador(self, p_buena_para_proximo: Optional[float] = None) -> None:
        # Si tenemos lista de shooters, avanzamos circularmente por ella
        if self._shooters_list:
            self._shooters_idx = (self._shooters_idx + 1) % len(self._shooters_list)
            self.tirador_id = self._shooters_list[self._shooters_idx]
            # definir apuesta según setup si está dado
            line = self._player_line_by_id(self.tirador_id)
            if line is not None and str(line).strip().lower() != "no":
                self.tirador_apuesta = "Buena" if str(line).strip().lower() == "buena" else "Mala"
            else:
                # fallback a probabilistico si no hay info de linea
                if p_buena_para_proximo is None:
                    p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
                self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"
            self.tirador_tiene_vidas = True
            self.tirador_vidas = 3
            return

        # fallback original si no hay setup
        self.tirador_id = (self.tirador_id % self.max_jugadores_en_mesa) + 1
        if p_buena_para_proximo is None:
            p_buena_para_proximo = getattr(self, "_session_p_buena", 0.7)
        self.tirador_apuesta = "Buena" if self.rng.random() < p_buena_para_proximo else "Mala"
        self.tirador_tiene_vidas = True
        self.tirador_vidas = 3
        

    def _fin_pase(self) -> None:
        self.bus.publicar("PUNTO_LIBRE")
        print(f"[MOTOR] Pase completado. Pases acumulados: {self.stats.pases_simulados if self.stats else 'N/A'}")
        # Nota: NO rotamos acá; la rotación se decide en _rotacion_por_resultado_en_off/on

    # ---- Decisión de rotación según el resultado del pase ----

    def _rotacion_por_resultado_en_off(self, ganador: str) -> None:
        """
        ganador ∈ {"Buena", "Mala", "Empate12"}
        Reglas:
          - Si tirador juega "Buena":
              * Gana en 7/11 -> mantiene dados; vidas dejan de contarse (ya ganó una vez).
              * Pierde en 2/3/12 -> si tenía vidas, restar 1; si llega a 0 -> pasa dados.
              * Si ya había ganado alguna vez (vidas desactivadas), cualquier pérdida pasa dados.
          - Si tirador juega "Mala":
              * Gana en 2/3 -> pasa dados inmediatamente.
              * 12 = empate -> sigue tirando (vidas no cambian).
              * Pierde en 7/11 -> si tenía vidas, restar 1; si llega a 0 -> pasa dados.
        """
        if self.tirador_apuesta == "Buena":
            if ganador == "Buena":  # 7/11
                # ganó un pase → ya no se contabilizan vidas
                self.tirador_tiene_vidas = False
            elif ganador in ("Mala", "Empate12"):
                # pérdida para Buena (2/3/12) — 12 es pérdida de Buena
                if self.tirador_tiene_vidas:
                    if ganador != "Empate12":  # (para Buena, 12 es pérdida, sí resta vida)
                        self.tirador_vidas -= 1
                    # si se acaban vidas → pasa dados
                    if self.tirador_vidas <= 0:
                        self._rotar_tirador()
                else:
                    # ya no se contabilizan vidas: pérdida → pasa dados
                    self._rotar_tirador()
        else:  # tirador juega "Mala"
            if ganador == "Mala":  # 2/3
                # si gana Don't en OFF, pasa los dados inmediatamente
                self._rotar_tirador()
            elif ganador == "Empate12":
                # 12 = push para Mala → sin cambios de vidas
                pass
            else:  # "Buena" (7/11) → pérdida para Mala
                if self.tirador_tiene_vidas:
                    self.tirador_vidas -= 1
                    if self.tirador_vidas <= 0:
                        self._rotar_tirador()
                else:
                    # si ya no se contabilizan vidas (después de alguna victoria previa),
                    # cualquier pérdida pasa dados (raro en Mala, pero consistente)
                    self._rotar_tirador()

    def _rotacion_por_resultado_en_on(self, ganador: str) -> None:
        """
        ganador ∈ {"Buena","Mala"} al resolverse el Punto (Punto logrado o seven-out).
        Reglas:
          - En ON no hay contador: el resultado manda.
          - Tirador "Buena":
              * Gana → mantiene dados y desactiva vidas.
              * Pierde → pasa dados.
          - Tirador "Mala":
              * Gana → pasa dados.
              * Pierde → si ya había ganado antes (vidas desactivadas), pasa; si nunca ganó aún,
                         igual pasa (en ON no se usan vidas).
        """
        if self.tirador_apuesta == "Buena":
            if ganador == "Buena":
                self.tirador_tiene_vidas = False
                # mantiene dados
            else:  # pierde
                self._rotar_tirador()
        else:  # Mala
            if ganador == "Mala":
                self._rotar_tirador()
            else:
                # pierde en ON → pasa dados igual
                self._rotar_tirador()

    # --------- Resoluciones y pagos ---------

    def _resolver_linea_final(self, motivo: str, buena_gana: bool) -> None:
        for ap in self.apuestas_linea:
            if (ap.tipo == "Buena" and buena_gana) or (ap.tipo == "Mala" and not buena_gana):
                self._pagar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo)
            else:
                self._cobrar(ap.id_jugador, ap.monto, motivo, tipo=ap.tipo)
        # sin enganches en OFF
        

    def _resolver_linea_final_12(self) -> None:
        for ap in self.apuestas_linea:
            if ap.tipo == "Buena":
                self._cobrar(ap.id_jugador, ap.monto, "come-out 12", tipo=ap.tipo)
            else:
                self.bus.publicar("APUESTA_RESUELTA",
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
    
    def _resolver_field(self, tirada: int, jugador, monto: int):
        if tirada in (3, 4, 9, 10, 11):
            self._pagar(jugador["id"], monto, "Field gana 1:1", tipo="Field")
        elif tirada in (2, 12):
            self._pagar(jugador["id"], monto * 2, "Field gana 2:1", tipo="Field")
        else:
            self._cobrar(jugador["id"], monto, "Field pierde", tipo="Field")

    def _resolver_enganche(self, punto: int, tirada: int, jugador, monto: int):
        if jugador["linea"] == "Buena":
            if tirada == punto:
                mult = self._true_odds_buena(punto)
                self._pagar(jugador["id"], int(monto * mult), f"Enganche Buena ({punto})", tipo="Enganche Buena")
            elif tirada == 7:
                self._cobrar(jugador["id"], monto, "Enganche Buena pierde", tipo="Enganche Buena")
        else:
            if tirada == 7:
                mult = self._true_odds_mala(punto)
                self._pagar(jugador["id"], int(monto * mult), f"Enganche Mala ({punto})", tipo="Enganche Mala")
            elif tirada == punto:
                self._cobrar(jugador["id"], monto, "Enganche Mala pierde", tipo="Enganche Mala")

    def _pagar(self, id_jugador: int, monto: int, motivo: str, tipo: str) -> None:
        self.bus.publicar("APUESTA_RESUELTA",
                          id_jugador=id_jugador,
                          resultado="GANA",
                          pago=int(monto),
                          motivo=motivo,
                          tipo_apuesta=tipo)

    def _cobrar(self, id_jugador: int, monto: int, motivo: str, tipo: str) -> None:
        self.bus.publicar("APUESTA_RESUELTA",
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

    ## PARA HACER EL x2 x3 x4
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
        else:  # Mala
            base = ap.monto * self._true_odds_buena()
            if modo == 2:
                base *= self._factor_modo2()
            return redondear_500(base)
