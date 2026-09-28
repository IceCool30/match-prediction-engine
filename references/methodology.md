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
