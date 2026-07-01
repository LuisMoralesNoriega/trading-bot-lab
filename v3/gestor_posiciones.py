import time
import MetaTrader5 as mt5
from utils_mt5 import get_symbol_info
from config import SYMBOLS


def cerrar_posicion(pos):
    price = (
        mt5.symbol_info_tick(pos.symbol).bid
        if pos.type == mt5.ORDER_TYPE_BUY
        else mt5.symbol_info_tick(pos.symbol).ask
    )
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": pos.ticket,
        "price": price,
        "deviation": 10,
        "magic": 101010,
        "comment": "Cierre manual TP/SL"
    }
    result = mt5.order_send(request)
    print(f"⚠️ Cierre manual ejecutado para {pos.symbol}: {result}")


def monitor_posiciones(symbol=None, intervalo=30):
    """
    Monitorea las posiciones abiertas cada 'intervalo' segundos.
    Si el precio alcanza el TP o SL, cierra la orden manualmente.
    Si 'symbol' es None, monitorea todos los símbolos de SYMBOLS.
    """
    print("🔍 Iniciando monitor de posiciones...")
    while True:
        symbols_to_check = SYMBOLS if symbol is None else [symbol]

        for sym in symbols_to_check:
            posiciones = mt5.positions_get(symbol=sym)
            if posiciones:
                tick = mt5.symbol_info_tick(sym)
                for pos in posiciones:
                    if pos.type == mt5.ORDER_TYPE_BUY:
                        if pos.tp > 0 and tick.bid >= pos.tp:
                            print(f"✅ TP alcanzado (BUY) en {sym}: {tick.bid} >= {pos.tp}")
                            cerrar_posicion(pos)
                        elif pos.sl > 0 and tick.bid <= pos.sl:
                            print(f"❌ SL alcanzado (BUY) en {sym}: {tick.bid} <= {pos.sl}")
                            cerrar_posicion(pos)

                    elif pos.type == mt5.ORDER_TYPE_SELL:
                        if pos.tp > 0 and tick.ask <= pos.tp:
                            print(f"✅ TP alcanzado (SELL) en {sym}: {tick.ask} <= {pos.tp}")
                            cerrar_posicion(pos)
                        elif pos.sl > 0 and tick.ask >= pos.sl:
                            print(f"❌ SL alcanzado (SELL) en {sym}: {tick.ask} >= {pos.sl}")
                            cerrar_posicion(pos)

        time.sleep(intervalo)
