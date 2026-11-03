"""Trade studies: sweep one design choice or requirement and re-size the whole aircraft at
every point (constraint design point, geometry, polar, class II weights, mission fuel).

* ``aspect_ratio`` — wing aspect ratio at fixed taper and sweep;
* ``bypass_ratio`` — rubber engines of the CFM56-7B26/3's core technology at other bypass
  ratios (``parametric_engine``), plus the two calibrated engines of AERO-03;
* ``cruise_altitude`` — the initial cruise altitude requirement;
* ``carpet`` — wing loading x thrust loading held fixed (the constraint design point is
  bypassed), with the constraint envelope to show which points are feasible.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from acdesign.external.engine import parametric_engine
from acdesign.sizing import Design, SizedAircraft, size_aircraft


@dataclass(frozen=True)
class TradePoint:
    value: float
    W0: float  # [kg]
    oew: float  # [kg]
    fuel: float  # design-mission fuel incl. reserves [kg]
    S: float  # [m^2]
    thrust: float  # per engine [N]
    LD: float  # mid-cruise L/D
    tsfc: float  # cruise TSFC [kg/(N s)]
    active: str  # binding T/W requirement

    @classmethod
    def of(cls, value: float, a: SizedAircraft) -> TradePoint:
        return cls(value, a.W0, a.oew, a.fuel_mass, a.S, a.thrust, a.fuel.LD_cruise,
                   a.fuel.tsfc_cruise, a.diagram.active(a.ws))  # fmt: skip


def sweep(mission, design: Design, field: str, values) -> list[TradePoint]:
    """Re-size for every value of one ``Design`` field."""
    return [TradePoint.of(v, size_aircraft(mission, design.with_(**{field: v}))) for v in values]


def aspect_ratio(mission, values=(7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0), design=None):
    return sweep(mission, design or Design(), "AR", values)


def bypass_ratio(mission, values=(3.0, 4.0, 5.1, 6.5, 8.0, 9.5, 11.0), design=None):
    d = design or Design()
    return [
        TradePoint.of(b, size_aircraft(mission, d.with_(engine=parametric_engine(b))))
        for b in values
    ]  # noqa: E501


def cruise_altitude(mission, values_m, design: Design | None = None):
    d = design or Design()
    return [
        TradePoint.of(h, size_aircraft(replace(mission, cruise_altitude=h), d)) for h in values_m
    ]  # noqa: E501


def carpet(mission, ws_values, tw_values, design: Design | None = None):
    """W0 and fuel on a W/S x T/W grid: arrays indexed [i_tw, j_ws]."""
    d = design or Design()
    W0 = np.full((len(tw_values), len(ws_values)), np.nan)
    fuel = np.full_like(W0, np.nan)
    for i, tw in enumerate(tw_values):
        for j, ws in enumerate(ws_values):
            try:
                a = size_aircraft(mission, d.with_(ws=float(ws), tw=float(tw)))
            except (RuntimeError, ValueError):  # cannot climb or does not converge
                continue
            W0[i, j], fuel[i, j] = a.W0, a.fuel_mass
    return W0, fuel
