# Döner saplı zımpara bloğu — ilk prototip

Fotoğraftaki üründen esinlenen, markasız ve parametrik bir **FDM 3D baskı konsepti**. Siyah taban + turuncu sap önerisi inşaat ortamında görünürlük ve parçaları ayırt etmek için seçildi. Model, fotoğraftan ölçülendirilmedi; aşağıdaki ölçüler üretilebilir bir ilk deneme için benim tasarım varsayımlarımdır.

## Tasarım

Üç basılabilir plastik parça:

1. **Taban (`base`)** — D biçimli düz zımpara pabucu. Altına kesilmiş yapışkanlı cırt (hook-and-loop) yüzey veya yapışkanlı zımpara takılır.
2. **Döner mafsal (`swivel`)** — tabana M6 merkez civatasıyla bağlanır; sapı tabana göre 360° yönlendirmeyi sağlar. M4 bağlantı kulakları da bu parçadadır.
3. **Tutamak (`grip`)** — avuç içine oturan köprü sapı; M4 civatalarla mafsal kulaklarının arasına bağlanır.

Mafsalların gerçek yük ve ömür performansı henüz test edilmedi. İlk baskıyı prototip kabul edin; satış öncesi zımpara çekişi, sap bağlantısı, düşme ve yorulma denemeleri yapın.

## Üç ölçü seçeneği

| Boy | Taban dış genişliği | Yaklaşık derinlik | Not |
|---|---:|---:|---|
| S | 120 mm | 60 mm | dar alan / küçük el |
| M | 170 mm | 85 mm | başlangıç için önerilen |
| L | 220 mm | 110 mm | geniş yüzey; 220 mm tabla sınırına yakın |

Bunlar tabanın nominal dış ölçüleridir. Zımpara kâğıdını tabanın alt şekline göre kesin. Yapışkanlı cırt/ara yüz, baskı dosyasına dahil değildir; hazır ürünü tabanın düz altına yapıştırın. M6 somun yuvası zımpara yüzünün altında ve yüzeyle aynı hizada kalacak şekilde tasarlanmıştır.

## Dosyayı açma ve STL dışa aktarma

`zimpra_blok.scad` OpenSCAD ile açılır. Üstteki `size` ve `part` seçimlerini değiştirin:

- `size = "S"`, `"M"` veya `"L"`
- `part = "base"`, `"swivel"`, `"grip"` veya `"assembly"`

Baskı için üç parçayı **ayrı ayrı** STL olarak dışa aktarın; `assembly` yalnızca montajı kontrol etmek içindir. Komut satırında örnek:

```sh
openscad -o base_M.stl   -D 'size="M"' -D 'part="base"'   zimpra_blok.scad
openscad -o swivel_M.stl -D 'size="M"' -D 'part="swivel"' zimpra_blok.scad
openscad -o grip_M.stl   -D 'size="M"' -D 'part="grip"'   zimpra_blok.scad
```

S/M/L için `M` değerini değiştirin. Üç boyun dokuz ayrı STL çıktısı böyle alınabilir.

## Baskı önerisi

- **Malzeme:** PETG önerilir; daha sıcak/sert şantiye kullanımı için ASA düşünülebilir. PLA/PLA+ yalnızca ölçü ve ergonomi prototipi için uygundur.
- **Tabla:** taban düz alt yüzeyi üzerine; mafsal tabanı aşağı; tutamak OpenSCAD'deki düz profil yüzeyi tabla üzerinde olacak şekilde.
- **Başlangıç ayarı:** 0,20 mm katman, 4–5 duvar, tabanda %35–45; mafsal ve sapta %50–60 doluluk. Yazıcının ve filamentin gerçek ayarlarına göre değiştirin.
- Delik toleransları baskı kalibrasyonuna bağlıdır. M4 delikler 4,5 mm, merkez delik 6,6 mm çizilmiştir; baskı sonrası civata geçişini kontrol edin. Gerekirse delikleri matkapla temizleyin; tasarım dosyasındaki toleransları yazıcıya göre artırın.
- **Donanım:** 2 adet M4×35 civata + pul + kilitli somun; merkez için 1 adet M6×25 düşük başlı alyan civata, M6 altıgen somun ve ince düşük sürtünmeli pul/ara rondela. Merkez mafsalı sıkarken dönme hareketini tamamen kilitlemeyin; somun yuvası ve pul ölçülerini elinizdeki donanıma göre doğrulayın.

## Güvenlik / ticari kullanım

Baskı malzemesi, katman yönü ve civata montajı taşıma dayanımını etkiler. Kullanıcıya satmadan önce gerçek zımpara ve çalışma kuvvetleriyle test edin; kırılan baskı parçası yaralanmaya veya yüzey hasarına yol açabilir. Bu dosya teknik sertifikalı/endüstriyel yük sınıfı bir ürün değildir. Logolar ve markalar bilerek eklenmemiştir.
