import pandas as pd
from datetime import datetime

class EstadisticasCasino:
    def __init__(self):
        self.total_manos = 0        
        self.manos_ganadas = 0
        self.manos_perdidas = 0
        self.manos_empatadas = 0
        self.blackjacks_jugador = 0
        self.blackjacks_dealer = 0
        self.splits = 0
        self.split_ases = 0
        self.doubles = 0
        self.ganancias_casino = 0.0
        self.dinero_en_juego = 0.0
        self.dinero_en_juego_mano_actual = 0.0
        self.ganancia_mano_actual = 0.0
        self.seguros_apostados = 0
        self.seguros_cobrados = 0
        self.monto_seguros_apostados = 0
        self.monto_seguros_pagados = 0
        self.monto_seguros_perdidos = 0
        self.historial_manos = []
        self.historial_ganancias = []
        self.historial_porcentaje_ganancia = []
        self.manos_por_minuto = 0.0
        self.historial_step = 1      

    def registrar_seguro_apostado(self, monto):
        self.seguros_apostados += 1
        self.monto_seguros_apostados += monto

    def registrar_seguro_cobrado(self, monto_pagado):
        self.seguros_cobrados += 1
        self.monto_seguros_pagados += monto_pagado

    def registrar_seguro_perdido(self, monto):
        self.monto_seguros_perdidos += monto

    def registrar_apuesta(self, monto):
        
        self.dinero_en_juego_mano_actual += monto

    def registrar_ganancia_mano_actual(self, ganancia_mano):
        self.ganancia_mano_actual = ganancia_mano
        self.ganancias_casino += ganancia_mano
        if self.total_manos % self.historial_step == 0:
            self.guardar_progreso()   
        
    def registrar_evento(self, evento):
        if evento == "ganada":
            self.manos_ganadas += 1
        elif evento == "perdida":
            self.manos_perdidas += 1
        elif evento == "empatada":
            self.manos_empatadas += 1
        elif evento == "blackjack_jugador":
            self.blackjacks_jugador += 1
        elif evento == "blackjack_dealer":
            self.blackjacks_dealer += 1
        elif evento == "split":
            self.splits += 1
        elif evento == "split_ases":
            self.split_ases += 1
        elif evento == "double":
            self.doubles += 1
            
    def calcular_porcentaje_ganancia(self):
        if self.dinero_en_juego == 0:
            return 0.0
        try:
            return (self.ganancias_casino / self.dinero_en_juego) * 100
        except ZeroDivisionError:
            return 0.0
        
    def guardar_progreso(self):
        self.historial_manos.append(self.total_manos)
        self.historial_ganancias.append(self.ganancias_casino)
        self.historial_porcentaje_ganancia.append(self.calcular_porcentaje_ganancia())

    def generar_reporte(self, file_path="reporte_blackjack.txt"):
        reporte = f"""
        =============== REPORTE DE SIMULACIÓN BLACKJACK ===============
        Fecha y Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        ===============================================================

        - Manos simuladas: {self.total_manos:,}
        - Manos por minuto: {self.manos_por_minuto:,.0f}

        - Ganancias acumuladas del casino: ${self.ganancias_casino:,.2f}
        - Dinero total en juego: ${self.dinero_en_juego:,.2f}
        - Porcentaje de ventaja de la casa: {self.calcular_porcentaje_ganancia():.4f}%

        ----------------- Estadísticas de resultados -----------------
        - Manos ganadas por jugadores: {self.manos_ganadas:,}
        - Manos perdidas por jugadores: {self.manos_perdidas:,}
        - Manos empatadas: {self.manos_empatadas:,}

        - Blackjacks de jugadores: {self.blackjacks_jugador:,}
        - Blackjacks del dealer: {self.blackjacks_dealer:,}

        ----------------- Estadísticas de acciones -----------------
        - Aperturas de pares (splits): {self.splits:,}
        - Duplicadas (doubles): {self.doubles:,}
        
        ===============================================================
        """
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(reporte)
        print(f"Reporte guardado en {file_path}")

    def to_dataframe(self):
        data = {
            'Mano': self.historial_manos,
            'Ganancia Acumulada': self.historial_ganancias,
            'Porcentaje Ganancia': self.historial_porcentaje_ganancia
        }
        return pd.DataFrame(data)