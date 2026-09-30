#!/usr/bin/env python3
"""
Sport Profiles Registry for match-prediction-engine.
Defines per-sport configurations: scoring parameters, market availability,
model selection, Dixon-Coles rho, over/under lines, terminology, and
public statistical data sources.

No external dependencies required (pure standard library).
"""

from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Sport Profile Schema
# ---------------------------------------------------------------------------
# Each profile is a dictionary with these keys:
#   name            : Human-readable sport name
#   scoring_unit    : What gets scored ("goals", "points", "runs", "games")
#   model           : "poisson" for low/mid scoring, "normal" for high scoring
#   rho             : Dixon-Coles correlation factor (0.0 = disabled)
#   max_score       : Upper bound for Poisson matrix dimension
#   default_home_avg: Typical home scoring average (league baseline)
#   default_away_avg: Typical away scoring average (league baseline)
#   has_draw        : Whether regulation time can end in a draw
#   has_btts        : Whether "both teams to score" market is meaningful
#   has_clean_sheet : Whether shutouts / clean sheets are a relevant market
#   ou_lines        : Default over/under lines for the sport
#   spread_lines    : Default spread / handicap lines
#   markets         : List of available market categories
#   labels          : Display labels for output formatting
#   stat_sources    : Public statistical data sources for research
#   key_metrics     : Sport-specific performance metrics to research
#   focus_modes     : Available analytical focus modes
# ---------------------------------------------------------------------------


def _football_profile() -> Dict[str, Any]:
    return {
        "name": "Football (Soccer)",
        "scoring_unit": "goals",
        "model": "poisson",
        "rho": -0.11,
        "max_score": 10,
        "default_home_avg": 1.52,
        "default_away_avg": 1.20,
        "has_draw": True,
        "has_btts": True,
        "has_clean_sheet": True,
        "ou_lines": [0.5, 1.5, 2.5, 3.5, 4.5],
        "spread_lines": [-2.5, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.5],
        "markets": [
            "1x2", "double_chance", "draw_no_bet", "over_under",
            "btts", "clean_sheet", "exact_score", "half_time_full_time",
            "corners", "cards", "player_props", "asian_handicap",
            "combos", "goal_bands", "team_totals", "win_to_nil", "odd_even"
        ],
        "labels": {
            "score": "goals",
            "home_score": "Home Goals",
            "away_score": "Away Goals",
            "total_score": "Total Goals",
            "expected": "Expected Goals (xG)",
            "result": "1X2 Match Outcome",
        },
        "stat_sources": [
            "FBref (fbref.com)", "Understat (understat.com)",
            "WhoScored (whoscored.com)", "Flashscore (flashscore.com)",
            "Transfermarkt (transfermarkt.com)", "SofaScore (sofascore.com)"
        ],
        "key_metrics": [
            "xG created per 90", "xG conceded (xGA) per 90",
            "Shot conversion rate", "Box entries per 90",
            "Corner averages (won/conceded)", "Referee cards per game",
            "Possession %", "PPDA (Passes Per Defensive Action)"
        ],
        "focus_modes": [
            "goals_match_flow", "btts", "corners", "cards_discipline",
            "player_props_goalscorer", "half_time_trends",
            "accumulator_anchor", "value_hunter", "asian_handicap"
        ],
    }


