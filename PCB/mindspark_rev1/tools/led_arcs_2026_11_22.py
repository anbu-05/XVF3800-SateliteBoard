"""LED chain links as arcs along the +5V_LED ring (user 2026-11-22).

User: "take the DOUT out of the LED, place it really close to the power ring, and just draw a
curved trace to the DIN of the next LED ... it's okay if it's a curved line." Curved tracks are an
agreed exception to jog routing for these links only.

Each WS2812B-2020 on the ring (bottom layer) has VDD and DOUT in the outer column (r 27.57) and
DIN and GND in the inner column (r 26.47). Since the ring was reversed
(tools/led_ring_reverse_2026_11_22.py) the chain runs with increasing angle (board angle, y down):
DOUT sits 1.9 deg past its LED's centre, the next LED's DIN 1.98 deg before that LED's centre.
Each link, all on B.Cu, 0.15 mm:
  1. out from DOUT's centre to r 27.9, just inside the ring (ring inner edge r 28.2, so 0.225 mm
     of clearance);
  2. an arc at r 27.9 along the ring towards the next LED;
  3. a straight 45-ish dive inward to r 26.47 (DIN's radius), finishing DIVE_END deg before DIN's
     edge, because the next LED's VDD pad (and its stub to the ring) fills the outer column there;
  4. a short arc at r 26.47 into DIN's centre.
The next LED's supply cap C8xx then joins its VDD pad round DIN's other side (power_v2), or, for
C802 and C807, by the user's top-layer hop (tools/user_edits_2026_11_22.py CAP_HOPS).

D801's DIN is fed by LED_D0 from R802 (frozen with the signals); D812's DOUT is unused.
"""
import math

CX, CY = 146.558, 98.679
W = 0.15
CLR = 0.15            # to other nets' copper
RING_IN = 28.2        # the ring's inner edge (r 28.7, 1.0 mm wide)
R_IN = 26.47          # DIN's radius
# Shape of each link, searched per link in this order until it clears everything laid so far:
R_OUTS = (27.95, 27.9, 27.85, 27.8, 27.7)                  # the run along the ring (27.95: 0.175 to it)
DIVE_ENDS = tuple(round(1.2 + 0.4 * k, 1) for k in range(14))  # deg from the end of the dive to DIN
DIVE_SPANS = (3.2, 2.8, 3.6, 4.0, 2.4, 4.8, 1.6, 0.8, 0.4)  # deg the dive takes (3.2 is about 45 deg,
#   0.4 nearly straight in: for a link whose last stretch has a via just before the next LED)

# The user's lines that drop from the top layer to the bottom layer just inside the ring cross every
# run along it on their bottom-layer leg; their vias move inward a little (user: nearby lines may
# move a little), each pair together so it keeps its spacing. Edits to the frozen snapshot:
#   EDITS: (net, layer, old points, new points) -- a run of segments replaced
#   VIA_MOVES: (net, old centre, new centre)
EDITS = [
    # UART_TX / UART_RX pair between D808 and D809: both vias 0.35 mm further in along their 45 deg
    # lines; R608's line under them steps down 0.27 mm and jogs back up into its via
    ("/ESP_UART_TX", "F.Cu", [(126.2819, 76.2508), (128.0601, 78.029)], [(126.2819, 76.2508), (128.3101, 78.279)]),
    ("/ESP_UART_TX", "B.Cu", [(130.6068, 80.5757), (128.0601, 78.029)], [(130.6068, 80.5757), (128.3101, 78.279)]),
    ("/ESP_UART_RX", "F.Cu", [(126.3202, 75.6412), (128.658, 77.979)], [(126.3202, 75.6412), (128.908, 78.229)]),
    ("/ESP_UART_RX", "B.Cu", [(131.158, 80.479), (128.658, 77.979)], [(131.158, 80.479), (128.908, 78.229)]),
    ("Net-(R608-Pad1)", "F.Cu", [(125.358, 76.779), (127.058, 78.479), (133.358, 78.479)],
     [(125.358, 76.779), (127.329, 78.75), (133.087, 78.75), (133.358, 78.479)]),
    # GPIO1 / GPIO2 pair between D806 and D807 (the ESP32 USB pair runs 0.6 mm east, so there is
    # little room): GPIO1's via 0.1 mm along its bottom-layer diagonal (r 27.23 -> 27.14); GPIO2's via
    # up its own top-layer line to r 27.49, its bottom-layer loop round GPIO1's via pulled in from
    # r 27.8 to 27.6
    ("/ESP_GPIO1", "F.Cu", [(121.558, 109.479), (121.458, 109.579)], [(121.629, 109.408), (121.458, 109.579)]),
    ("/ESP_GPIO1", "B.Cu", [(123.358, 107.679), (121.558, 109.479)], [(123.358, 107.679), (121.629, 109.408)]),
    ("/ESP_GPIO2", "F.Cu", [(120.9966, 109.2674), (120.9966, 115.0202)], [(120.9966, 108.78), (120.9966, 115.0202)]),
    ("/ESP_GPIO2", "B.Cu", [(123.444, 108.3564), (121.8714, 109.929), (121.3716, 109.929), (120.9966, 109.5539),
                            (120.9966, 109.2674)],
     [(123.444, 108.3564), (121.9404, 109.86), (121.445, 109.86), (121.15, 109.565), (121.15, 108.9334),
      (120.9966, 108.78)]),
    # GPIO8 just before D804: its via 0.15 mm further in (GPIO6's top-layer line limits it) along its bottom-layer diagonal, so the
    # link can step in to D804's DIN between it and D804's VDD pad
    ("/ESP_GPIO8", "F.Cu", [(148.615, 126.122), (147.828, 126.922)], [(148.7641, 125.9729), (147.828, 126.922)]),
    ("/ESP_GPIO8", "B.Cu", [(150.658, 124.079), (148.658, 126.079)], [(150.658, 124.079), (148.7641, 125.9729)]),
]
VIA_MOVES = [("/ESP_GPIO8", (148.658, 126.079), (148.7641, 125.9729)),
             ("/ESP_UART_TX", (128.060085, 78.029), (128.310085, 78.279)),
             ("/ESP_UART_RX", (128.658, 77.979), (128.908, 78.229)),
             ("/ESP_GPIO1", (121.558, 109.479), (121.629, 109.408)),
             ("/ESP_GPIO2", (120.996551, 109.26739), (120.9966, 108.78))]

