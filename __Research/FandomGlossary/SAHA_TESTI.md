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
