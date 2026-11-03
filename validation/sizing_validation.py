"""Phase 4: the closed design — convergence, drag polar, planform — against the 737-800.

Writes ``docs/figures/sizing_convergence.png``, ``sizing_polar.png``, ``sizing_planform.png``
and ``validation/results/sizing.md``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from acdesign import plotting as P
from acdesign.external.wing_aero import Planform
from acdesign.requirements import B737_800_MISSION as M
from acdesign.sizing import Design, drag_polar, size_aircraft
from acdesign.units import G0

from reference import b737_800
from reference_aircraft import geometry as reference_geometry

RESULTS = Path(__file__).resolve().parent / "results"
R = b737_800()
WING_MAC_QC = 0.45  # x of the wing MAC quarter chord / fuselage length, for drawing only


def figure_convergence(a):
    P.use_style()
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    h = np.array(a.history) / 1e3
    ax.plot(range(len(h)), h, "o-", color=P.SERIES[0], ms=5, label="W0 from the weight build-up")
    ax.axhline(R["mtow"] / 1e3, color=P.REFERENCE, ls="--", lw=1.2, label="737-800 MTOW")
    ax.set_xlabel("iteration (secant-accelerated)")
    ax.set_ylabel("take-off mass [t]")
    ax.set_title("Closing the design on W0")
    ax.legend()
    return P.save(fig, "sizing_convergence.png")


def figure_polar(a, ref_polar):
    P.use_style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    CL = np.linspace(0.0, 0.9, 181)
    Mc = M.cruise_mach
    for polar, label, c, ls in [(a.polar, "sized", P.SERIES[0], "-"), (ref_polar, "737-800 geometry", P.REFERENCE, "--")]:  # fmt: skip  # noqa: E501
        axes[0].plot(polar.CD(CL, Mc) * 1e4, CL, color=c, ls=ls, lw=1.6, label=label)
        axes[1].plot(CL, polar.LD(CL, Mc), color=c, ls=ls, lw=1.6, label=label)
    axes[0].set_xlabel("CD [counts] at Mach 0.78")
    axes[0].set_ylabel("CL")
    axes[0].set_title("Drag polar")
    axes[1].axvline(a.fuel.CL_cruise, color=P.TEXT_MUTED, lw=1, ls=":")
    axes[1].set_xlabel("CL")
    axes[1].set_ylabel("L/D at Mach 0.78")
    axes[1].set_title(f"Mid-cruise CL {a.fuel.CL_cruise:.3f}, L/D {a.fuel.LD_cruise:.2f}")
    axes[0].legend()
    names = list(a.drag_breakdown)
    vals = [a.drag_breakdown[k] * 1e4 for k in names]
    axes[2].barh(range(len(names))[::-1], vals, color=P.SERIES[0], height=0.6)
    axes[2].set_yticks(range(len(names))[::-1], names)
    axes[2].set_xlabel("CD0 [counts]")
    axes[2].set_title(f"Zero-lift drag build-up: {a.polar.CD0 * 1e4:.0f} counts")
    fig.tight_layout()
    return P.save(fig, "sizing_polar.png")


def _wing(ax, p: Planform, x_qc_mac, color, ls, label=None):
    """Draw a planform with its MAC quarter chord at ``x_qc_mac`` (nose at x = 0, x aft)."""
    x_le_root = x_qc_mac - p.x_mac_le - 0.25 * p.mac
    tan_le = np.tan(p.sweep_at(0.0))
    s = p.b / 2
    xs = [x_le_root, x_le_root + s * tan_le, x_le_root + s * tan_le + p.c_tip, x_le_root + p.c_root]
    xs += [x_le_root + s * tan_le + p.c_tip, x_le_root + s * tan_le, x_le_root]
    ys = [0, s, s, 0, -s, -s, 0]
    ax.plot(ys, xs, color=color, ls=ls, lw=1.6, label=label)


def _fin(ax, p: Planform, x_qc_mac, color, ls):
    x_le_root = x_qc_mac - p.x_mac_le - 0.25 * p.mac
    ax.plot([0, 0], [x_le_root, x_le_root + p.c_root], color=color, ls=ls, lw=3)


def figure_planform(a, ref):
    P.use_style()
    fig, ax = plt.subplots(figsize=(7, 7))
    for g, color, ls, label in [(ref, P.REFERENCE, "--", "737-800 (JSR Table 2)"), (a.geometry, P.SERIES[0], "-", "sized design")]:  # fmt: skip  # noqa: E501
        L, D = g.fuselage_length, g.fuselage_diameter
        x_w = WING_MAC_QC * L
        ax.plot([-D / 2, -D / 2, D / 2, D / 2], [0, L, L, 0], color=color, ls=ls, lw=1.0)
        _wing(ax, g.wing, x_w, color, ls, label)
        _wing(ax, g.htail, x_w + g.l_ht, color, ls)
        _fin(ax, g.vtail, x_w + g.l_vt, color, ls)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    ax.set_xlabel("y [m]")
    ax.set_ylabel("x [m] (nose at 0)")
    ax.set_title("Planform: sized design and the 737-800")
    ax.legend(loc="lower left")
    return P.save(fig, "sizing_planform.png")


def _fmt(v: float) -> str:
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    return f"{v:.1f}" if abs(v) >= 10 else f"{v:.2f}" if abs(v) >= 1 else f"{v:.4f}"


def write_results(a, ref, ref_polar):
    g = a.geometry
    rows = [
        ("take-off mass W0 [kg]", a.W0, R["mtow"]),
        ("operating empty mass [kg]", a.oew, R["oew"]),
        ("mission fuel incl. reserves [kg]", a.fuel_mass, R["mtow"] - R["oew"] - M.payload),
        ("wing area [m²]", a.S, R["wing_area"]),
        ("span [m]", g.wing.b, R["wing_span"]),
        ("MAC [m]", g.wing.mac, R["wing_mac"]),
        ("horizontal tail area [m²]", g.htail.S, R["htail_area"]),
        ("vertical tail area [m²]", g.vtail.S, R["vtail_area"]),
        ("thrust per engine, SLS [kN]", a.thrust / 1e3, 117.0),
        ("wing loading [Pa]", a.ws, R["mtow"] * G0 / R["wing_area"]),
        ("thrust loading", a.tw, 2 * 117e3 / (R["mtow"] * G0)),
        ("CD0 (build-up) [counts]", a.polar.CD0 * 1e4, ref_polar.CD0 * 1e4),
        ("Oswald e", a.polar.e, ref_polar.e),
    ]
    lines = [
        "# Sizing: the closed design against the 737-800",
        "",
        "Generated by `validation/sizing_validation.py`. Reference column: D6-58325-7 and JSR",
        "(data); its fuel is MTOW − OEW − payload, i.e. what the 737 carries at MTOW with",
        "the design payload, its CD0 and e are this package's build-up on its geometry.",
        "",
        "| quantity | sized | 737-800 | difference |",
        "|---|---|---|---|",
        *[f"| {n} | {_fmt(s)} | {_fmt(r)} | {s / r - 1:+.1%} |" for n, s, r in rows],
        "",
        f"Mid-cruise CL {a.fuel.CL_cruise:.3f}, L/D {a.fuel.LD_cruise:.2f}, "
        f"TSFC {a.fuel.tsfc_cruise * 1e6:.2f} mg/(N s); (L/D)max {a.polar.LDmax:.2f}. "
        f"Converged in {len(a.history) - 1} iterations; "
        f"active constraints: {a.diagram.active(a.ws)} (T/W), landing field length (W/S).",
        "",
    ]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "sizing.md").write_text("\n".join(lines))


if __name__ == "__main__":
    a = size_aircraft(M)
    ref = reference_geometry()
    ref_polar, _ = drag_polar(ref, Design(), M.cruise_mach, M.cruise_altitude)
    print(figure_convergence(a))
    print(figure_polar(a, ref_polar))
    print(figure_planform(a, ref))
    write_results(a, ref, ref_polar)
