# ejecutor/ordenes.py

import MetaTrader5 as mt5

class EjecutorOrdenes:
    def enviar_orden_buy(self, simbolo, volumen, sl, tp):
        precio = mt5.symbol_info_tick(simbolo).ask
        modos_validos = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_FOK]

        for modo in modos_validos:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": simbolo,
                "volume": volumen,
                "type": mt5.ORDER_TYPE_BUY,
                "price": precio,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": 1001,
                "comment": "Tendencia-BUY",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": modo,
            }
            resultado = mt5.order_send(request)
            if resultado and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[INFO BUY] {simbolo} -> orden ejecutada correctamente con modo: {modo}")
                print(f"✅ Orden ejecutada: {resultado.order}")
                return resultado

        print(f"[ERROR] Ningún tipo de llenado funcionó para {simbolo} (BUY)")
        return None

    def enviar_orden_sell(self, simbolo, volumen, sl, tp):
        precio = mt5.symbol_info_tick(simbolo).bid
        modos_validos = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_FOK]

        for modo in modos_validos:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": simbolo,
                "volume": volumen,
                "type": mt5.ORDER_TYPE_SELL,
                "price": precio,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": 1001,
                "comment": "Tendencia-SELL",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": modo,
            }
            resultado = mt5.order_send(request)
            if resultado and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[INFO SELL] {simbolo} -> orden ejecutada correctamente con modo: {modo}")
                print(f"✅ Orden ejecutada: {resultado.order}")
                return resultado

        print(f"[ERROR] Ningún tipo de llenado funcionó para {simbolo} (SELL)")
        return None
