# Wing and tail sizing, drag, and the sizing loop

Theory note for [`src/acdesign/wing_tail_sizing/`](../src/acdesign/wing_tail_sizing),
[`src/acdesign/sizing.py`](../src/acdesign/sizing.py) and
[`src/acdesign/external/wing_aero.py`](../src/acdesign/external/wing_aero.py).
Lesson: [04](lessons/04-wing-and-tail-sizing.md).

## Planform and tails

```math
b = \sqrt{AS},\ c_r = \frac{2S}{b(1+\lambda)},\ \bar c = \tfrac23c_r\frac{1+\lambda+\lambda^2}{1+\lambda},\
y_{\bar c} = \frac b6\frac{1+2\lambda}{1+\lambda},\ \tan\Lambda_{x} = \tan\Lambda_{c/4} - \frac4A\left(x - \tfrac14\right)\frac{1-\lambda}{1+\lambda}
```

Tails are sized by volume coefficients: $S_H = V_H\bar cS/l_H$ and $S_V = V_V bS/l_V$.

## Aerodynamics from AERO-01

- **Lift slope.** By the Göthert rule, the VLM of the wing stretched by 1/β gives
  $C_{L_\alpha}(M) = C_{L_\alpha}'/\beta$.
- **Span efficiency.** From the Trefftz plane.
- **Downwash.** From Biot–Savart at the tail, with an odd strip count so the symmetry plane
  is a strip centre. It is scaled to Mach by $C_{L_\alpha}(M)/C_{L_\alpha}(0)$.

## Drag ([`drag.py`](../src/acdesign/wing_tail_sizing/drag.py))

```math
C_{D_0} = 1.03\sum_c \frac{C_f FF\,Q\,S_{\text{wet}}}{S_{\text{ref}}},\quad
C_f = \frac{0.455}{(\log_{10}Re)^{2.58}(1+0.144M^2)^{0.65}},\quad
\frac1e = \frac1{e_{\text{inv}}(1 - 2(d_f/b)^2)} + 0.38C_{D_0}\pi A
```

Wave drag uses the Korn equation:

```math
M_{dd} = \frac{\kappa}{\cos\Lambda} - \frac{t/c}{\cos^2\Lambda} - \frac{C_L}{10\cos^3\Lambda}
```

with $M_{crit} = M_{dd} - (0.1/80)^{1/3}$ and $\Delta C_D = 20(M - M_{crit})^4$.

## The loop

At each iteration: constraint design point, then geometry, then polar, then class II, then
mission fuel, then $W_0$ = OEW + payload + fuel. The iteration uses a secant update and
converges in 4 iterations to a relative tolerance of 1e-6.

## Verification ([`tests/test_wing_aero.py`](../tests/test_wing_aero.py), [`tests/test_drag.py`](../tests/test_drag.py), [`tests/test_sizing.py`](../tests/test_sizing.py))

- Planform against AERO-01's `Wing` (area, A, MAC).
- VLM against DATCOM within 4 % (tapered planforms, Mach 0–0.8). As A grows, the slope
  tends to the 2D Prandtl–Glauert value.
- Far-wake downwash: equal to AERO-01's Trefftz plane to 1e-5, and to the elliptic
  $2C_L/(\pi A)$ within 3 %. Tail downwash within 15 % of DATCOM.
- Sutherland viscosity; the flat-plate limit; form factors; Lock's law slope 0.1 at $M_{dd}$.
- Closed design: weight closure, W/S and T/W equal to the design point, tail volumes, class
  II of the final geometry, and the cruise TSFC equal to the engine's at the cruise drag.
