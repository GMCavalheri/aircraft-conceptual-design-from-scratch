"""Class I and class II weight estimation."""

import numpy as np
import pytest

from acdesign.requirements import B737_800_MISSION as M
from acdesign.units import G0, LB, NMI
from acdesign.weight_estimation import (
    breguet_cruise_fraction,
    breguet_hold_fraction,
    breguet_range,
    component_masses,
    empty_weight_fraction,
    group_masses,
    max_lift_to_drag,
    mission_fractions,
    operating_empty_mass,
    size_class_one,
)
from acdesign.weight_estimation.fractions import F_CLIMB, F_LANDING, F_TAKEOFF, TRAPPED_FUEL

from reference import b737_800
from reference_aircraft import class_two_inputs, crew_mass, wetted_areas

R = b737_800()
TSFC = 17.12e-6  # kg/(N s): AERO-03 minimum cruise TSFC of the CFM56-7B26/3 at FL350


def test_breguet_round_trip_and_closed_form():
    V, LD = 231.3, 16.5
    f = breguet_cruise_fraction(2800 * NMI, V, LD, TSFC)
    assert breguet_range(f, V, LD, TSFC) == pytest.approx(2800 * NMI, rel=1e-12)
    # ln(W0/W1) = R c / (V L/D), c = TSFC g0
    assert np.log(1 / f) == pytest.approx(2800 * NMI * TSFC * G0 / (V * LD), rel=1e-12)
    # hold: 30 min at L/D 19 and the same TSFC
    assert breguet_hold_fraction(1800, 19.0, TSFC) == pytest.approx(
        np.exp(-1800 * TSFC * G0 / 19.0), rel=1e-12
    )


def test_fuel_fraction_bookkeeping():
    fr = mission_fractions(M, 231.3, 16.5, 19.0, TSFC, TSFC)
    trip = 1 - F_TAKEOFF * F_CLIMB * fr.cruise * F_LANDING
    assert fr.trip == pytest.approx(trip, rel=1e-12)
    assert fr.contingency == pytest.approx(0.05 * trip, rel=1e-12)
    reserve = fr.contingency + (1 - trip) * (1 - fr.alternate * fr.hold)
    assert fr.fuel * (1 - TRAPPED_FUEL) == pytest.approx(trip + reserve, rel=1e-12)


def test_empty_weight_regression():
    # Raymer ch. 3, jet transport: We/W0 = 1.02 W0^-0.06 (W0 in lb)
    assert empty_weight_fraction(174200 * LB) == pytest.approx(1.02 * 174200**-0.06, rel=1e-12)
    # wetted aspect ratio: (L/D)max = 15.5 sqrt(A / (Swet/Sref))
    assert max_lift_to_drag(9.0, 6.0) == pytest.approx(15.5 * np.sqrt(1.5), rel=1e-12)


def test_class_one_closes_the_weight_equation():
    res = size_class_one(M, 231.3, 19.1, TSFC, 18.0e-6, crew=crew_mass())
    W0 = res.W0
    assert W0 * (1 - res.fractions.fuel - empty_weight_fraction(W0)) == pytest.approx(
        crew_mass() + M.payload, rel=1e-8
    )
    assert np.diff(res.history)[-1] == pytest.approx(0.0, abs=1e-6 * W0)


def test_class_one_lands_near_the_reference_mtow():
    # Class I uses historical fractions only; Raymer presents it as a first estimate. Here,
    # with the reference wetted area ratio and AERO-03's uninstalled cruise TSFC, it lands
    # within 5 % of the 737-800 MTOW (the mission is flown at MTOW to ~1 %, Phase 1).
    S_wet = sum(wetted_areas().values())
    LD = max_lift_to_drag(R["wing_aspect_ratio"], S_wet / R["wing_area"])
    res = size_class_one(M, 231.3, LD, TSFC, 18.0e-6, crew=crew_mass())
    assert res.W0 == pytest.approx(R["mtow"], rel=0.05)


def test_class_two_equations_by_hand():
    i = class_two_inputs()
    m = component_masses(i)
    # FLOPS eq. 110 furnishings, by hand in imperial units
    XLP, WF = i.L_cabin / 0.3048, i.D_f / 0.3048
    furn = 127 * 2 + 112 * 12 + 44 * 148 + 2.6 * XLP * 2 * WF
    assert m["furnishings"] / LB == pytest.approx(furn, rel=1e-12)
    # Raymer wing: mass ∝ (W_dg N_z)^0.557 — the exponent survives the unit wrapping
    m2 = component_masses(i.with_(W_dg=2 * i.W_dg))
    assert m2["wing"] / m["wing"] == pytest.approx(2**0.557, rel=1e-12)
    # FLOPS eq. 123 engine oil: 0.082 N_eng T^0.65 (T in lbf)
    assert m["engine_oil"] / LB == pytest.approx(0.082 * 2 * (117e3 / (LB * G0)) ** 0.65)


def test_class_two_oew_of_the_737_800():
    # Uncalibrated statistical methods on the published geometry: the model OEW is 11.7 %
    # below the published 91,300 lb. No input was tuned; the gap is reported in the design
    # report (Lesson 2). Tolerance: the band such methods are trusted to at the conceptual
    # stage (±15 %), tight enough to catch a broken equation (each one is ≥ 0.2 % of OEW).
    oew = operating_empty_mass(component_masses(class_two_inputs()))
    assert oew == pytest.approx(R["oew"], rel=0.15)
    assert oew / R["oew"] - 1 == pytest.approx(-0.117, abs=0.002)
    g = group_masses(component_masses(class_two_inputs()))
    assert g["structure"] > g["systems"] > g["propulsion"] > g["operating_items"]
