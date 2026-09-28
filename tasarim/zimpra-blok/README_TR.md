# Project 360 tarzı zımpara bloğu — V3 görsel prototip

Bu sürüm, gönderdiğin son fotoğraflardaki biçime göre yeniden kuruldu: **D biçimli siyah taban, içte gri yüz paneli, ortada siyah kilit bloğu, iki mavi mafsal ayağı ve alçak U/yoke biçimli mavi tutamak**. Tırtıklı pivot kapakları da görseldeki ayar parçalarını temsil ediyor. Önceki ince düz kol/ayak düzeni bu sürümde kullanılmıyor.

Ölçüler, isteğin üzerine S/M/L olarak mantıksal biçimde seçildi; fotoğraftan alınmış kesin ölçüler değildir. Bu nedenle dosyayı **ölçüsü yaklaşık görsel prototip** olarak değerlendir. Tutamak ve kilit mekanizmasının gerçek hareket aralığı, iç detayları ve donanım toleransları fotoğraflardan tam çıkarılamıyor.

## Üç boy

| Boy | D taban genişliği | Yaklaşık derinlik | Kullanım |
|---|---:|---:|---|
| S | 140 mm | 70 mm | küçük yüzey/kompakt |
| M | 180 mm | 90 mm | ilk deneme için önerilen |
| L | 220 mm | 110 mm | geniş yüzey; tabla ölçüsünü kontrol et |

## Dosyadaki model parçaları

- `base`: siyah D taban; M3 somun yuvaları içerir.
- `face`: tabanın üstündeki gri, içe alınmış yüz paneli; ayrı renkte basılabilir.
- `pivot`: iki mavi mafsal ayağı (tek dosyada, iki ayrı parça olarak yerleşir).
- `handle`: mavi, alçak U/yoke tutamak; düz yatırılarak basılır.
- `lock`: siyah orta kilit bloğu ve iki tırtıklı pivot kapağı.
- `assembly`: tüm parçaların renkli montaj önizlemesi.

OpenSCAD Customizer'dan `size` değerini S/M/L, `part` değerini yukarıdaki parçalardan biri yap. Montajı görmek için `part = "assembly"` seç.

## STL oluşturma

OpenSCAD'de `zimpra_blok.scad` dosyasını aç. Her parçayı ayrı STL olarak almak için `part` seçimini değiştir, **F6** ile render et ve **File → Export → Export as STL** seç. Toplu dışa aktarma için:

- Windows: OpenSCAD yüklü ve `openscad` PATH'te olacak şekilde PowerShell'den `export_all.ps1` çalıştır.
- Mac/Linux: `export_all.sh` çalıştır.

Bu işlem S/M/L boylarının her biri için beşer dosya (toplam 15 STL) üretir. İlk montaj denemesinde yalnızca **M** boyunu dışa aktar.

## Baskı ve donanım önerileri

- Taban ve mafsallar için **PETG**; tutamak için PETG veya ASA. PLA'yı yalnızca ilk ebat/ergonomi denemesine ayır.
- Taban altı düz şekilde; yüz paneli düz şekilde; mafsal ayakları tabanları üzerinde; tutamak geniş profil yüzeyi tabla üzerinde basılır.
- Başlangıç: 0,20 mm katman, tabanda 4–5 duvar/%35–45 doluluk; tutamak ve mafsallarda 5 duvar/%50 doluluk.
- Önerilen metal donanım: mafsal için 2 adet M4 civata (yaklaşık 30 mm) ve kilitli somun; ayakları tabana bağlamak için 4 adet M3 civata ve somun. Metal donanım STL'ye dahil değildir. Civata deliklerini yazıcı toleransına göre kontrol et.
- Alt zımpara yüzüne yapışkanlı cırt veya uygun zımpara ara yüzü yapıştırılabilir; yumuşak/abrasif katman sarf malzemesidir, baskı modeline dahil değildir.

## Önemli

Bu dosya fotoğraflara göre hazırlanmış görsel/işlevsel bir ilk konsepttir; orijinal ürünün ölçülendirilmiş kopyası veya dayanım sertifikalı bir tasarım değildir. Baskı, hareket, kilit ve zımpara tutuşu gerçek malzemeyle test edilmeden satışta kullanma. Kırılma ve mafsal sıkışması riskini kontrol et.
