import argparse
import csv
import msvcrt
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from config import (
    HISTORY_BARS,
    MAGIC_NUMBER,
    MAX_OPEN_POSITIONS,
    MAX_TOTAL_RISK,
    ORDER_DEVIATION,
    POLL_SECONDS,
    RISK_PER_TRADE,
    STOP_LOOKBACK,
    SYMBOLS,
    TIMEFRAMES,
)
from strategy import (
    calculate_awesome_oscillator,
    calculate_trend,
    generate_base_signal,
)


BASE_DIRECTORY = Path(__file__).resolve().parent
LOG_DIRECTORY = BASE_DIRECTORY / "logs"
SIGNALS_LOG = LOG_DIRECTORY / "signals.csv"
POSITIONS_LOG = LOG_DIRECTORY / "positions.csv"
LOCK_FILE = LOG_DIRECTORY / "bot.lock"
SIGNAL_FIELDS = [
    "fecha",
    "símbolo",
    "timeframe",
    "vela",
    "señal",
    "entrada",
    "SL",
    "TP",
    "volumen",
    "risk_ticks",
    "reward_ticks",
    "ratio_real",
    "posiciones_abiertas",
    "riesgo_abierto_dinero",
    "riesgo_abierto_porcentaje",
    "riesgo_operacion_dinero",
    "riesgo_operacion_porcentaje",
    "riesgo_global_antes",
    "riesgo_global_despues",
    "comentario_mt5",
    "retcode",
    "resultado_orden",
    "motivo",
]
POSITION_FIELDS = [
    "fecha",
    "símbolo",
    "timeframe",
    "ticket",
    "tipo",
    "volumen",
    "precio",
    "beneficio",
    "hora",
]


class SingleInstanceLock:
    def __init__(self, file):
        self.file = file
        self.stream = None

    def __enter__(self):
        LOG_DIRECTORY.mkdir(exist_ok=True)
        self.stream = self.file.open("a+b")
        if self.stream.tell() == 0:
            self.stream.write(b"0")
            self.stream.flush()
        self.stream.seek(0)
        try:
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            self.stream.close()
            raise RuntimeError("Ya existe otra instancia de bot.py en ejecución") from error
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.stream is not None:
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            self.stream.close()


def append_csv(file, fieldnames, row):
    with file.open("a", newline="", encoding="utf-8") as stream:
        csv.DictWriter(stream, fieldnames=fieldnames).writerow(row)


def ensure_csv_schema(file, fieldnames, defaults):
    if not file.exists() or file.stat().st_size == 0:
        with file.open("w", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=fieldnames).writeheader()
        return

    with file.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        existing_fields = reader.fieldnames or []
        if existing_fields == fieldnames:
            return
        rows = list(reader)

    with file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for old_row in rows:
            new_row = {
                field: old_row.get(field, defaults.get(field, ""))
                for field in fieldnames
            }
            writer.writerow(new_row)


def initialize_logs():
    LOG_DIRECTORY.mkdir(exist_ok=True)
    ensure_csv_schema(
        SIGNALS_LOG,
        SIGNAL_FIELDS,
        {"símbolo": "BTCUSD-T"},
    )
    ensure_csv_schema(
        POSITIONS_LOG,
        POSITION_FIELDS,
        {"fecha": "", "símbolo": "BTCUSD-T", "timeframe": ""},
    )


