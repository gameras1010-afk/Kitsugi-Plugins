# C2ME Tabanlı Sunucu Optimizasyon Paketi
### Minecraft 1.21.1 · NeoForge · Dedicated Server
### Donanım: i5-9400F (6c/6t) · 16 GB · NVMe · Ubuntu 24.04

Bu paket **C2ME'yi merkeze alır**. Moonrise kullanılmaz.

> **Sürüm geçmişi notu:** Bu paket önce Moonrise tabanlı yazılmıştı.
> Moonrise'ın tek-thread chunk sistemi bu donanımda yetersiz kaldığı
> için tamamen C2ME'ye geçildi. Moonrise'ın üstlendiği işler ayrı
> modlara dağıtıldı — tablo aşağıda.

---

## 0. Önce Bunu Oku

**Hepsini birden kurma.** Katman katman kur, her katmandan sonra sunucuyu aç,
10 dakika oyna, `/spark tps` ile ölç. Bir şey bozulursa hangi katman olduğunu bilirsin.

**Dünya yedeği al.** Moonrise → C2ME geçişi chunk sistemini değiştiriyor.

---

## 1. Moonrise'ın işleri nereye gitti?

| Moonrise'ın yaptığı | Yeni sahibi |
|---|---|
| Chunk system rewrite | ✅ **C2ME** — hem de paralel, Moonrise tek-thread'di |
| Starlight (ışık motoru) | 🔴 **ScalableLux** — zorunlu, atlanamaz |
| Collision optimizasyonu | 🟢 **Lithium** (`mixin.entity.collisions`) |
| Entity tracker rewrite | 🟢 **Lithium** + **ServerCore** |
| Random ticking | 🟢 **Lithium** (`mixin.world.tick_scheduler`) |
| Async chunk save | ✅ **C2ME** (`ioSystem.async` + `autoSave=ENHANCED`) |
| Chunk send rate limit | ✅ **C2ME** (`noTickViewDistance`) |
| `fix-MC-224294` (lav çift tick) | 🟡 Kayıp. Önemsiz, kabul et. |

**Bonus:** Moonrise kuruluyken Lithium'un collision / entity tracker /
random tick mixin'leri **zorla kapalıydı** (Moonrise aynı yerlere kendi
kodunu koyuyordu). Moonrise gidince bu baskı kalktı — **Lithium artık
tam kapasite çalışıyor.** Yani o işleri gerçekten kaybetmedin.

---

## 2. KATMAN 1 — Çekirdek

| Mod | Ne yapar | Not |
|---|---|---|
| **C2ME** | Paralel chunk gen / IO / loading | Ana motor. Config şart. |
| 🔴 **ScalableLux** | Işık motoru | C2ME devinin (ishland) kendi modu |
| **Lithium** | Oyun mantığı hot path'leri | C2ME ile resmen uyumlu |
| **FerriteCore** | RAM deduplikasyonu (~%40) | |
| **ModernFix** | Başlangıç + bellek | `mixin.perf.worldgen_allocation=true` |
| **AllTheLeaks** | Bellek sızıntısı yamaları | 1.21.1 NeoForge ✅ |
| **spark** | Profiler | Ölçmeden optimize etme |

C2ME dokümantasyonu birebir:
> *"For best performance, use C2ME with **Lithium** and **ScalableLux**."*
> *"It is **strongly recommended** to install ScalableLux, because lighting
> can easily become a bottleneck"*

Üçünü de aynı geliştirici (**ishland**) yazdı. Birlikte çalışmak için tasarlandılar.

---

## 3. KATMAN 2 — Tick / TPS

| Mod | Ne yapar | Not |
|---|---|---|
| **ServerCore** | Entity limitleri, mob AI throttling, async login | 🟢 Moonrise gidince artık kurabilirsin |
| **Alternate Current** | Redstone dust yayılımı | Lag'de ~%95 |
| **Clumps** | XP orb birleştirme | Mob farm |
| **Get It Together, Drops!** | Item birleştirme | Aynı mantık |
| **FastFurnace / FastWorkbench / FastSuite** | Recipe cache | Auto-smelter |
| **Ksyxis** | Spawn chunk yüklemeyi bırakır | Hızlı açılış |
| **AI Improvements** | Pathfinding | Mob yoğunsa |
| **Async Locator** | `/locate` async | Donma yok |

---

## 4. KATMAN 3 — Worldgen ekstra

| Mod | Not |
|---|---|
| **Structure Layout Optimizer** `1.0.11` | + **Resourceful Config** bağımlılığı. ishland'in listesinde. |
| **Fast Noise** (`zfastnoise`) | ⚠️ **Moonrise ile uyumsuzdu, C2ME ile uyumlu.** Ama 1.21.1'de Sinytra Connector gerekiyor. Connector yoksa atla. |

