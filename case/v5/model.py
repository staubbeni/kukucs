"""kukucs case v5: XIAO ESP32-S3 Sense + 15x40 mm cylinder LiPo + 10x10 mm salvaged button board.

The board is turned so the sensor's wide side runs left-right: pictures come out landscape.
Layout seen from the FRONT (lens side): board on the right, battery lying along the bottom on the left with the
shutter button above it. USB-C and the microSD slot are in the bottom wall.

Run:  python model.py            -> body.stl, lid.stl, cap.stl (print orientation) + case_assembled.step
Check: python check_fit.py <Seeed Sense .step>   (collision test against Seeed's official model)

Coordinates (assembled): origin = inner front-bottom-left corner of the cavity.
x -> right (seen from the front), y -> back (lens in the front wall, lid at the back), z -> up.
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
# Seeed model axes: x along the board (USB-C end at +x), y up through the stack (lens side +y), z across the board.
pcb_edge_x = 12.28   # XIAO PCB edge at the USB-C end (model x)
top_x = -8.98        # far end of the stack: expansion board edge (model x)
mz_min, mz_max = -15.01, 2.79   # board width range (model z)
lens_top_y = 13.71   # top of lens barrel = front of stack (model y)
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
board_w = mz_max - mz_min     # 17.8

# --- openings
lens_d = 5.0          # smaller than the ~6 mm barrel: the barrel rests on the wall
usb_hole = (9.6, 3.9)  # rounded slot around the 8.94 x 3.21 metal mouth (+0.33 per side)
pin_d = 1.6           # paperclip / SIM-tool hole for BOOT and RESET
pin_tube_od = 3.0     # guide tube behind the BOOT hole (RESET has none: the camera holder is in the way)
pin_tube_len = 5.0    # stops before the microSD card (card starts 5.46 behind the front)

# --- battery: cylinder lying along the bottom of the left half
bat_d = 15.0
bat_l = 40.0
bat_end = 2.5     # room at each battery end for its wires to bend (wires leave at both ends)

# --- shutter button: 10x10 PCB slides into rails under the top wall from the back (switch up),
#     a tab on the lid stops it sliding out; printed plunger cap through the top wall
btn_pcb = 10.0
btn_t = 1.6       # its PCB thickness
sw_h = 2.0        # switch height above its PCB  <- only remaining estimate
cap_w, cap_l, cap_r = 7.0, 4.5, 1.2   # rounded-rectangle plunger: width (x), length (y), corner radius
flange = 1.0      # cap flange under the top wall
flange_extra = 1.5  # flange sticks out this much past the plunger on every side
cap_out = 1.2     # how far the cap sticks out above the case
sw_off = (0.0, 0.0)  # switch position relative to its PCB centre (x, y), if not centred
rail_t = 1.2      # rail wall thickness
ledge = 1.0       # how far the rails reach under the PCB edges
btn_cx = 26.0     # shutter button position along the top (x)

# --- keychain tunnel: straight hole through the top-left corner, top face -> left face
kc_d = 2.5        # fits a split ring or a lanyard cord
kc_inset = 6.5    # how far the tunnel sits in from the corner (bigger = stronger bridge)
kc_block = (6.0, 7.0, 7.0)  # solid corner block inside the cavity: width (x), depth (y), height (z)

# --- antenna: flat 40 x 20 mm FPC strip (Seeed XIAO antenna, 1.13 mm coax) stuck on the inside of the lid, left half
ant_w, ant_h = 40.5, 20.5   # strip 40 x 20 plus margin
ant_t = 0.25                # strip + adhesive thickness
ant_x0 = 2.0                # left edge of the strip (x)
ant_margin = 0.5            # clear lid face above and below it, inside the lip ring

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
pad_h = 0.3                      # floor pads under the board's USB-end edge lift it off the floor
raise_ = usb_out + 0.2           # the board goes in from the back raised by this, then drops so USB-C seats in its slot
div_t = 1.2                      # wall between the battery and the board
div_y = 12.0                     # ...front part only; the back stays open for wires
right_gap = 3.0                  # room right of the board for the antenna cable and button wires

lw = bat_l + 2 * bat_end         # left half (battery) width
Xb = lw + div_t + tol            # board's left edge
X0 = Xb + mz_max                 # case x of model z = 0 (x grows as model z falls)
Z0 = pcb_edge_x + pad_h          # case z of model x = 0 (z grows as model x falls)
board_top_z = Z0 - top_x         # top edge of the board stack
iw = Xb + board_w + right_gap    # cavity width
ih = max(board_top_z + raise_ + tol,
         ant_h + 2 * (tol + lip_wall + ant_margin))   # cavity height: also tall enough for the antenna strip
id = stack_d + 2.5               # cavity depth (wires; antenna FPC sticks to the lid)
lip = id - stack_d - tol - 0.2   # lid lip depth, stops short of the board
xr = Xb + board_w                # board's right edge


def to_case(mx, my, mz):
    """Seeed model coords -> case coords: a 180 degree turn about the axis (1, 0, -1), then a shift."""
    return (X0 - mz, lens_top_y - my, Z0 - mx)


lens_x, _, lens_z = to_case(lens_c[0], 0, lens_c[1])
usb_x, usb_y, _ = to_case(0, usb_c[0], usb_c[1])
sd_x0, sd_x1 = X0 - card_z[1], X0 - card_z[0]
sd_y0, sd_y1 = lens_top_y - card_y[1], lens_top_y - card_y[0]
card_out = Z0 - card_x_max       # (negative) case z of the card's end
boot_x, _, boot_z = to_case(btn_boot[0], 0, btn_boot[1])
reset_x, _, reset_z = to_case(btn_reset[0], 0, btn_reset[1])

p0 = btn_pcb / 2 + tol                           # half slot width for the button PCB
dr_x = btn_cx                                    # drawer centre x
dr_y1 = id - lip - 0.3                           # drawer back end, before the lid lip
dr_y0 = dr_y1 - 2 * p0                           # button PCB front edge when pushed in
pcb_z0 = ih - flange - sw_h - btn_t              # button PCB bottom face
btn_x, btn_y = dr_x + sw_off[0], dr_y1 - p0 + sw_off[1]   # switch / cap position
bat_c = (bat_d / 2 + tol, bat_d / 2 + tol)       # battery axis (y, z)
ant_z0 = tol + lip_wall + ant_margin             # bottom edge of the antenna strip (z)
crush = tol                                      # ribs on the drawer rails reach this far toward the button PCB

assert sd_y0 > pin_tube_len, "pin guide tubes would hit the microSD card"
assert dr_y0 - rail_t > 0, "button drawer does not fit front-to-back"
assert dr_x - p0 - rail_t > kc_block[0], "button drawer runs into the keychain block"
assert dr_x + p0 + rail_t < lw, "button drawer runs into the divider"
assert pcb_z0 - rail_t > bat_c[1] + bat_d / 2 + 0.5, "button drawer sits on the battery"


def box(x0, y0, z0, x1, y1, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl(r, h, pnt, axis):
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(r, h, cq.Vector(*pnt), cq.Vector(*axis)))


def rrect(w, l, r, z0, h, cx, cy):
    """Rounded-rectangle prism with its bottom at z0."""
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy).rect(w, l).extrude(h)
            .edges("|Z").fillet(r))


# ============================================================
# BODY
# ============================================================
body = (box(-wall, -wall, -wall, iw + wall, id, ih + wall).edges("|Y").fillet(corner_r)
        .cut(box(0, 0, 0, iw, id + 1, ih)))

# wall between the battery and the board (front part only)
body = body.union(box(lw, 0, 0, lw + div_t, div_y, ih))

# floor pads under the PCB's USB-end edge; the USB-C slot and the lid tab hold the board in place
for px in (Xb + 0.5, Xb + board_w - 3.5):
    body = body.union(box(px, 12.9, -0.1, px + 3.0, 13.9, pad_h - 0.02))   # 0.02 under the PCB edge: coplanar faces confuse the fit check

# shutter button drawer: two rails with ledges + a front stop, open at the back
for sx in (-1, 1):
    wall_x = dr_x + sx * p0
    body = body.union(box(min(wall_x, wall_x + sx * rail_t), dr_y0 - rail_t, pcb_z0 - rail_t,
                          max(wall_x, wall_x + sx * rail_t), dr_y1, ih))
    body = body.union(box(min(wall_x, wall_x - sx * ledge), dr_y0 - rail_t, pcb_z0 - rail_t,
                          max(wall_x, wall_x - sx * ledge), dr_y1, pcb_z0))
body = body.union(box(dr_x - p0, dr_y0 - rail_t, pcb_z0 - rail_t, dr_x + p0, dr_y0, ih))
# crush ribs on the rails' inner faces hold the button PCB by friction (the lid has no tab here: that face is for the antenna)
for sx in (-1, 1):
    wall_x = dr_x + sx * p0
    for ry in (dr_y0 + 1.5, dr_y1 - 2.5):
        body = body.union(box(min(wall_x, wall_x - sx * crush), ry, pcb_z0, max(wall_x, wall_x - sx * crush), ry + 1.0, pcb_z0 + btn_t))

# battery cradle ribs (stop before the lid lip)
for rx in (8.0, lw - 10.0):
    rib = box(rx, 0, 0, rx + 2, id - lip - 0.5, 5.0)
    rib = rib.cut(cyl(bat_d / 2 + tol, 4, (rx - 1, bat_c[0], bat_c[1]), (1, 0, 0)))
    body = body.union(rib)

# pin guide tube behind the BOOT hole
body = body.union(cyl(pin_tube_od / 2, pin_tube_len, (boot_x, 0, boot_z), (0, 1, 0)))

# solid corner block for the keychain tunnel (top-left, against the front wall)
body = body.union(box(0, 0, ih - kc_block[2], kc_block[0], kc_block[1], ih))

# --- cuts
# lens: 45-degree outer chamfer so the frame doesn't vignette
body = body.cut(cq.Workplane("XY").add(cq.Solid.makeCone(lens_d / 2 + wall, lens_d / 2, wall + 0.02,
                                                        cq.Vector(lens_x, -wall - 0.01, lens_z), cq.Vector(0, 1, 0))))
# USB-C: rounded slot through the floor, metal mouth sits just inside the outer surface
body = body.cut(cq.Workplane("XY").workplane(offset=-wall - 1).center(usb_x, usb_y)
                .slot2D(usb_hole[0], usb_hole[1], 0).extrude(wall + 2))
# shallow recess in the floor for the camera holder overhang
cam_in = cam_x_max - pcb_edge_x - pad_h + tol
body = body.cut(box(X0 - cam_z[1] - tol, -0.01, -cam_in, X0 - cam_z[0] + tol, lens_top_y - cam_y_min + tol, 0.01))
# microSD slot through the floor: the card pokes out of it (the slot also lets you pull the card)
body = body.cut(box(sd_x0 - tol, sd_y0 - tol, -wall - 1, sd_x1 + tol, sd_y1 + tol, 1))
# BOOT / RESET pin holes through the front wall and tubes
for px, pz in ((boot_x, boot_z), (reset_x, reset_z)):
    body = body.cut(cyl(pin_d / 2, wall + pin_tube_len + 1, (px, -wall - 0.5, pz), (0, 1, 0)))
# keychain tunnel at 45 degrees through the top-left corner
kc_dir = (-(2 ** -0.5), 0, -(2 ** -0.5))
kc_mid = (-wall + kc_inset / 2, kc_block[1] / 2, ih + wall - kc_inset / 2)
body = body.cut(cyl(kc_d / 2, 30, tuple(m - 15 * d for m, d in zip(kc_mid, kc_dir)), kc_dir))
# shutter cap hole (rounded rectangle)
body = body.cut(rrect(cap_w + 2 * tol, cap_l + 2 * tol, cap_r + tol, ih - 1, wall + 2, btn_x, btn_y))
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
# two ribs press the board against the barrel/front wall; they sit at the board's edges (the centre stays free for
# the battery pads), above the D1/GND pins and below the antenna cable
for rx in (Xb + 1.5, xr - 3.5):
    lid = lid.union(box(rx, stack_d + 0.1, 9.5, rx + 2.0, id, 17.0))
# tab above the board's top edge: stops the board lifting out of its USB-C slot (it is only raised during assembly)
lid = lid.union(box(Xb + 3.5, 9.0, board_top_z + 0.1, Xb + 11.0, id, ih - 0.1))
# the left half of the lid face stays clear for the antenna strip (ant_x0, ant_z0, ant_w, ant_h): no battery rib
# (the battery has under 1 mm of slack front to back) and no button tab (friction ribs in the drawer instead)

# engraved name on the outside of the lid, reading correctly when seen from behind
if label:
    back = cq.Plane(origin=(iw / 2, id + wall, ih / 2), xDir=(-1, 0, 0), normal=(0, 1, 0))
    lid = lid.cut(cq.Workplane(back).text(label, label_size, -label_depth, combine=False, fontPath=label_font,
                                          halign="center", valign="center"))

# ============================================================
# CAP (printed flange-down): rounded-rectangle plunger with a flange under the top wall
# ============================================================
cap = (rrect(cap_w + 2 * flange_extra, cap_l + 2 * flange_extra, cap_r + flange_extra, 0, flange, 0, 0)
       .union(rrect(cap_w, cap_l, cap_r, 0, flange + wall + cap_out, 0, 0)))

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
    print(f"lens ({lens_x:.2f}, {lens_z:.2f})  usb ({usb_x:.2f}, {usb_y:.2f})  card pokes out {-card_out - wall:.2f} past the outer floor")
    print(f"BOOT ({boot_x:.2f}, {boot_z:.2f})  RESET ({reset_x:.2f}, {reset_z:.2f})  button ({btn_x:.2f}, {btn_y:.2f})")
