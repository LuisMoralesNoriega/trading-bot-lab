# gestion/stops.py

import MetaTrader5 as mt5

class VerificadorStops:
    def obtener_trade_stops_level(self, simbolo):
        info = mt5.symbol_info(simbolo)
        return info.trade_stops_level if info else None

    def validar_distancia_minima_SL_TP(self, simbolo, sl, tp):
        symbol_info = mt5.symbol_info(simbolo)
        if symbol_info is None:
            return False

        print(f"[DEBUG] {simbolo} trade_stops_level: {symbol_info.trade_stops_level}, digits: {symbol_info.digits}")
        
        point = symbol_info.point
        min_dist = symbol_info.trade_stops_level * point
        price = mt5.symbol_info_tick(simbolo).ask

        return (
            abs(sl - price) >= min_dist and
            abs(tp - price) >= min_dist
        )