def _basketball_profile(league_format: str = "nba") -> Dict[str, Any]:
    return {
        "name": "Basketball (NBA / 48-Min)",
        "scoring_unit": "points",
        "model": "normal",
        "rho": 0.0,
        "max_score": 200,
        "default_home_avg": 112.0,
        "default_away_avg": 109.0,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [195.5, 200.5, 205.5, 210.5, 215.5, 220.5, 225.5],
        "spread_lines": [-10.5, -7.5, -5.5, -3.5, -1.5, 1.5, 3.5, 5.5, 7.5, 10.5],
        "markets": [
            "moneyline", "spread", "over_under", "quarter_totals",
            "half_totals", "player_props", "race_to_points"
        ],
        "labels": {
            "score": "points",
            "home_score": "Home Points",
            "away_score": "Away Points",
            "total_score": "Total Points",
            "expected": "Expected Points",
            "result": "Moneyline Outcome",
        },
        "stat_sources": [
            "Basketball Reference (basketball-reference.com)",
            "NBA Stats (nba.com/stats)", "ESPN (espn.com)",
            "Flashscore (flashscore.com)", "SofaScore (sofascore.com)"
        ],
        "key_metrics": [
            "Offensive Rating (ORtg) per 100 possessions",
            "Defensive Rating (DRtg) per 100 possessions",
            "Pace (possessions per 48 minutes)",
            "Effective Field Goal % (eFG%)",
            "Turnover rate", "Rebound rate (ORB% / DRB%)",
            "Free throw rate", "3-point attempt rate and accuracy"
        ],
        "focus_modes": [
            "moneyline", "spread", "total_points",
            "quarter_totals", "player_props_points",
            "player_props_rebounds", "player_props_assists",
            "accumulator_anchor", "value_hunter"
        ],
    }


def _basketball_fiba_profile() -> Dict[str, Any]:
    return {
        "name": "Basketball (FIBA / EuroLeague / VTB / 40-Min)",
        "scoring_unit": "points",
        "model": "normal",
        "rho": 0.0,
        "max_score": 160,
        "default_home_avg": 81.5,
        "default_away_avg": 78.0,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [148.5, 152.5, 156.5, 160.5, 164.5, 168.5, 172.5],
        "spread_lines": [-10.5, -7.5, -5.5, -3.5, -1.5, 1.5, 3.5, 5.5, 7.5, 10.5],
        "markets": [
            "moneyline", "spread", "over_under", "quarter_totals",
            "half_totals", "player_props", "race_to_points"
        ],
        "labels": {
            "score": "points",
            "home_score": "Home Points",
            "away_score": "Away Points",
            "total_score": "Total Points",
            "expected": "Expected Points",
            "result": "Moneyline Outcome",
        },
        "stat_sources": [
            "EuroLeague Stats (euroleaguebasketball.net)",
            "VTB United League (vtb-league.com)",
            "ACB (acb.com)", "Flashscore (flashscore.com)", "SofaScore (sofascore.com)",
            "Basketball Reference (basketball-reference.com)"
        ],
        "key_metrics": [
            "Offensive Rating (ORtg) per 100 possessions",
            "Defensive Rating (DRtg) per 100 possessions",
            "Pace (possessions per 40 minutes)",
            "Effective Field Goal % (eFG%)",
            "Turnover rate", "Rebound rate (ORB% / DRB%)",
            "Free throw rate", "3-point attempt rate and accuracy"
        ],
        "focus_modes": [
            "moneyline", "spread", "total_points",
            "quarter_totals", "half_totals", "accumulator_anchor", "value_hunter"
        ],
    }


def _basketball_ncaa_profile() -> Dict[str, Any]:
    return {
        "name": "Basketball (NCAA Men's College / 40-Min)",
        "scoring_unit": "points",
        "model": "normal",
        "rho": 0.0,
        "max_score": 150,
        "default_home_avg": 73.5,
        "default_away_avg": 69.0,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [132.5, 136.5, 140.5, 144.5, 148.5, 152.5],
        "spread_lines": [-12.5, -9.5, -6.5, -3.5, -1.5, 1.5, 3.5, 6.5, 9.5, 12.5],
        "markets": [
            "moneyline", "spread", "over_under", "half_totals", "accumulator_anchor"
        ],
        "labels": {
            "score": "points",
            "home_score": "Home Points",
            "away_score": "Away Points",
            "total_score": "Total Points",
            "expected": "Expected Points",
            "result": "Moneyline Outcome",
        },
        "stat_sources": [
            "KenPom (kenpom.com)", "BartTorvik (barttorvik.com)",
            "NCAA Stats (ncaa.com)", "ESPN (espn.com)", "Sports Reference CBB"
        ],
        "key_metrics": [
            "Adjusted Offensive Efficiency (AdjO)",
            "Adjusted Defensive Efficiency (AdjD)",
            "Adjusted Tempo (Pace)",
            "Effective FG% (Offense vs Defense)",
            "Turnover %", "Offensive Rebound %"
        ],
        "focus_modes": [
            "moneyline", "spread", "total_points",
            "half_totals", "accumulator_anchor", "value_hunter"
        ],
    }


