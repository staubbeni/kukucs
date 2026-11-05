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
body, lid = m.body.val(), m.lid.val()
cap = m.cap.translate((m.btn_x, m.btn_y, m.ih - m.flange)).val()


def overlap(a, b):
    return a.intersect(b).Volume()


bad = 0
for name, part in (("body", body), ("lid", lid), ("cap", cap)):
    v = sum(overlap(part, s) for s in board)
    print(f"board vs {name}: {v:.4f} mm3")
    bad += v > 1e-3
for name, a, b in (("lid vs body", lid, body), ("cap vs body", cap, body), ("cap vs lid", cap, lid)):
    v = overlap(a, b)
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
print("FIT OK" if not bad else f"{bad} COLLISIONS")
