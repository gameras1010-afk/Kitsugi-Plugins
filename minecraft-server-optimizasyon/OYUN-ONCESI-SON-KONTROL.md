# Oynamadan Önce — Son Kontrol

O özet büyük ölçüde doğru. Ama içinde **3 sorun** var.
Biri gerçekten önemli, biri sessiz kayıp, biri de yanlış güven.

---

## 🔴 1. ServerCore `dynamic` — bunu AÇMA

Özette şöyle diyor:

> *"dinamik kontrol sayesinde tek başınayken mesafeyi 20 chunk yapıp,
> sunucu yükü arttıkça otomatik ve güvenli bir şekilde 2'şer 2'şer düşürüyor"*

Bu **benim önerimin tam tersi** ve iki ayrı sebepten kötü.

### Sebep A — 1.18'den beri view distance değişimi chunk reload tetikliyor

someaddon'un (Chunk Sending'in de yazarı) Dynamic View mod sayfasında
birebir şu not var:

> *"Version 1.18 Note: Vanilla changed behaviour of view distance changes,
> **now they trigger a chunk reload on client-side.**"*

Yani sunucu mesafeyi 20'den 18'e her düşürdüğünde **senin ekranında tüm
chunk'lar yeniden yükleniyor.** Lag'i önlemek için konan sistem, kendisi
lag üretiyor. Üstelik bu, tam da yük arttığı anda — yani zaten
zorlandığın anda — oluyor.

### Sebep B — C2ME ile aynı işi yapıyor

C2ME'nin `noTickViewDistance` modülü zaten chunk gönderim mesafesini
yönetiyor. ServerCore dinamik modda aynı değeri ezmeye çalışıyor.
İki mod aynı sayıyı çekiştiriyor.

### ✅ Yapılacak

`config/servercore.toml`:
```toml
[dynamic]
    enabled = false
```

`server.properties`:
```properties
view-distance=10
simulation-distance=6
```

Sonra C2ME'nin no-tick VD'sini kullan — **görüş mesafesi yüksek kalır ama
o chunk'lar tick yemez.** İstediğin "20 chunk görme" bu şekilde,
reload olmadan elde edilir. Dinamik zıplamaya gerek yok.

> Dinamik mesafeyi gerçekten istiyorsan yanına **Farsight** kurman gerekir
> (mod yazarının kendi tavsiyesi) — ama gereksiz karmaşa. Sabit bırak.

---

## 🟡 2. Annuus — client'ına da kurmadıysan HİÇBİR ŞEY yapmıyor

Annuus'un kendi açıklaması:

> *"When the player doesn't install annuus on the client, network packet
> will send normally **like vanilla**"*

Yani sıkıştırma ancak **iki tarafta da** mod varsa devreye giriyor.
Sadece sunucuda varsa — vanilla gibi davranıyor, kazanç sıfır.

**Kontrol:** Client mods klasöründe `Annuus-neoforge-*.jar` var mı?
Yoksa o "10'da 1'ine düşürme" gerçekleşmiyor.

**Ayrıca:** Annuus'un kazancı **bant genişliği**. Kendi bilgisayarında,
kendi sunucunda, tek başına oynuyorsan ağ zaten darboğazın değil.
Bu mod sana ölçülebilir bir FPS/TPS getirmez.

**Daisy** kısmı doğru — cao_awa'nın kütüphanesi, Annuus/Sepals için
gerekli. Onda sorun yok.

---

## 🟠 3. "0.2–1.2 ms MSPT" bir kanıt değil

Bu değerler **boş, hareketsiz bir sunucunun** değerleri. Kimse yokken
vanilla sunucu da 0.5 ms verir. Bu, kurulumun iyi olduğunu göstermez —
sadece sunucunun şu an **hiçbir iş yapmadığını** gösterir.

Gerçek test şu üçü:

| Test | Nasıl | İyi sonuç |
|---|---|---|
| **Elytra/at ile yeni araziye dalış** | 2-3 dk sürekli yeni chunk | MSPT < 30 ms, takılma yok |
| **Nether portal + boyut geçişi** | Gidip gel | 1 sn'lik donma normal, 5 sn değil |
| **Uzağa /tp** | Hiç gidilmemiş koordinat | Chunk'lar akarak gelmeli |

Bu üçünde takılma yoksa kurulum gerçekten iyi demektir.

---

## ✅ Özette DOĞRU olanlar

Bunlarda itirazım yok:

- **C2ME 5 paralel worker** → doğru, i5-9400F için ideal ayar
- **ScalableLux entegrasyonu** → doğru, kod seviyesinde C2ME ile entegre
- **zfastnoise** → Overworld %37 / Nether %85 rakamları modun kendi ölçümü
- **Chunk Sending** → login/teleport paket sıralaması, doğru iş yapıyor
- **ServerCore mob AI throttle** → doğru (sadece `dynamic` kısmı hatalı)

---

## 🎮 Oynarken neye bakacaksın

Özette *"asıl oynarken belli olacak"* denmiş — doğru. İşte bakacakların:

### İyi işaretler
- Elytra ile uçarken önünde **gri/boş alan oluşmuyor**
- Yeni araziye girerken ekran **donmuyor**, chunk'lar akıyor
- Nether'a geçiş 1-2 saniye
- `/spark tps` sürekli 20

### Kötü işaretler ve ne yapacağın

| Belirti | Sebep | Çözüm |
|---|---|---|
| Uçarken önü boş kalıyor | Chunk üretimi yetişmiyor | **Chunky ile pregen yap** |
| Her 30-60 sn'de bir takılma | GC duraklaması | `start.sh`'ta heap'i kurcalama, önce spark ile bak |
| Ekran periyodik "yeniden yükleniyor" | **ServerCore dynamic** | Yukarıdaki 1. maddeyi uygula |
| Teleport sonrası uzun donma | Chunk Sending ayarı | Varsayılanda bırak |
| Kalabalık yerde TPS düşüşü | Entity/mob | ServerCore entity limitleri |

### İlk oturumdan sonra çalıştır

```bash
grep -iE "ERROR|Mixin apply failed|Can't keep up" logs/latest.log
```

`Can't keep up` çıkıyorsa gerçek bir sorun var. Sadece `Force-disabling`
ve `Disabling config` satırları varsa **normal** — modlar kendi arasında
anlaşıyor.

---

## 📌 Kalan tek gerçek iş: PREGEN

Bütün bu modlar chunk üretimini **hızlandırıyor.** Chunky ise
**üretim işini oyundan önce bitiriyor.** Hiçbir mod bununla yarışamaz.

```
/chunky radius 3000
/chunky start
```

Bunu bir gece boyunca çalıştır. Ertesi gün oynadığında fark
diğer tüm modların toplamından büyük olacak.

Bu yapılmadıysa kurulum **tam kapasite değil** — motoru hazırladın ama
yolu henüz asfaltlamadın.
