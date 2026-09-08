'''## CODIGO QUE YA NO ME SIRVE

# states/blackjack_simulado.py
import pygame
from core.base_state import BaseState
from config import WHITE, SCREEN_WIDTH

class BlackjackSimulado(BaseState):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from core.global_state import state_manager
            from states.menu_blackjack import MenuBlackjack
            state_manager.change_state(MenuBlackjack())

    def update(self, dt): pass

    def render(self, screen):
        screen.fill((10, 40, 10))
        font = pygame.font.Font(None, 64)
        text = font.render("Modo Simulador - Blackjack", True, WHITE)
        screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 300))
        '''