# U601 escape map (ESP32-S3-WROOM-1U-N16R8, top side): length-sensitive signals to a board edge

Group = side of the chip the trace must leave from (N/E/S/W, seen from the top), `local` = only close destinations on the same side, `power` = decoupling / plane, `wraps` = destination is not on the pin's own side. Layer change = destination on the other side of the board (needs a via). Test pads (TP) are movable, so they set the group only when nothing else is on the net; `also X` = real destinations in more than one direction.

| Pin | Pad side | Net | Group | Wraps | Destinations (ref.pin, side, mm) | Why length-sensitive |
|---|---|---|---|---|---|---|
| 13 | S | ESP_USB_DM | W | yes | J102.A7 (F, via R606, 38), J102.B7 (F, via R606, 38) | USB full-speed pair (match D+/D-) |
| 14 | S | ESP_USB_DP | W | yes | J102.B6 (F, via R605, 39), J102.A6 (F, via R605, 39) | USB full-speed pair (match D+/D-) |
