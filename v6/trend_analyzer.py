import pandas as pd


class TrendAnalyzer:

    EMA_PERIODS = [30, 35, 40, 45, 50, 60]

    def add_emas(self, df: pd.DataFrame):

        for period in self.EMA_PERIODS:
            df[f"ema_{period}"] = (
                df["close"]
                .ewm(span=period, adjust=False)
                .mean()
            )

        return df

    def is_bullish_trend(self, candle):

        return (
            candle["ema_30"] >
            candle["ema_35"] >
            candle["ema_40"] >
            candle["ema_45"] >
            candle["ema_50"] >
            candle["ema_60"]
        )

    def is_bearish_trend(self, candle):

        return (
            candle["ema_30"] <
            candle["ema_35"] <
            candle["ema_40"] <
            candle["ema_45"] <
            candle["ema_50"] <
            candle["ema_60"]
        )

    def analyze_trend(self, df: pd.DataFrame):

        df = self.add_emas(df)
        df = self.add_ao(df)

        candles = df.tail(10)

        bullish_count = 0
        bearish_count = 0

        for _, candle in candles.iterrows():

            if self.is_bullish_trend(candle):
                bullish_count += 1

            if self.is_bearish_trend(candle):
                bearish_count += 1

        last = candles.iloc[-1]
        first = candles.iloc[0]

        price_near_band = self.is_price_near_ema_band(last)

        ao_green = last["ao"] > last["ao_prev"]
        ao_red = last["ao"] < last["ao_prev"]

        ema30_up = last["ema_30"] > first["ema_30"]
        ema60_up = last["ema_60"] > first["ema_60"]

        ema30_down = last["ema_30"] < first["ema_30"]
        ema60_down = last["ema_60"] < first["ema_60"]

        bullish = bullish_count >= 7 and ema30_up and ema60_up
        bearish = bearish_count >= 7 and ema30_down and ema60_down

        setup = "NO_TRADE"

        if bullish:
            if not price_near_band:
                setup = "WAIT_PULLBACK"
            elif ao_green:
                setup = "READY_BUY"
            else:
                setup = "WAIT_CONFIRMATION"

        elif bearish:
            if not price_near_band:
                setup = "WAIT_PULLBACK"
            elif ao_red:
                setup = "READY_SELL"
            else:
                setup = "WAIT_CONFIRMATION"
        
        entry = None
        sl = None
        tp = None
        rr = None

        if setup in ["READY_BUY", "READY_SELL"]:
            entry, sl, tp, rr = self.calculate_sl_tp(
                trend="BULLISH" if bullish else "BEARISH",
                df=df
            )

        if bullish:
            return "BULLISH", price_near_band, setup, entry, sl, tp, rr

        if bearish:
            return "BEARISH", price_near_band, setup, entry, sl, tp, rr

        return "NEUTRAL", price_near_band, setup, entry, sl, tp, rr
    
    def is_price_near_ema_band(self, candle):

        band_top = max(candle["ema_30"], candle["ema_60"])
        band_bottom = min(candle["ema_30"], candle["ema_60"])

        close_inside_band = band_bottom <= candle["close"] <= band_top

        candle_touches_band = (
            candle["high"] >= band_bottom and
            candle["low"] <= band_top
        )

        return close_inside_band or candle_touches_band
    
    def add_ao(self, df: pd.DataFrame):

        median_price = (df["high"] + df["low"]) / 2

        sma_5 = median_price.rolling(window=5).mean()
        sma_34 = median_price.rolling(window=34).mean()

        df["ao"] = sma_5 - sma_34
        df["ao_prev"] = df["ao"].shift(1)

        return df
    
    def calculate_sl_tp(self, trend, df: pd.DataFrame):

        candles = df.tail(6)
        last = candles.iloc[-1]
        recent = candles.iloc[:-1]

        if trend == "BULLISH":
            entry = last["close"]
            swing_low = recent["low"].min()
            sl = swing_low
            risk = entry - sl
            tp = entry + (risk * 2)

        elif trend == "BEARISH":
            entry = last["close"]
            swing_high = recent["high"].max()
            sl = swing_high
            risk = sl - entry
            tp = entry - (risk * 2)

        else:
            return None, None, None, None

        rr = 2.0

        return entry, sl, tp, rr