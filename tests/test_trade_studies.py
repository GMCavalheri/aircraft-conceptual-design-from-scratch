"""Trade studies re-size consistently; parametric engines reproduce their base engine."""

import pytest

from acdesign.external.engine import CFM56_7B26, K_BPR, LEAP_1B28, calibrated, parametric_engine
from acdesign.requirements import B737_800_MISSION as M
from acdesign.sizing import Design, size_aircraft
from acdesign.trade_studies import carpet, sweep

BASE = size_aircraft(M)


def test_sweep_at_the_baseline_value_is_the_baseline():
    (p,) = sweep(M, Design(), "AR", [Design().AR])
    assert p.W0 == pytest.approx(BASE.W0, rel=1e-9)


def test_carpet_at_the_design_point_is_the_baseline():
    W0, fuel = carpet(M, [BASE.ws], [BASE.tw])
    # same W/S and T/W, so the same aircraft, to the sizing tolerance
    assert W0[0, 0] == pytest.approx(BASE.W0, rel=1e-5)
    assert fuel[0, 0] == pytest.approx(BASE.fuel_mass, rel=1e-5)


def test_parametric_engine_at_the_base_bypass_ratio():
    d = parametric_engine(CFM56_7B26.bpr)
    a, b = calibrated(d).design_point, calibrated(CFM56_7B26).design_point
    assert a.Tt4 == pytest.approx(b.Tt4, rel=1e-12)
    assert a.tsfc == pytest.approx(b.tsfc, rel=1e-9)
    assert (d.dry_mass, d.nacelle_diameter) == pytest.approx((2386.0, 2.06), rel=1e-9)
    # the mass trend reproduces the LEAP-1B28's TCDS mass at its bypass ratio and thrust
    leap_like = parametric_engine(LEAP_1B28.bpr).dry_mass * (130.41 / 117.0) ** 1.1
    assert leap_like == pytest.approx(LEAP_1B28.dry_mass, rel=1e-6)
    assert K_BPR > 0
