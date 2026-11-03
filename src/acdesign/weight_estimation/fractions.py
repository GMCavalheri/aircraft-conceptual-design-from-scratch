"""Mission fuel by segment weight fractions (Raymer, *Aircraft Design*, ch. 3).

Each mission segment i ends at a weight W_i = f_i W_(i-1). Warm-up/take-off, climb and
landing use historical fractions; cruise and hold use the Breguet equations for a jet,

    cruise:  W_end/W_start = exp(-R c / (V L/D))
    hold:    W_end/W_start = exp(-E c / (L/D))

with c = TSFC · g0 in 1/s (TSFC in kg/(N s)).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.units import G0

# Historical segment fractions for transport jets (Raymer, ch. 3)
F_TAKEOFF = 0.970  # warm-up and take-off
F_CLIMB = 0.985  # climb and accelerate to cruise
F_LANDING = 0.995  # descent and landing
TRAPPED_FUEL = 0.01  # trapped and unusable fuel, fraction of total fuel: assumption


def breguet_cruise_fraction(range_: float, V: float, LD: float, tsfc: float) -> float:
    """W_end/W_start over ``range_`` [m] at speed ``V`` [m/s], L/D and TSFC [kg/(N s)]."""
    return float(np.exp(-range_ * tsfc * G0 / (V * LD)))


def breguet_range(fraction: float, V: float, LD: float, tsfc: float) -> float:
    """Range [m] flown while the weight falls by ``fraction`` = W_end/W_start."""
    return float(-np.log(fraction) * V * LD / (tsfc * G0))


def breguet_hold_fraction(time: float, LD: float, tsfc: float) -> float:
    """W_end/W_start over ``time`` [s] of hold at L/D and TSFC [kg/(N s)]."""
    return float(np.exp(-time * tsfc * G0 / LD))


@dataclass(frozen=True)
class FuelFractions:
    """Mission segment fractions and the resulting fuel fraction Wf/W0."""

    takeoff: float
    climb: float
    cruise: float
    landing: float
    contingency: float  # reserve fuel for contingency, as a fraction of W0
    alternate: float  # W_end/W_start of the diversion (climb + cruise + landing)
    hold: float  # W_end/W_start of the hold

    @property
    def trip(self) -> float:
        """Trip fuel / W0."""
        return 1.0 - self.takeoff * self.climb * self.cruise * self.landing

    @property
    def fuel(self) -> float:
        """Total fuel / W0, including reserves and trapped fuel."""
        landing_weight = 1.0 - self.trip  # W_landing / W0 at the destination
        reserve = self.contingency + landing_weight * (1.0 - self.alternate * self.hold)
        return (self.trip + reserve) / (1.0 - TRAPPED_FUEL)


def mission_fractions(
    mission, V: float, LD_cruise: float, LD_hold: float, tsfc_cruise: float, tsfc_hold: float
) -> FuelFractions:
    """Segment fractions of ``mission`` (a ``Mission``) at cruise speed ``V`` [m/s].

    The diversion is flown as climb + cruise at the same L/D and TSFC + landing (a
    conservative simplification: diversions are flown lower and slower), then the hold.
    """
    res = mission.reserves
    cruise = breguet_cruise_fraction(mission.design_range, V, LD_cruise, tsfc_cruise)
    trip = 1.0 - F_TAKEOFF * F_CLIMB * cruise * F_LANDING
    alt_cruise = breguet_cruise_fraction(res.alternate_range, V, LD_cruise, tsfc_cruise)
    return FuelFractions(
        takeoff=F_TAKEOFF,
        climb=F_CLIMB,
        cruise=cruise,
        landing=F_LANDING,
        contingency=res.contingency * trip,
        alternate=F_CLIMB * alt_cruise * F_LANDING,
        hold=breguet_hold_fraction(res.hold_time, LD_hold, tsfc_hold),
    )
