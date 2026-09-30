import unittest
import subprocess
import sys
import json
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
SCRIPT_PATH = os.path.join(SCRIPTS_DIR, "poisson_model.py")


class TestCLI(unittest.TestCase):

    def run_cmd(self, args):
        cmd = [sys.executable, SCRIPT_PATH] + args
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res

    def test_list_sports_cli(self):
        res = self.run_cmd(["--list-sports"])
        self.assertEqual(res.returncode, 0)
        self.assertIn("Football (Soccer)", res.stdout)
        self.assertIn("Basketball", res.stdout)

    def test_football_json_output(self):
        res = self.run_cmd([
            "--sport", "football",
            "--home", "Arsenal", "--away", "Chelsea",
            "--home-xg", "1.85", "--away-xg", "1.15",
            "--odds-home", "1.70", "--odds-draw", "3.80", "--odds-away", "4.50",
            "--json"
        ])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["sport_model"], "poisson")
        self.assertIn("match_result", data)
        self.assertIn("devigged_market", data)
        self.assertIn("recommendations", data)

    def test_basketball_fiba_multi_line_cli(self):
        res = self.run_cmd([
            "--sport", "basketball",
            "--league-format", "fiba",
            "--home", "Avtodor", "--away", "Uralmash",
            "--home-xg", "73.5", "--away-xg", "83.5",
            "--odds-home", "3.80", "--odds-away", "1.23",
            "--ou-odds", "154.5:1.43:2.65,160.5:1.80:1.91,168.5:2.70:1.41",
            "--json"
        ])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["sport_model"], "normal")
        self.assertEqual(data["league_format"], "fiba")
        self.assertIn("Under 168.5", data["value_bets"])
        # Should have recommended Under 168.5 as anchor
        rec = data["recommendations"]
        self.assertIn("accumulator_anchor", rec)
        self.assertEqual(rec["accumulator_anchor"]["selection"], "Under 168.5")
        self.assertGreaterEqual(rec["accumulator_anchor"]["aai_score"], 85.0)


if __name__ == "__main__":
    unittest.main()
