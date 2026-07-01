# utils/temporalidad.py

from config import tf_map
from utils.indicadores import calcular_ao
import MetaTrader5 as mt5

def get_temporalidades_vecinas(timeframe):
    return tf_map.get(timeframe, [])

def validar_contexto(simbolo, timeframe, direccion):
    vecinos = get_temporalidades_vecinas(timeframe)
    total = len(vecinos)
    confirmados = 0

    for tf in vecinos:
        velas = mt5.copy_rates_from_pos(simbolo, tf, 0, 40)
        if velas is None or len(velas) < 35:
            print(f"[{simbolo}] ⚠️ No suficientes velas para validar contexto en TF {tf}")
            continue

        ao = calcular_ao(velas)
        if len(ao) == 0:
            print(f"[{simbolo}] ⚠️ No se pudo calcular AO en TF {tf}")
            continue

        color_ao = "BUY" if ao[-1] > 0 else "SELL"
        print(f"[{simbolo}] 🔍 AO en TF {tf}: {ao[-1]:.5f} → {color_ao} (esperado: {direccion})")

        if color_ao == direccion:
            confirmados += 1

    if confirmados >= 1:
        print(f"[{simbolo}] ✅ Contexto multitemporal confirmado con {confirmados} de {total}")
        return True
    else:
        print(f"[{simbolo}] ❌ Contexto multitemporal no confirmado ({confirmados} de {total})")
        return False