def polar(r, deg):
    a = math.radians(deg)
    return (CX + r * math.cos(a), CY + r * math.sin(a))


def angle_of(p):
    return math.degrees(math.atan2(p[1] - CY, p[0] - CX))


def radius(p):
    return math.dist(p, (CX, CY))


def link(dout, din, r_out=27.9, dive_end=1.4, dive_span=3.2):
    """Pieces ("seg", a, b) / ("arc", a, mid, b) from a DOUT pad centre to the next DIN's centre."""
    ad = angle_of(dout)
    an = angle_of(din)
    while an <= ad:
        an += 360.0
    ae = an - dive_end                     # dive ends here, then the short arc into DIN
    as_ = ae - dive_span                   # dive starts here
    q1 = polar(r_out, ad)
    q2 = polar(r_out, as_)
    q3 = polar(R_IN, ae)
    return [("seg", dout, q1),
            ("arc", q1, polar(r_out, (ad + as_) / 2), q2),
            ("seg", q2, q3),
            ("arc", q3, polar(R_IN, (ae + an) / 2), din)]


def samples(pieces, step=0.05):
    """Points along the pieces every ~step mm."""
    out = []
    for pc in pieces:
        if pc[0] == "seg":
            a, b = pc[1], pc[2]
            n = max(1, int(math.dist(a, b) / step))
            out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n + 1)]
        else:
            a, m, b = pc[1], pc[2], pc[3]
            r = radius(a)
            a0, a1 = angle_of(a), angle_of(b)
            while a1 <= a0:
                a1 += 360.0
            n = max(1, int(math.radians(a1 - a0) * r / step))
            out += [polar(r, a0 + (a1 - a0) * k / n) for k in range(n + 1)]
    return out


def clear(pieces, net, shapes):
    """True when the pieces keep CLR from every other net's bottom-layer copper and the ring."""
    pts = samples(pieces)
    if any(radius(p) + W / 2 + CLR > RING_IN for p in pts):
        return False
    near = [sh for sh in shapes if sh.net != net and "B.Cu" in sh.layers
            and not (sh.net == "+5V_LED" and sh.seg and sh.seg[2] > 1.2)]     # ring chords: tested above
    box = (min(p[0] for p in pts) - 1, min(p[1] for p in pts) - 1, max(p[0] for p in pts) + 1, max(p[1] for p in pts) + 1)
    near = [sh for sh in near if sh.box[0] < box[2] and sh.box[2] > box[0] and sh.box[1] < box[3] and sh.box[3] > box[1]]
    return all(sh.dist(*p) >= W / 2 + CLR + 0.005 for sh in near for p in pts)


def links(pad_centre, shapes):
    """[(net, pieces or None, (r_out, dive_end, dive_span))] for D801->D802 ... D811->D812.
    pad_centre(ref, pin) -> (x, y); shapes: copper laid so far (jog_router Shapes)."""
    out = []
    for i in range(1, 12):
        net = f"Net-(D8{i:02d}-DOUT)"
        dout, din = pad_centre(f"D8{i:02d}", 1), pad_centre(f"D8{i + 1:02d}", 3)
        got = None
        for r_out in R_OUTS:
            for de in DIVE_ENDS:
                for ds in DIVE_SPANS:
                    pcs = link(dout, din, r_out, de, ds)
                    if clear(pcs, net, shapes):
                        got = (pcs, (r_out, de, ds))
                        break
                if got:
                    break
            if got:
                break
        out.append((net, got[0] if got else link(dout, din), got[1] if got else None))
    return out


def nudge(tracks, vias):
    """Apply EDITS and VIA_MOVES to the user's snapshot (lists as tools/user_edits_2026_11_22.load
    gives them). Each old run must be found segment by segment, or the script stops."""
    def same(p, q):
        return math.dist(p, q) < 2e-3
    for net, layer, old, new in EDITS:
        hit = []
        for a, b in zip(old, old[1:]):
            k = [i for i, t in enumerate(tracks) if t[0] == "segment" and t[1] == net and t[2] == layer
                 and ((same(t[4][0], a) and same(t[4][1], b)) or (same(t[4][0], b) and same(t[4][1], a)))]
            if not k:
                raise SystemExit(f"led_arcs EDITS: {net} {layer} {a}-{b} not in the snapshot")
            hit.append(k[0])
        w = tracks[hit[0]][3]
        for i in sorted(hit, reverse=True):
            del tracks[i]
        tracks += [("segment", net, layer, w, [a, b]) for a, b in zip(new, new[1:])]
    for net, old, new in VIA_MOVES:
        k = [i for i, v in enumerate(vias) if v[0] == net and same(v[1], old)]
        if not k:
            raise SystemExit(f"led_arcs VIA_MOVES: {net} via {old} not in the snapshot")
        vias[k[0]] = (net, new, vias[k[0]][2])
    return tracks, vias
