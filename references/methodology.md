# Mathematical Methodology: Poisson Distribution & Dixon-Coles in Soccer Modeling

## 1. The Fundamental Poisson Assumption
A soccer match can be modeled as two independent Poisson processes occurring over 90 minutes. The number of goals scored by team $i$ against team $j$ follows a Poisson distribution with parameter $\lambda_i$:

$$P(X = k) = \frac{\lambda^k e^{-\lambda}}{k!}$$

where $\lambda$ represents the expected number of goals.

### Attacking and Defensive Strength
To determine $\lambda$ for both home and away teams:

1. **Home Attack Strength ($AS_H$)**:
   $$AS_H = \frac{\text{Home Goals Scored by Team } H / \text{Home Games Played}}{\text{League Average Home Goals Scored per Game}}$$

2. **Away Defense Strength ($DS_A$)**:
   $$DS_A = \frac{\text{Away Goals Conceded by Team } A / \text{Away Games Played}}{\text{League Average Home Goals Scored per Game}}$$

3. **Home Expected Goals ($\lambda$)**:
   $$\lambda = AS_H \times DS_A \times \text{League Average Home Goals}$$

4. **Away Expected Goals ($\mu$)**:
   $$\mu = AS_A \times DS_H \times \text{League Average Away Goals}$$

---

## 2. Dixon-Coles Adjustment for Low Scorelines
Mark Dixon and Stuart Coles (1997) observed that soccer matches show mild structural dependence at low scorelines (0-0, 1-0, 0-1, 1-1) that pure independent Poisson underestimates or overestimates.

They introduced a correction factor $\tau(x, y; \lambda, \mu, \rho)$:

$$\tau(x, y) = \begin{cases}
1 - \lambda \mu \rho & \text{if } x = 0, y = 0 \\
1 + \mu \rho & \text{if } x = 1, y = 0 \\
1 + \lambda \rho & \text{if } x = 0, y = 1 \\
1 - \rho & \text{if } x = 1, y = 1 \\
1 & \text{otherwise}
\end{cases}$$

In European football, empirical testing typically sets $\rho \approx -0.11$.

The adjusted probability of score $(x, y)$ is:
$$P(X=x, Y=y) = \tau(x, y) \cdot P(X=x; \lambda) \cdot P(Y=y; \mu)$$

---

## 3. Market Conversion and Expected Value (+EV)

### Fair Odds
Fair odds represent the inverse of true probability with zero bookmaker margin (vigorish/overround):
$$\text{Fair Odds} = \frac{1}{P(\text{Outcome})}$$

### Bookmaker Implied Probability
$$\text{Implied Probability} = \frac{1}{\text{Bookmaker Decimal Odds}}$$

### Expected Value (+EV)
A bet has positive expected value if the return over the long term exceeds the capital staked:
$$\text{EV (\%)} = \left( P_{\text{model}} \times \text{Odds}_{\text{bookmaker}} - 1 \right) \times 100$$

A pick is classified as a value bet when $\text{EV} \ge 3\%$.
