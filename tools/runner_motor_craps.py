# tools/runner_motor_craps.py
from __future__ import annotations
import os, sys

# Asegurar imports tipo "from games.craps..." aunque ejecutes este archivo directo
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Proyecto
from games.craps.estadisticas.craps_stats import EstadisticasCraps
from games.craps.debug.suscriptor_narrativo import (
    ActualizadorEstadisticas,
    SuscriptorEventosNarrativo,
)
from games.craps.motor.motor_craps import MotorCraps

# ---------------------------
# Parámetros de simulación
# ---------------------------
SEMILLA = None          # poné un int para reproducibilidad (p.ej., 12345)
NUM_PASES = 10
NUM_JUGADORES = 8
P_BUENA = 0.7           # probabilidad de que un jugador elija Buena
MIN_APUESTA = 5000
MAX_APUESTA = 150000

def main() -> None:
    # Contadores compartidos
    stats = EstadisticasCraps()

    # Motor real mínimo
    motor = MotorCraps(estadisticas=stats, semilla=SEMILLA)

    # Suscriptores (mismos que usarán simulador gráfico/masivo)
    narrador = SuscriptorEventosNarrativo(stats, ruta_archivo="logs/craps/debug_narrativo.log")
    actualizador = ActualizadorEstadisticas(stats)

    # Conectar ambos a los eventos relevantes del motor
    for evt in ["NUEVO_TIRADOR", "APUESTA_COLOCADA", "TIRO_INICIADO",
                "PUNTO_FIJADO", "APUESTA_RESUELTA", "PUNTO_LIBRE"]:
        motor.suscribir(evt, actualizador)
        motor.suscribir(evt, narrador)

    # Simulación: NUM_PASES pases reales
    for _ in range(NUM_PASES):
        motor.jugar_pase_random(
            num_jugadores=NUM_JUGADORES,
            p_buena=P_BUENA,
            pases_linea_min=MIN_APUESTA,
            pases_linea_max=MAX_APUESTA,
        )

    log_path = os.path.abspath("logs/craps/debug_narrativo.log")
    print(f"Listo. Abrí {log_path} para ver el resultado.")

if __name__ == "__main__":
    main()
