"""Collision check of the v5 case against Seeed's official XIAO ESP32-S3 Sense model.
Usage: python check_fit.py "Seeed Studio XIAO-ESP32-S3-Sense.step"
(from https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/seeed-studio-xiao-esp32s3-sense-3d_model.zip)
"""
import sys
import cadquery as cq
import model as m

raw = cq.importers.importStep(sys.argv[1]).solids().vals()
V = cq.Vector


def place(s, dy=0.0, dz=0.0):
    """Model frame -> case frame (180 deg about (1,0,-1), then shift); dy/dz move it for the assembly path."""
    return s.rotate(V(0, 0, 0), V(1, 0, -1), 180).translate(V(m.X0, m.lens_top_y + dy, m.Z0 + dz))


# the microSD card goes in afterwards, from outside through its slot: find it in the model frame
cards = [s for s in raw if s.BoundingBox().xmax > 15.0]
assert len(cards) == 1, "could not find the microSD card in the model"
board = [place(s) for s in raw]
no_card = [s for s in raw if s.BoundingBox().xmax <= 15.0]

bat = cq.Solid.makeCylinder(m.bat_d / 2, m.bat_l, V(m.bat_end, *m.bat_c), V(1, 0, 0))
ant = cq.Solid.makeBox(m.ant_w, m.ant_t, m.ant_h, V(m.ant_x0, m.id - m.ant_t, m.ant_z0))   # strip stuck on the lid's inner face
btn_pcb = cq.Solid.makeBox(m.btn_pcb, m.btn_pcb, m.btn_t, V(m.dr_x - m.btn_pcb / 2, m.dr_y1 - m.tol - m.btn_pcb, m.pcb_z0))
body, lid = m.body.val(), m.lid.val()
cap = m.cap.translate((m.btn_x, m.btn_y, m.ih - m.flange)).val()


def overlap(a, b):
    return a.intersect(b).Volume()


bad = 0
for name, part in (("body", body), ("lid", lid), ("cap", cap)):
    v = sum(overlap(part, s) for s in board)
    print(f"board vs {name}: {v:.4f} mm3")
    bad += v > 1e-3
for name, a, b in (("lid vs body", lid, body), ("cap vs body", cap, body), ("cap vs lid", cap, lid),
                   ("battery vs body", bat, body), ("battery vs lid", bat, lid),
                   ("button PCB vs body", btn_pcb, body), ("button PCB vs lid", btn_pcb, lid),
                   ("button PCB vs cap", btn_pcb, cap), ("battery vs board", bat, board),
                   ("button PCB vs board", btn_pcb, board),
                   ("antenna strip vs lid", ant, lid), ("antenna strip vs body", ant, body), ("antenna strip vs battery", ant, bat),
                   ("antenna strip vs board", ant, board)):
    v = sum(overlap(a, x) for x in b) if isinstance(b, list) else overlap(a, b)
    print(f"{name}: {v:.4f} mm3")
    bad += v > 1e-3

# paperclip path: from the front wall to the top of each button
for name, (px, pz) in (("BOOT", (m.boot_x, m.boot_z)), ("RESET", (m.reset_x, m.reset_z))):
    depth = m.lens_top_y - m.btn_top_y
    pin = cq.Solid.makeCylinder(0.45, depth - 0.05, V(px, 0, pz), V(0, 1, 0))
    hits = [s for s in board if overlap(pin, s) > 1e-4]
    bb = [s.BoundingBox() for s in hits]
    print(f"{name} pin path ({depth:.1f} mm deep): " +
          ("clear" if not hits else "blocked by " + ", ".join(f"part x{b.xmin:.1f}..{b.xmax:.1f} y{b.ymin:.1f}..{b.ymax:.1f}" for b in bb)))

# assembly path (lid off): the board goes in from the back raised, slides forward until the barrel meets the front
# wall, then drops so the USB-C seats in its slot
def blocked(dy, dz):
    return [(s, overlap(body, s)) for s in (place(r, dy, dz) for r in no_card) if overlap(body, s) > 1e-3]

