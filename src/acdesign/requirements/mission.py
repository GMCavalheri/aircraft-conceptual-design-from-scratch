"""Top-level mission requirements and the design mission of this project.

Every number of ``B737_800_MISSION`` is labelled: *data* (printed in a cited source, see
``validation/reference_data/b737_800.csv``), *assumption* (chosen), or *deduction*.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from acdesign.units import FT, LB, MINUTE, NMI


@dataclass(frozen=True)
class Reserves:
    """Fuel reserves: contingency on trip fuel, diversion to an alternate, then a hold."""

    contingency: float = 0.05  # fraction of trip fuel
    alternate_range: float = 200 * NMI  # [m]
    hold_time: float = 30 * MINUTE  # [s]
    hold_altitude: float = 1500 * FT  # [m]


@dataclass(frozen=True)
class Mission:
    """Design requirements (SI). The design range is the still-air cruise distance of the
    whole flight, take-off to touchdown, at standard day."""

    passengers: int
    mass_per_passenger: float  # [kg] including baggage
    design_range: float  # [m]
    cruise_mach: float
    cruise_altitude: float  # initial cruise, geopotential pressure altitude [m]
    takeoff_field_length: float  # FAR 25 field length at MTOW, sea level ISA [m]
    landing_field_length: float  # FAR 25 field length at MLW, sea level ISA [m]
    landing_weight_ratio: float  # MLW / MTOW for the landing constraint
    cargo: float = 0.0  # [kg] beyond passenger baggage
    reserves: Reserves = field(default_factory=Reserves)

    @property
    def payload(self) -> float:
        """Payload mass [kg]."""
        return self.passengers * self.mass_per_passenger + self.cargo


B737_800_MISSION = Mission(
    passengers=160,  # data: two-class seating (D6-58325-7 2.1.3)
    # assumption: 225 lb per passenger with baggage (Raymer, Aircraft Design, ch. 3:
    # 180 lb per person plus 40-60 lb of baggage) -> 36,000 lb payload
    mass_per_passenger=225 * LB,
    # assumption (requirement): 2,800 nmi. With 36,000 lb of payload the 737-800 flies this
    # just inside its MTOW / full-fuel corner (2,860 nmi with 37,000 lb, D6-58325-7 3.2.4),
    # so the reference aircraft's take-off weight for this mission is its MTOW within ~1 %.
    design_range=2800 * NMI,
    # assumption: Mach 0.78 at FL350, consistent with JSR's long-range cruise of 452 kt
    # (Mach 0.784 at FL350) and with AERO-03's cruise point
    cruise_mach=0.78,
    cruise_altitude=35000 * FT,
    # data (requirement = the reference's capability): D6-58325-7 3.3.29 and 3.4.3, read
    # from the charts at MTOW / MLW, sea level, standard day, dry runway
    takeoff_field_length=7800 * FT,
    landing_field_length=5800 * FT,
    landing_weight_ratio=146300 / 174200,  # deduction: MLW / MTOW of the 737-800 (2.1.3)
    # assumption: reserves in the style of the "typical mission rules" of the
    # airport-planning charts (5 % contingency, 200 nmi alternate, 30 min hold at 1,500 ft)
    reserves=Reserves(),
)
