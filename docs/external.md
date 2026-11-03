# The pillar packages as libraries

Theory note for [`src/acdesign/external/`](../src/acdesign/external), the only modules that
import the four AERO projects. The projects are uv git dependencies pinned to a commit in
[`pyproject.toml`](../pyproject.toml).

| adapter | package | provides | cross-project check |
|---|---|---|---|
| [`engine.py`](../src/acdesign/external/engine.py) | `propulsion` (AERO-03) | the AERO-03 calibration rebuilt from the public API; exact rubber scaling; lapse tables at take-off and climb rating; part-power TSFC lines; parametric engines | Tt4 1417.3 K, airflow 348.6 kg/s, take-off TSFC 10.368 and cruise minimum 17.12 mg/(N·s), all as AERO-03 prints them |
| [`atmosphere.py`](../src/acdesign/external/atmosphere.py) | `propulsion` | ISA at geopotential pressure altitude | 11 km and FL350 table values |
| [`wing_aero.py`](../src/acdesign/external/wing_aero.py) | `aero` (AERO-01) | planform bookkeeping, Göthert lift slope, span efficiency and loading, Biot–Savart downwash, VLM roll derivatives | DATCOM, far-wake Trefftz, strip-theory limits |
| [`wing_box.py`](../src/acdesign/external/wing_box.py) | `structures` (AERO-02) | cantilever shear and moment, closed thin-walled box, materials, buckling, S-N curves | closed-form cantilever, thin-wall I and J |
| [`stability.py`](../src/acdesign/external/stability.py) | `flightdyn` (AERO-04) | Aircraft, trim, linearization, modes, neutral point, tail contributions | `move_cg` zeroes the margin |

**Rubber scaling is exact.** The off-design matching equations of AERO-03 are ratios of
flows and areas. An engine designed at k times the thrust therefore has k times every flow,
area and thrust, and the same TSFC and lapse; the test designs one at twice the thrust. An
`Engine` can then store a scale factor and reuse the unscaled model's tables.
