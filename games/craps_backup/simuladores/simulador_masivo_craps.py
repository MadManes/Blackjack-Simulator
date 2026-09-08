# -*- coding: utf-8 -*-
from __future__ import annotations
import io, os, threading, time, pygame
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.base_state import BaseState
from core.global_state import state_manager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE
from utils.paths import FONT_PATH, writable_path

from games.craps.estadisticas.craps_stats_masivo import EstadisticasCrapsMasivo
from games.craps.motor.motor_craps import MotorCraps

SIM_DONE_EVENT = pygame.USEREVENT + 301

class _BridgeEventosAStats:
    """Puente del bus de MotorCraps hacia EstadisticasCrapsMasivo."""
    def __init__(self, stats: EstadisticasCrapsMasivo):
        self.s = stats
        self._ultimo_motivo_cierre: str = ""  # para detectar ganador de pase

    def __call__(self, ev: dict) -> None:
        t = ev.get("tipo")
        if t == "NUEVO_TIRADOR":
            self.s.on_nuevo_tirador()
        elif t == "APUESTA_COLOCADA":
            self.s.on_apuesta(float(ev.get("monto", 0)))
        elif t == "TIRO_INICIADO":
            self.s.on_tiro(int(ev["d1"]), int(ev["d2"]), int(ev["suma"]), bool(ev.get("es_doble", False)))
        elif t == "PUNTO_FIJADO":
            self.s.on_punto_fijado(int(ev.get("valor", 0)))
        elif t == "APUESTA_RESUELTA":
            motivo = str(ev.get("motivo", "")).lower()
            # Solo guardamos como "motivo de cierre" si es uno de los motivos definitivos
            motivos_finales = {"punto logrado", "seven-out", "come-out 7/11", "come-out 2/3", "come-out 12"}
            if motivo in motivos_finales:
                self._ultimo_motivo_cierre = motivo
            # siempre registramos la resolución en stats
            self.s.on_resolucion(str(ev.get("resultado","")).upper(),
                                 float(ev.get("pago",0)),
                                 str(ev.get("tipo_apuesta","")),
                                 motivo)
        elif t == "PUNTO_LIBRE":
            # decidir ganador del pase para totales
            motivo = (self._ultimo_motivo_cierre or "").lower()
            buena_gana = None

            # COME-OUT (usamos motivos del tipo "come-out 7", "come-out 11", "come-out 2", "come-out 3", "come-out 12")
            if motivo.startswith("come-out"):
                # extraer número si viene como "come-out X"
                parts = motivo.split()
                if len(parts) >= 2:
                    num = parts[1]
                    if num in ("7", "11"):
                        buena_gana = True
                    elif num in ("2", "3", "12"):
                        buena_gana = False
            else:
                # punto logrado / seven-out
                if motivo == "punto logrado":
                    buena_gana = True
                elif motivo == "seven-out":
                    buena_gana = False

            self.s.on_fin_pase(buena_gana)

            
