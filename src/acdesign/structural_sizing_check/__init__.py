"""Structural sizing check: a physics-based wing box against the statistical wing weight."""

from acdesign.structural_sizing_check.wing_box import (
    ULTIMATE_LOAD_FACTOR,
    BoxAssumptions,
    WingBoxResult,
    wing_box,
)

__all__ = ["ULTIMATE_LOAD_FACTOR", "BoxAssumptions", "WingBoxResult", "wing_box"]
