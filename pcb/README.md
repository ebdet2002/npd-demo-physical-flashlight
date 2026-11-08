# PCB — Smart Adaptive Flashlight Driver Board

Generated entirely by script with [gerber-writer](https://pypi.org/project/gerber-writer/)
(pure-Python RS-274X Gerber writer) — **no KiCad or other EDA GUI tool was
used or installed.** The Excellon drill file is hand-written directly
(gerber-writer only emits Gerber copper/mask/silk/outline layers, not
drill files).

## IMPORTANT — read before ordering

These Gerbers are **structurally valid** RS-274X (correct header, aperture
definitions with X2 attributes, D01/D02/D03 draw commands, proper
`%MOMM*%`/`%FSLAX36Y36*%` format statements, M02 end-of-file) and the
drill file is valid Excellon, with a correct 2-layer stack (top signal
layer, bottom ground-pour layer, top silkscreen, top/bottom soldermask,
board outline).

**They have NOT been run through a DRC (design rule check) engine.** There
is no KiCad or other EDA tool installed in this environment to run one.
Before ordering real boards:

1. Zip the contents of `pcb/gerbers/` (or use `manufacturing/pcb_jlcpcb.zip`,
   already assembled).
2. Upload to **JLCPCB's free online Gerber viewer** at
   https://jlcpcb.com/gerber-viewer — it renders every layer and flags
   obvious issues (missing layers, overlapping copper/drill, outline
   problems) even without a full DRC pass.
3. For a real DRC pass (clearance rules, annular ring minimums, etc.),
   import into KiCad (free) or a similar EDA tool and run its DRC before
   committing to a production order.

## Layout

Single rectangular board, 50mm x 30mm, 2-layer:

- `flashlight_driver_v1-F_Cu.gbr` — top copper: component pads + signal
  routing (I2C bus, LED PWM/gate drive, power distribution).
- `flashlight_driver_v1-B_Cu.gbr` — bottom copper: simple ground pour.
- `flashlight_driver_v1-F_Silkscreen.gbr` — component courtyards + mounting
  hole rings.
- `flashlight_driver_v1-F_Mask.gbr` / `-B_Mask.gbr` — soldermask openings.
- `flashlight_driver_v1-Edge_Cuts.gbr` — board outline.
- `flashlight_driver_v1.drl` — Excellon drill file (connector/header holes
  plated 1.0mm, two M2 mounting holes NPTH 2.0mm).

## Components (see `pcb/bom/bom.csv` + `pcb/pick_and_place/cpl.csv`)

| Ref | Part | Role |
|-----|------|------|
| U1  | ESP32-WROOM-32E | Main MCU |
| U2  | BH1750FVI | Ambient light sensor (I2C) |
| U3  | LIS3DH | Accelerometer, hardware single/double-click detection (I2C) |
| Q1  | AO3400A | N-MOSFET LED driver gate |
| R1  | 0.1R sense resistor | Current sense (open-loop in v1) |
| J1  | JST-PH 2-pin | LED connector (off-board star) |
| J2  | JST-PH 2-pin | 18650 cell connector |
| J3  | 1x4 header | TP4056 charge module (off-board module, not hand-routed — see SPEC.md) |
| H1, H2 | M2 NPTH | Mounting holes |

**The BOM, CPL, and the placement table in `generate_pcb.py` (`COMPONENTS`
dict) share the exact same reference designators and (x, y) coordinates.**
This is intentional and matters in practice — a BOM/CPL/Gerber mismatch
(wrong part at a given position, or a CPL row with no matching footprint)
is a real and common assembly-house failure mode, so keeping these three
artifacts mutually consistent is treated as a correctness requirement here,
not a nice-to-have.

## Regenerating

```bash
cd ..   # repo root
source .venv/bin/activate   # created with: uv venv && uv pip install gerber-writer
python3 pcb/generate_pcb.py
```

## Firmware

`pcb/firmware/flashlight.ino` — real Arduino/ESP32 sketch implementing the
exact state machine from `docs/SPEC.md`: single-tap brightness cycling
(OFF→LOW→MED→HIGH→OFF), double-tap STROBE/SOS toggle, ambient-light-
adaptive PWM baseline from the BH1750, and a hardware long-press fallback
switch independent of the accelerometer.
