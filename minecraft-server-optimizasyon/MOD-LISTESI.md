# Mod Listesi — İndirme Linkleri
### Minecraft 1.21.1 · NeoForge · Server-side · **C2ME tabanlı**

> Sürüm numaraları hızlı değişiyor. Linke git, **1.21.1 + NeoForge** filtresini
> uygula, en son **Release** dosyasını indir. Aşağıdaki dosya adları
> araştırma anındaki son sürümlerdir, referans amaçlıdır.

---

## ❌ ÖNCE SİL

| Mod | Neden |
|---|---|
| **Moonrise** | C2ME ile temelden uyumsuz — ikisi de chunk sistemini baştan yazıyor |
| **Moonrise Compats** | Moonrise gidince anlamsız |
| **Generator Accelerator** | Moonrise için yapılmıştı, C2ME ile çakışır |
| `config/moonrise.yml` | Kalıntı bırakma |

---

## KATMAN 1 — Çekirdek (hepsi zorunlu)

| Mod | Link | Notlar |
|---|---|---|
| **C2ME** | `modrinth.com/mod/c2me-fabric` (neoforge dosyası var) · `github.com/RelativityMC/C2ME-fabric` | Ana motor. `c2me-neoforge-mc1.21.1-0.3.0+alpha.0.91.jar` |
| 🔴 **ScalableLux** | `curseforge.com/minecraft/mc-mods/scalablelux` · `modrinth.com/mod/scalablelux` | **ZORUNLU.** Işık motoru. `0.2.0+neoforge` |
| **Lithium** | `modrinth.com/mod/lithium` | Moonrise gidince TAM kapasite ✅ |
| **FerriteCore** | `modrinth.com/mod/ferrite-core` | RAM ~%40 |
| **ModernFix** | `modrinth.com/mod/modernfix` | Config notu aşağıda |
| **AllTheLeaks** | `curseforge.com/minecraft/mc-mods/alltheleaks` | `alltheleaks-1.1.11+1.21.1-neoforge.jar` |
| **spark** | `modrinth.com/mod/spark` | Profiler. Kurmadan optimize etme. |

### 🔴 ScalableLux neden atlanamaz

C2ME'nin **kendi geliştiricisi** (ishland) yazdı. C2ME dokümantasyonu birebir:

> *"It is strongly recommended to install ScalableLux, because lighting can
> easily become a bottleneck"*

ScalableLux changelog'u:
> *"Reduced scheduling overhead with proper chunk system integration with C2ME"*

Yani C2ME'ye **özel entegre edilmiş**. Kurmazsan Moonrise'ın Starlight'ını
kaybettiğin için ışık hesabı yeni darboğazın olur ve C2ME'nin hızını göremezsin.

**Not:** Bu, Moonrise'ın en büyük kaybıydı ve tam karşılığı var. Rahat ol.

### ModernFix config (`config/modernfix-mixins.properties`)
```properties
mixin.perf.dynamic_resources=false
mixin.perf.worldgen_allocation=true
mixin.perf.faster_item_rendering=false
mixin.perf.compact_bit_storage=true
mixin.perf.reduce_blockstate_cache_rebuilds=true
```
> `dynamic_resources` ve `faster_item_rendering` client-side, server'da kapalı kalsın.

---

## KATMAN 2 — Worldgen ekstra

| Mod | Link | Notlar |
|---|---|---|
| **Structure Layout Optimizer** | `modrinth.com/mod/structure-layout-optimizer` | `1.0.11`. **Resourceful Config** bağımlılığı var. ishland'in tavsiye listesinde. |
| **Resourceful Config** | `modrinth.com/mod/resourceful-config` | Üstteki için gerekli |
| **Fast Noise** (`zfastnoise`) | `curseforge.com/minecraft/mc-mods/zfastnoise` | ⚠️ Detay aşağıda |

### Fast Noise — okumadan kurma

**İyi haber:** Bu mod **Moonrise ile açıkça uyumsuzdu**. Moonrise'ı sildiğin
için artık kurabilirsin. C2ME ile birlikte benchmark ediliyor — uyumlu.

