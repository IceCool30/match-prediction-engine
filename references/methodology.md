# Mathematical Methodology: Multi-Sport Probability Modeling

This document describes the mathematical foundations behind the match-prediction-engine's multi-sport probability and value models.

---

## 1. Model Selection by Sport

The engine uses two primary probability models, selected automatically based on the sport's scoring characteristics:

| Model | When Used | Scoring Type | Sports |
|-------|-----------|-------------|--------|
| **Poisson** (+ optional Dixon-Coles) | Low-to-medium discrete scoring events | Goals, runs, sets, games | Football, Ice Hockey, Baseball, Tennis, Table Tennis, Handball, Volleyball |
| **Normal (Gaussian)** | High-scoring continuous-like distributions | Points, runs (high-volume) | Basketball, American Football, Rugby, Cricket |

### Why Two Models?

The Poisson distribution models **discrete, rare events** — it works brilliantly when teams score 0-5 times per match (football, hockey). But for basketball where teams score 90-130 points, computing a 200×200 Poisson matrix becomes computationally expensive and statistically unnecessary. The Normal distribution provides accurate, efficient probability estimation for high-volume scoring via its continuous approximation.

---

## 2. The Poisson Model

### Fundamental Assumption
A sporting event can be modeled as two independent Poisson processes. The number of scoring events by team $i$ against team $j$ follows a Poisson distribution with parameter $\lambda_i$:

$$P(X = k) = \frac{\lambda^k e^{-\lambda}}{k!}$$

where $\lambda$ represents the expected number of scoring events (goals, runs, etc.).

### Attacking and Defensive Strength Decomposition
To determine $\lambda$ (home expected scoring) and $\mu$ (away expected scoring):

1. **Home Attack Strength ($AS_H$)**:
   $$AS_H = \frac{\text{Home Scoring Rate by Team } H}{\text{League Average Home Scoring Rate}}$$

2. **Away Defense Strength ($DS_A$)**:
   $$DS_A = \frac{\text{Away Conceding Rate by Team } A}{\text{League Average Home Scoring Rate}}$$

3. **Home Expected Scoring ($\lambda$)**:
   $$\lambda = AS_H \times DS_A \times \text{League Average Home Scoring}$$

4. **Away Expected Scoring ($\mu$)**:
   $$\mu = AS_A \times DS_H \times \text{League Average Away Scoring}$$

This multiplicative structure is **universal across sports** — it applies to goals (football, hockey, handball), runs (baseball), points per game averages, and any rate-based scoring metric relative to a league baseline.

### Scoreline Probability Matrix
For a Poisson-model sport with maximum score $N$, the engine builds an $(N+1) \times (N+1)$ matrix where entry $(h, a)$ represents the probability of home team scoring $h$ and away team scoring $a$:

$$P(H=h, A=a) = P(H=h; \lambda) \times P(A=a; \mu) \times \tau(h, a)$$

where $\tau$ is the Dixon-Coles adjustment (see below).

### Default Maximum Scores by Sport
| Sport | Max Score | Rationale |
|-------|-----------|-----------|
| Football | 10 | Matches exceeding 10 goals are astronomically rare |
| Ice Hockey | 12 | Slightly higher baseline scoring than football |
| Baseball | 20 | Rare for team totals to exceed 15 runs |
| Handball | 50 | High-scoring but discrete |
| Tennis | 13 | Games per set, including tiebreak |
| Table Tennis | 15 | Points per game with deuce potential |
| Volleyball | 5 | Best-of-5 sets |

---

## 3. Dixon-Coles Low-Score Adjustment

### Origin and Applicability
Mark Dixon and Stuart Coles (1997) observed that **football (soccer)** matches show mild structural dependence at low scorelines (0-0, 1-0, 0-1, 1-1) that pure independent Poisson underestimates or overestimates.

They introduced a correction factor $\tau(x, y; \lambda, \mu, \rho)$:

