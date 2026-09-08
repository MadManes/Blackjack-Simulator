"""Calculadora de pagos (usa config y redondeo)."""
from typing import Any, Dict
from games.craps.utils.redondeo import redondear_500


class CalculadoraPagos:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def pago_linea(self, monto: int, tipo: str) -> int:
        ratio = self.config.get("pagos", {}).get("linea", {}).get(tipo.lower(), 1.0)
        bruto = int(monto * ratio)
        return redondear_500(bruto)