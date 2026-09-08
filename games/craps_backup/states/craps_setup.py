
# craps/states/craps_setup.py
# -*- coding: utf-8 -*-
import pygame
from core.base_state import BaseState
from core.global_state import state_manager
from utils.button import Button
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    DARK_GREEN, LIGHT_GREEN, WHITE, RED, DARK_RED,
    GRAY, LIGHT_GRAY, DARK_GRAY, BLACK
)

# ============== Widgets compactos ==============
class Toggle:
    def __init__(self, rect, value=True):
        self.rect = pygame.Rect(rect); self.value = bool(value)
        self.active_color = RED 
        self.hover = False
    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.rect.collidepoint(e.pos): self.value = not self.value
    def draw(self, s, font):
        if self.value: self.active_color = DARK_GREEN 
        else: self.active_color = RED
        pygame.draw.rect(s, DARK_GRAY if self.hover else self.active_color, self.rect, border_radius=8)
        k = self.rect.height - 6
        kx = self.rect.x + 3 if not self.value else self.rect.right - 3 - k
        pygame.draw.rect(s, GRAY, (kx, self.rect.y + 3, k, k), border_radius=6)
        
        #txt = self.label_on if self.value else self.label_off
        #lbl = font.render(txt, True, GRAY)
        #s.blit(lbl, (self.rect.centerx - lbl.get_width() // 2, self.rect.y - lbl.get_height() - 2))

