import time

import MetaTrader5 as mt5
import pandas as pd
import csv
from datetime import datetime

from trend_analyzer import TrendAnalyzer

TRADES_LOG_FILE = "v6/trades_log.csv"

SYMBOLS = ["BTCUSD-T", "AUDUSD-T", "USDCAD-T", "NZDUSD-T", "USDCHF-T", "EURGBP-T", "EURJPY-T", "GBPJPY-T", "SOLUSD-T"]

TIMEFRAME = mt5.TIMEFRAME_M15
BARS = 5000
RISK_PERCENT = 1

MAGIC_NUMBER = 20260512
DEVIATION = 20
REAL_MODE = True
SLEEP_SECONDS = 120


def get_market_data(symbol):

    rates = mt5.copy_rates_from_pos(
        symbol,
        TIMEFRAME,
        0,
        BARS
    )

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")

    return df


def calculate_volume_by_risk(symbol, entry, sl):

    if entry is None or sl is None:
        return None, None

    account_info = mt5.account_info()
    symbol_info = mt5.symbol_info(symbol)

    if account_info is None or symbol_info is None:
        return None, None

    balance = account_info.balance
    risk_amount = balance * (RISK_PERCENT / 100)

    distance = abs(entry - sl)

    if distance <= 0:
        return None, None

    tick_value = symbol_info.trade_tick_value
    tick_size = symbol_info.trade_tick_size

    cost_per_lot = (distance / tick_size) * tick_value

    if cost_per_lot <= 0:
        return None, None

    volume = risk_amount / cost_per_lot

    volume = max(symbol_info.volume_min, min(volume, symbol_info.volume_max))
    volume = round(volume / symbol_info.volume_step) * symbol_info.volume_step
    volume = round(volume, 2)

    return risk_amount, volume


def has_open_position(symbol):

    positions = mt5.positions_get(symbol=symbol)

    if not positions:
        return False

    for position in positions:
        if position.magic == MAGIC_NUMBER:
            return True

    return False


def send_order(symbol, setup, volume, sl, tp):

    if setup not in ["READY_BUY", "READY_SELL"]:
        print("ℹ️ Setup no listo. No se ejecuta orden.")
        return None

    if volume is None or sl is None or tp is None:
        print("⚠️ Datos incompletos. No se ejecuta orden.")
        return None

    if has_open_position(symbol):
        print("⚠️ Ya existe una operación abierta para este símbolo.")
        return None

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:
        print("❌ No se pudo obtener información del símbolo.")
        return None

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print("❌ No se pudo seleccionar el símbolo.")
            return None

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        print("❌ No se pudo obtener el precio actual.")
        return None

    if setup == "READY_BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        comment = "V6 BUY"
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        comment = "V6 SELL"
    
    if setup == "READY_BUY":
        risk = price - sl

        if risk <= 0:
            print("⚠️ SL inválido para BUY. No se ejecuta orden.")
            return None

        tp = price + (risk * 2)

    else:
        risk = sl - price

        if risk <= 0:
            print("⚠️ SL inválido para SELL. No se ejecuta orden.")
            return None

        tp = price - (risk * 2)

    digits = symbol_info.digits

    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    print("=== ORDER REQUEST ===")
    print(request)

    if not REAL_MODE:
        print("🧪 REAL_MODE = False. Orden simulada, no enviada.")
        return None

    result = mt5.order_send(request)

    if result is None:
        print("❌ order_send devolvió None")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error al abrir orden: {result.retcode} | {result.comment}")
    else:
        print(f"✅ Orden ejecutada correctamente en {symbol}")

    return result

def log_trade_decision(symbol, setup, trend, entry, sl, tp, volume, df):

    last = df.iloc[-1]

    tick = mt5.symbol_info_tick(symbol)

    bid = tick.bid if tick else None
    ask = tick.ask if tick else None

    file_exists = False

    try:
        with open(TRADES_LOG_FILE, "r", encoding="utf-8"):
            file_exists = True
    except FileNotFoundError:
        pass

    with open(TRADES_LOG_FILE, "a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "datetime",
                "symbol",
                "setup",
                "trend",
                "candle_time",
                "open",
                "high",
                "low",
                "close",
                "bid",
                "ask",
                "ema_30",
                "ema_35",
                "ema_40",
                "ema_45",
                "ema_50",
                "ema_60",
                "ao",
                "ao_prev",
                "entry",
                "sl",
                "tp",
                "volume"
            ])

        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            symbol,
            setup,
            trend,
            last["time"],
            last["open"],
            last["high"],
            last["low"],
            last["close"],
            bid,
            ask,
            last["ema_30"],
            last["ema_35"],
            last["ema_40"],
            last["ema_45"],
            last["ema_50"],
            last["ema_60"],
            last["ao"],
            last["ao_prev"],
            entry,
            sl,
            tp,
            volume
        ])

