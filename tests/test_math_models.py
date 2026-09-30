import unittest
import math
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from poisson_model import (
    poisson_pmf,
    dixon_coles_tau,
    normal_cdf,
    normal_pdf,
    compute_poisson_probabilities,
    compute_normal_probabilities,
    calculate_devigged_probabilities,
    compute_accumulator_anchor_index,
    evaluate_value,
    parse_ou_odds_string,
    compute_period_splits,
)


class TestMathModels(unittest.TestCase):

    def test_poisson_pmf(self):
        # Lambda = 0
        self.assertEqual(poisson_pmf(0, 0.0), 1.0)
        self.assertEqual(poisson_pmf(1, 0.0), 0.0)

        # Standard Poisson: lambda=1.5, k=0 -> e^-1.5
        expected_0 = math.exp(-1.5)
        self.assertAlmostEqual(poisson_pmf(0, 1.5), expected_0, places=5)

        # Sum of probabilities across k=0..20 should be ~1.0
        prob_sum = sum(poisson_pmf(k, 1.8) for k in range(25))
        self.assertAlmostEqual(prob_sum, 1.0, places=5)

    def test_dixon_coles_tau(self):
        # Disabled rho returns 1.0
        self.assertEqual(dixon_coles_tau(0, 0, 1.5, 1.2, 0.0), 1.0)

        # Negative rho (standard football)
        rho = -0.11
        lambd, mu = 1.5, 1.2
        # (0, 0) should be: 1.0 - (lambd * mu * rho) = 1.0 - (1.8 * -0.11) = 1.0 + 0.198 = 1.198
        self.assertAlmostEqual(dixon_coles_tau(0, 0, lambd, mu, rho), 1.0 - (lambd * mu * rho), places=5)
        # (2, 2) should be untouched
        self.assertEqual(dixon_coles_tau(2, 2, lambd, mu, rho), 1.0)

    def test_normal_cdf(self):
        # Mean 0, std 1
        self.assertAlmostEqual(normal_cdf(0.0), 0.5, places=5)
        self.assertAlmostEqual(normal_cdf(1.95996), 0.975, places=3)
        self.assertAlmostEqual(normal_cdf(-1.95996), 0.025, places=3)

    def test_compute_poisson_probabilities(self):
        res = compute_poisson_probabilities(
            home_exp=1.85,
            away_exp=1.15,
            rho=-0.11,
            max_score=10,
            has_draw=True,
            has_btts=True,
            ou_lines=[1.5, 2.5, 3.5],
            spread_lines=[-1.5, 1.5]
        )
        # Match result probs must sum to ~1.0
        mr = res["match_result"]
        total_p = mr["home_win"]["prob"] + mr["draw"]["prob"] + mr["away_win"]["prob"]
        self.assertAlmostEqual(total_p, 1.0, places=3)

        # Over + Under 2.5 must sum to 1.0
        ou = res["over_under"]
        self.assertAlmostEqual(ou["over_2_5"]["prob"] + ou["under_2_5"]["prob"], 1.0, places=3)

        # BTTS Yes + No must sum to 1.0
        btts = res["btts"]
        self.assertAlmostEqual(btts["yes"]["prob"] + btts["no"]["prob"], 1.0, places=3)

    def test_compute_normal_probabilities(self):
        res = compute_normal_probabilities(
            home_exp=110.0,
            away_exp=100.0,
            has_draw=False,
            ou_lines=[205.5, 210.5, 215.5],
            spread_lines=[-5.5, 5.5],
            scoring_unit="points"
        )
        mr = res["match_result"]
        # Home should be favored
        self.assertGreater(mr["home_win"]["prob"], mr["away_win"]["prob"])
        self.assertAlmostEqual(mr["home_win"]["prob"] + mr["away_win"]["prob"], 1.0, places=4)

        # Over + Under must sum to 1.0
        ou = res["over_under"]
        self.assertAlmostEqual(ou["over_210_5"]["prob"] + ou["under_210_5"]["prob"], 1.0, places=4)

    def test_devigging(self):
        # Standard 2-way market: 1.90 / 1.90 -> 50% fair prob, overround ~5.26%
        devig_2way = calculate_devigged_probabilities({"Home": 1.90, "Away": 1.90})
        self.assertAlmostEqual(devig_2way["outcomes"]["Home"]["devigged_prob"], 0.5, places=3)
        self.assertAlmostEqual(devig_2way["outcomes"]["Away"]["devigged_prob"], 0.5, places=3)
        self.assertGreater(devig_2way["bookmaker_margin_pct"], 5.0)

        # 3-way 1X2 market
        devig_3way = calculate_devigged_probabilities({"1": 1.70, "X": 3.80, "2": 4.50})
        p_sum = sum(v["devigged_prob"] for v in devig_3way["outcomes"].values())
        self.assertAlmostEqual(p_sum, 1.0, places=3)

    def test_accumulator_anchor_index(self):
        # Below 65% must be rejected
        low_res = compute_accumulator_anchor_index(0.60, 1.50)
        self.assertEqual(low_res["score"], 0.0)
        self.assertFalse(low_res["is_anchor"])
        self.assertEqual(low_res["tier"], "UNSUITABLE")

        # Elite anchor (>80% prob, +EV, buffer)
        elite_res = compute_accumulator_anchor_index(0.82, 1.41, z_buffer=1.0)
        self.assertGreaterEqual(elite_res["score"], 85.0)
        self.assertTrue(elite_res["is_anchor"])
        self.assertEqual(elite_res["tier"], "ELITE")

    def test_parse_ou_odds_string(self):
        # Line with over and under
        parsed = parse_ou_odds_string("154.5:1.43:2.65,168.5:2.70:1.41")
        self.assertIn(154.5, parsed)
        self.assertEqual(parsed[154.5]["over"], 1.43)
        self.assertEqual(parsed[154.5]["under"], 2.65)
        self.assertIn(168.5, parsed)
        self.assertEqual(parsed[168.5]["under"], 1.41)

        # Single side
        single = parse_ou_odds_string("168.5:U:1.41")
        self.assertEqual(single[168.5]["under"], 1.41)

    def test_period_splits(self):
        # Football 1H
        fb_split = compute_period_splits(1.85, 1.15, "football", "goals")
        self.assertIn("1st_half", fb_split)
        self.assertAlmostEqual(fb_split["1st_half"]["home_exp"], 1.85 * 0.45, places=2)

        # Basketball 1H
        bb_split = compute_period_splits(73.5, 83.5, "basketball_fiba", "points")
        self.assertIn("1st_half", bb_split)
        self.assertAlmostEqual(bb_split["1st_half"]["total_exp"], round((73.5 + 83.5) * 0.485, 1), places=1)


if __name__ == "__main__":
    unittest.main()
