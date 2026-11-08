# Manufacturing Package

Everything needed to go from this repo's generated files to actual
manufactured parts, via two JLC services. Both bundles here are built
directly from the current `cad/` and `pcb/` outputs (v1.1.0) — regenerate
them with `cad/generate_cad.py` / `pcb/generate_pcb.py` and re-copy/re-zip
if those change.

## 3D-printed body → JLC3DP

**Files:** `manufacturing/cad_jlc3dp/flashlight_body_v1.step` (preferred —
exact BREP solid) and `flashlight_body_v1.stl` (mesh, also accepted).

**Steps on https://jlc3dp.com :**
1. Create an account / log in, click "Upload File", select
   `flashlight_body_v1.step`.
2. **Process:** SLA or SLS for a smooth-surface prototype (recommended for
   checking the o-ring grooves and lens pocket fit); CNC machining if you
   want the actual 6061-T6 aluminum body described in `cad/boms/bom.csv`
   (JLC3DP's CNC service supports aluminum — select material "Aluminum
   6061" under the CNC process, not SLA/SLS).
3. **Material:** for an SLA prototype, a rigid resin (e.g. "Standard
   Resin" or "Rigid 4000-ish" equivalent) is fine for fit-checking; it will
   not be anodizable or structurally representative of the final aluminum
   part.
4. **Quantity:** 1 for a first fit-check print.
5. **Surface finish:** as-printed/as-machined is fine for v1 fit-check; no
   anodizing/plating needed until you're ordering the real aluminum run.
6. Confirm the quoted bounding box matches `130mm x 32mm x 32mm` (printed
   by `cad/generate_cad.py` on every run) before placing the order — if it
   doesn't, the STEP file didn't upload at the scale you expect.

## PCB → JLCPCB

**File:** `manufacturing/pcb_jlcpcb.zip` — contains all 6 Gerber layers,
the Excellon drill file, `bom.csv`, and `cpl.csv` from `pcb/`.

**IMPORTANT — read `pcb/README.md` first.** These Gerbers are
structurally valid RS-274X but have not been run through a DRC engine (no
KiCad installed here). Before ordering:
1. Upload `pcb_jlcpcb.zip` to JLCPCB's free online Gerber viewer at
   https://jlcpcb.com/gerber-viewer and visually confirm all 6 layers plus
   the drill hits render sensibly (correct outline, pads aligned with
   silkscreen, no obviously missing copper).
2. For a full DRC pass, import the same Gerbers into KiCad (free) and run
   its DRC before committing to a production run.

**Steps on https://jlcpcb.com (PCB ordering flow), once you've visually
checked the Gerbers:**
1. Click "Instant Quote," upload `pcb_jlcpcb.zip` directly — JLCPCB
   extracts the Gerbers automatically.
2. **Layers:** 2 (matches the board — top signal + bottom ground pour).
3. **Dimensions:** should auto-detect as 50mm x 30mm from the outline
   layer; confirm it does.
4. **PCB thickness:** 1.6mm (standard; nothing in this design needs a
   thinner or thicker board).
5. **PCB color:** any — soldermask color has no electrical effect; pick
   black or the project's "Night Black" brand color (`brand/colors.json`)
   if you want it to visually match the flashlight body.
6. **Surface finish:** HASL (lead-free) is the cheapest standard option
   and is fine for this design — no fine-pitch BGA parts that would need
   ENIG.
7. For **SMT assembly** (optional — JLCPCB can assemble, not just
   fabricate): upload `bom.csv` and `cpl.csv` from the same zip in the
   "SMT Assembly" step of the same order flow. Double-check JLCPCB's part
   matching for U1 (ESP32-WROOM-32E), U2 (BH1750FVI), and U3 (LIS3DH) —
   these are common parts and usually in JLCPCB's basic library, but
   confirm the matched part number before approving the order, since a
   wrong auto-match is exactly the kind of BOM/CPL mismatch failure mode
   called out in `pcb/README.md`.
8. Order quantity: a 5-unit prototype run is JLCPCB's practical minimum
   for a quick fab-only turn; assembled boards are typically quoted from 2
   units upward.

## What's NOT in this package

- The off-the-shelf mechanical parts from `cad/boms/bom.csv` (lens,
  o-rings, 18650 cell, pocket clip, screws) — source those from a
  distributor (McMaster-Carr, Digi-Key, etc.), they are not manufactured
  from files in this repo.
- The TP4056 charge module (`J3` on the PCB) — per `docs/SPEC.md`'s v1
  scope cut-line, this is sourced as an off-the-shelf breakout module, not
  fabricated.
