"""Simulador gráfico (pygame) — esqueleto de estado UI y hooks de eventos."""
# Nota: no importes pygame aún si no lo necesitás. Dejá los métodos vacíos.
from typing import Any


class SimuladorGraficoCraps:
    def __init__(self, motor) -> None:
        self.motor = motor
        #self.font = ... (dejar para integrar despues)


    def handle_evento_motor(self, evento: dict) -> None:
        pass


    def update(self, dt: float) -> None:
        pass


    def render(self, surface: Any) -> None:
        pass