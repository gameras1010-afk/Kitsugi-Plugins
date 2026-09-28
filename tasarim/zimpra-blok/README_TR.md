# Fotoğrafa göre zımpara bloğu — V5

Bu sürüm, son gönderdiğin **üstten ve yandan net fotoğraflara göre** önceki U saplı tasarımdan tamamen farklı olarak yeniden çizildi. Mavi parça artık yüksek kemer değil: **iki geniş yuvarlak ucu olan, arası daralan düz merkez kol**. Altında iki açık renk pivot yuvası, ortada siyah dikdörtgen kilit plakası ve uçta siyah tırtıklı düğme bulunuyor. Kafa; siyah D biçimli gövde, gri üst yüz, altta koyu yumuşak tabaka ve açık renk zımpara yüzü olarak katmanlandı.

Fotoğraf açıları dış görünüşü belirliyor; gerçek ölçü yok. Bu yüzden üç boyut mantıklı tahminlerle seçildi. Dış silueti ve görünen parçaları fotoğrafa yaklaştırdım; içeride görünmeyen kilit/mafsal mekanizmasının birebir kopyası olduğunu iddia etmiyorum.

## Üç boy

| Seçim | D taban genişliği | Yaklaşık derinlik |
|---|---:|---:|
| S | 140 mm | 70 mm |
| M | 180 mm | 90 mm |
| L | 220 mm | 110 mm |

## Parça seçimi

OpenSCAD'de `size` S/M/L ve `part` alanından `assembly`, `base`, `face`, `pad`, `abrasive`, `trim`, `handle`, `lock`, `knob` veya `label` seç. `assembly` renkli montaj önizlemesidir.

- `base`: siyah D gövde; iki uçta M4 insert yuvası, merkez plakada M3 insert yuvası.
- `face`: gri, üstteki içe alınmış yüz.
- `pad`: alt yumuşak/cırt arayüzü (esnek filament veya ticari cırt tercih et).
- `abrasive`: açık renk ince prototip katmanı; gerçek zımpara için şablon/ölçü parçasıdır.
- `trim`: iki beyaz/gri uç yuvası.
- `handle`: iki oval uçlu düz mavi kol.
- `lock`: siyah merkez plaka.
- `knob`: tırtıklı siyah uç düğmesi.
- `label`: beyaz “360” işareti; yazıcıdaki Arial fontu yoksa dışa aktarmadan önce etiket parçasını kapat.

## STL oluşturma

OpenSCAD'de `zimpra_blok.scad` dosyasını aç. Parçayı seç, **F6 → File → Export → Export as STL** ile ayrı STL oluştur. İlk baskıda yalnızca M boyunu kullan.

Toplu aktarma için OpenSCAD'in `openscad` komutu PATH'te olmalı:

- Windows PowerShell: `export_all.ps1`
- Mac/Linux: `export_all.sh`

Bunlar üç boy × dokuz parça için 27 STL üretir. Üretim için gerekli olmayan `pad`, `abrasive` ve `label` parçalarını dışa aktarmadan da baskı yapılabilir.

## Baskı ve birleştirme

- İlk prototipte gövde/sap için PETG; esnek ara katman için TPU veya hazır yapışkanlı cırt kullan.
- Taban, yüz, ped ve etiket düz yatırılır. Mavi kol geniş düz yüzeyi üzerinde basılır.
- Başlangıç ayarı: 0,20 mm katman; taban 4–5 duvar/%35–45 doluluk; kol ve düğme 5 duvar/%50 doluluk.
- Donanım: uç pivotlarda M4 civata ve ısı ile gömülen M4 insert; merkez kilit plakası için 2 M3 civata/insert. Donanım STL'ye dahil değildir.
- Gerçek zımpara kâğıdının alt arayüzünü tabana yapıştırın. Isıl insert, civata geçişi ve pivot hareketini basımdan sonra prova edin.

Bu bir fotoğraf tabanlı ilk prototiptir, endüstriyel sertifikalı ürün değildir. Satış öncesi hareket, kilit, çekme, düşme ve yorulma testleri yapın.
