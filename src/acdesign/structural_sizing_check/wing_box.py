"""Physics-based sizing of the wing box, as a check on the statistical wing weight.

The wing is a cantilever from the side of the body, along a structural axis swept at the
box mid-chord. At each span station the box — two skin-stringer covers and two spar webs —
gets the least material that carries the ultimate loads:

* **Loads.** Symmetric pull-up at the ultimate load factor n = 1.5 × 2.5 (FAR 25.337,
  25.303). Lift follows the VLM span loading (AERO-01); inertia relief n·g·m from the wing
  structure (spread like the chord), the fuel in the wing tanks (spread like the chord²,
  over the inner part of the span) and the engine (a point load). Two cases, take-off mass
  with fuel and zero-fuel mass without, give the envelope. Shear and moment from the AERO-02
  beam solver.
* **Upper cover** (7075-T6, compression): skin-stringer panel at the Johnson–Euler column
  stress of a stringer between ribs, and thick enough that the skin between stringers does
  not buckle below limit load (ultimate / 1.5).
* **Lower cover** (2024-T3, tension): the smaller of Ftu and n × the 1-g stress for the
  fatigue life of a ground–air–ground cycle (MIL-HDBK-5J Kt = 2 curve).
* **Spar webs** (7075-T6): the shear flow V/(2h) at the smaller of Fsu and the web's shear
  buckling stress (no tension field credited).
* **Minimum gauge** on every element.

The ideal box mass is then multiplied by a non-optimum factor (ribs, joints, fasteners,
cut-outs) and secondary structure (leading and trailing edges, high-lift devices, control
surfaces) is added per unit area, to compare with the class II wing mass. Box geometry,
panel dimensions and these factors are assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.external.wing_aero import Planform, span_loading
from acdesign.external.wing_box import (
    box_section,
    cantilever_shear_moment,
    compression_k,
    handbook_curve,
    isotropic,
    johnson_stress,
    plate_critical_stress,
    shear_k,
)
from acdesign.units import G0


@dataclass(frozen=True)
class BoxAssumptions:
    front_spar: float = 0.15  # chord fractions
    rear_spar: float = 0.65
    height_factor: float = 0.85  # box height / local maximum thickness
    tc_root: float = 0.13
    tc_tip: float = 0.10
    stringer_pitch: float = 0.15  # [m]
    rib_pitch: float = 0.60  # [m]
    stringer_radius_of_gyration: float = 0.018  # skin-stringer combination [m]
    skin_fraction: float = 0.5  # of cover area in the skin (rest in stringers)
    min_gauge: float = 1.6e-3  # [m]
    wing_fuel_fraction: float = 0.375  # of total fuel, in the two wing tanks
    fuel_span: float = 0.75  # wing tanks extend over this fraction of the exposed semispan
    engine_station: float = 0.282  # engine at this fraction of the semispan (data, JSR)
    fatigue_cycles: float = 75000 * 3  # design service goal x scatter factor
    non_optimum: float = 1.5
    secondary_areal_mass: float = 15.0  # [kg/m^2 of reference wing area]
    n_stations: int = 41


ULTIMATE_LOAD_FACTOR = 1.5 * 2.5


@dataclass(frozen=True)
class WingBoxResult:
    y: np.ndarray  # span stations (from the centreline) [m]
    s: np.ndarray  # distance along the structural axis from the side of body [m]
    shear: np.ndarray  # ultimate envelope, normal to the structural axis [N]
    moment: np.ndarray  # ultimate envelope [N m]
    height: np.ndarray  # box height [m]
    width: np.ndarray  # box width normal to the structural axis [m]
    t_upper: np.ndarray  # equivalent (smeared) cover thicknesses [m]
    t_lower: np.ndarray
    t_web: np.ndarray
    sigma_upper: float  # allowable stresses [Pa]
    sigma_lower: float
    lower_governed_by: str
    skin_buckling_ratio: np.ndarray  # upper skin buckling stress / applied ultimate stress
    upper_governed_by: np.ndarray  # "column", "skin buckling" or "minimum gauge" per station
    box_mass: float  # ideal box, both wings [kg]
    wing_mass: float  # with non-optimum factor and secondary structure [kg]
    tip_deflection_1g: float  # [m], 1 g at take-off mass (case of the larger moment / n)

    @property
    def root_moment(self) -> float:
        return float(self.moment[0])


def wing_box(
    wing: Planform,
    fuselage_diameter: float,
    W0: float,
    zero_fuel_mass: float,
    fuel_mass: float,
    wing_mass: float,
    engine_mass: float,
    a: BoxAssumptions | None = None,
) -> WingBoxResult:
    """Size the box of ``wing`` for take-off mass ``W0`` and ``zero_fuel_mass`` [kg]; the
    relief masses are the class II wing ``wing_mass`` (both sides), the ``fuel_mass`` of
    the mission and one ``engine_mass`` (engine + nacelle) per side."""
    a = BoxAssumptions() if a is None else a
    n = ULTIMATE_LOAD_FACTOR
    y0, half = fuselage_diameter / 2, wing.b / 2
    y = np.linspace(y0, half, a.n_stations)
    sweep_ea = wing.sweep_at(0.5 * (a.front_spar + a.rear_spar))
    cs = np.cos(sweep_ea)
    s = (y - y0) / cs
    c = wing.chord(y)

    # spanwise shape of lift (VLM), mean 1 over the full span
    yv, shape = span_loading(wing)
    lift_shape = np.interp(y, yv[yv >= 0], shape[yv >= 0])

    def per_span(total, weight, mask=None):
        """Distribute ``total`` [N] over one exposed semispan in proportion to ``weight``."""
        wgt = weight if mask is None else weight * mask
        return total * wgt / np.trapezoid(wgt, y)

    m_struct = per_span(wing_mass / 2 * G0, c)
    fuel_mask = (y - y0) <= a.fuel_span * (half - y0)
    m_fuel = per_span(a.wing_fuel_fraction * fuel_mass / 2 * G0, c**2, fuel_mask)
    y_eng = a.engine_station * half
    eng = [((y_eng - y0) / cs, -n * engine_mass * G0)]

    cases = {}
    for name, W, fuel in (("take-off", W0, m_fuel), ("zero fuel", zero_fuel_mass, 0.0 * m_fuel)):
        lift = n * W * G0 / wing.b * lift_shape  # [N per m of span]
        w = (lift - n * (m_struct + fuel)) * cs  # per unit structural length
        V, M = cantilever_shear_moment(s, w, eng)
        cases[name] = (np.abs(V), np.abs(M))
    V = np.maximum(cases["take-off"][0], cases["zero fuel"][0])
    M = np.maximum(cases["take-off"][1], cases["zero fuel"][1])

    # box geometry, normal to the structural axis
    tc = a.tc_root + (a.tc_tip - a.tc_root) * (y - y0) / (half - y0)
    h = a.height_factor * tc * c
    width = (a.rear_spar - a.front_spar) * c * cs

    al7075, al2024 = isotropic("7075-T6"), isotropic("2024-T3")
    sigma_up = float(
        min(
            al7075.Fcy,
            johnson_stress(al7075.E, al7075.Fcy, a.rib_pitch / a.stringer_radius_of_gyration),
        )  # noqa: E501
    )
    s_fat = float(handbook_curve("2024-T3_Kt2").max_stress_for_life(a.fatigue_cycles, 0.0))
    sigma_lo, gov = (al2024.Ftu, "Ftu") if al2024.Ftu <= n * s_fat else (n * s_fat, "fatigue")

    P = M / h  # cover force couple
    k_c, _ = compression_k(a.rib_pitch / a.stringer_pitch)
    D_plate = k_c * np.pi**2 * al7075.E / (12 * (1 - al7075.nu**2))
    # skin stress P/(w t) at limit load <= D (f t / b)^2  ->  t^3 >= P b^2 / (1.5 w D f^2)
    t_skin = (P * a.stringer_pitch**2 / (1.5 * width * D_plate * a.skin_fraction**2)) ** (1 / 3)
    t_up = np.maximum(np.maximum(P / (width * sigma_up), t_skin), a.min_gauge)
    t_lo = np.maximum(P / (width * sigma_lo), a.min_gauge)
    q = V / (2 * h)  # shear flow per web
    k_s = np.array([shear_k(a.rib_pitch / hi) for hi in h])
    t_buckle = (q * h**2 * 12 * (1 - al7075.nu**2) / (k_s * np.pi**2 * al7075.E)) ** (1 / 3)
    t_web = np.maximum(np.maximum(q / al7075.Fsu, t_buckle), a.min_gauge)

    sigma_applied = P / (width * t_up)
    skin_cr = np.array(
        [
            plate_critical_stress(al7075.E, al7075.nu, a.skin_fraction * t, a.stringer_pitch, k_c)
            for t in t_up
        ]  # noqa: E501
    )

    mass_per_length = (
        al7075.density * width * t_up
        + al2024.density * width * t_lo
        + al7075.density * 2 * h * t_web
    )
    box = 2 * float(np.trapezoid(mass_per_length, s))
    total = a.non_optimum * box + a.secondary_areal_mass * wing.S

    # 1-g deflection at take-off mass: curvature M/(EI), integrated twice from the clamp
    I = np.array(
        [
            box_section(wi, hi, tu, tl, tw)[0]
            for wi, hi, tu, tl, tw in zip(width, h, t_up, t_lo, t_web, strict=True)
        ]
    )  # noqa: E501
    kappa = cases["take-off"][1] / n / (al7075.E * I)
    slope = np.concatenate([[0.0], np.cumsum(np.diff(s) * 0.5 * (kappa[1:] + kappa[:-1]))])
    defl = np.concatenate([[0.0], np.cumsum(np.diff(s) * 0.5 * (slope[1:] + slope[:-1]))])

    return WingBoxResult(
        y=y, s=s, shear=V, moment=M, height=h, width=width, t_upper=t_up, t_lower=t_lo,
        t_web=t_web, sigma_upper=sigma_up, sigma_lower=float(sigma_lo), lower_governed_by=gov,
        skin_buckling_ratio=skin_cr / sigma_applied,
        upper_governed_by=np.where(
            t_up <= a.min_gauge, "minimum gauge",
            np.where(t_skin > P / (width * sigma_up), "skin buckling", "column"),
        ),
        box_mass=box, wing_mass=total,
        tip_deflection_1g=float(defl[-1]),
    )  # fmt: skip
