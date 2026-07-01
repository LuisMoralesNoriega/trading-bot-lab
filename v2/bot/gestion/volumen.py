# gestion/volumen.py

from config import VOLUME_MIN, VOLUME_MAX

class CalculadorVolumen:
    def calcular_volumen(self, sl, riesgo_pct):
        # Provisional: retornar volumen fijo (ajustar luego según balance real)
        return 0.1

    def validar_volumen_en_rango(self, volumen):
        return VOLUME_MIN <= volumen <= VOLUME_MAX
