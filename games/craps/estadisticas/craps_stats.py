# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Optional
from collections import deque

FIELD_NUMS = {2,3,4,9,10,11,12}
CUADROS = {2,3,11,12}
COSTILLA = {4,5,6,8,9,10}

class EstadisticasCraps:
    """
    Estadísticas unificadas usadas por MotorCraps + UIs.
    Maneja eventos publicados por BridgeEventosCraps y expone snapshot().
    """

    def __init__(self):
        # contadores principales
        self.pase_actual: int = 0
        self.pases_simulados: int = 0

        # dinero
        self.dinero_en_juego: float = 0.0        
        self.pagos_a_jugadores: float = 0.0
        self.cobros_de_apuestas: float = 0.0
        self.ganancias_casino: float = 0.0

        # tiros
        self.tiros_totales: int = 0

        # OFF counters (resumen simple)
        self.off_buena_ganadas = 0
        self.off_buena_perdidas = 0
        self.off_7 = self.off_11 = self.off_2 = self.off_3 = self.off_12 = 0
        self.off_punto_4_10 = 0
        self.off_punto_5_9 = 0
        self.off_punto_6_8 = 0
        self.off_cuadros_total = 0

        # ON counters
        self.on_buena_ganadas = 0
        self.on_buena_perdidas = 0
        self.on_gana_punto_4_10 = 0
        self.on_gana_punto_5_9 = 0
        self.on_gana_punto_6_8 = 0
        self.on_gana_punto_camunina = 0
        self.on_pierde_7 = 0
        self.on_11 = 0
        self.on_craps = 0
        self.on_cuadros_total = 0

        # totales
        self.tot_buena_ganadas = 0
        self.tot_buena_perdidas = 0
        self.field_total = 0
        self.cuadros_total = 0

        # rachas / pase mas largo
        self.racha_misma_camunina_max = 0
        self.racha_cualquier_camunina_max = 0
        self.racha_cuatro_distintas_max = 0

        self.pase_mas_largo_tiros = 0
        self.pase_mas_largo_costillas = 0
        self.pase_mas_largo_cuadros = 0
        self.pase_mas_largo_resultado_buena = "GANADOR"

        # historiales para graficar
        self.historial_pases: List[int] = []
        self.historial_pct: List[float] = []
        self.historial_step: int = 500

        # temporal por pase
        self._boton_on: bool = False
        self._punto: int = 0
        self._tiros_pase: int = 0
        self._costillas_pase: int = 0
        self._cuadros_pase: int = 0

        # book-keeping apuestas activas
        self._active_bets: Dict[int, float] = {}
        self.total_apuestas_ever: float = 0.0

        # rachas aux
        self._streak_same_val: Optional[int] = None
        self._streak_same_len: int = 0
        self._streak_any_len: int = 0
        self._ventana_ult_4_camuninas: deque = deque(maxlen=4)

    # ---------- util ----------
    def porcentaje_ganancia(self) -> float:
        base = (self.cobros_de_apuestas + self.pagos_a_jugadores)
        if base <= 0:
            return 0.0
        return (self.ganancias_casino / max(1.0, base)) * 100.0

    def snapshot(self) -> dict:
        return {
            "pase_actual": self.pase_actual,
            "pases_simulados": self.pases_simulados,
            "dinero_en_juego": self.dinero_en_juego,
            "ganancias_casino": self.ganancias_casino,
            "porcentaje_ganancia": round(self.porcentaje_ganancia(), 4),
            "tiros_totales": self.tiros_totales,
        }

    # ---------- receptor de eventos ----------
    def on_evento(self, evento: Dict[str, Any]) -> None:
        t = evento.get("tipo")
        if not t:
            return

        # ---- PASE INICIADO ----
        if t == "PASE_INICIADO":
            self.pase_actual += 1
            self.pases_simulados += 1
            # sincronizado: sólo aquí (y en FIN_DE_PASE) actualizamos historial (mismo tamaño x/y)
            if self.pases_simulados % max(1, self.historial_step) == 0:
                self.historial_pases.append(self.pases_simulados)
                self.historial_pct.append(self.porcentaje_ganancia())

        # ---- APUESTA COLOCADA ----
        elif t == "APUESTA_COLOCADA":
            monto = float(evento.get("monto", 0.0) or 0.0)
            id_ap = evento.get("id_apuesta")
            if id_ap is not None:
                try:
                    self._active_bets[int(id_ap)] = monto                    
                except Exception:
                    pass
            self.dinero_en_juego += monto
            self.total_apuestas_ever += monto

        # ---- APUESTA RESUELTA ----
        elif t == "APUESTA_RESUELTA":
            pago_j = float(evento.get("pago_jugador", evento.get("pago", 0)) or 0.0)
            pago_c = float(evento.get("pago_casino", evento.get("pago", 0)) or 0.0)
            id_ap = evento.get("id_apuesta")
            monto_original = float(evento.get("monto_apuesta", evento.get("monto", 0)) or 0.0)
            resultado = evento.get("resultado", "")

            # finanzas
            self.pagos_a_jugadores += pago_j
            self.cobros_de_apuestas += pago_c
            self.ganancias_casino = self.cobros_de_apuestas - self.pagos_a_jugadores

            # restar dinero en juego si estaba registrado
            if id_ap is not None:
                try:
                    prev = self._active_bets.pop(int(id_ap), None)
                    if prev is not None:
                        self.dinero_en_juego = max(0.0, self.dinero_en_juego - prev)
                except Exception:
                    pass
            elif monto_original > 0:
                self.dinero_en_juego = max(0.0, self.dinero_en_juego - monto_original)

            # NOTA: no tocamos historial_pases aquí para evitar desajustes en el gráfico

            # actualizaciones simples por resultado (totales)
            if resultado == "GANA":
                self.tot_buena_ganadas += 1
            elif resultado == "PIERDE":
                self.tot_buena_perdidas += 1

        # ---- TIRO ----
        elif t == "TIRO_INICIADO":
            self.tiros_totales += 1
            self._tiros_pase += 1

            # sumar field/costilla/cuadros si viene suma
            s = evento.get("suma")
            try:
                s = int(s) if s is not None else None
            except Exception:
                s = None

            if s is not None:
                if s in FIELD_NUMS:
                    self.field_total += 1
                if s in COSTILLA:
                    self._costillas_pase += 1
                if s in CUADROS:
                    self._cuadros_pase += 1

                # camunina detection (dobles)
                es_doble = evento.get("es_doble", False)
                d1 = evento.get("d1", evento.get("dado1"))
                d2 = evento.get("d2", evento.get("dado2"))
                try:
                    if es_doble and d1 is not None and d1 == d2 and int(d1) in {2,3,4,5}:
                        camu_val = int(str(int(d1)) * 2)
                        if self._streak_same_val == camu_val:
                            self._streak_same_len += 1
                        else:
                            self._streak_same_val = camu_val
                            self._streak_same_len = 1
                        self.racha_misma_camunina_max = max(self.racha_misma_camunina_max, self._streak_same_len)
                        self._streak_any_len += 1
                        self.racha_cualquier_camunina_max = max(self.racha_cualquier_camunina_max, self._streak_any_len)
                        self._ventana_ult_4_camuninas.append(camu_val)
                        if len(set(self._ventana_ult_4_camuninas)) == 4:
                            self.racha_cuatro_distintas_max = max(self.racha_cuatro_distintas_max, 4)
                    else:
                        self._streak_any_len = 0
                        # no reset de _streak_same_val aquí (se rompe si hay otro camu)
                        self._streak_same_val = None
                        self._streak_same_len = 0
                except Exception:
                    pass

        # ---- PUNTO_FIJADO / PUNTO_LIBRE ----
        elif t == "PUNTO_FIJADO":
            self._boton_on = True
            try:
                v = int(evento.get("valor", 0))
            except Exception:
                v = 0
            self._punto = v
            if v in (4,10):
                self.off_punto_4_10 += 1
            elif v in (5,9):
                self.off_punto_5_9 += 1
            elif v in (6,8):
                self.off_punto_6_8 += 1

        elif t == "PUNTO_LIBRE":
            self._boton_on = False
            self._punto = 0

        # ---- FIN_DE_PASE ----
        elif t == "FIN_DE_PASE":
            snap = evento.get("stats")
            if isinstance(snap, dict):
                try:
                    if snap.get("pases_simulados") is not None:
                        self.pases_simulados = int(snap.get("pases_simulados", self.pases_simulados))
                    if snap.get("dinero_en_juego") is not None:
                        self.dinero_en_juego = float(snap.get("dinero_en_juego", self.dinero_en_juego))
                    if snap.get("ganancias_casino") is not None:
                        self.ganancias_casino = float(snap.get("ganancias_casino", self.ganancias_casino))
                except Exception:
                    pass

            # pase más largo
            if self._tiros_pase > self.pase_mas_largo_tiros:
                self.pase_mas_largo_tiros = self._tiros_pase
                self.pase_mas_largo_costillas = self._costillas_pase
                self.pase_mas_largo_cuadros = self._cuadros_pase
                # No tenemos un booleano "buena_gana" consistente aquí en todos los caminos; si snap trae inf, podrías setearlo.

            # Actualizar acumulado histórico
            # En este punto del pase, dinero_en_juego debería ser 0
            # total_apuestas_ever representa el dinero histórico
            print(
                f"[STATS DEBUG] FIN_DE_PASE -> pase={self.pases_simulados}, "
                f"total_apuestas_ever={self.total_apuestas_ever}, "
                f"dinero_en_juego={self.dinero_en_juego}"
            )

            # recomponer totales
            self.cuadros_total = getattr(self, "off_cuadros_total", 0) + getattr(self, "on_cuadros_total", 0)

            # DEBUG (eliminar después de confirmar que todo funciona):
            print(
                f"[STATS DEBUG] FIN_DE_PASE -> "
                f"dinero_en_juego={self.dinero_en_juego}, "
                f"total_apuestas_ever={self.total_apuestas_ever}, "
                f"dinero_total_acumulado={self.dinero_total_acumulado}"
            )

            # append sincronizado al historial (por pase)
            self.historial_pases.append(self.pases_simulados)
            self.historial_pct.append(self.porcentaje_ganancia())

            # reset temporales de pase
            self._boton_on = False
            self._punto = 0
            self._tiros_pase = 0
            self._costillas_pase = 0
            self._cuadros_pase = 0
