/*
  Photo-based Project 360-style sanding block, visual prototype V4.
  Parametric S / M / L sizes. Units: mm.

  Visible pieces in the assembly:
    D-shaped black body + inset grey face + dark soft interface + white abrasive face
    blue two-arm adjustable yoke handle
    two blue pivot feet with black ribbed adjustment caps
    central black locking plate

  Geometry is estimated from the supplied photos; it is not a metrology scan.
  The metal pivot/fastening hardware is intentionally left as real purchased hardware.
*/

size = "M";             // [S, M, L]
part = "assembly";       // [assembly, base, face, pad, abrasive, pivot, handle, lock]
$fn = 72;

function width_for(s) = s == "S" ? 140 : s == "L" ? 220 : 180;
w = width_for(size);
r = w/2;
span = w*0.48;
pivot_y = r*0.36;
base_t = 8;
face_t = 1.8;
pad_t = 1.8;
abrasive_t = 0.9;
foot_t = 4;
eye_t = 4;
handle_t = 22;
M3_hole = 3.4;
M4_hole = 4.5;
M5_hole = 5.3;
pivot_z = base_t + face_t + foot_t + 8;

module d_outline(width) {
    rr = width/2;
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
          [for (i=[1:96]) [rr*cos(180*i/96),rr*sin(180*i/96)]]));
}

module rounded_2d(xlen,ylen,rad=2) {
    offset(r=rad) offset(delta=-rad) square([xlen,ylen],center=true);
}

module base_body(width) {
    rr=width/2;
    py=rr*0.36;
    s=width*0.48;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Four M3 mount holes for the two hinge feet; M3 nuts sit in bottom pockets.
        for (sx=[-1,1]) for (dx=[-7.5,7.5]) {
            translate([sx*s/2+dx,py,-0.1]) cylinder(h=base_t+0.2,d=M3_hole);
            translate([sx*s/2+dx,py,-0.01]) rotate([0,0,30])
                cylinder(h=2.8,d=6.5,$fn=6);
        }
        // Two small holes for the central black locking plate.
        for (x=[-12,12]) {
            translate([x,py,-0.1]) cylinder(h=base_t+0.2,d=M3_hole);
            translate([x,py,-0.01]) rotate([0,0,30])
                cylinder(h=2.8,d=6.5,$fn=6);
        }
    }
}

module face_body(width) {
    py=width/2*0.36;
    s=width*0.48;
    difference() {
        linear_extrude(height=face_t) d_outline(width-8);
        // Clearances leave the blue pivot soles and black centre lock exposed.
        for (sx=[-1,1])
            translate([sx*s/2,py,-0.1]) linear_extrude(height=face_t+0.2)
                rounded_2d(28,30,2);
        translate([0,py,-0.1]) linear_extrude(height=face_t+0.2)
            rounded_2d(46,32,3);
    }
}

module soft_pad_body(width) {
    linear_extrude(height=pad_t) d_outline(width-4);
}

module abrasive_body(width) {
    linear_extrude(height=abrasive_t) d_outline(width-7);
}

module pivot_body(width) {
    py=width/2*0.36;
    s=width*0.48;
    feet=[-s/2,s/2];
    difference() {
        union() {
            for (cx=feet) {
                // Compact blue sole at each end of the handle yoke.
                translate([cx,py,base_t]) linear_extrude(height=foot_t)
                    rounded_2d(25,28,2.5);
                // Clevis cheeks around the handle's two pivot eyes.
                for (side=[-1,1])
                    translate([cx-7,py+side*(handle_t/2+eye_t/2)-eye_t/2,
                               base_t+foot_t]) cube([14,eye_t,16]);
            }
        }
        for (cx=feet) for (dx=[-7.5,7.5])
            translate([cx+dx,py,base_t-0.1]) cylinder(h=foot_t+0.2,d=M3_hole);
        for (cx=feet)
            translate([cx,py,pivot_z]) rotate([90,0,0])
                cylinder(h=34,d=M5_hole,center=true);
    }
}

module handle_profile(width) {
    s=width*0.48;
    difference() {
        union() {
            // Short, gently swept arms down to the two pivot eyes.
            for (side=[-1,1]) hull() {
                translate([side*s/2,0]) circle(r=7.5);
                translate([side*(s/2-11),24]) circle(r=8.5);
            }
            // Thick rounded hand grip across the top of the yoke.
            hull() {
                translate([-s/2+11,25]) circle(r=9);
                translate([ s/2-11,25]) circle(r=9);
            }
            // Palm swell in the middle; small raised ribs mimic the moulded grip.
            hull() {
                translate([-19,25]) circle(r=9);
                translate([19,25]) circle(r=9);
            }
            for (k=[-3:3]) translate([k*4.5,33.1]) circle(r=0.9);
        }
        for (side=[-1,1]) translate([side*s/2,0]) circle(d=M5_hole);
    }
}

module handle_body(width) {
    // Print flat on the broad side; rotate into its upright position only in assembly.
    linear_extrude(height=handle_t) handle_profile(width);
}

module ribbed_cap() {
    difference() {
        union() {
            cylinder(h=7,d=18,center=true);
            for (a=[0:12:348]) rotate([0,0,a])
                translate([8.7,0,0]) cube([1.4,2.2,7],center=true);
        }
        cylinder(h=7.4,d=M5_hole,center=true);
    }
}

module lock_plate() {
    difference() {
        linear_extrude(height=5) rounded_2d(40,24,3);
        for (x=[-12,12]) translate([x,0,-0.1]) cylinder(h=5.2,d=M3_hole);
    }
}

module lock_body(width) {
    s=width*0.48;
    // Print layout: central lock plate and two ribbed caps rest flat on the build plate.
    lock_plate();
    for (cx=[-s/2,s/2]) translate([cx,0,3.5]) ribbed_cap();
}

module assembly_view(width) {
    py=width/2*0.36;
    s=width*0.48;
    zhinge=base_t+face_t+foot_t+8;
    color([0.12,0.14,0.16]) base_body(width);
    // Thin dark elastomer/backing layer and light replaceable abrasive sheet underneath.
    color([0.08,0.09,0.10]) translate([0,0,-pad_t]) soft_pad_body(width);
    color([0.88,0.87,0.82]) translate([0,0,-pad_t-abrasive_t]) abrasive_body(width);
    color([0.64,0.67,0.69]) translate([0,0,base_t]) face_body(width);
    color([0.02,0.28,0.88]) pivot_body(width);
    color([0.02,0.28,0.88])
        translate([0,py+handle_t/2,zhinge]) rotate([90,0,0]) handle_body(width);
    color([0.10,0.11,0.13]) {
        translate([0,py,base_t]) lock_plate();
        for (cx=[-s/2,s/2])
            translate([cx,py+handle_t/2+eye_t+3.5,pivot_z])
                rotate([90,0,0]) ribbed_cap();
    }
}

if (part=="base") {
    color([0.12,0.14,0.16]) base_body(w);
} else if (part=="face") {
    color([0.64,0.67,0.69]) face_body(w);
} else if (part=="pad") {
    color([0.08,0.09,0.10]) soft_pad_body(w);
} else if (part=="abrasive") {
    color([0.88,0.87,0.82]) abrasive_body(w);
} else if (part=="pivot") {
    color([0.02,0.28,0.88]) pivot_body(w);
} else if (part=="handle") {
    color([0.02,0.28,0.88]) handle_body(w);
} else if (part=="lock") {
    color([0.10,0.11,0.13]) lock_body(w);
} else {
    assembly_view(w);
}
