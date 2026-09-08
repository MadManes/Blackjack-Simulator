
# config_craps.py

"""Configuración por defecto: límites, pagos y modos (placeholders)."""


CONFIG_POR_DEFECTO = {
    "limites": {
        "buena_mala": {"min": 5000, "max": 150000},
        "costilla": {"min": 5000, "max": 50000},
        "camuninas": {"min": 1500, "max": 15000},
        "cuadro_individual": {"min": 1000, "max": 10000},
        "cuadro_conjunto": {"min_total": 4000, "max_total": 40000},
        "any_seven": {"min": 1000, "max": 4000},
        "any_craps": {"min": 1000, "max": 5000},
        "field": {"min": 2500, "max": 50000},
    },
    "modos": {
        "modo_enganche": 1, # 1 o 2  (este tambien me cambia maximos de costilla buena)
        "alto": False, # Cuadro Modo 1/2
    },
    "pagos": {
        "linea": {"buena": 1.0, "mala": 1.0},
        "enganche_buena_true_odds": {"4_10": 2.0, "5_9": 1.5, "6_8": 1.2},
        "enganche_mala_true_reverse": {"4_10": 0.5, "5_9": 0.6667, "6_8": 0.8333},
        "costilla": {"4_10": 1.8, "5_9": 1.4, "6_8": 1.1},
        "camuninas": {"2_2": 7.0, "3_3": 9.0, "4_4": 9.0, "5_5": 7.0},
        "cuadro_individual": {"dos": 31.0, "tres": 15.0, "once": 15.0, "doce": 31.0},
        "cuadro_conjunto": {"dos": 7.0, "tres": 3.0, "once": 3.0, "doce": 7.0},
        "any_seven": 4.0,
        "any_craps": 7.0,
        "field": {"base_1a1": [3, 4, 9, 10, 11], "dos_y_doce_2a1": [2, 12]},
    },
}