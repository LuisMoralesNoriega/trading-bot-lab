import MetaTrader5 as mt5

def obtener_beneficio_flotante_total():
    posiciones = mt5.positions_get()
    if posiciones is None:
        return 0.0
    return sum(p.profit for p in posiciones)

def evaluar_cierre_global(umbral_min=20.0):
    posiciones = mt5.positions_get()
    if not posiciones:
        return False, []

    ganadoras = [p for p in posiciones if p.profit > 0]
    total_profit = sum(p.profit for p in ganadoras)

    if total_profit >= umbral_min:
        return True, ganadoras
    return False, []