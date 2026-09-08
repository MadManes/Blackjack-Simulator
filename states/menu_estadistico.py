# states/menu_estadistico.py
import pygame
from core.base_state import BaseState
from core.global_state import state_manager

from utils.button import Button
from utils.msg import Msg

from config import SCREEN_WIDTH, WHITE, DARK_GREEN, LIGHT_GREEN, DARK_RED, RED

from states.menu_blackjack import MenuBlackjack
from states.menu_blackjack_nuevo import MenuBlackjackNuevo
from states.menu_craps import MenuCraps
from states.menu_central_poker import MenuCentralPoker
from states.menu_tripoker import MenuTripoker
from states.menu_punto_y_banca import MenuPuntoBanca
from states.menu_baccarat import MenuBaccarat
from states.menu_ruleta import MenuRuleta

class MenuEstadistico(BaseState):
    def __init__(self):
        self.buttons = []
        self.messages = []
        self.create_buttons_and_messages()        

    def create_buttons_and_messages(self):
        juegos = [
            ("Blackjack clásico", self.blackjack_tradicional, True),
            ("Blackjack nuevo", self.blackjack_nuevo, True),
            ("Craps", self.craps, True),
            ("Central Poker", self.central_poker, False),
            ("Tri Poker", self.tripoker, False),
            ("Punto y banca", self.punto_y_banca, False),
            ("Baccarat", self.baccarat, False),
            ("Ruleta", self.ruleta, False),
        ]
        for i, (nombre, callback, available) in enumerate(juegos):            
            if not available:
                self.buttons.append(Button(nombre, (450, 95 + i * 70), (380, 50), callback, DARK_RED, RED))
                self.messages.append(Msg("No disponible en esta versión", (450, 95 + i * 70), (380, 50), None, RED))                
            else:
                self.buttons.append(Button(nombre, (450, 95 + i * 70), (380, 50), callback, DARK_GREEN, LIGHT_GREEN))

        self.buttons.append(Button("Volver", (120, 600), (180, 40), self.volver, DARK_RED, RED))

    def blackjack_tradicional(self):        
        state_manager.push_state(MenuBlackjack())

    def blackjack_nuevo(self):
        state_manager.push_state(MenuBlackjackNuevo())

    def craps(self):        
        state_manager.push_state(MenuCraps())
    
    def central_poker(self):
        pass
        #state_manager.change_state(MenuCentralPoker())

    def tripoker(self):
        pass
        #state_manager.change_state(MenuTripoker())

    def punto_y_banca(self):
        pass
        #state_manager.change_state(MenuPuntoBanca())

    def baccarat(self):
        pass
        #state_manager.change_state(MenuBaccarat())

    def ruleta(self):
        pass
        #state_manager.change_state(MenuRuleta())
    
    def volver(self):
        state_manager.pop_state()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt): pass

    def render(self, screen):
        screen.fill((20, 20, 20))
        font = pygame.font.Font(None, 64)
        title = font.render("Menú Modo Estadístico", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 40))

        for button in self.buttons:
            button.draw(screen)

        for msg in self.messages:            
            msg.draw(screen)