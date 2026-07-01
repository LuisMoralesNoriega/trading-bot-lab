import time
import MetaTrader5 as mt5
from scanner_multitimeframe import escanear_senales
from ejecutor import ejecutar_orden
from helpers import registrar_operacion, mostrar_posiciones_abiertas, ajustar_volumen_margen_y_restricciones, tiene_margen_suficiente
from monitor import actualizar_resultado_operacion
from logger_trading import log_operacion
from dashboard import mostrar_resumen_diario
from trailing import aplicar_trailing_stop
from cierre_dinamico import control_cierre_dinamico

# 📌 Gestión de riesgo por volumen dinámico
def calcular_volumen_por_riesgo(balance, riesgo_pct, distancia_sl_pips, valor_por_pip=10):
    if distancia_sl_pips == 0:
        print("⚠️ SL inválido: distancia es 0 pips.")
        return 0.0
    riesgo_usd = balance * (riesgo_pct / 100)
    volumen = riesgo_usd / (distancia_sl_pips * valor_por_pip)
    return round(volumen, 2)

def ejecutar_operacion(op, cuenta, real_mode=True, riesgo_pct=1.0):
    symbol = op["symbol"]
    estrategia = op["estrategia"]
    datos = op["datos"]
    tipo = datos.get("tipo", "BUY")
    entrada = datos["entrada"]
    sl = datos["sl"]
    tp = datos["tp"]

    print(f"🚀 Ejecutando {estrategia.upper()} en {symbol} [{op['timeframe']}]")
    log_operacion(op)

    # Ajuste automático por instrumento
    if symbol.startswith("BTC") or symbol.startswith("ETH"):
        divisor_pip = 1.0
        valor_por_pip = 1.0
    elif symbol.startswith("XRP") or symbol.startswith("DOGE"):
        divisor_pip = 0.01
        valor_por_pip = 0.5
    else:
        divisor_pip = 0.0001  # Forex estándar
        valor_por_pip = 10.0

    distancia_sl_pips = abs(entrada - sl) / divisor_pip
    volumen = calcular_volumen_por_riesgo(cuenta.balance, riesgo_pct, distancia_sl_pips, valor_por_pip)

    # Ajustar según restricciones y margen disponible
    volumen = ajustar_volumen_margen_y_restricciones(symbol, volumen)
    if volumen is None or volumen < 0.01:
        print("⚠️ Volumen no válido después del ajuste. Se descarta la operación.")
        return

    print(f"📦 Volumen calculado: {volumen:.2f} lotes")

    if real_mode and cuenta.balance >= 50 and volumen > 0 and tiene_margen_suficiente(symbol):
        result = ejecutar_orden(
            symbol=symbol,
            entrada=entrada,
            sl=sl,
            tp=tp,
            volumen=volumen,
            tipo=tipo
        )

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            registrar_operacion(
                symbol, entrada, sl, tp, volumen,
                estrategia=estrategia,
                confirmada="si"
            )
        else:
            print("❌ Orden no confirmada por MT5. No se registrará en la bitácora.")
    else:
        print("⚠️ No se pudo ejecutar la operación por volumen inválido o balance insuficiente.")

def main():
    if not mt5.initialize():
        print("❌ No se pudo conectar a MetaTrader 5")
        return

    cuenta = mt5.account_info()
    if cuenta:
        print(f"\n✅ Cuenta conectada: {cuenta.login} | Tipo: DEMO/REAL | Balance: {cuenta.balance}")
    else:
        print("⚠️ No se pudo obtener información de la cuenta.")
        mt5.shutdown()
        return

    # ✅ Evaluar si debe cerrarse por retroceso de beneficio flotante dinámico
    control_cierre_dinamico(trailing_piso=20.0, intervalo=60)

    # ✅ Escaneo y operaciones normales
    symbols = [
        "AUDUSD-T", "NZDUSD-T", "USDCAD-T", "USDCHF-T", "EURGBP-T", "EURJPY-T", "GBPJPY-T",
        "SOLUSD-T", "LTCUSD-T", "ADAUSD-T", "XLMUSD-T", "ETCUSD-T",
        "[USA500]-T", "[USA100]-T", "[GER40]-T", "[SPA35]-T", "[JP225]-T"
    ]
    real_mode = True
    riesgo_pct = 1.0

    oportunidades = escanear_senales(symbols)
    for op in oportunidades:
        ejecutar_operacion(op, cuenta, real_mode, riesgo_pct)
        actualizar_resultado_operacion(op["symbol"])
        mostrar_posiciones_abiertas(op["symbol"])
        aplicar_trailing_stop()

    mt5.shutdown()
    mostrar_resumen_diario()

while True:
    print("\n================= Nuevo ciclo =================")
    main()
    print("⏳ Esperando 5 minutos para el próximo análisis...\n")
    time.sleep(300)
