import csv
import os
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from ejecutor import cerrar_orden

def actualizar_resultado_operacion(symbol):
    archivo = "bitacora_operaciones.csv"
    if not os.path.exists(archivo):
        print("📭 No hay bitácora para actualizar.")
        return

    with open(archivo, mode="r", newline="") as f:
        reader = list(csv.DictReader(f))

    inicio = datetime.now() - timedelta(days=7)
    fin = datetime.now()
    historial = mt5.history_deals_get(inicio, fin)

    if historial is None:
        print("⚠️ No se pudo obtener historial de operaciones.")
        return

    historial_filtrado = [
        h for h in historial if h.symbol == symbol and h.comment.startswith("bot")
    ]

    actualizado = False

    for op in reader:
        if op["symbol"] != symbol:
            continue
        if op["resultado"] != "pendiente":
            continue
        if op["confirmada"] != "si":
            op["resultado"] = "rechazada"
            actualizado = True
            continue

        precio_entrada = float(op["precio_entrada"])
        sl = float(op["stop_loss"])
        tp = float(op["take_profit"])

        # Buscar match por precio de entrada y volumen
        match = next(
            (
                h for h in historial_filtrado
                if abs(h.price - precio_entrada) < 0.1 and abs(h.volume - float(op["volumen"])) < 0.001
            ),
            None
        )

        if match:
            precio_salida = match.price
            if match.type == mt5.ORDER_TYPE_BUY:
                resultado = "ganada" if precio_salida >= tp else "perdida" if precio_salida <= sl else "cerrada sin definir"
            else:
                resultado = "ganada" if precio_salida <= tp else "perdida" if precio_salida >= sl else "cerrada sin definir"
            op["resultado"] = resultado
            actualizado = True
        else:
            print(f"⏳ No se encontró coincidencia cerrada en historial para orden de {symbol} (entrada: {precio_entrada})")

    if actualizado:
        with open(archivo, mode="w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=reader[0].keys())
            writer.writeheader()
            writer.writerows(reader)
        print(f"🛠️ Resultados actualizados para {symbol}")
    else:
        print(f"⏳ No se detectaron cambios para {symbol}")


def verificar_ordenes_abiertas():
    posiciones = mt5.positions_get()
    if not posiciones:
        print("🔍 No hay posiciones abiertas.")
        return

    print("🔎 Verificando posiciones abiertas...")
    for pos in posiciones:
        symbol = pos.symbol
        ticket = pos.ticket
        sl = pos.sl
        tp = pos.tp
        current_price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

        if current_price <= sl or current_price >= tp:
            print(f"🔔 Condición de cierre detectada para {symbol}. Precio actual: {current_price:.2f}")
            cerrar_orden(ticket)
        else:
            print(f"⏳ {symbol} sigue abierto. Precio: {current_price:.2f} | TP: {tp} | SL: {sl}")
