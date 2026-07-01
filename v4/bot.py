# bot.py
import time
from config import (
    SYMBOLS, TIMEFRAME, EMA_PERIODS_RIBBON, EMA_TREND_MAJOR,
    BARS_TO_LOAD, EMA_SOURCE, USE_HEIKIN_ASHI, USE_SMA_MAJOR
)
from utils import (
    conectar_cuenta, get_rates, compute_ema_set, compute_major_trend
)

CHECK_INTERVAL_SEC = 300  # 5 minutos

def describe_state(symbol, df_ema, ema_major):
    """
    Texto corto para verificar rápidamente si el precio está por encima/dentro/detrás del ribbon.
    """
    last_close = get_last_value(df_ema.index, "close_placeholder")  # marcador
    # Tomamos el precio actual desde la última fila de una de las EMAs (índice)
    last_ts = df_ema.index[-1]
    # El precio lo sacamos de la EMA más corta + necesitamos close real; mejor volvemos a pedir close:
    # (para no mezclar dependencias, la función que llama ya tiene el df original)
    return last_ts

def run_bot():
    cuenta = conectar_cuenta()
    print("🔍 Iniciando monitor de tendencias cada 5 minutos...")

    while True:
        print("\n================= INICIO =================")
        for symbol in SYMBOLS:
            print(f"▶ Símbolo: {symbol}")
            try:
                df = get_rates(symbol, TIMEFRAME, BARS_TO_LOAD)

                # EMAs del ribbon
                ema_ribbon = compute_ema_set(
                    df, EMA_PERIODS_RIBBON, source=EMA_SOURCE, use_heikin=USE_HEIKIN_ASHI
                )

                # EMA (o SMA) mayor (amarilla)
                ema_major = compute_major_trend(
                    df, EMA_TREND_MAJOR, source=EMA_SOURCE, use_heikin=USE_HEIKIN_ASHI,
                    use_sma_instead=USE_SMA_MAJOR   # <- ahora se controla con config.py
                )

                # Log limpio de los últimos valores
                last_idx = ema_ribbon.index[-1]
                print(f"  Última vela: {last_idx}")

                # Precio “base” (close o HA close)
                price_base = df["close"].iloc[-1] if not USE_HEIKIN_ASHI else (
                    (df["open"].iloc[-1] + df["high"].iloc[-1] + df["low"].iloc[-1] + df["close"].iloc[-1]) / 4.0
                )

                print(f"  Precio ({EMA_SOURCE}): {price_base:.5f}")
                print("  Ribbon EMAs:")
                for p in EMA_PERIODS_RIBBON:
                    val = float(ema_ribbon[f"EMA_{p}"].iloc[-1])
                    print(f"    EMA {p:>3}: {val:.5f}")

                print(f"  EMA {EMA_TREND_MAJOR}: {float(ema_major.iloc[-1]):.5f}")

                # Señales rápidas de consistencia vs gráfico:
                # - En tendencia alcista, EMA corta > EMA larga y precio > EMA_200
                # - En bajista, al revés
                ema_short = ema_ribbon[f"EMA_{EMA_PERIODS_RIBBON[0]}"].iloc[-1]
                ema_long  = ema_ribbon[f"EMA_{EMA_PERIODS_RIBBON[-1]}"].iloc[-1]
                major     = ema_major.iloc[-1]

                bias = "ALCISTA" if (ema_short > ema_long and price_base > major) else \
                       "BAJISTA" if (ema_short < ema_long and price_base < major) else "MIXTA/LATERAL"
                print(f"  Sesgo estimado: {bias}")

            except Exception as e:
                print(f"  ❌ Error con {symbol}: {e}")

        print("⏳ Esperando 5 minutos para la próxima evaluación...")
        time.sleep(CHECK_INTERVAL_SEC)

if __name__ == "__main__":
    run_bot()