**Ölçümler** (kendi JMH benchmark'ı, 1089 chunk, C2ME kurulu):

| Test | C2ME | C2ME + Fast Noise | Kazanç |
|---|---|---|---|
| Overworld noise | 11552 ms | 8441 ms | **1.37x** |
| Nether noise | 1920 ms | 1039 ms | **1.85x** |
| End biome | 26.0 ms | 11.8 ms | **2.21x** |

Vanilla parity korunur — dünya birebir aynı üretilir.

**Kötü haber:** 1.21.1'de native NeoForge sürümü yok. Mod sayfası "native
NeoForge desteği 26.1 sonrasına planlı" diyor, şu an **Sinytra Connector**
gerekiyor. Connector kendi başına bir risk kaynağı.

**Karar:** Sinytra Connector zaten kuruluysa ekle. Değilse **atla** —
tek bir mod için Connector kurmaya değmez, C2ME ana kazancı zaten veriyor.

---

## KATMAN 3 — Tick / TPS (Moonrise'ın boşluğunu dolduranlar)

| Mod | Link | Notlar |
|---|---|---|
| **ServerCore** | `modrinth.com/mod/servercore` | 🟢 **Moonrise gidince artık kurabilirsin.** Entity limitleri, mob AI throttling, async login. Moonrise'ın entity tracker işini kısmen üstlenir. |
| **Chunk Sending** | `curseforge.com/minecraft/mc-mods/chunk-sending-forge-fabric` | 🆕 `chunksending-1.21-3.7.jar` + **Cupboard** bağımlılığı. Chunk paketlerini zamana yayar → login/teleport donması biter. "No known incompatibilities". Moonrise'ın *packet handling* maddesinin karşılığı. ⚠️ Kurarsan c2me.toml'de `maxConcurrentChunkLoads`'u yükseltme. |
| **Alternate Current** | `modrinth.com/mod/alternate-current` | Redstone %95. Lithium `block_entity_ticking` ile çakışabilir. |
| **Clumps** | `curseforge.com/minecraft/mc-mods/clumps` | XP orb birleştirme |
| **Get It Together, Drops!** | `modrinth.com/mod/get-it-together-drops` | Item birleştirme |
| **FastFurnace** | `curseforge.com/minecraft/mc-mods/fastfurnace` | Recipe cache |
| **FastWorkbench** | `curseforge.com/minecraft/mc-mods/fastworkbench` | Recipe cache |
| **FastSuite** | `curseforge.com/minecraft/mc-mods/fastsuite` | Recipe cache |
| **AI Improvements** | `curseforge.com/minecraft/mc-mods/ai-improvements` | Pathfinding |
| **Async Locator** | `modrinth.com/mod/async-locator` | `/locate` async |
| **Ksyxis** | `modrinth.com/mod/ksyxis` | Spawn chunk yükleme yok → hızlı açılış |

---

## KATMAN 4 — Pregen

| Mod | Link | Notlar |
|---|---|---|
| **Chunky** | `modrinth.com/mod/chunky` | **En büyük tek kazanç.** `start.sh`'ta `-Dchunky.maxWorkingCount=768` var. |

---

## ❌ KURMA — ve nedenleri

| Mod | Neden olmaz |
|---|---|
| **Moonrise** | C2ME ile temelden uyumsuz |
| **Starlight** | ScalableLux zaten onun 1.21+ devamı |
| **Lucis** | ScalableLux ile **tanımı gereği uyumsuz** — ikisinden sadece biri. ScalableLux'ta kal (C2ME entegrasyonu var). |
| **Canary / Radium** | Lithium fork'u, ikisi birden olmaz |
| **Noisium / NoisiumForked** | Fast Noise yerine geçti |
| **Smooth Chunk Save** | C2ME `ioSystem` ile çakışır |
| **Dimensional Threading** (dimthread) | C2ME `midTickChunkTasksInterval` ile **açıkça uyumsuz** |
| **c2me-ocl** | RX 550 minimum eşiğin çok altında. Detay `C2ME-PAKET.md` §3'te. |
| **VMP (Very Many Players)** | **Fabric-only.** NeoForge 1.21.1'de yok. |
| **Gnetum** | Client-side HUD modu. Sunucuya faydası sıfır. |
| **Krypton** | Fabric-only |
| **Chunkumulator** | 🆕 Mod sayfası birebir: *"Known Incompatibilities: C2ME"* |
| **Sepals** | 🆕 C2ME ile **resmî uyumlu** ve entity/AI'da çok güçlü — ama sürümleri 1.21.7+ , **1.21.1 yok**. Sürüm yükseltirsen ★ birinci öneri. |
| **Async** (AxalotLDev) | 🆕 Entity'leri paralel tick'liyor (9000 villager: 4.4 → 20 TPS). C2ME ile uyumlu, Moonrise ile değil. **Ama MC 26.1+ ve Java 25+ istiyor** → 1.21.1'de kullanılamaz. |
| **Adaptive Performance Tweaks** | 🆕 TPS düşünce oyun özelliklerini kısıyor (vanilla parity yok). NeoForge 1.21.1 desteği belirsiz. |

---

## 🟡 OPSİYONEL — şartlı kur

| Mod | Link | Ne zaman |
|---|---|---|
| **Annuus** | `modrinth.com/mod/annuus` | 🆕 Ağ paketi sıkıştırma. Chunk data (VD 10): **13.94 MB → 1.17 MB**, 35.03 → 29.76 ms. NeoForge 1.21.x, bağımlılık yok. **Sadece 5+ oyuncu + düşük upload varsa.** Tek başına oynuyorsan gereksiz. ⚠️ Experimental, C2ME ile birlikte resmî test edilmemiş. |
| **ThreadTweak Reforged** | `curseforge.com/minecraft/mc-mods/threadtweak-reforged` | 🆕 `threadtweak-1.21.1-NeoForge-1.0.0.jar` (248.5K indirme). CPU scheduling / thread önceliği. **En son dene**, spark ile ölç, fark yoksa kaldır. |

---

## Kaynak

Bu listenin çekirdeği iki yerden doğrulandı:

1. **PTFE MC-Optimization-Guide** (`github.com/Polytetrafluoroethylene-PTFE/MC-Optimization-Guide`, `mods-n-stuff/1.21.1.md`) — NeoForge 1.21.1 server tarafı: AllTheLeaks, **C2ME**, FerriteCore, **Lithium**, ModernFix. **Bu listede Moonrise YOK.**
2. **ishland'in (C2ME geliştiricisi) resmî tavsiyesi** — ScalableLux, Lithium, FerriteCore, Structure Layout Optimizer, zFastNoise.