def log_signal(
    symbol,
    timeframe,
    candle,
    signal,
    entry="",
    sl="",
    tp="",
    volume="",
    risk_ticks="",
    reward_ticks="",
    real_ratio="",
    open_positions="",
    open_risk_money="",
    open_risk_percentage="",
    trade_risk_money="",
    trade_risk_percentage="",
    global_risk_before="",
    global_risk_after="",
    mt5_comment="",
    retcode="",
    order_result="",
    reason="",
):
    row = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "símbolo": symbol,
        "timeframe": timeframe,
        "vela": candle.isoformat(),
        "señal": signal,
        "entrada": entry,
        "SL": sl,
        "TP": tp,
        "volumen": volume,
        "risk_ticks": risk_ticks,
        "reward_ticks": reward_ticks,
        "ratio_real": real_ratio,
        "posiciones_abiertas": open_positions,
        "riesgo_abierto_dinero": open_risk_money,
        "riesgo_abierto_porcentaje": open_risk_percentage,
        "riesgo_operacion_dinero": trade_risk_money,
        "riesgo_operacion_porcentaje": trade_risk_percentage,
        "riesgo_global_antes": global_risk_before,
        "riesgo_global_despues": global_risk_after,
        "comentario_mt5": mt5_comment,
        "retcode": retcode,
        "resultado_orden": order_result,
        "motivo": reason,
    }
    append_csv(SIGNALS_LOG, SIGNAL_FIELDS, row)
    print(
        f"[{symbol} {timeframe}] vela={row['vela']} señal={signal} "
        f"entrada={entry or '-'} SL={sl or '-'} TP={tp or '-'} "
        f"volumen={volume or '-'} risk_ticks={risk_ticks or '-'} "
        f"reward_ticks={reward_ticks or '-'} ratio={real_ratio or '-'} "
        f"posiciones={open_positions} "
        f"riesgo_abierto={open_risk_money} ({open_risk_percentage}%) "
        f"riesgo_operacion={trade_risk_money} ({trade_risk_percentage}%) "
        f"riesgo_global={global_risk_before}->{global_risk_after} "
        f"comentario={mt5_comment or '-'} retcode={retcode or '-'} "
        f"resultado={order_result or '-'} "
        f"motivo={reason}"
    )


def log_combination_error(symbol, timeframe, error, candle=None):
    if candle is None:
        candle = datetime.now(timezone.utc)
    log_signal(
        symbol,
        timeframe,
        candle,
        "ERROR",
        reason=f"{type(error).__name__}: {error}",
    )


COMMENT_PATTERN = re.compile(r"^V7\|(M1|M5|M15|M30|H1)\|EMA_AO$")


def parse_timeframe_comment(comment):
    match = COMMENT_PATTERN.fullmatch((comment or "").strip())
    return match.group(1) if match else None


def order_comment(timeframe):
    comment = f"V7|{timeframe}|EMA_AO"
    if len(comment) > 31:
        raise ValueError("El comentario excede el limite de MT5")
    return comment


def configured_positions():
    positions = mt5.positions_get()
    if positions is None:
        return None
    configured = set(SYMBOLS)
    return tuple(
        position for position in positions
        if position.symbol in configured and position.magic == MAGIC_NUMBER
    )


def calculate_open_risk(account):
    positions = configured_positions()
    if positions is None:
        return None, f"Error consultando posiciones: {mt5.last_error()}"
    if account.equity <= 0:
        return None, "El equity actual no es válido"

    portfolio = {
        "positions": positions,
        "count": len(positions),
        "money": 0.0,
        "percentage": 0.0,
        "combinations": set(),
        "legacy_symbols": set(),
    }
    for position in positions:
        position_timeframe = parse_timeframe_comment(position.comment)
        if position_timeframe is None:
            portfolio["legacy_symbols"].add(position.symbol)
        else:
            portfolio["combinations"].add((position.symbol, position_timeframe))
        if not position.sl:
            portfolio["percentage"] = (
                portfolio["money"] / account.equity
            ) * 100
            return portfolio, (
                f"La posición {position.ticket} de {position.symbol} no tiene SL"
            )
        order_type = (
            mt5.ORDER_TYPE_BUY
            if position.type == mt5.POSITION_TYPE_BUY
            else mt5.ORDER_TYPE_SELL
        )
        profit_at_stop = mt5.order_calc_profit(
            order_type,
            position.symbol,
            position.volume,
            position.price_open,
            position.sl,
        )
        if profit_at_stop is None:
            portfolio["percentage"] = (
                portfolio["money"] / account.equity
            ) * 100
            return portfolio, (
                f"No se pudo calcular el riesgo de la posición "
                f"{position.ticket}: {mt5.last_error()}"
            )
        portfolio["money"] += max(0.0, -float(profit_at_stop))

    portfolio["percentage"] = (
        portfolio["money"] / account.equity
    ) * 100
    return portfolio, ""


