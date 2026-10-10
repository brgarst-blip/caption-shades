#!/usr/bin/env python3
"""Caption Shades LED panel generator (Rev D geometry).

Writes one KiCad 8 board per panel (wearer's left and right), plus a placement
CSV and a preview image. Stage 1: board outline with see-through slots, every LED
and its decoupling capacitor placed, nets assigned, data chain ordered.
Not yet done: copper routing, the planes, the parts on the top tab.

Coordinates: millimetres in the front view used on the blueprint. x = 0 is the
centre seam, y = 0 is the bottom of the window, y = 55 its top. This script builds
the panel for x >= 0 and mirrors it for the other side.

Run: python3 gen_panel.py   (no dependencies beyond the standard library;
matplotlib is used for the preview if it is installed)
"""
import math, uuid, csv, os

OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------- design constants ----------------
ROWS = 14
WIN_H = 55.0                 # window height
PITCH_Y = WIN_H / ROWS       # 3.93 mm bar pitch
BAR = 1.4                    # bar height (copper board under each LED row)
PITCH_X = 1.8                # LED pitch along a bar
LED = 1.0                    # LED body (XL-1010RGBC-WS2812B, 1.0 x 1.0 mm)
SEAM = 0.25                  # each panel stops 0.25 mm short of the centre line
SEAM_SPINE = 1.1             # solid board along the seam, hidden behind the centre rib
RING = 2.0                   # solid board around the window, hidden under the frame rim
TAB_TOP = 59.0               # top edge of the parts tab, under the top rim
THICKNESS = 0.8

# ---------------- window outline (Rev D) ----------------
def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(1, n + 1):
        t = i / n; u = 1 - t
        out.append((u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
                    u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1]))
    return out

def arc(cx, cy, r, a0, a1, n=24):
    return [(cx + r*math.cos(math.radians(a0 + (a1 - a0)*i/n)), cy + r*math.sin(math.radians(a0 + (a1 - a0)*i/n))) for i in range(1, n + 1)]

def window_right():
    """Right half of the window, from the notch top at the seam round to the top centre."""
    p = [(0.0, 33.0)]
    p += bez((0, 33), (10, 33), (16.5, 26), (18, 15))
    p += bez((18, 15), (19, 9), (19.5, 0), (21, 0))
    p.append((52.5, 0.0))
    p += arc(52.5, 18, 18, -90, 0)
    p.append((70.5, 51.0))
    p += arc(66.5, 51, 4, 0, 90)
    p.append((0.0, 55.0))
    return p

WIN = window_right()

def crossings(poly, y):
    xs = []
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 <= y < y2) or (y2 <= y < y1):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    return sorted(xs)

def span(y):
    """Window x-span at height y for the right half (closed polygon incl. the seam edge)."""
    xs = crossings(WIN, y)
    return (max(xs[0], SEAM), xs[-1]) if len(xs) >= 2 else None

def span_both(y0, y1):
    a, b = span(y0), span(y1)
    if not a or not b: return None
    return (max(a[0], b[0]), min(a[1], b[1]))

