# utils/indicadores.py

import MetaTrader5 as mt5
from datetime import datetime, timedelta

def obtener_velas_mt5(simbolo, timeframe, cantidad):
    utc_from = datetime.utcnow() - timedelta(days=2)
    velas = mt5.copy_rates_from(simbolo, timeframe, utc_from, cantidad)
    if velas is None or len(velas) == 0:
        return None
    return velas

def calcular_ema(cierres, periodo):
    if len(cierres) < periodo:
        return None
    k = 2 / (periodo + 1)
    ema = cierres[0]
    for precio in cierres[1:]:
        ema = precio * k + ema * (1 - k)
    return ema

def calcular_ao(velas):
    ao = []
    for i in range(5, len(velas)):
        median_price = lambda v: (v['high'] + v['low']) / 2
        sma5 = sum(median_price(v) for v in velas[i-5:i]) / 5
        sma34 = sum(median_price(v) for v in velas[i-34:i]) / 34 if i >= 34 else sma5
        ao.append(sma5 - sma34)
    return ao


