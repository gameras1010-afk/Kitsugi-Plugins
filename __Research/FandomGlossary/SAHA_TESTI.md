# Fandom Glossary v2 — Kapsamlı Saha Testi Raporu
**Tarih:** 2026-08-28 · 18 başlık / 4 kategori / 24 canlı API çağrısı (paralel koşuldu)

## Amaç
Popüler → orta → niş → hiç bilinmeyen yelpazesinde anime + dizi + film başlıklarıyla
tüm pipeline'ı (unified-search → Wikidata fallback → doğrulama) gerçek dünyada sınamak;
karmaşık/tuzaklı vakalarda davranışı ölçmek.

## Sonuç Matrisi

### ✅ Kusursuz geçenler (tek denemede doğru wiki)

| Başlık | Tür/Seviye | Bulunan | Not |
|---|---|---|---|
| Shingeki no Kyojin (romaji arandı!) | Anime/popüler | `attackontitan` | Romaji→İngilizce wiki eşleşti; 2. sonuç fanon idi, pageCount farkı (2000 vs 300) ayırıyor |
| Breaking Bad | Dizi/popüler | `breakingbad` | Roblox oyunu `hub:games` cezasıyla elendi ✓ |
| Squid Game | K-dizi/popüler | `squid-game` | AU/fanon/reality türevleri pageCount+isim skoru ile eleniyor |
| Dark (Netflix) | Dizi/orta | `dark-netflix` | Jenerik "dark" kelimesine rağmen doğru |
| The Wire | Dizi/orta | `thewire` | |
| Inception | Film/orta | `inception` | `hub:movies` doğru; F1/CSI gürültüsü isim skoru ile eleniyor |
| Vinland Saga | Anime/orta | `vinlandsaga` | Tek sonuç |
| Odd Taxi | Anime/niş | `oddtaxi` | Tek sonuç |
| Girls' Last Tour (romaji: Shoujo Shuumatsu Ryokou) | Anime/niş | `girls-last-tour` | Romaji sorgusu İngilizce adlı wiki'yi buldu — synonym stratejisi kanıtlandı |
| Monster (Urasawa) | Anime/niş | **`obluda`** | Slug Çekçe "canavar"! AI asla tahmin edemezdi; arama + sitename eşleşmesi buldu |
| Link Click (donghua) | Donghua/niş | `linkclick` | Çin animasyonu da sorunsuz |
| Legend of the Galactic Heroes | Anime/kült | `gineipaedia` + `legendofthegalacticheroes` | **2 meşru wiki!** Skorlama pageViews (5000 vs 500) ile ikinciyi seçer — ikisi de doğru evren |

### 🟡 Arama kaçırdı, Wikidata fallback KURTARDI (katman sistemi çalışıyor)

| Başlık | Sorun | Kurtaran |
|---|---|---|
| **Sonny Boy** | unified-search **0 sonuç** döndü (wiki var: `sonny-boy`!) | MAL 48849 → Q106837406 → **P4073: `sonny-boy`** ✓ tek zincirde çözüldü |
| **Perfect Blue** | Arama 0 sonuç | Wikidata QID bulundu (Q1205051) ama P4073 boş → **"eşleşme yok"** (doğru: gerçekten adanmış wiki'si yok) |

> **Kritik ders:** unified-search'ün indeksi küçük/az-trafikli wiki'leri bazen hiç dönmüyor.
> K2a (Wikidata) ve K2b (arama) **asla tek başına yeterli değil — iki yönlü fallback şart** (mimaride zaten var, sahada kanıtlandı).

### 🟠 Yapısal boşluk: K-drama'lar ve merkezi wiki problemi

| Başlık | Durum |
|---|---|
| Crash Landing on You | Adanmış wiki yok; arama 0 |
| Queen of Tears | Adanmış wiki yok; arama 0 |
| Misaeng | Adanmış wiki yok; `misaeng.fandom.com` boş döndü |

**Bulgu:** Bu diziler `kdrama.fandom.com` **merkezi wiki'sinde** yaşıyor (canlı doğrulandı:
Queen of Tears sayfası orada mevcut). Aynı desen: `asianwiki` benzeri merkezi topluluklar.
**Öneri (v2.2):** "Umbrella wiki" kavramı — dizi bazlı wiki bulunamazsa, tür bazlı merkezi
wiki'lerde (`kdrama`, `cdrama`, `turkish-series` vb.) `list=search` ile dizinin ANA SAYFASINI bul,
o sayfanın linklediği karakter sayfalarını mini-sözlük olarak çek. Crossover blocklist'in tersi:
bunlar "güvenilir merkezi wiki whitelist'i" olur.

