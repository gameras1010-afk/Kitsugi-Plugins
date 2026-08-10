# 🗺️ YÜKSEK CHUNK GÖRÜŞÜ + SHADER = FPS DÜŞÜŞÜ — ÇÖZÜM REHBERİ (1.21.1 NeoForge, 2026-08-09)

**Senin PC:** RTX 4060 Ti · 5900X · 32GB · 1.21.1 NeoForge + Iris/Sodium + Complementary

## 🧠 ÖNCE NEDEN DÜŞÜYOR? (2 ayrı maliyet)

Yüksek render distance'ta FPS düşmesinin **2 bağımsız nedeni** var:

1. **GPU maliyeti (shader):** Render distance arttıkça shader'ın **shadow map + fragman işi** üstel artar. `Complementary` gibi shader'larda RD 20+ = her karede devasa piksel yükü.
2. **CPU maliyeti (chunk build):** Her yeni chunk **CPU'da build edilir** (vertex üretimi, ışık, culling). RD 20+ = her saniye build edilen chunk sayısı fırlar → stutter.

**Çözümün anahtarı:** Vanilla RD'yi **düşük tut** (8-12), **uzak mesafeyi LOD (basit model) ile render et**. Böylece GPU shader yükü azalır, CPU chunk build azalır, ama gözün ufka kadar görür. İşte bunu yapan modlar:

## ✅ ÇÖZÜM 1 — Distant Horizons (DH) — ASIL CEVAP (doğrulandı)

- **DistantHorizons 3.2.0-b** — 1.21.1 **fabric + neoforge** ✅ (Modrinth, Tem 2026, beta, 30MB)
- **Ne yapar:** Vanilla render mesafesinin ötesindeki her şeyi **basitleştirilmiş LOD modeli** olarak render eder → **binlerce blok uzağı görürsün, FPS düşmez**
- İndir: https://cdn.modrinth.com/data/uCdwusMi/versions/ZpKb4kZp/DistantHorizons-3.2.0-b-1.21.1-fabric-neoforge.jar

**Kurulum (client):**
```text
1) Jar'ı client mods/'a at (sunucuya gerek yok; sunucuda da olursa /dh ile LOD pregen yapabilir)
2) Oyun içi: Ayarlar → Distant Horizons:
   - LOD Render Distance: 128-256 (görüş genişliği)
   - Quality: Medium/High (4060 Ti rahat)
   - "Fancy/Quality" yerine "Performance" modu dene
3) Vanilla Render Distance'ı 8-12'ye düşür (DH uzakları zaten render ediyor)
```

**⚠️ DH notları (dürüst):**
- **Iris shader ile LOD'lar dokusuz render olur** (geliştiricinin notu: "Iris shaders will render LODs as untextured") — yani shader açıkken uzaklar düz renk görünür. Yine de ufuk görünür, FPS yüksek kalır. Shader'sız oynarsan LOD'lar tam dokulu.
- Beta sürüm → kopya client'ta dene; glass/transparency bazı sürümlerde tuhaftı (eski notlar), 3.2.0-b'de düzeldi.
- RAM: yüksek LOD ayarında +2-4GB → client JVM'i 8G yap (rehberde var).
- Server'da da kurarsan: `/dh pregen start minecraft:overworld 0 0 375` ile LOD'ları sunucuda önceden üretirsin (oyunculara hızlı).

## ✅ ÇÖZÜM 2 — Bobby (alternatif, builder'lar için) — doğrulandı

- **Bobby 5.2.4.1+mc1.21** — 1.21.1 **Fabric** ✅ (Connector ile NeoForge'de çalışır)
- **Ne yapar:** Sunucunun view-distance'ını aşan bölgeleri **client tarafında önbelleğe alır** → server `view-distance=10` olsa bile client 32+ chunk render edebilir (dünya önbellekten gelir)
- İndir: https://cdn.modrinth.com/data/M08ruV16/versions/a8r0n94h/bobby-5.2.4.1%2Bmc1.21.jar
- **Ne zaman iyi:** Sunucu sim/view'ı düşük tutarken sen inşa/gezinti için geniş görmek istiyorsan. DH kadar "sonsuz" değil; ama doku sorunu yok (shader ile tam uyumlu).

## ✅ ÇÖZÜM 3 — ScalableLux (chunk yükleme stutter'ı) — doğrulandı

- **ScalableLux 0.3.0-alpha.0.6** — NeoForge 1.21.1 ✅ (C2ME ekibi — ishland)
- **Ne yapar:** 1.21+'deki ışık motorunu hızlandırır (Starlight'ın halefi) → **yeni chunk yüklenirken ışık hesabı hızlı biter → stutter azalır**
- İndir: https://cdn.modrinth.com/data/Ps1zyz6x/versions/w2yQbU01/ScalableLux-neoforge-0.3.0-alpha.0.6-all.jar
- **Not:** Alpha; C2ME ile birlikte kullanılması önerilir (ikisi de RelativityMC). Kopya dünyada test.

