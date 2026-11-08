#!/usr/bin/env python3
"""
Scripted PCB generator for the Smart Adaptive Flashlight driver board (v1).

No KiCad/EDA GUI tool was used. This script places simple rectangular/
circular footprints at explicit (x, y) coordinates on a fixed board
outline, routes a handful of orthogonal traces between them, and emits
real RS-274X Gerber layers plus an Excellon drill file.

Board: 50mm x 30mm, 2-layer (top copper signal, bottom copper mostly a
ground pour), units = millimeters throughout.

The component placement table (COMPONENTS, below) is the single source of
truth for position/rotation -- pcb/bom/bom.csv and
pcb/pick_and_place/cpl.csv are hand-authored to exactly match these same
reference designators and the same (x, y) coordinates, so Gerbers/BOM/CPL
stay mutually consistent (a mismatched CPL is a real assembly-house
failure mode worth modeling correctly even in a demo).

Run:
    source .venv/bin/activate
    python3 pcb/generate_pcb.py
"""

import os
import gerber_writer as gw

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerbers")

BOARD_W = 50.0
BOARD_H = 30.0
BOARD_CORNER_R = 2.0  # mm, cosmetic rounded corner on the outline

TRACE_WIDTH = 0.3     # mm, signal traces
POWER_TRACE_WIDTH = 0.6  # mm, VCC/GND traces (named separately -- this is
                          # the parameter touched if current budget grows)

# ---------------------------------------------------------------------------
# Component placement table -- single source of truth, mirrored by hand in
# pcb/bom/bom.csv and pcb/pick_and_place/cpl.csv. (x, y) = footprint center,
# rotation in degrees, 0 = default orientation (pin 1 convention noted per
# part in the BOM).
# ---------------------------------------------------------------------------
COMPONENTS = {
    "U1": {"desc": "ESP32-WROOM-32 module", "x": 11.0, "y": 15.0, "rot": 0,
           "size": (18.0, 25.5)},
    "U2": {"desc": "BH1750 ambient light sensor (I2C)", "x": 30.0, "y": 25.0,
           "rot": 0, "size": (3.0, 3.0)},
    "U3": {"desc": "LIS3DH accelerometer (I2C, tap/click IRQ)", "x": 30.0,
           "y": 17.0, "rot": 0, "size": (3.0, 3.0)},
    "Q1": {"desc": "AO3400 N-MOSFET, LED driver (SOT-23)", "x": 30.0,
           "y": 9.0, "rot": 0, "size": (2.9, 2.5)},
    "R1": {"desc": "0.1R current-sense resistor (0805)", "x": 36.0, "y": 9.0,
           "rot": 0, "size": (2.0, 1.25)},
    "J1": {"desc": "LED connector, 2-pin JST-PH", "x": 42.0, "y": 9.0,
           "rot": 0, "size": (4.0, 2.5)},
    "J2": {"desc": "18650 cell connector, 2-pin JST-PH", "x": 30.0, "y": 3.0,
           "rot": 0, "size": (4.0, 2.5)},
    "J3": {"desc": "TP4056 charge module header, 1x4", "x": 42.0, "y": 3.0,
           "rot": 0, "size": (5.0, 2.5)},
    "H1": {"desc": "Mounting hole, M2, NPTH", "x": 4.0, "y": 4.0, "rot": 0,
           "size": (2.5, 2.5)},
    "H2": {"desc": "Mounting hole, M2, NPTH", "x": 46.0, "y": 26.0, "rot": 0,
           "size": (2.5, 2.5)},
}

# Named pin coordinates on U1 (ESP32 module) used as trace endpoints --
# these sit on the module's right-hand castellated edge (x = 20.0).
U1_PINS = {
    "3V3": (20.0, 25.0),
    "GND_A": (20.0, 22.0),
    "EN": (20.0, 19.0),
    "SDA": (20.0, 16.0),
    "SCL": (20.0, 13.0),
    "ACCEL_INT": (20.0, 10.0),
    "LED_PWM": (20.0, 7.0),
    "GND_B": (20.0, 4.0),
}