$$\tau(x, y) = \begin{cases}
1 - \lambda \mu \rho & \text{if } x = 0, y = 0 \\
1 + \mu \rho & \text{if } x = 1, y = 0 \\
1 + \lambda \rho & \text{if } x = 0, y = 1 \\
1 - \rho & \text{if } x = 1, y = 1 \\
1 & \text{otherwise}
\end{cases}$$

### Rho ($\rho$) Values by Sport
| Sport | $\rho$ | Rationale |
|-------|--------|-----------|
| Football (Soccer) | $-0.11$ | Empirically calibrated from European league data |
| Ice Hockey | $-0.08$ | Similar low-scoring dynamics, slightly less correlated |
| All other sports | $0.0$ (disabled) | Either no low-score dependence or too high-scoring for the adjustment to be meaningful |

The adjusted probability of score $(x, y)$ is:
$$P(X=x, Y=y) = \tau(x, y) \cdot P(X=x; \lambda) \cdot P(Y=y; \mu)$$

---

## 4. The Normal (Gaussian) Model

### When Poisson Breaks Down
For sports where teams score 80-200+ points per match (basketball, American football), the Poisson distribution's discrete nature becomes impractical:
- Matrix dimensions would need to be 200+ × 200+ (40,000+ cells)
- The Central Limit Theorem tells us that for large $\lambda$, Poisson converges to Normal anyway

### Model Structure
Each team's scoring follows a Normal distribution:
- Home: $H \sim N(\mu_H, \sigma_H^2)$
- Away: $A \sim N(\mu_A, \sigma_A^2)$

The **margin of victory** (home perspective) follows:
$$M = H - A \sim N(\mu_H - \mu_A, \sigma_H^2 + \sigma_A^2 + 2\rho_{HA}\sigma_H\sigma_A)$$

The **total scoring** follows:
$$T = H + A \sim N(\mu_H + \mu_A, \sigma_H^2 + \sigma_A^2 + 2\rho_{HA}\sigma_H\sigma_A)$$

where $\rho_{HA} \approx -0.1$ is a mild negative correlation between opposing team totals (better defense tends to depress both scores slightly).

### Win Probabilities
For sports with no draws:
$$P(\text{Home Win}) = P(M > 0) = 1 - \Phi\left(\frac{0 - \mu_M}{\sigma_M}\right)$$

For sports with draws (using a draw band $\pm 0.5$):
$$P(\text{Home Win}) = 1 - \Phi\left(\frac{0.5 - \mu_M}{\sigma_M}\right)$$
$$P(\text{Away Win}) = \Phi\left(\frac{-0.5 - \mu_M}{\sigma_M}\right)$$
$$P(\text{Draw}) = 1 - P(\text{Home}) - P(\text{Away})$$

### Standard Deviation Estimation
When explicit standard deviations are not provided, the engine defaults to $\sigma \approx 0.12 \times \mu$ (12% of the mean), with a minimum floor of 3.0 points. This is empirically reasonable for most team sports.

### Spread / Handicap Calculation
$$P(\text{Home covers line } L) = P(M > -L) = 1 - \Phi\left(\frac{-L - \mu_M}{\sigma_M}\right)$$

### Over/Under Calculation
$$P(\text{Over line } L) = P(T > L) = 1 - \Phi\left(\frac{L - \mu_T}{\sigma_T}\right)$$

---

## 5. Market Conversion and Expected Value (+EV)

These formulas are **universal across all sports and all betting markets**.

### Fair Odds
Fair odds represent the inverse of true probability with zero bookmaker margin:
$$\text{Fair Odds} = \frac{1}{P(\text{Outcome})}$$

### Bookmaker Implied Probability
$$\text{Implied Probability} = \frac{1}{\text{Bookmaker Decimal Odds}}$$

### Expected Value (+EV)
A bet has positive expected value if the model's probability suggests a long-term edge:
$$\text{EV (\%)} = \left( P_{\text{model}} \times \text{Odds}_{\text{bookmaker}} - 1 \right) \times 100$$

