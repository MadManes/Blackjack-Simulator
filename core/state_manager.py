# core/state_manager.py

class StateManager:
    def __init__(self):
        self.stack = []          # pila de estados
        self.should_quit = False # flag para salir del bucle principal

    # Mantén compatibilidad: reemplaza toda la pila por un único estado
    def change_state(self, new_state):
        self.stack = [new_state]

    # Navegar hacia dentro (abre una nueva pantalla encima de la actual)
    def push_state(self, new_state):
        self.stack.append(new_state)

    # Volver (cierra la pantalla actual y vuelve a la anterior)
    def pop_state(self):
        if self.stack:
            self.stack.pop()
        # Si no queda ningún estado, salimos del programa
        if not self.stack:
            self.should_quit = True

    # Estado actual (top de la pila)
    def _current(self):
        return self.stack[-1] if self.stack else None

    # Señal para salir desde un botón (Salir en menú principal)
    def quit(self):
        self.should_quit = True

    def handle_event(self, event):
        st = self._current()
        if st:
            st.handle_event(event)

    def update(self, dt):
        st = self._current()
        if st:
            st.update(dt)

    def render(self, screen):
        st = self._current()
        if st:
            st.render(screen)
