# Constraint analysis

Theory note for [`src/acdesign/constraint_analysis/`](../src/acdesign/constraint_analysis).
Lesson: [03](lessons/03-constraint-diagram.md).

## Master equation (Mattingly, ch. 2)

```math
\frac{T_{SL}}{W_{TO}} = \frac{\beta}{\alpha}\left[\frac{q}{\beta\,W/S}\left(C_{D_0}
+ K\left(\frac{n\beta\,W/S}{q}\right)^2\right) + \frac{P_s}{V}\right],\qquad K = \frac{1}{\pi A e}
```

Here α is the lapse of the AERO-03 engine at the flight condition and rating, and β the
weight fraction.

## Requirements ([`diagram.py`](../src/acdesign/constraint_analysis/diagram.py))

| requirement | model |
|---|---|
| take-off field length | Loftin: $s_{TO}$ [ft] = 37.5 (W/S [psf])/(σ CLmax,TO T/W) |
| landing field length | Loftin: $s_L$ [ft] = 0.3 $V_A^2$ [kt], $V_A = 1.3V_s$ → max W/S |
| second segment (FAR 25.121b) | N/(N−1) (β/α)(1/(L/D) + 0.024), take-off flaps, $V_2 = 1.2V_s$ |
| approach climb (25.121d) | G = 0.021 at landing weight, approach flaps, 1.3 $V_s$ |
| landing climb (25.119) | G = 0.032, all engines, landing flaps and gear |
| cruise / initial cruise altitude | master equation with $P_s$ = 0 / 300 ft/min |
| buffet margin | W/S ≤ $q C_{L,\text{buffet}}/(1.3\beta)$ |

The polar ([`polar.py`](../src/acdesign/constraint_analysis/polar.py)) is parabolic, with
optional wave drag, and low-speed configurations add flap and gear increments. A first
estimate of $C_{D_0}$ is $C_{fe} S_{\text{wet}}/S_{\text{ref}}$, with $C_{fe}$ = 0.0026, and of
e, Raymer's fit. The design point is the highest W/S the vertical limits allow, with the
envelope's T/W there.

## Verification ([`tests/test_constraint_analysis.py`](../tests/test_constraint_analysis.py))

- Loftin round trips. The landing correlation equals $m/S = 0.107\sigma C_{L_{\max}} s$.
- Master-equation minimum = 1/(L/D)max at $W/S = q\sqrt{C_{D_0}/K}$. The climb term is
  $P_s/V$.
- The OEI gradient factor; the polar's L/D maximum; Raymer's Oswald fit.
- The design point is feasible and landing-limited.
- Deduction: the 737's take-off chart implies CLmax,TO = 2.09.
