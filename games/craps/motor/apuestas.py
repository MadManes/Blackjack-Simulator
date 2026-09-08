
## ESTE CODIGO SE ESTA USANDO?? 
#games/craps/motor/apuestas.py

"""Jerarquía de Apuestas — stubs por tipo."""
from typing import Optional, Dict, Any
from games.craps.motor.registro_apuestas import Apuesta


class ApuestaLinea(Apuesta):
    """Línea: Buena/Mala (Enganches se agregarán luego)."""
    def __init__(self, id_apuesta: int, id_jugador: int, tipo: str, monto: int, meta: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(id_apuesta, id_jugador, tipo, monto, meta)


class ApuestaCostilla(Apuesta):
    def __init__(self, id_apuesta: int, id_jugador: int, numero: int, monto: int, meta: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(id_apuesta, id_jugador, "Costilla", monto, meta)
        self.numero = int(numero)


class ApuestaCamunina(Apuesta):
    def __init__(self, id_apuesta: int, id_jugador: int, duro: int, monto: int, meta: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(id_apuesta, id_jugador, "Camunina", monto, meta)
        self.duro = int(duro) # 2,3,4,5


class ApuestaCuadro(Apuesta):
    def __init__(self, id_apuesta: int, id_jugador: int, modo: str, monto: int, meta: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(id_apuesta, id_jugador, "Cuadro", monto, meta)
        self.modo = modo # "individual" | "conjunto"


class ApuestaField(Apuesta):
    pass


class ApuestaAnySeven(Apuesta):
    pass


class ApuestaAnyCraps(Apuesta):
    pass


class ApuestaCome(Apuesta):
    pass


class ApuestaDontCome(Apuesta):
    pass

class ApuestaCostillaMala(Apuesta):
    pass