"""Banca y saldos de jugadores."""
from typing import Dict


class Banca:
    def __init__(self) -> None:
        self._saldos: Dict[int, int] = {}


    def debitar(self, id_jugador: int, monto: int) -> None:
        self._saldos[id_jugador] = self._saldos.get(id_jugador, 0) - int(monto)


    def acreditar(self, id_jugador: int, monto: int) -> None:
        self._saldos[id_jugador] = self._saldos.get(id_jugador, 0) + int(monto)


    def saldo(self, id_jugador: int) -> int:
        return self._saldos.get(id_jugador, 0)