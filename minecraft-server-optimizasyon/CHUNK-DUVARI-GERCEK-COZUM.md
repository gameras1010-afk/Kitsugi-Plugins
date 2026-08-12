# Chunk Duvarı — Gerçek Çözüm (ForceBlend)

> **Önce özür:** "Chunky ile pregen yap, fark minimum olur" **çözüm değildi.**
> O sadece duvarı daha uzağa taşır. Duvar yine oluşur, sadece daha ötede.
> Doğru yol var ve aşağıda.

---

## 🔴 ÖNCE: TEŞHİS YANLIŞTI

Sana söylenen şuydu:

> *"1.20.1'de kaydedilmiş eski chunk'ların terrain yüksekliği ile
> 1.21.1 noise parametreleriyle üretilen chunk'ların yüksekliği uyuşmuyor"*

**Bu büyük ihtimalle yanlış.** Vanilla arazi üretimi **1.18'den 1.21'e kadar
değişmedi.** 1.18'de noise sistemi arazi ve biyom için ayrı haritalara
bölündü ve arazi haritası o günden beri aynı:

> *"terrain generation doesn't change much between modern versions.
> This is why terrain **is the exact same between all versions from
> 1.18 and onwards**"*

Yani 1.20.1 → 1.21.1 taşımak **tek başına** duvar yaratmaz.
Vanilla suçlu değil. Gerçek sebep şunlardan biri:

| Gerçek sebep | Nasıl anlarsın |
|---|---|
| **Worldgen modlarının SÜRÜMÜ değişti** (Terralith, BoP, Tectonic 1.20.1 sürümü ≠ 1.21.1 sürümü) | En olası sebep. Mod sürüm notlarında "terrain changes" var mı bak |
| **Bir worldgen modu eklendi/çıkarıldı** | Mod listesini eski sunucuyla karşılaştır |
| **`blending_data` tag'i** eski chunk'larda takılı kaldı | Duvar değil, tam tersi: garip çukur/tümsek |
| C2ME `allowThreadedFeatures` / `reduceLockRadius` | Bunlar **duvar** değil **yarım yapı** yapar — farklı semptom |

> Not: Dünyayı eski sunucudan tekrar çekmen **doğru** bir hamleydi.
> Bozuk chunk'lardan kurtuldun. Kalan duvar başka bir olay.

---

## ✅ GERÇEK ÇÖZÜM: ForceBlend

**Minecraft'ın kendi arazi harmanlama motoru var.** 1.18'de eklendi.
Mojang'ın 1.17 dünyalarını 1.18'e geçirirken kullandığı sistem —
eski ve yeni araziyi sınırda yumuşak geçişle birleştirir.

Normalde bu motor **sadece sürüm yükseltmede** otomatik tetiklenir.
Ama **elle tetikleyebilirsin.**

MCA Selector'da `ForceBlend` diye bir NBT alanı var. Resmî tanımı:

> *"Can be used to force chunks generated in 1.18 to blend with other
> chunks generated in 1.18."*

Grokipedia'nın teknik özeti:

> *"This flag causes the game to **treat selected chunks as if they were
> upgraded from an older version**, prompting in-game blending to smooth
> transitions between adjacent chunks **without altering terrain blocks
> directly**."*

Kritik nokta: **MCA Selector harmanlama yapmıyor.** Sadece bayrağı
dikiyor, işi **oyunun kendi motoru** yapıyor. Yani sonuç "el işi
düzeltme" değil, Mojang'ın algoritması.

Gerçek kullanıcı raporu:

> *"I highlighted/selected the chunks I imported, **as well as a ton of
> chunks around the region**, clicked Tools > Change Fields > Force Blend
> > true... once I opened the world again the chunks had been **pretty
> seamlessly blended** into the surrounding area."*

---

## 📋 ADIM ADIM

### Adım 0 — YEDEK. Tartışma yok.

```
/backup snapshot          ← FTB Backups kuruluysa
```
Kurulu değilse sunucuyu `/stop` ile kapat, `world/` klasörünü kopyala.
**Bu adımı atlarsan bu dokümanı okumamış say.**

### Adım 1 — Sunucuyu KAPAT

```
/stop
```
MCA Selector çalışan sunucunun dünyasına dokunursa dosyayı bozar.

### Adım 2 — Duvarın nerede olduğunu bul

Oyunda duvarın yanında dur, **F3** aç, koordinatı not et.
Birden fazla yerdeyse hepsini not et.

### Adım 3 — MCA Selector'da aç

`File > Open World` → `world/region` klasörünü seç.

### Adım 4 — Duvarın YENİ tarafındaki chunk'ları SİL

Duvarın **yeni üretilmiş** (1.21.1 tarafı) chunk'larını seç.
Eski/yapılarının olduğu tarafa **dokunma.**

`Selection > Delete selected chunks`

> **Neden siliyoruz:** Harmanlamanın çalışması için yeni arazinin
> **yeniden üretilmesi** lazım. Var olan chunk'a dokunmaz.
> Bir kullanıcının sözü: *"delete surrounding adjacent chunks to give
> room for yours to **grow**"* — araziye büyüyecek yer açıyorsun.

