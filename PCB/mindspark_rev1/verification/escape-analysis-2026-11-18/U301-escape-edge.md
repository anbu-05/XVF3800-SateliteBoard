# U301 escape map (XVF3800-QF60B-C, bottom side): length-sensitive signals to a board edge

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) | Why length-sensitive |
|---|---|---|---|---|---|---|
| 50 | N | MIC_DATA1 | N + layer change |  | R507.2 (F, 40) | PDM data, sampled on MIC_CLK edges |
| 24 | S | XVF_TCK | N + layer change | yes | J301.3 (F, 34) | JTAG clock |
| 23 | S | XVF_TMS | N + layer change | yes | J301.2 (F, 34) | JTAG, sampled on TCK |
| 20 | S | XVF_TDO | N + layer change | yes | J301.4 (F, 33) | JTAG, sampled on TCK |
| 18 | S | XVF_TDI | N + layer change | yes | J301.5 (F, 32) | JTAG, sampled on TCK |
| 46 | N | MIC_DATA0 | E + layer change | yes | R506.2 (F, 44) | PDM data, sampled on MIC_CLK edges |
| 29 | S | USB_MAIN_DP | E + layer change | yes | J101.A6 (F, 33), J101.B6 (F, 33) | USB 2.0 high-speed pair (90 ohm, match D+/D-) |
| 28 | S | USB_MAIN_DM | E + layer change | yes | J101.B7 (F, 32), J101.A7 (F, 32) | USB 2.0 high-speed pair (90 ohm, match D+/D-) |
| 39 | W | XVF_I2S_DATA1 | S + layer change | yes | J701.18 (F, 34) | I2S data, timed against BCLK |
| 51 | N | MIC_DATA3 | S + layer change | yes | R509.2 (F, 47) | PDM data, sampled on MIC_CLK edges |
| 53 | N | XVF_I2S_DATA2 | S + layer change | yes | J701.19 (F, 33) | I2S data, timed against BCLK |
| 48 | N | MIC_DATA2 | W + layer change | yes | R508.2 (F, 45) | PDM data, sampled on MIC_CLK edges |
