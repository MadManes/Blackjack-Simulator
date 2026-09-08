# states/menu_blackjack.py
import pygame
from core.base_state import BaseState
from core.global_state import state_manager
from utils.button import Button
from utils.msg import Msg
from config import SCREEN_WIDTH, DARK_GREEN, LIGHT_GREEN, WHITE, RED, DARK_RED
from games.central_poker.states.simulador_estadistico import SimuladorEstadistico

class MenuCentralPoker(BaseState):
    def __init__(self):
        self.buttons = []
        self.messages = []
        self.create_buttons()
        self.create_messages()

    def create_messages(self):
        self.messages.append(Msg("No disponible en esta version", (500, 250), (280, 60), None, RED))
        self.messages.append(Msg("No disponible en esta version", (500, 350), (280, 60), None, RED))

    def create_buttons(self):
        self.buttons.append(Button("Simulador", (500, 250), (280, 60), self.simulador, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Estadística", (500, 350), (280, 60), self.estadistica, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Volver", (120, 640), (180, 40), self.volver, DARK_RED, RED))

    def simulador(self):        
        # ACTIVAR CUANDO TENGA EL CODIGO DE LA SIMULACION GRAFICA
        #state_manager.change_state(SimuladorEstadistico())
        pass

    def estadistica(self):
        print("Ejecutando 2.000.000 de manos...")  # Esto después lo conectamos con la lógica real

    def volver(self):
        pass
    
    def handle_event(self, event):
        for button in self.buttons:            
            button.handle_event(event)

    def update(self, dt): pass

    def render(self, screen):
        screen.fill((0, 0, 30))
        font = pygame.font.Font(None, 114)
        title = font.render("C e n t r a l    P o k e r", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        for button in self.buttons:
            button.draw(screen)

        for msg in self.messages:
            msg.draw(screen)