import MetaTrader5 as mt5

def aplicar_trailing_stop(distancia_pct=0.5, trailing_buffer_pct=0.3):
    posiciones = mt5.positions_get()
    if not posiciones:
        print("📭 No hay posiciones abiertas para aplicar trailing stop.")
        return

    print("🔄 Aplicando Trailing Stop...")
    for pos in posiciones:
        symbol = pos.symbol
        entrada = pos.price_open
        sl_actual = pos.sl
        volumen = pos.volume
        ticket = pos.ticket
        tipo = pos.type

        precio_actual = mt5.symbol_info_tick(symbol).bid if tipo == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

        avance = (precio_actual - entrada) / entrada * 100 if tipo == mt5.ORDER_TYPE_BUY else (entrada - precio_actual) / entrada * 100

        if avance >= distancia_pct:
            nuevo_sl = precio_actual - (precio_actual * trailing_buffer_pct / 100) if tipo == mt5.ORDER_TYPE_BUY else precio_actual + (precio_actual * trailing_buffer_pct / 100)

            # Si el SL nuevo es más favorable que el actual, lo actualizamos
            if (tipo == mt5.ORDER_TYPE_BUY and nuevo_sl > sl_actual) or (tipo == mt5.ORDER_TYPE_SELL and nuevo_sl < sl_actual):
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "sl": nuevo_sl,
                    "tp": pos.tp,
                    "symbol": symbol,
                    "magic": 202506,
                    "comment": "Trailing SL"
                }
                result = mt5.order_send(request)

                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ SL actualizado para {symbol} a {nuevo_sl:.2f} (avance: {avance:.2f}%)")
                else:
                    print(f"❌ No se pudo actualizar SL para {symbol}: {result.retcode}")
            else:
                print(f"⏳ {symbol}: SL ya está en mejor nivel o no es necesario moverlo.")
        else:
            print(f"⏳ {symbol}: avance actual {avance:.2f}% aún no alcanza el mínimo requerido ({distancia_pct}%)")
