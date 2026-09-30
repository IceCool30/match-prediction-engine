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
import re
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


def tennis_game_to_set_prob(g: float) -> float:
    """
    Exact Markov tennis set win probability from game win probability g.
    Calibrated to standard 6-game set with tiebreak at 6-6.
    """
    if g <= 0.0:
        return 0.0
    if g >= 1.0:
        return 1.0
    q = 1.0 - g
    # Set won 6-0, 6-1, 6-2, 6-3, 6-4
    p_before = sum(math.comb(5 + k, k) * (g ** 6) * (q ** k) for k in range(5))
    # Reach 5-5
    p_55 = math.comb(10, 5) * (g ** 5) * (q ** 5)
    # Tiebreak win probability (approx from game win probability)
    tb_denom = (g ** 2) + (q ** 2)
    tb_win = (g ** 2) / tb_denom if tb_denom > 0 else 0.5
    # From 5-5: win 7-5 (g^2) or win tiebreak 7-6 (2*g*q*tb_win)
    p_after = p_55 * (g ** 2 + 2.0 * g * q * tb_win)
    return max(0.0, min(1.0, p_before + p_after))


def table_tennis_point_to_game_prob(r: float) -> float:
    """
    Exact table tennis set win probability from point win ratio r (game to 11, win by 2).
    """
    if r <= 0.0:
        return 0.0
    if r >= 1.0:
        return 1.0
    q = 1.0 - r
    # Win before deuce: 11-0, 11-1, ..., 11-9
    p_before = sum(math.comb(10 + k, k) * (r ** 11) * (q ** k) for k in range(10))
    # Deuce at 10-10
    p_1010 = math.comb(20, 10) * (r ** 10) * (q ** 10)
    # Win from deuce
    deuce_denom = (r ** 2) + (q ** 2)
    p_deuce_win = (r ** 2) / deuce_denom if deuce_denom > 0 else 0.5
    return max(0.0, min(1.0, p_before + p_1010 * p_deuce_win))


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

    # Win to Nil & Clean Sheets
    win_to_nil_home = sum(matrix[h][0] for h in range(1, max_score + 1))
    win_to_nil_away = sum(matrix[0][a] for a in range(1, max_score + 1))
    result["win_to_nil"] = {
        "home": {"prob": round(win_to_nil_home, 4), "pct": f"{win_to_nil_home * 100:.1f}%", "fair_odds": fair_odds(win_to_nil_home)},
        "away": {"prob": round(win_to_nil_away, 4), "pct": f"{win_to_nil_away * 100:.1f}%", "fair_odds": fair_odds(win_to_nil_away)},
    }

    # Team Totals (Home / Away Over & Under)
    team_tot_lines = [0.5, 1.5, 2.5, 3.5]
    team_totals = {"home": {}, "away": {}}
    for tl in team_tot_lines:
        p_h_over = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h > tl)
        p_h_under = 1.0 - p_h_over
        p_a_over = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if a > tl)
        p_a_under = 1.0 - p_a_over
        k_over = f"over_{str(tl).replace('.', '_')}"
        k_under = f"under_{str(tl).replace('.', '_')}"
        team_totals["home"][k_over] = {"prob": round(p_h_over, 4), "pct": f"{p_h_over * 100:.1f}%", "fair_odds": fair_odds(p_h_over)}
        team_totals["home"][k_under] = {"prob": round(p_h_under, 4), "pct": f"{p_h_under * 100:.1f}%", "fair_odds": fair_odds(p_h_under)}
        team_totals["away"][k_over] = {"prob": round(p_a_over, 4), "pct": f"{p_a_over * 100:.1f}%", "fair_odds": fair_odds(p_a_over)}
        team_totals["away"][k_under] = {"prob": round(p_a_under, 4), "pct": f"{p_a_under * 100:.1f}%", "fair_odds": fair_odds(p_a_under)}
    result["team_totals"] = team_totals

    # Combo Markets (Double Chance & Totals, 1X2 & Totals, BTTS & Totals)
    combos = {}
    for cl in [1.5, 2.5, 3.5, 4.5]:
        p_1x_u = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h >= a and (h + a) < cl)
        p_1x_o = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h >= a and (h + a) > cl)
        p_x2_u = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h <= a and (h + a) < cl)
        p_x2_o = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h <= a and (h + a) > cl)
        p_1_u = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h > a and (h + a) < cl)
        p_1_o = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h > a and (h + a) > cl)
        p_2_u = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h < a and (h + a) < cl)
        p_2_o = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if h < a and (h + a) > cl)
        combos[f"1X & Under {cl}"] = {"prob": round(p_1x_u, 4), "pct": f"{p_1x_u * 100:.1f}%", "fair_odds": fair_odds(p_1x_u)}
        combos[f"1X & Over {cl}"] = {"prob": round(p_1x_o, 4), "pct": f"{p_1x_o * 100:.1f}%", "fair_odds": fair_odds(p_1x_o)}
        combos[f"X2 & Under {cl}"] = {"prob": round(p_x2_u, 4), "pct": f"{p_x2_u * 100:.1f}%", "fair_odds": fair_odds(p_x2_u)}
        combos[f"X2 & Over {cl}"] = {"prob": round(p_x2_o, 4), "pct": f"{p_x2_o * 100:.1f}%", "fair_odds": fair_odds(p_x2_o)}
        combos[f"1 & Under {cl}"] = {"prob": round(p_1_u, 4), "pct": f"{p_1_u * 100:.1f}%", "fair_odds": fair_odds(p_1_u)}
        combos[f"1 & Over {cl}"] = {"prob": round(p_1_o, 4), "pct": f"{p_1_o * 100:.1f}%", "fair_odds": fair_odds(p_1_o)}
        combos[f"2 & Under {cl}"] = {"prob": round(p_2_u, 4), "pct": f"{p_2_u * 100:.1f}%", "fair_odds": fair_odds(p_2_u)}
        combos[f"2 & Over {cl}"] = {"prob": round(p_2_o, 4), "pct": f"{p_2_o * 100:.1f}%", "fair_odds": fair_odds(p_2_o)}

    # BTTS Combos
    p_btts_o25 = sum(matrix[h][a] for h in range(1, max_score + 1) for a in range(1, max_score + 1) if (h + a) > 2.5)
    p_btts_u25 = sum(matrix[h][a] for h in range(1, max_score + 1) for a in range(1, max_score + 1) if (h + a) < 2.5)
    p_1_btts_y = sum(matrix[h][a] for h in range(1, max_score + 1) for a in range(1, max_score + 1) if h > a)
    p_1_btts_n = win_to_nil_home
    p_2_btts_y = sum(matrix[h][a] for h in range(1, max_score + 1) for a in range(1, max_score + 1) if a > h)
    p_2_btts_n = win_to_nil_away
    p_x_btts_y = sum(matrix[h][h] for h in range(1, max_score + 1))
    p_x_btts_n = matrix[0][0]
    combos["BTTS & Over 2.5"] = {"prob": round(p_btts_o25, 4), "pct": f"{p_btts_o25 * 100:.1f}%", "fair_odds": fair_odds(p_btts_o25)}
    combos["BTTS & Under 2.5"] = {"prob": round(p_btts_u25, 4), "pct": f"{p_btts_u25 * 100:.1f}%", "fair_odds": fair_odds(p_btts_u25)}
    combos["1 & BTTS Yes"] = {"prob": round(p_1_btts_y, 4), "pct": f"{p_1_btts_y * 100:.1f}%", "fair_odds": fair_odds(p_1_btts_y)}
    combos["1 & BTTS No"] = {"prob": round(p_1_btts_n, 4), "pct": f"{p_1_btts_n * 100:.1f}%", "fair_odds": fair_odds(p_1_btts_n)}
    combos["2 & BTTS Yes"] = {"prob": round(p_2_btts_y, 4), "pct": f"{p_2_btts_y * 100:.1f}%", "fair_odds": fair_odds(p_2_btts_y)}
    combos["2 & BTTS No"] = {"prob": round(p_2_btts_n, 4), "pct": f"{p_2_btts_n * 100:.1f}%", "fair_odds": fair_odds(p_2_btts_n)}
    combos["X & BTTS Yes"] = {"prob": round(p_x_btts_y, 4), "pct": f"{p_x_btts_y * 100:.1f}%", "fair_odds": fair_odds(p_x_btts_y)}
    combos["X & BTTS No"] = {"prob": round(p_x_btts_n, 4), "pct": f"{p_x_btts_n * 100:.1f}%", "fair_odds": fair_odds(p_x_btts_n)}
    result["combos"] = combos

    # Goal Bands / Multi-Goals
    bands_def = [
        ("0-1", 0, 1), ("1-2", 1, 2), ("1-3", 1, 3), ("2-3", 2, 3),
        ("2-4", 2, 4), ("2-5", 2, 5), ("3-4", 3, 4), ("3-5", 3, 5),
        ("4-6", 4, 6), ("7+", 7, 30)
    ]
    goal_bands = {}
    for b_label, b_min, b_max in bands_def:
        bp = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if b_min <= (h + a) <= b_max)
        goal_bands[b_label] = {"prob": round(bp, 4), "pct": f"{bp * 100:.1f}%", "fair_odds": fair_odds(bp)}
    result["goal_bands"] = goal_bands

    # Odd / Even Goals
    p_odd = sum(matrix[h][a] for h in range(max_score + 1) for a in range(max_score + 1) if (h + a) % 2 == 1)
    p_even = 1.0 - p_odd
    result["odd_even"] = {
        "odd": {"prob": round(p_odd, 4), "pct": f"{p_odd * 100:.1f}%", "fair_odds": fair_odds(p_odd)},
        "even": {"prob": round(p_even, 4), "pct": f"{p_even * 100:.1f}%", "fair_odds": fair_odds(p_even)},
    }

    # Half-Time / Full-Time (HT/FT) and Halves Markets
    if has_draw:
        lh1, la1 = 0.45 * home_exp, 0.45 * away_exp
        lh2, la2 = 0.55 * home_exp, 0.55 * away_exp
        htft_probs = {}
        for h1 in range(7):
            for a1 in range(7):
                p1 = poisson_pmf(h1, lh1) * poisson_pmf(a1, la1)
                r1 = "1" if h1 > a1 else ("2" if h1 < a1 else "X")
                for h2 in range(7):
                    for a2 in range(7):
                        p2 = poisson_pmf(h2, lh2) * poisson_pmf(a2, la2)
                        hf = h1 + h2
                        af = a1 + a2
                        rf = "1" if hf > af else ("2" if hf < af else "X")
                        key = f"{r1}/{rf}"
                        htft_probs[key] = htft_probs.get(key, 0.0) + (p1 * p2)
        tot_htft = sum(htft_probs.values())
        if tot_htft > 0:
            for k in htft_probs:
                htft_probs[k] /= tot_htft
        result["half_time_full_time"] = {
            k: {"prob": round(v, 4), "pct": f"{v * 100:.1f}%", "fair_odds": fair_odds(v)}
            for k, v in htft_probs.items()
        }

        # Both Halves Scoring & Win Either Half
        p_h_both = (1.0 - math.exp(-lh1)) * (1.0 - math.exp(-lh2))
        p_a_both = (1.0 - math.exp(-la1)) * (1.0 - math.exp(-la2))
        result["both_halves"] = {
            "home_score_both_halves": {"prob": round(p_h_both, 4), "pct": f"{p_h_both * 100:.1f}%", "fair_odds": fair_odds(p_h_both)},
            "away_score_both_halves": {"prob": round(p_a_both, 4), "pct": f"{p_a_both * 100:.1f}%", "fair_odds": fair_odds(p_a_both)},
        }

    # Store normalized scoreline matrix for dynamic arbitrary queries
    result["_scoreline_matrix"] = matrix

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
    # Team Totals (Home & Away)
    tt_offsets = [-8.5, -4.5, -0.5, 3.5, 7.5]
    team_totals = {"home": {}, "away": {}}
    for off in tt_offsets:
        hl = round(home_exp + off, 1)
        al = round(away_exp + off, 1)
        p_h_o = 1.0 - normal_cdf((hl - home_exp) / home_std) if home_std > 0 else 0.5
        p_h_u = 1.0 - p_h_o
        p_a_o = 1.0 - normal_cdf((al - away_exp) / away_std) if away_std > 0 else 0.5
        p_a_u = 1.0 - p_a_o
        k_ho = f"over_{str(hl).replace('.', '_')}"
        k_hu = f"under_{str(hl).replace('.', '_')}"
        k_ao = f"over_{str(al).replace('.', '_')}"
        k_au = f"under_{str(al).replace('.', '_')}"
        team_totals["home"][k_ho] = {"prob": round(p_h_o, 4), "pct": f"{p_h_o * 100:.1f}%", "fair_odds": fair_odds(p_h_o)}
        team_totals["home"][k_hu] = {"prob": round(p_h_u, 4), "pct": f"{p_h_u * 100:.1f}%", "fair_odds": fair_odds(p_h_u)}
        team_totals["away"][k_ao] = {"prob": round(p_a_o, 4), "pct": f"{p_a_o * 100:.1f}%", "fair_odds": fair_odds(p_a_o)}
        team_totals["away"][k_au] = {"prob": round(p_a_u, 4), "pct": f"{p_a_u * 100:.1f}%", "fair_odds": fair_odds(p_a_u)}
    result["team_totals"] = team_totals

    # Half-Time / Full-Time for Basketball / High-Scoring
    mu_1h_diff = mu_diff * 0.485
    sigma_1h_diff = sigma_diff * math.sqrt(0.485)
    p_1h_home = 1.0 - normal_cdf((0.0 - mu_1h_diff) / sigma_1h_diff) if sigma_1h_diff > 0 else 0.5
    p_1h_away = 1.0 - p_1h_home
    # Joint FT/HT modeling
    p_11 = p_1h_home * 0.88 if p_home > 0.5 else p_1h_home * 0.70
    p_22 = p_1h_away * 0.88 if p_away > 0.5 else p_1h_away * 0.70
    p_12 = max(0.01, p_away - p_22)
    p_21 = max(0.01, p_home - p_11)
    tot_htft = p_11 + p_22 + p_12 + p_21
    if tot_htft > 0:
        p_11 /= tot_htft
        p_22 /= tot_htft
        p_12 /= tot_htft
        p_21 /= tot_htft
    result["half_time_full_time"] = {
        "1/1": {"prob": round(p_11, 4), "pct": f"{p_11 * 100:.1f}%", "fair_odds": fair_odds(p_11)},
        "2/2": {"prob": round(p_22, 4), "pct": f"{p_22 * 100:.1f}%", "fair_odds": fair_odds(p_22)},
        "1/2": {"prob": round(p_12, 4), "pct": f"{p_12 * 100:.1f}%", "fair_odds": fair_odds(p_12)},
        "2/1": {"prob": round(p_21, 4), "pct": f"{p_21 * 100:.1f}%", "fair_odds": fair_odds(p_21)},
    }

    return result


