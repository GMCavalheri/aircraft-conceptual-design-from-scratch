"""The engine adapter reproduces AERO-03's published numbers and scales exactly."""

import numpy as np
import pytest
from propulsion.off_design_performance import TurbofanEngine

from acdesign.external.engine import CFM56_7B26, LEAP_1B28, Engine, calibrated, flight

from reference import icao, tcds

E = Engine(CFM56_7B26)


@pytest.mark.parametrize("data", [CFM56_7B26, LEAP_1B28])
def test_engine_constants_are_the_databank_rows(data):
    d = icao(data.name)
    assert (data.bpr, data.opr, data.rated_thrust, data.ff_takeoff) == (
        d["bpr"],
        d["opr"],
        d["rated_thrust"],
        d["ff_takeoff"],
    )
    assert data.dry_mass == tcds(data.name)["dry_mass"]


@pytest.mark.parametrize(
    "data, Tt4, airflow, tsfc_mg",
    # AERO-03 validation/results/engine_validation.md, "Calibrated design points"
    [(CFM56_7B26, 1417.3, 348.6, 10.368), (LEAP_1B28, 1492.3, 475.2, 8.205)],
)
def test_calibration_reproduces_aero03(data, Tt4, airflow, tsfc_mg):
    p = calibrated(data).design_point
    assert p.Tt4 == pytest.approx(Tt4, abs=0.05)
    assert p.mdot0 == pytest.approx(airflow, abs=0.05)
    assert p.tsfc * 1e6 == pytest.approx(tsfc_mg, abs=5e-4)
    assert p.fuel_flow == pytest.approx(data.ff_takeoff, rel=1e-6)  # the calibration point


def test_minimum_cruise_tsfc_reproduces_aero03():
    # AERO-03 engine_validation.md: CFM56-7B26/3 minimum TSFC at FL350, M0.78 is
    # 17.12 mg/(N s) at 21.2 kN (throttle line from the take-off Tt4 down)
    e = calibrated(CFM56_7B26)
    fc = flight(35000 * 0.3048, 0.78)
    pts, guess = [], None
    for t in np.linspace(e.design_point.Tt4, 0.62 * e.design_point.Tt4, 40):
        guess = e.operate(fc, t, guess=guess)
        pts.append(guess)
    best = min(pts, key=lambda p: p.tsfc)
    assert best.tsfc * 1e6 == pytest.approx(17.12, abs=0.005)
    assert best.thrust / 1e3 == pytest.approx(21.2, abs=0.05)


def test_rubber_scaling_is_exact():
    # Designing the same cycle at twice the thrust doubles flows and thrust, keeps TSFC.
    e1 = calibrated(CFM56_7B26)
    d = e1.design_point
    e2 = TurbofanEngine.design(
        d.flight,
        alpha=d.alpha,
        pi_f=d.pi_f,
        pi_c=d.pi_c,
        Tt4=d.Tt4,
        pi_cL=d.pi_cL,
        thrust=2 * d.thrust,
        components=e1.components,
    )
    fc = flight(10000.0, 0.8)
    p1, p2 = e1.operate(fc, 0.9 * d.Tt4), e2.operate(fc, 0.9 * d.Tt4)
    assert p2.thrust == pytest.approx(2 * p1.thrust, rel=1e-8)
    assert p2.tsfc == pytest.approx(p1.tsfc, rel=1e-8)
    big = E.scaled(2 * CFM56_7B26.rated_thrust)
    assert big.max_thrust(10000.0, 0.8) == pytest.approx(2 * E.max_thrust(10000.0, 0.8))


def test_lapse_table_matches_direct_solves_and_density_trend():
    # Grid nodes are exact solves; between nodes the interpolation error stays small.
    e = calibrated(CFM56_7B26)
    assert E.lapse(0.0, 0.0) == pytest.approx(1.0, rel=1e-9)
    direct = e.operate(
        flight(10500.0, 0.775), e.design_point.Tt4, guess=E._nearest_full_power(10500.0, 0.775)
    )
    assert direct.converged
    assert E.lapse(10500.0, 0.775) == pytest.approx(
        direct.thrust / CFM56_7B26.rated_thrust, rel=0.01
    )
    # Thrust falls with altitude roughly like the pressure ratio delta (AERO-03 lesson 6)
    assert 0.2 < E.lapse(11000.0, 0.78) < 0.35


def test_part_power_tsfc_matches_operate_at_thrust():
    h, M = 10668.0, 0.78
    p = E.operate_at_thrust(h, M, 22e3)
    assert p.thrust == pytest.approx(22e3, rel=1e-6)
    assert E.tsfc(h, M, 22e3) == pytest.approx(p.tsfc, rel=2e-3)  # 30-point throttle line
