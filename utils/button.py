# utils/button.py
import pygame
from utils.paths import FONT_PATH

class Button:
    def __init__(self, text, pos, size, callback, base_color, hover_color):
        self.text = text
        self.pos = pos
        self.size = size
        self.callback = callback
        self.base_color = base_color
        self.hover_color = hover_color
        self.rect = pygame.Rect(pos, size)
        self.font = pygame.font.Font(FONT_PATH, 36)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        is_hovered = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if is_hovered else self.base_color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        text_surface = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()