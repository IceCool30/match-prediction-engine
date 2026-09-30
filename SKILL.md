---
name: match-prediction-engine
description: Multi-sport quantitative prediction engine. Operates with zero paid APIs by combining live public intelligence, statistical analysis, and mathematical modeling (Poisson / Normal distribution) across football, basketball, ice hockey, tennis, table tennis, baseball, American football, rugby, handball, volleyball, and cricket. Delivers verified prediction dossiers with expected value (+EV) calculations across all major betting markets.
---

# Match Prediction Engine

The `match-prediction-engine` is a rigorous, multi-sport quantitative analysis workflow designed to deliver high-accuracy match breakdowns and betting predictions without reliance on expensive paid APIs.

It replaces gut feeling and generic AI guessing with a disciplined two-pillar methodology:
1. **Live Contextual Intelligence**: Real-time public intelligence on team news, injuries, form, matchups, and schedule dynamics.
2. **Mathematical Modeling**: Deterministic Poisson (low/mid-scoring) or Normal/Gaussian (high-scoring) models executed locally to establish objective probabilities, fair odds, and market discrepancies (+EV).

---

## Supported Sports

| Sport | Model | Scoring Unit | Draws? | Key Statistical Sources |
|-------|-------|-------------|--------|------------------------|
| Football (Soccer) | Poisson + Dixon-Coles | Goals | Yes | FBref, Understat, WhoScored, Transfermarkt |
| Basketball | Normal (Gaussian) | Points | No | Basketball Reference, NBA Stats, ESPN |
| Ice Hockey | Poisson + Dixon-Coles | Goals | Yes (reg) | Natural Stat Trick, Hockey Reference, MoneyPuck |
| Tennis | Poisson | Games | No | Tennis Abstract, Ultimate Tennis Statistics, ATP/WTA |
| Table Tennis | Poisson | Points | No | ITTF, Flashscore, SofaScore |
| Baseball | Poisson | Runs | No | Baseball Reference, FanGraphs, Baseball Savant |
| American Football | Normal (Gaussian) | Points | No | Pro Football Reference, Football Outsiders, ESPN |
| Rugby Union | Normal (Gaussian) | Points | Rare | ESPN Scrum, World Rugby, Ultimate Rugby |
| Handball | Poisson | Goals | Yes | EHF, IHF, Flashscore |
| Volleyball | Poisson | Sets | No | FIVB, Flashscore, SofaScore |
| Cricket | Normal (Gaussian) | Runs | No | ESPNcricinfo, Cricbuzz, HowSTAT |

---

## Dynamic User Directives & Adaptive Focus Modes

The engine **never boxes itself into a single market or sport**. It dynamically adapts its research depth, mathematical filters, and output focus according to:
1. **The sport being analyzed** (auto-detected from user context or explicitly stated)
2. **The user's specific betting objective** (market focus, bankroll strategy, accumulator building)

### Sport-Adaptive Market Focus Modes

#### Football (Soccer)
- **Goals & Match Flow** (Over/Under, Goal Bands): xG, shot conversion, box entries, rolling xG vs xGA, pace of play.
- **Both Teams to Score (BTTS)**: Home scoring consistency vs Away clean-sheet vulnerability.
- **Corners**: Team corner averages (home/away), wing play vs central overload, cross frequency.
- **Cards & Discipline**: Referee cards-per-game, derby intensity, aggressive player matchups.
- **Player Props & Goalscorer**: Shots on target per 90, penalty duties, aerial duel vulnerability.
- **Half-Time Trends**: 1st vs 2nd half scoring splits, slow starters, fatigue drop-offs (60-75+ min).

#### Basketball
- **Moneyline**: Offensive/Defensive rating per 100 possessions, pace, home court advantage.
- **Spread**: Margin of victory modeling via Normal distribution, strength of schedule.
- **Total Points**: Combined pace analysis, defensive tempo, 3-point volume.
- **Quarter/Half Totals**: Scoring splits by period, fast start vs slow start teams.
- **Player Props**: Points, rebounds, assists, PRA (Points + Rebounds + Assists).

#### Ice Hockey
- **Regulation Result (1X2)**: xG per 60 (5v5), Corsi %, high-danger chances.
- **Puck Line (±1.5)**: Margin of victory distribution, empty-net goal trends.
- **Total Goals**: Combined xG, goaltender save %, power play/penalty kill impact.
- **Period Betting**: Scoring by period, fatigue and travel factors.