def validate_position_capacity(symbol, timeframe, account, candidate_risk):
    portfolio, reason = calculate_open_risk(account)
    if portfolio is None:
        return None, reason
    if reason:
        return portfolio, reason
    if portfolio["count"] >= MAX_OPEN_POSITIONS:
        return portfolio, (
            f"Límite global de {MAX_OPEN_POSITIONS} posiciones alcanzado"
        )
    if symbol in portfolio["legacy_symbols"]:
        return portfolio, (
            f"Posición antigua sin timeframe bloquea todo el símbolo {symbol}"
        )
    if (symbol, timeframe) in portfolio["combinations"]:
        return portfolio, (
            f"Misma combinación símbolo/timeframe abierta: {symbol} {timeframe}"
        )
    if candidate_risk > account.equity * RISK_PER_TRADE + 1e-9:
        return portfolio, "El riesgo candidato supera el objetivo de 0.1%"

    total_risk = portfolio["money"] + candidate_risk
    maximum_risk = account.equity * MAX_TOTAL_RISK
    if total_risk > maximum_risk:
        return portfolio, (
            f"Riesgo total candidato {total_risk:g} supera el "
            f"{MAX_TOTAL_RISK:.0%} del equity ({maximum_risk:g})"
        )
    return portfolio, ""


def log_positions(positions):
    if positions is None:
        print(f"No se pudieron consultar posiciones: {mt5.last_error()}")
        return

    observed_at = datetime.now(timezone.utc).isoformat()
    for position in positions:
        position_type = (
            "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL"
        )
        row = {
            "fecha": observed_at,
            "símbolo": position.symbol,
            "timeframe": parse_timeframe_comment(position.comment) or "LEGACY",
            "ticket": position.ticket,
            "tipo": position_type,
            "volumen": position.volume,
            "precio": position.price_open,
            "beneficio": position.profit,
            "hora": datetime.fromtimestamp(
                position.time,
                timezone.utc,
            ).isoformat(),
        }
        append_csv(POSITIONS_LOG, POSITION_FIELDS, row)


def require_demo_account():
    account = mt5.account_info()
    if account is None:
        raise RuntimeError(f"No se pudo leer la cuenta: {mt5.last_error()}")

    is_demo_mode = account.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
    is_demo_server = "demo" in account.server.lower()
    if not is_demo_mode or not is_demo_server:
        raise RuntimeError(
            "Seguridad: se requiere trade_mode DEMO y un servidor cuyo nombre "
            "contenga 'demo'."
        )
    return account


def activate_symbols():
    active = {}
    rejected = {}
    for symbol in SYMBOLS:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            rejected[symbol] = f"symbol_info no disponible: {mt5.last_error()}"
            print(f"[{symbol}] RECHAZADO: {rejected[symbol]}")
            continue
        if not mt5.symbol_select(symbol, True):
            rejected[symbol] = f"symbol_select falló: {mt5.last_error()}"
            print(f"[{symbol}] RECHAZADO: {rejected[symbol]}")
            continue
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            rejected[symbol] = f"symbol_info falló tras activación: {mt5.last_error()}"
            print(f"[{symbol}] RECHAZADO: {rejected[symbol]}")
            continue
        active[symbol] = symbol_info
        print(f"[{symbol}] activo")
    return active, rejected


def get_closed_bars(symbol, timeframe, bars=HISTORY_BARS):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, bars)
    if rates is None or len(rates) < bars:
        raise RuntimeError(
            f"Datos insuficientes para {symbol}: {mt5.last_error()}"
        )
    dataframe = pd.DataFrame(rates)
    dataframe["time"] = pd.to_datetime(dataframe["time"], unit="s", utc=True)
    return dataframe


def analyze_closed_bars(dataframe):
    dataframe = calculate_trend(dataframe)
    dataframe = calculate_awesome_oscillator(dataframe)
    return generate_base_signal(dataframe)


def normalize_volume(volume, symbol_info):
    step = Decimal(str(symbol_info.volume_step))
    requested = min(
        Decimal(str(volume)),
        Decimal(str(symbol_info.volume_max)),
    )
    steps = (requested / step).to_integral_value(rounding=ROUND_FLOOR)
    return float(steps * step)


def price_to_ticks(price, symbol_info, rounding=ROUND_HALF_UP):
    tick_size = Decimal(str(symbol_info.trade_tick_size or symbol_info.point))
    value = Decimal(str(price))
    return int((value / tick_size).to_integral_value(rounding=rounding))


def ticks_to_price(ticks, symbol_info):
    tick_size = Decimal(str(symbol_info.trade_tick_size or symbol_info.point))
    return round(float(Decimal(ticks) * tick_size), symbol_info.digits)


def normalize_price(price, symbol_info, rounding):
    return ticks_to_price(
        price_to_ticks(price, symbol_info, rounding),
        symbol_info,
    )


