

# games/blackjack/nuevo/states/simulador_estadistico_masivo.py

import io, os
import pygame
import time
import threading
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.base_state import BaseState
from core.global_state import state_manager
from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE
from utils.paths import FONT_PATH

from utils.paths import writable_path
from games.blackjack.nuevo.statistics.blackjack_stats import EstadisticasCasino
from games.blackjack.nuevo.motor_probado import MotorBlackjackProbado, BLACKJACK_STRATEGIES

SIM_DONE_EVENT = pygame.USEREVENT + 101  # separado del “nuevo” por si conviven
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

class SimuladorMasivo:
    def __init__(self, config):
        self.config = config or {}
        self.lock = threading.Lock()

        self.en_ejecucion = False
        self.hilo_simulacion = None

        self.estadisticas = EstadisticasCasino()
        self.motor = None

        self.manos_objetivo = int(self.config.get("manos", 1_000_000))
        self.manos_por_minuto = 0
        
        self.hist_manos = []
        self.hist_pct = []
        self.hist_step = int(self.config.get("hist_step", 500))
        
        # Estrtegias para el setup
        num_players = int(self.config.get("jugadores", 4))
        
        estrats = []
        from games.blackjack.nuevo.motor_probado import BLACKJACK_STRATEGIES
        for p in self.config.get("players", [])[:num_players]:
            base = BLACKJACK_STRATEGIES.get(p["estrategia"], {"tipo": p.get("estrategia", "nunca_se_pasa")})
            estrats.append({
                **base,
                "duplica": p.get("duplica", False),
                "apertura_pares": p.get("aperturas", False),
                "apertura_ases": True,
                "apertura_multiple": p.get("aperturas", False),
                "seguro": p.get("seguro", False),
            })

        
        while len(estrats) < num_players:
            estrats.append(BLACKJACK_STRATEGIES["nunca_se_pasa"])

        self.estrategias = estrats

        apuestas = [int(p.get("apuesta", 3000)) for p in self.config.get("players", [])[:num_players]]
        while len(apuestas) < num_players:
            apuestas.append(3000)
        self.apuestas_por_jugador = apuestas

        # Crear motor con las estrategias/apuestas iniciales
        self._crear_motor(num_players)

    def _crear_motor(self, num_players):
        self.motor = MotorBlackjackProbado(
            num_players=num_players,
            num_decks=8,
            estadisticas=self.estadisticas,
            estrategias=self.estrategias,
            seed=None
        )
        self.motor.apuestas_por_jugador = self.apuestas_por_jugador[:]
    
    def iniciar_simulacion(self):
        if self.en_ejecucion:
            return
        self.en_ejecucion = True

        # Reset de estado
        with self.lock:
            self.estadisticas = EstadisticasCasino()
            self.estadisticas.historial_step = 500
            if self.motor is not None:
                self.motor.estadisticas = self.estadisticas
                # mantener mismas estrategias/apuestas
                self.motor.apuestas_por_jugador = self.apuestas_por_jugador[:]

            self.hist_manos = []
            self.hist_pct = []

        self.hilo_simulacion = threading.Thread(target=self._simular, daemon=True)
        self.hilo_simulacion.start()            
            
    
    def detener_simulacion(self):
        if not self.en_ejecucion:
            return
        self.en_ejecucion = False
        if self.hilo_simulacion:
            self.hilo_simulacion.join(timeout=1.0)
    
    def _simular(self):
        # snapshot inicial
        with self.lock:
            self.hist_manos.append(self.estadisticas.total_manos)
            self.hist_pct.append(self.estadisticas.calcular_porcentaje_ganancia())

        while self.en_ejecucion and self.estadisticas.total_manos < self.manos_objetivo:
            try:
                with self.lock:
                    self.motor.play_round()
                    if (self.estadisticas.total_manos % self.hist_step) == 0:
                        self.hist_manos.append(self.estadisticas.total_manos)
                        self.hist_pct.append(self.estadisticas.calcular_porcentaje_ganancia())
            except Exception as e:
                print(f"[CLÁSICO] Error en mano {self.estadisticas.total_manos}: {e}")
                break

        # último snapshot
        with self.lock:
            if not self.hist_manos or self.hist_manos[-1] != self.estadisticas.total_manos:
                self.hist_manos.append(self.estadisticas.total_manos)
                self.hist_pct.append(self.estadisticas.calcular_porcentaje_ganancia())

        self.en_ejecucion = False
        try:
            pygame.event.post(pygame.event.Event(SIM_DONE_EVENT))
        except Exception:
            pass
    
    def get_estadisticas(self):
        """Obtiene una copia segura de las estadísticas actuales"""
        with self.lock:
            return self.estadisticas        
       

