
# games/blackjack/traditional/states/tbj_setup.py
import pygame
from core.base_state import BaseState
from core.global_state import state_manager
from utils.button import Button
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    DARK_GREEN, LIGHT_GREEN, WHITE, RED, DARK_RED,
    GRAY, LIGHT_GRAY, DARK_GRAY, BLACK
)
from games.blackjack.traditional.states.simulador_estadistico_masivo import SimuladorEstadisticoMasivo
# Estrategias soportadas en el clásico
ESTRATEGIAS = ["nunca_se_pasa", "arriesgado_1", "arriesgado_2", "arriesgado_3"]

class Toggle:
    def __init__(self, rect, value=True, label_on="Sí", label_off="No"):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.label_on = label_on
        self.label_off = label_off
        self.hover = False
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
    def draw(self, surface, font):
        pygame.draw.rect(surface, DARK_GRAY if self.hover else BLACK, self.rect, border_radius=8)
        knob_w = self.rect.height - 6
        knob_x = self.rect.x + 3 if not self.value else self.rect.right - 3 - knob_w
        pygame.draw.rect(surface, GRAY, (knob_x, self.rect.y + 3, knob_w, knob_w), border_radius=6)
        txt = self.label_on if self.value else self.label_off
        lbl = font.render(txt, True, GRAY)
        surface.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y - lbl.get_height() - 2))

