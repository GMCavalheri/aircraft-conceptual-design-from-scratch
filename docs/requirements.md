# Requirements

Theory note for [`src/acdesign/requirements/`](../src/acdesign/requirements).
Lesson: [01](lessons/01-requirements-and-reference.md).

## The mission

`Mission` holds the top-level requirements in SI units:
- passengers and the mass allowed per passenger;
- the design range;
- cruise Mach and initial cruise altitude (geopotential pressure altitude);
- FAR take-off and landing field lengths at MTOW and MLW, and MLW/MTOW;
- reserves (`Reserves`): a contingency fraction of trip fuel, a diversion distance, and a
  hold time at an altitude.

`B737_800_MISSION` labels every value:

| requirement | value | label |
|---|---|---|
| passengers | 160 (12 first, 148 economy) | data, D6-58325-7 §2.1.3, §2.4.4 |
| mass per passenger | 225 lb with baggage | assumption (Raymer ch. 3) |
| design range | 2,800 nmi | requirement, chosen just inside the full-fuel corner (2,860 nmi) |
| cruise | Mach 0.78, FL350 | assumption, consistent with JSR's LRC of 452 kt |
| field lengths | 7,800 ft take-off, 5,800 ft landing | data, read from §3.3.29 and §3.4.3 |
| MLW/MTOW | 146,300/174,200 | deduction |
| reserves | 5 % + 200 nmi + 30 min at 1,500 ft | assumption |

## Reference data

[`validation/reference_data/b737_800.csv`](../validation/reference_data/b737_800.csv) has
three kinds of row:
- printed values, with section and page;
- chart readings, with their resolution;
- Jenkinson et al.'s geometry table, using only rows filled for every aircraft, so the
  column alignment is unambiguous.

[`reference.py`](../validation/reference.py) converts these to SI on load.

## Verification ([`tests/test_reference_data.py`](../tests/test_reference_data.py), [`tests/test_requirements.py`](../tests/test_requirements.py))

- Printed pounds against printed kilograms. The fuel pair differs by 4 kg because both
  masses are derived from volume, at 6.7 lb/gal and 0.803 kg/L.
- MZFW = OEW + maximum payload.
- At the full-fuel corner of the payload-range chart, MTOW − (OEW + payload) reproduces the
  fuel capacity to the chart's resolution.
- Geometry identities: $A = b^2/S$, the tail volume coefficients, and the tail aspect ratio.
- The design mission lies inside the reference envelope, within 3 % of its full-fuel
  corner.
