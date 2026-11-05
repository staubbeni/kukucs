// mini-cam case: XIAO ESP32-S3 Sense + 15x40 mm cylinder LiPo + 10x10 mm button board.
// All sizes in mm. Change a number, re-export. part = "body" | "lid" | "cap" | "all" (print layout) | "view"
part = "all";
$fn = 48;

wall = 1.6;   // shell thickness
tol  = 0.3;   // print clearance per side
r    = 3;     // outer corner radius

// XIAO + Sense stack, lens facing the front wall, USB-C facing the left wall.
// Numbers from Seeed's official 3D model (seeed-studio-xiao-esp32s3-sense-3d_model.zip).
pcb_w   = 21.3;  // board envelope along USB direction (PCB 20.95 + parts overhanging the far end)
pcb_h   = 17.8;
stack_d = 14;    // lens top to XIAO back
usb_out = 1.55;  // USB-C sticks out past the PCB edge
sd_out  = 3.1;   // microSD socket sticks out past the PCB edge, above the USB-C
sd_y    = [5.5, 7.1];    // microSD socket depth range, from the lens top
sd_z    = [2.0, 14.1];   // microSD socket range, from the board's bottom edge
lens_x  = 3.5;   // lens centre from the USB-C edge of the PCB
lens_z  = 8.25;  // lens centre from the board's bottom edge (the edge near the battery)
lens_d  = 5;     // hole in front wall; smaller than the lens barrel, so the barrel rests on the wall
usb_y   = 11.6;  // USB-C centre, back from the front inner wall
usb_z   = 8.9;   // USB-C centre from the board's bottom edge
usb_w   = 12.5;  // opening fits the plug's plastic body, so the plug goes in fully
usb_h   = 7;

// battery: cylinder lying along the bottom
bat_d = 15;
bat_l = 40;

// button: 10x10 PCB glued under the top wall, printed plunger cap through it
btn_pcb = 10;
btn_t   = 1.6;  // PCB thickness
sw_h    = 2;    // switch height above its PCB   <- MEASURE
cap_d   = 5;    // plunger diameter
flange  = 1;    // plunger flange under the top wall, keeps it from falling out

// interior
iw = bat_l + 3;
ih = bat_d + pcb_h + 1.5;
id = stack_d + 2.5;  // room behind the board for wires; antenna FPC sticks to the lid

bx = usb_out + tol;     // PCB's USB-C edge; USB-C face sits just inside the left wall
bz = ih - pcb_h - tol;  // board sits against the top wall
btn_x = pcb_w + 1 + (iw - pcb_w - 1) / 2;  // free space right of the board
btn_y = id / 2;

module rbox(w, d, h, rr) {  // box rounded around the y (front-back) axis
  hull() for (x = [rr, w - rr], z = [rr, h - rr])
    translate([x, 0, z]) rotate([-90, 0, 0]) cylinder(r = rr, h = d);
}

module body() {
  difference() {
    translate([-wall, -wall, -wall]) rbox(iw + 2 * wall, id + wall, ih + 2 * wall, r);
    cube([iw, id + 1, ih]);
    // lens, with a 45-degree outer chamfer so the frame doesn't vignette
    translate([bx + lens_x, -wall - 0.01, bz + lens_z]) rotate([-90, 0, 0])
      cylinder(d1 = lens_d + 2 * wall, d2 = lens_d, h = wall + 0.02);
    // USB-C
    translate([-wall - 1, usb_y - usb_h / 2, bz + usb_z - usb_w / 2]) cube([wall + 2, usb_h, usb_w]);
    // microSD socket pokes into the left wall; the slot also lets you swap the card
    translate([-wall - 1, sd_y[0] - tol, bz + sd_z[0] - tol]) cube([wall + 2, sd_y[1] - sd_y[0] + 2 * tol, sd_z[1] - sd_z[0] + 2 * tol]);
    // button plunger hole
    translate([btn_x, btn_y, ih - 1]) cylinder(d = cap_d + 2 * tol, h = wall + 2);
  }
  // board frame: right and bottom sides (left/top are the case walls), short so wires pass behind
  fy = 8;
  translate([bx + pcb_w + tol, 0, bz - 1.2]) cube([1.2, fy, ih - bz + 1.2]);
  translate([0, 0, bz - 1.2]) cube([bx + pcb_w + tol + 1.2, fy, 1.2]);
  // button pocket: PCB pushed up into it and hot-glued, switch facing up
  pd = flange + sw_h + btn_t;
  translate([btn_x, btn_y, ih - pd]) difference() {
    translate([-btn_pcb / 2 - tol - 1.2, -btn_pcb / 2 - tol - 1.2, 0]) cube([btn_pcb + 2 * tol + 2.4, btn_pcb + 2 * tol + 2.4, pd]);
    translate([-btn_pcb / 2 - tol, -btn_pcb / 2 - tol, -1]) cube([btn_pcb + 2 * tol, btn_pcb + 2 * tol, pd + 2]);
  }
  // battery cradle ribs
  for (x = [8, iw - 10]) difference() {
    translate([x, 0, 0]) cube([2, id, 5]);
    translate([x - 1, bat_d / 2 + tol, bat_d / 2 + tol]) rotate([0, 90, 0]) cylinder(d = bat_d + 2 * tol, h = 4);
  }
}

module lid() {
  lip = id - stack_d - tol - 0.2;  // stops short of the board stack
  translate([-wall, id, -wall]) rbox(iw + 2 * wall, wall, ih + 2 * wall, r);
  // friction lip that slides into the body, notched around the USB-C plug
  difference() {
    translate([0, id - lip, 0]) difference() {
      translate([tol, 0, tol]) cube([iw - 2 * tol, lip, ih - 2 * tol]);
      translate([tol + 1.2, -1, tol + 1.2]) cube([iw - 2 * tol - 2.4, lip + 2, ih - 2 * tol - 2.4]);
    }
    translate([-1, usb_y - usb_h / 2, bz + usb_z - usb_w / 2]) cube([bx + 1, id, usb_w]);
  }
  // two ribs along the board's long edges press the stack against the front wall
  // (centre left free: battery pads and wires are on the XIAO's back)
  for (z = [bz + 0.5, ih - 2.5])
    translate([bx + 3, stack_d + tol, z]) cube([pcb_w - 6, id - stack_d - tol, 2]);
}

module cap() {  // printed flange-down
  cylinder(d = cap_d + 3, h = flange);
  cylinder(d = cap_d, h = flange + wall + 1.2);  // sticks out 1.2 mm
}

if (part == "body") rotate([90, 0, 0]) translate([0, wall, 0]) body();
if (part == "lid")  translate([0, 0, id + wall]) rotate([-90, 0, 0]) lid();
if (part == "cap")  cap();
if (part == "all") {  // everything laid out on the bed
  translate([0, 0, wall]) rotate([90, 0, 0]) body();
  translate([iw + 10, 0, id + wall]) rotate([-90, 0, 0]) translate([0, 0, -ih]) lid();
  translate([-12, 10, 0]) cap();
}
if (part == "view") {  // assembled, lid pulled back
  color("SteelBlue") body();
  color("LightSteelBlue") translate([0, 12, 0]) lid();
  color("Orange") translate([btn_x, btn_y, ih - flange]) cap();
}
