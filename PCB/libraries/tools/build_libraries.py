#!/usr/bin/env python3
"""
Build the curated Mindspark KiCad library from the raw easyeda2kicad imports.

Inputs  (never modified):
  ../incoming/easyeda/easyeda_raw.kicad_sym / .pretty / .3dshapes   (easyeda2kicad output)
  /usr/share/kicad/symbols/*.kicad_sym                                (stock KiCad 10 symbols)
Outputs (regenerated every run):
  ../symbols/Mindspark.kicad_sym
  ../footprints/Mindspark.pretty/*.kicad_mod
  ../3dmodels/*.step

Every pin map below was checked against the manufacturer datasheet (2026-11-07; new parts 2026-11-10)
(see ../README.md for which document and which revision). Run with: python3 -I build_libraries.py
After running, upgrade both libraries to the KiCad 10 format with kicad-cli (see README).
"""
import re
import shutil
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent          # PCB/libraries
RAW = LIB / "incoming" / "easyeda"
STOCK = Path("/usr/share/kicad/symbols")
OUT_SYM = LIB / "symbols" / "Mindspark.kicad_sym"
OUT_FP = LIB / "footprints" / "Mindspark.pretty"
OUT_3D = LIB / "3dmodels"

# 3D model paths are stored relative to the project folder (PCB/mindspark_rev1),
# matching how the project library tables point at ../libraries.
MODEL_DIR = "${KIPRJMOD}/../libraries/3dmodels"


# --------------------------------------------------------------------------
# Small S-expression helpers (text based, enough for KiCad library files)
# --------------------------------------------------------------------------
def find_block(text, start):
    """Return the end index (exclusive) of the balanced '(...)' block starting at text[start]."""
    depth, i, in_str = 0, start, False
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError("unbalanced block")


def get_symbol(text, name):
    """Extract one top-level (symbol "name" ...) block from a .kicad_sym file."""
    m = re.search(r'\(symbol\s+"%s"' % re.escape(name), text)
    if not m:
        raise KeyError(name)
    return text[m.start():find_block(text, m.start())]


def set_property(block, key, value):
    """Replace the value of (property "key" "...") or add it (hidden) if missing."""
    pat = re.compile(r'(\(property\s+"%s"\s+")([^"]*)(")' % re.escape(key))
    if pat.search(block):
        return pat.sub(lambda m: m.group(1) + value + m.group(3), block, count=1)
    # Add a hidden property just after the last existing property.
    last = list(re.finditer(r'\(property\s+"', block))[-1]
    end = find_block(block, last.start())
    new = ('\n\t\t(property "%s" "%s"\n\t\t\t(at 0 0 0)\n\t\t\t(effects (font (size 1.27 1.27)) (hide yes))\n\t\t)'
           % (key, value))
    return block[:end] + new + block[end:]


def drop_property(block, key):
    m = re.search(r'\(property\s+"%s"' % re.escape(key), block)
    if not m:
        return block
    return block[:m.start()] + block[find_block(block, m.start()):]


def rename_symbol(block, old, new):
    """Rename a symbol and its unit sub-symbols (old_0_1 -> new_0_1, ...)."""
    block = block.replace('(symbol "%s"' % old, '(symbol "%s"' % new, 1)
    return re.sub(r'\(symbol\s+"%s_(\d+_\d+)"' % re.escape(old),
                  lambda m: '(symbol "%s_%s"' % (new, m.group(1)), block)


def edit_pins(block, pinmap):
    """pinmap: {number: (new_name or None, electrical_type)}. Every pin must be listed."""
    seen = set()

    def fix(m):
        pin = block_text = m.group(0)
        num = re.search(r'\(number\s+"([^"]*)"', pin).group(1)
        if num not in pinmap:
            raise KeyError("pin %s missing from map" % num)
        seen.add(num)
        name, etype = pinmap[num]
        pin = re.sub(r'^\(pin\s+\w+', '(pin ' + etype, pin)
        if name is not None:
            pin = re.sub(r'(\(name\s+")[^"]*(")', lambda n: n.group(1) + name + n.group(2), pin, count=1)
        return pin

    out, i = [], 0
    for m in re.finditer(r'\(pin\s+\w+\s+\w+', block):
        if m.start() < i:
            continue
        end = find_block(block, m.start())
        out.append(block[i:m.start()])
        out.append(fix(re.match(r'[\s\S]*', block[m.start():end])))
        i = end
    out.append(block[i:])
    missing = set(pinmap) - seen
    if missing:
        raise KeyError("map lists pins not in symbol: %s" % sorted(missing))
    return "".join(out)


# --------------------------------------------------------------------------
# Pin maps (number -> (name, KiCad electrical type)); names None = keep import name
# --------------------------------------------------------------------------
PWR, IN, OUT, BI, PAS, NC, TRI, POUT = ("power_in", "input", "output", "bidirectional",
                                        "passive", "no_connect", "tri_state", "power_out")

# XVF3800: XMOS "Device Pinout" table, docs v3.2.1. Names are SIGNAL/PORT so the
# XMOS function and the raw xcore port are both visible (Seeed re-uses some ports).
XVF_SIGNALS = {
    "1": "QSPI_D1/X0D05", "2": "QSPI_D3/X0D07", "3": "QSPI_CS_N/X0D01", "5": "QSPI_CLK/X0D10",
    "6": "SPI_CS_N/X0D00", "7": "SPI_MOSI/X0D11", "9": "I2S_DATA0/X1D00", "10": "I2S_LRCK/X1D01",
    "11": "P_BUTTON_0/X1D09", "13": "I2S_BCLK/X1D10", "14": "MCLK_INOUT/X1D11",
    "32": "P_BUTTON_1/X1D13", "33": "XL_DN1/X1D16", "35": "XL_DN0/X1D17", "36": "XL_UP0/X1D18",
    "37": "XL_UP1/X1D19", "39": "I2S_DATA1/X1D22", "40": "CODEC_RST_N/X0D29", "41": "MCLK/X0D35",
    "43": "MIC_CLK/X0D36", "44": "I2C_SCL/X0D37", "45": "I2C_SDA/X0D38", "46": "MIC_DATA0/X0D40",
    "47": "SPI_MISO/X0D39", "48": "MIC_DATA2/X0D42", "50": "MIC_DATA1/X0D41", "51": "MIC_DATA3/X0D43",
    "53": "I2S_DATA2/X1D34", "54": "SQ_nLIN/X0D30", "55": "INT_N/X0D31", "56": "LED_R/X0D32",
    "58": "LED_G/X0D33", "59": "QSPI_D0/X0D04", "60": "QSPI_D2/X0D06",
}
XVF_PINS = {n: (s, BI) for n, s in XVF_SIGNALS.items()}
XVF_PINS.update({n: ("VDD", PWR) for n in ["4", "12", "19", "27", "34", "42", "49", "57",
                                          "61", "62", "63", "64"]})   # 61-64 are VDD paddles
XVF_PINS.update({
    "8": ("VDDIOL", PWR), "38": ("VDDIOR", PWR), "52": ("VDDIOT", PWR),
    "17": ("VDDIOB18", PWR), "26": ("VDDIOB18", PWR), "22": ("PLL_AVDD", PWR),
    "30": ("USB_VDD33A", PWR), "31": ("USB_VDD18A", PWR),
    "28": ("USB_DM", BI), "29": ("USB_DP", BI),
    "15": ("XOUT", OUT), "16": ("XIN", IN), "21": ("RST_N", IN),
    "18": ("TDI", IN), "20": ("TDO", OUT), "23": ("TMS", IN), "24": ("TCK", IN),
    "25": ("NC", NC), "65": ("GND", PWR),
})

# TPS22918: TI datasheet pin functions table (DBV).
TPS_PINS = {"1": ("VIN", PWR), "2": ("GND", PWR), "3": ("ON", IN),
            "4": ("CT", PAS), "5": ("QOD", PAS), "6": ("VOUT", POUT)}