def calculate_volume(symbol, account, symbol_info, order_type, entry, stop_loss):
    loss_for_one_lot = mt5.order_calc_profit(
        order_type,
        symbol,
        1.0,
        entry,
        stop_loss,
    )
    if loss_for_one_lot is None:
        return None, None, f"order_calc_profit falló: {mt5.last_error()}"
    loss_for_one_lot = abs(loss_for_one_lot)
    if loss_for_one_lot <= 0:
        return None, None, "La pérdida calculada para volumen 1.0 no es válida"

    risk_amount = account.equity * RISK_PER_TRADE
    volume = normalize_volume(risk_amount / loss_for_one_lot, symbol_info)
    if volume < symbol_info.volume_min:
        return None, None, (
            f"Volumen mínimo incompatible con 0.1%: calculado {volume}, "
            f"volume_min {symbol_info.volume_min}"
        )
    candidate_profit = mt5.order_calc_profit(
        order_type,
        symbol,
        volume,
        entry,
        stop_loss,
    )
    if candidate_profit is None:
        return None, None, (
            f"No se pudo confirmar el riesgo de la candidata: {mt5.last_error()}"
        )
    candidate_risk = max(0.0, -float(candidate_profit))
    return volume, candidate_risk, ""


def get_filling_type(symbol_info):
    filling_mode = int(symbol_info.filling_mode)
    if filling_mode & 1:
        return mt5.ORDER_FILLING_FOK
    if filling_mode & 2:
        return mt5.ORDER_FILLING_IOC
    if symbol_info.trade_exemode != mt5.SYMBOL_TRADE_EXECUTION_MARKET:
        return mt5.ORDER_FILLING_RETURN
    return None


def get_filling_name(filling_type):
    names = {
        mt5.ORDER_FILLING_FOK: "FOK",
        mt5.ORDER_FILLING_IOC: "IOC",
        mt5.ORDER_FILLING_RETURN: "RETURN",
    }
    return names.get(filling_type, "NINGUNO")


def print_filling_check(active_symbols):
    print("=== COMPROBACIÓN FILLING MODE | DRY RUN ===")
    print("símbolo | filling_mode original | type_filling seleccionado | nombre")
    for symbol, symbol_info in active_symbols.items():
        filling_type = get_filling_type(symbol_info)
        selected = "NINGUNO" if filling_type is None else filling_type
        print(
            f"{symbol} | {symbol_info.filling_mode} | {selected} | "
            f"{get_filling_name(filling_type)}"
        )


def print_sol_stop_test(account):
    symbol = "SOLUSD-T"
    historical_ask = 104.67
    historical_technical_stop = 103.00
    historical_take_profit = 108.01
    historical_volume = 60.0

    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No se pudo activar {symbol}: {mt5.last_error()}")
    symbol_info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if symbol_info is None or tick is None:
        raise RuntimeError(f"No se pudo leer {symbol}: {mt5.last_error()}")

    current_spread = tick.ask - tick.bid
    historical_bid = historical_ask - current_spread
    levels = calculate_effective_levels(
        "BUY_CANDIDATE",
        historical_technical_stop,
        historical_bid,
        historical_ask,
        symbol_info,
    )
    reason = validate_effective_levels(
        "BUY_CANDIDATE",
        levels,
        historical_bid,
        historical_ask,
        symbol_info,
    )
    volume, candidate_risk, volume_reason = calculate_volume(
        symbol,
        account,
        symbol_info,
        mt5.ORDER_TYPE_BUY,
        levels["entry"],
        levels["effective_stop"],
    )

    print("=== PRUEBA SOL STOP MÍNIMO | DRY RUN ===")
    print(f"símbolo: {symbol}")
    print(f"entrada histórica (ask): {historical_ask}")
    print(f"SL técnico histórico: {historical_technical_stop}")
    print(f"TP histórico: {historical_take_profit}")
    print(f"volumen histórico: {historical_volume}")
    print(f"spread actual usado para reconstruir Bid: {current_spread}")
    print(f"bid de prueba: {historical_bid}")
    print(f"point: {symbol_info.point}")
    print(f"tick_size: {symbol_info.trade_tick_size}")
    print(f"trade_stops_level: {symbol_info.trade_stops_level}")
    print(f"min_stop_distance: {levels['minimum_stop_distance']}")
    print(f"buffer: {levels['buffer']}")
    print(f"SL efectivo ajustado: {levels['effective_stop']}")
    print(f"TP 2R recalculado: {levels['take_profit']}")
    print(f"volumen recalculado al 1%: {volume}")
    print(f"riesgo monetario calculado: {candidate_risk}")
    print(f"validación de stops: {reason or 'OK'}")
    print(f"validación de volumen: {volume_reason or 'OK'}")
    print("Resultado: ajuste demostrado; no se creó ni envió ninguna orden.")


