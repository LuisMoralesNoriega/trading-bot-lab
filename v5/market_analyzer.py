import json


class MarketAnalyzer:
    def __init__(self, input_path="v5/market_data.json"):
        self.input_path = input_path
        self.data = None
        self.closed_candles = []

    def load_data(self):
        with open(self.input_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.closed_candles = [
            candle for candle in self.data["candles"]
            if not candle["is_live"]
        ]

    def _is_bullish_alignment(self, candle):
        return (
            candle["ema_30"] > candle["ema_35"] > candle["ema_40"] >
            candle["ema_45"] > candle["ema_50"] > candle["ema_60"]
        )

    def _is_bearish_alignment(self, candle):
        return (
            candle["ema_30"] < candle["ema_35"] < candle["ema_40"] <
            candle["ema_45"] < candle["ema_50"] < candle["ema_60"]
        )

    def _is_above_sma_200(self, candle):
        return candle["close"] > candle["sma_200"]

    def _is_below_sma_200(self, candle):
        return candle["close"] < candle["sma_200"]

    def _is_inside_ema_band(self, candle):
        band_top = max(candle["ema_30"], candle["ema_60"])
        band_bottom = min(candle["ema_30"], candle["ema_60"])

        close_inside = band_bottom <= candle["close"] <= band_top
        range_touches_band = candle["high"] >= band_bottom and candle["low"] <= band_top

        return close_inside or range_touches_band

    def analyze(self):
        if len(self.closed_candles) < 10:
            raise ValueError("No hay suficientes velas cerradas para analizar.")

        last_10 = self.closed_candles[-10:]

        bullish_aligned_count = sum(1 for c in last_10 if self._is_bullish_alignment(c))
        bearish_aligned_count = sum(1 for c in last_10 if self._is_bearish_alignment(c))

        closes_above_sma_200 = sum(1 for c in last_10 if self._is_above_sma_200(c))
        closes_below_sma_200 = sum(1 for c in last_10 if self._is_below_sma_200(c))

        ema30_rising = last_10[-1]["ema_30"] > last_10[-6]["ema_30"]
        ema60_rising = last_10[-1]["ema_60"] > last_10[-6]["ema_60"]

        ema30_falling = last_10[-1]["ema_30"] < last_10[-6]["ema_30"]
        ema60_falling = last_10[-1]["ema_60"] < last_10[-6]["ema_60"]

        bullish_trend = bullish_aligned_count >= 7 and ema30_rising and ema60_rising
        bearish_trend = bearish_aligned_count >= 7 and ema30_falling and ema60_falling

        last_closed = self.closed_candles[-1]
        pullback_to_band = self._is_live_price_inside_band()

        ao_green = last_closed["ao_color"] == "green"
        ao_red = last_closed["ao_color"] == "red"
        ao_above_zero = last_closed["ao_above_zero"] is True
        ao_below_zero = last_closed["ao_above_zero"] is False

        signal = "NONE"
        trend = "NEUTRAL"
        setup_status = "NO_TREND"

        if bullish_trend:
            trend = "BULLISH"
            if not pullback_to_band:
                setup_status = "WAIT_PULLBACK"
            elif not (ao_green and ao_above_zero):
                setup_status = "WAIT_AO_CONFIRMATION"
            else:
                setup_status = "READY_BUY"
                signal = "BUY"

        elif bearish_trend:
            trend = "BEARISH"
            if not pullback_to_band:
                setup_status = "WAIT_PULLBACK"
            elif not (ao_red and ao_below_zero):
                setup_status = "WAIT_AO_CONFIRMATION"
            else:
                setup_status = "READY_SELL"
                signal = "SELL"

        return {
            "symbol": self.data["symbol"],
            "timeframe": self.data["timeframe"],
            "trend": trend,
            "signal": signal,
            "bullish_aligned_count": bullish_aligned_count,
            "bearish_aligned_count": bearish_aligned_count,
            "closes_above_sma_200": closes_above_sma_200,
            "closes_below_sma_200": closes_below_sma_200,
            "ema30_rising": ema30_rising,
            "ema60_rising": ema60_rising,
            "ema30_falling": ema30_falling,
            "ema60_falling": ema60_falling,
            "pullback_to_band": pullback_to_band,
            "ao_green": ao_green,
            "ao_red": ao_red,
            "ao_above_zero": ao_above_zero,
            "ao_below_zero": ao_below_zero,
            "setup_status": setup_status,
            "last_closed_time": last_closed["time"]
        }
    
    def _is_live_price_inside_band(self):
        live_candle = next((c for c in self.data["candles"] if c["is_live"]), None)
        if live_candle is None:
            return False

        current_bid = self.data["current_price"]["bid"]
        current_ask = self.data["current_price"]["ask"]
        current_price = (current_bid + current_ask) / 2

        band_top = live_candle["ema_band_top"]
        band_bottom = live_candle["ema_band_bottom"]

        price_inside = band_bottom <= current_price <= band_top
        range_touches_band = live_candle["high"] >= band_bottom and live_candle["low"] <= band_top

        return price_inside or range_touches_band