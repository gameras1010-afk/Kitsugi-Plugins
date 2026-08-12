# C2ME Tabanlı Paket — Moonrise ÇÖPE
### i5-9400F / 16GB / NVMe / Ubuntu 24.04 · MC 1.21.1 NeoForge

Moonrise siliniyor. C2ME kalıyor. Moonrise'ın yaptığı **her işi** başka
modlara dağıtıyoruz.

---

## 1. Moonrise ne yapıyordu, yerine ne geliyor?

Moonrise = Paper'dan portlanmış 5 ayrı yamanın paketi. Tek tek yerine koyuyoruz:

| Moonrise'ın işi | C2ME yapıyor mu? | YERİNE KURULACAK |
|---|---|---|
| **Chunk system rewrite** | ✅ **EVET** — C2ME'nin asıl işi, hem de paralel | — (C2ME zaten daha iyi) |
| **Starlight (ışık motoru)** | ❌ HAYIR | 🔴 **ScalableLux** — ZORUNLU |
| **Collision optimizasyonu** | ❌ HAYIR | 🟢 **Lithium** (`mixin.entity.collisions`) |
| **Entity tracker rewrite** | ❌ HAYIR | 🟢 **Lithium** + **ServerCore** |
| **Random ticking opt.** | ❌ HAYIR | 🟢 **Lithium** (`mixin.world.tick_scheduler`) |
| **Block/Entity retrieval (pathfinding/AI)** | ❌ HAYIR | 🟢 **Lithium** (`ai.pathing`, `block`) |
| **Packet handling while waiting for tick** | ❌ HAYIR | 🟢 **Chunk Sending** (+Cupboard) |
| **Lower worker thread count (low core)** | ⚙️ ELLE | `globalExecutorParallelism = 5` |
| **Reduce TPS catchup** | ❌ HAYIR | 🔴 **Karşılığı yok.** Kozmetik, kabul et. |
| **`fix-MC-224294` (lav çift tick)** | ❌ HAYIR | 🟡 Kayıp. Küçük, kabul et. |
| **Server list ping UI** | — | Client-only, sunucuda alakasız |
| **Chunk send/load rate limit** | ✅ EVET | C2ME `noTickViewDistance` |
| **Async chunk save** | ✅ EVET | C2ME `ioSystem.async` + `autoSave = ENHANCED` |

> Bu tablonun **eksiksizlik denetimi** ayrı bir dosyada: `BOSLUK-ANALIZI.md`.
> Orada Moonrise'ın resmî README'sindeki 11 maddenin her biri tek tek
> karşılanıyor, elenen 6 aday mod sebebiyle birlikte yazılı.

**Kritik nokta:** Moonrise'ı silince Lithium'un **kapalı olan kısımları
otomatik açılır.** Moonrise "çakışan Lithium mixin'lerini kapatıyordu" —
o baskı kalkınca Lithium tam kapasite çalışır. Collision, entity tracker,
random ticking büyük ölçüde geri gelir.

### 🔴 ScalableLux ZORUNLU — atlamak yok

C2ME'nin **kendi geliştiricisi** (ishland) yazmış. Aynı kişi Lithium ve
C2ME'yi de yazdı. C2ME dokümantasyonundan:

> *"It is **strongly recommended** to install ScalableLux, because lighting
> can easily become a bottleneck"*

ScalableLux 0.2.0 changelog'undan:
> *"Reduced scheduling overhead with proper chunk system integration with C2ME"*

Yani ScalableLux C2ME'ye **özel olarak entegre edilmiş**. Kurmazsan ışık
hesabı yeni darboğazın olur ve C2ME'nin hızını göremezsin.

`ScalableLux 0.2.0+neoforge` · `curseforge.com/minecraft/mc-mods/scalablelux`

---

## 2. Tam Mod Listesi

### Çekirdek — hepsi zorunlu

| Mod | Neden |
|---|---|
| **C2ME** `0.3.0+alpha.0.91+1.21.1` neoforge | Paralel chunk gen/IO/loading |
| 🔴 **ScalableLux** `0.2.0+neoforge` | Işık motoru. C2ME devinin kendi modu. |
| **Lithium** | Moonrise gidince TAM kapasite çalışır |
| **FerriteCore** | RAM ~%40 |
| **ModernFix** | Bellek + başlangıç |
| **AllTheLeaks** `1.1.11+1.21.1-neoforge` | Bellek sızıntıları |
| **spark** | Ölçüm |

