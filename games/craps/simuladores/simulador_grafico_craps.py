# -*- coding: utf-8 -*-
from __future__ import annotations
import pygame, math, time
from typing import Dict, Any

from core.base_state import BaseState
from core.global_state import state_manager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, DARK_GREEN, DARK_RED, BLACK
from utils.paths import FONT_PATH

from games.craps.motor.motor_craps import MotorCraps
from games.craps.estadisticas.craps_stats import EstadisticasCraps

BTN_X = SCREEN_WIDTH // 2 - 60
BTN_Y = SCREEN_HEIGHT // 2
BTN_W = 120
BTN_H = 48


class SimuladorGraficoCraps(BaseState):
    def __init__(self, config: dict | None = None):
        super().__init__()
        self.config = config or {}
        
        # fonts
        self.font = pygame.font.Font(FONT_PATH, 18)
        self.big  = pygame.font.Font(FONT_PATH, 32)

        # background
        self.bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.bg.fill((8,12,22))

        # motor + stats
        self.stats = EstadisticasCraps()
        self.motor = MotorCraps(estadisticas=self.stats, semilla=self.config.get("semilla"))
        self.motor.bus.registrar_observador(self.on_evento)

        # auto-run control
        self.auto_run = False
        self._timer = 0.0
        self._tick_interval = 0.60   # ← 3 veces más lento

        # UI state
        self.ultimo_tiro = None
        self.mensaje_central = ""
        self.boton_on = False
        self.punto_actual = None
        self.tirador_actual = self.motor.tirador_id

        # jugadores visibles
        self.jugadores = []
        self._build_random_setup()

        # guardar setup en motor (sesión persistente)
        self._sync_setup_motor()

        # Iniciar tirador
        self.motor._configurar_tirador_inicial(
            self.config.get("p_buena", 0.7)
        )
        self.tirador_actual = self.motor.tirador_id

        self.running = True

    # ----------------------------------------------------------
    # SETUP
    # ----------------------------------------------------------
    def _build_random_setup(self):
        import random
        n = int(self.config.get("num_jugadores", 6))
        self.jugadores.clear()
        xs = [80 + i * 80 for i in range(n)]
        for i in range(n):
            linea = "Buena" if random.random() < 0.6 else "Mala"
            monto = 5000 * (i + 1)
            self.jugadores.append({
                "id": i+1,
                "linea": linea,
                "monto": monto,
                "x": xs[i],
                "y": SCREEN_HEIGHT - 140
            })

    def _players_for_motor(self):
        out = []
        for p in self.jugadores:
            out.append({
                "jugador": p["id"],
                "linea": p["linea"],
                "monto": p["monto"],
                "puede_tirar": True
            })
        return out

    def _sync_setup_motor(self):
        """Copia config de sesión al motor, para que step() sepa arrancar pases correctos."""
        self.motor._session_setup_players = self._players_for_motor()
        self.motor._session_num_jug      = len(self.jugadores)
        self.motor._session_p_buena      = float(self.config.get("p_buena", 0.7))
        self.motor._session_min_line     = int(self.config.get("min_linea", 5000))
        self.motor._session_max_line     = int(self.config.get("max_linea", 200000))
        self.motor._session_prob_enganche= float(self.config.get("prob_enganche", 0.5))

    # ----------------------------------------------------------
    # EVENTOS DESDE EL BUS
    # ----------------------------------------------------------
    def on_evento(self, evento: Dict[str, Any]) -> None:
        t = evento.get("tipo")
        if not t:
            return

        if t == "PASE_INICIADO":
            self.boton_on = False
            self.punto_actual = None
            self.mensaje_central = ""
            self.tirador_actual = evento.get("tirador", self.tirador_actual)

        elif t in ("TIRO_INICIADO", "TIRADA_REALIZADA"):
            d1 = evento.get("d1", evento.get("dado1"))
            d2 = evento.get("d2", evento.get("dado2"))
            suma = evento.get("suma")
            if d1 is not None:
                self.ultimo_tiro = (d1, d2, suma)
                self.mensaje_central = f"{d1} + {d2} = {suma}"

        elif t == "PUNTO_FIJADO":
            self.boton_on = True
            self.punto_actual = evento.get("valor")
            self.mensaje_central = f"El punto es: {self.punto_actual}"

        elif t == "PUNTO_LIBRE":
            self.boton_on = False
            self.punto_actual = None

        elif t == "APUESTA_COLOCADA":
            # DEBUG: ver apuestas que lleguen
            print(f"[UI DEBUG] APUESTA_COLOCADA -> {evento}")
            # no hacemos nada visual todavía

        elif t == "APUESTA_RESUELTA":
            # DEBUG: ver resoluciones
            print(f"[UI DEBUG] APUESTA_RESUELTA -> {evento}")
            res = evento.get("resultado", "")
            motivo = evento.get("motivo", "")
            self.mensaje_central = f"{res} ({motivo})"

        elif t == "FIN_DE_PASE":
            self.mensaje_central = ""


    # ----------------------------------------------------------
    # MOTOR TICK
    # ----------------------------------------------------------
    def _tick_motor(self):
        """Un solo paso del motor."""
        # si no hay pase en curso → iniciar con setup real
        if not getattr(self.motor, "_pase_in_progress", False):
            # IMPORTANT: for graphical debug mode we DISABLE enganches (prob=0)
            self.motor.start_pase(
                num_jugadores=len(self.jugadores),
                p_buena=self.motor._session_p_buena,
                pases_linea_min=self.motor._session_min_line,
                pases_linea_max=self.motor._session_max_line,
                prob_enganche=0.0,  # <<< force 0 so no enganches are attached
                setup_players=self._players_for_motor()
            )
        else:
            # seguir tirando dentro del mismo pase (un tiro por tick)
            self.motor.step()


    # ----------------------------------------------------------
    # INPUT
    # ----------------------------------------------------------
    def toggle_auto(self):
        self.auto_run = not self.auto_run

    def step_one_pase(self):
        # Si no hay pase en curso, arrancamos uno (coloca apuestas UNA sola vez)
        if not getattr(self.motor, "_pase_in_progress", False):
            # disable enganches for step-by-step visual debugging
            self.motor.start_pase(
                num_jugadores=len(self.jugadores),
                p_buena=float(self.config.get("p_buena", 0.7)),
                pases_linea_min=int(self.config.get("min_linea", 5000)),
                pases_linea_max=int(self.config.get("max_linea", 200000)),
                prob_enganche=0.0,  # <<< force 0 here also
                setup_players=self._players_for_motor()
            )
        # un step = un tiro/resolución
        self.motor.step()



    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if pygame.Rect(BTN_X, BTN_Y, BTN_W, BTN_H).collidepoint(e.pos):
                self.toggle_auto()

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self._tick_motor()
            elif e.key == pygame.K_r:
                self._build_random_setup()
                self._sync_setup_motor()
                self.motor._configurar_tirador_inicial(
                    self.config.get("p_buena", 0.7)
                )
                self.tirador_actual = self.motor.tirador_id

    # ----------------------------------------------------------
    # UPDATE
    # ----------------------------------------------------------
    def update(self, dt):
        if self.auto_run:
            self._timer += dt
            if self._timer >= self._tick_interval:
                self._timer = 0.0
                self._tick_motor()

    # ----------------------------------------------------------
    # RENDER
    # ----------------------------------------------------------
    def render(self, screen):
        screen.blit(self.bg, (0,0))

        title = self.big.render("Simulador Visual Craps", True, (255,215,0))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 10))

        st = self.stats
        panel = [
            f"Pase n°: {st.pases_simulados}",
            f"Dinero en juego (pase actual): ${st.dinero_en_juego:,.0f}",
            f"Dinero total acumulado: ${st.total_apuestas_ever:,.0f}",
            f"Ganancia casino: ${st.ganancias_casino:,.0f}",
            f"% Ganancia: {st.porcentaje_ganancia():.2f}%",
            f"Tirador: {self.tirador_actual}",
            f"Punto: {self.punto_actual if self.punto_actual else '-'}",
        ]
        x=24; y=80
        for line in panel:
            screen.blit(self.font.render(line, True, WHITE), (x,y))
            y+=20

        # jugadores
        for p in self.jugadores:
            pygame.draw.circle(screen, DARK_GREEN if p["linea"]=="Buena" else DARK_RED,
                               (p["x"], p["y"]), 20)
            lbl = self.font.render(str(p["id"]), True, WHITE)
            screen.blit(lbl,(p["x"]-lbl.get_width()//2,p["y"]-lbl.get_height()//2))

            mtxt = self.font.render(f"${p['monto']:,}", True, WHITE)
            screen.blit(mtxt,(p["x"]-mtxt.get_width()//2,p["y"]+22))

        # botón ON/OFF
        bx = SCREEN_WIDTH//2 - 60
        by = SCREEN_HEIGHT//2 - 24
        color = (0,180,0) if self.boton_on else (180,0,0)
        pygame.draw.rect(screen, color, (bx,by,120,48), border_radius=8)
        txt = self.font.render("ON" if self.boton_on else "OFF", True, WHITE)
        screen.blit(txt,(bx+60-txt.get_width()//2, by+24-txt.get_height()//2))

        # mensaje central
        mid = self.font.render(self.mensaje_central or "-", True, WHITE)
        screen.blit(mid,(SCREEN_WIDTH//2 - mid.get_width()//2, SCREEN_HEIGHT//2 - 120))

        # último tiro
        if self.ultimo_tiro:
            d1,d2,s = self.ultimo_tiro
            tt = self.big.render(f"{d1}+{d2} = {s}", True, WHITE)
            screen.blit(tt,(SCREEN_WIDTH - tt.get_width() - 40, 80))

        inst = self.font.render("Click ON/OFF. SPACE=1 tiro | R=setup", True, WHITE)
        screen.blit(inst,(24, SCREEN_HEIGHT - 40))
