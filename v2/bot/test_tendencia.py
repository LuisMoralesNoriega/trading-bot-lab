# test_tendencia.py

from estrategias.tendencia import EstrategiaTendencia
import MetaTrader5 as mt5
from config import symbols

def iniciar_mt5():
    if not mt5.initialize():
        print("❌ Error al conectar con MetaTrader 5")
        quit()
    print("✅ MetaTrader 5 conectado")

def test_estrategia_tendencia():
    iniciar_mt5()

    simbolo = symbols[0]  # Puedes cambiar el índice o poner "BTCUSD-T", etc.
    timeframe = mt5.TIMEFRAME_M5

    estrategia = EstrategiaTendencia(simbolo, timeframe)
    resultado = estrategia.detectar_senal_tendencia()

    if resultado:
        print("✅ Señal detectada correctamente")
    else:
        print("⚠️ No se detectó señal válida")

    mt5.shutdown()

if __name__ == "__main__":
    test_estrategia_tendencia()
