"""Structural building blocks from AERO-02 (``structures``): materials (MIL-HDBK-5J
B-basis), the Macaulay beam solver, thin-walled sections, plate and column buckling, and the
handbook S-N curves."""

from __future__ import annotations

import numpy as np
from structures.beam_theory import Beam, DistributedLoad, PointLoad, Support, thin_walled
from structures.buckling import compression_k, johnson_stress, plate_critical_stress, shear_k
from structures.fatigue import handbook_curve
from structures.materials import IsotropicMaterial, isotropic

__all__ = [
    "IsotropicMaterial",
    "box_section",
    "cantilever_shear_moment",
    "compression_k",
    "handbook_curve",
    "isotropic",
    "johnson_stress",
    "plate_critical_stress",
    "shear_k",
]


def cantilever_shear_moment(x, w, point_loads=()) -> tuple[np.ndarray, np.ndarray]:
    """Shear and bending moment along a cantilever fixed at x = 0 and free at x[-1], under a
    piecewise-linear distributed load ``w`` [N/m] given at the nodes ``x`` and point loads
    ``(x_p, P)`` [m, N] (positive up), from the AERO-02 beam solver. Statically
    determinate, so the stiffness given to the solver does not matter."""
    x, w = np.asarray(x, float), np.asarray(w, float)
    beam = Beam(float(x[-1]), 1.0).add(Support(0.0, "fixed"))
    for i in range(len(x) - 1):
        beam.add(DistributedLoad(float(x[i]), float(x[i + 1]), float(w[i]), float(w[i + 1])))
    for xp, P in point_loads:
        beam.add(PointLoad(float(xp), float(P)))
    sol = beam.solve()
    return np.asarray(sol.shear(x), float), np.asarray(sol.moment(x), float)


def box_section(width: float, height: float, t_upper: float, t_lower: float, t_web: float):
    """Closed rectangular box (covers and two spar webs on its mid-line): I about the
    horizontal axis and J (Bredt–Batho), from AERO-02's thin-walled section."""
    w, h = width, height
    s = thin_walled(
        [
            ((0.0, h), (w, h), t_upper),
            ((w, h), (w, 0.0), t_web),
            ((w, 0.0), (0.0, 0.0), t_lower),
            ((0.0, 0.0), (0.0, h), t_web),
        ],
        closed=True,
    )
    return s.I, s.J