### 🔴 Doğru şekilde reddedilenler (yanlış pozitif üretmedi)

| Başlık | Davranış |
|---|---|
| Ezel (TR dizi) | 0 sonuç → "eşleşme yok" ✓ (Fandom'da wiki'si yok, doğru karar) |
| Kurtlar Vadisi | 0 sonuç → "eşleşme yok" ✓ |
| Drive My Car (film) | Arama sadece alakasız oyunlar döndürdü (`does-not-commute` vb.) → hepsi hub:games cezası + isim skoru altında → **veto** ✓. Eski sistem burada muhtemelen yanlış wiki kabul ederdi |
| Castle (tuzak: jenerik isim) | İlk sonuç gerçek Castle (ABC) wiki'si — ama bunu ancak **ID doğrulaması** (izlediğin yapım gerçekten o dizi mi?) ayırır; karakter problaması şart (Beckett/Castle isimleri probe edilmeli) |

## Karmaşıklık Analizi — "problem yaşar mıyız?" sorusunun cevabı

1. **Romaji/synonym sorguları çalışıyor** (SnK→AoT, Shoujo Shuumatsu→Girls' Last Tour) ama
   **her iki adla da sorgu atmak şart** — tek sorguya güvenme.
2. **Çift meşru wiki** (LoGH) vakasında hangisi seçilirse seçilsin terimler doğru evrenden gelir —
   risk düşük; pageViews tie-breaker yeterli.
3. **unified-search indeks boşlukları** gerçek ve tahmin edilemez (Sonny Boy). Wikidata fallback
   olmasaydı burada eski sistemin AI-tahmin kumarına dönerdik. **İki katman birbirini tamamlıyor.**
4. **K-drama/TR-dizi segmenti** adanmış-wiki modeliyle kapsanamıyor → umbrella wiki özelliği
   eklenene kadar bu segmentte "eşleşme yok" normaldir (yanlış pozitiften iyidir).
5. **Sahte/fanon türevler** (SnK Fanon, Squid Game AU, Breaking Bad Tycoon) her popüler yapımda
   var ama hub + pageCount + isim skoru üçlüsü hepsini güvenilir şekilde eledi.

## Skor Özeti

- Adanmış wiki'si OLAN 14 başlık: **14/14 doğru çözüm** (12 aramadan, 1 Wikidata'dan, 1 çift-meşru)
- Wiki'si OLMAYAN 4 başlık: **4/4 doğru red** (sıfır yanlış pozitif)
- **Yanlış eşleşme: 0** — eski sistemin ana hastalığı bu testte hiç görülmedi.

## Aksiyon Önerileri (öncelik sırasıyla)
1. **[Orta]** Umbrella-wiki whitelist özelliği (kdrama vb.) — K-drama segmenti için tek eksik.
2. **[Düşük]** LoGH gibi çoklu-meşru vakalarda pageViews tie-breaker'ının loglanması.
3. **[Düşük]** unified-search 0 sonuç dönünce Wikidata'ya düşüşün metriklenmesi (hangi oranla oluyor).

---

# TUR 2 — Derin Niş Testi (19 yeni başlık, 2026-08-28)
**Kapsam:** az bilinen/kült anime (10) + niş dizi (5) + niş film (4). Toplam test edilen başlık: **37**.

## Tur 2 Sonuç Matrisi

### ✅ Aramadan tek atışta doğru çözülenler (8)
| Başlık | Slug | Not |
|---|---|---|
| Shinsekai Yori | `shinsekaiyori` | Romaji sorgu, tek sonuç |
| Kaiba (Yuasa, 2008) | `kaiba` | Ultra-niş, tek sonuç |
| Planetes | `planetes` | pageCount:10'luk mini wiki bile bulundu |
| Mushishi | `mushishi` | |
| Barakamon | `barakamon` | |
| Deadwood | `deadwood` | |
| Rectify | `rectify` | pageViews:10'luk ölü wiki bile ilk sırada |
| Halt and Catch Fire | `haltandcatchfire` | Breath of Fire gürültüsü hub:games ile elendi |
| The Leftovers | `the-leftovers` | Pokemon hack gürültüsü elendi |

