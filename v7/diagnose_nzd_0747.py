import json
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from config import EMA_PERIODS, SLOPE_BARS
from strategy import (
    calculate_awesome_oscillator,
    calculate_trend,
    generate_base_signal,
)


SYMBOL = "NZDUSD-T"
TIMEFRAME = mt5.TIMEFRAME_M1
TIMEFRAME_NAME = "M1"
BARS = 500
TARGET_TIMES = {
    pd.Timestamp("2026-09-01T07:46:00+00:00"),
    pd.Timestamp("2026-09-01T07:47:00+00:00"),
}
OUTPUT = (
    Path(__file__).resolve().parent
    / "debug"
    / "NZDUSD-T_M1_2026-09-01T0747_diagnostic.json"
)


def condition(approved, approved_reason, rejected_reason):
    return {
        "approved": bool(approved),
        "reason": approved_reason if approved else rejected_reason,
    }


def analyze(dataframe):
    dataframe = calculate_trend(dataframe)
    dataframe = calculate_awesome_oscillator(dataframe)
    return generate_base_signal(dataframe)


def build_candle_diagnostic(dataframe, index, digits):
    row = dataframe.loc[index]
    previous = dataframe.loc[index - 1]
    slope_comparison = dataframe.loc[index - SLOPE_BARS]

    bullish_order_comparisons = []
    bearish_order_comparisons = []
    for short, long in zip(EMA_PERIODS, EMA_PERIODS[1:]):
        short_value = float(row[f"ema_{short}"])
        long_value = float(row[f"ema_{long}"])
        bullish_order_comparisons.append({
            "comparison": f"ema_{short} > ema_{long}",
            "left": short_value,
            "right": long_value,
            "approved": short_value > long_value,
        })
        bearish_order_comparisons.append({
            "comparison": f"ema_{short} < ema_{long}",
            "left": short_value,
            "right": long_value,
            "approved": short_value < long_value,
        })

    slopes = {}
    for period in EMA_PERIODS:
        current_value = float(row[f"ema_{period}"])
        compared_value = float(slope_comparison[f"ema_{period}"])
        direction = (
            "ASCENDING"
            if current_value > compared_value
            else "DESCENDING"
            if current_value < compared_value
            else "FLAT"
        )
        slopes[f"ema_{period}"] = {
            "current": current_value,
            "compared_with_time": slope_comparison["time"].isoformat(),
            "compared_with_value": compared_value,
            "algorithm_comparison_bullish": (
                f"{current_value} > {compared_value}"
            ),
            "algorithm_comparison_bearish": (
                f"{current_value} < {compared_value}"
            ),
            "direction": direction,
            "bullish_approved": current_value > compared_value,
            "bearish_approved": current_value < compared_value,
        }

    trend = str(row["trend"])
    touches_band = bool(row["touches_band"])
    turns_green = bool(row["ao_turn_green"])
    turns_red = bool(row["ao_turn_red"])
    buy_conditions = {
        "trend_is_bullish": condition(
            trend == "BULLISH",
            "Aprobada: trend es BULLISH.",
            f"Rechazada: trend es {trend}, no BULLISH.",
        ),
        "touches_band": condition(
            touches_band,
            "Aprobada: low <= band_max y high >= band_min.",
            "Rechazada: la vela no intersecta la banda EMA.",
        ),
        "ao_changed_to_green": condition(
            turns_green,
            "Aprobada: AO actual sube y el anterior no subía.",
            "Rechazada: AO no cambió de rojo a verde según el algoritmo.",
        ),
    }
    sell_conditions = {
        "trend_is_bearish": condition(
            trend == "BEARISH",
            "Aprobada: trend es BEARISH.",
            f"Rechazada: trend es {trend}, no BEARISH.",
        ),
        "touches_band": condition(
            touches_band,
            "Aprobada: low <= band_max y high >= band_min.",
            "Rechazada: la vela no intersecta la banda EMA.",
        ),
        "ao_changed_to_red": condition(
            turns_red,
            "Aprobada: AO actual baja y el anterior no bajaba.",
            "Rechazada: AO no cambió de verde a rojo según el algoritmo.",
        ),
    }

    return {
        "time_utc": row["time"].isoformat(),
        "ohlc": {
            name: round(float(row[name]), digits)
            for name in ("open", "high", "low", "close")
        },
        "emas": {
            f"ema_{period}": float(row[f"ema_{period}"])
            for period in EMA_PERIODS
        },
        "ema_order": {
            "bullish_order_approved": all(
                item["approved"] for item in bullish_order_comparisons
            ),
            "bearish_order_approved": all(
                item["approved"] for item in bearish_order_comparisons
            ),
            "bullish_comparisons": bullish_order_comparisons,
            "bearish_comparisons": bearish_order_comparisons,
        },
        "ema_slopes": slopes,
        "band_min": float(row["band_bottom"]),
        "band_max": float(row["band_top"]),
        "low": round(float(row["low"]), digits),
        "high": round(float(row["high"]), digits),
        "touches_band": touches_band,
        "touches_band_comparison": {
            "low_lte_band_max": bool(row["low"] <= row["band_top"]),
            "high_gte_band_min": bool(row["high"] >= row["band_bottom"]),
        },
        "awesome_oscillator": float(row["ao"]),
        "awesome_oscillator_previous": float(previous["ao"]),
        "ao_color": str(row["ao_color"]),
        "ao_color_previous": str(previous["ao_color"]),
        "ao_changed_to_red": turns_red,
        "ao_changed_to_green": turns_green,
        "trend": trend,
        "base_signal": str(row["base_signal"]),
        "buy_conditions": buy_conditions,
        "sell_conditions": sell_conditions,
        "exact_result_reason": (
            "BUY_CANDIDATE: las tres condiciones BUY fueron aprobadas."
            if row["base_signal"] == "BUY_CANDIDATE"
            else "SELL_CANDIDATE: las tres condiciones SELL fueron aprobadas."
            if row["base_signal"] == "SELL_CANDIDATE"
            else "WAIT: al menos una condición de BUY y una de SELL fueron rechazadas."
        ),
    }


