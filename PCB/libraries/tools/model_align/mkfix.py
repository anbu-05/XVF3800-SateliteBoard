# Usage: mkfix.py OUT.kicad_pcb FOOTPRINT.kicad_mod MODELPATH "ox oy oz" "rx ry rz"
# Places one footprint at the board centre (50,50) with its model replaced, on a 100x100 board.
import sys, re, uuid
out, fp, model, off, rot = sys.argv[1:6]
hdr = open('/home/anbu/Z/projects/PDB/libraries/tools/make_model_fixture.py').read().split("parse('",1)[1].split("')",1)[0]
t = open(fp).read().rstrip()
# drop existing model blocks
def drop_models(t):
    while True:
        m = re.search(r'\(model\s', t)
        if not m: return t
        d, i = 0, m.start()
        while True:
            if t[i] == '(': d += 1
            elif t[i] == ')':
                d -= 1
                if d == 0: break
            i += 1
        t = t[:m.start()] + t[i+1:]
t = drop_models(t)
t = t[:-1] + f'(model "{model}" (offset (xyz {off})) (scale (xyz 1 1 1)) (rotate (xyz {rot}))) (at 50 50) (uuid "{uuid.uuid4()}"))'
edge = ''.join(f'(gr_line (start {a}) (end {b}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts") (uuid "{uuid.uuid4()}"))'
               for a, b in [('0 0','100 0'),('100 0','100 100'),('100 100','0 100'),('0 100','0 0')])
open(out, 'w').write(hdr[:-1] + '\n' + t + edge + ')\n')
