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

# Timeframe para calcular EMAs
TIMEFRAME = "M30"

# Ribbon rojo (exacto a tu plantilla)
EMA_PERIODS_RIBBON = [30, 35, 40, 45, 50, 60]

# Línea amarilla (SMA 200)
EMA_TREND_MAJOR = 200
USE_SMA_MAJOR = True   # <- activamos SMA en vez de EMA

# Nº de velas a descargar
BARS_TO_LOAD = 1500

# Fuente de precio
EMA_SOURCE = "close"

# No usas Heikin Ashi, así que lo dejamos False
USE_HEIKIN_ASHI = False