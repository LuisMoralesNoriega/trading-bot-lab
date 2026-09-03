import numpy as np

from config import AO_FAST_PERIOD, AO_SLOW_PERIOD, EMA_PERIODS, SLOPE_BARS



def calculate_trend(dataframe):
    dataframe = dataframe.copy()

    for period in EMA_PERIODS:
        dataframe[f"ema_{period}"] = (
            dataframe["close"]
            .ewm(span=period, adjust=False)
            .mean()
        )

    bullish_order = np.logical_and.reduce([
        dataframe[f"ema_{short}"] > dataframe[f"ema_{long}"]
        for short, long in zip(EMA_PERIODS, EMA_PERIODS[1:])
    ])

    bearish_order = np.logical_and.reduce([
        dataframe[f"ema_{short}"] < dataframe[f"ema_{long}"]
        for short, long in zip(EMA_PERIODS, EMA_PERIODS[1:])
    ])

    bullish_slope = np.logical_and.reduce([
        dataframe[f"ema_{period}"]
        > dataframe[f"ema_{period}"].shift(SLOPE_BARS)
        for period in EMA_PERIODS
    ])

    bearish_slope = np.logical_and.reduce([
        dataframe[f"ema_{period}"]
        < dataframe[f"ema_{period}"].shift(SLOPE_BARS)
        for period in EMA_PERIODS
    ])

    dataframe["trend"] = np.select(
        [
            bullish_order & bullish_slope,
            bearish_order & bearish_slope,
        ],
        [
            "BULLISH",
            "BEARISH",
        ],
        default="LATERAL",
    )

    ema_columns = [f"ema_{period}" for period in EMA_PERIODS]

    dataframe["band_top"] = dataframe[ema_columns].max(axis=1)
    dataframe["band_bottom"] = dataframe[ema_columns].min(axis=1)

    dataframe["touches_band"] = (
        (dataframe["low"] <= dataframe["band_top"])
        & (dataframe["high"] >= dataframe["band_bottom"])
    )

    return dataframe


def calculate_awesome_oscillator(dataframe):
    dataframe = dataframe.copy()

    median_price = (
        dataframe["high"] + dataframe["low"]
    ) / 2

    dataframe["ao"] = (
        median_price.rolling(AO_FAST_PERIOD).mean()
        - median_price.rolling(AO_SLOW_PERIOD).mean()
    )

    dataframe["ao_color"] = np.select(
        [
            dataframe["ao"] > dataframe["ao"].shift(1),
            dataframe["ao"] < dataframe["ao"].shift(1),
        ],
        [
            "GREEN",
            "RED",
        ],
        default="FLAT",
    )

    dataframe["ao_turn_green"] = (
        (dataframe["ao"] > dataframe["ao"].shift(1))
        & (
            dataframe["ao"].shift(1)
            <= dataframe["ao"].shift(2)
        )
    )

    dataframe["ao_turn_red"] = (
        (dataframe["ao"] < dataframe["ao"].shift(1))
        & (
            dataframe["ao"].shift(1)
            >= dataframe["ao"].shift(2)
        )
    )

    return dataframe


def generate_base_signal(dataframe):
    dataframe = dataframe.copy()

    dataframe["base_signal"] = np.select(
        [
            (dataframe["trend"] == "BULLISH")
            & dataframe["touches_band"]
            & dataframe["ao_turn_green"],
            (dataframe["trend"] == "BEARISH")
            & dataframe["touches_band"]
            & dataframe["ao_turn_red"],
        ],
        [
            "BUY_CANDIDATE",
            "SELL_CANDIDATE",
        ],
        default="WAIT",
    )

    return dataframe
