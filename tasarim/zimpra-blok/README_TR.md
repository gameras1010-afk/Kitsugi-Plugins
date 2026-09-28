# Zımpara bloğu — V4 fotoğraf tabanlı prototip

Bu sürüm, gönderdiğin yakın planlar ve gövde fotoğraflarındaki ana parçaları aynı montajda toplamaya çalışır: **D biçimli siyah alt gövde, gri üst yüz, altta koyu yumuşak ara katman ve açık renk zımpara yüzü; üstte iki mafsallı mavi U sapı, siyah tırtıklı ayar kapakları ve ortada siyah kilit bloğu.** Önceki basit düz kol tasarımı kaldırıldı.

İstediğin gibi ölçüleri şimdilik mantıklı varsayımlarla üç boy yaptım. Görselden üretildiği için bu CAD, orijinal ürünün ölçülmüş/tıpatıp teknik kopyası değildir; dış form ve parçaların yerleşimine odaklı prototiptir. Dişler ve mafsal iç detayı fotoğrafta görünmediğinden standart metal civata/somun için boşluk bırakıldı.

## Boylar

| Seçenek | Taban genişliği | Yaklaşık derinlik |
|---|---:|---:|
| S | 140 mm | 70 mm |
| M | 180 mm | 90 mm |
| L | 220 mm | 110 mm |

`size` ile S/M/L; `part` ile assembly, base, face, pad, abrasive, pivot, handle veya lock seçilir. `assembly` renkli montaj önizlemesidir.

## 3D yazdırılabilir dosyalar

OpenSCAD'de `zimpra_blok.scad` dosyasını aç. Parçaları tek tek almak için `part` seçimini yap, **F6 → File → Export → Export as STL** kullan. Örnek olarak önce S/M/L içinden **M** boyutunu test et. Toplu dışa aktarma:

- Windows: PowerShell'de `export_all.ps1` (OpenSCAD komutu PATH'te olmalı)
- Mac/Linux: `export_all.sh`

Betikler 3 boy × 7 parça = 21 STL üretir. `pad` ve `abrasive` katmanları görsel/ölçü prototipidir; gerçek kullanımda yumuşak ara yüz ve gerçek zımpara kâğıdı tercih edilir.

## Baskı başlangıç ayarı

- Taban, yüz paneli ve ara katman düz yatırılarak; tutamak geniş yan yüzü tablaya gelecek şekilde basılır.
- Taban için PETG, tutamak ve mafsallar için PETG/ASA önerilir. PLA/PLA+ sadece ilk ergonomi denemesi için.
- Başlangıç: 0,20 mm katman; tabanda 4–5 duvar ve %35–45 doluluk; mafsal/tutamakta 5 duvar ve yaklaşık %50 doluluk.
- Donanım: taban mafsal ayakları için 4 adet M3 civata/somun; sap mafsalları için 2 adet M5 civata, pul ve kilitli somun. Donanım STL'ye dahil değildir. Delik geçişlerini basımdan sonra kontrol edin.

**Satış öncesi:** önce prototip basıp yüzeye oturuş, mafsal hareketi, kilit, çekme ve düşme dayanımını test et. Tasarım sertifikalı değildir; fotoğraftan ölçülmeyen iç mekanik ayrıntıların işlevi test gerektirir.