# ============================================================================
# Tennis Model (Best of 3 / Best of 5 Markov Sets)
# ============================================================================

def compute_tennis_probabilities(
    home_exp: float,
    away_exp: float,
    match_format: str = "best_of_3",
    ou_lines: List[float] = None,
    spread_lines: List[float] = None,
    scoring_unit: str = "games"
) -> Dict[str, Any]:
    """
    Quantitative probability model for Tennis.
    Calculates exact set betting (2-0, 2-1, 0-2, 1-2), set handicaps (+1.5, -1.5),
    total sets (over/under 2.5), game totals, and game handicaps.
    """
    if ou_lines is None:
        ou_lines = [19.5, 20.5, 21.5, 22.5, 23.5, 24.5]
    if spread_lines is None:
        spread_lines = [-4.5, -3.5, -2.5, -1.5, 1.5, 2.5, 3.5, 4.5]

    tot_exp = home_exp + away_exp
    g = home_exp / tot_exp if tot_exp > 0 else 0.5
    p_set = tennis_game_to_set_prob(g)
    q_set = 1.0 - p_set

    def fair_odds(p: float) -> float:
        return round(1.0 / p, 2) if p > 0.0001 else 999.0

    # Best of 3 sets mechanics
    p_20 = p_set ** 2
    p_21 = 2.0 * (p_set ** 2) * q_set
    p_02 = q_set ** 2
    p_12 = 2.0 * (q_set ** 2) * p_set

    p_home_win = p_20 + p_21
    p_away_win = p_02 + p_12

    # Set handicaps
    p_home_m15 = p_20
    p_home_p15 = 1.0 - p_02
    p_away_m15 = p_02
    p_away_p15 = 1.0 - p_20

    # Total sets
    p_over_25 = p_21 + p_12
    p_under_25 = p_20 + p_02

    # Total games mixture model (2-set matches ~19.4 games, 3-set matches ~28.5 games)
    mu_2, sigma_2 = 19.4, 2.2
    mu_3, sigma_3 = 28.5, 2.8

    ou_result = {}
    for line in sorted(ou_lines):
        p_o2 = 1.0 - normal_cdf((line - mu_2) / sigma_2)
        p_o3 = 1.0 - normal_cdf((line - mu_3) / sigma_3)
        p_over = (p_under_25 * p_o2) + (p_over_25 * p_o3)
        p_under = 1.0 - p_over
        k_over = f"over_{str(line).replace('.', '_')}"
        k_under = f"under_{str(line).replace('.', '_')}"
        ou_result[k_over] = {"prob": round(p_over, 4), "pct": f"{p_over * 100:.1f}%", "fair_odds": fair_odds(p_over)}
        ou_result[k_under] = {"prob": round(p_under, 4), "pct": f"{p_under * 100:.1f}%", "fair_odds": fair_odds(p_under)}

    # Game spread / handicap
    spread_result = {}
    mu_margin = (2.0 * p_set - 1.0) * 5.8
    sigma_margin = 4.2
    for line in sorted(spread_lines):
        p_cover = 1.0 - normal_cdf((-line - mu_margin) / sigma_margin)
        key = f"home_{'+' if line >= 0 else ''}{line}"
        spread_result[key] = {"prob": round(p_cover, 4), "pct": f"{p_cover * 100:.1f}%", "fair_odds": fair_odds(p_cover)}

    score_ranking = [
        ("2-0", p_20),
        ("2-1", p_21),
        ("1-2", p_12),
        ("0-2", p_02),
    ]
    score_ranking.sort(key=lambda x: x[1], reverse=True)

    result = {
        "sport_model": "tennis",
        "expected_scoring": {
            "home": round(home_exp, 2),
            "away": round(away_exp, 2),
            "total": round(tot_exp, 2),
            "game_win_prob_home": round(g, 4),
            "set_win_prob_home": round(p_set, 4),
            "unit": scoring_unit,
        },
        "match_result": {
            "home_win": {"prob": round(p_home_win, 4), "pct": f"{p_home_win * 100:.1f}%", "fair_odds": fair_odds(p_home_win)},
            "away_win": {"prob": round(p_away_win, 4), "pct": f"{p_away_win * 100:.1f}%", "fair_odds": fair_odds(p_away_win)},
        },
        "set_betting": {
            "2-0": {"prob": round(p_20, 4), "pct": f"{p_20 * 100:.1f}%", "fair_odds": fair_odds(p_20)},
            "2-1": {"prob": round(p_21, 4), "pct": f"{p_21 * 100:.1f}%", "fair_odds": fair_odds(p_21)},
            "0-2": {"prob": round(p_02, 4), "pct": f"{p_02 * 100:.1f}%", "fair_odds": fair_odds(p_02)},
            "1-2": {"prob": round(p_12, 4), "pct": f"{p_12 * 100:.1f}%", "fair_odds": fair_odds(p_12)},
        },
        "set_handicap": {
            "home -1.5 sets": {"prob": round(p_home_m15, 4), "pct": f"{p_home_m15 * 100:.1f}%", "fair_odds": fair_odds(p_home_m15)},
            "home +1.5 sets": {"prob": round(p_home_p15, 4), "pct": f"{p_home_p15 * 100:.1f}%", "fair_odds": fair_odds(p_home_p15)},
            "away -1.5 sets": {"prob": round(p_away_m15, 4), "pct": f"{p_away_m15 * 100:.1f}%", "fair_odds": fair_odds(p_away_m15)},
            "away +1.5 sets": {"prob": round(p_away_p15, 4), "pct": f"{p_away_p15 * 100:.1f}%", "fair_odds": fair_odds(p_away_p15)},
        },
        "total_sets": {
            "over_2_5": {"prob": round(p_over_25, 4), "pct": f"{p_over_25 * 100:.1f}%", "fair_odds": fair_odds(p_over_25)},
            "under_2_5": {"prob": round(p_under_25, 4), "pct": f"{p_under_25 * 100:.1f}%", "fair_odds": fair_odds(p_under_25)},
        },
        "first_set_winner": {
            "home": {"prob": round(p_set, 4), "pct": f"{p_set * 100:.1f}%", "fair_odds": fair_odds(p_set)},
            "away": {"prob": round(q_set, 4), "pct": f"{q_set * 100:.1f}%", "fair_odds": fair_odds(q_set)},
        },
        "over_under": ou_result,
        "spread": spread_result,
        "top_scorelines": [
            {"score": s[0], "prob": round(s[1], 4), "pct": f"{s[1] * 100:.1f}%", "fair_odds": fair_odds(s[1])}
            for s in score_ranking
        ]
    }
    return result


# ============================================================================
# Table Tennis Model (Best of 5 ITTF Sets)
# ============================================================================

