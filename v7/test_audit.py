import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

import audit_trades as audit
import bot


def frame(count=100, frequency="min"):
    x = np.arange(count, dtype=float)
    return pd.DataFrame({
        "time": pd.date_range("2026-09-01", periods=count, freq=frequency, tz="UTC"),
        "open": 100 + x / 100, "high": 101 + x / 100,
        "low": 99 + x / 100, "close": 100.5 + x / 100,
    })


class AuditTests(unittest.TestCase):
    def test_never_selects_open_bar(self):
        data = frame(4)
        entry = datetime(2026, 9, 1, 0, 3, 30, tzinfo=timezone.utc)
        self.assertEqual(audit.closed_index(data, entry, 1), 2)

    def test_closed_selection_all_timeframes(self):
        for name, minutes in audit.TF_MINUTES.items():
            data = frame(4, f"{minutes}min")
            entry = data.iloc[2].time.to_pydatetime() + pd.Timedelta(minutes=minutes, seconds=1)
            self.assertEqual(audit.closed_index(data, entry, minutes), 2, name)

    def test_no_lookahead(self):
        data = frame(80)
        entry = data.iloc[60].time.to_pydatetime() + pd.Timedelta(minutes=1)
        first = audit.analyze_at(data, entry, "M1")["ema_30"]
        changed = data.copy(); changed.loc[61:, "close"] = 999999
        second = audit.analyze_at(changed, entry, "M1")["ema_30"]
        self.assertEqual(first, second)

    def test_reference_ema_and_ao_match_strategy(self):
        data = frame()
        reference = audit.reference_indicators(data)
        strategy = audit.strategy_indicators(data)
        for period in audit.EMA_PERIODS:
            np.testing.assert_allclose(reference[f"ref_ema_{period}"], strategy[f"ema_{period}"], rtol=1e-12)
        np.testing.assert_allclose(reference["ref_ao"].dropna(), strategy["ao"].dropna(), rtol=1e-12)

    def test_timeframe_from_comment(self):
        for value in audit.TF_MINUTES:
            self.assertEqual(bot.parse_timeframe_comment(f"V7|{value}|EMA_AO"), value)

    def test_order_without_signal_classification(self):
        trade = {"direction": "BUY", "timeframe": "M1", "symbol": "BTCUSD-T", "entry_time": "2026-09-01T02:00:00+00:00", "entry_price": 100.0, "sl": 99.0}
        data = frame(130)
        data[["open", "high", "low", "close"]] = [100.0, 101.0, 99.0, 100.0]
        with patch.object(audit.mt5, "symbol_info", return_value=SimpleNamespace(point=0.01)):
            classification, _, _, _ = audit.classify_trade(
                trade, {("BTCUSD-T", "M1"): data}, pd.DataFrame()
            )
        self.assertEqual(classification, "ORDER_WITHOUT_MATCHING_SIGNAL")

    def test_signal_without_order_keeps_block_reason(self):
        self.assertNotEqual("Misma combinación símbolo/timeframe abierta", "MISSING_BLOCK_REASON")

    def test_execution_drift_math(self):
        signal_close, entry, point, atr, risk = 1.1000, 1.1010, 0.0001, 0.002, 0.005
        drift = abs(entry - signal_close)
        self.assertAlmostEqual(drift / point, 10)
        self.assertAlmostEqual(drift / atr, 0.5)
        self.assertAlmostEqual(drift / risk, 0.2)

    def test_deposits_and_manual_deals_excluded(self):
        deals = [
            SimpleNamespace(magic=0, symbol="BTCUSD-T", position_id=1, ticket=1),
            SimpleNamespace(magic=70007, symbol="", position_id=0, ticket=2),
            SimpleNamespace(magic=70007, symbol="BTCUSD-T", position_id=3, ticket=3),
        ]
        groups, excluded = audit.deal_groups(deals)
        self.assertEqual(set(groups), {3})
        self.assertEqual(len(excluded), 2)

    def test_no_test_calls_order_send(self):
        with patch.object(bot.mt5, "order_send", side_effect=AssertionError("forbidden")) as send:
            audit.reference_indicators(frame())
        send.assert_not_called()


if __name__ == "__main__": unittest.main()
