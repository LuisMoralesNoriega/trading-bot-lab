import MetaTrader5 as mt5
from helpers import ajustar_volumen_margen_y_restricciones

def ejecutar_orden(symbol, entrada, sl, tp, volumen=0.01, tipo="BUY"):
    print(f"📤 Ejecutando orden real: {tipo} para {symbol}")

    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"❌ No se pudo obtener info para {symbol}")
        return

    tick = mt5.symbol_info_tick(symbol)
    if tick is None or tick.bid == 0 or tick.ask == 0:
        print(f"❌ Error al obtener precio de mercado para {symbol}")
        return

    digits = info.digits
    price = round(tick.ask if tipo == "BUY" else tick.bid, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)

    stops_level = info.trade_stops_level * info.point
    margen_seguridad = 1.5
    min_distancia = stops_level * margen_seguridad

    if abs(price - sl) < min_distancia:
        sl = round(price - min_distancia if tipo == "BUY" else price + min_distancia, digits)
        print(f"⚠️ SL ajustado con margen de seguridad a {sl}")

    if abs(tp - price) < min_distancia:
        tp = round(price + min_distancia if tipo == "BUY" else price - min_distancia, digits)
        print(f"⚠️ TP ajustado con margen de seguridad a {tp}")

    volumen = ajustar_volumen_margen_y_restricciones(symbol, volumen)
    if volumen is None or volumen < 0.01:
        print("⚠️ Volumen no válido después del ajuste. No se ejecutará la orden.")
        return

    volumen = round(volumen, 2)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volumen,
        "type": mt5.ORDER_TYPE_BUY if tipo == "BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 300,
        "magic": 202506,
        "comment": f"bot-{tipo.lower()}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None:
        print(f"❌ Error crítico: no se pudo ejecutar la orden para {symbol}.")
        print(f"🧪 mt5.last_error(): {mt5.last_error()}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error al ejecutar orden: {result.retcode}")
        print(f"🧪 Detalles: {result}")
    else:
        print("✅ Orden ejecutada con éxito:")
        print(result)

    return result

def cerrar_orden(ticket):
    position = mt5.positions_get(ticket=ticket)
    if not position:
        print(f"⚠️ No se encontró posición con ticket {ticket}")
        return

    pos = position[0]
    tick = mt5.symbol_info_tick(pos.symbol)
    price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

    close_request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 300,
        "magic": 202506,
        "comment": "Cierre por TP/SL",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(close_request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Error al cerrar orden {ticket}: {result.retcode}")
        print(f"🧪 Detalles: {result}")
    else:
        print(f"✅ Orden {ticket} cerrada exitosamente")
    return result

def cerrar_posiciones_ganadoras(posiciones):
    for pos in posiciones:
        if pos.profit > 0:
            cerrar_orden(pos.ticket)