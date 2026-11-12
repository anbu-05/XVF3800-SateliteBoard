"""Tiny helper for drawing the MindSpeak block diagrams as standalone SVG files."""
from html import escape

STYLE = """
<style>
  .bg { fill: #ffffff; }
  text { font-family: 'Inter', 'Segoe UI', 'DejaVu Sans', Arial, sans-serif; fill: #1f2328; }
  .t  { font-size: 14px; font-weight: 600; }
  .s  { font-size: 11.5px; fill: #3d444d; }
  .xs { font-size: 10px; fill: #57606a; }
  .h1 { font-size: 20px; font-weight: 700; }
  .h2 { font-size: 13px; font-weight: 600; fill: #57606a; letter-spacing: 0.04em; }
  .wire { stroke: #57606a; stroke-width: 1.4; fill: none; }
  .wire.dash { stroke-dasharray: 5 4; }
  .wire.pwr { stroke: #0f766e; stroke-width: 2; }
  .wire.sig { stroke: #1d4ed8; }
  .wire.aud { stroke: #c2410c; }
  .wire.mcu { stroke: #7e22ce; }
  .wire.prg { stroke: #be185d; }
  .lbl { font-size: 10.5px; fill: #3d444d; }
  .box { stroke-width: 1.2; }
  .k-pwr  { fill: #e6f4f1; stroke: #0f766e; }
  .k-xvf  { fill: #e8efff; stroke: #1d4ed8; }
  .k-mcu  { fill: #f3e8ff; stroke: #7e22ce; }
  .k-aud  { fill: #fff1e8; stroke: #c2410c; }
  .k-mic  { fill: #e9f7e6; stroke: #2f7d1f; }
  .k-ui   { fill: #fff7db; stroke: #a16207; }
  .k-prg  { fill: #fde8f1; stroke: #be185d; }
  .k-gry  { fill: #f2f3f5; stroke: #6e7781; }
  .k-dnp  { fill: #ffffff; stroke: #6e7781; stroke-dasharray: 4 3; }
  .note   { fill: #fffbea; stroke: #d4a72c; stroke-width: 1; }
</style>
"""


class Svg:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = []
        self.title, self.desc = title, desc

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, cls="s", anchor="start", rot=None):
        tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
        self.add(f'<text class="{cls}" x="{x}" y="{y}" text-anchor="{anchor}" '
                 f'dominant-baseline="central"{tr}>{escape(s)}</text>')

    def box(self, x, y, w, h, title, lines=(), kind="gry", rx=8, title_cls="t"):
        """Rounded box with a bold title and smaller lines underneath, centred."""
        self.add(f'<rect class="box k-{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>')
        n = len(lines)
        # Stack title + lines vertically around the box centre.
        total = 18 + 15 * n
        top = y + h / 2 - total / 2 + 9
        if title:
            self.text(x + w / 2, top, title, title_cls, "middle")
        for i, ln in enumerate(lines):
            self.text(x + w / 2, top + 18 + 15 * i, ln, "s", "middle")

    def rect(self, x, y, w, h, kind="gry", rx=3):
        self.add(f'<rect class="box k-{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>')

    def note(self, x, y, w, lines, title=None):
        h = 14 + 15 * len(lines) + (18 if title else 0)
        self.add(f'<rect class="note" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>')
        yy = y + 14
        if title:
            self.text(x + 10, yy, title, "t")
            yy += 18
        for ln in lines:
            self.text(x + 10, yy, ln, "s")
            yy += 15
        return h

    def wire(self, pts, cls="", arrow=True, label=None, lpos=None, lanchor="middle"):
        d = "M" + " L".join(f"{x} {y}" for x, y in pts)
        m = ' marker-end="url(#ah)"' if arrow else ""
        self.add(f'<path class="wire {cls}" d="{d}"{m}/>')
        if label:
            if lpos is None:
                (x1, y1), (x2, y2) = pts[0], pts[1]
                lpos = ((x1 + x2) / 2, (y1 + y2) / 2 - 8)
            self.text(lpos[0], lpos[1], label, "lbl", lanchor)

    def legend(self, x, y, items, col_w=170):
        for i, (kind, name) in enumerate(items):
            xx = x + (i % 5) * col_w
            yy = y + (i // 5) * 20
            self.rect(xx, yy - 6, 14, 12, kind)
            self.text(xx + 20, yy, name, "xs")

    def save(self, path):
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" role="img">'
                f'<title>{escape(self.title)}</title><desc>{escape(self.desc)}</desc>{STYLE}'
                '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                'markerHeight="7" orient="auto-start-reverse"><path d="M1 1L9 5L1 9z" '
                'fill="#57606a"/></marker></defs>'
                f'<rect class="bg" x="0" y="0" width="{self.w}" height="{self.h}"/>')
        with open(path, "w") as f:
            f.write(head + "\n".join(self.parts) + "</svg>\n")
