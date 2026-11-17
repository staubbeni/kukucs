"""Draws the inside face of the lid (seen from the front, like the front view: board on the right) with the antenna strip
and the cable route.  Usage: python antenna_route.py antenna_route.svg   (then: magick -density 100 in.svg out.png)"""
import sys
import model as m

K = 11                      # px per mm
PAD = 70
W, H = m.iw, m.ih
out = []
X = lambda x: PAD + K * x
Z = lambda z: PAD + 30 + K * (H - z)          # z up


def rect(x0, z0, x1, z1, cls, label=None, lx=None, lz=None, anchor='middle'):
    out.append(f'<rect class="{cls}" x="{X(x0):.1f}" y="{Z(z1):.1f}" width="{K*(x1-x0):.1f}" height="{K*(z1-z0):.1f}"/>')
    if label:
        out.append(f'<text x="{X(lx if lx is not None else (x0+x1)/2):.1f}" y="{Z(lz if lz is not None else (z0+z1)/2) + 4:.1f}" text-anchor="{anchor}">{label}</text>')


def poly(pts, cls):
    out.append(f'<polyline class="{cls}" points="{" ".join(f"{X(x):.1f},{Z(z):.1f}" for x, z in pts)}"/>')


# the lid face and its lip ring
rect(0, 0, W, H, 'face')
rect(m.tol + m.lip_wall, m.tol + m.lip_wall, W - m.tol - m.lip_wall, H - m.tol - m.lip_wall, 'ring')
# lid features that stand on the face
for rx in (m.Xb + 1.5, m.xr - 3.5):
    rect(rx, 9.5, rx + 2.0, 17.0, 'rib')
rect(m.Xb + 3.5, m.board_top_z + 0.1, m.Xb + 11.0, m.ih - 0.1, 'rib', 'tab', lz=(m.board_top_z + m.ih) / 2)
# battery wires (both ends run along the back of the battery at mid height)
rect(1.6, 6.9, m.Xb + 9, 8.7, 'wire', 'battery wires', lx=22, lz=7.8)
# antenna strip
rect(m.ant_x0, m.ant_z0, m.ant_x0 + m.ant_w, m.ant_z0 + m.ant_h, 'ant', 'antenna strip 40 × 20', lz=m.ant_z0 + m.ant_h / 2 - 3)
# things behind the lid face (dashed): battery, board, button drawer
rect(m.bat_end, m.tol, m.bat_end + m.bat_l, m.tol + m.bat_d, 'ghost', 'battery behind the strip', lz=4.0)
rect(m.Xb, m.pad_h, m.xr, m.board_top_z, 'ghost', 'board (behind)', lx=(m.Xb + m.xr) / 2, lz=4.5)
rect(m.dr_x - m.p0 - m.rail_t, m.pcb_z0 - m.rail_t, m.dr_x + m.p0 + m.rail_t, m.ih, 'ghost', 'button drawer', lz=m.ih - 1.0)
# u.FL connector position (between the boards, ~4.5 mm in front of the lid face)
ux0, ux1 = m.X0 - m.ufl[2][1], m.X0 - m.ufl[2][0]
uz0, uz1 = m.Z0 - m.ufl[0][1], m.Z0 - m.ufl[0][0]
rect(ux0, uz0, ux1, uz1, 'ufl', 'u.FL', lz=uz1 + 1.8)
# cable corridor and route
rect(m.ant_x0 + m.ant_w, 17.5, m.xr + 1.0, 20.5, 'corridor')
cx, cz = (ux0 + ux1) / 2, (uz0 + uz1) / 2
gap_x = m.xr + 0.5
feed = (m.ant_x0 + m.ant_w - 0.5, m.ant_z0 + m.ant_h - 1.5)
route = [(cx, cz), (gap_x, cz), (gap_x, 19.0), (feed[0] + 0.5, 19.0), feed]
poly(route, 'cable')
for (x, z), t in ((route[1], 'turns back'), (feed, 'solder end')):
    out.append(f'<circle class="dot" cx="{X(x):.1f}" cy="{Z(z):.1f}" r="4"/>')
out.append(f'<text x="{X(gap_x) + 10:.1f}" y="{Z(cz) + 4:.1f}" text-anchor="start">turns back</text>')
out.append(f'<text x="{X(gap_x) + 10:.1f}" y="{Z(cz) + 20:.1f}" text-anchor="start">past the board edge</text>')
out.append(f'<text x="{X(feed[0]) - 6:.1f}" y="{Z(feed[1]) - 10:.1f}" text-anchor="end">feed corner</text>')

# lengths
seg = [abs(gap_x - cx), 4.8, abs(gap_x - feed[0]), abs(19.0 - feed[1])]
to_strip = sum(seg)
along = 23.0
text = [f'cable: u.FL → right edge {seg[0]:.0f} mm, back to the lid face ≈{seg[1]:.0f} mm, across the back {seg[2]:.0f} mm, up to the strip {seg[3]:.0f} mm',
        f'≈ {to_strip:.0f} mm to the strip, + ≈ {along:.0f} mm along the strip (photo) = ≈ {to_strip + along:.0f} mm of the 80 mm cable: ≈ {80 - to_strip - along:.0f} mm of slack for an S-curve']
w, h = int(PAD * 2 + K * W + 130), int(PAD + 30 + K * H + 90)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
 svg{{background:#fff}} text{{font:13px sans-serif;fill:#222}}
 .face{{fill:#eef2f6;stroke:#1f4e79;stroke-width:1.2}} .ring{{fill:none;stroke:#7a8da0;stroke-width:1;stroke-dasharray:6 3}}
 .ghost{{fill:none;stroke:#9aa;stroke-width:1;stroke-dasharray:4 3}} .rib{{fill:#c9d6e3;stroke:#1f4e79;stroke-width:1}}
 .ant{{fill:#ffd9a8;stroke:#c26a00;stroke-width:1.5}} .ufl{{fill:#f6b3b3;stroke:#a30000;stroke-width:1.2}}
 .corridor{{fill:#d8f0d8;stroke:#2e7d32;stroke-width:1;stroke-dasharray:4 3}} .wire{{fill:#fff3b0;stroke:#b59b00;stroke-width:1}}
 .cable{{fill:none;stroke:#2e7d32;stroke-width:3;stroke-linejoin:round}} .dot{{fill:#2e7d32}}
</style>
<rect width="100%" height="100%" fill="#fff"/>
<text x="20" y="26" style="font-weight:bold;font-size:17px">kukucs case v5: inside face of the lid with the antenna strip and its cable</text>
<text x="20" y="46">seen from the front, like the front view: the board is on the right. Green = cable, orange = strip, yellow = battery wires</text>
{''.join(out)}
<text x="{PAD}" y="{PAD + 30 + K * H + 30:.0f}">{text[0]}</text>
<text x="{PAD}" y="{PAD + 30 + K * H + 52:.0f}">{text[1]}</text>
</svg>'''
open(sys.argv[1], 'w').write(svg)
print(w, h, f"to strip {to_strip:.1f} mm")
