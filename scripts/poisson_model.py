#!/usr/bin/env python3
"""
match-prediction-engine: Multi-Sport Quantitative Probability & Value Model
Supports 11+ sports with automatic model selection:
  - Bivariate Poisson + Dixon-Coles for low/mid-scoring sports (football, hockey, baseball)
  - Normal (Gaussian) distribution for high-scoring sports (basketball, American football)
Calculates win/loss/draw probabilities, over/under, spread, BTTS (where applicable),
exact scores, fair odds, and Expected Value (+EV) against bookmaker odds.
No external dependencies required (pure standard library).
"""

import math
import sys
import json
import argparse
from typing import Dict, Any, List, Tuple, Optional

# Import sport profiles (same directory)
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sport_profiles import get_profile, list_sports, SPORT_PROFILES


# ============================================================================
# Core Math Functions
# ============================================================================

def poisson_pmf(k: int, lambd: float) -> float:
    """Calculate standard Poisson PMF: P(k; lambda) = (lambda^k * exp(-lambda)) / k!"""
    if lambd <= 0:
        return 1.0 if k == 0 else 0.0
    if k > 170:  # Avoid factorial overflow
        # Use Stirling's approximation via log
        log_p = k * math.log(lambd) - lambd - sum(math.log(i) for i in range(1, k + 1))
        return math.exp(log_p)
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)