for dy in (20, 16, 12, 8, 6, 4, 2, 0):
    hit = blocked(dy, m.raise_)
    if hit:
        bad += 1
        print(f"board insert path blocked at back-offset {dy} mm (raised {m.raise_:.2f}): {sum(v for _, v in hit):.3f} mm3")
        for s, _ in hit:
            c = body.intersect(s); b = c.BoundingBox()
            print(f"   at x {b.xmin:.1f}..{b.xmax:.1f} y {b.ymin:.1f}..{b.ymax:.1f} z {b.zmin:.1f}..{b.zmax:.1f}")
for dz in (m.raise_, m.raise_ * 0.66, m.raise_ * 0.33, 0.1):
    hit = blocked(0, dz)
    if hit:
        bad += 1
        print(f"board drop blocked at height {dz:.2f}: {sum(v for _, v in hit):.3f} mm3")
for dy in (1, 2, 4, 6):
    v = overlap(body, btn_pcb.translate(V(0, dy, 0)))
    if v > 1e-3: print(f"button PCB drawer path blocked at {dy} mm: {v:.3f} mm3"); bad += 1

# wire routes (must stay free of body and lid); the parts of a route inside the board are not tested
Xr, Y1, Y2 = m.xr, m.lens_top_y + 0.26 + 0.01, m.id - 0.2     # back face of the XIAO ... lid
pin_z = m.Z0 - m.pin2_x
fx = m.X0 - m.ufl[2][0]   # u.FL connector x (the cable leaves it towards the right)
routes = {
    # antenna coax: out of the gap between the boards past the board's right edge, then back to the lid
    "antenna cable": cq.Solid.makeBox(m.iw - 1.6 - (Xr + 0.1), Y2 - 10.0, 3.0, V(Xr + 0.1, 10.0, 18.0)),
    # switch wires leaving the top of the button PCB towards the back, under the cap flange
    "switch wires": cq.Solid.makeBox(6.0, m.id - 0.2 - (m.dr_y1 - 3), 1.0, V(m.dr_x - 3, m.dr_y1 - 3, m.pcb_z0 + m.btn_t + 0.05)),
    # button wires: over the top of the button PCB (above its lid tab, past the drawer rails), across the back of the
    # board under the board-top tab, then down both board edges to D1 / GND
    "button wires across": cq.Solid.makeBox(m.iw - 1.6 - (m.dr_x - 3), 0.9, 0.9, V(m.dr_x - 3, 14.3, m.board_top_z - 1.0)),
    "button wire down (left)": cq.Solid.makeBox(2.1, 1.1, m.board_top_z - (pin_z - 1.5), V(m.Xb - 0.8, Y1 + 0.1, pin_z - 1.5)),
    "button wire down (right)": cq.Solid.makeBox(2.1, 1.1, m.board_top_z - (pin_z - 1.5), V(Xr - 1.3, Y1 + 0.1, pin_z - 1.5)),
    # battery wires: both ends, along the back of the battery at mid height, on to the board's back
    "battery wire (left end)": cq.Solid.makeBox(m.bat_end - 0.85, m.id - m.ant_t - 7.0, 1.7, V(1.6, 7.0, 6.9)),
    "battery wires along the back": cq.Solid.makeBox(m.Xb + 9 - 1.6, m.id - m.ant_t - 15.35, 1.8, V(1.6, 15.35, 6.9)),
    "battery wire (right end)": cq.Solid.makeBox(1.5, m.id - m.ant_t - 7.0, 1.7, V(m.bat_end + m.bat_l + 0.05, 7.0, 6.9)),
    # antenna cable, second half: from the right gap across the back of the board to the strip's right end, in the
    # corridor above the lid ribs (z 17) and below the button wires (z 20.7), in front of the strip (y < id - 0.25)
    "antenna cable across the back": cq.Solid.makeBox(Xr + 1.0 - (m.ant_x0 + m.ant_w), 1.1, 3.0, V(m.ant_x0 + m.ant_w, 15.3, 17.5)),
}
for name, r in routes.items():
    v = overlap(r, body) + overlap(r, lid)
    print(f"{name} route: {'clear' if v < 1e-3 else f'BLOCKED {v:.2f} mm3'}")
    bad += v >= 1e-3
print("assembly paths checked")
print("FIT OK" if not bad else f"{bad} COLLISIONS")
