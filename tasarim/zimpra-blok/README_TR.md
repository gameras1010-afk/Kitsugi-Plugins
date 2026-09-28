# Düşük profilli döner saplı zımpara bloğu — V2 konsept

Kullanıcının gönderdiği fotoğraflardaki **siyah yarım daire taban + iki küçük bağlantı ayağı + alçak, ince sap** biçimine göre baştan düzenlenmiş parametrik OpenSCAD tasarımıdır. Önceki yüksek kemerli sap ve geniş turuncu taşıyıcı bu sürümde kaldırılmıştır. Görsel ve renk yaklaşımı referansa yakın olsun diye koyu taban ve mavi bağlantı/sap seçilmiştir. Marka veya logo eklenmemiştir.

> Tasarım fotoğraftan ölçülendirilmedi. Aşağıdaki değerler ilk prototip içindir; orijinal ürünle birebir ölçü uyumu iddiası yoktur.

## Üç basılabilir bileşen

1. **Taban (`base`)** — düz alt yüzeyli D biçimli/yarım daire zımpara taşıyıcı.
2. **İki pivot ayağı (`pivot`)** — aynı STL dosyasında bulunan iki küçük mafsal ayağı; tabana M3 civatalarla sabitlenir.
3. **Alçak sap (`grip`)** — iki ayağın arasına M4 mafsal civatalarıyla bağlanan ince, hafif yükseltilmiş kol. Yüksek U biçimli kemer yoktur.

## Boy seçenekleri

| Boy | Taban genişliği | Yaklaşık derinlik |
|---|---:|---:|
| S | 140 mm | 70 mm |
| M | 180 mm | 90 mm |
| L | 220 mm | 110 mm |

OpenSCAD'de `size = "S"`, `"M"` veya `"L"`; `part = "base"`, `"pivot"`, `"grip"` ya da `"assembly"` seçilebilir. `assembly` sadece görünüm/montaj kontrolü içindir.

## STL dışa aktarma

OpenSCAD'de dosyayı açın; her parçayı ayrı STL alın. Örneğin M boyunda `part` değerini sırayla `base`, `pivot`, `grip` yapıp her seferinde **F6 → File → Export → Export as STL** seçin. `size` değerini değiştirerek S ve L boyları da alınabilir.

Windows'ta PowerShell açıp `export_all.ps1` dosyasını çalıştırarak dokuz STL'yi topluca alabilirsiniz (OpenSCAD komutu PATH'te olmalı). Mac/Linux için `export_all.sh` vardır.

## Baskı ve montaj başlangıç önerisi

- **Filament:** PETG. PLA/PLA+ yalnızca ebat ve elde tutuş prototipi için.
- **Taban:** düz alt yüzeyi tablaya gelecek şekilde basın.
- **Pivot ayakları:** alt tabanları tablaya gelecek şekilde; iki ayağın STL'de ayrı olması normaldir.
- **Sap:** geniş profil yüzeyi tablaya gelecek şekilde düz basın.
- Başlangıç ayarı: 0,20 mm katman; tabanda 4–5 duvar ve %35–45 doluluk; pivot ve sapta 4–5 duvar ve %50–60 doluluk. Yazıcıya göre kalibre edin.
- **Donanım:** 4 adet M3 civata ve somun (pivot ayaklarını tabana bağlamak için); 2 adet M4×30 civata, pul ve kilitli somun (sap mafsalları için). Deliklerin baskı sonrası geçişini kontrol edin.
- Alt yüzeye kesilmiş yapışkanlı cırt/uygun zımpara ara yüzü veya kendi yapışkanı olan zımpara uygulanabilir; bu sarf malzemesi modele dahil değildir.

## Güvenlik

Bu, yük/ömür sertifikası bulunmayan prototip tasarımdır. Satıştan önce gerçek zımpara ile çalışma, çekme, düşme ve yorulma denemeleri yapın. Baskı katman yönü ve malzeme dayanımı sonucu etkiler.
