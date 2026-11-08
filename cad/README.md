# CAD — Smart Adaptive Flashlight

Generated entirely by script with [cadquery](https://cadquery.readthedocs.io/)
(headless Python CAD kernel built on OpenCascade) — no GUI CAD tool was used
or installed.

## Regenerating

```bash
cd ..   # repo root
source .venv/bin/activate   # created with: uv venv && uv pip install cadquery
python3 cad/generate_cad.py
```

## Outputs

- `cad/step/flashlight_body_v1.step` — full 3D solid, STEP (AP214), for
  import into any CAD tool or for manufacturing quoting (JLC3DP, etc).
- `cad/stl/flashlight_body_v1.stl` — triangulated mesh for 3D printing and
  for the browser viewer at `viewers/cad-viewer/`.
- `cad/dwg/flashlight_profile_v1.dxf` — 2D cross-section profile.
  **Note:** true `.dwg` is a proprietary Autodesk format and needs
  AutoCAD/Autodesk tooling to produce correctly. `.dxf` is the open,
  broadly-supported equivalent — essentially every CAD tool, PCB house, and
  machine shop accepts DXF, so that's what this generates. Treat
  `flashlight_profile_v1.dxf` as the DWG deliverable.
- `cad/boms/bom.csv` — mechanical BOM (body, lens, o-rings, cell, fasteners,
  packaging) with rough per-unit costs at the SPEC.md target volume.

## Model

A three-section revolved solid (tail cap / battery tube / head), bored
through for an 18650 cell + electronics stack, with a lens pocket machined
into the head face and o-ring grooves at both section joints. All key
dimensions are named parameters at the top of `generate_cad.py` and are
meant to be edited directly — see `docs/CHANGELOG.md` for the v1→v1.1
wall-thickness iteration.

Dimensions are verified against `docs/SPEC.md`'s "Form Factor & Target
Dimensions" section every run — the script prints its resulting bounding
box next to the SPEC.md targets so drift is obvious immediately.
