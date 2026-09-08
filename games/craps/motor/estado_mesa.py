"""Estado inmutable de mesa (snapshot por tiro)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoMesa:
    boton: bool # False=OFF (Fase 1), True=ON (Fase 2)
    punto: int # 0 si no hay punto
    tirador_id: int
    contador_tiros: int