#### Tennis
- **Match Winner**: Service/return game win rates, surface specialization, head-to-head.
- **Set Betting**: Set win probabilities, tiebreak tendencies, 3-set vs 5-set dynamics.
- **Total Games**: Hold rates, break frequency, expected game count per set.
- **Game/Set Handicap**: Margin modeling based on service game dominance.

#### Table Tennis
- **Match Winner**: Recent form, head-to-head, ranking trajectory.
- **Total Games**: 3-0 / 3-1 / 3-2 outcome distribution, deciding-game win rate.
- **Game Handicap**: Per-game point differentials, momentum patterns.

#### Baseball
- **Moneyline**: Starting pitcher ERA/FIP, bullpen strength, lineup OPS/wOBA.
- **Run Line (±1.5)**: Margin of victory, blowout vs close-game frequency.
- **Total Runs**: Park factors, starting pitcher vs opposing lineup splits.
- **First 5 Innings (F5)**: Isolates starting pitcher impact.

#### American Football
- **Moneyline**: DVOA, points per game, turnover differential.
- **Spread**: Margin modeling, home/away splits, divisional matchup dynamics.
- **Total Points**: Combined scoring pace, defensive efficiency, red zone %.
- **Player Props**: Passing yards, rushing yards, receiving yards, touchdowns.

#### Rugby Union
- **Match Result**: Points per game, try scoring rate, discipline (penalties).
- **Handicap**: Winning margin distribution, home advantage weighting.
- **Total Points/Tries**: Combined scoring rates, lineout/scrum efficiency.

#### Handball
- **Match Result (1X2)**: Goals per game, shooting efficiency, goalkeeper save %.
- **Handicap**: Margin of victory, fast break conversion, suspension impact.
- **Total Goals**: Combined scoring rates, 7-meter conversion, pace of play.

#### Volleyball
- **Match Winner**: Set win rates, attack efficiency, block/ace per set.
- **Set Betting**: 3-0 / 3-1 / 3-2 outcome modeling.
- **Total Sets**: Close-match frequency, tiebreak (5th set) tendencies.

#### Cricket
- **Match Winner**: Batting/bowling averages, venue stats, toss impact, pitch report.
- **Total Runs**: Scoring rates by phase (powerplay, middle overs, death), venue history.
- **Top Batsman/Bowler**: Strike rates, opposition vulnerability, batting position.
- **Total Sixes/Fours**: Power hitting metrics, boundary-scoring rates.

### Strategic / Bankroll Objectives (All Sports)
- **Accumulator / Parlay Anchor Mode**: Filters to highest probability floor outcomes (>75%) across any sport.
- **Value Hunter & Underdog Mode (+EV)**: Identifies mispriced lines where public bias inflates odds.
- **Asian Handicap / Spread Mode**: Evaluates margin of victory distributions for handicap line value.

---

## The 6-Step Analysis Workflow

When the user asks for a prediction on any match or fixture in any sport, execute these steps in order.

### Step 1: Intake, Sport Detection & Screenshot Processing
- **Detect the sport & competition** from the teams/players mentioned, competition name, or explicit user statement.
- **Mobile Screenshot & Slip Intake**:
  - If the user provides or references a screenshot on their phone or a specific bookmaker app (e.g., SportyBet, Bet9ja, Betway, 1xBet):
    1. Scan Termux screenshot locations: `/storage/emulated/0/Pictures/Screenshots`, `/storage/emulated/0/Pictures/Screenshot`, `/sdcard/DCIM/Screenshots` using `ls -lt | head -n 5`.
    2. Inspect the latest image with `view_file` to directly extract the teams, league, kickoff time, Game ID, and **all visible odds and alternative lines** (Over/Under lines, 1st Half lines, handicaps, moneyline).
    3. Note bookmaker-specific terms (e.g., "incl. overtime", "Draw No Bet", Asian lines).
- Clarify the fixture: Home team/player, Away team/player, Competition, Date, Venue.
- Identify the user's focus directive (e.g., Accumulator Anchor Mode, High-Stake Bankroll Protection, Value Hunter).
- Confirm home/away status (neutral venue matches must not use home-advantage weighting).
- Load the appropriate sport profile to configure the model, markets, and research sources.

