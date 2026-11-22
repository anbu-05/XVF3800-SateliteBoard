"""3D model fixes (2026-11-22, user).

The read-only 3D check (AGENTS.md open questions) found two missing and three suspect models.
Second pass (same day): the two SHOU HAN side switches were attached at zero offset by
libraries/tools/build_libraries.py and never aligned. Offsets solved with
libraries/tools/model_align/align.py (STEP bounding box = EasyEDA's WRL on EasyEDA's own
footprint, pads matched exactly): TS24CA (0, 1.049, 0.865) rot 0; MSK12C02 (0, -0.5, 0.005)
rot 180 (the box alone can't tell 0 from 180; the render picks 180: lever over the edge).

Each was rendered alone on a copy of the board (side and top views) before this script:

  J301   JST S7B-PH-SM4-TB   turned 180 deg: opening faced into the board, leads sat at the
                             edge instead of on pads 1-7. Model turned about the footprint
                             centre: offset (-6, 2.825) rot -180  ->  offset (6, -2.825) rot 0.
                             Its side profile now matches J501's.
  J501   JST S2B-PH-SM4-TB   already right (opening at the north edge, leads on the pads);
                             left alone.
  SW701  SHOUHAN MSK12C02    turned 180 deg: lever pointed into the board, leads off the pads.
                             rot 0 -> 180, and (second pass, below) shifted 0.5 mm outward.
  SW401, SW402, SW603  SHOUHAN TS24CA  (second pass, user saw them off position) the model sat
                             1.05 mm inward and 0.87 mm sunk into the board.
  U401   W25Q32JVUUIQ        no model (KiCad 10 ships no STEP for the stock Winbond USON-8-2EP).
                             EasyEDA C2999380 (easyeda2kicad --3d), centred 3 x 4 mm body; the
                             pin-1 dot lands next to the pin-1 silk mark as is.
  D402   TOGIALED 1615 RGB   no model. EasyEDA C601684 (easyeda2kicad --3d), 1.6 x 1.5 mm,
                             centred; turned 180 deg so its polarity mark sits between pads 1
                             and 4 (datasheet p.2, TJ-S1615CY6TGLCCSRGB_C601684.pdf).

The same model line goes into the board footprint and into the Mindspark library footprint, so
an "update footprint from library" keeps it. libraries/tools/build_libraries.py carries the
same values (it is not rerun here: its output has drifted from the committed library).

Run once, PCB editor closed:  python3 tools/models_3d_2026_11_22.py
Running it again changes nothing.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from place_tidy import BOARD  # noqa: E402
from sexpr import parse, dump, children, child, q  # noqa: E402

LIB_FP = os.path.join(os.path.dirname(BOARD), "..", "libraries", "footprints", "Mindspark.pretty")
MODEL_DIR = "${KIPRJMOD}/../libraries/3dmodels"

# reference -> (library footprint name, model file, offset xyz, rotate xyz)
MODELS = {
    "J301": ("JST_PH_S7B-PH-SM4-TB_1x07-1MP_P2.00mm_Horizontal", "JST_S7B-PH-SM4-TB.step",
             ("6", "-2.825", "0.005"), ("0", "0", "0")),
    "SW701": ("SW_SHOUHAN_MSK12C02_SideActuated", "SHOUHAN_MSK12C02.step",
              ("0", "-0.5", "0.005"), ("0", "0", "180")),
    **{ref: ("SW_SHOUHAN_TS24CA_SideActuated", "SHOUHAN_TS24CA.step",
             ("0", "1.049", "0.865"), ("0", "0", "0")) for ref in ("SW401", "SW402", "SW603")},
    "U401": ("Winbond_USON-8-2EP_3x4mm_P0.8mm_EP0.2x0.8mm", "Winbond_USON-8-2EP_3x4mm.step",
             ("0", "0", "0"), ("0", "0", "0")),
    "D402": ("LED_RGB_TOGIALED_1615_1.6x1.5mm", "LED_RGB_1615.step",
             ("0", "0", "0"), ("0", "0", "180")),
}


def model_node(fname, off, rot):
    return ["model", q(f"{MODEL_DIR}/{fname}"),
            ["offset", ["xyz", *off]],
            ["scale", ["xyz", "1", "1", "1"]],
            ["rotate", ["xyz", *rot]]]


def set_model(fp, node):
    """Replace every (model ...) in a footprint with the one given."""
    fp[:] = [c for c in fp if not (isinstance(c, list) and c and c[0] == "model")]
    fp.append(node)


def ref_of(fp):
    r = [p[2] for p in children(fp, "property") if p[1] == "Reference"]
    return r[0] if r else None


def main():
    # Every model file must exist before anything points at it.
    lib_3d = os.path.join(os.path.dirname(BOARD), "..", "libraries", "3dmodels")
    for _, fname, _, _ in MODELS.values():
        assert os.path.exists(os.path.join(lib_3d, fname)), fname

    # Board footprints.
    root = parse(open(BOARD).read())
    done = set()
    for fp in children(root, "footprint"):
        ref = ref_of(fp)
        if ref in MODELS:
            name, fname, off, rot = MODELS[ref]
            assert fp[1] == f"Mindspark:{name}", (ref, fp[1])
            set_model(fp, model_node(fname, off, rot))
            done.add(ref)
    assert done == set(MODELS), set(MODELS) - done
    open(BOARD, "w").write(dump(root) + "\n")

    # Library footprints.
    for name, fname, off, rot in {v[0]: v for v in MODELS.values()}.values():
        path = os.path.join(LIB_FP, name + ".kicad_mod")
        fp = parse(open(path).read())
        set_model(fp, model_node(fname, off, rot))
        open(path, "w").write(dump(fp) + "\n")
    print("models set:", ", ".join(sorted(done)))


if __name__ == "__main__":
    main()
