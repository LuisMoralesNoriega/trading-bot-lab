import csv
import os
import math
import MetaTrader5 as mt5
from datetime import datetime

# --- NUEVO BLOQUE: Margen libre mínimo por tipo de activo ---
MARGEN_MINIMO = {
    "forex": 20,
    "crypto": 30,
    "indice": 50,
    "default": 50
}

def clasificar_simbolo(symbol: str) -> str:
    symbol = symbol.lower()
    if symbol.endswith("usd-t") or symbol.endswith("eur-t") or symbol.endswith("jpy-t"):
        return "forex"
    if symbol in ["btcusd-t", "ethusd-t", "ltcusd-t", "xrpusd-t", "xlmusd-t", "etcusd-t", "adausd-t", "solusd-t"]:
        return "crypto"
    if "[" in symbol or "usa" in symbol or "jp225" in symbol or "spa35" in symbol or "ger40" in symbol:
        return "indice"
    return "default"

def tiene_margen_suficiente(symbol: str) -> bool:
    account = mt5.account_info()
    if account is None:
        print("❌ No se pudo obtener la información de la cuenta.")
        return False

    tipo = clasificar_simbolo(symbol)
    minimo = MARGEN_MINIMO.get(tipo, MARGEN_MINIMO["default"])
    if account.margin_free < minimo:
        print(f"🚫 Margen libre insuficiente (${account.margin_free:.2f}) para operar {symbol.upper()} (mínimo requerido: ${minimo})")
        return False

    return True

def ya_hay_demasiadas_posiciones(symbol, max_por_simbolo=2):
    posiciones = mt5.positions_get(symbol=symbol)
    return posiciones is not None and len(posiciones) >= max_por_simbolo

def verificar_ordenes_abiertas():
    print("\n📋 Verificando órdenes abiertas:")
    posiciones = mt5.positions_get()
    if posiciones is None or len(posiciones) == 0:
        print("📭 No hay posiciones abiertas.")
    else:
        for pos in posiciones:
            print(f"🔹 Símbolo: {pos.symbol}, Tipo: {'BUY' if pos.type == 0 else 'SELL'}, Volumen: {pos.volume}, Precio entrada: {pos.price_open}")

def registrar_operacion(symbol, entrada, sl, tp, volumen, estrategia="desconocida", confirmada="no"):
    archivo = "bitacora_operaciones.csv"
    entrada = round(entrada, 2)
    tp = round(tp, 2)
    sl = round(sl, 2)
    volumen = round(volumen, 2)

    if os.path.isfile(archivo):
        with open(archivo, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if (
                    row["symbol"] == symbol and
                    row["estrategia"] == estrategia and
                    abs(float(row["precio_entrada"]) - entrada) < 0.1 and
                    abs(float(row["volumen"]) - volumen) < 0.001 and
                    row["resultado"] in ["pendiente", "rechazada"]
                ):
                    print(f"⚠️ Ya existe una operación similar ({row['resultado']}) para {symbol}. No se registrará de nuevo.")
                    return

    timestamp = mt5.symbol_info_tick(symbol).time
    fecha_servidor = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
    fecha_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    resultado = {
        "fecha_servidor": fecha_servidor,
        "fecha_local": fecha_local,
        "symbol": symbol,
        "tipo": "BUY",
        "modo": "real",
        "estrategia": estrategia,
        "precio_entrada": entrada,
        "stop_loss": sl,
        "take_profit": tp,
        "volumen": volumen,
        "resultado": "pendiente",
        "confirmada": confirmada
    }

    archivo_existe = os.path.isfile(archivo)
    with open(archivo, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=resultado.keys())
        if not archivo_existe:
            writer.writeheader()
        writer.writerow(resultado)

    print(f"📝 Operación ({estrategia.upper()}) registrada con fecha servidor {fecha_servidor} y local {fecha_local}.")

def mostrar_posiciones_abiertas(symbol):
    posiciones = mt5.positions_get(symbol=symbol)
    if not posiciones:
        print(f"📭 No hay posiciones abiertas para {symbol}.")
        return

    print(f"📌 {len(posiciones)} posición(es) abierta(s) para {symbol}:")
    for pos in posiciones:
        tipo = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        print(f"   - Tipo: {tipo}, Volumen: {pos.volume}, Precio entrada: {pos.price_open:.2f}")

def ajustar_volumen_margen_y_restricciones(symbol, vol_deseado):
    info = mt5.symbol_info(symbol)
    cuenta = mt5.account_info()

    if not info or not cuenta:
        print("❌ No se pudo obtener información de símbolo o cuenta.")
        return None

    vol_min = info.volume_min
    vol_max = info.volume_max
    vol_step = info.volume_step

    tick = mt5.symbol_info_tick(symbol)
    if not tick or tick.ask == 0 or tick.bid == 0:
        print("❌ No se pudo obtener tick válido para el símbolo.")
        return None

    price = tick.ask if symbol.endswith("-T") else tick.bid

    # Estimación de margen necesario
    margen_necesario = vol_deseado * price / 100
    margen_disponible = cuenta.margin_free * 0.95

    if margen_necesario > margen_disponible:
        vol_deseado = margen_disponible * 100 / price

    vol_redondeado = math.floor(vol_deseado / vol_step) * vol_step
    vol_final = max(vol_min, min(vol_redondeado, vol_max))

    if vol_final < vol_min:
        print(f"⚠️ Volumen ajustado ({vol_final}) es menor que el mínimo permitido ({vol_min}). No se ejecutará la orden.")
        return None

    return round(vol_final, 2)