# Simple 2-pad footprint pin offsets (local, added to component center).
PIN_OFFSETS_2PAD = [(-1.2, 0.0), (1.2, 0.0)]       # J1, J2
PIN_OFFSETS_SOT23 = [(-0.95, 0.9), (0.95, 0.9), (0.0, -0.9)]  # Q1: G,D,S
PIN_OFFSETS_0805 = [(-0.9, 0.0), (0.9, 0.0)]       # R1
PIN_OFFSETS_IC5 = [  # U2/U3 small 5-pad IC: VCC, GND, SDA, SCL, INT/ADDR
    (-1.2, 1.0), (-1.2, 0.0), (-1.2, -1.0), (1.2, 0.5), (1.2, -0.5)
]
PIN_OFFSETS_HDR4 = [(-1.5, 0.0), (-0.5, 0.0), (0.5, 0.0), (1.5, 0.0)]  # J3


def comp_pos(ref):
    c = COMPONENTS[ref]
    return (c["x"], c["y"])


def add_component_pads(copper, silk, ref, pin_offsets, pad_size=(0.8, 0.8)):
    """Add rectangular SMD pads for a component's pins (copper) and a
    silkscreen courtyard rectangle around the component body."""
    cx, cy = comp_pos(ref)
    pad = gw.Rectangle(pad_size[0], pad_size[1], "SMDPad,CuDef")
    for (ox, oy) in pin_offsets:
        copper.add_pad(pad, (cx + ox, cy + oy))

    bw, bh = COMPONENTS[ref]["size"]
    half_w, half_h = bw / 2, bh / 2
    corners = [
        (cx - half_w, cy - half_h), (cx + half_w, cy - half_h),
        (cx + half_w, cy + half_h), (cx - half_w, cy + half_h),
    ]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        silk.add_trace_line((x0, y0), (x1, y1), 0.15, "Legend,Top")


def route_orthogonal(copper, start, end, width, function):
    """Route a simple two-segment orthogonal (Manhattan) trace: horizontal
    then vertical leg, meeting at an L-corner."""
    corner = (end[0], start[1])
    copper.add_trace_line(start, corner, width, function)
    copper.add_trace_line(corner, end, width, function)


