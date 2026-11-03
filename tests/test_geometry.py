import numpy as np
import pytest

from acdesign.geometry import fuselage_wetted_area, surface_wetted_area


def test_fuselage_wetted_area_limits():
    # A very slender body tends to the cylinder pi D L; at L/D = 10.2 (737-800, JSR) the
    # nose and tail cones remove about 13 %.
    assert fuselage_wetted_area(1e4, 1.0) == pytest.approx(np.pi * 1e4, rel=1e-3)
    assert fuselage_wetted_area(38.08, 3.73) / (np.pi * 38.08 * 3.73) == pytest.approx(
        0.873, abs=0.001
    )


def test_surface_wetted_area():
    # Raymer: S_wet = S_exp (1.977 + 0.52 t/c) — about twice the exposed area
    assert surface_wetted_area(100.0, 0.12) == pytest.approx(100 * (1.977 + 0.0624))
