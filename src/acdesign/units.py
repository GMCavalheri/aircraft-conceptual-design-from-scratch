"""Exact unit conversion factors (to SI). Internal quantities are always SI.

Source: NIST SP 811 (2008), Appendix B — the foot, inch, pound-mass, pound-force, nautical mile
and knot are defined exactly in SI. The U.S. liquid gallon is exactly 231 in³.
"""

from __future__ import annotations

import numpy as np

FT = 0.3048  # m per foot (exact)
INCH = FT / 12.0  # m per inch (exact)
LB = 0.45359237  # kg per pound-mass (exact)
G0 = 9.80665  # m/s^2, standard gravity (exact)
LBF = LB * G0  # N per pound-force (exact)
NMI = 1852.0  # m per nautical mile (exact)
KT = NMI / 3600.0  # m/s per knot (exact)
FT2 = FT**2  # m^2 per ft^2
PSF = LBF / FT2  # Pa per lbf/ft^2
US_GAL = 231.0 * INCH**3  # m^3 per U.S. liquid gallon = 3.785411784e-3
HOUR = 3600.0  # s
MINUTE = 60.0  # s
FPM = FT / MINUTE  # m/s per ft/min
DEG = np.pi / 180.0  # rad per degree
TSFC_LB_PER_LBF_H = LB / (LBF * HOUR)  # kg/(N s) per lb/(lbf h) = 2.8325e-5
