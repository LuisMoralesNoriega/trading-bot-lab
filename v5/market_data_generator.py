import json
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd


class MarketDataGenerator:
    def __init__(self, symbol="BTCUSD-T", timeframe=mt5.TIMEFRAME_M30, timeframe_name="M30", bars=5000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.timeframe_name = timeframe_name
        self.bars = bars

    def generate_market_data_file(self, output_path="v5/market_data.json", candles_to_export=20):
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, self.bars)
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")

        for period in [30, 35, 40, 45, 50, 60]:
            df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean().round(3)

        df["sma_200"] = df["close"].rolling(window=200).mean().round(3)

        median_price = (df["high"] + df["low"]) / 2
        sma_5 = median_price.rolling(window=5).mean()
        sma_34 = median_price.rolling(window=34).mean()
        df["ao"] = (sma_5 - sma_34).round(3)

        tick = mt5.symbol_info_tick(self.symbol)

        ultimas_velas = df.tail(candles_to_export).copy()
        ultimo_indice = ultimas_velas.index[-1]

        candles = []
        ao_prev = None

        for idx, row in ultimas_velas.iterrows():
            ao_actual = None if pd.isna(row["ao"]) else round(float(row["ao"]), 3)

            if ao_actual is None or ao_prev is None:
                ao_color = None
            else:
                ao_color = "green" if ao_actual > ao_prev else "red" if ao_actual < ao_prev else "neutral"

            candle = {
                "time": row["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "ema_30": round(float(row["ema_30"]), 3),
                "ema_35": round(float(row["ema_35"]), 3),
                "ema_40": round(float(row["ema_40"]), 3),
                "ema_45": round(float(row["ema_45"]), 3),
                "ema_50": round(float(row["ema_50"]), 3),
                "ema_60": round(float(row["ema_60"]), 3),
                "ema_band_top": round(max(float(row["ema_30"]), float(row["ema_60"])), 3),
                "ema_band_bottom": round(min(float(row["ema_30"]), float(row["ema_60"])), 3),
                "sma_200": None if pd.isna(row["sma_200"]) else round(float(row["sma_200"]), 3),
                "ao": ao_actual,
                "ao_color": ao_color,
                "ao_above_zero": None if ao_actual is None else ao_actual > 0,
                "is_live": idx == ultimo_indice
            }

            candles.append(candle)
            ao_prev = ao_actual

        data = {
            "symbol": self.symbol,
            "timeframe": self.timeframe_name,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "current_price": {
                "bid": round(float(tick.bid), 2),
                "ask": round(float(tick.ask), 2)
            },
            "candles": candles
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Archivo generado en: {output_path}")