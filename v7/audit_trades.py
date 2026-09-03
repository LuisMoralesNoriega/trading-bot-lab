"""Auditor histórico V7. Solo usa consultas de lectura de MetaTrader 5."""
import argparse
import csv
import json
import math
import struct
import zlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import numpy as np
import pandas as pd

from bot import parse_timeframe_comment
from config import EMA_PERIODS, MAGIC_NUMBER, SLOPE_BARS, SYMBOLS, TIMEFRAMES
from strategy import calculate_awesome_oscillator, calculate_trend, generate_base_signal

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "audit"
CHARTS = AUDIT / "charts"
LOG = ROOT / "logs" / "signals.csv"
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}
SIGNALS = {"BUY": "BUY_CANDIDATE", "SELL": "SELL_CANDIDATE"}
SUSPECT_PRICES = (0.58701, 0.58600, 0.58540)


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc)


def reference_indicators(frame):
    """Implementación independiente (sin llamar a strategy.py)."""
    out = frame.copy()
    close = out["close"].astype(float).tolist()
    for period in EMA_PERIODS:
        alpha = 2.0 / (period + 1.0)
        values = []
        previous = None
        for price in close:
            previous = price if previous is None else alpha * price + (1 - alpha) * previous
            values.append(previous)
        out[f"ref_ema_{period}"] = values
    median = ((out["high"] + out["low"]) / 2).astype(float)
    out["ref_ao"] = median.rolling(5).mean() - median.rolling(34).mean()
    return out


def strategy_indicators(frame):
    return generate_base_signal(calculate_awesome_oscillator(calculate_trend(frame)))


def closed_index(frame, entry_time, minutes):
    closes = frame["time"] + pd.to_timedelta(minutes, unit="m")
    valid = np.flatnonzero(closes <= pd.Timestamp(entry_time))
    return None if len(valid) == 0 else int(valid[-1])


def condition_reason(row):
    if row["base_signal"] == "BUY_CANDIDATE":
        return "BULLISH + touches_band + ao_turn_green"
    if row["base_signal"] == "SELL_CANDIDATE":
        return "BEARISH + touches_band + ao_turn_red"
    failed = []
    if row["trend"] not in ("BULLISH", "BEARISH"):
        failed.append("trend=LATERAL")
    if not bool(row["touches_band"]):
        failed.append("no_touches_band")
    if not bool(row["ao_turn_green"]) and not bool(row["ao_turn_red"]):
        failed.append("no_AO_turn")
    return "; ".join(failed) or "conditions_do_not_align"


def analyze_at(frame, entry_time, timeframe):
    idx = closed_index(frame, entry_time, TF_MINUTES[timeframe])
    if idx is None:
        return None
    past = frame.iloc[: idx + 1].copy()
    strategy = strategy_indicators(past)
    reference = reference_indicators(past)
    row = strategy.iloc[-1]
    result = {
        "timeframe": timeframe,
        "bar_open": row["time"].isoformat(),
        "bar_close": (row["time"] + pd.Timedelta(minutes=TF_MINUTES[timeframe])).isoformat(),
        "open": row["open"], "high": row["high"], "low": row["low"], "close": row["close"],
        "trend": row["trend"], "band_bottom": row["band_bottom"],
        "band_top": row["band_top"], "touches_band": bool(row["touches_band"]),
        "ao_previous": strategy["ao"].iloc[-2] if len(strategy) > 1 else None,
        "ao_current": row["ao"],
        "color_previous": strategy["ao_color"].iloc[-2] if len(strategy) > 1 else None,
        "color_current": row["ao_color"],
        "turn_green": bool(row["ao_turn_green"]), "turn_red": bool(row["ao_turn_red"]),
        "reconstructed_signal": row["base_signal"], "signal_reason": condition_reason(row),
    }
    for period in EMA_PERIODS:
        current = row[f"ema_{period}"]
        prior = strategy[f"ema_{period}"].iloc[-1 - SLOPE_BARS] if len(strategy) > SLOPE_BARS else None
        result[f"ema_{period}"] = current
        result[f"ema_{period}_slope_base"] = prior
        result[f"ema_{period}_slope_up"] = bool(current > prior) if prior is not None else False
        result[f"ema_{period}_slope_down"] = bool(current < prior) if prior is not None else False
        result[f"ema_{period}_reference"] = reference[f"ref_ema_{period}"].iloc[-1]
        result[f"ema_{period}_difference"] = current - result[f"ema_{period}_reference"]
    result["ao_reference"] = reference["ref_ao"].iloc[-1]
    result["ao_difference"] = row["ao"] - result["ao_reference"]
    result["_frame"] = strategy
    result["_index"] = idx
    return result


