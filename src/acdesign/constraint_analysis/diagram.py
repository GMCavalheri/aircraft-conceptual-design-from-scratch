"""The constraint diagram of a mission: every requirement as T/W(W/S), the feasible region
and the design point.

Requirements (FAR 25 paragraphs as cited; speeds and gradients are the regulation's
minimums, the configurations are assumptions):

* take-off field length at MTOW, sea level ISA (Loftin);
* landing field length at MLW (Loftin) — a maximum W/S;
* second-segment climb, one engine out (25.121(b)): 2.4 % for twins, take-off flaps, gear
  up, V2 = 1.2 V_stall, take-off thrust;
* approach climb, one engine out (25.121(d)): 2.1 %, approach (= take-off) flaps, gear up,
  1.3 V_stall, at landing weight;
* landing climb, all engines (25.119): 3.2 %, landing flaps, gear down, 1.3 V_stall;
* cruise at the design Mach and initial altitude, maximum climb/cruise rating;
* initial cruise altitude capability: 300 ft/min residual climb at the same condition;
* buffet margin at cruise: a 1.3 g manoeuvre without reaching buffet onset — a maximum W/S.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from acdesign.constraint_analysis.constraints import (
    climb_gradient,
    landing_wing_loading,
    master,
    stall_mach,
    takeoff_field_length,
)
from acdesign.constraint_analysis.polar import DragPolar
from acdesign.external.atmosphere import isa
from acdesign.external.engine import RATING_CLIMB, Engine
from acdesign.units import FPM

BETA_CRUISE = 0.970 * 0.985  # W/W_TO at start of cruise (Raymer's take-off and climb fractions)
CL_BUFFET = 0.80  # buffet-onset CL at the cruise Mach: assumption
BUFFET_MARGIN = 1.3  # g to buffet onset at the initial cruise point (industry practice)
CEILING_ROC = 300 * FPM  # residual rate of climb at initial cruise altitude


@dataclass
class ConstraintDiagram:
    ws: np.ndarray  # wing-loading grid [Pa]
    tw: dict[str, np.ndarray]  # T/W lines
    ws_max: dict[str, float]  # vertical lines (maximum W/S)
    design: tuple[float, float] = field(init=False)

    def __post_init__(self):
        self.design = self.design_point()

    @property
    def envelope(self) -> np.ndarray:
        return np.max(np.vstack(list(self.tw.values())), axis=0)

    @property
    def ws_limit(self) -> float:
        return min(self.ws_max.values())

    def feasible(self, ws, tw) -> bool:
        return bool(ws <= self.ws_limit and tw >= np.interp(ws, self.ws, self.envelope) - 1e-12)

    def active(self, ws: float) -> str:
        """Name of the binding T/W requirement at ``ws``."""
        return max(self.tw, key=lambda k: np.interp(ws, self.ws, self.tw[k]))

    def design_point(self) -> tuple[float, float]:
        """(W/S, T/W): the highest wing loading the W/S limits allow, with the least thrust
        that meets every T/W requirement there — the smallest wing, then the smallest
        engine. (Least T/W alone is no criterion when a requirement is nearly flat in W/S,
        as the one-engine-out climbs are; Phase 7 checks this point against least W0.)"""
        ws = self.ws_limit
        return float(ws), float(np.interp(ws, self.ws, self.envelope))


def constraint_diagram(
    mission, polar: DragPolar, engine: Engine, n_engines: int = 2, ws=None
) -> ConstraintDiagram:
    """All the requirements of ``mission`` for an aircraft with ``polar`` and engines of
    ``engine``'s cycle (lapse only; the engine's size does not enter T/W)."""
    ws = np.linspace(3000.0, 9000.0, 601) if ws is None else np.asarray(ws, float)
    to, ld = polar.takeoff, polar.landing
    beta_l = mission.landing_weight_ratio
    tw, ws_max = {}, {}

    tw["take-off field length"] = takeoff_field_length(ws, mission.takeoff_field_length, to.CLmax)
    ws_max["landing field length"] = landing_wing_loading(
        mission.landing_field_length, ld.CLmax, beta_l
    )

    def lapse_at(V_ratio, CLmax, beta=1.0):
        M = V_ratio * stall_mach(ws, CLmax, beta=beta)
        return engine.lapse(np.zeros_like(M), M, rating=1.0)

    p_to = polar.low_speed(to, gear_down=False)
    tw["second segment (OEI)"] = climb_gradient(ws, p_to, 0.024, n_engines, 1.2, 1.0) / lapse_at(
        1.2, to.CLmax
    )
    tw["approach climb (OEI)"] = climb_gradient(
        ws, p_to, 0.021, n_engines, 1.3, 1.0, beta=beta_l
    ) / lapse_at(1.3, to.CLmax, beta_l)
    p_ld = polar.low_speed(ld, gear_down=True)
    CL = ld.CLmax / 1.3**2
    aeo = beta_l * (1 / p_ld.LD(CL) + 0.032)
    tw["landing climb (AEO)"] = aeo / lapse_at(1.3, ld.CLmax, beta_l)

    h, M = mission.cruise_altitude, mission.cruise_mach
    alpha = float(engine.lapse(h, M, rating=RATING_CLIMB))
    tw["cruise"] = master(ws, polar, h, M, alpha, BETA_CRUISE)
    tw["initial cruise altitude (300 ft/min)"] = master(
        ws, polar, h, M, alpha, BETA_CRUISE, Ps=CEILING_ROC
    )
    atm = isa(h)
    q = 0.5 * float(atm.rho) * (M * float(atm.a)) ** 2
    ws_max["buffet margin (1.3 g)"] = q * CL_BUFFET / (BUFFET_MARGIN * BETA_CRUISE)
    return ConstraintDiagram(ws, tw, ws_max)
