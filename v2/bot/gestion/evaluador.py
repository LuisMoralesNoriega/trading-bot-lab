# gestion/evaluador.py

from utils.indicadores import calcular_ema
from utils.patrones import es_martillo, es_envolvente, es_pin_bar
from utils.indicadores import calcular_ao

class EvaluadorGeneral:
    def __init__(self):
        self.direccion = None

    def validar_emas_ordenadas(self, velas):
        cierres = [v['close'] for v in velas]
        emas = [calcular_ema(cierres, p) for p in [30, 35, 40, 45, 50, 60]]
        print("EMAs:", emas)
        if all(emas[i] < emas[i + 1] for i in range(len(emas) - 1)):
            self.direccion = "BUY"
            return "BUY"
        elif all(emas[i] > emas[i + 1] for i in range(len(emas) - 1)):
            self.direccion = "SELL"
            return "SELL"
        return None

    def validar_precio_en_banda(self, velas):
        cierre = velas[-1]['close']
        cierres = [v['close'] for v in velas]
        emas = [calcular_ema(cierres, p) for p in [30, 35, 40, 45, 50, 60]]
        
        min_ema = min(emas)
        max_ema = max(emas)
        tolerancia = cierre * 0.001  # 0.1%

        return (min_ema - tolerancia) <= cierre <= (max_ema + tolerancia)


    def validar_ao_color(self, velas):
        ao = calcular_ao(velas)
        if ao[-1] > 0:
            return self.direccion == "BUY"
        elif ao[-1] < 0:
            return self.direccion == "SELL"
        return False

    def validar_patron_vela(self, velas):
        vela = velas[-1]
        return es_martillo(vela) or es_envolvente(vela) or es_pin_bar(vela)
