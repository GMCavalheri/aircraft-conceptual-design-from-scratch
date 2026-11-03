"""Wing-box sizing: statics, allowables, and the cross-check against class II."""

import numpy as np
import pytest

from acdesign.external.wing_aero import span_loading
from acdesign.external.wing_box import isotropic
from acdesign.requirements import B737_800_MISSION as M
from acdesign.sizing import size_aircraft
from acdesign.structural_sizing_check import ULTIMATE_LOAD_FACTOR, BoxAssumptions, wing_box
from acdesign.units import G0
from acdesign.weight_estimation import component_masses

from reference import b737_800
from reference_aircraft import class_two_inputs, geometry

R = b737_800()
WING = geometry().wing


def test_root_moment_is_the_integrated_lift():
    # No relief: root moment about the side of body = n W/b ∫ shape(y) (y − y0) dy / cos Λ
    W = 60000.0
    r = wing_box(WING, 3.73, W, W, 0.0, 0.0, 0.0)
    yv, shape = span_loading(WING)
    y = np.linspace(3.73 / 2, WING.b / 2, 4001)
    sh = np.interp(y, yv[yv >= 0], shape[yv >= 0])
    a = BoxAssumptions()
    cs = np.cos(WING.sweep_at(0.5 * (a.front_spar + a.rear_spar)))
    expect = ULTIMATE_LOAD_FACTOR * W * G0 / WING.b * np.trapezoid(sh * (y - y[0]), y) / cs
    # 41 stations with linear load segments vs 4001-point integration: 0.2 % apart
    assert r.root_moment == pytest.approx(expect, rel=5e-3)
    assert r.shear[0] == pytest.approx(
        ULTIMATE_LOAD_FACTOR * W * G0 / WING.b * np.trapezoid(sh, y), rel=5e-3
    )


def test_allowables_and_cover_sizing():
    a = BoxAssumptions()
    al = isotropic("7075-T6")
    lam = a.rib_pitch / a.stringer_radius_of_gyration
    johnson = al.Fcy * (1 - al.Fcy * lam**2 / (4 * np.pi**2 * al.E))  # Johnson parabola
    r = wing_box(WING, 3.73, R["mtow"], R["mzfw"], R["usable_fuel"], 6000.0, 3000.0)
    assert r.sigma_upper == pytest.approx(johnson, rel=1e-9)
    i = 0  # the root is column-governed: the cover works exactly at the allowable
    assert r.upper_governed_by[i] == "column"
    stress = r.moment[i] / r.height[i] / (r.width[i] * r.t_upper[i])
    assert stress == pytest.approx(r.sigma_upper, rel=1e-9)
    # no skin buckling below limit load anywhere
    assert r.skin_buckling_ratio.min() >= 1 / 1.5 - 1e-9
    # webs carry V/(2h) within the shear allowable
    assert np.all(r.shear / (2 * r.height) / r.t_web <= al.Fsu * (1 + 1e-9))


@pytest.mark.parametrize("which", ["737-800 geometry", "sized design"])
def test_physics_wing_mass_against_class_two(which):
    # Two independent estimates of one mass: the ideal box x non-optimum 1.5 + 15 kg/m² of
    # secondary structure (assumptions fixed before the comparison) against Raymer's
    # statistical wing. They agree to 2 %; the band is the ±15 % such a box model is
    # trusted to, set by its assumed non-optimum factor.
    if which == "sized design":
        a = size_aircraft(M)
        g, W0, zfw, fuel, m = a.geometry, a.W0, a.W0 - a.fuel_mass, a.fuel_mass, a.masses
    else:
        g, W0, zfw, fuel = geometry(), R["mtow"], R["mzfw"], R["usable_fuel"]
        m = component_masses(class_two_inputs())
    eng = (m["engines"] + m["nacelles"]) / 2
    r = wing_box(g.wing, g.fuselage_diameter, W0, zfw, fuel, m["wing"], eng)
    assert r.wing_mass == pytest.approx(m["wing"], rel=0.15)