def build_layers():
    top_copper = gw.DataLayer("Copper,L1,Top")
    bot_copper = gw.DataLayer("Copper,L2,Bot")
    top_silk = gw.DataLayer("Legend,Top")
    top_mask = gw.DataLayer("Soldermask,Top", negative=True)
    bot_mask = gw.DataLayer("Soldermask,Bot", negative=True)
    outline = gw.DataLayer("Profile,NP")

    # --- Board outline (edge cuts) ---------------------------------------
    corners = [
        (0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H),
    ]
    for i in range(4):
        outline.add_trace_line(corners[i], corners[(i + 1) % 4], 0.1, "Profile,NP")

    # --- U1 ESP32 module: body outline + named pin pads -------------------
    u1x, u1y = comp_pos("U1")
    bw, bh = COMPONENTS["U1"]["size"]
    half_w, half_h = bw / 2, bh / 2
    body_corners = [
        (u1x - half_w, u1y - half_h), (u1x + half_w, u1y - half_h),
        (u1x + half_w, u1y + half_h), (u1x - half_w, u1y + half_h),
    ]
    for i in range(4):
        top_silk.add_trace_line(body_corners[i], body_corners[(i + 1) % 4],
                                 0.15, "Legend,Top")
    castellated_pad = gw.Rectangle(1.0, 1.2, "SMDPad,CuDef")
    for name, pos in U1_PINS.items():
        top_copper.add_pad(castellated_pad, pos)

    # --- Other components: pads + courtyard silkscreen --------------------
    add_component_pads(top_copper, top_silk, "U2", PIN_OFFSETS_IC5, (0.6, 0.6))
    add_component_pads(top_copper, top_silk, "U3", PIN_OFFSETS_IC5, (0.6, 0.6))
    add_component_pads(top_copper, top_silk, "Q1", PIN_OFFSETS_SOT23, (0.7, 0.9))
    add_component_pads(top_copper, top_silk, "R1", PIN_OFFSETS_0805, (0.9, 1.1))
    add_component_pads(top_copper, top_silk, "J1", PIN_OFFSETS_2PAD, (1.3, 1.6))
    add_component_pads(top_copper, top_silk, "J2", PIN_OFFSETS_2PAD, (1.3, 1.6))
    add_component_pads(top_copper, top_silk, "J3", PIN_OFFSETS_HDR4, (0.9, 1.6))

    # --- Mounting holes (silkscreen ring only -- the real hole is in the
    #     Excellon drill file; NPTH so no copper pad needed) --------------
    for ref in ("H1", "H2"):
        cx, cy = comp_pos(ref)
        top_silk.add_pad(gw.Circle(2.6, "Legend,Top"), (cx, cy))

    # --- Routing: orthogonal traces between named nets --------------------
    u2x, u2y = comp_pos("U2")
    u3x, u3y = comp_pos("U3")
    q1x, q1y = comp_pos("Q1")
    r1x, r1y = comp_pos("R1")
    j1x, j1y = comp_pos("J1")
    j2x, j2y = comp_pos("J2")
    j3x, j3y = comp_pos("J3")

    # I2C bus: ESP32 SDA/SCL -> BH1750 -> LIS3DH (daisy-chained)
    route_orthogonal(top_copper, U1_PINS["SDA"], (u2x - 1.2, u2y + 1.0),
                      TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, (u2x - 1.2, u2y + 1.0), (u3x - 1.2, u3y + 1.0),
                      TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, U1_PINS["SCL"], (u2x - 1.2, u2y - 1.0),
                      TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, (u2x - 1.2, u2y - 1.0), (u3x - 1.2, u3y - 1.0),
                      TRACE_WIDTH, "Conductor")

    # Accelerometer interrupt -> ESP32 GPIO
    route_orthogonal(top_copper, (u3x + 1.2, u3y - 0.5), U1_PINS["ACCEL_INT"],
                      TRACE_WIDTH, "Conductor")

    # LED PWM: ESP32 GPIO -> MOSFET gate
    route_orthogonal(top_copper, U1_PINS["LED_PWM"], (q1x - 0.95, q1y + 0.9),
                      TRACE_WIDTH, "Conductor")
    # MOSFET drain -> LED connector (+)
    route_orthogonal(top_copper, (q1x + 0.95, q1y + 0.9), (j1x - 1.2, j1y),
                      POWER_TRACE_WIDTH, "Conductor")
    # MOSFET source -> current-sense resistor -> GND
    route_orthogonal(top_copper, (q1x, q1y - 0.9), (r1x - 0.9, r1y),
                      POWER_TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, (r1x + 0.9, r1y), U1_PINS["GND_B"],
                      POWER_TRACE_WIDTH, "Conductor")

    # Battery (J2) -> TP4056 header (J3) -> ESP32 3V3/GND (power)
    route_orthogonal(top_copper, (j2x + 1.2, j2y), (j3x - 1.5, j3y),
                      POWER_TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, (j3x + 1.5, j3y), U1_PINS["3V3"],
                      POWER_TRACE_WIDTH, "Conductor")
    route_orthogonal(top_copper, (j2x - 1.2, j2y), U1_PINS["GND_A"],
                      POWER_TRACE_WIDTH, "Conductor")
    # EN pin pulled to 3V3 (always-run, no sleep header in v1)
    route_orthogonal(top_copper, U1_PINS["EN"], U1_PINS["3V3"],
                      TRACE_WIDTH, "Conductor")

    # --- Bottom copper: simple ground pour rectangle (slightly inset from
    #     the board edge) acting as the GND return plane. ------------------
    inset = 2.0
    gnd_pour = gw.Path()
    gnd_pour.moveto((inset, inset))
    gnd_pour.lineto((BOARD_W - inset, inset))
    gnd_pour.lineto((BOARD_W - inset, BOARD_H - inset))
    gnd_pour.lineto((inset, BOARD_H - inset))
    gnd_pour.lineto((inset, inset))
    bot_copper.add_region(gnd_pour, "Copper,L2,Bot")

    # --- Soldermask: openings over every copper pad (simplified -- mask
    #     layer mirrors the copper pad set with a small expansion) --------
    for name, pos in U1_PINS.items():
        top_mask.add_pad(gw.Rectangle(1.2, 1.4, "Soldermask,Top"), pos)
    for ref, offs, size in (
        ("U2", PIN_OFFSETS_IC5, (0.8, 0.8)),
        ("U3", PIN_OFFSETS_IC5, (0.8, 0.8)),
        ("Q1", PIN_OFFSETS_SOT23, (0.9, 1.1)),
        ("R1", PIN_OFFSETS_0805, (1.1, 1.3)),
        ("J1", PIN_OFFSETS_2PAD, (1.5, 1.8)),
        ("J2", PIN_OFFSETS_2PAD, (1.5, 1.8)),
        ("J3", PIN_OFFSETS_HDR4, (1.1, 1.8)),
    ):
        cx, cy = comp_pos(ref)
        pad = gw.Rectangle(size[0], size[1], "Soldermask,Top")
        for (ox, oy) in offs:
            top_mask.add_pad(pad, (cx + ox, cy + oy))
    bot_mask.add_pad(gw.Rectangle(BOARD_W - 2 * inset, BOARD_H - 2 * inset,
                                   "Soldermask,Bot"),
                      (BOARD_W / 2, BOARD_H / 2))

    return {
        "top_copper": top_copper,
        "bot_copper": bot_copper,
        "top_silk": top_silk,
        "top_mask": top_mask,
        "bot_mask": bot_mask,
        "outline": outline,
    }


