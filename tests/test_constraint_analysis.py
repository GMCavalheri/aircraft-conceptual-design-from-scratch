"""Constraint analysis: correlations, the master equation and the design point."""

import numpy as np
import pytest

from acdesign.constraint_analysis import DragPolar, constraint_diagram, oswald_raymer
from acdesign.constraint_analysis.constraints import (
    climb_gradient,
    landing_field_length_of,
    landing_wing_loading,
    master,
    takeoff_field_length,
    takeoff_field_length_of,
)
from acdesign.external.atmosphere import isa
from acdesign.external.engine import Engine
from acdesign.requirements import B737_800_MISSION as M
from acdesign.units import FT, G0, LBF

from reference import b737_800

R = b737_800()
POLAR = DragPolar(CD0=0.0162, e=0.77, AR=9.44)


def test_loftin_takeoff_round_trip_and_737_deduction():
    tw = takeoff_field_length(6000.0, 2400.0, 2.1)
    assert takeoff_field_length_of(6000.0, tw, 2.1) == pytest.approx(2400.0, rel=1e-12)
    # Deduction: the 737-800 at MTOW with 2 x 26,000 lbf (D6-58325-7 3.3.29: 7,800 ft)
    # sits on Loftin's line for CLmax,TO = 37.5 TOP / s = 2.09
    ws = R["mtow"] * G0 / R["wing_area"]
    tw = 2 * 26000 * LBF / (R["mtow"] * G0)
    s = R["takeoff_field_length_mtow_sl"]
    CLmax_to = 37.5 * ws / 47.880259 / (tw * s / FT)
    assert CLmax_to == pytest.approx(2.09, abs=0.01)


def test_loftin_landing_round_trip():
    ws = landing_wing_loading(1768.0, 2.7, 0.84)
    assert landing_field_length_of(ws, 2.7, 0.84) == pytest.approx(1768.0, rel=1e-12)
    # 0.3 V_A^2 [ft, kt] with V_A = 1.3 V_s is m/S = 0.107 sigma CLmax s (kg/m^2, m)
    assert ws * 0.84 / G0 == pytest.approx(0.107 * 2.7 * 1768.0, rel=0.002)


def test_master_equation_minimum_is_one_over_ld_max():
    # Level flight, beta = alpha = 1: T/W = q CD0/(W/S) + K (W/S)/q, minimum 1/(L/D)max at
    # W/S = q sqrt(CD0/K) (Anderson, *Aircraft Performance and Design*, ch. 5)
    h, Mach = 10000.0, 0.6
    atm = isa(h)
    q = 0.5 * float(atm.rho) * (Mach * float(atm.a)) ** 2
    ws = np.linspace(2000, 12000, 20001)
    tw = master(ws, POLAR, h, Mach, alpha=1.0)
    assert tw.min() == pytest.approx(1 / POLAR.LDmax, rel=1e-6)
    assert ws[np.argmin(tw)] == pytest.approx(q * np.sqrt(POLAR.CD0 / POLAR.K), rel=1e-3)
    # climb: Ps/V adds the climb gradient
    assert master(7000.0, POLAR, h, Mach, 1.0, Ps=10.0) - master(7000.0, POLAR, h, Mach, 1.0) == (
        pytest.approx(10.0 / (Mach * float(atm.a)))
    )


def test_climb_gradient_one_engine_out():
    # twin, OEI: T/W = 2 (1/(L/D) + G)
    p = POLAR.low_speed(POLAR.takeoff, gear_down=False)
    CL = p.CLmax_clean / 1.2**2
    tw = climb_gradient(6000.0, p, 0.024, 2, 1.2, 1.0)
    assert tw == pytest.approx(2 * (1 / p.LD(CL) + 0.024), rel=1e-12)


def test_polar_ld_max_and_oswald():
    CL = np.linspace(0.01, 1.5, 150001)
    assert POLAR.LD(CL).max() == pytest.approx(POLAR.LDmax, rel=1e-8)
    # Raymer's straight-wing fit at A = 9.44: 1.78 (1 - 0.045 A^0.68) - 0.64
    assert oswald_raymer(9.44, 0.3) == pytest.approx(1.78 * (1 - 0.045 * 9.44**0.68) - 0.64)


def test_design_point_is_feasible_and_landing_limited():
    d = constraint_diagram(M, POLAR, Engine())
    ws, tw = d.design
    assert d.feasible(ws, tw)
    assert ws == pytest.approx(d.ws_max["landing field length"])
    assert not d.feasible(ws * 1.01, tw) and not d.feasible(ws, tw * 0.99)