def print_two_r_tests():
    symbol = "BTCUSD-T"
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"No se pudo activar {symbol}: {mt5.last_error()}")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        raise RuntimeError(f"No se pudo leer {symbol}: {mt5.last_error()}")

    cases = [
        ("BUY_CANDIDATE", 99000.07, 100000.11, 100200.13),
        ("SELL_CANDIDATE", 101000.19, 100000.11, 100200.13),
    ]
    print("=== PRUEBAS 2R CON TICKS ENTEROS | DRY RUN ===")
    for signal, technical_stop, bid, ask in cases:
        levels = calculate_effective_levels(
            signal,
            technical_stop,
            bid,
            ask,
            symbol_info,
        )
        reason = validate_effective_levels(
            signal,
            levels,
            bid,
            ask,
            symbol_info,
        )
        side = "BUY" if signal == "BUY_CANDIDATE" else "SELL"
        print(
            f"{side} | entry={levels['entry']} | "
            f"SL={levels['effective_stop']} | TP={levels['take_profit']} | "
            f"risk_ticks={levels['risk_ticks']} | "
            f"reward_ticks={levels['reward_ticks']} | "
            f"ratio={levels['real_ratio']:.6f} | "
            f"resultado={reason or 'OK'}"
        )
    print("Pruebas 2R completadas; no se creó ni envió ninguna orden.")


def calculate_effective_levels(signal, technical_stop, bid, ask, symbol_info):
    minimum_stop_distance = symbol_info.trade_stops_level * symbol_info.point
    buffer = max(2 * symbol_info.trade_tick_size, symbol_info.point)

    if signal == "BUY_CANDIDATE":
        entry_ticks = price_to_ticks(ask, symbol_info, ROUND_HALF_UP)
        maximum_valid_stop = bid - minimum_stop_distance - buffer
        stop_ticks = price_to_ticks(
            min(technical_stop, maximum_valid_stop),
            symbol_info,
            ROUND_FLOOR,
        )
        risk_ticks = entry_ticks - stop_ticks
        reward_ticks = 2 * risk_ticks
        take_profit_ticks = entry_ticks + reward_ticks
    else:
        entry_ticks = price_to_ticks(bid, symbol_info, ROUND_HALF_UP)
        minimum_valid_stop = ask + minimum_stop_distance + buffer
        stop_ticks = price_to_ticks(
            max(technical_stop, minimum_valid_stop),
            symbol_info,
            ROUND_CEILING,
        )
        risk_ticks = stop_ticks - entry_ticks
        reward_ticks = 2 * risk_ticks
        take_profit_ticks = entry_ticks - reward_ticks

    entry = ticks_to_price(entry_ticks, symbol_info)
    effective_stop = ticks_to_price(stop_ticks, symbol_info)
    take_profit = ticks_to_price(take_profit_ticks, symbol_info)
    distance = abs(entry - effective_stop)

    return {
        "bid": bid,
        "ask": ask,
        "point": symbol_info.point,
        "tick_size": symbol_info.trade_tick_size,
        "trade_stops_level": symbol_info.trade_stops_level,
        "entry": entry,
        "technical_stop": technical_stop,
        "effective_stop": effective_stop,
        "take_profit": take_profit,
        "distance": distance,
        "entry_ticks": entry_ticks,
        "stop_ticks": stop_ticks,
        "take_profit_ticks": take_profit_ticks,
        "risk_ticks": risk_ticks,
        "reward_ticks": reward_ticks,
        "real_ratio": reward_ticks / risk_ticks if risk_ticks > 0 else 0.0,
        "minimum_stop_distance": minimum_stop_distance,
        "buffer": buffer,
    }


