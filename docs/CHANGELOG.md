# Changelog

## v1.1.0 — CAD iteration: body wall thickness bug

**Issue found:** `cad/generate_cad.py` defines `WALL_THICKNESS = 1.5` (mm)
as a named parameter, explicitly matching `docs/SPEC.md`'s "Form Factor &
Target Dimensions" section (`wall thickness 1.5mm`). But in v1.0.0, that
parameter was **dead code** — the internal bore that actually determines
wall thickness was computed only from the 18650 cell diameter plus a
fitting clearance (`BORE_DIAMETER = CELL_DIAMETER + 2 * CELL_CLEARANCE`),
completely independent of `WALL_THICKNESS`.

The result: the body's *actual* wall thickness was 2.6mm, not the 1.5mm
the model claimed to implement and that SPEC.md documents.

```
# Before (v1.0.0)
BODY_DIAMETER = 25.0 mm
BORE_DIAMETER = CELL_DIAMETER + 2*CELL_CLEARANCE = 18.6 + 1.2 = 19.8 mm
actual wall = (25.0 - 19.8) / 2 = 2.6 mm   <-- documented as 1.5mm, isn't
```

This matters for a few real reasons:
- **Weight.** An extra 1.1mm of aluminum wall around a 75mm battery tube
  is real, non-trivial added mass against the SPEC.md target of ≤150g —
  exactly the kind of silent creep that blows a weight budget without
  anyone changing a number on purpose.
- **BOM cost drift.** More material per unit = higher per-unit machining/
  material cost than what was quoted against the 1.5mm wall assumption in
  `cad/boms/bom.csv`.
- **Trust in the parametric model.** The entire point of scripting the CAD
  instead of hand-modeling it in a GUI is that named parameters are
  supposed to be the single source of truth. A parameter that's named,
  documented, and silently ignored is worse than not having the parameter
  at all — it looks adjustable and isn't.

**Fix (v1.1.0):** `BORE_DIAMETER` is now computed directly from
`BODY_DIAMETER - 2 * WALL_THICKNESS`. The old cell-clearance calculation
is kept as `MIN_BORE_DIAMETER`, a floor the script asserts against at
generation time — so a future edit to `WALL_THICKNESS` can't silently
produce a bore too small for the 18650 cell to physically fit, it'll throw
immediately instead.

```
# After (v1.1.0)
BORE_DIAMETER = BODY_DIAMETER - 2*WALL_THICKNESS = 25.0 - 3.0 = 22.0 mm
actual wall = (25.0 - 22.0) / 2 = 1.5 mm   <-- matches SPEC.md exactly
assert BORE_DIAMETER (22.0) >= MIN_BORE_DIAMETER (19.8)   # passes, 2.2mm margin
```

**What changed on disk:**
- `cad/generate_cad.py`: `BORE_DIAMETER` calculation (see diff), plus a new
  printed line (`Body wall thickness: documented=.. actual=..`) so this
  specific drift is visually impossible to miss on every future run.
- `cad/step/flashlight_body_v1.step`, `cad/stl/flashlight_body_v1.stl`,
  `cad/dwg/flashlight_profile_v1.dxf` — regenerated. Overall envelope is
  unchanged (still 130.0mm x 32.0mm, matching SPEC.md) since the fix only
  changes the *internal* bore diameter, not the outer profile.

**What didn't change:** the resulting bore (22.0mm) is still larger than
the 18650-cell-plus-clearance floor (19.8mm) — there's slightly more
internal room than the original clearance-only design, which is a
reasonable place to land since it leaves margin for the driver PCB sleeve
without needing a wall any thinner than SPEC.md's stated target.

## v1.0.0 — first working draft

Initial scripted CAD (cadquery) + PCB (gerber-writer) + firmware +
viewers, per `docs/SPEC.md`. See the `v1.0.0` git tag.
