"""Wing aerodynamics adapter: planform identities, Göthert compressibility, downwash."""

import numpy as np
import pytest
from aero.vortex_lattice_3d import Wing, solve_vlm

from acdesign.external.wing_aero import (
    Planform,
    _solve,
    downwash_gradient,
    downwash_gradient_datcom,
    induced_velocity,
    lift_slope,
    lift_slope_datcom,
    span_efficiency,
    span_loading,
)

DEG = np.pi / 180
B738 = Planform(124.6, 9.44, 0.278, 25 * DEG)  # JSR Table 2 planform


def test_planform_matches_aero_wing():
    w = B738.vlm_wing()
    assert w.area == pytest.approx(B738.S, rel=1e-6)
    assert w.aspect_ratio == pytest.approx(B738.AR, rel=1e-6)
    assert w.mean_aerodynamic_chord == pytest.approx(B738.mac, rel=1e-6)
    assert B738.b == pytest.approx(34.30, abs=0.01)  # JSR span 34.30 m


def test_mac_station_and_sweep_conversion():
    # y_mac is where the local chord equals the MAC (straight taper)
    assert B738.chord(B738.y_mac) == pytest.approx(B738.mac, rel=1e-12)
    assert B738.sweep_at(0.25) == pytest.approx(B738.sweep, abs=1e-12)
    # LE sweep from the planform's own coordinates: tan Λ_LE = (x_LE,tip − 0)/(b/2)
    x_le_tip = (B738.b / 2) * np.tan(B738.sweep) + 0.25 * (B738.c_root - B738.c_tip)
    assert np.tan(B738.sweep_at(0.0)) == pytest.approx(x_le_tip / (B738.b / 2), rel=1e-12)


@pytest.mark.parametrize("M", [0.0, 0.5, 0.7, 0.8])
@pytest.mark.parametrize(
    "p",
    [
        B738,
        Planform(32.4, 5.54, 0.186, 30 * DEG),  # 737-800 horizontal tail (JSR)
        Planform(1.0, 3.12, 0.31, 35 * DEG),  # its fin, aspect ratio doubled by the end plate
        Planform(1.0, 12.0, 0.3, 35 * DEG),
    ],
    ids=["737-wing", "737-htail", "737-fin-eff", "AR12-swept"],
)
def test_lift_slope_agrees_with_datcom(p, M):
    # Helmbold/DATCOM is a semi-empirical fit to lifting-surface results, good to a few per
    # cent for tapered planforms like these; both carry the same Göthert Mach dependence.
    # (For untapered wings the fit is worse: 7 % above the VLM at AR 6.)
    assert lift_slope(p, M) == pytest.approx(lift_slope_datcom(p, M), rel=0.04)


def test_gothert_approaches_2d_prandtl_glauert():
    # Very high aspect ratio, unswept: CLα(M)/CLα(0) → 1/β (2D Prandtl–Glauert)
    p = Planform(1.0, 200.0, 1.0, 0.0)
    M = 0.6
    assert lift_slope(p, M) / lift_slope(p, 0.0) == pytest.approx(1 / np.sqrt(1 - M**2), rel=0.01)


def test_span_loading_is_normalised():
    s = _solve(B738, 0.0)
    y, load = span_loading(B738)
    dy = np.diff(s.lattice.y_nodes) * B738.b / s.wing.span
    assert np.sum(load * dy) / B738.b == pytest.approx(1.0, rel=1e-9)
    assert span_efficiency(Planform(1.0, 8.0, 0.4, 0.0)) == pytest.approx(0.99, abs=0.01)


def test_far_wake_downwash_is_twice_the_wing_downwash():
    # Far behind an elliptically loaded wing the downwash is uniform, ε = 2 CL/(π A), twice
    # its value at the wing (Anderson, *Fundamentals of Aerodynamics*, ch. 5).
    w = Wing.elliptic(8.0)
    s = solve_vlm(w, 2 * DEG, 41, 6)
    wn, _ = s.trefftz()
    for k in (20, 30):  # strip centres (see N_SPAN in wing_aero)
        eps = -induced_velocity(s, (200 * w.span, s.y_mid[k], 0.0))[2]
        # Biot–Savart far downstream = AERO-01's 2D Trefftz-plane wash, to the 1/200b leg end
        assert eps == pytest.approx(-wn[k], rel=1e-5)
        # The lattice's elliptic loading is within 3 % of exactly uniform downwash (the
        # deviation does not shrink with mesh: 2.8 % at the root at 41 and 81 strips)
        assert eps == pytest.approx(2 * s.CL / (np.pi * w.aspect_ratio), rel=0.03)


def test_tail_downwash_against_datcom():
    # 737-800 tail: arm 17.68 m (JSR). DATCOM's formula is an empirical fit; the flat-wake
    # VLM (no roll-up, wake left in the chord plane) sits 11-14 % above it here. The design
    # uses the VLM value; this bounds the model-form uncertainty the stability check carries.
    for h_t in (0.0, 1.0, 2.0):
        vlm = downwash_gradient(B738, 17.68, h_t, M=0.78)
        assert vlm == pytest.approx(downwash_gradient_datcom(B738, 17.68, h_t, M=0.78), rel=0.15)
