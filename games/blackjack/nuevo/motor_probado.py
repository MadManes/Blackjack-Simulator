

# games/blackjack/nuevo/motor_probado.py

import random
from games.blackjack.nuevo.statistics.blackjack_stats import EstadisticasCasino

# Diccionario de estrategias
BLACKJACK_STRATEGIES = {
    'nunca_se_pasa': {
        'tipo': 'nunca_se_pasa',
        'apertura_pares': True,
        'apertura_ases': True,
        'apertura_multiple': False,
        'duplica': True,
        'seguro': True
    },
    'arriesgado_1': {
        'tipo': 'arriesgado_1',
        'apertura_pares': True,
        'apertura_ases': True,
        'apertura_multiple': True,
        'duplica': True,
        'seguro': False
    },
    'arriesgado_2': {
        'tipo': 'arriesgado_2',
        'apertura_pares': True,
        'apertura_ases': True,
        'apertura_multiple': False,
        'duplica': True,
        'seguro': False
    },
    'arriesgado_3': {
        'tipo': 'arriesgado_3',
        'apertura_pares': True,
        'apertura_ases': True,
        'apertura_multiple': True,
        'duplica': True,
        'seguro': True
    },
    # Agregar más estrategias aca
}

class Card:
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit

    def get_blackjack_value(self):
        if self.value > 10:
            return 10
        if self.value == 1:
            return 11
        return self.value

    def image_key(self):
        return f"{self.value}{self.suit}"

    def __str__(self):
        value_map = {
            1: 'A',
            11: 'J',
            12: 'Q',
            13: 'K'
        }
        value_str = value_map.get(self.value, str(self.value))
        suit_names = {
            'hearts': 'C',
            'spades': 'P',
            'diamonds': 'D',
            'clubs': 'T' 
        }
        suit_str = suit_names.get(self.suit, self.suit)
        return f"{value_str}{suit_str}"
    

class Hand:
    def __init__(self, player_idx, is_split=False, bet=3000, motor=None):
        self.player_idx = player_idx
        self.cards = []
        self.is_split = is_split        
        self.status = "active"
        self.bet = bet
        self.insurance = 0
        self.motor = motor
        self.is_split_ace = False
        self.is_split_twenty = False

    def add_card(self, card):
        self.cards.append(card)
        self._check_status()

    def _check_status(self):
        value = self.best_value()
        if value > 21:
            self.status = "bust"
        elif value == 21 and len(self.cards) == 2:
            self.status = "blackjack"
            if self.motor and self.motor.dealer_hand == self:
                self.motor.estadisticas.registrar_evento("blackjack_dealer")
            elif self.motor:
                self.motor.estadisticas.registrar_evento("blackjack_jugador")

    def best_value(self):
        value = sum(card.get_blackjack_value() for card in self.cards)
        num_aces = sum(1 for card in self.cards if card.value == 1)
        
        while value > 21 and num_aces > 0:
            value -= 10
            num_aces -= 1
        return value

    def is_soft_hand(self):           
        if not any(card.value == 1 for card in self.cards):
            return False
        
        value_with_aces_as_1 = sum(card.get_blackjack_value() if card.value != 1 else 1 for card in self.cards)
        
        return self.best_value() > value_with_aces_as_1

    def can_double(self):
        if self.is_split_ace:
            return False
        if self.is_split and (self.motor is None or not self.motor.permite_doblar_en_split):
            return False
        return len(self.cards) == 2 and 2 <= self.best_value() <= 13

    def can_split(self, max_hands=3):
        if len(self.cards) != 2:
            return False
        if self.motor and self.player_idx is not None:
            if len(self.motor.players[self.player_idx]) >= max_hands:
                return False
        # Mismo valor BJ (10 para 10/J/Q/K)
        return self.cards[0].get_blackjack_value() == self.cards[1].get_blackjack_value()

    
    def __str__(self):
        cards_str = ", ".join(str(card) for card in self.cards)
        return f"{cards_str} (Valor: {self.best_value()})"

