# Mod Listesi — İndirme Linkleri
### Minecraft 1.21.1 · NeoForge · Server-side

> Sürüm numaraları hızlı değişiyor. Linke git, **1.21.1 + NeoForge** filtresini
> uygula, en son **Release** dosyasını indir. Aşağıdaki dosya adları
> araştırma anındaki son sürümlerdir, referans amaçlıdır.

---

## KATMAN 1 — Çekirdek

| Mod | Link | Notlar |
|---|---|---|
| **Moonrise** | `modrinth.com/mod/moonrise-opt` · `github.com/Tuinity/Moonrise` | Ana motor. Starlight gömülü. |
| **Lithium** | `modrinth.com/mod/lithium` | Moonrise çakışanları otomatik kapatır ✅ |
| **FerriteCore** | `modrinth.com/mod/ferrite-core` | Aynı ✅ |
| **ModernFix** | `modrinth.com/mod/modernfix` | Aşağıdaki config notuna bak |
| **AllTheLeaks** | `curseforge.com/minecraft/mc-mods/alltheleaks` | `alltheleaks-1.1.11+1.21.1-neoforge.jar` |
| **spark** | `modrinth.com/mod/spark` | Profiler. Kurmadan optimize etme. |

**ModernFix config** (`config/modernfix-mixins.properties`):
```properties
mixin.perf.dynamic_resources=false
mixin.perf.worldgen_allocation=true
mixin.perf.faster_item_rendering=false
mixin.perf.compact_bit_storage=true
mixin.perf.reduce_blockstate_cache_rebuilds=true
```
> `dynamic_resources` server'da kapalı kalsın (client-side özellik, sorun çıkarır).

---

## KATMAN 2 — Tick / TPS

| Mod | Link | Ne yapar |
|---|---|---|
| **Alternate Current** | `modrinth.com/mod/alternate-current` | Redstone yayılımı yeniden yazılmış |
| **Clumps** | `curseforge.com/minecraft/mc-mods/clumps` | XP orb birleştirme |
| **Get It Together, Drops!** | `modrinth.com/mod/get-it-together-drops` | Yerdeki item birleştirme |
| **FastFurnace** | `curseforge.com/minecraft/mc-mods/fastfurnace` | Fırın recipe cache |
| **FastWorkbench** | `curseforge.com/minecraft/mc-mods/fastworkbench` | Crafting cache |
| **FastSuite** | `curseforge.com/minecraft/mc-mods/fastsuite` | Genişletilmiş recipe cache |
| **Structure Layout Optimizer** | `modrinth.com/mod/structure-layout-optimizer` | `structure_layout_optimizer-neoforge-1.0.11.jar` — **Resourceful Config gerekir** |
| **Resourceful Config** | `curseforge.com/minecraft/mc-mods/resourceful-config` | ↑ üstündekinin bağımlılığı |
| **Ksyxis** | `modrinth.com/mod/ksyxis` | Spawn chunk yükleme kaldırılır → hızlı açılış |
| **AI Improvements** | `curseforge.com/minecraft/mc-mods/ai-improvements` | Pathfinding |
| **Async Locator** | `curseforge.com/minecraft/mc-mods/async-locator` | `/locate` ve harita async |
| **Chunky** | `modrinth.com/mod/chunky` | Pregen. **En büyük tek kazanç.** |

### Opsiyonel — Katman 2.5

| Mod | Link | Not |
|---|---|---|
| **ServerCore** | `modrinth.com/mod/servercore` | Dinamik view-distance, mob AI throttling. **Moonrise ile chunk ayarları çakışabilir** — kurarsan ServerCore'un chunk ile ilgili özelliklerini kapat. |
| **Sepals** | `modrinth.com/mod/sepals` | AI scheduler rewrite. Mob farm testinde 12→19 TPS. **Architectury gerektirir.** |
| **Let Me Despawn** | `modrinth.com/mod/lets-despawn` | Mob despawn davranışı düzeltmesi |
| **Smooth Chunk Save** | `curseforge.com/minecraft/mc-mods/smooth-chunk-save` | Kayıt spike'larını yayar. **Moonrise'ın kendi chunk-saving ayarları var — ikisi çakışabilir, önce moonrise.yml'yi dene.** |