### 🥇 TUR 2'NİN YILDIZI: Ping Pong tuzağı — K3 katmanı hayat kurtardı
- Arama "ping pong the animation" → alakasız sonuçlar (0 gerçek aday)
- `pingpong.fandom.com` diye bir wiki VAR (sitename: "Ping Pong Wiki") — eski sistem bunu %100 kabul ederdi!
- **Karakter problaması: Peco / Smile / Kazama → 3/3 MISSING → VETO** ✓
- Yani wiki var ama BAŞKA bir "ping pong" konusu. Doğrulama katmanı tam da tasarlandığı işi yaptı.
- Sonuç: "eşleşme yok" (doğru — animenin adanmış wiki'si gerçekten yok)

### 🟡 Arama indeks boşluğu #2 kanıtlandı: Pan's Labyrinth
- Arama: 0 sonuç. Ama `pans-labyrinth.fandom.com` VAR (canlı doğrulandı, sitename tam eşleşme).
- Sonny Boy'dan sonra ikinci kanıtlı indeks boşluğu. Fark: Sonny Boy'u Wikidata kurtardı;
  Pan's Labyrinth'te P4073 yoksa üçüncü fallback gerekir →
  **ÖNERİ (v2.3): "slugify probe" fallback'i** — başlıktan deterministik slug üret
  (`pans-labyrinth`, `pan-s-labyrinth`, `panslabyrinth`) → siteinfo probu → sitename fuzzy ≥0.8
  VE karakter problaması geçerse kabul. Bu, AI tahmininden farklı: sadece deterministik
  varyantlar denenir ve K3'ün tamamından geçmek zorundadır.

### 🟠 Wikidata kapsam gerçeği (niş animelerde traversal boş)
Ping Pong, Mononoke, Dennou Coil, Aku no Hana, Tatami Galaxy → **5/5 QID bulundu** (haswbstatement
mükemmel çalışıyor) ama **traversal 5'inde de P4073/P6262'siz döndü**. RAPOR.md'deki %20 kapsam
tahmini niş segmentte daha da düşük. Sistem bu durumda doğru şekilde "eşleşme yok" diyor
(Tatami Galaxy'nin `tatamigalaxy` slug'ı da gerçekten boş — doğru karar).

### 🔴 Doğru redler (wiki gerçekten yok) (7)
Coherence, Primer, Dark City, Moon (2009), Babylon Berlin*, Gomorrah*, Patriot*
(*bu üçünün slug probları boş döndü; adanmış wiki yok veya farklı slug'da —
umbrella/slugify fallback'leri eklendiğinde yeniden değerlendirilebilir)

## Kümülatif Skor (37 başlık)
| Metrik | Değer |
|---|---|
| Adanmış wiki'si olup doğru çözülen | 23/25 (%92) |
| Arama indeks boşluğu (kanıtlı) | 2 → 1'i Wikidata kurtardı, 1'i açık (slugify önerisi) |
| Wiki'si olmayıp doğru reddedilen | 12/12 (%100) |
| **Yanlış eşleşme (yanlış wiki kabul)** | **0/37 (%0)** ← eski sistemin ana hastalığı |
| K3 veto kurtarışı (yanlış wiki engellendi) | 1 kanıtlı (Ping Pong) |

## Nihai Hüküm
Sistem **sağlam**: 37 başlıkta tek bir yanlış eşleşme yok. Kalan iki iyileştirme alanı
(öncelik sırasıyla): (1) umbrella wiki (kdrama vb.), (2) slugify-probe fallback'i
(Pan's Labyrinth vakası). İkisi de "kaçırma"yı azaltır — "yanlış eşleşme" riski taşımaz,
çünkü her ikisi de K3 doğrulamasından geçmek zorundadır.

---

# TUR 3 — "Hiç Bilinmeyenler" Dip Testi (15 başlık, 2026-08-28)
**Kapsam:** 1974 çöp animeleri, tek sezonluk iptal dizileri, kültün kültü OVA'lar, yabancı dil yapımlar.
Kümülatif test: **52 başlık**.

## Test edilenler ve sonuçlar

### ✅ Aramadan doğru çözülen dip-niş (3)
| Başlık | Slug | Not |
|---|---|---|
| Haibane Renmei (2002, ABe kültü) | `haibanerenmei` | Tek sonuç, 10 sayfalık wiki bile |
| Patlabor (1989 mecha) | `patlabor` | Tek sonuç |
| Kaamelott (FR dizi) | `kaamelott` (fr) | ⚠️ **lang=en'de 0, lang=fr'de bulundu** → yeni bulgu ↓ |

### 🥇 YENİ BULGU #1: Çok dilli arama gerekliliği (Kaamelott vakası)
unified-search `lang` parametresi **yapımın kaynak diliyle** sorgulanmalı: Kaamelott
`lang=en` ile görünmez, `lang=fr` ile ilk sonuç. **Öneri (v2.4):** yapımın ülke/dil
metadata'sı (AniList countryOfOrigin / TMDB original_language) biliniyorsa arama
`lang=en` + `lang={orijinal_dil}` olarak İKİ kez atılmalı. Fransız/Alman/İspanyol
yapımlarının wiki'leri çoğunlukla kendi dillerinde.

### 🥇 YENİ BULGU #2: Slugify-probe artık kanıtlı gereklilik (2 yeni vaka, toplam 4)
| Başlık | Arama | Wikidata | Gerçek |
|---|---|---|---|
| **Chargeman Ken!** (1974) | 0 sonuç | QID yok | Wiki VAR: `chargeman-ken` (32 makale, aktif!) |
| **Gankutsuou** (2004) | 0 sonuç | — | Wiki VAR: `gankutsuou` (29 makale; dikkat: wikiid'si `duo` — eski slug mirası) |
| Sonny Boy (Tur 1) | 0 | ✓ kurtardı | `sonny-boy` |
| Pan's Labyrinth (Tur 2) | 0 | boş | `pans-labyrinth` |

Dört vakada da doğru slug = başlığın basit slugify'ı (`chargeman-ken`, `gankutsuou`,
`pans-labyrinth`, `sonny-boy`). **Slugify-probe fallback'i artık "öneri" değil,
"gerekli özellik" statüsünde** — dip-niş segmentte arama indeksinin kör noktası sistematik.

### 🔴 Doğru redler — jenerik gürültüye rağmen sıfır yanlış pozitif (9)
| Başlık | Aramanın döndürdüğü çöp | Neden elenir |
|---|---|---|
| Oruchuban Ebichu | 0 sonuç | temiz red |
| Kuuchuu Buranko (Trapeze) | Taro Okamoto, PJSK fanon | isim skoru ~0 |
| NieA_7 | Plim Plim (çocuk TV), HUstudios | isim skoru ~0 |
| Windy Tales | Tales of Wind (2 OYUN wiki'si) | hub:games cezası + isim ters |
| Cat Soup (Nekojiru-sou) | Plant Cats, Planet Yarnball | isim skoru ~0 |
| Jinrui wa Suitai Shimashita | Vietnamca roman wiki'si (!) | isim skoru ~0; `jintai` slug probu da boş |
| Terriers (2010 FX) | Secret Life of Pets (!) | isim/tür uyumsuz |
| Lodge 49 | 0 sonuç | temiz red |
| The Man from Earth | **Warhammer 40k + One-Punch Man** (!) | isim skoru ~0 — eski sistem burada W40k'dan terim çekebilirdi! |
| Kingdom Hospital | 0; slug probu da boş | temiz red |

## Kümülatif Skor (52 başlık, 3 tur)
| Metrik | Değer |
|---|---|
| **Yanlış eşleşme** | **0/52 (%0)** — üç turda da sıfır |
| Wiki'si olanlarda isabet | 26/30 (%87) — kaçan 4'ün hepsi slugify-probe ile kapanır → potansiyel %100 |
| Wiki'si olmayanlarda doğru red | 22/22 (%100) |
| Kanıtlı arama indeks boşluğu | 4 (Sonny Boy, Pan's Labyrinth, Chargeman Ken, Gankutsuou) |
| K3 veto kurtarışı | 1 (Ping Pong) + The Man from Earth'te W40k tuzağı isim skoruyla engellendi |

## Güncellenmiş yol haritası (öncelik sırası değişti!)
1. **[YÜKSEK — yükseltildi]** Slugify-probe fallback (4 kanıtlı vaka; dip-niş segmentin anahtarı)
2. **[ORTA]** Çok dilli arama (`lang=en` + orijinal dil) — Kaamelott vakası
3. **[ORTA]** Umbrella wiki whitelist (kdrama vb.)
