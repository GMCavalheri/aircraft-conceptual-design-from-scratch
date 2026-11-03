"""Mission performance by time integration, as a check on the Breguet sizing.

* **Climb** from 1,500 ft to the cruise altitude at 290 kt CAS, then at the cruise Mach,
  at maximum climb thrust (AERO-03 engine at the climb rating): rate of climb from the
  energy equation, (T − D) V / W = dh/dt (1 + V/g dV/dh), fuel from the engine model.
* **Cruise** at constant Mach and altitude: the thrust equals the drag of the current weight
  (polar with wave drag), fuel flow = TSFC(thrust) × thrust, integrated in distance.
* **Descent** at flight idle along a 3° path: the distance is credited, the fuel is
  Raymer's descent-and-landing fraction (0.995) — idle fuel is not modelled.
* **Reserves** as in the sizing (contingency, diversion, hold), from the Breguet fractions.

The take-off and the climb to 1,500 ft use Raymer's take-off fraction (0.970).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from acdesign.external.atmosphere import isa
from acdesign.external.engine import RATING_CLIMB
from acdesign.units import FT, G0, KT, NMI
from acdesign.weight_estimation.fractions import F_LANDING, F_TAKEOFF, TRAPPED_FUEL

CLIMB_CAS = 290 * KT
CLIMB_START = 1500 * FT
DESCENT_ANGLE = np.deg2rad(3.0)


def cas_to_tas(cas: float, h: float) -> float:
    """True airspeed for a calibrated airspeed (compressible, subsonic) at altitude h."""
    a0, p0 = 340.294, 101325.0
    atm = isa(h)
    qc = p0 * ((1 + 0.2 * (cas / a0) ** 2) ** 3.5 - 1)
    M = np.sqrt(5 * ((qc / float(atm.P) + 1) ** (2 / 7) - 1))
    return float(M * atm.a)


@dataclass(frozen=True)
class Segment:
    name: str
    distance: float  # [m]
    fuel: float  # [kg]
    time: float  # [s]


def climb(aircraft, W_start: float, dh: float = 250.0) -> Segment:
    """Climb from CLIMB_START to the cruise altitude [mass in kg]."""
    m = aircraft.mission
    e, n, polar, S = aircraft.engine, aircraft.design.n_engines, aircraft.polar, aircraft.S
    hs = np.arange(CLIMB_START, m.cruise_altitude + 1e-6, dh)
    hs[-1] = m.cruise_altitude
    W, x, t, fuel = W_start, 0.0, 0.0, 0.0
    for h0, h1 in zip(hs[:-1], hs[1:], strict=True):
        h = 0.5 * (h0 + h1)
        atm = isa(h)
        V0 = min(cas_to_tas(CLIMB_CAS, h0), m.cruise_mach * float(isa(h0).a))
        V1 = min(cas_to_tas(CLIMB_CAS, h1), m.cruise_mach * float(isa(h1).a))
        V = 0.5 * (V0 + V1)
        M = V / float(atm.a)
        q = 0.5 * float(atm.rho) * V**2
        D = q * S * float(polar.CD(W * G0 / (q * S), M))
        T = n * float(e.max_thrust(h, M, RATING_CLIMB))
        roc = (T - D) * V / (W * G0) / (1 + V / G0 * (V1 - V0) / (h1 - h0))
        if roc <= 0:
            raise ValueError(f"no climb capability at {h:.0f} m")
        dt = (h1 - h0) / roc
        mdot = T * e.tsfc(h, M, T / n)
        W -= mdot * dt
        fuel += mdot * dt
        x += V * dt
        t += dt
    return Segment("climb", x, fuel, t)


def cruise(aircraft, W_start: float, fuel: float, steps: int = 200) -> Segment:
    """Cruise at constant Mach and altitude until ``fuel`` [kg] is burnt."""
    m = aircraft.mission
    e, n, polar, S = aircraft.engine, aircraft.design.n_engines, aircraft.polar, aircraft.S
    h, M = m.cruise_altitude, m.cruise_mach
    atm = isa(h)
    V = M * float(atm.a)
    q = 0.5 * float(atm.rho) * V**2

    def rate(W):  # fuel burnt per metre [kg/m]
        D = q * S * float(polar.CD(W * G0 / (q * S), M))
        return D * e.tsfc(h, M, D / n) / V

    # integrate dx = dW / rate(W) with Simpson's rule over the weight
    Ws = np.linspace(W_start, W_start - fuel, 2 * steps + 1)
    f = np.array([1 / rate(W) for W in Ws])
    dW = fuel / (2 * steps)
    x = dW / 3 * (f[0] + f[-1] + 4 * f[1:-1:2].sum() + 2 * f[2:-1:2].sum())
    return Segment("cruise", float(x), fuel, float(x / V))


@dataclass(frozen=True)
class MissionResult:
    segments: tuple[Segment, ...]
    reserve_fuel: float

    @property
    def range(self) -> float:
        return sum(s.distance for s in self.segments)

    @property
    def trip_fuel(self) -> float:
        return sum(s.fuel for s in self.segments)


def fly(aircraft, takeoff_mass: float, fuel: float) -> MissionResult:
    """Fly the mission profile with ``fuel`` [kg] on board, holding back the reserves the
    sizing assumed (their fractions are applied to this flight's own weights)."""
    fr = aircraft.fuel.fractions
    W = takeoff_mass * F_TAKEOFF
    takeoff = Segment("take-off", 0.0, takeoff_mass - W, 0.0)
    c = climb(aircraft, W)
    W -= c.fuel
    descent_distance = aircraft.mission.cruise_altitude / np.tan(DESCENT_ANGLE)

    # fuel left for cruise: total - used - descent - reserves (reserves ~ landing weight)
    def reserves(W_land):
        trip = takeoff_mass - W_land
        contingency = aircraft.mission.reserves.contingency * trip
        return contingency + W_land * (1 - fr.alternate * fr.hold)

    # solve for the cruise fuel that leaves exactly the reserves at touchdown
    lo, hi = 0.0, fuel - (takeoff_mass - W)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        W_end = (W - mid) * F_LANDING
        burnt = takeoff_mass - W_end
        if (burnt + reserves(W_end)) / (1 - TRAPPED_FUEL) > fuel:
            hi = mid
        else:
            lo = mid
    cr = cruise(aircraft, W, lo)
    W_end = (W - lo) * F_LANDING
    descent = Segment(
        "descent and landing", descent_distance, (W - lo) - W_end, descent_distance / 120.0
    )
    return MissionResult((takeoff, c, cr, descent), reserves(W_end))


def design_range(aircraft) -> MissionResult:
    """The design mission flown with the fuel the sizing put on board."""
    return fly(aircraft, aircraft.W0, aircraft.fuel_mass)


def payload_range(aircraft, max_payload: float, fuel_capacity: float):
    """Corners of the payload-range diagram at the sized take-off mass: (range [nmi],
    payload [kg]) at maximum payload, at full tanks with MTOW, and at zero payload."""
    oew, W0 = aircraft.oew, aircraft.W0
    out = [(0.0, max_payload)]
    fuel_a = W0 - oew - max_payload
    out.append((design_range_with(aircraft, W0, fuel_a), max_payload))
    payload_b = W0 - oew - fuel_capacity
    out.append((design_range_with(aircraft, W0, fuel_capacity), payload_b))
    out.append((design_range_with(aircraft, oew + fuel_capacity, fuel_capacity), 0.0))
    return [(r / NMI, p) for r, p in out]


def design_range_with(aircraft, takeoff_mass: float, fuel: float) -> float:
    return fly(aircraft, takeoff_mass, fuel).range
