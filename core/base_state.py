# core/base_state.py
class BaseState:
    def handle_event(self, event): pass
    def update(self, dt): pass
    def render(self, screen): pass