def _ice_hockey_profile() -> Dict[str, Any]:
    return {
        "name": "Ice Hockey",
        "scoring_unit": "goals",
        "model": "poisson",
        "rho": -0.08,
        "max_score": 12,
        "default_home_avg": 3.10,
        "default_away_avg": 2.80,
        "has_draw": True,  # Regulation time can draw (OT/SO decides)
        "has_btts": True,
        "has_clean_sheet": True,
        "ou_lines": [3.5, 4.5, 5.5, 6.5, 7.5],
        "spread_lines": [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5],
        "markets": [
            "1x2_regulation", "moneyline_inc_ot", "puck_line",
            "over_under", "btts", "period_betting",
            "player_props", "exact_score"
        ],
        "labels": {
            "score": "goals",
            "home_score": "Home Goals",
            "away_score": "Away Goals",
            "total_score": "Total Goals",
            "expected": "Expected Goals (xG)",
            "result": "Regulation Time Result",
        },
        "stat_sources": [
            "Natural Stat Trick (naturalstattrick.com)",
            "Hockey Reference (hockey-reference.com)",
            "MoneyPuck (moneypuck.com)", "Elite Prospects (eliteprospects.com)",
            "Flashscore (flashscore.com)", "NHL Stats (nhl.com/stats)"
        ],
        "key_metrics": [
            "xG per 60 (5v5)", "Corsi For % (CF%)",
            "Fenwick For % (FF%)", "High-Danger Chances For/Against",
            "Save percentage (SV%)", "Power play % (PP%)",
            "Penalty kill % (PK%)", "Shots on goal per game"
        ],
        "focus_modes": [
            "regulation_result", "puck_line", "total_goals",
            "period_betting", "btts", "player_props_goals",
            "player_props_shots", "accumulator_anchor", "value_hunter"
        ],
    }


def _tennis_profile() -> Dict[str, Any]:
    return {
        "name": "Tennis",
        "scoring_unit": "games",
        "model": "tennis",
        "rho": 0.0,
        "max_score": 13,  # Max games in a set
        "default_home_avg": 6.0,  # Expected games per set
        "default_away_avg": 4.8,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [19.5, 20.5, 21.5, 22.5, 23.5, 24.5],
        "spread_lines": [-4.5, -3.5, -2.5, -1.5, 1.5, 2.5, 3.5, 4.5],
        "markets": [
            "match_winner", "set_betting", "total_games",
            "set_handicap", "game_handicap", "tiebreak",
            "first_set_winner", "player_to_win_set", "total_sets"
        ],
        "labels": {
            "score": "games",
            "home_score": "Player 1 Games",
            "away_score": "Player 2 Games",
            "total_score": "Total Games",
            "expected": "Expected Games Per Set",
            "result": "Match Winner",
        },
        "stat_sources": [
            "Tennis Abstract (tennisabstract.com)",
            "Ultimate Tennis Statistics (ultimatetennisstatistics.com)",
            "ATP/WTA Tour (atptour.com / wtatennis.com)",
            "Flashscore (flashscore.com)", "SofaScore (sofascore.com)"
        ],
        "key_metrics": [
            "Service games won %", "Return games won %",
            "1st serve % in", "1st serve points won %",
            "2nd serve points won %", "Break points saved %",
            "Break points converted %", "Tiebreak win rate",
            "Surface win rate (hard/clay/grass)"
        ],
        "focus_modes": [
            "match_winner", "set_betting", "total_games",
            "set_handicap", "game_handicap", "first_set",
            "accumulator_anchor", "value_hunter"
        ],
    }


