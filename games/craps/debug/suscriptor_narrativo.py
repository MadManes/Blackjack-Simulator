# games/craps/debug/suscriptor_narrativo.py
from __future__ import annotations
from typing import Dict, Any, List, Optional
import os

from games.craps.estadisticas.craps_stats import EstadisticasCraps

class ActualizadorEstadisticas:
    def __init__(self, stats: EstadisticasCraps) -> None:
        self.stats = stats

    def __call__(self, evento: Dict[str, Any]) -> None:
        t = evento.get("tipo")
        if t == "NUEVO_TIRADOR":
            self.stats.total_pases += 1
            self.stats.tiros_por_pase.append(0)
            self.stats.dinero_en_juego_pase_actual = 0.0
        elif t == "APUESTA_COLOCADA":
            monto = float(evento.get("monto", 0))
            self.stats.dinero_en_juego_pase_actual += monto
            self.stats.dinero_en_juego += monto
        elif t == "TIRO_INICIADO":
            if self.stats.tiros_por_pase:
                self.stats.tiros_por_pase[-1] += 1
        elif t == "APUESTA_RESUELTA":
            res = str(evento.get("resultado", "")).upper()
            pago = float(evento.get("pago", 0))
            tipo = str(evento.get("tipo_apuesta", "")).lower()
            if res == "GANA":
                self.stats.ganancias_casino -= pago
                if tipo == "buena":
                    self.stats.linea_buena_ganadas += 1
                elif tipo == "mala":
                    self.stats.linea_mala_ganadas += 1
            elif res == "PIERDE":
                self.stats.ganancias_casino += pago
            elif res == "EMPATE":
                self.stats.linea_empates += 1

