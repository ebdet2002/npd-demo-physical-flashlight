# Why: Smart Adaptive Flashlight

## Customer

Night-shift warehouse workers and outdoor tradespeople — electricians, HVAC
technicians, line workers — who do physically demanding work in low light,
often with one or both hands occupied, gloved, or wet.

## Pain Point

Standard flashlights require manual mode-switching: twisting a bezel,
cycling through a multi-click button sequence, or holding a button for a
timed interval to reach the mode you want. This is slow, fiddly, and
genuinely unsafe when:

- your hands are gloved (can't feel a small button or twist collar),
- your hands are wet or greasy (slip risk, static discharge near
  electrical panels),
- you're holding a tool, a part, or a ladder rail in the other hand and
  can't spare a hand to fumble with mode cycling,
- you're switching between "need a lot of light right now" (inspecting a
  breaker panel) and "need to not blind your coworker or wake someone up"
  (walking through a warehouse break area) multiple times per shift.

Existing flashlights also run at a fixed brightness regardless of ambient
conditions, which either wastes battery in bright conditions or under-lights
in genuine darkness — and running out of charge mid-shift is its own safety
issue.

## Novel Product Angle

A **smart flashlight** with two behaviors layered on top of a standard
handheld form factor:

1. **Tap-based mode switching.** A single tap on the tail cap (detected via
   a simple accelerometer) cycles through brightness levels. A double tap
   toggles a strobe/SOS mode. No bezel twist, no multi-click timing window —
   a tap works through gloves and wet hands, and doesn't require fine motor
   control or looking at the flashlight.

2. **Ambient-light-adaptive brightness.** An onboard light sensor measures
   ambient conditions and sets a baseline PWM duty cycle automatically —
   dimmer in a lit warehouse aisle, brighter in genuine darkness — so the
   user's tap-selected "level" (low/med/high) is relative to current
   conditions rather than an absolute duty cycle, saving battery without the
   user having to think about it.

This is deliberately a modest, buildable v1: one new sensor-driven
interaction model and one adaptive-brightness behavior, layered onto an
otherwise conventional 18650-cell flashlight body — not a full smart-device
redesign.
