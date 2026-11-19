<!-- agents-md: v1 · archive · ≤5000 words -->
# AGENTS.md archive 001

## Archived 2026-11-05 (covers 2026-11-03): ESP32 module sourcing, superseded when the ESP32 was dropped

### ESP32-S3 WROOM module — checked 2026-11-03

- User wants a WROOM module, "high end", believing variants cost about the same.
- [LCSC WROOM search](https://www.lcsc.com/search?q=ESP32-S3-WROOM): WROOM-1 tops out at N16R8 on LCSC. [ESP32-S3-WROOM-1-N16R8, C2913202](https://www.lcsc.com/product-detail/C2913202.html): 28,127 in stock, $5.4076 @1, $3.6277 @650. -40 to +65 °C. WROOM-1 variants span about $4.31–5.84 @1, so the user's "same price" holds within WROOM-1.
- [LCSC search for WROOM-1-N16R16VA](https://www.lcsc.com/search?q=ESP32-S3-WROOM-1-N16R16VA): no listing. [DigiKey India search](https://www.digikey.in/en/products/result?keywords=ESP32-S3-WROOM-1-N16R16VA) redirected to an ESP-VOCAT dev board, so no module listing there either.
- [LCSC WROOM-2 search](https://www.lcsc.com/search?q=ESP32-S3-WROOM-2): N32R16V (C42417293) 0 stock, $10.95 @1; N32R8V 0 stock.
- [DigiKey India ESP32-S3-WROOM-2-N32R16V](https://www.digikey.in/en/products/detail/espressif-systems/ESP32-S3-WROOM-2-N32R16V/25811280): 684 in stock, Active, ₹1,243.09 @1, ₹690.74 @650. N32R8V and N16R8V listed Obsolete, 0 stock.
- WROOM-2 at about ₹1,243 vs N16R8 at about ₹514 (at ₹95/USD) is roughly 2.4× at qty 1, so the "same price" assumption breaks there.
- **Decided 2026-11-03: ESP32-S3-WROOM-1-N16R8 (LCSC C2913202), PCB-antenna version.** User chose it after the WROOM-2 cost/1.8 V pushback. External-antenna 1U-N16R8 ([LCSC C3013946](https://www.lcsc.com/search?q=ESP32-S3-WROOM-1U-N16R8), $5.24) remains an option if the enclosure blocks the PCB antenna.

## Archived 2026-11-07 (covers 2026-11-05): CM5 reference details and smart-speaker teardown comparison

### From "Reference documents"

- **CM5 (rev 2):** [datasheet, Release 3, 08/06/2026](https://pip-assets.raspberrypi.com/categories/944-raspberry-pi-compute-module-5/documents/RP-008180-DS-7-cm5-datasheet.pdf); [CM5 IO board datasheet (schematic appendix)](https://pip-assets.raspberrypi.com/categories/1097-raspberry-pi-compute-module-5-io-board/documents/RP-008182-DS-2-cm5io-datasheet.pdf). IO board KiCad files on Raspberry Pi's pip site (not opened).
  - Carrier connectors: Amphenol 10164227-1001A1RLF (1.5 mm stack) or 10164227-1004A1RLF (4.0 mm stack, 2.5 mm clearance).
  - Power: 5 V on pins 77–85, 4.75–5.25 V, up to 5 A, monotonic rise. CC1/CC2 (pins 94/96) let the CM5 PMIC negotiate 5 V / 5 A on a USB-C connector itself.
  - USB: one USB 2.0 port (pins 103/105, boot port, dwc2 overlay for host); two USB 3.0 ports each with their own USB 2.0 pair (USB3-0-DP/DM pins 134/136) — planned XVF3800 link.
  - nRPI_BOOT: hold low within 2 ms of 5 V rising to boot over USB 2.0. Module has its own JST-SH debug UART.

## Smart-speaker comparison — researched 2026-11-05

Amazon and Google don't publish speaker wattage; teardowns give amp chips and driver sizes only. Amp chip ratings are headroom, not speaker power.
- Echo Dot 3rd gen: 40 mm (1.6") driver, TI TAS2770 (20 W-class) amp ([teardown](https://briandorey.com/post/echo-dot-3rd-gen-smart-speaker-teardown)).
- Echo Dot 4th gen: same 40 mm driver, TI TAS5805M ([teardown](https://www.briandorey.com/post/echo-dot-4th-gen-smart-speaker-teardown)).
- Echo Dot 5th gen: 44 mm (1.73") driver, Maxim MAX98396 ([teardown](https://briandorey.com/post/echo-dot-5th-gen-smart-speaker-teardown)).
- Google Nest Mini: 40 mm driver; amp not identified ([Google specs](https://support.google.com/googlenest/answer/7072284?hl=en)).

## Archived 2026-11-07 (covers 2026-11-05): LM48511 sourcing detail

### LM48511 amp — checked 2026-11-05

- [TI product page](https://www.ti.com/product/LM48511): active, analog input, built-in boost, 3–5.5 V supply. 3 W @ 8 Ω or 5.4 W @ 4 Ω at 5 V.
- [LCSC C527406 LM48511SQX/NOPB](https://www.lcsc.com/category/1415.html?scene=FULL_MATCH&globalKeyword=LM48511): 1,082 in stock. $1.4243 @1, $1.3085 @10, $0.9893 @500, $0.976 @1,000. Reel 4,500. SMT Extended.
- LCSC C527474 LM48511SQ/NOPB (1,000 reel): 0 in stock, $4.814 @1.
- Same chip gives the step up: a 4 Ω speaker gets 5.4 W instead of 3 W at no extra cost.

## Archived 2026-11-07 (covers 2026-11-07): speaker shortlists, LCSC and DigiKey (superseded by the Challenge CS45 decision)

### Speaker shortlist — checked 2026-11-07

Pulled all 3,004 parts in the [LCSC Speakers category](https://www.lcsc.com/category/55.html) through LCSC's listing API. Filtered to 4 Ω, 3–10 W, 36–60 mm: 47 matches, 14 in stock. Ranked by resonant frequency (F0); lower F0 means more bass, which matters more than the wattage rating.

| Pick | LCSC | Size | Rated | F0 | SPL | Stock | $ @1 / @100 |
|---|---|---|---|---|---|---|---|
| 1 | [C5156352 FUET FS44DS0450-H25-R01](https://www.lcsc.com/product-detail/C5156352.html) ([datasheet](https://datasheet.lcsc.com/datasheet/pdf/0751dade54522b555fef1bb26613c899.pdf?productCode=C5156352)) | 43.5 mm, about 25 mm deep | 5 W | 150 Hz | 88 dB | 16 | 3.56 / 2.35 @80 |
| 2 | [C782108 FUET FS40DS0450-H18.3](https://www.lcsc.com/product-detail/C782108.html) ([datasheet](https://datasheet.lcsc.com/datasheet/pdf/c2feda8a21f9a1772a041a0975ad9f90.pdf?productCode=C782108)) | 40 mm, about 18 mm deep | 5 W | 230 Hz | 89 dB | 61 | 2.11 / 1.38 |
| 3 | [C53325602 Dragonstate HDK-5204KC-4W](https://www.lcsc.com/product-detail/C53325602.html) ([datasheet](https://datasheet.lcsc.com/datasheet/pdf/2839566b8986ba40647683d12d3d6ee1.pdf?productCode=C53325602)) | 52 mm | 3 W | 200 Hz | 92.5 dB | 60 | 0.80 / 0.50 @80 |

- Depth reading from the "H25"/"H18.3" in model names is an assumption; confirm in the datasheets.
- Rejected: in-stock parts with F0 ≥ 375 Hz (thin, phone-like sound), e.g. FS50M01 (F0 600 Hz, 500 Hz–5 kHz). Western brands (PUI, CUI, Visaton) are listed but 0 stock on LCSC.

### Speaker shortlist, DigiKey India — checked 2026-11-07

From the [DigiKey Speakers category](https://www.digikey.in/en/products/filter/speakers/156), keyword "SPEAKER 4OHM 5W" (52 results). Prices shown in USD on the page. Sensitivity figures use different test distances per maker, so they are not comparable; F0 is.

| Part | Size, depth | Rated | F0 | Stock | $ @1 |
|---|---|---|---|---|---|
| [Challenge CS45-05D13-24-1X](https://www.digikey.in/en/products/detail/challenge-electronics/CS45-05D13-24-1X/25602924) | 45 mm round, 24 mm | 5 W | 130 Hz | 279 | 8.37 |
| [Ole Wolff OWS-525229TA-4](https://www.digikey.in/en/products/detail/ole-wolff-electronics-inc/OWS-525229TA-4/16735145) | 52 mm square, 31.6 mm | 5 W | 120 Hz | 109 | 8.69 |
| [Challenge CS52-05D12-31-1](https://www.digikey.in/en/products/detail/challenge-electronics/CS52-05D12-31-1/18717667) | 52 mm square, 31.6 mm | 5 W | 120 Hz | 917 | 11.60 |
| [DB Unlimited SP520104-1](https://www.digikey.in/en/products/detail/db-unlimited/SP520104-1/9990682) | 52 mm round, 28 mm | 5 W | 150 Hz | 145 | 11.58 |
| [PUI AS04004MR-N50-WP-2-R](https://www.digikey.in/en/products/detail/pui-audio-inc/AS04004MR-N50-WP-2-R/10135896) | 40 mm round, 21.5 mm | 5 W | 180 Hz | 953 | 8.54 |

- Recommended overall: Challenge CS45-05D13-24-1X (lowest F0 at 45 mm). LCSC FUET FS44DS0450-H25-R01 (F0 150 Hz, $3.56) is the cheaper near-equivalent.
- Mouser not checked (blocked the automated browser before).

## Archived 2026-11-07 (covers 2026-11-03): XVF3800 distributor detail

### XMOS XVF3800 — checked 2026-11-03

- [XMOS product page](https://www.xmos.com/xvf3800/): single order code XVF3800-QF60B-C; no higher-spec variant.
- [LCSC C20491135](https://www.lcsc.com/product-detail/C20491135.html): 26 in stock. $23.1568 @1, $22.1135 @10, $20.3086 @30, $18.7328 @100. Full tray 416. SMT Extended.
- [JLC parts library](https://jlcpcb.com/parts/componentSearch?searchTxt=C20491135): same C20491135, shared LCSC stock. $23.0489 @1, $18.6455 @416+.
- [DigiKey India 880-XVF3800-QF60B-C-ND](https://www.digikey.in/en/products/detail/xmos/XVF3800-QF60B-C/21280440): 2,272 in stock, MSL 3, 12-week lead. ₹2,061.98 @1, ₹1,647.97 @10, ₹1,544.62 @25, ₹1,431.07 @100, ₹1,352.38 @416.
- [Mouser India search](https://www.mouser.in/c/?q=XVF3800-QF60B-C): blocked the automated browser; not checked.

## Archived 2026-11-07 (covers 2026-11-05): TLV320AIC3104 sourcing detail

### TLV320AIC3104 codec — checked 2026-11-05

- [TI product page](https://www.ti.com/product/TLV320AIC3104), datasheet SLAS510G (rev Feb 2021): I²C control, I²S/TDM, 8–96 kHz. Headphone and line outputs only, **no speaker driver**. AVDD/DRVDD 2.7–3.6 V, DVDD 1.525–1.95 V (share XVF3800 1.8 V), IOVDD 1.1–3.6 V. 5 × 5 mm 32-pin QFN.
- [LCSC C181753 TLV320AIC3104IRHBR](https://www.lcsc.com/product-detail/C181753.html): 1,695 in stock. $2.4701 @1, $2.0815 @10, $1.4764 @500, $1.4285 @1,000. Reel 3,000. SMT Extended.
- [LCSC C2867364 TLV320AIC3104IRHBT](https://www.lcsc.com/product-detail/C2867364.html) (small 250 reel): 40 in stock. $1.9062 @1, $1.6042 @10. Cheaper at qty 1 than the IRHBR; same die.
- No step-up part considered: the firmware only knows the AIC3104, so a different codec breaks Option A.

## Archived 2026-11-07 (covers 2026-11-05): ReSpeaker bench test detail

## ReSpeaker XVF3800 bench test — 2026-11-05

- User owns the plain USB ReSpeaker XVF3800 (no XIAO), USB ID 2886:001a, bcdDevice 2.06. Reference for rev 1.
- USB firmware: one stereo playback and one stereo capture stream, 16 kHz / 16-bit only; raw mics not exposed.
- Capture: left peaks moderately (likely comms output); right near full scale (likely ASR output with heavy AGC). User judged both "pretty good". LED ring follows the talker.
- **USB drop issue (unresolved):** with a 5 W passive speaker on the amp connector, the board reset off USB 26+ times in ~4 min, even idle (kernel `-71` errors). Without the speaker: clean 60 s, then drops resumed in bursts (10 drops, 16:56–17:03). Speaker not the only cause; cable/port not ruled out. Speaker impedance not recorded.
- Test clips: `respeaker-tests/01-voice-near-far.wav` (stereo), `01-left.wav`, `01-right.wav`.


## Archived 2026-11-07 (covers 2026-11-05 to 2026-11-07): MAX98357A sourcing detail

### MAX98357A I²S amp — checked 2026-11-05

- Pin-configured I²S class-D amp with built-in DAC, no I²C. 2.5–5.5 V. 3.2 W @ 4 Ω, 1.8 W @ 8 Ω at 5 V. So the speaker should be 4 Ω.
- [LCSC C910544 MAX98357AETE+T](https://www.lcsc.com/category/1415.html?scene=FULL_MATCH&globalKeyword=MAX98357A), TQFN-16 3 × 3 mm: 32,588 in stock. $1.3203 @1, $1.1536 @10, $0.8335 @500, $0.8104 @1,000. SMT Extended.
- LCSC C2682619 MAX98357AEWL+T, 9-ball WLP 1.3 × 1.3 mm: 8,708 in stock, $0.6017 @1. **Chosen** (machine-assembled board). Needs fine-pitch PCB rules; hard to rework by hand.
- Step up: none at 5 V. About 3 W into 4 Ω is the practical limit of any amp running directly from 5 V; more needs a boost amp such as the LM48511 (5.4 W @ 4 Ω).

## Archived 2026-11-07 (covers 2026-11-07): echo cancellation notes from the XMOS tuning guide

## Echo cancellation (AEC) — from the XMOS tuning guide, 2026-11-07

Source: [Tuning the Application](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/user_guide/04_tuning_the_application.html).
- Linear AEC adapts on its own, continuously, using the playback (reference) signal; converges in under 30 s. No calibration run for speaker position.
- Per-product tuning (done once per enclosure, by us): mic/reference gains, `AUDIO_MGR_SYS_DELAY` (measured with a white-noise track + `xvf_tools.py mic_ref_correlate`; reference must arrive before the echo, delay ≤ about 40 samples and constant), silence level, AGC, echo/noise suppression, EQ, and a non-linear echo model trained in a quiet room.
- Runtime parameters reset on power-up. Making them default, and installing the trained non-linear model, needs the XMOS source release and a firmware rebuild (YAML files under `sources/app_xvf3800/.../settings_and_defaults/product/`).
- Speaker must stay in its linear range (no rattles or buzz); mic peaks about 6 dB below reference peak.

## Archived 2026-11-07: Mics research (verbatim)

### Mics (rev 1) — researched 2026-11-07

- XMOS guidance ([acoustic guidelines](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/user_guide/06_acoustic_design_guidelines.html)): 4 omni PDM MEMS mics, 3.072 MHz clock, SNR > 67 dB (page also says 64), THD < 1 %, 6–10 dB headroom below overload at max speaker volume, matching not required, pair coherence < 0.1. At least two mics about 10 cm apart.
- XVF3800 mic pins: MIC_CLK pin 43 (VDDIOR), MIC_DATA0–3 pins 46/50/48/51 (VDDIOT), all 3.3 V banks, so mics run from 3.3 V. Which data pins a 4-mic build uses (one mic per pin or two per pin, L/R) is unverified.
- Seeed board ([mechanical drawing](https://files.seeedstudio.com/wiki/respeaker_xvf3800_usb/respeaker_xvf3800_2d_mechanical_drawing.pdf)): 100 mm round PCB, 1.2 mm thick; 4 mics on the underside at the corners of a 66 × 66 mm square (93.3 mm diagonal), XVF3800 in the centre. Seeed's mics: −26 dBFS, 64 dB SNR, 120 dB AOP (part number not published). **Seeed's firmware has this geometry baked in, so copy it exactly (positions and mic order) to use their binaries.**
- Est. SPL at a mic 5 cm from the CS45 at full power: about 110 dB.

| Option | Part | Source | SNR | Sens. | AOP | Supply | Stock | $ @1 |
|---|---|---|---|---|---|---|---|---|
| Alternative | Infineon IM73D122V01XTMA1 | [DigiKey India](https://www.digikey.in/en/products/detail/infineon-technologies/IM73D122V01XTMA1/16999563) | 73 dB | −26 dBFS | 122 dB | 1.62–3.6 V | 40,767 | 2.73 |
| **Chosen** | Infineon IM69D129FV01XTMA1 | [LCSC C43314439](https://www.lcsc.com/product-detail/C43314439.html) | 69 dB | −36 dBFS | 129 dB | 1.62–3.6 V | 45 | 2.92 |
| Budget | MEMSensing MSM261DDB019 | [LCSC C51928210](https://www.lcsc.com/product-detail/C51928210.html) | 66 dB | −26 dBFS | 120 dB | 1.6–3.6 V | 5,272 | 0.72 |

- IM73D122 was the step up (higher SNR, cheaper, same −26 dBFS as Seeed) but is not on LCSC; user chose the LCSC part.
- LCSC mic category (1,737 parts) filtered for PDM, SNR ≥ 63 dB; IM69D130 and IM73D122 not stocked there.
- 1 µF bypass at each mic VDD pad.

## Archived 2026-11-07: Rev 2 CM5 carrier plan (verbatim)

### Rev 2 (deferred): CM5 carrier

Agreed earlier, kept for rev 2: CM5 eMMC on the same board as the mics; boot button and UART only (CM5 flashed on a separate IO board); one analog USB 2.0 switch + slide switch routes XVF3800 USB to the USB-C port or to the CM5; schematic split into sheets. Power for rev 2 would be USB-C PD at 15 V with a 5 V / 5 A buck for the CM5.


## Archived 2026-11-07 (from AGENTS.md, verbatim)

## Component sourcing

Prices are page snapshots, excluding shipping, GST and duty.

### XMOS XVF3800

- [LCSC C20491135](https://www.lcsc.com/product-detail/C20491135.html) XVF3800-QF60B-C: 26 in stock, $23.1568 @1 (2026-11-03). DigiKey India has 2,272. JLC/DigiKey/Mouser detail archived.

### TLV320AIC3104 codec

- [LCSC C181753 TLV320AIC3104IRHBR](https://www.lcsc.com/product-detail/C181753.html): 1,695 in stock, $2.4701 @1. Line/headphone outputs only, no speaker driver; DVDD shares the 1.8 V rail. Full detail archived.

### LM48511 amp

- [LCSC C527406 LM48511SQX/NOPB](https://www.lcsc.com/category/1415.html?scene=FULL_MATCH&globalKeyword=LM48511): 1,082 in stock, $1.4243 @1. 3 W @ 8 Ω, 5.4 W @ 4 Ω (built-in boost). Full detail archived.

### MAX98357A I²S amp

- Chosen: MAX98357AEWL+T, WLP-9, [LCSC C2682619](https://www.lcsc.com/product-detail/C2682619.html), 8,708 in stock, $0.6017 @1. 3.2 W @ 4 Ω at 5 V (practical 5 V ceiling). Full detail archived.

### Speakers

- Chosen: Challenge CS45-05D13-24-1X (see Decisions in force). LCSC and DigiKey shortlists archived; LCSC fallback FUET FS44DS0450-H25-R01 (C5156352, F0 150 Hz, $3.56).

## QSPI flash (rev 1) — researched 2026-11-07

- XMOS ([device operation](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/06_device_operation.html)): minimum 2 MB, 256-byte pages, 3-byte address, 4 kB sector erase 0x20, quad read 0xEB; Quad Enable bit must be set. Example given is W25Q16JWSNIM, but that is a 1.8 V part and the QSPI pins sit on the 3.3 V IOL bank, so use the 3.3 V **JV** version. QSPI_CS_N 4.7 kΩ pull-up; QSPI_D1 straight to flash.
- Seeed USB firmware images are 0.89 MB each (factory + upgrade ≈ 1.8 MB); their recovery file `4mb_all_ff.bin` suggests a 4 MB flash on the ReSpeaker (inferred).

| Option | Part | LCSC | Stock | $ @1 |
|---|---|---|---|---|
| 2 MB (not used) | Winbond W25Q16JVSNIQ, SOIC-8 | [C2456211](https://www.lcsc.com/product-detail/C2456211.html) | 35,168 | 1.1777 |
| **Chosen** 4 MB | Winbond W25Q32JVSNIQ, SOIC-8 | [C5355146](https://www.lcsc.com/product-detail/C5355146.html) | 13,738 | 1.5161 |


## Archived 2026-11-07, second batch (from AGENTS.md, verbatim)

## Echo cancellation (AEC)

- Adapts on its own to speaker position (no calibration run). Per-product tuning (delay, gains, non-linear model) is done once per enclosure; making it default needs the XMOS source release and a rebuild. Full notes archived ([tuning guide](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/user_guide/04_tuning_the_application.html)).

## ReSpeaker XVF3800 bench test — 2026-11-05

- Reference board (USB ID 2886:001a). Voice capture judged good. **Unresolved:** it dropped off USB repeatedly with a 5 W speaker attached (kernel `-71`), and in bursts without it; cable/port not ruled out. Test clips in `respeaker-tests/`. Full notes archived.

## Archived 2026-11-10 (covers 2026-11-05 to 2026-11-07): full AGENTS.md body before the RP2350 / MAX-only rewrite (verbatim)

## What this is

- A voice front-end board built around the XMOS XVF3800, later to carry a Raspberry Pi CM5.
- **Prototype, not yet a product.** Thin distributor stock (e.g. LCSC's 26 XVF3800) is fine for now; bulk ordering is deferred to production. Do not flag low stock as a blocker.
- Goal: rev 1 schematic and schematic-backed BOM, target Fri 2026-11-06. KiCad project skeleton and libraries exist (2026-11-07); schematic not drawn yet. No purchase or vendor contact made.

## PCB folder (KiCad 10)

- `PCB/mindspark_rev1/`: project (empty schematic; PCB file is created when the board editor is first opened). Libraries are registered **in the project only**, as `${KIPRJMOD}/../libraries/...`, same pattern as the PDB and oscilloscope projects.
- `PCB/libraries/`: `Mindspark` symbol + footprint library, built by `tools/build_libraries.py` from raw easyeda2kicad imports. Details, rebuild steps and what was wrong with the imports: `PCB/libraries/README.md`. Part → symbol → footprint → LCSC map: `parts-map.json`.
- easyeda2kicad 1.0.1 lives in `~/.local/venvs/easyeda2kicad` (linked in `~/.local/bin`).
- Use `Mindspark:XVF3800-QF60B-C` with its 5-paddle footprint, never the stock single-paddle QFN-60. The mic footprint was redrawn from the Infineon datasheet (EasyEDA's was ST's pattern).
- Speaker connector: JST S2B-PH-SM4-TB, [LCSC C295747](https://www.lcsc.com/product-detail/C295747.html) (chosen 2026-11-07). Lead: PHR-2 + SPH-002T-P0.5S.
- 3.5 mm jack: SOFNG PJ-327A, [LCSC C22355751](https://www.lcsc.com/product-detail/C22355751.html) (chosen 2026-11-07), for audio path 2 (TLV320AIC3104 outputs). Pin TN is a normally-closed tip switch for plug detect (e.g. mute the speaker amp); how to use it is a schematic decision.
- Chosen 2026-11-07: buck inductor Bourns SRP4020TA-2R2M ([C719179](https://www.lcsc.com/product-detail/C719179.html)); LM48511 inductor Vishay IHLP2525CZER6R8M01 6.8 µH ([C506575](https://www.lcsc.com/product-detail/C506575.html)) and diode DFLS230LH-7 ([C2960361](https://www.lcsc.com/product-detail/C2960361.html)); JTAG header JST S7B-PH-SM4-TB ([C265453](https://www.lcsc.com/product-detail/C265453.html), xSYS2 JTAG-only signals at **1.8 V**, needs a 1.8 V XTAG). Speaker and JTAG also get parallel solder pads.
- All library parts have 3D models. Mic uses the stock InvenSense ICS-43434 model (same body); Infineon's official CAD needs a myInfineon login.

## Decisions in force

- **Rev 1 = XVF3800 breakout only** (decided 2026-11-05). The only link between the XVF3800 and a compute module is USB, so the CM5 moves to rev 2. Rev 1 is: XVF3800 + mics + audio out + power + USB-C + UI.
- ESP32 dropped. Jetson left out. CM5 (eMMC) is the planned host for rev 2.
- **Audio out: both footprints on rev 1** (decided 2026-11-05). Path 1: pin-configured I²S amp (MAX98357A-type), no code. Path 2: Seeed's TLV320AIC3104 → LM48511. Zero-ohm links select the path; populate per test. Fit path 2 if the XVF3800 firmware turns out to need its codec present.
- **Speaker power: 3–5 W, plain 5 V USB-C, no PD** (decided 2026-11-05). Echo Dot class.
- **Mics: Infineon IM69D129FV01XTMA1 ×4** (decided 2026-11-07), [LCSC C43314439](https://www.lcsc.com/product-detail/C43314439.html). −36 dBFS is 10 dB below Seeed's mics, so raise `AUDIO_MGR_MIC_GAIN` about 10 dB when running Seeed firmware.
- **Flash: Winbond W25Q32JVSNIQ, 4 MB** (decided 2026-11-07), [LCSC C5355146](https://www.lcsc.com/product-detail/C5355146.html): room for factory + upgrade images, matches Seeed's apparent 4 MB.
- **Speaker: Challenge Electronics CS45-05D13-24-1X** (decided 2026-11-07): 45 mm, 24 mm deep, 4 Ω, 5 W, F0 130 Hz, [DigiKey India](https://www.digikey.in/en/products/detail/challenge-electronics/CS45-05D13-24-1X/25602924), 279 in stock, $8.37 @1. Not ordered.

## Rev 1 blocks

| Block | Contents |
|---|---|
| Power | Plain 5 V USB-C input, no PD. Regulators for XVF3800 (3.3 V, 0.9 V, 1.8 V). Amp runs from 5 V. Must not repeat the Seeed board's USB drops under speaker load. |
| XVF3800 | Chip, QSPI flash, crystal, copied from reference. USB firmware. USB-C data goes straight to the XVF3800. |
| Mics | 4 PDM MEMS mics in the Seeed board geometry. |
| Audio out | Both paths on board, selected by zero-ohm links: MAX98357A-type I²S amp, and TLV320AIC3104 → LM48511 (as on Seeed). 3–5 W at 5 V. |
| UI | Status LEDs, mic mute switch + LED, buttons, copied from or inspired by the Seeed board. |

## Rev 2 (deferred): CM5 carrier

CM5 eMMC on the mic board, USB switch between USB-C and CM5, USB-C PD 15 V. Full plan archived.

## Reference documents — checked 2026-11-05

- **XVF3800:** [XMOS docs v3.2.1](https://www.xmos.com/documentation/XM-014888-PC/html/); [pinout page](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/04_device_pinout.html); [PDF v3.1.0](https://xmos.com/view/XVF3800-Documentation(v3_1_0).pdf). Read alongside the XU316-1024-QF60B datasheet.
  - Boot: QSPI flash (QSPI_D1 floating/to flash) or SPI-slave boot (QSPI_D1 pulled high 4.7 kΩ). QSPI_CS_N 4.7 kΩ pull-up. MCLK_INOUT (pin 14) tied to MCLK (pin 41). Mic clock 3.072 MHz. Crystal frequency not on the pinout page; check XU316 datasheet.
  - No XMOS reference schematic found on the docs site.
  - XMOS ships a **source release** (ZIP → TAR, LICENSE.rst inside); user-modifiable code in `sources/app_xvf3800`, CMake build on Linux ([build guide](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/user_guide/05_building_the_firmware.html)). Docs don't say whether the firmware sets up a DAC over I²C, or whether download needs registration. Unchecked.
- **CM5 (rev 2):** datasheet, IO board datasheet, connectors, power, USB and boot details are archived in `AGENTS.archive-001.md` (2026-11-07 section).
- **Seeed ReSpeaker XVF3800:** [wiki](https://wiki.seeedstudio.com/respeaker_xvf3800_introduction/); [GitHub firmware/control repo](https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY); [2D mechanical drawing](https://files.seeedstudio.com/wiki/respeaker_xvf3800_usb/respeaker_xvf3800_2d_mechanical_drawing.pdf). **No schematic or PCB files published.**
  - Codec TLV320AIC3104, amp LM48511, 12 × WS2812 LEDs, mute button + red mute LED, reset button, JST speaker connector (5 W speakers), 3.5 mm jack.

## Component sourcing

LCSC numbers for every rev 1 part are in `PCB/libraries/parts-map.json`. Stock and price snapshots (XVF3800, TLV320AIC3104, LM48511, MAX98357A, speakers) archived in `AGENTS.archive-001.md` (2026-11-07 section).

## Power block (rev 1) — researched 2026-11-07

XU316 datasheet (via [LCSC C6036851](https://www.lcsc.com/datasheet/C6036851.pdf)): VDD 0.855–0.945 V, active current 300 mA typ / 1,000 mA max (budget figure). VDDIO 2.97–3.63 V. USB_VDD18 up to 36 mA. Supplies must rise monotonically, within 50 ms of each other; VDDIOL/R/T must be valid before reset releases (or hold RST_N). PLL_AVDD: 1 µF + 600 Ω@100 MHz ferrite (DCR < 1 Ω). ≥ 8 × 100 nF on VDD, 100 nF per VDDIO pin, ≥ 10 µF bulk per rail. Crystal 24 MHz, 12 pF load. Bus-powered USB device needs no VBUS sense pin (rev 2 with CM5 host: check).

Power tree (agreed 2026-11-07, TI LDOs chosen):
- USB-C (Rd 5.1 kΩ on CC1/CC2) → TVS on VBUS → 5 V rail.
- 3.3 V: LDO from 5 V (~150 mA: XVF I/O, USB, mics, flash, codec).
- 1.8 V: LDO from 3.3 V (~60 mA).
- 0.9 V: buck from 5 V (up to 1 A); PLL_AVDD via ferrite + 1 µF.
- Reset: supervisor on 3.3 V drives RST_N.
- Amp: load switch with soft start from 5 V, own bulk capacitor. LEDs on 5 V with a power switch (Seeed uses X0D33).
- 5 V budget: typical about 0.6 A; worst peak about 2.4 A (amp ~1.4 A peak at 3.2 W, 12 LEDs full white ~0.6 A). Needs a 5 V / 3 A USB-C supply for full volume and LED brightness.

| Function | Part | LCSC | Stock | $ @5 |
|---|---|---|---|---|
| 0.9 V buck, 2 A | TI TLV62569DBVR | [C141836](https://www.lcsc.com/product-detail/C141836.html) | 271,590 | 0.0691 |
| 3.3 V LDO, 1 A | TI TLV75733PDBVR | [C485517](https://www.lcsc.com/product-detail/C485517.html) | 38,100 | 0.2096 |
| 1.8 V LDO, 500 mA | TI TLV75518PDBVR | [C2877863](https://www.lcsc.com/product-detail/C2877863.html) | 8,030 | 0.2063 |
| Reset supervisor | TI TPS3839G33DBZR | [C485802](https://www.lcsc.com/product-detail/C485802.html) | 1,903 | 0.4084 @1 |
| Amp load switch, 2 A | TI TPS22918DBVR | [C131941](https://www.lcsc.com/product-detail/C131941.html) | 70,620 | 0.3454 |
| USB-C receptacle | Hroparts TYPE-C-31-M-12 | [C165948](https://www.lcsc.com/product-detail/C165948.html) | 309,350 | 0.1887 |
| USB data ESD | ST USBLC6-2SC6 | [C7519](https://www.lcsc.com/product-detail/C7519.html) | 24,210 | 0.1639 |
| VBUS TVS | MDD SMF5.0A | [C193402](https://www.lcsc.com/product-detail/C193402.html) | 474,020 | 0.0285 @20 |
| PLL ferrite | Murata BLM15AG601SN1D | [C76884](https://www.lcsc.com/product-detail/C76884.html) | 903,700 | 0.0091 @100 |
| 24 MHz crystal, 12 pF | YXC X322524MOB4SI | [C70590](https://www.lcsc.com/product-detail/C70590.html) | 142,715 | 0.0956 |

- Step-up checks: TLV62585 (3 A) is $0.31 vs $0.07, so stay with TLV62569. User chose the TI LDOs (TLV75733P / TLV75518P) over the slightly cheaper AP2112K. TI's suggested PLL ferrite BKH1005LM601-T is not on LCSC; BLM15AG601SN1D meets the spec.
- Unverified: TPS3839G33 trip voltage vs the 2.97 V VDDIO minimum; mic supply voltage (depends on the mic part and its I/O bank).

## Mics (rev 1) — researched 2026-11-07

- Chosen part: see Decisions in force. 1 µF bypass at each mic VDD; mics run from 3.3 V. MIC_CLK pin 43, MIC_DATA0–3 pins 46/50/48/51; one-or-two-mics-per-pin mapping unverified.
- Copy Seeed's geometry exactly (4 mics, underside, corners of a 66 × 66 mm square on a 100 mm round board) to use their firmware. XMOS guidance, table of options and Seeed mic specs archived.

## QSPI flash (rev 1)

Chosen part: see Decisions in force. Use the 3.3 V **JV** version (QSPI pins are on the 3.3 V IOL bank); QSPI_CS_N 4.7 kΩ pull-up, QSPI_D1 straight to flash. XMOS requirements and the 2 MB/4 MB comparison archived.

## UI (rev 1) — researched 2026-11-07

- XVF3800 GPIO, standard XMOS map ([pinout](https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/04_device_pinout.html)): buttons pin 11 (X1D09, mute) and pin 32 (X1D13, action), active low with 10 kΩ pull-up; CODEC_RST_N pin 40 (X0D29); LED_R pin 56 (X0D32), LED_G pin 58 (X0D33).
- Seeed reuses these: mute button X1D09; mute LED + mic mute X0D30 (pin 54); amp enable X0D31 (pin 55, low = on); WS2812 power X0D33 (pin 58). Seeed's WS2812 data pin is not published; X0D32 (pin 56) is the likely candidate. **Confirm by continuity on the ReSpeaker** (first LED DIN to XVF3800 pin).
- WS2812 at 5 V needs ≥ 3.5 V logic high, so buffer the 3.3 V data through a 74AHCT1G125 on 5 V. Switch LED power with a second TPS22918 (already in the BOM).

| Function | Part | LCSC | Stock | $ |
|---|---|---|---|---|
| 12 × RGB LED | Worldsemi WS2812B-2020-V6 | [C52917434](https://www.lcsc.com/product-detail/C52917434.html) | 730,295 | 0.0923 @5 |
| LED data buffer | TI SN74AHCT1G125DBVR | [C7484](https://www.lcsc.com/product-detail/C7484.html) | 13,745 | 0.1009 @5 |
| Mute, action, reset buttons | XKB TS-1187A-B-A-B | [C318884](https://www.lcsc.com/product-detail/C318884.html) | 698,500 | 0.0208 @20 |
| Mute LED (red) | KENTO KT-0603R | [C2286](https://www.lcsc.com/product-detail/C2286.html) | 4,171,700 | 0.0077 @100 |
| Power LED (green) | KENTO KT-0603G | [C12624](https://www.lcsc.com/product-detail/C12624.html) | 337,050 | 0.0120 @50 |

## Echo cancellation (AEC)

Adapts on its own; per-enclosure tuning needs the XMOS source release. Notes archived (2026-11-07 section).

## ReSpeaker XVF3800 bench test — 2026-11-05

Voice capture good; **unresolved** USB drops (kernel `-71`) with a 5 W speaker. Clips in `respeaker-tests/`; details archived.

## Open questions

- Unverified: whether XVF3800 firmware (Seeed's or stock) runs normally with its expected codec absent. Decides which audio path gets fitted. Rejected for rev 1: setup MCU on a private I²C bus (second firmware); adding setup code to the XMOS source release stays an option for later.
- Firmware licence: Seeed's USB firmware is binaries only, no source or licence file. Fine for the prototype; production needs our own build or Seeed/XMOS permission.

## Next steps

- I²S amp: **MAX98357AEWL+T (WLP-9, LCSC C2682619)**, chosen 2026-11-07; board is machine-assembled. Check the 0.4 mm-pitch footprint against the fab's BGA rules (centre ball may need via-in-pad).
- Speaker chosen: see Decisions in force. PCM5102A path not pursued.
- Confirm Seeed's WS2812 data pin on the ReSpeaker (continuity from first LED DIN).
- Get the XMOS source release: needed to bake in AEC tuning and the non-linear model.
- Not yet done on the ReSpeaker: echo-cancellation test, Seeed control tool (DoA, AEC/NS toggles).

## 2026-11-10: RP2350A-era sections, replaced by the ESP32-S3 swap (copied verbatim)

### Power (rev 1)

XU316 limits ([datasheet via LCSC C6036851](https://www.lcsc.com/datasheet/C6036851.pdf)): VDD 0.855–0.945 V, 300 mA typ / 1 A max. VDDIO 2.97–3.63 V. USB_VDD18 ≤ 36 mA. Rails rise monotonically within 50 ms of each other. PLL_AVDD: 1 µF + 600 Ω@100 MHz ferrite. ≥ 8 × 100 nF on VDD, 100 nF per VDDIO pin, ≥ 10 µF bulk per rail. Bus-powered USB needs no VBUS sense.

- USB-C main and USB-C RP: Rd 5.1 kΩ on CC, SMF5.0A TVS, 10 µF + 100 nF on VBUS → TPS2121 (IN1 main, IN2 RP) → +5V (22 µF + 100 nF).
- 0.9 V buck (XVF core; PLL_AVDD via ferrite). 3.3 V buck (≈200 mA). 1.8 V LDO from 3.3 V (≈60 mA). Both bucks have EN tied to VIN, so they start together.
- RST_N: TPS3808 open drain, 10 kΩ to 1.8 V, reset button on MR, CT open (20 ms). Wired-OR with the RP2350's 2N7002 (via 0 Ω) and the XTAG.
- Amp: TPS22918 from 5 V, EN = XVF pin 40, 47 µF bulk. LED ring: second TPS22918, EN from RP2350 GPIO19, 22 µF bulk.
- 5 V budget ≈0.6 A typical, ≈2.4 A peak. On the RP port alone the RP2350 keeps the ring dim.
- **24 MHz crystal: YXC X322524MOB4SI** ([C70590](https://www.lcsc.com/product-detail/C70590.html)). 12 pF load and 50 Ω ESR per LCSC meet the XU316 spec (12 pF, ≤ 60 Ω). Fallback: TXC 7M-24.000MAAE-T ([C2450246](https://www.lcsc.com/product-detail/C2450246.html), 0 stock 2026-11-10).
- Step-up checks: TPS2116 (2.5 A) is too close to the 2.4 A peak, so TPS2121. TLV62585 (3 A) costs more, so TLV62569 stays.

### XVF3800 pin use (diagram 04)

- QSPI flash 1, 2, 3, 5, 59, 60 (CS_N 4.7 kΩ pull-up). Crystal 16/15 (1.8 V bank). USB 28/29 (90 Ω). JTAG 18/20/23/24, RST_N 21.
- Mics: CLK 43 (33R series); DATA 46 (mic 0), 50 (1), 48 (2), 51 (3). MCLK loop: PCB trace 14 → 41.
- I²S to MAX98357A: 9 DATA0, 10 LRCK, 13 BCLK.
- Buttons 11 (mute), 32 (action), active low, 10 kΩ pull-ups.
- Stock GPO (port 8C, host-controlled, PWM/flash): 40 amp EN, 54 mute LED, 56 R / 58 G / 55 B RGB status. RP2350 also reads 54/55/56/58.
- RP2350 link: 3, 5, 59, 1 through the four flash switches; 6 (SS) and 7 (MOSI) via 33 Ω for SPI-slave boot; 4.7 kΩ pull-up on pin 1 placed as DNP (fitting it selects SPI-slave boot).
- Spare: 39, 44, 45, 47, 53, XLINK 33/35/36/37. Pin 25 NC: left unconnected.

### RP2350A block (diagram 07)

- **GPIO map** (UART0, I²C1 and SPI1 per the function table):
  - Host link: 0 UART TX, 1 UART RX, 2 I²C1 SDA, 3 I²C1 SCL.
  - XVF programming: 9 XVF SPI_CS_N (slave boot); 10–13 SPI1 to the XVF flash (SCK, TX→DI, RX←DO, CSn); 15 XVF SPI_MOSI; 16 XVF reset (Q701); 18 jumper sense (PRG_EN).
  - Board: 17 mux ST, 19 LED ring enable, 20 LED data (PIO).
  - 22–25 XVF GPO taps (mute, R, G, B).
  - Spare: 4–8, 14, 21, 26 on J702 (1 × 10 with 3V3/GND); 27–29 on test pads.
- **Parts:**
  - RP2350A [C42411118](https://www.lcsc.com/product-detail/C42411118.html).
  - AOTA-B201610S3R3-101-T [C42411119](https://www.lcsc.com/product-detail/C42411119.html) (LCSC 20, JLC 1,400).
  - ABM8-272-T3 [C20625731](https://www.lcsc.com/product-detail/C20625731.html).
  - 4 × TS5A3166YZPR [C2651902](https://www.lcsc.com/product-detail/C2651902.html).
- Step-up RP2354A ([C41378174](https://www.lcsc.com/product-detail/C41378174.html), flash inside) is out of stock.
- Switch choice: four single switches instead of one quad (the '3125 has no in-stock QFN; TMUX1574RSVR had 12 in stock). Fallback with active-low OE: SN74CBTLV1G125DCKR ([C131992](https://www.lcsc.com/product-detail/C131992.html)).
- **TS5A3166 datasheet check:**
  - Off-state capacitance is 18–19 pF on each switched XVF QSPI line.
  - IN logic-high threshold is 2.0 V at 3.3 V supply.
- WS2812B ring: data through SN74AHCT1G125 on the switched 5 V rail, driven by PIO. The RP2350 must hold LED_DATA low while the ring is off.
- Follow Raspberry Pi's [Hardware design with RP2350](https://datasheets.raspberrypi.com/rp2350/hardware-design-with-rp2350.pdf) for the regulator layout and inductor orientation. Pi's RP2350A Minimal KiCad design (RP-010328-CA) was used as the reference. Erratum E9 is handled with external pull-downs; check which stepping LCSC ships.

### XVF3800 programming (diagram 08)

- **Path A, XTAG4:** JTAG header at 1.8 V; XMOS tools load a helper that writes the flash. Also the only route for live debugging. Check that the XTAG4 works at 1.8 V.
- **Path B, RP2350:**
  - Four TS5A3166 switches sit on flash CS_N, CLK, D0 and D1 (XVF pins 3, 5, 59, 1). D2/D3 are not needed: the JV-IQ has QE fixed on, so plain SPI writes work.
  - PRG_EN has a 4.7k pull-down (off by default). JP701 ties it to 3.3 V, and GPIO18 reads it.
  - Sequence: the RP2350 holds RST_N low through Q701, writes the W25Q32, reads it back, releases the lines (59/60/1 are boot straps), then releases reset.
- The image is the `.xe` converted to raw flash bytes by XMOS `xflash` (free tool); the exact option is unverified. Verify boot from an RP-written image on the first board.

# Archived 2026-11-12: "Small parts picked 2026-11-10" section (verbatim)

## Small parts picked 2026-11-10

Full list with JLC stock and price for every line: `PCB/mindspark_rev1/bom/sourcing-2026-11-10-esp32.md`. All are on JLC Basic unless marked Extended.

| Part | LCSC |
|---|---|
| 2N7002 (CJ) | [C8545](https://www.lcsc.com/product-detail/C8545.html) |
| Mic clock buffer SN74LVC1G125DBVR (TI, Extended) | [C23654](https://www.lcsc.com/product-detail/C23654.html) |
| 2×12 SMD header (HCTL PZ254-2-12-S, Extended, 2026-11-11) + loose I²C shunts | [C3294470](https://www.lcsc.com/product-detail/C3294470.html) + [C100114](https://www.lcsc.com/product-detail/C100114.html) |
| PROG slide switch SHOU HAN MSK12C02 (Extended, 2026-11-11) | [C431540](https://www.lcsc.com/product-detail/C431540.html) |
| 0402 resistors, UNI-ROYAL 0402WGF | 0R [C17168](https://www.lcsc.com/product-detail/C17168.html), 33R [C25105](https://www.lcsc.com/product-detail/C25105.html), 100R [C25076](https://www.lcsc.com/product-detail/C25076.html), 330R [C25104](https://www.lcsc.com/product-detail/C25104.html), 1k [C11702](https://www.lcsc.com/product-detail/C11702.html), 2.2k [C25879](https://www.lcsc.com/product-detail/C25879.html), 4.7k [C25900](https://www.lcsc.com/product-detail/C25900.html), 5.1k [C25905](https://www.lcsc.com/product-detail/C25905.html), 10k [C25744](https://www.lcsc.com/product-detail/C25744.html), 12k [C25752](https://www.lcsc.com/product-detail/C25752.html), 22k [C25768](https://www.lcsc.com/product-detail/C25768.html), 33k [C25779](https://www.lcsc.com/product-detail/C25779.html), 51k [C25794](https://www.lcsc.com/product-detail/C25794.html), 100k [C25741](https://www.lcsc.com/product-detail/C25741.html), 1M [C26083](https://www.lcsc.com/product-detail/C26083.html) |
| Extended resistors (kept as specified) | 27R [C25100](https://www.lcsc.com/product-detail/C25100.html) (ESP32 USB), 680R [C25130](https://www.lcsc.com/product-detail/C25130.html) (XMOS Rd) |
| Capacitors | 100nF 16V X7R [C1525](https://www.lcsc.com/product-detail/C1525.html), 10µF 10V 0603 [C19702](https://www.lcsc.com/product-detail/C19702.html), 1µF 25V [C52923](https://www.lcsc.com/product-detail/C52923.html), 22µF 25V 0805 [C45783](https://www.lcsc.com/product-detail/C45783.html), 47µF 10V 1206 [C96123](https://www.lcsc.com/product-detail/C96123.html), 1nF [C1523](https://www.lcsc.com/product-detail/C1523.html), 15pF [C1548](https://www.lcsc.com/product-detail/C1548.html), 22pF [C1555](https://www.lcsc.com/product-detail/C1555.html) |

- One step up was applied where the price was the same: all 100 nF are 16 V X7R, 1 µF are 25 V, and 22 µF are 25 V.
- Parts cost is ≈ $53 per board at JLC single-piece prices, of which the XVF3800 is $23 and the ESP32 module $5.

## 2026-11-12: moved out of AGENTS.md (verbatim) to keep it under 4,000 words

- **JLC quote 2026-11-10** (screenshots in `docs/report/jlc_quote_2026-11-10/`):
  - The bare-PCB quote used the robot controller board (4-layer, 88.9 mm) as a reference PCB, on purpose: $29.05 for 5, with epoxy-filled vias.
  - Components: $90.54 for 2 boards, $212.71 for 5. The '54/55 of 60 lines' is JLC merging BOM lines that share a part (e.g. six buttons with different Value labels); nothing is missing.
  - Build: 2–3 day build costs +$66.20. Shipping: UPS $9.76 (5–7 business days) or DHL $25.31 (2–5 business days).
  - Not yet quoted: assembly fees. Customs was up to ₹9,000 (≈$100) on the user's last PCB import.

- Status 2026-11-12: **rev 1 schematic regenerated with no ball-grid parts**: MAX98357AETE+T (TQFN-16) and 4 × TS5A3166DBVR (SOT-23-5) replace the WLP-9 amp and the DSBGA-5 switches. This sits on top of the 2026-11-11 side buttons / PROG switch / 2×12 SMD header and the 2026-11-10 ESP32-S3 swap.
  - The user's 2026-11-12 02:28 KiCad save of all sheets held two hand edits, now in the generator, so `--force` kept them: ESP32 footprint → Espressif's own `ESP32-S3-WROOM-1U` (copied into the Mindspark library the same day); JTAG parallel pads TP301–TP307 → 1.0 × 1.0 mm. Checked by regenerating the old version and comparing; nothing else differed.
  - Earlier user edits in the generator: M2 mounting holes (2026-11-11).
  - Nine A4 sheets, ERC 0 errors / 0 warnings, KiCad netlist matches the intended connections, tidy and floating checks pass.
  - Library rebuilt; BOM regenerated from the schematic (59 lines, 189 parts), LCSC number on every line. Schematic PDF re-exported (`PCB/mindspark_rev1/mindspark_rev1_schematic.pdf`).
  - No purchase and no vendor contact.

- **Deviations from the agreed sheet plan.**
  - The single-unit XVF3800 symbol had to sit on one sheet, so sheet 3 holds the chip and sheet 4 its peripherals.
  - The XVF spare-pin pads sit on sheet 4 so that sheet 3 stays on A4.

- **Tidy** (kicad-schematic-tidy):
  - 100 mil leads and 300 mil passive pitch.
  - Simple support circuits are wired; labels remain only at dense IC pins and where a part fans out (each case is listed in `verification/tidy-exceptions.json`).
  - Box padding is measured on the native plot, with exact 200 mil gaps.
  - Deviation: tall-IC sheets use bottom-left packing instead of strict rows, so they stay on A4; group order on `audio` was chosen so it fits. Details: `verification/tidy-record.md`.

## UI parts

| Function | Part | LCSC | Stock 2026-11-10 | $ |
|---|---|---|---|---|
| 12 × ring RGB LED + 1 × user RGB LED | Worldsemi WS2812B-2020-V6 | [C52917434](https://www.lcsc.com/product-detail/C52917434.html) | 860,095 | 0.0923 @5 |
| LED data buffer ×2 (ring, user LED) | TI SN74AHCT1G125DBVR | [C7484](https://www.lcsc.com/product-detail/C7484.html) | 4,830 | 0.1009 @5 |
| Top buttons ×3 (XVF reset, ESP32 EN, BOOT) | XKB TS-1187A-B-A-B | [C318884](https://www.lcsc.com/product-detail/C318884.html) | 653,600 | 0.0208 @20 |
| Side buttons ×3 (mute, action, user; JLC stock 2026-11-11) | SHOU HAN TS24CA | [C393942](https://www.lcsc.com/product-detail/C393942.html) | 407,453 | 0.0254 |
| Mute LED (red, ESP32-driven) | KENTO KT-0603R | [C2286](https://www.lcsc.com/product-detail/C2286.html) | 3,923,900 | 0.0077 @100 |
| Power LED (green, Extended) | KENTO KT-0603G | [C12624](https://www.lcsc.com/product-detail/C12624.html) | 318,050 | 0.0120 @50 |
| XVF status LED (RGB part, red/green used) | TOGIALED TJ-S1615CY6TGLCCSRGB-A5 | [C601684](https://www.lcsc.com/product-detail/C601684.html) | 8,890 | 0.0963 @5 |


## Firmware facts (checked 2026-11-09/10)

- XVF3800 source release ("Source Code and Tools" v3.2.1 on the [developer page](https://www.xmos.com/develop/xvf3800)) needs an XMOS account with a corporate email **and** a purchase of XK-VOICE-SQ66 or XVF3800 silicon through an XMOS distributor. Not pursued, since the firmware stays stock. Seeed's board serial must not be used for the form.
- Prebuilt images come in `-lin` (linear) and `-sqr` (square/rectangular) mic builds ([list of applications](https://www.xmos.com/documentation/XM-014888-PC/html/doc/user_guide/list_of_applications.html)). USB build: `application_xvf3800_ua-io48-sqr.xe`.
- Voice DSP is precompiled even in the source release; licence text unconfirmed.
- USB VID: XMOS's 0x20B1 is fine for prototypes; production needs a PID from XMOS (or our own VID).

## 2026-11-12 (third entry): pointer sections moved out of AGENTS.md (verbatim)

### UI parts

Table of the UI parts (WS2812B-2020, AHCT buffers, TS-1187A, TS24CA, 0603 LEDs, TOGIALED RGB) with LCSC links and 2026-11-10 stock: archive (2026-11-12 entry) and the `bom/sourcing-*.md` files.

### Firmware facts

Stock XMOS USB firmware `application_xvf3800_ua-io48-sqr.xe`; source release needs an XMOS corporate account plus a distributor purchase (not pursued); XMOS VID 0x20B1 fine for prototypes. Details in the archive (2026-11-12 entry).

## 2026-11-12 (fourth entry): moved out of AGENTS.md (verbatim) after the second placement tidy

## PCB placement (rules from the user, applied 2026-11-12 by `tools/place_tidy.py`)

- **Board:** 74 × 74 mm (grown from 70 so the mic ports sit 4 mm in), centre (146.558, 98.679). **4 layers**, JLC 1.6 mm stackup copied from the controller board: In1 GND, In2 power. Copper-to-edge rule set to JLC's 0.3 mm (was the 0.5 mm template default).
- **Edges:**
  - **USB-C ×2:** centred on the left/right edges, origin 3.015 mm inside, as on the controller board.
  - **JSTs:** origin 5.67 mm inside the top edge. J301 sits where equal gaps between the top mounting holes put it. **J501 is shifted 1.6 mm right (x 135.0)** to clear the LED ring (user's choice; the ring has since shrunk to 27.2 mm). The amp U503 and TP501/TP502 move with J501 as one block, with the test points symmetric about it. TP501/TP502 are 1.0 mm top-side SMD pads (user's edit).
  - **Buttons, switches and LEDs:** equal courtyard gaps per half-edge, from the mounting-hole line to the USB.
    - Left: PROG, RESET / BOOT, EN, user LED.
    - Right: MUTE, mute LED, ACTION / USER, status LED, power LED.
  - **Against the edge:** flush, copper ≥ 0.3 mm in. Stems out: PROG 1.18 mm, TS24CA only **0.31 mm** (front anchor pads reach 0.39 mm past the body).
- **Mounting holes:** 10 mm in from both edges.
- **J701:** centred on the bottom edge.
- **Test pads:** two bottom-side rows 1.5 mm in from the top and bottom edges, at equal gaps between the hole pads.
- **Mics:** **top side**, ports opening on the LED side (user); turned 45°, port facing the corner; sound ports measured exactly on the 66 mm square. Mic-to-DATA corners unchanged (XMOS order turned 180°).
- **Centred:** XVF3800 (bottom) and the ESP32 module body (top) on the board centre. The clock buffer U501 is left where the user put it.
- **Regulators:** U203/U202/U201 in a column (0.5 mm gaps, centred on the board's y), 0.5 mm left of the ESP32 at its pin-free IPEX end, toward J102 (user: away from the module pins); inductors 6.45 mm further left.
- **LED ring:** bottom side, 12 LEDs at clock positions, turned to follow the circle, radius **27.2 mm** (was 33.0): no LED under a USB-C (user), so the 3/9 o'clock LEDs (D801/D807) are limited by the USB-C courtyards. The amp U503 is on the top side (user's edit).
- **DRC after the tidy:** no new errors (the old ones remain: off-board TS5A3166 stack, mic pad clearance, switch-peg annulus); new warnings are silkscreen only.

## Small parts picked 2026-11-10

Every line (2N7002, mic clock buffer, header/shunts, PROG switch, 0402 resistors, capacitors) with LCSC link, JLC stock and price: `PCB/mindspark_rev1/bom/sourcing-2026-11-10-esp32.md`, `-11-11.md` and `-11-12.md`. The full table is in `AGENTS.archive-001.md`. Passives are JLC Basic, with one step up where the price was the same (100 nF 16 V X7R, 1 µF 25 V, 22 µF 25 V). Parts cost ≈ $53 per board at JLC single-piece prices (XVF3800 $23, ESP32 module $5); the 2026-11-12 package swap changed it by about −$0.17.



## Archived 2026-11-18 (from AGENTS.md)

### PCB placement: checks 2026-11-12

- **Checks 2026-11-12:**
  - No overlaps, pads included.
  - DRC: same errors as before, all inside footprints (mic pad clearance, switch-peg annulus).
  - Schematic parity: clean.
  - The user's trial tracks were removed (they're in the `pre-tidy2` backup).

### Reference documents: rev 2 and ReSpeaker lines

- **Rev 2 (deferred):** CM5 eMMC carrier, USB switch, USB-C PD 15 V. Plan and CM5 references archived.
- **ReSpeaker bench test 2026-11-05:** voice capture good; USB drops (kernel `-71`) with a 5 W speaker unresolved. Clips in `respeaker-tests/`.

### Power, schematic and reference lines

- **Deviations from the sheet plan:** XVF3800 chip on sheet 3, its peripherals and spare-pin pads on sheet 4 (A4 fit).
- Step-up checks: TPS2116 (2.5 A) is too close to the peak, so TPS2121. TLV62585 (3 A) costs more, so TLV62569 stays.
- **XK-VOICE-SQ66** (XMOS reference board JGB0084 1V1 C): files in `incoming/xk_voice_sq66/` (schematic `JGB0084-SCHEMATIC-1V1-C.PDF`; mic positions in `JGB0084-PCBA-1V1-C/BOM/JGB0084-XY-1V1-C.xls`). It uses a 6-mic board with a 74LVC257 linear/square mux, TLV320DAC3101 + headphone jack, LDOs for 1.8/3.3 V, an RC reset and a 20-pin FTSH debug header.

## Archived 2026-11-18, second entry (from AGENTS.md)

- **JLC quote 2026-11-10:** bare PCB $29.05 for 5 (controller board as reference), components $90.54 for 2 / $212.71 for 5; details and screenshots in the archive and `docs/report/jlc_quote_2026-11-10/`.
- **Renders:** `verification/placement-2026-11-12-{top,bot}.png` (KiCad) and `-plan-{top,bot}.png` (`tools/view_placement.py`: pads coloured by net, refs).

## Archived 2026-11-18, third entry (from AGENTS.md)

- **Symbol compaction** (tidy Step 0, Mindspark library only): IM69D129, TPS22918, MAX98357A, TS5A3166 and TPS2121 were redrawn (TPS2121 so its dividers wire straight to their pins); the XVF3800 body was widened. Pins and types are unchanged. PLL_AVDD is a power symbol.
