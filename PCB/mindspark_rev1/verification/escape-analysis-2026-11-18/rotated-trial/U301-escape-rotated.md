# U301 escape map (XVF3800-QF60B-C, bottom side)

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) |
|---|---|---|---|---|---|
| 54 | W | XVF_SQ_NLIN | N | yes | TP404.1 (B, 40) |
| 50 | W | MIC_DATA1 | N + layer change | yes | R507.2 (F, 42) |
| 47 | W | XVF_SPI_MISO | N | yes | TP403.1 (B, 38) |
| 41 | S | MCLK_LOOP | N | yes | TP412.1 (B, 43) |
| 6 | N | XVF_SPI_CS_N | N |  | TP401.1 (B, 38) |
| 40 | S | AMP_EN | N + layer change | yes | R510.1 (F, 22), U502.3 (F, 23) |
| 7 | N | XVF_SPI_MOSI | N |  | TP402.1 (B, 33) |
| 9 | N | I2S_DATA0 | N + layer change |  | U503.1 (F, 21), TP409.1 (B, 36) |
| 37 | S | XL_UP1 | N | yes | TP408.1 (B, 39) |
| 10 | N | I2S_LRCK | N + layer change |  | U503.14 (F, 23), TP410.1 (B, 33) |
| 36 | S | XL_UP0 | N | yes | TP407.1 (B, 41) |
| 35 | S | XL_DN0 | N | yes | TP406.1 (B, 41) |
| 13 | N | I2S_BCLK | N + layer change |  | U503.16 (F, 23), TP411.1 (B, 33) |
| 33 | S | XL_DN1 | N | yes | TP405.1 (B, 39) |
| 14 | N | MCLK_LOOP | N |  | TP412.1 (B, 39) |
| 18 | E | XVF_TDI | N + layer change | yes | J301.5 (F, 27), TP305.1 (B, 39) |
| 20 | E | XVF_TDO | N + layer change | yes | J301.4 (F, 28), TP304.1 (B, 39) |
| 23 | E | XVF_TMS | N + layer change | yes | J301.2 (F, 30), TP302.1 (B, 41) |
| 24 | E | XVF_TCK | N + layer change | yes | J301.3 (F, 30), TP303.1 (B, 39) |
| 60 | W | XVF_QSPI_D2 | E | yes | U401.3 (B, 12) |
| 59 | W | XVF_QSPI_D0 | E + layer change | yes | U401.5 (B, 9), U703.2 (F, 18) |
| 46 | W | MIC_DATA0 | E + layer change | yes | R506.2 (F, 48) |
| 1 | N | XVF_QSPI_D1 | E + layer change | yes | U401.2 (B, 11), U704.2 (F, 16) |
| 3 | N | XVF_QSPI_CS_N | E (also N) + layer change | yes | U401.1 (B, 11), R401.1 (B, 12), U701.2 (F, 19) |
| 5 | N | XVF_QSPI_CLK | E + layer change | yes | U401.6 (B, 7), U702.2 (F, 15) |
| 11 | N | BTN_MUTE_N | E + layer change | yes | R402.2 (F, 36), SW401.1 (F, 38) |
| 32 | S | BTN_ACTION_N | E + layer change | yes | R403.2 (F, 33), SW402.1 (F, 35) |
| 15 | N | XVF_XOUT | E | yes | R301.2 (B, 9), R302.2 (B, 9) |
| 16 | E | XVF_XIN | E |  | R302.1 (B, 9), Y301.1 (B, 10), C320.1 (B, 12) |
| 21 | E | XVF_RST_N | E (also N/W) + layer change |  | R703.2 (F, 10), J301.6 (F, 28), R303.1 (F, 32), U302.1 (F, 33), TP306.1 (B, 37) |
| 28 | E | USB_MAIN_DM | E + layer change |  | U101.2 (F, 25), J101.B7 (F, 26), J101.A7 (F, 27) |
| 29 | E | USB_MAIN_DP | E + layer change |  | U101.4 (F, 25), J101.A6 (F, 27), J101.B6 (F, 27) |
| 58 | W | XVF_GPO_G | S (also E) + layer change | yes | U601.9 (F, 12), R406.2 (F, 41) |
| 56 | W | XVF_GPO_R | S (also E) + layer change | yes | U601.8 (F, 11), R405.2 (F, 40) |
| 55 | W | XVF_INT_N | S + layer change | yes | U601.10 (F, 12), J701.17 (F, 29) |
| 53 | W | XVF_I2S_DATA2 | S + layer change | yes | J701.19 (F, 29) |
| 51 | W | MIC_DATA3 | S + layer change | yes | R509.2 (F, 46) |
| 45 | S | XVF_I2C_SDA | S + layer change |  | J701.14 (F, 30) |
| 44 | S | XVF_I2C_SCL | S + layer change |  | J701.16 (F, 30) |
| 39 | S | XVF_I2S_DATA1 | S + layer change |  | J701.18 (F, 31) |
| 48 | W | MIC_DATA2 | W + layer change |  | R508.2 (F, 40) |
| 2 | N | XVF_QSPI_D3 | local |  | U401.7 (B, 8) |
| 43 | S | MIC_CLK | local |  | U501.2 (B, 8) |
| 57 | W | +0V9 | power |  | C308.1 (B, 2), C307.1 (B, 4), C301.1 (B, 5), C309.1 (B, 6), C302.1 (B, 7), C306.1 (B, 8) |
| 52 | W | +3V3 | power |  | C312.1 (B, 2), C311.1 (B, 7), C310.1 (B, 7), U601.2 (F, 9), C313.1 (B, 10), C314.1 (B, 10) |
| 49 | W | +0V9 | power |  | C307.1 (B, 2), C308.1 (B, 4), C309.1 (B, 5), C306.1 (B, 5), C305.1 (B, 7), C301.1 (B, 8) |
| 64 | W | +0V9 | power |  | C307.1 (B, 4), C308.1 (B, 4), C309.1 (B, 6), C306.1 (B, 6), C301.1 (B, 6), C305.1 (B, 7) |
| 4 | N | +0V9 | power |  | C301.1 (B, 2), C302.1 (B, 4), C308.1 (B, 5), C307.1 (B, 7), C303.1 (B, 8), C309.1 (B, 8) |
| 42 | S | +0V9 | power |  | C306.1 (B, 2), C305.1 (B, 4), C307.1 (B, 5), C308.1 (B, 7), C309.1 (B, 7), C304.1 (B, 8) |
| 8 | N | +3V3 | power |  | C310.1 (B, 2), U401.8 (B, 7), C312.1 (B, 7), C401.1 (B, 8), R705.1 (F, 8), R704.1 (F, 9) |
| 61 | N | +0V9 | power |  | C302.1 (B, 4), C301.1 (B, 4), C308.1 (B, 6), C303.1 (B, 6), C307.1 (B, 7), C304.1 (B, 7) |
| 63 | S | +0V9 | power |  | C306.1 (B, 4), C305.1 (B, 4), C304.1 (B, 6), C307.1 (B, 6), C303.1 (B, 7), C308.1 (B, 7) |
| 38 | S | +3V3 | power |  | C311.1 (B, 2), C314.1 (B, 6), C313.1 (B, 6), C312.1 (B, 7), U601.2 (F, 9), C310.1 (B, 9) |
| 12 | N | +0V9 | power |  | C302.1 (B, 2), C301.1 (B, 4), C303.1 (B, 5), C304.1 (B, 7), C308.1 (B, 8), FB301.1 (B, 8) |
| 34 | S | +0V9 | power |  | C305.1 (B, 2), C306.1 (B, 4), C304.1 (B, 5), C303.1 (B, 7), C307.1 (B, 8), FB301.1 (B, 8) |
| 62 | E | +0V9 | power |  | C303.1 (B, 4), C304.1 (B, 4), C305.1 (B, 6), C302.1 (B, 6), FB301.1 (B, 6), C306.1 (B, 7) |
| 31 | S | +1V8 | power |  | C317.1 (B, 2), C316.1 (B, 4), C315.1 (B, 7), C318.1 (B, 8), U203.5 (F, 19), C209.1 (F, 21) |
| 17 | E | +1V8 | power |  | C315.1 (B, 2), C318.1 (B, 3), C316.1 (B, 4), C317.1 (B, 8), U203.5 (F, 24), C209.1 (F, 26) |
| 19 | E | +0V9 | power |  | C303.1 (B, 2), C304.1 (B, 4), C302.1 (B, 5), FB301.1 (B, 6), C301.1 (B, 7), C305.1 (B, 8) |
| 22 | E | PLL_AVDD | power |  | C319.1 (B, 2), FB301.2 (B, 4) |
| 26 | E | +1V8 | power |  | C316.1 (B, 3), C315.1 (B, 4), C317.1 (B, 5), C318.1 (B, 6), U203.5 (F, 21), C209.1 (F, 23) |
| 27 | E | +0V9 | power |  | C304.1 (B, 2), C303.1 (B, 4), C305.1 (B, 5), FB301.1 (B, 6), C306.1 (B, 7), C302.1 (B, 8) |
| 30 | E | +3V3 | power |  | C313.1 (B, 2), C314.1 (B, 3), C311.1 (B, 5), C310.1 (B, 9), C312.1 (B, 10), U401.8 (B, 11) |
| 65 | W | GND | GND |  |  |
| 25 | E | unconnected-(U301-NC-Pad25) | NC |  |  |
