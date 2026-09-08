# games/craps/eventos/bus_eventos.py
class BridgeEventosCraps:
    """
    Event bus simple:
    - Suscriptores por tipo de evento
    - Publicación de eventos con kwargs
    - Notifica a Estadísticas y a Observadores externos (UI)
    """

    def __init__(self, stats=None):
        self.stats = stats
        self._suscriptores = {}     # { "TIPO_EVENTO": [handlers] }
        self._observadores = []     # funciones externas (UI)

    # ------------ API PARA MOTOR (UI / STATS) ------------
    def registrar_observador(self, fn):
        """Observadores externos (UI del simulador gráfico)."""
        self._observadores.append(fn)

    def notificar_observadores(self, evento):
        for fn in list(self._observadores):
            try:
                fn(evento)
            except Exception:
                # Observadores no deben romper el bus
                pass

    # ------------ API PÚBLICA PARA EL MOTOR ------------
    def suscribir(self, tipo_evento, handler):
        """Suscribe un handler a un tipo de evento."""
        self._suscriptores.setdefault(tipo_evento, []).append(handler)

    def publicar(self, tipo_evento, **kwargs):
        """Dispara el evento hacia stats, handlers y observadores."""
        evento = {"tipo": tipo_evento, **kwargs}

        # 1) Notificar STAT engine (si está)
        try:
            if self.stats:
                self.stats.on_evento(evento)
        except Exception:
            # No queremos que fallos en stats corten la simulación
            pass

        # 2) Notificar handlers del tipo de evento
        for handler in list(self._suscriptores.get(tipo_evento, [])):
            try:
                handler(evento)
            except Exception:
                pass

        # 3) Notificar Observadores (UI gráfico)
        try:
            self.notificar_observadores(evento)
        except Exception:
            pass
