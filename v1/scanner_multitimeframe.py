import MetaTrader5 as mt5
from obtener_candles import obtener_candles
from strategy import calcular_ao, calcular_emas_escalonadas, estrategia_tendencia, estrategia_doble_piso, estrategia_doble_techo
from mtf_validador import confirmar_contexto
from helpers import ya_hay_demasiadas_posiciones

# Lista de temporalidades a escanear con nombre legible
TIMEFRAMES = {
    "5M": mt5.TIMEFRAME_M5,
    "15M": mt5.TIMEFRAME_M15,
    "30M": mt5.TIMEFRAME_M30,
    "1H": mt5.TIMEFRAME_H1,
    "4H": mt5.TIMEFRAME_H4,
    "1D": mt5.TIMEFRAME_D1
}

def escanear_senales(symbols):
    oportunidades = []

    for symbol in symbols:
        for nombre_tf, tf in TIMEFRAMES.items():
            print(f"\n🔎 Buscando señal en {symbol} [{nombre_tf}]...")

            try:
                df = obtener_candles(symbol, timeframe=tf, bars=100)
                df = calcular_ao(df)
                df = calcular_emas_escalonadas(df)
            except Exception as e:
                print(f"❌ Error en {symbol} [{nombre_tf}]: {e}")
                continue

            # Validar contexto superior/inferior
            if not confirmar_contexto(symbol, tf):
                continue

            # Buscar señales
            datos_tendencia = estrategia_tendencia(df, symbol)
            if datos_tendencia and not ya_hay_demasiadas_posiciones(symbol):
                oportunidades.append({
                    "symbol": symbol,
                    "timeframe": nombre_tf,
                    "estrategia": "tendencia",
                    "datos": datos_tendencia
                })
                continue

            datos_doble_piso = estrategia_doble_piso(df, symbol)
            if datos_doble_piso and not ya_hay_demasiadas_posiciones(symbol):
                oportunidades.append({
                    "symbol": symbol,
                    "timeframe": nombre_tf,
                    "estrategia": "doble_piso",
                    "datos": datos_doble_piso
                })
            
            datos_doble_techo = estrategia_doble_techo(df, symbol)
            if datos_doble_techo and not ya_hay_demasiadas_posiciones(symbol):
                oportunidades.append({
                    "symbol": symbol,
                    "timeframe": nombre_tf,
                    "estrategia": "doble_techo",
                    "datos": datos_doble_techo
                })


    return oportunidades