def write_excellon_drill(path):
    """Hand-written minimal Excellon drill file (gerber_writer has no
    Excellon support). Tool list + hits for: connector/header through-holes
    (plated, 1.0mm) and the two mechanical mounting holes (non-plated,
    2.0mm). Coordinates in millimeters, matching the Gerber layers above.
    """
    plated_holes = []
    for ref, offs in (("J1", PIN_OFFSETS_2PAD), ("J2", PIN_OFFSETS_2PAD),
                       ("J3", PIN_OFFSETS_HDR4)):
        cx, cy = comp_pos(ref)
        for (ox, oy) in offs:
            plated_holes.append((cx + ox, cy + oy))

    npth_holes = [comp_pos("H1"), comp_pos("H2")]

    lines = []
    lines.append("M48")
    lines.append("; Smart Adaptive Flashlight driver board v1 -- drill file")
    lines.append("; Generated by pcb/generate_pcb.py (gerber-writer does not")
    lines.append("; emit Excellon, so this file is hand-written directly)")
    lines.append("METRIC,TZ")
    lines.append("T01C1.00")   # plated connector/header pins
    lines.append("T02C2.00")   # NPTH mounting holes
    lines.append("%")
    lines.append("G90")
    lines.append("G05")
    lines.append("T01")
    for (x, y) in plated_holes:
        lines.append(f"X{x:07.3f}Y{y:07.3f}")
    lines.append("T02")
    for (x, y) in npth_holes:
        lines.append(f"X{x:07.3f}Y{y:07.3f}")
    lines.append("T00")
    lines.append("M30")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    return len(plated_holes) + len(npth_holes)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    layers = build_layers()

    file_map = {
        "top_copper": "flashlight_driver_v1-F_Cu.gbr",
        "bot_copper": "flashlight_driver_v1-B_Cu.gbr",
        "top_silk": "flashlight_driver_v1-F_Silkscreen.gbr",
        "top_mask": "flashlight_driver_v1-F_Mask.gbr",
        "bot_mask": "flashlight_driver_v1-B_Mask.gbr",
        "outline": "flashlight_driver_v1-Edge_Cuts.gbr",
    }

    print("=== PCB generation complete ===")
    for key, fname in file_map.items():
        path = os.path.join(OUT_DIR, fname)
        with open(path, "w") as f:
            layers[key].dump_gerber(f)
        print(f"{fname}: {os.path.getsize(path)} bytes")

    drill_path = os.path.join(OUT_DIR, "flashlight_driver_v1.drl")
    n_holes = write_excellon_drill(drill_path)
    print(f"{os.path.basename(drill_path)}: {os.path.getsize(drill_path)} bytes "
          f"({n_holes} holes)")

    print(f"\nBoard outline: {BOARD_W} x {BOARD_H} mm, 2-layer")
    print(f"Components placed: {', '.join(COMPONENTS.keys())}")


if __name__ == "__main__":
    main()
