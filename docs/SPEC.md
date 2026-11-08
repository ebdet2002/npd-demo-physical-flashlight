# Smart Adaptive Flashlight — SPEC v1

## Problem
- Manual mode-switching (bezel twist / multi-click) is slow and unsafe with gloved, wet, or occupied hands.
- Tradespeople/warehouse workers need to switch light levels frequently (panel inspection vs. walking) without fine motor control or looking at the device.
- Fixed brightness wastes battery in bright conditions and under-lights in true darkness; running dry mid-shift is a safety issue.
- Existing "smart" flashlights that solve this add app/Bluetooth complexity the target user doesn't want or trust on the job site.

## Target User
- Night-shift warehouse workers, electricians, HVAC techs — hands often gloved, wet, or holding a tool/ladder.
- Needs one-handed, no-look operation; tactile tap beats a precision button sequence.
- Price-sensitive prosumer tool tier: would pay $35–$55 street price (vs. ~$20 for a dumb flashlight), not $150+ smart-home-tier pricing.

## Form Factor & Target Dimensions
- Overall envelope: 130mm length x 25mm body diameter (cylindrical, single 18650 cell, aluminum body).
- Head section: 30mm length x 32mm diameter (steps up from body for the LED/lens/bezel).
- Body (battery tube): 75mm length x 25mm diameter, wall thickness 1.5mm.
- Tail cap: 25mm length x 25mm diameter, houses the accelerometer tap sensor + charging port.
- Target weight: ≤150g with battery installed.
- IP-rated o-ring seals at head/body and body/tail joints (2x o-ring grooves, 1.5mm cross-section).

## Power Budget
- Cell: single 18650 Li-ion, 3.7V nominal, 3000mAh.
- Charge: USB-C into onboard TP4056 linear charge module (500mA charge current), accessible through tail cap port.
- Current draw: LOW ~80mA (~150 lm), MED ~300mA (~500 lm), HIGH ~900mA (~1000 lm), STROBE ~900mA pulsed.
- Estimated runtime: LOW ~34hr, MED ~9hr, HIGH ~3hr continuous (ESP32 + sensor idle draw ~15mA adds ~0.5hr of cumulative overhead per full discharge, budgeted in above).
- Peak current draw (HIGH + ESP32 active): ~950mA — sets minimum wire gauge and MOSFET rating.

## MCU / Sensor Choice
- MCU: **ESP32-WROOM-32** module — chosen for integrated PWM-capable GPIO, I2C, deep-sleep current (<1mA) for standby, and headroom for a v2 BLE feature without a board respin.
- Ambient light sensor: **BH1750** (I2C digital ambient light sensor) — chosen over an analog LDR for direct lux readout (no per-unit calibration) and simple I2C integration alongside the accelerometer.
- Tap sensor: **LIS3DH** (3-axis I2C/SPI accelerometer, chosen over a piezo disc) — piezo is cheaper but single-axis and prone to false triggers from walking/vibration; LIS3DH's built-in click/double-click interrupt engine does the single/double-tap detection in hardware, offloading the ESP32 and giving much better false-positive rejection.
- LED driver: N-channel MOSFET (logic-level, e.g. AO3400) gate-driven by ESP32 PWM, with a 0.1Ω current-sense resistor to ground for a future closed-loop current limit (open-loop PWM in v1).
- LED emitter: single high-power LED module (e.g. Cree XP-L class, ~1000 lm @ 900mA) — off-the-shelf star-mount, not custom.

## Interface Behavior / State Machine
- OFF --tap--> LOW
- LOW --tap--> MED
- MED --tap--> HIGH
- HIGH --tap--> OFF
- any state (except OFF) --double-tap--> STROBE (toggle; double-tap again returns to the state held before STROBE)
- OFF --double-tap--> SOS (toggle; distinct from STROBE — SOS is a fixed Morse timing pattern, STROBE is a fast fixed-frequency flash)
- Continuous behavior: in LOW/MED/HIGH, the BH1750 ambient reading sets a baseline PWM multiplier (0.5x–1.2x of the level's nominal duty cycle) every 2s, so the user's selected *level* stays relative to ambient conditions rather than a fixed absolute brightness.
- Long-press (>3s) on tail cap from any state --> OFF (hardware fallback, debounced, independent of tap logic, in case of accelerometer fault).

## BOM Cost Target
- Target unit cost: $14.50 at 5,000-unit volume.
- Split: mechanical (body/lens/tailcap/o-rings/hardware) ~$5.80, electrical (PCB/MCU/sensors/LED/battery/charge module) ~$8.20, assembly/test ~$0.50.
- Biggest single cost driver: the 18650 cell + TP4056 charge module pairing (~$3.10 combined) and the machined aluminum body (~$2.90) — together nearly half the BOM.

## v1 Scope Cut-Line
- No Bluetooth/app control in v1 — ESP32 chosen partly to keep this a clean v2 firmware-only addition, not a board respin.
- No custom injection-molded lens/bezel in v1 — use an off-the-shelf polycarbonate TIR lens + aluminum bezel.
- No multi-color LED / color temperature control in v1 — single fixed-CCT LED only.
- No wireless charging in v1 — USB-C wired charge only.
- No IP68 full submersion rating in v1 — IPX4 splash/rain resistance via o-rings only, not independently lab-certified.
- No capacitive touch alternative to accelerometer tap — one sensing modality, chosen and committed (LIS3DH).
