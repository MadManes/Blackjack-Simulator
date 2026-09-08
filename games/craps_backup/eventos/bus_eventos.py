
# games/craps/eventos/bus_eventos.py
"""Bus de eventos (pub/sub in-process)."""
from typing import Callable, Dict, List, Any


class BusEventos:
    def __init__(self) -> None:
        self._subs: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}


    def suscribir(self, tipo_evento: str, handler: Callable[[Dict[str, Any]], None]) -> str:
        self._subs.setdefault(tipo_evento, []).append(handler)
        return f"{tipo_evento}#{id(handler)}"


    def publicar(self, tipo_evento: str, **payload) -> None:
        for handler in self._subs.get(tipo_evento, []):
            try:
                handler({"tipo": tipo_evento, **payload})
            except Exception:
                pass