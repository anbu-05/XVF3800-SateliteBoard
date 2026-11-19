# U301 escape map (XVF3800-QF60B-C, bottom side): length-sensitive signals to a board edge

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) | Why length-sensitive |
|---|---|---|---|---|---|---|
| 50 | W | MIC_DATA1 | N + layer change | yes | R507.2 (F, 42) | PDM data, sampled on MIC_CLK edges |
| 18 | E | XVF_TDI | N + layer change | yes | J301.5 (F, 27) | JTAG, sampled on TCK |
| 20 | E | XVF_TDO | N + layer change | yes | J301.4 (F, 28) | JTAG, sampled on TCK |
| 23 | E | XVF_TMS | N + layer change | yes | J301.2 (F, 30) | JTAG, sampled on TCK |
| 24 | E | XVF_TCK | N + layer change | yes | J301.3 (F, 30) | JTAG clock |
| 46 | W | MIC_DATA0 | E + layer change | yes | R506.2 (F, 48) | PDM data, sampled on MIC_CLK edges |
| 28 | E | USB_MAIN_DM | E + layer change |  | J101.B7 (F, 26), J101.A7 (F, 27) | USB 2.0 high-speed pair (90 ohm, match D+/D-) |
| 29 | E | USB_MAIN_DP | E + layer change |  | J101.A6 (F, 27), J101.B6 (F, 27) | USB 2.0 high-speed pair (90 ohm, match D+/D-) |
| 53 | W | XVF_I2S_DATA2 | S + layer change | yes | J701.19 (F, 29) | I2S data, timed against BCLK |
| 51 | W | MIC_DATA3 | S + layer change | yes | R509.2 (F, 46) | PDM data, sampled on MIC_CLK edges |
| 39 | S | XVF_I2S_DATA1 | S + layer change |  | J701.18 (F, 31) | I2S data, timed against BCLK |
| 48 | W | MIC_DATA2 | W + layer change |  | R508.2 (F, 40) | PDM data, sampled on MIC_CLK edges |
