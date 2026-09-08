
# main.py
import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT
from core.global_state import state_manager, CARD_IMAGES, SOUNDS
from core.naipes_graficos import cargar_cartas
from core.sound import load_sounds
from states.menu_principal import MenuPrincipal


pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

CARD_IMAGES.update(cargar_cartas())
load_sounds()
pygame.display.set_caption("Simulador - Casino Central")
clock = pygame.time.Clock()

state_manager.change_state(MenuPrincipal())

running = True
while running:
    dt = clock.tick(60) / 1000
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        state_manager.handle_event(event)       

    state_manager.update(dt)
    state_manager.render(screen)    
    pygame.display.flip()

    if state_manager.should_quit:
        running = False

pygame.quit()
