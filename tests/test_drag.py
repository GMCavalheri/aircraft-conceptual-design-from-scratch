"""Drag build-up: flat-plate friction, form factors, Korn wave drag, Oswald."""

import numpy as np
import pytest

from acdesign.wing_tail_sizing.drag import (
    WaveDrag,
    ff_fuselage,
    ff_lifting,
    oswald_kroo,
    skin_friction,
    viscosity,
)


def test_sutherland_viscosity():
    # 1.7894e-5 Pa s at 288.15 K (U.S. Standard Atmosphere 1976)
    assert viscosity(288.15) == pytest.approx(1.7894e-5, rel=1e-4)


def test_turbulent_flat_plate_limit():
    # Prandtl-Schlichting form 0.455/(log Re)^2.58 at low Mach, smooth plate
    from acdesign.external.atmosphere import isa

    atm = isa(0.0)
    M, L = 0.05, 10.0
    Re = float(atm.rho) * M * float(atm.a) * L / viscosity(float(atm.T))
    expect = 0.455 / np.log10(Re) ** 2.58 / (1 + 0.144 * M**2) ** 0.65
    assert skin_friction(L, M, 0.0, roughness=1e-12) == pytest.approx(expect, rel=1e-12)
    # roughness caps Re: a rough plate has more friction than a smooth one; production
    # sheet metal does not cap a 4 m chord at cruise (Re 2.4e7 < cutoff 7.5e8)
    assert skin_friction(L, 0.78, 10668.0, roughness=1e-4) > skin_friction(L, 0.78, 10668.0)
    assert skin_friction(4.0, 0.78, 10668.0) == skin_friction(4.0, 0.78, 10668.0, roughness=1e-12)


def test_form_factors():
    assert ff_fuselage(10.0) == pytest.approx(1 + 0.06 + 0.025)
    # an infinitely thin, unswept surface at M = 1 has FF = 1.34
    assert ff_lifting(0.0, 1.0, 0.0) == pytest.approx(1.34)


def test_korn_wave_drag():
    w = WaveDrag(tc=0.11, sweep=np.deg2rad(25.0))
    c = np.cos(w.sweep)
    assert w.drag_divergence_mach(0.5) == pytest.approx(0.95 / c - 0.11 / c**2 - 0.05 / c**3)
    Mc = w.critical_mach(0.5)
    assert w(Mc - 0.01, 0.5) == 0.0
    # Lock's law at M_dd: 20 (0.1/80)^(4/3) = 0.0027
    assert w(w.drag_divergence_mach(0.5), 0.5) == pytest.approx(20 * (0.1 / 80) ** (4 / 3))
    # dCD/dM = 0.1 at M_dd (the drag-divergence definition the law is built on)
    Mdd = w.drag_divergence_mach(0.5)
    dM = 1e-6
    assert (w(Mdd + dM, 0.5) - w(Mdd - dM, 0.5)) / (2 * dM) == pytest.approx(0.1, rel=1e-4)


def test_oswald_kroo_limits():
    # no fuselage, no viscous drag: e = e_inv
    assert oswald_kroo(0.98, 0.0, 30.0, 0.0, 9.0) == pytest.approx(0.98)
    assert oswald_kroo(0.98, 3.7, 34.3, 0.017, 9.44) < 0.98
