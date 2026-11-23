"""U103 (TPS2121, TI RUX0012A VQFN-HR-12) 3D model fix (2026-11-23, user).

The Ultra Librarian STEP (incoming/ti_tps2121/TPS2121RUXR.step) is exported Y-up: on the
footprint it measured X -1..1, Y 0..1 (the 1 mm body height), Z -1.25..1.25 (the 2.5 mm
length), so the part stood on its side, half under the board, leads on one side only.

Fix: rotate -90 deg about X (+90 sinks it under the board), lift 0.005 mm onto the copper.
Measured after (libraries/tools/model_align, kicad-cli GLB export): X -1..1, Y -1.25..1.25,
Z 0..1.0, matching the 2.0 x 2.5 x 1.0 mm package and the pad field. The top render puts the
model's pin-1 dot at the corner by pad 1 and the silk pin-1 dot (the pads are symmetric, so
only the dot tells 0 from 180 deg about Z; 0 is right).

Board copy and Mindspark library footprint get the same model line, so the library-mismatch
check stays clean. Run with the PCB editor closed:  python3 tools/model_rux_2026_11_23.py
Running it again changes nothing.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children  # noqa: E402
from models_3d_2026_11_22 import LIB_FP, model_node, set_model, ref_of  # noqa: E402

REF = "U103"
NAME = "TI_RUX0012A_VQFN-HR-12_2x2.5mm"
MODEL = ("TI_RUX0012A.step", ("0", "0", "0.005"), ("-90", "0", "0"))


def main():
    node = model_node(*MODEL)

    # Board copy of U103.
    root = parse(open(BOARD).read())
    hits = [fp for fp in children(root, "footprint") if ref_of(fp) == REF]
    assert len(hits) == 1 and hits[0][1] == f"Mindspark:{NAME}", REF
    set_model(hits[0], node)
    open(BOARD, "w").write(dump(root) + "\n")

    # Library footprint.
    path = os.path.join(LIB_FP, NAME + ".kicad_mod")
    fp = parse(open(path).read())
    set_model(fp, node)
    open(path, "w").write(dump(fp) + "\n")
    print("U103 model: rotate -90 0 0, offset 0 0 0.005")


if __name__ == "__main__":
    main()
