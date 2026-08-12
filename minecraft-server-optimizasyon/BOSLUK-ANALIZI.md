# "Başka mod kalmadı mı?" — Tam Boşluk Analizi

Sen sordun, ben tekrar taradım. **Dürüst cevap: tam emin değildim.**
3 mod buldum ki listemde yoktu. 3 mod da eledim.

Aşağıda Moonrise'ın **resmî README'sindeki** özellik listesi madde madde,
her birinin karşılığı ve **doğrulama kaynağı** var.

---

## 1. Moonrise'ın RESMÎ özellik listesi

Kaynak: `github.com/Tuinity/Moonrise` README (`mc/1.21.1` branch), birebir:

> Moonrise ports several important Paper patches. Listed below are notable patches:
> - Chunk system rewrite
> - Collision optimisations
> - Entity tracker optimisations
> - Random ticking optimisations
> - Starlight

Ve "Optimised areas" bölümü:
> - Entity movement/collisions/physics/tracking
> - Chunk ticking/loading/generation/saving
> - Block/Entity retrieval (which systems like pathfinding and entity AI use frequently)

Ve "Responsiveness improvements":
> - Improve/fix the server list server ping UI (**client install only**)
> - Handle packets sent while the server is waiting for next tick (lowering perceived latency)
> - Lower worker thread count by default for low core systems
> - Reduce TPS catchup by default

**Bu, listenin tamamı.** Gizli bir özellik yok.

---

## 2. Madde madde karşılık tablosu

| # | Moonrise özelliği | Karşılığı | Durum |
|---|---|---|---|
| 1 | Chunk system rewrite | **C2ME** | ✅ Üstelik paralel, Moonrise tek-thread'di |
| 2 | Starlight | **ScalableLux** | ✅ Tam karşılık (aynı geliştirici) |
| 3 | Collision optimisations | **Lithium** `mixin.entity.collisions` | ✅ Moonrise gidince açıldı |
| 4 | Entity tracker optimisations | **Lithium** + **ServerCore** | 🟡 Kısmi (aşağıda) |
| 5 | Random ticking optimisations | **Lithium** `mixin.world.tick_scheduler` | ✅ Moonrise gidince açıldı |
| 6 | Block/Entity retrieval | **Lithium** (`ai.pathing`, `block`) | ✅ |
| 7 | Chunk ticking/loading/saving | **C2ME** `ioSystem` + `autoSave` | ✅ |
| 8 | Packet handling while waiting | **Chunk Sending** (yeni bulgu) | 🟢 Aşağıda |
| 9 | Lower worker thread count | C2ME `globalExecutorParallelism` | ✅ Elle ayarlıyorsun |
| 10 | Reduce TPS catchup | ❌ **Karşılığı yok** | 🔴 Tek gerçek kayıp |
| 11 | Server list ping UI | Client-only | ⬜ Sunucuda alakasız |

---

## 3. 🟢 YENİ BULGULAR — listeme eklenenler

### Chunk Sending (`chunksending`)

**Moonrise'ın 8. maddesini karşılıyor.** Chunk paketlerini sıralayıp zamana
yayıyor — login/teleport/boyut değiştirme sırasındaki donmaları bitiriyor.

- `curseforge.com/minecraft/mc-mods/chunk-sending-forge-fabric`
- **1.21.1 NeoForge:** `chunksending-1.21-3.7.jar` (Ağu 2026) veya `2.9`
- **Bağımlılık:** Cupboard
- **68 milyon indirme** — bu listedeki en çok kullanılan mod
- Mod sayfası: *"No known incompatibilities, should work fine with any mod."*

> ⚠️ **C2ME ile örtüşme uyarısı:** C2ME'nin `noTickViewDistance` bölümündeki
> `maxConcurrentChunkLoads` ve `updatesPerTick` ayarları benzer iş yapıyor.
> İkisini birden kurabilirsin ama **ikisini birden agresif ayarlama.**
> Chunk Sending kurarsan C2ME'de `maxConcurrentChunkLoads = 3` bırak, oynama.

**Karar:** Kur. Login/teleport donması yaşıyorsan büyük fark. Yaşamıyorsan atla.

