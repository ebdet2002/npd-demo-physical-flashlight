---
name: arr-physical-spec
description: Turn a product "why" doc (problem/user/opportunity narrative) into a token-efficient physical-product SPEC.md plus full folder scaffolding (CAD, PCB, brand). Use when starting a new physical/hardware product demo and you have a docs/WHY.md (or equivalent narrative) but no structured spec yet.
---

# arr-physical-spec

Converts a free-form `docs/WHY.md` into a dense, structured `docs/SPEC.md` that
downstream tooling (notably the `arr-physical-proto` skill) can consume
mechanically, and scaffolds the folder layout every physical-product repo in
this series uses.

## When to use

- You have (or are about to write) a `docs/WHY.md` describing: the customer,
  their pain point, and a novel product angle.
- You do not yet have a `docs/SPEC.md`.
- You want the standard folder scaffold (`cad/`, `pcb/`, `brand/`) created
  consistently so `arr-physical-proto` can find everything by convention.

## Inputs

- `docs/WHY.md` — narrative only. No structure required, but should contain
  enough detail to answer: who is the customer, what's the pain point, what's
  the novel angle, roughly what kind of device is this (handheld/wearable/
  benchtop/etc).

## Steps

1. **Read `docs/WHY.md`.** If it doesn't exist, write one first from
   whatever narrative the user/caller supplied — 1-2 short paragraphs,
   Problem / Target User / Novel Angle.

2. **Produce `docs/SPEC.md`** using the exact format below. Keep every
   section terse — bullet points, numbers, not prose. This file is the
   contract that `arr-physical-proto` reads; do not change the section
   headers.

3. **Scaffold folders** (empty dirs are fine, git will need a `.gitkeep` or
   a real file dropped in later — don't worry about empty-dir tracking,
   just create the paths):
   ```
   cad/boms/
   cad/step/
   cad/stl/
   cad/dwg/
   pcb/gerbers/
   pcb/bom/
   pcb/pick_and_place/
   pcb/firmware/
   pcb/datasheets/
   brand/
   ```

4. **Generate the brand package** in `brand/`:
   - `brand/colors.json` — a small JSON palette: primary, secondary, accent,
     neutral-dark, neutral-light, each with a hex value and a one-line usage
     note. Pick colors that fit the product's context (e.g. a safety/工具
     product skews toward high-visibility industrial colors: safety orange,
     charcoal, reflective silver).
   - `brand/fonts.md` — pick a display font and a body/UI font (real,
     commonly available font names — e.g. system/Google fonts), one sentence
     each on why, plus fallback stacks.
   - `brand/logo.svg` — **hand-author a real, valid SVG**, not a placeholder
     rectangle-with-text. It should be simple enough to render correctly at
     both 24px and 400px (favicon-to-hero range): limited color count (use
     the palette from `colors.json`), clean geometry (paths/shapes, not
     embedded raster), and a viewBox that makes it scale cleanly. Reflect
     the product concept in the mark (e.g. a lighting product might
     stylize a beam/cone shape).

## Output format: `docs/SPEC.md`

Use exactly these top-level sections, in this order:

```markdown
# <Product Name> — SPEC v1

## Problem
<2-4 bullets. The pain point, who feels it, why existing solutions fail.>

## Target User
<1-3 bullets. Role/context, environment constraints (gloves, wet, dark,
hands-busy, etc), what they'd pay.>

## Form Factor & Target Dimensions
<Concrete numbers. Overall envelope (L x D or L x W x H in mm), weight
target, key sub-assembly dimensions (e.g. head/body/tail breakdown for a
cylindrical product). These numbers are load-bearing — arr-physical-proto
will model to them directly.>

## Power Budget
<Battery chemistry/cell, nominal capacity (mAh), estimated runtime per mode,
peak current draw, charge method.>

## MCU / Sensor Choice
<Name the exact MCU (real part, e.g. ESP32-WROOM-32) and each sensor with
real part numbers (e.g. BH1750 ambient light, LIS3DH accelerometer), plus
one line per part on why it was chosen over alternatives.>

## Interface Behavior / State Machine
<Enumerate states and transitions as a list, e.g.:
- OFF --tap--> LOW
- LOW --tap--> MED
- MED --tap--> HIGH
- HIGH --tap--> OFF
- any state --double-tap--> STROBE (toggle)
Include any continuous behavior (e.g. ambient-light-adaptive baseline PWM)
as a separate bullet, not folded into the discrete transitions.>

## BOM Cost Target
<Target unit cost at a stated volume, split roughly between mechanical/
electrical/firmware-free, and the single biggest cost driver.>

## v1 Scope Cut-Line
<Explicit bullet list of what is OUT of scope for v1 (e.g. "no wireless/
app control in v1", "no custom injection-molded lens in v1, use off-the-shelf
polycarbonate lens"). This is what keeps arr-physical-proto from gold-plating.>
```

## Notes for the executing agent

- This skill produces **documents and folders only** — no CAD/PCB files.
  That's `arr-physical-proto`'s job, reading this exact SPEC.md.
- Keep SPEC.md under ~1 page of dense bullets. If you're writing prose
  paragraphs, you're doing it wrong — this is a machine-readable contract
  as much as a human one.
- Numbers in "Form Factor & Target Dimensions" and part numbers in "MCU /
  Sensor Choice" must be concrete and specific — "small lens" and "a
  microcontroller" are not acceptable, downstream generation needs real
  numbers and real part names to reference.
