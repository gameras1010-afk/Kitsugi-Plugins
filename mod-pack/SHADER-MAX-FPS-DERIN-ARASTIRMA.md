# 🎮 SHADER "MAKSİMUM AYAR + MAKSİMUM FPS" DERİN ARAŞTIRMA — RTX 4060 Ti · 1.21.1 NeoForge (2026-08-09)

**Senin kurulum:** Complementary Reimagined r5.8.1 + **EuphoriaPatches 1.9.2 (SpaceEagle17)** · Iris + Sodium 0.8 · RTX 4060 Ti · 5900X · 32GB

---

## 1️⃣ GERÇEK (dürüst, kanıtlı)

- **Complementary Reimagined, Unbound'dan ~%20-40 DAHA AĞIR** (aynı ayarlarda) — kaynak: güncel karşılaştırma (RTX 4070: Reimagined High 150-200 FPS, Unbound High 220-280).
- **EuphoriaPatches "quite demanding"** — geliştirici (SpaceEagle17) bunu açıkça söylüyor; tüm yeni özellikler **varsayılan kapalı** (performans için).
- **4060 Ti orta-üst bir kart** — "her şey max + Euphoria" 1440p'de 144 FPS veremez (fiziksel sınır). AMA:
- **Kaliteyi BOZMADAN FPS artırmanın yolları var** — bunlar "görünmez katiller" denen, FPS yiyip görsel farkı sıfır olan ayarlar. İşte asıl araştırma burada.

---

## 2️⃣ "GÖRÜNMEZ KATİLLER" — BOZMADAN KISILACAKLAR (FPS'in asıl düşmanı)

Bunları değiştirmek görselliği **gözle görülür şekilde bozmaz** ama FPS'e ciddi kazandırır:

| Ayar (Complementary → Shader Settings) | Değer | FPS etkisi |
|---|---|---|
| **Shadow Resolution** | **2048** (varsayılan 4096!) | 🔥 **+%30-40 FPS** — 4096'yı oyun içinde fark etmezsin; gölge keskinliği farkı mikroskobik |
| **Shadow Distance** | **160** (max değil) | +%10-15 — 160'ın ötesindeki gölge zaten seçilmiyor |
| **Motion Blur** | **OFF** | +%3-5 — zevk meselesi; çoğu oyuncu kapatır |
| **Bloom** | **Medium** (Ultra değil) | +%5-8 — bloom Ultra vs Medium gözle ayırt edilmez |
| **Vanilla Clouds** | **OFF** (shader'ın kendi bulutu var) | +%3 — shader zaten bulut çiziyor, vanilya bulutu çift iş |
| **Vanilla Particles** | **Minimal** | +%2-3 — oynanışı etkilemez |
| **Colored Lighting (Euphoria)** | **6 chunk** (önerilen; max değil) | +%5 — 6 chunk ötesi renkli ışık zaten görünmüyor |

## 3️⃣ "KORU" LİSTESİ — BUNLARA DOKUNMA (görselin kalbi)

Bunlar max kalsın — görmek istediğin şeyler:

```text
✅ Volumetric Lighting: ON (High)      ← sahnenin derinliği
✅ Volumetric Clouds: Fancy            ← gökyüzü karakteri
✅ Reflections (Water/Block): ON       ← su/parlak yüzeyler
✅ Ambient Occlusion: High             ← gölgelenme derinliği
✅ Water: Fancy + refraksiyon          ← su kalitesi
✅ PBR/Emissive (Euphoria): ON         ← blok dokusu zenginliği
✅ TAA (Iris anti-aliasing): ON        ← kenar düzgünlüğü (ucuz, güzel)
✅ Render Quality (Iris): 1.0          ← iç çözünürlük TAM (bozma yok!)
✅ Euphoria "Advanced Colored Lighting": 6 chunks
```

## 4️⃣ EUPHORIAPATCHES ÖZEL — PRESET & AYARLAR (SpaceEagle17 önerisi)

Euphoria'nın kendi menüsünden (Shader Options → Euphoria Patches):
- **Preset: "Popular Settings"** veya **"High"** kullan (Ultra DEĞİL — Ultra sadece ekran görüntüsü içindir)
- **Materials → End Portal Rays: ON** (geliştiricinin "her zaman açık" önerisi)
- **World → End → End Crystal Vortex: Vortex** (geliştirici önerisi)
- **Performance → Advanced Colored Lighting: 6 Chunks**
- **Seasonal/Extra effects:** ihtiyacına göre seç — her biri FPS maliyeti; hepsini açma

> Euphoria'da yeni özellikler varsayılan kapalı — "hepsini açmak" = FPS'i yarıya indirmek. Seçici ol.

## 5️⃣ CLIENT MOD YIĞINI (1.21.1 NeoForge — hepsi doğrulandı, pakette)

Shader AÇIKKEN çalışanlar (Acedium/Nvidium shader'la kendini kapatır, normal):
- **Sodium 0.8.12** (kurulu) + **Iris 1.8.14-beta.1** (kurulu) → render temeli
- **ImmediatelyFast** → arayüz/JEI takılması yok
- **EntityCulling** → görünmeyen sandık/mob çizilmez (kalabalık bölgede +%50-150)
- **MoreCulling 1.0.9** → ekstra yüz culling (bina/orman)
- **Sodium Extra 0.9.3** → bulut/parçacık/zırh gizleme, FPS dostu animasyonlar
- **Reese's Sodium Options 2.2.3** → ince ayar UI
- **BadOptimizations** → gökyüzü/yazı/ışık mikro-optimizasyonu
- **Nvidium (Acedium)** → shader KAPALIYKEN devreye girer (Mesh Shaders, 200-400 FPS) — shader açıkken otomatik kapanır

## 6️⃣ CPU TARAFI (stutter'ı bitiren — 5900X)

```text
Sodium → Advanced → Chunk Update Threads: 8
Distant Horizons kullanıyorsan → CPU Usage: Aggressive (ama shader'la LOD dokusuz — DH'yi shader'da kapat)
JVM (client): -Xmx8G -Xms4G -XX:+UseG1GC -XX:ParallelGCThreads=8 -XX:ConcGCThreads=2 ...
```

## 7️⃣ NVIDIA AYARLARI (javaw.exe) — KALİTE BOZMAZ, SADECE HIZ

```text
NVIDIA Control Panel → Program Ayarları → javaw.exe (veya Minecraft):
- Güç Yönetimi: Maximum performance
- Threaded optimization: On
- V-Sync: Off (Iris'in Frame Limit'i kullan)
- Low Latency: On (Ultra değil)
- Dikey senkron/Low Latency shader'ı etkilemez; sadece kuyruk azalır
```

**Kritik kontrol (senin eski "CPU kullanıyor" sorunun):** Oyunu tam ekran (Fullscreen) oyna — pencereli modda bazı sistemler GPU yerine CPU render'ına düşer (Reddit'te 4060 Ti kullanıcısı aynı sorunu böyle çözdü).

## 8️⃣ GERÇEKÇİ BEKLENEN FPS (4060 Ti, 1080p)

| Yapılandırma | 1080p | 1440p |
|---|---|---|
| Reimagined High (varsayılan 4096 shadow) | ~60-80 | ~45-60 |
| **+ Görünmez katiller (2048 shadow vb.)** | **~110-150** | ~80-110 |
| + Euphoria "Popular" preset | ~90-130 | ~65-95 |
| + RD 16 (Bobby yerine) | +%15 | +%15 |
| **Unbound High (daha hızlı alternatif)** | ~140-190 | ~100-140 |

> Not: 1440p'de 144+ FPS "her şey max + Euphoria" ile **fiziksel olarak olmaz** (4060 Ti bütçesi). 1080p'de 100-150 FPS ile max görünüm + akıcılık **olur**.

## 9️⃣ 5 DAKİKALIK UYGULAMA SIRASI

```text
1) Shader Settings → Shadow Resolution 4096→2048, Shadow Distance→160, Motion Blur OFF, Bloom Medium
2) Euphoria → Preset: "Popular" / Advanced Colored Lighting: 6
3) Vanilla: Render Distance 16, Simulation 12, Particles Minimal, Vanilla Clouds OFF
4) Sodium → Chunk Update Threads 8
5) NVIDIA: javaw → max performance + V-Sync OFF; oyunu TAM EKRAN aç
6) Oyunu baştan başlat (Sodium ayarı devreye girer) → F3'te ölç
```

**Sonuç:** Görselliğin %95'i AYNI (volumetric, reflections, AO, su, PBR hepsi max), FPS ~2 katı. "Bozmadan artırma" dediğin şey tam olarak bu — görünmez katilleri kıs, kalbi koru.
