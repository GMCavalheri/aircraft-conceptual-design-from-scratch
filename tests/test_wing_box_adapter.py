import numpy as np
import pytest

from acdesign.external.wing_box import box_section, cantilever_shear_moment


def test_cantilever_uniform_load():
    # Root shear w L, root moment w L^2 / 2 (Gere & Goodno, Mechanics of Materials, ch. 4)
    x = np.linspace(0.0, 10.0, 11)
    V, M = cantilever_shear_moment(x, np.full_like(x, 100.0), [(5.0, -200.0)])
    assert abs(V[0]) == pytest.approx(1000.0 - 200.0)
    assert abs(M[0]) == pytest.approx(100.0 * 10**2 / 2 - 200.0 * 5.0)
    assert M[-1] == pytest.approx(0.0, abs=1e-9)


def test_box_section_thin_wall_limits():
    # covers dominate: I ~ 2 (w t)(h/2)^2 + 2 t_w h^3/12; J = 4 A^2 / sum(l/t)
    w, h, t = 1.0, 0.3, 0.004
    I, J = box_section(w, h, t, t, t)
    assert I == pytest.approx(2 * w * t * (h / 2) ** 2 + 2 * t * h**3 / 12, rel=1e-3)
    assert J == pytest.approx(4 * (w * h) ** 2 / (2 * (w + h) / t), rel=1e-12)
