
# states/menu_principal.py
import pygame
from core.base_state import BaseState
from core.global_state import state_manager
from utils.button import Button
from utils.msg import Msg
from config import SCREEN_WIDTH, SCREEN_HEIGHT, DARK_GREEN, LIGHT_GREEN, WHITE, DARK_RED, RED
from states.menu_estadistico import MenuEstadistico

class MenuPrincipal(BaseState):
    def __init__(self):
        self.buttons = []
        self.messages = []
        self.create_buttons()
        self.create_messages()

    def create_buttons(self):
        self.buttons.append(Button("Modo juego", (500, 250), (280, 60), self.modo_juego, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Modo estadístico", (500, 340), (280, 60), self.modo_estadistico, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Salir", (980, 600), (180, 40), self.salir, DARK_RED, RED))        

    def create_messages(self):
        self.messages.append(Msg("No disponible en esta versión", (500, 250), (280, 60), None, RED))

    def modo_juego(self):
        print("Modo juego seleccionado (a implementar)")

    def modo_estadistico(self):        
        state_manager.push_state(MenuEstadistico())

    def salir(self):
        state_manager.quit()

    def handle_event(self, event):
        for button in self.buttons:            
            button.handle_event(event)

    def update(self, dt): pass

    def render(self, screen):
        screen.fill((30, 30, 30))
        font = pygame.font.Font(None, 126)
        title = font.render("Simulador - Casino Central", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        for button in self.buttons:
            button.draw(screen)

        for msg in self.messages:
            msg.draw(screen)