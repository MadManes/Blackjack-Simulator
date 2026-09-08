"""Registro e índices de apuestas."""
from typing import Dict, List, Optional, Any
import itertools


class Apuesta:
    """Base de apuesta (abstracta por convención)."""
    def __init__(self, id_apuesta: int, id_jugador: int, tipo: str, monto: int, meta: Optional[Dict[str, Any]] = None) -> None:
        self.id_apuesta = id_apuesta
        self.id_jugador = id_jugador
        self.tipo = tipo
        self.monto = int(monto)
        self.working = True
        self.meta = meta or {}


class RegistroApuestas:
    def __init__(self) -> None:
        self._apuestas: Dict[int, Apuesta] = {}
        self._autoid = itertools.count(1)


    def crear(self, id_jugador: int, tipo: str, monto: int, meta: Optional[Dict[str, Any]] = None) -> Apuesta:
        ap = Apuesta(next(self._autoid), id_jugador, tipo, int(monto), meta)
        self._apuestas[ap.id_apuesta] = ap
        return ap


    def por_tipo(self, tipo: str) -> List[Apuesta]:
        return [a for a in self._apuestas.values() if a.tipo == tipo]


    def todas(self) -> List[Apuesta]:
        return list(self._apuestas.values())


    def limpiar(self) -> None:
        self._apuestas.clear()