class SimuladorEstadisticoMasivo(BaseState):
    def __init__(self, config=None):
        super().__init__()
        self.font = pygame.font.Font(FONT_PATH, 24)
        self.title_font = pygame.font.Font(FONT_PATH, 36)
        self.background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.background.fill((30, 30, 50))
        
        self.config = config or {}

        # Inicializamos el simulador masivo
        self.simulador = SimuladorMasivo(self.config)
        self.estadisticas = self.simulador.estadisticas        
        
        self.ultimo_grafico_path = None
        self.grafico_surface = None
        self.grafico_cargado = False
        
        self.inicio_simulacion = time.time()
        self.estadisticas_visual = EstadisticasCasino()
        self.ultima_actualizacion = 0  
        
        # Configurar botones
        self.btn_iniciar = pygame.Rect(SCREEN_WIDTH//2 - 150, SCREEN_HEIGHT - 100, 140, 50)
        self.btn_detener = pygame.Rect(SCREEN_WIDTH//2 + 10, SCREEN_HEIGHT - 100, 140, 50)
        self.btn_volver = pygame.Rect(20, SCREEN_HEIGHT - 60, 140, 40)
        
    def _iniciar_simulacion(self):
        if not self.simulador.en_ejecucion:
            self.grafico_cargado = False
            self.grafico_surface = None
            self.ultimo_grafico_path = None
            self.inicio_simulacion = time.time()
            self.simulador.iniciar_simulacion()
    
    def _detener_simulacion(self):
        if self.simulador.en_ejecucion:
            self.simulador.detener_simulacion()            
            self.mostrar_grafico()
            self.grafico_cargado = True

    def mostrar_grafico(self):
        stats = self.simulador.get_estadisticas()
    
        # Historial del motor si existe; si no, snapshots locales
        if getattr(stats, "historial_manos", None) and getattr(stats, "historial_porcentaje_ganancia", None):
            manos = list(stats.historial_manos)
            ganancias = list(stats.historial_porcentaje_ganancia)
        else:
            manos = self.simulador.hist_manos[:]
            ganancias = self.simulador.hist_pct[:]
    
        if not manos:
            manos = [stats.total_manos]
            ganancias = [stats.calcular_porcentaje_ganancia()]

        # ordenar 
        pares = sorted({(m, g) for m, g in zip(manos, ganancias)}, key=lambda t: t[0])
        manos = [m for m, _ in pares]
        ganancias = [g for _, g in pares]

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 8), dpi=180)
        fig.patch.set_facecolor('#2d2d2d')
        ax.set_facecolor('#252526')

        line_color = '#66ccff'
        label_color = '#cccccc'
        title_color = '#ffffff'
        grid_color = '#444444'

        ax.plot(manos, ganancias, label="Ganancia acumulada (%)", color=line_color, linewidth=2)
        ax.set_title("Evolución de ganancias blackjack CLÁSICO", color=title_color)
        ax.set_xlabel("Número de manos", color=label_color)
        ax.set_ylabel("Ganancia acumulada (%)", color=label_color)
        ax.tick_params(axis='x', colors=label_color)
        ax.tick_params(axis='y', colors=label_color)
        ax.grid(True, linestyle='--', color=grid_color)
        ax.legend(facecolor='#252526', edgecolor=label_color, labelcolor=label_color)

        plt.tight_layout()

        # Guardar (opcional) y también a buffer para Pygame
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = writable_path("plots", "blackjack_clasico")
        nombre_archivo = os.path.join(output_dir, f"ganancia_BJ_clasico_{timestamp}.png")

        fig.savefig(nombre_archivo, dpi=180, bbox_inches="tight", pad_inches=0.1)
        
        buf = io.BytesIO()
        fig.savefig(buf, format="PNG", dpi=180, bbox_inches="tight", pad_inches=0.1)
        buf.seek(0)
        try:
            self.grafico_surface = pygame.image.load(buf, 'png').convert_alpha()
            self.grafico_cargado = True
        except Exception as e:
            print(f"[CLÁSICO] No se pudo crear la Surface del gráfico: {e}")
            self.grafico_surface = None
            self.grafico_cargado = False
        
        plt.close(fig)
        self.ultimo_grafico_path = nombre_archivo

    
    def update(self, dt):
        now = time.time()
        if now - self.ultima_actualizacion > 0.5:
            # Obtener estadísticas actualizadas de forma segura
            if self.simulador.en_ejecucion:
                self.estadisticas_visual = self.simulador.get_estadisticas()
                
                # Calcular manos por minuto
                if self.inicio_simulacion == 0:
                    self.inicio_simulacion = now
                tiempo_transcurrido = now - self.inicio_simulacion
                if tiempo_transcurrido > 0:
                    manos_simuladas = self.estadisticas_visual.total_manos
                    self.simulador.manos_por_minuto = (manos_simuladas / tiempo_transcurrido) * 60
            
            self.ultima_actualizacion = now
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            if self.btn_iniciar.collidepoint(mouse_pos):
                self._iniciar_simulacion()
                
            elif self.btn_detener.collidepoint(mouse_pos):
                self._detener_simulacion()
                
            elif self.btn_volver.collidepoint(mouse_pos):
                from games.blackjack.nuevo.states.simulador_estadistico import SimuladorEstadistico
                # Asumiendo que state_manager se inyecta en la inicialización
                state_manager.pop_state()

        if event.type == SIM_DONE_EVENT:
            self.mostrar_grafico()
            self.grafico_cargado = True

    def render(self, screen):
        screen.blit(self.background, (0, 0))        
        title = self.title_font.render("Simulación Blackjack NUEVO", True, (255, 215, 0))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 20))        
        
        stats = self._obtener_datos_estadisticos()
        y_pos = 100
        for stat in stats:
            text = self.font.render(stat, True, (255, 255, 255))
            screen.blit(text, (50, y_pos))
            y_pos += 30
        
        self._dibujar_botones(screen)
        
        estado_text = "EN EJECUCIÓN" if self.simulador.en_ejecucion else "DETENIDA"
        estado_color = (0, 255, 0) if self.simulador.en_ejecucion else (255, 0, 0)
        estado = self.font.render(f"Estado: {estado_text}", True, estado_color)
        screen.blit(estado, (SCREEN_WIDTH - 300, SCREEN_HEIGHT - 60))

        if self.grafico_cargado and self.grafico_surface:
            # tamaño agradable y nítido
            target_w, target_h = 650, 420
            scaled = pygame.transform.smoothscale(self.grafico_surface, (target_w, target_h))
            screen.blit(scaled, (SCREEN_WIDTH - target_w - 50, 100))
    
    def _obtener_datos_estadisticos(self):
        objetivo = self.simulador.manos_objetivo or 1_000_000
        est = self.simulador.get_estadisticas()
        prog = (est.total_manos / objetivo) * 100 if objetivo else 0.0
        return [
            f"Manos simuladas: {est.total_manos:,}/{objetivo:,}",
            f"Progreso: {prog:.1f}%",
            f"Manos por minuto: {self.simulador.manos_por_minuto:,.0f}",
            f"Ganancias casino: ${est.ganancias_casino:,.2f}",
            f"Porcentaje ganancia: {est.calcular_porcentaje_ganancia():.4f}%",
            f"Manos ganadas: {est.manos_ganadas:,}",
            f"Manos perdidas: {est.manos_perdidas:,}",
            f"Manos empatadas: {est.manos_empatadas:,}",
            f"Blackjacks jugador: {est.blackjacks_jugador:,}",
            f"Blackjacks dealer: {est.blackjacks_dealer:,}",
            f"Aperturas realizadas: {est.splits:,}",
            f"Aperturas de Ases realizadas: {est.split_ases:,}",
            f"Duplicadas realizadas: {est.doubles:,}",
        ]

    def _dibujar_botones(self, screen):
        # Iniciar
        btn_iniciar_color = (0, 150, 0) if not self.simulador.en_ejecucion else (100, 100, 100)
        pygame.draw.rect(screen, btn_iniciar_color, self.btn_iniciar)
        t1 = self.font.render("Iniciar", True, WHITE)
        screen.blit(t1, (self.btn_iniciar.centerx - t1.get_width()//2,
                         self.btn_iniciar.centery - t1.get_height()//2))
        # Detener
        btn_detener_color = (150, 0, 0) if self.simulador.en_ejecucion else (100, 100, 100)
        pygame.draw.rect(screen, btn_detener_color, self.btn_detener)
        t2 = self.font.render("Detener", True, WHITE)
        screen.blit(t2, (self.btn_detener.centerx - t2.get_width()//2,
                         self.btn_detener.centery - t2.get_height()//2))
        # Volver
        pygame.draw.rect(screen, (50, 50, 150), self.btn_volver)
        t3 = self.font.render("Volver", True, WHITE)
        screen.blit(t3, (self.btn_volver.centerx - t3.get_width()//2,
                         self.btn_volver.centery - t3.get_height()//2))