import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def obtener_candles(symbol="BTCUSD-T", timeframe=mt5.TIMEFRAME_H1, bars=200):
    # Verificamos que esté conectado
    if not mt5.initialize():
        raise Exception("Error al inicializar MT5")

    # Obtener datos históricos
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)

    # Validación
    if rates is None or len(rates) == 0:
        raise Exception("No se pudo obtener datos de", symbol)

    # Convertimos a DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df