def load_rates(symbol, timeframe, start, end):
    warmup = start - timedelta(days=7)
    rates = mt5.copy_rates_range(symbol, TIMEFRAMES[timeframe], warmup, end + timedelta(hours=2))
    if rates is None or len(rates) == 0:
        return None
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame.sort_values("time").drop_duplicates("time").reset_index(drop=True)


def deal_groups(deals):
    included, excluded = defaultdict(list), []
    for deal in deals or ():
        if deal.magic != MAGIC_NUMBER:
            excluded.append({"ticket": deal.ticket, "reason": "OTHER_MAGIC_OR_MANUAL"})
        elif not deal.symbol or deal.position_id == 0:
            excluded.append({"ticket": deal.ticket, "reason": "BALANCE_OR_NON_TRADE"})
        else:
            included[deal.position_id].append(deal)
    return included, excluded


def reconstruct_trades(groups, orders):
    order_map = defaultdict(list)
    for order in orders or ():
        order_map[order.position_id].append(order)
    trades = []
    for position_id, items in groups.items():
        items.sort(key=lambda x: x.time_msc)
        entries = [x for x in items if x.entry in (mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_INOUT)]
        exits = [x for x in items if x.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)]
        if not entries:
            continue
        first, last = entries[0], exits[-1] if exits else None
        side = "BUY" if first.type == mt5.DEAL_TYPE_BUY else "SELL"
        related_orders = order_map.get(position_id, [])
        source_order = next((x for x in related_orders if x.ticket == first.order), related_orders[0] if related_orders else None)
        comment = first.comment or (source_order.comment if source_order else "")
        timeframe = parse_timeframe_comment(comment)
        sl = getattr(source_order, "sl", 0.0) if source_order else 0.0
        tp = getattr(source_order, "tp", 0.0) if source_order else 0.0
        profit = sum(float(x.profit) for x in items)
        commission = sum(float(x.commission) for x in items)
        swap = sum(float(x.swap) for x in items)
        fee = sum(float(x.fee) for x in items)
        close_reason = "OPEN"
        if last:
            close_reason = {mt5.DEAL_REASON_TP: "TP", mt5.DEAL_REASON_SL: "SL", mt5.DEAL_REASON_CLIENT: "MANUAL"}.get(last.reason, "OTHER")
        risk_distance = abs(first.price - sl) if sl else math.nan
        signed_move = ((last.price - first.price) * (1 if side == "BUY" else -1)) if last else math.nan
        realized_r = signed_move / risk_distance if risk_distance else math.nan
        trades.append({
            "ticket": first.order, "position_id": position_id, "symbol": first.symbol,
            "timeframe": timeframe or "", "comment": comment, "direction": side,
            "entry_time": utc(first.time).isoformat(), "entry_price": first.price,
            "exit_time": utc(last.time).isoformat() if last else "", "exit_price": last.price if last else "",
            "volume": sum(x.volume for x in entries), "sl": sl, "tp": tp,
            "profit": profit, "commission": commission, "swap": swap, "fee": fee,
            "net_result": profit + commission + swap + fee, "close_reason": close_reason,
            "duration_seconds": (last.time - first.time) if last else "",
            "realized_r": realized_r,
        })
    return sorted(trades, key=lambda x: x["entry_time"])


def read_log():
    if not LOG.exists():
        return pd.DataFrame()
    log = pd.read_csv(LOG, low_memory=False, encoding="utf-8-sig")
    log.columns = [c.replace("sÃ­mbolo", "símbolo").replace("seÃ±al", "señal") for c in log.columns]
    for name in ("fecha", "vela"):
        if name in log:
            log[name] = pd.to_datetime(log[name], utc=True, errors="coerce")
    return log


