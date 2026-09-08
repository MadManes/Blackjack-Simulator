# tools/runner_debug_narrativo.py
from __future__ import annotations
import os, sys, random

# Asegurar imports tipo "from games.craps..." aunque ejecutes este archivo directo
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from games.craps.eventos.bus_eventos import BusEventos
from games.craps.estadisticas.craps_stats import EstadisticasCraps
from games.craps.debug.suscriptor_narrativo import (
    ActualizadorEstadisticas,
    SuscriptorEventosNarrativo,
)

# =========================
# Parámetros de simulación
# =========================
SEMILLA = None           # poné un int para reproducibilidad (p.ej. 12345)
NUM_PASES = 10           # cantidad de pases a simular
NUM_JUGADORES = 6        # jugadores en la mesa
P_BUENA = 0.7            # probabilidad de que un jugador elija Buena (sino Mala)
APUESTA_MIN = 5000
APUESTA_MAX = 150000
PASO_APUESTA = 500       # múltiplos de 500

def monto_aleatorio():
    base = random.randint(APUESTA_MIN // PASO_APUESTA, APUESTA_MAX // PASO_APUESTA)
    return base * PASO_APUESTA

def elegir_linea():
    return "Buena" if random.random() < P_BUENA else "Mala"

def tirar_dados():
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return d1, d2, d1 + d2, (d1 == d2)

def main():
    if SEMILLA is not None:
        random.seed(SEMILLA)

    # 1) Infraestructura
    bus = BusEventos()
    stats = EstadisticasCraps()
    actualizador = ActualizadorEstadisticas(stats)
    narrador = SuscriptorEventosNarrativo(stats, ruta_archivo="logs/craps/debug_narrativo.log")

    for evt in ["NUEVO_TIRADOR","APUESTA_COLOCADA","TIRO_INICIADO",
                "PUNTO_FIJADO","APUESTA_RESUELTA","PUNTO_LIBRE"]:
        bus.suscribir(evt, actualizador)
        bus.suscribir(evt, narrador)

    # Helpers para publicar
    def nuevo_tirador(id_tirador: int):
        bus.publicar("NUEVO_TIRADOR", id=id_tirador)

    def apostar(id_jugador: int, tipo: str, monto: int):
        bus.publicar("APUESTA_COLOCADA", id_jugador=id_jugador, tipo=tipo, monto=monto)

    def tiro(d1: int, d2: int):
        bus.publicar("TIRO_INICIADO", d1=d1, d2=d2, suma=d1+d2, es_doble=(d1==d2))

    def fijar_punto(p: int):
        bus.publicar("PUNTO_FIJADO", valor=p)

    def resolver(id_jugador: int, resultado: str, pago: int, motivo: str, tipo_linea: str):
        # resultado desde la perspectiva del jugador: "GANA" | "PIERDE" | "EMPATE"
        bus.publicar("APUESTA_RESUELTA",
                     id_jugador=id_jugador,
                     resultado=resultado,
                     pago=pago,
                     motivo=motivo,
                     tipo=tipo_linea)

    def cerrar_pase():
        bus.publicar("PUNTO_LIBRE")

    # =========================
    # Simulación de pases (Línea)
    # =========================
    tirador_actual = 1
    for pase in range(NUM_PASES):
        # Inicio del pase
        nuevo_tirador(tirador_actual)

        # Apuestas de línea (solo Buena/Mala)
        apuestas = []  # [(jugador, tipo, monto)]
        for j in range(1, NUM_JUGADORES + 1):
            tipo = elegir_linea()
            monto = monto_aleatorio()
            apuestas.append((j, tipo, monto))
            apostar(j, tipo, monto)

        # Fase 1 (Botón OFF) — primera tirada “come-out”
        d1, d2, suma, es_doble = tirar_dados()
        tiro(d1, d2)

        if suma in (7, 11):
            # Buena gana, Mala pierde
            for j, tipo, monto in apuestas:
                if tipo == "Buena":
                    resolver(j, "GANA", monto, "come-out 7/11", "Buena")
                else:
                    resolver(j, "PIERDE", monto, "come-out 7/11", "Mala")
            cerrar_pase()

        elif suma in (2, 3):
            # Buena pierde, Mala gana
            for j, tipo, monto in apuestas:
                if tipo == "Buena":
                    resolver(j, "PIERDE", monto, "come-out 2/3", "Buena")
                else:
                    resolver(j, "GANA", monto, "come-out 2/3", "Mala")
            cerrar_pase()

        elif suma == 12:
            # Buena pierde, Mala empata
            for j, tipo, monto in apuestas:
                if tipo == "Buena":
                    resolver(j, "PIERDE", monto, "come-out 12", "Buena")
                else:
                    resolver(j, "EMPATE", 0, "come-out 12", "Mala")
            cerrar_pase()

        else:
            # Punto establecido → Fase 2 (Botón ON)
            punto = suma
            fijar_punto(punto)

            # Tirar hasta punto (Buena gana) o 7 (Mala gana)
            while True:
                d1, d2, suma, es_doble = tirar_dados()
                tiro(d1, d2)

                if suma == punto:
                    # Buena gana, Mala pierde
                    for j, tipo, monto in apuestas:
                        if tipo == "Buena":
                            resolver(j, "GANA", monto, "punto logrado", "Buena")
                        else:
                            resolver(j, "PIERDE", monto, "punto logrado", "Mala")
                    cerrar_pase()
                    break

                elif suma == 7:
                    # Seven-out: Buena pierde, Mala gana
                    for j, tipo, monto in apuestas:
                        if tipo == "Buena":
                            resolver(j, "PIERDE", monto, "seven-out", "Buena")
                        else:
                            resolver(j, "GANA", monto, "seven-out", "Mala")
                    cerrar_pase()
                    break
                else:
                    # Otros números: en este runner base no hay apuestas accesorios
                    continue

        # (opcional) rotar tirador cada pase
        tirador_actual = ((tirador_actual) % NUM_JUGADORES) + 1

    log_path = os.path.abspath("logs/craps/debug_narrativo.log")
    print(f"Listo. Abrí {log_path} para ver el resultado.")


if __name__ == "__main__":
    main()