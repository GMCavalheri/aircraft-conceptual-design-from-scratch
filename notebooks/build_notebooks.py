"""Generate and execute the demo notebooks from the cell sources below.

Run with ``uv run python notebooks/build_notebooks.py``. Keeping the sources here (instead of
hand-editing .ipynb JSON) makes the notebooks reviewable in diffs and reproducible: rebuilds are
byte-identical.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

SETUP = """\
import sys
import numpy as np
import matplotlib.pyplot as plt
from acdesign import plotting as P
from acdesign.requirements import B737_800_MISSION as M
from acdesign.units import FT, G0, LB, NMI

P.use_style()
np.set_printoptions(precision=4, suppress=True)
sys.path.insert(0, "../validation")  # cited reference data and the reference aircraft
from reference import b737_800

R = b737_800()"""

NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "01_requirements.ipynb": [
        (
            "md",
            """\
# 1 · Requirements and the reference aircraft

The design mission and the 737-800 data it is checked against.
Lesson: [01](../docs/lessons/01-requirements-and-reference.md) ·
Theory: [requirements](../docs/requirements.md).""",
        ),
        ("code", SETUP),
        ("md", "The design mission, in SI and in the units of the airport-planning charts:"),
        (
            "code",
            """\
print(f"payload {M.payload:,.0f} kg = {M.payload / LB:,.0f} lb")
print(f"range {M.design_range / NMI:,.0f} nmi at Mach {M.cruise_mach}, FL{M.cruise_altitude / FT / 100:.0f}")
print(f"field lengths: take-off {M.takeoff_field_length / FT:,.0f} ft, landing {M.landing_field_length / FT:,.0f} ft")""",
        ),
        (
            "md",
            """\
The transcribed 737-800 data checks itself: the payload-range chart's full-fuel corner must
give back the fuel capacity of the weight table.""",
        ),
        (
            "code",
            """\
fuel_from_chart = R["mtow"] - R["oew_plus_payload_at_full_fuel_mtow"]
print(f"chart: {fuel_from_chart:,.0f} kg, weight table: {R['usable_fuel']:,.0f} kg")
print(f"MZFW - OEW - max payload = {R['mzfw'] - R['oew'] - R['max_structural_payload']:.3f} kg")""",
        ),
        (
            "code",
            """\
from mission_definition import envelope

x, y = envelope(R)
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.plot(x, np.array(y) / 1e3, "--", color=P.REFERENCE, label="737-800 at MTOW")
ax.plot(M.design_range / NMI, M.payload / LB / 1e3, "o", color=P.SERIES[1], label="design mission")
ax.set_xlabel("range [nmi]"); ax.set_ylabel("payload [1,000 lb]"); ax.legend();""",
        ),
    ],
    "02_weight_estimation.ipynb": [
        (
            "md",
            """\
# 2 · Weight estimation

