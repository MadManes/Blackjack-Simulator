"""Servicio de azar: dados d6 con semilla."""
from typing import Optional, Tuple
import random


class ServicioAzar:
    def __init__(self, semilla: Optional[int] = None) -> None:
        self.rng = random.Random(semilla)


    def d6(self) -> int:
        return self.rng.randint(1, 6)


    def tirar_dos_dados(self) -> Tuple[int, int]:
        return self.d6(), self.d6()