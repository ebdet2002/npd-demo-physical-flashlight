#!/usr/bin/env python3
"""
Parametric CAD generator for the Smart Adaptive Flashlight (v1).

Reads its target dimensions from docs/SPEC.md's "Form Factor & Target
Dimensions" section (hardcoded here as named constants that mirror those
numbers exactly -- keep these two in sync by hand if SPEC.md changes).

Builds a simple three-section body (tail cap / battery tube / head) as a
single revolved/extruded solid, with a bore through the body for the
18650 cell + electronics stack, and exports:

  cad/step/flashlight_body_v1.step
  cad/stl/flashlight_body_v1.stl
  cad/dwg/flashlight_profile_v1.dxf   (2D profile -- DXF stands in for DWG;
                                        DWG itself requires proprietary
                                        Autodesk tooling we don't have.
                                        DXF is the open equivalent accepted
                                        by essentially every CAD tool and
                                        manufacturer.)

Run:
    source .venv/bin/activate
    python cad/generate_cad.py
"""

import os
import cadquery as cq
from cadquery import exporters

# ---------------------------------------------------------------------------
# Named parameters -- mirror docs/SPEC.md "Form Factor & Target Dimensions"
# ---------------------------------------------------------------------------

# Overall envelope
BODY_LENGTH = 75.0        # mm, battery tube length
HEAD_LENGTH = 30.0        # mm, head section length
TAIL_LENGTH = 25.0        # mm, tail cap length
TOTAL_LENGTH = BODY_LENGTH + HEAD_LENGTH + TAIL_LENGTH  # 130.0 mm target

BODY_DIAMETER = 25.0      # mm, battery tube OD
HEAD_DIAMETER = 32.0      # mm, head OD (steps up for lens/bezel)
TAIL_DIAMETER = 25.0      # mm, tail cap OD (flush with body)

WALL_THICKNESS = 1.5      # mm -- named so it's trivially adjustable; this
                           # is exactly the parameter touched in the v1.1
                           # iteration pass (see docs/CHANGELOG.md).

# 18650 cell: 18.6mm diameter nominal, 65.2mm length -- needs clearance bore
CELL_DIAMETER = 18.6
CELL_CLEARANCE = 0.6      # mm radial clearance around the cell for the PCB
                           # sleeve + fitting tolerance
BORE_DIAMETER = CELL_DIAMETER + 2 * CELL_CLEARANCE  # 19.8 mm

# O-ring grooves at head/body and body/tail joints
ORING_CROSS_SECTION = 1.5   # mm
ORING_GROOVE_DEPTH = 1.0    # mm
ORING_GROOVE_WIDTH = ORING_CROSS_SECTION + 0.3

# Head-section lens pocket (holds an off-the-shelf TIR lens + bezel, per
# SPEC.md v1 scope cut-line -- no custom lens)
LENS_POCKET_DEPTH = 8.0
LENS_POCKET_DIAMETER = HEAD_DIAMETER - 2 * 4.0  # leaves 4mm bezel wall

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def build_profile_2d():
    """2D half-profile of the flashlight (for the DXF export), as a list
    of (x, y) points where x runs along the flashlight's long axis (0 =
    tail end) and y is the radius at that point. Used both to drive the
    revolve and to emit the DXF."""
    r_tail = TAIL_DIAMETER / 2
    r_body = BODY_DIAMETER / 2
    r_head = HEAD_DIAMETER / 2

    x_tail_end = TAIL_LENGTH
    x_body_end = TAIL_LENGTH + BODY_LENGTH
    x_head_end = TAIL_LENGTH + BODY_LENGTH + HEAD_LENGTH

    pts = [
        (0.0, 0.0),
        (0.0, r_tail),
        (x_tail_end, r_tail),
    ]
    # Tail and body share the same OD (flush joint per SPEC.md) -- only
    # emit a step point if the diameters actually differ, otherwise we'd
    # produce a zero-length edge.
    if abs(r_tail - r_body) > 1e-6:
        pts.append((x_tail_end, r_body))
    pts.append((x_body_end, r_body))
    if abs(r_body - r_head) > 1e-6:
        pts.append((x_body_end, r_head))
    pts.append((x_head_end, r_head))
    pts.append((x_head_end, 0.0))
    return pts