class SimuladorMasivoCraps(BaseState):
    def __init__(self, config: dict):
        super().__init__()
        self.font = pygame.font.Font(FONT_PATH, 12)      # más pequeños que BJ
        self.button_font = pygame.font.Font(FONT_PATH, 24)
        self.title_font = pygame.font.Font(FONT_PATH, 38)

        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill((8, 12, 22))

        self.config = config or {}
        self.stats = EstadisticasCrapsMasivo()
        self.stats.pases_objetivo = int(self.config.get("pases"))#, 20_000))

        # Motor + suscripción
        self.motor = MotorCraps(estadisticas=None, semilla=None)
        self.bridge = None        

        # parámetros básicos (por ahora globales)        
        self.num_jugadores = int(self.config.get("jugadores", 2))
        # default de línea: si no vino desde setup, usar 70% Buena, apuestas 5k..150k, enganche 50%
        self.p_buena = float(self.config.get("p_buena", 0.7))
        self.min_linea = int(self.config.get("min_linea", 5000))
        self.max_linea = int(self.config.get("max_linea", 200000))
        self.prob_enganche = float(self.config.get("prob_enganche", 0.5)) 
        

        # control de simulación
        self.en_ejecucion = False
        self._hilo = None

        # gráfico
        self.grafico_surface = None
        self.grafico_cargado = False
        self.ultimo_png = None

        # botones
        self.btn_iniciar = pygame.Rect(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT - 86, 140, 48)
        self.btn_detener = pygame.Rect(SCREEN_WIDTH//2 + 10,  SCREEN_HEIGHT - 86, 140, 48)
        self.btn_volver  = pygame.Rect(24, SCREEN_HEIGHT - 60, 140, 40)

    # -------- Simulación en hilo --------
    def _loop(self):
        objetivo = max(1, self.stats.pases_objetivo)
        while self.en_ejecucion and self.stats.pases_simulados < objetivo:
            try:
                self.motor.jugar_pase_random(
                    num_jugadores=self.num_jugadores,
                    p_buena=self.p_buena,
                    pases_linea_min=self.min_linea,
                    pases_linea_max=self.max_linea,
                    prob_enganche=self.prob_enganche,
                    setup_players=self.setup_players if self.config.get("players") else None,
                )                
            except Exception as e:
                print(f"[CRAPS] Error durante simulación: {e}")
                break        
        self.en_ejecucion = False
        try:
            pygame.event.post(pygame.event.Event(SIM_DONE_EVENT))
        except Exception:
            pass

    def _iniciar(self):
        if self.en_ejecucion: return
        # reset
        self.stats = EstadisticasCrapsMasivo()
        self.stats.pases_objetivo = int(self.config.get("pases", 20_000))

        # crear motor y bridge nuevos para evitar suscripciones previas y se superpongan
        self.motor = MotorCraps(estadisticas=None, semilla=None)        
        self.bridge = _BridgeEventosAStats(self.stats)
        
        # construir lista de apuestas usando la config del setup (si existe)
        cfg_players = self.config.get("players", [])
        self.setup_players = []
        for idx in range(self.num_jugadores):
            if idx < len(cfg_players):
                p = cfg_players[idx]
                # el get_config de tu setup devuelve:
                # "apuesta_linea_rango": (min,max) o similar; usamos el mínimo para determinismo
                monto = None
                # si viene un rango (tuple/list), usamos la primera entrada
                rng = p.get("apuesta_linea_rango")
                if isinstance(rng, (list, tuple)) and len(rng) >= 1:
                    monto = int(rng[0])
                else:
                    # podría venir un entero directo en "apuesta"
                    monto = int(p.get("apuesta", p.get("monto", self.min_linea)))
                linea = p.get("linea", "Buena")
                self.setup_players.append({
                    "jugador": p.get("jugador", idx+1),
                    "linea": linea,
                    "monto": monto
                })
            else:
                # rellenar por si hay menos perfiles que num_jugadores
                self.setup_players.append({
                    "jugador": idx+1,
                    "linea": "Buena",
                    "monto": self.min_linea
                })

        for evt in ["NUEVO_TIRADOR","APUESTA_COLOCADA","TIRO_INICIADO","PUNTO_FIJADO","APUESTA_RESUELTA","PUNTO_LIBRE"]:
            self.motor.suscribir(evt, self.bridge)

        self.grafico_cargado = False
        self.grafico_surface = None
        self.en_ejecucion = True
        self._hilo = threading.Thread(target=self._loop, daemon=True)
        self._hilo.start()

    def _detener(self):
        if not self.en_ejecucion: return
        self.en_ejecucion = False
        if self._hilo: self._hilo.join(timeout=1.0)
        self._mostrar_grafico()

    # -------- Render / UI --------
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            if self.btn_iniciar.collidepoint(pos): self._iniciar()
            elif self.btn_detener.collidepoint(pos): self._detener()
            elif self.btn_volver.collidepoint(pos): state_manager.pop_state()
        if e.type == SIM_DONE_EVENT:
            self._mostrar_grafico(); self.grafico_cargado = True

    def update(self, dt): pass

    def render(self, screen):
        s = screen
        s.blit(self.background, (0,0))
        title = self.title_font.render("Simulación Craps", True, (255,215,0))
        s.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 20))

        y = 80
        for line in self._lineas_panel_izq():
            txt = self.font.render(line, True, WHITE)
            s.blit(txt, (40, y))
            y += 12  # más compacto que BJ

        # botones
        pygame.draw.rect(s, (0,150,0) if not self.en_ejecucion else (100,100,100), self.btn_iniciar)
        t1 = self.button_font.render("Iniciar", True, WHITE)
        s.blit(t1, (self.btn_iniciar.centerx - t1.get_width()//2, self.btn_iniciar.centery - t1.get_height()//2))

        pygame.draw.rect(s, (150,0,0) if self.en_ejecucion else (100,100,100), self.btn_detener)
        t2 = self.button_font.render("Detener", True, WHITE)
        s.blit(t2, (self.btn_detener.centerx - t2.get_width()//2, self.btn_detener.centery - t2.get_height()//2))

        pygame.draw.rect(s, (50,50,150), self.btn_volver)
        t3 = self.button_font.render("Volver", True, WHITE)
        s.blit(t3, (self.btn_volver.centerx - t3.get_width()//2, self.btn_volver.centery - t3.get_height()//2))

        estado = self.button_font.render(f"Estado: {'EN EJECUCIÓN' if self.en_ejecucion else 'DETENIDA'}",
                                  True, (0,255,0) if self.en_ejecucion else (255,0,0))
        s.blit(estado, (SCREEN_WIDTH - 320, SCREEN_HEIGHT - 48))

        # gráfico
        if self.grafico_cargado and self.grafico_surface:
            scaled = pygame.transform.smoothscale(self.grafico_surface, (650, 420))
            s.blit(scaled, (SCREEN_WIDTH - 650 - 40, 110))

    # -------- Panel izquierdo --------
    def _lineas_panel_izq(self) -> list[str]:
        st = self.stats
        prog = (st.pases_simulados / st.pases_objetivo * 100.0) if st.pases_objetivo else 0.0
        pct = st.porcentaje_ganancia()
        lines = [
            f"Pases simulados: {st.pases_simulados:,}/{st.pases_objetivo:,}                                        Progreso: {prog:.2f}%",  
            f"N° de jugadores: {self.num_jugadores}                                      Dinero en juego: {st.dinero_en_juego:,}",
            f">> Ganancia CASINO:",
            f"Ingreso a la banca: {st.cobros_de_apuestas:,}                     Pagos: {st.pagos_a_jugadores:,}", 
            f"Ganancia casino: ${st.ganancias_casino:,.0f} (Ingresos - Pagos)         Porcentaje: {pct:.2f}%",
            "---------------------------------------------------------------------------------------------",
            "--------------------------> FASE OFF",
            "",            
            f"Buenas ganadas: {int(st.off_buena_ganadas/self.num_jugadores)}        Buenas perdidas: {int(st.off_buena_perdidas/self.num_jugadores)}",
            #">> Por el total de jugadores:",
            #f"Buenas ganadas: {st.off_buena_ganadas}          Buenas perdidas: {st.off_buena_perdidas}",
            "---------------------------------------------------------------------------------------------",
            f" - Siete: {st.off_7}   - Once: {st.off_11}   - Dos: {st.off_2}     - Tres: {st.off_3}    - Doce: {st.off_12}",
            f"",
            f"Cuadros totales: {st.off_cuadros_total}",
            f"",
            f">> Puntos a buscar:   4/10: {st.off_punto_4_10}    5/9: {st.off_punto_5_9}      6/8: {st.off_punto_6_8}",
            "---------------------------------------------------------------------------------------------",
            "--------------------------> FASE ON",
            "",
            f"Buenas ganadas: {int(st.on_buena_ganadas/self.num_jugadores)}         Buenas perdidas: {int(st.on_buena_perdidas/self.num_jugadores)}",
            #">> Por el total de jugadores:",
            #f"Buenas ganadas: {int(st.on_buena_ganadas)}          Buenas perdidas: {int(st.on_buena_perdidas)}",
            f"",
            f">> Puntos encontrados:    4/10: {st.on_gana_punto_4_10}    5/9: {st.on_gana_punto_5_9}      6/8: {st.on_gana_punto_6_8}",
            f"Punto de Camunina: {st.on_gana_punto_camunina}",
            f" - Siete: {st.on_pierde_7}     - Once: {st.on_11}    - Craps: {st.on_craps}",
            f"Cuadros totales: {st.on_cuadros_total}",
            "---------------------------------------------------------------------------------------------",
            "TOTALES",
            f"Buenas Ganadas: {(st.off_buena_ganadas + st.on_buena_ganadas)//self.num_jugadores}",
            f"Buenas Perdidas: {(st.off_buena_perdidas + st.on_buena_perdidas)//self.num_jugadores}",
            f"Camuninas seguidas (la misma): {st.racha_misma_camunina_max}",
            f"Camuninas seguidas (cualquiera): {st.racha_cualquier_camunina_max}",
            f"Camuninas seguidas (las cuatro): {st.racha_cuatro_distintas_max}",
            f"Field: {st.field_total}",
            f"Cuadros Totales: {st.cuadros_total}",
            f"Tiros totales de la simulación: {st.tiros_totales}",
            "---------------------------------------------------------------------------------------------",
            "PASE MÁS LARGO",
            f"El pase más largo fue de {st.pase_mas_largo_tiros} tiros, "
            f"se obtuvieron {st.pase_mas_largo_costillas} números de la costilla "
            f"y {st.pase_mas_largo_cuadros} cuadros.",
            f"Resultando un pase {st.pase_mas_largo_resultado_buena} para la Buena.",
        ]
        return lines

    # -------- Gráfico --------
    def _mostrar_grafico(self):
        st = self.stats
        x = st.historial_pases[:] or [st.pases_simulados]
        y = st.historial_pct[:] or [st.porcentaje_ganancia()]

        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(14,8), dpi=180)
        fig.patch.set_facecolor('#2d2d2d'); ax.set_facecolor('#252526')
        ax.plot(x, y, linewidth=2)
        ax.set_title("Evolución de ganancias Craps", color='#ffffff')
        ax.set_xlabel("Pases", color='#cccccc'); ax.set_ylabel("Ganancia acumulada (%)", color='#cccccc')
        ax.tick_params(axis='x', colors='#cccccc'); ax.tick_params(axis='y', colors='#cccccc')
        ax.grid(True, linestyle='--', color='#444444')

        plt.tight_layout()
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        outdir = writable_path("plots", "craps")
        path = os.path.join(outdir, f"ganancia_craps_{ts}.png")
        fig.savefig(path, dpi=180, bbox_inches="tight", pad_inches=0.1)

        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=180, bbox_inches="tight", pad_inches=0.1)
        buf.seek(0)
        try:
            self.grafico_surface = pygame.image.load(buf, 'png').convert_alpha()
            self.grafico_cargado = True
        except Exception:
            self.grafico_surface = None
            self.grafico_cargado = False
        plt.close(fig)
        self.ultimo_png = path
