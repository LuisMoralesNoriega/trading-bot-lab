import pandas as pd
import MetaTrader5 as mt5

def calcular_atr(df, periodos=14):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift(1))
    df['low_close'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=periodos).mean()
    return df['atr']

def definir_tp_sl_dinamico(df, tipo="BUY", multiplicador_tp=2.0, multiplicador_sl=1.5):
    df = df.copy()
    df['atr'] = calcular_atr(df)

    if df['atr'].isna().all():
        raise Exception("No se pudo calcular ATR")

    atr_actual = df['atr'].iloc[-1]
    precio_actual = df['close'].iloc[-1]

    if tipo == "BUY":
        sl = precio_actual - (atr_actual * multiplicador_sl)
        tp = precio_actual + (atr_actual * multiplicador_tp)
    else:
        sl = precio_actual + (atr_actual * multiplicador_sl)
        tp = precio_actual - (atr_actual * multiplicador_tp)

    return round(sl, 2), round(tp, 2)
