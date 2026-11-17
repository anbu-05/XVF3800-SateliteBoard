# Power routing review, 2026-11-17

Review of the power routing as saved on 2026-11-13 15:18, before the TPS2121 and LED switch were moved.
Renders come from `tools/power_render.py` and drop figures from `tools/power_drop.py`. Copper is JLC's default: 35 µm outer, 15.2 µm (0.5 oz) inner.

## Images

- `current-F.Cu.png`, `current-In1.Cu.png`, `current-In2.Cu.png`, `current-B.Cu.png`: power nets on each layer, coloured by rail.
- `current-regulators-F.Cu.png`: buck and LDO area, close up.
- `current-tps2121-F.Cu.png`: TPS2121 area, close up.
- `proposed-In2-regions.png`: proposed In2 regions (rough sketch, not final geometry).

## Findings on the routing as it was

1. No GND copper: no zones, In1 empty, 181 unconnected GND items.
2. In2 used as 0.5 mm tracks on 0.5 oz copper (≈2.3 mΩ/mm), not a plane:
   - J101 → TPS2121 IN1: 74–85 mΩ (≈0.25 V and 0.7 W at 3 A).
   - J102 → TPS2121 IN2: ≈133 mΩ (≈0.4 V and 1.2 W at 3 A).
   - The TPS2121 PR1/CP2/OV dividers see this drop, so the hand-over threshold moves under load.
   - B.Cu (XVF3800 side) references a patchwork of rail tracks.
3. +0V9: 69 mΩ from L201 to the XVF3800 VDD paddles (21 mV at 0.3 A, 69 mV at 1 A, against a ±45 mV window); one 0.45/0.2 via carries it; FB senses at C203.
4. 49 vias in SMD pads (USB-C VBUS/GND, SOT-23 pins, 0402 caps, J701, WS2812 VDD).
5. Moderate: vias smaller than the Power class (0.6/0.3), no local caps at TPS2121 IN pins, U201 SW track 4 mm, C202 GND has no via, 0.1 mm power tracks, low-current runs breaking up In2.

## Proposal

- In1: solid GND, nothing else.
- In2 regions: +3V3 background fill; +5V band along the bottom (TPS2121 output, buck inputs, LED switch); +0V9 island under the XVF3800 with a ≈6 mm neck to L201 (L201 output facing up, FB divider top taken from a VDD paddle); VBUS_MAIN short strip J101 → TPS2121; VBUS_ESP 4–5 mm strip down the left edge and under J701.
- Tracks: +5V to the amp switch (1.5 mm outer), +5V_LED as a ring track on B.Cu, +1V8, PLL_AVDD and mic rails as now.
- Move the TPS2121 block (U103, R105–R114, C105–C107) and the LED switch (U801, C814, C815) to the bottom right, next to L201, so power flows one way: in at the bottom, up through the middle.
- Rules: B.Cu signals must not cross region edges (take long runs to F.Cu over In1); ≥2 vias of 0.6/0.3 per layer change on rails above 0.5 A; no vias in pads.
