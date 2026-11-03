"""Simple geometric estimates shared by the weight and drag build-ups."""

from __future__ import annotations

import numpy as np


def fuselage_wetted_area(length: float, diameter: float) -> float:
    """Wetted area [m²] of a fuselage of fineness L/D with nose and tail cones:
    π D L (1 − 2/λ)^(2/3) (1 + 1/λ²), λ = L/D (Torenbeek, *Synthesis of Subsonic Airplane
    Design*, app. F)."""
    lam = length / diameter
    return float(np.pi * diameter * length * (1 - 2 / lam) ** (2 / 3) * (1 + 1 / lam**2))


def surface_wetted_area(exposed_area: float, tc: float) -> float:
    """Wetted area [m²] of a wing or tail from its exposed planform area:
    S_exp (1.977 + 0.52 t/c), Raymer's formula for t/c > 0.05 (*Aircraft Design*, ch. 7)."""
    return float(exposed_area * (1.977 + 0.52 * tc))


def nacelle_wetted_area(length: float, diameter: float) -> float:
    """Wetted area [m²] of a nacelle approximated as a cylinder (assumption)."""
    return float(np.pi * diameter * length)