Class I sizing, the snowball, and class II on the 737-800's geometry.
Lesson: [02](../docs/lessons/02-weight-estimation.md) ·
Theory: [weight estimation](../docs/weight_estimation.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.weight_estimation import (
    breguet_cruise_fraction, size_class_one, max_lift_to_drag,
    component_masses, group_masses, operating_empty_mass,
)
from reference_aircraft import class_two_inputs, crew_mass, wetted_areas""",
        ),
        ("md", "Breguet: the cruise fraction for the design range, at three L/D values."),
        (
            "code",
            """\
V, tsfc = 231.3, 17.12e-6  # Mach 0.78 at FL350; AERO-03 cruise TSFC [kg/(N s)]
for LD in (15.0, 16.5, 18.0):
    f = breguet_cruise_fraction(M.design_range, V, LD, tsfc)
    print(f"L/D {LD}: W_end/W_start = {f:.4f}, cruise burns {1 - f:.1%}")""",
        ),
        (
            "md",
            "Class I with the reference's wetted-area ratio; then the growth factor by adding payload.",
        ),
        (
            "code",
            """\
from dataclasses import replace

LD = max_lift_to_drag(R["wing_aspect_ratio"], sum(wetted_areas().values()) / R["wing_area"])
r = size_class_one(M, V, LD, tsfc, 18.0e-6, crew=crew_mass())
r2 = size_class_one(replace(M, cargo=1000.0), V, LD, tsfc, 18.0e-6, crew=crew_mass())
print(f"(L/D)max {LD:.2f}; W0 = {r.W0:,.0f} kg ({r.W0 / R['mtow'] - 1:+.1%} vs MTOW), {len(r.history) - 1} iterations")
print(f"growth factor dW0/dWp = {(r2.W0 - r.W0) / 1000:.2f}")""",
        ),
        ("md", "Class II on the published 737-800 geometry, no calibration:"),
        (
            "code",
            """\
m = component_masses(class_two_inputs())
for g, v in group_masses(m).items():
    print(f"{g:16s} {v:8,.0f} kg")
oew = operating_empty_mass(m)
print(f"OEW {oew:,.0f} kg vs {R['oew']:,.0f} kg published ({oew / R['oew'] - 1:+.1%})")""",
        ),
    ],
    "03_constraint_diagram.ipynb": [
        (
            "md",
            """\
# 3 · The constraint diagram

Every requirement as T/W(W/S), with the AERO-03 engine's thrust lapse.
Lesson: [03](../docs/lessons/03-constraint-diagram.md) ·
Theory: [constraint analysis](../docs/constraint_analysis.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.constraint_analysis import constraint_diagram
from acdesign.external.engine import Engine
from constraint_validation import reference_polar""",
        ),
        (
            "code",
            """\
e = Engine()
for h, Mach, rating in [(0, 0.2, 1.0), (10668, 0.78, 0.92)]:
    print(f"lapse at {h:5.0f} m, Mach {Mach}, rating {rating}: {float(e.lapse(h, Mach, rating)):.3f}")""",
        ),
        (
            "code",
            """\
polar = reference_polar()
d = constraint_diagram(M, polar, e)
fig, ax = plt.subplots(figsize=(7.5, 4.5))
for name, tw in d.tw.items():
    ax.plot(d.ws, tw, label=name)
for name, ws in d.ws_max.items():
    ax.axvline(ws, ls="--", label=name)
ax.plot(*d.design, "ko")
ax.set_ylim(0.15, 0.4); ax.set_xlabel("W/S [Pa]"); ax.set_ylabel("T/W"); ax.legend(fontsize=7);
print("design point", d.design, "set by", d.active(d.design[0]))""",
        ),
        ("md", "Change a requirement: a 1,500 m landing field moves the wing-loading limit."),
        (
            "code",
            """\
from dataclasses import replace

d2 = constraint_diagram(replace(M, landing_field_length=1500.0), polar, e)
print(f"W/S limit {d.ws_limit:,.0f} Pa -> {d2.ws_limit:,.0f} Pa; T/W {d.design[1]:.3f} -> {d2.design[1]:.3f}")""",
        ),
    ],
    "04_wing_and_tail_sizing.ipynb": [
        (
            "md",
            """\
# 4 · Wing and tail sizing, and closing the design

VLM lift slope with the Göthert rule, the drag build-up, and the closed sizing loop.
Lesson: [04](../docs/lessons/04-wing-and-tail-sizing.md) ·
Theory: [wing and tail sizing](../docs/wing_tail_sizing.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.external.wing_aero import Planform, lift_slope, lift_slope_datcom, downwash_gradient
from acdesign.sizing import size_aircraft""",
        ),
        (
            "code",
            """\
w = Planform(124.6, 9.44, 0.278, np.deg2rad(25))
for Mach in (0.0, 0.5, 0.78):
    print(f"Mach {Mach}: VLM {lift_slope(w, Mach):.3f}/rad, DATCOM {lift_slope_datcom(w, Mach):.3f}/rad")
print(f"downwash gradient at the tail (17.68 m aft, 1.5 m up), Mach 0.78: {downwash_gradient(w, 17.68, 1.5, 0.78):.3f}")""",
        ),
        (
            "code",
            """\
a = size_aircraft(M)
print(f"W0 {a.W0:,.0f} kg | OEW {a.oew:,.0f} | fuel {a.fuel_mass:,.0f} | S {a.S:.1f} m2 | T {a.thrust / 1e3:.1f} kN")
print(f"CD0 {a.polar.CD0 * 1e4:.0f} counts, e {a.polar.e:.3f}, cruise L/D {a.fuel.LD_cruise:.2f}")
for k, v in a.drag_breakdown.items():
    print(f"  {k:26s} {v * 1e4:5.1f} counts")""",
        ),
        ("md", "Change a design choice — a 30° sweep — and re-size:"),
        (
            "code",
            """\
from acdesign.sizing import Design

b = size_aircraft(M, Design(sweep=np.deg2rad(30)))
print(f"W0 {b.W0:,.0f} kg ({b.W0 / a.W0 - 1:+.1%}), fuel {b.fuel_mass:,.0f} kg ({b.fuel_mass / a.fuel_mass - 1:+.1%})")""",
        ),
    ],
    "05_structural_sizing_check.ipynb": [
        (
            "md",
            """\
# 5 · Structural sizing check

A physics-based wing box on AERO-02, against the statistical wing mass.
Lesson: [05](../docs/lessons/05-structural-sizing-check.md) ·
Theory: [structural sizing check](../docs/structural_sizing_check.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.sizing import size_aircraft
from acdesign.structural_sizing_check import wing_box""",
        ),
        (
            "code",
            """\
a = size_aircraft(M)
m = a.masses
r = wing_box(a.geometry.wing, a.geometry.fuselage_diameter, a.W0, a.W0 - a.fuel_mass,
             a.fuel_mass, m["wing"], (m["engines"] + m["nacelles"]) / 2)
print(f"ideal box {r.box_mass:,.0f} kg -> wing {r.wing_mass:,.0f} kg vs class II {m['wing']:,.0f} kg")
print(f"root moment {r.root_moment / 1e6:.2f} MN m, 1-g tip deflection {r.tip_deflection_1g:.2f} m")""",
        ),
        (
            "code",
            """\
fig, ax = plt.subplots(figsize=(7, 3.8))
ax.plot(r.y, r.t_upper * 1e3, label="upper cover")
ax.plot(r.y, r.t_lower * 1e3, label="lower cover")
ax.plot(r.y, r.t_web * 1e3, label="spar webs")
ax.set_xlabel("y [m]"); ax.set_ylabel("thickness [mm]"); ax.legend();""",
        ),
    ],
    "06_performance_and_stability.ipynb": [
        (
            "md",
            """\
# 6 · Performance and stability verification

The mission flown by time integration, and the AERO-04 stability model.
Lesson: [06](../docs/lessons/06-performance-and-stability.md) ·
Theory: [performance verification](../docs/performance_verification.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.sizing import size_aircraft
from acdesign.performance_verification import design_range, stability_model, modes, flying_qualities""",
        ),
        (
            "code",
            """\
a = size_aircraft(M)
res = design_range(a)
for s in res.segments:
    print(f"{s.name:20s} {s.distance / NMI:7,.0f} nmi {s.fuel:8,.0f} kg")
print(f"range {res.range / NMI:,.0f} nmi on the sized fuel (requirement {M.design_range / NMI:,.0f})")""",
        ),
        (
            "code",
            """\
s = stability_model(a)
mo = modes(s)
print(f"static margin {s.static_margin:.1%} MAC (textbook {s.h_n_classic - s.balance.h_cg:.1%})")
for k, (v, ok) in flying_qualities(mo).items():
    print(f"{k:38s} {v:8.3f}  {'ok' if ok else 'NOT MET'}")""",
        ),
    ],
    "07_trade_studies.ipynb": [
        (
            "md",
            """\
# 7 · Trade studies

Every point a re-sized aircraft.
Lesson: [07](../docs/lessons/07-trade-studies.md) ·
Theory: [trade studies](../docs/trade_studies.md).""",
        ),
        (
            "code",
            SETUP
            + """
from acdesign.trade_studies import aspect_ratio
from acdesign.sizing import Design, size_aircraft
from acdesign.external.engine import LEAP_1B28""",
        ),
        (
            "code",
            """\
pts = aspect_ratio(M, values=(8.0, 10.0, 12.0))
for p in pts:
    print(f"A {p.value:4.1f}: W0 {p.W0:7,.0f} kg, fuel {p.fuel:6,.0f} kg, L/D {p.LD:.2f}, T/W set by {p.active}")""",
        ),
        (
            "code",
            """\
base, leap = size_aircraft(M), size_aircraft(M, Design(engine=LEAP_1B28))
print(f"LEAP-1B28 vs CFM56-7B26/3: fuel {leap.fuel_mass / base.fuel_mass - 1:+.1%}, W0 {leap.W0 / base.W0 - 1:+.1%}")""",
        ),
    ],
}


def _merge_streams(outputs):
    """Join consecutive stdout/stderr chunks; how the kernel splits them depends on timing."""
    merged = []
    for out in outputs:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and out.get("output_type") == "stream"
            and prev.get("output_type") == "stream"
            and prev.get("name") == out.get("name")
        ):
            prev["text"] += out["text"]
        else:
            merged.append(out)
    return merged


def build(name: str, cells: list[tuple[str, str]]) -> Path:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.cells = [
        nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
        for kind, src in cells
    ]
    for i, cell in enumerate(nb.cells):
        cell.id = f"cell-{i:02d}"  # stable ids keep rebuilds diff-free
    NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        record_timing=False,
        resources={"metadata": {"path": str(HERE)}},
    ).execute()
    for cell in nb.cells:
        cell.get("outputs", [])[:] = _merge_streams(cell.get("outputs", []))
    path = HERE / name
    nbformat.write(nb, path)
    return path


def main() -> None:
    for name, cells in NOTEBOOKS.items():
        print("built", build(name, cells).name)


if __name__ == "__main__":
    main()