def _table_tennis_profile() -> Dict[str, Any]:
    return {
        "name": "Table Tennis",
        "scoring_unit": "points",
        "model": "table_tennis",
        "rho": 0.0,
        "max_score": 15,  # Per game, can go to deuce beyond 11
        "default_home_avg": 11.0,
        "default_away_avg": 9.5,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [71.5, 73.5, 74.5, 75.5, 77.5],  # Total match points
        "spread_lines": [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5],  # Sets handicap
        "markets": [
            "match_winner", "set_betting", "set_handicap",
            "total_sets", "total_points", "first_set_winner",
            "player_to_win_set"
        ],
        "labels": {
            "score": "points",
            "home_score": "Player 1 Points",
            "away_score": "Player 2 Points",
            "total_score": "Total Points",
            "expected": "Expected Points Per Game",
            "result": "Match Winner",
        },
        "stat_sources": [
            "ITTF (ittf.com)", "Table Tennis Reference",
            "Flashscore (flashscore.com)", "SofaScore (sofascore.com)",
            "RatingsDB (tabletennis.guide)"
        ],
        "key_metrics": [
            "Match win rate (last 10-20 matches)",
            "Games won per match average",
            "Head-to-head record",
            "5th game (deciding game) win rate",
            "Recent form streak",
            "Surface / ball type adaptation"
        ],
        "focus_modes": [
            "match_winner", "set_betting", "set_handicap",
            "total_sets", "total_points",
            "accumulator_anchor", "value_hunter"
        ],
    }


def _baseball_profile() -> Dict[str, Any]:
    return {
        "name": "Baseball",
        "scoring_unit": "runs",
        "model": "poisson",
        "rho": 0.0,
        "max_score": 20,
        "default_home_avg": 4.60,
        "default_away_avg": 4.40,
        "has_draw": False,
        "has_btts": True,
        "has_clean_sheet": True,
        "ou_lines": [6.5, 7.5, 8.5, 9.5, 10.5],
        "spread_lines": [-2.5, -1.5, 1.5, 2.5],
        "markets": [
            "moneyline", "run_line", "over_under",
            "first_5_innings", "btts_runs", "player_props",
            "inning_scoring"
        ],
        "labels": {
            "score": "runs",
            "home_score": "Home Runs Scored",
            "away_score": "Away Runs Scored",
            "total_score": "Total Runs",
            "expected": "Expected Runs",
            "result": "Moneyline Outcome",
        },
        "stat_sources": [
            "Baseball Reference (baseball-reference.com)",
            "FanGraphs (fangraphs.com)", "Baseball Savant (baseballsavant.mlb.com)",
            "ESPN (espn.com)", "Flashscore (flashscore.com)"
        ],
        "key_metrics": [
            "ERA (Earned Run Average)", "FIP (Fielding Independent Pitching)",
            "WHIP (Walks + Hits per Inning Pitched)",
            "wOBA (Weighted On-Base Average)", "OPS (On-base Plus Slugging)",
            "K/9 (Strikeouts per 9 innings)", "BB/9 (Walks per 9)",
            "Bullpen ERA", "Starting pitcher matchup"
        ],
        "focus_modes": [
            "moneyline", "run_line", "total_runs",
            "first_5_innings", "player_props_hits",
            "player_props_strikeouts", "accumulator_anchor", "value_hunter"
        ],
    }


