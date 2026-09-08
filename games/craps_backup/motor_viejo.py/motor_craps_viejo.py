

"""Motor de Craps — esqueleto con API pública (stubs)."""
from typing import Any, Dict, Optional, Tuple
from games.craps.config_craps import CONFIG_POR_DEFECTO
from games.craps.eventos.bus_eventos import BusEventos
from games.craps.motor.estado_mesa import EstadoMesa
from games.craps.motor.servicio_azar import ServicioAzar
from games.craps.motor.banca import Banca
from games.craps.motor.calculadora_pagos import CalculadoraPagos
from games.craps.motor.registro_apuestas import RegistroApuestas

def _merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out

class MotorCraps:
    """Orquesta estado, tiradas y resolución (solo estructura)."""
    def __init__(self, config: Optional[Dict[str, Any]] = None, semilla: Optional[int] = None) -> None:
        self.config = _merge(CONFIG_POR_DEFECTO, config or {})
        self.eventos = BusEventos()
        self.azar = ServicioAzar(semilla)
        self.banca = Banca()
        self.pagos = CalculadoraPagos(self.config)
        self.apuestas = RegistroApuestas()
        self.estado = EstadoMesa(boton=False, punto=0, tirador_id=0, contador_tiros=0)


    # -------- API pública --------
    def snapshot(self) -> EstadoMesa:
        return self.estado


    def suscribir(self, tipo_evento: str, handler) -> str:
        return self.eventos.suscribir(tipo_evento, handler)


    def fijar_semilla(self, semilla: int) -> None:
        self.azar = ServicioAzar(semilla)


    def colocar_apuesta(self, id_jugador: int, tipo: str, monto: int, meta: Optional[Dict[str, Any]] = None) -> int:
    # validaciones de límites irán aquí
        ap = self.apuestas.crear(id_jugador, tipo.capitalize(), int(monto), meta)
        self.banca.debitar(id_jugador, int(monto))
        self.eventos.publicar("APUESTA_COLOCADA", id_ap=ap.id_apuesta, id_jugador=id_jugador, tipo=tipo.capitalize(), monto=monto, meta=meta or {})
        return ap.id_apuesta


    def tirar_dados(self, forzar: Optional[Tuple[int, int]] = None) -> Dict[str, Any]:
        d1, d2 = forzar if forzar else self.azar.tirar_dos_dados()
        suma = d1 + d2
        self.eventos.publicar("TIRO_INICIADO", d1=d1, d2=d2, suma=suma, es_doble=(d1 == d2))
        # resolución por fases se añadirá en la siguiente sub-etapa
        self.estado = EstadoMesa(
            boton=self.estado.boton,
            punto=self.estado.punto,
            tirador_id=self.estado.tirador_id,
            contador_tiros=self.estado.contador_tiros + 1,
        )
        self.eventos.publicar("SNAPSHOT_ESTADO", estado=self.estado)
        return {"d1": d1, "d2": d2, "suma": suma, "estado": self.estado}


    # -------- Internos (stubs) --------
    def _resolver_fase1(self, suma: int) -> None:
        pass


    def _resolver_fase2(self, suma: int) -> None:
        pass


    def _finalizar_pase(self) -> None:
        pass