def process_symbol(symbol, analyzer):

    print("")
    print("====================")
    print(f"SYMBOL: {symbol}")

    try:
        df = get_market_data(symbol)

        df_debug = analyzer.add_emas(df.copy())
        df_debug = analyzer.add_ao(df_debug)

        last = df_debug.iloc[-1]

        tick = mt5.symbol_info_tick(symbol)
        bid = tick.bid if tick else None
        ask = tick.ask if tick else None

        band_top = max(last["ema_30"], last["ema_60"])
        band_bottom = min(last["ema_30"], last["ema_60"])

        print("=== LIVE DATA DEBUG ===")
        print(f"CANDLE TIME: {last['time']}")
        print(f"CANDLE OPEN: {last['open']}")
        print(f"CANDLE HIGH: {last['high']}")
        print(f"CANDLE LOW: {last['low']}")
        print(f"CANDLE CLOSE: {last['close']}")
        print(f"BID: {bid}")
        print(f"ASK: {ask}")
        print(f"EMA30: {last['ema_30']}")
        print(f"EMA35: {last['ema_35']}")
        print(f"EMA40: {last['ema_40']}")
        print(f"EMA45: {last['ema_45']}")
        print(f"EMA50: {last['ema_50']}")
        print(f"EMA60: {last['ema_60']}")
        print(f"EMA BAND BOTTOM: {band_bottom}")
        print(f"EMA BAND TOP: {band_top}")
        print(f"AO: {last['ao']}")
        print(f"AO_PREV: {last['ao_prev']}")
        print("=======================")

        trend, price_near_band, setup, entry, sl, tp, rr = analyzer.analyze_trend(df)
        risk_amount, volume = calculate_volume_by_risk(symbol, entry, sl)

        print(f"TREND: {trend}")
        print(f"PRICE NEAR EMA BAND: {price_near_band}")
        print(f"SETUP: {setup}")
        print(f"ENTRY: {entry}")
        print(f"SL: {sl}")
        print(f"TP: {tp}")
        print(f"RR: {rr}")
        print(f"RISK_PERCENT: {RISK_PERCENT}")
        print(f"RISK_AMOUNT: {risk_amount}")
        print(f"VOLUME: {volume}")

        if setup in ["READY_BUY", "READY_SELL"]:
            df_debug = analyzer.add_emas(df.copy())
            df_debug = analyzer.add_ao(df_debug)

            log_trade_decision(
                symbol=symbol,
                setup=setup,
                trend=trend,
                entry=entry,
                sl=sl,
                tp=tp,
                volume=volume,
                df=df_debug
            )

        if setup in ["READY_BUY", "READY_SELL"]:

            if not is_current_price_inside_band(symbol, setup, df, analyzer):
                print("⚠️ Precio actual fuera de la banda EMA. No se ejecuta orden.")
                return

        send_order(symbol, setup, volume, sl, tp)

    except Exception as e:
        print(f"❌ Error procesando {symbol}: {e}")

    print("====================")

def is_current_price_inside_band(symbol, setup, df, analyzer):

    df = analyzer.add_emas(df.copy())
    last = df.iloc[-1]

    band_top = max(last["ema_30"], last["ema_60"])
    band_bottom = min(last["ema_30"], last["ema_60"])

    tick = mt5.symbol_info_tick(symbol)

    if tick is None:
        return False

    current_price = tick.ask if setup == "READY_BUY" else tick.bid

    print(f"CURRENT PRICE: {current_price}")
    print(f"EMA BAND BOTTOM: {band_bottom}")
    print(f"EMA BAND TOP: {band_top}")

    return band_bottom <= current_price <= band_top

def main():

    if not mt5.initialize():
        print("❌ Error iniciando MT5")
        return

    analyzer = TrendAnalyzer()

    try:
        while True:

            print("")
            print("################################")
            print("🔄 Nueva revisión del mercado")
            print("################################")

            for symbol in SYMBOLS:
                process_symbol(symbol, analyzer)

            print(f"⏳ Esperando {SLEEP_SECONDS} segundos...")
            time.sleep(SLEEP_SECONDS)

    except KeyboardInterrupt:
        print("")
        print("⛔ Bot detenido manualmente")

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()