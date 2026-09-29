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

### Step 1: Intake, Sport Detection & Focus Identification
- **Detect the sport** from the teams/players mentioned, competition name, or explicit user statement.
- Clarify the fixture: Home team/player, Away team/player, Competition, Date, Venue.
- Identify the user's focus directive (e.g., general match, spread, totals, player props, accumulator anchor).
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
- Current market odds from public odds comparison pages (Oddschecker, OddsPortal)
- **Sport-specific advanced metrics** (see sport profile `key_metrics` list)

### Step 4: Local Mathematical Modeling
Run the local calculation script with the detected sport:

**Football (Poisson model — default):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport football \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_XG> --away-xg <AWAY_XG> \
  --odds-home <H_ODDS> --odds-draw <D_ODDS> --odds-away <A_ODDS>
```

**Basketball (Normal model):**
```bash
python3 /data/data/com.termux/files/home/.agents/skills/match-prediction-engine/scripts/poisson_model.py \
  --sport basketball \
  --home "<HOME_TEAM>" --away "<AWAY_TEAM>" \
  --home-xg <HOME_PPG> --away-xg <AWAY_PPG> \
  --odds-home <H_ODDS> --odds-away <A_ODDS>
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

**Custom over/under lines:**
```bash
python3 ... --ou-lines "195.5,200.5,210.5,220.5"
```

### Step 5: Value (+EV) and Risk Synthesis
- Compare the model's true probability against the bookmaker's implied probability:
  $$\text{Edge (\%)} = (\text{Model Probability} \times \text{Bookmaker Odds} - 1) \times 100$$
- If the edge is $> 3\%$, mark the selection as a **Value Bet (+EV)**.
- Align the output with the user's specific requested focus and sport-appropriate markets.

### Step 6: Deliver the Match Prediction Dossier
Assemble the analysis using the layout defined in `templates/dossier_template.md`:
1. **Match Header**: Teams/players, sport, competition, date, venue, Active Focus Lens.
2. **Context & Availability**: Sport-relevant context (tactical setup for football, pitching matchup for baseball, surface for tennis, etc.).
3. **Statistical Summary**: Table of sport-specific performance metrics.
4. **Model Output**: Objective probabilities, fair odds vs market odds for applicable markets.
5. **Categorized Recommendations**:
   - Primary Selection (safest statistical floor or user-targeted focus)
   - Value Selection (+EV pick where odds favor the punter)
   - Probable Score/Outcome
6. **Risk Invalidation**: The exact condition that would nullify the logic.

---

## Non-Negotiable Operational Rules

1. **No Emotional or Brand Bias**: Never pick a team simply because they have a bigger name or stronger brand if their rolling form metrics tell a different story.
2. **No Invented Numbers**: All scoring rates, advanced metrics, and odds must come from actual search results or calculated directly by the script.
3. **Account for Motivation**: Beware of dead rubbers, end-of-season rotation, exhibition matches, or situations where a team/player has already secured qualification.
4. **Discipline Over Volume**: If a match is completely unpredictable due to high rotation, chaotic conditions, or insufficient data, explicitly state "Pass / Low Stake" rather than forcing a high-confidence pick.
5. **Sport-Appropriate Analysis**: Never apply football-specific concepts (corners, BTTS, clean sheets) to sports where they don't exist. Use the sport profile to determine which markets and metrics are valid.
6. **Model Selection Integrity**: Use Poisson for low/mid-scoring discrete events, Normal for high-scoring continuous-like distributions. Never force the wrong model onto a sport.
