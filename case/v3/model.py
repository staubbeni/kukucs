"""mini-cam case v3: XIAO ESP32-S3 Sense + 15x40 mm cylinder LiPo + 10x10 mm salvaged button board.

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
pcb_low_z = -15.01   # XIAO PCB edge nearest the battery (model z)
lens_top_y = 13.71   # top of lens barrel = front of stack (model y)
board_len = 21.3     # PCB 20.95 + FPC connector overhang at the far end
board_h = 17.8       # PCB width
stack_d = 14.0       # lens top to XIAO back (model y -0.26 .. 13.71)
lens_c = (8.75, -6.75)        # lens centre (model x, z); barrel is ~6 mm across at the top
usb_c = (2.6, -6.12)          # USB-C mouth centre (model y, z); mouth is 8.94 x 3.21
usb_out = 13.81 - 12.28       # USB-C sticks out past the PCB edge (model x)
card_x_max = 15.39            # inserted microSD card sticks out 3.1 mm past the PCB edge
card_y = (6.60, 8.25)         # card thickness range (model y)
card_z = (-12.52, -1.34)      # card width range (model z)
btn_boot = (10.71, -0.19)     # BOOT button centre (model x, z), top-push, 0.11 mm travel
btn_reset = (10.71, -12.04)   # RESET button centre; the microSD card sits over it
btn_top_y = 1.73              # button top (model y)
ufl = ((-8.45, -5.45), (1.0, 2.25), (-12.39, -9.29))   # antenna u.FL connector on the XIAO, between the boards
pin2_x = 12.28 - 4.8          # D1 / GND (2nd castellated pin from the USB-C end), model x; wires soldered on the back
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

# --- shutter button: 10x10 PCB slides into rails under the top wall from the back (switch up),
#     a tab on the lid stops it sliding out; printed plunger cap through the top wall
btn_pcb = 10.0
btn_t = 1.6       # its PCB thickness
sw_h = 2.0        # switch height above its PCB  <- only remaining estimate
cap_d = 5.0
flange = 1.0      # cap flange under the top wall
cap_out = 1.2     # how far the cap sticks out above the case
sw_off = (0.0, 0.0)  # switch position relative to its PCB centre (x, y), if not centred
rail_t = 1.2      # rail wall thickness
ledge = 1.0       # how far the rails reach under the PCB edges

# --- keychain tunnel: straight hole through the top-right corner, top face -> right face
kc_d = 2.5        # fits a split ring or a lanyard cord
kc_inset = 6.5    # how far the tunnel sits in from the corner (bigger = stronger bridge)
kc_block = (6.0, 7.0, 7.0)  # solid corner block inside the cavity: width (x), depth (y), height (z)

# --- lid
lip_wall = 1.2
snap_r = 0.5      # snap ridge on the lid lip / groove in the body; set 0 for friction only
snap_in = 0.3     # snap interference
notch_w = 10.0    # fingernail notch to pry the lid off
label = "kukucs"  # engraved on the outside of the lid ("" = none)
label_size = 9.0  # font size
label_depth = 0.6 # engraving depth (lid plate is 1.6)
label_font = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"  # any .ttf with these letters

# ============================================================
# DERIVED LAYOUT
# ============================================================
frame_t = 1.2                    # board frame thickness
iw = bat_l + 3.0                 # cavity width
ih = tol + bat_d + tol + frame_t + board_h + tol   # battery, frame, board stacked bottom to top
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

fr_x = bx + board_len + tol                      # board frame, right end
p0 = btn_pcb / 2 + tol                           # half slot width for the button PCB
dr_x = fr_x + frame_t + 0.5 + rail_t + p0         # drawer centre x, right of the board frame
dr_y1 = id - lip - 0.3                           # drawer back end, before the lid lip
dr_y0 = dr_y1 - 2 * p0                           # button PCB front edge when pushed in
pcb_z0 = ih - flange - sw_h - btn_t              # button PCB bottom face
btn_x, btn_y = dr_x + sw_off[0], dr_y1 - p0 + sw_off[1]   # switch / cap position
bat_c = (bat_d / 2 + tol, bat_d / 2 + tol)       # battery axis (y, z)
kc_x0 = iw - kc_block[0]

assert card_y0 > pin_tube_len, "pin guide tubes would hit the microSD card"
assert dr_y0 - rail_t > 0, "button drawer does not fit front-to-back"
assert dr_x + p0 + rail_t < kc_x0, "button drawer runs into the keychain block"


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, h, pnt, axis):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*pnt), cq.Vector(*axis)))


# ============================================================
# BODY
# ============================================================
body = (box(-wall, -wall, -wall, iw + wall, id, ih + wall).edges("|Y").fillet(corner_r)
        .cut(box(0, 0, 0, iw, id + 1, ih)))

# board ledge under the board's bottom edge, along its full depth. The right-hand stop is a key on the lid:
# the board goes in from the back shifted right, slides left into the USB-C hole, and the lid key locks it there.
frame_y = stack_d - 0.5
body = body.union(box(0, 0, bz - frame_t, fr_x + frame_t, frame_y, bz))

# shutter button drawer: two rails with ledges + a front stop, open at the back
for sx in (-1, 1):
    wall_x = dr_x + sx * p0
    body = body.union(box(min(wall_x, wall_x + sx * rail_t), dr_y0 - rail_t, pcb_z0 - rail_t,
                          max(wall_x, wall_x + sx * rail_t), dr_y1, ih))
    body = body.union(box(min(wall_x, wall_x - sx * ledge), dr_y0 - rail_t, pcb_z0 - rail_t,
                          max(wall_x, wall_x - sx * ledge), dr_y1, pcb_z0))
body = body.union(box(dr_x - p0, dr_y0 - rail_t, pcb_z0 - rail_t, dr_x + p0, dr_y0, ih))

# battery cradle ribs (stop before the lid lip)
for rx in (8.0, iw - 10.0):
    rib = box(rx, 0, 0, rx + 2, id - lip - 0.5, 5.0)
    rib = rib.cut(cyl(bat_d / 2 + tol, 4, (rx - 1, bat_d / 2 + tol, bat_d / 2 + tol), (1, 0, 0)))
    body = body.union(rib)

# pin guide tube behind the BOOT hole
body = body.union(cyl(pin_tube_od / 2, pin_tube_len, (boot_x, 0, boot_z), (0, 1, 0)))

# solid corner block for the keychain tunnel (top-right, against the front wall)
body = body.union(box(kc_x0, 0, ih - kc_block[2], iw, kc_block[1], ih))

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
# keychain tunnel at 45 degrees through the top-right corner
kc_dir = (2 ** -0.5, 0, -(2 ** -0.5))
kc_mid = (iw + wall - kc_inset / 2, kc_block[1] / 2, ih + wall - kc_inset / 2)
body = body.cut(cyl(kc_d / 2, 30, tuple(m - 15 * d for m, d in zip(kc_mid, kc_dir)), kc_dir))
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
# notch in the lip's top side over the D1/GND pins: the top-edge solder joint sits right under the top wall
pin_cx = bx + pcb_edge_x - pin2_x
lid = lid.cut(box(pin_cx - 2.5, id - lip - 1, ih - tol - lip_wall - 0.5, pin_cx + 2.5, id - 0.01, ih + 1))
# two ribs press the board stack against the front wall (centre stays free for battery wires)
# ribs start past the D1/GND pins so they don't press on solder joints; centre stays free for the battery pads
rib_x0 = bx + (pcb_edge_x - pin2_x) + 2.5
for rz in (bz + 0.5, ih - 2.5):
    lid = lid.union(box(rib_x0, stack_d + 0.1, rz, bx + board_len - 3, id, rz + 2))
# key at the board's right end: stops the board sliding right, out of the USB-C hole
key_y0 = lens_top_y - 5.18 - 0.5   # just behind the front-most part at the board's right end (Sense PCB, model y 5.18)
# key height: above the antenna cable (leaves the u.FL towards the right end), below the button wires
key_z0 = bz - pcb_low_z + ufl[2][1] + 2.0
key_z1 = key_z0 + 4.0
lid = lid.union(box(fr_x, key_y0, key_z0, fr_x + frame_t, id, key_z1))
# rib that holds the battery against the cradle / front wall
lid = lid.union(box(4, bat_c[0] + bat_d / 2 + tol, bat_c[1] - 1, iw - 4, id, bat_c[1] + 1))
# tab that keeps the button PCB from sliding out of its drawer; only as tall as the PCB edge, so the
# switch wires (soldered to the switch's end tabs, on top of the PCB) leave above it towards the back
lid = lid.union(box(dr_x - p0 + 1, dr_y1 + 0.1, pcb_z0 - 0.5, dr_x + p0 - 1, id, pcb_z0 + btn_t))

# engraved name on the outside of the lid, reading correctly when seen from behind
if label:
    back = cq.Plane(origin=(iw / 2, id + wall, ih / 2), xDir=(-1, 0, 0), normal=(0, 1, 0))
    lid = lid.cut(cq.Workplane(back).text(label, label_size, -label_depth, combine=False, fontPath=label_font,
                                          halign="center", valign="center"))

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
    print(f"outside: {iw + 2 * wall:.1f} x {ih + 2 * wall:.1f} x {id + 2 * wall:.1f} mm")
    print(f"lens ({lens_x:.2f}, {lens_z:.2f})  usb ({usb_y:.2f}, {usb_z:.2f})  card pokes out {card_out - wall:.2f} past the outer wall")
    print(f"BOOT ({boot_x:.2f}, {boot_z:.2f})  RESET ({reset_x:.2f}, {reset_z:.2f})  button ({btn_x:.2f}, {btn_y:.2f})")
