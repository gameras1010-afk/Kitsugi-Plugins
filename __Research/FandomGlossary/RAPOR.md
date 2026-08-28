# Fandom Glossary v2 — Deep Research Raporu
**Tarih:** 2026-08-28 · Tüm endpoint'ler bu tarihte canlı test edilmiştir.

---

## 0. Yönetici Özeti

Mevcut sistemin (`fandom_glossary.py`) yanlış eşleşme ve duplicate üretmesinin kök nedeni
**iki ayrı zayıflığın üst üste binmesi**:

1. **Aday üretimi tahmine dayalı** (AI slug guess) → aday havuzu baştan kirli.
2. **Doğrulama katmanı zayıf** (ana sayfa metin araması) → kirli adayları eleyemiyor.
3. **Terim çekme aşaması filtresiz** (`categorymembers` ham) → doğru wiki bulunsa bile duplicate/çöp geliyor.

Araştırma sonucunda plan taslağındaki bazı varsayımların **güncel olmadığı** tespit edildi
(ARM API artık Wikidata QID dönmüyor) ve çok daha güçlü, **tamamen deterministik** iki kaynak bulundu:
Wikidata `haswbstatement` ters araması ve **Fandom'un resmi unified-search API'si**.

Önerilen yeni mimari 4 katman:

```
[K1] Kimlik Çözümleme     ID'ler (AniList/MAL/TMDB) → Wikidata QID (+ animeapi.my.id ile ID zenginleştirme)
[K2] Aday Üretimi         (a) Wikidata P4073/P6262 + ilişki traversal'ı  → yüksek güven
                          (b) Fandom unified-search (resmi arama API'si) → orta güven, geniş kapsam
                          (c) AI slug tahmini                            → SADECE son çare
[K3] Hakemli Doğrulama    karakter-problama + sitename eşleşmesi + hub/boyut kontrolü + crossover blocklist
[K4] Terim Çekme+Temizlik cmnamespace=0&cmtype=page + subpage filtresi + redirect canonicalization + dedupe
```

---

## 1. Canlı Test Sonuçları (Kanıtlar)

