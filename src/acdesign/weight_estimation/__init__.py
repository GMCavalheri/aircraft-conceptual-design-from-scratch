"""Weight estimation: class I (empty-weight and fuel fractions) and class II (components)."""

from acdesign.weight_estimation.class_one import (
    ClassOneResult,
    empty_weight_fraction,
    max_lift_to_drag,
    size_class_one,
)
from acdesign.weight_estimation.class_two import (
    ClassTwoInputs,
    component_masses,
    empty_mass,
    group_masses,
    operating_empty_mass,
)
from acdesign.weight_estimation.fractions import (
    FuelFractions,
    breguet_cruise_fraction,
    breguet_hold_fraction,
    breguet_range,
    mission_fractions,
)

__all__ = [
    "ClassOneResult",
    "ClassTwoInputs",
    "FuelFractions",
    "breguet_cruise_fraction",
    "breguet_hold_fraction",
    "breguet_range",
    "component_masses",
    "empty_mass",
    "empty_weight_fraction",
    "group_masses",
    "max_lift_to_drag",
    "mission_fractions",
    "operating_empty_mass",
    "size_class_one",
]