class SuscriptorEventosNarrativo:
    def __init__(self, stats: EstadisticasCraps, ruta_archivo: str = "logs/craps/debug_narrativo.log") -> None:
        self.stats = stats
        self.ruta = ruta_archivo
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        open(self.ruta, "w", encoding="utf-8").close()

        self.tirador_actual: Optional[int] = None
        self.tirador_apuesta: str = "Buena"
        self.tirador_tiros_restantes: int = 0
        self.tirador_contabiliza: bool = False

        self.apuestas_pase: List[Dict[str, Any]] = []
        self.pagos_pase: List[Dict[str, Any]] = []
        self.boton_on: bool = False
        self.punto: int = 0
        self.tiro_n: int = 0
        self._apuestas_impresas: int = 0

    def _w(self, linea: str = "") -> None:
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(linea + "\n")

    def _porcentaje(self) -> float:
        if self.stats.dinero_en_juego > 0:
            return (self.stats.ganancias_casino / self.stats.dinero_en_juego) * 100.0
        return 0.0

    def _encabezado_pase(self) -> None:
        self._w(f"Pase {self.stats.total_pases}:\n")
        self._w(f"Dinero en juego en este pase: {int(self.stats.dinero_en_juego_pase_actual)}")
        self._w(f"Dinero en juego acumulado: {int(self.stats.dinero_en_juego)}")
        self._w(f"Ganancia del casino: $ {int(self.stats.ganancias_casino)}")
        self._w(f"Porcentaje de ganancia del casino: {self._porcentaje():.2f} %\n")
        self._w(f"Numero de jugadores: (según apuestas del pase)")
        self._w(f"Tirador: {self.tirador_actual} ({self.tirador_apuesta}) ")
        if not self.boton_on and self.tirador_contabiliza and self.tirador_tiros_restantes > 0:
            self._w(f"\nTiros disponibles: {self.tirador_tiros_restantes}")
        self._w("")

    def _imprimir_apuestas(self, desde: int = 0, titulo: Optional[str] = None) -> None:
        if desde >= len(self.apuestas_pase):
            return
        if titulo:
            self._w(titulo)
        for ap in self.apuestas_pase[desde:]:
            self._w(f"Jugador {ap['id_jugador']}:  Apuesta {int(ap['monto'])} a {ap['tipo']}")
        self._w("")
        self._w(f"Dinero en juego en este pase: {int(self.stats.dinero_en_juego_pase_actual)}")
        self._w(f"Dinero en juego acumulado: {int(self.stats.dinero_en_juego)}\n")
        self._apuestas_impresas = len(self.apuestas_pase)

    def _imprimir_fase(self) -> None:
        fase = "Boton On" if self.boton_on else "Boton off"
        self._w(f"Fase: {fase}")

    def _imprimir_pagos(self) -> None:
        self._w("\nPagos pase:")
        if not self.pagos_pase:
            self._w("(Sin pagos registrados)")
            return

        agreg: Dict[int, Dict[str, int]] = {}
        for p in self.pagos_pase:
            j = int(p.get("id_jugador"))
            res = str(p.get("resultado")).upper()
            monto = int(float(p.get("pago", 0)))
            tipo = str(p.get("tipo", p.get("tipo_apuesta", ""))).lower()
            es_enganche = "enganche" in tipo
            d = agreg.setdefault(j, {
                "gana_linea": 0, "pierde_linea": 0, "empate_linea": 0,
                "gana_eng": 0, "pierde_eng": 0
            })
            if res == "GANA":
                if es_enganche:
                    d["gana_eng"] += monto
                else:
                    d["gana_linea"] += monto
            elif res == "PIERDE":
                if es_enganche:
                    d["pierde_eng"] += monto
                else:
                    d["pierde_linea"] += monto
            elif res == "EMPATE":
                d["empate_linea"] += 1

        for j in sorted(agreg.keys()):
            d = agreg[j]
            if d["pierde_linea"] or d["pierde_eng"]:
                if d["pierde_eng"]:
                    self._w(f"Jugador {j}:  Pierde {d['pierde_linea'] + d['pierde_eng']} (incluye {d['pierde_eng']} de enganche)")
                else:
                    self._w(f"Jugador {j}:  Pierde {d['pierde_linea']}")
            if d["gana_linea"] or d["gana_eng"]:
                if d["gana_eng"]:
                    self._w(f"Jugador {j}:  Gana {d['gana_linea']} + {d['gana_eng']} de enganche")
                else:
                    self._w(f"Jugador {j}:  Gana {d['gana_linea']}")
            if d["empate_linea"] and not (d["gana_linea"] or d["pierde_linea"]):
                self._w(f"Jugador {j}:  Empate")

    def _imprimir_resumen_pase(self) -> None:
        self._w("\nResumen pase:")
        self._w(f"Dinero en juego en este pase: {int(self.stats.dinero_en_juego_pase_actual)}")
        self._w(f"Dinero en juego acumulado: {int(self.stats.dinero_en_juego)}")
        self._w(f"Ganancia del casino: $ {int(self.stats.ganancias_casino)}")
        self._w(f"Porcentaje de ganancia del casino: {self._porcentaje():.2f} %")
        self._w("\n" + "-" * 106 + "\n")

    def __call__(self, evento: Dict[str, Any]) -> None:
        t = evento.get("tipo")

        if t == "NUEVO_TIRADOR":
            self.tirador_actual = evento.get("id")
            self.tirador_apuesta = str(evento.get("apuesta_tirador", "Buena"))
            self.tirador_tiros_restantes = int(evento.get("tiros_restantes", 0) or 0)
            self.tirador_contabiliza = bool(evento.get("contabiliza_tiros", False))

            self.apuestas_pase = []
            self.pagos_pase = []
            self.boton_on = False
            self.punto = 0
            self.tiro_n = 0
            self._apuestas_impresas = 0

            self._w("")
            self._encabezado_pase()

        elif t == "APUESTA_COLOCADA":
            self.apuestas_pase.append({
                "id_jugador": evento.get("id_jugador"),
                "monto": float(evento.get("monto", 0)),
                "tipo": evento.get("tipo_apuesta"),
            })

        elif t == "TIRO_INICIADO":
            self.tiro_n += 1
            d1, d2, suma = evento["d1"], evento["d2"], evento["suma"]
            if self._apuestas_impresas < len(self.apuestas_pase):
                titulo = "Apuestas (inicio del pase):" if self._apuestas_impresas == 0 else "Apuestas adicionales (Fase 2):"
                self._imprimir_apuestas(desde=self._apuestas_impresas, titulo=titulo)
            if self.tiro_n == 1:
                self._imprimir_fase()
            self._w(f"Tiro {self.tiro_n}: {d1} + {d2} = {suma}")

        elif t == "PUNTO_FIJADO":
            self.boton_on = True
            self.punto = int(evento.get("valor", 0))
            self._w(f"El punto es: {self.punto}")
            self._imprimir_fase()

        elif t == "APUESTA_RESUELTA":
            reg = {
                "id_jugador": evento.get("id_jugador"),
                "resultado": str(evento.get("resultado", "")).upper(),
                "pago": float(evento.get("pago", 0)),
                "motivo": evento.get("motivo"),
                "tipo": evento.get("tipo_apuesta"),
            }
            self.pagos_pase.append(reg)

        elif t == "PUNTO_LIBRE":
            self._w("")
            self._imprimir_pagos()
            self._imprimir_resumen_pase()
