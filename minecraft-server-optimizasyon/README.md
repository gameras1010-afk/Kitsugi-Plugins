# Moonrise Tabanlı Sunucu Optimizasyon Paketi
### Minecraft 1.21.1 · NeoForge · Dedicated Server

Bu paket, **Moonrise'ı merkeze alan** bir sunucu optimizasyon yığınıdır. C2ME
kullanılamadığı (Moonrise ile temelden uyumsuz) varsayımıyla hazırlanmıştır.

---

## 0. Önce Bunu Oku

**Hepsini birden kurma.** Mod listesi 4 katmana ayrılmıştır. Katman katman kur,
her katmandan sonra sunucuyu aç, 10 dakika oyna, `/spark tps` ile ölç.
Bir şey bozulursa hangi katman olduğunu bilirsin.

**Dünya yedeği al.** Özellikle Katman 3'e geçmeden önce.

---

## 1. KATMAN 1 — Çekirdek (Zaten Var / Olmazsa Olmaz)

Bunlar tartışmasız. Hepsi Moonrise ile resmî olarak uyumlu.

| Mod | Ne yapar | Not |
|---|---|---|
| **Moonrise** | Chunk sistemi + Starlight + collision + entity tracker | Ana motor |
| **Lithium** | Oyun mantığı hot path'leri | Moonrise çakışanları OTOMATİK kapatır |
| **FerriteCore** | RAM deduplikasyonu (~%40 tasarruf) | Moonrise çakışanları OTOMATİK kapatır |
| **ModernFix** | Başlangıç + bellek + çeşitli fix | `mixin.perf.worldgen_allocation=true` |
| **AllTheLeaks** | Bellek sızıntısı yamaları | 1.21.1 NeoForge ✅ aktif geliştiriliyor |
| **spark** | Profiler | Ölçmeden optimize etme. Şart. |

> **Moonrise kaynağı:** Lithium ve FerriteCore satırları Moonrise'ın kendi
> README'sindeki uyumluluk tablosundan alınmıştır (`Tuinity/Moonrise`, `mc/1.21.1`).
> "Moonrise will automatically disable conflicting parts" — yani elle bir şey yapmana gerek yok.

---

## 2. KATMAN 2 — Sunucu Tick / TPS (Güvenli Kazanç)

Bunlar chunk sistemine dokunmaz, dolayısıyla Moonrise ile çakışma riski düşüktür.

| Mod | Ne yapar | Kazanç |
|---|---|---|
| **Alternate Current** | Redstone dust yayılımını baştan yazar | Redstone lag'inde ~%95 |
| **Clumps** | XP orb'larını birleştirir | Mob farm'da entity sayısı çöker |
| **Get It Together, Drops!** | Yerdeki item'ları birleştirir | Aynı mantık, item tarafı |
| **FastFurnace / FastWorkbench / FastSuite** | Recipe cache | Büyük auto-smelter'da MSPT |
| **Structure Layout Optimizer** | Jigsaw yapı üretimi | Modlu yapılarda büyük fark |
| **Ksyxis** | Spawn chunk'larını yüklemeyi bırakır | Sunucu açılışı çok hızlanır |
| **AI Improvements** | Pathfinding | Mob yoğun sunucuda |
| **Async Locator** | `/locate`, hazine haritası async | Donma yok |

**Structure Layout Optimizer** için: `Resourceful Config` bağımlılığı gerekir.
1.21.1 NeoForge son sürüm `1.0.11+1.21.1-neoforge`.

---

## 3. KATMAN 3 — Worldgen Hızlandırma (C2ME'nin Yerine)

### 🏆 Generator Accelerator

C2ME kullanamadığın için worldgen tarafı boş kalıyor. Bu mod o boşluğu dolduruyor.

- **CurseForge:** `curseforge.com/minecraft/mc-mods/generator-accelerator`
- **Kaynak:** `github.com/Team-Argentum/GeneratorAccelerator`
- **Moonrise = Optional Dependency** (birlikte çalışmak için tasarlanmış)
- Eski adı: *Moonrise Generator Accelerator*

**README'den:** *"the 1.21.1 release boasts full compatibility with the Moonrise chunk system."*

**Krediler:** C2ME (`MixinNoiseBasedAquifer`, `MixinBeardifier`, `MixinConfiguredFeature`,
`MixinOreFeature`), CanvasMC, Noisium. Yani C2ME'nin ve Noisium'un mantığını
Moonrise'a uyumlu şekilde yeniden yazmışlar.

#### Hangi sürüm?

| Sürüm | Tarih | Durum |
|---|---|---|
| `[1.21.1-1.4.10] ...-neoforge.jar` | 5 May 2026 | ✅ **Buradan başla** |
| `[1.21.1-1.6.1] ...-neoforge.jar` | 18 May 2026 | ⚠️ En popüler (12.2K), ama 1.5+ uyarısı var |
| `[1.21.1-1.6.2] ...-neoforge.jar` | 30 May 2026 | ⚠️ En yeni, en riskli |

> **⚠️ Çelişki uyarısı:** GitHub README "Moonrise ile tam uyumlu" diyor,
> ama CurseForge açıklaması daha yeni ve daha temkinli:
> *"As of 1.5, we've reworked major parts of the mod, so there may be conflicts
> with other optimization mods such as Moonrise and C2ME. Versions below should
> be mostly compatible."*
>
> Bu yüzden **1.4.10** ile başla. Sorun çıkmazsa 1.6.1'e çık.

