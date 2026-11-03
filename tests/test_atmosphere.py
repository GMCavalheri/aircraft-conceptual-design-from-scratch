import pytest

from acdesign.external.atmosphere import isa
from acdesign.units import FT


def test_isa_tropopause_and_fl350():
    # U.S. Standard Atmosphere 1976: 11 km geopotential, T = 216.65 K, P = 22632 Pa
    a = isa(11000.0)
    assert a.T == pytest.approx(216.65, abs=1e-6)
    assert a.P == pytest.approx(22632.06, rel=1e-5)
    # FL350 (35,000 ft pressure altitude): delta = 0.23530 (ICAO Doc 7488 table)
    assert isa(35000 * FT).delta == pytest.approx(0.23530, abs=5e-5)