### Worldgen ek hızlandırma

| Mod | Not |
|---|---|
| **Fast Noise** (`zfastnoise`) | ⚠️ **Moonrise ile uyumsuzdu — C2ME ile UYUMLU.** Moonrise'ı sildiğin için artık kurabilirsin. C2ME devi bunu bizzat tavsiye ediyor. Kendi benchmark'ı C2ME **üstüne** ekstra kazanç gösteriyor (aşağıda) |
| **Structure Layout Optimizer** `1.0.11` + **Resourceful Config** | Yapı üretimi. ishland'in tavsiye listesinde var. |

**Fast Noise'un C2ME üstüne kazancı** (kendi JMH benchmark'ı, C2ME kurulu):

| Test | Sadece C2ME | C2ME + Fast Noise | Kazanç |
|---|---|---|---|
| Overworld noise | 11552 ms | 8441 ms | **1.37x** |
| Nether noise | 1920 ms | 1039 ms | **1.85x** |
| End biome | 26.0 ms | 11.8 ms | **2.21x** |

> ⚠️ **1.21.1 NeoForge notu:** Fast Noise'un native NeoForge sürümü
> "26.1 sonrası planlanıyor" diyor; 1.21.x için **Sinytra Connector**
> gerekebilir. Connector kurmak istemiyorsan bu modu atla — C2ME zaten
> ana kazancı veriyor.

### Tick / TPS — Moonrise'ın boşluğunu dolduranlar

| Mod | Neden önemli |
|---|---|
| **ServerCore** | 🟢 C2ME'nin resmî sayfası ServerCore'u **isim vererek** uyumlu stack'te sayıyor. Entity limitleri, mob AI throttle, async login. 🔴 **ZORUNLU ŞART:** `config/servercore.toml` içinde `[dynamic] enabled = false` yap — dinamik view/simulation distance C2ME'nin `noTickViewDistance`'ı ile aynı işi yapıp ayarını ezer. Kanıt ve log örnekleri: **`UYUMLULUK-KANITI.md`** |
| **Alternate Current** | Redstone %95 |
| **Clumps** | XP orb birleştirme |
| **Get It Together, Drops!** | Item birleştirme |
| **FastFurnace / FastWorkbench / FastSuite** | Recipe cache |
| **Ksyxis** | Spawn chunk yükleme yok → hızlı açılış |
| **AI Improvements** | Pathfinding |
| **Async Locator** | `/locate` async |
| **Chunky** | Pregen |

---

## 3. ❌ SİL / KURMA

```
❌ SİL:   Moonrise                  → C2ME ile temelden uyumsuz
❌ SİL:   Moonrise Compats          → Moonrise gidince anlamsız
❌ SİL:   Generator Accelerator     → C2ME ile çakışır (Moonrise için yapıldı)
❌ KURMA: Starlight                 → ScalableLux zaten o
❌ KURMA: Lucis                     → ScalableLux ile "tanımı gereği uyumsuz"
❌ KURMA: Canary / Radium           → Lithium fork'u
❌ KURMA: Noisium / NoisiumForked   → Fast Noise zaten yerine geçti
❌ KURMA: Smooth Chunk Save         → C2ME ile kısmen uyumsuz
❌ KURMA: Dimensional Threading     → C2ME midTickChunkTasks ile uyumsuz
❌ KURMA: c2me-ocl                  → RX 550 için anlamsız (aşağıda)
```

### c2me-ocl neden senin GPU'nda çalışmaz

C2ME OpenCL modülünün **kendi** minimum donanım tablosu:

| Hedef | Gereken GPU |
|---|---|
| 1200+ chunk/sn | GTX 1060 **veya üstü** / **RX 6500 XT veya üstü** |
| 2500+ chunk/sn | RX 7600 XT / Arc B570 |

