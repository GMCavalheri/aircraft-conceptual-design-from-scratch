"""The 737-800 described with this package's inputs, from the cited reference data.

Every value is labelled: **data** (``reference_data/b737_800.csv``, ``tcds.csv``),
**assumption** (chosen, not published in the cited sources), or **deduction**. The class II
inputs were fixed before the weight equations were run against the reference OEW; none is
tuned to it.
"""

from __future__ import annotations

import numpy as np

from acdesign.geometry import fuselage_wetted_area, nacelle_wetted_area
from acdesign.requirements import B737_800_MISSION
from acdesign.units import INCH, LB
from acdesign.weight_estimation.class_two import ClassTwoInputs

from reference import b737_800, icao, tcds

R = b737_800()

# --- assumptions used by more than one discipline --------------------------------------
TC_ROOT = 0.13  # wing root thickness ratio (not in the cited sources)
TC_ROOT_VT = 0.12  # fin root thickness ratio
CLMAX_LANDING = 2.6  # landing-flap CLmax, for the stall speed in the gear equation
LIMIT_LOAD_FACTOR = 2.5  # FAR 25.337 minimum positive limit load factor for this weight
FLIGHT_CREW, CABIN_CREW = 2, 4  # one attendant per 50 seats for 184 seats (FAR 121.391)
# cabin: rows x pitch from the mixed-class layout (data, D6-58325-7 2.4.4) plus 4.5 m of
# galleys, lavatories and door zones (assumption)
FIRST_ROWS, ECONOMY_ROWS = 3, 25  # 12 first at 4 abreast, 148 economy at 6 abreast
CABIN_LENGTH = FIRST_ROWS * 36 * INCH + ECONOMY_ROWS * 32 * INCH + 4.5


def stall_speed(mass: float, S: float, CLmax: float, rho: float = 1.225) -> float:
    return float(np.sqrt(2 * mass * 9.80665 / (rho * S * CLmax)))


def class_two_inputs() -> ClassTwoInputs:
    S, b = R["wing_area"], R["wing_span_jsr"]  # data (JSR)
    S_ht, S_vt = R["htail_area"], R["vtail_area"]  # data (JSR)
    S_csw = 0.25 * S  # assumption: flaps, slats, ailerons and spoilers
    L_f, D_f = R["fuselage_length"], R["fuselage_diameter"]  # data (JSR)
    engine = icao("CFM56-7B26/3")
    return ClassTwoInputs(
        W_dg=R["mtow"],  # data
        W_l=R["mlw"],  # data
        N_z=1.5 * LIMIT_LOAD_FACTOR,
        M_max=R["mmo"],  # data (JSR)
        design_range=B737_800_MISSION.design_range,
        S_w=S,
        A=R["wing_aspect_ratio"],  # data
        tc_root=TC_ROOT,
        taper=R["wing_taper_ratio"],  # data
        sweep=R["wing_sweep_quarter_chord"],  # data
        S_csw=S_csw,
        b_w=b,
        S_ht=S_ht,
        A_h=R["htail_aspect_ratio"],  # data
        sweep_ht=R["htail_sweep_quarter_chord"],  # data
        b_h=R["htail_span"],  # data
        L_t=R["htail_arm"],  # data
        S_e=0.25 * S_ht,  # assumption: elevator area
        F_w=1.5,  # assumption: fuselage width at the tailplane [m]
        S_vt=S_vt,
        A_v=R["vtail_aspect_ratio"],  # data
        sweep_vt=R["vtail_sweep_quarter_chord"],  # data
        tc_root_vt=TC_ROOT_VT,
        Ht_Hv=0.0,  # data: conventional tail (D6-58325-7 2.2.5 drawing)
        S_r=0.30 * S_vt,  # assumption: rudder area
        L_f=L_f,
        D_f=D_f,
        S_f=fuselage_wetted_area(L_f, D_f),
        L_cabin=CABIN_LENGTH,
        K_door=1.12,  # data: two lower-deck side cargo doors (Raymer's factor for two)
        K_Lg=1.0,  # data: wing-mounted main gear
        N_gear=3.0,  # assumption: gear load factor
        L_m=1.8,  # assumption: main gear length [m]
        L_n=1.3,  # assumption: nose gear length [m]
        N_mw=4,  # data (JSR: 2 nose; 4 main wheels)
        N_nw=2,
        N_mss=2,
        V_stall=stall_speed(R["mlw"], S, CLMAX_LANDING),
        N_en=2,
        W_en=tcds("CFM56-7B26/3")["dry_mass"],  # data: EASA TCDS E.004
        T_en=engine["rated_thrust"],  # data: ICAO databank
        nacelle_length=R["nacelle_length"],  # data (JSR)
        nacelle_width=R["nacelle_max_width"],  # data (JSR)
        S_n=nacelle_wetted_area(R["nacelle_length"], R["nacelle_max_width"]),
        K_tr=1.18,  # data: thrust reversers fitted (Raymer's factor)
        L_ec=30.0,  # assumption: engine-to-cockpit routing, both engines [m]
        V_t=26.024,  # data: usable fuel 26,024 L (D6-58325-7 2.1.3)
        V_i=26.024,  # assumption: all integral tanks
        fuel_capacity=R["usable_fuel"],  # data
        N_t=3,  # assumption: left, right and centre tanks
        flight_crew=FLIGHT_CREW,
        cabin_crew=CABIN_CREW,
        pax_first=int(R["seats_first_mixed"]),  # data
        pax_business=0,
        pax_tourist=int(R["seats_economy_mixed"]),  # data
    )


def wetted_areas() -> dict[str, float]:
    """Wetted areas [m²] of the reference geometry (Raymer's and Torenbeek's estimates;
    exposed wing = reference area less the root-chord strip inside the fuselage)."""
    from acdesign.geometry import surface_wetted_area

    c_root = 2 * R["wing_area"] / (R["wing_span_jsr"] * (1 + R["wing_taper_ratio"]))
    exposed_wing = R["wing_area"] - c_root * R["fuselage_diameter"]
    return {
        "wing": surface_wetted_area(exposed_wing, TC_ROOT),
        "horizontal_tail": surface_wetted_area(R["htail_area"], 0.10),  # assumption t/c
        "vertical_tail": surface_wetted_area(R["vtail_area"], TC_ROOT_VT),
        "fuselage": fuselage_wetted_area(R["fuselage_length"], R["fuselage_diameter"]),
        "nacelles": 2 * nacelle_wetted_area(R["nacelle_length"], R["nacelle_max_width"]),
    }


def crew_mass() -> float:
    """Crew with baggage [kg]: FLOPS eqs. 119-120, 225 lb per pilot, 155 lb per attendant."""
    return (FLIGHT_CREW * 225 + CABIN_CREW * 155) * LB
