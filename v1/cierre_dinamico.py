
import MetaTrader5 as mt5
import time
import threading

pico_maximo = 0
monitoreo_activo = False

def obtener_beneficio_total():
    posiciones = mt5.positions_get()
    if not posiciones:
        return 0.0
    return sum(p.profit for p in posiciones if pos.profit > 0)

def cerrar_posiciones_ganadoras():
    posiciones = mt5.positions_get()
    if not posiciones:
        print("📭 No hay posiciones abiertas para cerrar.")
        return

    cerradas = 0
    for pos in posiciones:
        if pos.profit <= 0:
            continue  # Solo cerramos ganadoras

        tipo = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": tipo,
            "price": price,
            "deviation": 300,
            "magic": 202506,
            "comment": "Cierre por trailing dinámico",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(close_request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"✅ Orden {pos.ticket} cerrada exitosamente")
            cerradas += 1
        else:
            print(f"❌ Error al cerrar orden {pos.ticket}: {result.retcode}")

    print(f"🔚 Cierre total completado. {cerradas} posiciones ganadoras cerradas.")

def control_cierre_dinamico(trailing_piso=20.0, intervalo=60):
    global pico_maximo, monitoreo_activo
    if monitoreo_activo:
        return  # Evita que se lancen múltiples hilos

    monitoreo_activo = True
    print(f"📊 Hilo de control de beneficio activo. Piso mínimo ${trailing_piso} cada {intervalo}s...")

    def loop():
        global pico_maximo, monitoreo_activo
        while True:
            beneficio_total = obtener_beneficio_total()
            beneficio_total = round(beneficio_total, 2)

            if beneficio_total > pico_maximo:
                pico_maximo = beneficio_total
                print(f"🔼 Nuevo pico de beneficio: ${pico_maximo}")

            piso_dinamico = max(trailing_piso, pico_maximo)
            if beneficio_total < piso_dinamico:
                print(f"🚨 Retroceso: bajó de ${pico_maximo} a ${beneficio_total}. Ejecutando cierre...")
                cerrar_posiciones_ganadoras()
                pico_maximo = 0
                monitoreo_activo = False
                break

            print(f"⏳ Beneficio actual: ${beneficio_total} — Piso dinámico: ${pico_maximo}")
            time.sleep(intervalo)

    threading.Thread(target=loop, daemon=True).start()