A pick is classified as a **value bet** when $\text{EV} \ge 3\%$.

---

## 6. Sport-Specific Derived Markets

### Markets Available by Model Type

| Market | Poisson (Low-Score) | Normal (High-Score) | Notes |
|--------|:---:|:---:|-------|
| Win/Loss/Draw (1X2) | ✅ | ✅ | Draw only for sports with draws |
| Moneyline (no draw) | ✅ | ✅ | Re-normalized for no-draw sports |
| Over/Under | ✅ | ✅ | Sport-specific lines |
| Spread / Handicap | ✅ | ✅ | From margin distribution |
| BTTS | ✅ | ❌ | Only low-scoring sports (football, hockey, baseball) |
| Clean Sheet / Shutout | ✅ | ❌ | Only meaningful in low-scoring sports |
| Double Chance | ✅ | ✅ | Only for sports with draws |
| Draw No Bet | ✅ | ✅ | Only for sports with draws |
| Exact Scoreline | ✅ | ❌ | Matrix-derived, Poisson only |

---

## 7. Proportional De-vigging (Margin Stripping)

Bookmaker odds include an artificial profit margin (the "vig" or overround). To assess true market expectations and avoid false value signals, the engine applies proportional margin stripping:

### Overround / Total Margin
Given a full market with decimal odds $O_1, O_2, \dots, O_k$:
$$\text{Margin (\%)} = \left( \sum_{i=1}^k \frac{1}{O_i} - 1 \right) \times 100$$

### True De-vigged Probability
The fair probability implied by the bookmaker market after stripping the vig is:
$$P_{\text{devig}, i} = \frac{\frac{1}{O_i}}{\sum_{j=1}^k \frac{1}{O_j}}$$

### Fair Market Odds
$$\text{Odds}_{\text{fair}, i} = \frac{1}{P_{\text{devig}, i}}$$

The model compares its own independently derived probability $P_{\text{model}}$ against both raw bookmaker odds (for bet payout EV) and de-vigged market probability $P_{\text{devig}}$ (for true informational edge).

---

## 8. Accumulator Anchor Index (AAI: 0–100)

Single-bet value hunting (+EV) is structurally distinct from Accumulator / Parlay Building. In single bets, a 3.50 underdog with +5% EV is an acceptable mathematical play. In a **high-stake accumulator**, an underdog with a 70% failure rate will destroy the ticket.

The engine uses the **Accumulator Anchor Index (AAI)** to evaluate parlay suitability:

### 1. Probability Threshold Gate
If $P_{\text{model}} < 0.65$, $\text{AAI} = 0.0$ (`UNSUITABLE`). Parlay anchors require high survival floors.

### 2. Base Probability Score
$$S_{\text{base}} = \begin{cases}
40.0 + \frac{P - 0.65}{0.10} \times 25.0 & \text{if } 0.65 \le P < 0.75 \\
65.0 + \frac{P - 0.75}{0.10} \times 23.0 & \text{if } 0.75 \le P < 0.85 \\
88.0 + \min\left(\frac{P - 0.85}{0.10} \times 12.0, 12.0\right) & \text{if } P \ge 0.85
\end{cases}$$

### 3. Margin Buffer Bonus
Lines situated deep in the distribution tails carry statistical buffer against variance:
$$Z_{\text{buffer}} = \frac{|\text{Line} - \mu|}{\sigma}$$
$$B_{\text{buffer}} = \min\left(\frac{Z_{\text{buffer}}}{1.5}, 1.0\right) \times 8.0$$

### 4. Market EV Adjustment
$$A_{\text{EV}} = \begin{cases}
\min(\text{EV} \times 0.4, 8.0) & \text{if } \text{EV} > 0 \\
\max(-10.0, (\text{EV} + 5.0) \times 0.5) & \text{if } \text{EV} < -5.0 \\
0.0 & \text{otherwise}
\end{cases}$$

