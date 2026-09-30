# Match Prediction Dossier: {HOME_TEAM} vs {AWAY_TEAM}

**Sport:** {SPORT_NAME}  
**Competition:** {COMPETITION}  
**Date & Kickoff:** {MATCH_DATE} {KICKOFF_TIME}  
**Venue:** {VENUE}  
**Active Analytical Lens:** {ACTIVE_FOCUS_LENS} *(e.g., General Match Overview, Spread/Handicap, Total Points, Player Props, Accumulator Anchor)*

---

## 1. Context, Form & Availability

- **{HOME_TEAM} Context:** {HOME_CONTEXT} (Form: {HOME_FORM_LAST_5_10})
  - Confirmed / Probable Absences: {HOME_ABSENCES}
  - Tactical / Strategic Tendency: {HOME_TENDENCY}
- **{AWAY_TEAM} Context:** {AWAY_CONTEXT} (Form: {AWAY_FORM_LAST_5_10})
  - Confirmed / Probable Absences: {AWAY_ABSENCES}
  - Tactical / Strategic Tendency: {AWAY_TENDENCY}
- **Schedule, Rest & Motivation:** {REST_MOTIVATION_NOTES}
- **Venue / Conditions Factor:** {VENUE_CONDITIONS} *(e.g., home court/field advantage, surface type, altitude, weather, neutral site)*

---

## 2. Statistical & Underlying Metrics (Last 5-10 Matches)

| Metric | {HOME_TEAM} (Home) | {AWAY_TEAM} (Away) |
| :--- | :--- | :--- |
| **Primary Scoring Rate** | {HOME_SCORING_RATE} {SCORING_UNIT}/game | {AWAY_SCORING_RATE} {SCORING_UNIT}/game |
| **Conceding Rate** | {HOME_CONCEDING_RATE} {SCORING_UNIT}/game | {AWAY_CONCEDING_RATE} {SCORING_UNIT}/game |
| **Key Advanced Metric 1** | {HOME_ADV_METRIC_1} | {AWAY_ADV_METRIC_1} |
| **Key Advanced Metric 2** | {HOME_ADV_METRIC_2} | {AWAY_ADV_METRIC_2} |
| **Key Advanced Metric 3** | {HOME_ADV_METRIC_3} | {AWAY_ADV_METRIC_3} |
| **Specialized Market Metric** | {HOME_SPECIALIZED_STAT} | {AWAY_SPECIALIZED_STAT} |

*Advanced metrics are sport-specific. Examples: xG/xGA (football/hockey), ORtg/DRtg (basketball), ERA/FIP (baseball), Service game win % (tennis), Set win rate (volleyball/table tennis).*

---

## 3. Mathematical Model Output

**Model Used:** {MODEL_TYPE} *(Bivariate Poisson + Dixon-Coles / Standard Poisson / Normal Distribution)*  
*Calculated with zero emotional bias based on adjusted offensive and defensive ratings.*

### Match Result & Market De-vigging

*Bookmaker Overround / Margin:* `{VIG_PERCENT}%`

| Market | Outcome | Model Probability | Fair Odds | Market Odds | De-vigged Market Prob | Expected Value (+EV) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **{RESULT_MARKET}** | {HOME_TEAM} Win | {P_HOME}% | {FAIR_HOME} | {MKT_HOME} | {DEVIG_HOME}% | {EV_HOME}% |
| **{RESULT_MARKET}** | {DRAW_OR_NA} | {P_DRAW}% | {FAIR_DRAW} | {MKT_DRAW} | {DEVIG_DRAW}% | {EV_DRAW}% |
| **{RESULT_MARKET}** | {AWAY_TEAM} Win | {P_AWAY}% | {FAIR_AWAY} | {MKT_AWAY} | {DEVIG_AWAY}% | {EV_AWAY}% |

### Audited Over/Under {SCORING_UNIT} & Accumulator Anchor Audit

| Line | Over Prob | Over Odds | Over EV | Under Prob | Under Odds | Under EV | Accumulator Anchor Index (AAI) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **{OU_LINE_1}** | {P_OVER_1}% | {ODDS_O1} | {EV_O1}% | {P_UNDER_1}% | {ODDS_U1} | {EV_U1}% | {AAI_1} |
| **{OU_LINE_2}** | {P_OVER_2}% | {ODDS_O2} | {EV_O2}% | {P_UNDER_2}% | {ODDS_U2} | {EV_U2}% | {AAI_2} |
| **{OU_LINE_3}** | {P_OVER_3}% | {ODDS_O3} | {EV_O3}% | {P_UNDER_3}% | {ODDS_U3} | {EV_U3}% | {AAI_3} |

### Spread / Handicap

| Line | Cover Probability | Fair Odds |
| :--- | :--- | :--- |
| {HOME_TEAM} {SPREAD_1} | {P_SPREAD_1}% | {FAIR_SPREAD_1} |
| {HOME_TEAM} {SPREAD_2} | {P_SPREAD_2}% | {FAIR_SPREAD_2} |
| {HOME_TEAM} {SPREAD_3} | {P_SPREAD_3}% | {FAIR_SPREAD_3} |

<!-- Include BTTS section only for football, ice hockey, baseball, handball -->
### Both Teams to Score *(if applicable)*

| Outcome | Model Probability | Fair Odds | Market Odds | EV |
| :--- | :--- | :--- | :--- | :--- |
| BTTS Yes | {P_BTTS_YES}% | {FAIR_BTTS_YES} | {MKT_BTTS_YES} | {EV_BTTS_YES}% |
| BTTS No | {P_BTTS_NO}% | {FAIR_BTTS_NO} | {MKT_BTTS_NO} | {EV_BTTS_NO}% |

<!-- Include top scorelines for Poisson-model sports only -->
### Top Modeled Exact Scorelines *(Poisson model sports)*

1. **{SCORE_1}** ({P_SCORE_1}%)
2. **{SCORE_2}** ({P_SCORE_2}%)
3. **{SCORE_3}** ({P_SCORE_3}%)

---

## 4. Final Categorized Selections

### 🟢 Safest Accumulator Anchor (High-Stake Parlay Leg)
- **Selection:** `{PRIMARY_PICK}`
- **Market:** `{PRIMARY_MARKET}`
- **Indicative Odds:** `{PRIMARY_ODDS}`
- **Survival Probability:** `{PRIMARY_PROB}%`
- **Accumulator Anchor Index (AAI):** `{AAI_SCORE}/100 ({AAI_TIER})`
- **Analytical Rationale:** {PRIMARY_RATIONALE}

### 🟡 Value Selection (+EV / Mispriced Market)
- **Selection:** `{VALUE_PICK}`
- **Market:** `{VALUE_MARKET}`
- **Indicative Odds:** `{VALUE_ODDS}`
- **Market Edge:** `{VALUE_EDGE}% edge against market price`
- **Analytical Rationale:** {VALUE_RATIONALE}

### 🎯 Most Probable Outcome / Scoreline
- **Prediction:** `{OUTCOME_PICK}` ({OUTCOME_PROB}%)

---

## 5. Risk Factors & Invalidation Checklist
- **Key Vulnerability:** {KEY_RISK_SCENARIO}
- **Invalidation Condition:** {INVALIDATION_TRIGGER} *(e.g., late lineup change, pitcher scratch, key player ruled out, weather shift, venue change)*