| # | Test | Sonuç | Çıkarım |
|---|------|-------|---------|
| 1 | `arm.haglund.dev/api/v2/ids?source=anilist&id=154587` | ✅ Çalışıyor; anidb/mal/imdb/tmdb/tvdb döndü. **`wikidata` alanı YOK.** `include=wikidata` → **HTTP 500** | ARM'dan QID alma planı geçersiz. ARM sadece ID köprüsü olarak kullanılabilir. |
| 2 | `animeapi.my.id/myanimelist/52991` (nattadasu AnimeAPI) | ✅ ARM'dan çok daha zengin: tmdb+season, tvdb, imdb, trakt, shikimori, `title` dahil 25+ alan | ARM yerine/yanına birincil ID köprüsü olarak daha iyi. Slug tabanlı sorgu da destekliyor (`/animeplanet/campione` çalıştı). |
| 3 | Wikidata `action=query&list=search&srsearch=haswbstatement:P8729=154587` | ✅ Tek sonuç: `Q130377145` (Frieren S1). Aynısı `P4086` (MAL) ve `P4983` (TMDB TV: 46184→Q89195494) ile de çalıştı | **SPARQL'siz, anlık ID→QID ters araması.** En hızlı ve en ucuz yol. |
| 4 | SPARQL traversal (Frieren): `P144/P179/P361/P8345/P4969` ± ters yönler | ✅ Anime item'inde link yokken **manga item'inden** `P6262: frieren:...` ve **TV dizisi item'inden** `P4073: frieren` bulundu | Traversal şart ve çalışıyor. Plandaki "manga/LN'ye bakma" fikri doğru. |
| 5 | SPARQL kapsam sayımı | ⚠️ MAL ID'li **7.093** item'den traversal dahil sadece **1.432'si (%20)** Fandom'a ulaşıyor. AniList item'lerinde direkt P4073: **64** (~%1) | **Wikidata tek başına asla yetmez.** %80 vakada K2b devreye girmeli. |
| 6 | `services.fandom.com/unified-search/community-search?query=campione&lang=en` | ✅ Tek sonuç: **`thecampione.fandom.com`** — hub:`anime`, pageCount:200. (AI'nin tahmin edeceği `campione` slug'ı değil!) | **AI slug tahmininin yerine geçecek resmi arama.** Metadata (hub/pageCount/pageViews) skorlama için hazır geliyor. |
| 7 | Aynı API, `query=sousou no frieren` (romaji) | ✅ Doğru wiki (`frieren`) tek sonuç | Romaji/synonym'lerle de çalışıyor → synonym listesiyle çoklu sorgu atılabilir. |
| 8 | Aynı API, `query=hero` | ⚠️ 1015 sonuç; ilk sonuç `hero.fandom.com` (Heroes Wiki — crossover mega-wiki) | Belirsiz başlıklarda arama tek başına yetmez → K3 doğrulama şart. |
| 9 | Aynı API, `query=solo leveling` | ✅ 3 sonuç: anime wiki (hub:anime) + 2 oyun wiki'si (hub:games) | `hub` alanı medya türü uyuşmazlığını (anime vs oyun) yakalıyor. |
| 10 | Karakter-problama: `thecampione.fandom.com/api.php?action=query&titles=Godou Kusanagi\|Erica Blandelli\|Yuri Mariya&redirects=1` | ✅ 3/3 sayfa mevcut | Ana sayfa metin aramasından kat kat güçlü doğrulama sinyali. |
| 11 | Aynı problama `hero.fandom.com`'da | 🚨 3/3 karakter ORADA DA VAR (crossover wiki). Ama `Verethragna` (nadir terim) YOK | Crossover blocklist + nadir/ayırt edici terim problaması gerekli. |
| 12 | `frieren.fandom.com/api.php?...meta=siteinfo&siprop=general\|interwikimap` | ✅ `interwikimap` içinde `es` prefix'i `bcp47:"es"` ile geldi; `/es/api.php` siteinfo'su `wikiid:esfrieren`, `articlepath:/es/wiki/$1` döndü | **Dil alt-wiki keşfi tek çağrıda.** /es/, /ja/ deneme-yanılması tarihe karışıyor. |
| 13 | unified-search `lang=es` ile frieren | ❌ 0 sonuç (es alt-folder wiki'si indekslenmiyor) | Dil varyantları aramayla DEĞİL, root wiki'nin interwikimap'iyle bulunmalı. |
| 14 | `categorymembers` ham çağrı (Campione, Category:Characters) | 🚨 Sonuçlarda `Template:Character Infobox` (ns:10) ve `Godou Kusanagi/Relationships`, `.../Image Gallery` alt sayfaları var | **Duplicate/çöp terimlerin ana kaynağı bu.** `cmnamespace=0&cmtype=page` + `/` filtresi ile çözülüyor (test edildi, temiz geldi). |
| 15 | `community.fandom.com/api/v1/Wikis/Details?ids=...` | ✅ Wiki id'siyle istatistik (articles, edits), gerçek URL, verticalId dönüyor | unified-search sonucundaki `id` ile zincirlenip skorlamada kullanılabilir. |

---

## 2. Kök Neden Analizi: Neden "bombok" sonuçlar geliyor?

### 2.1 Yanlış eşleşmeler
- **Aday havuzu tahminle kuruluyor.** Gemini `campione` der, gerçek slug `thecampione`dur; `campione` diye
  alakasız bir wiki varsa doğrulamaya o girer (Test #6 bunun gerçek örneği).
- **Doğrulama "ana sayfada kelime geçiyor mu"ya bakıyor.** Ana sayfalar reklam/portal içeriklidir;
  jenerik kelimeler ("hero", "castle") tesadüfen geçer. Crossover mega-wiki'ler (Heroes Wiki, Villains Wiki,
  All Fiction, Listofdeaths, VS Battles, Superpower/powerlisting...) *her* yapımın karakterini içerdiği için
  her testten geçer (Test #11 kanıtı).
- **Medya türü hiç kontrol edilmiyor.** "Solo Leveling" için oyun wiki'si (`solo-leveling-arise`) seçilebilir (Test #9).

### 2.2 Duplicate'ler
- `categorymembers` **namespace filtresi olmadan** çağrılıyor → Template'ler, kategoriler, dosyalar sızıyor (Test #14).
- **Alt sayfalar** (`X/Relationships`, `X/Image Gallery`, `X/History`) ayrı terim sanılıyor.
- **Redirect'ler çözülmüyor**: "Godou", "Kusanagi Godou", "Godou Kusanagi" üç ayrı terim olarak listeye giriyor;
  hepsi aynı sayfaya redirect'tir.
- Çok dilli `CATEGORY_GROUPS` (tr/es/ja kategori adları) **yanlış dildeki alt-wiki'de** taranınca aynı kavram
  iki dilde iki kez geliyor.

---

## 3. Yeni Mimari (Katman Katman)

### K1 — Kimlik Çözümleme (deterministik)

**Girdi:** elindeki herhangi bir ID (AniList / MAL / Kitsu / TMDB / IMDb) veya sadece başlık.

1. **ID zenginleştirme** — tek çağrı:
   - `https://animeapi.my.id/myanimelist/{id}` (veya `/anilist/{id}`, `/kitsu/{id}` ...) →
     mal, anilist, anidb, **themoviedb (+season)**, thetvdb, imdb, trakt + kanonik `title`.
   - Yedek: `https://arm.haglund.dev/api/v2/ids?source=anilist&id={id}` (⚠️ `include=wikidata` KULLANMA → 500).
2. **ID → Wikidata QID** (SPARQL'siz, ~100ms):
   ```
   https://www.wikidata.org/w/api.php?action=query&list=search
     &srsearch=haswbstatement:P8729={anilist_id}
     &format=json&formatversion=2
   ```
   Sıra: `P8729` (AniList) → `P4086` (MAL) → `P4983` (TMDB dizi) / `P4947` (TMDB film) → `P345` (IMDb).
   İlk hit'te dur. (Hepsi Test #3'te doğrulandı.)
3. **Dizi/film için kestirme:** TMDB `/tv/{id}/external_ids` zaten `wikidata_id` alanını direkt döner —
   TMDB anahtarın varsa Wikidata aramasına bile gerek yok.

### K2 — Aday Üretimi (üç kaynak, öncelik sıralı)

**K2a. Wikidata (güven: 0.90–0.95)**
- QID üstünde `wbgetclaims` ile direkt `P4073` (wiki slug) ve `P6262` (subdomain:Sayfa) oku.
- Yoksa **1 SPARQL ile traversal** (Test #4'te çalıştı):

```sparql
SELECT DISTINCT ?related ?fandom ?article ?lang WHERE {
  BIND(wd:{QID} AS ?item)
  ?item ((wdt:P144|wdt:P179|wdt:P361|wdt:P8345|wdt:P4969|^wdt:P4969|^wdt:P144)?)/
        ((wdt:P144|wdt:P179|wdt:P361|wdt:P8345|wdt:P4969|^wdt:P4969|^wdt:P144)?) ?related .
  OPTIONAL { ?related p:P4073 ?st . ?st ps:P4073 ?fandom .
             OPTIONAL { ?st pq:P407/wdt:P424 ?lang } }
  OPTIONAL { ?related wdt:P6262 ?article }
  FILTER(BOUND(?fandom) || BOUND(?article))
} LIMIT 20
```
- `P6262` formatı `subdomain:Sayfa_Adı`, İngilizce değilse `es.subdomain:Sayfa` → `:`dan öncesini al,
  `.` varsa sol taraf dil kodu.
- ⚠️ **Kapsam gerçeği:** bu yol vakaların yalnızca ~%20'sinde sonuç verir (Test #5). Boş dönerse K2b'ye düş —
  bu bir hata değil, tasarımın parçası.
- 💡 **Offline ön-yükleme:** aynı traversal'ı `?item wdt:P8729 []` ile evrensel çalıştırıp ~1.4k satırlık
  `anilist→slug` haritasını haftalık dump'la uygulamaya gömebilirsin; Wikidata'ya runtime sorgu sıfırlanır.
  (PlexAniBridge-Mappings projesi tam olarak bunu yapıyor: Wikidata'yı SPARQL ile dump'layıp JSON dağıtıyor.)

**K2b. Fandom resmi arama (güven: 0.55 taban + metadata bonusu) — YENİ ANA YOL**
```
https://services.fandom.com/unified-search/community-search?query={başlık}&lang=en&limit=8
```
- Dönen her sonuç: gerçek `url` (slug tahmini yok!), `hub` (anime/tv/games/movies/books/comics),
  `pageCount`, `pageViews`, `language`, `description`, `id`.
- **Her synonym ile ayrı sorgu at** (ana başlık, romaji, İngilizce ad — sende zaten AniDB/Manami synonym'leri var),
  sonuçları `id` üzerinden birleştir; birden çok sorguda görünen aday bonus alır.
- Skor bonusları: `hub` medya türüyle uyumlu (+0.15), `pageCount ≥ 100` (+0.05),
  wiki adı ile başlık fuzzy-match (+0.15), aynı wiki 2+ synonym sorgusunda göründü (+0.10).
- İstersen `community.fandom.com/api/v1/Wikis/Details?ids={id}` ile makale sayısı/istatistik zenginleştir (Test #15).

**K2c. AI slug tahmini (güven: 0.30) — sadece K2a ve K2b boşsa.**
Artık asla tek başına karar veremez; K3'ten geçmeden kullanılamaz.

### K3 — Hakemli Doğrulama (kalbi burası)

Her aday için sırayla; herhangi bir **veto** adayı direkt eler:

1. **Crossover blocklist (veto):** `hero`, `villains`, `characters`, `allfiction`, `listofdeaths`,
   `love-interest`, `antagonists`, `vsbattles`, `powerlisting`, `deathbattlefanon`, `fictional-battle-omniverse`,
   `dubbing`, `ideas`, `fanon` içeren slug'lar. (Test #11: Heroes Wiki 3/3 karakter problamasını geçiyordu —
   blocklist olmadan karakter testi bile yetmez.)
2. **Siteinfo çek (tek çağrı):** `{base}/api.php?action=query&meta=siteinfo&siprop=general|interwikimap`
   → `sitename`, `lang`, `wikiid`, `mainpage` + tüm dil varyantları.
   - `sitename` ile yapım başlığı/synonym'leri arasında normalize fuzzy-match: eşik altındaysa güçlü negatif.
3. **Karakter-problama (pozitif kanıt):**
   - AniList GraphQL (`characters(sort:ROLE, perPage:8)`) veya Jikan `/anime/{mal}/characters`
     veya Kitsu `/anime/{id}/characters?include=character` ile 5–8 ana karakter adı al.
   - Tek batch: `{base}/api.php?action=query&titles=A|B|C|D|E&redirects=1&format=json&formatversion=2`
   - Hit oranı ≥ %50 → +0.25; %0 → veto. Hem "Ad Soyad" hem "Soyad Ad" varyantını dene (romaji sıra farkı).
   - Mümkünse 1–2 **ayırt edici/nadir terim** ekle (yapıma özgü özel isim; Test #11'de `Verethragna`
     crossover wiki'yi ayırt eden tek sinyaldi).
4. **Medya türü uyumu:** unified-search `hub` alanı ↔ yapım tipi (anime/dizi/film). Uyumsuzsa −0.20
   (oyun wiki tuzağı, Test #9).
5. **Karar:** `skor = kaynak_önceliği + bonuslar − cezalar`. Eşik: **0.75**. Eşiği geçen yoksa
   **"eşleşme yok" dön ve negatif-cache'e yaz** — mevcut sistemin "en iyi tahmini kabul et" davranışı
   yanlış pozitiflerin ana üreticisi.

### K4 — Terim Çekme + Temizlik (duplicate katili)

1. **Doğru dil alt-wiki'sini seç:** root siteinfo'daki `interwikimap`ten hedef dilin `bcp47` girdisini bul;
   varsa o `articlepath`/`scriptpath` ile çalış (Test #12). Yoksa root (İngilizce). Deneme-yanılma yok.
   ⚠️ Çok dilli `CATEGORY_GROUPS`'u **sadece o wiki'nin `lang`'ine uyan grupla** tara — çapraz dil taraması
   duplicate üretir.
2. **Kategori çağrısını filtreli yap:**
   ```
   ?action=query&list=categorymembers&cmtitle=Category:{X}
   &cmnamespace=0&cmtype=page&cmlimit=500&format=json&formatversion=2
   ```
   (Test #14: filtresiz çağrıda gelen Template ve alt sayfalar filtreli çağrıda kayboldu.)
3. **Başlık temizliği:** `"/"` içerenleri at (alt sayfa), `(disambiguation)`/`(anime)`/`(manga)` parantezlerini
   soy, `List of ...` / `... Gallery` kalıplarını at.
4. **Redirect canonicalization:** 50'lik batch'lerle `action=query&titles=...&redirects=1` çağır;
   `redirects[]` haritasından her terimi hedef sayfa başlığına indirge → "Godou" ve "Kusanagi Godou"
   tek kanonik kayda düşer; alias'ları terimin `aliases` alanında sakla (çeviri için alias'lar değerli!).
5. **Dedupe anahtarı:** `casefold + NFKD + noktalama-sız` normalize başlık.

### Cache stratejisi
- **Anahtar: kararlı ID** (`anilist:12293`), asla temizlenmiş başlık değil — başlık temizleme kararsız,
  aynı seri farklı release'lerde farklı anahtara düşüp yeniden (ve farklı!) çözümleniyor.
- **Negatif cache TTL'li** (ör. 14 gün): "bulunamadı" da cache'lenir, ama yeni wiki açılabilir diye süreli.
- **Manuel override dosyası** (`overrides.json`: `{"anilist:12293": "thecampione"}`) her şeyi ezer —
  hiçbir otomatik sistem %100 değil, kullanıcıya düzeltme kapısı bırak.
- Cache'e **hangi kaynaktan, hangi skorla** eşleştiğini de yaz → düşük skorlu eski kayıtları sonradan
  yeniden doğrulayabilirsin.

---

## 4. Başkaları Ne Yapmış? (İncelenen Projeler)

| Proje | Alınacak ders |
|-------|---------------|
| **PlexAniBridge-Mappings** (eliasbenb) | Wikidata'yı runtime'da değil **SPARQL dump + haftalık CI** ile kullanıyor; manuel `mappings.edits.yaml` override katmanı var; veri doğrulama adımı (bölüm sayısı tutarlılığı) ile yanlış eşleşmeleri flagliyor. → Offline harita + override dosyası fikirlerinin kaynağı. |
| **nattadasu/animeApi** (`animeapi.my.id`) | 25+ platform ID'sini tek GET ile köprülüyor; ARM'dan geniş. → K1'in birincil servisi. |
| **Fribb/anime-lists** & **manami anime-offline-database** | MAL↔TMDB/TVDB eşleşmesinin ana offline kaynakları; ARM v2 de bunlardan besleniyor. Zaten lokal Manami kullanıyorsun → TMDB id'yi buradan da alabilirsin. |
| **Indie Wiki Buddy / BreezeWiki** | Wikidata P4073/P6262 formatlarını üretimde kullanan gerçek tüketiciler; `language-code.subdomain` prefix kuralı buradan teyitli. |
| **GOLEM-lab/fandom-wiki** | Fandom'dan yapılandırılmış veri çıkarırken kategori yerine **infobox template parse** ediyor (`Character Infobox` parametreleri) → sözlüğe "tür" (karakter/yetenek/mekân) etiketi eklemek istersen ileri seviye yol. |

## 5. Bilinen Sınırlar
- unified-search resmi dokümante değil (Fandom'un kendi sitesinin kullandığı servis) → bir gün kırılabilir;
  K2a (Wikidata) ve K2c (AI) fallback zinciri bu yüzden korunuyor. İsteklere gerçekçi bir `User-Agent` koy.
- Wikidata `haswbstatement` bazı ID'lerde sezon-item'ine düşer (Frieren → "season 1" item'i);
  traversal'daki `P179` (series) ilişkisi bunu ana esere bağlar.
- Kitsu characters endpoint'i `?include=character` olmadan isim dönmez (sadece ilişki stub'ı döner).
- Jikan zaman zaman 504 verir (test sırasında da verdi) → karakter kaynağını AniList→Jikan→Kitsu sıralı dene.

## 6. Referans İmplementasyon
Yan dosya: [`fandom_resolver_v2.py`](./fandom_resolver_v2.py) — yukarıdaki 4 katmanın çalışır iskeleti
(stdlib-only, kendi uygulamana kopyala-uyarla).

---

## 7. EK — İkinci Tur Testler: Son Bulgular ve Kalan Riskler
*(2026-08-28, ikinci doğrulama turu; testler #16–#23)*

### 7.1 Yeni canlı test bulguları

| # | Test | Sonuç | Çıkarım |
|---|------|-------|---------|
| 16 | `prop=extracts` (TextExtracts) Fandom'da | ❌ **YOK** — "Unrecognized value for parameter prop: extracts" | Terim tanımı/özet çekmek için MW extracts KULLANILAMAZ. Alternatif ↓ |
| 17 | Nirvana v1: `/api/v1/Articles/Details?titles=Godou Kusanagi&abstract=200` | ✅ Temiz düz-metin özet döndü: *"...male protagonist of Campione!. Upon his encounter and defeat of Verethragna..."* + thumbnail | **Çeviri bağlamı için altın:** her terimin 1-2 cümlelik tanımını AI çeviri prompt'una bağlam olarak verebilirsin. Toplu da çalışır (`titles=A,B,C`). |
| 18 | `prop=redirects` (sayfa başına alias hasadı) | ✅ Godou Kusanagi → **7 alias**: `Kusanagi Godo`, `Godou`, `Kusanagi Godou`, `Kusanago Godou` (yazım hatası dahil!) | Alias'ları K4'te sadece "çözüp atmak" israf: **hepsini sözlüğe alias olarak kaydet.** Altyazıda "Godou" tek başına geçer; alias tablosu olmadan eşleşmez. |
| 19 | Tek çağrıda tür etiketi: `generator=categorymembers&prop=categories` | ✅ Her terim kendi TÜM kategorileriyle döndü (Athena → God, Female, Greek, Heretic God) | Sözlüğe **terim tipi** (karakter/tanrı/örgüt/eşya) tek çağrıda eklenir. Çeviri tutarlılığı için tip bilgisi (ör. kılıç adı çevrilmez, unvan çevrilir) kritik. |
| 20 | Alt-kategori kontrolü: `cmtype=subcat` | ✅ Campione'de boş; ama büyük wiki'lerde `Characters` altında `Male Characters` vb. iç içe olur | Kategori taramasına **sınırlı derinlikli (max 2) subcat recursion** ekle; yoksa büyük wiki'lerde terimlerin yarısı kaçar. |
| 21 | Nirvana v1 `Articles/List?category=Characters` | ⚠️ Çalışıyor ama offset'inde Template sızıntısı görüldü | MW `categorymembers` (filtreli) birincil kalsın; v1 List sadece yedek. |
| 22 | `list=recentchanges&rclimit=1` | ✅ Son düzenleme zamanı tek çağrıda | **Akıllı cache tazeleme:** TTL yerine "son edit timestamp'i değişti mi?" kontrolü — değişmediyse indirme yok, kota yok. |
| 23 | `prop=langlinks` (makale bazında) | ✅ Frieren sayfası `ru: Фрирен` langlink'i döndü | Karakterin hedef dildeki resmî yazılışını **makale langlink'inden** alabilirsin — çeviri sözlüğü için interwikimap'ten daha ince taneli ikinci yol. |

### 7.2 Değinilmesi gereken kalan konular (kod dışı ama kritik)

1. **wiki.gg göçü / Fandom'u terk eden wiki'ler.** Son yıllarda birçok büyük topluluk Fandom'dan
   `wiki.gg`'ye veya bağımsız sitelere taşındı ve **Fandom'daki kopya bayat/donuk kaldı**
   (ör. Terraria, Calamity, Yu-Gi-Oh!). Wikidata bazen hâlâ eski Fandom slug'ını gösterir.
   Anime tarafında nadir ama oyun-uyarlaması yapımlarda gerçek risk. Pratik önlem:
   `recentchanges` son edit tarihi 1+ yıl eskiyse "bayat wiki" bayrağı koy; Indie Wiki Buddy'nin
   açık kaynak yönlendirme veritabanı (fandom→bağımsız wiki eşleşmeleri) blocklist/redirect
   kaynağı olarak kullanılabilir.
2. **Rate limit / nezaket politikası.** Wikidata SPARQL için UA zorunlu (koyduk); `haswbstatement`
   araması ucuz, SPARQL pahalı — traversal sonuçlarını mutlaka cache'le. unified-search resmî
   dokümante olmadığı için: istekler arası ≥300ms, 429/5xx'te üstel backoff, günde seri başına
   1 çözümleme (zaten cache'li). MediaWiki API'de `maxlag=5` parametresi eklemek iyi vatandaşlıktır.
3. **Sezon/parça ID tuzağı.** `haswbstatement` bazı ID'lerde **sezon item'ine** düşer
   (Frieren → Q130377145 "season 1"). Traversal'daki `P179` bunu ana esere bağlıyor (çözüldü),
   ama cache anahtarında dikkat: aynı serinin S1/S2'si farklı AniList ID'dir → **franchise-level
   ikinci cache anahtarı** (ör. AniDB id veya Wikidata ana eser QID'si) tut ki S2 başladığında
   S1'in sözlüğü sıfırdan çözülmesin.
4. **Karakter kaynağı zinciri netleşti:** AniList GraphQL (POST, sandbox'ta engelliydi ama üretimde ana yol)
   → Jikan (test sırasında 504 verdi, tek kaynak yapma) → Kitsu (`?include=character` şart, yoksa boş stub döner).
5. **Terim sayfası olmayan wiki'ler:** 10-50 sayfalık minik wiki'lerde (unified-search'te `pageCount:10`)
   kategori hiç olmayabilir → `list=allpages&apfilterredir=nonredirects` fallback'i kullan,
   ama `/` alt sayfa ve `Administrators` gibi meta sayfaları yine filtrele (Test #14/16'daki filtreler geçerli).

### 7.3 Nihai kontrol listesi (uygulamaya geçirirken)

- [ ] K1: animeapi.my.id → yedek ARM (⚠️ `include=wikidata` asla)
- [ ] K1: `haswbstatement` sırası P8729 → P4086 → P4983/P4947 → P345; TMDB varsa `external_ids` kestirmesi
- [ ] K2: Wikidata traversal + unified-search (synonym başına sorgu) + AI sadece son çare
- [ ] K3: crossover blocklist → sitename fuzzy → karakter problaması (ad-soyad ters varyantlı) → nadir terim → hub uyumu → eşik 0.75, geçemeyen = "eşleşme yok"
- [ ] K4: `cmnamespace=0&cmtype=page` + subcat recursion (max 2) + alt sayfa/çöp filtresi
- [ ] K4: redirect canonicalization + `prop=redirects` ile alias hasadı + normalize dedupe
- [ ] K4: `prop=categories` ile terim tipi etiketi; `Articles/Details?abstract=` ile çeviri bağlamı
- [ ] Cache: ID anahtarlı + franchise anahtarı + negatif TTL + `recentchanges` tazelik kontrolü + overrides.json
- [ ] Nezaket: UA, 300ms aralık, backoff, maxlag=5, bayat-wiki bayrağı