class Choice:
    def __init__(self, rect, options, index=0):
        self.rect = pygame.Rect(rect); self.options = options[:]; self.index = index
        h = self.rect.height
        self.left_rect  = pygame.Rect(self.rect.x, self.rect.y, h, h)
        self.right_rect = pygame.Rect(self.rect.right - h, self.rect.y, h, h)
        self.value_rect = pygame.Rect(self.rect.x + h, self.rect.y, self.rect.width - 2*h, h)
        self.hL = self.hR = False
    @property
    def value(self): return self.options[self.index]
    def handle_event(self, e):
        if e.type == pygame.MOUSEMOTION:
            self.hL = self.left_rect.collidepoint(e.pos); self.hR = self.right_rect.collidepoint(e.pos)
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.left_rect.collidepoint(e.pos):  self.index = (self.index - 1) % len(self.options)
            elif self.right_rect.collidepoint(e.pos): self.index = (self.index + 1) % len(self.options)
    def draw(self, s, font):
        pygame.draw.rect(s, GRAY, self.rect, border_radius=0)
        pygame.draw.rect(s, DARK_GRAY if self.hL else BLACK, self.left_rect, border_radius=0)
        l = font.render("<", True, WHITE); s.blit(l, (self.left_rect.centerx - l.get_width()//2, self.left_rect.centery - l.get_height()//2))
        pygame.draw.rect(s, DARK_GRAY if self.hR else BLACK, self.right_rect, border_radius=0)
        r = font.render(">", True, WHITE); s.blit(r, (self.right_rect.centerx - r.get_width()//2, self.right_rect.centery - r.get_height()//2))
        v = font.render(str(self.value), True, BLACK)
        pygame.draw.rect(s, GRAY, self.value_rect, border_radius=0)
        s.blit(v, (self.value_rect.centerx - v.get_width()//2, self.value_rect.centery - v.get_height()//2))

# ============== Opciones ==============
APUESTA_NIVELES = ["mín", "bajo", "med", "alto", "máx"]
LINEA_OPC = ["Buena", "Mala", "No"]

COSTILLA_BUENA_OPC = [
    "No", "4/10", "5/9", "6/8",
    "Afuera", "Adentro", "4/5/6", "8/9/10", "Todo"
]
COSTILLA_BUENA_DUR = ["100%", "80%", "50%", "20%", "Una"]
COSTILLA_MALA_OPC  = ["No", "4/10", "5/9", "6/8", "Todo"]

CUADRO_OPC  = ["No", "Todos", "2/3", "2/12", "3/11", "11/12", "11", "2/3/12"]
FREQ_STD    = ["100%", "80%", "50%", "20%"]
FREQ_SALIDA = ["Nunca", "100%", "80%", "50%", "20%"]  # Any7/AnyC (come-out)
CAMU_OBJ    = ["No", "punto", "33/44", "22/55", "33/22", "44/55", "Todas"]
COME_CANT   = ["1", "2", "3", "4", "Todos"]

# ============== (jugadores en columnas) ==============
class CrapsSetup(BaseState):
    def __init__(self):
        # Fuentes
        self.title_font = pygame.font.Font(None, 46)
        self.label_font = pygame.font.Font(None, 22)
        self.row_font   = pygame.font.Font(None, 20)

        # Globals arriba
        self.pases = self._make_stepper_like(center=(SCREEN_WIDTH//2 - 140, 80), val=20_000)
        self.players = self._make_stepper_players(center=(SCREEN_WIDTH//2 + 220, 80), val=2)

        # Definición de filas (etiqueta + tipo de control + opciones)
        # Cada celda se genera por jugador
        self.rows_def = [
            ("Apuesta",      "choice", APUESTA_NIVELES),
            ("Línea",        "choice", LINEA_OPC),
            ("Enganche",     "toggle", None),
            ("Costilla B",   "choice", COSTILLA_BUENA_OPC),
            ("Duración B",   "choice", COSTILLA_BUENA_DUR),
            ("También Punto B", "toggle", None),
            ("Costilla M",   "choice", COSTILLA_MALA_OPC),
            ("Cuadro",       "choice", CUADRO_OPC),
            ("Freq Cuadro",  "choice", ["Siempre", "Salida", "80%", "50%", "20%"]),
            ("Any Seven",    "choice", FREQ_SALIDA),
            ("Any Craps",    "choice", FREQ_SALIDA),
            ("Camuninas",    "choice", CAMU_OBJ),
            ("Freq Camu",    "choice", FREQ_STD),
            ("Field",        "toggle", None),
            ("Freq Field",   "choice", ["100%", "80%", "50%", "20%"]),
            ("Come/Don't",   "toggle", None),
            ("Freq Come",    "choice", FREQ_STD),
            ("Cant. Come",   "choice", COME_CANT),
            ("Eng. Come",    "toggle", None),
        ]

        # Grid de celdas: dict[row_idx][jug_idx] -> widget
        self.grid = []
        self._rebuild_grid(int(self.players["val"]))

        # Botones
        self.btn_aceptar = Button("Aceptar", (SCREEN_WIDTH - 220, 56), (170, 44),
                                  self.aceptar, DARK_GREEN, LIGHT_GREEN)
        self.btn_volver  = Button("Volver", (50, 56), (170, 44),
                                  self.volver, DARK_RED, RED)
        self.buttons = [self.btn_aceptar, self.btn_volver]

    # ---------- helpers steppers compactos ----------
    def _make_stepper_like(self, center, val):
        # “Stepper” simple visual (– / + controlado por clicks) para pases
        w, h = 160, 24
        rect = pygame.Rect(0,0,w,h); rect.center = center
        return {"rect": rect, "val": val, "min": 1, "max": 2_000_000, "step": 1_000}
    def _make_stepper_players(self, center, val):
        w, h = 120, 24
        rect = pygame.Rect(0,0,w,h); rect.center = center
        return {"rect": rect, "val": val, "min": 1, "max": 12, "step": 1}

    # ---------- grid ----------
    def _col_xs(self, n_cols):
        left = 180      # margen para etiquetas de fila
        right = SCREEN_WIDTH - 40
        col_w = max(100, (right - left) // max(1, n_cols))
        xs = [left + i*col_w + col_w//2 for i in range(n_cols)]
        return xs, col_w

    def _rebuild_grid(self, n_players: int):
        self.grid = []
        xs, col_w = self._col_xs(n_players)
        y0 = 140; row_h = 28
        for r, (label, kind, opts) in enumerate(self.rows_def):
            y = y0 + r*row_h
            row_widgets = []
            for j in range(n_players):
                if kind == "toggle":
                    w = Toggle(rect=(xs[j]-28, y-12, 56, 24), value=False)
                else:  # choice
                    w = Choice(rect=pygame.Rect(xs[j]-col_w//2, y-12, col_w-8, 24), options=opts, index=0)
                row_widgets.append(w)
            self.grid.append(row_widgets)

    # ---------- navegación ----------
    def volver(self): state_manager.pop_state()

    # ---------- eventos ----------
    def handle_event(self, e):
        # pases
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            rect = self.pases["rect"]; h = rect.height
            minus = pygame.Rect(rect.left, rect.top, h, h)
            plus  = pygame.Rect(rect.right - h, rect.top, h, h)
            if minus.collidepoint(e.pos):
                self.pases["val"] = max(self.pases["min"], self.pases["val"] - self.pases["step"])
            elif plus.collidepoint(e.pos):
                self.pases["val"] = min(self.pases["max"], self.pases["val"] + self.pases["step"])

            rectp = self.players["rect"]; hp = rectp.height
            minusp = pygame.Rect(rectp.left, rectp.top, hp, hp)
            plusp  = pygame.Rect(rectp.right - hp, rectp.top, hp, hp)
            prev = int(self.players["val"])
            if minusp.collidepoint(e.pos):
                self.players["val"] = max(self.players["min"], self.players["val"] - self.players["step"])
            elif plusp.collidepoint(e.pos):
                self.players["val"] = min(self.players["max"], self.players["val"] + self.players["step"])
            if int(self.players["val"]) != prev:
                self._rebuild_grid(int(self.players["val"]))

        # celdas
        for row in self.grid:
            for cell in row: cell.handle_event(e)

        for b in self.buttons: b.handle_event(e)

    def update(self, dt): pass

    # ---------- render ----------
    def render(self, screen):
        screen.fill((8, 12, 22))
        title = self.title_font.render("Configuración — Craps (Masivo)", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 28))

        # etiquetas globales
        lbl_pases   = self.label_font.render("Pases:", True, WHITE)
        lbl_players = self.label_font.render("Jugadores:", True, WHITE)
        screen.blit(lbl_pases, (260, 74))
        screen.blit(lbl_players, (SCREEN_WIDTH//2 + 120, 70))

        # dibujar “stepper” de pases
        self._draw_stepper_like(screen, self.pases, fmt=lambda v: f"{v:,}".replace(",", "."))
        # dibujar “stepper” de jugadores
        self._draw_stepper_like(screen, self.players, fmt=lambda v: str(int(v)))

        # encabezado columnas (jugadores)
        n = int(self.players["val"])
        xs, _ = self._col_xs(n)
        head_y = 112
        for j, x in enumerate(xs, start=1):
            lbl = self.label_font.render(f"J{j}", True, LIGHT_GRAY)
            screen.blit(lbl, (x - lbl.get_width()//2, head_y))

        # etiquetas de filas
        y0 = 140; row_h = 28
        for r, (label, _, _) in enumerate(self.rows_def):
            y = y0 + r*row_h
            txt = self.row_font.render(label, True, LIGHT_GRAY)
            screen.blit(txt, (24, y - txt.get_height()//2))

        # celdas
        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                cell.draw(screen, self.row_font)

        for b in self.buttons: b.draw(screen)

    def _draw_stepper_like(self, screen, st, fmt=str):
        rect = st["rect"]; h = rect.height
        minus = pygame.Rect(rect.left, rect.top, h, h)
        plus  = pygame.Rect(rect.right - h, rect.top, h, h)
        valr  = pygame.Rect(rect.left + h, rect.top, rect.width - 2*h, h)
        pygame.draw.rect(screen, GRAY, rect, border_radius=0)
        pygame.draw.rect(screen, DARK_RED, minus); m = self.row_font.render("-", True, WHITE)
        screen.blit(m, (minus.centerx - m.get_width()//2, minus.centery - m.get_height()//2))
        pygame.draw.rect(screen, LIGHT_GREEN, plus); p = self.row_font.render("+", True, WHITE)
        screen.blit(p, (plus.centerx - p.get_width()//2, plus.centery - p.get_height()//2))
        v = self.row_font.render(fmt(int(st["val"])), True, BLACK)
        pygame.draw.rect(screen, GRAY, valr, border_radius=0)
        screen.blit(v, (valr.centerx - v.get_width()//2, valr.centery - v.get_height()//2))

    # ---------- aceptar / salida ----------
    def aceptar(self):
        cfg = self.get_config()
        from games.craps.simuladores.simulador_masivo_craps import SimuladorMasivoCraps
        state_manager.push_state(SimuladorMasivoCraps(cfg))

    # ---------- helpers de parse ----------
    def _parse_pct(self, s: str) -> float:
        t = s.lower()
        if t == "siempre": return 1.0
        if t == "salida":  return -1.0
        if t.endswith("%"):
            try: return max(0.0, min(1.0, float(t[:-1]) / 100.0))
            except: return 0.0
        if t == "nunca": return 0.0
        if t == "cobra una": return -2.0
        return 0.0

    def _nivel_a_rango(self, nivel: str) -> tuple[int,int]:
        tabla = {
            "mínimo": (5000, 5000),
            "medio bajo": (10000, 30000),
            "medio": (30000, 70000),
            "medio alto": (70000, 120000),
            "máximo": (150000, 200000),
        }
        return tabla.get(nivel, (5000, 200000))

    # ---------- construir la config ----------
    def get_config(self):
        n = int(self.players["val"])
        # índices de filas para leer fácil
        IDX = {name: i for i, (name, _, _) in enumerate(self.rows_def)}

        players = []
        for j in range(n):
            def val_choice(idx): return self.grid[idx][j].value
            def val_toggle(idx): return bool(self.grid[idx][j].value)

            nivel = val_choice(IDX["Apuesta"])
            linea = val_choice(IDX["Línea"])
            rango = self._nivel_a_rango(nivel)

            # monto fijo tomando el minimo del rango
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                monto = int(rango[0])
            else:
                monto = int(rango) # si ya es un numero unico
            
            player_cfg = {
                "jugador": j+1,
                "pase": str(linea).capitalize(),  # <--- Buena o Mala o No
                "apuesta": monto,                 # <--- monto fijo                
                "apuesta_linea_nivel": nivel,
                "apuesta_linea_rango": self._nivel_a_rango(nivel),
                "linea": linea,
                "enganche_linea": val_toggle(IDX["Enganche"]),
                "costilla_b": {
                    "preset":   val_choice(IDX["Costilla B"]),
                    "duracion": self._parse_pct(val_choice(IDX["Duración B"])),
                    "tambien_al_punto": val_toggle(IDX["También Punto B"]),
                },
                "costilla_m": { "preset": val_choice(IDX["Costilla M"]) },
                "cuadro": {
                    "preset":    val_choice(IDX["Cuadro"]),
                    "frecuencia": self._parse_pct(val_choice(IDX["Freq Cuadro"])),
                },
                "any7":     self._parse_pct(val_choice(IDX["Any Seven"])),
                "anycraps": self._parse_pct(val_choice(IDX["Any Craps"])),
                "camuninas": {
                    "objetivo":  val_choice(IDX["Camuninas"]),
                    "frecuencia": self._parse_pct(val_choice(IDX["Freq Camu"])),
                },
                "field": {
                    "usar": bool(val_toggle(IDX["Field"])),
                    "frecuencia": self._parse_pct(val_choice(IDX["Freq Field"])),
                },
                "come_dc": {
                    "usar": bool(val_toggle(IDX["Come/Don't"])),
                    "frecuencia": self._parse_pct(val_choice(IDX["Freq Come"])),
                    "cantidad": val_choice(IDX["Cant. Come"]),
                    "enganche": bool(val_toggle(IDX["Eng. Come"])),
                },
            }

            players.append(player_cfg)

        return {
            "pases": int(self.pases["val"]),
            "jugadores": n,
            "players": players,
        }
