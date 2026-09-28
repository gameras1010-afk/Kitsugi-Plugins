/*
  Project 360-inspired sanding block — visual prototype V3
  Parametric sizes S / M / L; all dimensions in millimetres.

  Components:
    base  : dark D-shaped back plate
    face  : separate inset grey top skin
    pivot : two compact clevis mounts
    handle: low U/yoke-shaped blue hand grip
    lock  : black center slider + two ribbed pivot caps

  IMPORTANT: visual/mechanical concept based on photos, not a measured scan.
  Use metal M4/M3 hardware at the pivots/mounts; do not rely on printed threads.
*/

size = "M";           // [S, M, L]
part = "assembly";     // [assembly, base, face, pivot, handle, lock]
$fn = 64;

function width_for(s) = s == "S" ? 140 : s == "L" ? 220 : 180;
w = width_for(size);
r = w/2;
span = w*0.48;
pivot_y = r*0.36;
base_t = 8;
face_t = 1.8;
foot_t = 4;
eye_t = 4;
handle_t = 14;
mount_clearance = 3.4;  // M3
pivot_clearance = 4.4;  // M4
pivot_z = base_t + face_t + foot_t + 8;

module d_outline(width) {
    rr = width/2;
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
          [for (i=[1:80]) [rr*cos(180*i/80),rr*sin(180*i/80)]]));
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
        // Four M3 mounting holes with recessed M3 nut pockets on the underside.
        for (sx=[-1,1]) for (dx=[-7.5,7.5]) {
            translate([sx*s/2+dx,py,-0.1]) cylinder(h=base_t+0.2,d=mount_clearance);
            translate([sx*s/2+dx,py,-0.01]) rotate([0,0,30])
                cylinder(h=2.8,d=6.5,$fn=6);
        }
    }
}

module face_body(width) {
    py=width/2*0.36;
    s=width*0.48;
    difference() {
        linear_extrude(height=face_t) d_outline(width-8);
        // Openings leave the blue feet and black center lock seated on the dark plate.
        for (sx=[-1,1])
            translate([sx*s/2,py,-0.1]) linear_extrude(height=face_t+0.2)
                rounded_2d(28,30,2);
        translate([0,py,-0.1]) linear_extrude(height=face_t+0.2)
            rounded_2d(44,30,2);
    }
}

module pivot_body(width) {
    py=width/2*0.36;
    s=width*0.48;
    feet=[-s/2,s/2];
    difference() {
        union() {
            for (cx=feet) {
                // Small separate-looking sole under each blue hinge.
                translate([cx,py,base_t]) linear_extrude(height=foot_t)
                    rounded_2d(25,28,2.5);
                // Fork/clevis leaves room for the handle end between the ears.
                for (side=[-1,1])
                    translate([cx-7,py+side*(handle_t/2+eye_t/2)-eye_t/2,
                               base_t+foot_t]) cube([14,eye_t,16]);
            }
        }
        // M3 holes through feet; screws fit the base nut pockets.
        for (cx=feet) for (dx=[-7.5,7.5])
            translate([cx+dx,py,base_t-0.1]) cylinder(h=foot_t+0.2,d=mount_clearance);
        // M4 pivot bores through clevises and matching handle ears.
        for (cx=feet)
            translate([cx,py,pivot_z]) rotate([90,0,0])
                cylinder(h=32,d=pivot_clearance,center=true);
    }
}

module handle_profile(width) {
    s=width*0.48;
    difference() {
        union() {
            // Two short rising arms
            for (side=[-1,1]) hull() {
                translate([side*s/2,0]) circle(r=6.5);
                translate([side*(s/2-8),18]) circle(r=6.5);
            }
            // Broad, rounded low cross-grip (U/yoke silhouette)
            hull() {
                translate([-s/2+8,18]) circle(r=6.5);
                translate([ s/2-8,18]) circle(r=6.5);
            }
            // Slight palm swell in the middle, kept low to match the reference.
            hull() {
                translate([-17,19]) circle(r=6.5);
                translate([17,19]) circle(r=6.5);
            }
            // Fine raised grip ribs, molded into the upper face of the handle.
            for (k=[-3:3]) translate([k*4,24.0]) circle(r=0.75);
        }
        for (side=[-1,1]) translate([side*s/2,0]) circle(d=pivot_clearance);
    }
}

module handle_body(width) {
    // Prints flat on this face; rotate only in the assembly view.
    linear_extrude(height=handle_t) handle_profile(width);
}

module ribbed_cap() {
    difference() {
        union() {
            cylinder(h=5,d=14,center=true);
            for (a=[0:15:345]) rotate([0,0,a])
                translate([6.8,0,0]) cube([1.3,2.0,5],center=true);
        }
        cylinder(h=5.4,d=pivot_clearance,center=true);
    }
}

module lock_body(width) {
    s=width*0.48;
    // Print layout: central block and the two caps all sit flat on the build plate.
    linear_extrude(height=5) rounded_2d(38,22,3);
    for (cx=[-s/2,s/2])
        translate([cx,0,2.5]) ribbed_cap();
}

module assembly_view(width) {
    py=width/2*0.36;
    zhinge=base_t+face_t+foot_t+8;
    s=width*0.48;
    color([0.12,0.14,0.16]) base_body(width);
    color([0.64,0.67,0.69])
        translate([0,0,base_t]) face_body(width);
    color([0.02,0.28,0.88]) pivot_body(width);
    color([0.02,0.28,0.88])
        translate([0,py+handle_t/2,zhinge]) rotate([90,0,0]) handle_body(width);
    color([0.10,0.11,0.13]) {
        translate([0,py,base_t+face_t]) linear_extrude(height=5)
            rounded_2d(38,22,3);
        for (cx=[-s/2,s/2])
            translate([cx,py+14,pivot_z]) rotate([90,0,0]) ribbed_cap();
    }
}

if (part=="base") {
    color([0.12,0.14,0.16]) base_body(w);
} else if (part=="face") {
    color([0.64,0.67,0.69]) face_body(w);
} else if (part=="pivot") {
    color([0.02,0.28,0.88]) pivot_body(w);
} else if (part=="handle") {
    color([0.02,0.28,0.88]) handle_body(w);
} else if (part=="lock") {
    lock_body(w);
} else {
    assembly_view(w);
}