Senin **RX 550 (Lexa PRO)** bu eşiğin çok altında. Ayrıca dokümanda:
> *"CL_QUEUE_OUT_OF_ORDER_EXEC_MODE_ENABLE for optimal performance.
> **Not present on AMD GPUs**"*

Üstüne Linux'ta AMD için `rocm-opencl-runtime` kurman gerekir ve Lexa PRO
ROCm'de resmi desteklenmiyor. **Bu kapıyı kapat.**

---

## 4. `config/c2me.toml` — SENİN CPU'na göre

Sunucuyu bir kez aç-kapa, `config/c2me.toml` oluşsun. Sonra şunları değiştir:

```toml
version = 3

# ############################################################
# ##  EN ÖNEMLİ AYAR — i5-9400F için 5                      ##
# ############################################################
#
# C2ME devinin tavsiyesi:
#   "change globalExecutorParallelism to your thread count or
#    slightly below. Note: if you need fps and tps stability,
#    you need to reserve a few threads for the rest of the system."
#
# Senin CPU'n: 6 çekirdek / 6 THREAD (SMT YOK)
#
#   6 yazarsan  -> ana tick thread aç kalır, TPS düşer
#   5 yazarsan  -> 1 thread sisteme kalır  ← DOĞRU
#   4 yazarsan  -> daha güvenli, biraz yavaş
#
# 5 ile başla. TPS düşerse 4'e in.
globalExecutorParallelism = 5

[threadedWorldGen]
# ############################################################
# ##  BU VARSAYILAN OLARAK KAPALI. AÇMAZSAN C2ME'nin ASIL   ##
# ##  ÖZELLİĞİNİ KULLANMIYORSUN.                            ##
# ############################################################
enabled = true

# Ağaç/cevher gibi süslemeler paralel üretilsin
allowThreadedFeatures = true

# Kilit yarıçapını küçült — daha çok paralellik
reduceLockRadius = true

# Async + paralel zamanlama, ana thread yükünü azaltır
asyncScheduling = true

[vanillaWorldGenOptimizations]
optimizeAquifer = true      # Overworld hızlanır
useEndBiomeCache = true     # End hızlanır

[ioSystem]
# NVMe'n var, async IO şart
async = true
replaceImpl = true          # optimize IO implementasyonu

# NBT cache. 8G heap için makul değerler.
chunkDataCacheSoftLimit = 4096
chunkDataCacheLimit = 16384

[generalOptimizations]
# Tick döngüsü sırasında chunk görevleri çalıştırır.
# Chunk yüklemeyi hızlandırır, MSPT'yi biraz yükseltebilir.
# Varsayılan 100000 ns. Bırak.
midTickChunkTasksInterval = "default"

optimizeAsyncChunkRequest = true

[generalOptimizations.autoSave]
# ENHANCED = sunucu boş vakti olunca kaydet (VANILLA = her tick)
# Kesinlikle ENHANCED.
mode = "ENHANCED"

[noTickViewDistance]
enabled = true
compatibilityMode = true    # mod uyumluluğu, açık bırak

# Düşük = daha iyi latency, yüksek = daha hızlı yükleme
# 6 thread için 3 doğru.
maxConcurrentChunkLoads = 3

ensureChunkCorrectness = false   # true = chunk'ları 2 kez gönderir, ağ yükü

[fixes]
# Off-thread world random erişimini yakalar. AÇIK BIRAK —
# kapatırsan gizli bug'lar sessizce dünyayı bozar.
```

> ⚠️ Anahtar isimleri C2ME sürümüne göre biraz değişebilir. Kendi
> dosyanda karşılığını bul. `"default"` yazan yerleri sadece
> yukarıda belirttiklerimde değiştir.

---

## 5. `start.sh` değişikliği

Mevcut `start.sh` çoğunlukla doğru. **Tek değişiklik:**

```bash
# ŞUNU EKLE — C2ME devinin tavsiyesi:
-XX:+UseCompactObjectHeaders

# Chunky pregen yaparken şunu da ekle:
-Dchunky.maxWorkingCount=768
```

