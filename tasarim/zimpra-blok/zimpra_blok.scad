/*
  Photo-based 360 sanding block — V7 hand-clearance prototype.
  The D-shaped sanding head has a raised blue cross-handle parallel to its straight edge.
  The arch has a deliberately open gap below it for fingers/hand grip.
  Parametric S/M/L; dimensions are sensible estimates from the reference photos.
*/

size = "M"; // [S, M, L]
part = "assembly"; // [assembly, base, face, pad, abrasive, trim, pivot, handle, lock, knob, label]
$fn = 72;

function width_for(s) = s == "S" ? 140 : s == "L" ? 220 : 180;
w = width_for(size);
r = w/2;
base_t = 8;
face_t = 1.6;
pad_t = 1.6;
abrasive_t = 0.9;
trim_t = 2.2;
foot_t = 3;
eye_t = 4;
handle_t = 22;
handle_span = w*0.50;
pivot_y = r*0.42;
foot_top = base_t+face_t+trim_t+foot_t;
pivot_z = foot_top+7.5;  // handle eyes rest on the feet; about 35 mm clearance below the grip
M3_insert_bore = 4.2;
M3_clearance = 3.4;
M5_pivot_hole = 5.3;

module d_outline(width) {
    rr=width/2;
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
          [for (i=[1:96]) [rr*cos(180*i/96),rr*sin(180*i/96)]]));
}

module rounded_2d(xlen,ylen,rad=3) {
    offset(r=rad) offset(delta=-rad) square([xlen,ylen],center=true);
}

module base_body(width) {
    rr=width/2;
    span=width*0.50;
    py=rr*0.42;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Four vertical M3 insert seats fastening the two white/blue feet.
        for (cx=[-span/2,span/2]) for (dx=[-8,8])
            translate([cx+dx,py,1.7]) cylinder(h=base_t-1.6,d=M3_insert_bore);
        // Two central M3 inserts for the black locking plate.
        for (dx=[-16,16])
            translate([dx,py,2]) cylinder(h=base_t-1.9,d=M3_insert_bore);
    }
}

module face_body(width) {
    rr=width/2;
    span=width*0.50;
    py=rr*0.42;
    difference() {
        linear_extrude(height=face_t) d_outline(width-8);
        for (cx=[-span/2,span/2]) for (dx=[-8,8])
            translate([cx+dx,py,-0.1]) cylinder(h=face_t+0.2,d=3.8);
        for (dx=[-16,16])
            translate([dx,py,-0.1]) cylinder(h=face_t+0.2,d=3.8);
    }
}

module pad_body(width) {
    linear_extrude(height=pad_t) d_outline(width-4);
}

module abrasive_body(width) {
    linear_extrude(height=abrasive_t) d_outline(width-7);
}

module trim_body(width) {
    rr=width/2;
    span=width*0.50;
    py=rr*0.42;
    difference() {
        union() {
            translate([-span/2,py]) rounded_2d(30,34,8);
            translate([ span/2,py]) rounded_2d(30,34,8);
        }
        for (cx=[-span/2,span/2]) for (dx=[-8,8])
            translate([cx+dx,py]) circle(d=3.8);
    }
}

module pivot_body(width) {
    rr=width/2;
    span=width*0.50;
    py=rr*0.42;
    feet=[-span/2,span/2];
    difference() {
        union() {
            for (cx=feet) {
                translate([cx,py,base_t+face_t+trim_t])
                    linear_extrude(height=foot_t) rounded_2d(26,30,3);
                // Fork ears leave room for the thick handle ends between them.
                for (side=[-1,1])
                    translate([cx-7,py+side*(handle_t/2+eye_t/2)-eye_t/2,foot_top])
                        cube([14,eye_t,15]);
            }
        }
        for (cx=feet) for (dx=[-8,8])
            translate([cx+dx,py,base_t+face_t-0.1]) cylinder(h=trim_t+foot_t+0.2,d=M3_clearance);
        for (cx=feet)
            translate([cx,py,pivot_z]) rotate([90,0,0])
                cylinder(h=36,d=M5_pivot_hole,center=true);
    }
}

