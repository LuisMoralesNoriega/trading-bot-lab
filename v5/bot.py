import time
from datetime import datetime

import MetaTrader5 as mt5

from market_data_generator import MarketDataGenerator
from market_analyzer import MarketAnalyzer
from trade_executor import TradeExecutor


SYMBOLS = ["BTCUSD-T", "AUDUSD-T", "USDCAD-T"]
TIMEFRAMES = [
    ("M1", mt5.TIMEFRAME_M1),
    ("M5", mt5.TIMEFRAME_M5),
    ("M15", mt5.TIMEFRAME_M15),
]
BARS = 5000
CANDLES_TO_EXPORT = 20
REAL_MODE = True
SLEEP_SECONDS = 30
COOLDOWN_CANDLES = 5


def timeframe_to_minutes(timeframe):
    mapping = {
        mt5.TIMEFRAME_M1: 1,
        mt5.TIMEFRAME_M5: 5,
        mt5.TIMEFRAME_M15: 15,
        mt5.TIMEFRAME_M30: 30,
        mt5.TIMEFRAME_H1: 60,
    }
    return mapping.get(timeframe, 5)


def main():
    if not mt5.initialize():
        print("❌ No se pudo inicializar MT5")
        return

    last_processed_candle_time = {}
    last_trade_candle_time = {}

    try:
        while True:
            print("\n==============================")
            print("🔄 Nueva iteración del bot")

            for symbol in SYMBOLS:
                for timeframe_name, timeframe in TIMEFRAMES:
                    key = f"{symbol}_{timeframe_name}"

                    print(f"\n########## {symbol} | {timeframe_name} ##########")

                    generator = MarketDataGenerator(
                        symbol=symbol,
                        timeframe=timeframe,
                        timeframe_name=timeframe_name,
                        bars=BARS
                    )

                    executor = TradeExecutor(
                        symbol=symbol,
                        magic_number=20260428,
                        deviation=20,
                        risk_percent=5,
                        sl_buffer_points=100,
                        max_total_risk_percent=30
                    )

                    output_path = f"v5/{symbol}_{timeframe_name}_market_data.json"

                    generator.generate_market_data_file(
                        output_path=output_path,
                        candles_to_export=CANDLES_TO_EXPORT
                    )

                    analyzer = MarketAnalyzer(input_path=output_path)
                    analyzer.load_data()
                    result = analyzer.analyze()

                    current_candle_time = result["last_closed_time"]
                    prev_candle_time = last_processed_candle_time.get(key)
                    new_closed_candle = current_candle_time != prev_candle_time

                    if new_closed_candle:
                        print(f"🆕 Nueva vela cerrada detectada para {symbol} {timeframe_name}: {current_candle_time}")
                        last_processed_candle_time[key] = current_candle_time
                    else:
                        print(f"⏱️ Misma vela cerrada para {symbol} {timeframe_name} ({current_candle_time}), analizando vela viva...")

                    print("=== RESULTADO ANALISIS ===")
                    for k, value in result.items():
                        print(f"{k}: {value}")

                    signal = result["signal"]

                    if REAL_MODE and signal in ["BUY", "SELL"]:
                        can_trade_symbol_tf = True

                        if key in last_trade_candle_time:
                            current_dt = datetime.strptime(current_candle_time, "%Y-%m-%d %H:%M:%S")
                            last_trade_dt = datetime.strptime(last_trade_candle_time[key], "%Y-%m-%d %H:%M:%S")

                            timeframe_minutes = timeframe_to_minutes(timeframe)
                            candles_passed = int(
                                (current_dt - last_trade_dt).total_seconds() // (timeframe_minutes * 60)
                            )

                            if candles_passed < COOLDOWN_CANDLES:
                                can_trade_symbol_tf = False
                                print(f"⏳ Cooldown activo para {symbol} {timeframe_name}: {candles_passed}/{COOLDOWN_CANDLES} velas")

                        if can_trade_symbol_tf:
                            print(f"🚀 Ejecutando orden {signal} en demo para {symbol} {timeframe_name}...")
                            order_result = executor.send_order(signal, analyzer.data)

                            if order_result is None:
                                print("⚠️ No se ejecutó orden")
                            else:
                                print("=== RESULTADO ORDEN ===")
                                print(order_result)

                                if order_result.retcode == mt5.TRADE_RETCODE_DONE:
                                    last_trade_candle_time[key] = current_candle_time
                        else:
                            print("ℹ️ Señal válida, pero símbolo/timeframe en cooldown")
                    else:
                        print("ℹ️ No hay orden para ejecutar")

            time.sleep(SLEEP_SECONDS)

    except KeyboardInterrupt:
        print("\n⛔ Bot detenido manualmente")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()