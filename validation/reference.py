"""Load the cited reference values in ``validation/reference_data``.

* ``b737_800()`` — Boeing D6-58325-7 Rev C (airport planning) and Jenkinson, Simpkin & Rhodes
  (1999) Data A Table 2, converted to SI on load (``units.py`` factors).
* ``icao(engine)``, ``tcds(engine)`` — the CFM56-7B and LEAP-1B rows of the ICAO Engine
  Emissions Databank and EASA TCDS, copied from AERO-03 with their citations.
"""

from __future__ import annotations

import csv
from pathlib import Path

from acdesign.units import DEG, FT, KT, LB, NMI

DATA = Path(__file__).resolve().parent / "reference_data"

# report unit -> (SI unit, factor)
_SI = {
    "lb": ("kg", LB),
    "ft": ("m", FT),
    "nmi": ("m", NMI),
    "kt": ("m/s", KT),
    "deg": ("rad", DEG),
    "m": ("m", 1.0),
    "m2": ("m2", 1.0),
    "-": ("-", 1.0),
}


def load(name: str) -> list[dict[str, str]]:
    with open(DATA / name) as f:
        rows = [line for line in f if not line.startswith("#")]
    return list(csv.DictReader(rows))


def b737_800_printed() -> dict[str, tuple[float, str, str]]:
    """{quantity: (value, unit, source)} exactly as transcribed (report units)."""
    return {
        r["quantity"]: (float(r["value"]), r["unit"], r["source"]) for r in load("b737_800.csv")
    }


def b737_800() -> dict[str, float]:
    """737-800 reference values in SI: masses in kg, lengths in m, angles in rad."""
    return {q: v * _SI[unit][1] for q, (v, unit, _) in b737_800_printed().items()}


def _row(name: str, engine: str) -> dict[str, str]:
    for row in load(name):
        if row["engine"] == engine:
            return row
    raise KeyError(engine)


def icao(engine: str) -> dict:
    """ICAO Engine Emissions Databank (Issue 32) row; thrust in N, fuel flows in kg/s."""
    r = _row("icao_eedb.csv", engine)
    out = {k: float(r[k]) for k in r if k not in ("engine", "uid", "combustor", "source")}
    out["rated_thrust"] = out.pop("rated_thrust_kN") * 1e3
    out.update(engine=r["engine"], uid=r["uid"], combustor=r["combustor"], source=r["source"])
    return out


def tcds(engine: str) -> dict:
    """EASA type-certificate data sheet values (thrust in N, dry mass in kg)."""
    r = _row("tcds.csv", engine)
    return {
        "engine": r["engine"],
        "takeoff_thrust": float(r["takeoff_thrust_daN"]) * 10.0,
        "max_continuous_thrust": float(r["max_continuous_thrust_daN"]) * 10.0,
        "dry_mass": float(r["dry_weight_kg"]),
        "source": r["source"],
    }