### Step 2: Live Public Intelligence Gathering
Execute targeted web queries adapted to the sport:
- **Universal queries**:
  - `"[Team A] vs [Team B] [Sport] preview [Current Year]"`
  - `"[Team/Player] injury update news [Month Year]"`
  - `"[Team A] [Team B] odds [Competition] [Current Year]"`
- **Sport-specific queries**:
  - Football: `"[Team] xG stats"`, `"[Referee] cards per game stats"`
  - Basketball: `"[Team] offensive rating defensive rating pace"`, `"[Player] injury report"`
  - Tennis: `"[Player] serve stats surface win rate [surface]"`
  - Baseball: `"[Starting Pitcher] ERA FIP stats [Year]"`, `"[Team] bullpen ERA"`
  - Ice Hockey: `"[Team] Corsi xG 5v5 stats"`, `"[Goalie] save percentage"`
- Extract:
  - Confirmed lineup / roster availability and key absences
  - Schedule density and fatigue factors (back-to-back, travel)
  - Venue/surface/conditions impact
  - Motivation context (playoff implications, rivalry, dead rubber)

### Step 3: Statistical Sourcing (Last 5-10 Matches/Events)
Search the sport's public data sources (defined in the sport profile) for:
- Home/Player 1 recent form: scoring rate, defensive rate, key performance metrics
- Away/Player 2 recent form: same metrics
- League/tour average baselines for the sport
- Current market odds from public odds comparison pages (Oddschecker, OddsPortal, SportyBet)
- **Sport-specific advanced metrics** (see sport profile `key_metrics` list)

### Step 4: Local Mathematical Modeling
Run the local calculation script with the detected sport, format, and multi-line odds:

**Football (Poisson model — default):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport football \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_XG> --away-xg <AWAY_XG> \
  --odds-home <H_ODDS> --odds-draw <D_ODDS> --odds-away <A_ODDS> \
  --ou-odds "1.5:1.30:3.40,2.5:1.85:1.95,3.5:3.10:1.35"
```

**Basketball (FIBA / EuroLeague / VTB / 40-Min):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport basketball \
  --league-format fiba \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_PPG> --away-xg <AWAY_PPG> \
  --odds-home <H_ODDS> --odds-away <A_ODDS> \
  --ou-odds "154.5:1.43:2.65,160.5:1.80:1.91,166.5:2.40:1.50,168.5:2.70:1.41"
```

**Basketball (NBA / 48-Min):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport basketball \
  --league-format nba \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_PPG> --away-xg <AWAY_PPG> \
  --odds-home <H_ODDS> --odds-away <A_ODDS> \
  --ou-odds "215.5:1.90:1.90,220.5:2.10:1.75"
```

**Ice Hockey (Poisson with Dixon-Coles):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport ice_hockey \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_XG> --away-xg <AWAY_XG> \
  --odds-home <H_ODDS> --odds-draw <D_ODDS> --odds-away <A_ODDS>
```

**Tennis:**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport tennis \
  --home "<PLAYER_1>" --away "<PLAYER_2>" \
  --home-xg <P1_GAMES_PER_SET> --away-xg <P2_GAMES_PER_SET> \
  --odds-home <P1_ODDS> --odds-away <P2_ODDS>
```

**Table Tennis:**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport table_tennis \
  --home "<PLAYER_1>" --away "<PLAYER_2>" \
  --home-xg <P1_PPG> --away-xg <P2_PPG> \
  --odds-home <P1_ODDS> --odds-away <P2_ODDS>
```

**Baseball:**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport baseball \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_RPG> --away-xg <AWAY_RPG> \
  --odds-home <H_ODDS> --odds-away <A_ODDS>
```

**Using Attack/Defense ratings (any sport):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport <SPORT> \
  --home "<HOME>" --away "<AWAY>" \
  --home-attack <SCORING_RATE> --home-defense <CONCEDE_RATE> \
  --away-attack <SCORING_RATE> --away-defense <CONCEDE_RATE>
```

