"""Thrust-to-weight requirements as functions of wing loading.

Thrust loading T/W is the **sea-level-static rated** thrust of all engines over the
**take-off** weight; wing loading W/S [Pa] is take-off weight over reference area. A
requirement met at weight βW_TO with available thrust αT_SL becomes, on that basis
(Mattingly, *Aircraft Engine Design*, ch. 2, "master equation"),

    T_SL/W_TO = (β/α) [ (q/(β W/S)) (CD0 + K (n β W/S / q)²) + P_s/V ]

with α the thrust lapse at that flight condition and rating (from the AERO-03 engine).
Field lengths use Loftin's correlations (NASA RP-1060, 1980): FAR take-off field length
s_TO [ft] = 37.5 (W/S)/(σ CLmax,TO T/W) with W/S in lb/ft², and FAR landing field length
s_L [ft] = 0.3 V_A² with V_A [kt] = 1.3 V_stall.
"""

from __future__ import annotations

import numpy as np

from acdesign.external.atmosphere import RHO_SL, isa
from acdesign.units import FT, KT, PSF

LOFTIN_TAKEOFF = 37.5  # ft per lb/ft² of take-off parameter
LOFTIN_LANDING = 0.3  # ft per kt² of approach speed
APPROACH_TO_STALL = 1.3  # Loftin's V_A / V_stall


def takeoff_field_length(ws, s_to: float, CLmax_to: float, sigma: float = 1.0):
    """T/W needed for a FAR 25 take-off field length ``s_to`` [m]."""
    ws_psf = np.asarray(ws, float) / PSF
    return LOFTIN_TAKEOFF * ws_psf / (sigma * CLmax_to * s_to / FT)


def takeoff_field_length_of(ws: float, tw: float, CLmax_to: float, sigma: float = 1.0):
    """FAR take-off field length [m] at ``ws`` [Pa] and ``tw`` (inverse of the above)."""
    return LOFTIN_TAKEOFF * (ws / PSF) / (sigma * CLmax_to * tw) * FT


def landing_wing_loading(
    s_land: float, CLmax_land: float, landing_ratio: float, sigma: float = 1.0
) -> float:
    """Largest take-off W/S [Pa] that lands in ``s_land`` [m] at W_L = ratio · W_TO."""
    V_A = np.sqrt(s_land / FT / LOFTIN_LANDING) * KT  # [m/s]
    V_s = V_A / APPROACH_TO_STALL
    ws_land = 0.5 * RHO_SL * sigma * V_s**2 * CLmax_land
    return float(ws_land / landing_ratio)


def landing_field_length_of(ws: float, CLmax_land: float, landing_ratio: float):
    """FAR landing field length [m] at take-off W/S ``ws`` [Pa] (sea level)."""
    V_s = np.sqrt(2 * ws * landing_ratio / (RHO_SL * CLmax_land))
    return LOFTIN_LANDING * (APPROACH_TO_STALL * V_s / KT) ** 2 * FT


def master(ws, polar, h: float, M: float, alpha: float, beta: float = 1.0, n=1.0, Ps=0.0):
    """Mattingly's master equation: T_SL/W_TO at W/S_TO ``ws`` [Pa] for flight at altitude
    ``h``, Mach ``M``, load factor ``n`` and specific excess power ``Ps`` [m/s], at weight
    fraction ``beta`` with thrust lapse ``alpha``."""
    ws = np.asarray(ws, float)
    atm = isa(h)
    V = M * float(atm.a)
    q = 0.5 * float(atm.rho) * V**2
    CL = n * beta * ws / q
    D_over_W = q * polar.CD(CL, M) / (beta * ws)
    return beta / alpha * (D_over_W + Ps / V)


def climb_gradient(ws, polar, gradient: float, n_engines: int, V_ratio: float, alpha: float,
                   beta: float = 1.0, h: float = 0.0):  # fmt: skip
    """T_SL/W_TO for a climb gradient with one engine inoperative (FAR 25.121), at
    V = ``V_ratio`` · V_stall in the polar's configuration (its CLmax_clean is the
    configuration's CLmax). With L/D at that CL the requirement is independent of W/S:

        T/W = (N/(N−1)) (β/α) (1/(L/D) + G)
    """
    CL = polar.CLmax_clean / V_ratio**2
    tw = n_engines / (n_engines - 1) * beta / alpha * (1 / polar.LD(CL) + gradient)
    return np.full_like(np.asarray(ws, float), tw)


def stall_mach(ws, CLmax: float, h: float = 0.0, beta: float = 1.0):
    """Mach number of the 1-g stall at weight β W_TO (``ws`` scalar or array)."""
    atm = isa(h)
    return np.sqrt(2 * beta * np.asarray(ws, float) / (float(atm.rho) * CLmax)) / float(atm.a)
