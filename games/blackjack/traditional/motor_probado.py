

# games/blackjack/traditional/motor_probado.py

import random, time
from games.blackjack.traditional.statistics.blackjack_stats import EstadisticasCasino

# Diccionario de estrategias
BLACKJACK_STRATEGIES = {
    'nunca_se_pasa': {
        'tipo': 'nunca_se_pasa',
        'apertura_pares': False,
        'apertura_ases': True,
        'duplica': True,
        'seguro': True
    },
    'arriesgado_1': {
        'tipo': 'arriesgado_1',
        'apertura_pares': True,
        'apertura_ases': True,
        'duplica': True,
        'seguro': False
    },
    'arriesgado_2': {
        'tipo': 'arriesgado_2',
        'apertura_pares': True,
        'apertura_ases': True,
        'duplica': True,
        'seguro': False
    },
    'arriesgado_3': {
        'tipo': 'arriesgado_3',
        'apertura_pares': False,
        'apertura_ases': True,
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
    def __init__(self, is_split=False, bet=3000, motor=None):
        self.cards = []        
        self.status = "active"
        self.bet = bet
        self.insurance = 0
        self.motor = motor
        self.doubled = False
        self.is_split = is_split
        self.is_split_ace = False
        self.is_split_ten = False
        self.is_first_split_hand = False

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
        if self.is_split:
            return False
        if len(self.cards) != 2:
            return False
        total = sum(c.get_blackjack_value() for c in self.cards)
        return total in (10, 11)

    def can_split(self):
        if len(self.cards) != 2:
            return False
        
        val1 = self.cards[0].get_blackjack_value()
        val2 = self.cards[1].get_blackjack_value()
        
        return val1 == val2

class Deck:
    def __init__(self, num_decks=8, seed=None):
        if seed:
            random.seed(seed)
        self.cards = []
        suits = ['C', 'P', 'D', 'T']
        for _ in range(num_decks):
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
    def __init__(self, num_players=1, num_decks=8, estadisticas=None, estrategias=None, log_file=None, seed=None):
        self.num_players = num_players
        self.num_decks = num_decks
        self.seed = seed
        self.sabot_count = 1
        self.ultimo_sabot = False
        self.deck = Deck(self.num_decks, seed=self.seed)
        self.players = []
        self.dealer_hand = Hand()
        self.estadisticas = estadisticas if estadisticas else EstadisticasCasino()
        self.estrategias = estrategias
        self.apuesta_minima = 3000
        self.apuestas_por_jugador = None
        self.seguro_tomado_jugador = [False] * self.num_players
        self.blackjack_payout_rate = 1.5
        self.log_file = log_file
        self.round_number = 0
        self.total_ganancia_banca = 0.0
        self.total_dinero_jugado = 0.0
        self._initialize_players()
        self._log_deck_state_to_file("Iniciando nueva simulación...", self.deck.initial_deck_state)
        
    def _log_to_file(self, message):
        # No-op: sin I/O
        return

    def _format_card_list(self, cards_list):
        return [str(card) for card in cards_list]

    def _log_special_case_to_file(self, message):
        # No-op: sin I/O
        return
    
    def _log_deck_state_to_file(self, message, cards=None):
        return

    def _initialize_players(self):        
        self.players = [[Hand(bet=self.apuesta_minima, motor=self)] for _ in range(self.num_players)]

    def _min_cards_threshold(self):
        # Cálculo 
        #return self.num_players * 8 # 56 cartas de corte para 7 jugadores  
        return 60
    
    def prepare_game(self):
        self.seguro_tomado_jugador = [False] * self.num_players
        self.round_number += 1
        self.estadisticas.total_manos += 1
        self._log_to_file("---")
        self._log_to_file(f"** Mano N° {self.estadisticas.total_manos} **")
        self._log_to_file(f"Dinero total en juego ANTES de la mano: {self.estadisticas.dinero_en_juego}")        

        if self.ultimo_sabot:
            self.deck = Deck(self.num_decks, seed=self.seed) # Regenerar con la misma semilla si es necesario
            self.sabot_count += 1
            self._log_to_file("Mazo barajado.")
            self._log_deck_state_to_file("Mazo barajado. Lista completa de cartas:", self.deck.get_all_cards_as_string_list())
            self.ultimo_sabot = False

        self.estadisticas.ganancia_mano_actual = 0.0
        self.estadisticas.dinero_en_juego_mano_actual = 0

        # Verificar si este será el último sabot
        if self.deck.get_remaining_cards() < self._min_cards_threshold():
            self._log_to_file("ADVERTENCIA: Este es el último sabot antes de barajar")
            self.ultimo_sabot = True

        self.players = [[Hand(bet=self.apuesta_minima, motor=self)] for _ in range(self.num_players)]
        
        if self.apuestas_por_jugador and len(self.apuestas_por_jugador) == self.num_players:
            for i in range(self.num_players):
                self.players[i][0].bet = int(self.apuestas_por_jugador[i])

        for i in range(self.num_players):
            self.estadisticas.registrar_apuesta(self.players[i][0].bet)
        
        
        self.dealer_hand = Hand(bet=0, motor=self)
        self.dealer_hand.status = "active"        
        
        
        self._log_to_file(f"Apuesta inicial por jugador: {self.apuesta_minima}")

        try:
            flags = []
            for i, strat in enumerate(self.estrategias[:self.num_players], 1):
                flags.append(f"J{i}: dup={strat.get('duplica')}, apr={strat.get('apertura_pares')}, ases={strat.get('apertura_ases')}, seg={strat.get('seguro')}, tipo={strat.get('tipo')}")
            self._log_to_file("Estrategias mano: " + " | ".join(flags))
        except Exception:
            pass


    def deal_one_card(self, recipient, hand_idx=0):
        try:
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

        # 1) SPLIT (solo si está ON)
        puede_split = (len(self.players[player_idx]) == 1 and hand.can_split())
        if puede_split:
            is_ace_pair = (hand.cards[0].value == 1 and hand.cards[1].value == 1)
            is_ten_pair = (hand.cards[0].get_blackjack_value() == 10 and hand.cards[1].get_blackjack_value() == 10)
            if is_ace_pair and strategy.get('apertura_ases', True):
                self._log_to_file("Acción: split (par de Ases)")
                return "split"
            elif strategy.get('apertura_pares', False):
                self._log_to_file("Acción: split (par no Ases)")
                return "split"

        # 2) DOUBLE (solo si está ON)
        if strategy.get('duplica', False) and hand.can_double():
            self._log_to_file("Acción: double")
            return "double"

        # 3) REGLAS UNIVERSALES (igual que en el motor NUEVO)
        player_value = hand.best_value()
        if player_value <= 11:
            self._log_to_file("Acción: hit (valor <= 11)")
            return "hit"
        if player_value >= 17 and not hand.is_soft_hand():
            self._log_to_file("Acción: stand (mano dura >= 17)")
            return "stand"
        if hand.is_soft_hand():
            if player_value < 17:
                self._log_to_file("Acción: hit (mano soft)")
                return "hit"
            else:
                self._log_to_file("Acción: stand (mano soft >= 17)")
                return "stand"

        # 4) Matiz por tipo (si NO es 'nunca_se_pasa')
        t = strategy.get('tipo', 'nunca_se_pasa')
        dealer_val = self.dealer_hand.cards[0].get_blackjack_value() if self.dealer_hand.cards else 10
        if t == 'arriesgado_1':
            return "stand" if dealer_val in (4,5,6) else "hit"
        elif t == 'arriesgado_2':
            return "stand" if dealer_val in (2,3,4,5,6) else "hit"
        elif t == 'arriesgado_3':
            return "stand"

        return "stand"




    
    def play_player_action(self, player_idx, hand_idx, strategy):
        hand = self.players[player_idx][hand_idx]        
        if hand.status != "active":
            return "finished"
        
        # PRE-PASO para manos de split que aún tengan 1 carta:
        if hand.is_split and len(hand.cards) == 1:
            card = self.deal_one_card(player_idx, hand_idx)  # carta obligatoria
            self._log_to_file(f"-> Carta obligatoria post-split: {card}")

            # Si es split de Ases: una carta y listo (se planta)
            if hand.is_split_ace:
                # Si esa carta vale 10 es Blackjack (paga 150%)
                if card.get_blackjack_value() == 10:
                    hand.status = "blackjack"
                else:
                    hand.status = "stand"
                return "stand"

            # Si es split de 10/10: si la carta obligatoria es As, contar como Blackjack
            if hand.is_split_ten and card.get_blackjack_value() == 11:
                hand.status = "blackjack"
                return "stand"  # ya no sigue pidiendo

            # Para splits que no son Ases: luego de la carta obligatoria, sigue jugando normalmente
            # (NO se puede duplicar como en el blackjack nuevo)
            

        action = self.get_player_action(hand, strategy, player_idx, hand_idx)
        self._log_to_file(
            f"Jugador {player_idx+1}, Mano {hand_idx+1} | Valor: {hand.best_value()} | "
            f"Cartas: {[str(c) for c in hand.cards]} | Acción: {action}"
        )

        if action == "split":
            c1, c2 = hand.cards[0], hand.cards[1]
            new1 = Hand(is_split=True, bet=hand.bet, motor=self)
            new2 = Hand(is_split=True, bet=hand.bet, motor=self)
            new1.insurance = hand.insurance
            new2.insurance = 0
            new1.add_card(c1)
            new2.add_card(c2)

            # Marcar tipo de split
            if c1.value == 1 and c2.value == 1:
                new1.is_split_ace = True
                new2.is_split_ace = True
                self.estadisticas.registrar_evento("split_ases")
            elif c1.get_blackjack_value() == 10 and c2.get_blackjack_value() == 10:
                new1.is_split_ten = True
                new2.is_split_ten = True

            # Mano 1 y Mano 2
            new1.is_first_split_hand = True
            new2.is_first_split_hand = False

            # Reemplazar y registrar apuesta adicional por la segunda mano
            self.players[player_idx].pop(hand_idx)
            self.players[player_idx].insert(hand_idx, new1)
            self.players[player_idx].insert(hand_idx + 1, new2)
            self.estadisticas.registrar_apuesta(new2.bet)
            self.estadisticas.registrar_evento("split")
            return "split"

        elif action == "double":
            
            self.estadisticas.registrar_apuesta(hand.bet)  # registrar el incremento
            hand.bet *= 2
            hand.doubled = True
            card = self.deal_one_card(player_idx, hand_idx)
            self._log_to_file(f"-> Recibe carta (double): {card}")
            self.estadisticas.registrar_evento("double")
            hand.status = "stand"
            return "double"

        elif action == "hit":
            card = self.deal_one_card(player_idx, hand_idx)
            self._log_to_file(f"-> Recibe carta (hit): {card}")
            return "hit"

        elif action == "stand":
            hand.status = "stand"
            return "stand"

        # fallback
        hand.status = "stand"
        return "stand"
    
    def play_dealer_turn(self):
        self._log_to_file(f"Turno del Dealer | Carta visible: {self.dealer_hand.cards[0]} | Carta oculta: {self.dealer_hand.cards[1]}")
        
        if self.dealer_hand.status != "blackjack" and self.dealer_hand.status != "bust":
            while self.dealer_hand.best_value() < 17:
                self.deal_one_card("dealer")
            
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

    def deal_initial_cards_and_log(self):
        # Reparte 2 cartas a cada jugador + 2 al dealer (sin logs, sin listas intermedias)
        for _ in range(2):
            for i in range(self.num_players):
                self.deal_one_card(i)
            self.deal_one_card("dealer")

    def play_round(self, estrategias=None):
        if self.seed:
            random.seed(self.seed) # Asegura la reproducibilidad de la aleatoriedad

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

                if self.offer_insurance() and not self.seguro_tomado_jugador[i] and hand.insurance == 0:
                    if player_strategy.get('seguro', False): #Falso = no entra
                    # Lógica de seguro con aleatoriedad controlada por la semilla
                        if random.random() < 0.3:                        
                            self.take_insurance(i, hand_idx, hand.bet // 2)

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
        self._log_to_file("--- Evaluando resultados ---")
        dealer_value = self.dealer_hand.best_value()
        dealer_is_bust = self.dealer_hand.status == "bust"
        dealer_blackjack = self.dealer_hand.status == "blackjack"
        
        ganancia_mano_actual = 0.0
        resultados = []                
    
        for i in range(self.num_players):
            player_hands = self.players[i]
            player_results = []
    
            if dealer_blackjack:  
                # Paga seguro (2:1). Tras split, lo atamos a la 1ª mano (así lo propagamos).
                r_seguro = sum(h.insurance * 2 for h in player_hands) if any(h.insurance for h in player_hands) else 0.0
                if r_seguro > 0:
                    self.estadisticas.registrar_seguro_cobrado(r_seguro)

                if len(player_hands) == 1:
                    h = player_hands[0]
                    r = r_seguro
                    if h.status == "blackjack" and not h.is_split:
                        # BJ vs BJ = +50% para el jugador
                        r += h.bet * 0.5
                    else:
                        # Si duplicó: pierde la mitad del total (equivale a la apuesta original)
                        r -= (h.bet / 2.0) if h.doubled else h.bet

                    player_results.append(r)
                    ganancia_mano_actual += -r
                    # contadores desde la perspectiva del casino
                    if r > 0:  self.estadisticas.registrar_evento("perdida")
                    elif r < 0: self.estadisticas.registrar_evento("ganada")
                    else:       self.estadisticas.registrar_evento("empatada")

                else:
                    # Con split (exactamente 2 manos)
                    h1, h2 = player_hands[0], player_hands[1]
                    split_aces = (h1.is_split_ace and h2.is_split_ace)
                    split_tens = (h1.is_split_ten and h2.is_split_ten)
                    bj1 = (h1.status == "blackjack")
                    bj2 = (h2.status == "blackjack")

                    r1 = 0.0
                    r2 = 0.0

                    if not (split_aces or split_tens):
                        # reglas: split "otros" → pierde solo la mano1, mano2 push
                        r1 -= h1.bet
                        self._log_to_file(f"J{i+1} split 'otros' con Dealer BJ: mano1 -{h1.bet}, mano2 push")
                    else:
                        # split de Ases o dieces:
                        if not bj1 and not bj2:
                            r1 -= h1.bet
                            self._log_to_file(f"J{i+1} split A/10 sin BJ: mano1 -{h1.bet}, mano2 push")
                        elif (bj1 ^ bj2):
                            # un BJ en alguna → empata todo
                            self._log_to_file(f"J{i+1} split A/10 con un BJ: todo push")
                        else:
                            # dos BJ → mano1 cobra 150%, mano2 push
                            r1 += h1.bet * self.blackjack_payout_rate
                            self._log_to_file(f"J{i+1} split A/10 con dos BJ: mano1 +{h1.bet*self.blackjack_payout_rate:.2f}, mano2 push")

                    # el seguro lo aplicamos a la primera mano
                    r1 += r_seguro

                    player_results.extend([r1, r2])
                    ganancia_mano_actual += -(r1 + r2)
                    for r in (r1, r2):
                        if r > 0:  self.estadisticas.registrar_evento("perdida")
                        elif r < 0: self.estadisticas.registrar_evento("ganada")
                        else:       self.estadisticas.registrar_evento("empatada")

            else:
                # Flujo normal (sin BJ del dealer)
                for h in player_hands:
                    r = 0.0

                    if h.insurance > 0:
                        # seguro perdido
                        self.estadisticas.registrar_seguro_perdido(h.insurance)
                        r -= h.insurance
                        self._log_to_file(f"J{i+1} pierde seguro: -{h.insurance}")

                    if h.status == "bust":
                        r -= h.bet
                        self._log_to_file(f"J{i+1} bust: -{h.bet}")
                    elif h.status == "blackjack":
                        r += h.bet * self.blackjack_payout_rate
                        self._log_to_file(f"J{i+1} BJ: +{h.bet*self.blackjack_payout_rate:.2f}")
                    elif dealer_is_bust:
                        r += h.bet
                        self._log_to_file(f"J{i+1} gana vs dealer bust: +{h.bet}")
                    else:
                        hv = h.best_value()
                        if hv > dealer_value:
                            r += h.bet
                            self._log_to_file(f"J{i+1} {hv} > {dealer_value}: +{h.bet}")
                        elif hv < dealer_value:
                            r -= h.bet
                            self._log_to_file(f"J{i+1} {hv} < {dealer_value}: -{h.bet}")
                        else:
                            self._log_to_file(f"J{i+1} {hv} == {dealer_value}: push")

                    player_results.append(r)
                    ganancia_mano_actual += -r
                    if r > 0:  self.estadisticas.registrar_evento("perdida")
                    elif r < 0: self.estadisticas.registrar_evento("ganada")
                    else:       self.estadisticas.registrar_evento("empatada")

            resultados.append(player_results)

        self.estadisticas.ganancias_casino += ganancia_mano_actual
        self.total_dinero_jugado += self.estadisticas.dinero_en_juego_mano_actual
        self.total_ganancia_banca += ganancia_mano_actual
        self.estadisticas.dinero_en_juego += self.estadisticas.dinero_en_juego_mano_actual

        # (logs finales como los tenías…)
        return resultados

    def offer_insurance(self):
        return self.dealer_hand.cards and self.dealer_hand.cards[0].get_blackjack_value() == 11
    
    def take_insurance(self, player_idx, hand_idx, amount):
        if self.seguro_tomado_jugador[player_idx]:
            return False
        
        hand = self.players[player_idx][hand_idx]
        required_insurance = hand.bet // 2
        if amount == required_insurance:
            hand.insurance = amount
            self.estadisticas.registrar_apuesta(amount)
            self.estadisticas.registrar_seguro_apostado(amount)
            self.seguro_tomado_jugador[player_idx] = True
            return True
        return False