def nearest_log_signal(log, trade):
    if log.empty or "símbolo" not in log:
        return None
    entry = pd.Timestamp(trade["entry_time"])
    rows = log[(log["símbolo"] == trade["symbol"]) & (log["señal"] == SIGNALS[trade["direction"]])]
    if trade["timeframe"]:
        rows = rows[rows["timeframe"] == trade["timeframe"]]
    rows = rows[rows["fecha"] <= entry + pd.Timedelta(minutes=5)]
    return None if rows.empty else rows.iloc[-1]


def classify_trade(trade, rates, log):
    entry = datetime.fromisoformat(trade["entry_time"])
    expected = SIGNALS[trade["direction"]]
    preferred = [trade["timeframe"]] if trade["timeframe"] else []
    search = preferred + [x for x in TF_MINUTES if x not in preferred]
    matches, evaluated = [], None
    for timeframe in search:
        frame = rates.get((trade["symbol"], timeframe))
        if frame is None:
            continue
        audit = analyze_at(frame, entry, timeframe)
        if audit is None:
            continue
        if timeframe == trade["timeframe"]:
            evaluated = audit
        if audit["reconstructed_signal"] == expected:
            matches.append((0, timeframe, audit))
            continue
        full = strategy_indicators(frame[frame["time"] + pd.Timedelta(minutes=TF_MINUTES[timeframe]) <= pd.Timestamp(entry)])
        candidate_indexes = full.index[full["base_signal"] == expected].tolist()
        if candidate_indexes:
            prior = full.loc[candidate_indexes[-1]]
            lag = (pd.Timestamp(entry) - (prior["time"] + pd.Timedelta(minutes=TF_MINUTES[timeframe]))).total_seconds()
            prior_audit = analyze_at(frame, (prior["time"] + pd.Timedelta(minutes=TF_MINUTES[timeframe])).to_pydatetime(), timeframe)
            matches.append((lag, timeframe, prior_audit))
    if matches:
        lag, matched_tf, chosen = min(matches, key=lambda x: x[0])
        classification = "VALID_SIGNAL_AND_ENTRY" if lag <= 1 else "VALID_SIGNAL_BUT_LATE_ENTRY"
    else:
        chosen, matched_tf, lag = evaluated, trade["timeframe"], None
        classification = "UNKNOWN_LEGACY_TIMEFRAME" if not trade["timeframe"] else "ORDER_WITHOUT_MATCHING_SIGNAL"
    if chosen is None:
        return classification, {}, matched_tf, lag
    point_info = mt5.symbol_info(trade["symbol"])
    point = point_info.point if point_info else 0.0
    drift = abs(float(trade["entry_price"]) - float(chosen["close"]))
    frame = chosen.pop("_frame")
    chosen.pop("_index")
    tr = pd.concat([(frame["high"] - frame["low"]), (frame["high"] - frame["close"].shift()).abs(), (frame["low"] - frame["close"].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1]
    risk = abs(float(trade["entry_price"]) - float(trade["sl"])) if trade["sl"] else math.nan
    chosen.update({
        "matched_timeframe": matched_tf, "classification": classification,
        "signal_close": chosen["close"], "market_entry": trade["entry_price"],
        "absolute_drift": drift, "drift_points": drift / point if point else None,
        "atr_14": atr, "drift_in_atr": drift / atr if atr else None,
        "initial_risk_distance": risk, "drift_in_r": drift / risk if risk else None,
        "entry_delay_seconds": lag if lag is not None else (pd.Timestamp(entry) - pd.Timestamp(chosen["bar_close"])).total_seconds(),
    })
    logrow = nearest_log_signal(log, trade)
    chosen["signal_log_time"] = "" if logrow is None else logrow["fecha"].isoformat()
    return classification, chosen, matched_tf, lag


def replay_comparison(rates, trades, log):
    order_keys = {
        (x["symbol"], x["timeframe"], pd.Timestamp(x["entry_time"]))
        for x in trades
    }
    rows = []
    for (symbol, timeframe), frame in rates.items():
        analyzed = strategy_indicators(frame)
        for _, bar in analyzed[analyzed["base_signal"] != "WAIT"].iterrows():
            close_time = bar["time"] + pd.Timedelta(minutes=TF_MINUTES[timeframe])
            if close_time < pd.Timestamp(min(x["entry_time"] for x in trades)):
                continue
            candidate = log[(log.get("símbolo") == symbol) & (log.get("timeframe") == timeframe) & (log.get("vela") == bar["time"])] if not log.empty else pd.DataFrame()
            has_order = any(k[0] == symbol and k[1] == timeframe and abs((pd.Timestamp(k[2]) - close_time).total_seconds()) < 600 for k in order_keys)
            if not candidate.empty:
                logged_reasons = candidate["motivo"].fillna("").astype(str)
                has_order = has_order or logged_reasons.str.contains(
                    "order_send retcode=10009", regex=False
                ).any()
            reason = "ORDER_MATCHED" if has_order else (str(candidate.iloc[-1].get("motivo", "")) if not candidate.empty else "MISSING_BLOCK_REASON")
            rows.append({"symbol": symbol, "timeframe": timeframe, "closed_bar_time": close_time.isoformat(), "candidate": bar["base_signal"], "order_sent": has_order, "block_reason": reason or "MISSING_BLOCK_REASON"})
    return rows


def summary_groups(trades, conditions, comparisons):
    cond_by_position = {x["position_id"]: x for x in conditions}
    dimensions = {"symbol": lambda t: t["symbol"], "timeframe": lambda t: t["timeframe"] or "LEGACY", "symbol_timeframe": lambda t: f'{t["symbol"]}|{t["timeframe"] or "LEGACY"}', "direction": lambda t: t["direction"], "m1_vs_higher": lambda t: "M1" if t["timeframe"] == "M1" else "HIGHER_OR_LEGACY"}
    output = {}
    for dimension, keyfn in dimensions.items():
        groups = defaultdict(list)
        for trade in trades:
            groups[keyfn(trade)].append(trade)
        output[dimension] = {}
        for key, items in groups.items():
            net = [x["net_result"] for x in items]
            wins, losses = [x for x in net if x > 0], [x for x in net if x < 0]
            curve, peak, drawdown = 0.0, 0.0, 0.0
            for value in net:
                curve += value; peak = max(peak, curve); drawdown = max(drawdown, peak - curve)
            realized_r = sum(x["realized_r"] for x in items if not pd.isna(x["realized_r"]))
            related = [cond_by_position.get(x["position_id"], {}) for x in items]
            output[dimension][key] = {"trades": len(items), "won": len(wins), "lost": len(losses), "win_rate": len(wins) / len(items) if items else 0, "gross_profit": sum(wins), "gross_loss": sum(losses), "net_including_costs": sum(net), "profit_factor": sum(wins) / abs(sum(losses)) if losses else None, "average_win": np.mean(wins) if wins else 0, "average_loss": np.mean(losses) if losses else 0, "realized_r": realized_r, "expectancy": np.mean(net) if net else 0, "max_drawdown": drawdown, "orders_without_signal": sum(x.get("classification") == "ORDER_WITHOUT_MATCHING_SIGNAL" for x in related), "late_entries": sum(x.get("classification") == "VALID_SIGNAL_BUT_LATE_ENTRY" for x in related), "blocked_signals": sum((not x["order_sent"]) for x in comparisons if (x[dimension] if dimension in x else None) == key)}
    return output


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = []
    for row in rows:
        fields.extend(x for x in row if x not in fields)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(rows)


def png_chart(path, trade, condition, source_frame):
    width, height = 1000, 600
    pixels = bytearray([255] * width * height * 3)
    def line(x0, y0, x1, y1, color):
        steps = max(abs(x1-x0), abs(y1-y0), 1)
        for i in range(steps + 1):
            x = int(x0 + (x1-x0)*i/steps); y = int(y0 + (y1-y0)*i/steps)
            if 0 <= x < width and 0 <= y < height:
                pos = (y*width+x)*3; pixels[pos:pos+3] = bytes(color)
    analyzed = strategy_indicators(source_frame)
    target = pd.Timestamp(condition["bar_open"])
    indexes = np.flatnonzero(analyzed["time"] == target)
    center = int(indexes[0]) if len(indexes) else len(analyzed) - 1
    left, right = max(0, center - 35), min(len(analyzed), center + 16)
    view = analyzed.iloc[left:right]
    values = list(view["low"]) + list(view["high"]) + [float(trade["entry_price"])] + [float(trade[x]) for x in ("sl", "tp") if trade[x]]
    low, high = min(values), max(values)
    span = high-low or 1
    def y(v): return int(410-(float(v)-low)/span*330)
    def x(i): return int(70 + i * 850 / max(len(view)-1, 1))
    for i, (_, bar) in enumerate(view.iterrows()):
        color = (0, 135, 70) if bar["close"] >= bar["open"] else (190, 45, 45)
        line(x(i), y(bar["low"]), x(i), y(bar["high"]), color)
        for offset in range(-3, 4): line(x(i)+offset, y(bar["open"]), x(i)+offset, y(bar["close"]), color)
    ema_colors = ((20,80,210),(20,150,190),(70,170,80),(200,160,20),(210,90,30),(150,40,170))
    for period, color in zip(EMA_PERIODS, ema_colors):
        vals = view[f"ema_{period}"].tolist()
        for i in range(1, len(vals)): line(x(i-1), y(vals[i-1]), x(i), y(vals[i]), color)
    signal_x = x(center-left)
    line(signal_x, 45, signal_x, 550, (70,70,70))
    entry_x = min(940, signal_x + 12)
    line(entry_x, 45, entry_x, 550, (0,0,0))
    ao = view["ao"].fillna(0).tolist(); ao_span = max(max(map(abs, ao), default=1), 1e-12)
    line(60, 500, 940, 500, (170,170,170))
    for i, value in enumerate(ao):
        line(x(i), 500, x(i), int(500-value/ao_span*65), (0,140,70) if i and value >= ao[i-1] else (190,50,50))
    colors = ((0,120,0),(180,0,0),(0,0,180),(180,100,0))
    levels = [float(condition.get("signal_close", 0)), float(trade["entry_price"])] + [float(trade[x]) for x in ("sl", "tp") if trade[x]]
    for value, color in zip(levels, colors): line(60, y(value), 940, y(value), color)
    raw = b"".join(b"\x00" + pixels[row*width*3:(row+1)*width*3] for row in range(height))
    def chunk(kind, data): return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    metadata = f'ticket={trade["ticket"]}; timeframe={condition.get("matched_timeframe")}; delay_seconds={condition.get("entry_delay_seconds")}; drift_points={condition.get("drift_points")}; future_bars_are_context_only'.encode()
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width,height,8,2,0,0,0)) + chunk(b"tEXt", b"audit\x00" + metadata) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def compare_labels(path, conditions):
    if not path:
        return []
    labels = pd.read_csv(path)
    observed = {(x["symbol"], x["timeframe"], x["bar_close"]): x["reconstructed_signal"] for x in conditions}
    return [{**row.to_dict(), "bot_signal": observed.get((row.symbol, row.timeframe, row.closed_bar_time), "NOT_FOUND"), "matches": observed.get((row.symbol, row.timeframe, row.closed_bar_time)) == row.expected_signal} for _, row in labels.iterrows()]