class Deck:
    def __init__(self, num_decks=8, seed=None):
        self.num_decks = num_decks
        self.seed = seed
        self.reset()
        
    def reset(self):
        if self.seed:
            random.seed(self.seed)
        else:
            random.seed(None)
        self.cards = []
        suits = ['C', 'P', 'D', 'T']
        for _ in range(self.num_decks):
            for suit in suits:
                for value in range(1, 14):
                    self.cards.append(Card(value, suit))
        random.shuffle(self.cards)
        self.initial_deck_state = [str(card) for card in self.cards]

    def deal_card(self):
        if not self.cards:
            raise Exception("No hay más cartas en el mazo.")
        return self.cards.pop()

    def get_remaining_cards(self):
        return len(self.cards)

    def get_all_cards_as_string_list(self):
        return [str(card) for card in self.cards]

class MotorBlackjackProbado:
    def __init__(self, num_players=1, num_decks=8, estadisticas=None, estrategias=None, 
                 log_file=None, seed=None, silencioso=None, log_hands_limit=None):
        self.num_players = num_players
        self.num_decks = num_decks
        self.seed = seed
        self.silencioso = silencioso
        self.long_hands_limit = log_hands_limit
        self.split_una_carta_y_planta = False
        self.permite_doblar_en_split = True
        self.permite_segundo_split_en_segunda_mano = True
        self.sabot_count = 1  # Contador de sabot
        self.deck = Deck(self.num_decks, seed=self.seed)
        self.players = []
        self.dealer_hand = Hand(None, bet=0, motor=self)
        self.estadisticas = estadisticas if estadisticas else EstadisticasCasino()
        self.estrategias = estrategias
        self.apuesta_minima = 3000
        self.apuestas_por_jugador = None
        self.blackjack_payout_rate = 1.5
        self.jugadores_asegurados_round = set()
        self.log_file = log_file
        self.round_number = 0
        self.total_ganancia_banca = 0.0
        self.total_dinero_jugado = 0.0
        self.mano_actual = 0
        self.ultimo_sabot = False  # Indica si este es el último sabot           
        
        self._initialize_players()
        
    def _log_to_file(self, message):
        return
    
    def _initialize_players(self):
        self.players = []
        for i in range(self.num_players):
            self.players.append([Hand(i, bet=self.apuesta_minima, motor=self)])

    def _hit_threshold_from_strategy(self, strategy, dealer_up):
        """
        Devuelve el umbral (entero) hasta el cual se PIDE carta (inclusive)
        de acuerdo al 'tipo' y la carta visible del dealer.
        Si no hay dealer_up disponible, toma umbral conservador (12).
        """
        t = (strategy or {}).get('tipo', 'nunca_se_pasa')
        up = dealer_up or 0

        if t == 'nunca_se_pasa':
            # pide mientras total <= 12
            return 12

        elif t == 'arriesgado_1':
            # pide <= 12 si up in {4,5,6}, si no pide <= 14
            return 12 if up in (4,5,6) else 14

        elif t == 'arriesgado_2':
            # pide <= 12 si up in {2,3,4,5,6}, si no pide <= 14
            return 12 if up in (2,3,4,5,6) else 14

        elif t == 'arriesgado_3':
            # pide <= 14 si up NOT in {2,3,4,5,6,7}; si sí está en {2..7}, usamos 12 (supuesto razonable)
            return 14 if up not in (2,3,4,5,6,7) else 12

        # fallback
        return 12


    def prepare_game(self):
        self.jugadores_asegurados_round.clear()
        # Verificar si es el último pase y si debemos reiniciar
        if self.ultimo_sabot:
            self.sabot_count += 1
            self.deck = Deck(self.num_decks, seed=self.seed)
            self._log_to_file(f"Sabot #{self.sabot_count} - Nuevo mazo barajado")
            self.ultimo_sabot = False
        
        self.round_number += 1
        self.estadisticas.total_manos += 1
        
        
        #self._log_to_file(LOG_SEPARATOR)
        self._log_to_file(f"MANO N° {self.round_number} - Sabot #{self.sabot_count} [ALEATORIO]")
        #self._log_to_file(LOG_SEPARATOR)
        
        self._log_to_file(f"Dinero total acumulado ANTES de la mano: ${self.total_dinero_jugado:.2f}")
        self._log_to_file(f"Ganancia banca acumulada: ${self.total_ganancia_banca:.2f}")
        self._log_to_file(f"Cartas restantes: {self.deck.get_remaining_cards()}")

        self.estadisticas.ganancia_mano_actual = 0.0
        self.estadisticas.dinero_en_juego_mano_actual = 0 # <--- Se reinicia a 0 aquí
        
        # Verificar si este será el último sabot
        if self.deck.get_remaining_cards() < 100:
            self._log_to_file("ADVERTENCIA: Este es el último sabot antes de barajar")
            self.ultimo_sabot = True

        self.players = [[Hand(i, bet=self.apuesta_minima, motor=self)] for i in range(self.num_players)]

        if self.apuestas_por_jugador and len(self.apuestas_por_jugador) == self.num_players:
            for i in range(self.num_players):
                self.players[i][0].bet = int(self.apuestas_por_jugador[i])

        for i in range(self.num_players):
            self.estadisticas.registrar_apuesta(self.players[i][0].bet)

        self.dealer_hand = Hand(None, bet=0, motor=self)
        self.dealer_hand.status = "active"
        
        self._log_to_file(f"Apuesta inicial por jugador: {self.apuesta_minima}")

    def deal_one_card(self, recipient, hand_idx=0):
        try:
            # Verificar si quedan suficientes cartas
            if self.deck.get_remaining_cards() == 0:
                raise Exception("No hay más cartas en el mazo.")
                
            card = self.deck.deal_card()
            if recipient == "dealer":
                self.dealer_hand.add_card(card)
            else:
                if recipient < len(self.players):
                    player_hands = self.players[recipient]
                    if hand_idx < len(player_hands):
                        hand = player_hands[hand_idx]
                        if hand.motor is None:
                            hand.motor = self
                        hand.add_card(card)
                    else:
                        self._log_to_file(f"Error: Invalid hand index {hand_idx} for player {recipient}")
                else:
                    self._log_to_file(f"Error: Invalid player index {recipient}")
            return card
        except Exception as e:
            self._log_to_file(f"EXCEPCIÓN en deal_one_card: {str(e)}")
            raise
        
    def get_player_action(self, hand, strategy, player_idx, hand_idx):
        if hand.status != "active":
            return "stand"
    
        # Asegura dict válido
        if not isinstance(strategy, dict) or 'tipo' not in strategy:
            strategy = BLACKJACK_STRATEGIES['nunca_se_pasa']
    
        total = hand.best_value()
        dealer_up = self.dealer_hand.cards[0].get_blackjack_value() if self.dealer_hand.cards else 0

        # --- Ventana del PRIMER split (única) ---
        num_hands = len(self.players[player_idx])
        ventana_primer_split = (num_hands == 1 and hand_idx == 0)
        if ventana_primer_split and hand.can_split(max_hands=3):
            c1, c2 = hand.cards[0], hand.cards[1]
            es_par_ases = (c1.value == 1 and c2.value == 1)

            if es_par_ases and strategy.get('apertura_ases', True):
                return "split"  # siempre split de AA

            if not es_par_ases and strategy.get('apertura_pares', True):
                # split de pares con probabilidad 75%
                if random.random() < 0.75:
                    return "split"
                # si cae en el 25% restante, no splitea y sigue a decidir hit/stand

        # --- Doble (si estrategia lo permite) ---
        if strategy.get('duplica', True) and hand.can_double():
            soft = hand.is_soft_hand()
            debe_doblar = False
            # reglas conservadoras 
            if not soft:
                if total == 9 and dealer_up in (3,4,5,6): debe_doblar = True
                elif total == 10 and dealer_up in (2,3,4,5,6,7,8,9): debe_doblar = True
                elif total == 11 and dealer_up in (2,3,4,5,6,7,8,9,10): debe_doblar = True
            else:
                if 13 <= total <= 18 and dealer_up in (4,5,6): debe_doblar = True

            if debe_doblar:
                return "double"    
        
        # --- HIT/STAND ---
        # Soft: mantenemos la regla clásica (pedir < 17, plantarse >= 17)
        if hand.is_soft_hand():
            return "hit" if total < 17 else "stand"

        # umbral por 'tipo'
        threshold = self._hit_threshold_from_strategy(strategy, dealer_up)
        if total <= threshold:
            return "hit"
        else:
            return "stand"

  
    def play_player_action(self, player_idx, hand_idx, strategy):
        """
        Secuencia de juego por mano con regla de split escalonado:
        - Primer split: crea mano1 y mano2 (sin repartir carta obligatoria aquí).
        - Al entrar en el turno de cada mano de split (len==1), se reparte 1 carta obligatoria:
            * mano1: 1 carta y planta.
            * mano2: 1 carta; si queda par y es la segunda mano y aún hay 2 manos, permite segundo split.
        - Segundo split (solo sobre mano2): crea mano2a y mano3 (sin cartas obligatorias aquí).
          Las cartas obligatorias para mano2a y mano3 se darán cuando les toque su turno (mismo pre-paso).
        """
        hand = self.players[player_idx][hand_idx]

        # =========================
        # PRE-PASO: manos de split con 1 sola carta
        # =========================
        if hand.is_split and len(hand.cards) == 1:
            carta_obligatoria = self.deal_one_card(player_idx, hand_idx)
            self._log_to_file(f"-> Recibe carta obligatoria (post-split): {carta_obligatoria}")

            # Lee si la estrategia permite segundo split
            estrat = self.estrategias[player_idx] if self.estrategias else {}
            permite_multi = estrat.get('apertura_multiple', True)


            # SEGUNDO SPLIT: solo sobre la segunda mano del primer split
            if (self.permite_segundo_split_en_segunda_mano
                and len(self.players[player_idx]) == 2       # aún solo mano1 y mano2
                and hand_idx == 1                             # estamos en la segunda mano
                and hand.can_split(max_hands=3)):

                self._log_to_file("--> SEGUNDO SPLIT (sobre la segunda mano)")

                c1, c2 = hand.cards[0], hand.cards[1]
                mano2a = Hand(player_idx, is_split=True, bet=hand.bet, motor=self)
                mano2a.add_card(c1)
                mano3  = Hand(player_idx, is_split=True, bet=hand.bet, motor=self)
                mano3.add_card(c2)

                # Marcar split de ases (solo para que 21 post-split no cuente como BJ si así lo definiste)
                if c1.value == 1 and c2.value == 1:
                    mano2a.is_split_ace = True
                    mano3.is_split_ace  = True
                    self.estadisticas.registrar_evento("split_ases")

                # Reemplazar mano actual por mano2a y mano3
                self.players[player_idx].pop(hand_idx)
                self.players[player_idx].insert(hand_idx, mano2a)
                self.players[player_idx].insert(hand_idx + 1, mano3)

                # Registrar apuesta adicional por el segundo split (mano3)
                self.estadisticas.registrar_evento("split")
                self.estadisticas.registrar_apuesta(mano3.bet)

                # No repartir aquí cartas obligatorias a mano2a/mano3: el pre-paso lo hará cuando les toque
                return "split"

            # Regla especial ases, una carta y planta
            if hand.is_split_ace:
                hand.status = "stand"
                return "stand"

            # Regla: tras recibir la carta obligatoria, planta (mano1 y, si no hubo segundo split, también mano2)
            if self.split_una_carta_y_planta:
                hand.status = "stand"
                return "stand"

        # Si ya no está activa, terminada
        if hand.status != "active":
            return "finished"

        # =========================
        # LOG "ANTES DE ACCIÓN"
        # =========================
        self._log_to_file(f"\nJugador {player_idx+1}, Mano {hand_idx+1} - ANTES DE ACCIÓN:")
        self._log_to_file(f"- Cartas: {hand}")
        self._log_to_file(f"- Apuesta: ${hand.bet}")
        if hand.insurance > 0:
            self._log_to_file(f"- Seguro: ${hand.insurance}")

        # Decidir acción
        action = self.get_player_action(hand, strategy, player_idx, hand_idx)
        if action is not None:
            self._log_to_file(f"Acción seleccionada: {action.upper()}")

        # =========================
        # ACCIONES
        # =========================

        # SPLIT (primer split, se crean mano1 y mano2, sin cartas obligatorias aquí)
        if action == "split":
            self._log_to_file(f"--> SPLIT")

            seguro_original = hand.insurance

            c1, c2 = hand.cards[0], hand.cards[1]

            mano1 = Hand(player_idx, is_split=True, bet=hand.bet, motor=self)
            mano1.add_card(c1)
            mano2 = Hand(player_idx, is_split=True, bet=hand.bet, motor=self)
            mano2.add_card(c2)

            mano1.insurance = seguro_original
            mano2.insurance = 0

            if c1.value == 1 and c2.value == 1:
                mano1.is_split_ace = True
                mano2.is_split_ace = True
                self.estadisticas.registrar_evento("split_ases")

            # Reemplazar la mano original por mano1 y mano2
            self.players[player_idx].pop(hand_idx)
            self.players[player_idx].insert(hand_idx, mano1)
            self.players[player_idx].insert(hand_idx + 1, mano2)

            # Registrar apuesta adicional por el split (mano2)
            self.estadisticas.registrar_evento("split")
            self.estadisticas.registrar_apuesta(mano2.bet)

            # No repartir aún las cartas obligatorias: se dará al entrar al turno de cada mano (pre-paso)
            self._log_to_file("DESPUÉS DE SPLIT (pendiente carta obligatoria en cada mano):")
            for idx, h in enumerate(self.players[player_idx], 1):
                self._log_to_file(f"- Mano {idx}: {h} | Apuesta: ${h.bet}")

            return "split"

        # DOUBLE
        elif action == "double":
            self._log_to_file(f"--> DOUBLE")
            old_bet = hand.bet
            hand.bet *= 2
            self.estadisticas.registrar_apuesta(old_bet)  # registrar solo el incremento
            card_dealt = self.deal_one_card(player_idx, hand_idx)
            self._log_to_file(f"-> Recibe carta (double): {card_dealt}")
            self.estadisticas.registrar_evento("double")
            hand.status = "stand"  # en double: 1 carta y planta

            self._log_to_file(f"DESPUÉS DE DOUBLE:")
            self._log_to_file(f"- Cartas: {hand}")
            self._log_to_file(f"- Nueva apuesta: ${hand.bet}")
            return "double"

        # HIT
        elif action == "hit":
            self._log_to_file(f"--> HIT")
            card_dealt = self.deal_one_card(player_idx, hand_idx)
            self._log_to_file(f"-> Recibe carta: {card_dealt}")
            self._log_to_file(f"DESPUÉS DE HIT: {hand}")
            return "hit"

        # STAND
        elif action == "stand":
            self._log_to_file(f"--> STAND")
            hand.status = "stand"
            self._log_to_file(f"Jugador se PLANTA con {hand.best_value()} puntos")
            return "stand"

        # Fallback
        else:
            self._log_to_file(f"--> STAND (fallback)")
            hand.status = "stand"
            return "stand"

    def deal_initial_cards_and_log(self):
        self._log_to_file("\nREPARTO INICIAL:")
        
        # Primera ronda de cartas
        for i in range(self.num_players):
            card = self.deal_one_card(i)
            self._log_to_file(f"Jugador {i+1} recibe: {card}")
        
        dealer_card = self.deal_one_card("dealer")
        self._log_to_file(f"Dealer recibe: {dealer_card} (visible)")
        
        # Segunda ronda de cartas
        for i in range(self.num_players):
            card = self.deal_one_card(i)
            self._log_to_file(f"Jugador {i+1} recibe: {card}")
        
        dealer_card = self.deal_one_card("dealer")
        self._log_to_file(f"Dealer recibe carta oculta")

        # Registrar estado final
        self._log_to_file("\nMANOS INICIALES:")
        for i, player_hands in enumerate(self.players):
            for hand_idx, hand in enumerate(player_hands):
                self._log_to_file(f"Jugador {i+1}, Mano {hand_idx+1}: {hand} | Apuesta: ${hand.bet}")
        
        self._log_to_file(f"Dealer: {[str(c) for c in self.dealer_hand.cards]} | Carta visible: {self.dealer_hand.cards[0]}")

    def play_dealer_turn(self):
        self._log_to_file("\nTURNO DEL DEALER")
        self._log_to_file(f"Mano inicial: {[str(c) for c in self.dealer_hand.cards]} (Valor: {self.dealer_hand.best_value()})")
        
        if self.dealer_hand.status != "blackjack" and self.dealer_hand.status != "bust":
            while self.dealer_hand.best_value() < 17:
                card = self.deal_one_card("dealer")
                self._log_to_file(f"Dealer recibe carta: {card}")
                self._log_to_file(f"Nueva mano: {[str(c) for c in self.dealer_hand.cards]} (Valor: {self.dealer_hand.best_value()})")
            
            if self.dealer_hand.best_value() > 21:
                self.dealer_hand.status = "bust"
                self._log_to_file(f"El Dealer se pasó! Valor: {self.dealer_hand.best_value()}")
            else:
                self.dealer_hand.status = "stand"
                self._log_to_file(f"El Dealer se planta con un valor de: {self.dealer_hand.best_value()}")
        elif self.dealer_hand.status == "blackjack":
            self._log_to_file(f"El Dealer tiene BLACKJACK con un valor de: {self.dealer_hand.best_value()}")
        elif self.dealer_hand.status == "bust":
            self._log_to_file(f"El Dealer ya se había pasado con un valor de: {self.dealer_hand.best_value()}")

    def play_round(self, estrategias=None):
        if self.seed:
            random.seed(self.seed)

        if estrategias is None:
            if self.estrategias is not None:
                estrategias_para_jugadores = self.estrategias
            else:
                print("Advertencia: No se proporcionó ninguna estrategia, se usará la predeterminada.")
                estrategias_para_jugadores = [BLACKJACK_STRATEGIES['nunca_se_pasa']] * self.num_players
        elif isinstance(estrategias, dict):
            estrategias_para_jugadores = [estrategias] * self.num_players
        elif isinstance(estrategias, list) and len(estrategias) == self.num_players:
            estrategias_para_jugadores = estrategias
        else:
            print("Advertencia: El formato de estrategias no es válido. Se usará la estrategia predeterminada.")
            estrategias_para_jugadores = [BLACKJACK_STRATEGIES['nunca_se_pasa']] * self.num_players

        self.prepare_game()
        self.deal_initial_cards_and_log()

        for i in range(self.num_players):
            hand_idx = 0
            while hand_idx < len(self.players[i]):
                hand = self.players[i][hand_idx]
                player_strategy = estrategias_para_jugadores[i]

                if self.offer_insurance() and hand.insurance == 0 and player_strategy.get('seguro', True):
                    if random.random() < 0.7:
                        max_insurance = hand.bet // 2
                        insurance_bet = max_insurance
                        self.take_insurance(i, hand_idx, insurance_bet)

                if hand.status == "active":
                    action = self.play_player_action(i, hand_idx, player_strategy)

                    if action in ["double", "stand", "finished"]:
                        hand_idx += 1
                    elif action == "split":
                        pass
                    elif action == "hit":
                        pass
                    else:
                        hand_idx += 1
                else:
                    hand_idx += 1
        
        self.play_dealer_turn()
        self.evaluate_results()
        return self.estadisticas.ganancia_mano_actual

    def evaluate_results(self):
        self._log_to_file("\n--- EVALUANDO RESULTADOS ---")
        dealer_value = self.dealer_hand.best_value()
        dealer_is_bust = self.dealer_hand.status == "bust"
        dealer_blackjack = self.dealer_hand.status == "blackjack"

        ganancia_mano_actual = 0.0
        resultados = []         

        for i in range(self.num_players):
            player_results = []

            if dealer_blackjack:
                for hand in self.players[i]:
                    resultado_mano = 0.0

                    # Seguro paga 2:1 si dealer tiene BJ
                    if hand.insurance > 0:
                        self._log_to_file(f"SEGURO APOSTADO por jugador {i+1}: ${hand.insurance}")
                        resultado_mano += hand.insurance * 2
                        self._log_to_file(f"-> Gana SEGURO: +${(hand.insurance * 2):.2f}")

                        if hasattr(self.estadisticas, "registrar_seguro_cobrado"):
                            self.estadisticas.registrar_seguro_cobrado(hand.insurance * 2)

                    if hand.status == "blackjack":
                        # REGLA: BJ vs BJ paga 50% al jugador
                        ganado = hand.bet * 0.5
                        resultado_mano += ganado
                        self._log_to_file(f"Jugador {i+1} BLACKJACK vs Dealer BLACKJACK. Paga 50%: +${ganado:.2f}")
                    else:
                        # Pierde la apuesta principal
                        resultado_mano -= hand.bet
                        self._log_to_file(f"Jugador {i+1} sin BJ vs Dealer BLACKJACK. Pierde: -${hand.bet:.2f}")

                    if resultado_mano > 0:
                        self.estadisticas.registrar_evento("perdida")
                    elif resultado_mano < 0:
                        self.estadisticas.registrar_evento("ganada")
                    else:                        
                        self.estadisticas.registrar_evento("empatada")
                    player_results.append(resultado_mano)
                    ganancia_mano_actual += -resultado_mano

            else:
                for hand in self.players[i]:
                    hand_value = hand.best_value()
                    hand_is_bust = hand.status == "bust"
                    hand_is_blackjack = hand.status == "blackjack"

                    resultado_mano = 0.0

                    if hand.insurance > 0:
                        resultado_mano -= hand.insurance
                        self._log_to_file(f"Jugador {i+1} vs Dealer {dealer_value} (no BJ). Pierde seguro: -${hand.insurance:.2f}")
                        if hasattr(self.estadisticas, "registrar_seguro_perdido"):
                            self.estadisticas.registrar_seguro_perdido(hand.insurance)

                    if hand_is_bust:
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} se pasa. Pierde: -${hand.bet:.2f}")
                        resultado_mano -= hand.bet
                    elif hand_is_blackjack:
                        ganado = hand.bet * self.blackjack_payout_rate
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} BLACKJACK! Gana: +${ganado:.2f}")
                        resultado_mano += ganado
                        if hand.insurance > 0:
                            self._log_to_file(
                                f"Jugador {i+1}, BLACKJACK: Pago BJ +${resultado_mano:.2f}   | Seguro perdido -${hand.insurance:.2f}  | Neto ${resultado_mano:.2f}"
                            )
                        else:
                            self._log_to_file(f"Jugador {i+1}, BLACKJACK: Gana +${resultado_mano:.2f}")

                    elif dealer_is_bust:
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} vs Dealer {dealer_value} (bust). Gana: +${hand.bet:.2f}")
                        resultado_mano += hand.bet
                    elif hand_value > dealer_value:
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} > Dealer {dealer_value}. Gana: +${hand.bet:.2f}")
                        resultado_mano += hand.bet
                    elif hand_value < dealer_value:
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} < Dealer {dealer_value}. Pierde: -${hand.bet:.2f}")
                        resultado_mano -= hand.bet
                    else:
                        self._log_to_file(f"Jugador {i+1}, Mano {hand.best_value()} == Dealer {dealer_value}. Push.")

                    # <<< CLASIFICACIÓN CORRECTA (perspectiva casino) >>>
                    if resultado_mano > 0:
                        self.estadisticas.registrar_evento("perdida")   # ganó el jugador
                    elif resultado_mano < 0:
                        self.estadisticas.registrar_evento("ganada")    # ganó el casino
                    else:
                        self.estadisticas.registrar_evento("empatada")

                    player_results.append(resultado_mano)
                    ganancia_mano_actual += -resultado_mano
                    

            resultados.append(player_results)

        self.estadisticas.ganancias_casino += ganancia_mano_actual
        self.total_dinero_jugado += self.estadisticas.dinero_en_juego_mano_actual
        #self.estadisticas.registrar_ganancia_mano_actual(ganancia_mano_actual)
        self.total_ganancia_banca += ganancia_mano_actual
        
        self.estadisticas.dinero_en_juego += self.estadisticas.dinero_en_juego_mano_actual

        self._log_to_file("\nRESUMEN FINANCIERO:")
        self._log_to_file(f"Dinero jugado en esta mano: ${self.estadisticas.dinero_en_juego_mano_actual:.2f}")
        self._log_to_file(f"Dinero total acumulado: ${self.total_dinero_jugado:.2f}")
        self._log_to_file(f"Ganancia banca en esta mano: ${ganancia_mano_actual:.2f}")
        self._log_to_file(f"Ganancia banca acumulada: ${self.total_ganancia_banca:.2f}")

        if self.total_dinero_jugado > 0:
            porcentaje_ganancia = (self.total_ganancia_banca / self.total_dinero_jugado) * 100
            self._log_to_file(f"Porcentaje de ganancia acumulado: {porcentaje_ganancia:.4f}%")

        self._log_to_file("\nRESULTADOS POR JUGADOR:")
        for i in range(self.num_players):
            for hand_idx, hand in enumerate(self.players[i]):
                resultado = resultados[i][hand_idx]
                self._log_to_file(f"Jugador {i+1}, Mano {hand_idx+1}: Resultado ${resultado:.2f}")

        
        self.writing_log = True

        self.last_resultados = resultados

        return resultados



    def offer_insurance(self):
        return self.dealer_hand.cards and self.dealer_hand.cards[0].get_blackjack_value() == 11
    
    def take_insurance(self, player_idx, hand_idx, amount):
        if player_idx in self.jugadores_asegurados_round:
            self._log_to_file(f"Jugador {player_idx + 1} intentó apostar SEGURO nuevamente y se bloqueó porque ya lo había apostado")

            return False
        
        hand = self.players[player_idx][hand_idx]
        required_insurance = hand.bet // 2
        if amount == required_insurance:
            hand.insurance = amount
            self.estadisticas.registrar_apuesta(amount)
            self.jugadores_asegurados_round.add(player_idx)
            self._log_to_file(f"Jugador {player_idx+1} compra SEGURO por ${amount}")

            if hasattr(self.estadisticas, "registrar_seguro_apostado"):
                self.estadisticas.registrar_seguro_apostado(amount)
            return True
        return False
    

    ## METODO PARA DEBUGEAR

    def log_resumen_mano(self, sabot_num, writing):
        return