import datetime

def log_operacion(op):
    symbol = op["symbol"]
    tf = op["timeframe"]
    estrategia = op["estrategia"]
    datos = op["datos"]
    tipo = datos.get("tipo", "BUY")
    entrada = datos["entrada"]
    sl = datos["sl"]
    tp = datos["tp"]

    print("\n📘 LOG DE OPERACIÓN")
    print("────────────────────────────")
    print(f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 Símbolo: {symbol} | TF: {tf} | Estrategia: {estrategia.upper()}")
    print(f"🔸 Tipo: {tipo} | Entrada: {entrada:.2f}")
    print(f"🔻 SL: {sl:.2f} | 🔺 TP: {tp:.2f}")
    print("────────────────────────────")
