import MetaTrader5 as mt5

symbol = "USDJPY-T"

if not mt5.initialize():
    print("❌ No se pudo iniciar MT5")
else:
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"❌ No se encontró el símbolo: {symbol}")
    else:
        print(f"✅ Símbolo encontrado: {symbol}")
        print(f"🔁 Trade permitido: {info.trade_mode}, Visible: {info.visible}")
        if not info.visible or info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
            print("⚠️ El símbolo no está habilitado para trading.")
