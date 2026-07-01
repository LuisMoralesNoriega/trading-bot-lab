# gestion/trailing.py

import MetaTrader5 as mt5
from utils.logger import log_console

class GestorTrailing:
    def aplicar_trailing_individual(self):
        posiciones = mt5.positions_get()
        if not posiciones:
            return

        for p in posiciones:
            profit = p.profit
            if profit < 5:
                continue

            # SL dinámico: profit - 2 USD (como colchón)
            nuevo_sl = p.price_open + (profit - 2) / p.volume if p.type == mt5.ORDER_TYPE_BUY else p.price_open - (profit - 2) / p.volume

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": p.ticket,
                "sl": round(nuevo_sl, 5),
                "tp": p.tp,
                "symbol": p.symbol,
                "magic": p.magic,
                "comment": "Trailing individual"
            }

            resultado = mt5.order_send(request)
            log_console(f"[{p.symbol}] 🔁 Trailing SL actualizado: {resultado.retcode if resultado else 'Error'}")

    def cerrar_en_bloque_por_bajada_de_piso(self, piso_actual):
        posiciones = [p for p in mt5.positions_get() if p.profit > 1]
        beneficio_total = sum(p.profit for p in posiciones)

        if beneficio_total < piso_actual:
            log_console(f"🔻 Beneficio combinado bajó de {piso_actual:.2f}. Cerrando en bloque...")
            for p in posiciones:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": p.ticket,
                    "type": mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                    "volume": p.volume,
                    "price": mt5.symbol_info_tick(p.symbol).bid if p.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(p.symbol).ask,
                    "symbol": p.symbol,
                    "deviation": 10,
                    "magic": p.magic,
                    "comment": "Cierre por bloque"
                }
                mt5.order_send(request)