#### Native C3 JNI modülü (GPU merakının gerçek cevabı)

README'den: *"[Experimental] Native C3 Noise Module (JNI) — An optional,
ultra-fast noise generation module written entirely in C3 and hooked directly
into the JVM via JNI. Support: Currently supports Linux and Windows."*

Sen GPU'ya iş atmaya çalışıyordun. Bu modül noise matematiğini JVM'den çıkarıp
native koda atıyor — RX 550X'in FP64'ü zaten CPU'nun ~1/5'i olduğu için
**native CPU kodu o GPU'dan daha hızlı olacak.**

**AMA varsayılan kapalı, sebebi:** *"floating-point math differences in the
native implementation may cause noticeable discrepancies in world generation
compared to vanilla."*

→ **Mevcut dünyanda AÇMA.** Chunk sınırlarında duvarlar/uçurumlar oluşur.
→ Yeni dünyada açabilirsin.

### Moonrise Compats

- **CurseForge:** `curseforge.com/minecraft/mc-mods/moonrise-compats`
- 1.21.1 NeoForge son sürüm: `MoonriseCompats-neoforge-0.1.0-beta.15+2eae1b1.8.jar`

**Versiyon eşleşmesi ZORUNLU.** Base versiyon Moonrise'ınkiyle birebir aynı olmalı:

```
Moonrise-NeoForge   0.1.0-beta.15+2eae1b1
MoonriseCompats     0.1.0-beta.15+2eae1b1.8   ← base aynı, sonuna .8 patch eki
```

Vanilla+az modsan şart değil. Modlu oynuyorsan kur.

---

## 4. KATMAN 4 — Pregen (En Büyük Tek Kazanç)

### Chunky

Hiçbir mod, "chunk zaten üretilmiş" olmanın yerini tutmaz. Worldgen
optimizasyonu chunk üretimini 2x hızlandırır; pregen onu **sıfırlar**.

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 5000
/chunky start

# bitince:
/chunky world minecraft:the_nether
/chunky radius 1000
/chunky start

/chunky world minecraft:the_end
/chunky radius 1000
/chunky start
```

**Nether radius'unu küçük tut** — Nether'da 1 blok = Overworld'de 8 blok.
1000 nether radius = 8000 overworld kapsama.

Pregen'i **oyuncular yokken** çalıştır. Bitince `/chunky cancel`.

---

## 5. ❌ KURMA — Moonrise ile Uyumsuz

| Mod | Neden |
|---|---|
| **C2ME** | Chunk sistemini baştan yazıyor, Moonrise da öyle → temelden uyumsuz |
| **c2me-ocl** | C2ME olmadan anlamsız |
| **Fast Noise** | Biyomlar yanlış üretiliyor, Nether'da zombi/creeper spawn ediyor (`Tuinity/Moonrise#160`, Fast Noise geliştiricisinin kendi açtığı issue) |
| **Noisium / NoisiumForked** | Uyumsuz |
| **ScalableLux** | Starlight fork'u — Moonrise'da Starlight ZATEN var |
| **Starlight (NeoForge)** | Aynı sebep |
| **Canary / Radium** | Lithium fork'u — Lithium'u kullan, ikisini birden değil |
| **Lucis** | Starlight fork'larıyla "tanımı gereği uyumsuz" diyor; Moonrise Starlight içeriyor → büyük ihtimalle çakışır |
| **Krypton / Pluto** | Krypton = Fabric only. Pluto = 1.19.3'te kalmış. 1.21.1 NeoForge'da yok. |
| **PoCL** | Sistemden tamamen sil |
| **Biomes O' Plenty + TerraBlender** | Generator Accelerator ile biyom yerleşimi bozulabilir |

---

## 6. Config Dosyaları

Bu klasördeki `config/` içinde hazır dosyalar var:

| Dosya | Nereye |
|---|---|
| `config/moonrise.yml` | `<sunucu>/config/moonrise.yml` |
| `config/lithium.properties` | `<sunucu>/config/lithium.properties` |
| `config/server.properties.ornek` | `<sunucu>/server.properties` (birleştir, üzerine yazma) |
| `start.sh` | `<sunucu>/start.sh` (Linux) |
| `start.bat` | `<sunucu>\start.bat` (Windows) |

---

## 7. Uygulama Sırası

```
1.  Dünya yedeği al                          ← atlamak yok
2.  Katman 1 kur → aç → 10 dk oyna → /spark tps
3.  Katman 2 kur → aç → 10 dk oyna → /spark tps
4.  moonrise.yml + lithium.properties koy → aç → test
5.  Generator Accelerator 1.4.10 kur → aç → 10 dk oyna
    ↳ mob spawn oranlarına bak, entity sayısı patlıyor mu?
6.  Chunky pregen çalıştır (oyuncular yokken)
7.  Sorun yoksa Generator Accelerator 1.6.1'e çık
8.  Yeni dünya açacaksan native C3 modülünü dene
```

## 8. Ölçüm

```
/spark tps                                    ← genel durum
/spark profiler start --thread * --not-combined   ← Generator Accelerator'ın istediği format
# 60 saniye yeni chunk'a doğru uç
/spark profiler stop
/spark healthreport
```

**Hedef:** MSPT < 50ms (= 20 TPS). 40ms altı iyi. 30ms altı çok iyi.
