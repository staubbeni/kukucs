import re, sys
D = sys.argv[1]  # dir with front/top/left.svg and x.echo
v = dict((k, float(x)) for k, x in re.findall(r'(\w+) = ([\d.]+)', open(f'{D}/x.echo').read()))
paths = lambda n: ''.join(re.findall(r'<path[^>]*/>', open(f'{D}/{n}.svg').read(), re.S))
k = 7  # px per mm
W, H, Dp = v['W'], v['H'], v['D']
out = []
def line(x1, y1, x2, y2, cls='dim'): out.append(f'<line class="{cls}" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
def text(x, y, t, rot=0, anchor='middle'):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ''
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{tr}>{t}</text>')
def hdim(P, a1, a2, b, off, label=None):  # horizontal dimension between local a1..a2 at height b, offset px
    (x1, y), (x2, _) = P(a1, b), P(a2, b); yy = y + off
    line(x1, y, x1, yy + (4 if off > 0 else -4), 'ext'); line(x2, y, x2, yy + (4 if off > 0 else -4), 'ext')
    line(x1, yy, x2, yy, 'dim arrow'); text((x1 + x2) / 2, yy - 4, label or f'{abs(a2 - a1):.1f}')
def vdim(P, b1, b2, a, off, label=None):
    (x, y1), (_, y2) = P(a, b1), P(a, b2); xx = x + off
    line(x, y1, xx + (4 if off > 0 else -4), y1, 'ext'); line(x, y2, xx + (4 if off > 0 else -4), y2, 'ext')
    line(xx, y1, xx, y2, 'dim arrow'); text(xx - 5, (y1 + y2) / 2, label or f'{abs(b2 - b1):.1f}', -90)
def cross(P, a, b):
    x, y = P(a, b); line(x - 10, y, x + 10, y, 'ctr'); line(x, y - 10, x, y + 10, 'ctr')

# front view: origin bottom-left outer corner
FX, FY = 90, 110 + k * H
F = lambda a, b: (FX + k * a, FY - k * b)
out.append(f'<g class="part" transform="translate({FX},{FY}) scale({k}) translate(1.6,-1.6)">{paths("front")}</g>')
text(FX + k * W / 2, FY - k * H - 60, 'FRONT (lens side)', anchor='middle')
hdim(F, 0, W, 0, 45); vdim(F, 0, H, 0, -45)
cross(F, v['lens_cx'], v['lens_cz'])
hdim(F, 0, v['lens_cx'], H, -22); vdim(F, v['lens_cz'], H, W, 30)
lx, ly = F(v['lens_cx'], v['lens_cz']); text(lx - 12, ly + 42, f'lens hole Ø{v["lens_d"]:.0f}', anchor='start')

# left side view: front edge on the right
LXR, LY = FX + k * W + 110 + k * Dp + 20, FY
L = lambda e, b: (LXR - k * e, LY - k * b)
x0, y0 = L(Dp, H); out.append(f'<rect class="outline" x="{x0:.1f}" y="{y0:.1f}" width="{k*Dp:.1f}" height="{k*H:.1f}"/>')
out.append(f'<g class="part" transform="translate({LXR - 1.6 * k},{LY - 1.6 * k}) scale({k}) matrix(0,-1,1,0,0,0)">{paths("left")}</g>')
text(LXR - k * Dp / 2, LY - k * H - 60, 'LEFT SIDE (USB-C)', anchor='middle')
hdim(L, 0, Dp, 0, 45, f'{Dp:.1f} (+{v["LID"]:.1f} lid)'); vdim(L, 0, H, Dp, -45)
cross(L, v['usb_cy'], v['usb_cz'])
hdim(L, 0, v['usb_cy'], H, -22); vdim(L, 0, v['usb_cz'], 0, 30)
lx0, ly0 = L(Dp, 0)
text(lx0, ly0 + 85, f'big opening: USB-C, {v["usb_h"]:.0f} × {v["usb_w"]:.1f}', anchor='start')
text(lx0, ly0 + 105, f'narrow slot: microSD, {v["sd_y1"]-v["sd_y0"]:.1f} × {v["sd_z1"]-v["sd_z0"]:.1f}', anchor='start')
text(lx0, ly0 + 125, f'  ({v["sd_y0"]:.1f}–{v["sd_y1"]:.1f} from front, {v["sd_z0"]:.1f}–{v["sd_z1"]:.1f} from bottom)', anchor='start')

# top view: front edge at the bottom
TX, TY = FX, FY + 120 + k * Dp
T = lambda a, c: (TX + k * a, TY - k * c)
x0, y0 = T(0, Dp); out.append(f'<rect class="outline" x="{x0:.1f}" y="{y0:.1f}" width="{k*W:.1f}" height="{k*Dp:.1f}"/>')
out.append(f'<g class="part" transform="translate({TX},{TY}) scale({k}) translate(1.6,-1.6)">{paths("top")}</g>')
text(TX + k * W / 2, TY + 75, 'TOP (button)  ·  front edge at the bottom', anchor='middle')
hdim(T, 0, W, 0, 45); vdim(T, 0, Dp, 0, -45)
cross(T, v['btn_cx'], v['btn_cy'])
hdim(T, 0, v['btn_cx'], Dp, -22); vdim(T, 0, v['btn_cy'], W, 30)
bx_, by_ = T(v['btn_cx'], v['btn_cy']); text(bx_ - 14, by_ + 26, f'button hole Ø{v["btn_d"]:.1f}', anchor='end')

w, h = int(LXR + 200), int(TY + 110)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c0392b"/></marker></defs>
<style>
 svg{{background:#fff}} text{{font:14px sans-serif;fill:#222}}
 .outline{{fill:#fff;stroke:#1f4e79;stroke-width:1}} .part path{{fill:#9ec3e6;stroke:#1f4e79;stroke-width:0.15}}
 .dim{{stroke:#c0392b;stroke-width:1.2}} .arrow{{marker-start:url(#a);marker-end:url(#a)}}
 .ext{{stroke:#c0392b;stroke-width:0.6;opacity:.6}} .ctr{{stroke:#555;stroke-width:0.8;stroke-dasharray:3 2}}
</style>
<rect width="100%" height="100%" fill="#fff"/>
<text x="20" y="30" text-anchor="start" style="font-weight:bold;font-size:18px">mini-cam case body: all sizes in mm, measured from the outside edges</text>
{''.join(out)}
</svg>'''
open(sys.argv[2], 'w').write(svg)
print(w, h)