def _american_football_profile() -> Dict[str, Any]:
    return {
        "name": "American Football",
        "scoring_unit": "points",
        "model": "normal",
        "rho": 0.0,
        "max_score": 70,
        "default_home_avg": 23.5,
        "default_away_avg": 21.0,
        "has_draw": False,  # OT rules virtually eliminate draws
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [37.5, 40.5, 43.5, 45.5, 47.5, 50.5, 53.5],
        "spread_lines": [-14.5, -10.5, -7.5, -6.5, -3.5, -2.5, -1.5,
                         1.5, 2.5, 3.5, 6.5, 7.5, 10.5, 14.5],
        "markets": [
            "moneyline", "spread", "over_under",
            "half_totals", "quarter_spreads", "player_props",
            "touchdown_scorer"
        ],
        "labels": {
            "score": "points",
            "home_score": "Home Points",
            "away_score": "Away Points",
            "total_score": "Total Points",
            "expected": "Expected Points",
            "result": "Moneyline Outcome",
        },
        "stat_sources": [
            "Pro Football Reference (pro-football-reference.com)",
            "ESPN (espn.com)", "NFL Stats (nfl.com/stats)",
            "Football Outsiders (footballoutsiders.com)",
            "PFF (pff.com)", "The Football Database (footballdb.com)"
        ],
        "key_metrics": [
            "Points per game (PPG)", "Points allowed per game",
            "DVOA (Defense-adjusted Value Over Average)",
            "Yards per play (offense/defense)",
            "Turnover differential", "Red zone scoring %",
            "3rd down conversion rate", "Time of possession",
            "QB passer rating"
        ],
        "focus_modes": [
            "moneyline", "spread", "total_points",
            "half_totals", "player_props_passing",
            "player_props_rushing", "player_props_receiving",
            "touchdown_scorer", "accumulator_anchor", "value_hunter"
        ],
    }


def _rugby_profile() -> Dict[str, Any]:
    return {
        "name": "Rugby Union",
        "scoring_unit": "points",
        "model": "normal",
        "rho": 0.0,
        "max_score": 80,
        "default_home_avg": 25.0,
        "default_away_avg": 20.0,
        "has_draw": True,  # Rare but possible
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [35.5, 40.5, 45.5, 50.5, 55.5],
        "spread_lines": [-15.5, -10.5, -7.5, -3.5, 3.5, 7.5, 10.5, 15.5],
        "markets": [
            "1x2", "handicap", "over_under", "try_scorer",
            "total_tries", "winning_margin", "half_time_result"
        ],
        "labels": {
            "score": "points",
            "home_score": "Home Points",
            "away_score": "Away Points",
            "total_score": "Total Points",
            "expected": "Expected Points",
            "result": "Match Result",
        },
        "stat_sources": [
            "ESPN Scrum (espn.com/rugby)", "World Rugby (world.rugby)",
            "Ultimate Rugby (ultimaterugby.com)",
            "Rugby Pass (rugbypass.com)", "Flashscore (flashscore.com)"
        ],
        "key_metrics": [
            "Points per game (PPG)", "Points conceded per game",
            "Try scoring rate", "Lineout success %",
            "Scrum success %", "Tackle completion %",
            "Discipline (penalties conceded per game)",
            "Territory and possession %"
        ],
        "focus_modes": [
            "match_result", "handicap", "total_points",
            "total_tries", "try_scorer", "winning_margin",
            "accumulator_anchor", "value_hunter"
        ],
    }