def main():
    parser = argparse.ArgumentParser(description="Auditor V7 de solo lectura")
    parser.add_argument("--manual-labels")
    args = parser.parse_args()
    AUDIT.mkdir(exist_ok=True); CHARTS.mkdir(exist_ok=True)
    if not mt5.initialize(): raise RuntimeError(mt5.last_error())
    try:
        end = datetime.now(timezone.utc); start = datetime(2026, 8, 28, tzinfo=timezone.utc)
        deals = mt5.history_deals_get(start, end); orders = mt5.history_orders_get(start, end)
        groups, excluded = deal_groups(deals)
        trades = reconstruct_trades(groups, orders)
        if not trades: raise RuntimeError("No se encontraron operaciones magic=70007")
        first = datetime.fromisoformat(trades[0]["entry_time"]); last = end
        rates = {(s, tf): load_rates(s, tf, first, last) for s in SYMBOLS for tf in TF_MINUTES}
        rates = {k: v for k, v in rates.items() if v is not None}
        log = read_log(); conditions = []
        for trade in trades:
            classification, detail, matched_tf, _ = classify_trade(trade, rates, log)
            trade["classification"] = classification; trade["matched_timeframe"] = matched_tf or ""
            detail.update({"ticket": trade["ticket"], "position_id": trade["position_id"], "symbol": trade["symbol"], "timeframe": trade["timeframe"]})
            conditions.append(detail)
        comparisons = replay_comparison(rates, trades, log)
        summaries = summary_groups(trades, conditions, comparisons)
        suspicious = sorted([x for x in trades if x["symbol"] == "NZDUSD-T" and x["direction"] == "SELL"], key=lambda x: min(abs(x["entry_price"]-p) for p in SUSPECT_PRICES))[:3]
        for trade in suspicious:
            condition = next(x for x in conditions if x["position_id"] == trade["position_id"])
            chart_tf = condition.get("matched_timeframe") or trade["timeframe"]
            png_chart(CHARTS / f'NZDUSD-T_{trade["position_id"]}.png', trade, condition, rates[(trade["symbol"], chart_tf)])
        write_csv(AUDIT / "trades.csv", trades); write_csv(AUDIT / "conditions.csv", conditions); write_csv(AUDIT / "signal_order_comparison.csv", comparisons)
        labels = compare_labels(args.manual_labels, conditions)
        if args.manual_labels: write_csv(AUDIT / "manual_labels_comparison.csv", labels)
        payload = {"generated_at": end.isoformat(), "audited_operations": len(trades), "excluded_deals": len(excluded), "excluded_by_reason": dict(pd.Series([x["reason"] for x in excluded]).value_counts()), "classifications": dict(pd.Series([x["classification"] for x in trades]).value_counts()), "blocked_candidates": sum(not x["order_sent"] for x in comparisons), "suspicious_nzdusd_position_ids": [x["position_id"] for x in suspicious], "statistics": summaries}
        (AUDIT / "summary.json").write_text(json.dumps(payload, indent=2, default=lambda x: x.item() if hasattr(x, "item") else str(x)), encoding="utf-8")
        report = ["# Informe de auditoría V7", "", f"Generado: {end.isoformat()}", f"Operaciones auditadas: {len(trades)}", f"Deals excluidos: {len(excluded)}", f"Candidatos bloqueados/sin orden: {payload['blocked_candidates']}", "", "## Clasificaciones", ""] + [f"- {k}: {v}" for k,v in payload["classifications"].items()] + ["", "## Ventas NZDUSD examinadas", ""]
        for trade in suspicious:
            c = next(x for x in conditions if x["position_id"] == trade["position_id"])
            report.append(f'- position_id {trade["position_id"]}, ticket {trade["ticket"]}, {trade["timeframe"] or "LEGACY"}, entrada {trade["entry_price"]}: {trade["classification"]}; vela {c.get("bar_close")}; señal {c.get("reconstructed_signal")}; demora {c.get("entry_delay_seconds")} s; drift {c.get("drift_points")} puntos, {c.get("drift_in_atr")} ATR, {c.get("drift_in_r")} R.')
        report += ["", "Las reglas documentadas son las de la implementación actual; este informe no presume que coincidan con el video ni que sean rentables."]
        (AUDIT / "report.md").write_text("\n".join(report), encoding="utf-8")
        print(json.dumps(
            {k: payload[k] for k in ("audited_operations", "excluded_deals", "classifications", "blocked_candidates", "suspicious_nzdusd_position_ids")},
            indent=2,
            default=lambda x: x.item() if hasattr(x, "item") else str(x),
        ))
        print("AUDITORÍA SOLO LECTURA: order_send no fue llamado.")
    finally:
        mt5.shutdown()


if __name__ == "__main__": main()