class Stepper:
    def __init__(self, center, value, min_v, max_v, step=1, width=140, height=32, fmt=str):
        self.value = value
        self.min = min_v
        self.max = max_v
        self.step = step
        self.fmt = fmt
        self.rect = pygame.Rect(0, 0, width, height); 
        self.rect.center = center
        bw = height
        self.minus_rect = pygame.Rect(self.rect.x, self.rect.y, bw, height)
        self.plus_rect  = pygame.Rect(self.rect.right - bw, self.rect.y, bw, height)
        self.value_rect = pygame.Rect(self.rect.x + bw, self.rect.y, self.rect.width - 2*bw, height)
        self.hL = self.hR = False

    def _apply_step(self, sign, shift):
        mult = 10 if shift else 1
        new_val = self.value + sign * self.step * mult
        new_val = max(self.min, min(self.max, new_val))
        self.value = new_val

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover_minus = self.minus_rect.collidepoint(event.pos)
            self.hover_plus  = self.plus_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
            if self.minus_rect.collidepoint(event.pos):
                self._apply_step(-1, shift)
            elif self.plus_rect.collidepoint(event.pos):
                self._apply_step(+1, shift)

    def draw(self, surface, font):
        pygame.draw.rect(surface, GRAY, self.rect, border_radius=0)
        # -
        pygame.draw.rect(surface, DARK_RED if self.hL else RED, self.minus_rect, border_radius=0)
        m = font.render("-", True, WHITE); surface.blit(m, (self.minus_rect.centerx - m.get_width()//2, self.minus_rect.centery - m.get_height()//2))
        # +
        pygame.draw.rect(surface, DARK_GREEN if self.hR else LIGHT_GREEN, self.plus_rect, border_radius=0)
        p = font.render("+", True, WHITE); surface.blit(p, (self.plus_rect.centerx - p.get_width()//2, self.plus_rect.centery - p.get_height()//2))
        # val
        s = self.fmt(self.value); s = s if isinstance(s, str) else str(s)
        vs = font.render(s, True, BLACK)
        pygame.draw.rect(surface, GRAY, self.value_rect, border_radius=0)
        surface.blit(vs, (self.value_rect.centerx - vs.get_width()//2, self.value_rect.centery - vs.get_height()//2))

class Choice:
    def __init__(self, center, options, index=0, width=210, height=32):
        self.options = options[:]; self.index = index
        self.rect = pygame.Rect(0,0,width,height); self.rect.center = center
        bw = height
        self.left_rect  = pygame.Rect(self.rect.x, self.rect.y, bw, height)
        self.right_rect = pygame.Rect(self.rect.right - bw, self.rect.y, bw, height)
        self.value_rect = pygame.Rect(self.rect.x + bw, self.rect.y, self.rect.width - 2*bw, height)
        self.hL = self.hR = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hL = self.left_rect.collidepoint(event.pos); self.hR = self.right_rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.left_rect.collidepoint(event.pos): self.index = (self.index - 1) % len(self.options)
            elif self.right_rect.collidepoint(event.pos): self.index = (self.index + 1) % len(self.options)

    @property
    def value(self): return self.options[self.index]

    def draw(self, surface, font):
        pygame.draw.rect(surface, GRAY, self.rect, border_radius=0)
        pygame.draw.rect(surface, DARK_GRAY if self.hL else BLACK, self.left_rect, border_radius=0)
        l = font.render("<", True, WHITE); surface.blit(l, (self.left_rect.centerx - l.get_width()//2, self.left_rect.centery - l.get_height()//2))
        pygame.draw.rect(surface, DARK_GRAY if self.hR else BLACK, self.right_rect, border_radius=0)
        r = font.render(">", True, WHITE); surface.blit(r, (self.right_rect.centerx - r.get_width()//2, self.right_rect.centery - r.get_height()//2))
        v = font.render(str(self.value), True, BLACK)
        pygame.draw.rect(surface, GRAY, self.value_rect, border_radius=0)
        surface.blit(v, (self.value_rect.centerx - v.get_width()//2, self.value_rect.centery - v.get_height()//2))

class TBJSetup(BaseState):
    def __init__(self):
        # Fuentes (compactas)
        self.title_font = pygame.font.Font(None, 46)
        self.label_font = pygame.font.Font(None, 24)
        self.row_font   = pygame.font.Font(None, 22)

        # Steppers globales (compactar y ubicar arriba)
        # Asumo una pantalla 1280x720 aprox; si es otra, la layout se mantiene proporcional.
        top_y = 15
        col_gap = 320
        center_x_left  = SCREEN_WIDTH//2 - col_gap
        center_x_right = SCREEN_WIDTH//2 + col_gap

        self.hands_stepper = Stepper(
            center=(center_x_left + 90, top_y),
            value=500000, min_v=1, max_v=1_000_000, step=1000,
            width=120, height=24, fmt=lambda v: f"{v:,}".replace(",", ".")
        )
        self.players_stepper = Stepper(
            center=(center_x_right + 24, top_y),
            value=7, min_v=1, max_v=7, step=1,
            width=120, height=24, fmt=int
        )

        # UI dinámica por jugador
        self.player_rows = []
        self._ensure_player_rows(self.players_stepper.value)

        # Botones
        self.buttons = []
        self.create_buttons()

    def create_buttons(self):
        # Compactar y ubicar abajo sin tapar filas
        self.btn_aceptar = Button("Aceptar", (SCREEN_WIDTH - 220, SCREEN_HEIGHT - 56), (170, 44),
                                  self.aceptar, DARK_GREEN, LIGHT_GREEN)
        self.btn_volver = Button("Volver", (50, SCREEN_HEIGHT - 56), (170, 44),
                                 self.volver, DARK_RED, RED)
        self.buttons = [self.btn_aceptar, self.btn_volver]

    # ----- Estructura por jugador -----
    def _make_player_row(self, idx, y):
        """
        Layout compacto de columnas (entra todo sin scroll):
        Cols X aprox: 70 (N°), 160 (Apuesta), 390 (Estrategia), 620 (Duplica), 720 (Aperturas), 820 (Seguro)
        Ajusté tamaños para que quepa en ~1280 px y también en resoluciones similares.
        """
        apuesta = Stepper(center=(256, y), value=3000, min_v=3000, max_v=60000, step=500,
                          width=170, height=32, fmt=lambda v: f"${v:,}".replace(",", "."))
        estrategia = Choice(center=(518, y), options=ESTRATEGIAS, index=0, width=210, height=32)
        toggle_dup = Toggle(rect=(705, y-16, 60, 28), value=True)
        toggle_ap  = Toggle(rect=(855, y-16, 60, 28), value=True)
        toggle_seg = Toggle(rect=(1005, y-16, 60, 28), value=False)
        return {
            "idx": idx,
            "y": y,
            "apuesta": apuesta,
            "estrategia": estrategia,
            "duplica": toggle_dup,
            "aperturas": toggle_ap,
            "seguro": toggle_seg,
        }

    def _ensure_player_rows(self, n):
        self.player_rows = []
        # Calcular altura disponible entre el header y los botones
        header_bottom = 180
        footer_top = SCREEN_HEIGHT - 80
        available = footer_top - header_bottom
        # Con 7 jugadores, un gap de ~ (available / 7). Para 1..7 queda proporcionado.
        n = max(1, min(7, n))
        gap = max(48, int(available / max(1, n + 0.2)))  # un pelín de margen
        start_y = header_bottom + gap // 2
        for i in range(n):
            self.player_rows.append(self._make_player_row(i, start_y + i*gap))

    # ----- Navegación -----
    def volver(self):
        state_manager.pop_state()

    def aceptar(self):
        cfg = self.get_config()
        from games.blackjack.traditional.motor_probado import BLACKJACK_STRATEGIES
        estrats = []
        for p in cfg["players"]:
            base = BLACKJACK_STRATEGIES.get(p["estrategia"], {"tipo": p["estrategia"]})
            estrats.append({
                **base,
                "duplica": p["duplica"],
                "apertura_pares": p["aperturas"],   # respeta toggle
                "apertura_ases": True,              # SIEMPRE ON
                "seguro": p["seguro"],
            })
        state_manager.push_state(SimuladorEstadisticoMasivo(cfg))

    def get_config(self):
        n = int(self.players_stepper.value)
        players = []
        for i in range(n):
            row = self.player_rows[i]
            players.append({
                "jugador": i+1,
                "apuesta": int(row["apuesta"].value),
                "estrategia": row["estrategia"].value,
                "duplica": row["duplica"].value,
                "aperturas": row["aperturas"].value,
                "seguro": row["seguro"].value,
            })
        return {
            "manos": int(self.hands_stepper.value),
            "jugadores": n,
            "players": players
        }

    # ----- Eventos / Update / Render -----
    def handle_event(self, event):
        # Controles globales
        self.hands_stepper.handle_event(event)
        prev_players = self.players_stepper.value
        self.players_stepper.handle_event(event)
        if self.players_stepper.value != prev_players:
            self._ensure_player_rows(self.players_stepper.value)

        # Controles por jugador
        for row in self.player_rows[:self.players_stepper.value]:
            row["apuesta"].handle_event(event)
            row["estrategia"].handle_event(event)
            row["duplica"].handle_event(event)
            row["aperturas"].handle_event(event)
            row["seguro"].handle_event(event)

        # Botones
        for b in self.buttons:
            b.handle_event(event)

    def update(self, dt):
        pass

    def render(self, screen):
        screen.fill((8, 12, 22))

        # Título
        title = self.title_font.render("Configuración — Blackjack CLÁSICO", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 36))

        # Labels globales (compactos y alineados a los steppers)
        left_label = self.label_font.render("Cantidad de manos (Shift = x10):", True, WHITE)
        right_label = self.label_font.render("Jugadores:", True, WHITE)

        # Coordenadas de los steppers definidas en __init__
        top_y = 96
        col_gap = 340
        center_x_left  = SCREEN_WIDTH//2 - col_gap
        center_x_right = SCREEN_WIDTH//2 + col_gap

        screen.blit(left_label, (105, top_y))
        self.hands_stepper.rect.center = (center_x_left + 165, top_y + 7)
        self.hands_stepper.minus_rect.topleft = (self.hands_stepper.rect.left, self.hands_stepper.rect.top)
        self.hands_stepper.plus_rect.topleft  = (self.hands_stepper.rect.right - self.hands_stepper.rect.height, self.hands_stepper.rect.top)
        self.hands_stepper.value_rect.topleft = (self.hands_stepper.minus_rect.right, self.hands_stepper.rect.top)
        self.hands_stepper.draw(screen, self.row_font)

        screen.blit(right_label, (725, top_y))
        self.players_stepper.rect.center = (center_x_right - 64, top_y + 7)
        self.players_stepper.minus_rect.topleft = (self.players_stepper.rect.left, self.players_stepper.rect.top)
        self.players_stepper.plus_rect.topleft  = (self.players_stepper.rect.right - self.players_stepper.rect.height, self.players_stepper.rect.top)
        self.players_stepper.value_rect.topleft = (self.players_stepper.minus_rect.right, self.players_stepper.rect.top)
        self.players_stepper.draw(screen, self.row_font)

        # Cabecera de columnas (compacta)
        headers = [
            ("Jugador", 65),
            ("Apuesta", 220),
            ("Estrategia", 480),
            ("Duplica", 706),
            ("Aperturas", 846),
            ("Seguro", 1005),
        ]
        y_head = 166
        for text, x in headers:
            lbl = self.label_font.render(text, True, LIGHT_GRAY)
            screen.blit(lbl, (x, y_head - 20))

        # Dibujar filas (todas visibles, sin scroll)
        for row in self.player_rows[:self.players_stepper.value]:
            y = row["y"]
            # número de jugador
            jlbl = self.row_font.render(f"{row['idx']+1}", True, WHITE)
            screen.blit(jlbl, (headers[0][1] + 20, y - jlbl.get_height()//2))

            # controles
            # Apuesta
            row["apuesta"].rect.centery = y
            row["apuesta"].minus_rect.y = row["apuesta"].rect.y
            row["apuesta"].plus_rect.y  = row["apuesta"].rect.y
            row["apuesta"].value_rect.y = row["apuesta"].rect.y
            row["apuesta"].draw(screen, self.row_font)

            # Estrategia
            row["estrategia"].rect.centery = y
            row["estrategia"].left_rect.y  = row["estrategia"].rect.y
            row["estrategia"].right_rect.y = row["estrategia"].rect.y
            row["estrategia"].value_rect.y = row["estrategia"].rect.y
            row["estrategia"].draw(screen, self.row_font)

            # Toggles (alineados a columnas)
            row["duplica"].rect.centery   = y
            row["aperturas"].rect.centery = y
            row["seguro"].rect.centery    = y
            row["duplica"].draw(screen, self.row_font)
            row["aperturas"].draw(screen, self.row_font)
            row["seguro"].draw(screen, self.row_font)

        # Botones
        for b in self.buttons:
            b.draw(screen)
