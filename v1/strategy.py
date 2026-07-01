import pandas as pd
import MetaTrader5 as mt5
from tp_sl_dinamico import definir_tp_sl_dinamico

def detectar_doble_piso(df, profundidad=5, tolerancia_pct=0.5):
    lows = df["low"].values

    minimos = []
    for i in range(profundidad, len(lows) - profundidad):
        es_minimo_local = all(
            lows[i] < lows[i - j] and lows[i] < lows[i + j]
            for j in range(1, profundidad + 1)
        )
        if es_minimo_local:
            minimos.append((i, lows[i]))

    if len(minimos) < 2:
        return False, None

    for i in range(len(minimos) - 1):
        idx1, val1 = minimos[i]
        idx2, val2 = minimos[i + 1]

        tolerancia = val1 * (tolerancia_pct / 100)
        son_similares = abs(val1 - val2) <= tolerancia
        hay_valle = df["close"].iloc[idx1:idx2].max() > val1

        neckline = df["close"].iloc[idx1:idx2].max()
        confirmacion = df["close"].iloc[-1] > neckline

        if son_similares and hay_valle and confirmacion:
            return True, {
                "idx1": idx1,
                "idx2": idx2,
                "p1": val1,
                "p2": val2,
                "neckline": neckline,
                "confirm_close": df["close"].iloc[-1]
            }

    return False, None

def calcular_ao(df):
    median_price = (df["high"] + df["low"]) / 2
    sma5 = median_price.rolling(window=5).mean()
    sma34 = median_price.rolling(window=34).mean()
    ao = sma5 - sma34
    df["ao"] = ao
    return df

def calcular_emas_escalonadas(df):
    periodos = [30, 35, 40, 45, 50, 55]
    for p in periodos:
        df[f'ema_{p}'] = df['close'].ewm(span=p, adjust=False).mean()
    return df

def rompe_linea_tendencia(df, idx1, idx2, tolerancia_pct=0.3):
    sub_df = df.iloc[idx1:idx2+1]
    max_idx = sub_df['high'].idxmax()
    max_price = df['high'].loc[max_idx]

    last_low_price = min(df['low'].iloc[idx1], df['low'].iloc[idx2])
    x1, x2 = idx1, idx2
    y1, y2 = max_price, last_low_price
    pendiente = (y2 - y1) / (x2 - x1) if (x2 - x1) != 0 else 0

    x_actual = len(df) - 1
    y_tendencia = y1 + pendiente * (x_actual - x1)

    cierre_actual = df['close'].iloc[-1]
    diferencia = cierre_actual - y_tendencia
    return diferencia > (y_tendencia * tolerancia_pct / 100)

def es_tendencia_clara(df):
    ult = df.iloc[-1]
    precio = ult["close"]
    emas = [ult[f"ema_{p}"] for p in [30, 35, 40, 45, 50, 55]]

    es_orden_ascendente = all(emas[i] > emas[i+1] for i in range(len(emas)-1))
    es_orden_descendente = all(emas[i] < emas[i+1] for i in range(len(emas)-1))

    if precio > max(emas) and es_orden_ascendente:
        return "alcista"
    elif precio < min(emas) and es_orden_descendente:
        return "bajista"
    else:
        return None

def estrategia_tendencia(df, symbol):
    tendencia = es_tendencia_clara(df)
    if not tendencia:
        return None

    ao_actual = df["ao"].iloc[-1]
    ao_previo = df["ao"].iloc[-2]

    tick = mt5.symbol_info_tick(symbol)
    if not tick or tick.bid <= 0 or tick.ask <= 0:
        print(f"❌ Tick inválido para {symbol}")
        return None

    entrada = tick.ask if tendencia == "alcista" else tick.bid
    
    if tendencia == "alcista" and ao_actual > ao_previo and ao_actual > 0:
        print("✅ Entrada por tendencia alcista con AO confirmando.")
        sl, tp = definir_tp_sl_dinamico(df, tipo="BUY")
        return {"entrada": entrada, "sl": sl, "tp": tp, "tipo": "BUY"}

    if tendencia == "bajista" and ao_actual < ao_previo and ao_actual < 0:
        print("✅ Entrada por tendencia bajista con AO confirmando.")
        sl, tp = definir_tp_sl_dinamico(df, tipo="SELL")
        return {"entrada": entrada, "sl": sl, "tp": tp, "tipo": "SELL"}

    return None

def estrategia_doble_piso(df, symbol):
    señal, datos = detectar_doble_piso(df)
    if not señal:
        return None

    print("✅ Doble piso detectado:")
    print(datos)

    ao_actual = df["ao"].iloc[-1]
    ao_previo = df["ao"].iloc[-2]

    if ao_actual > ao_previo and ao_actual > 0:
        print("🧠 AO confirma momentum positivo.")
        if rompe_linea_tendencia(df, datos["idx1"], datos["idx2"]):
            print("📈 Confirmación: rompió la línea de tendencia descendente.")
            tick = mt5.symbol_info_tick(symbol)
            if tick is None or tick.ask <= 0:
                print(f"❌ Precio actual inválido para {symbol}. No se puede enviar la orden.")
                return None

            entrada = tick.ask
            sl, tp = definir_tp_sl_dinamico(df, tipo="BUY")
            return {"entrada": entrada, "sl": sl, "tp": tp}

        else:
            print("⚠️ Aún no rompe la línea de tendencia. Esperar confirmación.")
    else:
        print("⚠️ AO no confirma aún. Esperar nueva vela.")

    return None

def estrategia_doble_techo(df, symbol):
    """
    Detecta un patrón de doble techo en el dataframe y retorna datos de entrada.
    """
    techos = []

    for i in range(2, len(df) - 2):
        if df["high"][i] > df["high"][i - 1] and df["high"][i] > df["high"][i + 1]:
            techos.append((i, df["high"][i]))

    if len(techos) < 2:
        return None

    # Tomar los últimos dos techos
    idx1, p1 = techos[-2]
    idx2, p2 = techos[-1]

    tolerancia = p1 * 0.002  # 0.2% de tolerancia
    if abs(p1 - p2) > tolerancia:
        return None

    # Neckline: punto mínimo entre los dos techos
    neckline = min(df["low"][idx1:idx2 + 1])
    confirm_close = neckline - ((p1 - neckline) * 0.1)

    # Confirmar rompimiento y AO negativo
    if df["close"].iloc[-1] < confirm_close and df["ao"].iloc[-1] < 0:
        print(f"✅ Doble techo detectado en {symbol}")
        return {
            "tipo": "SELL",
            "entrada": df["close"].iloc[-1],
            "sl": max(p1, p2),
            "tp": neckline - (max(p1, p2) - neckline),
            "estructura": {
                "idx1": idx1,
                "idx2": idx2,
                "p1": p1,
                "p2": p2,
                "neckline": neckline,
                "confirm_close": confirm_close
            }
        }

    return None

