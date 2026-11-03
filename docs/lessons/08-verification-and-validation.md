# Lesson 8 · Verification and validation

> *A conceptual design tool chains five disciplines and a hundred assumptions. "It gives
> plausible numbers" is not evidence. This lesson collects what was checked, against what,
> and what the checks found — including where the tool is wrong.*

**Code:** [`tests/`](../../tests), [`validation/`](../../validation) ·
**Report:** [Design report](../design-report.md) ·
**Previous:** [Lesson 7](07-trade-studies.md) ·
**Course index:** [README](README.md)

## Learning objectives

1. Organise checks into a hierarchy, from closed forms to a real aircraft.
2. Tell verification (the code solves the equations) from validation (the equations
   describe the aircraft).
3. Use independent methods to locate an error inside a chain.
4. State a validation result with its tolerance and its reason.

---

## 1. The hierarchy

| Level | Question | Examples in this project |
|---|---|---|
| closed forms | does each function solve its equation? | Breguet round trip; master-equation minimum = 1/(L/D)max; uniform-load cantilever; Lock's law slope 0.1 at $M_{dd}$ |
| cross-project | do the pillar packages behave as their own reports say? | engine adapter reproduces AERO-03's Tt4, airflow and TSFCs to the printed digit; VLM far wake = AERO-01's Trefftz plane to 1e-5 |
| internal consistency | does the closed design agree with itself? | W0 = OEW + payload + fuel; W0 g/S = constraint W/S; tail volumes as specified; static margin moved to zero by `move_cg` |
| independent methods | do two routes to one quantity agree? | physics wing vs class II wing (2 %); time integration vs Breguet (+5 %); textbook neutral point vs AERO-04 (1.5 % MAC); VLM lift slope vs DATCOM (4 %); VLM downwash vs DATCOM (11–14 %) |
| reference aircraft | does the design look like the 737-800? | W0, OEW, S, T, fuel, field-length deduction, payload-range |

Every test names its source and explains its tolerance
([`tests/`](../../tests), 89 tests). Each comparison with the reference has a script in
[`validation/`](../../validation) that writes a results table.

## 2. Verification is not validation

The closed-form tests prove the code solves Raymer's, Loftin's and Mattingly's equations
correctly. They do not prove that the equations describe a 737. The 737-800 comparison does
that, and it is the only level where the answer can be "the model is wrong":

| | sized | 737-800 | |
|---|---|---|---|
| take-off mass | 70.0 t | 79.0 t | −11.5 % |
| operating empty mass | 33.7 t | 41.4 t | −18.7 % |
| mission fuel | 20.0 t | 21.3 t | −6.1 % |
| wing area | 115 m² | 125 m² | −7.6 % |
| thrust per engine | 98 kN | 117 kN | −16.4 % |
| wing loading / thrust loading | 5,962 Pa / 0.285 | 6,219 Pa / 0.302 | −4 % / −6 % |

## 3. Locating the error

The sized aircraft is consistently light. Where does that come from? The independent checks
narrow it down:

1. **Not the aerodynamics.** On the 737's own geometry, the drag build-up gives the same
   CD0 and e as on the sized design to 0.3 %. The mission fuel is only 6 % low, and the
   sized design's payload-range corners fall within 11 % of the 737's chart.
2. **Not the engine.** It reproduces AERO-03, and AERO-03 reproduces ICAO fuel flows
   (+1 % climb-out).
3. **Not the wing structure.** The physics-based box agrees with the statistical wing to
   2 %.
4. **The empty weight.** Class II on the 737's *published* geometry already gives an OEW
   11.7 % low. With the fuselage and wing statistically sound, the shortfall lies in what a
   conceptual method weighs least well: systems, interior and operator items. The growth
   factor of 2.2 then turns −12 % of OEW into −19 % at the closed design and −11.5 % in W0.

Each step uses a check that is *independent* of the one before. That is what makes the
diagnosis credible. A single end-to-end comparison would only have said "11.5 % light".

## 4. Calibrate or not?

The common fix is a calibration factor on the empty mass, about 1.13 here, fitted to the
737. Then W0 would match by construction, and it could no longer be used to validate
anything. This project keeps the uncalibrated result. It is the honest answer to the plan's
question, "does a from-scratch chain of textbook methods size a 737-class aircraft?": yes,
to within 12 % in weight and 8 % in wing area, with every trend in the right direction. A
calibrated variant would be the right tool for the *next* step: designing a derivative of
the 737, where only differences matter.

## 5. What the checks found

Checking the sources and the models against themselves found things none of them states:

- **Boeing's fuel weights come from volume.** The manual derives its two fuel masses from
  volume with different densities (6.7 lb/gal and 0.803 kg/L), so they differ by 4 kg.
- **Raymer's furnishings miss an airliner cabin.** His transport furnishings equation gives
  1,400 lb for a 160-seat cabin, where FLOPS gives 13,900 lb. The equations' military
  population does not cover airline interiors.
- **The 737's field lengths imply its high-lift CLmax.** Loftin's take-off correlation with
  the 737's own numbers gives CLmax,TO = 2.09; the landing chart gives CLmax,L = 2.82.
- **Raymer's engine-mass trend has the wrong sign here.** It makes engines lighter as bypass
  ratio rises, the opposite of the CFM56-7B to LEAP-1B step in the TCDS masses.
- **An even strip count halves the tail downwash.** A vortex lattice with an even strip
  count puts a trailing-vortex node on the symmetry plane, where the tail is, and halves
  the downwash computed there.
- **The design needs a yaw damper.** Its bare airframe misses the dutch-roll ζω requirement,
  as swept-wing transports do.

## 6. Exercises

1. Which level of the hierarchy would catch a unit error in one of Raymer's equations? Which
   would catch a wrong exponent?
2. Why is the 2 % wing-mass agreement weaker evidence than it looks?
3. Suppose the empty mass were calibrated to the 737. Which rows of §2 could still validate
   the model?
4. Propose one more independent check that would locate the OEW shortfall further.

<details>
<summary>Answers</summary>

1. A unit error shifts every result and shows at the reference level. It is caught
   precisely by a hand calculation in imperial units (`test_class_two_equations_by_hand`).
   A wrong exponent is caught by the scaling test that doubles $W_{dg}$.
2. The non-optimum factor (1.5) and the secondary areal mass were assumed. Each carries
   ±15 % on its own. The agreement says the two methods are consistent, not that either is
   accurate to 2 %.
3. Only quantities the calibration does not touch: the fuel's split between climb and
   cruise, the field-length deductions, the payload-range *shape*. W0, S and T would all be
   partly calibrated.
4. Compare each class II group with a published component weight breakdown of a
   737-family aircraft. Group weights appear in some textbooks and NASA reports; with them
   the shortfall could be pinned to one group.

</details>

## Key takeaways

- Build checks in levels: closed forms, cross-project, internal consistency, independent
  methods, the real aircraft.
- Use independent methods to locate an error, not just to detect one.
- Report uncalibrated results with their tolerance and their cause. Calibrate only for
  questions about differences.

## Further reading

- W. L. Oberkampf & C. J. Roy, *Verification and Validation in Scientific Computing*
  (Cambridge, 2010), ch. 1–2.
- AERO-04, Lesson 7, and AERO-03, Lesson 7 (verification and validation of the pillar
  models).