### 5. Final Score & Classification
$$\text{AAI} = \text{clamp}(S_{\text{base}} + B_{\text{buffer}} + A_{\text{EV}}, 0, 100)$$

| AAI Score | Classification | Action for High-Stake Accumulators |
|:---:|:---|:---|
| **85 – 100** | 🟢 **ELITE ANCHOR** | Top-tier capital protection; statistical floor $\ge 80\%$, verified buffer. Approved for maximum stake. |
| **72 – 84** | 🟢 **STRONG ANCHOR** | Reliable probability floor $\ge 75\%$, positive or fair market expectancy. |
| **60 – 71** | 🟡 **VIABLE LEG** | Acceptable for low/moderate stake multis, but carries measurable tail risk. |
| **< 60** | 🔴 **SPECULATIVE** | Reject as parlay anchor. High risk of ticket bust. |

---

## 9. Multi-Format Basketball Modeling

Basketball cannot be treated with a single 48-minute baseline:

| Format | Regulation Time | Typical Total Points | Team PPG Average | Over/Under Baseline Lines | Key Competitions |
|:---|:---:|:---:|:---:|:---:|:---|
| **NBA** | 48 mins (4×12) | 215 – 230 | 110 – 115 | `195.5 – 225.5` | NBA, NBA G-League |
| **FIBA / Euro** | 40 mins (4×10) | 150 – 165 | 75 – 83 | `148.5 – 172.5` | EuroLeague, EuroCup, VTB, ACB Spain, BBL, Olympics |
| **NCAA (CBB)** | 40 mins (2×20) | 135 – 148 | 67 – 74 | `132.5 – 152.5` | NCAA Men's College Basketball |

The engine accepts `--league-format fiba` (or aliases `euroleague`, `vtb`) to instantly load FIBA parameters, preventing massive over-estimation of totals.

---

## 10. Derivative Period Splits (1st Half / 2nd Half)

Empirical period scoring distributions differ from simple halves:
* **Football (Soccer):**
  * 1st Half: $\approx 45\%$ of full-time xG ($xG_{1H} = 0.45 \times xG_{FT}$)
  * 2nd Half: $\approx 55\%$ of full-time xG (substitutions, tactical opening, late fatigue)
* **Basketball:**
  * 1st Half: $\approx 48.5\%$ of full-time points
  * Standard deviation: $\sigma_{1H} = \sigma_{FT} \times \sqrt{0.485} \approx 0.70 \times \sigma_{FT}$
  * 2nd Half: $\approx 51.5\%$ of full-time points (due to late-game tactical intentional fouls and free throw frequency)

---

## 11. Tennis Markov Probability Modeling

Tennis scoring possesses a hierarchical nested structure: points $\to$ games $\to$ sets $\to$ match. Computing match odds from game win probabilities requires Markov combinatorics rather than naive independent counting.

### Game-to-Set Closed-Form Markov Model
Let $p$ be the probability that Player 1 wins a game on court. A set is won by the first player to reach 6 games with a 2-game advantage, or at 7-6 via tiebreak:

1. **Winning before 5–5 (6–0, 6–1, 6–2, 6–3, 6–4)**:
   $$P_{\text{win } < 5-5} = \sum_{k=0}^4 \binom{5 + k}{k} p^6 (1 - p)^k$$

2. **Reaching 5–5**:
   $$P_{5-5} = \binom{10}{5} p^5 (1 - p)^5$$

3. **Outcome from 5–5**:
   From 5–5, Player 1 wins the set directly at 7–5 with probability $p^2$, Player 2 wins at 5–7 with $(1 - p)^2$, and the set proceeds to a 6–6 tiebreak with probability $2 p (1 - p)$.

4. **Tiebreak Probability**:
   Modeling the 7-point tiebreak with slight server advantage compression:
   $$p_{tb} \approx \frac{p^{1.1}}{p^{1.1} + (1 - p)^{1.1}}$$

