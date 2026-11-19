# U601 escape map (ESP32-S3-WROOM-1U-N16R8, top side)

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) |
|---|---|---|---|---|---|
| 8 | S | XVF_GPO_R | N (also E) + layer change | yes | U301.56 (B, 12), R405.2 (F, 33) |
| 9 | S | XVF_GPO_G | N (also E) + layer change | yes | U301.58 (B, 12), R406.2 (F, 32) |
| 10 | S | XVF_INT_N | N (also S) + layer change | yes | U301.55 (B, 12), J701.17 (F, 22) |
| 35 | N | BTN_USER_N | E | yes | R607.2 (F, 39), SW603.1 (F, 40) |
| 34 | N | ESP_MUTE_LED | E | yes | R404.2 (F, 35) |
| 11 | S | MUX_ST | E | yes | U103.9 (F, 20), R114.1 (F, 21) |
| 24 | E | LED_EN | E |  | R801.1 (F, 18), U801.3 (F, 19) |
| 22 | E | PRG_EN | E (also W) |  | U704.4 (F, 6), U702.4 (F, 7), U703.4 (F, 10), U701.4 (F, 13), R701.1 (F, 44), SW701.2 (F, 45) |
| 39 | N | ESP_GPIO1 | S | yes | J701.5 (F, 40) |
| 38 | N | ESP_GPIO2 | S | yes | J701.6 (F, 45) |
| 37 | N | ESP_UART_TX | S | yes | J701.21 (F, 38) |
| 4 | S | ESP_GPIO4 | S |  | J701.7 (F, 22) |
| 36 | N | ESP_UART_RX | S | yes | J701.22 (F, 43) |
| 5 | S | ESP_GPIO5 | S |  | J701.8 (F, 27) |
| 6 | S | ESP_GPIO6 | S |  | J701.9 (F, 20) |
| 7 | S | ESP_GPIO7 | S |  | J701.10 (F, 25) |
| 32 | N | ESP_I2C_SCL | S | yes | R705.2 (F, 2), J701.15 (F, 37) |
| 31 | N | ESP_I2C_SDA | S | yes | R704.2 (F, 2), J701.13 (F, 37) |
| 12 | S | ESP_GPIO8 | S |  | J701.11 (F, 20) |
| 17 | E | ESP_GPIO9 | S | yes | J701.12 (F, 30) |
| 3 | S | ESP_EN | W | yes | R601.1 (F, 24), C603.1 (F, 25), SW601.1 (F, 26), SW601.1 (F, 32) |
| 13 | S | ESP_USB_DM | W | yes | U102.2 (F, via R606, 36), J102.A7 (F, via R606, 38), J102.B7 (F, via R606, 38) |
| 27 | N | ESP_BOOT | W | yes | R602.1 (F, 41), SW602.1 (F, 43), SW602.1 (F, 49) |
| 14 | S | ESP_USB_DP | W | yes | U102.4 (F, via R605, 37), J102.B6 (F, via R605, 39), J102.A6 (F, via R605, 39) |
| 33 | N | USER_LED_DATA | local |  | U602.2 (F, 5) |
| 25 | E | LED_DATA | local |  | U802.2 (F, 6) |
| 23 | E | PRG_RST | local |  | Q701.1 (F, 6), R702.1 (F, 8) |
| 21 | E | PRG_DO | local |  | U704.1 (F, 5) |
| 20 | E | PRG_CLK | local |  | U702.1 (F, 4) |
| 19 | E | PRG_DI | local |  | U703.1 (F, 4) |
| 18 | E | PRG_CS_N | local |  | U701.1 (F, 6) |
| 2 | S | +3V3 | power |  | C602.1 (F, 2), C601.1 (F, 3), C314.1 (B, 4), C313.1 (B, 5), L202.2 (F, 6), C208.1 (F, 6) |
| 40 | N | GND | GND |  |  |
| 1 | S | GND | GND |  |  |
| 41 | W | GND | GND |  |  |
| 41 | W | GND | GND |  |  |
| 41 | S | GND | GND |  |  |
| 41 | W | GND | GND |  |  |
| 41 | S | GND | GND |  |  |
| 41 | S | GND | GND |  |  |
| 41 | E | GND | GND |  |  |
| 41 | S | GND | GND |  |  |
| 41 | S | GND | GND |  |  |
| 30 | N | unconnected-(U601-IO37-Pad30) | NC |  |  |
| 29 | N | unconnected-(U601-IO36-Pad29) | NC |  |  |
| 28 | N | unconnected-(U601-IO35-Pad28) | NC |  |  |
| 26 | E | unconnected-(U601-IO45-Pad26) | NC |  |  |
| 16 | E | unconnected-(U601-IO46-Pad16) | NC |  |  |
| 15 | E | unconnected-(U601-IO3-Pad15) | NC |  |  |
