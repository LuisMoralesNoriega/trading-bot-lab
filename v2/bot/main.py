# main.py

import time
import threading
import MetaTrader5 as mt5
from config import symbols, tf_map, CICLO_Oportunidades
from estrategias.tendencia import EstrategiaTendencia
from ejecutor.ordenes import EjecutorOrdenes
from gestion.trailing import GestorTrailing
from utils.logger import guardar_operacion_exitosa, log_console

ejecutor = EjecutorOrdenes()
trailing = GestorTrailing()
piso_dinamico = [25]  # Piso inicial para beneficio combinado

def iniciar_mt5():
    if not mt5.initialize():
        print("❌ No se pudo conectar con MetaTrader 5")
        exit()
    print("✅ MetaTrader 5 conectado")

def ejecutar_estrategias():
    for simbolo in symbols:
        for timeframe in tf_map.keys():
            estrategia = EstrategiaTendencia(simbolo, timeframe)
            operacion = estrategia.detectar_senal_tendencia()
            if operacion:
                print(f"🚀 Operación válida en {simbolo} | TF: {timeframe}")
                print(operacion)

                if operacion["tipo"] == "BUY":
                    resultado = ejecutor.enviar_orden_buy(
                        operacion["simbolo"],
                        operacion["volumen"],
                        operacion["sl"],
                        operacion["tp"]
                    )
                else:
                    resultado = ejecutor.enviar_orden_sell(
                        operacion["simbolo"],
                        operacion["volumen"],
                        operacion["sl"],
                        operacion["tp"]
                    )

                if resultado and resultado.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ Orden ejecutada: {resultado.order}")
                    guardar_operacion_exitosa(operacion)
                else:
                    print(f"❌ Error al ejecutar orden: {resultado.retcode if resultado else 'Sin respuesta'}")

def ciclo_gestion_abierta():
    while True:
        trailing.aplicar_trailing_individual()

        posiciones = [p for p in mt5.positions_get() if p.profit > 1]
        total = sum(p.profit for p in posiciones)

        if total >= piso_dinamico[0] + 5:
            piso_dinamico[0] = total
            log_console(f"🔼 Nuevo piso dinámico: {piso_dinamico[0]:.2f}")

        elif total < piso_dinamico[0] and total > 0:
            trailing.cerrar_en_bloque_por_bajada_de_piso(piso_dinamico[0])
            piso_dinamico[0] = 25  # Reiniciar
        time.sleep(60)

def iniciar_bot():
    iniciar_mt5()
    threading.Thread(target=ciclo_gestion_abierta, daemon=True).start()
    while True:
        print("================= Nuevo ciclo =================")
        ejecutar_estrategias()
        time.sleep(CICLO_Oportunidades)

if __name__ == "__main__":
    iniciar_bot()
