# PLAN.md — AERO-05: Aircraft Conceptual Design From Scratch

## Overview
A capstone project integrating the four preceding pillar projects (Aerodynamics, Structures, Propulsion, Flight Dynamics) into a working aircraft conceptual design and sizing tool, following the classical methodology used in early-stage aircraft design (in the spirit of Raymer's *Aircraft Design: A Conceptual Approach*). Fifth of five projects covering the classical pillars of aerospace engineering.

## Objective
Build a parametric conceptual design tool that takes top-level mission requirements (range, payload, cruise speed/altitude) and produces a sized aircraft configuration (weight, wing area, engine thrust requirement) with a basic performance and stability check, using the physics modules built in the previous four projects.

## Why This Project
Conceptual design is where all the classical pillars are actually used together in industry — no aerospace engineer works in aerodynamics, structures, propulsion, or flight dynamics in total isolation. A working, integrated sizing tool demonstrates systems-level aerospace engineering thinking, not just isolated technical depth in each area. This is the project that ties the whole portfolio series together into a coherent narrative for an interview.

## Knowledge Covered
1. **Requirements Definition**: define a mission profile (range, payload, cruise Mach/altitude, field length) — e.g., sized loosely around a 737-800-class narrow-body mission, for a concrete, relatable reference point.
2. **Weight Estimation**: implement statistical weight estimation (empty weight fraction methods) and iterate to closure with fuel weight via the mission fuel fraction method (Breguet range equation, reusing propulsion model TSFC).
3. **Constraint Analysis**: build the classical thrust-to-weight vs. wing-loading constraint diagram (takeoff distance, cruise, climb, and maneuver constraints), identify the feasible design point.
4. **Wing and Tail Sizing**: use aerodynamic module outputs (from Aerodynamics From Scratch) to size wing area/aspect ratio for the constraint-diagram design point, and size tail surfaces using volume coefficient methods (feeding into the Flight Dynamics stability check).
5. **Structural Sizing Check**: apply a simplified structural sizing pass (using the Structures From Scratch beam/buckling modules) to estimate primary structure weight and sanity-check the statistical weight estimate.
6. **Performance and Stability Verification**: verify the sized aircraft meets the mission's range/payload requirement (using the Propulsion module's cycle performance) and has acceptable static margin and dynamic mode characteristics (using the Flight Dynamics module).
7. **Trade Studies**: explore sensitivity of the design to key assumptions — bypass ratio, aspect ratio, cruise altitude — and present classic aircraft design trade-off curves.

## Prerequisites / Background
Completion (or at least the core modules) of:
- Aerodynamics From Scratch
- Aircraft Structures From Scratch
- Propulsion From Scratch
- Flight Dynamics From Scratch

## Data / Dataset
- **Reference aircraft specifications**: publicly available data for a 737-800-class narrow-body (manufacturer airport-planning documents, type-certificate data sheets, public performance summaries).
- **Statistical sizing relations**: historical weight-fraction and component-weight regressions from conceptual design textbooks (e.g., Raymer).
- **Component models**: outputs of AERO-01 (aerodynamics), AERO-02 (structures), AERO-03 (propulsion), and AERO-04 (flight dynamics).

## Tech Stack
- Python, NumPy, SciPy
- Reuses modules/APIs from the four prior "From Scratch" projects as importable libraries
- Matplotlib/Plotly for constraint diagrams, sizing convergence plots, trade study charts
- Pytest for validation against published reference aircraft data

## Repository Structure
```
aircraft-conceptual-design-from-scratch/
  src/
    requirements/
    weight_estimation/
    constraint_analysis/
    wing_tail_sizing/
    structural_sizing_check/
    performance_verification/
  external/            # imported modules from the 4 prior "From Scratch" projects
  validation/           # comparison against a real reference aircraft's known specs
  notebooks/
  docs/
  tests/
```

## Execution Plan
- [ ] **Phase 1 — Requirements and reference aircraft selection**: define mission requirements, select a real reference aircraft (e.g., a 737-800-class narrow-body) for validation comparison.
- [ ] **Phase 2 — Weight estimation and fuel fraction sizing**: implement statistical weight buildup and Breguet-based fuel fraction, iterate to closure.
- [ ] **Phase 3 — Constraint diagram**: implement thrust-to-weight vs. wing-loading constraint analysis, identify feasible design point.
- [ ] **Phase 4 — Wing/tail sizing**: size wing and tail surfaces, integrating the Aerodynamics module.
- [ ] **Phase 5 — Structural sizing check**: apply simplified structural sizing using the Structures module, cross-check against statistical weight estimate.
- [ ] **Phase 6 — Performance and stability verification**: verify range/payload performance (Propulsion module) and stability characteristics (Flight Dynamics module) of the final sized configuration.
- [ ] **Phase 7 — Trade studies and sensitivity analysis**: sweep key design parameters, produce classical trade-off visualizations.
- [ ] **Phase 8 — Documentation and publishing**: full design report style write-up (mirroring an actual conceptual design report), publish repository.

## Validation Strategy
- Compare final sized weight, wing area, and thrust requirement against the real specifications of the chosen reference aircraft (order-of-magnitude and qualitative trend agreement, not exact match).
- Cross-check that outputs from each imported "From Scratch" module remain physically consistent when chained together (e.g., wing loading from constraint analysis matches the wing area used in the aerodynamic model).

## Deliverables
- Public repository with an integrated, documented conceptual sizing tool
- A design report comparing the sized aircraft against a real reference aircraft
- Visualizations: constraint diagram, weight convergence, trade-off curves

## Portfolio Differentiators
- This is the project that turns four deep-but-separate technical projects into a single coherent "I can design an aircraft end-to-end at the conceptual level" narrative — the systems-thinking signal that isolated deep-dives don't provide on their own.
- Using a 737-class mission as the validation reference ties the entire five-project series to one of the most widely operated airliners in service, so every result can be checked against a real, well-documented aircraft.

## Possible Extensions
- Extend to a basic cost estimation module (acquisition + operating cost, including maintenance cost driven by reliability/MTBF assumptions)
- Add a simple multidisciplinary optimization (MDO) loop, using genetic algorithms (reusing expertise from your thesis) to search the design space instead of manual trade studies
