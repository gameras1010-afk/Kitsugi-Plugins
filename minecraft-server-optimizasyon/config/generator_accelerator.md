# Generator Accelerator — Config Rehberi

## Config dosyası nerede?

Mod ilk açılışta kendi config'ini üretir. Muhtemel konumlar:

```
<sunucu>/config/generatoraccelerator.toml
<sunucu>/config/generator_accelerator.json
<sunucu>/config/argentum/generatoraccelerator.toml
```

Sunucuyu **bir kez aç, kapat**, sonra `config/` klasörüne bak.

Mod alpha aşamasında olduğu için anahtar isimleri sürümden sürüme değişiyor.
Aşağıda **hangi modülün ne yaptığını** anlatıyorum; sen kendi dosyanda
karşılığını bulup ayarla.

---

## Modüller ve önerilen durumları

### ✅ AÇIK BIRAK — Bunlar güvenli, asıl kazanç burada

| Modül | Ne yapar | Neden güvenli |
|---|---|---|
| **Chunk Data Layer** | Üretim sırasında `PalettedContainer` yerine düz `int[4096]` kullanır. Palet aramasındaki Stream API kaldırılmış. | Sadece bellek düzeni değişiyor, çıktı bit bit aynı |
| **DOD Surface** | Yüzey oluşturmayı data-oriented hale getirir | Aynı |
| **FlatClimateIndex** | Biyom arama: SoA layout + warm-start heuristic + branchless matematik | Aynı biyom, daha hızlı arama |
| **Lazy Biome Alloc** | `LevelChunkSection` biyom dizisini geç ayırır | Saf bellek kazancı |
| **Feature Sorter DOD** | `TreeSet`/`TreeMap` → `ObjectArrayList` + TimSort. O(N log N) → O(N) | Sıralama sonucu aynı |
| **PlacedFeature Stream removal** | `Stream.flatMap` kaldırılmış | Davranış aynı |
| **Ore/Tree Refactor** | Cevher ve ağaç yerleştirme yeniden yazılmış | Aynı çıktı |
| **VectorNoise** | SIMD + x4 loop unroll + zero-allocation noise | Java Vector API, FP sonuç aynı |
| **Density Function Compiler** | IR folding + CSE (common subexpression elimination) | Matematiksel olarak eşdeğer |
| **Heightmap hole-punching** | Heightmap güncellemelerini optimize eder | — |
| **Aquifer / Beardifier** | C2ME'nin mixin'lerinden portlanmış | C2ME'de yıllardır test edilmiş |

### ❌ KAPALI BIRAK

| Modül | Neden |
|---|---|

**Native C3 Noise Module (JNI)** — `native_noise`, `c3_noise`, `use_native` gibi
bir isimle geçer. **Varsayılan zaten KAPALI, öyle bırak.**

Modun kendi uyarısı:

> *"floating-point math differences in the native implementation may cause
> noticeable discrepancies in world generation compared to vanilla."*

**Ne olur açarsan:** Mevcut dünyanda daha önce Java tarafında üretilmiş
chunk'larla, yeni native tarafta üretilecek chunk'lar **birbirine uymaz**.
Chunk sınırlarında düz kesilmiş duvarlar, havada asılı ada parçaları,
biten mağaralar görürsün. Geri dönüşü yok — o chunk'ları silmen gerekir.

**Ne zaman açabilirsin:** Sıfırdan yeni dünya açarken, ilk chunk üretilmeden
önce. O zaman tüm dünya tutarlı şekilde native ile üretilir.

Bu senin GPU worldgen arayışının pratikteki en yakın karşılığı — hesabı
JVM'den çıkarıp native koda taşıyor. RX 550X'in FP64 gücü CPU'nun altında
olduğu için native CPU yolu o GPU'dan hızlı çalışır.

---

## Sürüm seçimi

```
1.4.10  (5 May 2026)   ← BURADAN BAŞLA
1.6.1   (18 May 2026)  ← sorun yoksa buraya çık
1.6.2   (30 May 2026)  ← en yeni, en riskli
```

**Sebep:** CurseForge açıklaması diyor ki *"As of 1.5, we've reworked major
parts of the mod, so there may be conflicts with other optimization mods such
as Moonrise and C2ME."* GitHub README ise tam uyumluluk iddia ediyor.
İki kaynak çelişiyor → temkinli olan doğru.

---

## Kurulumdan sonra ne kontrol edeceksin

Generator Accelerator worldgen'i değiştirdiği için yan etkileri
**hemen görünmez**. 10-15 dakika şunlara bak:

- [ ] Yeni chunk'larda **cevher dağılımı** normal mi? (elmas/demir yoğunluğu)
- [ ] **Ağaç yoğunluğu** normal mi? Orman biyomu boş mu kalmış?
- [ ] **Biyom geçişleri** düzgün mü? Ani/keskin sınır var mı?
- [ ] **Mağaralar** birbirine bağlanıyor mu, yoksa kopuk mu?
- [ ] **Mob spawn** oranı normal mi? (Fast Noise'un yaptığı hatanın belirtisi:
      Nether'da zombi/creeper spawn etmesi — bunu görürsen anında kaldır)
- [ ] **Yapılar** (köy, kale, maden) üretiliyor mu?
- [ ] Log'da `WARN`/`ERROR` var mı?

Bunlardan biri bozuksa: modu kaldır, o bölgedeki region dosyalarını sil.

---

## Ölçüm

Mod geliştiricisinin istediği profil komutu:

```
/spark profiler start --thread * --not-combined
```

`--not-combined` önemli — Generator Accelerator worker thread'lerde çalışır,
thread'ler birleştirilirse kazancı göremezsin.

60 saniye boyunca **hiç üretilmemiş araziye doğru** elytra ile uç, sonra:

```
/spark profiler stop
```

Öncesi/sonrası karşılaştır. Bakacağın yer: `ChunkGenerator`, `NoiseBasedChunkGenerator`,
`SurfaceSystem`, `PlacedFeature` altındaki süreler.