5. **Overall Set Win Probability ($P_{\text{set}}$)**:
   $$P_{\text{set}} = P_{\text{win } < 5-5} + P_{5-5} \left[ p^2 + 2p(1 - p) p_{tb} \right]$$

### Match Set-Score Distribution (Best-of-3)
* **2–0**: $P(2-0) = P_{\text{set}}^2$
* **2–1**: $P(2-1) = 2 \cdot P_{\text{set}}^2 (1 - P_{\text{set}})$
* **0–2**: $P(0-2) = (1 - P_{\text{set}})^2$
* **1–2**: $P(1-2) = 2 \cdot (1 - P_{\text{set}})^2 P_{\text{set}}$
* **Match Win**: $P(\text{Match Win}) = P(2-0) + P(2-1)$
* **Player to Win At Least 1 Set**:
  $$P(\text{P1 Win }\ge 1\text{ Set}) = 1 - P(0-2) = P(2-0) + P(2-1) + P(1-2)$$

### Best-of-5 Matches (Grand Slams)
* **3–0**: $P(3-0) = P_{\text{set}}^3$
* **3–1**: $P(3-1) = 3 P_{\text{set}}^3 (1 - P_{\text{set}})$
* **3–2**: $P(3-2) = 6 P_{\text{set}}^3 (1 - P_{\text{set}})^2$
* Symmetric formulas apply for Player 2.

### Set Handicaps & Game Margins
* **Set Handicap (+1.5)**: Equivalent to winning $\ge 1$ set ($1 - P(0-2)$ in Bo3).
* **Set Handicap (-1.5)**: Equivalent to winning in straight sets ($P(2-0)$ in Bo3).
* **Total Games Mixture Model**: Expected games per set are conditioned on scorelines ($\approx 8.3$ in straight sets, $\approx 9.6$ in deciders), yielding precise Over/Under game lines.

---

## 12. Table Tennis Deuce-Adjusted Markov Point-to-Game Model

Table tennis games are played to 11 points, requiring a 2-point margin. At 10–10, play enters deuce.

### Closed-Form Game Probability
Let $p = \frac{\lambda_{P1}}{\lambda_{P1} + \lambda_{P2}}$ be the point-win probability for Player 1.

1. **Winning before Deuce (11–0 through 11–9)**:
   $$P_{\text{win } < 10-10} = \sum_{k=0}^9 \binom{10 + k}{k} p^{11} (1 - p)^k$$

2. **Reaching Deuce (10–10)**:
   $$P_{10-10} = \binom{20}{10} p^{10} (1 - p)^{10}$$

3. **Deuce Resolution via Infinite Absorbing Markov Chain**:
   From 10–10, Player 1 wins by scoring 2 consecutive points ($p^2$), Player 2 wins with $(1 - p)^2$, and deuce repeats with $2 p (1 - p)$. Summing the infinite geometric series:
   $$P(\text{Win} \mid \text{Deuce}) = \sum_{n=0}^{\infty} p^2 [2p(1 - p)]^n = \frac{p^2}{1 - 2p(1 - p)} = \frac{p^2}{p^2 + (1 - p)^2}$$

4. **Total Game Win Probability ($P_{\text{game}}$)**:
   $$P_{\text{game}} = P_{\text{win } < 10-10} + P_{10-10} \times \frac{p^2}{p^2 + (1 - p)^2}$$

### Best-of-5 Match Combinatorics
Matches are first to 3 games:
* $P(3-0) = P_{\text{game}}^3$
* $P(3-1) = 3 P_{\text{game}}^3 (1 - P_{\text{game}})$
* $P(3-2) = 6 P_{\text{game}}^3 (1 - P_{\text{game}})^2$
* Set Handicap $\pm 1.5$ and $\pm 2.5$ directly sum these disjoint exact scoreline paths.

---

## 13. Football Joint Distributions & Exotic Market Combinatorics

