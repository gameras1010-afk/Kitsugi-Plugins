/*
  Low-profile sanding block inspired by the user's reference photos.
  Parametric OpenSCAD concept; dimensions in mm.

  Three printable components:
    base  : semicircular sanding plate
    pivot : TWO compact clevis feet (one STL containing both feet)
    grip  : slim, gently raised cross-handle

  Select size S/M/L and part assembly/base/pivot/grip in Customizer.
  This is a revised visual concept; it is not a measured scan of the reference.
*/

size = "M";          // [S, M, L]
part = "assembly";    // [assembly, base, pivot, grip]
$fn = 64;

function body_width(s) = s == "S" ? 140 : s == "L" ? 220 : 180;
w = body_width(size);
r = w/2;
span = w*0.46;       // spacing between compact hinge feet
pivot_y = r*0.34;
base_t = 8;
foot_t = 4;
eye_t = 3;
grip_t = 12;
M3_clearance = 3.4;
M4_clearance = 4.4;

module d_outline(width) {
    rr = width/2;
    // Flat chord and rounded half-circle nose, with softened corners.
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
          [for (i=[1:80]) [rr*cos(180*i/80),rr*sin(180*i/80)]]));
}

module rounded_pad_2d(xlen,ylen,rad=2) {
    offset(r=rad) offset(delta=-rad) square([xlen,ylen],center=true);
}

module base_body(width) {
    rr=width/2;
    py=rr*0.34;
    s=width*0.46;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Four small M3 fastener holes; nuts are recessed from the underside.
        for (sx=[-1,1]) for (dx=[-7.5,7.5]) {
            translate([sx*s/2+dx,py,-0.1]) cylinder(h=base_t+0.2,d=M3_clearance);
            translate([sx*s/2+dx,py,-0.01]) rotate([0,0,30])
                cylinder(h=2.8,d=6.5,$fn=6);
        }
    }
}

module pivot_body(width) {
    py=width/2*0.34;
    s=width*0.46;
    foot_x=[-s/2,s/2];
    difference() {
        union() {
            // Two discrete low feet; no full-width platform under the handle.
            for (cx=foot_x) {
                translate([cx,py,base_t])
                    linear_extrude(height=foot_t) rounded_pad_2d(24,24,2.5);
                // Two small ears form a clevis around each end of the grip.
                for (side=[-1,1])
                    translate([cx-5,py+side*(grip_t/2+eye_t/2)-eye_t/2,
                               base_t+foot_t]) cube([10,eye_t,10]);
            }
        }
        // M3 fastening holes through each foot into the base's nut traps.
        for (cx=foot_x) for (dx=[-7.5,7.5])
            translate([cx+dx,py,base_t-0.1]) cylinder(h=foot_t+0.2,d=M3_clearance);
        // M4 pivot holes through the two clevis ears at each end.
        for (cx=foot_x)
            translate([cx,py,base_t+foot_t+5]) rotate([90,0,0])
                cylinder(h=30,d=M4_clearance,center=true);
    }
}

module grip_profile(width) {
    s=width*0.46;
    difference() {
        union() {
            // A low, slim paddle with a subtly lifted center — not a tall arch.
            hull() {
                translate([-s/2,0]) circle(r=5.8);
                translate([-s*0.19,7.5]) circle(r=6.8);
            }
            hull() {
                translate([s*0.19,7.5]) circle(r=6.8);
                translate([s/2,0]) circle(r=5.8);
            }
            hull() {
                translate([-s*0.19,7.5]) circle(r=6.8);
                translate([s*0.19,7.5]) circle(r=6.8);
            }
        }
        // M4 bolts pass through the grip ends and clevis ears.
        for (side=[-1,1]) translate([side*s/2,0]) circle(d=M4_clearance);
    }
}

module grip_body(width) {
    linear_extrude(height=grip_t) grip_profile(width);
}

module assembly_view(width) {
    py=width/2*0.34;
    zhinge=base_t+foot_t+5;
    color([0.16,0.18,0.20]) base_body(width);
    color([0.02,0.25,0.82]) pivot_body(width);
    // Stand the low-profile grip across the two feet; use M4 bolts in the real assembly.
    translate([0,py+grip_t/2,zhinge]) rotate([90,0,0])
        color([0.02,0.25,0.82]) grip_body(width);
}

if (part=="base") {
    color([0.16,0.18,0.20]) base_body(w);
} else if (part=="pivot") {
    color([0.02,0.25,0.82]) pivot_body(w);
} else if (part=="grip") {
    color([0.02,0.25,0.82]) grip_body(w);
} else {
    assembly_view(w);
}