# MAX98357AETE+T, TQFN-16 (2026-11-12, replaces the WLP-9 MAX98357AEWL+T so nothing on the
# board is a ball-grid part). ADI datasheet p.15 pin description, TQFN column: 1 DIN, 2 GAIN_SLOT,
# 3/11/15 GND, 4 SD_MODE, 5/6/12/13 N.C., 7/8 VDD, 9 OUTP, 10 OUTN, 14 LRCLK, 16 BCLK, EP.
# The stock Audio:MAX98357A symbol has exactly these numbers. EP is "not internally connected;
# connect to a solid ground plane", so it becomes a hidden GND pin stacked on pin 3.
MAX_PINS = {"1": ("DIN", IN), "2": ("GAIN_SLOT", IN), "3": ("GND", PWR), "4": ("~{SD_MODE}", IN),
            "5": ("NC", NC), "6": ("NC", NC), "7": ("VDD", PWR), "8": ("VDD", PAS),
            "9": ("OUTP", OUT), "10": ("OUTN", OUT), "11": ("GND", PAS), "12": ("NC", NC),
            "13": ("NC", NC), "14": ("LRCLK", IN), "15": ("GND", PAS), "16": ("BCLK", IN),
            "17": ("GND", PAS)}

# IM69D129FV01: Infineon datasheet v1.0 (2025-02-21), Table 8.
MIC_PINS = {"1": ("DATA", TRI), "2": ("SELECT", IN), "3": ("GND", PWR),
            "4": ("CLK", IN), "5": ("VDD", PWR)}

# TS5A3166DBVR, SOT-23-5 (2026-11-12, replaces the DSBGA-5 TS5A3166YZPR): TI SCDS188D Pin
# Functions table, DBV column: 1 NO, 2 COM, 3 GND, 4 IN (high = closed), 5 V+. The stock
# Analog_Switch:TS5A3166DBVR symbol has the same numbers but leaves 1, 2 and 4 unnamed.
TS5_PINS = {"1": ("NO", PAS), "2": ("COM", PAS), "3": ("GND", PWR),
            "4": ("IN", IN), "5": ("V+", PWR)}

# TOGIALED TJ-S1615CY6TGLCCSRGB-A5 (datasheet p.2): pin 1 common cathode, 2 blue anode,
# 3 green anode, 4 red anode.
RGB_PINS = {"1": ("K", PAS), "2": ("BA", PAS), "3": ("GA", PAS), "4": ("RA", PAS)}

# TPS3808 DBV: TI datasheet Table 5-1. RESET is open drain (wired-OR with the ESP32's
# 2N7002 and the XTAG), so it is typed open_collector instead of the stock "output".
TPS3808_PINS = {"1": ("~{RESET}", "open_collector"), "2": ("GND", PWR), "3": ("~{MR}", IN),
                "4": ("CT", IN), "5": ("SENSE", IN), "6": ("VDD", PWR)}

# TPS2121RUXR: TI SLVSEA3F Pin Functions table (VQFN-HR column). ST is open drain
# (needs an external 6-20 kOhm pull-up, Recommended Operating Conditions).
TPS2121_PINS = {"7": ("IN1", PWR), "2": ("IN2", PWR), "1": ("OUT", POUT), "8": ("OUT", POUT),
                "9": ("ST", "open_collector"), "10": ("ILIM", PAS), "11": ("SS", PAS),
                "12": ("GND", PWR), "6": ("PR1", IN), "5": ("OV1", IN), "4": ("OV2", IN),
                "3": ("CP2", IN)}


