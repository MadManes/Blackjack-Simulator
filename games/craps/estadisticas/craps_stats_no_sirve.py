"""Contadores base (stubs) — análogo a blackjack_stats."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class EstadisticasCraps:
    total_pases: int = 0
    tiros_por_pase: List[int] = field(default_factory=list)
    ganancias_casino: float = 0.0
    dinero_en_juego: float = 0.0
    dinero_en_juego_pase_actual: float = 0.0
    linea_buena_ganadas: int = 0
    linea_mala_ganadas: int = 0
    linea_empates: int = 0


    def registrar_apuesta(self, monto: int) -> None:
        pass


    def registrar_evento(self, nombre: str) -> None:
        pass


    def guardar_progreso(self) -> None:
        pass