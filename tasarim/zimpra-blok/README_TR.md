# Fotoğrafa göre zımpara bloğu — V6

Bu sürüm, son gönderdiğin resimde belirgin olan yönü düzeltiyor: **mavi kol D tabanın düz kenarına paralel, iki yuvarlak ucu arasındaki dar kol biçiminde yerleşiyor.** Önceki sürümde kol 90° yanlış yöndeydi. Modelde siyah D gövde, gri üst plaka, beyaz uç yatakları, siyah merkez kilit plakası, tek uçta tırtıklı siyah düğme ve altta yumuşak/zımpara katmanları bulunur.

Boyutlar fotoğraflardan tahmin edilmiştir; dış yerleşim ve renkler referansa yaklaştırıldı, görünmeyen mekanik ayrıntılar ise prototip amaçlı sadeleştirilmiştir.

## Boylar

| Seçim | Taban genişliği | Yaklaşık derinlik |
|---|---:|---:|
| S | 140 mm | 70 mm |
| M | 180 mm | 90 mm |
| L | 220 mm | 110 mm |

OpenSCAD Customizer'dan `size` S/M/L seç. `part = "assembly"` renkli montaj önizlemesidir.

## Parçalar ve STL

`part` seçenekleri: `base`, `face`, `pad`, `abrasive`, `trim`, `handle`, `lock`, `knob`, `label`.

OpenSCAD'de `zimpra_blok.scad` dosyasını aç, istenen `part` değerini seç, **F6 → File → Export → Export as STL** ile parçaları ayrı ayrı dışa aktar. Önce M boyunu dene. Toplu dışa aktarma için Windows PowerShell'de `export_all.ps1`, Mac/Linux'ta `export_all.sh` çalıştır (OpenSCAD komutu PATH'te olmalı). Betik S/M/L için 27 STL üretir.

## Baskı notları

- Taban, gri panel, alt ped ve zımpara yüzü düz yatırılır. Mavi kol da düz yüzeyi üzerinde basılır.
- PETG önerilir; esnek alt katman için TPU ya da hazır cırt/ara yüz kullan. Gerçek abrasif zımparayı ayrıca yapıştır.
- Başlangıç ayarı: 0,20 mm katman; taban 4–5 duvar, kol ve düğme 5 duvar ve %40–50 doluluk.
- İki uçta M4 insert/civata, orta plakada iki M3 insert/civata varsayılmıştır. Donanım baskı dosyasına dahil değildir.
- `label` parçasındaki “project 360” yazısının görünmesi sistemde Arial fontunun bulunmasına bağlıdır.

Bu dosya fotoğraf tabanlı bir prototiptir; gerçek mafsal hareketi, kilit ve dayanım test edilmeden seri satışa hazır kabul edilmemelidir.
