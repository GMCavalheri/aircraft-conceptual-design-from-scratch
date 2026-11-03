"""Parabolic drag polar, CD = CD0 + K CL² (+ wave drag), K = 1/(π A e), with high-lift and
landing-gear increments for the low-speed configurations."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

CFE_CIVIL_TRANSPORT = 0.0026  # equivalent skin-friction coefficient (Raymer, ch. 12)


def cd0_equivalent_skin_friction(wetted_ratio: float, Cfe: float = CFE_CIVIL_TRANSPORT) -> float:
    """First-estimate CD0 = C_fe S_wet/S_ref (Raymer, *Aircraft Design*, ch. 12)."""
    return Cfe * wetted_ratio


def oswald_raymer(aspect_ratio: float, sweep_le: float) -> float:
    """Oswald efficiency of a whole aircraft from Raymer's statistical fits (*Aircraft
    Design*, ch. 12): straight wings 1.78 (1 − 0.045 A^0.68) − 0.64; swept wings
    (Λ_LE > 30°) 4.61 (1 − 0.045 A^0.68) cos(Λ_LE)^0.15 − 3.1."""
    f = 1 - 0.045 * aspect_ratio**0.68
    if sweep_le <= np.deg2rad(30.0):
        return float(1.78 * f - 0.64)
    return float(4.61 * f * np.cos(sweep_le) ** 0.15 - 3.1)


@dataclass(frozen=True)
class Configuration:
    """Low-speed configuration: high-lift CLmax and drag increments (all assumptions)."""

    CLmax: float
    dCD0: float = 0.0  # flap profile-drag increment
    de: float = 0.0  # loss of Oswald efficiency with flaps down
    gear_dCD0: float = 0.0  # landing-gear drag increment when down


@dataclass(frozen=True)
class DragPolar:
    CD0: float  # clean, low-Mach zero-lift drag
    e: float  # Oswald efficiency, clean
    AR: float
    CLmax_clean: float = 1.4
    takeoff: Configuration = Configuration(CLmax=2.1, dCD0=0.015, de=0.05)
    landing: Configuration = Configuration(CLmax=2.7, dCD0=0.060, de=0.10, gear_dCD0=0.020)
    wave: callable = None  # optional wave drag ΔCD(M, CL)

    @property
    def K(self) -> float:
        return 1.0 / (np.pi * self.AR * self.e)

    def CD(self, CL, M: float = 0.0):
        CL = np.asarray(CL, float)
        cd = self.CD0 + self.K * CL**2
        if self.wave is not None:
            cd = cd + self.wave(M, CL)
        return cd

    def LD(self, CL, M: float = 0.0):
        return np.asarray(CL, float) / self.CD(CL, M)

    @property
    def LDmax(self) -> float:
        """Maximum L/D of the parabolic polar (no wave drag): ½ √(π A e / CD0)."""
        return 0.5 * float(np.sqrt(np.pi * self.AR * self.e / self.CD0))

    def low_speed(self, config: Configuration, gear_down: bool) -> DragPolar:
        """The polar in a flap configuration (no wave drag at low speed)."""
        return replace(
            self,
            CD0=self.CD0 + config.dCD0 + (config.gear_dCD0 if gear_down else 0.0),
            e=self.e - config.de,
            CLmax_clean=config.CLmax,
            wave=None,
        )
