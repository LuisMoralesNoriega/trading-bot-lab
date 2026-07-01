# estrategias/tendencia.py

import MetaTrader5 as mt5
from gestion.evaluador import EvaluadorGeneral
from gestion.volumen import CalculadorVolumen
from gestion.stops import VerificadorStops
from utils.indicadores import obtener_velas_mt5
from utils.logger import log_console
from utils.temporalidad import validar_contexto
from config import RIESGO_POR_OPERACION
from utils.indicadores import calcular_ema

class EstrategiaTendencia:
    def __init__(self, simbolo, timeframe):
        self.simbolo = simbolo
        self.timeframe = timeframe
        self.evaluador = EvaluadorGeneral()
        self.volumen_calc = CalculadorVolumen()
        self.stops_check = VerificadorStops()

    def detectar_senal_tendencia(self):
        velas = obtener_velas_mt5(self.simbolo, self.timeframe, 100)
        if velas is None or len(velas) < 60:
            log_console(f"[{self.simbolo}] ❌ No se obtuvieron suficientes velas para {self.timeframe}")
            return None

        direccion = self.evaluador.validar_emas_ordenadas(velas)
        if direccion is None:
            log_console(f"[{self.simbolo}] ❌ EMAs no están ordenadas para tendencia clara.")
            return None
        self.evaluador.direccion = direccion

        # ✅ AHORA sí es seguro usar la dirección
        tick = mt5.symbol_info_tick(self.simbolo)
        precio_actual = tick.bid if direccion == "SELL" else tick.ask

        if not self.evaluador.validar_precio_en_banda(velas):
            log_console(f"[{self.simbolo}] ❌ Precio fuera de banda de EMAs.")
            return None
        log_console(f"[{self.simbolo}] ✅ EMAs y precio dentro de banda confirmados ({direccion})")

        if not self.evaluador.validar_ao_color(velas):
            log_console(f"[{self.simbolo}] ❌ AO no confirma la dirección ({direccion})")
            return None

        if not self.evaluador.validar_patron_vela(velas):
            log_console(f"[{self.simbolo}] ❌ No hay patrón de vela fuerte.")
            return None
        log_console(f"[{self.simbolo}] ✅ AO y patrón de vela confirmados")

        if not validar_contexto(self.simbolo, self.timeframe, direccion):
            log_console(f"[{self.simbolo}] ❌ Contexto multitemporal no confirma la dirección ({direccion})")
            return None
        log_console(f"[{self.simbolo}] ✅ Contexto multitemporal confirmado ({direccion})")

        sl, tp = self.calcular_sl_tp(velas, direccion, precio_actual)
        log_console(f"[{self.simbolo}] SL: {sl:.2f} | TP: {tp:.2f}")

        if not self.stops_check.validar_distancia_minima_SL_TP(self.simbolo, sl, tp):
            log_console(f"[{self.simbolo}] ❌ SL/TP no cumplen distancia mínima permitida por el bróker.")
            return None
        log_console(f"[{self.simbolo}] ✅ SL y TP cumplen distancia mínima")

        sl_pips = abs(precio_actual - sl)
        volumen = self.volumen_calc.calcular_volumen(sl_pips, RIESGO_POR_OPERACION)

        if not self.volumen_calc.validar_volumen_en_rango(volumen):
            log_console(f"[{self.simbolo}] ❌ Volumen calculado fuera de rango permitido.")
            return None
        log_console(f"[{self.simbolo}] ✅ Volumen válido: {volumen}")

        operacion = self.construir_operacion(sl, tp, volumen)
        log_console(f"[{self.simbolo}] ✅ Operación lista para ejecutar: {operacion}")
        return operacion


    def calcular_sl_tp(self, velas, direccion, precio_actual):
        if direccion == "BUY":
            sl = min([v['low'] for v in velas[-5:]])
            distancia = precio_actual - sl
        else:
            sl = max([v['high'] for v in velas[-5:]])
            distancia = sl - precio_actual

        symbol_info = mt5.symbol_info(self.simbolo)
        if symbol_info is None:
            return sl, precio_actual

        min_dist = symbol_info.trade_stops_level * symbol_info.point
        if distancia < min_dist:
            distancia = min_dist

        if direccion == "BUY":
            sl = precio_actual - distancia
            tp = precio_actual + 2 * distancia
        else:
            sl = precio_actual + distancia
            tp = precio_actual - 2 * distancia

        return sl, tp


    def construir_operacion(self, sl, tp, volumen):
        return {
            "simbolo": self.simbolo,
            "tipo": "BUY" if self.evaluador.direccion == "BUY" else "SELL",
            "precio": None,
            "sl": sl,
            "tp": tp,
            "volumen": volumen
        }
