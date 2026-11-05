include </home/beni/Projects/mini-cam/case/v1/minicam_case.scad>
// cut sections through each outer wall, seen from outside
if (v == "front") projection(cut = true) rotate([-90, 0, 0]) translate([0, wall / 2, 0]) body();
if (v == "top")   projection(cut = true) translate([0, 0, -(ih + wall / 2)]) body();
if (v == "left")  projection(cut = true) rotate([0, 90, 0]) translate([wall / 2, 0, 0]) body();
if (v == "echo") echo(W = iw + 2 * wall, H = ih + 2 * wall, D = id + wall, LID = wall,
  lens_cx = wall + bx + lens_x, lens_cz = wall + bz + lens_z, lens_d = lens_d,
  btn_cx = wall + btn_x, btn_cy = wall + btn_y, btn_d = cap_d + 2 * tol,
  usb_cy = wall + usb_y, usb_cz = wall + bz + usb_z, usb_w = usb_w, usb_h = usb_h,
  sd_y0 = wall + sd_y[0] - tol, sd_y1 = wall + sd_y[1] + tol, sd_z0 = wall + bz + sd_z[0] - tol, sd_z1 = wall + bz + sd_z[1] + tol);
