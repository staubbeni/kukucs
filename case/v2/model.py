"""mini-cam case v2: XIAO ESP32-S3 Sense + 15x40 mm cylinder LiPo + 10x10 mm salvaged button board.

Run:  python model.py            -> body.stl, lid.stl, cap.stl (print orientation) + case_assembled.step
Check: python check_fit.py <Seeed Sense .step>   (collision test against Seeed's official model)

Coordinates (assembled): origin = inner front-bottom-left corner of the cavity.
x -> right (USB-C on the left wall), y -> back (lens in the front wall, lid at the back), z -> up.
Print: body front-face down, lid plate down, cap flange down. No supports.
"""
import cadquery as cq

# ============================================================
# PARAMETERS (mm)
# ============================================================
wall = 1.6       # shell; 4 perimeters with a 0.4 nozzle
tol = 0.3        # clearance per side for parts that drop in
corner_r = 3.0   # outer corner radius around the front-back axis

# --- XIAO ESP32-S3 Sense stack (source: Seeed official 3D model, seeed-studio-xiao-esp32s3-sense-3d_model.zip)
# Seeed model axes: x along board (USB-C end at +x), y up through the stack, z across the board.
pcb_edge_x = 12.28   # XIAO PCB USB-C edge (model x)
pcb_low_z = -15.0    # XIAO PCB edge nearest the battery (model z)
lens_top_y = 13.71   # top of lens barrel = front of stack (model y)
board_len = 21.3     # PCB 20.95 + FPC connector overhang at the far end
board_h = 17.8       # PCB width
stack_d = 14.0       # lens top to XIAO back (model y -0.26 .. 13.71)
lens_c = (8.75, -6.75)        # lens centre (model x, z); barrel is ~6 mm across at the top
usb_c = (2.6, -6.12)          # USB-C mouth centre (model y, z); mouth is 8.94 x 3.21
card_x_max = 15.39            # inserted microSD card sticks out 3.1 mm past the PCB edge
card_y = (6.60, 8.25)         # card thickness range (model y)
card_z = (-12.52, -1.34)      # card width range (model z)
btn_boot = (10.71, -0.19)     # BOOT button centre (model x, z), top-push, 0.11 mm travel
btn_reset = (10.71, -12.04)   # RESET button centre; the microSD card sits over it
btn_top_y = 1.73              # button top (model y)
cam_x_max = 12.75             # camera holder overhangs the PCB USB-C edge by 0.47 mm
cam_y_min = 7.95              # camera holder bottom (model y)
cam_z = (-10.75, -2.75)       # camera holder width range (model z)

# --- openings
lens_d = 5.0          # smaller than the ~6 mm barrel: the barrel rests on the wall
usb_hole = (9.6, 3.9)  # rounded slot around the 8.94 x 3.21 metal mouth (+0.33 per side)
pin_d = 1.6           # paperclip / SIM-tool hole for BOOT and RESET
pin_tube_od = 3.0     # guide tube behind the BOOT hole (RESET has none: the camera holder is in the way)
pin_tube_len = 5.0    # stops before the microSD card (card starts 5.46 behind the front)

# --- battery: cylinder lying along the bottom
bat_d = 15.0
bat_l = 40.0

# --- shutter button: 10x10 PCB pushed up into a pocket under the top wall, printed plunger cap
btn_pcb = 10.0
btn_t = 1.6       # its PCB thickness
sw_h = 2.0        # switch height above its PCB  <- only remaining estimate
cap_d = 5.0
flange = 1.0      # cap flange under the top wall
cap_out = 1.2     # how far the cap sticks out above the case

# --- keychain lug on the right side, top corner, flush with the front face
lug_out = 8.0     # how far it sticks out from the right wall (tip)
lug_r = 4.0       # half height / end radius
lug_t = 4.0       # thickness (front-back)
lug_hole_d = 4.0  # fits a split ring or lanyard

# --- lid
lip_wall = 1.2
snap_r = 0.5      # snap ridge on the lid lip / groove in the body; set 0 for friction only
snap_in = 0.3     # snap interference
notch_w = 10.0    # fingernail notch to pry the lid off

