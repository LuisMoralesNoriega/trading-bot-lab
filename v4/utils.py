import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mapa de timeframe
_TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

def conectar_cuenta():
    if not mt5.initialize():
        raise Exception("❌ No se pudo inicializar MetaTrader 5")
    cuenta = mt5.account_info()
    if cuenta is None:
        raise Exception("❌ No se pudo obtener información de la cuenta")
    print(f"✅ Conectado a cuenta: {cuenta.login} | Balance: {cuenta.balance}")
    return cuenta

def _to_pandas(rates):
    df = pd.DataFrame(rates)
    if not df.empty and "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
    return df

def _heikin_ashi(df):
    """
    Convierte OHLC a Heikin Ashi (por si tu plantilla lo usa).
    """
    ha = pd.DataFrame(index=df.index, columns=["open","high","low","close"])
    ha["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0
    ha["open"] = np.nan
    ha.iloc[0, ha.columns.get_loc("open")] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2.0
    for i in range(1, len(df)):
        ha.iloc[i, ha.columns.get_loc("open")] = (ha["open"].iloc[i-1] + ha["close"].iloc[i-1]) / 2.0
    ha["high"] = df[["high", "open", "close"]].max(axis=1)
    ha["low"]  = df[["low", "open", "close"]].min(axis=1)
    return ha

def get_rates(symbol: str, timeframe_str: str, bars: int) -> pd.DataFrame:
    tf = _TF_MAP.get(timeframe_str)
    if tf is None:
        raise ValueError(f"Timeframe no soportado: {timeframe_str}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None:
        raise RuntimeError(f"No se pudieron obtener velas de {symbol} en {timeframe_str}")

    df = _to_pandas(rates)
    # Renombra columnas a minúsculas por consistencia
    df.rename(columns={"open":"open","high":"high","low":"low","close":"close","tick_volume":"tick_volume"}, inplace=True)
    return df

def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()

def build_source_series(df: pd.DataFrame, source: str = "close", use_heikin: bool = False) -> pd.Series:
    if use_heikin:
        ha = _heikin_ashi(df)
        base = ha[source]
    else:
        base = df[source]
    return base

def compute_ema_set(df: pd.DataFrame, periods: list[int], source: str = "close",
                    use_heikin: bool = False) -> pd.DataFrame:
    s = build_source_series(df, source, use_heikin)
    out = pd.DataFrame(index=df.index)
    for p in periods:
        out[f"EMA_{p}"] = calc_ema(s, p)
    return out

def compute_major_trend(df: pd.DataFrame, period: int, source: str = "close",
                        use_heikin: bool = False, use_sma_instead: bool = False) -> pd.Series:
    s = build_source_series(df, source, use_heikin)
    if use_sma_instead:
        return calc_sma(s, period)   # ← cámbialo a True si tu amarilla es SMA 200
    return calc_ema(s, period)