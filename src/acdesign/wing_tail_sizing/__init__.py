"""Wing and tail sizing: drag build-up and tail volume coefficients. The wing planform and
tail geometry themselves are built in ``acdesign.sizing`` (``size_geometry``)."""

from acdesign.wing_tail_sizing.drag import (
    Component,
    WaveDrag,
    oswald_kroo,
    parasite_drag,
    skin_friction,
)

__all__ = ["Component", "WaveDrag", "oswald_kroo", "parasite_drag", "skin_friction"]
