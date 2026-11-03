# Performance and stability verification

Theory note for [`src/acdesign/performance_verification/`](../src/acdesign/performance_verification)
and [`src/acdesign/external/stability.py`](../src/acdesign/external/stability.py).
Lesson: [06](lessons/06-performance-and-stability.md).

## Mission integration ([`mission.py`](../src/acdesign/performance_verification/mission.py))

- **Climb** from 1,500 ft, at 290 KCAS and then Mach 0.78, at the climb rating:
  $(T-D)V/W = \dot h(1 + (V/g)dV/dh)$, in 250 m steps.
- **Cruise** at constant M and h: $dx = -V dW/(D\cdot\text{TSFC}(D))$, by Simpson's rule
  over weight.
- **Descent** along 3°: distance credited, fuel fraction 0.995.

Reserves are held back as in the sizing. The cruise fuel is found by bisection so that
trip + reserves + trapped fuel equals the fuel on board. The payload-range corners come from
the same routine.

## Stability ([`stability.py`](../src/acdesign/performance_verification/stability.py))

- **Balance.** Component CG build-up; the wing is placed for a 25 % MAC mid-cruise CG.
- **Aerodynamic centres.**
  - Wing: VLM moment, Göthert-corrected.
  - Fuselage shift: $-1.8 b_f h_f l_{fn}/(S\bar cC_{L_\alpha})$ (Torenbeek).
  - Neutral point:
    $h_n = (h_{ac} + \eta V_H (a_t/a)(1-\varepsilon_\alpha))/(1 + \eta (S_t/S)(a_t/a)(1-\varepsilon_\alpha))$.
- **Tail.** AERO-04's `HorizontalTail.contributions()`, with tail lift slope and downwash
  from the VLM.
- **Wing roll derivatives.** From the AERO-01 lattice with sideslip, rotation and aileron in
  the boundary condition: $\mathbf v = \mathbf V_\infty - \boldsymbol\omega\times\mathbf r$
  at control points and bound vortices, with Kutta–Joukowski forces in lattice axes
  rotated to body axes.
- **Fin.** VLM lift slope at 1.55 A, the DATCOM sidewash fit, and Etkin & Reid's tail-arm
  formulas.
- **Fuselage.** $C_{n_\beta} = -1.3 \text{Vol}/(Sb)$.
- **Model.** AERO-04 `Aircraft`, then `neutral_point_shift`, `trim`, `linearize` and the
  modal analysis.
- **Flying qualities.** Judged against MIL-F-8785C Level 1, Class III, category B.

## Verification ([`tests/test_performance_verification.py`](../tests/test_performance_verification.py))

- CAS↔TAS round trip.
- Fuel accounting closes. The integrated range exceeds the Breguet requirement by less than
  the climb and descent distance.
- Roll-derivative signs; $C_{l_p}$ tends to strip theory as A → ∞.
- CG at target. AERO-04's static margin within 0.02 of the textbook value; `move_cg` by the
  margin zeroes it.
- Phugoid against Lanchester (15 %); roll time constant against $-2VI_{xx}/(qSb^2C_{l_p})$
  (10 %).
