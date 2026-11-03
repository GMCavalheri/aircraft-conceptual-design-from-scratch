"""Regenerate every validation figure and results table.

Run with ``uv run python validation/run_all.py`` (about a minute; the trade studies re-size
the aircraft some 110 times).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "mission_definition.py",
    "weight_validation.py",
    "constraint_validation.py",
    "sizing_validation.py",
    "structure_validation.py",
    "performance_validation.py",
    "stability_validation.py",
    "trade_studies.py",
]

if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    for name in SCRIPTS:
        print(f"== {name}")
        runpy.run_path(str(HERE / name), run_name="__main__")
