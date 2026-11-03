"""Wing aerodynamics from the AERO-01 vortex lattice method (``aero``).

The VLM is incompressible, flat (camber enters through the zero-lift angle) and
nondimensional (V = 1, rho = 1). Three things are added here:

* **Planform bookkeeping** for a straight-tapered wing of given area: chords, the mean
  aerodynamic chord and where it sits, sweep of any chord line (``Planform``).
* **Compressibility** by the Prandtl–Glauert–Göthert rule: the wing in subsonic compressible
  flow has the lift slope of the *incompressible* wing stretched in x by 1/β (β = √(1−M²)),
  divided by β (Katz & Plotkin, *Low-Speed Aerodynamics*, ch. 13). The stretched wing has
  aspect ratio βA and tan Λ' = tan Λ / β, which is exactly how the DATCOM/Helmbold formula
  is built — the test compares the two.
* **Downwash at the tail** from the solved horseshoe strengths through the Biot–Savart law,
  scaled to Mach by the lift-slope ratio (the DATCOM rule), with the DATCOM empirical formula
  as a cross-check.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

import numpy as np
from aero.vortex_lattice_3d import Wing, solve_vlm
from aero.vortex_lattice_3d.biot_savart import horseshoe_velocity

ALPHA = np.deg2rad(2.0)  # small angle for slopes: the flat lattice is linear in alpha
# AERO-01's default mesh, with an odd strip count: a strip is then centred on the symmetry
# plane, where the tail sits. Induced velocity evaluated *at* a trailing-vortex node (as with
# an even count) is the classic discrete-vortex error and halves the downwash there.
N_SPAN, N_CHORD = 41, 6


@dataclass(frozen=True)
class Planform:
    """Straight-tapered trapezoidal wing (or tail) of reference area ``S`` [m²]."""

    S: float
    AR: float
    taper: float
    sweep: float  # quarter-chord sweep [rad]

    @property
    def b(self) -> float:
        return float(np.sqrt(self.AR * self.S))

    @property
    def c_root(self) -> float:
        return 2.0 * self.S / (self.b * (1.0 + self.taper))

    @property
    def c_tip(self) -> float:
        return self.taper * self.c_root

    @property
    def mac(self) -> float:
        """Mean aerodynamic chord: (2/3) c_r (1 + λ + λ²)/(1 + λ)."""
        lam = self.taper
        return 2.0 / 3.0 * self.c_root * (1 + lam + lam**2) / (1 + lam)

    @property
    def y_mac(self) -> float:
        """Spanwise station of the MAC: (b/6)(1 + 2λ)/(1 + λ)."""
        return self.b / 6.0 * (1 + 2 * self.taper) / (1 + self.taper)

    @property
    def x_mac_qc(self) -> float:
        """x of the MAC quarter chord, aft of the root quarter chord."""
        return self.y_mac * np.tan(self.sweep)

    @property
    def x_mac_le(self) -> float:
        """x of the MAC leading edge, aft of the root leading edge."""
        return self.x_mac_qc + 0.25 * self.c_root - 0.25 * self.mac

    def sweep_at(self, frac: float) -> float:
        """Sweep of the chord line at fraction ``frac`` of the chord (0 = LE)."""
        return float(
            np.arctan(
                np.tan(self.sweep)
                - 4.0 / self.AR * (frac - 0.25) * (1 - self.taper) / (1 + self.taper)
            )
        )

    def chord(self, y) -> np.ndarray:
        return self.c_root * (1 - (1 - self.taper) * 2 * np.abs(np.asarray(y, float)) / self.b)

    def vlm_wing(self, M: float = 0.0) -> Wing:
        """The AERO-01 wing; for M > 0 the Göthert-stretched equivalent wing."""
        beta = np.sqrt(1.0 - M**2)
        c_r = self.c_root / beta
        return Wing(
            self.b,
            lambda eta: c_r * (1 - (1 - self.taper) * np.asarray(eta, float)),
            sweep=float(np.arctan(np.tan(self.sweep) / beta)),
        )


@cache
def _solve(p: Planform, M: float, alpha: float = ALPHA):
    return solve_vlm(p.vlm_wing(M), alpha, N_SPAN, N_CHORD)


def lift_slope(p: Planform, M: float = 0.0) -> float:
    """dCL/dα [1/rad] at Mach ``M`` (VLM + Göthert), per unit reference area S."""
    beta = np.sqrt(1.0 - M**2)
    return _solve(p, M).CL / ALPHA / beta


def lift_slope_datcom(p: Planform, M: float = 0.0, eta: float = 1.0) -> float:
    """DATCOM/Helmbold semi-empirical lift slope (Raymer, *Aircraft Design*, ch. 12), with
    section-slope factor ``eta`` = c_lα/2π (1 for the thin-airfoil 2π the VLM assumes)."""
    beta2 = 1.0 - M**2
    tan_hc = np.tan(p.sweep_at(0.5))
    A = p.AR
    return 2 * np.pi * A / (2 + np.sqrt(4 + A**2 * beta2 / eta**2 * (1 + tan_hc**2 / beta2)))


def span_efficiency(p: Planform) -> float:
    """Inviscid span efficiency CL²/(π A CDi) of the untwisted wing (Trefftz plane)."""
    return _solve(p, 0.0).span_efficiency


def span_loading(p: Planform) -> tuple[np.ndarray, np.ndarray]:
    """(y [m], c·cl/(CL·c_avg)) at the strip mid-points, normalised so the mean over the
    span is 1: the lift per unit span at total lift L is L/b times this shape."""
    s = _solve(p, 0.0)
    return s.y_mid * p.b / s.wing.span, s.span_loading / s.CL


def induced_velocity(solution, point) -> np.ndarray:
    """Velocity (per unit free-stream speed) induced at ``point`` (x, y, z) by all the
    horseshoe vortices of a solved lattice (Biot–Savart, AERO-01)."""
    lat = solution.lattice
    a = lat.bound_a.reshape(-1, 3)
    b = lat.bound_b.reshape(-1, 3)
    v = horseshoe_velocity(np.asarray(point, float)[None, :], a, b)
    return np.einsum("ik,i->k", v, solution.gamma.reshape(-1))


def downwash_gradient(p: Planform, l_t: float, h_t: float, M: float = 0.0) -> float:
    """dε/dα at a point ``l_t`` [m] aft of the MAC quarter chord and ``h_t`` [m] above the
    wing's chord plane, on the centreline, from the solved incompressible lattice; scaled to
    Mach by CLα(M)/CLα(0) (DATCOM)."""
    s = _solve(p, 0.0)
    w = induced_velocity(s, (p.x_mac_qc + l_t, 0.0, h_t))[2]
    return float(-w / s.alpha * lift_slope(p, M) / lift_slope(p, 0.0))


def downwash_gradient_datcom(p: Planform, l_t: float, h_t: float, M: float = 0.0) -> float:
    """DATCOM empirical dε/dα (Raymer, *Aircraft Design*, ch. 16):
    4.44 [K_A K_λ K_H √cos Λ]^1.19 · CLα(M)/CLα(0)."""
    A, lam, b = p.AR, p.taper, p.b
    K_A = 1 / A - 1 / (1 + A**1.7)
    K_lam = (10 - 3 * lam) / 7
    K_H = (1 - abs(h_t / b)) / (2 * l_t / b) ** (1 / 3)
    de = 4.44 * (K_A * K_lam * K_H * np.sqrt(np.cos(p.sweep))) ** 1.19
    return float(de * lift_slope_datcom(p, M) / lift_slope_datcom(p, 0.0))


def _rolling_moment(
    p: Planform,
    dihedral: float,
    alpha: float,
    beta: float = 0.0,
    p_hat: float = 0.0,
    r_hat: float = 0.0,
    aileron: float = 0.0,
    aileron_span=(0.70, 0.95),
) -> tuple[float, float]:
    """(CL, Cl) of the wing in body axes (x forward, y right, z down; Cl > 0 right wing
    down) from the AERO-01 lattice with sideslip, roll and yaw rate in the boundary
    condition and the Kutta–Joukowski forces. ``aileron`` [rad] is the incidence change of
    the aileron strips, positive for right wing down (right aileron trailing edge up, left
    down: the AERO-04 / CR-2144 convention). Lattice axes: x aft, y right, z up; V = 1."""
    from aero.vortex_lattice_3d.geometry import build_lattice
    from aero.vortex_lattice_3d.vlm import influence_matrix

    wing = Wing(p.b, lambda eta: p.c_root * (1 - (1 - p.taper) * np.asarray(eta, float)),
                sweep=p.sweep, dihedral=dihedral)  # fmt: skip
    lat = build_lattice(wing, N_SPAN, N_CHORD)
    v_inf = np.array([np.cos(alpha) * np.cos(beta), -np.sin(beta), np.sin(alpha) * np.cos(beta)])
    omega = np.array([-p_hat * 2 / p.b, 0.0, -r_hat * 2 / p.b])  # body (p, q, r) in lattice axes
    normal = lat.normal
    if aileron:
        y_c = lat.control[..., 1]
        eta = np.abs(y_c) / (p.b / 2)
        on = (eta >= aileron_span[0]) & (eta <= aileron_span[1])
        d = np.where(on, np.where(y_c > 0, -aileron, aileron), 0.0)[..., None]
        normal = normal * np.cos(d) + np.array([1.0, 0.0, 0.0]) * np.sin(d)
    vel = v_inf - np.cross(omega, lat.control)
    rhs = -np.sum(normal * vel, axis=-1).reshape(-1)
    gamma = np.linalg.solve(influence_matrix(lat), rhs).reshape(lat.control.shape[:2])
    mid = 0.5 * (lat.bound_a + lat.bound_b)
    F = gamma[..., None] * np.cross(v_inf - np.cross(omega, mid), lat.bound_b - lat.bound_a)
    S = float(lat.area.sum())
    lift = float(np.sum(F[..., 2]) * np.cos(alpha) - np.sum(F[..., 0]) * np.sin(alpha))
    roll_lattice = float(np.sum(np.cross(mid, F)[..., 0]))
    return 2 * lift / S, -2 * roll_lattice / (S * p.b)


@dataclass(frozen=True)
class RollDerivatives:
    Cl_b: float
    Cl_p: float
    Cl_r: float
    Cl_da: float  # per radian of aileron incidence change (multiply by τ for deflection)


def roll_derivatives(p: Planform, dihedral: float, CL: float, M: float = 0.0) -> RollDerivatives:
    """Wing rolling-moment derivatives (body axes, per rad) at lift coefficient ``CL``, by
    central differences of the linear lattice; scaled to Mach by CLα(M)/CLα(0) (the
    DATCOM practice for the lift-proportional derivatives)."""
    a0 = lift_slope(p, 0.0)
    alpha = CL / a0
    d = 1e-3
    k = lift_slope(p, M) / a0

    def diff(**kw):
        name, _ = next(iter(kw.items()))
        hi = _rolling_moment(p, dihedral, alpha, **{name: d})[1]
        lo = _rolling_moment(p, dihedral, alpha, **{name: -d})[1]
        return (hi - lo) / (2 * d)

    return RollDerivatives(
        Cl_b=k * diff(beta=1), Cl_p=k * diff(p_hat=1), Cl_r=k * diff(r_hat=1),
        Cl_da=k * diff(aileron=1),
    )  # fmt: skip
