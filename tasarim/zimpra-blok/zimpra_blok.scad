/*
  Photo-based Project 360-style sanding block — V6 visual prototype.
  The blue paddle runs ACROSS the D-shaped head, parallel to its straight edge.
  S/M/L sizes; units are millimetres. Dimensions are estimated from photos.
*/

size = "M"; // [S, M, L]
part = "assembly"; // [assembly, base, face, pad, abrasive, trim, handle, lock, knob, label]
$fn = 72;

function width_for(s) = s == "S" ? 140 : s == "L" ? 220 : 180;
w = width_for(size);
r = w/2;
base_t = 8;
face_t = 1.6;
pad_t = 1.6;
abrasive_t = 0.9;
trim_t = 2.2;
handle_t = 5.5;
lever_span = w*0.48;
lever_y = r*0.42;
x_left = -lever_span/2;
x_right = lever_span/2;
M4_insert_bore = 5.0; // heat-set insert outer bore for M4 pivot screws
M3_insert_bore = 4.2; // heat-set insert outer bore for M3 lock screws
M3_clearance = 3.4;

module d_outline(width) {
    rr = width/2;
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
          [for (i=[1:96]) [rr*cos(180*i/96),rr*sin(180*i/96)]]));
}

module rounded_2d(xlen,ylen,rad=3) {
    offset(r=rad) offset(delta=-rad) square([xlen,ylen],center=true);
}

module base_body(width) {
    rr=width/2;
    s=width*0.48;
    py=rr*0.42;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Two blind M4 insert bores beneath the transverse handle end pads.
        for (x=[-s/2,s/2]) translate([x,py,1.5]) cylinder(h=base_t-1.4,d=M4_insert_bore);
        // M3 insert bores for the small centre locking plate.
        for (x=[-16,16]) translate([x,py,2]) cylinder(h=base_t-1.9,d=M3_insert_bore);
    }
}

module face_body(width) {
    rr=width/2;
    s=width*0.48;
    py=rr*0.42;
    difference() {
        // Grey top insert, slightly inset from the black outside rim.
        linear_extrude(height=face_t) d_outline(width-8);
        // Clearance holes for the two handle pivots and centre-lock screws.
        for (x=[-s/2,s/2]) translate([x,py,-0.1]) cylinder(h=face_t+0.2,d=5.8);
        for (x=[-16,16]) translate([x,py,-0.1]) cylinder(h=face_t+0.2,d=3.8);
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
    s=width*0.48;
    py=rr*0.42;
    difference() {
        union() {
            translate([-s/2,py]) rounded_2d(28,25,8);
            translate([ s/2,py]) rounded_2d(28,25,8);
        }
        for (x=[-s/2,s/2]) translate([x,py]) circle(d=5.4);
    }
}

module handle_profile(width) {
    rr=width/2;
    s=width*0.48;
    py=rr*0.42;
    difference() {
        // Two broad rounded pivots joined by a slim central paddle.
        union() {
            translate([-s/2,py]) rounded_2d(23,21,7);
            translate([ s/2,py]) rounded_2d(23,21,7);
            hull() {
                translate([-s/2+8,py]) circle(r=6.8);
                translate([ s/2-8,py]) circle(r=6.8);
            }
            // Mild molded grip swell through the centre; all remains low-profile.
            hull() {
                translate([-12,py]) circle(r=7.5);
                translate([ 12,py]) circle(r=7.5);
            }
        }
        for (x=[-s/2,s/2]) translate([x,py]) circle(d=5.4);
    }
}

module handle_body(width) {
    linear_extrude(height=handle_t) handle_profile(width);
}

module lock_plate() {
    difference() {
        linear_extrude(height=trim_t) rounded_2d(42,25,3.5);
        for (x=[-16,16]) translate([x,0,-0.1]) cylinder(h=trim_t+0.2,d=M3_clearance);
    }
}

module lock_body(width) { lock_plate(); }

module thumb_knob() {
    difference() {
        union() {
            cylinder(h=4,d=11,center=false);
            for (a=[0:15:345]) rotate([0,0,a])
                translate([5.4,0,2]) cube([1,1.2,4],center=true);
        }
        cylinder(h=4.2,d=4.3);
    }
}

module label_body() {
    // White generic marking, oriented along the handle length as in the reference.
    translate([0,lever_y+2.2]) linear_extrude(height=0.45)
        text("project",size=2.7,font="Arial:style=Bold",halign="center",valign="center");
    translate([0,lever_y-1.7]) linear_extrude(height=0.45)
        text("360",size=6.4,font="Arial:style=Bold",halign="center",valign="center");
}

module assembly_view(width) {
    rr=width/2;
    s=width*0.48;
    py=rr*0.42;
    top=base_t+face_t;
    lever_z=top+trim_t;
    color([0.11,0.13,0.15]) base_body(width);
    // Soft interface and light abrasive layer on the underside.
    color([0.07,0.08,0.09]) translate([0,0,-pad_t]) pad_body(width);
    color([0.91,0.89,0.82]) translate([0,0,-pad_t-abrasive_t]) abrasive_body(width);
    color([0.62,0.65,0.67]) translate([0,0,base_t]) face_body(width);
    color([0.90,0.91,0.90]) translate([0,0,top]) linear_extrude(height=trim_t) trim_body(width);
    // Long axis is X, parallel to the D head's straight chord (key reference detail).
    color([0.02,0.28,0.88]) translate([0,0,lever_z]) handle_body(width);
    color([0.12,0.13,0.14]) translate([0,py,top]) lock_plate();
    // Ribbed black thumb screw over the curved-side end of the blue lever.
    color([0.08,0.09,0.10]) translate([s/2,py,lever_z+handle_t]) thumb_knob();
    // White generic brand-style lettering on the blue paddle.
    color([0.98,0.98,0.96]) translate([0,0,lever_z+handle_t]) label_body();
    // Centre plate fasteners visible beside the narrow blue lever.
    color([0.03,0.03,0.03]) for (x=[-16,16])
        translate([x,py,top+trim_t]) cylinder(h=1.2,d=4.5);
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
} else if (part=="handle") {
    color([0.02,0.28,0.88]) handle_body(w);
} else if (part=="lock") {
    color([0.12,0.13,0.14]) lock_body(w);
} else if (part=="knob") {
    color([0.08,0.09,0.10]) thumb_knob();
} else if (part=="label") {
    color([0.98,0.98,0.96]) label_body();
} else {
    assembly_view(w);
}
