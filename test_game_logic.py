import random
import unittest

import game_logic as g


def solve(order):
    if order.only_coin:
        return {order.only_coin: order.target_total // order.only_coin}
    return g.minimal_coins(order.target_total)


class OrderTests(unittest.TestCase):
    def test_generated_orders_are_solvable(self):
        for seed in range(500):
            order = g.make_order(1 + seed % 8, random.Random(seed))
            if order.uses_tray:
                self.assertGreater(order.target_total, 0)
                ok, _ = g.check_order(order, solve(order), "")
                self.assertTrue(ok, order)
            elif order.kind == "haggle":
                self.assertGreater(order.offer, 0)
            else:
                ok, _ = g.check_order(order, {}, str(order.answer))
                self.assertTrue(ok, order)

    def test_exchange_needs_few_coins(self):
        for seed in range(500):
            order = g.make_order(8, random.Random(seed))
            if order.kind == "exchange":
                self.assertEqual(order.target_total // order.only_coin, 10)

    def test_wrong_answers_rejected(self):
        order = g.Order("quote", [], answer=1200)
        self.assertFalse(g.check_order(order, {}, "1199")[0])
        self.assertFalse(g.check_order(order, {}, "")[0])

    def test_exchange_rejects_other_coins(self):
        order = g.Order("exchange", [], target_total=100, only_coin=10)
        self.assertFalse(g.check_order(order, {1: 100}, "")[0])
        self.assertTrue(g.check_order(order, {10: 10}, "")[0])

    def test_minimal_coins(self):
        self.assertEqual(g.minimal_coins(11_230),
                         {10_000: 1, 1_000: 1, 100: 2, 10: 3})


class HaggleTests(unittest.TestCase):
    def setUp(self):
        self.order = g.Order("haggle", [], cost=10_000, offer=8_000,
                             budget=12_000)

    def test_minimum_price(self):
        self.assertEqual(g.haggle_min(10_000), 11_500)

    def test_accept_low_offer_is_bad_deal(self):
        self.assertEqual(g.haggle_accept(self.order)[0], "bad_deal")

    def test_counter_below_minimum_is_bad_deal(self):
        self.assertEqual(g.haggle_counter(self.order, 11_000)[0], "bad_deal")

    def test_counter_within_budget_sells(self):
        self.assertEqual(g.haggle_counter(self.order, 12_000)[0], "sold")

    def test_greedy_counter_ends_in_walk_away(self):
        statuses = [g.haggle_counter(self.order, 20_000)[0]
                    for _ in range(g.MAX_HAGGLE_ROUNDS)]
        self.assertEqual(statuses[-1], "walked")
        self.assertEqual(statuses[0], "new_offer")

    def test_counter_offer_moves_towards_player(self):
        g.haggle_counter(self.order, 20_000)
        self.assertGreater(self.order.offer, 8_000)
        self.assertLess(self.order.offer, 20_000)


if __name__ == "__main__":
    unittest.main()
