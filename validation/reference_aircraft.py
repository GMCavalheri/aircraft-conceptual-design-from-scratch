"""The 737-800 described with this package's inputs, from the cited reference data.

Geometry is **data** (``reference_data/b737_800.csv``: JSR Table 2 and D6-58325-7);
everything the sources do not give comes from the shared **assumptions** of
``acdesign.sizing`` — the same ones the sized design uses — so the reference and the design
differ only in what the sizing decides. None was tuned to the reference's weights.
"""

from __future__ import annotations

from acdesign.external.engine import CFM56_7B26
from acdesign.external.wing_aero import Planform
from acdesign.requirements import B737_800_MISSION
from acdesign.sizing import (
    CABIN_CREW,
    FLIGHT_CREW,
    Cabin,
    Design,
    Geometry,
)
from acdesign.sizing import (
    class_two_inputs as _c2,
)
from acdesign.units import LB
from acdesign.weight_estimation.class_two import ClassTwoInputs

from reference import b737_800

R = b737_800()


def geometry() -> Geometry:
    return Geometry(
        wing=Planform(R["wing_area"], R["wing_aspect_ratio"], R["wing_taper_ratio"], R["wing_sweep_quarter_chord"]),  # noqa: E501
        htail=Planform(R["htail_area"], R["htail_aspect_ratio"], R["htail_taper_ratio"], R["htail_sweep_quarter_chord"]),  # noqa: E501
        vtail=Planform(R["vtail_area"], R["vtail_aspect_ratio"], R["vtail_taper_ratio"], R["vtail_sweep_quarter_chord"]),  # noqa: E501
        l_ht=R["htail_arm"],
        l_vt=R["vtail_arm"],
        fuselage_length=R["fuselage_length"],
        fuselage_diameter=R["fuselage_diameter"],
        cabin_length=Cabin().length,
        nacelle_length=R["nacelle_length"],
        nacelle_diameter=R["nacelle_max_width"],
        n_engines=2,
    )  # fmt: skip


def class_two_inputs() -> ClassTwoInputs:
    """At MTOW, with the ICAO-rated CFM56-7B26/3 and the published tank capacity."""
    return _c2(
        geometry(), R["mtow"], B737_800_MISSION, CFM56_7B26.rated_thrust, CFM56_7B26,
        R["usable_fuel"], Cabin(), Design().CLmax_landing,
    )  # fmt: skip


def wetted_areas() -> dict[str, float]:
    return geometry().wetted_areas()


def crew_mass() -> float:
    """Crew with baggage [kg]: FLOPS eqs. 119-120, 225 lb per pilot, 155 lb per attendant."""
    return (FLIGHT_CREW * 225 + CABIN_CREW * 155) * LB
