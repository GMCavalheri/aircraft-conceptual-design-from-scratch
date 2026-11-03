"""Rubber turbofan built on the AERO-03 off-design engine model (``propulsion``).

The calibration recipe is AERO-03's (``validation/engines.py`` there, which is not part of the
installed package, so it is rebuilt here from the public API):

- **Data**: bypass ratio, overall pressure ratio, rated sea-level-static thrust and take-off
  fuel flow from the ICAO Engine Emissions Databank (``EngineData`` constants below; a test
  checks them against ``validation/reference_data/icao_eedb.csv``).
- **Assumptions**: polytropic efficiency 0.92 for fan, compressors and turbines, otherwise
  ``Components.modern()``; booster pressure ratio 1.6; convergent nozzles; no bleed or
  cooling flows.
- **Choice**: the fan pressure ratio of minimum sea-level-static TSFC.
- **Calibration**: Tt4 such that the take-off fuel flow equals the ICAO value.

**Rubber scaling.** The matching equations of the off-design model are ratios of flows and
areas, so an engine designed at a different thrust with the same cycle has every flow, area,
thrust and fuel flow scaled by the same factor and identical TSFC, lapse and spool speeds
(checked in the tests). ``Engine.scaled(thrust)`` therefore only stores the factor.

**Ratings.** The model has no rating schedule. Maximum thrust at altitude is the thrust at
``rating × Tt4_takeoff`` (``RATING_CLIMB`` for climb and cruise, an assumption).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache

import numpy as np
from propulsion.component_models import Components
from propulsion.flight import FlightCondition
from propulsion.off_design_performance import OperatingPoint, TurbofanEngine
from propulsion.trade_studies import best_fan_pressure_ratio
from propulsion.turbofan_model import turbofan
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import brentq

PI_CL = 1.6  # booster pressure ratio: assumption (AERO-03)
# Assumption (AERO-03): polytropic efficiency 0.92 for fan, compressors and turbines
COMPONENTS = Components.modern().with_(e_f=0.92, e_c=0.92, e_t=0.92)
_KW = {"components": COMPONENTS, "core_nozzle": "convergent", "fan_nozzle": "convergent"}
SLS = FlightCondition.sea_level_static()
# Assumption: maximum climb/cruise rating, as a fraction of the take-off Tt4.
RATING_CLIMB = 0.92

# Grid of the thrust-lapse table (geopotential altitude [m], flight Mach number)
H_GRID = np.arange(0.0, 13001.0, 1000.0)
M_GRID = np.round(np.arange(0.0, 0.8601, 0.05), 2)


@dataclass(frozen=True)
class EngineData:
    """ICAO databank values that define one engine (SI)."""

    name: str
    bpr: float
    opr: float
    rated_thrust: float  # sea-level static ISA [N]
    ff_takeoff: float  # take-off fuel flow at rated thrust [kg/s]
    dry_mass: float  # [kg], EASA type-certificate data sheet
    nacelle_diameter: float  # [m]
    nacelle_length: float  # [m]


# Data: ICAO Engine Emissions Databank Issue 32 (UIDs 8CM065, 08P28CM143); dry mass from
# EASA TCDS E.004 / E.115. CFM56-7 nacelle: Jenkinson et al. Data A Table 2 (737-800).
# LEAP-1B nacelle (deduction): diameter scaled by the square root of the AERO-03 models'
# airflow ratio (475.2/348.6 kg/s), length by the TCDS engine-length ratio (3147/2508 mm).
CFM56_7B26 = EngineData("CFM56-7B26/3", 5.1, 27.7, 117.0e3, 1.213, 2386.0, 2.06, 4.70)
LEAP_1B28 = EngineData(
    "LEAP-1B28", 8.240, 42.03, 130.41e3, 1.0700, 2780.0, 2.06 * (475.2 / 348.6) ** 0.5,
    4.70 * 3147 / 2508,
)  # fmt: skip


def flight(h: float, M: float, dT: float = 0.0) -> FlightCondition:
    """Flight condition at geopotential pressure altitude ``h`` [m] and Mach ``M``."""
    return FlightCondition.at_altitude(float(h), float(M), dT=dT, geopotential=True)


@cache
def calibrated(data: EngineData) -> TurbofanEngine:
    """The engine sized at its ICAO rating, Tt4 calibrated to the ICAO take-off fuel flow."""

    def excess_fuel(Tt4):
        pi_f = best_fan_pressure_ratio(SLS, data.bpr, data.opr, Tt4, pi_cL=PI_CL, **_KW)
        p = turbofan(SLS, data.bpr, pi_f, data.opr, Tt4, pi_cL=PI_CL, **_KW)
        return data.rated_thrust * float(p.tsfc) - data.ff_takeoff

    Tt4 = brentq(excess_fuel, 1300.0, 2000.0, xtol=1e-6)
    pi_f = best_fan_pressure_ratio(SLS, data.bpr, data.opr, Tt4, pi_cL=PI_CL, **_KW)
    return TurbofanEngine.design(
        SLS,
        alpha=data.bpr,
        pi_f=pi_f,
        pi_c=data.opr,
        Tt4=Tt4,
        pi_cL=PI_CL,
        thrust=data.rated_thrust,
        components=COMPONENTS,
    )


@cache
def _full_power_grid(data: EngineData, rating: float) -> dict[tuple[int, int], OperatingPoint]:
    """Operating points at ``rating × Tt4_takeoff`` on (H_GRID × M_GRID), by continuation:
    up each Mach column from sea level, each column started from its neighbour."""
    e = calibrated(data)
    Tt4 = rating * e.design_point.Tt4
    pts: dict[tuple[int, int], OperatingPoint] = {}
    guess = e.operate(SLS, Tt4)
    for j, M in enumerate(M_GRID):
        guess = e.operate(flight(0.0, M), Tt4, guess=guess)
        col = guess
        for i, h in enumerate(H_GRID):
            col = e.operate(flight(h, M), Tt4, guess=col)
            if not col.converged:
                raise RuntimeError(f"{data.name}: no converged point at h={h} m, M={M}")
            pts[i, j] = col
    return pts


@cache
def _lapse_interpolator(data: EngineData, rating: float) -> RegularGridInterpolator:
    pts = _full_power_grid(data, rating)
    F = np.array([[pts[i, j].thrust for j in range(len(M_GRID))] for i in range(len(H_GRID))])
    return RegularGridInterpolator((H_GRID, M_GRID), F / data.rated_thrust)


@dataclass(frozen=True)
class Engine:
    """One engine of the data's cycle, scaled to ``thrust`` [N] sea-level-static rated."""

    data: EngineData = CFM56_7B26
    thrust: float = field(default=None)  # type: ignore[assignment]

    def __post_init__(self):
        if self.thrust is None:
            object.__setattr__(self, "thrust", self.data.rated_thrust)

    @property
    def scale(self) -> float:
        return self.thrust / self.data.rated_thrust

    @property
    def model(self) -> TurbofanEngine:
        """The calibrated AERO-03 engine at the data's own rating (unscaled)."""
        return calibrated(self.data)

    def scaled(self, thrust: float) -> Engine:
        return Engine(self.data, thrust)

    def lapse(self, h, M, rating: float = 1.0):
        """Maximum thrust / rated sea-level-static thrust at Tt4 = rating × take-off Tt4."""
        h, M = np.broadcast_arrays(np.asarray(h, float), np.asarray(M, float))
        out = _lapse_interpolator(self.data, rating)(np.stack([h, M], axis=-1))
        return out.reshape(h.shape)[()]

    def max_thrust(self, h, M, rating: float = 1.0):
        """Maximum thrust [N] of this (scaled) engine."""
        return self.thrust * self.lapse(h, M, rating)

    def operate_at_thrust(self, h: float, M: float, thrust: float) -> OperatingPoint:
        """Operating point (of the unscaled model) delivering ``thrust`` [N] of this engine.

        TSFC is independent of the scale; thrust and fuel flow of the returned point are the
        unscaled model's (multiply by ``scale``).
        """
        start = self._nearest_full_power(h, M)
        fc = flight(h, M)
        start = self.model.operate(fc, start.Tt4, guess=start)
        return self.model.operate_at_thrust(fc, thrust / self.scale, start=start)

    def tsfc(self, h: float, M: float, thrust: float) -> float:
        """TSFC [kg/(N s)] at ``thrust`` [N] of this engine."""
        return part_power(self.data, float(h), float(M))(thrust / self.thrust)

    def _nearest_full_power(self, h, M, rating: float = 1.0) -> OperatingPoint:
        i = int(np.argmin(np.abs(H_GRID - h)))
        j = int(np.argmin(np.abs(M_GRID - M)))
        return _full_power_grid(self.data, rating)[i, j]


@cache
def part_power(data: EngineData, h: float, M: float, n: int = 30):
    """TSFC as a function of thrust / rated SLS thrust at (h, M): a throttle line from the
    take-off Tt4 down to 45 % of it (continuation), linearly interpolated."""
    e = Engine(data)
    start = e._nearest_full_power(h, M)
    fc = flight(h, M)
    Tt4 = np.linspace(start.Tt4, 0.45 * start.Tt4, n)
    F, c, guess = [], [], start
    for t in Tt4:
        p = e.model.operate(fc, t, guess=guess)
        if not p.converged:
            break
        F.append(p.thrust / data.rated_thrust)
        c.append(p.tsfc)
        guess = p
    F, c = np.array(F[::-1]), np.array(c[::-1])

    def tsfc(thrust_ratio):
        if np.any(np.asarray(thrust_ratio) > F[-1] * (1 + 1e-9)):
            raise ValueError(f"thrust ratio above the maximum {F[-1]:.4f} at h={h}, M={M}")
        return float(np.interp(thrust_ratio, F, c))

    return tsfc