Bookmakers offer intricate exotic combinations (e.g. SportyBet combos). Because the engine computes the full $(N+1) \times (N+1)$ Dixon-Coles scoreline matrix $P(H=h, A=a)$, all derived markets are calculated with mathematical exactness:

### Double Chance & Over/Under Combos
Let $S_{1X} = \{(h, a) \mid h \ge a\}$, $S_{X2} = \{(h, a) \mid a \ge h\}$, $S_{12} = \{(h, a) \mid h \ne a\}$.
For any goal line $L$:
$$P(\text{1X \& Under } L) = \sum_{(h, a) \in S_{1X}, h+a < L} P(H=h, A=a)$$
$$P(\text{1X \& Over } L) = \sum_{(h, a) \in S_{1X}, h+a > L} P(H=h, A=a)$$
$$P(\text{X2 \& Under } L) = \sum_{(h, a) \in S_{X2}, h+a < L} P(H=h, A=a)$$
$$P(\text{X2 \& Over } L) = \sum_{(h, a) \in S_{X2}, h+a > L} P(H=h, A=a)$$

### Match Result & Both Teams to Score (1X2 & BTTS)
$$P(\text{Home Win \& BTTS Yes}) = \sum_{h > a, a \ge 1} P(H=h, A=a)$$
$$P(\text{Home Win \& BTTS No}) = \sum_{h \ge 1} P(H=h, A=0)$$

### Win to Nil
$$P(\text{Home Win to Nil}) = \sum_{h=1}^N P(H=h, A=0)$$
$$P(\text{Away Win to Nil}) = \sum_{a=1}^N P(H=0, A=a)$$

### Multi-Goal Bands
For any band $[L_{\min}, L_{\max}]$:
$$P(\text{Goals } L_{\min}\text{--}L_{\max}) = \sum_{t = L_{\min}}^{L_{\max}} \left[ \sum_{h + a = t} P(H=h, A=a) \right]$$
Common bands calculated: `0-1`, `1-2`, `1-3`, `2-3`, `2-4`, `2-5`, `3-4`, `3-5`, `4-6`, `7+`.

### Team Individual Totals
$$P(\text{Home Over } L) = \sum_{h > L} P(H=h) = 1 - \sum_{h \le \lfloor L \rfloor} P(H=h)$$
$$P(\text{Away Under } L) = \sum_{a < L} P(A=a) = \sum_{a \le \lfloor L \rfloor} P(A=a)$$

---

## 14. Universal Market Matcher & Arbitrary Query Resolution Engine

To support real-time ticket and screenshot auditing from bookmakers like SportyBet, the engine incorporates `match_arbitrary_market(query, odds, probabilities, sport)`.

### Resolution Pipeline
1. **Query Normalization**: Standardizes punctuation, whitespace, and team alias identifiers (`home`, `away`, `1`, `2`, `x`, team names).
2. **Regex Parsing**: Maps natural queries (e.g. `"1X & Under 3.5"`, `"Away Under 1.5"`, `"P1 to win a set"`, `"2-3 Goals"`, `"P2 +1.5 sets"`) to deterministic probability functions.
3. **Quantitative Metrics Generation**:
   * Evaluates exact model probability $P_{\text{model}}$
   * Computes fair odds: $\text{Odds}_{\text{fair}} = 1 / P_{\text{model}}$
   * If bookmaker odds are supplied:
     * Computes implied probability $P_{\text{implied}} = 1 / \text{Odds}_{\text{mkt}}$
     * Computes expected value: $\text{EV (\%)} = (P_{\text{model}} \times \text{Odds}_{\text{mkt}} - 1) \times 100$
     * Calculates the Accumulator Anchor Index (AAI: 0–100)
4. **Anchor Promotion**: Audited selections with high probability floors ($P \ge 75\%$) and elite AAI scores ($\ge 85$) compete alongside standard lines for the primary accumulator recommendation, ensuring users receive the mathematically safest possible ticket leg.


