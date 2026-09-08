from typing import Dict, Any
from games.craps.utils.logs import get_debug_logger, j

class SuscriptorEventosDebug:
    """Suscriptor que escucha el BusEventos y vuelca eventos a NDJSON.
    No toca el motor. Se puede enchufar/retirar cuando quieras.
    """
    def __init__(self, extra_context: Dict[str, Any] | None = None):
        self.log = get_debug_logger()
        self.ctx = {"session_id": "S1", "pase_id": 0, "tiro": 0, **(extra_context or {})}


    def __call__(self, evento: Dict[str, Any]):
        t = evento.get("tipo", "EVENTO")
        # Contexto derivado simple
        if t == "TIRO_INICIADO":
            self.ctx["tiro"] += 1
        elif t == "PUNTO_LIBRE":
            self.ctx["pase_id"] += 1
            self.ctx["tiro"] = 0
        # Armar payload y emitir una línea JSON
        payload = {"tipo": t, **{k: v for k, v in evento.items() if k != "tipo"}, **self.ctx}
        self.log.debug(j(payload))