def validate_effective_levels(signal, levels, bid, ask, symbol_info):
    minimum_stop_distance = levels["minimum_stop_distance"]
    stop_loss = levels["effective_stop"]
    take_profit = levels["take_profit"]
    entry = levels["entry"]

    if not stop_loss or not take_profit:
        return "La orden no contiene SL y TP válidos"
    if signal == "BUY_CANDIDATE":
        if stop_loss >= entry:
            return "SL de BUY no está por debajo de la entrada"
        if stop_loss > bid - minimum_stop_distance:
            return "SL de BUY no respeta la distancia mínima desde Bid"
        if take_profit < bid + minimum_stop_distance:
            return "TP de BUY no respeta la distancia mínima desde Bid"
    else:
        if stop_loss <= entry:
            return "SL de SELL no está por encima de la entrada"
        if stop_loss < ask + minimum_stop_distance:
            return "SL de SELL no respeta la distancia mínima desde Ask"
        if take_profit > ask - minimum_stop_distance:
            return "TP de SELL no respeta la distancia mínima desde Ask"

    risk_ticks = int(levels["risk_ticks"])
    reward_ticks = int(levels["reward_ticks"])
    if risk_ticks <= 0:
        return "La distancia de riesgo en ticks no es válida"
    if reward_ticks < 2 * risk_ticks:
        return (
            f"TP insuficiente: reward_ticks={reward_ticks}, "
            f"risk_ticks={risk_ticks}"
        )
    return ""


def format_order_check_failure(symbol, timeframe, levels, request, check):
    retcode = "None" if check is None else check.retcode
    comment = (
        f"mt5.last_error={mt5.last_error()}"
        if check is None
        else check.comment
    )
    return (
        f"symbol={symbol}; timeframe={timeframe}; bid={levels['bid']}; "
        f"ask={levels['ask']}; point={levels['point']}; "
        f"tick_size={levels['tick_size']}; "
        f"trade_stops_level={levels['trade_stops_level']}; "
        f"min_stop_distance={levels['minimum_stop_distance']}; "
        f"SL_técnico={levels['technical_stop']}; "
        f"SL_efectivo={levels['effective_stop']}; "
        f"TP={request['tp']}; volumen={request['volume']}; "
        f"retcode={retcode}; comentario={comment}"
    )


def prepare_order(symbol, timeframe, signal, dataframe, account, symbol_info):
    # El tick se obtiene inmediatamente antes de calcular entrada, SL y TP.
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None, None, None, f"No se pudo leer el tick: {mt5.last_error()}"

    recent = dataframe.tail(STOP_LOOKBACK)
    spread_price = tick.ask - tick.bid
    if signal == "BUY_CANDIDATE":
        order_type = mt5.ORDER_TYPE_BUY
        technical_stop = float(recent["low"].min())
    else:
        order_type = mt5.ORDER_TYPE_SELL
        technical_stop = float(recent["high"].max() + spread_price)

    levels = calculate_effective_levels(
        signal,
        technical_stop,
        tick.bid,
        tick.ask,
        symbol_info,
    )
    reason = validate_effective_levels(
        signal,
        levels,
        tick.bid,
        tick.ask,
        symbol_info,
    )
    if reason:
        return None, None, levels, reason

    entry = levels["entry"]
    stop_loss = levels["effective_stop"]
    take_profit = levels["take_profit"]

    volume, candidate_risk, reason = calculate_volume(
        symbol,
        account,
        symbol_info,
        order_type,
        entry,
        stop_loss,
    )
    if volume is None:
        return None, None, levels, reason

    filling_type = get_filling_type(symbol_info)
    if filling_type is None:
        return None, None, levels, (
            f"Sin filling mode válido: filling_mode={symbol_info.filling_mode}, "
            f"trade_exemode={symbol_info.trade_exemode}"
        )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": entry,
        "sl": stop_loss,
        "tp": take_profit,
        "deviation": ORDER_DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": order_comment(timeframe),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }
    return request, candidate_risk, levels, ""