def build_solid():
    """Revolve the outer profile 360 degrees around the long axis (modeled
    along Y in the XY sketch plane, revolved about the X axis after
    sketching in XZ for cadquery's revolve convention), then bore the
    internal cavity and cut the lens pocket + o-ring grooves."""
    pts = build_profile_2d()

    # Sketch in the XZ plane: cadquery revolve sweeps a wire in a plane
    # around an axis lying in that same plane. We sketch profile as
    # (axial, radial) = (x, y) in XZ, revolve around the X axis.
    sketch = cq.Workplane("XZ").polyline(pts).close()
    solid = sketch.revolve(360, (0, 0, 0), (1, 0, 0))

    # Bore the internal cavity for the 18650 cell + electronics, running
    # from the tail end through the body and stopping short of the head
    # (head holds the LED/lens stack, modeled as solid in v1 -- the
    # driver PCB sits in the body bore).
    bore_len = TAIL_LENGTH + BODY_LENGTH - 2.0  # stop 2mm short of head face
    bore = (
        cq.Workplane("YZ")
        .workplane(offset=0)
        .center(0, 0)
        .circle(BORE_DIAMETER / 2)
        .extrude(bore_len)
        .translate((0, 0, 0))
    )
    # cadquery extrudes along local Z of the workplane's normal; YZ plane's
    # normal is X, so this bore runs along +X already. Position it from x=0.
    solid = solid.cut(bore)

    # Lens pocket: a shallow bore from the head's outer face inward.
    x_head_face = TAIL_LENGTH + BODY_LENGTH + HEAD_LENGTH
    lens_pocket = (
        cq.Workplane("YZ", origin=(x_head_face, 0, 0))
        .circle(LENS_POCKET_DIAMETER / 2)
        .extrude(-LENS_POCKET_DEPTH)
    )
    solid = solid.cut(lens_pocket)

    # O-ring grooves: two shallow circumferential cuts at the two joints.
    x_joint_1 = TAIL_LENGTH            # tail / body joint
    x_joint_2 = TAIL_LENGTH + BODY_LENGTH  # body / head joint

    for x_joint, outer_r in (
        (x_joint_1, BODY_DIAMETER / 2),
        (x_joint_2, HEAD_DIAMETER / 2),
    ):
        groove = (
            cq.Workplane("YZ", origin=(x_joint - ORING_GROOVE_WIDTH / 2, 0, 0))
            .circle(outer_r)
            .circle(outer_r - ORING_GROOVE_DEPTH)
            .extrude(ORING_GROOVE_WIDTH)
        )
        solid = solid.cut(groove)

    return solid


def main():
    solid = build_solid()

    step_dir = os.path.join(OUT_DIR, "step")
    stl_dir = os.path.join(OUT_DIR, "stl")
    dxf_dir = os.path.join(OUT_DIR, "dwg")
    for d in (step_dir, stl_dir, dxf_dir):
        os.makedirs(d, exist_ok=True)

    step_path = os.path.join(step_dir, "flashlight_body_v1.step")
    stl_path = os.path.join(stl_dir, "flashlight_body_v1.stl")
    dxf_path = os.path.join(dxf_dir, "flashlight_profile_v1.dxf")

    exporters.export(solid, step_path)
    exporters.export(solid, stl_path, tolerance=0.05, angularTolerance=0.1)

    # 2D profile DXF: just the outer polyline profile (half-section),
    # mirrored to show the full cross-section outline for manufacturing
    # reference drawings.
    pts = build_profile_2d()
    mirrored = [(x, -y) for (x, y) in reversed(pts)]
    full_profile = pts + mirrored
    # Drop consecutive duplicate points (the two ends of the profile both
    # touch y=0 on the axis, which after mirroring produces a zero-length
    # edge that OCC's edge builder rejects).
    deduped = [full_profile[0]]
    for p in full_profile[1:]:
        if p != deduped[-1]:
            deduped.append(p)
    if deduped[0] == deduped[-1]:
        deduped.pop()
    profile_wp = cq.Workplane("XY").polyline(deduped).close()
    exporters.export(profile_wp, dxf_path)

    bb = solid.val().BoundingBox()
    print("=== CAD generation complete ===")
    print(f"STEP: {step_path} ({os.path.getsize(step_path)} bytes)")
    print(f"STL:  {stl_path} ({os.path.getsize(stl_path)} bytes)")
    print(f"DXF:  {dxf_path} ({os.path.getsize(dxf_path)} bytes)")
    print(
        f"Bounding box (mm): "
        f"X(length)={bb.xlen:.2f} Y={bb.ylen:.2f} Z={bb.zlen:.2f}"
    )
    print(f"Target length from SPEC.md: {TOTAL_LENGTH:.2f} mm")
    print(f"Target max diameter from SPEC.md: {HEAD_DIAMETER:.2f} mm")


if __name__ == "__main__":
    main()
