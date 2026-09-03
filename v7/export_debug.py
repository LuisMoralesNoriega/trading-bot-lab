import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from config import EMA_PERIODS
from strategy import (
    calculate_awesome_oscillator,
    calculate_trend,
    generate_base_signal,
)


SYMBOL = "BTCUSD-T"
TIMEFRAME_NAME = "M1"
TIMEFRAME = mt5.TIMEFRAME_M1
BARS = 500
OUTPUT = (
    Path(__file__).resolve().parent
    / "debug"
    / "BTCUSD-T_M1_last10.json"
)


def calculate_indicators(dataframe):
    dataframe = calculate_trend(dataframe)
    dataframe = calculate_awesome_oscillator(dataframe)
    return generate_base_signal(dataframe)


def decimal_value(value, decimal_places=8):
    return round(float(value), decimal_places)


def export_debug():
    if not mt5.initialize():
        raise RuntimeError(f"No se pudo conectar con MT5: {mt5.last_error()}")

    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"No se pudo leer la cuenta: {mt5.last_error()}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(
                f"No se pudo activar {SYMBOL}: {mt5.last_error()}"
            )
        symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            raise RuntimeError(
                f"No se pudo leer {SYMBOL}: {mt5.last_error()}"
            )

        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, BARS)
        if rates is None or len(rates) < BARS:
            raise RuntimeError(
                f"Se recibieron menos de {BARS} velas cerradas: "
                f"{mt5.last_error()}"
            )

        dataframe = pd.DataFrame(rates)
        dataframe["time_epoch_original"] = dataframe["time"].astype("int64")
        dataframe["time"] = pd.to_datetime(
            dataframe["time"],
            unit="s",
            utc=True,
        )
        dataframe = calculate_indicators(dataframe)

        precision = max(8, symbol_info.digits)
        candles = []
        for _, row in dataframe.tail(10).iterrows():
            candle = {
                "time_epoch_original": int(row["time_epoch_original"]),
                "time_utc": row["time"].isoformat(),
                "open": round(float(row["open"]), symbol_info.digits),
                "high": round(float(row["high"]), symbol_info.digits),
                "low": round(float(row["low"]), symbol_info.digits),
                "close": round(float(row["close"]), symbol_info.digits),
                "tick_volume": int(row["tick_volume"]),
                "spread_points": int(row["spread"]),
                "real_volume": int(row["real_volume"]),
            }
            for period in EMA_PERIODS:
                candle[f"ema_{period}"] = decimal_value(
                    row[f"ema_{period}"],
                    precision,
                )
            candle.update({
                "band_min": decimal_value(row["band_bottom"], precision),
                "band_max": decimal_value(row["band_top"], precision),
                "trend": str(row["trend"]),
                "touches_band": bool(row["touches_band"]),
                "awesome_oscillator": decimal_value(row["ao"], precision),
                "ao_color": str(row["ao_color"]),
                "ao_changed_to_green": bool(row["ao_turn_green"]),
                "ao_changed_to_red": bool(row["ao_turn_red"]),
                "base_signal": str(row["base_signal"]),
            })
            candles.append(candle)

        document = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "server": account.server,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME_NAME,
            "digits": symbol_info.digits,
            "point": symbol_info.point,
            "bars_used_for_calculation": len(dataframe),
            "excluded_active_candle": True,
            "candles": candles,
        }
        OUTPUT.parent.mkdir(exist_ok=True)
        with OUTPUT.open("w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"JSON exportado: {OUTPUT}")
        print(f"Velas cerradas exportadas: {len(candles)}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    export_debug()