# ---------------- board outline ----------------
def offset_notch():
    """Notch edge of the board: the window notch pushed RING mm into the nose opening."""
    pts = [(0.0, 33.0)] + bez((0, 33), (10, 33), (16.5, 26), (18, 15), 30) + bez((18, 15), (19, 9), (19.5, 0), (21, 0), 30)
    out = []
    for i, (x, y) in enumerate(pts):
        a = pts[max(0, i - 1)]; b = pts[min(len(pts) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]; L = math.hypot(tx, ty) or 1
        nx, ny = ty / L, -tx / L          # normal pointing into the nose opening
        out.append((x + nx * RING, y + ny * RING))
    return out

def outline_right():
    n = offset_notch()
    n = [(x, y) for (x, y) in n if y >= -RING]     # stop at the bottom edge line
    p = [(SEAM, TAB_TOP), (SEAM, n[0][1])]
    p += [(max(SEAM, x), y) for (x, y) in n]
    p.append((n[-1][0], -RING))
    p.append((52.5, -RING))
    p += arc(52.5, 18, 18 + RING, -90, 0)
    p.append((70.5 + RING, TAB_TOP - 2))
    p += arc(70.5 + RING - 2, TAB_TOP - 2, 2, 0, 90, 8)
    return p

def bar_centre(r):
    return WIN_H - (r + 0.5) * PITCH_Y

def slots_right():
    """See-through slots between neighbouring bars (13 per panel)."""
    out = []
    for r in range(ROWS - 1):
        top = bar_centre(r) - BAR / 2
        bot = bar_centre(r + 1) + BAR / 2
        s = span_both(bot + 0.01, top - 0.01)
        if not s: continue
        x0, x1 = max(s[0], SEAM_SPINE), s[1]
        if x1 - x0 > 1.0:
            out.append((x0, bot, x1, top))
    return out

# ---------------- LEDs and chain order ----------------
def leds_right():
    """LED centres, bar by bar, top bar first. Each bar runs seam->outer or outer->seam
    so the data chain snakes down the panel."""
    bars = []
    for r in range(ROWS):
        yc = bar_centre(r)
        s = span_both(yc - BAR / 2, yc + BAR / 2)
        row = []
        for k in range(40):
            x = 0.9 + k * PITCH_X
            if s and x - LED / 2 >= s[0] - 0.4 and x + LED / 2 <= s[1]:
                row.append((x, yc))
        if r % 2: row.reverse()
        bars.append((r, row))
    return bars

# ---------------- KiCad writer ----------------
def U(): return str(uuid.uuid4())
def f(v): return ('%.4f' % v).rstrip('0').rstrip('.')

class Board:
    def __init__(self, title):
        self.title, self.nets, self.items = title, [''], []
    def net(self, name):
        if name not in self.nets: self.nets.append(name)
        return self.nets.index(name), name
    def poly(self, pts, layer='Edge.Cuts', width=0.1):
        xy = ' '.join('(xy %s %s)' % (f(x), f(-y)) for x, y in pts)
        self.items.append('  (gr_poly (pts %s) (stroke (width %s) (type solid)) (fill none) (layer "%s") (uuid "%s"))' % (xy, f(width), layer, U()))
    def fp(self, lib, ref, value, x, y, rot, side, pads, lcsc=''):
        """pads: list of (number, dx, dy, w, h, netname)"""
        F = side == 'F'
        cu, paste, mask, silk, fab = ('%s.Cu' % side, '%s.Paste' % side, '%s.Mask' % side, '%s.SilkS' % side, '%s.Fab' % side)
        s = ['  (footprint "%s" (layer "%s") (uuid "%s") (at %s %s %s)' % (lib, cu, U(), f(x), f(-y), f(rot))]
        s.append('    (property "Reference" "%s" (at 0 0 %s) (layer "%s") (hide yes) (uuid "%s") (effects (font (size 0.3 0.3) (thickness 0.05))%s))' % (ref, f(rot), fab, U(), '' if F else ' (justify mirror)'))
        s.append('    (property "Value" "%s" (at 0 0 %s) (layer "%s") (hide yes) (uuid "%s") (effects (font (size 0.3 0.3) (thickness 0.05))%s))' % (value, f(rot), fab, U(), '' if F else ' (justify mirror)'))
        if lcsc:
            s.append('    (property "LCSC" "%s" (at 0 0 0) (layer "%s") (hide yes) (uuid "%s") (effects (font (size 0.3 0.3) (thickness 0.05))))' % (lcsc, fab, U()))
        s.append('    (attr smd)')
        for num, dx, dy, w, h, netname in pads:
            ni, nn = self.net(netname)
            s.append('    (pad "%s" smd roundrect (at %s %s %s) (size %s %s) (layers "%s" "%s" "%s") (roundrect_rratio 0.25) (net %d "%s") (uuid "%s"))' % (
                num, f(dx if F else -dx), f(-dy), f(rot), f(w), f(h), cu, paste, mask, ni, nn, U()))
        s.append('  )')
        self.items.append('\n'.join(s))
    def write(self, path):
        layers = '''  (layers
    (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" power) (31 "B.Cu" signal)
    (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen")
    (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments")
    (44 "Edge.Cuts" user) (45 "Margin" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard")
    (48 "B.Fab" user) (49 "F.Fab" user)
  )'''
        out = ['(kicad_pcb (version 20240108) (generator "caption_shades_gen_panel") (generator_version "0.1")',
               '  (general (thickness %s) (legacy_teardrops no))' % f(THICKNESS),
               '  (paper "A3")',
               '  (title_block (title "%s") (rev "D-1") (company "Caption Shades"))' % self.title,
               layers,
               '  (setup (pad_to_mask_clearance 0))']
        out += ['  (net %d "%s")' % (i, n) for i, n in enumerate(self.nets)]
        out += self.items
        out.append(')')
        open(path, 'w').write('\n'.join(out) + '\n')

# Pad layout for the LED. ASSUMED typical 1010 land pattern: 2 x 2 pads, 0.35 mm square
# at +/-0.3 mm. Pin numbering from the datasheet text: 1 DO, 2 VDD, 3 GND, 4 DI.
# Pad POSITIONS are not in the datasheet text we could read: replace these with LCSC's
# footprint for C5349953 before ordering.
LED_PADS = [('1', 0.3, 0.3, 'DO'), ('2', 0.3, -0.3, 'VDD'), ('3', -0.3, -0.3, 'GND'), ('4', -0.3, 0.3, 'DI')]

def build(side):
    """side 'R' = panel at x >= 0 in the front view; 'L' = its mirror image."""
    m = 1 if side == 'R' else -1
    name = 'Caption Shades panel %s' % ('A (x+)' if side == 'R' else 'B (x-)')
    b = Board(name)
    b.poly([(m * x, y) for x, y in outline_right()])
    for x0, y0, x1, y1 in slots_right():
        b.poly([(m * x0, y0), (m * x1, y0), (m * x1, y1), (m * x0, y1)])
    rows = []
    n = 0
    prev = 'DIN_%s' % side
    for r, row in leds_right():
        for x, y in row:
            n += 1
            ref = 'D%d' % n
            nxt = 'D%d_DO' % n
            # flip LEDs on reverse bars so DI faces the previous LED
            rev = (r % 2 == 1) != (side == 'L')
            rot = 180 if rev else 0
            nets = {'DO': nxt, 'VDD': '+5V_LED', 'GND': 'GND', 'DI': prev}
            b.fp('CaptionShades:LED_XL-1010_WS2812B', ref, 'XL-1010RGBC-WS2812B', m * x, y, rot, 'F',
                 [(num, dx, dy, 0.35, 0.35, nets[fn]) for num, dx, dy, fn in LED_PADS], 'C5349953')
            b.fp('Capacitor_SMD:C_0201_0603Metric', 'C%d' % n, '100nF', m * x, y, 90, 'B',
                 [('1', -0.32, 0, 0.36, 0.3, '+5V_LED'), ('2', 0.32, 0, 0.36, 0.3, 'GND')], 'C76939')
            rows.append((ref, 'C%d' % n, round(m * x, 3), round(y, 3), rot, r))
            prev = nxt
    b.write(os.path.join(OUT, 'panel_%s.kicad_pcb' % side))
    return rows, b

if __name__ == '__main__':
    summary = {}
    for side in ('R', 'L'):
        rows, b = build(side)
        summary[side] = len(rows)
        with open(os.path.join(OUT, 'placement_%s.csv' % side), 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['LED', 'Cap', 'x_mm', 'y_mm', 'rotation', 'bar'])
            w.writerows(rows)
    print('LEDs per panel:', summary, 'total', sum(summary.values()))
    print('slots per panel:', len(slots_right()))
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(14, 6), dpi=110)
        for side, m in (('R', 1), ('L', -1)):
            o = outline_right() + [outline_right()[0]]
            ax.fill([m * x for x, y in o], [y for x, y in o], color='#111418', zorder=1)
            for x0, y0, x1, y1 in slots_right():
                ax.fill([m * x0, m * x1, m * x1, m * x0], [y0, y0, y1, y1], color='#dfe6ee', zorder=2)
            for r, row in leds_right():
                ax.scatter([m * x for x, y in row], [y for x, y in row], s=2.2, marker='s', color='#f2efe6', zorder=3)
                if row:
                    ax.plot([m * x for x, y in row], [y for x, y in row], color='#3fa7ff', lw=0.35, zorder=2.5)
        w = WIN + [WIN[0]]
        for m in (1, -1):
            ax.plot([m * x for x, y in w], [y for x, y in w], color='#ff9f40', lw=0.8, ls='--', zorder=4)
        ax.set_aspect('equal'); ax.set_xlim(-76, 76); ax.set_ylim(-5, 61)
        ax.set_title('Caption Shades LED panels, Rev D-1: board (black), see-through slots (light), LEDs (dots), data chain (blue), window (orange dashes). Front view, mm.', fontsize=8)
        fig.tight_layout(); fig.savefig(os.path.join(OUT, 'preview.png'))
    except ImportError:
        pass
