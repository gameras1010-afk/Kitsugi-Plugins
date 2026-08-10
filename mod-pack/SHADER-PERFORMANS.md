# 🎮 SHADER PERFORMANS REHBERİ — RTX 4060 Ti + 5900X (1.21.1 NeoForge, 2026-08-09)

**Senin PC:** Ryzen 9 5900X (12C/24T) · RTX 4060 Ti · 32GB DDR4 3600 · Windows
**Mevcut client paketi:** Sodium + Iris 1.8.14-beta.1 + ImmediatelyFast + EntityCulling + ModernFix + FerriteCore + EMF/ETF

---

## 1️⃣ GERÇEK: "Her şey max" hiçbir kartta 60+ FPS vermez

RTX 4060 Ti güçlü ama "en yüksek ayarlar" dediğin şeylerden bazıları **her kartı öldürür**:
- **Volumetric Lighting / Clouds** (en büyük katil — FPS'i %40-60 düşürür)
- **4096x Shadow Resolution** + uzun shadow distance
- **Path tracing / SSGI** (Photon, SEUS PTGI) — 4060 Ti'da 30-40 FPS'e düşer
- **Motion Blur + yüksek Bloom** — GPU'yu boşuna yer

**Akıllı yöntem:** "Görsel olarak max görünen ama FPS'i koruyan" ayar reçetesi (aşağıda).

## 2️⃣ EN İYİ SHADER PAKETLERİ (FPS/görsel dengesi)

| Paket | Görsel | FPS (4060 Ti) | Tavsiye |
|---|---|---|---|
| **Complementary Reimagined** | Çok iyi, dengeli | 100+ (1080p) / 70-90 (1440p) | ⭐ En iyi seçim |
| **Complementary Unbound** | Biraz daha güzel | 80-110 (1080p) | İkinci seçenek |
| **BSL** | İyi, popüler | 70-100 (1080p) | Alternatif |
| **MakeUp Ultra Fast** | İyi, hafif | 120+ | Yüksek FPS istiyorsan |
| Photon / SEUS PTGI | Path tracing, muhteşem | 30-50 | ❌ "max" hedefinde önermem |

> İndirme: kurulu `iris_shader_folder` içindeki shader'ların yanına yeni klasör. (Iris → Shader Packs → Open Folder)

## 3️⃣ "MAX GÖRÜNÜM, AKILLI KISMA" REÇETESİ (Complementary Reimagined)

Iris shader ayarlarında (shader seçiliyken sağ alttaki "Shader Settings"):

| Ayar | Öneri | FPS etkisi |
|---|---|---|
| **Render Quality (Iris)** | 0.9 (veya 1.0) | %10-15 kazanç, görsel fark az |
| **Shadow Resolution** | 2048 (4096 değil) | Büyük kazanç, gölge farkı az |
| **Shadow Distance** | 64-96 | Orta kazanç |
| **Volumetric Lighting** | **OFF** (veya LOW) | 🔥 En büyük kazanç |
| **Volumetric Clouds** | **OFF** (veya LOW) | 🔥 Büyük kazanç |
| **Cloud Shadows** | OFF | Orta |
| **Motion Blur** | OFF | Küçük |
| **Bloom** | LOW/Medium | Küçük-orta |
| **TAA (Anti-aliasing)** | AÇIK (Iris kendi) | Görsel + FPS dostu |
| **SSGI / Path Tracing** | OFF | Zaten kapalı olmalı |

**Sonuç:** "Her şey max" gibi görünür, FPS ikiye katlanır.

## 4️⃣ SODIUM AYARLARI + YENİ 2 MOD (doğrulandı — manifeste eklendi)

### Sodium ayarları (Video Settings → Sodium)
- **Render Distance:** 12-16 yeter (20+ shader'da gereksiz GPU yükü)
- **Translucency Sorting / Culling:** açık bırak
- **"Use Compact Vertex Format"** → on (zaten varsayılan)

### 🆕 Sodium Extra 0.9.3 (1.21.1 NeoForge ✅)
- Zırh gizleme, bulut/kar/yaprak animasyonlarını kapatma, parçacık limiti, "hide features" — **FPS'i hissedilir artırır**
- İndir: https://cdn.modrinth.com/data/PtjYWJkn/versions/iJsZtWpc/sodium-extra-neoforge-0.9.3%2Bmc1.21.1.jar

### 🆕 MoreCulling 1.0.9 (1.21.1 NeoForge ✅)
- Daha fazla yüz culling — **büyük yapılar/ormanlarda büyük FPS artışı** (Cloth Config zaten pakette → dep tamam)
- İndir: https://cdn.modrinth.com/data/51shyZVL/versions/cJQs4xht/moreculling-neoforge-1.21.1-1.0.9.jar

İkisini de `mods/`'a at (client). Sunucuya gerek yok.

## 5️⃣ LAUNCHER / JVM (client — Windows)

```text
Minecraft 1.21.1 + NeoForge profili → JVM Arguments:
-Xmx8G -Xms4G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=100 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:SurvivorRatio=32 -XX:MaxTenuringThreshold=1
```
- 8G heap 32GB RAM'de rahat (shader + modlar için)
- `AlwaysPreTouch` client'ta OK (kısa yükleme, stabilite)

## 6️⃣ NVIDIA AYARLARI (Control Panel → javaw.exe veya Minecraft.exe)

| Ayar | Değer |
|---|---|
| Güç yönetimi modu | **Maximum performance** |
| Threaded optimization | **On** |
| Dikey senkron (V-Sync) | **Off** (Iris'in kendi frame limitini kullan) |
| Low Latency Mode | **On** (Ultra değil) |
| Çözünürlük/ölçekleme | Oyun içi Iris Render Quality ile yönet |

Iris → "Frame Limit" = monitör Hz'in (144 ise 144, 165 ise 165).

## 7️⃣ BEKLENTİ (gerçekçi)

- **1080p + Complementary Reimagined + reçete** → **100-140 FPS**
- **1440p + aynı** → **70-100 FPS**
- **Her şey max (volumetric açık + 4096 shadow + PT)** → 30-50 FPS (kaçınılacak)
- Chunk yükleme: sunucu tarafı C2ME + pregen zaten hızlı → client'ta Sodium + MoreCulling ile uçarken donma azalır

## 8️⃣ EKSTRA SHADER/PERFORMANS MODLARI (2026-08-09 doğrulandı)

| Mod | 1.21.1 | Ne işe yarar | FPS etkisi |
|---|---|---|---|
| **Reese's Sodium Options 2.2.3** | ✅ NeoForge | Sodium ayarlarını tam/aranabilir UI yapar (ince ayar kolay) | Dolaylı — ayar yönetimi |
| **Nvidium 0.4.1-beta10** | ⚠️ **Fabric** (Connector ile) | NVIDIA GPU'larda renderer'ı GPU-driven yapar — **NVIDIA'da en büyük FPS artışı** | 🔥 Çok büyük (NVIDIA) |
| ~~MemoryLeakFix~~ | ❌ NeoForge 1.21.1 doğrulanamadı | Bellek sızıntısı onarımı | — |
| ~~Cull Less Leaves~~ | ❌ NeoForge 1.21.1 doğrulanamadı | Yaprak culling | MoreCulling zaten var |
| ~~FastAnim~~ | ❌ NeoForge 1.21.1 doğrulanamadı | Animasyon optimizasyonu | — |

### ⚠️ Nvidium DİKKAT (sürüm uyumu)
- Nvidium **Fabric** modudur → NeoForge'de **Sinytra Connector** ile çalışır (pakette var)
- Ama **Sodium 0.6.13 ile eşleşir** — senin kurulu **Sodium 0.8.12** ile **uyumsuzluk riski** var (çakışabilir/crash olabilir)
- Bu yüzden **DENEYSEL** işaretli → script `--include-experimental` ile indirir; çakışırsa çıkar, zararsız
- **Test:** kopya client'ta dene → F3'te "Nvidium active" yazıyorsa çalışıyor, FPS artışı gör; crash olursa sil

### Neden bu kadar az "yeni" mod?
Çünkü en iyiler **zaten pakette**: Sodium, Iris, ImmediatelyFast, EntityCulling, EMF/ETF, ModernFix, FerriteCore, BadOptimizations + yeni eklenen Sodium Extra + MoreCulling. Shader performansının %80'i **ayar** (%20 mod) — reçete (volumetric OFF, shadow 2048, shader paketi seçimi) en büyük kazancı verir.

## 9️⃣ NVIDIA'DA EN BÜYÜK KAZANIM SIRASI
1. Complementary Reimagined + reçete (volumetric OFF) → ~2x FPS
2. Nvidium (çalışırsa) → +%30-60 daha
3. Sodium Extra + MoreCulling + Reese's UI → ayarları iyileştir
4. JVM 8G + NVIDIA max performance → stabilite

## 📌 ÖZET (yapılacaklar)

1. Shader'ı **Complementary Reimagined** yap
2. **Reçetedeki ayarları** uygula (volumetric OFF = anahtar)
3. **Sodium Extra + MoreCulling** ekle (manifeste işlendi, `indir_modlar.py` indirir)
4. **JVM 8G + NVIDIA maximum performance + Iris frame limit**
5. Ölç: F3 ekranındaki FPS + `/spark tps` (server) → reçeteyle büyük fark görürsün
