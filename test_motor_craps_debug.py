# tools/test_motor_craps_debug.py
from games.craps.motor.motor_craps import MotorCraps
from games.craps.estadisticas.craps_stats import EstadisticasCraps

def run_test(seed=12345, pases=10, tiros_por_pase_max=20):
    stats = EstadisticasCraps()
    m = MotorCraps(estadisticas=stats, semilla=seed)
    # construir setup simple: 3 jugadores: 1 Buena, 2 Mala, 3 Buena
    setup = [
        {"jugador": 1, "linea": "Buena", "monto": 5000, "puede_tirar": True},
        {"jugador": 2, "linea": "Mala", "monto": 5000, "puede_tirar": True},
        {"jugador": 3, "linea": "Buena", "monto": 5000, "puede_tirar": True},
    ]
    m.set_setup_players(setup)
    m._configurar_tirador_inicial(0.7)

    for i in range(pases):
        print("\n=== INICIO PASE #{}/{} ===".format(i+1, pases))
        m.start_pase(num_jugadores=3, p_buena=0.7, pases_linea_min=5000, pases_linea_max=5000, prob_enganche=0.0, setup_players=setup)
        # hasta que pase termine, hacemos step con tope de tiros
        tiros = 0
        while getattr(m, "_pase_in_progress", False) and tiros < tiros_por_pase_max:
            m.step()
            tiros += 1
        print("=== FIN PASE (tiros) ===", tiros)
        # imprimimos snapshot
        try:
            print("Stats snapshot:", m.stats.snapshot())
        except Exception as e:
            print("Stats snapshot error:", e)

if __name__ == "__main__":
    run_test()
