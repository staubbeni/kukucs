"""Collision check of the v2 case against Seeed's official XIAO ESP32-S3 Sense model.
Usage: python check_fit.py "Seeed Studio XIAO-ESP32-S3-Sense.step"
(from https://files.seeedstudio.com/wiki/SeeedStudio-XIAO-ESP32S3/res/seeed-studio-xiao-esp32s3-sense-3d_model.zip)
"""
import sys
import cadquery as cq
import model as m

board = [s.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), 180)
          .translate(cq.Vector(m.bx + m.pcb_edge_x, m.lens_top_y, m.bz - m.pcb_low_z))
         for s in cq.importers.importStep(sys.argv[1]).solids().vals()]
bat = cq.Solid.makeCylinder(m.bat_d / 2, m.bat_l, cq.Vector((m.iw - m.bat_l) / 2, *m.bat_c), cq.Vector(1, 0, 0))
btn_pcb = cq.Solid.makeBox(m.btn_pcb, m.btn_pcb, m.btn_t, cq.Vector(m.dr_x - m.btn_pcb / 2, m.dr_y1 - m.tol - m.btn_pcb, m.pcb_z0))
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
                   ("button PCB vs cap", btn_pcb, cap), ("battery vs board", bat, board)):
    v = sum(overlap(a, x) for x in b) if isinstance(b, list) else overlap(a, b)
    print(f"{name}: {v:.4f} mm3")
    bad += v > 1e-3

# paperclip path: from the front wall to the top of each button
for name, (px, pz) in (("BOOT", (m.boot_x, m.boot_z)), ("RESET", (m.reset_x, m.reset_z))):
    depth = m.lens_top_y - m.btn_top_y
    pin = cq.Solid.makeCylinder(0.45, depth - 0.05, cq.Vector(px, 0, pz), cq.Vector(0, 1, 0))
    hits = [s for s in board if overlap(pin, s) > 1e-4]
    bb = [s.BoundingBox() for s in hits]
    print(f"{name} pin path ({depth:.1f} mm deep): " +
          ("clear" if not hits else "blocked by " + ", ".join(f"part x{b.xmin:.1f}..{b.xmax:.1f} y{b.ymin:.1f}..{b.ymax:.1f}" for b in bb)))
# assembly paths (lid off): board slides in from the back shifted right, then left into the USB-C hole;
# button PCB slides into its drawer from the back
shift = m.usb_out - m.bx + 0.1   # USB-C tip clears the left wall
# the microSD card goes in afterwards, from outside through its slot
card_bb = lambda s: s.BoundingBox().xmin < m.bx - 2 and s.BoundingBox().xmax - s.BoundingBox().xmin > 14
no_card = [s for s in board if not card_bb(s)]
assert len(no_card) == len(board) - 1, "could not find the microSD card in the model"
def board_at(dx, dy): return [s.translate(cq.Vector(dx, dy, 0)) for s in no_card]
for dy in (0.0, 2, 4, 6, 8, 12, 16, 20):
    v = sum(overlap(body, s) for s in board_at(shift, dy))
    if v > 1e-3:
        bad += 1; print(f"board insert path blocked at back-offset {dy} mm: {v:.3f} mm3")
        for x in board_at(shift, dy):
            c = body.intersect(x)
            if c.Volume() > 1e-3:
                b = c.BoundingBox(); print(f"   at x {b.xmin:.1f}..{b.xmax:.1f} y {b.ymin:.1f}..{b.ymax:.1f} z {b.zmin:.1f}..{b.zmax:.1f}")
for dx in (shift, shift * 0.66, shift * 0.33):
    v = sum(overlap(body, s) for s in board_at(dx, 0))
    if v > 1e-3: print(f"board slide-left blocked at {dx:.2f} mm: {v:.3f} mm3"); bad += 1
for dy in (1, 2, 4, 6):
    v = overlap(body, btn_pcb.translate(cq.Vector(0, dy, 0)))
    if v > 1e-3: print(f"button PCB drawer path blocked at {dy} mm: {v:.3f} mm3"); bad += 1
# wire routes (must stay free of body and lid):
_, uy0, uz0 = m.to_case(0, m.ufl[1][1], m.ufl[2][0]); _, uy1, uz1 = m.to_case(0, m.ufl[1][0], m.ufl[2][1])
routes = {
    # antenna coax from the u.FL out past the board's right end, then back to the lid
    "antenna cable": cq.Solid.makeBox(m.fr_x + m.frame_t + 0.5 - (m.bx + m.board_len - 1), m.id - uy0, uz1 - uz0 + 1,
                                      cq.Vector(m.bx + m.board_len - 1, uy0, uz0 - 0.5)),
    # switch wires leaving the top of the button PCB towards the back, under the cap flange
    "switch wires": cq.Solid.makeBox(6.0, m.id - 0.2 - (m.dr_y1 - 3), 1.0,
                                     cq.Vector(m.dr_x - 3, m.dr_y1 - 3, m.pcb_z0 + m.btn_t + 0.05)),
    # button wires from the drawer to the back of the board, above the key
    "button wires": cq.Solid.makeBox(m.dr_x - m.p0 - (m.bx + 2), m.id - 0.2 - (m.stack_d + 0.2), 1.5,
                                     cq.Vector(m.bx + 2, m.stack_d + 0.2, m.key_z1 + 0.5)),
    # solder joints on D1 / GND (2nd pin) on the back, both edges
    "D1/GND joints": cq.Solid.makeBox(3.0, 1.2, m.board_h, cq.Vector(m.bx + m.pcb_edge_x - m.pin2_x - 1.5, m.stack_d + 0.05, m.bz)),
    # wire from the battery's right end, along the battery's top-back to the left end
    "battery wire (right end)": cq.Solid.makeBox(m.iw - 3, m.id - 0.2 - (m.stack_d - 0.2), 1.8,
                                                 cq.Vector(1.5, m.stack_d - 0.2, m.bz - m.frame_t - 2.0)),
    # battery wires up the left end, behind the board ledge
    "battery wires": cq.Solid.makeBox(2.0, m.id - 0.2 - (m.stack_d - 0.3), m.bz - 4,
                                      cq.Vector(1.5, m.stack_d - 0.3, 3.0)),
}
for name, r in routes.items():
    v = overlap(r, body) + overlap(r, lid)
    print(f"{name} route: {'clear' if v < 1e-3 else f'BLOCKED {v:.2f} mm3'}")
    bad += v >= 1e-3
print("assembly paths checked")
print("FIT OK" if not bad else f"{bad} COLLISIONS")
