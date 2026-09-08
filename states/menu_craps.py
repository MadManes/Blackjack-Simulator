# states/menu_blackjack.py
import pygame
from core.base_state import BaseState
from core.global_state import state_manager
from utils.button import Button
from utils.msg import Msg
from config import SCREEN_WIDTH, DARK_GREEN, LIGHT_GREEN, WHITE, RED, DARK_RED

# Hacer bien la importacion
from games.craps.simuladores.simulador_grafico_craps import SimuladorGraficoCraps
from games.craps.states.craps_setup import CrapsSetup

class MenuCraps(BaseState):
    def __init__(self):
        self.buttons = []        
        self.create_buttons()                  

    def create_buttons(self):
        self.buttons.append(Button("Simulador", (500, 250), (280, 60), self.simulador, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Estadística", (500, 350), (280, 60), self.estadistica, DARK_GREEN, LIGHT_GREEN))
        self.buttons.append(Button("Volver", (120, 600), (180, 40), self.volver, DARK_RED, RED))

    def simulador(self):
        state_manager.push_state(SimuladorGraficoCraps())        

    def estadistica(self):
        state_manager.push_state(CrapsSetup())

    def volver(self):
        state_manager.pop_state()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt): pass

    def render(self, screen):
        screen.fill((0, 0, 30))
        font = pygame.font.Font(None, 114)
        title = font.render("C r a p s", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        for button in self.buttons:
            button.draw(screen)        
        