def process_timeframe(symbol, name, timeframe, account, symbol_info, live):
    dataframe = analyze_closed_bars(get_closed_bars(symbol, timeframe))
    latest = dataframe.iloc[-1]
    candle = latest["time"]
    signal = latest["base_signal"]

    portfolio, portfolio_error = calculate_open_risk(account)
    if portfolio is None:
        log_signal(
            symbol,
            name,
            candle,
            signal,
            reason=portfolio_error,
        )
        return
    metrics = {
        "open_positions": portfolio["count"],
        "open_risk_money": f"{portfolio['money']:.2f}",
        "open_risk_percentage": f"{portfolio['percentage']:.4f}",
    }

    if signal == "WAIT":
        log_signal(
            symbol,
            name,
            candle,
            signal,
            reason="Sin señal base",
            **metrics,
        )
        return

    request, candidate_risk, levels, reason = prepare_order(
        symbol,
        name,
        signal,
        dataframe,
        account,
        symbol_info,
    )
    level_metrics = {}
    if levels is not None:
        level_metrics = {
            "risk_ticks": levels["risk_ticks"],
            "reward_ticks": levels["reward_ticks"],
            "real_ratio": f"{levels['real_ratio']:.6f}",
        }
    if request is None:
        log_signal(
            symbol,
            name,
            candle,
            signal,
            entry="" if levels is None else levels["entry"],
            sl="" if levels is None else levels["effective_stop"],
            tp="" if levels is None else levels["take_profit"],
            reason=reason,
            **level_metrics,
            **metrics,
        )
        return

    trade_metrics = {
        "trade_risk_money": f"{candidate_risk:.2f}",
        "trade_risk_percentage": (
            f"{candidate_risk / account.equity * 100:.4f}"
        ),
        "global_risk_before": f"{portfolio['percentage']:.4f}%",
        "global_risk_after": (
            f"{(portfolio['money'] + candidate_risk) / account.equity * 100:.4f}%"
        ),
        "mt5_comment": request["comment"],
    }

    portfolio, reason = validate_position_capacity(
        symbol,
        name,
        account,
        candidate_risk,
    )
    if portfolio is not None:
        trade_metrics["global_risk_before"] = f"{portfolio['percentage']:.4f}%"
        trade_metrics["global_risk_after"] = (
            f"{(portfolio['money'] + candidate_risk) / account.equity * 100:.4f}%"
        )
    if reason:
        log_signal(
            symbol,
            name,
            candle,
            signal,
            request["price"],
            request["sl"],
            request["tp"],
            request["volume"],
            reason=reason,
            **level_metrics,
            **metrics,
            **trade_metrics,
        )
        return

    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        reason = format_order_check_failure(
            symbol,
            name,
            levels,
            request,
            check,
        )
        log_signal(
            symbol,
            name,
            candle,
            signal,
            request["price"],
            request["sl"],
            request["tp"],
            request["volume"],
            reason=reason,
            **level_metrics,
            **metrics,
            **trade_metrics,
        )
        return

    if not live:
        log_signal(
            symbol,
            name,
            candle,
            signal,
            request["price"],
            request["sl"],
            request["tp"],
            request["volume"],
            reason="DRY RUN: order_check aprobado; orden no enviada",
            **level_metrics,
            **metrics,
            **trade_metrics,
        )
        return

    current_account = require_demo_account()
    current_portfolio, reason = validate_position_capacity(
        symbol,
        name,
        current_account,
        candidate_risk,
    )
    if current_portfolio is not None:
        trade_metrics["global_risk_before"] = (
            f"{current_portfolio['percentage']:.4f}%"
        )
        trade_metrics["global_risk_after"] = (
            f"{(current_portfolio['money'] + candidate_risk) / current_account.equity * 100:.4f}%"
        )
    if reason:
        current_metrics = metrics
        if current_portfolio is not None:
            current_metrics = {
                "open_positions": current_portfolio["count"],
                "open_risk_money": f"{current_portfolio['money']:.2f}",
                "open_risk_percentage": (
                    f"{current_portfolio['percentage']:.4f}"
                ),
            }
        log_signal(
            symbol,
            name,
            candle,
            signal,
            request["price"],
            request["sl"],
            request["tp"],
            request["volume"],
            reason=reason,
            **level_metrics,
            **current_metrics,
            **trade_metrics,
        )
        return

    result = mt5.order_send(request)
    reason = (
        f"order_send falló: {mt5.last_error()}"
        if result is None
        else f"order_send retcode={result.retcode} {result.comment}"
    )
    result_metrics = dict(trade_metrics)
    result_metrics["retcode"] = "None" if result is None else result.retcode
    result_metrics["order_result"] = reason
    successful_retcodes = {
        mt5.TRADE_RETCODE_DONE,
        mt5.TRADE_RETCODE_DONE_PARTIAL,
        mt5.TRADE_RETCODE_PLACED,
    }
    if result is not None and result.retcode in successful_retcodes:
        after_account = require_demo_account()
        after_portfolio, after_error = calculate_open_risk(after_account)
        if after_portfolio is not None:
            result_metrics["global_risk_after"] = (
                f"{after_portfolio['percentage']:.4f}%"
            )
            metrics = {
                "open_positions": after_portfolio["count"],
                "open_risk_money": f"{after_portfolio['money']:.2f}",
                "open_risk_percentage": (
                    f"{after_portfolio['percentage']:.4f}"
                ),
            }
        elif after_error:
            reason += f"; recálculo posterior falló: {after_error}"
    log_signal(
        symbol,
        name,
        candle,
        signal,
        request["price"],
        request["sl"],
        request["tp"],
        request["volume"],
        reason=reason,
        **level_metrics,
        **metrics,
        **result_metrics,
    )