## 🎛️ SHADER'DA YÜKSEK RD İÇİN AYARLAR (Complementary)

RD'yi 20+ yapmak yerine shader ayarlarında "uzak kaliteyi" düşür:
```text
Shader Settings (Complementary):
- Render Quality (Iris): 0.9
- Shadow Resolution: 2048 (4096 DEĞİL)   ← RD artınca shadow maliyeti katlanır
- Shadow Distance: 64-96
- Volumetric Lighting: OFF (veya LOW)     ← her zaman kapalı, asıl kazandıran
- Volumetric Clouds: OFF
- Fog: açık bırak (uzakları yumuşatır, maliyeti az)
```

Vanilla/Sodium:
```text
- Render Distance: 8-12 (DH uzakları alıyor)
- Simulation Distance: ≤ Render Distance (asla daha büyük değil)
- "Advanced" → "Use Compact Vertex Format": ON
- EntityDistanceCulling (EntityCulling): açık
```

## 🎯 ÖNERİLEN KOMBO (4060 Ti + 5900X + shader + yüksek görüş)

| Katman | Ne | Sonuç |
|---|---|---|
| 1 | Vanilla RD **10-12** + **DH LOD 128-256** | Ufuk görünür, FPS sabit |
| 2 | **Complementary + reçete** (volumetric OFF, shadow 2048) | Shader maliyeti kontrol altında |
| 3 | Sodium Extra + MoreCulling + ImmediatelyFast + EntityCulling (hepsi pakette) | Chunk build + culling hızlı |
| 4 | **ScalableLux** (sunucuda) | Yeni chunk ışığı hızlı → stutter az |
| 5 | JVM 8G + NVIDIA max performance + Iris frame limit | Stabilite |

**Sonuç beklentisi:** 100+ FPS, 10 chunk vanilla + DH ile "sonsuz" görüş, stutter minimum.

## 🧵 ÇOKLU ÇEKİRDEK KULLANIMI (5900X 12C/24T) — "12 çekirdeği kullansak?"

**Gerçek:** Ana render thread = **1 çekirdek** (mimari, hiçbir mod bölemez). Ama yardımcı işler (chunk build, LOD, GC, culling) **zaten çoklu çekirdek** — asıl mesele ayarları açmak.

### Yapılacak 3 ayar (5900X için)
1. **Sodium → Advanced → Chunk Update Threads: 8** → chunk yükleme/stutter azalır (en etkili)
2. **Distant Horizons → CPU Usage: Aggressive** → LOD üretimi 12 çekirdeği kullanır
3. **JVM:** `-XX:ParallelGCThreads=8 -XX:ConcGCThreads=2` (8'den fazla heap küçükken zararlı)

### Dikkat
- 24 thread'e boğma → GC+render+build+OS thrash eder, FPS düşer. Render 1 + build 8 + GC 8 ≈ yeterli.
- `-Xmx` 8G yeter; 16G yapma (GC yavaşlar).

### Ne çoklu çekirdek kullanır (pakette)
| İş | Çoklu? |
|---|---|
| Ana render loop | ❌ 1 çekirdek |
| Sodium chunk build | ✅ ayarlanır |
| Distant Horizons LOD | ✅ Aggressive |
| EntityCulling/MoreCulling | ⚠️ kısmen |
| G1GC | ✅ |
| Sunucu C2ME | ✅ 6 çekirdek |

## 📦 MANİFESTE EKLENDİ (doğrulandı)

- `distanthorizons` → client (DH) — beta ama kullanılabilir
- `bobby` → client, fabric (Connector ile)
- `scalablelux` → deneysel (alpha; --include-experimental ile iner)

## 🧪 Test sırası
1. DH'yi client'a kur, vanilla RD 12, DH 256 → FPS ölç (F3)
2. Beğenmezsen Bobby'yi dene (shader ile tam doku)
3. Sunucuya ScalableLux ekle (kopya dünyada) → stutter azaldı mı bak
4. Her değişiklik sonrası `/spark tps` (server) + F3 FPS (client)
