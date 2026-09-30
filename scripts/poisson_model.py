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

    # Top Scorelines (Poisson only)
    if "top_scorelines" in results:
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
    parser.add_argument("--model", type=str, default=None, choices=["poisson", "normal"],
                        help="Force a specific model (overrides sport default)")

    # Custom over/under lines & multi-line odds
    parser.add_argument("--ou-lines", type=str, default=None,
                        help="Comma-separated over/under lines (e.g., '2.5,3.5,4.5' or '154.5,161.5,168.5')")
    parser.add_argument("--ou-odds", type=str, default=None,
                        help="Multi-line Over/Under odds. Format: 'line:over:under,...' e.g. '154.5:1.43:2.65,168.5:2.70:1.41'")

    # Arbitrary custom market odds line (repeatable)
    parser.add_argument("--odds-line", type=str, action="append", default=[],
                        help="Custom market line with odd. Format: 'label:odds' e.g. '1h_under_82_5:1.64'")

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

    # Custom single line odds (--odds-line)
    for custom_spec in args.odds_line:
        if ":" in custom_spec:
            lbl, odd_s = custom_spec.split(":", 1)
            try:
                odd_f = float(odd_s.strip())
                lbl_clean = lbl.strip()
                # Check if it matches an OU line
                for ok in ou_dict:
                    if ok in lbl_clean.lower().replace(".", "_"):
                        value_analysis[lbl_clean] = evaluate_value(ou_dict[ok]["prob"], odd_f)
                        break
                else:
                    value_analysis[lbl_clean] = {"market_odds": odd_f, "implied_pct": f"{100/odd_f:.1f}%", "ev_pct": 0.0, "is_value": False}
            except ValueError:
                pass

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

