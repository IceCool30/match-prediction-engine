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