Fast Noise'un C2ME **üstüne** kazancı: overworld noise 1.37x, nether 1.85x,
end biome 2.21x. Vanilla parity korunur. Detay `MOD-LISTESI.md`'de.

---

## 5. KATMAN 4 — Pregen (En Büyük Tek Kazanç)

Hiçbir mod, "chunk zaten üretilmiş" olmanın yerini tutmaz. C2ME chunk
üretimini birkaç kat hızlandırır; **pregen onu sıfırlar.**

Pregen öncesi geçici ayarlar:
```properties
# server.properties
max-tick-time=-1
view-distance=4
simulation-distance=4
spawn-monsters=false
spawn-animals=false
```
```toml
# c2me.toml — oyuncu yok, TPS önemsiz
globalExecutorParallelism = 6
```

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 3000
/chunky start

/chunky world minecraft:the_nether
/chunky radius 1000
/chunky start
```

**Nether radius'unu küçük tut** — Nether'da 1 blok = Overworld'de 8 blok.

Bitince ayarları geri al, `globalExecutorParallelism = 5` yap.

---

## 6. ❌ KURMA

| Mod | Neden |
|---|---|
| **Moonrise** | C2ME ile temelden uyumsuz — ikisi de chunk sistemini yeniden yazıyor |
| **Moonrise Compats** | Moonrise gidince anlamsız |
| **Generator Accelerator** | Moonrise için yapıldı, C2ME ile çakışır |
| **Starlight** | ScalableLux zaten onun 1.21+ devamı |
| **Lucis** | ScalableLux ile "tanımı gereği uyumsuz" — birini seç |
| **Canary / Radium** | Lithium fork'u |
| **Noisium / NoisiumForked** | Fast Noise yerine geçti |
| **Smooth Chunk Save** | C2ME `ioSystem` ile çakışır |
| **Dimensional Threading** | C2ME `midTickChunkTasksInterval` ile uyumsuz |
| **c2me-ocl** | RX 550 minimum eşiğin çok altında (detay `C2ME-PAKET.md` §3) |
| **VMP** | Fabric-only |
| **Krypton** | Fabric-only |
| **Gnetum** | Client-side HUD modu |

---

## 7. Config Dosyaları

| Dosya | Nereye |
|---|---|
| `config/c2me.toml` | `<sunucu>/config/c2me.toml` ⚠️ **Kopyalama** — sunucuyu bir kez aç, oluşan dosyada değerleri değiştir |
| `config/lithium.properties` | `<sunucu>/config/lithium.properties` (opsiyonel, sorun giderme referansı) |
| `config/server.properties.ornek` | `<sunucu>/server.properties` (birleştir, üzerine yazma) |
| `start.sh` | `<sunucu>/start.sh` (Linux) |
| `start.bat` | `<sunucu>\start.bat` (Windows) |

---

## 8. Uygulama Sırası

```
1.  Dünya yedeği al                                    ← atlamak yok
2.  mods/ içinden Moonrise*, MoonriseCompats*,
    generator-accelerator* SİL
3.  config/moonrise.yml SİL
4.  Katman 1 kur (C2ME + ScalableLux dahil)
5.  Sunucuyu aç → kapat  (config/c2me.toml oluşsun)
6.  c2me.toml'da şunları değiştir:
       globalExecutorParallelism = 5
       [threadedWorldGen] enabled = true       ← EN KRİTİK
       allowThreadedFeatures = false           ← AÇMA (chunk bozar)
       reduceLockRadius      = false           ← AÇMA (chunk bozar)
       asyncScheduling = true
       [ioSystem] replaceImpl = true
       [generalOptimizations.autoSave] mode = "ENHANCED"