def parse_arguments():
    parser = argparse.ArgumentParser(description="Bot V7 para cuenta DEMO")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Permite enviar órdenes después de todas las validaciones",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Registra las velas actuales y finaliza sin esperar otra vela",
    )
    parser.add_argument(
        "--check-filling",
        action="store_true",
        help="Comprueba type_filling por símbolo y finaliza en DRY RUN",
    )
    parser.add_argument(
        "--test-sol-stops",
        action="store_true",
        help="Reproduce en DRY RUN el ajuste histórico de SL para SOLUSD-T",
    )
    parser.add_argument(
        "--test-2r",
        action="store_true",
        help="Ejecuta pruebas BUY/SELL de 2R con ticks enteros",
    )
    return parser.parse_args()


def run(arguments):
    diagnostic = (
        arguments.check_filling
        or arguments.test_sol_stops
        or arguments.test_2r
    )
    mode = "LIVE DEMO" if arguments.live and not diagnostic else "DRY RUN"
    print(f"=== BOT V7 MULTISÍMBOLO | {mode} ===")
    initialize_logs()
    if not mt5.initialize():
        raise RuntimeError(f"No se pudo conectar con MT5: {mt5.last_error()}")

    try:
        account = require_demo_account()
        print(
            f"Cuenta DEMO validada | servidor={account.server} | "
            f"equity={account.equity}"
        )
        if arguments.test_sol_stops:
            print_sol_stop_test(account)
            return
        if arguments.test_2r:
            print_two_r_tests()
            return

        active_symbols, rejected_symbols = activate_symbols()
        if not active_symbols:
            raise RuntimeError("MT5 rechazó todos los símbolos configurados")

        if arguments.check_filling:
            print_filling_check(active_symbols)
            print(
                f"Símbolos comprobados: {len(active_symbols)} | "
                f"símbolos rechazados: {len(rejected_symbols)}"
            )
            print("Comprobación completada en DRY RUN; no se enviaron órdenes.")
            return

        positions = configured_positions()
        log_positions(positions)
        if positions is not None:
            print(f"Posiciones globales configuradas abiertas: {len(positions)}")

        last_candles = {}
        for symbol in active_symbols:
            for name, timeframe in TIMEFRAMES.items():
                try:
                    dataframe = get_closed_bars(symbol, timeframe)
                    key = (symbol, name)
                    last_candles[key] = dataframe.iloc[-1]["time"]
                    print(
                        f"[{symbol} {name}] vela inicial registrada: "
                        f"{last_candles[key].isoformat()}"
                    )
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    log_combination_error(symbol, name, error)
                    continue

        print(
            f"Combinaciones activas: {len(last_candles)} | "
            f"símbolos rechazados: {len(rejected_symbols)}"
        )
        if arguments.once:
            print("--once completado en DRY RUN; no se evaluaron señales antiguas.")
            return

        print("Monitoreando nuevas velas cerradas. Ctrl+C para detener.")
        while True:
            positions = configured_positions()
            if positions is None:
                print(f"Error consultando posiciones: {mt5.last_error()}")
                time.sleep(POLL_SECONDS)
                continue
            for (symbol, name), previous_candle in list(last_candles.items()):
                timeframe = TIMEFRAMES[name]
                latest_candle = None
                try:
                    dataframe = get_closed_bars(symbol, timeframe)
                    latest_candle = dataframe.iloc[-1]["time"]
                    if latest_candle <= previous_candle:
                        continue
                    last_candles[(symbol, name)] = latest_candle
                    account = require_demo_account()
                    process_timeframe(
                        symbol,
                        name,
                        timeframe,
                        account,
                        active_symbols[symbol],
                        arguments.live,
                    )
                except KeyboardInterrupt:
                    raise
                except Exception as error:
                    log_combination_error(
                        symbol,
                        name,
                        error,
                        latest_candle,
                    )
                    continue

            if positions:
                log_positions(positions)
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("Monitoreo detenido por el usuario.")
    finally:
        mt5.shutdown()


def main():
    arguments = parse_arguments()
    with SingleInstanceLock(LOCK_FILE):
        run(arguments)


if __name__ == "__main__":
    main()
