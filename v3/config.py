# config.py

# ===========================
# PARÁMETROS DEL BOT
# ===========================

# Símbolos principales a operar
#SYMBOLS = [
#    "BTCUSD-T", "AUDUSD-T", "NZDUSD-T", "USDCAD-T", "USDCHF-T", "EURGBP-T", "EURJPY-T", "GBPJPY-T",
#    "SOLUSD-T", "LTCUSD-T", "ADAUSD-T", "XLMUSD-T", "ETCUSD-T",
#    "[USA500]-T", "[USA100]-T", "[GER40]-T", "[SPA35]-T", "[JP225]-T"
#]
SYMBOLS = [
    "USDCAD-T"
]

# Timeframe para las velas (en minutos)
# Opciones disponibles en utils_mt5: 1, 5, 15, 60
TIMEFRAME = 5  

# Temporalidades que se evaluarán para estrategias de tendencia
TIMEFRAMES_TENDENCIA = [1, 5, 15, 30, 60]


# Períodos de EMAs utilizados en la estrategia de tendencia
EMAS_PERIODS = [30, 35, 40, 45, 50, 55, 60, 65, 70]

# Distancia por defecto de SL y TP (en "pips" o puntos básicos)
SL_PIPS_DEFAULT = 300
TP_PIPS_DEFAULT = 600

# Porcentaje de riesgo por operación (usado para calcular el volumen dinámico)
RIESGO_PORCENTAJE = 1  # 1% del balance

# ===========================
# MONITOR DE POSICIONES
# ===========================

# Intervalo para revisar posiciones abiertas (en segundos)
INTERVALO_MONITOR = 30  

# ===========================
# CICLO DE APERTURA
# ===========================

# Intervalo para evaluar nuevas entradas (en segundos)
INTERVALO_APERTURA = 300  # 5 minutos

# ===========================
# LOGS Y DEBUG
# ===========================

# Mostrar detalles de debug
DEBUG_MODE = True
