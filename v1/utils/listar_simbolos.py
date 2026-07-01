import MetaTrader5 as mt5

archivo_salida = "simbolos_disponibles.txt"

# Iniciar conexión con MetaTrader 5
if not mt5.initialize():
    print("❌ No se pudo conectar a MetaTrader 5")
    exit()

# Obtener símbolos disponibles
symbols = mt5.symbols_get()

# Guardar nombres en archivo
with open(archivo_salida, "w", encoding="utf-8") as f:
    for s in symbols:
        f.write(s.name + "\n")

mt5.shutdown()

print(f"✅ Símbolos guardados en: {archivo_salida}")
