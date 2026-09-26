---
name: match-prediction-engine
description: Deep sports betting research and quantitative match prediction engine. Operates with zero paid APIs by combining live public match intelligence, Expected Goals (xG), lineup dynamics, bivariate Poisson distribution modeling, and expected value (+EV) calculations into verified prediction dossiers.
---

# Match Prediction Engine

The `match-prediction-engine` is a rigorous, quantitative sports analysis workflow designed to deliver high-accuracy match breakdowns and betting predictions without reliance on expensive paid APIs. 

It replaces gut feeling and generic AI guessing with a disciplined two-pillar methodology:
1. **Live Contextual Intelligence**: Real-time public intelligence on starting elevens, injuries, tactical setups, and rest differentials.
2. **Mathematical Modeling**: A deterministic Poisson and Dixon-Coles model executed locally to establish objective probabilities, fair odds, and market discrepancies (+EV).

---

## The 6-Step Analysis Workflow

When the user asks for a prediction on any match or random fixture, execute these steps in order.

### Step 1: Intake & Match Verification
- Clarify the exact fixture: Home team, Away team, Competition, Date, and Kickoff venue.
- Confirm home/away venue status (neutral venue matches must not use home-advantage weighting).

### Step 2: Live Public Intelligence Gathering
Execute targeted web queries to extract current, match-specific conditions:
- Search query examples:
  - `"[Home Team] vs [Away Team] team news injuries lineups [Current Year]"`
  - `"[Team Name] injury update press conference [Month Year]"`
- Extract:
  - Confirmed or highly anticipated starting lineups.
  - Missing key personnel: starting goalkeeper, primary goalscorer, central defensive anchor.
  - Schedule density: Did either team play an intense continental or cup match 3 days ago?
  - Tactical dynamic: High-press vs low-block, transition vulnerability.

### Step 3: Statistical Sourcing (Last 5 to 10 Matches)
Search public sports data sources (FBref, Understat, Flashscore, WhoScored, Transfermarkt) for:
- Home team home form: Expected Goals (xG) created, xG conceded (xGA), actual goals scored/conceded.
- Away team away form: xG created, xGA conceded, actual goals scored/conceded.
- League average goals per match (default to 1.52 Home and 1.20 Away for standard European top flights if unspecified).
- Current market odds from public odds comparison pages.

### Step 4: Local Mathematical Modeling
Run the local calculation script located at:
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --home "<HOME_TEAM>" \
  --away "<AWAY_TEAM>" \
  --home-xg <HOME_XG> \
  --away-xg <AWAY_XG> \
  --odds-home <HOME_ODDS> \
  --odds-draw <DRAW_ODDS> \
  --odds-away <AWAY_ODDS> \
  --odds-o25 <O25_ODDS> \
  --odds-btts-yes <BTTS_ODDS>
```
If direct xG expectation is derived from attack/defense ratios:
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --home "<HOME_TEAM>" \
  --away "<AWAY_TEAM>" \
  --home-attack <HOME_GOALS_SCORED_PER_GAME> \
  --home-defense <HOME_GOALS_CONCEDED_PER_GAME> \
  --away-attack <AWAY_GOALS_SCORED_PER_GAME> \
  --away-defense <AWAY_GOALS_CONCEDED_PER_GAME>
```

### Step 5: Value (+EV) and Risk Synthesis
- Compare the model's true probability against the bookmaker's implied probability:
  $$\text{Edge (\%)} = (\text{Model Probability} \times \text{Bookmaker Odds} - 1) \times 100$$
- If the edge is $> 3\%$, mark the selection as a **Value Bet (+EV)**.
- If no positive edge exists on 1X2, examine secondary markets: Double Chance (1X/X2), Draw No Bet (DNB), Over/Under 1.5 or 2.5, or Both Teams to Score (BTTS).

### Step 6: Deliver the Match Prediction Dossier
Assemble the analysis using the layout defined in `templates/dossier_template.md`:
1. **Match Header**: Teams, league, date, venue.
2. **Tactical Context & Absences**: Real reasons for performance swings.
3. **Statistical Summary**: Table of xG, xGA, and goal averages.
4. **Model Output**: Objective probabilities, fair odds vs market odds.
5. **Categorized Recommendations**:
   - Primary Selection (safest statistical floor)
   - Value Selection (+EV pick where odds favor the punter)
   - Probable Scoreline
6. **Risk Invalidation**: The exact condition that would nullify the logic.

---

## Non-Negotiable Operational Rules

1. **No Emotional or Brand Bias**: Never pick a team simply because they have a bigger name (e.g. Manchester United, Chelsea, Barcelona) if their rolling 5-game underlying xGA is relegation-tier.
2. **No Invented Numbers**: All goals, xG, and odds must come from actual search results or calculated directly by the script.
3. **Account for Motivation**: Beware of "dead rubbers" at the end of group stages or league seasons where a top team has already secured qualification and rests key starters.
4. **Discipline Over Volume**: If a match is completely unpredictable due to high rotation or chaotic weather, explicitly state "Pass / Low Stake" rather than forcing a high-confidence pick.
