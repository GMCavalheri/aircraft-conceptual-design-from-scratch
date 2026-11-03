# Trade studies

Theory note for [`src/acdesign/trade_studies/`](../src/acdesign/trade_studies).
Lesson: [07](lessons/07-trade-studies.md).

Every trade point is a call to `size_aircraft` with one `Design` field or one `Mission`
field changed.

| study | variable | notes |
|---|---|---|
| `aspect_ratio` | A = 7–13 | taper and sweep fixed |
| `bypass_ratio` | BPR = 3–11 | `parametric_engine`: the CFM56-7B26/3's calibrated Tt4, OPR and component efficiencies, best-TSFC fan; nacelle ∝ √airflow; mass at equal thrust ∝ exp(0.0107 BPR), fitted to the CFM56-7B26/3 and LEAP-1B28 TCDS masses (calibration) |
| `cruise_altitude` | FL290–FL410 | the buffet and ceiling lines move with altitude |
| `carpet` | W/S × T/W grid | the constraint design point is bypassed; infeasible or non-converging points are NaN |

## Verification ([`tests/test_trade_studies.py`](../tests/test_trade_studies.py))

- A sweep at the baseline value reproduces the baseline. The carpet at the design point
  reproduces it.
- The parametric engine at the base BPR is the calibrated engine. The mass trend reproduces
  the LEAP-1B28's TCDS mass at its BPR and thrust.
