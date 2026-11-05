"""Writes front/top/left wall sections as SVG + dimension values, for drawing.py."""
import sys, os
import cadquery as cq
import model as m

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
b = m.body.val()
BIG = 500


def face_on(axis, at):
    # keep the part of the body on the outside of the plane, take its faces lying in the plane
    lo = {"x": (-BIG, -BIG, -BIG), "y": (-BIG, -BIG, -BIG), "z": (-BIG, -BIG, -BIG)}[axis]
    size = [2 * BIG] * 3; i = "xyz".index(axis)
    if axis == "z":  # top: keep above the plane
        o = list(lo); o[i] = at; size[i] = BIG
    else:            # front / left: keep below the plane
        o = list(lo); size[i] = BIG + at
    half = b.intersect(cq.Solid.makeBox(*size, cq.Vector(*o)))
    return [f for f in half.Faces() if abs(getattr(f.Center(), axis) - at) < 1e-3]


def svg(faces, proj, name):
    d = []
    for f in faces:
        for w in [f.outerWire()] + f.innerWires():
            pts = [proj(w.positionAt(i / 400)) for i in range(401)]
            d.append("M " + " L ".join(f"{x:.3f},{y:.3f}" for x, y in pts) + " z")
    open(f"{out}/{name}.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg"><path d="{" ".join(d)}" fill-rule="evenodd"/></svg>')


svg(face_on("y", -m.wall / 2), lambda p: (p.x, -p.z), "front")
svg(face_on("z", m.ih + m.wall / 2), lambda p: (p.x, -p.y), "top")
svg(face_on("x", -m.wall / 2), lambda p: (p.z, -p.y), "left")
w = m.wall
vals = dict(W=m.iw + 2 * w, H=m.ih + 2 * w, D=m.id + w, LID=w,
            lens_cx=w + m.lens_x, lens_cz=w + m.lens_z, lens_d=m.lens_d,
            btn_cx=w + m.btn_x, btn_cy=w + m.btn_y, btn_d=m.cap_d + 2 * m.tol,
            usb_cy=w + m.usb_y, usb_cz=w + m.usb_z, usb_w=m.usb_hole[0], usb_h=m.usb_hole[1],
            sd_y0=w + m.card_y0 - m.tol, sd_y1=w + m.card_y1 + m.tol, sd_z0=w + m.card_z0 - m.tol, sd_z1=w + m.card_z1 + m.tol,
            boot_cx=w + m.boot_x, boot_cz=w + m.boot_z, reset_cz=w + m.reset_z, pin_d=m.pin_d,
            kc_d=m.kc_d)
open(f"{out}/x.echo", "w").write("ECHO: " + ", ".join(f"{k} = {v:.2f}" for k, v in vals.items()))
print(vals)
