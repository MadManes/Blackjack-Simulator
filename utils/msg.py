# utils/button.py
import pygame
from utils.paths import FONT_PATH

class Msg:
    def __init__(self, text, pos, size, callback, color):
        self.text = text
        self.pos = pos
        self.size = size
        self.callback = callback        
        self.color = color
        self.rect = pygame.Rect(pos, size)
        self.font = pygame.font.Font(FONT_PATH, 20)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)
        if is_hovered:
            pygame.draw.rect(screen, self.color, self.rect, border_radius=10)
            text_surface = self.font.render(self.text, True, (200, 200, 200))
            text_rect = text_surface.get_rect(center=self.rect.center)
            screen.blit(text_surface, text_rect)

    