# ============================================================
# DERIVED LAYOUT
# ============================================================
iw = bat_l + 3.0                 # cavity width
ih = bat_d + board_h + 1.5       # cavity height
id = stack_d + 2.5               # cavity depth (wires; antenna FPC sticks to the lid)
lip = id - stack_d - tol - 0.2   # lid lip depth, stops short of the board

bx = tol                         # PCB USB-C edge, just inside the left wall
bz = ih - board_h - tol          # board bottom edge; top edge against the top wall


def to_case(mx, my, mz):
    """Seeed model coords -> case coords (180 deg about z, then shift)."""
    return (bx + pcb_edge_x - mx, lens_top_y - my, bz - pcb_low_z + mz)


lens_x, _, lens_z = to_case(lens_c[0], 0, lens_c[1])
_, usb_y, usb_z = to_case(0, usb_c[0], usb_c[1])
card_out = card_x_max - pcb_edge_x - bx          # how far the card pokes past the inner wall
card_y0, card_y1 = lens_top_y - card_y[1], lens_top_y - card_y[0]
card_z0, card_z1 = bz - pcb_low_z + card_z[0], bz - pcb_low_z + card_z[1]
boot_x, _, boot_z = to_case(btn_boot[0], 0, btn_boot[1])
reset_x, _, reset_z = to_case(btn_reset[0], 0, btn_reset[1])

pocket_out = btn_pcb + 2 * tol + 2 * 1.2         # button pocket outer size
pocket_d = flange + sw_h + btn_t
btn_x = board_len + bx + tol + 1.2 + (iw - (board_len + bx + tol + 1.2)) / 2
btn_y = id - lip - 0.3 - pocket_out / 2          # pocket ends before the lid lip

assert card_y0 > pin_tube_len, "pin guide tubes would hit the microSD card"
assert btn_y - pocket_out / 2 > 0, "button pocket does not fit front-to-back"


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, h, pnt, axis):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*pnt), cq.Vector(*axis)))


# ============================================================
# BODY
# ============================================================
body = (box(-wall, -wall, -wall, iw + wall, id, ih + wall).edges("|Y").fillet(corner_r)
        .cut(box(0, 0, 0, iw, id + 1, ih)))

# board frame: right end and bottom edge (left/top are case walls); short so wires pass behind
frame_y = 8.0
fr_x = bx + board_len + tol
body = body.union(box(fr_x, 0, bz - 1.2, fr_x + 1.2, frame_y, ih))
body = body.union(box(0, 0, bz - 1.2, fr_x + 1.2, frame_y, bz))

# shutter button pocket hanging from the top wall
p0 = btn_pcb / 2 + tol
body = body.union(box(btn_x - p0 - 1.2, btn_y - p0 - 1.2, ih - pocket_d, btn_x + p0 + 1.2, btn_y + p0 + 1.2, ih)
                  .cut(box(btn_x - p0, btn_y - p0, ih - pocket_d - 1, btn_x + p0, btn_y + p0, ih)))

# battery cradle ribs (stop before the lid lip)
for rx in (8.0, iw - 10.0):
    rib = box(rx, 0, 0, rx + 2, id - lip - 0.5, 5.0)
    rib = rib.cut(cyl(bat_d / 2 + tol, 4, (rx - 1, bat_d / 2 + tol, bat_d / 2 + tol), (1, 0, 0)))
    body = body.union(rib)

# pin guide tube behind the BOOT hole
body = body.union(cyl(pin_tube_od / 2, pin_tube_len, (boot_x, 0, boot_z), (0, 1, 0)))

# keychain lug, flush with the front face so it prints on the bed
lug_z = ih - lug_r
lug_cx = iw + wall + lug_out - lug_r
lug = (box(iw, -wall, lug_z - lug_r, lug_cx, -wall + lug_t, lug_z + lug_r)
       .union(cyl(lug_r, lug_t, (lug_cx, -wall, lug_z), (0, 1, 0))))
lug = lug.cut(cyl(lug_hole_d / 2, lug_t + 2, (lug_cx, -wall - 1, lug_z), (0, 1, 0)))
body = body.union(lug)

# --- cuts
# lens: 45-degree outer chamfer so the frame doesn't vignette
body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCone(lens_d / 2 + wall, lens_d / 2, wall + 0.02,
                                                        cq.Vector(lens_x, -wall - 0.01, lens_z), cq.Vector(0, 1, 0))))