def main():
    if not mt5.initialize():
        raise RuntimeError(f"No se pudo conectar con MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        if account is None:
            raise RuntimeError(f"No se pudo leer la cuenta: {mt5.last_error()}")
        if not mt5.symbol_select(SYMBOL, True):
            raise RuntimeError(f"No se pudo activar {SYMBOL}: {mt5.last_error()}")
        symbol_info = mt5.symbol_info(SYMBOL)
        if symbol_info is None:
            raise RuntimeError(f"No se pudo leer {SYMBOL}: {mt5.last_error()}")

        rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, BARS)
        if rates is None or len(rates) < BARS:
            raise RuntimeError(
                f"No se obtuvieron {BARS} velas cerradas: {mt5.last_error()}"
            )
        dataframe = pd.DataFrame(rates)
        dataframe["time"] = pd.to_datetime(
            dataframe["time"],
            unit="s",
            utc=True,
        )
        dataframe = analyze(dataframe)

        indices = dataframe.index[dataframe["time"].isin(TARGET_TIMES)].tolist()
        found_times = set(dataframe.loc[indices, "time"])
        missing = TARGET_TIMES - found_times
        if missing:
            raise RuntimeError(
                "No se localizaron estas velas: "
                + ", ".join(sorted(timestamp.isoformat() for timestamp in missing))
            )

        document = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "server": account.server,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME_NAME,
            "bars_downloaded": len(dataframe),
            "excluded_active_candle": True,
            "strategy_functions_used": [
                "calculate_trend",
                "calculate_awesome_oscillator",
                "generate_base_signal",
            ],
            "candles": [
                build_candle_diagnostic(dataframe, index, symbol_info.digits)
                for index in indices
            ],
        }
        OUTPUT.parent.mkdir(exist_ok=True)
        with OUTPUT.open("w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"Diagnóstico exportado: {OUTPUT}")
        for candle in document["candles"]:
            print(
                f"{candle['time_utc']} | trend={candle['trend']} | "
                f"touches_band={candle['touches_band']} | "
                f"AO={candle['ao_color_previous']}→{candle['ao_color']} | "
                f"turn_red={candle['ao_changed_to_red']} | "
                f"signal={candle['base_signal']}"
            )
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