### Annuus

Network paket encoder/decoder'ı sıfırdan yazıyor, chunk verisini sıkıştırıyor.
**Krypton Fabric-only olduğu için NeoForge'daki network boşluğunu bu dolduruyor.**

- `modrinth.com/mod/annuus` · `github.com/cao-awa/Annuus`
- **1.21.x NeoForge** ✅ (`Annuus-neoforge-1.0.17.jar`)
- NeoForge'da ek bağımlılık yok

Kendi benchmark'ı (view distance 10, 473 chunk):

| | Süre | Bant genişliği |
|---|---|---|
| Vanilla | 35.03 ms | 13.94 MB |
| Annuus (Deflate 9) | 29.76 ms | **1.17 MB** |

Bant genişliği **12x** düşüyor. Süre de biraz iyileşiyor.

> ⚠️ **Experimental** etiketli. Ve C2ME ile birlikte resmî olarak test edilmiş
> değil (ikisi de chunk paketlerine dokunuyor).

**Karar:** Sen tek/az kişi oynuyorsan **atla** — ağ senin darboğazın değil.
Ev sunucusunda upload'un düşükse ve 5+ kişi bağlanıyorsa dene.

### ThreadTweak Reforged

Minecraft'ın CPU scheduling'ini ayarlıyor — Smooth Boot'un modern devamı.
Thread önceliklerini yeniden dengeleyip başlangıçtaki %100 CPU tıkanmalarını
ve thread çekişmesinden kaynaklanan TPS spike'larını azaltıyor.

- `curseforge.com/minecraft/mc-mods/threadtweak-reforged`
- **1.21.1 NeoForge:** `threadtweak-1.21.1-NeoForge-1.0.0.jar` (19.7 KB)
- Bu tek dosya **248.5K indirilmiş** — 1.21.1'de en çok kullanılan sürümü
- MIT lisans, bağımlılık yok

**Neden senin durumunda mantıklı:** 6 thread'lik bir CPU'da C2ME 5 worker
açıyor, ana server thread'i + I/O thread'leri + GC thread'leri kalan yeri
paylaşıyor. Java varsayılan olarak hepsine aynı önceliği veriyor. Server
thread'ini öne almak burada işe yarayabilir.

> ⚠️ **Ölçmeden kalıcı yapma.** Thread önceliği ayarları çoğu zaman plasebo.
> spark ile öncesi/sonrası MSPT karşılaştır, fark yoksa kaldır.

**Karar:** 🟡 En son dene. C2ME zaten kendi havuzunu yönetiyor, o yüzden
`threadedWorldGen` + Chunky'yi yaptıktan **sonra** bak.

---

## 4. ❌ ARAŞTIRDIM, ELEDİM — ve nedenleri

### Sepals — C2ME uyumlu ama **1.21.1'de YOK**

Bu en çok umutlandığım moddu. Villager/mob AI'yı derinden yeniden yazıyor,
uyumluluk tablosunda **C2ME açıkça listeli**. Entity cramming: 53.6 ms → 10.2 ms.

**Ama:** CurseForge sürüm listesi `1.21.7, 1.21.8, 1.21.9, 1.21.10, 1.21.11`.
**1.21.1 yok.** Bir de Architectury API gerekiyor.

**Karar:** Sürüm yükseltirsen (1.21.8+) **kesinlikle kur.** Şimdilik kullanamazsın.

### Async — Moonrise ile uyumsuz, C2ME ile uyumlu, ama **Java 25 + MC 26.1 istiyor**

Entity'leri paralel işliyor. 9000 villager testi:

| | TPS | MSPT |
|---|---|---|
| Lithium (Async yok) | 4.4 | 225.4 |
| **Lithium + Async** | **20** | **41.8** |

Uyumsuzluk listesinde tek satır: *"❌ Moonrise - Known incompatibility"*.
C2ME yok, yani uyumlu.

**Ama gereksinimleri:** *"Minecraft: 26.1 or newer, Java: 25 or newer"*.
Sen 1.21.1 + Java 21'desin. **Kullanamazsın.**

