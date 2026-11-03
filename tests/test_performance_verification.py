"""Mission integration and the stability model of the sized aircraft."""

import numpy as np
import pytest

from acdesign.external import stability as fd
from acdesign.external.atmosphere import isa
from acdesign.external.wing_aero import Planform, lift_slope, roll_derivatives
from acdesign.performance_verification import design_range, modes, stability_model
from acdesign.performance_verification.mission import cas_to_tas
from acdesign.performance_verification.stability import CG_TARGET
from acdesign.requirements import B737_800_MISSION as M
from acdesign.sizing import size_aircraft
from acdesign.units import G0, KT

A = size_aircraft(M)
S = stability_model(A)
MO = modes(S)


def test_cas_to_tas():
    # at sea level CAS = TAS (a0 to 6 digits)
    assert cas_to_tas(290 * KT, 0.0) == pytest.approx(290 * KT, rel=1e-6)
    # round trip through the isentropic impact pressure at FL350 (Anderson, ch. 3)
    atm = isa(10668.0)
    M = cas_to_tas(290 * KT, 10668.0) / float(atm.a)
    qc = float(atm.P) * ((1 + 0.2 * M**2) ** 3.5 - 1)
    cas = 340.294 * np.sqrt(5 * ((qc / 101325.0 + 1) ** (2 / 7) - 1))
    assert cas == pytest.approx(290 * KT, rel=1e-9)
    assert M > 0.78  # above the 290 kt / Mach 0.78 crossover: the climb ends at Mach 0.78


def test_integrated_mission_against_breguet():
    r = design_range(A)
    # every kilogram of fuel is accounted for: trip + reserves + 1 % trapped = loaded fuel
    assert (r.trip_fuel + r.reserve_fuel) / 0.99 == pytest.approx(A.fuel_mass, rel=1e-6)
    # The Breguet sizing counts no distance in climb and descent (Raymer's fractions), so
    # the integrated flight goes further on the same fuel: 6.5 % here. Band: the climb and
    # descent distance (~270 nmi) is ~10 % of the range; the integrated range must exceed
    # the requirement but by less than that.
    assert M.design_range < r.range < 1.10 * M.design_range


def test_roll_derivatives_signs_and_strip_theory_limit():
    p = Planform(1.0, 8.0, 0.4, np.deg2rad(25.0))
    r = roll_derivatives(p, np.deg2rad(5.0), 0.5)
    assert r.Cl_b < 0 and r.Cl_p < 0 and r.Cl_r > 0 and r.Cl_da > 0  # Etkin & Reid ch. 5 signs
    # high aspect ratio, untapered: Cl_p -> strip theory -a0/6 (a0 = 2 pi), from below
    lo = roll_derivatives(Planform(1.0, 40.0, 1.0, 0.0), 0.0, 0.0).Cl_p
    hi = roll_derivatives(Planform(1.0, 160.0, 1.0, 0.0), 0.0, 0.0).Cl_p
    assert abs(lo) < abs(hi) < 2 * np.pi / 6
    # the lifting-surface correction decays slowly (~1/A): still 6 % at A = 160
    assert hi == pytest.approx(-2 * np.pi / 6, rel=0.07)


def test_balance_and_neutral_point():
    assert S.balance.h_cg == pytest.approx(CG_TARGET, abs=1e-9)
    # AERO-04's neutral point (exact, tail arm from the CG) against the textbook formula
    # (tail arm from the wing-body ac): they differ by the arm definition, ~SM * St/S.
    classic = S.h_n_classic - S.balance.h_cg
    assert S.static_margin == pytest.approx(classic, abs=0.02)
    # moving the CG to the neutral point removes the static stability (exact CG transfer)
    ac = fd.move_cg(S.aircraft, S.static_margin)
    assert fd.neutral_point_shift(ac) == pytest.approx(0.0, abs=1e-9)


def test_modes_against_approximations():
    # phugoid damping ~ 1/(sqrt 2 L/D) (Lanchester; Etkin & Reid ch. 6)
    d = S.aircraft.aero
    assert MO.phugoid.zeta == pytest.approx(d.CD0 / (np.sqrt(2) * d.CL0), rel=0.15)
    # roll subsidence: tau = -2 V Ixx / (q S b^2 Cl_p) (Etkin & Reid ch. 6)
    atm = isa(S.h)
    q = 0.5 * float(atm.rho) * S.V**2
    ac = S.aircraft
    tau = -2 * S.V * ac.mass.Ixx / (q * ac.geometry.S * ac.geometry.b**2 * d.Cl_p)
    assert MO.roll.time_constant == pytest.approx(tau, rel=0.10)
    assert MO.trim.de == pytest.approx(0.0, abs=1e-9)  # trimmed by construction
    assert lift_slope(A.geometry.wing, M.cruise_mach) == pytest.approx(S.a_wb)
    assert S.aircraft.mass.mass * G0 == pytest.approx(d.CL0 * q * ac.geometry.S)
