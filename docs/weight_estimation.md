# Weight estimation

Theory note for [`src/acdesign/weight_estimation/`](../src/acdesign/weight_estimation).
Lesson: [02](lessons/02-weight-estimation.md).

## Class I ([`class_one.py`](../src/acdesign/weight_estimation/class_one.py), [`fractions.py`](../src/acdesign/weight_estimation/fractions.py))

```math
W_0 = \frac{W_{\text{crew}} + W_p}{1 - W_f/W_0 - W_e/W_0}, \qquad
\frac{W_e}{W_0} = 1.02\,W_0^{-0.06}\ (\text{lb}), \qquad
\left(\frac LD\right)_{\max} = 15.5\sqrt{\frac{A}{S_{\text{wet}}/S_{\text{ref}}}}
```

Segment fractions follow Raymer, ch. 3: 0.970 for warm-up and take-off, 0.985 for climb and
0.995 for landing. Cruise and hold use the Breguet equations with $c$ = TSFC·$g_0$:

```math
\frac{W_{\text{end}}}{W_{\text{start}}} = \exp\left(-\frac{R\,c}{V\,L/D}\right), \qquad
\frac{W_{\text{end}}}{W_{\text{start}}} = \exp\left(-\frac{E\,c}{L/D}\right)
```

Fuel = (trip + contingency + diversion and hold at landing weight) / (1 − 1 % trapped).
$W_0$ is solved by fixed-point iteration.

## Class II ([`class_two.py`](../src/acdesign/weight_estimation/class_two.py))

| group | method |
|---|---|
| structure | Raymer ch. 15 cargo/transport: wing, horizontal and vertical tails, fuselage, main and nose gear, nacelles |
| propulsion | engines (TCDS dry mass), Raymer's engine controls, starter, fuel system |
| systems | FLOPS (NASA/TM-2017-219627) eqs. 97, 101–108, 110, 113, 115: surface controls, APU, instruments, hydraulics, electrical, avionics, furnishings, air conditioning, anti-icing |
| operating items | FLOPS eqs. 119–124: crew, unusable fuel, engine oil, passenger service |

The inputs (`ClassTwoInputs`) are SI. Each equation converts to lb, ft, ft², inches, US gal,
ft/s or nmi at its boundary, with the exact factors of [`units.py`](../src/acdesign/units.py).

## Verification ([`tests/test_weight_estimation.py`](../tests/test_weight_estimation.py))

- Breguet round trip and closed form; fuel-fraction bookkeeping; the empty-fraction
  regression; the wetted-aspect-ratio L/D.
- Class I closes its own equation.
- FLOPS furnishings, by hand in imperial units. The wing scales as $(W_{dg}N_z)^{0.557}$
  under a doubling of $W_{dg}$. Engine oil follows FLOPS eq. 123.

## Validation

- **Class I** sizes the design mission to 80.4 t, 1.8 % above the 737-800 MTOW.
- **Class II** on the 737-800's published geometry gives an OEW 11.7 % below Boeing's
  (uncalibrated). See the [design report](design-report.md).
