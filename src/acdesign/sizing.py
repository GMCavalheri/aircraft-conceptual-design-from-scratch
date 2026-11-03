"""Design synthesis: size an aircraft for a mission by closing every discipline on W0.

One iteration, starting from a take-off mass W0:

1. **Constraint analysis** with the current drag polar gives the design point (W/S, T/W).
2. **Geometry**: wing area S = W0 g/(W/S); planform from the design's A, λ, Λ; tails from
   volume coefficients; engines rubber-scaled to T = (T/W) W0 g / N.
3. **Aerodynamics**: VLM lift slope and span efficiency (AERO-01), component drag build-up,
   Korn wave drag → a new polar.
4. **Weights**: class II component masses (Raymer structure/propulsion, FLOPS systems and
   operating items) → OEW.
5. **Mission fuel**: segment fractions with Breguet cruise at the polar's mid-cruise L/D and
   the engine's TSFC at the thrust that holds it (AERO-03) → fuel mass.
6. W0 ← OEW + payload + fuel.

The fuselage is the reference's: it is fixed by the cabin, which the mission fixes. Every
constant below is an assumption unless labelled otherwise; the 737-800 description in
``validation/reference_aircraft.py`` uses the same ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from acdesign.constraint_analysis import Configuration, ConstraintDiagram, DragPolar
from acdesign.constraint_analysis import constraint_diagram as make_diagram
from acdesign.external.atmosphere import isa
from acdesign.external.engine import CFM56_7B26, Engine, EngineData
from acdesign.external.wing_aero import Planform, span_efficiency
from acdesign.geometry import fuselage_wetted_area, nacelle_wetted_area, surface_wetted_area
from acdesign.units import DEG, FT, G0, INCH
from acdesign.weight_estimation.class_two import (
    ClassTwoInputs,
    component_masses,
    operating_empty_mass,
)
from acdesign.weight_estimation.fractions import (
    F_CLIMB,
    F_TAKEOFF,
    FuelFractions,
    breguet_cruise_fraction,
    mission_fractions,
)
from acdesign.wing_tail_sizing.drag import (
    Q_FUSELAGE,
    Q_NACELLE,
    Q_TAIL,
    Q_WING,
    Component,
    WaveDrag,
    ff_fuselage,
    ff_lifting,
    ff_nacelle,
    oswald_kroo,
    parasite_drag,
)

# --- shared assumptions (labelled; used for the sized design and the 737-800 alike) ---------
TC_ROOT, TC_MEAN = 0.13, 0.11  # wing root and mean thickness ratios
TC_HT, TC_VT = 0.10, 0.12  # tail thickness ratios
LIMIT_LOAD_FACTOR = 2.5  # FAR 25.337 minimum for transports of this weight
CONTROL_SURFACE_FRACTIONS = (
    0.25,
    0.25,
    0.30,
)  # of wing, tailplane, fin: wing devices, elevator, rudder  # noqa: E501
F_W_TAIL = 1.5  # fuselage width at the tailplane [m]
GEAR_LOAD_FACTOR = 3.0
MAIN_GEAR_LENGTH, NOSE_GEAR_LENGTH = 1.8, 1.3  # [m]
ENGINE_CONTROLS_LENGTH = 30.0  # routing, both engines [m]
FUEL_TANKS = 3
FUEL_DENSITY = 0.803  # kg/L, deduction from D6-58325-7 2.1.3 (26,024 L = 20,897 kg)
FLIGHT_CREW, CABIN_CREW = 2, 4  # FAR 121.391: one attendant per 50 seats (184 max)
ENGINE_WEIGHT_EXPONENT = 1.1  # rubber engine mass ∝ thrust^1.1 (Raymer, ch. 10)
NACELLE_LENGTH_EXPONENT, NACELLE_DIAMETER_EXPONENT = 0.4, 0.5  # (Raymer, ch. 10)
HOLD = (1500 * FT, 0.40)  # hold altitude [m] and Mach


@dataclass(frozen=True)
class Cabin:
    """Cabin layout (data: D6-58325-7 2.4.4 mixed class) and the fuselage that wraps it."""

    pax_first: int = 12
    pax_tourist: int = 148
    first_rows: int = 3  # 4 abreast at 36 in
    tourist_rows: int = 25  # 6 abreast at 32 in
    service_length: float = 4.5  # galleys, lavatories, door zones [m]: assumption
    fuselage_length: float = 38.08  # data (JSR)
    fuselage_diameter: float = 3.73  # data (JSR)

    @property
    def length(self) -> float:
        return self.first_rows * 36 * INCH + self.tourist_rows * 32 * INCH + self.service_length


@dataclass(frozen=True)
class Design:
    """Design choices. The planform and tail shapes default to the 737-800's (data, JSR),
    so that the comparison isolates the sizing; volume coefficients are Raymer's typical
    jet-transport values (ch. 6); CLmax values are assumptions."""

    AR: float = 9.44
    taper: float = 0.278
    sweep: float = 25.0 * DEG
    engine: EngineData = CFM56_7B26
    n_engines: int = 2
    V_ht: float = 1.00
    V_vt: float = 0.09
    ht_shape: tuple[float, float, float] = (5.54, 0.186, 30.0 * DEG)  # A, λ, Λ (data, JSR)
    vt_shape: tuple[float, float, float] = (1.56, 0.31, 35.0 * DEG)  # (data, JSR)
    tail_arm_fraction: float = 17.68 / 38.08  # of fuselage length (deduction, JSR)
    cabin: Cabin = field(default_factory=Cabin)
    CLmax_takeoff: float = 2.1
    CLmax_landing: float = 2.7
    ws: float | None = None  # wing loading [Pa]; None: the constraint design point
    tw: float | None = None  # thrust loading; None: the constraint envelope at ws

    def with_(self, **changes) -> Design:
        return replace(self, **changes)


@dataclass(frozen=True)
class Geometry:
    wing: Planform
    htail: Planform
    vtail: Planform  # "span" is the fin height
    l_ht: float  # tail arms, wing to tail quarter-chord of MAC [m]
    l_vt: float
    fuselage_length: float
    fuselage_diameter: float
    cabin_length: float
    nacelle_length: float
    nacelle_diameter: float
    n_engines: int

    def wetted_areas(self) -> dict[str, float]:
        exposed_wing = self.wing.S - self.wing.c_root * self.fuselage_diameter
        return {
            "wing": surface_wetted_area(exposed_wing, TC_MEAN),
            "horizontal_tail": surface_wetted_area(self.htail.S, TC_HT),
            "vertical_tail": surface_wetted_area(self.vtail.S, TC_VT),
            "fuselage": fuselage_wetted_area(self.fuselage_length, self.fuselage_diameter),
            "nacelles": self.n_engines
            * nacelle_wetted_area(self.nacelle_length, self.nacelle_diameter),
        }


def size_geometry(design: Design, S: float, thrust: float) -> Geometry:
    """Geometry of a wing of area ``S`` [m²] and engines of ``thrust`` [N] each."""
    wing = Planform(S, design.AR, design.taper, design.sweep)
    cab = design.cabin
    l_t = design.tail_arm_fraction * cab.fuselage_length
    S_ht = design.V_ht * wing.mac * S / l_t
    S_vt = design.V_vt * wing.b * S / l_t
    sf = thrust / design.engine.rated_thrust
    return Geometry(
        wing=wing,
        htail=Planform(S_ht, *design.ht_shape),
        vtail=Planform(S_vt, *design.vt_shape),
        l_ht=l_t,
        l_vt=l_t,
        fuselage_length=cab.fuselage_length,
        fuselage_diameter=cab.fuselage_diameter,
        cabin_length=cab.length,
        nacelle_length=design.engine.nacelle_length * sf**NACELLE_LENGTH_EXPONENT,
        nacelle_diameter=design.engine.nacelle_diameter * sf**NACELLE_DIAMETER_EXPONENT,
        n_engines=design.n_engines,
    )


def drag_polar(geo: Geometry, design: Design, M: float, h: float) -> tuple[DragPolar, dict]:
    """Polar from the component build-up at the cruise condition; Oswald from the VLM."""
    w, ht, vt = geo.wing, geo.htail, geo.vtail
    S_wet = geo.wetted_areas()
    comps = [
        Component("wing", S_wet["wing"], w.mac, ff_lifting(TC_MEAN, M, w.sweep_at(0.4)), Q_WING),
        Component("horizontal tail", S_wet["horizontal_tail"], ht.mac, ff_lifting(TC_HT, M, ht.sweep_at(0.4)), Q_TAIL),  # noqa: E501
        Component("vertical tail", S_wet["vertical_tail"], vt.mac, ff_lifting(TC_VT, M, vt.sweep_at(0.4)), Q_TAIL),  # noqa: E501
        Component("fuselage", S_wet["fuselage"], geo.fuselage_length, ff_fuselage(geo.fuselage_length / geo.fuselage_diameter), Q_FUSELAGE),  # noqa: E501
        Component("nacelles", S_wet["nacelles"], geo.nacelle_length, ff_nacelle(geo.nacelle_length / geo.nacelle_diameter), Q_NACELLE),  # noqa: E501
    ]  # fmt: skip
    cd = parasite_drag(comps, w.S, M, h)
    CD0 = sum(cd.values())
    e = oswald_kroo(span_efficiency(w), geo.fuselage_diameter, w.b, CD0, w.AR)
    polar = DragPolar(
        CD0=CD0,
        e=e,
        AR=w.AR,
        takeoff=Configuration(CLmax=design.CLmax_takeoff, dCD0=0.015, de=0.05),
        landing=Configuration(CLmax=design.CLmax_landing, dCD0=0.060, de=0.10, gear_dCD0=0.020),
        wave=WaveDrag(TC_MEAN, w.sweep),
    )
    return polar, cd


def class_two_inputs(
    geo: Geometry,
    W0: float,
    mission,
    thrust: float,
    engine: EngineData,
    fuel_capacity: float,
    cabin: Cabin,
    CLmax_landing: float,
) -> ClassTwoInputs:
    """Class II inputs of a geometry at take-off mass ``W0`` with engines of ``thrust`` [N]
    and tanks for ``fuel_capacity`` [kg]."""
    w, ht, vt = geo.wing, geo.htail, geo.vtail
    f_w, f_e, f_r = CONTROL_SURFACE_FRACTIONS
    sf = thrust / engine.rated_thrust
    W_l = mission.landing_weight_ratio * W0
    V_stall = float(np.sqrt(2 * W_l * G0 / (1.225 * w.S * CLmax_landing)))
    if cabin.pax_first + cabin.pax_tourist != mission.passengers:
        raise ValueError("the cabin layout does not seat the mission's passengers")
    return ClassTwoInputs(
        W_dg=W0,
        W_l=W_l,
        N_z=1.5 * LIMIT_LOAD_FACTOR,
        M_max=0.84,  # data: JSR Mmo of the 737-800
        design_range=mission.design_range,
        S_w=w.S,
        A=w.AR,
        tc_root=TC_ROOT,
        taper=w.taper,
        sweep=w.sweep,
        S_csw=f_w * w.S,
        b_w=w.b,
        S_ht=ht.S,
        A_h=ht.AR,
        sweep_ht=ht.sweep,
        b_h=ht.b,
        L_t=geo.l_ht,
        S_e=f_e * ht.S,
        F_w=F_W_TAIL,
        S_vt=vt.S,
        A_v=vt.AR,
        sweep_vt=vt.sweep,
        tc_root_vt=TC_VT,
        Ht_Hv=0.0,
        S_r=f_r * vt.S,
        L_f=geo.fuselage_length,
        D_f=geo.fuselage_diameter,
        S_f=fuselage_wetted_area(geo.fuselage_length, geo.fuselage_diameter),
        L_cabin=geo.cabin_length,
        K_door=1.12,
        K_Lg=1.0,
        N_gear=GEAR_LOAD_FACTOR,
        L_m=MAIN_GEAR_LENGTH,
        L_n=NOSE_GEAR_LENGTH,
        N_mw=4,
        N_nw=2,
        N_mss=2,
        V_stall=V_stall,
        N_en=geo.n_engines,
        W_en=engine.dry_mass * sf**ENGINE_WEIGHT_EXPONENT,
        T_en=thrust,
        nacelle_length=geo.nacelle_length,
        nacelle_width=geo.nacelle_diameter,
        S_n=nacelle_wetted_area(geo.nacelle_length, geo.nacelle_diameter),
        K_tr=1.18,
        L_ec=ENGINE_CONTROLS_LENGTH,
        V_t=fuel_capacity / FUEL_DENSITY / 1000.0,
        V_i=fuel_capacity / FUEL_DENSITY / 1000.0,
        fuel_capacity=fuel_capacity,
        N_t=FUEL_TANKS,
        flight_crew=FLIGHT_CREW,
        cabin_crew=CABIN_CREW,
        pax_first=cabin.pax_first,
        pax_business=0,
        pax_tourist=cabin.pax_tourist,
    )


@dataclass(frozen=True)
class MissionFuel:
    fractions: FuelFractions
    LD_cruise: float
    CL_cruise: float  # at mid-cruise weight
    tsfc_cruise: float
    LD_hold: float
    tsfc_hold: float

    def fuel(self, W0: float) -> float:
        return self.fractions.fuel * W0


def mission_fuel(mission, polar: DragPolar, S: float, W0: float, engine: Engine, n: int):
    """Mission fuel fractions at take-off mass ``W0`` with the polar's mid-cruise L/D and the
    engine's TSFC at the thrust that holds it."""
    h, M = mission.cruise_altitude, mission.cruise_mach
    atm = isa(h)
    V = M * float(atm.a)
    q = 0.5 * float(atm.rho) * V**2
    W_start = F_TAKEOFF * F_CLIMB * W0
    f = 0.8
    for _ in range(50):
        W_mid = W_start * (1 + f) / 2
        CL = W_mid * G0 / (q * S)
        LD = float(polar.LD(CL, M))
        tsfc = engine.tsfc(h, M, W_mid * G0 / LD / n)
        f_new = breguet_cruise_fraction(mission.design_range, V, LD, tsfc)
        if abs(f_new - f) < 1e-12:
            break
        f = f_new
    h_hold, M_hold = HOLD
    W_hold = W0 * (1 - (1 - F_TAKEOFF * F_CLIMB * f))  # ~ landing weight
    tsfc_hold = engine.tsfc(h_hold, M_hold, W_hold * G0 / polar.LDmax / n)
    fr = mission_fractions(mission, V, LD, polar.LDmax, tsfc, tsfc_hold)
    return MissionFuel(fr, LD, CL, tsfc, polar.LDmax, tsfc_hold)


