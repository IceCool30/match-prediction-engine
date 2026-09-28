# match-prediction-engine

A multi-sport autonomous analytics skill and quantitative prediction engine. Built to deliver enterprise-grade match forecasting and betting intelligence across **11 sports** with **zero paid API fees**.

## Supported Sports

| Sport | Model | Scoring Unit | Key Sources |
|-------|-------|-------------|-------------|
| ⚽ Football (Soccer) | Poisson + Dixon-Coles | Goals | FBref, Understat, WhoScored |
| 🏀 Basketball | Normal (Gaussian) | Points | Basketball Reference, NBA Stats |
| 🏒 Ice Hockey | Poisson + Dixon-Coles | Goals | Natural Stat Trick, MoneyPuck |
| 🎾 Tennis | Poisson | Games | Tennis Abstract, ATP/WTA Tour |
| 🏓 Table Tennis | Poisson | Points | ITTF, Flashscore |
| ⚾ Baseball | Poisson | Runs | Baseball Reference, FanGraphs |
| 🏈 American Football | Normal (Gaussian) | Points | Pro Football Reference, ESPN |
| 🏉 Rugby Union | Normal (Gaussian) | Points | ESPN Scrum, World Rugby |
| 🤾 Handball | Poisson | Goals | EHF, IHF |
| 🏐 Volleyball | Poisson | Sets | FIVB, Flashscore |
| 🏏 Cricket | Normal (Gaussian) | Runs | ESPNcricinfo, Cricbuzz |

## Overview

The `match-prediction-engine` delivers rigorous match analysis, probability modeling, and expected value (+EV) identification by combining real-time public intelligence with deterministic mathematical calculations.

### Core Capabilities
- **Zero Paid APIs**: Uses live public intelligence, sports databases, and open stats.
- **Adaptive Sport Detection**: Automatically configures model type, markets, and metrics per sport.
- **Dual Mathematical Models**:
  - **Poisson + Dixon-Coles**: For low/mid-scoring discrete-event sports (football, hockey, baseball)
  - **Normal (Gaussian)**: For high-scoring sports (basketball, American football, rugby)
- **Sport-Conditional Markets**: Only outputs markets that exist for the sport — no BTTS for tennis, no draws for basketball.
- **Expected Value (+EV) Detection**: Evaluates model probabilities against live bookmaker odds to locate mathematical market edges (> 3%).
- **Structured Prediction Dossiers**: Generates publication-ready match briefs with sport-appropriate metrics and risk factors.
- **Backward Compatible**: All existing football commands work unchanged.

---

## Directory Structure
```
match-prediction-engine/
├── SKILL.md                    # Agent operational protocol & multi-sport workflow
├── README.md                   # This file
├── .gitignore
├── scripts/
│   ├── poisson_model.py        # Multi-sport calculation engine (Poisson + Normal)
│   └── sport_profiles.py       # Sport configuration registry (11 sports)
├── templates/
│   └── dossier_template.md     # Sport-neutral publication format
└── references/
    └── methodology.md          # Mathematical derivations (Poisson, Normal, Dixon-Coles, +EV)
```

---

## Standalone CLI Usage

The core calculation script requires no third-party libraries (runs on standard Python 3.8+).

### List All Supported Sports
```bash
python3 scripts/poisson_model.py --list-sports
```

### Football (Default — Backward Compatible)
```bash
python3 scripts/poisson_model.py \
  --home "Arsenal" \
  --away "Chelsea" \
  --home-xg 1.85 \
  --away-xg 1.15 \
  --odds-home 1.70 \
  --odds-draw 3.80 \
  --odds-away 4.50 \
  --odds-o25 1.75 \
  --odds-btts-yes 1.75
```

### Basketball
```bash
python3 scripts/poisson_model.py \
  --sport basketball \
  --home "Lakers" \
  --away "Celtics" \
  --home-xg 112.5 \
  --away-xg 108.0 \
  --odds-home 1.90 \
  --odds-away 1.95
```

### Ice Hockey
```bash
python3 scripts/poisson_model.py \
  --sport ice_hockey \
  --home "Rangers" \
  --away "Bruins" \
  --home-xg 3.2 \
  --away-xg 2.7 \
  --odds-home 2.10 \
  --odds-draw 3.60 \
  --odds-away 3.20
```

### Tennis
```bash
python3 scripts/poisson_model.py \
  --sport tennis \
  --home "Djokovic" \
  --away "Alcaraz" \
  --home-xg 5.8 \
  --away-xg 5.2 \
  --odds-home 2.20 \
  --odds-away 1.72
```

### Table Tennis
```bash
python3 scripts/poisson_model.py \
  --sport table_tennis \
  --home "Ma Long" \
  --away "Fan Zhendong" \
  --home-xg 11.2 \
  --away-xg 10.5
```

### Baseball
```bash
python3 scripts/poisson_model.py \
  --sport baseball \
  --home "Yankees" \
  --away "Red Sox" \
  --home-xg 4.8 \
  --away-xg 4.2 \
  --odds-home 1.65 \
  --odds-away 2.30
```

### American Football
```bash
python3 scripts/poisson_model.py \
  --sport american_football \
  --home "Chiefs" \
  --away "Bills" \
  --home-xg 27.5 \
  --away-xg 24.0 \
  --odds-home 1.55 \
  --odds-away 2.50
```

### Using Attack & Defense Ratings (Any Sport)
```bash
python3 scripts/poisson_model.py \
  --sport football \
  --home "Real Madrid" \
  --away "Barcelona" \
  --home-attack 2.20 \
  --home-defense 0.85 \
  --away-attack 2.10 \
  --away-defense 1.10
```

### Custom Over/Under Lines
```bash
python3 scripts/poisson_model.py \
  --sport basketball \
  --home "Warriors" \
  --away "Suns" \
  --home-xg 115 \
  --away-xg 112 \
  --ou-lines "215.5,220.5,225.5,230.5"
```

### JSON Output
Add `--json` for raw JSON output suitable for databases, APIs, or pipelines:
```bash
python3 scripts/poisson_model.py \
  --sport baseball \
  --home "Dodgers" --away "Padres" \
  --home-xg 5.1 --away-xg 3.8 \
  --json
```

---

## License
MIT
