"""International Standard Atmosphere from AERO-03 (``propulsion.atmosphere``), at
geopotential pressure altitude (flight levels) — the convention throughout this package."""

from __future__ import annotations

from propulsion.atmosphere import G0, P_SL, RHO_SL, T_SL, Atmosphere
from propulsion.atmosphere import isa as _isa

__all__ = ["G0", "P_SL", "RHO_SL", "T_SL", "Atmosphere", "isa"]


def isa(h, dT: float = 0.0) -> Atmosphere:
    """ISA at geopotential altitude ``h`` [m] (0–32 km), temperature offset ``dT`` [K]."""
    return _isa(h, dT=dT, geopotential=True)
