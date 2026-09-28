# Zımpara bloğu — V7 el boşluklu prototip

Son fotoğrafa göre modelin **yüksekliği ve tutuşu** yeniden düzenlendi. Mavi sap artık tabanın üzerinde yatan düz kol değil: D tabanın düz kenarına paralel uzanan, uçlardan mafsallı, üstte kalın bir kavrama köprüsü. Köprünün altında yaklaşık **35 mm dikey el/parmak boşluğu** ve M boyunda yaklaşık 50 mm yatay el/parmak açıklığı bırakıldı. Gövde siyah D biçimli; üst yüz gri; mafsal altlıkları açık renk; sap mavi; orta kilit ve ayar düğmeleri siyah; alt yüz katmanlı.

Üç boy, fotoğrafta ölçek olmadığı için mantıklı başlangıç ölçüleridir; orijinal ölçünün garantisi değildir.

| Boy | Gövde genişliği | Yaklaşık derinlik | Nominal sap altı boşluğu |
|---|---:|---:|---:|
| S | 140 mm | 70 mm | 35 mm |
| M | 180 mm | 90 mm | 35 mm |
| L | 220 mm | 110 mm | 35 mm |

## OpenSCAD / STL

`zimpra_blok.scad` dosyasını açıp Customizer'dan `size` ve `part` seç. `part = "assembly"` tüm parçaların renkli montajını gösterir. Parçaları tek tek dışa aktarmak için **F6 → File → Export → Export as STL** kullan.

Parça seçenekleri: `base`, `face`, `pad`, `abrasive`, `trim`, `pivot`, `handle`, `lock`, `knob`, `label`.

Toplu dışa aktarım için OpenSCAD'in `openscad` komutu PATH'te olmalı:

- Windows PowerShell: `export_all.ps1`
- Mac/Linux: `export_all.sh`

Betikler 3 boy × 10 parça = 30 STL çıkarır. İlk kez basarken M boyunu ve yalnızca base/face/pivot/handle/lock/knob parçalarını dene. `pad` için TPU veya hazır cırt; `abrasive` yerine gerçek zımpara kâğıdı; `label` için çok renkli baskı/filament değişimi kullan.

## Konstrüksiyon ve baskı başlangıç ayarı

- Ana gövde için PETG; el tutamağı için PETG veya ASA. PLA/PLA+ sadece boyut/ergonomi prototipi.
- Mavi sap geniş profil yüzeyi üzerine yatırılarak basılır; mafsal delikleri basımdan sonra temizlenir.
- Başlangıç: 0,20 mm katman; tabanda 4–5 duvar, pivot/sapta 5–6 duvar ve %45–55 doluluk.
- Donanım varsayımı: mafsal eksenleri için 2 adet M5 civata ve kilitli somun; pivot tabanlarını sabitlemek için 4 adet M3 civata/insert; merkez kilit için 2 adet M3.
- Alt yumuşak ara yüz ve zımpara sarf malzemesini yapıştırmadan önce metal bağlantıları kur.

Model, fotoğraflardan dış görünüş ve el boşluğu hedefiyle hazırlanmış ilk prototiptir. Fotoğrafta görünmeyen gerçek kilit/mafsal iç yapısı sadeleştirilmiştir; basım, hareket ve çekme testleri yapılmadan seri satışa hazır kabul edilmemelidir.