# USB-C: rounded slot, metal mouth sits just behind the outer surface
body = body.cut(cq.Workplane("YZ").workplane(offset=-wall - 1).center(usb_y, usb_z)
                .slot2D(usb_hole[0], usb_hole[1], 90).extrude(wall + 2))
# shallow recess in the left wall for the camera holder overhang
cam_in = cam_x_max - pcb_edge_x - bx + tol
body = body.cut(box(-cam_in, -0.01, bz - pcb_low_z + cam_z[0] - tol, 0.01, lens_top_y - cam_y_min + tol,
                    bz - pcb_low_z + cam_z[1] + tol))
# microSD card pokes through the left wall (slot also lets you pull the card)
body = body.cut(box(-wall - 1, card_y0 - tol, card_z0 - tol, 1, card_y1 + tol, card_z1 + tol))
# BOOT / RESET pin holes through the front wall and tubes
for px, pz in ((boot_x, boot_z), (reset_x, reset_z)):
    body = body.cut(cyl(pin_d / 2, wall + pin_tube_len + 1, (px, -wall - 0.5, pz), (0, 1, 0)))
# shutter cap hole
body = body.cut(cyl(cap_d / 2 + tol, wall + 2, (btn_x, btn_y, ih - 1), (0, 0, 1)))
# snap grooves in the top and bottom walls, where the lid lip sits
snap_y = id - lip / 2
if snap_r > 0:
    for gz in (0.0, ih):
        body = body.cut(cyl(snap_r, iw, (0, snap_y, gz), (1, 0, 0)))
# fingernail notch at the back edge of the bottom wall
body = body.cut(box(iw / 2 - notch_w / 2, id - 1.0, -wall - 1, iw / 2 + notch_w / 2, id + 1, 0.01))

# ============================================================
# LID
# ============================================================
lid = box(-wall, id, -wall, iw + wall, id + wall, ih + wall).edges("|Y").fillet(corner_r)
ring = (box(tol, id - lip, tol, iw - tol, id, ih - tol)
        .cut(box(tol + lip_wall, id - lip - 1, tol + lip_wall, iw - tol - lip_wall, id + 1, ih - tol - lip_wall)))
lid = lid.union(ring)
# snap ridges on the lip's top and bottom faces, reaching snap_in into the wall grooves
if snap_r > 0:
    for rz in (-snap_in + snap_r, ih + snap_in - snap_r):
        lid = lid.union(cyl(snap_r, iw - 2 * tol - 4, (tol + 2, snap_y, rz), (1, 0, 0)))
# two ribs press the board stack against the front wall (centre stays free for battery wires)
for rz in (bz + 0.5, ih - 2.5):
    lid = lid.union(box(bx + 3, stack_d + tol, rz, bx + board_len - 3, id, rz + 2))

# ============================================================
# CAP (printed flange-down)
# ============================================================
cap = (cq.Workplane("XY").circle(cap_d / 2 + 1.5).extrude(flange)
       .faces(">Z").workplane().circle(cap_d / 2).extrude(wall + cap_out))

# ============================================================
# EXPORT
# ============================================================
if __name__ == "__main__":
    opts = dict(tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(body.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, wall)), "body.stl", **opts)
    cq.exporters.export(lid.rotate((0, 0, 0), (1, 0, 0), -90).translate((0, 0, id + wall)), "lid.stl", **opts)
    cq.exporters.export(cap, "cap.stl", **opts)
    asm = cq.Assembly().add(body, name="body").add(lid, name="lid").add(
        cap.translate((btn_x, btn_y, ih - flange)), name="cap")
    asm.save("case_assembled.step")
    print(f"outside: {iw + 2 * wall:.1f} ({iw + 2 * wall + lug_out:.1f} incl. lug) x {ih + 2 * wall:.1f} x {id + 2 * wall:.1f} mm")
    print(f"lens ({lens_x:.2f}, {lens_z:.2f})  usb ({usb_y:.2f}, {usb_z:.2f})  card pokes out {card_out - wall:.2f} past the outer wall")
    print(f"BOOT ({boot_x:.2f}, {boot_z:.2f})  RESET ({reset_x:.2f}, {reset_z:.2f})  button ({btn_x:.2f}, {btn_y:.2f})")
