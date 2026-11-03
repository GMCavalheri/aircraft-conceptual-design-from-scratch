"""Flight dynamics from AERO-04 (``flightdyn``): the aircraft model, trim, linearization,
modal analysis, the stick-fixed neutral point and the horizontal-tail contributions."""

from __future__ import annotations

from flightdyn.aero_derivatives import Geometry, StabilityDerivatives
from flightdyn.aircraft import Aircraft, MassProperties, ThrustLine
from flightdyn.linearization import lateral, linearize, longitudinal
from flightdyn.modal_analysis import lateral_modes, longitudinal_modes
from flightdyn.trade_studies import HorizontalTail, move_cg, neutral_point_shift
from flightdyn.trim_solver import trim

__all__ = [
    "Aircraft",
    "Geometry",
    "HorizontalTail",
    "MassProperties",
    "StabilityDerivatives",
    "ThrustLine",
    "lateral",
    "lateral_modes",
    "linearize",
    "longitudinal",
    "longitudinal_modes",
    "move_cg",
    "neutral_point_shift",
    "trim",
]
