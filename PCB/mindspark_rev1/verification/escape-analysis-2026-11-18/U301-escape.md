# U301 escape map (XVF3800-QF60B-C, bottom side)

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) |
|---|---|---|---|---|---|
| 41 | W | MCLK_LOOP | N | yes | TP412.1 (B, 38) |
| 40 | W | AMP_EN | N + layer change | yes | R510.1 (F, 17), U502.3 (F, 18) |
| 37 | W | XL_UP1 | N | yes | TP408.1 (B, 36) |
| 36 | W | XL_UP0 | N | yes | TP407.1 (B, 40) |
| 35 | W | XL_DN0 | N | yes | TP406.1 (B, 38) |
| 33 | W | XL_DN1 | N | yes | TP405.1 (B, 38) |
| 47 | N | XVF_SPI_MISO | N |  | TP403.1 (B, 33) |
| 50 | N | MIC_DATA1 | N + layer change |  | R507.2 (F, 40) |
| 24 | S | XVF_TCK | N + layer change | yes | J301.3 (F, 34), TP303.1 (B, 34) |
| 23 | S | XVF_TMS | N + layer change | yes | J301.2 (F, 34), TP302.1 (B, 36) |
| 54 | N | XVF_SQ_NLIN | N |  | TP404.1 (B, 36) |
| 20 | S | XVF_TDO | N + layer change | yes | J301.4 (F, 33), TP304.1 (B, 34) |
| 18 | S | XVF_TDI | N + layer change | yes | J301.5 (F, 32), TP305.1 (B, 33) |
| 6 | E | XVF_SPI_CS_N | N | yes | TP401.1 (B, 38) |
| 7 | E | XVF_SPI_MOSI | N | yes | TP402.1 (B, 35) |
| 9 | E | I2S_DATA0 | N + layer change | yes | U503.1 (F, 26), TP409.1 (B, 41) |
| 10 | E | I2S_LRCK | N + layer change | yes | U503.14 (F, 28), TP410.1 (B, 37) |
| 13 | E | I2S_BCLK | N + layer change | yes | U503.16 (F, 29), TP411.1 (B, 39) |
| 14 | E | MCLK_LOOP | N | yes | TP412.1 (B, 45) |
| 32 | W | BTN_ACTION_N | E + layer change | yes | R403.2 (F, 38), SW402.1 (F, 40) |
| 46 | N | MIC_DATA0 | E + layer change | yes | R506.2 (F, 44) |
| 29 | S | USB_MAIN_DP | E + layer change | yes | U101.4 (F, 31), J101.A6 (F, 33), J101.B6 (F, 33) |
| 28 | S | USB_MAIN_DM | E + layer change | yes | U101.2 (F, 30), J101.B7 (F, 32), J101.A7 (F, 32) |
| 21 | S | XVF_RST_N | E (also N/W) + layer change | yes | R703.2 (F, 15), R303.1 (F, 31), U302.1 (F, 32), TP306.1 (B, 32), J301.6 (F, 32) |
| 59 | N | XVF_QSPI_D0 | E + layer change | yes | U401.5 (B, 3), U703.2 (F, 13) |
| 1 | E | XVF_QSPI_D1 | E + layer change |  | U401.2 (B, 6), U704.2 (F, 10) |
| 3 | E | XVF_QSPI_CS_N | E + layer change |  | U401.1 (B, 7), R401.1 (B, 9), U701.2 (F, 14) |
| 5 | E | XVF_QSPI_CLK | E + layer change |  | U401.6 (B, 5), U702.2 (F, 10) |
| 11 | E | BTN_MUTE_N | E + layer change |  | R402.2 (F, 36), SW401.1 (F, 39) |
| 45 | W | XVF_I2C_SDA | S + layer change | yes | J701.14 (F, 36) |
| 44 | W | XVF_I2C_SCL | S + layer change | yes | J701.16 (F, 36) |
| 39 | W | XVF_I2S_DATA1 | S + layer change | yes | J701.18 (F, 34) |
| 51 | N | MIC_DATA3 | S + layer change | yes | R509.2 (F, 47) |
| 53 | N | XVF_I2S_DATA2 | S + layer change | yes | J701.19 (F, 33) |
| 55 | N | XVF_INT_N | S + layer change | yes | U601.10 (F, 12), J701.17 (F, 33) |
| 56 | N | XVF_GPO_R | S (also E) + layer change | yes | U601.8 (F, 12), R405.2 (F, 37) |
| 58 | N | XVF_GPO_G | S (also E) + layer change | yes | U601.9 (F, 12), R406.2 (F, 37) |
| 48 | N | MIC_DATA2 | W + layer change | yes | R508.2 (F, 45) |
| 43 | W | MIC_CLK | local |  | U501.2 (B, 8) |
| 60 | N | XVF_QSPI_D2 | local |  | U401.3 (B, 6) |
| 16 | S | XVF_XIN | local |  | R302.1 (B, 5), Y301.1 (B, 7), C320.1 (B, 8) |
| 2 | E | XVF_QSPI_D3 | local |  | U401.7 (B, 5) |
| 15 | E | XVF_XOUT | local |  | R302.2 (B, 4), C321.1 (B, via R301, 6), Y301.3 (B, via R301, 8) |
| 42 | W | +0V9 | power |  | C306.1 (B, 2), C305.1 (B, 4), C307.1 (B, 5), C308.1 (B, 7), C309.1 (B, 7), C304.1 (B, 8) |
| 38 | W | +3V3 | power |  | C311.1 (B, 2), C314.1 (B, 6), C313.1 (B, 6), C312.1 (B, 7), U601.2 (F, 9), C310.1 (B, 9) |
| 34 | W | +0V9 | power |  | C305.1 (B, 2), C306.1 (B, 4), C304.1 (B, 5), C303.1 (B, 7), C307.1 (B, 8), FB301.1 (B, 8) |
| 31 | W | +1V8 | power |  | C317.1 (B, 2), C316.1 (B, 4), C315.1 (B, 7), C318.1 (B, 8), U203.5 (F, 16), C209.1 (F, 18) |
| 30 | S | +3V3 | power |  | C313.1 (B, 2), C314.1 (B, 3), C311.1 (B, 5), U601.2 (F, 7), C602.1 (F, 8), C310.1 (B, 9) |
| 63 | W | +0V9 | power |  | C305.1 (B, 4), C306.1 (B, 4), C304.1 (B, 6), C307.1 (B, 6), C303.1 (B, 7), C308.1 (B, 7) |
| 49 | N | +0V9 | power |  | C307.1 (B, 2), C308.1 (B, 4), C309.1 (B, 5), C306.1 (B, 5), C305.1 (B, 7), C301.1 (B, 8) |
| 27 | S | +0V9 | power |  | C304.1 (B, 2), C303.1 (B, 4), C305.1 (B, 5), FB301.1 (B, 6), C306.1 (B, 7), C302.1 (B, 8) |
| 26 | S | +1V8 | power |  | C316.1 (B, 3), C315.1 (B, 4), C317.1 (B, 5), C318.1 (B, 6), U203.5 (F, 17), C209.1 (F, 18) |
| 52 | N | +3V3 | power |  | C312.1 (B, 2), C311.1 (B, 7), U401.8 (B, 7), C310.1 (B, 7), R705.1 (F, 8), C401.1 (B, 8) |
| 64 | N | +0V9 | power |  | C307.1 (B, 4), C308.1 (B, 4), C309.1 (B, 6), C306.1 (B, 6), C301.1 (B, 6), C305.1 (B, 7) |
| 62 | S | +0V9 | power |  | C303.1 (B, 4), C304.1 (B, 4), C305.1 (B, 6), C302.1 (B, 6), FB301.1 (B, 6), C306.1 (B, 7) |
| 22 | S | PLL_AVDD | power |  | C319.1 (B, 2), FB301.2 (B, 4) |
| 57 | N | +0V9 | power |  | C308.1 (B, 2), C307.1 (B, 4), C301.1 (B, 5), C309.1 (B, 6), C302.1 (B, 7), C306.1 (B, 8) |
| 19 | S | +0V9 | power |  | C303.1 (B, 2), C304.1 (B, 4), C302.1 (B, 5), FB301.1 (B, 6), C301.1 (B, 7), C305.1 (B, 8) |
| 17 | S | +1V8 | power |  | C315.1 (B, 2), C318.1 (B, 3), C316.1 (B, 4), C317.1 (B, 8), U203.5 (F, 19), C209.1 (F, 20) |
| 61 | E | +0V9 | power |  | C302.1 (B, 4), C301.1 (B, 4), C308.1 (B, 6), C303.1 (B, 6), C307.1 (B, 7), C304.1 (B, 7) |
| 4 | E | +0V9 | power |  | C301.1 (B, 2), C302.1 (B, 4), C308.1 (B, 5), C307.1 (B, 7), C303.1 (B, 8), C309.1 (B, 8) |
| 8 | E | +3V3 | power |  | C310.1 (B, 2), C312.1 (B, 7), U401.8 (B, 8), C313.1 (B, 9), C311.1 (B, 9), C401.1 (B, 10) |
| 12 | E | +0V9 | power |  | C302.1 (B, 2), C301.1 (B, 4), C303.1 (B, 5), C304.1 (B, 7), C308.1 (B, 8), FB301.1 (B, 8) |
| 65 | W | GND | GND |  |  |
| 25 | S | unconnected-(U301-NC-Pad25) | NC |  |  |
