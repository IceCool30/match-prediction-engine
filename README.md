# match-prediction-engine

An autonomous sports analytics skill and quantitative prediction engine for football (soccer). Built to emulate enterprise-grade match forecasting and betting intelligence with **zero paid API fees**.

## Overview
The `match-prediction-engine` delivers rigorous match analysis, probability modeling, and expected value (+EV) identification by combining real-time public tactical intelligence with deterministic mathematical calculations.

### Core Capabilities
- **Zero Paid APIs**: Uses live public intelligence, sports databases, and open stats (FBref, Understat, Flashscore, etc.).
- **Adaptive User Directives (Never Boxed In)**:
  - **Goals & Match Flow**: Over/Under 1.5, 2.5, 3.5, 1st Half Goals.
  - **BTTS**: Both teams to score probability.
  - **Corner Markets**: Team corner averages, crossing frequency, wing overloads.
  - **Cards & Discipline**: Referee strictness, derby intensity, foul rates.
  - **Player Props**: Shots on target, anytime goalscorer, set-piece matchups.
  - **Accumulator / Parlay Anchors**: Ultra-high probability floors ($>75\%$) for multi-bet slips.
  - **Value Hunter & Underdog (+EV)**: Locating mispriced lines where public bias inflates the odds.
- **Deterministic Python Probability Model**: Implements bivariate Poisson distribution with Dixon-Coles low-score adjustments.
- **Expected Value (+EV) Detection**: Evaluates model probabilities against live bookmaker odds to locate mathematical market edges ($> 3\%$).
- **Structured Prediction Dossiers**: Generates publication-ready match briefs with tactical summaries, lineup news, underlying metrics, and risk factors.

---

## Directory Structure
```
match-prediction-engine/
├── SKILL.md                  # Complete agent operational protocol & focus modes
├── README.md                 # Project overview and usage guide
├── .gitignore
├── scripts/
│   └── poisson_model.py      # Self-contained Python calculation engine
├── templates/
│   └── dossier_template.md   # Publication format with active analytical lens
└── references/
    └── methodology.md        # Mathematical derivations and formulas
```

---

## Standalone CLI Usage

The core calculation script requires no third-party libraries (runs on standard Python 3.8+):

### 1. Using Direct Expected Goals (xG):
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

### 2. Using Attack & Defense Ratings:
```bash
python3 scripts/poisson_model.py \
  --home "Real Madrid" \
  --away "Barcelona" \
  --home-attack 2.20 \
  --home-defense 0.85 \
  --away-attack 2.10 \
  --away-defense 1.10 \
  --league-avg-home 1.52 \
  --league-avg-away 1.20
```

### 3. Output as Raw JSON:
Add the `--json` flag to integrate into databases, APIs, or automated web pipelines:
```bash
python3 scripts/poisson_model.py --home "PSG" --away "Marseille" --home-xg 2.10 --away-xg 0.90 --json
```

---

## License
MIT
