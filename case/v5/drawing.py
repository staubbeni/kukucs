import re, sys
D = sys.argv[1]  # dir with front/top/bottom.svg and x.echo
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

# --- front view (seen from the lens side): origin bottom-left outer corner
FX, FY = 90, 110 + k * H
F = lambda a, b: (FX + k * a, FY - k * b)
out.append(f'<g class="part" transform="translate({FX},{FY}) scale({k}) translate(1.6,-1.6)">{paths("front")}</g>')
text(FX + k * W / 2, FY - k * H - 60, 'FRONT (seen from the lens side)', anchor='middle')
hdim(F, 0, W, 0, 45); vdim(F, 0, H, 0, -45)
cross(F, v['lens_cx'], v['lens_cz'])
hdim(F, v['lens_cx'], W, H, -22); vdim(F, 0, v['lens_cz'], W, 30)
for cx in (v['boot_cx'], v['reset_cx']): cross(F, cx, v['boot_cz'])
bx2, by2 = F(v['boot_cx'], v['boot_cz']); text(bx2, by2 - 14, 'BOOT')
rx2, ry2 = F(v['reset_cx'], v['boot_cz']); text(rx2, ry2 - 14, 'RESET')
lx, ly = F(v['lens_cx'], v['lens_cz']); text(lx, ly - 22, f'lens hole Ø{v["lens_d"]:.0f}')

# --- top view: front edge at the bottom
TX, TY = FX, FY + 120 + k * Dp
T = lambda a, c: (TX + k * a, TY - k * c)
x0, y0 = T(0, Dp); out.append(f'<rect class="outline" x="{x0:.1f}" y="{y0:.1f}" width="{k*W:.1f}" height="{k*Dp:.1f}"/>')
out.append(f'<g class="part" transform="translate({TX},{TY}) scale({k}) translate(1.6,-1.6)">{paths("top")}</g>')
text(TX + k * W / 2, TY + 75, 'TOP (shutter button)  ·  front edge at the bottom', anchor='middle')
hdim(T, 0, W, 0, 45); vdim(T, 0, Dp, 0, -45)
cross(T, v['btn_cx'], v['btn_cy'])
hdim(T, 0, v['btn_cx'], Dp, -22); vdim(T, 0, v['btn_cy'], W, 30)
bx_, by_ = T(v['btn_cx'], v['btn_cy']); text(bx_, by_ + 30, f'cap hole {v["btn_w"]:.1f} × {v["btn_l"]:.1f} (rounded)')

# --- bottom view: seen from below, front edge at the top, so left and right are swapped compared with the front view
BX, BY = FX, TY + 210
B = lambda a, c: (BX + k * a, BY + k * c)
x0, y0 = B(0, 0); out.append(f'<rect class="outline" x="{x0:.1f}" y="{y0:.1f}" width="{k*W:.1f}" height="{k*Dp:.1f}"/>')
out.append(f'<g class="part" transform="translate({BX},{BY}) scale({k}) translate({W - 1.6},1.6)">{paths("bottom")}</g>')
text(BX + k * W / 2, BY - 55, 'BOTTOM (seen from below)  ·  front edge at the top, left and right swapped', anchor='middle')
ux = W - v['usb_cx']                      # USB-C centre, measured from the left edge of this view
cross(B, ux, v['usb_cy'])
hdim(B, 0, ux, 0, -22); vdim(B, 0, v['usb_cy'], 0, -45)
sx0, sx1 = W - v['sd_x1'], W - v['sd_x0']
sdx, sdy = B((sx0 + sx1) / 2, (v['sd_y0'] + v['sd_y1']) / 2)
text(sdx + 95, sdy + 5, f'microSD slot {v["sd_x1"]-v["sd_x0"]:.1f} × {v["sd_y1"]-v["sd_y0"]:.1f}', anchor='start')
ucx, ucy = B(ux, v['usb_cy']); text(ucx + 95, ucy + 5, f'USB-C slot {v["usb_w"]:.1f} × {v["usb_h"]:.1f}', anchor='start')

# notes
nx, ny = FX + k * W + 40, FY - k * H
for i, t in enumerate([
        f'Outside {W:.1f} × {H:.1f} × {Dp + v["LID"]:.1f} mm ({Dp:.1f} body + {v["LID"]:.1f} lid)',
        f'Lens hole Ø{v["lens_d"]:.0f}; BOOT and RESET pin holes Ø{v["pin_d"]:.1f}',
        '(RESET only reachable with the SD card out)',
        f'Keychain: Ø{v["kc_d"]:.1f} tunnel through the top-left corner',
        'The microSD card sticks out 1.2 mm below the case',
        'Antenna: 40 × 20 mm strip on the inside of the lid, left half (see antenna_route.png)']):
    text(nx, ny + 20 * i, t, anchor='start')

w, h = int(FX + k * W + 520), int(BY + k * Dp + 60)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<defs><marker id="a" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#c0392b"/></marker></defs>
<style>
 svg{{background:#fff}} text{{font:14px sans-serif;fill:#222}}
 .outline{{fill:#fff;stroke:#1f4e79;stroke-width:1}} .part path{{fill:#9ec3e6;stroke:#1f4e79;stroke-width:0.15}}
 .dim{{stroke:#c0392b;stroke-width:1.2}} .arrow{{marker-start:url(#a);marker-end:url(#a)}}
 .ext{{stroke:#c0392b;stroke-width:0.6;opacity:.6}} .ctr{{stroke:#555;stroke-width:0.8;stroke-dasharray:3 2}}
</style>
<rect width="100%" height="100%" fill="#fff"/>
<text x="20" y="30" text-anchor="start" style="font-weight:bold;font-size:18px">kukucs case v5 body: all sizes in mm, measured from the outside edges</text>
{''.join(out)}
</svg>'''
open(sys.argv[2], 'w').write(svg)
print(w, h)
