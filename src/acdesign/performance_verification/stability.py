"""Static and dynamic stability of the sized aircraft, on the AERO-04 flight-dynamics model.

**Balance.** Component masses (class II) are placed along the fuselage — the fixed items by
fractions of its length and the cabin, the wing group with the wing — and the wing is
positioned so that the mid-cruise CG falls at ``CG_TARGET`` of the MAC (a design choice).

**Derivatives** (stability axes, per rad), all estimated from the sized geometry:

* wing lift slope and aerodynamic centre: AERO-01 VLM with the Göthert rule;
* fuselage shift of the aerodynamic centre: −1.8 b_f h_f l_fn / (S c CLα) (Torenbeek,
  *Synthesis of Subsonic Airplane Design*, app. E);
* horizontal tail: its own VLM lift slope, η = 0.9, the VLM downwash gradient at the tail,
  and AERO-04's ``HorizontalTail.contributions()`` (Etkin & Reid / Nelson formulas) for its
  share of CL_a, Cm_a, CL_q, Cm_q, CL_adot, Cm_adot, CL_de, Cm_de;
* wing rolling derivatives Cl_b, Cl_p, Cl_r, Cl_da: AERO-01 VLM with sideslip, rotation and
  aileron incidence in the boundary condition;
* fin: VLM lift slope at an end-plate-corrected aspect ratio, the DATCOM sidewash fit
  η_v(1 + dσ/dβ) = 0.724 + 3.06 (S_v/S)/(1 + cos Λ) + 0.4 z_w/d + 0.009 A (as given by
  Nelson, *Flight Stability and Automatic Control*, ch. 2), and the classical tail-arm
  formulas for its contributions to every lateral derivative (Etkin & Reid ch. 5);
* fuselage Cn_b = −1.3 Vol / (S b) (Raymer, *Aircraft Design*, ch. 16);
* wing Cn_p ≈ −CL/8, Cn_r ≈ −CD0/4, Cn_b ≈ CL²/(4πA) (Etkin & Reid's strip-theory
  estimates).

Every geometric and efficiency factor below is an assumption. The derivatives feed AERO-04's
``Aircraft``: ``neutral_point_shift`` gives the static margin, ``trim`` / ``linearize`` /
``longitudinal_modes`` / ``lateral_modes`` the roots, judged against MIL-F-8785C Class III.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.external import stability as fd
from acdesign.external.atmosphere import isa
from acdesign.external.wing_aero import (
    Planform,
    _solve,
    downwash_gradient,
    lift_slope,
    roll_derivatives,
)
from acdesign.units import G0

CG_TARGET = 0.25  # mid-cruise CG / MAC aft of the MAC leading edge: design choice
ETA_HT = 0.90  # tail dynamic-pressure ratio
TAU_E, TAU_R, TAU_A = 0.45, 0.50, 0.40  # elevator, rudder, aileron effectiveness
DIHEDRAL = np.deg2rad(6.0)
TAIL_HEIGHT = 1.5  # horizontal tail above the wing chord plane [m]
WING_Z = 0.35  # wing root below the fuselage centreline, / fuselage diameter (low wing)
FIN_END_PLATE = 1.55  # effective / geometric fin aspect ratio
FIN_CP_HEIGHT = 0.40  # fin aerodynamic centre, fraction of fin height above the fuselage top
CN_DA_PER_CL = -0.2  # adverse aileron yaw: Cn_da = this x CL x Cl_da
NOSE_TO_CABIN = 4.0  # cockpit length [m]
RADII_OF_GYRATION = (0.25, 0.38, 0.46)  # R_x/(b/2), R_y/(L/2), R_z/((b+L)/4)

# fixed items: x / fuselage length
X_FRACTION = {
    "fuselage": 0.45,
    "nose_gear": 0.10,
    "apu": 0.95,
    "horizontal_tail": None,  # with the wing (the tail arm is fixed)
}


@dataclass(frozen=True)
class Balance:
    x_wing_le_root: float  # wing root leading edge, from the nose [m]
    x_mac_le: float  # MAC leading edge, from the nose [m]
    x_cg: float  # mid-cruise CG [m]
    h_cg: float  # (x_cg − x_mac_le) / MAC
    h_cg_oew: float  # empty aircraft
    mass: float  # mid-cruise mass [kg]


def balance(a) -> Balance:
    """Place the wing so the mid-cruise CG is at ``CG_TARGET`` of the MAC."""
    g, m = a.geometry, a.masses
    w = g.wing
    L = g.fuselage_length
    cab_mid = NOSE_TO_CABIN + g.cabin_length / 2
    W_mid_fuel = a.fuel_mass * 0.5  # half the fuel at mid-cruise (in the wing)

    # x relative to the wing root LE (moving group) or to the nose (fixed group)
    tan_le = np.tan(w.sweep_at(0.0))
    x_eng_rel = 0.282 * w.b / 2 * tan_le - 0.6 * g.nacelle_length  # engines ahead of the LE
    moving = {
        "wing": w.x_mac_le + 0.40 * w.mac,
        "main_gear": w.x_mac_le + 0.55 * w.mac,
        "engines": x_eng_rel,
        "nacelles": x_eng_rel,
        "fuel": w.x_mac_le + 0.40 * w.mac,
        "horizontal_tail": w.x_mac_le + 0.25 * w.mac + g.l_ht,
        "vertical_tail": w.x_mac_le + 0.25 * w.mac + g.l_vt,
    }
    fixed = {k: X_FRACTION.get(k, 0.0) * L for k in ("fuselage", "nose_gear", "apu")}
    cabin_items = ("furnishings", "passenger_service", "crew", "air_conditioning")
    fixed |= {k: cab_mid for k in cabin_items}
    rest = [k for k in m if k not in moving and k not in fixed]
    fixed |= {k: 0.45 * L for k in rest}  # systems, controls, fuel system, oil...

    def x_cg(x_le, with_payload=True, fuel=W_mid_fuel):
        tot = mom = 0.0
        for k, mk in m.items():
            x = x_le + moving[k] if k in moving else fixed[k]
            tot, mom = tot + mk, mom + mk * x
        if fuel:
            tot, mom = tot + fuel, mom + fuel * (x_le + moving["fuel"])
        if with_payload:
            tot, mom = tot + a.mission.payload, mom + a.mission.payload * cab_mid
        return mom / tot, tot

    # x_cg is linear in x_le: solve x_cg(x_le) = x_le + x_mac_le + CG_TARGET * MAC
    target = lambda x_le: x_le + w.x_mac_le + CG_TARGET * w.mac  # noqa: E731
    f0 = x_cg(0.0)[0] - target(0.0)
    f1 = x_cg(1.0)[0] - target(1.0)
    x_le = -f0 / (f1 - f0)
    xc, mass = x_cg(x_le)
    x_mac = x_le + w.x_mac_le
    xe, _ = x_cg(x_le, with_payload=False, fuel=0.0)
    return Balance(x_le, x_mac, xc, (xc - x_mac) / w.mac, (xe - x_mac) / w.mac, mass)


def wing_aerodynamic_centre(w: Planform, M: float) -> float:
    """Wing aerodynamic centre / MAC aft of the MAC leading edge (VLM, Göthert)."""
    beta = np.sqrt(1 - M**2)
    s = _solve(w, M)  # stretched wing, moments about its root quarter chord
    x_ac_stretched = -s.Cm * s.wing.mean_aerodynamic_chord / s.CL
    x_ac = beta * x_ac_stretched  # back to physical x
    return float((x_ac + 0.25 * w.c_root - w.x_mac_le) / w.mac)


@dataclass(frozen=True)
class StabilityModel:
    aircraft: object  # flightdyn Aircraft
    balance: Balance
    V: float
    h: float
    h_ac_wing: float
    h_ac_wb: float
    h_n_classic: float  # neutral point / MAC by the textbook formula
    static_margin: float  # from AERO-04's neutral_point_shift
    eps_a: float
    a_wb: float
    a_t: float


def stability_model(a) -> StabilityModel:
    g = a.geometry
    w, ht, vt = g.wing, g.htail, g.vtail
    m = a.mission
    h, M = m.cruise_altitude, m.cruise_mach
    atm = isa(h)
    V = M * float(atm.a)
    q = 0.5 * float(atm.rho) * V**2
    bal = balance(a)
    CL = bal.mass * G0 / (q * w.S)

    a_w = lift_slope(w, M)
    h_ac_w = wing_aerodynamic_centre(w, M)
    l_fn = bal.x_wing_le_root
    D = g.fuselage_diameter
    h_ac_wb = h_ac_w - 1.8 * D * D * l_fn / (w.S * w.mac * a_w)
    a_wb = a_w  # wing-body lift slope ~ wing (assumption)

    a_t = lift_slope(ht, M)
    eps_a = downwash_gradient(w, g.l_ht, TAIL_HEIGHT, M)
    S_t = ht.S
    x_ac_t = bal.x_mac_le + 0.25 * w.mac + g.l_ht  # tail MAC quarter chord ~ its ac
    lt_cg = x_ac_t - bal.x_cg
    VH_cg = S_t * lt_cg / (w.S * w.mac)
    tail = fd.HorizontalTail(
        eta_at_VH=ETA_HT * a_t * VH_cg, lt_c=lt_cg / w.mac, eps_a=eps_a, tau=TAU_E
    )  # noqa: E501
    t = tail.contributions()

    # classic stick-fixed neutral point with the tail arm from the wing-body ac
    VH_ac = S_t * (x_ac_t - (bal.x_mac_le + h_ac_wb * w.mac)) / (w.S * w.mac)
    h_n = (h_ac_wb + ETA_HT * VH_ac * a_t / a_wb * (1 - eps_a)) / (
        1 + ETA_HT * S_t / w.S * a_t / a_wb * (1 - eps_a)
    )

    # fin
    A_v_eff = FIN_END_PLATE * vt.AR
    a_v = lift_slope(Planform(vt.S, A_v_eff, vt.taper, vt.sweep), M)
    sidewash = 0.724 + 3.06 * vt.S / w.S / (1 + np.cos(w.sweep)) + 0.4 * WING_Z + 0.009 * w.AR
    l_v = bal.x_mac_le + 0.25 * w.mac + g.l_vt - bal.x_cg
    z_v = D / 2 + FIN_CP_HEIGHT * vt.b  # above the x axis
    b = w.b
    CY_b_v = -a_v * sidewash * vt.S / w.S

    rd = roll_derivatives(w, DIHEDRAL, CL, M)
    vol = np.pi / 4 * D**2 * g.fuselage_length * 0.8
    CD0 = a.polar.CD0
    CL_a = a_wb + t["CL_a"]
    d = fd.StabilityDerivatives(
        alpha0=0.0,
        mach0=M,
        CL0=CL,
        CD0=float(a.polar.CD(CL, M)),
        CL_a=CL_a,
        CD_a=2 * a.polar.K * CL * CL_a,
        Cm_a=a_wb * (bal.h_cg - h_ac_wb) + t["Cm_a"],
        CL_de=t["CL_de"],
        Cm_de=t["Cm_de"],
        CL_q=t["CL_q"],
        Cm_q=1.1 * t["Cm_q"],  # wing and fuselage add ~10 % to the tail's (assumption)
        CL_adot=t["CL_adot"],
        Cm_adot=t["Cm_adot"],
        CY_b=CY_b_v,
        Cl_b=rd.Cl_b + CY_b_v * z_v / b,
        Cn_b=-CY_b_v * l_v / b - 1.3 * vol / (w.S * b) + CL**2 / (4 * np.pi * w.AR),
        CY_p=2 * CY_b_v * z_v / b,
        Cl_p=rd.Cl_p + 2 * CY_b_v * (z_v / b) ** 2,
        Cn_p=-CL / 8 - 2 * CY_b_v * l_v * z_v / b**2,
        CY_r=-2 * CY_b_v * l_v / b,
        Cl_r=rd.Cl_r - 2 * CY_b_v * z_v * l_v / b**2,
        Cn_r=-CD0 / 4 + 2 * CY_b_v * (l_v / b) ** 2,
        Cl_da=TAU_A * rd.Cl_da,
        Cn_da=CN_DA_PER_CL * CL * TAU_A * rd.Cl_da,
        CY_dr=a_v * sidewash * TAU_R * vt.S / w.S,
        Cl_dr=a_v * sidewash * TAU_R * vt.S / w.S * z_v / b,
        Cn_dr=-a_v * sidewash * TAU_R * vt.S / w.S * l_v / b,
        lateral_axes="stability",
    )
    L = g.fuselage_length
    kx, ky, kz = RADII_OF_GYRATION
    mass = bal.mass
    mp = fd.MassProperties(
        mass=mass,
        Ixx=mass * (kx * b / 2) ** 2,
        Iyy=mass * (ky * L / 2) ** 2,
        Izz=mass * (kz * (b + L) / 4) ** 2,
    )
    ac = fd.Aircraft("sized design", mp, fd.Geometry(w.S, b, w.mac), d, fd.ThrustLine())
    return StabilityModel(
        ac, bal, V, h, h_ac_w, h_ac_wb, h_n, float(fd.neutral_point_shift(ac)), eps_a, a_wb, a_t
    )


@dataclass(frozen=True)
class Modes:
    short_period: object
    phugoid: object
    dutch_roll: object
    roll: object
    spiral: object
    trim: object


def modes(model: StabilityModel) -> Modes:
    t = fd.trim(model.aircraft, model.V, model.h)
    lin = fd.linearize(model.aircraft, t)
    lon = fd.longitudinal_modes(fd.longitudinal(lin).A)
    lat = fd.lateral_modes(fd.lateral(lin, model.V).A)
    return Modes(
        lon["short_period"], lon["phugoid"], lat["dutch_roll"], lat["roll"], lat["spiral"], t
    )  # noqa: E501


# MIL-F-8785C Level 1, Class III (heavy transports); flight-phase category B (cruise)
LEVEL1_CAT_B = {
    "short-period damping": (0.30, 2.00),
    "phugoid damping (min)": 0.04,
    "dutch-roll damping (min)": 0.08,
    "dutch-roll zeta*wn (min) [rad/s]": 0.15,
    "dutch-roll frequency (min) [rad/s]": 0.4,
    "roll time constant (max) [s]": 1.4,
    "spiral time to double (min) [s]": 20.0,
}


def flying_qualities(mo: Modes) -> dict[str, tuple[float, bool]]:
    """Each MIL-F-8785C Level 1 (Class III, Cat. B) requirement: (value, met)."""
    sp, ph, dr, ro, spi = mo.short_period, mo.phugoid, mo.dutch_roll, mo.roll, mo.spiral
    lo, hi = LEVEL1_CAT_B["short-period damping"]
    t2 = spi.time_to_half  # negative: time to double
    spiral_ok = t2 > 0 or -t2 >= LEVEL1_CAT_B["spiral time to double (min) [s]"]
    return {
        "short-period damping": (sp.zeta, lo <= sp.zeta <= hi),
        "phugoid damping (min)": (ph.zeta, ph.zeta >= LEVEL1_CAT_B["phugoid damping (min)"]),
        "dutch-roll damping (min)": (dr.zeta, dr.zeta >= LEVEL1_CAT_B["dutch-roll damping (min)"]),  # noqa: E501
        "dutch-roll zeta*wn (min) [rad/s]": (dr.zeta * dr.wn, dr.zeta * dr.wn >= 0.15),
        "dutch-roll frequency (min) [rad/s]": (dr.wn, dr.wn >= 0.4),
        "roll time constant (max) [s]": (ro.time_constant, ro.time_constant <= 1.4),
        "spiral time to double (min) [s]": (-t2 if t2 < 0 else float("inf"), spiral_ok),
    }