def compute_table_tennis_probabilities(
    home_exp: float,
    away_exp: float,
    ou_lines: List[float] = None,
    spread_lines: List[float] = None,
    scoring_unit: str = "points"
) -> Dict[str, Any]:
    """
    Quantitative probability model for Table Tennis (Best of 5 sets).
    Calculates exact set betting (3:0, 3:1, 3:2, 0:3, 1:3, 2:3), set handicaps (+1.5, -1.5, +2.5, -2.5),
    total sets (over/under 3.5, 4.5), and total match points.
    """
    if ou_lines is None:
        ou_lines = [71.5, 73.5, 74.5, 75.5, 77.5]
    if spread_lines is None:
        spread_lines = [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5]

    tot_exp = home_exp + away_exp
    r = home_exp / tot_exp if tot_exp > 0 else 0.5
    p_set = table_tennis_point_to_game_prob(r)
    q_set = 1.0 - p_set

    def fair_odds(p: float) -> float:
        return round(1.0 / p, 2) if p > 0.0001 else 999.0

    p_30 = p_set ** 3
    p_31 = 3.0 * (p_set ** 3) * q_set
    p_32 = 6.0 * (p_set ** 3) * (q_set ** 2)
    p_03 = q_set ** 3
    p_13 = 3.0 * (q_set ** 3) * p_set
    p_23 = 6.0 * (q_set ** 3) * (p_set ** 2)

    tot_comb = p_30 + p_31 + p_32 + p_03 + p_13 + p_23
    if tot_comb > 0:
        p_30 /= tot_comb
        p_31 /= tot_comb
        p_32 /= tot_comb
        p_03 /= tot_comb
        p_13 /= tot_comb
        p_23 /= tot_comb

    p_home_win = p_30 + p_31 + p_32
    p_away_win = p_03 + p_13 + p_23

    p_home_m15 = p_30 + p_31
    p_home_m25 = p_30
    p_home_p15 = 1.0 - (p_03 + p_13)
    p_home_p25 = 1.0 - p_03

    p_away_m15 = p_03 + p_13
    p_away_m25 = p_03
    p_away_p15 = 1.0 - (p_30 + p_31)
    p_away_p25 = 1.0 - p_30

    p_sets_3 = p_30 + p_03
    p_sets_4 = p_31 + p_13
    p_sets_5 = p_32 + p_23

    p_over_35 = p_sets_4 + p_sets_5
    p_under_35 = p_sets_3
    p_over_45 = p_sets_5
    p_under_45 = 1.0 - p_sets_5

    mu_3, sigma_3 = 55.2, 3.2
    mu_4, sigma_4 = 73.6, 3.8
    mu_5, sigma_5 = 92.0, 4.5

    ou_result = {}
    for line in sorted(ou_lines):
        p_o3 = 1.0 - normal_cdf((line - mu_3) / sigma_3)
        p_o4 = 1.0 - normal_cdf((line - mu_4) / sigma_4)
        p_o5 = 1.0 - normal_cdf((line - mu_5) / sigma_5)
        p_over = (p_sets_3 * p_o3) + (p_sets_4 * p_o4) + (p_sets_5 * p_o5)
        p_under = 1.0 - p_over
        k_over = f"over_{str(line).replace('.', '_')}"
        k_under = f"under_{str(line).replace('.', '_')}"
        ou_result[k_over] = {"prob": round(p_over, 4), "pct": f"{p_over * 100:.1f}%", "fair_odds": fair_odds(p_over)}
        ou_result[k_under] = {"prob": round(p_under, 4), "pct": f"{p_under * 100:.1f}%", "fair_odds": fair_odds(p_under)}

    spread_result = {
        "home_-2.5": {"prob": round(p_home_m25, 4), "pct": f"{p_home_m25 * 100:.1f}%", "fair_odds": fair_odds(p_home_m25)},
        "home_-1.5": {"prob": round(p_home_m15, 4), "pct": f"{p_home_m15 * 100:.1f}%", "fair_odds": fair_odds(p_home_m15)},
        "home_+1.5": {"prob": round(p_home_p15, 4), "pct": f"{p_home_p15 * 100:.1f}%", "fair_odds": fair_odds(p_home_p15)},
        "home_+2.5": {"prob": round(p_home_p25, 4), "pct": f"{p_home_p25 * 100:.1f}%", "fair_odds": fair_odds(p_home_p25)},
    }

    score_ranking = [
        ("3-0", p_30),
        ("3-1", p_31),
        ("3-2", p_32),
        ("2-3", p_23),
        ("1-3", p_13),
        ("0-3", p_03),
    ]
    score_ranking.sort(key=lambda x: x[1], reverse=True)

    result = {
        "sport_model": "table_tennis",
        "expected_scoring": {
            "home": round(home_exp, 2),
            "away": round(away_exp, 2),
            "total": round(tot_exp, 2),
            "point_win_prob_home": round(r, 4),
            "set_win_prob_home": round(p_set, 4),
            "unit": scoring_unit,
        },
        "match_result": {
            "home_win": {"prob": round(p_home_win, 4), "pct": f"{p_home_win * 100:.1f}%", "fair_odds": fair_odds(p_home_win)},
            "away_win": {"prob": round(p_away_win, 4), "pct": f"{p_away_win * 100:.1f}%", "fair_odds": fair_odds(p_away_win)},
        },
        "set_betting": {
            "3-0": {"prob": round(p_30, 4), "pct": f"{p_30 * 100:.1f}%", "fair_odds": fair_odds(p_30)},
            "3-1": {"prob": round(p_31, 4), "pct": f"{p_31 * 100:.1f}%", "fair_odds": fair_odds(p_31)},
            "3-2": {"prob": round(p_32, 4), "pct": f"{p_32 * 100:.1f}%", "fair_odds": fair_odds(p_32)},
            "0-3": {"prob": round(p_03, 4), "pct": f"{p_03 * 100:.1f}%", "fair_odds": fair_odds(p_03)},
            "1-3": {"prob": round(p_13, 4), "pct": f"{p_13 * 100:.1f}%", "fair_odds": fair_odds(p_13)},
            "2-3": {"prob": round(p_23, 4), "pct": f"{p_23 * 100:.1f}%", "fair_odds": fair_odds(p_23)},
        },
        "set_handicap": {
            "home -1.5 sets": {"prob": round(p_home_m15, 4), "pct": f"{p_home_m15 * 100:.1f}%", "fair_odds": fair_odds(p_home_m15)},
            "home -2.5 sets": {"prob": round(p_home_m25, 4), "pct": f"{p_home_m25 * 100:.1f}%", "fair_odds": fair_odds(p_home_m25)},
            "home +1.5 sets": {"prob": round(p_home_p15, 4), "pct": f"{p_home_p15 * 100:.1f}%", "fair_odds": fair_odds(p_home_p15)},
            "home +2.5 sets": {"prob": round(p_home_p25, 4), "pct": f"{p_home_p25 * 100:.1f}%", "fair_odds": fair_odds(p_home_p25)},
            "away -1.5 sets": {"prob": round(p_away_m15, 4), "pct": f"{p_away_m15 * 100:.1f}%", "fair_odds": fair_odds(p_away_m15)},
            "away -2.5 sets": {"prob": round(p_away_m25, 4), "pct": f"{p_away_m25 * 100:.1f}%", "fair_odds": fair_odds(p_away_m25)},
            "away +1.5 sets": {"prob": round(p_away_p15, 4), "pct": f"{p_away_p15 * 100:.1f}%", "fair_odds": fair_odds(p_away_p15)},
            "away +2.5 sets": {"prob": round(p_away_p25, 4), "pct": f"{p_away_p25 * 100:.1f}%", "fair_odds": fair_odds(p_away_p25)},
        },
        "total_sets": {
            "over_3_5": {"prob": round(p_over_35, 4), "pct": f"{p_over_35 * 100:.1f}%", "fair_odds": fair_odds(p_over_35)},
            "under_3_5": {"prob": round(p_under_35, 4), "pct": f"{p_under_35 * 100:.1f}%", "fair_odds": fair_odds(p_under_35)},
            "over_4_5": {"prob": round(p_over_45, 4), "pct": f"{p_over_45 * 100:.1f}%", "fair_odds": fair_odds(p_over_45)},
            "under_4_5": {"prob": round(p_under_45, 4), "pct": f"{p_under_45 * 100:.1f}%", "fair_odds": fair_odds(p_under_45)},
            "exact_3": {"prob": round(p_sets_3, 4), "pct": f"{p_sets_3 * 100:.1f}%", "fair_odds": fair_odds(p_sets_3)},
            "exact_4": {"prob": round(p_sets_4, 4), "pct": f"{p_sets_4 * 100:.1f}%", "fair_odds": fair_odds(p_sets_4)},
            "exact_5": {"prob": round(p_sets_5, 4), "pct": f"{p_sets_5 * 100:.1f}%", "fair_odds": fair_odds(p_sets_5)},
        },
        "first_set_winner": {
            "home": {"prob": round(p_set, 4), "pct": f"{p_set * 100:.1f}%", "fair_odds": fair_odds(p_set)},
            "away": {"prob": round(q_set, 4), "pct": f"{q_set * 100:.1f}%", "fair_odds": fair_odds(q_set)},
        },
        "over_under": ou_result,
        "spread": spread_result,
        "top_scorelines": [
            {"score": s[0], "prob": round(s[1], 4), "pct": f"{s[1] * 100:.1f}%", "fair_odds": fair_odds(s[1])}
            for s in score_ranking
        ]
    }
    return result


# ============================================================================
# Universal Market Matcher & Option Resolver
# ============================================================================

