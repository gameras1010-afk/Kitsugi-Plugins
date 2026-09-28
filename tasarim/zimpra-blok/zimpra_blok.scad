/*
  360 derece dönebilen, D-formlu zımpara bloğu — parametrik konsept
  Birimler: mm

  Parçalar:
    base   : zımpara taşıyıcı gövde
    swivel : merkezde dönen tabla ve M4 mafsal kulakları
    grip   : ergonomik tutamak (düz yatırılarak basılır)
    assembly: montaj görünümü

  Boyutlar: S / M / L (Slicer tablasına ve eldeki zımpara ölçüsüne göre seçin.)
  Marka/logolar eklenmemiştir. Bu, ölçüleri fotoğraftan doğrulanmamış ilk prototip tasarımıdır.
*/

size = "M";       // [S, M, L]
part = "assembly"; // [assembly, base, swivel, grip]

$fn = 64;

// Boyut seçimi: dış genişlik x yarım daire derinliği
function body_width(s) = s == "S" ? 120 : s == "L" ? 220 : 170;

// Temel ölçüler
base_t = 8;
rotor_t = 5;
handle_t = 16;
eye_t = 4;
base_hole_d = 6.6;   // M6 pivot civatası boşluğu
hinge_hole_d = 4.5; // M4 tutamak bağlantısı

w = body_width(size);
r = w/2;
pivot_y = r*0.42;
spacing = w*0.54;

module d_outline(width) {
    rr = width/2;
    // Uç noktaları ve ön yarım daire. Offset'ler köşeleri yumuşatıp nominal ölçüyü korur.
    offset(r=2) offset(delta=-2)
        polygon(points=concat([[-rr,0],[rr,0]],
            [for (i=[1:72]) [rr*cos(180*i/72), rr*sin(180*i/72)]]));
}

module base_body(width) {
    rr = width/2;
    py = rr*0.42;
    difference() {
        linear_extrude(height=base_t) d_outline(width);
        // Merkezî döner mafsal geçişi
        translate([0,py,-0.1]) cylinder(h=base_t+0.2,d=base_hole_d);
        // M6 somun yuvası altta; somun tabanla aynı hizada kalır
        translate([0,py,-0.01]) rotate([0,0,30])
            cylinder(h=5.3,d=11.8,$fn=6);
    }
}

module swivel_body(width) {
    py = width/2*0.42;
    span = width*0.54;
    z0 = base_t;
    support_x = [-span/2, span/2];
    difference() {
        union() {
            // Merkezî yatak ve kulakların altındaki köprü
            translate([0,py,z0]) cylinder(h=rotor_t,d=40);
            translate([-(span+16)/2,py-16,z0])
                cube([span+16,32,rotor_t]);
            // Her bağlantıda iki kulak; tutamak arada kalır (gerçek clevis mafsalı)
            for (sx=support_x) for (side=[-1,1])
                translate([sx-7.5, py + side*(handle_t/2+eye_t/2)-eye_t/2, z0+rotor_t])
                    cube([15,eye_t,16]);
        }
        // Merkez pivot ve M6 başı için üstten yuva
        translate([0,py,z0-0.1]) cylinder(h=rotor_t+0.2,d=base_hole_d);
        translate([0,py,z0+rotor_t-3.2]) cylinder(h=3.4,d=11.3);
        // M4 bağlantı civataları: iki kulak ve tutamak aynı eksende delinmiş
        for (sx=support_x)
            translate([sx,py,z0+rotor_t+8]) rotate([90,0,0])
                cylinder(h=40,d=hinge_hole_d,center=true);
    }
}

module grip_profile(width) {
    span = width*0.54;
    difference() {
        union() {
            // Avuç içi için enine, geniş ve yuvarlatılmış köprü
            hull() {
                translate([-span/2+5,30]) circle(r=9);
                translate([ span/2-5,30]) circle(r=9);
            }
            // İki yana inen ergonomik kollar
            for (side=[-1,1]) hull() {
                translate([side*span/2,0]) circle(r=7.5);
                translate([side*(span/2-6),24]) circle(r=7.5);
            }
        }
        // M4 civata delikleri
        for (side=[-1,1]) translate([side*span/2,0]) circle(d=hinge_hole_d);
    }
}

module grip_part(width) {
    // Bu yönlendirmede tutamak yatay durur; köprü baskı tablasına temas eder.
    linear_extrude(height=handle_t) grip_profile(width);
}

module assembly_view(width) {
    py = width/2*0.42;
    translate([0,0,0]) color([0.15,0.17,0.19]) base_body(width);
    color([1.0,0.36,0.05]) swivel_body(width);
    // Profili XZ düzlemine kaldır; baskı dosyası olarak grip'i ayrı ve düz basın.
    translate([0,py+handle_t/2,base_t+rotor_t+8])
        rotate([90,0,0]) color([1.0,0.36,0.05]) grip_part(width);
}

if (part == "base") {
    color([0.15,0.17,0.19]) base_body(w);
} else if (part == "swivel") {
    color([1.0,0.36,0.05]) swivel_body(w);
} else if (part == "grip") {
    color([1.0,0.36,0.05]) grip_part(w);
} else {
    assembly_view(w);
}
