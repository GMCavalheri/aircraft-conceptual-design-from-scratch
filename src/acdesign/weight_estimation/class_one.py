"""Class I sizing: take-off gross weight from the empty-weight fraction and the mission fuel
fraction, iterated to closure (Raymer, *Aircraft Design*, ch. 3).

    W0 = (W_crew + W_payload) / (1 - Wf/W0 - We/W0(W0))

The empty-weight fraction is Raymer's historical regression for jet transports,
We/W0 = A · W0^C with W0 in lb (A = 1.02, C = -0.06), and the cruise L/D comes from the
wetted aspect ratio, (L/D)max = K_LD √(A / (S_wet/S_ref)) with K_LD = 15.5 for civil jets,
cruising at 0.866 (L/D)max (the L/D of best jet range). All three are Raymer's.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.units import LB
from acdesign.weight_estimation.fractions import FuelFractions, mission_fractions

A_JET_TRANSPORT, C_JET_TRANSPORT = 1.02, -0.06
K_LD_CIVIL_JET = 15.5
JET_CRUISE_LD_RATIO = 0.866  # (L/D)cruise / (L/D)max for best jet range: √3/2


def empty_weight_fraction(W0_mass: float, A: float = A_JET_TRANSPORT, C: float = C_JET_TRANSPORT):
    """We/W0 for a take-off mass ``W0_mass`` [kg] (the regression is in pounds)."""
    return A * (W0_mass / LB) ** C


def max_lift_to_drag(aspect_ratio: float, wetted_area_ratio: float) -> float:
    """(L/D)max from the wetted aspect ratio A / (S_wet/S_ref)."""
    return K_LD_CIVIL_JET * np.sqrt(aspect_ratio / wetted_area_ratio)


@dataclass(frozen=True)
class ClassOneResult:
    W0: float  # take-off mass [kg]
    empty_fraction: float
    fractions: FuelFractions
    history: tuple[float, ...]  # W0 at every iteration [kg]

    @property
    def fuel(self) -> float:
        return self.fractions.fuel * self.W0

    @property
    def empty(self) -> float:
        return self.empty_fraction * self.W0


def size_class_one(
    mission,
    V: float,
    LD_max: float,
    tsfc_cruise: float,
    tsfc_hold: float,
    crew: float,
    W0_guess: float = 70000.0,
    tol: float = 1e-9,
) -> ClassOneResult:
    """Fixed-point iteration on W0 [kg]; ``crew`` is the crew mass [kg]."""
    fr = mission_fractions(mission, V, JET_CRUISE_LD_RATIO * LD_max, LD_max, tsfc_cruise, tsfc_hold)
    W0, history = W0_guess, [W0_guess]
    for _ in range(200):
        new = (crew + mission.payload) / (1.0 - fr.fuel - empty_weight_fraction(W0))
        history.append(new)
        if abs(new - W0) < tol * new:
            return ClassOneResult(new, empty_weight_fraction(new), fr, tuple(history))
        W0 = new
    raise RuntimeError("class I sizing did not converge")
