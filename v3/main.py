import time
from config import SYMBOLS
from estrategia_tendencia import estrategia_tendencia
from utils_mt5 import conectar_cuenta

def run_bot():
    cuenta = conectar_cuenta()
    print("🔍 Iniciando monitor de tendencias cada 5 minutos...")

    while True:
        print("================= INICIO =================")
        for symbol in SYMBOLS:
            estrategia_tendencia(symbol)

        print("⏳ Esperando 5 minutos para la próxima evaluación...")
        time.sleep(300)  # 5 minutos

if __name__ == "__main__":
    run_bot()
