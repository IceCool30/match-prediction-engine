#!/usr/bin/env python3
"""
match-prediction-engine: Quantitative Soccer Probability & Value Model
Implements Bivariate Poisson distribution with Dixon-Coles low-score adjustment.
Calculates 1X2, Over/Under, BTTS, Double Chance, Draw No Bet, exact scores,
fair odds, and Expected Value (+EV) against bookmaker odds.
No external dependencies required (pure standard library).
"""

import math
import sys
import json
import argparse
from typing import Dict, Any, List, Tuple

def poisson_pmf(k: int, lambd: float) -> float:
    """Calculate standard Poisson PMF: P(k; lambda) = (lambda^k * exp(-lambda)) / k!"""
    if lambd <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

def dixon_coles_tau(x: int, y: int, lambd: float, mu: float, rho: float = -0.11) -> float:
    """
    Dixon-Coles adjustment factor for low-scoring dependence in football.
    Default rho = -0.11 based on empirical historical league data.
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

def compute_probabilities(
    home_exp: float,
    away_exp: float,
    rho: float = -0.11,
    max_goals: int = 10
) -> Dict[str, Any]:
    """Compute full scoreline matrix and derived betting market probabilities."""
    matrix: List[List[float]] = []
    total_prob = 0.0

    # Build scoreline probability matrix
    for h in range(max_goals + 1):
        row = []
        for a in range(max_goals + 1):
            base_p = poisson_pmf(h, home_exp) * poisson_pmf(a, away_exp)
            adj = dixon_coles_tau(h, a, home_exp, away_exp, rho)
            p = max(0.0, base_p * adj)
            row.append(p)
            total_prob += p
        matrix.append(row)

    # Normalize matrix to ensure sum = 1.0
    if total_prob > 0:
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                matrix[h][a] /= total_prob

    # 1X2 Probabilities
    p_home = 0.0
    p_draw = 0.0
    p_away = 0.0

    # Over/Under
    ou_probs = {0.5: 0.0, 1.5: 0.0, 2.5: 0.0, 3.5: 0.0, 4.5: 0.0}

    # BTTS
    btts_yes = 0.0
    btts_no = 0.0

    # Clean Sheets & Win to Nil
    clean_sheet_home = 0.0
    clean_sheet_away = 0.0
    win_to_nil_home = 0.0
    win_to_nil_away = 0.0

    score_ranking: List[Tuple[str, float]] = []

    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = matrix[h][a]
            tot_goals = h + a

            if h > a:
                p_home += prob
                if a == 0:
                    win_to_nil_home += prob
            elif h == a:
                p_draw += prob
            else:
                p_away += prob
                if h == 0:
                    win_to_nil_away += prob

            if a == 0:
                clean_sheet_home += prob
            if h == 0:
                clean_sheet_away += prob

            if h > 0 and a > 0:
                btts_yes += prob
            else:
                btts_no += prob

            for line in ou_probs.keys():
                if tot_goals > line:
                    ou_probs[line] += prob

            score_ranking.append((f"{h}-{a}", prob))

    score_ranking.sort(key=lambda x: x[1], reverse=True)

    # Derived Markets
    p_1x = p_home + p_draw
    p_x2 = p_draw + p_away
    p_12 = p_home + p_away

    # Draw No Bet (re-normalized conditional on no draw)
    non_draw = p_home + p_away
    dnb_home = (p_home / non_draw) if non_draw > 0 else 0.5
    dnb_away = (p_away / non_draw) if non_draw > 0 else 0.5

    def fair_odds(p: float) -> float:
        return round(1.0 / p, 2) if p > 0.0001 else 999.0

    return {
        "expected_goals": {
            "home": round(home_exp, 2),
            "away": round(away_exp, 2),
            "total": round(home_exp + away_exp, 2)
        },
        "1x2": {
            "home": {"prob": round(p_home, 4), "pct": f"{p_home * 100:.1f}%", "fair_odds": fair_odds(p_home)},
            "draw": {"prob": round(p_draw, 4), "pct": f"{p_draw * 100:.1f}%", "fair_odds": fair_odds(p_draw)},
            "away": {"prob": round(p_away, 4), "pct": f"{p_away * 100:.1f}%", "fair_odds": fair_odds(p_away)},
        },
        "double_chance": {
            "1X": {"prob": round(p_1x, 4), "pct": f"{p_1x * 100:.1f}%", "fair_odds": fair_odds(p_1x)},
            "X2": {"prob": round(p_x2, 4), "pct": f"{p_x2 * 100:.1f}%", "fair_odds": fair_odds(p_x2)},
            "12": {"prob": round(p_12, 4), "pct": f"{p_12 * 100:.1f}%", "fair_odds": fair_odds(p_12)},
        },
        "draw_no_bet": {
            "home": {"prob": round(dnb_home, 4), "pct": f"{dnb_home * 100:.1f}%", "fair_odds": fair_odds(dnb_home)},
            "away": {"prob": round(dnb_away, 4), "pct": f"{dnb_away * 100:.1f}%", "fair_odds": fair_odds(dnb_away)},
        },
        "over_under": {
            "over_1_5": {"prob": round(ou_probs[1.5], 4), "pct": f"{ou_probs[1.5] * 100:.1f}%", "fair_odds": fair_odds(ou_probs[1.5])},
            "under_1_5": {"prob": round(1 - ou_probs[1.5], 4), "pct": f"{(1 - ou_probs[1.5]) * 100:.1f}%", "fair_odds": fair_odds(1 - ou_probs[1.5])},
            "over_2_5": {"prob": round(ou_probs[2.5], 4), "pct": f"{ou_probs[2.5] * 100:.1f}%", "fair_odds": fair_odds(ou_probs[2.5])},
            "under_2_5": {"prob": round(1 - ou_probs[2.5], 4), "pct": f"{(1 - ou_probs[2.5]) * 100:.1f}%", "fair_odds": fair_odds(1 - ou_probs[2.5])},
            "over_3_5": {"prob": round(ou_probs[3.5], 4), "pct": f"{ou_probs[3.5] * 100:.1f}%", "fair_odds": fair_odds(ou_probs[3.5])},
            "under_3_5": {"prob": round(1 - ou_probs[3.5], 4), "pct": f"{(1 - ou_probs[3.5]) * 100:.1f}%", "fair_odds": fair_odds(1 - ou_probs[3.5])},
        },
        "btts": {
            "yes": {"prob": round(btts_yes, 4), "pct": f"{btts_yes * 100:.1f}%", "fair_odds": fair_odds(btts_yes)},
            "no": {"prob": round(btts_no, 4), "pct": f"{btts_no * 100:.1f}%", "fair_odds": fair_odds(btts_no)},
        },
        "clean_sheets": {
            "home": {"prob": round(clean_sheet_home, 4), "pct": f"{clean_sheet_home * 100:.1f}%"},
            "away": {"prob": round(clean_sheet_away, 4), "pct": f"{clean_sheet_away * 100:.1f}%"},
        },
        "top_scorelines": [
            {"score": s[0], "prob": round(s[1], 4), "pct": f"{s[1] * 100:.1f}%", "fair_odds": fair_odds(s[1])}
            for s in score_ranking[:6]
        ]
    }

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
        "is_value": ev_pct > 3.0  # Threshold of 3% positive expected value
    }

def main():
    parser = argparse.ArgumentParser(
        description="match-prediction-engine: Quantitative soccer prediction and EV calculator."
    )
    # Direct xG / Expectation Inputs
    parser.add_argument("--home-xg", type=float, help="Direct expected goals for Home team")
    parser.add_argument("--away-xg", type=float, help="Direct expected goals for Away team")

    # Or Attack / Defense calculation inputs
    parser.add_argument("--home-attack", type=float, help="Home team average goals/xG scored at home")
    parser.add_argument("--home-defense", type=float, help="Home team average goals/xG conceded at home")
    parser.add_argument("--away-attack", type=float, help="Away team average goals/xG scored away")
    parser.add_argument("--away-defense", type=float, help="Away team average goals/xG conceded away")
    parser.add_argument("--league-avg-home", type=float, default=1.52, help="League average home goals per match (default 1.52)")
    parser.add_argument("--league-avg-away", type=float, default=1.20, help="League average away goals per match (default 1.20)")

    # Metadata
    parser.add_argument("--home", type=str, default="Home Team", help="Home team name")
    parser.add_argument("--away", type=str, default="Away Team", help="Away team name")
    parser.add_argument("--competition", type=str, default="League", help="Competition name")
    parser.add_argument("--rho", type=float, default=-0.11, help="Dixon-Coles correlation factor (default -0.11)")

    # Optional Live Odds for Value Calculation
    parser.add_argument("--odds-home", type=float, help="Bookmaker odds for Home win")
    parser.add_argument("--odds-draw", type=float, help="Bookmaker odds for Draw")
    parser.add_argument("--odds-away", type=float, help="Bookmaker odds for Away win")
    parser.add_argument("--odds-o25", type=float, help="Bookmaker odds for Over 2.5 goals")
    parser.add_argument("--odds-u25", type=float, help="Bookmaker odds for Under 2.5 goals")
    parser.add_argument("--odds-btts-yes", type=float, help="Bookmaker odds for BTTS Yes")
    parser.add_argument("--odds-btts-no", type=float, help="Bookmaker odds for BTTS No")

    parser.add_argument("--json", action="store_true", help="Output raw JSON results")

    args = parser.parse_args()

    # Determine Expected Goals (Lambda & Mu)
    if args.home_xg is not None and args.away_xg is not None:
        home_exp = args.home_xg
        away_exp = args.away_xg
    elif (
        args.home_attack is not None
        and args.home_defense is not None
        and args.away_attack is not None
        and args.away_defense is not None
    ):
        home_attack_strength = args.home_attack / args.league_avg_home
        away_defense_strength = args.away_defense / args.league_avg_home
        home_exp = home_attack_strength * away_defense_strength * args.league_avg_home

        away_attack_strength = args.away_attack / args.league_avg_away
        home_defense_strength = args.home_defense / args.league_avg_away
        away_exp = away_attack_strength * home_defense_strength * args.league_avg_away
    else:
        # Fallback default baseline if neither specified
        home_exp = 1.45
        away_exp = 1.15

    results = compute_probabilities(home_exp, away_exp, rho=args.rho)

    # Attach Value Evaluations if odds provided
    value_analysis = {}
    if args.odds_home:
        value_analysis["Home Win"] = evaluate_value(results["1x2"]["home"]["prob"], args.odds_home)
    if args.odds_draw:
        value_analysis["Draw"] = evaluate_value(results["1x2"]["draw"]["prob"], args.odds_draw)
    if args.odds_away:
        value_analysis["Away Win"] = evaluate_value(results["1x2"]["away"]["prob"], args.odds_away)
    if args.odds_o25:
        value_analysis["Over 2.5 Goals"] = evaluate_value(results["over_under"]["over_2_5"]["prob"], args.odds_o25)
    if args.odds_u25:
        value_analysis["Under 2.5 Goals"] = evaluate_value(results["over_under"]["under_2_5"]["prob"], args.odds_u25)
    if args.odds_btts_yes:
        value_analysis["BTTS Yes"] = evaluate_value(results["btts"]["yes"]["prob"], args.odds_btts_yes)
    if args.odds_btts_no:
        value_analysis["BTTS No"] = evaluate_value(results["btts"]["no"]["prob"], args.odds_btts_no)

    if value_analysis:
        results["value_bets"] = value_analysis

    if args.json:
        print(json.dumps(results, indent=2))
        return

    # Print Formatted Human Report
    print("=" * 64)
    print(f" MATCH PREDICTION ENGINE: {args.home.upper()} vs {args.away.upper()}")
    print(f" Competition: {args.competition}")
    print(f" Modeled xG Expectation: {args.home} ({home_exp:.2f}) - ({away_exp:.2f}) {args.away}")
    print("=" * 64)

    print("\n[ 1X2 MATCH OUTCOME ]")
    print(f"  {args.home} Win: {results['1x2']['home']['pct']:<7} (Fair Odds: {results['1x2']['home']['fair_odds']})")
    print(f"  Draw:            {results['1x2']['draw']['pct']:<7} (Fair Odds: {results['1x2']['draw']['fair_odds']})")
    print(f"  {args.away} Win: {results['1x2']['away']['pct']:<7} (Fair Odds: {results['1x2']['away']['fair_odds']})")

    print("\n[ DOUBLE CHANCE & DRAW NO BET ]")
    print(f"  1X ({args.home} or Draw): {results['double_chance']['1X']['pct']} (Fair: {results['double_chance']['1X']['fair_odds']})")
    print(f"  X2 (Draw or {args.away}): {results['double_chance']['X2']['pct']} (Fair: {results['double_chance']['X2']['fair_odds']})")
    print(f"  DNB {args.home}:          {results['draw_no_bet']['home']['pct']} (Fair: {results['draw_no_bet']['home']['fair_odds']})")
    print(f"  DNB {args.away}:          {results['draw_no_bet']['away']['pct']} (Fair: {results['draw_no_bet']['away']['fair_odds']})")

    print("\n[ GOALS & BOTH TEAMS TO SCORE ]")
    print(f"  Over 1.5 Goals:  {results['over_under']['over_1_5']['pct']:<7} | Under 1.5: {results['over_under']['under_1_5']['pct']}")
    print(f"  Over 2.5 Goals:  {results['over_under']['over_2_5']['pct']:<7} | Under 2.5: {results['over_under']['under_2_5']['pct']}")
    print(f"  Over 3.5 Goals:  {results['over_under']['over_3_5']['pct']:<7} | Under 3.5: {results['over_under']['under_3_5']['pct']}")
    print(f"  BTTS (Yes):      {results['btts']['yes']['pct']:<7} | BTTS (No):  {results['btts']['no']['pct']}")

    print("\n[ TOP EXACT SCORELINES ]")
    for item in results["top_scorelines"][:4]:
        print(f"  {item['score']:<6} -> Probability: {item['pct']:<6} (Fair Odds: {item['fair_odds']})")

    if value_analysis:
        print("\n[ EXPECTED VALUE (+EV) ANALYSIS ]")
        has_val = False
        for market, val in value_analysis.items():
            flag = "[+EV VALUE FOUND]" if val["is_value"] else "[No Edge]"
            print(f"  {market:<16}: Bookmaker {val['market_odds']} (Implied: {val['implied_pct']}) -> Edge: {val['ev_pct']:+.1f}% {flag}")
            if val["is_value"]:
                has_val = True
        if not has_val:
            print("  No positive EV picks found at given odds threshold (>3%).")

    print("=" * 64)

if __name__ == "__main__":
    main()
