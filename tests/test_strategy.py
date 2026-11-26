import unittest

from src.strategy import Candidate, Strategy, choose_candidates, evaluate


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.policy = Strategy(
            budget_stars=400,
            max_per_gift_stars=200,
            target_gifts=2,
            min_profit_percent=15,
        )

    def test_two_profitable_gifts_fit_budget(self):
        candidates = [
            Candidate("a", "Gift A", 150, 400, 200),
            Candidate("b", "Gift B", 180, 400, 200),
        ]
        chosen = choose_candidates(candidates, self.policy)
        self.assertEqual(len(chosen), 2)
        self.assertLessEqual(sum(x.candidate.asking_price_stars for x in chosen), 400)

    def test_never_spends_more_than_200_on_one_gift(self):
        candidate = Candidate("a", "Gift A", 201, 500, 100)
        self.assertIsNone(evaluate(candidate, self.policy))

    def test_skips_unprofitable_gift(self):
        candidate = Candidate("a", "Gift A", 190, 200, 200)
        self.assertIsNone(evaluate(candidate, self.policy))

    def test_does_not_force_two_purchases(self):
        candidates = [Candidate("a", "Gift A", 150, 400, 200)]
        self.assertEqual(len(choose_candidates(candidates, self.policy)), 1)


if __name__ == "__main__":
    unittest.main()
