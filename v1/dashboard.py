import csv
from datetime import datetime
from collections import defaultdict

def mostrar_resumen_diario():
    archivo = "bitacora_operaciones.csv"
    hoy = datetime.now().strftime("%Y-%m-%d")

    resumen = []
    totales = {"ganadas": 0, "perdidas": 0, "cerrada sin definir": 0, "ganancia global": 0}

    try:
        with open(archivo, mode="r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row["fecha_local"].startswith(hoy):
                    continue

                resultado = row["resultado"]
                totales[resultado] = totales.get(resultado, 0) + 1

                resumen.append({
                    "simbolo": row["symbol"],
                    "estrategia": row["estrategia"],
                    "resultado": resultado,
                    "hora": row["fecha_local"].split()[1]
                })

    except FileNotFoundError:
        print("📭 No se encontró la bitácora. Aún no hay operaciones registradas.")
        return

    if not resumen:
        print("📭 No se registraron operaciones hoy.")
        return

    print(f"\n📊 RESUMEN DEL DÍA ({hoy})")
    print("╔════════════╦══════════════╦════════════╦══════════════╗")
    print("║  Hora      ║  Símbolo     ║ Estrategia ║ Resultado     ║")
    print("╠════════════╬══════════════╬════════════╬══════════════╣")
    for op in resumen:
        print(f"║ {op['hora']:<10} ║ {op['simbolo']:<12} ║ {op['estrategia']:<10} ║ {op['resultado']:<12} ║")
    print("╚════════════╩══════════════╩════════════╩══════════════╝")

    print("\n✅ Totales:")
    total_ops = sum(totales.values())
    for k, v in totales.items():
        print(f"- {k.capitalize()}: {v}")
    print(f"- Total operaciones: {total_ops}")

    # ✅ Mostrar mensaje especial si se ejecutó ganancia global
    if totales.get("ganancia global", 0) > 0:
        print("\n🚨 Se ejecutó cierre global por retroceso de ganancia. Buen trabajo gestionando el riesgo. 💰")

