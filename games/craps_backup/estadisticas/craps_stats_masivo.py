
# games/craps/estadisticas/craps_stats_masivo.py
# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from collections import deque

FIELD_NUMS = {2,3,4,9,10,11,12}
CUADROS = {2,3,11,12}
COSTILLA = {4,5,6,8,9,10}
CAMU_MAP = {(1,1):None,(2,2):22,(3,3):33,(4,4):44,(5,5):55,(6,6):None}  # mapa de ayuda resumen

@dataclass
class EstadisticasCrapsMasivo:
    # Progreso / dinero
    pases_objetivo: int = 0
    pases_simulados: int = 0
    ganancias_casino: float = 0.0
    pagos_a_jugadores: float = 0.0
    cobros_de_apuestas: float = 0.0
    dinero_en_juego: float = 0.0    

    # OFF
    off_buena_ganadas: int = 0
    off_buena_perdidas: int = 0
    off_7: int = 0
    off_11: int = 0
    off_2: int = 0
    off_3: int = 0
    off_12: int = 0
    off_punto_4_10: int = 0
    off_punto_5_9: int = 0
    off_punto_6_8: int = 0
    off_cuadros_total: int = 0  # 2/3/11/12 en OFF

    # ON
    on_buena_ganadas: int = 0
    on_buena_perdidas: int = 0
    on_gana_punto_4_10: int = 0
    on_gana_punto_5_9: int = 0
    on_gana_punto_6_8: int = 0
    on_gana_punto_camunina: int = 0
    on_pierde_7: int = 0
    on_11: int = 0
    on_craps: int = 0
    on_cuadros_total: int = 0  # on_11 + on_craps

    # Totales
    tot_buena_ganadas: int = 0
    tot_buena_perdidas: int = 0
    field_total: int = 0
    cuadros_total: int = 0
    tiros_totales: int = 0

    # Rachas camuninas
    racha_misma_camunina_max: int = 0
    racha_cualquier_camunina_max: int = 0
    racha_cuatro_distintas_max: int = 0

    # Pase más largo
    pase_mas_largo_tiros: int = 0
    pase_mas_largo_costillas: int = 0
    pase_mas_largo_cuadros: int = 0
    pase_mas_largo_resultado_buena: str = "GANADOR"  # o PERDEDOR

    # Histórico para gráfico (% de ganancia)
    historial_pases: List[int] = field(default_factory=list)
    historial_pct: List[float] = field(default_factory=list)
    historial_step: int = 500

    # ---- Estado temporal de pase / rachas ----
    _boton_on: bool = False
    _punto: int = 0
    _tiros_pase: int = 0
    _costillas_pase: int = 0
    _cuadros_pase: int = 0

    _streak_same_val: Optional[int] = None   # 22/33/44/55
    _streak_same_len: int = 0
    _streak_any_len: int = 0
    _ventana_ult_4_camuninas: deque = field(default_factory=lambda: deque(maxlen=4))

    def porcentaje_ganancia(self) -> float:
        return (self.ganancias_casino / self.dinero_en_juego * 100.0) if self.dinero_en_juego > 0 else 0.0

    # ---------- hooks ---------
    def on_nuevo_tirador(self) -> None:
        # iniciar un nuevo pase
        self._boton_on = False
        self._punto = 0
        self._tiros_pase = 0
        self._costillas_pase = 0
        self._cuadros_pase = 0

    def on_apuesta(self, monto: float) -> None:        
        self.dinero_en_juego += float(monto)

    def on_tiro(self, d1: int, d2: int, suma: int, es_doble: bool) -> None:
        self.tiros_totales += 1
        self._tiros_pase += 1

        # Field en cualquier fase
        if suma in FIELD_NUMS:
            self.field_total += 1

        # Costilla/cuadros por tiro (para pase más largo y tallys de fase)
        if suma in COSTILLA:
            self._costillas_pase += 1
        if suma in CUADROS:
            self._cuadros_pase += 1
            if self._boton_on:
                if suma == 11:
                    self.on_11 += 1
                else:  # 2/3/12
                    self.on_craps += 1
                self.on_cuadros_total += 1
            else:
                self.off_cuadros_total += 1

        # Rachas camuninas (22/33/44/55)
        camu_val = None
        if es_doble and suma in {4,6,8,10}:
            # mapear a 22/33/44/55
            if d1 == d2 and d1 in {2,3,4,5}:
                camu_val = int(str(d1) * 2)  # 22,33,44,55

        # racha misma
        if camu_val is not None:
            if self._streak_same_val == camu_val:
                self._streak_same_len += 1
            else:
                self._streak_same_val = camu_val
                self._streak_same_len = 1
            self.racha_misma_camunina_max = max(self.racha_misma_camunina_max, self._streak_same_len)
            # racha “cualquier camunina”
            self._streak_any_len += 1
            self.racha_cualquier_camunina_max = max(self.racha_cualquier_camunina_max, self._streak_any_len)
            # ventana 4 distintas
            self._ventana_ult_4_camuninas.append(camu_val)
            if len(set(self._ventana_ult_4_camuninas)) == 4:
                self.racha_cuatro_distintas_max = max(self.racha_cuatro_distintas_max, 4)
                # seguimos dejando que se superpongan; no reiniciamos
        else:
            # se rompe la racha de “cualquier”
            self._streak_any_len = 0
            # cambiar de camunina rompe “misma”
            self._streak_same_val = None
            self._streak_same_len = 0
            self._ventana_ult_4_camuninas.clear()

    def on_punto_fijado(self, valor: int) -> None:
        self._boton_on = True
        self._punto = int(valor)
        
        if valor in (4,10): self.off_punto_4_10 += 1
        elif valor in (5,9): self.off_punto_5_9 += 1
        elif valor in (6,8): self.off_punto_6_8 += 1

    def on_resolucion(self, resultado: str, pago: float, tipo: str, motivo: str) -> None:
        # Registrar ganancia de casino: GANA = paga al jugador (resta), PIERDE = cobra (suma)
        if resultado == "GANA":   
            self.ganancias_casino -= float(pago)
            self.pagos_a_jugadores += float(pago)
        elif resultado == "PIERDE": 
            self.ganancias_casino += float(pago)
            self.cobros_de_apuestas += float(pago)            

        # Línea (para sumar ganadas/perdidas OFF/ON y breakdown)
        t = (tipo or "").lower()
        if t in ("buena","mala","enganche buena","enganche mala","no"):
            # ¿estamos resolviendo el cierre del pase? lo detectamos por motivo
            m = (motivo or "").lower()
            if not self._boton_on:
                # sólo 7/11/2/3/12
                if m.startswith("come-out"):
                    if "7/11" in m:
                        # Buena gana
                        self.off_buena_ganadas += 1
                        if t != "no":
                            self.off_7 += 1 if "7" in m else 0
                            self.off_11 += 1 if "11" in m else 0
                    elif "2/3" in m:
                        # Buena pierde
                        self.off_buena_perdidas += 1
                        if t != "no":
                            self.off_2 += 1 if "2" in m else 0  # contamos ambas abajo
                            self.off_3 += 1 if "3" in m else 0
                    elif "12" in m:
                        self.off_buena_perdidas += 1
                        if t != "no": self.off_12 += 1
            else:
                if m == "punto logrado":
                    # Buena gana por punto
                    self.on_buena_ganadas += 1
                    if self._punto in (4,10): self.on_gana_punto_4_10 += 1
                    elif self._punto in (5,9): self.on_gana_punto_5_9 += 1
                    elif self._punto in (6,8): self.on_gana_punto_6_8 += 1
                elif m == "seven-out":
                    # Buena pierde con 7
                    self.on_buena_perdidas += 1
                    self.on_pierde_7 += 1

    def on_fin_pase(self, buena_gana: Optional[bool]) -> None:
        # 1) actualizar históricos / contador de pases (hacelo PRIMERO)
        self.pases_simulados += 1

        # Histórico por step
        if self.pases_simulados % max(1, self.historial_step) == 0:
            self.historial_pases.append(self.pases_simulados)
            self.historial_pct.append(self.porcentaje_ganancia())

        # 2) Finalizar pase y actualizar “pase más largo” (antes de resetear _tiros_pase)
        if self._tiros_pase > self.pase_mas_largo_tiros:
            self.pase_mas_largo_tiros = self._tiros_pase
            self.pase_mas_largo_costillas = self._costillas_pase
            self.pase_mas_largo_cuadros = self._cuadros_pase
            self.pase_mas_largo_resultado_buena = "GANADOR" if buena_gana else "PERDEDOR"        

        # 4) Cuadros totales globales
        self.cuadros_total = self.off_cuadros_total + self.on_cuadros_total

        # 5) reset de estado temporal de pase
        self._boton_on = False
        self._punto = 0
        self._tiros_pase = 0
        self._costillas_pase = 0
        self._cuadros_pase = 0

        