def _handball_profile() -> Dict[str, Any]:
    return {
        "name": "Handball",
        "scoring_unit": "goals",
        "model": "poisson",
        "rho": 0.0,
        "max_score": 50,
        "default_home_avg": 29.0,
        "default_away_avg": 26.5,
        "has_draw": True,
        "has_btts": True,
        "has_clean_sheet": False,
        "ou_lines": [48.5, 50.5, 52.5, 54.5, 56.5, 58.5],
        "spread_lines": [-6.5, -4.5, -2.5, -1.5, 1.5, 2.5, 4.5, 6.5],
        "markets": [
            "1x2", "handicap", "over_under", "half_time_result",
            "half_time_over_under", "double_chance",
            "winning_margin"
        ],
        "labels": {
            "score": "goals",
            "home_score": "Home Goals",
            "away_score": "Away Goals",
            "total_score": "Total Goals",
            "expected": "Expected Goals",
            "result": "Match Result",
        },
        "stat_sources": [
            "EHF (eurohandball.com)", "IHF (ihf.info)",
            "Handball World (handball-world.news)",
            "Flashscore (flashscore.com)", "SofaScore (sofascore.com)"
        ],
        "key_metrics": [
            "Goals per game (scored/conceded)",
            "Shooting efficiency %", "Save percentage (GK)",
            "Fast break goals per game", "7-meter (penalty) conversion %",
            "Turnover rate", "Suspension (2-min penalties) per game"
        ],
        "focus_modes": [
            "match_result", "handicap", "total_goals",
            "half_time", "accumulator_anchor", "value_hunter"
        ],
    }


def _volleyball_profile() -> Dict[str, Any]:
    return {
        "name": "Volleyball",
        "scoring_unit": "sets",
        "model": "poisson",
        "rho": 0.0,
        "max_score": 5,  # Best of 5 sets
        "default_home_avg": 2.8,
        "default_away_avg": 2.2,
        "has_draw": False,
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [3.5, 4.5],  # Total sets
        "spread_lines": [-2.5, -1.5, -0.5, 0.5, 1.5, 2.5],
        "markets": [
            "match_winner", "set_betting", "total_sets",
            "set_handicap", "total_points", "set_score"
        ],
        "labels": {
            "score": "sets",
            "home_score": "Home Sets",
            "away_score": "Away Sets",
            "total_score": "Total Sets",
            "expected": "Expected Sets Won",
            "result": "Match Winner",
        },
        "stat_sources": [
            "FIVB (fivb.com)", "Volleyball World",
            "Flashscore (flashscore.com)", "SofaScore (sofascore.com)"
        ],
        "key_metrics": [
            "Set win rate", "Attack efficiency %",
            "Block per set average", "Ace per set average",
            "Reception efficiency %", "Dig per set average",
            "3-0 / 3-1 / 3-2 outcome frequency"
        ],
        "focus_modes": [
            "match_winner", "set_betting", "total_sets",
            "set_handicap", "total_points",
            "accumulator_anchor", "value_hunter"
        ],
    }


def _cricket_profile() -> Dict[str, Any]:
    return {
        "name": "Cricket",
        "scoring_unit": "runs",
        "model": "normal",
        "rho": 0.0,
        "max_score": 300,
        "default_home_avg": 165.0,  # T20 baseline
        "default_away_avg": 155.0,
        "has_draw": False,  # Limited-overs; Test cricket is separate
        "has_btts": False,
        "has_clean_sheet": False,
        "ou_lines": [280.5, 300.5, 320.5, 340.5, 360.5],
        "spread_lines": [-20.5, -15.5, -10.5, -5.5, 5.5, 10.5, 15.5, 20.5],
        "markets": [
            "match_winner", "total_runs", "top_batsman",
            "top_bowler", "innings_runs", "player_props",
            "method_of_dismissal", "total_sixes", "total_fours"
        ],
        "labels": {
            "score": "runs",
            "home_score": "Team 1 Runs",
            "away_score": "Team 2 Runs",
            "total_score": "Total Runs",
            "expected": "Expected Runs",
            "result": "Match Winner",
        },
        "stat_sources": [
            "ESPNcricinfo (espncricinfo.com)", "Cricbuzz (cricbuzz.com)",
            "HowSTAT (howstat.com)", "Cricket Archive (cricketarchive.com)",
            "Flashscore (flashscore.com)"
        ],
        "key_metrics": [
            "Batting average", "Strike rate",
            "Economy rate (bowling)", "Bowling average",
            "Powerplay scoring rate", "Death overs economy",
            "Pitch report and toss advantage",
            "Head-to-head at venue", "Dew factor (day/night)"
        ],
        "focus_modes": [
            "match_winner", "total_runs", "top_batsman",
            "top_bowler", "total_sixes", "innings_runs",
            "accumulator_anchor", "value_hunter"
        ],
    }


