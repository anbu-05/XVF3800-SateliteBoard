# Compute KiCad model rotation+offset so a STEP sits on a target footprint the way a
# reference bbox says it should. Reference = EasyEDA WRL bbox in the EasyEDA footprint frame,
# carried to the target footprint by the pad-to-pad transform.
import sys, re, json, math, subprocess, os
sys.path.insert(0, os.path.dirname(__file__))
from bbox import wrl_bbox, glb_bbox
HERE = os.path.dirname(os.path.abspath(__file__))

def pads(fp):
    t = open(fp).read(); out = {}
    for m in re.finditer(r'\(pad\s+"?([^"\s]*)"?\s+\w+\s+\w+[^()]*\(at\s+([-\d.]+)\s+([-\d.]+)', t):
        out.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
    return {k: (sum(p[0] for p in v)/len(v), sum(p[1] for p in v)/len(v)) for k, v in out.items() if k}

def rot(p, deg):  # rotate in pcb frame (y down); positive deg = clockwise on screen
    a = math.radians(deg); return (p[0]*math.cos(a) - p[1]*math.sin(a), p[0]*math.sin(a) + p[1]*math.cos(a))

def pad_transform(src_fp, dst_fp, names=None):
    a, b = pads(src_fp), pads(dst_fp)
    common = [k for k in a if k in b and (names is None or k in names)]
    best = None
    for deg in (0, 90, 180, 270):
        ra = [rot(a[k], deg) for k in common]
        tx = sum(b[k][0] - r[0] for k, r in zip(common, ra)) / len(common)
        ty = sum(b[k][1] - r[1] for k, r in zip(common, ra)) / len(common)
        err = max(math.hypot(r[0] + tx - b[k][0], r[1] + ty - b[k][1]) for k, r in zip(common, ra))
        if best is None or err < best[0]: best = (err, deg, tx, ty)
    return best, common

def measure(fp, step, off, rotz, tag):
    pcb, glb = f'{HERE}/{tag}.kicad_pcb', f'{HERE}/{tag}.glb'
    subprocess.run(['python3', '-I', f'{HERE}/mkfix.py', pcb, fp, step, ' '.join(map(str, off)), f'0 0 {rotz}'], check=True)
    subprocess.run(['kicad-cli', 'pcb', 'export', 'glb', '--no-board-body', '-o', glb, pcb], check=True, capture_output=True)
    lo, hi = glb_bbox(glb)
    # glTF y-up metres -> KiCad 3D mm relative to footprint at (50,50): X right, Y up (= -pcb y), Z up from board top
    X = (lo[0]*1000 - 50, hi[0]*1000 - 50)
    Y = (-(hi[2]*1000 - 50), -(lo[2]*1000 - 50))
    Z = (lo[1]*1000 - 1.6, hi[1]*1000 - 1.6)
    return X, Y, Z

def ref_box_from_wrl(wrl, deg, tx, ty):
    lo, hi = wrl_bbox(wrl)   # 3D frame of the source footprint: x, y(up), z
    # corners in pcb frame (y down), rotate+translate into target footprint pcb frame, back to 3D y-up
    pts = [rot((x, -y), deg) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])]
    xs = [p[0] + tx for p in pts]; ys = [-(p[1] + ty) for p in pts]
    return (min(xs), max(xs)), (min(ys), max(ys)), (lo[2], hi[2])

def solve(src_fp, wrl, step, dst_fp, tag, names=None, ref=None):
    (err, deg, tx, ty), common = pad_transform(src_fp, dst_fp, names)
    rotz = -deg   # pcb clockwise -> KiCad model rotation (CCW positive, y up)
    R = ref or ref_box_from_wrl(wrl, deg, tx, ty)
    X0, Y0, Z0 = measure(dst_fp, step, (0, 0, 0), rotz, tag + '_0')
    off = (round((R[0][0]+R[0][1])/2 - (X0[0]+X0[1])/2, 3), round((R[1][0]+R[1][1])/2 - (Y0[0]+Y0[1])/2, 3), round(R[2][0] - Z0[0], 3))
    X1, Y1, Z1 = measure(dst_fp, step, off, rotz, tag + '_1')
    f = lambda b: '(%.2f..%.2f)' % b
    print(f'{tag}: pads {len(common)} matched, max err {err:.3f} mm, pad rot {deg} -> model rotz {rotz}, offset {off}')
    print(f'   ref  X{f(R[0])} Y{f(R[1])} Z{f(R[2])}')
    print(f'   step X{f(X1)} Y{f(Y1)} Z{f(Z1)}')
    return rotz, off

if __name__ == '__main__':
    a = sys.argv[1:]; solve(a[0], a[1], a[2], a[3], a[4])
