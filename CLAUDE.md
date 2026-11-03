# CLAUDE.md

From-scratch aircraft conceptual design (mission requirements → weight sizing → constraint
diagram → wing and tail sizing → structural check → performance and stability verification →
trade studies), integrating the four pillar projects as libraries.
Plan: `AERO-05-aircraft-conceptual-design-from-scratch-PLAN.md` (tick the phase checkboxes as phases land).

## Commands
- `uv sync` — install deps (numpy, scipy, matplotlib, the four pillar packages from GitHub;
  dev: pytest, ruff, nbclient)
- `uv run pytest` — tests
- `uv run ruff check . && uv run ruff format --check .` — lint/format (CI runs both). Ruff also
  formats the ```python blocks inside Markdown, so run it after editing docs too
- `uv run python validation/run_all.py` — regenerate every validation figure (`docs/figures/`)
  and results table (`validation/results/`); single scripts also run on their own
- `uv run python notebooks/build_notebooks.py` — regenerate and execute the notebooks (edit cell
  sources there, never the .ipynb JSON); rebuilds are byte-identical

## Layout
- `src/acdesign/` — single package; subpackages mirror the plan: `requirements`,
  `weight_estimation`, `constraint_analysis`, `wing_tail_sizing`, `structural_sizing_check`,
  `performance_verification`, `trade_studies`. `sizing.py` closes every discipline on W0 and
  holds the shared assumptions (the 737-800 description in `validation/reference_aircraft.py`
  reuses them); `geometry.py`, `units.py`, `plotting.py` are shared helpers.
- `src/acdesign/external/` — the **only** place the pillar packages are imported:
  `wing_aero.py` (`aero`, AERO-01), `wing_box.py` (`structures`, AERO-02), `engine.py` and
  `atmosphere.py` (`propulsion`, AERO-03), `stability.py` (`flightdyn`, AERO-04). They are uv
  git dependencies pinned to a commit in `pyproject.toml` (`[tool.uv.sources]`); bump the `rev`
  deliberately and rerun everything (tests, `run_all.py`, notebooks, lesson numbers).
- `tests/` — pytest, one file per module; `tests/conftest.py` puts `validation/` on the path.
- `validation/` — cited reference data (`reference_data/`, loaded by `reference.py`), one script
  per comparison, `run_all.py`, and `results/`.
- `docs/` — theory note per module, the design report, figures; `docs/lessons/` is the course
  (keep its numbers in sync with the code: rerun the snippets and the scripts that produced
  them after any model change). `notebooks/` — one executed demo per lesson.

## Gotchas
- The sizing caches VLM solutions per planform and engine tables per (engine, altitude, Mach)
  with `functools.cache`; the first sizing in a process takes seconds, the next ones tens of ms.
- AERO-03's `operate` can return unconverged points without raising: the engine adapter
  checks `.converged`. The flightdyn trim can report "no progress" at an exact start; nudge
  the guess.
- Induced velocity must not be evaluated on a trailing-vortex node: the VLM uses an odd
  strip count so the symmetry plane (where the tail is) is a strip centre.

## Conventions
- **SI units internally** (m, s, kg, N, Pa, rad). Helpers that take or return other units say
  so in the name (`*_lb`, `*_ft2`, `*_nmi`, `*_kt`, `*_deg`). Raymer's statistical equations are
  in imperial units: convert at the function boundary with the exact factors in `units.py`.
- Weights: `W` is a force (N), `m` a mass (kg). `W0` is the take-off gross weight, `We` empty,
  `Wf` fuel, `Wp` payload. Wing loading `W/S` in Pa, thrust loading `T/W` dimensionless, both
  referenced to take-off weight and sea-level static thrust unless the name says otherwise.
- TSFC is kg/(N·s) internally (as in AERO-03); Breguet uses `c = TSFC·g0` in 1/s.
- Altitudes are geopotential pressure altitudes (flight levels); call the pillar ISA functions
  with `geopotential=True`.
- Angles in radians; wing sweep is the quarter-chord sweep unless named otherwise.
- Pure NumPy/SciPy on top of the pillar packages — no aircraft-design libraries.

## Docs (GitHub-rendered math)
- Display equations go in ```` ```math ```` fences (no Markdown processing inside).
- Inline `$...$` is processed as Markdown first: no `\,` or `\;` (they become `,` `;`), no `\\`
  row breaks (put matrices in a display block), and no `_` right after `}` `)` `]` (it starts
  emphasis; write `C_{L_{\alpha}}`, not `{C_L}_\alpha`). `tests/test_docs.py` guards this.

## Testing rules
- Every test asserts against a closed-form result or a cited published value; name the source
  in a comment. Never loosen a tolerance to make a failing model pass without explaining why.
- Cite textbooks at chapter level unless the section/table number has been checked in the book.
- Reference data in `validation/reference_data/` must carry its citation (document, section,
  page). Do not invent data: leave a value out if it cannot be checked against its source.
- Label every input as data (printed, cited), assumption (chosen), deduction (forced by printed
  numbers) or calibration (fitted). Calibrated quantities cannot be used to validate.
- The sized aircraft is compared with the 737-800 at the level a conceptual method supports
  (trends, ±10–20 %): write the reason for every tolerance in the test.
- No employer references in the repo; name aircraft and engine types only.

## Workflow
- Commit small logical changes directly to `main`, push after
  `uv run ruff check . && uv run ruff format --check . && uv run pytest` pass (no pipes: a pipe
  hides the exit code). Stage explicit paths rather than `git add -A`.
- Each phase lands as code + tests, then its lesson in `docs/lessons/` as a separate commit.
