# Bounding-box helpers, pure Python (no numpy on this host).
import json, struct, re

def mm(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(4)) for j in range(4)] for i in range(4)]

def wrl_bbox(path):
    """Raw easyeda2kicad .wrl: plain point lists in 0.1-inch units, KiCad 3D frame (x right, y up, z up)."""
    t = open(path, errors='ignore').read()
    lo, hi = [1e9] * 3, [-1e9] * 3
    for blk in re.findall(r'point\s*\[([^\]]*)\]', t):
        v = [float(x) for x in re.findall(r'[-\d.eE+]+', blk)]
        for i in range(0, len(v) - 2, 3):
            for k in range(3):
                lo[k] = min(lo[k], v[i + k] * 2.54); hi[k] = max(hi[k], v[i + k] * 2.54)
    return lo, hi

def node_matrix(n):
    if 'matrix' in n:
        m = n['matrix']; return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    x, y, z, w = n.get('rotation', [0, 0, 0, 1]); s = n.get('scale', [1, 1, 1]); t = n.get('translation', [0, 0, 0])
    R = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    return [[R[i][0]*s[0], R[i][1]*s[1], R[i][2]*s[2], t[i]] for i in range(3)] + [[0, 0, 0, 1]]

def glb_bbox(path):
    """All component meshes in a kicad-cli GLB export, in the raw glTF frame (as exported)."""
    b = open(path, 'rb').read()
    L = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + L])
    lo, hi = [1e9] * 3, [-1e9] * 3
    def walk(i, P):
        n = j['nodes'][i]; M = mm(P, node_matrix(n))
        if 'mesh' in n:
            for pr in j['meshes'][n['mesh']]['primitives']:
                a = j['accessors'][pr['attributes']['POSITION']]
                for c in range(8):
                    p = [a['max'][k] if c >> k & 1 else a['min'][k] for k in range(3)] + [1]
                    q = [sum(M[r][k] * p[k] for k in range(4)) for r in range(3)]
                    for k in range(3): lo[k] = min(lo[k], q[k]); hi[k] = max(hi[k], q[k])
        for c in n.get('children', []): walk(c, M)
    I = [[float(r == c) for c in range(4)] for r in range(4)]
    for r in j['scenes'][j.get('scene', 0)]['nodes']: walk(r, I)
    return lo, hi