def dixon_coles_tau(x: int, y: int, lambd: float, mu: float, rho: float) -> float:
    """
    Dixon-Coles adjustment factor for low-score dependence.
    Active only for sports where rho != 0 (football, ice hockey).
    """
    if rho == 0.0:
        return 1.0
    if x == 0 and y == 0:
        return 1.0 - (lambd * mu * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambd * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard Normal using error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    """Probability density function for standard Normal."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


# ============================================================================
# Poisson Model (low/mid-scoring sports)
# ============================================================================

def compute_poisson_probabilities(
    home_exp: float,
    away_exp: float,
    rho: float = 0.0,
    max_score: int = 10,
    has_draw: bool = True,
    has_btts: bool = True,
    ou_lines: List[float] = None,
    spread_lines: List[float] = None,
    scoring_unit: str = "goals"
) -> Dict[str, Any]:
    """Compute full scoreline matrix and derived market probabilities using Poisson."""

    if ou_lines is None:
        ou_lines = [1.5, 2.5, 3.5]
    if spread_lines is None:
        spread_lines = [-1.5, -0.5, 0.5, 1.5]

    matrix: List[List[float]] = []
    total_prob = 0.0

    # Build scoreline probability matrix
    for h in range(max_score + 1):
        row = []
        for a in range(max_score + 1):
            base_p = poisson_pmf(h, home_exp) * poisson_pmf(a, away_exp)
            adj = dixon_coles_tau(h, a, home_exp, away_exp, rho)
            p = max(0.0, base_p * adj)
            row.append(p)
            total_prob += p
        matrix.append(row)

    # Normalize
    if total_prob > 0:
        for h in range(max_score + 1):
            for a in range(max_score + 1):
                matrix[h][a] /= total_prob

    # Outcome probabilities
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0

    # Over/Under for all configured lines
    ou_probs = {line: 0.0 for line in ou_lines}

    # BTTS
    btts_yes = 0.0
    btts_no = 0.0

    # Clean Sheets
    clean_sheet_home = 0.0
    clean_sheet_away = 0.0

    # Spread probabilities
    spread_cover = {line: 0.0 for line in spread_lines}

    score_ranking: List[Tuple[str, float]] = []

    for h in range(max_score + 1):
        for a in range(max_score + 1):
            prob = matrix[h][a]
            total = h + a
            margin = h - a  # Home perspective

            if h > a:
                p_home += prob
            elif h == a:
                p_draw += prob
            else:
                p_away += prob

            if a == 0:
                clean_sheet_home += prob
            if h == 0:
                clean_sheet_away += prob

            if h > 0 and a > 0:
                btts_yes += prob
            else:
                btts_no += prob

            for line in ou_lines:
                if total > line:
                    ou_probs[line] += prob

            for line in spread_lines:
                if margin + line > 0:
                    spread_cover[line] += prob

            score_ranking.append((f"{h}-{a}", prob))

    score_ranking.sort(key=lambda x: x[1], reverse=True)

    def fair_odds(p: float) -> float:
        return round(1.0 / p, 2) if p > 0.0001 else 999.0

    # Build result dictionary
    result: Dict[str, Any] = {
        "sport_model": "poisson",
        "expected_scoring": {
            "home": round(home_exp, 2),
            "away": round(away_exp, 2),
            "total": round(home_exp + away_exp, 2),
            "unit": scoring_unit,
        },
    }

    # Outcome markets
    if has_draw:
        result["match_result"] = {
            "home_win": {"prob": round(p_home, 4), "pct": f"{p_home * 100:.1f}%", "fair_odds": fair_odds(p_home)},
            "draw": {"prob": round(p_draw, 4), "pct": f"{p_draw * 100:.1f}%", "fair_odds": fair_odds(p_draw)},
            "away_win": {"prob": round(p_away, 4), "pct": f"{p_away * 100:.1f}%", "fair_odds": fair_odds(p_away)},
        }
        # Double Chance & DNB
        p_1x = p_home + p_draw
        p_x2 = p_draw + p_away
        p_12 = p_home + p_away
        non_draw = p_home + p_away
        dnb_home = (p_home / non_draw) if non_draw > 0 else 0.5
        dnb_away = (p_away / non_draw) if non_draw > 0 else 0.5
        result["double_chance"] = {
            "1X": {"prob": round(p_1x, 4), "pct": f"{p_1x * 100:.1f}%", "fair_odds": fair_odds(p_1x)},
            "X2": {"prob": round(p_x2, 4), "pct": f"{p_x2 * 100:.1f}%", "fair_odds": fair_odds(p_x2)},
            "12": {"prob": round(p_12, 4), "pct": f"{p_12 * 100:.1f}%", "fair_odds": fair_odds(p_12)},
        }
        result["draw_no_bet"] = {
            "home": {"prob": round(dnb_home, 4), "pct": f"{dnb_home * 100:.1f}%", "fair_odds": fair_odds(dnb_home)},
            "away": {"prob": round(dnb_away, 4), "pct": f"{dnb_away * 100:.1f}%", "fair_odds": fair_odds(dnb_away)},
        }
    else:
        # No-draw sports: moneyline
        # Re-normalize excluding draw probability
        total_decisive = p_home + p_away
        if total_decisive > 0:
            ml_home = p_home / total_decisive
            ml_away = p_away / total_decisive
        else:
            ml_home = ml_away = 0.5
        result["match_result"] = {
            "home_win": {"prob": round(ml_home, 4), "pct": f"{ml_home * 100:.1f}%", "fair_odds": fair_odds(ml_home)},
            "away_win": {"prob": round(ml_away, 4), "pct": f"{ml_away * 100:.1f}%", "fair_odds": fair_odds(ml_away)},
        }

    # Over/Under
    ou_result = {}
    for line in sorted(ou_lines):
        key_over = f"over_{str(line).replace('.', '_')}"
        key_under = f"under_{str(line).replace('.', '_')}"
        p_over = ou_probs[line]
        p_under = 1.0 - p_over
        ou_result[key_over] = {"prob": round(p_over, 4), "pct": f"{p_over * 100:.1f}%", "fair_odds": fair_odds(p_over)}
        ou_result[key_under] = {"prob": round(p_under, 4), "pct": f"{p_under * 100:.1f}%", "fair_odds": fair_odds(p_under)}
    result["over_under"] = ou_result

    # Spread / Handicap
    spread_result = {}
    for line in sorted(spread_lines):
        key = f"home_{'+' if line >= 0 else ''}{line}"
        p_cover = spread_cover[line]
        spread_result[key] = {"prob": round(p_cover, 4), "pct": f"{p_cover * 100:.1f}%", "fair_odds": fair_odds(p_cover)}
    result["spread"] = spread_result

    # BTTS (only for applicable sports)
    if has_btts:
        result["btts"] = {
            "yes": {"prob": round(btts_yes, 4), "pct": f"{btts_yes * 100:.1f}%", "fair_odds": fair_odds(btts_yes)},
            "no": {"prob": round(btts_no, 4), "pct": f"{btts_no * 100:.1f}%", "fair_odds": fair_odds(btts_no)},
        }
        result["clean_sheets"] = {
            "home": {"prob": round(clean_sheet_home, 4), "pct": f"{clean_sheet_home * 100:.1f}%"},
            "away": {"prob": round(clean_sheet_away, 4), "pct": f"{clean_sheet_away * 100:.1f}%"},
        }

    # Top scorelines
    result["top_scorelines"] = [
        {"score": s[0], "prob": round(s[1], 4), "pct": f"{s[1] * 100:.1f}%", "fair_odds": fair_odds(s[1])}
        for s in score_ranking[:8]
    ]

    return result


# ============================================================================
# Normal (Gaussian) Model (high-scoring sports)
# ============================================================================

def compute_normal_probabilities(
    home_exp: float,
    away_exp: float,
    home_std: float = None,
    away_std: float = None,
    has_draw: bool = False,
    ou_lines: List[float] = None,
    spread_lines: List[float] = None,
    scoring_unit: str = "points"
) -> Dict[str, Any]:
    """
    Compute win/loss probabilities and market lines using Normal distribution.
    Suitable for high-scoring sports (basketball, American football, rugby).
    """

    # Default standard deviations: ~12% of mean is typical for team sports
    if home_std is None:
        home_std = max(home_exp * 0.12, 3.0)
    if away_std is None:
        away_std = max(away_exp * 0.12, 3.0)

    if ou_lines is None:
        ou_lines = [home_exp + away_exp - 5, home_exp + away_exp, home_exp + away_exp + 5]
    if spread_lines is None:
        spread_lines = [-7.5, -3.5, -1.5, 1.5, 3.5, 7.5]

    # Margin of victory: Home - Away ~ Normal(mu_diff, sigma_diff)
    mu_diff = home_exp - away_exp
    sigma_diff = math.sqrt(home_std ** 2 + away_std ** 2)

    # Total: Home + Away ~ Normal(mu_total, sigma_total)
    mu_total = home_exp + away_exp
    # Correlation between team totals is slightly negative (~-0.1) in practice
    correlation = -0.1
    sigma_total = math.sqrt(home_std ** 2 + away_std ** 2 + 2 * correlation * home_std * away_std)

    def fair_odds(p: float) -> float:
        return round(1.0 / p, 2) if p > 0.0001 else 999.0

    # Win probabilities via margin distribution
    if has_draw:
        # Draw band: margin within [-0.5, +0.5] effectively
        p_home = 1.0 - normal_cdf((0.5 - mu_diff) / sigma_diff)
        p_away = normal_cdf((-0.5 - mu_diff) / sigma_diff)
        p_draw = 1.0 - p_home - p_away
        p_draw = max(0.0, p_draw)
    else:
        p_home = 1.0 - normal_cdf((0.0 - mu_diff) / sigma_diff)
        p_away = 1.0 - p_home
        p_draw = 0.0

    result: Dict[str, Any] = {
        "sport_model": "normal",
        "expected_scoring": {
            "home": round(home_exp, 2),
            "away": round(away_exp, 2),
            "total": round(mu_total, 2),
            "home_std": round(home_std, 2),
            "away_std": round(away_std, 2),
            "margin_mean": round(mu_diff, 2),
            "margin_std": round(sigma_diff, 2),
            "unit": scoring_unit,
        },
    }

    if has_draw:
        result["match_result"] = {
            "home_win": {"prob": round(p_home, 4), "pct": f"{p_home * 100:.1f}%", "fair_odds": fair_odds(p_home)},
            "draw": {"prob": round(p_draw, 4), "pct": f"{p_draw * 100:.1f}%", "fair_odds": fair_odds(p_draw)},
            "away_win": {"prob": round(p_away, 4), "pct": f"{p_away * 100:.1f}%", "fair_odds": fair_odds(p_away)},
        }
    else:
        result["match_result"] = {
            "home_win": {"prob": round(p_home, 4), "pct": f"{p_home * 100:.1f}%", "fair_odds": fair_odds(p_home)},
            "away_win": {"prob": round(p_away, 4), "pct": f"{p_away * 100:.1f}%", "fair_odds": fair_odds(p_away)},
        }

    # Over/Under via total distribution
    ou_result = {}
    for line in sorted(ou_lines):
        p_over = 1.0 - normal_cdf((line - mu_total) / sigma_total)
        p_under = 1.0 - p_over
        key_over = f"over_{str(line).replace('.', '_')}"
        key_under = f"under_{str(line).replace('.', '_')}"
        ou_result[key_over] = {"prob": round(p_over, 4), "pct": f"{p_over * 100:.1f}%", "fair_odds": fair_odds(p_over)}
        ou_result[key_under] = {"prob": round(p_under, 4), "pct": f"{p_under * 100:.1f}%", "fair_odds": fair_odds(p_under)}
    result["over_under"] = ou_result

    # Spread / Handicap via margin distribution
    spread_result = {}
    for line in sorted(spread_lines):
        # Home covers line if margin > -line (e.g., home -3.5 covers if margin > 3.5)
        p_cover = 1.0 - normal_cdf((-line - mu_diff) / sigma_diff)
        key = f"home_{'+' if line >= 0 else ''}{line}"
        spread_result[key] = {"prob": round(p_cover, 4), "pct": f"{p_cover * 100:.1f}%", "fair_odds": fair_odds(p_cover)}
    result["spread"] = spread_result

    return result


# ============================================================================
# Expected Value Calculator
# ============================================================================

def evaluate_value(model_prob: float, bookmaker_odds: float) -> Dict[str, Any]:
    """Calculate Expected Value (+EV) and bookmaker implied probability."""
    if bookmaker_odds <= 1.0:
        return {"ev_pct": 0.0, "is_value": False, "implied_pct": "N/A"}
    implied_prob = 1.0 / bookmaker_odds
    edge = (model_prob * bookmaker_odds) - 1.0
    ev_pct = edge * 100.0
    return {
        "market_odds": bookmaker_odds,
        "implied_prob": round(implied_prob, 4),
        "implied_pct": f"{implied_prob * 100:.1f}%",
        "ev_pct": round(ev_pct, 2),
        "is_value": ev_pct > 3.0
    }


# ============================================================================
# Formatted Output
# ============================================================================

def print_report(
    results: Dict[str, Any],
    home_name: str,
    away_name: str,
    competition: str,
    sport_name: str,
    home_exp: float,
    away_exp: float,
    scoring_unit: str,
    has_draw: bool,
    has_btts: bool,
    value_analysis: Dict[str, Any]
) -> None:
    """Print formatted human-readable report."""
    model_label = results.get("sport_model", "unknown").upper()

    print("=" * 68)
    print(f" MATCH PREDICTION ENGINE ({model_label} MODEL)")
    print(f" {home_name.upper()} vs {away_name.upper()}")
    print(f" Sport: {sport_name} | Competition: {competition}")
    print(f" Expected {scoring_unit.title()}: {home_name} ({home_exp:.2f}) - ({away_exp:.2f}) {away_name}")
    print("=" * 68)

    # Match Result
    mr = results["match_result"]
    if has_draw:
        print(f"\n[ MATCH RESULT (1X2) ]")
        print(f"  {home_name} Win: {mr['home_win']['pct']:<7} (Fair Odds: {mr['home_win']['fair_odds']})")
        print(f"  Draw:            {mr['draw']['pct']:<7} (Fair Odds: {mr['draw']['fair_odds']})")
        print(f"  {away_name} Win: {mr['away_win']['pct']:<7} (Fair Odds: {mr['away_win']['fair_odds']})")
    else:
        print(f"\n[ MONEYLINE ]")
        print(f"  {home_name} Win: {mr['home_win']['pct']:<7} (Fair Odds: {mr['home_win']['fair_odds']})")
        print(f"  {away_name} Win: {mr['away_win']['pct']:<7} (Fair Odds: {mr['away_win']['fair_odds']})")

    # Double Chance & DNB (draw sports only)
    if has_draw and "double_chance" in results:
        dc = results["double_chance"]
        dnb = results["draw_no_bet"]
        print(f"\n[ DOUBLE CHANCE & DRAW NO BET ]")
        print(f"  1X ({home_name} or Draw): {dc['1X']['pct']} (Fair: {dc['1X']['fair_odds']})")
        print(f"  X2 (Draw or {away_name}): {dc['X2']['pct']} (Fair: {dc['X2']['fair_odds']})")
        print(f"  DNB {home_name}:          {dnb['home']['pct']} (Fair: {dnb['home']['fair_odds']})")
        print(f"  DNB {away_name}:          {dnb['away']['pct']} (Fair: {dnb['away']['fair_odds']})")

    # Over/Under
    ou = results.get("over_under", {})
    if ou:
        print(f"\n[ OVER/UNDER {scoring_unit.upper()} ]")
        # Pair over/under keys
        over_keys = sorted([k for k in ou if k.startswith("over_")])
        for ok in over_keys:
            uk = ok.replace("over_", "under_")
            line = ok.replace("over_", "").replace("_", ".")
            if uk in ou:
                print(f"  Over {line}:  {ou[ok]['pct']:<7} | Under {line}: {ou[uk]['pct']}")

    # Spread / Handicap
    sp = results.get("spread", {})
    if sp:
        print(f"\n[ SPREAD / HANDICAP ]")
        for key in sorted(sp.keys(), key=lambda k: float(k.replace("home_", "").replace("+", ""))):
            line_val = key.replace("home_", "")
            print(f"  {home_name} {line_val}: {sp[key]['pct']:<7} (Fair: {sp[key]['fair_odds']})")

    # BTTS
    if has_btts and "btts" in results:
        btts = results["btts"]
        print(f"\n[ BOTH TEAMS TO SCORE ]")
        print(f"  BTTS (Yes): {btts['yes']['pct']:<7} | BTTS (No): {btts['no']['pct']}")

    # Top Scorelines (Poisson only)
    if "top_scorelines" in results:
        print(f"\n[ TOP EXACT SCORELINES ]")
        for item in results["top_scorelines"][:5]:
            print(f"  {item['score']:<6} -> Probability: {item['pct']:<6} (Fair Odds: {item['fair_odds']})")

    # Value Analysis
    if value_analysis:
        print(f"\n[ EXPECTED VALUE (+EV) ANALYSIS ]")
        has_val = False
        for market, val in value_analysis.items():
            flag = "[+EV VALUE FOUND]" if val["is_value"] else "[No Edge]"
            print(f"  {market:<20}: Bookmaker {val['market_odds']} (Implied: {val['implied_pct']}) -> Edge: {val['ev_pct']:+.1f}% {flag}")
            if val["is_value"]:
                has_val = True
        if not has_val:
            print("  No positive EV picks found at given odds threshold (>3%).")

    print("=" * 68)


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="match-prediction-engine: Multi-sport quantitative prediction and EV calculator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported sports: """ + ", ".join(list_sports()) + """

Examples:
  # Football (default)
  python3 poisson_model.py --home "Arsenal" --away "Chelsea" --home-xg 1.85 --away-xg 1.15

  # Basketball
  python3 poisson_model.py --sport basketball --home "Lakers" --away "Celtics" --home-xg 112.5 --away-xg 108.0

  # Ice Hockey
  python3 poisson_model.py --sport ice_hockey --home "Rangers" --away "Bruins" --home-xg 3.2 --away-xg 2.7

  # Table Tennis
  python3 poisson_model.py --sport table_tennis --home "Ma Long" --away "Fan Zhendong" --home-xg 11.2 --away-xg 10.5

  # Baseball
  python3 poisson_model.py --sport baseball --home "Yankees" --away "Red Sox" --home-xg 4.8 --away-xg 4.2
        """
    )

    # Sport selection
    parser.add_argument("--sport", type=str, default="football",
                        help=f"Sport type. Options: {', '.join(list_sports())}. Default: football")

    # Direct expected scoring inputs
    parser.add_argument("--home-xg", type=float,
                        help="Direct expected scoring rate for Home team (goals/points/runs)")
    parser.add_argument("--away-xg", type=float,
                        help="Direct expected scoring rate for Away team (goals/points/runs)")

    # Normal model standard deviation overrides
    parser.add_argument("--home-std", type=float,
                        help="Standard deviation for Home team scoring (Normal model only)")
    parser.add_argument("--away-std", type=float,
                        help="Standard deviation for Away team scoring (Normal model only)")

    # Attack / Defense calculation inputs
    parser.add_argument("--home-attack", type=float,
                        help="Home team average scoring rate at home")
    parser.add_argument("--home-defense", type=float,
                        help="Home team average conceded rate at home")
    parser.add_argument("--away-attack", type=float,
                        help="Away team average scoring rate away")
    parser.add_argument("--away-defense", type=float,
                        help="Away team average conceded rate away")
    parser.add_argument("--league-avg-home", type=float, default=None,
                        help="League average home scoring per match (auto-set per sport)")
    parser.add_argument("--league-avg-away", type=float, default=None,
                        help="League average away scoring per match (auto-set per sport)")

    # Metadata
    parser.add_argument("--home", type=str, default="Home Team", help="Home team / player name")
    parser.add_argument("--away", type=str, default="Away Team", help="Away team / player name")
    parser.add_argument("--competition", type=str, default="League", help="Competition name")
    parser.add_argument("--rho", type=float, default=None,
                        help="Dixon-Coles correlation (auto-set per sport, override if needed)")

    # Model override
    parser.add_argument("--model", type=str, default=None, choices=["poisson", "normal"],
                        help="Force a specific model (overrides sport default)")

    # Custom over/under lines
    parser.add_argument("--ou-lines", type=str, default=None,
                        help="Comma-separated over/under lines (e.g., '2.5,3.5,4.5')")

    # Optional Live Odds for Value Calculation
    parser.add_argument("--odds-home", type=float, help="Bookmaker odds for Home win")
    parser.add_argument("--odds-draw", type=float, help="Bookmaker odds for Draw")
    parser.add_argument("--odds-away", type=float, help="Bookmaker odds for Away win")
    parser.add_argument("--odds-o25", type=float, help="Bookmaker odds for Over 2.5 (or primary O/U line)")
    parser.add_argument("--odds-u25", type=float, help="Bookmaker odds for Under 2.5 (or primary O/U line)")
    parser.add_argument("--odds-btts-yes", type=float, help="Bookmaker odds for BTTS Yes")
    parser.add_argument("--odds-btts-no", type=float, help="Bookmaker odds for BTTS No")
    parser.add_argument("--odds-spread", type=float, help="Bookmaker odds for primary spread line")

    parser.add_argument("--json", action="store_true", help="Output raw JSON results")
    parser.add_argument("--list-sports", action="store_true", help="List all supported sports and exit")

    args = parser.parse_args()

    # List sports mode
    if args.list_sports:
        print("Supported Sports:")
        for sport in list_sports():
            p = get_profile(sport)
            print(f"  {p['name']} (--sport {sport}) — model: {p['model']}, "
                  f"unit: {p['scoring_unit']}, draws: {p['has_draw']}")
        return

    # Load sport profile
    try:
        profile = get_profile(args.sport)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine model
    model_type = args.model if args.model else profile["model"]

    # Set defaults from profile
    rho = args.rho if args.rho is not None else profile["rho"]
    max_score = profile["max_score"]
    has_draw = profile["has_draw"]
    has_btts = profile["has_btts"]
    scoring_unit = profile["scoring_unit"]
    league_avg_home = args.league_avg_home if args.league_avg_home else profile["default_home_avg"]
    league_avg_away = args.league_avg_away if args.league_avg_away else profile["default_away_avg"]

    # Parse custom OU lines
    ou_lines = profile["ou_lines"]
    if args.ou_lines:
        ou_lines = [float(x.strip()) for x in args.ou_lines.split(",")]

    spread_lines = profile["spread_lines"]

    # Determine expected scoring
    if args.home_xg is not None and args.away_xg is not None:
        home_exp = args.home_xg
        away_exp = args.away_xg
    elif (args.home_attack is not None and args.home_defense is not None
          and args.away_attack is not None and args.away_defense is not None):
        home_attack_strength = args.home_attack / league_avg_home
        away_defense_strength = args.away_defense / league_avg_home
        home_exp = home_attack_strength * away_defense_strength * league_avg_home

        away_attack_strength = args.away_attack / league_avg_away
        home_defense_strength = args.home_defense / league_avg_away
        away_exp = away_attack_strength * home_defense_strength * league_avg_away
    else:
        home_exp = league_avg_home
        away_exp = league_avg_away

    # Run appropriate model
    if model_type == "normal":
        results = compute_normal_probabilities(
            home_exp, away_exp,
            home_std=args.home_std,
            away_std=args.away_std,
            has_draw=has_draw,
            ou_lines=ou_lines,
            spread_lines=spread_lines,
            scoring_unit=scoring_unit,
        )
    else:
        results = compute_poisson_probabilities(
            home_exp, away_exp,
            rho=rho,
            max_score=max_score,
            has_draw=has_draw,
            has_btts=has_btts,
            ou_lines=ou_lines,
            spread_lines=spread_lines,
            scoring_unit=scoring_unit,
        )

    # Attach metadata
    results["sport"] = profile["name"]
    results["sport_key"] = args.sport

    # Value analysis
    value_analysis = {}
    mr = results["match_result"]

    if args.odds_home:
        value_analysis["Home Win"] = evaluate_value(mr["home_win"]["prob"], args.odds_home)
    if args.odds_draw and "draw" in mr:
        value_analysis["Draw"] = evaluate_value(mr["draw"]["prob"], args.odds_draw)
    if args.odds_away:
        value_analysis["Away Win"] = evaluate_value(mr["away_win"]["prob"], args.odds_away)

    # O/U value: find the closest matching line
    if args.odds_o25:
        ou = results.get("over_under", {})
        # Try exact 2.5, otherwise use first over line
        over_key = "over_2_5"
        if over_key not in ou:
            over_keys = [k for k in ou if k.startswith("over_")]
            over_key = over_keys[0] if over_keys else None
        if over_key and over_key in ou:
            label = over_key.replace("over_", "Over ").replace("_", ".")
            value_analysis[label] = evaluate_value(ou[over_key]["prob"], args.odds_o25)

    if args.odds_u25:
        ou = results.get("over_under", {})
        under_key = "under_2_5"
        if under_key not in ou:
            under_keys = [k for k in ou if k.startswith("under_")]
            under_key = under_keys[0] if under_keys else None
        if under_key and under_key in ou:
            label = under_key.replace("under_", "Under ").replace("_", ".")
            value_analysis[label] = evaluate_value(ou[under_key]["prob"], args.odds_u25)

    if args.odds_btts_yes and "btts" in results:
        value_analysis["BTTS Yes"] = evaluate_value(results["btts"]["yes"]["prob"], args.odds_btts_yes)
    if args.odds_btts_no and "btts" in results:
        value_analysis["BTTS No"] = evaluate_value(results["btts"]["no"]["prob"], args.odds_btts_no)

    if value_analysis:
        results["value_bets"] = value_analysis

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
        return

    print_report(
        results=results,
        home_name=args.home,
        away_name=args.away,
        competition=args.competition,
        sport_name=profile["name"],
        home_exp=home_exp,
        away_exp=away_exp,
        scoring_unit=scoring_unit,
        has_draw=has_draw,
        has_btts=has_btts,
        value_analysis=value_analysis,
    )


if __name__ == "__main__":
    main()
