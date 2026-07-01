# utils/logger.py

from datetime import datetime

def log_console(mensaje):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {mensaje}")

def guardar_operacion_exitosa(orden):
    with open("datos/historico_operaciones.txt", "a") as f:
        f.write(f"{datetime.now()} | {orden}\n")
