import MetaTrader5 as mt5
from obtener_candles import obtener_candles
from strategy import calcular_ao, calcular_emas_escalonadas, es_tendencia_clara

def confirmar_contexto(symbol, tf_base):
    """
    Valida si una señal en una temporalidad (tf_base) tiene respaldo
    en temporalidades vecinas (superior e inferior).
    Devuelve True si hay confluencia, False si hay conflicto o duda.
    """
    tf_map = {
        mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15],
        mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M30],
        mt5.TIMEFRAME_M30: [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_H1],
        mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H4],
        mt5.TIMEFRAME_H4: [mt5.TIMEFRAME_H1, mt5.TIMEFRAME_D1],
        mt5.TIMEFRAME_D1: [mt5.TIMEFRAME_H4],
    }

    if tf_base not in tf_map:
        print(f"⚠️ No hay contexto definido para TF base: {tf_base}")
        return True  # Por defecto permitir si no definido

    tfs_contexto = tf_map[tf_base]
    tendencias = []

    for tf in tfs_contexto:
        try:
            df = obtener_candles(symbol, timeframe=tf, bars=100)
            df = calcular_ao(df)
            df = calcular_emas_escalonadas(df)
            tendencia = es_tendencia_clara(df)
            tendencias.append((tf, tendencia))
        except Exception as e:
            print(f"❌ Error evaluando contexto en TF {tf}: {e}")
            return False

    # Reglas de validación: si al menos uno de los TFs apoya la entrada, permitimos
    tendencias_validas = [t for tf, t in tendencias if t in ["alcista", "bajista"]]

    if not tendencias_validas:
        print("⚠️ No hay confluencia en TFs vecinos.")
        return False

    print("✅ Contexto validado por temporalidades vecinas:", tendencias)
    return True
