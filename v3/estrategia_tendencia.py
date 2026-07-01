from utils_mt5 import (
    obtener_datos,
    abrir_orden,
    adjust_sl_tp,
    calcular_volumen,
    get_symbol_info,
    generar_heikin_ashi
)
from config import TIMEFRAMES_TENDENCIA, EMAS_PERIODS, SL_PIPS_DEFAULT, TP_PIPS_DEFAULT, RIESGO_PORCENTAJE
import numpy as np

def calcular_emas(df):
    for period in EMAS_PERIODS:
        df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    return df

def calcular_ATR(df, periodo=14):
    high_low = df['high'] - df['low']
    atr = high_low.rolling(window=periodo).mean()
    return atr

def obtener_pendiente(serie, velas=5):
    if len(serie) < velas:
        return 0
    y = serie[-velas:]
    x = np.arange(len(y))
    m, _ = np.polyfit(x, y, 1)
    return m

def determinar_tendencia(df, atr_actual):
    ult = df.iloc[-1]
    emas = [ult[f'EMA_{p}'] for p in EMAS_PERIODS]
    alcista = all(emas[i] > emas[i + 1] for i in range(len(emas) - 1))
    bajista = all(emas[i] < emas[i + 1] for i in range(len(emas) - 1))
    ema_max_period = df[f'EMA_{EMAS_PERIODS[-1]}']
    pendiente = obtener_pendiente(ema_max_period, velas=5)
    umbral_pendiente = atr_actual * 0.03

    if abs(pendiente) < umbral_pendiente:
        return "plano", pendiente
    if alcista and pendiente > 0:
        return "alcista", pendiente
    elif bajista and pendiente < 0:
        return "bajista", pendiente
    else:
        return "plano", pendiente

def calcular_AO(df):
    median_price = (df["high"] + df["low"]) / 2
    sma5 = median_price.rolling(window=5).mean()
    sma34 = median_price.rolling(window=34).mean()
    df["AO"] = sma5 - sma34
    return df

def estrategia_tendencia(symbol):
    for timeframe in TIMEFRAMES_TENDENCIA:
        df = obtener_datos(symbol, timeframe)
        if df is None or len(df) < 60:
            print(f"⚠️ [{symbol} | TF:{timeframe}] Datos insuficientes.")
            continue

        df = calcular_emas(df)
        df = calcular_AO(df)
        df["ATR"] = calcular_ATR(df)

        atr_actual = df.iloc[-1]["ATR"]
        if np.isnan(atr_actual) or atr_actual == 0:
            print(f"⚠️ [{symbol} | TF:{timeframe}] ATR inválido.")
            continue

        tendencia, pendiente = determinar_tendencia(df, atr_actual)
        actual = df.iloc[-1]
        precio_actual = actual["close"]

        ema_values = [actual[f'EMA_{p}'] for p in EMAS_PERIODS]
        ema_sorted = sorted(ema_values)
        ema_min = ema_sorted[0]
        ema_max = ema_sorted[-1]
        ema_central = ema_values[len(ema_values) // 2]

        print(f"\n🔍 [{symbol} | TF:{timeframe}] Análisis de Tendencia")
        print(f"    Precio actual: {precio_actual:.5f}")
        print(f"    EMAs: {[round(e, 5) for e in ema_values]}")
        print(f"    Pendiente EMA larga: {pendiente:.6f}")
        print(f"    ATR: {atr_actual:.5f}")
        print(f"    Tendencia detectada: {tendencia.upper()}")
        print(f"🧪 [{symbol} | TF:{timeframe}] Comparando precio={precio_actual:.2f} con canal EMA ({ema_min:.2f} - {ema_max:.2f})")

        if tendencia == "plano":
            continue

        if not (ema_min <= precio_actual <= ema_max):
            print(f"⚠️ [{symbol} | TF:{timeframe}] Precio fuera de banda de EMAs.")
            continue

        distancia = abs(precio_actual - ema_central)
        umbral_proximidad = atr_actual * 0.15
        if distancia > umbral_proximidad:
            print(f"⚠️ [{symbol} | TF:{timeframe}] Precio alejado de EMA central.")
            continue

        tipo = "buy" if tendencia == "alcista" else "sell"

        ao_values = df["AO"].iloc[-5:].tolist()
        ao_penultima = ao_values[-2]
        print(f"📉 AO últimos: {[round(a, 5) for a in ao_values]}")
        if tipo == "buy" and ao_penultima <= 0:
            print(f"❌ AO no confirma BUY.")
            continue
        if tipo == "sell" and ao_penultima >= 0:
            print(f"❌ AO no confirma SELL.")
            continue
        print(f"✅ AO confirmado.")

        ha_df = generar_heikin_ashi(df)
        ha = ha_df.iloc[-2]
        if tipo == "buy" and ha['ha_close'] <= ha['ha_open']:
            print(f"❌ Heikin Ashi no confirma BUY.")
            continue
        if tipo == "sell" and ha['ha_close'] >= ha['ha_open']:
            print(f"❌ Heikin Ashi no confirma SELL.")
            continue
        print(f"✅ Heikin Ashi confirmado.")

        sl, tp = adjust_sl_tp(symbol, precio_actual, SL_PIPS_DEFAULT, TP_PIPS_DEFAULT, is_buy=(tipo == "buy"))
        sl_distance_points = abs(precio_actual - sl) / get_symbol_info(symbol).point
        lot = calcular_volumen(symbol, RIESGO_PORCENTAJE, sl_distance_points)

        print(f"🎯 Entrada: {precio_actual:.5f} | SL: {sl:.5f} | TP: {tp:.5f} | Volumen: {lot}")
        abrir_orden(symbol, lot, tipo, sl, tp)
        break  # Detener al encontrar una entrada válida