**Karar:** Bu, Moonrise'ın entity tracker işini fazlasıyla yapardı. Sürüm
yükseltmeyi düşünürsen tek başına sebep olabilir. Şimdilik hayır.

### Chunkumulator — C2ME ile AÇIKÇA UYUMSUZ

Mod sayfası birebir: *"Known Incompatibilities: - C2ME"*.

**Karar:** Kurma. Tek satırlık karar.

### Radium Reforged — Lithium'un forku

NeoForge 1.21.1 desteği var ama Lithium'un kendisi zaten NeoForge 1.21.1'de
mevcut. İkisi birden olmaz.

**Karar:** Lithium'da kal.

### Adaptive Performance Tweaks

TPS düşünce özellikleri kısıyor. NeoForge 1.20.1'de kalmış, 1.21.1 desteği
belirsiz. Ayrıca "TPS düşünce oyunu bozar" mantığı — vanilla parity yok.

**Karar:** Atla.

---

## 5. 🔴 GERÇEKTEN KAYBETTİĞİN TEK ŞEY

### "Reduce TPS catchup"

Moonrise README'sinden:
> *"Reduce TPS catchup by default (stops the server from speeding up when it
> momentarily lags)"*

Vanilla sunucu bir tick geciktiğinde, sonraki tick'leri **hızlandırarak**
açığı kapatmaya çalışır. Bu, lag'den sonra oyunun bir an "ileri sarması"
hissini verir. Moonrise bunu kapatıyordu.

**Karşılığı olan bir mod bulamadım.** C2ME, Lithium, ServerCore — hiçbiri
bu davranışa dokunmuyor.

**Ne kadar önemli?** Az kişilik bir sunucuda **kozmetik.** Sadece lag
anlarından sonra hafif bir "sıçrama" hissedersin. TPS/MSPT sayılarını
etkilemez. Kabul edilebilir bir kayıp.

### `fix-MC-224294` (lav çift tick)

Küçük vanilla bug'ı. Karşılığı yok. Önemsiz.

---

## 6. 📋 GÜNCEL TAM LİSTE

### Zorunlu
```
C2ME · ScalableLux · Lithium · FerriteCore · ModernFix · AllTheLeaks · spark
```

### Moonrise görev devri için
```
ServerCore              → entity limitleri, mob AI throttle, async login
Chunk Sending (+Cupboard) → login/teleport chunk akışı        [YENİ]
```

### Tick/TPS
```
Alternate Current · Clumps · Get It Together Drops!
FastFurnace/Workbench/Suite · Ksyxis · AI Improvements · Async Locator
```

### Worldgen
```
Structure Layout Optimizer (+Resourceful Config)
Fast Noise (Sinytra Connector gerekiyorsa atla)
Chunky ← EN BÜYÜK KAZANÇ
```

### Opsiyonel / şartlı
```
Annuus         → sadece 5+ oyuncu + düşük upload varsa      [YENİ]
ThreadTweak    → en son dene, düşük öncelik                 [YENİ]
```

### Sürüm yükseltirsen (1.21.8+ / Java 25)
```
Sepals   → villager/mob AI, C2ME uyumlu, entity cramming 5x
Async    → entity paralel tick, 9000 villager'da 4.4→20 TPS
```

---

## 7. Sonuç — sorunun net cevabı

**Hayır, tam emin değildim.** İyi ki sordun:

- **3 mod ekledim:** Chunk Sending, Annuus, ThreadTweak
- **3 mod eledim** (sebepleriyle): Sepals (1.21.1 yok), Async (Java 25),
  Chunkumulator (C2ME uyumsuz)
- **1 gerçek kayıp tespit ettim:** TPS catchup — karşılığı yok, ama kozmetik

Moonrise'ın **11 özelliğinden 9'unun** tam karşılığı var, 1'i kısmi,
1'i kayıp (kozmetik).

**Ama şunu tekrar söyleyeyim:** Bu listedeki hiçbir mod, `threadedWorldGen =
true` + `globalExecutorParallelism = 5` + **Chunky pregen** üçlüsü kadar fark
yaratmayacak. Mod eklemeye devam etmek yerine önce o üçünü yap.