---

## KATMAN 3 — Worldgen

| Mod | Link | Sürüm |
|---|---|---|
| **Generator Accelerator** | `curseforge.com/minecraft/mc-mods/generator-accelerator` · `github.com/Team-Argentum/GeneratorAccelerator` | **1.4.10** ile başla → 1.6.1 |
| **Moonrise Compats** | `curseforge.com/minecraft/mc-mods/moonrise-compats` | `MoonriseCompats-neoforge-0.1.0-beta.15+2eae1b1.8.jar` — **base sürüm Moonrise ile aynı olmalı** |

---

## ❌ KURMA

```
C2ME              → Moonrise ile temelden uyumsuz (chunk sistemi çakışması)
c2me-ocl          → C2ME olmadan anlamsız
Fast Noise        → Nether'da zombi/creeper spawn ediyor (Tuinity/Moonrise#160)
Noisium           → uyumsuz
ScalableLux       → Starlight fork'u, Moonrise'da Starlight zaten var
Starlight         → aynı sebep
Lucis             → Starlight fork'larıyla uyumsuz olduğunu kendi söylüyor
Canary            → Lithium fork'u
Radium / Radium Reforged → Lithium fork'u
Krypton           → Fabric-only, NeoForge sürümü yok
Pluto             → 1.19.3'te durmuş, 1.21.1 yok
PoCL              → sistemden tamamen kaldır
```

---

## Kurulum Checklist

```
[ ] Dünya yedeği alındı
[ ] Java 21 kurulu (java -version → 21.x)
[ ] NeoForge 21.1.x kurulu
[ ] eula.txt → eula=true

--- Katman 1 ---
[ ] Moonrise
[ ] Lithium
[ ] FerriteCore
[ ] ModernFix (+ modernfix-mixins.properties)
[ ] AllTheLeaks
[ ] spark
[ ] Sunucu açıldı, log temiz, /spark tps ölçüldü → BASELINE: ____ MSPT

--- Config ---
[ ] config/moonrise.yml yerleştirildi
[ ] worker-threads CPU'ya göre ayarlandı  (CPU: ____ thread → değer: ____)
[ ] io-threads disk tipine göre ayarlandı (disk: ____ → değer: ____)
[ ] population-gen-parallelism: false doğrulandı
[ ] server.properties: view-distance / simulation-distance ayarlandı
[ ] start.sh / start.bat: MEMORY ve NeoForge sürüm yolu düzeltildi
[ ] Sunucu açıldı → /spark tps: ____ MSPT

--- Katman 2 ---
[ ] Katman 2 modları kuruldu
[ ] Sunucu açıldı, log temiz
[ ] 10 dk oynandı → /spark tps: ____ MSPT

--- Katman 3 ---
[ ] Generator Accelerator 1.4.10
[ ] Moonrise Compats (base sürüm eşleşiyor mu kontrol edildi)
[ ] 15 dk yeni araziye uçuldu
[ ] Cevher / ağaç / biyom / mağara / yapı kontrolü yapıldı
[ ] Mob spawn kontrolü yapıldı (Nether'da zombi VAR MI?)
[ ] /spark profiler start --thread * --not-combined ile ölçüldü

--- Katman 4 ---
[ ] Pregen ayarları geçici olarak uygulandı (max-tick-time=-1, view=4)
[ ] Chunky pregen çalıştırıldı (overworld 5000 / nether 1000 / end 1000)
[ ] Pregen ayarları geri alındı
[ ] FİNAL /spark tps: ____ MSPT
```
