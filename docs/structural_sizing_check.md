# Structural sizing check

Theory note for [`src/acdesign/structural_sizing_check/`](../src/acdesign/structural_sizing_check)
and [`src/acdesign/external/wing_box.py`](../src/acdesign/external/wing_box.py).
Lesson: [05](lessons/05-structural-sizing-check.md).

## Loads

Lift per unit span is $n W g \ell(y)/b$, with $\ell$ the VLM span-loading shape (mean 1)
and n = 3.75. Relief is n g times the wing structure (spread like c), the wing fuel (37.5 %
of the mission fuel, spread like c² over the inner 75 %) and the engine (a point mass at
28.2 % semispan). The take-off and zero-fuel cases are enveloped. The beam runs along the
mid-box axis, $s = (y - y_0)/\cos\Lambda$, with load $w\cos\Lambda$. The AERO-02 Macaulay
solver, clamped at the side of the body, gives V and M.

## Sizing at each station

The cover force is $P = M/h$, with $h$ = 0.85 t/c·c and width 0.50 c cos Λ.

| element | criterion |
|---|---|
| upper cover, 7075-T6 | $\sigma_J = F_{cy}[1 - F_{cy}(L/\rho)^2/(4\pi^2E)]$, L/ρ = 0.6/0.018; skin (half the area) does not buckle below limit load: $t^3 \ge P b^2/(1.5 w D f^2)$ |
| lower cover, 2024-T3 | min($F_{tu}$, n × the Kt = 2 GAG fatigue stress for 225,000 cycles) |
| spar webs, 7075-T6 | $q = V/(2h)$ at min($F_{su}$, shear buckling with k = 5.35 + 4/r²) |
| all | 1.6 mm minimum gauge |

Wing mass = 1.5 × ideal box + 15 kg/m² × S. The 1-g tip deflection integrates
$M/(EI)$ twice, with I from AERO-02's closed `thin_walled` box.

## Verification ([`tests/test_structural_check.py`](../tests/test_structural_check.py), [`tests/test_wing_box_adapter.py`](../tests/test_wing_box_adapter.py))

- Cantilever $wL^2/2$ with a point load. The thin-walled box I and Bredt–Batho J.
- Root moment and shear equal the integrated lift, to the discretisation.
- The column allowable is the Johnson formula. The root cover works exactly at it. No skin
  buckling occurs below limit load. The webs stay within $F_{su}$.
- Physics wing against the class II wing, for the sized design and for the 737-800
  geometry: 0.98 and 0.99.
