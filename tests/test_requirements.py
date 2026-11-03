import pytest

from acdesign.requirements import B737_800_MISSION as M
from acdesign.units import FT, LB, NMI

from reference import b737_800

R = b737_800()


def test_design_payload_is_36000_lb():
    # 160 passengers x 225 lb (Raymer ch. 3 allowance with baggage)
    assert M.payload / LB == pytest.approx(36000.0, rel=1e-12)


def test_design_mission_lies_inside_the_reference_payload_range():
    # The 737-800 carries this payload at MTOW to the full-fuel corner (2,860 nmi with
    # 37,000 lb, chart ±30 nmi): the design point is inside its envelope, below MZFW...
    assert R["oew"] + M.payload < R["mzfw"]
    corner_payload = R["oew_plus_payload_at_full_fuel_mtow"] - R["oew"]
    assert M.payload < corner_payload
    # ...and close to its edge: within 3 % of the corner's range
    assert M.design_range == pytest.approx(R["range_at_full_fuel_mtow"], rel=0.03)


def test_requirements_are_the_reference_field_lengths():
    assert M.takeoff_field_length == pytest.approx(R["takeoff_field_length_mtow_sl"])
    assert M.landing_field_length == pytest.approx(R["landing_field_length_mlw_sl"])
    assert M.landing_weight_ratio == pytest.approx(R["mlw"] / R["mtow"])
    assert M.cruise_altitude == pytest.approx(35000 * FT)
    assert M.reserves.alternate_range == pytest.approx(200 * NMI)
