import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import bot
import config


def position(symbol, comment, ticket=1, magic=config.MAGIC_NUMBER):
    return SimpleNamespace(
        symbol=symbol,
        comment=comment,
        magic=magic,
        sl=99.0,
        type=bot.mt5.POSITION_TYPE_BUY,
        volume=1.0,
        price_open=100.0,
        ticket=ticket,
    )


class BotV7Tests(unittest.TestCase):
    def setUp(self):
        self.account = SimpleNamespace(equity=10000.0)
        self.profit = patch.object(bot.mt5, "order_calc_profit", return_value=-10.0)
        self.profit.start()
        self.addCleanup(self.profit.stop)

    def portfolio_for(self, positions):
        with patch.object(bot.mt5, "positions_get", return_value=tuple(positions)):
            portfolio, reason = bot.calculate_open_risk(self.account)
        self.assertEqual(reason, "")
        return portfolio

    def capacity(self, positions, symbol, timeframe, risk=10.0):
        with patch.object(bot.mt5, "positions_get", return_value=tuple(positions)):
            return bot.validate_position_capacity(
                symbol, timeframe, self.account, risk
            )

    def test_requested_configuration(self):
        self.assertEqual(config.RISK_PER_TRADE, 0.001)
        self.assertEqual(config.MAX_OPEN_POSITIONS, 50)
        self.assertEqual(config.MAX_TOTAL_RISK, 0.50)

    def test_same_symbol_and_timeframe_is_blocked(self):
        _, reason = self.capacity(
            [position("EURJPY-T", "V7|M1|EMA_AO")], "EURJPY-T", "M1"
        )
        self.assertIn("Misma combinación", reason)

    def test_same_symbol_different_timeframe_is_allowed(self):
        _, reason = self.capacity(
            [position("EURJPY-T", "V7|M1|EMA_AO")], "EURJPY-T", "M30"
        )
        self.assertEqual(reason, "")

    def test_legacy_position_blocks_whole_symbol(self):
        _, reason = self.capacity(
            [position("EURJPY-T", "V7 EMA AO")], "EURJPY-T", "M30"
        )
        self.assertIn("antigua sin timeframe", reason)

    def test_position_51_is_rejected(self):
        positions = [
            position("BTCUSD-T", "V7|M1|EMA_AO", ticket=index)
            for index in range(50)
        ]
        _, reason = self.capacity(positions, "EURJPY-T", "M30")
        self.assertIn("50 posiciones", reason)

    def test_buy_and_sell_are_exactly_two_r_in_ticks(self):
        info = SimpleNamespace(
            trade_stops_level=10,
            point=0.01,
            trade_tick_size=0.01,
            digits=2,
        )
        for signal, stop in (("BUY_CANDIDATE", 98.0), ("SELL_CANDIDATE", 103.0)):
            levels = bot.calculate_effective_levels(signal, stop, 100.0, 100.2, info)
            self.assertEqual(levels["reward_ticks"], 2 * levels["risk_ticks"])
            self.assertEqual(levels["real_ratio"], 2.0)

    def test_volume_uses_point_one_percent_and_final_stop(self):
        info = SimpleNamespace(volume_step=0.01, volume_max=100.0, volume_min=0.01)
        calls = []

        def calc(_kind, _symbol, volume, entry, stop):
            calls.append((volume, entry, stop))
            return -100.0 * volume

        with patch.object(bot.mt5, "order_calc_profit", side_effect=calc):
            volume, risk, reason = bot.calculate_volume(
                "EURJPY-T", self.account, info, bot.mt5.ORDER_TYPE_BUY, 100.0, 99.0
            )
        self.assertEqual((volume, risk, reason), (0.1, 10.0, ""))
        self.assertTrue(all(call[2] == 99.0 for call in calls))

    def test_comment_parser_recognizes_all_configured_timeframes(self):
        for timeframe in ("M1", "M5", "M15", "M30", "H1"):
            comment = bot.order_comment(timeframe)
            self.assertEqual(bot.parse_timeframe_comment(comment), timeframe)
            self.assertLessEqual(len(comment), 31)

    def test_restart_rebuilds_combinations_from_mt5_positions(self):
        positions = [
            position("EURJPY-T", "V7|M1|EMA_AO"),
            position("BTCUSD-T", "V7|H1|EMA_AO", ticket=2),
        ]
        first = self.portfolio_for(positions)["combinations"]
        second = self.portfolio_for(positions)["combinations"]
        self.assertEqual(first, second)
        self.assertEqual(first, {("EURJPY-T", "M1"), ("BTCUSD-T", "H1")})

    def test_dry_run_never_calls_order_send(self):
        frame = pd.DataFrame([{
            "time": pd.Timestamp("2026-09-01", tz="UTC"),
            "base_signal": "BUY_CANDIDATE",
        }])
        portfolio = {
            "positions": (), "count": 0, "money": 0.0, "percentage": 0.0,
            "combinations": set(), "legacy_symbols": set(),
        }
        request = {
            "price": 100.0, "sl": 99.0, "tp": 102.0, "volume": 0.1,
            "comment": "V7|M1|EMA_AO",
        }
        levels = {"risk_ticks": 100, "reward_ticks": 200, "real_ratio": 2.0}
        with patch.object(bot, "get_closed_bars", return_value=frame), \
             patch.object(bot, "analyze_closed_bars", return_value=frame), \
             patch.object(bot, "calculate_open_risk", return_value=(portfolio, "")), \
             patch.object(bot, "prepare_order", return_value=(request, 10.0, levels, "")), \
             patch.object(bot, "validate_position_capacity", return_value=(portfolio, "")), \
             patch.object(bot.mt5, "order_check", return_value=SimpleNamespace(retcode=0)), \
             patch.object(bot.mt5, "order_send", side_effect=AssertionError("order_send invoked")) as send, \
             patch.object(bot, "log_signal"):
            bot.process_timeframe("EURJPY-T", "M1", 1, self.account, object(), False)
        send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
