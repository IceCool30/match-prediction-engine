import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from sport_profiles import get_profile, list_sports, SPORT_PROFILES, SPORT_ALIASES


class TestSportProfiles(unittest.TestCase):

    def test_canonical_sports_exist(self):
        canonical_sports = [
            "football", "basketball", "ice_hockey", "tennis",
            "table_tennis", "baseball", "american_football",
            "rugby", "handball", "volleyball", "cricket"
        ]
        available = list_sports()
        for s in canonical_sports:
            self.assertIn(s, available)

    def test_sport_profiles_schema(self):
        required_keys = [
            "name", "scoring_unit", "model", "rho", "max_score",
            "default_home_avg", "default_away_avg", "has_draw",
            "has_btts", "has_clean_sheet", "ou_lines", "spread_lines",
            "markets", "labels", "stat_sources", "key_metrics", "focus_modes"
        ]
        for sport in list_sports():
            profile = get_profile(sport)
            for k in required_keys:
                self.assertIn(k, profile, f"Missing key '{k}' in profile for '{sport}'")

    def test_basketball_format_variants(self):
        # Default is NBA (48-min)
        nba = get_profile("basketball")
        self.assertEqual(nba["default_home_avg"], 112.0)
        self.assertIn(210.5, nba["ou_lines"])

        # FIBA format (40-min)
        fiba = get_profile("basketball", league_format="fiba")
        self.assertEqual(fiba["default_home_avg"], 81.5)
        self.assertIn(160.5, fiba["ou_lines"])

        # NCAA format (40-min college)
        ncaa = get_profile("basketball", league_format="ncaa")
        self.assertEqual(ncaa["default_home_avg"], 73.5)
        self.assertIn(140.5, ncaa["ou_lines"])

        # Aliases
        vtb = get_profile("vtb")
        self.assertEqual(vtb["default_home_avg"], 81.5)

    def test_unknown_sport_raises_error(self):
        with self.assertRaises(ValueError):
            get_profile("quidditch")


if __name__ == "__main__":
    unittest.main()
