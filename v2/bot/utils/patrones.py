def es_martillo(vela):
    cuerpo = abs(vela['open'] - vela['close'])
    mecha = vela['high'] - vela['low']
    return cuerpo < mecha * 0.4 and vela['close'] > vela['open']

def es_envolvente(vela):
    return True  # Simulación temporal, luego se refina

def es_pin_bar(vela):
    return True  # Simulación temporal, luego se refina
