from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from config import SYMBOLS, TIMEFRAMES


BARS = 1000


def main():
    if not mt5.initialize():
        raise RuntimeError(f"No se pudo conectar con MT5: {mt5.last_error()}")

    try:
        data_directory = Path(__file__).resolve().parent / "data"
        data_directory.mkdir(exist_ok=True)

        for symbol in SYMBOLS:
            if mt5.symbol_info(symbol) is None:
                print(f"{symbol}: no disponible | error={mt5.last_error()}")
                continue
            if not mt5.symbol_select(symbol, True):
                print(f"{symbol}: no se pudo activar | error={mt5.last_error()}")
                continue

            for name, timeframe in TIMEFRAMES.items():
                # Inicia en 1 para excluir la vela actual todavía incompleta.
                rates = mt5.copy_rates_from_pos(
                    symbol,
                    timeframe,
                    1,
                    BARS,
                )

                if rates is None or len(rates) == 0:
                    print(
                        f"{symbol} {name}: sin datos | error={mt5.last_error()}"
                    )
                    continue

                dataframe = pd.DataFrame(rates)
                dataframe["time"] = pd.to_datetime(
                    dataframe["time"],
                    unit="s",
                    utc=True,
                )

                output = data_directory / f"{symbol}_{name}.csv"
                dataframe.to_csv(output, index=False)

                print(
                    f"{symbol} {name}: {len(dataframe)} velas | "
                    f"{dataframe['time'].iloc[0]} → "
                    f"{dataframe['time'].iloc[-1]}"
                )

    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
