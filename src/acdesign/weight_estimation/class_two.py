"""Class II sizing: component weights of a transport from its geometry.

Two published statistical methods are combined, each where it fits an airliner:

* **Structure and propulsion** — Raymer's cargo/transport equations (*Aircraft Design: A
  Conceptual Approach*, ch. 15): wing, tails, fuselage, landing gear, nacelles, engines,
  engine controls, starter, fuel system.
* **Systems, furnishings and operating items** — the transport equations of FLOPS (D. P.
  Wells, B. L. Horvath, L. A. McCullers, *The Flight Optimization System Weights Estimation
  Method*, NASA/TM-2017-219627 Vol. I, 2017, sections 5.4 and 5.5, eqs. 97-124). Raymer's
  equipment equations come from military transports; his furnishings equation gives about
  1,400 lb for a 160-seat cabin, where FLOPS's commercial equation (seats, galleys,
  lavatories, linings) gives about 13,000 lb.

Both are in imperial units — weights in lb, areas in ft², lengths in ft (gear lengths in
inches), volumes in U.S. gal, speeds in ft/s, range in nmi — so ``ClassTwoInputs`` is SI and
every equation converts at its boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from acdesign.units import FT, FT2, INCH, LB, LBF, NMI, US_GAL

GROUPS = {
    "structure": (
        "wing",
        "horizontal_tail",
        "vertical_tail",
        "fuselage",
        "main_gear",
        "nose_gear",
        "nacelles",
    ),  # fmt: skip
    "propulsion": ("engines", "engine_controls", "starter", "fuel_system"),
    "systems": (
        "surface_controls",
        "apu",
        "instruments",
        "hydraulics",
        "electrical",
        "avionics",
        "furnishings",
        "air_conditioning",
        "anti_icing",
    ),
    "operating_items": ("crew", "unusable_fuel", "engine_oil", "passenger_service"),
}


@dataclass(frozen=True)
class ClassTwoInputs:
    """Everything the transport weight equations need (SI unless named otherwise)."""

    # design and landing gross mass, ultimate load factor, speeds and range
    W_dg: float  # design gross mass [kg] (take-off mass)
    W_l: float  # landing design mass [kg]
    N_z: float  # ultimate load factor (1.5 x limit)
    M_max: float  # maximum Mach number
    design_range: float  # [m]
    # wing
    S_w: float  # reference area [m^2]
    A: float  # aspect ratio
    tc_root: float  # root thickness ratio
    taper: float
    sweep: float  # quarter-chord sweep [rad]
    S_csw: float  # wing-mounted control surface area [m^2]
    b_w: float  # span [m]
    # horizontal tail
    S_ht: float
    A_h: float
    sweep_ht: float
    b_h: float  # span [m]
    L_t: float  # tail arm, wing to tail quarter-chord [m]
    S_e: float  # elevator area [m^2]
    F_w: float  # fuselage width at the horizontal tail [m]
    # vertical tail
    S_vt: float
    A_v: float
    sweep_vt: float
    tc_root_vt: float
    Ht_Hv: float  # 0 for a conventional tail, 1 for a T-tail
    S_r: float  # rudder area [m^2]
    # fuselage
    L_f: float  # length [m]
    D_f: float  # diameter (width = depth) [m]
    S_f: float  # wetted area [m^2]
    L_cabin: float  # passenger compartment length [m]
    K_door: float  # Raymer: 1.06 one side cargo door, 1.12 two
    K_Lg: float  # 1.12 fuselage-mounted main gear, else 1.0
    # landing gear
    N_gear: float  # gear load factor; ultimate landing load factor N_l = 1.5 N_gear
    L_m: float  # main gear length [m]
    L_n: float  # nose gear length [m]
    N_mw: int  # main wheels
    N_nw: int  # nose wheels
    N_mss: int  # main gear shock struts
    V_stall: float  # [m/s]
    # propulsion
    N_en: int
    W_en: float  # dry mass of one engine [kg]
    T_en: float  # rated thrust of one engine [N]
    nacelle_length: float  # [m]
    nacelle_width: float  # [m]
    S_n: float  # wetted area of one nacelle [m^2]
    K_tr: float  # 1.18 with thrust reverser
    L_ec: float  # engine controls routing length, engine front to cockpit, total [m]
    V_t: float  # total fuel volume [m^3]
    V_i: float  # integral tank volume [m^3]
    fuel_capacity: float  # [kg]
    N_t: int  # number of fuel tanks
    # crew and cabin
    flight_crew: int
    cabin_crew: int
    pax_first: int
    pax_business: int
    pax_tourist: int

    @property
    def passengers(self) -> int:
        return self.pax_first + self.pax_business + self.pax_tourist

    def with_(self, **changes) -> ClassTwoInputs:
        return replace(self, **changes)


def raymer_structure_propulsion(i: ClassTwoInputs) -> dict[str, float]:
    """Structure and propulsion masses [kg], Raymer ch. 15 cargo/transport equations."""
    Wdg, Wl = i.W_dg / LB, i.W_l / LB
    Sw, Scsw, bw = i.S_w / FT2, i.S_csw / FT2, i.b_w / FT
    Sht, Se, Lt, Fw, bh = i.S_ht / FT2, i.S_e / FT2, i.L_t / FT, i.F_w / FT, i.b_h / FT
    Svt = i.S_vt / FT2
    Lf, Df, Sf = i.L_f / FT, i.D_f / FT, i.S_f / FT2
    Wen = i.W_en / LB
    Nlt, Nw, Sn = i.nacelle_length / FT, i.nacelle_width / FT, i.S_n / FT2
    Vt, Vi = i.V_t / US_GAL, i.V_i / US_GAL
    Nz = i.N_z
    Nl = 1.5 * i.N_gear
    K_y, K_z = 0.3 * Lt, Lt  # tail radii of gyration, Raymer's suggestion

    m = {}
    m["wing"] = (
        0.0051
        * (Wdg * Nz) ** 0.557
        * Sw**0.649
        * i.A**0.5
        * i.tc_root**-0.4
        * (1 + i.taper) ** 0.1
        / np.cos(i.sweep)
        * Scsw**0.1
    )
    m["horizontal_tail"] = (
        0.0379
        * (1 + Fw / bh) ** -0.25
        * Wdg**0.639
        * Nz**0.10
        * Sht**0.75
        / Lt
        * K_y**0.704
        / np.cos(i.sweep_ht)
        * i.A_h**0.166
        * (1 + Se / Sht) ** 0.1
    )
    m["vertical_tail"] = (
        0.0026
        * (1 + i.Ht_Hv) ** 0.225
        * Wdg**0.556
        * Nz**0.536
        * Lt**-0.5
        * Svt**0.5
        * K_z**0.875
        / np.cos(i.sweep_vt)
        * i.A_v**0.35
        * i.tc_root_vt**-0.5
    )
    K_ws = 0.75 * (1 + 2 * i.taper) / (1 + i.taper) * bw * np.tan(i.sweep) / Lf
    m["fuselage"] = (
        0.3280
        * i.K_door
        * i.K_Lg
        * (Wdg * Nz) ** 0.5
        * Lf**0.25
        * Sf**0.302
        * (1 + K_ws) ** 0.04
        * (Lf / Df) ** 0.10
    )
    Vstall = i.V_stall / FT
    m["main_gear"] = (
        0.0106
        * Wl**0.888
        * Nl**0.25
        * (i.L_m / INCH) ** 0.4
        * i.N_mw**0.321
        * i.N_mss**-0.5
        * Vstall**0.1
    )
    m["nose_gear"] = 0.032 * Wl**0.646 * Nl**0.2 * (i.L_n / INCH) ** 0.5 * i.N_nw**0.45
    W_ec = 2.331 * Wen**0.901 * i.K_tr  # engine + contents
    m["nacelles"] = (
        0.6724 * 1.017 * Nlt**0.10 * Nw**0.294 * Nz**0.119 * W_ec**0.611 * i.N_en**0.984 * Sn**0.224
    )
    m["engines"] = i.N_en * Wen
    m["engine_controls"] = 5.0 * i.N_en + 0.80 * i.L_ec / FT
    m["starter"] = 49.19 * (i.N_en * Wen / 1000) ** 0.541
    m["fuel_system"] = 2.405 * Vt**0.606 / (1 + Vi / Vt) * i.N_t**0.5  # no protected tanks
    return {k: float(v) * LB for k, v in m.items()}


def flops_systems_operating(i: ClassTwoInputs) -> dict[str, float]:
    """Systems, furnishings and operating-item masses [kg], FLOPS transport equations
    (NASA/TM-2017-219627, eqs. 97, 101-108, 110, 113, 115, 119-121, 123, 124)."""
    XL, WF, DF = i.L_f / FT, i.D_f / FT, i.D_f / FT
    FPAREA = XL * WF  # eq. 62
    SW, B = i.S_w / FT2, i.b_w / FT
    VMAX, DG = i.M_max, i.W_dg / LB
    NFLCR, NPASS, NENG = i.flight_crew, i.passengers, i.N_en
    SFLAP = (i.S_csw + i.S_e + i.S_r) / FT2  # all movable surfaces
    DESRNG = i.design_range / NMI
    FNAC = i.nacelle_width / FT
    THRUST = i.T_en / LBF
    XLP = i.L_cabin / FT

    m = {}
    m["surface_controls"] = 1.1 * VMAX**0.52 * SFLAP**0.6 * DG**0.32  # eq. 97
    m["apu"] = 54 * FPAREA**0.3 + 5.4 * NPASS**0.9  # eq. 101
    m["instruments"] = 0.48 * FPAREA**0.57 * VMAX**0.5 * (10 + 2.5 * NFLCR + NENG)  # eq. 102
    m["hydraulics"] = (  # eq. 104, wing-mounted engines, 3,000 psi, fixed sweep
        0.57 * (FPAREA + 0.27 * SW) * (1 + 0.03 * NENG) * VMAX**0.33
    )
    m["electrical"] = (  # eq. 106
        92 * XL**0.4 * WF**0.14 * NENG**0.69 * (1 + 0.044 * NFLCR + 0.0015 * NPASS)
    )
    m["avionics"] = 15.8 * DESRNG**0.1 * NFLCR**0.7 * FPAREA**0.43  # eq. 108
    m["furnishings"] = (  # eq. 110
        127 * NFLCR
        + 112 * i.pax_first
        + 78 * i.pax_business
        + 44 * i.pax_tourist
        + 2.6 * XLP * (WF + DF)
    )
    m["air_conditioning"] = (  # eq. 113
        (3.2 * (FPAREA * DF) ** 0.6 + 9 * NPASS**0.83) * VMAX + 0.075 * m["avionics"]
    )
    m["anti_icing"] = B / math.cos(i.sweep) + 3.8 * FNAC * NENG + 1.5 * WF  # eq. 115
    m["crew"] = i.cabin_crew * 155 + NFLCR * 225  # eqs. 119-120 (crew complement is input)
    m["unusable_fuel"] = (  # eq. 121
        11.5 * NENG * THRUST**0.2 + 0.07 * SW + 1.6 * i.N_t * (i.fuel_capacity / LB) ** 0.28
    )
    m["engine_oil"] = 0.082 * NENG * THRUST**0.65  # eq. 123
    m["passenger_service"] = (  # eq. 124
        (5.164 * i.pax_first + 3.846 * i.pax_business + 2.529 * i.pax_tourist)
        * (DESRNG / VMAX) ** 0.225
    )
    return {k: float(v) * LB for k, v in m.items()}


def component_masses(i: ClassTwoInputs) -> dict[str, float]:
    """All component masses [kg], keyed as in ``GROUPS``."""
    return raymer_structure_propulsion(i) | flops_systems_operating(i)


def group_masses(masses: dict[str, float]) -> dict[str, float]:
    """Sum the component masses by group."""
    return {g: sum(masses[k] for k in keys) for g, keys in GROUPS.items()}


def empty_mass(masses: dict[str, float]) -> float:
    """Manufacturer's empty mass [kg]: structure + propulsion + systems."""
    g = group_masses(masses)
    return g["structure"] + g["propulsion"] + g["systems"]


def operating_empty_mass(masses: dict[str, float]) -> float:
    """Operating empty mass [kg]: empty + operating items (crew, unusable fuel, oil,
    passenger service)."""
    return empty_mass(masses) + group_masses(masses)["operating_items"]