**Auditing Arbitrary Screenshot / Slip Markets (SportyBet Exotics):**
Pass any selection visible in screenshots or slips directly via `--odds-line "MARKET_NAME:ODDS"` or query model probability without odds via `--market-query "MARKET_NAME"`:
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport football \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_XG> --away-xg <AWAY_XG> \
  --odds-home <H_ODDS> --odds-draw <D_ODDS> --odds-away <A_ODDS> \
  --odds-line "1X & Under 3.5:1.55" \
  --odds-line "Away Under 1.5:1.32" \
  --odds-line "1-3 Goals:1.42" \
  --odds-line "Home Win to Nil:2.85" \
  --market-query "2-4 Goals"
```

The engine automatically parses and models:
- **Combos**: `1X & Under 3.5`, `Home Win & Over 1.5`, `BTTS Yes & Over 2.5`, `12 & Under 4.5`, etc.
- **Team Individual Totals**: `Home Over 1.5`, `Away Under 1.5`, `Home Under 0.5`.
- **Multi-Goal Bands**: `0-1 Goals`, `1-2 Goals`, `1-3 Goals`, `2-3 Goals`, `2-4 Goals`, `3-5 Goals`.
- **Win to Nil**: `Home Win to Nil`, `Away Win to Nil`.
- **Tennis & Table Tennis**: `Player 1 to win a set`, `Player 2 +1.5 sets`, `P1 -1.5 games`, `Over 3.5 sets`.
- **Basketball**: `1st Half Under 82.5`, `Home +7.5 spread`, `Away Over 78.5`.

### Step 5: De-vigging, Value (+EV), and Accumulator Anchor (AAI) Synthesis
1. **De-vigging (Market Overround)**:
   - Calculate bookmaker margin $M = \sum(1/O_i) - 1.0$.
   - Compute true vig-free market probabilities to eliminate bookmaker bias.
2. **Expected Value (+EV)**:
   - Calculate mathematical edge: $\text{Edge (\%)} = (P_{\text{model}} \times \text{Odds} - 1) \times 100$.
   - Mark as **Value Bet (+EV)** if Edge $> 3.0\%$.
3. **Accumulator Anchor Index (AAI: 0–100)**:
   - For users placing high-stake accumulators/parlays, filter to high probability floor options ($P_{\text{model}} \ge 75-80\%$).
   - Rank picks by AAI score. AAI $\ge 85$ indicates an **Elite Anchor** with deep margin protection.
   - Reject high-risk underdog plays or uncompensated low-odds road favorites from being recommended as high-stake anchors.

### Step 6: Deliver the Match Prediction Dossier
Assemble the analysis using the layout defined in `templates/dossier_template.md`:
1. **Executive Decision**: Upfront, binary PLAY or LEAVE verdict.
2. **Context, Form & Availability**: Tactical setup, starting availability, rest, and venue impact.
3. **Statistical Summary & H2H Truth**: Verified head-to-head table with past scorelines and totals.
4. **Mathematical Model & Multi-Line Table**: Full audit of bookmaker odds, devigged probabilities, EV, and AAI scores.
5. **Final Categorized Selections**:
   - 🟢 Safest Accumulator Anchor (highest AAI score, high probability floor)
   - 🟡 Value Selection (highest +EV edge)
   - 🎯 Most Probable Outcome
6. **Risk Invalidation**: Specific conditions that would nullify the statistical edge.

---

## Non-Negotiable Operational Rules

1. **Facts Only, Zero Slop & Zero Hallucination**: Every single scoring rate, advanced metric, head-to-head scoreline, and bookmaker decimal odd must be verifiable in public records or calculated directly by the local python script. Never invent or hallucinate statistics.
2. **No Emotional or Brand Bias**: Never pick a team simply because they have a bigger name or stronger reputation if their underlying metrics and travel splits argue otherwise.
3. **Accumulator Discipline Over Volume**: For high-stake accumulators, capital preservation is the absolute priority. Never recommend a volatile coin-flip or an uncompensated low-odds trap (e.g. 1.20 away moneyline with 20% upset risk) just to give a pick. If the only safe play is an alternative under/over buffer, state that with mathematical clarity.
4. **Discipline to State "LEAVE"**: If a fixture is completely unpredictable due to heavy rotation, chaotic conditions, or volatile lines, explicitly state "LEAVE / PASS" rather than guessing.
5. **Sport-Appropriate Modeling**: Respect the sport's scoring physics. Never apply Poisson to high-scoring sports (basketball, NFL) or Normal to low-scoring sports (football, hockey). Use FIBA 40-minute parameters for European/international basketball and NBA 48-minute parameters for NBA games.
