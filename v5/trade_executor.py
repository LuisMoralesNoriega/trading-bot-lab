import MetaTrader5 as mt5


class TradeExecutor:
    def __init__(
        self,
        symbol,
        magic_number=20260428,
        deviation=20,
        risk_percent=5,
        sl_buffer_points=100,
        max_total_risk_percent=30
    ):
        self.symbol = symbol
        self.magic_number = magic_number
        self.deviation = deviation
        self.risk_percent = risk_percent
        self.sl_buffer_points = sl_buffer_points
        self.max_total_risk_percent = max_total_risk_percent

    def has_open_position(self):
        positions = mt5.positions_get(symbol=self.symbol)
        if not positions:
            return False

        for pos in positions:
            if getattr(pos, "magic", 0) == self.magic_number:
                return True

        return False

    def get_tick(self):
        mt5.symbol_select(self.symbol, True)
        tick = mt5.symbol_info_tick(self.symbol)

        if tick is None or tick.bid <= 0 or tick.ask <= 0:
            raise ValueError(f"No se pudo obtener tick válido para {self.symbol}")

        return tick

    def calculate_volume_by_risk(self, entry_price, sl_price, risk_percent=5):
        account_info = mt5.account_info()
        symbol_info = mt5.symbol_info(self.symbol)

        if account_info is None:
            raise ValueError("No se pudo obtener account_info")

        if symbol_info is None:
            raise ValueError(f"No se pudo obtener symbol_info para {self.symbol}")

        balance = account_info.balance
        risk_usd = balance * (risk_percent / 100.0)

        distance = abs(entry_price - sl_price)
        if distance <= 0:
            raise ValueError("La distancia entre entrada y SL debe ser mayor que 0")

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size

        if tick_value <= 0 or tick_size <= 0:
            raise ValueError("tick_value o tick_size inválidos")

        cost_per_lot = (distance / tick_size) * tick_value
        if cost_per_lot <= 0:
            raise ValueError("No se pudo calcular el costo por lote")

        volume = risk_usd / cost_per_lot

        volume_min = symbol_info.volume_min
        volume_max = symbol_info.volume_max
        volume_step = symbol_info.volume_step

        volume = max(volume_min, min(volume, volume_max))
        volume = round(volume / volume_step) * volume_step
        volume = round(volume, 2)

        return volume

    def calculate_sl_tp_from_swing(self, signal, market_data, rr_ratio=2.0):
        closed_candles = [c for c in market_data["candles"] if not c["is_live"]]
        live_candle = next((c for c in market_data["candles"] if c["is_live"]), None)

        if len(closed_candles) < 5:
            raise ValueError("No hay suficientes velas cerradas para calcular swing")

        recent = closed_candles[-5:]
        tick = self.get_tick()
        symbol_info = mt5.symbol_info(self.symbol)

        if symbol_info is None:
            raise ValueError(f"No se pudo obtener symbol_info para {self.symbol}")

        point = symbol_info.point
        buffer_distance = self.sl_buffer_points * point

        recent_low = min(c["low"] for c in recent)
        recent_high = max(c["high"] for c in recent)

        live_low = live_candle["low"] if live_candle else recent_low
        live_high = live_candle["high"] if live_candle else recent_high

        if signal == "BUY":
            entry_price = tick.ask
            swing_low = min(recent_low, live_low)
            sl = swing_low - buffer_distance
            risk = entry_price - sl

            if risk <= 0:
                raise ValueError("Riesgo inválido para BUY")

            tp = entry_price + (risk * rr_ratio)

        else:
            entry_price = tick.bid
            swing_high = max(recent_high, live_high)
            sl = swing_high + buffer_distance
            risk = sl - entry_price

            if risk <= 0:
                raise ValueError("Riesgo inválido para SELL")

            tp = entry_price - (risk * rr_ratio)

        return entry_price, sl, tp

    def calculate_position_risk_usd(self, symbol, volume, entry_price, sl_price):
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.0

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size

        if tick_value <= 0 or tick_size <= 0:
            return 0.0

        distance = abs(entry_price - sl_price)
        cost_per_lot = (distance / tick_size) * tick_value
        return cost_per_lot * volume

    def get_total_open_risk_usd(self):
        positions = mt5.positions_get()
        if not positions:
            return 0.0

        total_risk = 0.0

        for pos in positions:
            if getattr(pos, "magic", 0) != self.magic_number:
                continue

            sl = getattr(pos, "sl", 0.0)
            if sl is None or sl == 0:
                continue

            risk_usd = self.calculate_position_risk_usd(
                symbol=pos.symbol,
                volume=pos.volume,
                entry_price=pos.price_open,
                sl_price=sl
            )
            total_risk += risk_usd

        return total_risk

    def send_order(self, signal, market_data):
        if signal not in ["BUY", "SELL"]:
            print("⚠️ Señal inválida para ejecutar orden")
            return None

        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            raise ValueError(f"No se pudo obtener symbol_info para {self.symbol}")

        if not symbol_info.visible:
            if not mt5.symbol_select(self.symbol, True):
                raise ValueError(f"No se pudo seleccionar el símbolo {self.symbol}")

        order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL

        entry_price, sl, tp = self.calculate_sl_tp_from_swing(
            signal=signal,
            market_data=market_data,
            rr_ratio=2.0
        )

        volume = self.calculate_volume_by_risk(
            entry_price=entry_price,
            sl_price=sl,
            risk_percent=self.risk_percent
        )

        new_trade_risk_usd = self.calculate_position_risk_usd(
            symbol=self.symbol,
            volume=volume,
            entry_price=entry_price,
            sl_price=sl
        )

        account_info = mt5.account_info()
        if account_info is None:
            raise ValueError("No se pudo obtener account_info")

        balance = account_info.balance
        max_total_risk_usd = balance * (self.max_total_risk_percent / 100.0)
        current_total_risk_usd = self.get_total_open_risk_usd()

        if current_total_risk_usd + new_trade_risk_usd > max_total_risk_usd:
            print("⚠️ Riesgo total excedido, no se abre nueva operación")
            print(f"📌 Riesgo abierto actual: {current_total_risk_usd:.2f} USD")
            print(f"📌 Riesgo nueva operación: {new_trade_risk_usd:.2f} USD")
            print(f"📌 Riesgo máximo permitido: {max_total_risk_usd:.2f} USD")
            return None

        digits = symbol_info.digits
        entry_price = round(entry_price, digits)
        sl = round(sl, digits)
        tp = round(tp, digits)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": self.deviation,
            "magic": self.magic_number,
            "comment": f"V5 {signal}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC
        }

        print(f"📌 Volumen calculado: {volume}")
        print(f"📌 Entry: {entry_price} | SL: {sl} | TP: {tp}")

        result = mt5.order_send(request)

        if result is None:
            print("❌ order_send devolvió None")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error al abrir orden: {result.retcode} | {result.comment}")
        else:
            print(f"✅ Orden ejecutada correctamente: {signal}")

        return result