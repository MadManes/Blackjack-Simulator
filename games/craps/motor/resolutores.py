"""Resolutores por tipo de apuesta (stubs)."""
from typing import Any, Dict


class ResolutorLinea:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def resolver_fase1(self, suma: int) -> None:
        pass


    def resolver_fase2(self, suma: int, punto: int) -> None:
        pass


class ResolutorCostilla:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def resolver(self, suma: int) -> None:
        pass


class ResolutorCamuninas:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def resolver(self, suma: int, d1: int, d2: int) -> None:
        pass


class ResolutorCuadro:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def resolver(self, suma: int) -> None:
        pass


class ResolutorFieldYProps:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config


    def resolver(self, suma: int) -> None:
        pass