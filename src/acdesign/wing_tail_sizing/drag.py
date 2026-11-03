"""Component drag build-up (Raymer, *Aircraft Design*, ch. 12) and compressibility drag.

Parasite drag of each component c, referenced to the wing area:

    CD0 = Σ C_f,c · FF_c · Q_c · S_wet,c / S_ref  · (1 + leakage and protuberances)

* C_f: turbulent flat-plate skin friction, 0.455 / ((log10 Re)^2.58 (1 + 0.144 M²)^0.65),
  with Re capped at the surface-roughness cutoff 38.21 (l/k)^1.053;
* FF: form factors — wing and tails [1 + 0.6/(x/c)_m · t/c + 100 (t/c)⁴]
  [1.34 M^0.18 cos(Λ_m)^0.28], fuselage 1 + 60/f³ + f/400, nacelle 1 + 0.35/f (f = l/d);
* Q: interference factors (the values below are Raymer's for each installation).

Wave drag (Korn equation with Lock's fourth-power law, as used by Malone & Mason, *J.
Aircraft* 32(2), 1995): M_dd = κ/cos Λ − (t/c)/cos² Λ − CL/(10 cos³ Λ),
M_crit = M_dd − (0.1/80)^(1/3), ΔCD_wave = 20 (M − M_crit)⁴ above M_crit.

The Oswald efficiency combines the VLM's inviscid span efficiency with the fuselage's
loss of lift and the lift dependence of viscous drag (Kroo, *Aircraft Design: Synthesis and
Analysis*, Stanford): 1/e = 1/(e_inv (1 − 2 (d_f/b)²)) + 0.38 CD0 π A.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.external.atmosphere import isa

ROUGHNESS = 4.05e-6  # [m] production sheet metal, 1.33e-5 ft (Raymer, ch. 12)
LEAKAGE_PROTUBERANCE = 0.03  # fraction of parasite drag, jet transport: assumption
KORN_KAPPA = 0.95  # supercritical-section technology factor: assumption
Q_WING, Q_TAIL, Q_FUSELAGE, Q_NACELLE = 1.0, 1.04, 1.0, 1.3  # Raymer's interference factors


def viscosity(T):
    """Dynamic viscosity of air [Pa s], Sutherland's law."""
    return 1.458e-6 * T**1.5 / (T + 110.4)


def skin_friction(length: float, M: float, h: float, roughness: float = ROUGHNESS) -> float:
    """Turbulent flat-plate C_f at Mach ``M``, altitude ``h`` [m], over ``length`` [m]."""
    atm = isa(h)
    V = M * float(atm.a)
    Re = float(atm.rho) * V * length / viscosity(float(atm.T))
    Re = min(Re, 38.21 * (length / roughness) ** 1.053)
    return 0.455 / (np.log10(Re) ** 2.58 * (1 + 0.144 * M**2) ** 0.65)


def ff_lifting(tc: float, M: float, sweep_m: float, xc_m: float = 0.4) -> float:
    """Form factor of a wing or tail; ``sweep_m`` at the maximum-thickness line."""
    return (1 + 0.6 / xc_m * tc + 100 * tc**4) * (1.34 * M**0.18 * np.cos(sweep_m) ** 0.28)


def ff_fuselage(fineness: float) -> float:
    return 1 + 60 / fineness**3 + fineness / 400


def ff_nacelle(fineness: float) -> float:
    return 1 + 0.35 / fineness


@dataclass(frozen=True)
class Component:
    name: str
    wetted_area: float  # [m^2]
    length: float  # reference length for Re [m]: MAC, or body length
    form_factor: float
    interference: float


def parasite_drag(components, S_ref: float, M: float, h: float) -> dict[str, float]:
    """CD0 contribution of every component, plus leakage and protuberances."""
    cd = {
        c.name: skin_friction(c.length, M, h)
        * c.form_factor
        * c.interference
        * c.wetted_area
        / S_ref
        for c in components
    }
    cd["leakage and protuberances"] = LEAKAGE_PROTUBERANCE * sum(cd.values())
    return cd


def oswald_kroo(e_inv: float, d_fus: float, span: float, CD0: float, AR: float) -> float:
    s = 1 - 2 * (d_fus / span) ** 2
    return 1 / (1 / (e_inv * s) + 0.38 * CD0 * np.pi * AR)


@dataclass(frozen=True)
class WaveDrag:
    """Korn/Lock compressibility drag of a wing of mean t/c and quarter-chord sweep
    (applied with the half-chord-ish quarter-chord sweep, as Malone & Mason do)."""

    tc: float
    sweep: float
    kappa: float = KORN_KAPPA

    def drag_divergence_mach(self, CL):
        c = np.cos(self.sweep)
        return self.kappa / c - self.tc / c**2 - np.asarray(CL, float) / (10 * c**3)

    def critical_mach(self, CL):
        return self.drag_divergence_mach(CL) - (0.1 / 80) ** (1 / 3)

    def __call__(self, M, CL):
        dM = np.maximum(M - self.critical_mach(CL), 0.0)
        return 20 * dM**4
