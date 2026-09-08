# games/craps/simuladores/simulador_estadistico_craps.py

import pygame
import time
import random

from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE
from utils.paths import FONT_PATH, resource_path
from core.base_state import BaseState
from core.global_state import state_manager

from games.craps.eventos.bus_eventos import BridgeEventosCraps
from games.craps.motor.motor_craps import MotorCraps  # motor de craps
from games.craps.estadisticas.craps_stats_masivo import EstadisticasCrapsMasivo # Estadisticas y contadores


CHIPS_VALUE = [0.5, 1, 5, 10, 50, 100]
CHIP_SIZE = 40

# Posiciones fijas para fichas por jugador (mantengo tu mapeo)
FICHA_POSICIONES = {
    1: {"buena": (50, 100), "mala": (150, 100)},
    2: {"buena": (50, 200), "mala": (150, 200)},
    3: {"buena": (50, 300), "mala": (150, 300)},
    4: {"buena": (50, 400), "mala": (150, 400)},
    5: {"buena": (200, 600), "mala": (200, 500)},
    6: {"buena": (300, 600), "mala": (300, 500)},
    7: {"buena": (400, 600), "mala": (400, 500)},
    8: {"buena": (500, 600), "mala": (500, 500)},
}


class SimuladorEstadistico(BaseState):
    def __init__(self):
        super().__init__()
        self.font = pygame.font.Font(FONT_PATH, 22)
        self.font_big = pygame.font.Font(FONT_PATH, 48)
        self.font_small = pygame.font.Font(FONT_PATH, 16)

        # background tile (si falla, no romper)
        try:
            self.background_tile = pygame.image.load(resource_path("assets/images/table_pattern.png")).convert()
        except Exception:
            self.background_tile = pygame.Surface((64, 64))
            self.background_tile.fill((12, 75, 12))
        self.background_surface = self.create_tiled_background()

        ## SISTEMA REAL: stats + motor + bridge
        self.stats = EstadisticasCrapsMasivo()
        self.motor = MotorCraps()
        # Asegurar atributo boton_on (por si motor no lo inicializó)
        if not hasattr(self.motor, "boton_on"):
            self.motor.boton_on = False
        self.bridge = BridgeEventosCraps(self.stats)

        # Suscribir bridge a eventos para que stats reciba los hooks
        for evt in ["NUEVO_TIRADOR","APUESTA_COLOCADA","TIRO_INICIADO","PUNTO_FIJADO","APUESTA_RESUELTA","PUNTO_LIBRE"]:
            try:
                self.motor.suscribir(evt, self.bridge)
            except Exception:
                pass  # si no funciona, igual seguimos usando motor.emitir/bus

        # Estado UI / simulación
        self.pase_actual = 1
        self.resultado_dados = None         # tupla (d1,d2,suma)
        self.punto = None
        self.ultimo_motivo = ""
        self.fin_de_pase = False

        # parámetros de simulador gráfico
        self.p_buena = 0.7  # probabilidad para elegir tirador/apuesta por defecto
        self.min_linea = 5000
        self.max_linea = 200000

        # Duración en pantalla para mostrar la última tirada (segundos)
        self.show_roll_duration = 0.9
        self.last_roll_time = 0.0

        # Estado del flujo: MOSTRAR_APUESTAS -> TIRO -> (si punto fijado) TIRO_ON -> FIN (vuelve a MOSTRAR_APUESTAS)
        self.estado = "MOSTRAR_APUESTAS"
        self.tiempo_estado = time.time()

        self.reset_round()

    def create_tiled_background(self):
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        tile_w, tile_h = self.background_tile.get_size()
        for y in range(0, SCREEN_HEIGHT, tile_h):
            for x in range(0, SCREEN_WIDTH, tile_w):
                bg.blit(self.background_tile, (x, y))
        return bg

    def enviar_evento_motor(self, tipo, **data):
        evento = {"tipo": tipo, "data": data}
        # Intentar usar bus callable (registra observadores)
        try:
            self.motor.bus(evento)
        except Exception:
            try:
                self.motor.emitir(tipo, **data)
            except Exception:
                pass

    def reset_round(self):
        # crea entre 1 y 8 jugadores con apuestas/flags aleatorios
        self.num_jugadores = random.randint(1, 8)
        self.jugadores = []

        for i in range(self.num_jugadores):
            jugador = {
                "id": i + 1,
                "linea": random.choice(["buena", "mala"]),
                # '5' -> 5000 (lo multiplicamos por 1000 al colocar)
                "apuesta_linea": random.choice([5, 10, 50]),
                "enganche": random.choice(["on", "off"]),
                "field": random.choice(["on", "off"]),
                "camuninas": "off",
                "cuadros": "off"
            }
            self.jugadores.append(jugador)

        # no modificar stats aquí
        self.resultado_dados = None
        self.punto = None
        self.fin_de_pase = False

    # ---------- Helpers que usan internals del motor ----------
    def _resolver_off(self, suma: int) -> bool:

        print("\n\n E N T R A N D O   A   R E S O L V E R   O F F")

        """
        Resuelve un tiro en fase OFF. Devuelve True si el pase termina.
        Llama a los internals del motor para mantener exactamente la misma lógica que el masivo.
        """
        # tirador actual y su apuesta (según motor)
        apuesta_tirador = getattr(self.motor, "tirador_apuesta", None)

        # Come-out rules (mismos motivos que en MotorCraps)
        if suma in (7, 11):
            # Buena gana en come-out -> motivo "come-out 7/11"
            try:
                self.motor._resolver_linea_final("come-out 7/11", buena_gana=True)
                print(f"\n\nGANA BUENA CON EL {suma}")
            except Exception:
                self.enviar_evento_motor("APUESTA_RESUELTA", resultado="GANA", pago=apuesta_tirador, motivo="come-out 7/11", tipo_apuesta="Buena")
                print(f"\n\nGANA BUENA CON EL {suma} desde el Exception")
            try:
                self.motor._rotacion_por_resultado_en_off("Buena")
                print(f"\n\nSe ejecutó rotacion por resultado en off")
            except Exception:
                pass
            try:
                self.motor._fin_pase()
                print(f"\n\nSe ejecutó fin pase")
            except Exception:
                pass

            return True

        elif suma in (2, 3):
            # Buena pierde, Mala gana -> motivo "come-out 2/3"
            try:
                self.motor._resolver_linea_final("come-out 2/3", buena_gana=False)
                print(f"\n\nPIERDE BUENA CON EL {suma}")
            except Exception:
                self.enviar_evento_motor("APUESTA_RESUELTA", resultado="PIERDE", pago=0, motivo="come-out 2/3", tipo_apuesta="Buena")
                print(f"\n\nPIERDE BUENA CON EL {suma} desde el Exception")
            try:
                self.motor._rotacion_por_resultado_en_off("Mala")
                print(f"\n\nSe ejecutó rotacion por resultado en off DESDE MALA")
            except Exception:
                pass
            try:
                self.motor._fin_pase()
                print(f"\n\nSe ejecutó fin pase DESDE MALA")
            except Exception:
                pass

            return True

        elif suma == 12:
            # 12 = Buena pierde, Mala push (empate)
            try:
                self.motor._resolver_linea_final_12()
            except Exception:
                pass
            try:
                self.motor._rotacion_por_resultado_en_off("Empate12")
            except Exception:
                pass
            try:
                self.motor._fin_pase()
            except Exception:
                pass
            return True

        else:
            # Punto fijado (4,5,6,8,9,10)
            # Establecer punto y pasar a ON
            self.motor.punto = suma
            self.motor.boton_on = True
            try:
                self.motor.emitir("PUNTO_FIJADO", valor=suma)
            except Exception:
                self.enviar_evento_motor("PUNTO_FIJADO", valor=suma)
            return False

    def _resolver_on(self, suma: int) -> bool:
        """
        Resuelve tiro en fase ON. Devuelve True si el pase termina.
        """
        # si sale el punto -> Buena gana
        if suma == getattr(self.motor, "punto", None):
            try:
                self.motor._resolver_linea_punto_logrado()
            except Exception:
                pass
            try:
                self.motor._rotacion_por_resultado_en_on("Buena")
            except Exception:
                pass
            try:
                self.motor._fin_pase()
            except Exception:
                pass
            return True

        # if 7 -> seven-out
        if suma == 7:
            try:
                self.motor._resolver_linea_seven_out()
            except Exception:
                pass
            try:
                self.motor._rotacion_por_resultado_en_on("Mala")
            except Exception:
                pass
            try:
                self.motor._fin_pase()
            except Exception:
                pass
            return True

        return False

    # ---------- Lógica del ciclo (update) ----------
    def update(self, dt):
        ahora = time.time()

        # Mostrar apuestas -> iniciar pase y colocar apuestas reales en motor
        if self.estado == "MOSTRAR_APUESTAS":
            if ahora - self.tiempo_estado > 1.0:
                # iniciar pase en motor (publica NUEVO_TIRADOR)
                try:
                    self.motor._inicio_pase(self.p_buena)
                except TypeError:
                    try:
                        self.motor._inicio_pase()
                    except Exception:
                        pass
                except Exception:
                    pass

                # colocar apuestas en motor (montos reales)
                for j in self.jugadores:
                    monto = int(j["apuesta_linea"] * 1000)  # ej: 5 -> 5000
                    tipo = "Buena" if j["linea"] == "buena" else "Mala"
                    try:
                        self.motor.colocar_apuesta(j["id"], tipo, monto)
                    except Exception:
                        # fallback emitir al bus
                        self.enviar_evento_motor("APUESTA_COLOCADA",
                                                 id_jugador=j["id"],
                                                 tipo_apuesta=tipo,
                                                 monto=monto,
                                                 id_apuesta=None)

                # ahora tirador viene definido por motor (tirador_id, tirador_apuesta, tirador_vidas)
                # cambiar estado para comenzar a tirar en OFF
                self.estado = "TIRO"
                self.tiempo_estado = ahora
                # limpiar resultado actual para que la UI muestre próximas tiradas
                self.resultado_dados = None
                self.last_roll_time = 0.0

        # TIRO: tiradas secuenciales. Dependiendo de motor.boton_on resolvemos OFF/ON.
        elif self.estado == "TIRO":
            if ahora - self.tiempo_estado > 0.6:
                # tirar dados
                try:
                    d1, d2, suma, es_doble = self.motor.tirar_dados()
                except Exception:
                    d1, d2 = random.randint(1,6), random.randint(1,6)
                    suma = d1 + d2
                    es_doble = (d1 == d2)
                    # emitir fallback
                    self.enviar_evento_motor("TIRO_INICIADO", d1=d1, d2=d2, suma=suma, es_doble=es_doble)

                # registrar la tirada para mostrar en UI
                self.resultado_dados = (d1, d2, suma)
                self.last_roll_time = ahora

                # resolver según fase actual del motor
                boton_on = getattr(self.motor, "boton_on", False)

                if not boton_on:
                    cerrar = self._resolver_off(suma)
                else:
                    cerrar = self._resolver_on(suma)

                # si se cerró el pase - dejamos la última tirada visible unos instantes y luego cambiamos a MOSTRAR_APUESTAS
                if cerrar:
                    # Emitir PUNTO_LIBRE ya lo hace motor._fin_pase()
                    # aumentar pase local (stats ya lo hace también)
                    # Mantener la tirada visible por show_roll_duration
                    self.fin_de_pase = True
                    self.tiempo_estado = ahora
                    # no resetear inmediatamente; esperar a que pase la duración de visualización
                else:
                    # continuidad en el pase: seguimos tirando luego del delay
                    self.tiempo_estado = ahora

        # Si estamos en fin de pase y queremos esperar para mostrar la última tirada un momento
        if self.fin_de_pase:
            # dejar la tirada visible show_roll_duration segundos y luego reiniciar para el siguiente pase
            if ahora - self.tiempo_estado > self.show_roll_duration:
                self.fin_de_pase = False
                self.estado = "MOSTRAR_APUESTAS"
                self.tiempo_estado = ahora
                # reset gráfico del pase (no tocar stats)
                self.resultado_dados = None
                # Pedimos al motor que prepare un nuevo tirador en el próximo inicio (rotación ya se hizo internamente)
                # no ejecutamos motor._rotar_tirador() aquí porque el motor ya rotó internamente en las funciones anteriores

    def on_evento_motor(self, evento):
        # Registro opcional si quieres que la UI sea observador del bus
        tipo = evento.get("tipo")
        data = evento.get("data")
        print(f"[EVENTO UI] {tipo}: {data}")

    # ---------- Render ----------
    def render(self, screen):
        screen.blit(self.background_surface, (0, 0))

        # Títulos
        title = self.font.render("Craps - Simulación gráfica", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        # Resumen desde stats (estas cifras vienen de EstadisticasCrapsMasivo)
        estado_stats = self.stats.resumen_estado_actual()
        # Pase actual lo muestra stats (pases_simulados + 1)
        pase_text = self.font_small.render(f"PASE: {estado_stats['pase_actual']}", True, WHITE)
        dinero_text = self.font_small.render(f"Dinero en juego: ${estado_stats['dinero_en_juego']:,.0f}", True, WHITE)
        ganancia_text = self.font_small.render(f"Ganancia casino: ${estado_stats['ganancias_casino']:,.0f}", True, WHITE)
        pct_text = self.font_small.render(f"% Ganancia: {estado_stats['porcentaje_ganancia']}%", True, WHITE)

        screen.blit(pase_text, (SCREEN_WIDTH - 500, 60))
        screen.blit(dinero_text, (SCREEN_WIDTH - 500, 100))
        screen.blit(ganancia_text, (SCREEN_WIDTH - 500, 140))
        screen.blit(pct_text, (SCREEN_WIDTH - 500, 180))

        # Mostrar tirador actual en el centro cuando comienza el pase o mientras está en OFF
        tirador_id = getattr(self.motor, "tirador_id", None)
        tirador_apuesta = getattr(self.motor, "tirador_apuesta", None)
        tiros_restantes = getattr(self.motor, "tirador_vidas", None)
        contabiliza = getattr(self.motor, "tirador_tiene_vidas", None)

        centro_x = SCREEN_WIDTH // 2
        centro_y = SCREEN_HEIGHT // 2 - 80

        # Si estamos en MOSTRAR_APUESTAS o en OFF y no hay punto, mostrar tirador
        mostrar_tirador = (self.estado == "MOSTRAR_APUESTAS") or (not getattr(self.motor, "boton_on", False))
        if tirador_id is not None and mostrar_tirador:
            text = f"Tirador: {tirador_id}   Apuesta: {tirador_apuesta}   Vidas: {tiros_restantes if contabiliza else '∞'}"
            t = self.font_big.render(text, True, WHITE)
            screen.blit(t, (centro_x - t.get_width() // 2, centro_y - t.get_height() // 2))

        # Mostrar Punto cuando está fijado
        if getattr(self.motor, "boton_on", False):
            punto = getattr(self.motor, "punto", None)
            if punto:
                text_punto = f"El punto a buscar es: {punto}"
                tp = self.font_big.render(text_punto, True, WHITE)
                screen.blit(tp, (centro_x - tp.get_width() // 2, centro_y - tp.get_height() // 2))

        # Dibujar las fichas de los jugadores (solo representación)
        for jugador in self.jugadores:
            pos_map = FICHA_POSICIONES.get(jugador["id"], {"buena": (40, 120), "mala": (140,120)})
            ficha_pos = pos_map[jugador["linea"]]
            pygame.draw.circle(screen, (200, 60, 60), ficha_pos, CHIP_SIZE // 2)
            texto = self.font_small.render(str(jugador["apuesta_linea"] * 1000), True, WHITE)
            screen.blit(texto, (ficha_pos[0] - 10, ficha_pos[1] - 8))

        # Mostrar resultado de dados si hay (mantener visible por show_roll_duration)
        if self.resultado_dados:
            d1, d2, suma = self.resultado_dados
            resultado_texto = self.font_big.render(f"{d1} + {d2} = {suma}", True, WHITE)
            screen.blit(resultado_texto, (centro_x - resultado_texto.get_width() // 2, SCREEN_HEIGHT // 2))

        # Mostrar último motivo/estado pequeño
        small_info = f"Estado UI: {self.estado}"
        small_surface = self.font_small.render(small_info, True, WHITE)
        screen.blit(small_surface, (24, SCREEN_HEIGHT - 40))
