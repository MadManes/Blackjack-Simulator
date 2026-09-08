


# SIMULADOR GRAFICO BLACKJACK
# games/blackjack/nuevo/states/simulador_estadistico.py

import pygame
import time
import random

from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, DARK_GREEN, LIGHT_GREEN
from utils.paths import FONT_PATH
from utils.paths import resource_path
from core.base_state import BaseState
from core.global_state import CARD_IMAGES, state_manager
from games.blackjack.nuevo.motor_probado import MotorBlackjackProbado, BLACKJACK_STRATEGIES
from games.blackjack.nuevo.statistics.blackjack_stats import EstadisticasCasino


NUM_JUGADORES = 7
NUM_BARAJAS = 8
TIEMPO_PAUSA_FINAL_MANO = 4.0
#SIMULATION_SEED = 12345 # Semilla fija para reproducibilidad

class SimuladorEstadistico(BaseState):
    def __init__(self):
        super().__init__()
        self.font = pygame.font.Font(FONT_PATH, 20)
        self.font_big = pygame.font.Font(FONT_PATH, 24)
        self.font_small = pygame.font.Font(FONT_PATH, 16)
        
        self.background_tile = pygame.image.load(resource_path("assets/images/table_pattern.png")).convert()
        self.background_surface = self.create_tiled_background()
        self.card_back = pygame.image.load(resource_path("assets/images/cartas/naipe_lomo.jpg")).convert_alpha()
        self.card_back = pygame.transform.scale(self.card_back, (54, 80))

        # Cargar estrategias desde el diccionario central
        random.seed(None) # Sincroniza la aleatoriedad de las estrategias
        estrategias_para_simulacion = [random.choice(list(BLACKJACK_STRATEGIES.values())) for _ in range(NUM_JUGADORES)]
        
        self.estadisticas = EstadisticasCasino()
        self.motor_juego = MotorBlackjackProbado(
            num_players=NUM_JUGADORES,
            num_decks=NUM_BARAJAS,
            estadisticas=self.estadisticas,
            estrategias=estrategias_para_simulacion,
            seed=None # Pasa la semilla al motor, None para aleatorio absoluto
        )
        
        self.tiempo_entre_acciones = 0.1

        self.fase = "PREPARACION"
        self.tiempo_ultima_accion = time.time()
        self.mano_actual = 0
        self.mano_cerrada = False
        self.sabot_count = 1
        self.reparto_paso = 0
        self.total_cards_to_deal = (NUM_JUGADORES + 1) * 2
        self.paused = False
        self.tiempo_fin_mano = 0
        self.volver_button = pygame.Rect(SCREEN_WIDTH - 150, SCREEN_HEIGHT - 60, 120, 40)
        self.volver_text = self.font.render("Volver", True, WHITE)

    def create_tiled_background(self):
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        tile_width, tile_height = self.background_tile.get_size()
        for y in range(0, SCREEN_HEIGHT, tile_height):
            for x in range(0, SCREEN_WIDTH, tile_width):
                bg.blit(self.background_tile, (x, y))
        return bg
    
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.paused = not self.paused
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.volver_button.collidepoint(event.pos):
                state_manager.pop_state()                

    def update(self, dt):
        if self.paused:
            return
        
        now = time.time()

        # Lógica de temporización para la pausa final
        if self.fase == "FINAL_MANO":
            if self.tiempo_fin_mano == 0:
                self.tiempo_fin_mano = now
            elif now - self.tiempo_fin_mano > TIEMPO_PAUSA_FINAL_MANO:
                if self.motor_juego.ultimo_sabot:
                    self.sabot_count = self.motor_juego.sabot_count
                self.mano_actual += 1 
                #self.motor_juego.prepare_game()
                self.fase = "PREPARACION"
                self.tiempo_ultima_accion = now
                self.reparto_paso = 0
                self.total_cards_to_deal = (NUM_JUGADORES + 1) * 2
                self.tiempo_fin_mano = 0
                
                # Resetea el sabot si es necesario
                if self.motor_juego.deck.get_remaining_cards() > 50:
                    self.sabot_count += 1
                
                return # Evita que se avance a la siguiente fase inmediatamente
                
        if now - self.tiempo_ultima_accion > self.tiempo_entre_acciones:
            self.tiempo_ultima_accion = now

            if self.fase == "PREPARACION":
                self.mano_cerrada = False
                self.motor_juego.prepare_game()
                self.tiempo_entre_acciones = 0.1
                self.fase = "REPARTO_ANIMADO"
            
            elif self.fase == "REPARTO_ANIMADO":
                if self.reparto_paso < self.total_cards_to_deal:
                    if self.reparto_paso < NUM_JUGADORES + 1:
                        # Reparte la primera carta a todos
                        recipient_idx = self.reparto_paso
                        if recipient_idx < NUM_JUGADORES:
                            self.motor_juego.deal_one_card(recipient_idx)
                        else: # Es el dealer
                            self.motor_juego.deal_one_card("dealer")
                    else:
                        # Reparte la segunda carta a todos
                        recipient_idx = self.reparto_paso - (NUM_JUGADORES + 1)
                        if recipient_idx < NUM_JUGADORES:
                            self.motor_juego.deal_one_card(recipient_idx)
                        else: # Es el dealer
                            self.motor_juego.deal_one_card("dealer")
                            
                    self.reparto_paso += 1
                else:
                    self.fase = "ACCIONES_JUGADORES"
                    self.tiempo_entre_acciones = 0.5
                    self.current_player_idx = 0
                    self.current_hand_idx = 0
            
            elif self.fase == "ACCIONES_JUGADORES":                
                if self.current_player_idx < NUM_JUGADORES:
                    player_hands = self.motor_juego.players[self.current_player_idx]
                    
                    if self.current_hand_idx < len(player_hands):
                        hand = player_hands[self.current_hand_idx]
                        if hand.status == "active":
                            # NUEVO: oportunidad de SEGURO
                            if self.motor_juego.offer_insurance() and hand.insurance == 0:
                                strat = self.motor_juego.estrategias[self.current_player_idx] or {}
                                if strat.get("seguro", True):
                                    if random.random() < 0.3:
                                        max_insurance = hand.bet // 2
                                        if max_insurance > 0:
                                            self.motor_juego.take_insurance(self.current_player_idx, self.current_hand_idx, max_insurance)

                            action = self.motor_juego.play_player_action(
                                self.current_player_idx, 
                                self.current_hand_idx, 
                                self.motor_juego.estrategias[self.current_player_idx]
                            )
                            
                            # Manejar splits recursivos
                            if action == "split":
                                # No avanzar, seguir en la misma posición para manejar el split
                                pass
                            elif action == "hit":
                                if player_hands[self.current_hand_idx].status != "active":
                                    self.current_hand_idx += 1
                            else:
                                self.current_hand_idx += 1
                        else:
                            self.current_hand_idx += 1
                    else:
                        self.current_player_idx += 1
                        self.current_hand_idx = 0
                else:
                    self.fase = "ACCIONES_DEALER"

            elif self.fase == "ACCIONES_DEALER":
                self.motor_juego.play_dealer_turn()
                self.fase = "PAUSA_DEALER"
                self.tiempo_inicio_pausa_dealer = time.time()                

            elif self.fase == "PAUSA_DEALER":
                if time.time() - self.tiempo_inicio_pausa_dealer > 2.0:  # 2 segundos de pausa
                    self.motor_juego.evaluate_results()
                    self.mano_cerrada = True
                    self.fase = "FINAL_MANO"
    
    def render(self, screen):
        # Fondo
        screen.blit(self.background_surface, (0, 0))

        # Título
        title = self.font_big.render("Blackjack NUEVO", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Panel de estadísticas en la esquina inferior izquierda
        stats_rect = pygame.Rect(10, SCREEN_HEIGHT - 170, 300, 160)
        pygame.draw.rect(screen, DARK_GREEN, stats_rect)
        pygame.draw.rect(screen, LIGHT_GREEN, stats_rect, 3)

        # Botón Volver
        pygame.draw.rect(screen, DARK_GREEN, self.volver_button)
        screen.blit(self.volver_text, (self.volver_button.centerx - self.volver_text.get_width()//2, 
                                        self.volver_button.centery - self.volver_text.get_height()//2))
        
        mano_mostrada = self.mano_actual + 1

        if self.mano_cerrada:
            en_juego_visible = self.estadisticas.dinero_en_juego
        else:
            en_juego_visible = (      
                self.estadisticas.dinero_en_juego
                + self.estadisticas.dinero_en_juego_mano_actual
            )   
        
        stats_text = [
            f"Sabot: {self.motor_juego.sabot_count}",
            f"Mano: {mano_mostrada}",
            f"Dinero en la mano: ${self.estadisticas.dinero_en_juego_mano_actual}",
            f"Dinero en juego: ${en_juego_visible}",
            f"Ganancia: ${self.estadisticas.ganancias_casino:.2f}",
            f"Porcentaje de ganancia: {self.estadisticas.calcular_porcentaje_ganancia():.2f}%"
        ]
        
        y_offset = SCREEN_HEIGHT - 160
        for text in stats_text:
            text_surface = self.font_small.render(text, True, WHITE)
            screen.blit(text_surface, (20, y_offset))
            y_offset += 25
            
        # Dibujar Dealer
        self._draw_dealer(screen)
        
        # Dibujar Jugadores
        player_zone_width = SCREEN_WIDTH - 250
        spacing = (player_zone_width - NUM_JUGADORES * 60) // (NUM_JUGADORES - 1)
        for i in range(NUM_JUGADORES):
            x = 20 + i * (80 + spacing)
            y = 50
            player_hands = self.motor_juego.players[i]
            self._draw_player_entity(screen, player_hands, f"J.{i+1}", x, y)
            
        if self.paused:
            pause_text = self.font_big.render("PAUSA", True, (255, 255, 0))
            pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            screen.blit(pause_text, pause_rect)

    def _draw_dealer(self, screen):
        x = SCREEN_WIDTH // 2 - 120
        y = SCREEN_HEIGHT - 150
        hand = self.motor_juego.dealer_hand

        if len(hand.cards) > 0:
            # Dibuja la primera carta siempre visible
            first_card_image_key = hand.cards[0].image_key()
            first_card_image = CARD_IMAGES.get(first_card_image_key, self.card_back)
            first_card_image = pygame.transform.scale(first_card_image, (54, 80))
            screen.blit(first_card_image, (x, y))

            # Dibuja el resto de las cartas, ocultando la segunda si es la fase de reparto o de jugadores
            for j, card in enumerate(hand.cards[1:]):
                if self.fase in ["REPARTO_ANIMADO", "ACCIONES_JUGADORES"] and j == 0:
                    image = self.card_back
                else:
                    image_key = card.image_key()
                    image = CARD_IMAGES.get(image_key, self.card_back)
                
                image = pygame.transform.scale(image, (54, 80))
                screen.blit(image, (x + (j+1) * 75, y))
        
        # Dibuja el puntaje del dealer solo cuando sus cartas están visibles
        if self.fase in ["ACCIONES_DEALER", "FINAL_MANO"]:
            valor = hand.best_value()
            valor_text_surface = self.font_big.render(f"{valor}", True, WHITE)
            screen.blit(valor_text_surface, (x, y - 30))

    def _draw_player_entity(self, screen, hands, label, x, y):
        if not isinstance(hands, list):
            hands = [hands]

        for i, hand in enumerate(hands):
            hand_x_offset = i * 55
            
            # 1. Nombre del jugador
            label_surface = self.font_big.render(label, True, WHITE)
            screen.blit(label_surface, (x + hand_x_offset, y))
            
            # 2. Apuesta
            bet_text_y = y + 30
            bet_text_surface = self.font.render(f"${hand.bet}", True, WHITE)
            screen.blit(bet_text_surface, (x + hand_x_offset, bet_text_y))

            # 3. Seguro (solo si se ha apostado)
            insurance_text_y = bet_text_y + 25
            if hand.insurance > 0:
                insurance_text_surface = self.font_small.render(f"${hand.insurance}", True, (255, 165, 0))
                screen.blit(insurance_text_surface, (x + hand_x_offset, insurance_text_y))
            
            # 4. Puntaje
            score_text_y = insurance_text_y + 25
            if len(hand.cards) > 0 and self.fase not in ["PREPARACION", "REPARTO_ANIMADO"]:
                valor = hand.best_value()
                valor_text_surface = self.font_big.render(f"{valor}", True, WHITE)
                screen.blit(valor_text_surface, (x + hand_x_offset, score_text_y))

            # 5. Cartas
            cards_y = score_text_y + 35
            for j, card in enumerate(hand.cards):
                image_key = card.image_key()
                image = CARD_IMAGES.get(image_key, self.card_back)
                image = pygame.transform.scale(image, (54, 80))
                screen.blit(image, (x + hand_x_offset, cards_y + j * 40))