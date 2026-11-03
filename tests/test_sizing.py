"""The closed design: internal consistency of every discipline, and the 737-800 comparison."""

import pytest

from acdesign.external.atmosphere import isa
from acdesign.external.engine import RATING_CLIMB
from acdesign.requirements import B737_800_MISSION as M
from acdesign.sizing import Design, class_two_inputs, size_aircraft
from acdesign.units import G0
from acdesign.weight_estimation import component_masses, operating_empty_mass

from reference import b737_800

R = b737_800()
A = size_aircraft(M)


def test_weight_closure():
    assert A.W0 == pytest.approx(A.oew + M.payload + A.fuel_mass, rel=1e-5)


def test_wing_loading_and_thrust_loading_are_the_constraint_design_point():
    # The wing area the aerodynamics, structures and weights use is W0 g / (W/S)* exactly
    ws, tw = A.diagram.design
    assert A.W0 * G0 / A.S == pytest.approx(ws, rel=1e-5)
    assert A.design.n_engines * A.thrust / (A.W0 * G0) == pytest.approx(tw, rel=1e-5)
    assert A.diagram.feasible(ws, tw)


def test_tail_volume_coefficients():
    g, d = A.geometry, A.design
    assert g.htail.S * g.l_ht / (g.wing.S * g.wing.mac) == pytest.approx(d.V_ht, rel=1e-12)
    assert g.vtail.S * g.l_vt / (g.wing.S * g.wing.b) == pytest.approx(d.V_vt, rel=1e-12)


def test_masses_are_class_two_of_the_final_geometry():
    i = class_two_inputs(
        A.geometry, A.W0, M, A.thrust, A.design.engine, A.fuel_mass, A.design.cabin,
        A.design.CLmax_landing,
    )  # fmt: skip
    assert operating_empty_mass(component_masses(i)) == pytest.approx(A.oew, rel=1e-5)


def test_cruise_thrust_is_within_the_climb_rating():
    # mid-cruise drag per engine, W_mid / (N L/D) with W_mid = q S CL, below maximum thrust
    atm = isa(M.cruise_altitude)
    q = 0.5 * float(atm.rho) * (M.cruise_mach * float(atm.a)) ** 2
    drag = q * A.S * A.fuel.CL_cruise / A.fuel.LD_cruise / 2
    assert drag < A.engine.max_thrust(M.cruise_altitude, M.cruise_mach, RATING_CLIMB)
    # and the TSFC used is the engine's at that thrust
    assert A.fuel.tsfc_cruise == pytest.approx(
        A.engine.tsfc(M.cruise_altitude, M.cruise_mach, drag), rel=1e-6
    )


def test_sized_aircraft_against_the_737_800():
    # Uncalibrated chain. The class II empty mass is 11.7 % light at the 737's own geometry
    # (test_weight_estimation); through the weight snowball the sized aircraft comes out
    # lighter in everything. Bands: what this conceptual chain is expected to hold to (20 %
    # on weights and thrust, 10 % on the landing-limited wing area); the measured values are
    # in validation/results/sizing.md and the design report.
    assert A.W0 == pytest.approx(R["mtow"], rel=0.20)
    assert A.oew == pytest.approx(R["oew"], rel=0.20)
    assert A.S == pytest.approx(R["wing_area"], rel=0.10)
    assert A.thrust == pytest.approx(117.0e3, rel=0.20)
    assert A.W0 < R["mtow"] and A.oew < R["oew"]


def test_fixed_wing_loading_option():
    a = size_aircraft(M, Design(ws=6219.0, tw=0.30))
    assert a.ws == 6219.0 and a.tw == 0.30
    assert a.W0 * G0 / a.S == pytest.approx(6219.0, rel=1e-5)