**Ne kadar silmeli:** Sınırdan itibaren **en az 4-8 chunk kalınlığında
bir şerit.** Dar tutarsan harmanlama için yer kalmaz, duvar hafifler
ama gitmez.

### Adım 5 — KALAN eski chunk'lara ForceBlend bas

Şimdi **silmediğin**, sınıra komşu eski chunk'ları seç
(sınır boyunca 2-3 chunk kalınlığında bir şerit yeter).

```
Tools > Change Fields
  └─ ForceBlend  →  true
  ☑ Force
  ☑ Apply to selection only     ← BUNU MUTLAKA İŞARETLE
OK
```

⚠️ **`Apply to selection only` işaretli değilse bayrağı DÜNYANIN
TAMAMINA basar.** Felaket olur.

### Adım 6 — Sunucuyu aç, oraya git

Yeni chunk'lar üretilirken oyun `ForceBlend` bayrağını görecek ve
eski araziyle harmanlayarak üretecek. Duvar yerine **eğim** olacak.

---

## ⚠️ TEHLİKE — bunu yaparsan çökertirsin

**Boş (hiç üretilmemiş) chunk'a ForceBlend basma.**

Kaynak, MCA Selector ve Minecraft kaynak kodunu okumuş bir kullanıcı:

> *"MCA Selector marked an **ungenerated chunk** with `blending_data` tag
> and the game will try to get the chunk's biome to blend it, **then fail**."*

Sonuç: oraya uçunca **oyun çöküyor.**

**Korunma yolu:**
- Sadece **var olan** (haritada renkli görünen) chunk'ları seç
- `Apply to selection only` her zaman işaretli
- Sildiğin bölgeye ForceBlend basma — orası artık boş

Bir kullanıcının deneyimi: *"there's **always a few corrupted chunks**
that crash my game"* → çözümü, işlemi bölgeyi düzgün seçerek birkaç kez
tekrarlamak olmuş. Yani **ilk denemede tutmayabilir**, yedeğin olsun.

---

## 🟡 Ya duvar değil de garip çukur/tümsek varsa

Farklı sorun: `blending_data` tag'i takılı kalmış olabilir.
Chunk silindikten sonra sınırda harmanlama **yanlış yerde** tetiklenir
(bir kullanıcının nehri kurumuş, arazi yükselmiş).

**Çözüm — harmanlamayı KAPAT:**

```
Tools > Change Fields > custom alanına:
region.remove("blending_data")
```

Ama önce şu tuzağa dikkat, aynı kullanıcının notu:

> *"At first, this solution failed for me because I was also **updating to
> a new version** right after cleaning unused chunks... If you update a
> chunk to a new version, the game **adds the `blending_data` tag right
> back**."*

Yani sürüm yükseltmesi varsa: önce chunk formatını yükselt
(**Singleplayer > Edit > Optimize World**, arazi üretmeden formatı
günceller), **sonra** `blending_data`'yı sil.

---

## ❌ İŞE YARAMAYAN YOLLAR — deneme

| Yol | Neden olmaz |
|---|---|
| **Chunky pregen** | Duvarı **yok etmez**, sadece daha uzağa taşır. Pregen'in işi performans, kozmetik değil |
| **TerraBlender** | Sadece **yeni** üretimde vanilla↔mod geçişini yumuşatır. *"Doesn't fix existing issues when borders start to form"* |
| Seed'i değiştirmek | Daha beter. Her yerde yeni duvar |
| Modları eski sürüme döndürmek | Yeni chunk'lar düzelir ama **zaten üretilmiş** olanlar kalır. Üstelik 1.21.1'de 1.20.1 modu çalışmaz |
| Bekleyip görmezden gelmek | Duvar kendi kendine geçmez |

### Son çare: elle terraform

ForceBlend tutmazsa (bazı aşırı yükseklik farklarında tutmaz —
bir kullanıcı: *"blending stops when old terrain rises into a mountain"*),
kalan yol **WorldEdit**:

```
//brush smooth 5 4
```
Duvara sağ tıklayarak yumuşatırsın. Zahmetli ama %100 kontrol sende.
**Axiom** daha modern ve görsel bir alternatif.

---

## 📌 ÖZET — sırayla

```
0. YEDEK AL                          ← atlamak yok
1. /stop
2. Duvar koordinatlarını F3 ile bul
3. MCA Selector aç
4. Duvarın YENİ tarafından 4-8 chunk şerit SİL
5. Kalan ESKİ tarafa (2-3 chunk şerit) ForceBlend = true
   ☑ Force   ☑ Apply to selection only
6. Sunucuyu aç, bölgeye git → oyun harmanlayarak üretir
7. Tutmadıysa: yedekten dön, şeridi genişlet, tekrar dene
8. O da olmadıysa: WorldEdit //brush smooth
```

**Beklenti dürüst olsun:** ForceBlend duvarı **eğime** çevirir,
%100 doğal arazi vaat etmez. Yükseklik farkı çok büyükse
(15+ blok) tam gizlenmeyebilir. Ama "duvar" görüntüsü gider.

Ve en önemlisi: bu **Mojang'ın kendi harmanlama motoru** —
uydurma bir numara değil, 1.17→1.18 geçişinde milyonlarca dünyada
çalışan sistem.
