"""The transcribed reference data is self-consistent: printed metric/imperial pairs, geometric
identities between printed quantities, and the payload-range chart against the weight table."""

import pytest

from acdesign.units import LB

from reference import b737_800, b737_800_printed, icao, tcds

R = b737_800()


def test_every_row_has_a_source():
    for q, (_, _, source) in b737_800_printed().items():
        assert source.startswith(("[ACAP]", "[JSR]")), q


@pytest.mark.parametrize(
    "quantity, kg",  # D6-58325-7 2.1.3 prints both units; kg rounded to 1 kg
    [("mtow", 79015), ("mlw", 66360), ("mzfw", 62731), ("oew", 41412)],
)
def test_acap_pounds_match_printed_kilograms(quantity, kg):
    assert R[quantity] == pytest.approx(kg, abs=1.0)


def test_fuel_mass_comes_from_volume():
    # D6-58325-7 2.1.3 derives each fuel mass from the volume with its own density, so the
    # printed 46,062 lb and 20,897 kg differ by 4 kg: 6875 US gal x 6.7 lb/gal and
    # 26,024 L x 0.803 kg/L (the densities are deductions from the printed numbers).
    assert 6875 * 6.7 == pytest.approx(46062, abs=1)
    assert 26024 * 0.803 == pytest.approx(20897, abs=1)
    assert R["usable_fuel"] == pytest.approx(20897, abs=5)


def test_weight_table_is_consistent():
    # MZFW = OEW + max structural payload (D6-58325-7 2.1.3: 91,300 + 47,000 = 138,300 lb)
    assert R["oew"] + R["max_structural_payload"] == pytest.approx(R["mzfw"])


def test_payload_range_chart_against_weight_table():
    # At the full-fuel corner of the MTOW line, OEW + payload + usable fuel = MTOW. The chart
    # reading (±500 lb) must reproduce the printed fuel capacity to within that resolution.
    fuel = R["mtow"] - R["oew_plus_payload_at_full_fuel_mtow"]
    assert fuel == pytest.approx(R["usable_fuel"], abs=500 * LB)


def test_jsr_wing_geometry_identities():
    # AR = b^2 / S with the printed span and area (JSR rounds AR to 0.01)
    assert R["wing_span_jsr"] ** 2 / R["wing_area"] == pytest.approx(
        R["wing_aspect_ratio"], abs=0.01
    )
    # JSR's span agrees with the airport-planning span to the 2 cm of their rounding
    assert R["wing_span_jsr"] == pytest.approx(R["wing_span"], abs=0.03)


def test_jsr_tail_volume_coefficients():
    # V_h = S_h l_h / (S c), V_v = S_v l_v / (S b), rounded to 0.001 in the table
    S, c, b = R["wing_area"], R["wing_mac"], R["wing_span_jsr"]
    assert R["htail_area"] * R["htail_arm"] / (S * c) == pytest.approx(R["htail_volume"], abs=1e-3)
    assert R["vtail_area"] * R["vtail_arm"] / (S * b) == pytest.approx(R["vtail_volume"], abs=1e-3)
    assert R["htail_span"] ** 2 / R["htail_area"] == pytest.approx(
        R["htail_aspect_ratio"], abs=0.01
    )


def test_engine_rows_copied_from_aero03():
    e = icao("CFM56-7B26/3")
    assert (e["bpr"], e["opr"], e["rated_thrust"], e["ff_takeoff"]) == (5.1, 27.7, 117e3, 1.213)
    # TCDS take-off thrust 11,699 daN is the same rating the databank rounds to 117.0 kN
    assert tcds("CFM56-7B26/3")["takeoff_thrust"] == pytest.approx(e["rated_thrust"], rel=1e-3)