module handle_profile(width) {
    span=width*0.50;
    difference() {
        union() {
            for (side=[-1,1]) translate([side*span/2,0]) circle(r=7.5);
            // Swept arms rise from the pivot eyes to the hand grip.
            for (side=[-1,1]) hull() {
                translate([side*span/2,0]) circle(r=7.5);
                translate([side*(span/2-10),29]) circle(r=8.5);
            }
            // Rounded, broad cross-grip; its underside is about 35 mm above the face.
            hull() {
                translate([-span/2+10,32]) circle(r=9.5);
                translate([ span/2-10,32]) circle(r=9.5);
            }
            hull() {
                translate([-14,32]) circle(r=9.5);
                translate([14,32]) circle(r=9.5);
            }
        }
        for (side=[-1,1]) translate([side*span/2,0]) circle(d=M5_pivot_hole);
    }
}

module handle_body(width) {
    // Printed flat on its broad side; erected above the head in assembly.
    linear_extrude(height=handle_t) handle_profile(width);
}

module lock_plate() {
    difference() {
        linear_extrude(height=trim_t) rounded_2d(42,25,3.5);
        for (dx=[-16,16]) translate([dx,0,-0.1]) cylinder(h=trim_t+0.2,d=M3_clearance);
    }
}

module lock_body(width) { lock_plate(); }

module ribbed_knob() {
    difference() {
        union() {
            cylinder(h=7,d=17,center=true);
            for (a=[0:12:348]) rotate([0,0,a])
                translate([8.2,0,0]) cube([1.4,2.0,7],center=true);
        }
        cylinder(h=7.4,d=M5_pivot_hole,center=true);
    }
}

module label_profile() {
    translate([-10,0]) text("project",size=4.2,font="Arial:style=Bold",halign="center",valign="center");
    translate([11,0]) text("360",size=10,font="Arial:style=Bold",halign="center",valign="center");
}

module label_body() {
    linear_extrude(height=0.45) label_profile();
}

module assembly_view(width) {
    rr=width/2;
    span=width*0.50;
    py=rr*0.42;
    top=base_t+face_t;
    grip_top=pivot_z+41.5;
    color([0.11,0.13,0.15]) base_body(width);
    color([0.07,0.08,0.09]) translate([0,0,-pad_t]) pad_body(width);
    color([0.91,0.89,0.82]) translate([0,0,-pad_t-abrasive_t]) abrasive_body(width);
    color([0.62,0.65,0.67]) translate([0,0,base_t]) face_body(width);
    color([0.90,0.91,0.90]) translate([0,0,top]) linear_extrude(height=trim_t) trim_body(width);
    color([0.02,0.28,0.88]) pivot_body(width);
    // Raised bridge runs across the D head; the opening below it is sized for a hand grip.
    translate([0,py+handle_t/2,pivot_z]) rotate([90,0,0])
        color([0.02,0.28,0.88]) handle_body(width);
    color([0.12,0.13,0.14]) translate([0,py,top]) lock_plate();
    for (cx=[-span/2,span/2])
        translate([cx,py+handle_t/2+eye_t+3.5,pivot_z]) rotate([90,0,0])
            color([0.08,0.09,0.10]) ribbed_knob();
    translate([0,py,grip_top]) color([0.98,0.98,0.96]) label_body();
    for (dx=[-16,16]) translate([dx,py,top+trim_t])
        color([0.03,0.03,0.03]) cylinder(h=1.1,d=4.5);
}

if (part=="base") {
    color([0.11,0.13,0.15]) base_body(w);
} else if (part=="face") {
    color([0.62,0.65,0.67]) face_body(w);
} else if (part=="pad") {
    color([0.07,0.08,0.09]) pad_body(w);
} else if (part=="abrasive") {
    color([0.91,0.89,0.82]) abrasive_body(w);
} else if (part=="trim") {
    color([0.90,0.91,0.90]) linear_extrude(height=trim_t) trim_body(w);
} else if (part=="pivot") {
    color([0.02,0.28,0.88]) pivot_body(w);
} else if (part=="handle") {
    color([0.02,0.28,0.88]) handle_body(w);
} else if (part=="lock") {
    color([0.12,0.13,0.14]) lock_body(w);
} else if (part=="knob") {
    color([0.08,0.09,0.10]) ribbed_knob();
} else if (part=="label") {
    color([0.98,0.98,0.96]) label_body();
} else {
    assembly_view(w);
}
