# utils_mt5.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz

def conectar_cuenta():
    if not mt5.initialize():
        raise Exception("❌ No se pudo inicializar MetaTrader 5")
    cuenta = mt5.account_info()
    if cuenta is None:
        raise Exception("❌ No se pudo obtener información de la cuenta")
    print(f"✅ Conectado a cuenta: {cuenta.login} | Balance: {cuenta.balance}")
    return cuenta

def obtener_datos(symbol, timeframe, n=300):
    tf_map = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1
    }
    if timeframe not in tf_map:
        raise ValueError(f"⛔ Timeframe {timeframe} no soportado")
    
    rates = mt5.copy_rates_from_pos(symbol, tf_map[timeframe], 0, n)
    if rates is None or len(rates) == 0:
        raise Exception(f"❌ No se pudo obtener datos para {symbol} en TF {timeframe}")
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    print(f"[DEBUG] Última vela para {symbol} TF:{timeframe}: {df['time'].iloc[-1]} | Close: {df['close'].iloc[-1]}")
    return df

def abrir_orden(symbol, lot, order_type, sl=None, tp=None):
    tipo = mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if order_type == "buy" else mt5.symbol_info_tick(symbol).bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": tipo,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 101010,
        "comment": f"v3-{order_type}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error al abrir orden: {result.comment}")
    else:
        print(f"✅ Orden enviada: {order_type.upper()} @ {price:.2f} | Volumen: {lot}")
        print(f"📌 SL: {sl:.2f} | TP: {tp:.2f}")

def get_symbol_info(symbol):
    info = mt5.symbol_info(symbol)
    if info is None:
        raise Exception(f"❌ No se pudo obtener información para el símbolo {symbol}")
    return info

def get_balance():
    """
    Devuelve el balance actual de la cuenta.
    """
    cuenta = mt5.account_info()
    if cuenta is None:
        raise Exception("❌ No se pudo obtener el balance de la cuenta")
    return cuenta.balance

def get_min_stop_distance(symbol):
    info = get_symbol_info(symbol)
    return info.trade_stops_level * info.point

def adjust_sl_tp(symbol, entry_price, sl_distance, tp_distance, is_buy=True):
    """
    Ajusta SL/TP para cumplir con el mínimo nivel de stops permitido por MT5.
    """
    info = get_symbol_info(symbol)
    point = info.point
    min_stop = get_min_stop_distance(symbol)
    
    # Usar multiplicador para evitar rechazos
    dynamic_min_stop = min_stop * 5  

    sl_distance = max(sl_distance * point, dynamic_min_stop)
    tp_distance = max(tp_distance * point, dynamic_min_stop)

    if is_buy:
        sl = entry_price - sl_distance
        tp = entry_price + tp_distance
    else:
        sl = entry_price + sl_distance
        tp = entry_price - tp_distance

    print(f"[DEBUG] Min Stop Required: {min_stop} | Used Stop Distance: {sl_distance}")
    return sl, tp

def calcular_volumen(symbol, riesgo_porcentaje, sl_distance_points):
    """
    Calcula el volumen (lot) para que la pérdida máxima al llegar al SL
    no supere el riesgo establecido (% del balance).
    """
    balance = get_balance()
    info = get_symbol_info(symbol)
    tick_value = info.trade_tick_value  # Valor monetario por punto
    riesgo_usd = balance * (riesgo_porcentaje / 100)

    if tick_value <= 0:
        raise Exception(f"❌ Tick value inválido para {symbol}")

    volumen = riesgo_usd / (sl_distance_points * tick_value)
    volumen = round(volumen, 2)  # Redondeamos a 2 decimales

    return max(volumen, info.volume_min)

def generar_heikin_ashi(df):
    """
    Convierte velas OHLC en velas Heikin Ashi.
    Devuelve un nuevo DataFrame con columnas: ha_open, ha_close, ha_high, ha_low.
    """
    ha_df = df.copy()
    ha_df['ha_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4

    ha_open = [(ha_df['open'].iloc[0] + ha_df['close'].iloc[0]) / 2]
    for i in range(1, len(ha_df)):
        ha_open.append((ha_open[i - 1] + ha_df['ha_close'].iloc[i - 1]) / 2)
    ha_df['ha_open'] = ha_open

    ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
    ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)
    
    return ha_df