# --------------------------------------------------------------------------
# Symbol list: (source, source name, new name, pin map, properties)
#   source "raw"      = easyeda2kicad output, "ti" = TI/Ultra Librarian download,
#   "stock:<lib>"     = KiCad 10 built-in (inheritance is flattened, see flatten()).
# --------------------------------------------------------------------------
SYMBOLS = [
    ("raw", "XVF3800-QF60B-C", "XVF3800-QF60B-C", XVF_PINS, {
        "Footprint": "Mindspark:XMOS_QFN-60-5EP_7x7mm_P0.4mm",
        "Datasheet": "https://www.xmos.com/documentation/XM-014888-PC/html/modules/fwk_xvf/doc/datasheet/04_device_pinout.html",
        "Description": "XMOS XVF3800 voice processor, QFN-60 with 5 paddles (61-64 VDD 0.9 V, 65 GND)",
        "Manufacturer": "XMOS", "LCSC Part": "C20491135"}),
    ("raw", "TPS22918DBVR", "TPS22918DBVR", TPS_PINS, {
        "Footprint": "Mindspark:SOT-23-6",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/tps22918.pdf",
        "Description": "5.5 V, 2 A load switch with adjustable rise time and quick output discharge",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C131941"}),
    ("stock:Audio", "MAX98357A", "MAX98357AETE+T", MAX_PINS, {
        "Footprint": "Mindspark:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
        "Datasheet": "https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf",
        "Description": "I2S class-D mono amplifier, 3.2 W into 4 ohm, TQFN-16 3x3 mm (T1633-4), EP to GND",
        "Manufacturer": "Analog Devices (Maxim)", "LCSC Part": "C910544"}),
    ("raw", "IM69D129FV01XTMA1", "IM69D129FV01XTMA1", MIC_PINS, {
        "Footprint": "Mindspark:Infineon_IM69D129FV01_LGA-5_3.5x2.65mm",
        "Datasheet": "https://www.infineon.com/assets/row/public/documents/24/49/infineon-im69d129f-datasheet-en.pdf",
        "Description": "Infineon XENSIV PDM MEMS microphone, -36 dBFS, bottom port",
        "Manufacturer": "Infineon", "LCSC Part": "C43314439"}),
    ("stock:Analog_Switch", "TS5A3166DBVR", "TS5A3166DBVR", TS5_PINS, {
        "Footprint": "Mindspark:SOT-23-5",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/ts5a3166.pdf",
        "Description": "0.9 ohm SPST analog switch, normally open, IN high = closed, SOT-23-5 (DBV)",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C353035"}),
    ("raw", "TJ-S1615CY6TGLCCSRGB-A5", "TJ-S1615CY6TGLCCSRGB-A5", RGB_PINS, {
        "Value": "TJ-S1615CY6TGLCCSRGB-A5",
        "Footprint": "Mindspark:LED_RGB_TOGIALED_1615_1.6x1.5mm",
        "Datasheet": "https://www.lcsc.com/datasheet/C601684.pdf",
        "Description": "RGB LED 1.6 x 1.5 mm, common cathode (pin 1)",
        "Manufacturer": "TOGIALED", "LCSC Part": "C601684"}),
    ("ti", "TPS2121RUXR", "TPS2121RUXR", TPS2121_PINS, {
        "Footprint": "Mindspark:TI_RUX0012A_VQFN-HR-12_2x2.5mm",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/tps2121.pdf",
        "Description": "2.8-22 V, 4.5 A, 56 mohm power mux with priority and seamless switchover, VQFN-HR-12",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C485916"}),
    # Stock symbols copied to fix the footprint and add the LCSC number.
    # ESP32-S3-WROOM-1U: the stock WROOM-1 symbol has the same 41 pins as the 1U (IPEX)
    # module (Espressif datasheet v1.x, pin definitions table); only the footprint differs.
    ("stock:RF_Module", "ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1U-N16R8", None, {
        "Footprint": "Mindspark:ESP32-S3-WROOM-1U",
        "Datasheet": "https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf",
        "Description": "ESP32-S3 module, 16 MB flash, 8 MB octal PSRAM (GPIO35-37 used), IPEX antenna connector",
        "ki_keywords": "RF Radio BT ESP ESP32-S3 Espressif IPEX U.FL",
        "Manufacturer": "Espressif", "LCSC Part": "C3013946"}),
    ("stock:Regulator_Switching", "TLV62569DBV", "TLV62569DBVR", None, {
        "Footprint": "Mindspark:SOT-23-5",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C141836"}),
    ("stock:Regulator_Linear", "TLV75518PDBV", "TLV75518PDBVR", None, {
        "Footprint": "Mindspark:SOT-23-5",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C2877863"}),
    ("stock:Power_Supervisor", "TPS3808DBV", "TPS3808G33DBVR", TPS3808_PINS, {
        "Footprint": "Mindspark:SOT-23-6",
        "Description": "Supervisor, 3.3 V nominal (3.07 V trip), open-drain RESET, manual reset, CT delay",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C43698"}),
    ("stock:Power_Protection", "TPD4E05U06DQA", "TPD4E05U06DQAR", None, {
        "Footprint": "Mindspark:USON-10_2.5x1.0mm_P0.5mm",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf",
        "Description": "4-channel 0.5 pF ESD protection for USB 2.0 D+/D- and CC, USON-10",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C138714"}),
    # Unidirectional TVS: the stock D_TVS is the bidirectional symbol (A1/A2), so the
    # Zener graphic (K = pin 1 = D_SMF cathode pad) is used.
    ("stock:Device", "D_Zener", "SMF5.0A", None, {
        "Footprint": "Mindspark:D_SMF",
        "Datasheet": "https://www.lcsc.com/datasheet/C193402.pdf",
        "Description": "200 W unidirectional TVS, 5.0 V standoff, SMF (VBUS clamp)",
        "Manufacturer": "MDD", "LCSC Part": "C193402"}),
    ("stock:Device", "Crystal_GND24", "X322524MOB4SI", None, {
        "Value": "24MHz",
        "Footprint": "Mindspark:Crystal_SMD_3225-4Pin_3.2x2.5mm",
        "Datasheet": "https://www.lcsc.com/datasheet/C70590.pdf",
        "Description": "24 MHz crystal, 12 pF load, +/-10 ppm, 50 ohm ESR, 3225 (XVF3800)",
        "Manufacturer": "YXC", "MPN": "X322524MOB4SI", "LCSC Part": "C70590"}),
    ("stock:Device", "FerriteBead_Small", "BLM15AG601SN1D", None, {
        "Value": "600R@100MHz",
        "Footprint": "Mindspark:L_0402_1005Metric",
        "Datasheet": "https://www.murata.com/en-us/products/productdata/8796738650142/ENFA0003.pdf",
        "Description": "Ferrite bead 600 ohm at 100 MHz, 300 mA, 0402",
        "Manufacturer": "Murata", "MPN": "BLM15AG601SN1D", "LCSC Part": "C76884"}),
    ("stock:Memory_Flash", "W25Q32JVZP", "W25Q32JVUUIQ", None, {
        "Footprint": "Mindspark:Winbond_USON-8-2EP_3x4mm_P0.8mm_EP0.2x0.8mm",
        "Datasheet": "https://www.winbond.com/hq/product/code-storage-flash-memory/serial-nor-flash/?__locale=en&partNo=W25Q32JV",
        "Description": "32 Mbit (4 MB) 3.3 V quad SPI flash, USON-8 4x3 mm (UU). Centre pads unconnected inside; leave floating",
        "Manufacturer": "Winbond", "LCSC Part": "C2999380"}),
    ("stock:Connector_Generic_MountingPin", "Conn_01x07_MountingPin", "S7B-PH-SM4-TB", None, {
        "Value": "S7B-PH-SM4-TB(LF)(SN)",
        "Footprint": "Mindspark:JST_PH_S7B-PH-SM4-TB_1x07-1MP_P2.00mm_Horizontal",
        "Datasheet": "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
        "Description": "JST PH 7-pin SMD side-entry header for XVF3800 JTAG (xSYS2 JTAG-only signals: "
                       "VREF 1.8 V, TMS, TCK, TDO, TDI, RST_N, GND). Mates with PHR-7 (C157951) + SPH-002T-P0.5S",
        "Manufacturer": "JST", "LCSC Part": "C265453"}),
    ("stock:Device", "L", "SRP4020TA-2R2M", None, {
        "Footprint": "Mindspark:L_Bourns_SRP4020TA",
        "Datasheet": "https://www.bourns.com/docs/Product-Datasheets/SRP4020TA.pdf",
        "Description": "2.2 uH +/-20 %, 4.0 A Irms, 6.0 A Isat, 61 mohm max, shielded, 4.5x4.1 mm (TLV62569 bucks)",
        "Manufacturer": "Bourns", "LCSC Part": "C719179"}),
    ("stock:LED", "WS2812B-2020", "WS2812B-2020", None, {
        "Value": "WS2812B-2020-V6",
        "Footprint": "Mindspark:LED_WS2812B-2020_PLCC4_2.0x2.0mm",
        "Manufacturer": "Worldsemi", "LCSC Part": "C52917434"}),
    ("stock:Switch", "SW_Push", "TS-1187A-B-A-B", None, {
        "Footprint": "Mindspark:SW_Push_1P1T_XKB_TS-1187A",
        "Datasheet": "https://www.lcsc.com/datasheet/C318884.pdf",
        "Description": "5.1 x 5.1 mm SMD tact switch, 1.5 mm actuator, top-pressed (XVF reset, ESP32 EN, BOOT)",
        "Manufacturer": "XKB Connection", "LCSC Part": "C318884"}),
    # Side-pressed buttons (2026-11-11): mute, action and user sit on the board edge. JLC has no
    # side-pressed tact switch in Basic; TS24CA (Extended) has the most stock. Pins 1/2 are the
    # contacts; the footprint's pads 3/4 are the metal hold-down tabs (no symbol pin, no net).
    ("stock:Switch", "SW_Push", "TS24CA", None, {
        "Footprint": "Mindspark:SW_SHOUHAN_TS24CA_SideActuated",
        "Datasheet": "https://www.lcsc.com/datasheet/C393942.pdf",
        "Description": "4.7 x 1.9 mm SMD tact switch, side-pressed (right angle), 160 gf (mute, action, user)",
        "Manufacturer": "SHOU HAN", "LCSC Part": "C393942"}),
    # PROG slide switch (2026-11-11, replaces the JP701 jumper). Stock SW_SPDT: pin 2 (B) is the
    # common, as on the MSK12C02 (datasheet: pin 2 sits 1.5 mm from pin 3 and 3 mm from pin 1).
    # The footprint's four pads "4" are the shell tabs (no symbol pin, no net).
    ("stock:Switch", "SW_SPDT", "MSK12C02", None, {
        "Footprint": "Mindspark:SW_SHOUHAN_MSK12C02_SideActuated",
        "Datasheet": "https://www.lcsc.com/datasheet/C431540.pdf",
        "Description": "SPDT SMD slide switch, side-actuated (right angle), 8 x 2.8 mm, 1.5 mm pitch",
        "Manufacturer": "SHOU HAN", "LCSC Part": "C431540"}),
    ("stock:Connector", "USB_C_Receptacle_USB2.0_16P", "TYPE-C-31-M-12", None, {
        "Footprint": "Mindspark:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        "Datasheet": "https://www.lcsc.com/datasheet/C165948.pdf",
        "Description": "USB-C 2.0 receptacle, 16-pin, horizontal SMD + THT shell",
        "Manufacturer": "Korean Hroparts", "LCSC Part": "C165948"}),
    ("stock:Connector_Generic_MountingPin", "Conn_01x02_MountingPin", "S2B-PH-SM4-TB", None, {
        "Value": "S2B-PH-SM4-TB(LF)(SN)",
        "Footprint": "Mindspark:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
        "Datasheet": "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf",
        "Description": "JST PH 2-pin SMD side-entry header, 2 A, speaker connector "
                       "(mates with PHR-2 housing C157955 + SPH-002T-P0.5S crimps C111515)",
        "Manufacturer": "JST", "LCSC Part": "C295747"}),
    # 2N7002: SOT-23 G1 S2 D3. Exact maker/LCSC part picked with the passives.
    ("stock:Transistor_FET", "2N7002", "2N7002", None, {
        "Footprint": "Mindspark:SOT-23"}),
    ("stock:74xGxx", "74AHCT1G125", "SN74AHCT1G125DBVR", None, {
        "Value": "SN74AHCT1G125DBVR",
        "Footprint": "Mindspark:SOT-23-5",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74ahct1g125.pdf",
        "Description": "Single bus buffer, 3-state, TTL-level inputs (3.3 V logic to 5 V WS2812 data)",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C7484"}),
    ("stock:74xGxx", "74LVC1G125", "SN74LVC1G125DBVR", None, {
        "Value": "SN74LVC1G125DBVR",
        "Footprint": "Mindspark:SOT-23-5",
        "Datasheet": "https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf",
        "Description": "Single bus buffer, 3-state, 1.65-5.5 V (MIC_CLK fan-out buffer, as XMOS XK-VOICE-SQ66)",
        "Manufacturer": "Texas Instruments", "LCSC Part": "C23654"}),
]

# Generic stock symbols copied unchanged (no fixed part yet; the LCSC number goes on each
# placed instance). Flattened like the others.
GENERIC = [("stock:Device", n) for n in ["R", "C", "LED", "LED_RGB"]] + [
    ("stock:Connector", "TestPoint"),
    ("stock:Mechanical", "MountingHole"),
] + [("stock:Connector_Generic", "Conn_01x%02d" % n) for n in (4, 7, 8, 12)] + [
    ("stock:Connector_Generic", "Conn_02x12_Odd_Even")] + [
    ("stock:power", n) for n in ["GND", "PWR_FLAG", "+5V", "+3V3", "+1V8"]]

# Rail symbols that do not exist in the stock power library: a stock power symbol with a
# new name and Value (KiCad 10 takes a power symbol's net name from its Value).
POWER_RENAMED = [("+1V0", "+0V9"), ("VBUS", "VBUS_MAIN"), ("VBUS", "VBUS_ESP"),
                 ("+5V", "+5V_AMP"), ("+5V", "+5V_LED"), ("+3V3", "+3V3_MIC"), ("+1V0", "PLL_AVDD")]


TI_SYM = LIB / "incoming" / "ti_tps2121" / "TPS2121RUXR.kicad_sym"


def all_properties(block):
    """[(key, value)] of the top-level properties of a symbol block."""
    return re.findall(r'\(property\s+"([^"]+)"\s+"([^"]*)"', block)


def flatten(lib_text, name):
    """Return a stock symbol with any (extends "base") resolved: the base symbol's pins
    and graphics, renamed to `name`, carrying the derived symbol's own properties."""
    blk = get_symbol(lib_text, name)
    m = re.search(r'\(extends\s+"([^"]+)"\)', blk)
    if not m:
        return blk
    base = rename_symbol(flatten(lib_text, m.group(1)), m.group(1), name)
    for k, v in all_properties(blk):
        base = set_property(base, k, v)
    return base


def drop_hidden_pins(block):
    """Ultra Librarian adds hidden pins (e.g. 7_1) for its in-pad vias; we remove those vias,
    so the matching pins go too."""
    out, i = [], 0
    for m in re.finditer(r'\(pin\s+\w+\s+\w+', block):
        if m.start() < i:
            continue
        end = find_block(block, m.start())
        pin = block[m.start():end]
        out.append(block[i:m.start()])
        if not re.search(r'\(number\s+"\d+_\d+"', pin):
            out.append(pin)
        i = end
    out.append(block[i:])
    return "".join(out)


def load(src):
    if src == "raw":
        return (RAW / "easyeda_raw.kicad_sym").read_text()
    if src == "ti":
        return TI_SYM.read_text()
    return (STOCK / (src.split(":")[1] + ".kicad_sym")).read_text()


# kicad-schematic-tidy Step 0 (authorised 2026-11-10 for the Mindspark library only): EasyEDA
# outlines with large empty bodies or mixed pin groups are redrawn. Pin numbers, names, electrical
# types, visibility and drawn lengths are unchanged; only positions and the body rectangle move.
# name -> (body rectangle x0, y0, x1, y1 in lib units (y up), {pin: (x, y, angle)})
COMPACT = {
    # 5 pins: DATA/CLK left; VDD, SELECT, GND right, supply on top (was 1300 x 400 mil).
    "IM69D129FV01XTMA1": ((-6.35, 3.81, 6.35, -3.81),
                          {"1": (-8.89, 1.27, 0), "4": (-8.89, -1.27, 0), "5": (8.89, 2.54, 180),
                           "2": (8.89, 0, 180), "3": (8.89, -2.54, 180)}),
    # 6 pins: inputs left, outputs right, GND below (was 1200 x 400 mil with GND among the inputs).
    "TPS22918DBVR": ((-6.35, 5.08, 6.35, -5.08),
                     {"1": (-11.43, 2.54, 0), "3": (-11.43, -2.54, 0), "6": (11.43, 2.54, 180),
                      "5": (11.43, 0, 180), "4": (11.43, -2.54, 180), "2": (0, -10.16, 90)}),
    # MAX98357AETE+T: same pin tips as the old WLP layout (digital inputs left, supply/outputs/ground
    # right), so the audio sheet wiring is unchanged. Stock pins are 100 mil long, so the body is
    # 1000 mil wide. Stacked: VDD 7/8, GND 3/11/15/EP 17 (the extra ones hidden, as in the stock
    # symbol). The four hidden N.C. pins sit apart inside the body (never drawn, never wired).
    "MAX98357AETE+T": ((-12.7, 7.62, 12.7, -7.62),
                       {"1": (-15.24, 5.08, 0), "16": (-15.24, 2.54, 0), "14": (-15.24, 0, 0),
                        "4": (-15.24, -2.54, 0), "2": (-15.24, -5.08, 0),
                        "7": (15.24, 5.08, 180), "8": (15.24, 5.08, 180),
                        "9": (15.24, 1.27, 180), "10": (15.24, -1.27, 180),
                        "3": (15.24, -5.08, 180), "11": (15.24, -5.08, 180), "15": (15.24, -5.08, 180),
                        "17": (15.24, -5.08, 180),
                        "5": (-5.08, 0, 0), "6": (-2.54, 0, 0), "12": (2.54, 0, 0), "13": (5.08, 0, 0)}),
    # TS5A3166DBVR: same layout as the old YZP symbol: COM/IN left, NO right, V+ above, GND below.
    "TS5A3166DBVR": ((-6.35, 5.08, 6.35, -5.08),
                     {"2": (-8.89, 2.54, 0), "4": (-8.89, -2.54, 0), "1": (8.89, 2.54, 180),
                      "5": (0, 7.62, 270), "3": (0, -7.62, 90)}),
}


# TPS2121 (2026-11-10 review): each control pin gets room for its divider wired straight to it.
# IN1 + PR1/OV1 left, IN2 + CP2/OV2 right (PR1/CP2 one row below the IN pin, OV1/OV2 800 mil
# lower so one divider's rail and the other's GND clear), OUT/ST on top, SS/ILIM/GND below.
COMPACT["TPS2121RUXR"] = ((-10.16, 7.62, 10.16, -25.4),
                          {"7": (-15.24, 5.08, 0), "6": (-15.24, 0, 0), "5": (-15.24, -20.32, 0),
                           "2": (15.24, 5.08, 180), "3": (15.24, 0, 180), "4": (15.24, -20.32, 180),
                           "1": (-5.08, 12.7, 270), "8": (-5.08, 12.7, 270), "9": (5.08, 12.7, 270),
                           "11": (-7.62, -30.48, 90), "10": (0, -30.48, 90), "12": (7.62, -30.48, 90)})


def _xvf_wide():
    """XVF3800: same pin rows and order, body widened from 1200 to 1800 mil so the long
    SIGNAL/PORT names on the two sides no longer overlap in the middle."""
    pins = {}
    left = [str(n) for n in range(1, 34)]
    for i, n in enumerate(left):
        pins[n] = (-25.4, 40.64 - 2.54 * i, 0)
    right = [str(n) for n in range(34, 66)]
    for i, n in enumerate(right):
        pins[n] = (25.4, -39.37 + 2.54 * i, 180)
    return ((-22.86, 43.18, 22.86, -43.18), pins)


COMPACT["XVF3800-QF60B-C"] = _xvf_wide()


def compact(block, name):
    rect, pins = COMPACT[name]
    # drop drawn graphics (EasyEDA outlines, pin-1 dots), keep pins
    for kind in ("rectangle", "polyline", "circle", "arc", "text"):
        while True:
            m = re.search(r'\(%s\s' % kind, block)
            if not m:
                break
            block = block[:m.start()] + block[find_block(block, m.start()):]
    seen = set()

    def move(m):
        pin = m.group(0)
        n = re.search(r'\(number\s+"([^"]*)"', pin).group(1)
        x, y, a = pins[n]
        seen.add(n)
        return re.sub(r'\(at\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\)', '(at %g %g %g)' % (x, y, a), pin, count=1)
    out, i = [], 0
    for m in re.finditer(r'\(pin\s+\w+\s+\w+', block):
        if m.start() < i:
            continue
        end = find_block(block, m.start())
        out.append(block[i:m.start()])
        out.append(move(re.match(r'[\s\S]*', block[m.start():end])))
        i = end
    out.append(block[i:])
    block = "".join(out)
    assert seen == set(pins), (name, sorted(seen ^ set(pins)))
    x0, y0, x1, y1 = rect
    rect_txt = ('(rectangle (start %g %g) (end %g %g) (stroke (width 0.254) (type default)) '
                '(fill (type background)))' % (x0, y0, x1, y1))
    m = re.search(r'\(symbol\s+"%s_\d+_\d+"' % re.escape(name), block)
    p = block.index(")", m.end()) if False else m.end()
    block = block[:p] + " " + rect_txt + block[p:]
    block = re.sub(r'(\(property\s+"Reference"\s+"[^"]*"\s+\(at\s+)[-\d.]+\s+[-\d.]+',
                   lambda mm: mm.group(1) + "%g %g" % (x0, y0 + 1.27), block, count=1)
    block = re.sub(r'(\(property\s+"Value"\s+"[^"]*"\s+\(at\s+)[-\d.]+\s+[-\d.]+',
                   lambda mm: mm.group(1) + "%g %g" % (x0, y1 - 1.27), block, count=1)
    return block


# Pins to hide after the pin map is applied: a stacked pin is drawn once, the rest are hidden.
# MAX98357A EP (17) joins the hidden GND stack.
HIDE_PINS = {"MAX98357AETE+T": ("17",)}


def hide_pin(block, num):
    """Add (hide yes) to the pin with this number, right after its (length ...)."""
    for m in re.finditer(r'\(pin\s+\w+\s+\w+', block):
        end = find_block(block, m.start())
        pin = block[m.start():end]
        if re.search(r'\(number\s+"%s"' % re.escape(num), pin):
            if "(hide yes)" not in pin:
                pin = re.sub(r'(\(length\s+[-\d.]+\))', r'\1 (hide yes)', pin, count=1)
            return block[:m.start()] + pin + block[end:]
    raise KeyError("pin %s not found" % num)


def build_symbols():
    blocks = []
    for src, name, new, pins, props in SYMBOLS:
        text = load(src)
        blk = flatten(text, name) if src.startswith("stock") else get_symbol(text, name)
        if new != name:
            blk = rename_symbol(blk, name, new)
        if src == "ti":
            blk = drop_hidden_pins(blk)
            for k in ["DATASHEET_URL", "DESCRIPTION", "MANUFACTURER", "MPN", "Package", "SOURCE_URL"]:
                blk = drop_property(blk, k)
        if pins:
            blk = edit_pins(blk, pins)
        for num in HIDE_PINS.get(new, ()):
            blk = hide_pin(blk, num)
        if new in COMPACT:
            blk = compact(blk, new)
        for k, v in props.items():
            blk = set_property(blk, k, v)
        blk = drop_property(blk, "ki_keywords") if src in ("raw", "ti") else blk
        blk = set_property(blk, "Value", props.get("Value", new))
        blk = set_property(blk, "MPN", props.get("MPN", props.get("Value", new)))
        blocks.append(blk)
    for src, name in GENERIC:
        blocks.append(flatten(load(src), name))
    power = load("stock:power")
    for base, new in POWER_RENAMED:
        blk = rename_symbol(flatten(power, base), base, new)
        blk = set_property(blk, "Value", new)
        blk = drop_property(blk, "Description")          # stock text has escaped quotes
        blk = set_property(blk, "Description", "Power symbol creates a global label with name %s" % new)
        blocks.append(blk)
    OUT_SYM.write_text('(kicad_symbol_lib\n\t(version 20211014)\n\t(generator "mindspark_build")\n\t'
                       + "\n\t".join(blocks) + "\n)\n")


# --------------------------------------------------------------------------
# Footprints
# --------------------------------------------------------------------------
def build_xvf_footprint():
    """EasyEDA QFN-60 checked against XU316-1024-QF60B datasheet section 15:
    D2=E2=3.60 GND paddle, four 3.60 x 0.60 VDD paddles at +/-2.50, 0.4 mm pitch.
    Only changes: name, 3D model path, and a 15 % paste reduction on the paddles
    (full paste on 3.6 mm paddles risks the part floating on a 0.4 mm pitch QFN)."""
    src = RAW / "easyeda_raw.pretty" / "QFN-60_L7.0-W7.0-P0.40-TL-EP_XU316-1024.kicad_mod"
    name = "XMOS_QFN-60-5EP_7x7mm_P0.4mm"
    t = src.read_text()
    t = re.sub(r'\((footprint|module)\s+"?[^"\s)]+"?', '(footprint "%s"' % name, t, count=1)
    t = re.sub(r'\(fp_text value \S+', '(fp_text value %s' % name, t, count=1)   # was the EasyEDA name
    for num in ["61", "62", "63", "64", "65"]:
        m = re.search(r'\(pad\s+"?%s"?\s' % num, t)
        end = find_block(t, m.start())
        t = t[:end - 1] + " (solder_paste_margin_ratio -0.15)" + t[end - 1:]
    step = "QFN-60_L7.0-W7.0-P0.40-TL-EP_XU316-1024.step"
    shutil.copy(RAW / "easyeda_raw.3dshapes" / step, OUT_3D / "XMOS_QFN-60-5EP_7x7mm.step")
    t = re.sub(r'\(model\s+"[^"]*"', '(model "%s/XMOS_QFN-60-5EP_7x7mm.step"' % MODEL_DIR, t)
    (OUT_FP / (name + ".kicad_mod")).write_text(t)


def build_mic_footprint():
    """Drawn from Infineon IM69D129FV01 datasheet Figure 14 (footprint, top view).
    Origin = package centre. Sound port is 0.71 mm right of centre.
    Pads 0.54 x 0.75, columns 0.822 apart, rows 0.838 apart, inner column 1.252 from port.
    GND ring: OD 1.725, ID 0.985 (copper + mask). Paste: 3 arc apertures R0.54-0.83, 0.12 gaps.
    PCB sound hole 0.6 mm (Infineon recommendation)."""
    import math
    name = "Infineon_IM69D129FV01_LGA-5_3.5x2.65mm"
    px = 0.71                      # port x from package centre
    xi, xo, y = px - 1.252, px - 1.252 - 0.822, 0.419
    pads = {"1": (xo, y), "2": (xi, y), "4": (xi, -y), "5": (xo, -y)}   # KiCad y points down
    L = []
    L.append('(footprint "%s"' % name)
    L.append('\t(version 20240108)\n\t(generator "mindspark_build")\n\t(layer "F.Cu")')
    L.append('\t(descr "Infineon IM69D129FV01 PDM MEMS microphone, 3.5x2.65 mm LGA-5, bottom port; '
             'land pattern from datasheet v1.0 Figure 14")')
    L.append('\t(tags "MEMS microphone PDM Infineon bottom port")\n\t(attr smd)')
    L.append('\t(property "Reference" "REF**" (at 0 -2.4 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))')
    L.append('\t(property "Value" "%s" (at 0 2.4 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))' % name)
    # Fab outline (package body 3.5 x 2.65) and courtyard (+0.25)
    L.append('\t(fp_rect (start -1.75 -1.325) (end 1.75 1.325) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))')
    L.append('\t(fp_rect (start -2 -1.575) (end 2 1.575) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))')
    # Silk: outline corners kept clear of pads, plus a pin-1 dot (pin 1 = bottom-left)
    L.append('\t(fp_rect (start -1.86 -1.435) (end 1.86 1.435) (stroke (width 0.12) (type solid)) (fill none) (layer "F.SilkS"))')
    L.append('\t(fp_circle (center -2.15 1.2) (end -2.05 1.2) (stroke (width 0.2) (type solid)) (fill solid) (layer "F.SilkS"))')
    for num, (x, yy) in pads.items():
        L.append('\t(pad "%s" smd rect (at %.4f %.4f) (size 0.54 0.75) (layers "F.Cu" "F.Mask" "F.Paste") '
                 '(solder_paste_margin -0.035))' % (num, x, yy))
    # GND ring as a custom pad: anchor sits on the ring so it does not cover the port.
    rm, rw = (1.725 + 0.985) / 4, (1.725 - 0.985) / 2           # mean radius 0.6775, width 0.37
    L.append('\t(pad "3" smd custom (at %.4f 0) (size 0.36 0.36) (layers "F.Cu" "F.Mask")\n'
             '\t\t(options (clearance outline) (anchor circle))\n'
             '\t\t(primitives (gr_circle (center %.4f 0) (end %.4f 0) (width %.3f) (fill no))))'
             % (px + rm, -rm, 0.0, rw))
    # Paste-only arcs (stencil apertures). Rounded arc ends shorten the gap, so the
    # angular gap is set to give a 0.12 mm straight gap between aperture edges.
    pr, pw = (0.83 + 0.54) / 2, 0.83 - 0.54                   # 0.685, 0.29
    gap = math.degrees((0.12 + pw) / pr)
    for k, centre in enumerate([0, 120, 240]):
        a0, a1 = math.radians(centre - (120 - gap) / 2), math.radians(centre + (120 - gap) / 2)
        am = (a0 + a1) / 2
        P = lambda a: (px + pr * math.cos(a), -pr * math.sin(a))
        s, m, e = P(a0), P(am), P(a1)
        L.append('\t(pad "3" smd custom (at %.4f %.4f) (size 0.2 0.2) (layers "F.Paste")\n'
                 '\t\t(options (clearance outline) (anchor circle))\n'
                 '\t\t(primitives (gr_arc (start %.4f %.4f) (mid %.4f %.4f) (end %.4f %.4f) (width %.3f))))'
                 % (m[0], m[1], s[0] - m[0], s[1] - m[1], 0, 0, e[0] - m[0], e[1] - m[1], pw))
    L.append('\t(pad "" np_thru_hole circle (at %.4f 0) (size 0.6 0.6) (drill 0.6) (layers "*.Cu" "*.Mask"))' % px)
    # 3D model: a real MEMS microphone (InvenSense ICS-43434, stock KiCad), same 3.5 x 2.65 mm
    # body and 0.98 mm height as the IM69D129F. Infineon's own CAD is behind a myInfineon login.
    # Rotated -90 deg: long side along X and the lid's pin-1 dot bottom-left, where pin 1 is.
    # Measured centred; the offset only lifts it 0.01 mm onto the board.
    L.append('\t(model "${KICAD10_3DMODEL_DIR}/Sensor_Audio.3dshapes/InvenSense_ICS-43434-6_3.5x2.65mm.step" '
             '(offset (xyz 0 0 0.01)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 -90)))')
    L.append(')')
    (OUT_FP / (name + ".kicad_mod")).write_text("\n".join(L) + "\n")


def build_jst_footprint():
    """Stock KiCad JST PH S2B-PH-SM4-TB footprint, unchanged copper. The installed
    kicad-packages3d lacks this STEP, so point at the JST model already verified in the
    PDB library, with the same offset/rotation PDB uses on this stock geometry."""
    src = Path("/usr/share/kicad/footprints/Connector_JST.pretty/"
               "JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal.kicad_mod")
    t = src.read_text()
    shutil.copy("/home/anbu/Z/projects/PDB/libraries/3dmodels/JST_S2B-PH-SM4-TB.step",
                OUT_3D / "JST_S2B-PH-SM4-TB.step")
    m = re.search(r'\(model\s', t)
    t = (t[:m.start()] + '(model "%s/JST_S2B-PH-SM4-TB.step" (offset (xyz 0 -4.3 0)) '
         '(scale (xyz 1 1 1)) (rotate (xyz -90 0 0)))' % MODEL_DIR + t[find_block(t, m.start()):])
    (OUT_FP / src.name).write_text(t)


STOCK_FP = Path("/usr/share/kicad/footprints")
EASY_MODELS = LIB / "incoming" / "easyeda_models"     # models pulled for footprints we keep stock
PDB_3D = Path("/home/anbu/Z/projects/PDB/libraries/3dmodels")

# Stock footprints whose STEP is missing from this KiCad install. Copper is unchanged; only a
# model is attached. Offsets/rotations were solved so each STEP's bounding box matches the
# reference placement exactly (EasyEDA WRL carried over by pad matching, or PDB's verified
# placement). (stock footprint, model source, model file name, offset xyz, rotate xyz)
STOCK_WITH_MODEL = [
    # MAX98357AETE+T (2026-11-12): stock TQFN-16 3x3 footprint, copper unchanged. It fits ADI's
    # T1633-4 drawing (21-0136: EP 0.95-1.25 mm -> 1.23 mm pad; leads b 0.20-0.30, L 0.30-0.50 ->
    # 0.25 x 0.825 mm pads, 0.5 mm pitch). The EP1.23 STEP is not installed; the stock EP1.6 model
    # has the same 3 x 3 x 0.75 mm body (only the hidden underside pad differs).
    ("Package_DFN_QFN/TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
     Path("/usr/share/kicad/3dmodels/Package_DFN_QFN.3dshapes/TQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm.step"),
     "TQFN-16-1EP_3x3mm_P0.5mm.step", "0 0 0", "0 0 0"),
    ("LED_SMD/LED_WS2812B-2020_PLCC4_2.0x2.0mm",
     EASY_MODELS / "LED-SMD_4P-L2.0-W2.0-H0.8-TL_WS2812B-2020.step", "WS2812B-2020.step",
     "0 0.005 0.025", "0 0 0"),
    ("Button_Switch_SMD/SW_Push_1P1T_XKB_TS-1187A",
     RAW / "easyeda_raw.3dshapes" / "SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5.step", "XKB_TS-1187A.step",
     "0 0 0.055", "0 0 0"),
    ("Connector_USB/USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     PDB_3D / "HRO_TYPE-C-31-M-12.step", "HRO_TYPE-C-31-M-12.step",
     "-4.47 -3.65 0", "-90 0 0"),
    ("Connector_JST/JST_PH_S7B-PH-SM4-TB_1x07-1MP_P2.00mm_Horizontal",
     RAW / "easyeda_raw.3dshapes" / "CONN-SMD_PH2.00-WS-7P.step", "JST_S7B-PH-SM4-TB.step",
     "-6.0 2.825 0.005", "0 0 -180"),
]


def replace_model(t, path, off, rot):
    """Drop every (model ...) block and add one pointing at our copy."""
    while True:
        m = re.search(r'\(model\s', t)
        if not m:
            break
        t = t[:m.start()] + t[find_block(t, m.start()):]
    end = t.rstrip().rfind(")")
    return (t[:end] + '\t(model "%s" (offset (xyz %s)) (scale (xyz 1 1 1)) (rotate (xyz %s)))\n'
            % (path, off, rot) + t[end:])


def build_stock_with_models():
    for fp, src, name, off, rot in STOCK_WITH_MODEL:
        lib, fname = fp.split("/")
        t = (STOCK_FP / (lib + ".pretty") / (fname + ".kicad_mod")).read_text()
        shutil.copy(src, OUT_3D / name)
        (OUT_FP / (fname + ".kicad_mod")).write_text(replace_model(t, "%s/%s" % (MODEL_DIR, name), off, rot))


def build_srp_footprint():
    """Bourns SRP4020TA: EasyEDA footprint matches Bourns' recommended layout exactly
    (pads 1.5 x 2.4 at +/-1.85, 5.2 overall, 2.2 gap; datasheet p.1). Model lifted 0.105 mm."""
    t = (RAW / "easyeda_raw.pretty" / "IND-SMD_L4.5-W4.1_SRP4020TA.kicad_mod").read_text()
    name = "L_Bourns_SRP4020TA"
    t = re.sub(r'\((footprint|module)\s+"?[^"\s)]+"?', '(footprint "%s"' % name, t, count=1)
    t = re.sub(r'\(fp_text value \S+', '(fp_text value %s' % name, t, count=1)
    shutil.copy(RAW / "easyeda_raw.3dshapes" / "IND-SMD_L4.5-W4.1-H1.2_SRP4020TA.step", OUT_3D / "Bourns_SRP4020TA.step")
    (OUT_FP / (name + ".kicad_mod")).write_text(
        replace_model(t, "%s/Bourns_SRP4020TA.step" % MODEL_DIR, "0 -0.005 0.105", "0 0 0"))


def rename_fp(t, name):
    t = re.sub(r'\((footprint|module)\s+"?[^"\s)]+"?', '(footprint "%s"' % name, t, count=1)
    return re.sub(r'\(fp_text value \S+', '(fp_text value %s' % name, t, count=1)


def build_side_switch_footprints():
    """SHOU HAN side-actuated switches from easyeda2kicad, checked against the datasheets in
    datasheets/ (2026-11-11). Copper unchanged; 3D models attached at zero offset (not yet aligned).
    - TS24CA (C393942, p.1 mounting reference): contacts 1/2 are 0.6 x 1.2 mm, 3.4 mm apart;
      L-shaped hold-down tabs 3/4 span 5.3 mm outside, 4.0 / 3.2 mm inside; two 0.7 mm locating
      holes 1.7 mm apart. The actuator points to -Y (put that edge on the board edge).
    - MSK12C02 (C431540, p.1): pins 3, 2, 1 at -2.25, -0.75 (mirrored: +0.75), +2.25 mm, so the
      common (2) is 1.5 mm from 3 and 3 mm from 1; four shell tabs (pad 4), 8.4 / 6.3 mm spans;
      two 0.85-0.9 mm locating holes 3 mm apart. The lever points to +Y."""
    for src, name, step, model in (
            ("SW-SMD_2P-TS24CA", "SW_SHOUHAN_TS24CA_SideActuated", "SW-SMD_2P-TS24CA.step", "SHOUHAN_TS24CA.step"),
            ("SW-TH_MSK12C02", "SW_SHOUHAN_MSK12C02_SideActuated",
             "SW-SMD_3P-L6.6-W2.7-LS7.8-P1.50.step", "SHOUHAN_MSK12C02.step")):
        t = rename_fp((RAW / "easyeda_raw.pretty" / (src + ".kicad_mod")).read_text(), name)
        shutil.copy(RAW / "easyeda_raw.3dshapes" / step, OUT_3D / model)
        (OUT_FP / (name + ".kicad_mod")).write_text(replace_model(t, "%s/%s" % (MODEL_DIR, model), "0 0 0", "0 0 0"))


def build_smd_header_footprint():
    """2x12 2.54 mm SMD pin header for J701, HCTL PZ254-2-12-S (C3294470, 2026-11-11).
    Starts from KiCad's stock PinHeader_2x12_P2.54mm_Vertical_SMD (silk, fab, courtyard and
    3D model kept) with the copper changed to HCTL's recommended layout (datasheet
    PZ254-2-12-S_C3294470.pdf, "Recommended P.C.B Layout"): pads 1.02 x 3.12 mm, 2.26 mm
    between the rows and W+1 = 8.5 mm overall, so pad centres sit at +/-2.69 mm. KiCad's
    generic pattern was 1.0 x 3.15 mm at +/-2.525 mm; EasyEDA's was 1.02 x 3.12 mm at +/-2.80 mm.
    Odd pins in the left column, even pins in the right, as Conn_02x12_Odd_Even.
    The -S part has no locating posts (those come only with the -P suffix)."""
    name = "PinHeader_2x12_P2.54mm_Vertical_SMD_HCTL_PZ254"
    t = (STOCK_FP / "Connector_PinHeader_2.54mm.pretty" / "PinHeader_2x12_P2.54mm_Vertical_SMD.kicad_mod").read_text()
    t = rename_fp(t, name)
    t = t.replace("(at -2.525 ", "(at -2.69 ").replace("(at 2.525 ", "(at 2.69 ")
    t = t.replace("(size 3.15 1)", "(size 3.12 1.02)")
    # Pin-1 silk tick: start it beyond the wider pad (outer edge now at -4.25 mm).
    t = t.replace("(start -4.04 -14.78)", "(start -4.6 -14.78)")
    t = t.replace('"surface-mounted straight pin header, 2x12, 2.54mm pitch, double rows"',
                  '"HCTL PZ254-2-12-S SMD straight pin header, 2x12, 2.54mm pitch, pads per HCTL datasheet"')
    for old in ("(at -2.525 ", "(at 2.525 ", "(size 3.15 1)", "(start -4.04 -14.78)"):
        assert old not in t, old      # every pad and the tick were changed
    (OUT_FP / (name + ".kicad_mod")).write_text(t)


def build_espressif_esp32_footprint():
    """ESP32-S3-WROOM-1U from Espressif's own KiCad library (github.com/espressif/kicad-libraries,
    installed through KiCad's plugin manager; copied into incoming/espressif/ 2026-11-12). The user
    picked it in KiCad over the stock RF_Module footprint: same 41 pads, and it has Espressif's 1U
    STEP, which the stock install lacks. Copper unchanged; only the model path moves to our
    3dmodels folder (Espressif's own placement offset kept)."""
    src = LIB / "incoming" / "espressif"
    t = (src / "ESP32-S3-WROOM-1U.kicad_mod").read_text()
    shutil.copy(src / "ESP32-S3-WROOM-1U.STEP", OUT_3D / "Espressif_ESP32-S3-WROOM-1U.step")
    t = replace_model(t, "%s/Espressif_ESP32-S3-WROOM-1U.step" % MODEL_DIR, "-9 -9.75 0", "0 0 0")
    (OUT_FP / "ESP32-S3-WROOM-1U.kicad_mod").write_text(t)


def build_rgb_footprint():
    """TOGIALED 1615 RGB LED, drawn from the datasheet's recommended pad layout (p.2): four
    0.85 x 0.5 mm pads, 0.9 mm between columns (2.6 mm overall), rows 1.6 mm overall (0.6 mm gap).
    Top view: pin 2 top-left, 1 top-right, 3 bottom-left, 4 bottom-right. EasyEDA's pads were
    1.1 x 0.6 mm with a 0.3 mm row gap, so they were not used. 3D model from EasyEDA."""
    name = "LED_RGB_TOGIALED_1615_1.6x1.5mm"
    px, py = 0.45 + 0.425, 0.8 - 0.25
    pads = {"1": (px, -py), "2": (-px, -py), "3": (-px, py), "4": (px, py)}
    L = ['(footprint "%s"' % name, '\t(version 20240108)\n\t(generator "mindspark_build")\n\t(layer "F.Cu")',
         '\t(descr "TOGIALED TJ-S1615CY6TGLCCSRGB-A5 RGB LED, 1.6x1.5 mm, pad layout from datasheet p.2")',
         '\t(tags "LED RGB 1615 common cathode")\n\t(attr smd)',
         '\t(property "Reference" "REF**" (at 0 -1.8 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '\t(property "Value" "%s" (at 0 1.8 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))' % name,
         '\t(fp_rect (start -0.8 -0.75) (end 0.8 0.75) (stroke (width 0.1) (type solid)) (fill none) (layer "F.Fab"))',
         '\t(fp_rect (start -1.55 -1.05) (end 1.55 1.05) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
         '\t(fp_circle (center 1.6 -1.05) (end 1.7 -1.05) (stroke (width 0.2) (type solid)) (fill solid) (layer "F.SilkS"))']
    for n, (x, y) in pads.items():
        L.append('\t(pad "%s" smd rect (at %.3f %.3f) (size 0.85 0.5) (layers "F.Cu" "F.Mask" "F.Paste"))' % (n, x, y))
    step = [f for f in (RAW / "easyeda_raw.3dshapes").iterdir() if "1615" in f.name and f.suffix == ".step"]
    if step:
        shutil.copy(step[0], OUT_3D / "LED_RGB_1615.step")
        L.append('\t(model "%s/LED_RGB_1615.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))' % MODEL_DIR)
    L.append(")")
    (OUT_FP / (name + ".kicad_mod")).write_text("\n".join(L) + "\n")


def build_tps2121_footprint():
    """TI/Ultra Librarian RUX0012A copper, checked against TI's land pattern (SLVSEA3F p.39:
    8 x 0.2 x 0.6 and 4 x 0.4 x 1.05, 2.3 and 1.35 spans, 0.5 pitch) and EasyEDA C485916
    (same pads rotated 90 deg). Changes: the four 0.2 mm via-in-pad holes are removed (no
    filled-via fab option needed; thermal vias go beside the pads in layout), and the
    separate mask polygons are replaced by a 0.05 mm NSMD opening on each pad."""
    name = "TI_RUX0012A_VQFN-HR-12_2x2.5mm"
    t = (LIB / "incoming" / "ti_tps2121" / "IC_TPS2121RUXR.kicad_mod").read_text()
    t = rename_fp(t, name)
    t = re.sub(r'\n\s*\(pad \d+_\d+ thru_hole[^\n]*', "", t)              # in-pad vias
    while True:                                                            # mask polygons
        m = re.search(r'\(fp_poly\s*\(pts[\s\S]*?\(layer F\.Mask\)', t)
        if not m:
            break
        s = t.rfind("(fp_poly", 0, m.end())
        t = t[:s] + t[find_block(t, s):]
    t = t.replace("(layers F.Cu F.Paste))", "(layers F.Cu F.Paste F.Mask) (solder_mask_margin 0.05))")
    shutil.copy(LIB / "incoming" / "ti_tps2121" / "TPS2121RUXR.step", OUT_3D / "TI_RUX0012A.step")
    (OUT_FP / (name + ".kicad_mod")).write_text(replace_model(t, "%s/TI_RUX0012A.step" % MODEL_DIR, "0 0 0", "0 0 0"))


# Stock footprints copied verbatim (copper and stock 3D path unchanged) so the project only
# depends on the Mindspark library.
STOCK_COPY = [
    "Package_TO_SOT_SMD/SOT-23", "Package_TO_SOT_SMD/SOT-23-5", "Package_TO_SOT_SMD/SOT-23-6",
    "Package_SON/USON-10_2.5x1.0mm_P0.5mm",
    "Package_SON/Winbond_USON-8-2EP_3x4mm_P0.8mm_EP0.2x0.8mm",
    "Diode_SMD/D_SMF",
    "Crystal/Crystal_SMD_3225-4Pin_3.2x2.5mm",
    "Inductor_SMD/L_0402_1005Metric",
    "Resistor_SMD/R_0402_1005Metric",
    "Capacitor_SMD/C_0402_1005Metric", "Capacitor_SMD/C_0603_1608Metric", "Capacitor_SMD/C_0805_2012Metric",
    "Capacitor_SMD/C_1206_3216Metric",
    "LED_SMD/LED_0603_1608Metric",
    "Connector_PinHeader_2.54mm/PinHeader_1x04_P2.54mm_Vertical",
    "Connector_PinHeader_2.54mm/PinHeader_1x08_P2.54mm_Vertical",
    "Connector_PinHeader_2.54mm/PinHeader_1x12_P2.54mm_Vertical",
    "TestPoint/TestPoint_Pad_1.0x1.0mm", "TestPoint/TestPoint_Pad_1.5x1.5mm",
    "TestPoint/TestPoint_THTPad_2.0x2.0mm_Drill1.0mm",
    "MountingHole/MountingHole_2.2mm_M2_Pad_Via",   # H1-H4: M2 with via pad, chosen in KiCad 2026-11-11
]


def build_stock_copies():
    for fp in STOCK_COPY:
        lib, fname = fp.split("/")
        shutil.copy(STOCK_FP / (lib + ".pretty") / (fname + ".kicad_mod"), OUT_FP / (fname + ".kicad_mod"))


def check_pins_match_pads():
    """Every pin number of every Mindspark symbol must exist as a pad on its footprint."""
    t = OUT_SYM.read_text()
    bad = []
    for m in re.finditer(r'\(symbol\s+"([^"]+)"', t):
        name = m.group(1)
        if re.search(r'_\d+_\d+$', name):
            continue
        blk = t[m.start():find_block(t, m.start())]
        fp = re.search(r'\(property\s+"Footprint"\s+"([^"]*)"', blk).group(1)
        if not fp:                       # generic symbol: footprint chosen per instance
            continue
        lib, fname = fp.split(":")
        path = (OUT_FP if lib == "Mindspark" else STOCK_FP / (lib + ".pretty")) / (fname + ".kicad_mod")
        padset = set(re.findall(r'\(pad\s+"?([^"\s]+)"?\s', path.read_text()))
        pins = set(re.findall(r'\(number\s+"([^"]*)"', blk))
        if pins - padset:
            bad.append("%s: pins %s not on %s" % (name, sorted(pins - padset), fp))
    if bad:
        raise SystemExit("pin/pad mismatch:\n  " + "\n  ".join(bad))
    print("pin/pad check: every symbol pin has a pad")


if __name__ == "__main__":
    # Outputs are fully regenerated: clear them so dropped parts disappear.
    for d in (OUT_FP, OUT_3D):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    build_symbols()
    build_xvf_footprint()
    build_mic_footprint()
    build_jst_footprint()
    build_tps2121_footprint()
    build_rgb_footprint()
    build_side_switch_footprints()
    build_smd_header_footprint()
    build_stock_copies()
    build_espressif_esp32_footprint()
    build_stock_with_models()
    build_srp_footprint()
    check_pins_match_pads()
    print("wrote", OUT_SYM, "and", sorted(p.name for p in OUT_FP.iterdir()))