@dataclass(frozen=True)
class SizedAircraft:
    design: Design
    mission: object
    W0: float  # take-off mass [kg]
    ws: float  # [Pa]
    tw: float
    thrust: float  # per engine, sea-level static [N]
    geometry: Geometry
    polar: DragPolar
    drag_breakdown: dict[str, float]
    masses: dict[str, float]  # class II components [kg]
    fuel: MissionFuel
    diagram: ConstraintDiagram
    history: tuple[float, ...]

    @property
    def S(self) -> float:
        return self.geometry.wing.S

    @property
    def oew(self) -> float:
        return operating_empty_mass(self.masses)

    @property
    def fuel_mass(self) -> float:
        return self.fuel.fuel(self.W0)

    @property
    def engine(self) -> Engine:
        return Engine(self.design.engine).scaled(self.thrust)


def size_aircraft(
    mission,
    design: Design | None = None,
    W0: float = 75000.0,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> SizedAircraft:
    """Close the design on W0 by fixed-point iteration (relative tolerance ``tol``)."""
    design = Design() if design is None else design
    h, M = mission.cruise_altitude, mission.cruise_mach
    engine = Engine(design.engine)
    ws = design.ws if design.ws is not None else 6000.0
    tw = design.tw if design.tw is not None else 0.29
    history = [W0]
    prev = None
    for _ in range(max_iter):
        thrust = tw * W0 * G0 / design.n_engines
        geo = size_geometry(design, W0 * G0 / ws, thrust)
        polar, cd = drag_polar(geo, design, M, h)
        diagram = make_diagram(mission, polar, engine, design.n_engines)
        ws = design.ws if design.ws is not None else diagram.design[0]
        env = float(np.interp(ws, diagram.ws, diagram.envelope))
        tw = design.tw if design.tw is not None else env
        thrust = tw * W0 * G0 / design.n_engines
        geo = size_geometry(design, W0 * G0 / ws, thrust)
        polar, cd = drag_polar(geo, design, M, h)
        fuel = mission_fuel(mission, polar, geo.wing.S, W0, engine.scaled(thrust), design.n_engines)
        inputs = class_two_inputs(
            geo, W0, mission, thrust, design.engine, fuel.fuel(W0), design.cabin,
            design.CLmax_landing,
        )  # fmt: skip
        masses = component_masses(inputs)
        new = operating_empty_mass(masses) + mission.payload + fuel.fuel(W0)
        history.append(new)
        converged = abs(new - W0) < tol * new
        # secant (Steffensen-like) acceleration of the fixed point W0 = F(W0)
        residual = new - W0
        if prev is not None and residual != prev[1]:
            step = residual * (W0 - prev[0]) / (residual - prev[1])
            prev, W0 = (W0, residual), W0 - step
        else:
            prev, W0 = (W0, residual), new
        if converged:
            W0 = new
            return SizedAircraft(
                design, mission, W0, ws, tw, thrust, geo, polar, cd, masses, fuel, diagram,
                tuple(history),
            )  # fmt: skip
    raise RuntimeError("sizing did not converge")
