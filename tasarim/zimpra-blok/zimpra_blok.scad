/*
  Photo-matched low-profile 360 sanding block — V5 visual prototype.
  S/M/L sizes, units in millimetres.

  Form follows the latest top/side photos: D-shaped black sanding head,
  inset grey top face, two white-edged pivot seats, one slim blue center lever,
  black center lock plate, black end thumb screw, and layered soft/abrasive underside.
  Dimensions are chosen for a plausible first print; they are not measured from the photo.
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
lever_y1 = r*0.16;
lever_y2 = r*0.78;
lever_mid = (lever_y1+lever_y2)/2;
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
    y1=rr*0.16;
    y2=rr*0.78;
    ym=(y1+y2)/2;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Blind M5 insert seats for the two end pivots (keeps the sanding underside flat).
        for (yy=[y1,y2]) translate([0,yy,1.5]) cylinder(h=base_t-1.4,d=M4_insert_bore);
        // Two M3 attachment points for the central lock plate.
        for (x=[-16,16]) translate([x,ym,2]) cylinder(h=base_t-1.9,d=M3_insert_bore);
    }
}

module face_body(width) {
    rr=width/2;
    y1=rr*0.16;
    y2=rr*0.78;
    ym=(y1+y2)/2;
    difference() {
        // Thin inset top skin leaves the black base visible as a continuous perimeter.
        linear_extrude(height=face_t) d_outline(width-8);
        // Clear the two pivot fasteners and two central-lock screws.
        for (yy=[y1,y2]) translate([0,yy,-0.1]) cylinder(h=face_t+0.2,d=5.8);
        for (x=[-16,16]) translate([x,ym,-0.1]) cylinder(h=face_t+0.2,d=3.8);
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
    y1=rr*0.16;
    y2=rr*0.78;
    difference() {
        union() {
            translate([0,y1]) rounded_2d(28,25,8);
            translate([0,y2]) rounded_2d(28,25,8);
        }
        for (yy=[y1,y2]) translate([0,yy]) circle(d=5.4);
    }
}

module handle_profile(width) {
    rr=width/2;
    y1=rr*0.16;
    y2=rr*0.78;
    difference() {
        // The photo shows two broad rounded pivot pads joined by one slim straight paddle.
        union() {
            translate([0,y1]) rounded_2d(23,21,7);
            translate([0,y2]) rounded_2d(23,21,7);
            hull() {
                translate([0,y1+8]) circle(r=6.8);
                translate([0,y2-8]) circle(r=6.8);
            }
            // A modest palm swell around the centre, still a flat lever, not a U-handle.
            hull() {
                translate([0,y1+(y2-y1)*0.40]) circle(r=7.5);
                translate([0,y1+(y2-y1)*0.60]) circle(r=7.5);
            }
        }
        // Pivot clearance at both rounded ends.
        for (yy=[y1,y2]) translate([0,yy]) circle(d=5.4);
    }
}

module handle_body(width) {
    // Flat, printable paddle/lever; the face with the logo points upward.
    linear_extrude(height=handle_t) handle_profile(width);
}

module lock_plate() {
    difference() {
        linear_extrude(height=trim_t) rounded_2d(42,25,3.5);
        for (x=[-16,16]) translate([x,0,-0.1]) cylinder(h=trim_t+0.2,d=M3_clearance);
    }
}

module lock_body(width) {
    lock_plate();
}

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

module label_body(width) {
    linear_extrude(height=0.45)
        rotate(90) text("360",size=6.4,font="Arial:style=Bold",halign="center",valign="center");
}

module assembly_view(width) {
    rr=width/2;
    y1=rr*0.16;
    y2=rr*0.78;
    ym=(y1+y2)/2;
    top=base_t+face_t;
    lever_z=top+trim_t;
    color([0.11,0.13,0.15]) base_body(width);
    // Thin back cushion and light replaceable abrasive layer below the black shell.
    color([0.07,0.08,0.09]) translate([0,0,-pad_t]) pad_body(width);
    color([0.91,0.89,0.82]) translate([0,0,-pad_t-abrasive_t]) abrasive_body(width);
    color([0.62,0.65,0.67]) translate([0,0,base_t]) face_body(width);
    color([0.90,0.91,0.90]) translate([0,0,top]) linear_extrude(height=trim_t) trim_body(width);
    color([0.02,0.28,0.88]) translate([0,0,lever_z]) handle_body(width);
    color([0.12,0.13,0.14]) translate([0,ym,top]) lock_plate();
    // One ribbed locking knob on the nose-side end; second end is the pivot seat.
    color([0.08,0.09,0.10]) translate([0,y2,lever_z+handle_t]) thumb_knob();
    color([0.04,0.04,0.04]) translate([0,ym,lever_z+handle_t]) label_body(width);
    // Two small black M3 screw heads fasten the center plate to the base.
    color([0.03,0.03,0.03]) for (x=[-16,16])
        translate([x,ym,top+trim_t]) cylinder(h=1.2,d=4.5);
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
    color([0.97,0.97,0.95]) label_body(w);
} else {
    assembly_view(w);
}