def match_arbitrary_market(
    query_label: str,
    results: Dict[str, Any]
) -> Tuple[Optional[float], str, str]:
    """
    Universal Market Matcher & Option Resolver.
    Normalizes arbitrary query strings from bookmaker / SportyBet screenshots
    and resolves the exact mathematical probability from underlying models.
    Returns: (probability, canonical_key, description) or (None, "", "")
    """
    raw = query_label.strip()
    q = raw.lower().replace("_", " ")
    q = re.sub(r"\s+", " ", q)
    sport_model = results.get("sport_model", "poisson")

    # 1. Double Chance + Over/Under: e.g. "1X & Under 3.5", "1X and U3.5", "X2 & Over 1.5"
    m_dc_ou = re.match(r"^(1x|x2|12)\s*(?:&|and|\+)\s*(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_dc_ou and sport_model == "poisson" and "_scoreline_matrix" in results:
        dc = m_dc_ou.group(1)
        ou_dir = "over" if m_dc_ou.group(2) in ("over", "o") else "under"
        line = float(m_dc_ou.group(3))
        M = results["_scoreline_matrix"]
        prob = 0.0
        for h in range(len(M)):
            for a in range(len(M[h])):
                if dc == "1x" and h < a: continue
                if dc == "x2" and h > a: continue
                if dc == "12" and h == a: continue
                if ou_dir == "over" and (h + a) <= line: continue
                if ou_dir == "under" and (h + a) >= line: continue
                prob += M[h][a]
        key = f"{dc.upper()} & {ou_dir.title()} {line}"
        return prob, key, f"Double Chance {dc.upper()} & {ou_dir.title()} {line} Goals"

    # 2. 1X2 + Over/Under: e.g. "1 & Over 1.5", "Home & Under 3.5", "2 & Under 3.5"
    m_1x2_ou = re.match(r"^(1|2|x|home|away|draw|w1|w2)\s*(?:&|and|\+)\s*(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_1x2_ou and sport_model == "poisson" and "_scoreline_matrix" in results:
        outc = m_1x2_ou.group(1)
        ou_dir = "over" if m_1x2_ou.group(2) in ("over", "o") else "under"
        line = float(m_1x2_ou.group(3))
        M = results["_scoreline_matrix"]
        prob = 0.0
        for h in range(len(M)):
            for a in range(len(M[h])):
                if outc in ('1', 'home', 'w1') and h <= a: continue
                if outc in ('2', 'away', 'w2') and a <= h: continue
                if outc in ('x', 'draw') and h != a: continue
                if ou_dir == "over" and (h + a) <= line: continue
                if ou_dir == "under" and (h + a) >= line: continue
                prob += M[h][a]
        label_outc = "1" if outc in ('1', 'home', 'w1') else ("2" if outc in ('2', 'away', 'w2') else "X")
        key = f"{label_outc} & {ou_dir.title()} {line}"
        return prob, key, f"Match Outcome {label_outc} & {ou_dir.title()} {line} Goals"

    # 3. 1X2 + BTTS: e.g. "1 & BTTS Yes", "Home & BTTS No", "1 & GG", "2 & NG"
    m_1x2_btts = re.match(r"^(1|2|x|home|away|draw|w1|w2)\s*(?:&|and|\+)\s*(?:btts\s*)?(yes|no|y|n|gg|ng)$", q)
    if m_1x2_btts and sport_model == "poisson" and "_scoreline_matrix" in results:
        outc = m_1x2_btts.group(1)
        btts_yn = "yes" if m_1x2_btts.group(2) in ("yes", "y", "gg") else "no"
        M = results["_scoreline_matrix"]
        prob = 0.0
        for h in range(len(M)):
            for a in range(len(M[h])):
                if outc in ('1', 'home', 'w1') and h <= a: continue
                if outc in ('2', 'away', 'w2') and a <= h: continue
                if outc in ('x', 'draw') and h != a: continue
                is_btts = (h > 0 and a > 0)
                if btts_yn == "yes" and not is_btts: continue
                if btts_yn == "no" and is_btts: continue
                prob += M[h][a]
        label_outc = "1" if outc in ('1', 'home', 'w1') else ("2" if outc in ('2', 'away', 'w2') else "X")
        key = f"{label_outc} & BTTS {btts_yn.title()}"
        return prob, key, f"Outcome {label_outc} & Both Teams To Score ({btts_yn.title()})"

    # 4. BTTS + Over/Under: e.g. "BTTS & Over 2.5", "GG & Over 2.5", "BTTS & Under 3.5"
    m_btts_ou = re.match(r"^(?:btts|gg|ng)\s*(?:(yes|no)\s*)?(?:&|and|\+)\s*(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_btts_ou and sport_model == "poisson" and "_scoreline_matrix" in results:
        yn = "no" if (m_btts_ou.group(1) == "no" or q.startswith("ng")) else "yes"
        ou_dir = "over" if m_btts_ou.group(2) in ("over", "o") else "under"
        line = float(m_btts_ou.group(3))
        M = results["_scoreline_matrix"]
        prob = 0.0
        for h in range(len(M)):
            for a in range(len(M[h])):
                is_btts = (h > 0 and a > 0)
                if yn == "yes" and not is_btts: continue
                if yn == "no" and is_btts: continue
                if ou_dir == "over" and (h + a) <= line: continue
                if ou_dir == "under" and (h + a) >= line: continue
                prob += M[h][a]
        key = f"BTTS {yn.title()} & {ou_dir.title()} {line}"
        return prob, key, f"Both Teams To Score ({yn.title()}) & {ou_dir.title()} {line} Goals"

    # 5. Win to Nil: e.g. "Home Win to Nil", "1 to Nil", "Away Win to Nil"
    m_wtn = re.match(r"^(?:win\s+to\s+nil\s+)?(home|away|1|2|w1|w2)(?:\s*win)?\s*(?:to\s*nil|win\s+to\s+nil)$", q)
    if m_wtn and sport_model == "poisson" and "_scoreline_matrix" in results:
        tm = m_wtn.group(1)
        M = results["_scoreline_matrix"]
        if tm in ("home", "1", "w1"):
            prob = sum(M[h][0] for h in range(1, len(M)))
            return prob, "Home Win to Nil", "Home Win to Nil"
        else:
            prob = sum(M[0][a] for a in range(1, len(M[0])))
            return prob, "Away Win to Nil", "Away Win to Nil"

    # 6. Clean Sheet: e.g. "Home Clean Sheet", "Away Clean Sheet Yes"
    m_cs = re.match(r"^(home|away|1|2)\s*clean\s*sheet(?:\s*(yes|no))?$", q)
    if m_cs and sport_model == "poisson" and "_scoreline_matrix" in results:
        tm = m_cs.group(1)
        yn = m_cs.group(2) or "yes"
        M = results["_scoreline_matrix"]
        if tm in ("home", "1"):
            p_yes = sum(M[h][0] for h in range(len(M)))
            prob = p_yes if yn == "yes" else 1.0 - p_yes
            return prob, f"Home Clean Sheet {yn.title()}", f"Home Clean Sheet ({yn.title()})"
        else:
            p_yes = sum(M[0][a] for a in range(len(M[0])))
            prob = p_yes if yn == "yes" else 1.0 - p_yes
            return prob, f"Away Clean Sheet {yn.title()}", f"Away Clean Sheet ({yn.title()})"

    # 7. Goal Bands / Multi-Goals: e.g. "1-2 Goals", "1-3 Goals", "2-4", "7+ Goals"
    m_gb = re.match(r"^([0-9]+)\s*(?:-|to)\s*([0-9]+)(?:\s*goals?|\s*pts?|\s*points?)?$", q)
    if m_gb and sport_model == "poisson" and "_scoreline_matrix" in results:
        g_min = int(m_gb.group(1))
        g_max = int(m_gb.group(2))
        M = results["_scoreline_matrix"]
        prob = 0.0
        for h in range(len(M)):
            for a in range(len(M[h])):
                if g_min <= (h + a) <= g_max:
                    prob += M[h][a]
        key = f"{g_min}-{g_max} Goals"
        return prob, key, f"Goal Band {g_min} to {g_max} Goals"

    m_gb_plus = re.match(r"^([0-9]+)\+(?:\s*goals?|\s*pts?|\s*points?)?$", q)
    if m_gb_plus and sport_model == "poisson" and "_scoreline_matrix" in results:
        g_min = int(m_gb_plus.group(1))
        M = results["_scoreline_matrix"]
        prob = sum(M[h][a] for h in range(len(M)) for a in range(len(M[h])) if (h + a) >= g_min)
        key = f"{g_min}+ Goals"
        return prob, key, f"Goal Band {g_min}+ Goals"

    # 8. Team Totals: e.g. "Home Over 1.5", "Away Under 1.5", "Home Total Over 82.5"
    m_tt = re.match(r"^(home|away|1|2|team\s*1|team\s*2)\s*(?:total\s*)?(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_tt:
        tm = m_tt.group(1)
        ou_dir = "over" if m_tt.group(2) in ("over", "o") else "under"
        line = float(m_tt.group(3))
        is_home = tm in ("home", "1", "team 1", "team1")
        if sport_model == "poisson" and "_scoreline_matrix" in results:
            M = results["_scoreline_matrix"]
            if is_home:
                prob = sum(M[h][a] for h in range(len(M)) for a in range(len(M[h])) if (h > line if ou_dir == "over" else h < line))
                key = f"Home {ou_dir.title()} {line}"
                return prob, key, f"Home Team Total {ou_dir.title()} {line} Goals"
            else:
                prob = sum(M[h][a] for h in range(len(M)) for a in range(len(M[h])) if (a > line if ou_dir == "over" else a < line))
                key = f"Away {ou_dir.title()} {line}"
                return prob, key, f"Away Team Total {ou_dir.title()} {line} Goals"
        elif sport_model == "normal":
            exp_info = results.get("expected_scoring", {})
            mu = exp_info.get("home" if is_home else "away", 80.0)
            sigma = exp_info.get("home_std" if is_home else "away_std", mu * 0.12)
            p_over = 1.0 - normal_cdf((line - mu) / sigma) if sigma > 0 else 0.5
            prob = p_over if ou_dir == "over" else (1.0 - p_over)
            lbl = "Home" if is_home else "Away"
            key = f"{lbl} {ou_dir.title()} {line}"
            return prob, key, f"{lbl} Team Total {ou_dir.title()} {line} Points"

    # 9. Odd / Even
    if q in ("odd", "odd goals", "odd points") and sport_model == "poisson" and "_scoreline_matrix" in results:
        M = results["_scoreline_matrix"]
        prob = sum(M[h][a] for h in range(len(M)) for a in range(len(M[h])) if (h + a) % 2 == 1)
        return prob, "Odd Goals", "Total Score Odd"
    if q in ("even", "even goals", "even points") and sport_model == "poisson" and "_scoreline_matrix" in results:
        M = results["_scoreline_matrix"]
        prob = sum(M[h][a] for h in range(len(M)) for a in range(len(M[h])) if (h + a) % 2 == 0)
        return prob, "Even Goals", "Total Score Even"

    # 10. Half-Time / Full-Time: e.g. "1/1", "HT/FT 1/1", "2/2", "X/1"
    m_htft = re.match(r"^(?:ht[\/_ ]ft\s*)?([1x2])\s*[\/_ ]\s*([1x2])$", q)
    if m_htft and "half_time_full_time" in results:
        htft_key = f"{m_htft.group(1).upper()}/{m_htft.group(2).upper()}"
        if htft_key in results["half_time_full_time"]:
            prob = results["half_time_full_time"][htft_key]["prob"]
            return prob, f"HT/FT {htft_key}", f"Half-Time / Full-Time {htft_key}"

    # 11. Tennis / Table Tennis: Set Betting: e.g. "2-0", "2:0", "3-1", "0-3"
    m_sb = re.match(r"^(?:set\s*betting\s*)?([0-3])\s*[-: ]\s*([0-3])$", q)
    if m_sb and "set_betting" in results:
        sb_key = f"{m_sb.group(1)}-{m_sb.group(2)}"
        if sb_key in results["set_betting"]:
            prob = results["set_betting"][sb_key]["prob"]
            return prob, f"Set Betting {sb_key}", f"Exact Set Score {sb_key}"

    # 12. Tennis / Table Tennis: Set Handicap & To Win a Set: e.g. "P1 to win a set", "P1 +1.5 sets", "P1 -1.5 Sets"
    m_sh = re.match(r"^(?:player\s*|p)?([12]|home|away)\s*(?:to\s*win\s*a\s*set|\+\s*([12]\.5)(?:\s*sets?)?|-\s*([12]\.5)(?:\s*sets?)?)$", q)
    if m_sh and "set_handicap" in results:
        p_tok = m_sh.group(1)
        tm_name = "home" if p_tok in ("1", "home") else "away"
        p_num = "1" if tm_name == "home" else "2"
        if "to win a set" in q:
            k = f"{tm_name} +1.5 sets" if sport_model == "tennis" else f"{tm_name} +2.5 sets"
            if k in results["set_handicap"]:
                prob = results["set_handicap"][k]["prob"]
                return prob, f"Player {p_num} To Win a Set", f"Player {p_num} To Win At Least One Set"
        elif m_sh.group(2):
            val = m_sh.group(2)
            k = f"{tm_name} +{val} sets"
            if k in results["set_handicap"]:
                prob = results["set_handicap"][k]["prob"]
                return prob, f"Player {p_num} +{val} Sets", f"Player {p_num} +{val} Sets Handicap"
        elif m_sh.group(3):
            val = m_sh.group(3)
            k = f"{tm_name} -{val} sets"
            if k in results["set_handicap"]:
                prob = results["set_handicap"][k]["prob"]
                return prob, f"Player {p_num} -{val} Sets", f"Player {p_num} -{val} Sets Handicap"

    # 13. Tennis / Table Tennis: Total Sets: e.g. "Over 2.5 Sets", "Under 3.5 Sets"
    m_ts = re.match(r"^(?:total\s*sets?\s*)?(over|under|o|u)\s*([2-4]\.5)(?:\s*sets?)?$", q)
    if m_ts and "total_sets" in results:
        ou_dir = "over" if m_ts.group(1) in ("over", "o") else "under"
        line_s = m_ts.group(2).replace(".", "_")
        k = f"{ou_dir}_{line_s}"
        if k in results["total_sets"]:
            prob = results["total_sets"][k]["prob"]
            return prob, f"Total Sets {ou_dir.title()} {m_ts.group(2)}", f"Total Sets {ou_dir.title()} {m_ts.group(2)}"

    # 14. 1st Half / Period OU: e.g. "1H Under 82.5", "1H Under 1.5"
    m_1h = re.match(r"^(?:1h|first\s*half|ht)\s*(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_1h:
        ou_dir = "over" if m_1h.group(1) in ("over", "o") else "under"
        line = float(m_1h.group(2))
        ps = results.get("period_splits", {}).get("1st_half", {})
        if ps:
            mu_1h = ps.get("total_exp", 0.0)
            if sport_model == "normal":
                sig_1h = ps.get("sigma_total", 8.0)
                p_o = 1.0 - normal_cdf((line - mu_1h) / sig_1h) if sig_1h > 0 else 0.5
                prob = p_o if ou_dir == "over" else 1.0 - p_o
                return prob, f"1H {ou_dir.title()} {line}", f"1st Half Total {ou_dir.title()} {line} Points"
            else:
                p_le = sum(poisson_pmf(k, mu_1h) for k in range(int(line) + 1))
                prob = 1.0 - p_le if ou_dir == "over" else p_le
                return prob, f"1H {ou_dir.title()} {line}", f"1st Half Total {ou_dir.title()} {line} Goals"

    # 15. Match Result / 1X2 / Moneyline
    if q in ("home", "home win", "1", "w1", "win 1", "p1", "player 1"):
        p = results["match_result"]["home_win"]["prob"]
        return p, "Home Win", "Match Winner (Home / Player 1)"
    if q in ("away", "away win", "2", "w2", "win 2", "p2", "player 2"):
        p = results["match_result"]["away_win"]["prob"]
        return p, "Away Win", "Match Winner (Away / Player 2)"
    if q in ("draw", "x", "tie") and "draw" in results.get("match_result", {}):
        p = results["match_result"]["draw"]["prob"]
        return p, "Draw", "Regulation Draw (X)"

    # 16. Double Chance & DNB
    if q in ("1x", "home or draw", "double chance 1x", "dc 1x") and "double_chance" in results:
        p = results["double_chance"]["1X"]["prob"]
        return p, "Double Chance 1X", "Double Chance 1X (Home or Draw)"
    if q in ("x2", "draw or away", "double chance x2", "dc x2") and "double_chance" in results:
        p = results["double_chance"]["X2"]["prob"]
        return p, "Double Chance X2", "Double Chance X2 (Draw or Away)"
    if q in ("12", "home or away", "double chance 12", "dc 12") and "double_chance" in results:
        p = results["double_chance"]["12"]["prob"]
        return p, "Double Chance 12", "Double Chance 12 (Home or Away)"
    if q in ("dnb home", "home dnb", "1 dnb", "dnb 1") and "draw_no_bet" in results:
        p = results["draw_no_bet"]["home"]["prob"]
        return p, "Home DNB", "Draw No Bet (Home)"
    if q in ("dnb away", "away dnb", "2 dnb", "dnb 2") and "draw_no_bet" in results:
        p = results["draw_no_bet"]["away"]["prob"]
        return p, "Away DNB", "Draw No Bet (Away)"

    # 17. BTTS
    if q in ("btts yes", "btts", "gg", "both teams to score yes") and "btts" in results:
        p = results["btts"]["yes"]["prob"]
        return p, "BTTS Yes", "Both Teams To Score (Yes)"
    if q in ("btts no", "ng", "both teams to score no") and "btts" in results:
        p = results["btts"]["no"]["prob"]
        return p, "BTTS No", "Both Teams To Score (No)"

    # 18. Over / Under (Total)
    m_ou_std = re.match(r"^(?:total\s*)?(over|under|o|u)\s*([0-9]+(?:\.[0-9]+)?)$", q)
    if m_ou_std and "over_under" in results:
        ou_dir = "over" if m_ou_std.group(1) in ("over", "o") else "under"
        line_val = float(m_ou_std.group(2))
        k = f"{ou_dir}_{str(line_val).replace('.', '_')}"
        if k in results["over_under"]:
            p = results["over_under"][k]["prob"]
            unit = results.get("expected_scoring", {}).get("unit", "units")
            return p, f"{ou_dir.title()} {line_val}", f"Total {ou_dir.title()} {line_val} {unit.title()}"

    return None, "", ""


# ============================================================================
# Expected Value, De-vigging & Accumulator Anchor Engine
# ============================================================================

def calculate_devigged_probabilities(odds_dict: Dict[str, float]) -> Dict[str, Any]:
    """
    Calculate vig-free (fair) probabilities using standard proportional devigging.
    odds_dict: {'Home': 3.80, 'Away': 1.23} or {'Over': 1.80, 'Under': 1.91}
    """
    valid_odds = {k: v for k, v in odds_dict.items() if v is not None and v > 1.0}
    if len(valid_odds) < 2:
        return {}

    inv_sum = sum(1.0 / o for o in valid_odds.values())
    margin_pct = (inv_sum - 1.0) * 100.0

    devigged = {}
    for k, o in valid_odds.items():
        raw_implied = (1.0 / o)
        fair_prob = raw_implied / inv_sum
        devigged[k] = {
            "market_odds": o,
            "raw_implied_prob": round(raw_implied, 4),
            "raw_implied_pct": f"{raw_implied * 100:.1f}%",
            "devigged_prob": round(fair_prob, 4),
            "devigged_pct": f"{fair_prob * 100:.1f}%",
            "fair_market_odds": round(1.0 / fair_prob, 2) if fair_prob > 0 else 999.0,
        }

    return {
        "outcomes": devigged,
        "bookmaker_margin_pct": round(margin_pct, 2)
    }


def compute_accumulator_anchor_index(model_prob: float, bookmaker_odds: float, z_buffer: float = 0.0) -> Dict[str, Any]:
    """
    Calculate Accumulator Anchor Index (AAI: 0-100) for evaluating high-stake parlay suitability.
    Filters to ultra-high probability floor outcomes (>75-80%) with wide margin buffers.
    """
    if model_prob < 0.65 or bookmaker_odds <= 1.0:
        return {
            "score": 0.0,
            "tier": "UNSUITABLE",
            "is_anchor": False,
            "badge": "🔴 REJECT (Below 65% threshold for parlay anchor)"
        }

    # Calibrated probability scaling:
    # 0.65 -> 40.0, 0.75 -> 65.0, 0.80 -> 76.5, 0.85 -> 88.0, 0.95+ -> 100.0
    if model_prob < 0.75:
        base = 40.0 + (model_prob - 0.65) / 0.10 * 25.0
    elif model_prob < 0.85:
        base = 65.0 + (model_prob - 0.75) / 0.10 * 23.0
    else:
        base = 88.0 + min((model_prob - 0.85) / 0.10 * 12.0, 12.0)

    # Margin cushion bonus (up to +8 pts for line deep in the distribution tails)
    buf_bonus = min(abs(z_buffer) / 1.5, 1.0) * 8.0 if z_buffer != 0.0 else 0.0

    # EV adjustment (bonus for positive EV, penalty for heavy bookmaker vig tax)
    ev_pct = (model_prob * bookmaker_odds - 1.0) * 100.0
    if ev_pct > 0:
        ev_adj = min(ev_pct * 0.4, 8.0)
    elif ev_pct < -5.0:
        ev_adj = max(-10.0, (ev_pct + 5.0) * 0.5)
    else:
        ev_adj = 0.0

    final_score = round(max(0.0, min(100.0, base + buf_bonus + ev_adj)), 1)
    is_anchor = final_score >= 70.0 and model_prob >= 0.75

    if final_score >= 85.0 and model_prob >= 0.80:
        tier = "ELITE"
        badge = "🟢 ELITE ANCHOR (High-Stake Safe)"
    elif final_score >= 72.0 and model_prob >= 0.75:
        tier = "STRONG"
        badge = "🟢 STRONG ANCHOR (Reliable Floor)"
    elif final_score >= 60.0:
        tier = "VIABLE"
        badge = "🟡 VIABLE PARLAY LEG (Moderate Risk)"
    else:
        tier = "SPECULATIVE"
        badge = "🔴 SPECULATIVE (Not Recommended as Anchor)"

    return {
        "score": final_score,
        "tier": tier,
        "is_anchor": is_anchor,
        "badge": badge
    }


def evaluate_value(model_prob: float, bookmaker_odds: float, devigged_prob: Optional[float] = None, z_buffer: float = 0.0) -> Dict[str, Any]:
    """Calculate Expected Value (+EV), bookmaker implied probability, and Accumulator Anchor Index."""
    if bookmaker_odds <= 1.0:
        return {"ev_pct": 0.0, "is_value": False, "implied_pct": "N/A", "aai": {"score": 0.0, "badge": "N/A"}}
    implied_prob = 1.0 / bookmaker_odds
    edge = (model_prob * bookmaker_odds) - 1.0
    ev_pct = edge * 100.0
    aai = compute_accumulator_anchor_index(model_prob, bookmaker_odds, z_buffer=z_buffer)

    res: Dict[str, Any] = {
        "market_odds": bookmaker_odds,
        "implied_prob": round(implied_prob, 4),
        "implied_pct": f"{implied_prob * 100:.1f}%",
        "ev_pct": round(ev_pct, 2),
        "is_value": ev_pct > 3.0,
        "aai": aai
    }
    if devigged_prob is not None:
        res["devigged_prob"] = round(devigged_prob, 4)
        res["devigged_pct"] = f"{devigged_prob * 100:.1f}%"
        res["edge_vs_market_pct"] = round((model_prob - devigged_prob) * 100.0, 2)
    return res


def parse_ou_odds_string(ou_odds_str: str) -> Dict[float, Dict[str, float]]:
    """
    Parse flexible comma-separated multi-line over/under odds strings.
    Supported formats:
      "154.5:1.43:2.65,160.5:1.80:1.91,168.5:2.70:1.41" -> {154.5: {'over': 1.43, 'under': 2.65}, ...}
      "168.5:U:1.41" or "168.5:under:1.41" -> {168.5: {'under': 1.41}}
      "154.5:O:1.43" or "154.5:over:1.43" -> {154.5: {'over': 1.43}}
    """
    parsed: Dict[float, Dict[str, float]] = {}
    if not ou_odds_str:
        return parsed

    tokens = [t.strip() for t in ou_odds_str.split(",") if t.strip()]
    for token in tokens:
        parts = token.split(":")
        if len(parts) == 3:
            try:
                line = float(parts[0].strip())
                parsed.setdefault(line, {})
                if parts[1].strip():
                    p1_lower = parts[1].strip().lower()
                    if p1_lower in ('o', 'over'):
                        parsed[line]["over"] = float(parts[2].strip())
                    elif p1_lower in ('u', 'under'):
                        parsed[line]["under"] = float(parts[2].strip())
                    else:
                        parsed[line]["over"] = float(parts[1].strip())
                        if parts[2].strip():
                            parsed[line]["under"] = float(parts[2].strip())
            except ValueError:
                continue
        elif len(parts) == 2:
            try:
                line = float(parts[0].strip())
                val = float(parts[1].strip())
                parsed.setdefault(line, {})["over"] = val
            except ValueError:
                continue
    return parsed


def compute_period_splits(
    home_exp: float,
    away_exp: float,
    sport_key: str,
    scoring_unit: str = "points"
) -> Dict[str, Any]:
    """
    Derive 1st Half projections based on empirical period distributions.
    Football: 1H ~ 45% of total scoring.
    Basketball: 1H ~ 48.5% of total scoring.
    """
    splits: Dict[str, Any] = {}
    if sport_key in ("football", "soccer", "ice_hockey", "hockey", "handball"):
        h1_ratio = 0.45
        home_1h = home_exp * h1_ratio
        away_1h = away_exp * h1_ratio
        splits["1st_half"] = {
            "home_exp": round(home_1h, 2),
            "away_exp": round(away_1h, 2),
            "total_exp": round(home_1h + away_1h, 2),
            "unit": scoring_unit
        }
    elif "basketball" in sport_key or sport_key in ("fiba", "nba", "ncaa", "vtb", "euroleague"):
        h1_ratio = 0.485
        home_1h = home_exp * h1_ratio
        away_1h = away_exp * h1_ratio
        tot_1h = home_1h + away_1h
        sigma_1h = max(tot_1h * 0.12 * math.sqrt(h1_ratio), 4.0)
        splits["1st_half"] = {
            "home_exp": round(home_1h, 1),
            "away_exp": round(away_1h, 1),
            "total_exp": round(tot_1h, 1),
            "sigma_total": round(sigma_1h, 2),
            "unit": scoring_unit
        }
    return splits


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
    value_analysis: Dict[str, Any],
    ou_analysis_table: Optional[List[Dict[str, Any]]] = None,
    devigged_market: Optional[Dict[str, Any]] = None,
    period_splits: Optional[Dict[str, Any]] = None,
) -> None:
    """Print formatted human-readable report."""
    model_label = results.get("sport_model", "unknown").upper()

    print("=" * 72)
    print(f" MATCH PREDICTION ENGINE ({model_label} MODEL)")
    print(f" {home_name.upper()} vs {away_name.upper()}")
    print(f" Sport: {sport_name} | Competition: {competition}")
    print(f" Expected {scoring_unit.title()}: {home_name} ({home_exp:.2f}) - ({away_exp:.2f}) {away_name}")
    if "expected_scoring" in results and "margin_mean" in results["expected_scoring"]:
        mm = results["expected_scoring"]["margin_mean"]
        ms = results["expected_scoring"]["margin_std"]
        print(f" Projected Margin: {home_name} {mm:+.1f} points (StdDev: {ms:.1f})")
    print("=" * 72)

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

    # Devigged Market Context
    if devigged_market and "bookmaker_margin_pct" in devigged_market:
        margin = devigged_market["bookmaker_margin_pct"]
        print(f"  * Bookmaker Overround / Vig: {margin:.1f}%")

    # Double Chance & DNB (draw sports only)
    if has_draw and "double_chance" in results:
        dc = results["double_chance"]
        dnb = results["draw_no_bet"]
        print(f"\n[ DOUBLE CHANCE & DRAW NO BET ]")
        print(f"  1X ({home_name} or Draw): {dc['1X']['pct']} (Fair: {dc['1X']['fair_odds']})")
        print(f"  X2 (Draw or {away_name}): {dc['X2']['pct']} (Fair: {dc['X2']['fair_odds']})")
        print(f"  DNB {home_name}:          {dnb['home']['pct']} (Fair: {dnb['home']['fair_odds']})")
        print(f"  DNB {away_name}:          {dnb['away']['pct']} (Fair: {dnb['away']['fair_odds']})")

    # Multi-Line O/U Audit Table
    if ou_analysis_table:
        print(f"\n[ AUDITED OVER/UNDER LINES & EV TABLE ]")
        print(f"  {'Line':<7} | {'Over %':<7} {'Odds':<6} {'EV%':<7} | {'Under %':<7} {'Odds':<6} {'EV%':<7} | {'AAI Anchor Rating':<24}")
        print("  " + "-" * 78)
        for row in ou_analysis_table:
            o_pct = row["over_pct"]
            o_odds = f"{row['over_odds']:.2f}" if row.get("over_odds") else "-"
            o_ev = f"{row['over_ev']:+.1f}%" if row.get("over_ev") is not None else "-"
            u_pct = row["under_pct"]
            u_odds = f"{row['under_odds']:.2f}" if row.get("under_odds") else "-"
            u_ev = f"{row['under_ev']:+.1f}%" if row.get("under_ev") is not None else "-"
            aai_text = row.get("aai_summary", "-")
            print(f"  {row['line']:<7.1f} | {o_pct:<7} {o_odds:<6} {o_ev:<7} | {u_pct:<7} {u_odds:<6} {u_ev:<7} | {aai_text:<24}")
    else:
        # Standard O/U display
        ou = results.get("over_under", {})
        if ou:
            print(f"\n[ OVER/UNDER {scoring_unit.upper()} ]")
            over_keys = sorted([k for k in ou if k.startswith("over_")])
            for ok in over_keys:
                uk = ok.replace("over_", "under_")
                line = ok.replace("over_", "").replace("_", ".")
                if uk in ou:
                    print(f"  Over {line}:  {ou[ok]['pct']:<7} | Under {line}: {ou[uk]['pct']}")

    # Period Splits (1st Half)
    if period_splits and "1st_half" in period_splits:
        p1 = period_splits["1st_half"]
        print(f"\n[ 1ST HALF DERIVATIVE PROJECTION ]")
        print(f"  Expected 1H Total: {p1['total_exp']} {p1['unit']} ({p1['home_exp']} - {p1['away_exp']})")

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

    # Tennis Set Betting & Handicaps
    if results.get("sport_model") == "tennis":
        if "set_betting" in results:
            print(f"\n[ SET BETTING (CORRECT SCORE) ]")
            for sc, data in results["set_betting"].items():
                print(f"  {sc:<6} -> Probability: {data['pct']:<6} (Fair: {data['fair_odds']})")
        if "set_handicap" in results:
            print(f"\n[ SET HANDICAP & TO WIN A SET ]")
            sh = results["set_handicap"]
            print(f"  {home_name} -1.5 Sets: {sh.get('home -1.5 sets', {}).get('pct', '-')} (Fair: {sh.get('home -1.5 sets', {}).get('fair_odds', '-')})")
            print(f"  {home_name} +1.5 Sets (Win Set): {sh.get('home +1.5 sets', {}).get('pct', '-')} (Fair: {sh.get('home +1.5 sets', {}).get('fair_odds', '-')})")
            print(f"  {away_name} -1.5 Sets: {sh.get('away -1.5 sets', {}).get('pct', '-')} (Fair: {sh.get('away -1.5 sets', {}).get('fair_odds', '-')})")
            print(f"  {away_name} +1.5 Sets (Win Set): {sh.get('away +1.5 sets', {}).get('pct', '-')} (Fair: {sh.get('away +1.5 sets', {}).get('fair_odds', '-')})")
        if "total_sets" in results:
            print(f"\n[ TOTAL SETS ]")
            ts = results["total_sets"]
            print(f"  Over 2.5 Sets (3 Sets):  {ts.get('over_2_5', {}).get('pct', '-')} (Fair: {ts.get('over_2_5', {}).get('fair_odds', '-')})")
            print(f"  Under 2.5 Sets (2 Sets): {ts.get('under_2_5', {}).get('pct', '-')} (Fair: {ts.get('under_2_5', {}).get('fair_odds', '-')})")

    # Table Tennis Set Betting & Handicaps
    if results.get("sport_model") == "table_tennis":
        if "set_betting" in results:
            print(f"\n[ SET BETTING (BEST OF 5) ]")
            for sc, data in results["set_betting"].items():
                print(f"  {sc:<6} -> Probability: {data['pct']:<6} (Fair: {data['fair_odds']})")
        if "set_handicap" in results:
            print(f"\n[ SET HANDICAP & TO WIN A SET ]")
            sh = results["set_handicap"]
            print(f"  {home_name} -1.5 Sets: {sh.get('home -1.5 sets', {}).get('pct', '-')} | {home_name} +1.5 Sets: {sh.get('home +1.5 sets', {}).get('pct', '-')}")
            print(f"  {home_name} -2.5 Sets: {sh.get('home -2.5 sets', {}).get('pct', '-')} | {home_name} +2.5 Sets (Win Set): {sh.get('home +2.5 sets', {}).get('pct', '-')}")
            print(f"  {away_name} -1.5 Sets: {sh.get('away -1.5 sets', {}).get('pct', '-')} | {away_name} +1.5 Sets: {sh.get('away +1.5 sets', {}).get('pct', '-')}")
            print(f"  {away_name} -2.5 Sets: {sh.get('away -2.5 sets', {}).get('pct', '-')} | {away_name} +2.5 Sets (Win Set): {sh.get('away +2.5 sets', {}).get('pct', '-')}")
        if "total_sets" in results:
            print(f"\n[ TOTAL SETS ]")
            ts = results["total_sets"]
            print(f"  Over 3.5 Sets (4+ Sets):  {ts.get('over_3_5', {}).get('pct', '-')} (Fair: {ts.get('over_3_5', {}).get('fair_odds', '-')})")
            print(f"  Under 3.5 Sets (3 Sets):  {ts.get('under_3_5', {}).get('pct', '-')} (Fair: {ts.get('under_3_5', {}).get('fair_odds', '-')})")
            print(f"  Over 4.5 Sets (5 Sets):   {ts.get('over_4_5', {}).get('pct', '-')} (Fair: {ts.get('over_4_5', {}).get('fair_odds', '-')})")
            print(f"  Under 4.5 Sets (<=4 Sets):{ts.get('under_4_5', {}).get('pct', '-')} (Fair: {ts.get('under_4_5', {}).get('fair_odds', '-')})")

    # Audited Arbitrary / SportyBet Options
    if results.get("audited_options"):
        print(f"\n[ AUDITED SPORTYBET SELECTIONS & PARLAY SUITABILITY ]")
        print(f"  {'Selection':<26} | {'Fair %':<7} {'Fair':<6} | {'Odds':<6} {'Implied':<7} {'EV%':<7} | {'AAI Verdict':<24}")
        print("  " + "-" * 88)
        for opt_key, opt_data in results["audited_options"].items():
            sel_lbl = opt_data.get("label", opt_key)
            fp_pct = opt_data.get("pct", f"{opt_data.get('model_prob', 0)*100:.1f}%")
            fo = f"{opt_data.get('fair_odds', 999.0):.2f}"
            mo = f"{opt_data.get('market_odds', 0.0):.2f}" if opt_data.get("market_odds") else "-"
            imp = opt_data.get("implied_pct", "-")
            ev_s = f"{opt_data.get('ev_pct', 0.0):+.1f}%" if opt_data.get("ev_pct") is not None else "-"
            aai_badge = opt_data.get("aai", {}).get("badge", "-") if opt_data.get("aai") else "-"
            print(f"  {sel_lbl:<26} | {fp_pct:<7} {fo:<6} | {mo:<6} {imp:<7} {ev_s:<7} | {aai_badge:<24}")

    # Top Scorelines (Poisson only)
    if "top_scorelines" in results and results.get("sport_model") == "poisson":
        print(f"\n[ TOP EXACT SCORELINES ]")
        for item in results["top_scorelines"][:5]:
            print(f"  {item['score']:<6} -> Probability: {item['pct']:<6} (Fair Odds: {item['fair_odds']})")

    # Value Analysis (+EV)
    if value_analysis:
        print(f"\n[ EXPECTED VALUE (+EV) & ANCHOR AUDIT ]")
        has_val = False
        for market, val in value_analysis.items():
            flag = "[+EV VALUE FOUND]" if val.get("is_value") else "[No Edge]"
            aai_tag = ""
            if "aai" in val and val["aai"]["is_anchor"]:
                aai_tag = f" -> {val['aai']['badge']} (AAI: {val['aai']['score']})"
            print(f"  {market:<22}: Bookmaker {val['market_odds']} (Implied: {val['implied_pct']}) -> Edge: {val['ev_pct']:+.1f}% {flag}{aai_tag}")
            if val.get("is_value"):
                has_val = True
        if not has_val:
            print("  No positive EV picks found at given odds threshold (>3%).")

    # Primary Recommendations
    if "recommendations" in results:
        rec = results["recommendations"]
        print(f"\n" + "=" * 72)
        print(f" PRIMARY RECOMMENDED SELECTIONS")
        print("=" * 72)
        if rec.get("accumulator_anchor"):
            anc = rec["accumulator_anchor"]
            print(f"  🟢 SAFEST ACCUMULATOR ANCHOR: {anc['selection']}")
            print(f"     Probability: {anc['prob_pct']} | Odds: {anc.get('odds', 'N/A')} | AAI Score: {anc['aai_score']}/100")
            print(f"     Rationale: {anc['rationale']}")
        if rec.get("value_bet"):
            vb = rec["value_bet"]
            print(f"\n  🟡 HIGHEST +EV VALUE BET:     {vb['selection']}")
            print(f"     Probability: {vb['prob_pct']} | Odds: {vb['odds']} | Edge: {vb['edge_pct']:+.1f}%")
        if rec.get("most_probable_outcome"):
            mp = rec["most_probable_outcome"]
            print(f"\n  🎯 MOST PROBABLE OUTCOME:     {mp['outcome']} ({mp['prob_pct']})")

    print("=" * 72)


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="match-prediction-engine: Multi-sport quantitative prediction, multi-line EV & accumulator anchor engine.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported sports: """ + ", ".join(list_sports()) + """

Examples:
  # Football (default)
  python3 poisson_model.py --home "Arsenal" --away "Chelsea" --home-xg 1.85 --away-xg 1.15

  # Basketball (FIBA / European / 40-Min)
  python3 poisson_model.py --sport basketball --league-format fiba --home "Avtodor" --away "Uralmash" --home-xg 73.5 --away-xg 83.5

  # Multi-Line O/U with live odds & Accumulator Anchor scoring
  python3 poisson_model.py --sport basketball --league-format fiba --home "Avtodor" --away "Uralmash" \\
    --home-xg 73.5 --away-xg 83.5 \\
    --ou-odds "154.5:1.43:2.65,160.5:1.80:1.91,166.5:2.40:1.50,168.5:2.70:1.41"
        """
    )

    # Sport selection
    parser.add_argument("--sport", type=str, default="football",
                        help=f"Sport type. Options: {', '.join(list_sports())}. Default: football")
    parser.add_argument("--league-format", type=str, default=None, choices=["nba", "fiba", "ncaa", "auto"],
                        help="Optional league format override for basketball (nba: 48min, fiba: 40min, ncaa: 40min)")

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
    parser.add_argument("--model", type=str, default=None, choices=["poisson", "normal", "tennis", "table_tennis"],
                        help="Force a specific model (overrides sport default)")

    # Custom over/under lines & multi-line odds
    parser.add_argument("--ou-lines", type=str, default=None,
                        help="Comma-separated over/under lines (e.g., '2.5,3.5,4.5' or '154.5,161.5,168.5')")
    parser.add_argument("--ou-odds", type=str, default=None,
                        help="Multi-line Over/Under odds. Format: 'line:over:under,...' e.g. '154.5:1.43:2.65,168.5:2.70:1.41'")

    # Arbitrary custom market odds line (repeatable)
    parser.add_argument("--odds-line", type=str, action="append", default=[],
                        help="Custom market line with odd. Format: 'label:odds' e.g. '1X & Under 3.5:1.52'")
    parser.add_argument("--market-query", type=str, action="append", default=[],
                        help="Evaluate fair probability of any custom market option (e.g. '1X & Under 3.5' or '1-3 Goals') without odds")

    # Standard Match Odds
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

    # Load sport profile with optional league format
    try:
        profile = get_profile(args.sport, league_format=args.league_format)
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

    # Parse custom OU lines and multi-line odds
    ou_lines = list(profile["ou_lines"])
    parsed_ou_odds = parse_ou_odds_string(args.ou_odds)
    if parsed_ou_odds:
        # Merge parsed lines into ou_lines
        for l in parsed_ou_odds.keys():
            if l not in ou_lines:
                ou_lines.append(l)

    if args.ou_lines:
        custom_lines = [float(x.strip()) for x in args.ou_lines.split(",") if x.strip()]
        for l in custom_lines:
            if l not in ou_lines:
                ou_lines.append(l)

    ou_lines = sorted(ou_lines)
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
    elif model_type == "tennis":
        results = compute_tennis_probabilities(
            home_exp, away_exp,
            ou_lines=ou_lines,
            spread_lines=spread_lines,
            scoring_unit=scoring_unit,
        )
    elif model_type == "table_tennis":
        results = compute_table_tennis_probabilities(
            home_exp, away_exp,
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
    if args.league_format:
        results["league_format"] = args.league_format

    # Compute period splits (1st Half)
    period_splits = compute_period_splits(home_exp, away_exp, args.sport, scoring_unit)
    if period_splits:
        results["period_splits"] = period_splits

    # Match Result Devigging & Value Analysis
    value_analysis = {}
    mr = results["match_result"]

    match_odds_dict = {}
    if args.odds_home: match_odds_dict["Home"] = args.odds_home
    if args.odds_draw and has_draw: match_odds_dict["Draw"] = args.odds_draw
    if args.odds_away: match_odds_dict["Away"] = args.odds_away

    devigged_match = calculate_devigged_probabilities(match_odds_dict) if len(match_odds_dict) >= 2 else None
    if devigged_match:
        results["devigged_market"] = devigged_match

    all_anchor_candidates = []
    all_value_candidates = []

    if args.odds_home:
        dev_p = devigged_match["outcomes"]["Home"]["devigged_prob"] if devigged_match and "Home" in devigged_match["outcomes"] else None
        h_val = evaluate_value(mr["home_win"]["prob"], args.odds_home, devigged_prob=dev_p)
        value_analysis["Home Win"] = h_val
        if h_val["aai"]["is_anchor"]:
            all_anchor_candidates.append({
                "selection": f"{args.home} Win",
                "prob": mr["home_win"]["prob"],
                "prob_pct": mr["home_win"]["pct"],
                "odds": args.odds_home,
                "aai_score": h_val["aai"]["score"],
                "rationale": f"High baseline win probability of {mr['home_win']['pct']}."
            })
        if h_val["is_value"]:
            all_value_candidates.append({
                "selection": f"{args.home} Win",
                "prob_pct": mr["home_win"]["pct"],
                "odds": args.odds_home,
                "edge_pct": h_val["ev_pct"]
            })
    if args.odds_draw and "draw" in mr:
        dev_p = devigged_match["outcomes"]["Draw"]["devigged_prob"] if devigged_match and "Draw" in devigged_match["outcomes"] else None
        value_analysis["Draw"] = evaluate_value(mr["draw"]["prob"], args.odds_draw, devigged_prob=dev_p)
    if args.odds_away:
        dev_p = devigged_match["outcomes"]["Away"]["devigged_prob"] if devigged_match and "Away" in devigged_match["outcomes"] else None
        a_val = evaluate_value(mr["away_win"]["prob"], args.odds_away, devigged_prob=dev_p)
        value_analysis["Away Win"] = a_val
        if a_val["aai"]["is_anchor"]:
            all_anchor_candidates.append({
                "selection": f"{args.away} Win",
                "prob": mr["away_win"]["prob"],
                "prob_pct": mr["away_win"]["pct"],
                "odds": args.odds_away,
                "aai_score": a_val["aai"]["score"],
                "rationale": f"High baseline win probability of {mr['away_win']['pct']}."
            })
        if a_val["is_value"]:
            all_value_candidates.append({
                "selection": f"{args.away} Win",
                "prob_pct": mr["away_win"]["pct"],
                "odds": args.odds_away,
                "edge_pct": a_val["ev_pct"]
            })

    # Multi-Line O/U Audited Table & EV Analysis
    ou_analysis_table = []
    ou_dict = results.get("over_under", {})
    tot_mean = home_exp + away_exp
    # Estimate total standard deviation for z-score buffer
    tot_sigma = results.get("expected_scoring", {}).get("margin_std", 12.0)
    if model_type != "normal":
        tot_sigma = math.sqrt(tot_mean) if tot_mean > 0 else 1.0

    for line in ou_lines:
        line_key_o = f"over_{str(line).replace('.', '_')}"
        line_key_u = f"under_{str(line).replace('.', '_')}"
        if line_key_o not in ou_dict or line_key_u not in ou_dict:
            continue

        p_over = ou_dict[line_key_o]["prob"]
        p_under = ou_dict[line_key_u]["prob"]
        z_buf_over = (tot_mean - line) / tot_sigma if tot_sigma > 0 else 0.0
        z_buf_under = (line - tot_mean) / tot_sigma if tot_sigma > 0 else 0.0

        o_odds = parsed_ou_odds.get(line, {}).get("over")
        u_odds = parsed_ou_odds.get(line, {}).get("under")

        # Devig line if both sides provided
        line_devig = calculate_devigged_probabilities({"Over": o_odds, "Under": u_odds}) if (o_odds and u_odds) else None

        o_val = None
        u_val = None
        row_aai_summary = "-"

        if o_odds:
            dev_p = line_devig["outcomes"]["Over"]["devigged_prob"] if line_devig else None
            o_val = evaluate_value(p_over, o_odds, devigged_prob=dev_p, z_buffer=z_buf_over)
            value_analysis[f"Over {line}"] = o_val
            if o_val["aai"]["is_anchor"]:
                all_anchor_candidates.append({
                    "selection": f"Over {line}",
                    "prob": p_over,
                    "prob_pct": f"{p_over * 100:.1f}%",
                    "odds": o_odds,
                    "aai_score": o_val["aai"]["score"],
                    "rationale": f"High probability floor of {p_over * 100:.1f}% with wide safety buffer."
                })
            if o_val["is_value"]:
                all_value_candidates.append({
                    "selection": f"Over {line}",
                    "prob_pct": f"{p_over * 100:.1f}%",
                    "odds": o_odds,
                    "edge_pct": o_val["ev_pct"]
                })

        if u_odds:
            dev_p = line_devig["outcomes"]["Under"]["devigged_prob"] if line_devig else None
            u_val = evaluate_value(p_under, u_odds, devigged_prob=dev_p, z_buffer=z_buf_under)
            value_analysis[f"Under {line}"] = u_val
            if u_val["aai"]["is_anchor"]:
                all_anchor_candidates.append({
                    "selection": f"Under {line}",
                    "prob": p_under,
                    "prob_pct": f"{p_under * 100:.1f}%",
                    "odds": u_odds,
                    "aai_score": u_val["aai"]["score"],
                    "rationale": f"High probability floor of {p_under * 100:.1f}% with {abs(z_buf_under):.1f}σ safety cushion below expectation."
                })
            if u_val["is_value"]:
                all_value_candidates.append({
                    "selection": f"Under {line}",
                    "prob_pct": f"{p_under * 100:.1f}%",
                    "odds": u_odds,
                    "edge_pct": u_val["ev_pct"]
                })

        # Summary badge for row
        if u_val and u_val["aai"]["is_anchor"]:
            row_aai_summary = f"Under AAI: {u_val['aai']['score']} ({u_val['aai']['tier']})"
        elif o_val and o_val["aai"]["is_anchor"]:
            row_aai_summary = f"Over AAI: {o_val['aai']['score']} ({o_val['aai']['tier']})"

        if o_odds or u_odds:
            ou_analysis_table.append({
                "line": line,
                "over_pct": ou_dict[line_key_o]["pct"],
                "over_odds": o_odds,
                "over_ev": o_val["ev_pct"] if o_val else None,
                "under_pct": ou_dict[line_key_u]["pct"],
                "under_odds": u_odds,
                "under_ev": u_val["ev_pct"] if u_val else None,
                "aai_summary": row_aai_summary
            })

    # Legacy O/U odds handling (fallback if --ou-odds not passed)
    if args.odds_o25 and not parsed_ou_odds:
        target_line = 2.5 if 2.5 in ou_lines else ou_lines[0]
        key = f"over_{str(target_line).replace('.', '_')}"
        if key in ou_dict:
            value_analysis[f"Over {target_line}"] = evaluate_value(ou_dict[key]["prob"], args.odds_o25)
    if args.odds_u25 and not parsed_ou_odds:
        target_line = 2.5 if 2.5 in ou_lines else ou_lines[0]
        key = f"under_{str(target_line).replace('.', '_')}"
        if key in ou_dict:
            value_analysis[f"Under {target_line}"] = evaluate_value(ou_dict[key]["prob"], args.odds_u25)

    # Initialize audited options
    audited_options: Dict[str, Any] = {}

    # Custom single line odds (--odds-line)
    for custom_spec in args.odds_line:
        if ":" in custom_spec:
            lbl, odd_s = custom_spec.rsplit(":", 1)
            try:
                odd_f = float(odd_s.strip())
                lbl_clean = lbl.strip()
                prob, c_key, desc = match_arbitrary_market(lbl_clean, results)
                if prob is not None:
                    eval_res = evaluate_value(prob, odd_f)
                    value_analysis[lbl_clean] = eval_res
                    audited_options[lbl_clean] = {
                        "label": lbl_clean,
                        "canonical_key": c_key,
                        "description": desc,
                        "model_prob": round(prob, 4),
                        "pct": f"{prob * 100:.1f}%",
                        "fair_odds": round(1.0 / prob, 2) if prob > 0 else 999.0,
                        "market_odds": odd_f,
                        "implied_pct": eval_res["implied_pct"],
                        "ev_pct": eval_res["ev_pct"],
                        "is_value": eval_res["is_value"],
                        "aai": eval_res["aai"]
                    }
                    if eval_res["aai"]["is_anchor"]:
                        all_anchor_candidates.append({
                            "selection": lbl_clean,
                            "prob": prob,
                            "prob_pct": f"{prob * 100:.1f}%",
                            "odds": odd_f,
                            "aai_score": eval_res["aai"]["score"],
                            "rationale": f"Audited selection '{desc}' with high probability floor of {prob * 100:.1f}% and verified safety buffer."
                        })
                    if eval_res["is_value"]:
                        all_value_candidates.append({
                            "selection": lbl_clean,
                            "prob_pct": f"{prob * 100:.1f}%",
                            "odds": odd_f,
                            "edge_pct": eval_res["ev_pct"]
                        })
                else:
                    for ok in ou_dict:
                        if ok in lbl_clean.lower().replace(".", "_"):
                            value_analysis[lbl_clean] = evaluate_value(ou_dict[ok]["prob"], odd_f)
                            break
                    else:
                        value_analysis[lbl_clean] = {
                            "market_odds": odd_f,
                            "implied_pct": f"{100/odd_f:.1f}%",
                            "ev_pct": 0.0,
                            "is_value": False,
                            "aai": {"score": 0.0, "badge": "N/A", "is_anchor": False}
                        }
            except ValueError:
                pass

    # Custom market queries without odds (--market-query)
    for q_spec in args.market_query:
        lbl_clean = q_spec.strip()
        prob, c_key, desc = match_arbitrary_market(lbl_clean, results)
        if prob is not None:
            audited_options[lbl_clean] = {
                "label": lbl_clean,
                "canonical_key": c_key,
                "description": desc,
                "model_prob": round(prob, 4),
                "pct": f"{prob * 100:.1f}%",
                "fair_odds": round(1.0 / prob, 2) if prob > 0 else 999.0
            }

    if audited_options:
        results["audited_options"] = audited_options

    if args.odds_btts_yes and "btts" in results:
        value_analysis["BTTS Yes"] = evaluate_value(results["btts"]["yes"]["prob"], args.odds_btts_yes)
    if args.odds_btts_no and "btts" in results:
        value_analysis["BTTS No"] = evaluate_value(results["btts"]["no"]["prob"], args.odds_btts_no)

    if value_analysis:
        results["value_bets"] = value_analysis

    # Determine Top Primary Recommendations
    recommendations: Dict[str, Any] = {}
    if all_anchor_candidates:
        all_anchor_candidates.sort(key=lambda x: x["aai_score"], reverse=True)
        recommendations["accumulator_anchor"] = all_anchor_candidates[0]
    elif mr["away_win"]["prob"] >= 0.75 and args.odds_away:
        recommendations["accumulator_anchor"] = {
            "selection": f"{args.away} Win",
            "prob_pct": mr["away_win"]["pct"],
            "odds": args.odds_away,
            "aai_score": evaluate_value(mr["away_win"]["prob"], args.odds_away)["aai"]["score"],
            "rationale": f"High baseline win probability of {mr['away_win']['pct']}."
        }
    elif mr["home_win"]["prob"] >= 0.75 and args.odds_home:
        recommendations["accumulator_anchor"] = {
            "selection": f"{args.home} Win",
            "prob_pct": mr["home_win"]["pct"],
            "odds": args.odds_home,
            "aai_score": evaluate_value(mr["home_win"]["prob"], args.odds_home)["aai"]["score"],
            "rationale": f"High baseline win probability of {mr['home_win']['pct']}."
        }

    if all_value_candidates:
        all_value_candidates.sort(key=lambda x: x["edge_pct"], reverse=True)
        recommendations["value_bet"] = all_value_candidates[0]

    # Most probable outcome
    if mr["home_win"]["prob"] > mr["away_win"]["prob"]:
        recommendations["most_probable_outcome"] = {"outcome": f"{args.home} Win", "prob_pct": mr["home_win"]["pct"]}
    else:
        recommendations["most_probable_outcome"] = {"outcome": f"{args.away} Win", "prob_pct": mr["away_win"]["pct"]}

    results["recommendations"] = recommendations

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
        ou_analysis_table=ou_analysis_table if ou_analysis_table else None,
        devigged_market=devigged_match,
        period_splits=period_splits if period_splits else None,
    )


if __name__ == "__main__":
    main()