`-XX:+UseCompactObjectHeaders` Java 21'de `-XX:+UnlockExperimentalVMOptions`
ile birlikte çalışır (script'te zaten var). Nesne başlıklarını küçültür,
C2ME'nin çok sayıda chunk objesi tuttuğu senaryoda RAM ve cache kazancı.

**GC değişmiyor:** ishland'in tavsiyesi *"Use -XX:+UseZGC if you are
allocating more than 16GB, otherwise use -XX:+UseG1GC -XX:G1HeapRegionSize=16M"*.
Sen 8G'desin → **G1GC doğru**. (Region size 8G heap için 8M kalsın.)

**Heap yine 8G.** C2ME "give it RAM" diyor ama senin 16 GB'ın var ve
page cache'e yer lazım. 10G'ye çıkmayı sadece log'da GC uyarısı görürsen dene.

---

## 6. `server.properties`

```properties
view-distance=10
simulation-distance=6
sync-chunk-writes=false
max-tick-time=60000
```

C2ME'nin `noTickViewDistance` özelliği sayesinde `view-distance`'ı yüksek
tutmak ucuz — chunk'lar gönderilir ama tick'lenmez. `simulation-distance`
maliyeti kübik, 6'da tut.

---

## 7. Kurulum Sırası

```
1. [ ] YEDEK AL (dünya + mods klasörü)

2. [ ] mods/ klasöründen SİL:
       - Moonrise*.jar
       - MoonriseCompats*.jar
       - generator-accelerator*.jar

3. [ ] config/ klasöründen SİL (kalıntı bırakma):
       - moonrise.yml
       - generatoraccelerator.toml (veya benzeri)

4. [ ] EKLE:
       - c2me-neoforge-mc1.21.1-0.3.0+alpha.0.91.jar
       - ScalableLux 0.2.0+neoforge          ← ATLAMA
       - ServerCore
       - Structure Layout Optimizer + Resourceful Config

5. [ ] Sunucuyu aç → kapat  (config/c2me.toml oluşsun)

6. [ ] c2me.toml düzenle:
       globalExecutorParallelism = 5
       [threadedWorldGen] enabled = true      ← EN ÖNEMLİSİ
       allowThreadedFeatures = true
       asyncScheduling = true

7. [ ] start.sh'a -XX:+UseCompactObjectHeaders ekle

8. [ ] cpupower governor = performance   (yaptıysan geç)

9. [ ] Aç, /spark tps → ÖLÇ
10.[ ] 15 dk yeni araziye uç → chunk hızını hisset
```

---

## 8. Beklenti — dürüst olalım

C2ME'nin gücü **thread sayısıyla** ölçeklenir. Sen 6 thread'desin, C2ME'nin
benchmark'ları 16-80 thread'de yapılıyor. **RX 550 + 6 thread bir sunucu
canavarı değil.**

`globalExecutorParallelism = 5` ile Moonrise'ın varsayılan 1 thread'ine göre
**5x** worker alıyorsun. Fark net hissedilecek.

**Ama beklentini ayarla:** 6 thread'lik bir CPU'da hiçbir mod sana 16
thread'lik sunucu hissi veremez. Fizik kanunu.

### Bu yüzden PREGEN şart

```bash
# server.properties geçici:
#   max-tick-time=-1
#   view-distance=4
#   simulation-distance=4
#   spawn-monsters=false
#   spawn-animals=false
# start.sh'a ekle: -Dchunky.maxWorkingCount=768
# c2me.toml geçici: globalExecutorParallelism = 6
```

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 3000
/chunky start
```

Oyuncu yokken çalıştır. Bittiğinde chunk üretimi **tamamen ortadan kalkar** —
worldgen hızı tartışması biter. Kalan tek iş diskten okumak, o da NVMe'de
mikrosaniye.

**Bu, hangi modu kullandığından bağımsız olarak en büyük kazanç.**

---

## 9. Ölçüm

```
/spark profiler start --thread * --not-combined
# 60 sn HİÇ gitmediğin yöne uç
/spark profiler stop
/spark tps
```

Bakacağın yerler:
- `ChunkGenerator` / `NoiseBasedChunkGenerator` → worldgen
- `LightEngine` üstteyse → ScalableLux kurmayı unutmuşsun
- `RegionFileStorage` üstteyse → disk, C2ME çözmez

**Sonucu bana at**, ince ayar yaparız.
