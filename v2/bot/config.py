# config.py

import MetaTrader5 as mt5

# Riesgo por operación (porcentaje del balance)
RIESGO_POR_OPERACION = 0.01  # 1%

# Volumen mínimo y máximo permitido por operación
VOLUME_MIN = 0.01
VOLUME_MAX = 1.0

# Ciclos de ejecución en segundos
CICLO_Oportunidades = 300  # 5 minutos
CICLO_GestionAbierta = 60  # 1 minuto

# Símbolos a operar
symbols = [
    "BTCUSD-T", "AUDUSD-T", "NZDUSD-T", "USDCAD-T", "USDCHF-T", "EURGBP-T", "EURJPY-T", "GBPJPY-T",
    "SOLUSD-T", "LTCUSD-T", "ADAUSD-T", "XLMUSD-T", "ETCUSD-T",
    "[USA500]-T", "[USA100]-T", "[GER40]-T", "[SPA35]-T", "[JP225]-T"
]
#symbols = ["BTCUSD-T"]

# Mapa de validación multitemporal
tf_map = {
    mt5.TIMEFRAME_M1: [mt5.TIMEFRAME_M5],
    mt5.TIMEFRAME_M5: [mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M15],
    mt5.TIMEFRAME_M15: [mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M30],
    mt5.TIMEFRAME_H1: [mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H4],
    mt5.TIMEFRAME_H4: [mt5.TIMEFRAME_H1, mt5.TIMEFRAME_D1],
    mt5.TIMEFRAME_D1: [mt5.TIMEFRAME_H4],
}