7.  Aç → 10 dk oyna → /spark tps
8.  Katman 2 kur → aç → 10 dk oyna → /spark tps
9.  Chunky pregen (oyuncular yokken)
10. Katman 3 (opsiyonel, Sinytra Connector varsa)
```

---

## 9. Ölçüm

```
/spark profiler start --thread * --not-combined
# 60 sn HİÇ gitmediğin yöne uç (chunk üretimini zorla)
/spark profiler stop
/spark tps
/spark health
```

| Profilde üstte görünen | Anlamı |
|---|---|
| `ChunkGenerator` / `NoiseBasedChunkGenerator` | Worldgen. `threadedWorldGen` açık mı? |
| `LightEngine` / `ThreadedLevelLightEngine` | **ScalableLux kurmayı unutmuşsun** |
| `RegionFileStorage` | Disk. `ioSystem.replaceImpl` açık mı? |
| `ServerChunkCache.tick` | `globalExecutorParallelism` düşük olabilir |

---

## 10. Dosyalar

| Dosya | İçerik |
|---|---|
| **`C2ME-PAKET.md`** | 🔴 **Ana doküman.** Moonrise görev devri, parallelism kararı, kurulum sırası, beklenti |
| `MOD-LISTESI.md` | İndirme linkleri + sürüm notları |
| **`BOSLUK-ANALIZI.md`** | 🆕 "Başka mod kalmadı mı?" — Moonrise'ın 11 resmî özelliğinin tek tek karşılığı, elenen 6 aday ve sebepleri |
| **`UYUMLULUK-KANITI.md`** | 🆕 **Her modun C2ME uyumluluğu, gerçek log kanıtlarıyla.** ServerCore `dynamic=false` şartı, Architectury tuzağı, uyumsuz mod listesi |
| **`OYUN-ONCESI-SON-KONTROL.md`** | 🆕 **Kurulum bittikten sonra oku.** ServerCore dynamic uyarısı, Annuus client şartı, MSPT yanılgısı, oyun içi test listesi, belirti→çözüm tablosu |
| **`BOZUK-CHUNK-COZUMU.md`** | 🔴 **Yarım açılan kapı, kesik chunk görüyorsan BURAYA BAK.** Sebep: `reduceLockRadius`+`allowThreadedFeatures` |
| **`CHUNK-DUVARI-GERCEK-COZUM.md`** | 🆕 🔴 **Chunk duvarı / bir bölge komşusundan yüksekte kalmışsa BURAYA BAK.** Gerçek çözüm: MCA Selector **ForceBlend** ile Minecraft'ın kendi harmanlama motorunu tetiklemek. Pregen'in neden çözüm olmadığı + `blending_data` crash tuzağı |
| **`DUNYA-AKTARIM.md`** | 🆕 🟢 **1.20.1 Forge dünyasını 1.21.1 NeoForge'a taşıma.** Kısa cevap: dünyayı taşıma, **yerinde yükselt** — DataFixerUpper chunk'ları kendi dönüştürür, mod blokları mod yüklü kaldığı sürece korunur. "Aynı seed + yeni dünya + schematic" planının neden üç ayrı yerden kırıldığı + mod eşleştirme kontrol listesi |
| **`SES-CHAT-TESHIS.md`** | 🆕 🔴 **Simple Voice Chat kopuyorsa BURAYA BAK.** `login_timeout` neden etkisiz, `keep_alive`'ı yükseltmenin neden timeout YAPTIĞI, ve asıl şüpheli: **Tailscale MTU 1280 vs `mtu_size`** çakışması. Log okuma tablosu + doğru config referansı |
| **`UZAKTAN-YONETIM.md`** | 🆕 🟢 **Arkadaşların PC'yi uzaktan açsın, sunucuyu başlatsın.** Neden **Tailscale WoL paketi gönderemez** (L3 vs L2) ve zorunlu sonucu: akıllı priz veya sürekli açık aracı cihaz. MSI B365M BIOS yolları (`ErP Ready`, `AC Power Loss = Power On` — **`Last State` değil**), Ubuntu GRUB `recordfail` tuzağı, Crafty Controller 4 paneli, Tailscale **180 günlük key expiry** bombası + ACL daraltma |
| **`GOREV-LISTESI.md`** | 🆕 🟢 **`UZAKTAN-YONETIM.md`'nin uygulama dosyası.** 12 aşama, kopyala-yapıştır komutlarla işaretlemeli kontrol listesi. Aşama 3 (güç testi) ve Aşama 10 (uçtan uca test) geçilmeden ilerlenmez |
| **`MOD-ONERILERI.md`** | 🆕 🟢 **"237 modum var, ne eksik?"** Kategori taraması: içerik/performans/QoL doymuş, **çok oyunculu altyapı komple boş**. 6 mod önerisi (FTB Backups 3, CoreProtectNeo, FTB Essentials/Chunks/Ranks, BlueMap) + kurulum sırası. Ayrıca mevcut listendeki 6 risk: yanlış sürümlü 2 jar (`1.21.3`, `mc1.14`), C2ME+BetterEnd issue #50, Sinytra Connector sunucu crash'i, FTB Chunks force-load tuzağı |
| **`EKSIK-GEDIK.md`** | 🆕 🔴 **Performans dışı katman.** Backup (YOK'tu!), rollback, izin, world border + BlueMap / voice chat / Distant Horizons fikirleri ve tuzakları |
| `DONANIMIMA-OZEL.md` | Donanımına özel karar gerekçeleri (heap, GC, Ubuntu ayarları) |
| `NEDEN-YAVAS.md` | Chunk yüklemenin neden yavaş olduğunun teknik açıklaması |
| `config/c2me.toml` | Satır satır yorumlu C2ME config |
| `start.sh` / `start.bat` | JVM flag'leri + sanity check |