# ---------------------------------------------------------------------------
# Profile Registry
# ---------------------------------------------------------------------------
SPORT_PROFILES: Dict[str, Dict[str, Any]] = {
    "football": _football_profile(),
    "soccer": _football_profile(),            # Alias
    "basketball": _basketball_profile(),      # NBA default
    "basketball_nba": _basketball_profile(),
    "nba": _basketball_profile(),             # Alias
    "basketball_fiba": _basketball_fiba_profile(),
    "fiba": _basketball_fiba_profile(),       # Alias
    "euroleague": _basketball_fiba_profile(), # Alias
    "vtb": _basketball_fiba_profile(),        # Alias
    "basketball_ncaa": _basketball_ncaa_profile(),
    "ncaa": _basketball_ncaa_profile(),       # Alias
    "ncaa_basketball": _basketball_ncaa_profile(),
    "college_basketball": _basketball_ncaa_profile(),
    "ice_hockey": _ice_hockey_profile(),
    "hockey": _ice_hockey_profile(),          # Alias
    "tennis": _tennis_profile(),
    "table_tennis": _table_tennis_profile(),
    "ping_pong": _table_tennis_profile(),     # Alias
    "baseball": _baseball_profile(),
    "mlb": _baseball_profile(),               # Alias
    "american_football": _american_football_profile(),
    "nfl": _american_football_profile(),      # Alias
    "rugby": _rugby_profile(),
    "handball": _handball_profile(),
    "volleyball": _volleyball_profile(),
    "cricket": _cricket_profile(),
}

# Canonical name mapping (alias -> canonical)
SPORT_ALIASES: Dict[str, str] = {
    "soccer": "football",
    "hockey": "ice_hockey",
    "nfl": "american_football",
    "mlb": "baseball",
    "ping_pong": "table_tennis",
    "nba": "basketball",
    "basketball_nba": "basketball",
    "fiba": "basketball_fiba",
    "euroleague": "basketball_fiba",
    "vtb": "basketball_fiba",
    "ncaa": "basketball_ncaa",
    "ncaa_basketball": "basketball_ncaa",
    "college_basketball": "basketball_ncaa",
}


def get_profile(sport: str, league_format: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieve sport profile by name. Case-insensitive, supports aliases.
    Supports optional league_format override (e.g. 'fiba', 'nba', 'ncaa' for basketball).
    Raises ValueError if sport is not recognized.
    """
    key = sport.lower().strip().replace(" ", "_").replace("-", "_")

    # If sport is basketball and a format was requested, redirect
    if key in ("basketball", "basketball_nba", "nba") and league_format:
        fmt = league_format.lower().strip()
        if fmt in ("fiba", "euro", "euroleague", "vtb", "40", "40min", "40_min"):
            key = "basketball_fiba"
        elif fmt in ("ncaa", "college", "cbb"):
            key = "basketball_ncaa"
        elif fmt in ("nba", "48", "48min", "48_min"):
            key = "basketball_nba"

    if key not in SPORT_PROFILES:
        canonical = sorted(set(SPORT_ALIASES.get(k, k) for k in SPORT_PROFILES))
        raise ValueError(
            f"Unknown sport: '{sport}'. Available: {', '.join(canonical)}"
        )
    return SPORT_PROFILES[key]


def list_sports() -> List[str]:
    """Return sorted list of canonical sport names."""
    return sorted(set(SPORT_ALIASES.get(k, k) for k in SPORT_PROFILES))


if __name__ == "__main__":
    import json
    print("Supported Sports:")
    for sport in list_sports():
        profile = get_profile(sport)
        print(f"  {profile['name']} ({sport}) — model: {profile['model']}, "
              f"unit: {profile['scoring_unit']}, draws: {profile['has_draw']}")
