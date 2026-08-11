# "Moonrise yavaş, C2ME kadar hızlı değil" — Neden?

## Kısa cevap

**Haklısın. Moonrise worldgen'de C2ME kadar hızlı DEĞİL. Çünkü Moonrise bir
worldgen modu değil.**

Bu bir bug değil, tasarım tercihi. İkisi farklı problemi çözüyor:

| | C2ME | Moonrise |
|---|---|---|
| **Asıl işi** | Worldgen'i **tüm çekirdeklere** yayar | Chunk sistemini, ışığı, collision'ı, entity tracker'ı yeniden yazar |
| **Yeni arazi üretimi** | 🚀 Çok hızlı (2.1x) | 😐 Orta |
| **Zaten üretilmiş chunk yükleme** | İyi | 🚀 Çok iyi |
| **MSPT / TPS (oyun içi tick)** | Az etkiler | 🚀 Çok iyi |
| **Işık motoru** | Yok (ScalableLux ister) | Starlight gömülü |
| **Stabilite** | ⚠️ Deadlock, kaybolan ağaç | ✅ Paper'da production'da |

Yani "Moonrise bozuk" değil — **sen worldgen hızı ölçüyorsun, Moonrise'ın
güçlü olduğu yer orası değil.**

---

## AMA: Muhtemelen Moonrise'ı 2 thread'le çalıştırıyorsun

İşte asıl suçlu bu. Moonrise'ın **varsayılan** worker thread formülü:

```
worker-threads = (CPU_çekirdek / 2) / 2
```

Bu şu demek:

| CPU | Moonrise varsayılan worker | C2ME'nin kullandığı |
|---|---|---|
| 4 çekirdek / 8 thread | **1** | 8 |
| 6 çekirdek / 12 thread | **1** | 12 |
| 8 çekirdek / 16 thread | **2** | 16 |
| 12 çekirdek / 24 thread | **3** | 24 |
| 16 çekirdek / 32 thread | **4** | 32 |

**8 çekirdekli CPU'da Moonrise chunk üretmek için 2 thread kullanıyor,
C2ME 16 kullanıyor.** Aradaki fark bu. Kod kalitesi değil, thread sayısı.

Moonrise bu kadar muhafazakâr çünkü Paper'dan geliyor ve Paper'ın önceliği
"asla TPS düşürme". Sen ise "chunk hızlı gelsin" istiyorsun. Farklı hedef.

### Düzeltme

`config/moonrise.yml`:

```yaml
worker-pool:
  worker-threads: 6     # ← 8c/16t CPU için. Kendi CPU'na göre ayarla.
  io-threads: 4         # ← NVMe SSD. SATA ise 2, HDD ise -1.
```

Bu tek değişiklik çoğu insanda **2-3x** fark yaratıyor.

---

## İkinci suçlu: `population-gen-parallelism: false`

Moonrise'ın paralel worldgen anahtarı. **Varsayılan kapalı.**

Ben sana önceki pakette "false bırak" demiştim — çünkü modlu sunucuda
riskli. Ama senin şikayetin tam olarak bu ayarın çözdüğü şey.

```yaml
chunk-system:
  population-gen-parallelism: true
```

### Açmadan önce oku

Moonrise'ın kendi notu: worldgen'e dokunan modlar paralel çalışmaya güvenli
değil. Açarsan **modlu sunucuda** bozuk chunk / kayıp yapı / rastgele crash
riski var.

**Ne zaman açabilirsin:**
- Vanilla veya vanilla+ setup (worldgen modu yok) → **aç, sorun olmaz**
- Biyom/yapı modu var (BOP, Terralith, YUNG's, Repurposed Structures) → **açma**
- Emin değilsen → yedek al, aç, yeni bölgede 15 dk uç, kontrol et

---

## Peki gerçekten hangisi yavaş? Önce ÖLÇ

"Yavaş" iki farklı şey olabilir ve çözümleri zıt:

```
/spark profiler start --thread * --not-combined
# 60 saniye HİÇ GİTMEDİĞİN yöne uç
/spark profiler stop
```

**Senaryo A — Worldgen yavaş**
Profilde üstte: `NoiseBasedChunkGenerator`, `SurfaceSystem`, `PlacedFeature`,
`NoiseChunk`
→ Çözüm: worker-threads ↑, Generator Accelerator, pregen, (belki) C2ME'ye geç

**Senaryo B — Chunk yükleme yavaş (zaten üretilmiş arazi)**
Profilde üstte: `ChunkSerializer`, `RegionFileStorage`, disk I/O
→ Çözüm: io-threads ↑, SSD'ye geç. **Bunda C2ME sana hiçbir şey vermez.**

**Senaryo C — TPS/MSPT düşük, chunk aslında normal**
Profilde üstte: entity tick, block entity, redstone
→ Çözüm: Katman 2 modları, simulation-distance ↓. **C2ME burada işe yaramaz.**

C2ME'ye geçmek sadece **Senaryo A**'da mantıklı.

---

## Karar Ağacı

```
Şikayetin: "yeni araziye uçarken chunk yavaş geliyor"
│
├─ moonrise.yml'deki worker-threads'i ayarladın mı?
│  └─ HAYIR → önce onu yap. Muhtemelen sorun bitecek.
│
├─ Ayarladın, hâlâ yavaş. Worldgen modun var mı? (BOP, Terralith vb.)
│  ├─ YOK  → population-gen-parallelism: true yap
│  └─ VAR  → Generator Accelerator kur
│
├─ Hâlâ yavaş, ve sadece worldgen umurunda
│  └─ C2ME'ye geç (aşağıdaki bedeli kabul ederek)
│
└─ Her durumda: Chunky ile pregen yap. Tartışmayı bitirir.
```

---

## Gerçekten C2ME'ye geçmek istersen

Önceki tavsiyemde C2ME'yi "1.21.1 NeoForge'da stabil değil" diye elemiştim.
Güncel durum daha iyi, dürüst olayım:

| Sürüm | Tarih | İndirme |
|---|---|---|
| `c2me-neoforge-mc1.21.1-0.3.0+alpha.0.91.jar` | 22 Nis 2026 | 175K |
| `c2me-neoforge-mc1.21.1-0.3.0+alpha.0.89.jar` | 11 Oca 2026 | 145K |

Aktif geliştiriliyor, ciddi kullanıcı kitlesi var. "Alpha" etiketi C2ME'de
yıllardır duruyor, pratikte çoğu insan sorunsuz kullanıyor.

### Geçersen NE KAYBEDERSİN

Moonrise'ı silmek zorundasın (birlikte çalışmazlar). Gidenler:

- ❌ **Starlight** (gömülü ışık motoru) → yerine **ScalableLux** kurmalısın
- ❌ Collision optimizasyonu → MSPT'de kayıp
- ❌ Entity tracker rewrite → kalabalık sunucuda hissedilir
- ❌ Random ticking optimizasyonu
- ❌ `fix-MC-224294` (lav çift tick fix'i)
- ⚠️ Deadlock riski (geliştiricinin kendi benchmark'ında bildirilmiş:
  *"may hang the world out due to random deadlocks. Sometimes chunks may
  just stop loading at all requiring the whole modpack reboot"*)
- ⚠️ Kaybolan ağaç/yapı (*"Some trees or world generation stuff are missing"*)

### C2ME'ye geçiş mod listesi

```
✅ EKLE:   C2ME (neoforge 1.21.1, 0.3.0+alpha.0.91)
✅ EKLE:   ScalableLux          ← Starlight'ın yerine, ZORUNLU
❌ SİL:    Moonrise
❌ SİL:    Moonrise Compats
❌ SİL:    Generator Accelerator   ← C2ME ile çakışır

Kalanlar aynı: Lithium, FerriteCore, ModernFix, AllTheLeaks, spark,
Katman 2'nin tamamı, Chunky
```

C2ME config: `config/c2me.toml` → `threadedWorldGen = true`

---

## Üçüncü yol: BTSEngine: Concurrent

Generator Accelerator'ın yazarının (DenisMasterHerobrine) diğer projesi.
LockFree & CAS mimarisi ile paralel worldgen.

**Kendi benchmark'ı** (341 mod, yapı ağırlıklı, render 32 / sim 8):

| Kurulum | Süre | Hızlanma |
|---|---|---|
| Mod yok | 4m 55s | 1.0x |
| **C2ME** (0.3.0.alpha73) | 2m 20s | **2.1x** — ama deadlock + kayıp ağaç |
| **BTSEngine: Concurrent** (0.1.4-alpha) | 2m 27s | **2.006x** — deadlock yok |

C2ME'ye çok yakın hız, deadlock olmadan.

**AMA dikkat:**
- 1.21.1 + NeoForge only ✅ (sana uyuyor)
- Son sürüm `v0.1.5-alpha`, **17 Eyl 2025** — ~1 yıldır güncelleme yok
- Toplam **407 indirme** — neredeyse hiç test edilmemiş
- Custom License
- Yazarının kendi uyarısı: *"sometimes you can see weird world generation
  stuff may be missing such as trees. The generated world is not the same
  with original world"*

**Verdict:** Deneysel. Ana sunucunda kullanma, test dünyasında dene.

---

## Benim önerim (sırayla dene, ilk işe yarayanda dur)

```
1. worker-threads ve io-threads'i CPU/diskine göre ayarla
   → maliyeti sıfır, riski sıfır, çoğu vakada sorunu bitirir

2. /spark ile ÖLÇ — gerçekten worldgen mi yavaş?
   → değilse C2ME zaten çözmeyecek

3. Worldgen modun yoksa: population-gen-parallelism: true

4. Generator Accelerator 1.4.10 kur

5. Chunky ile pregen — asıl çözüm bu, hepsini gereksiz kılar

6. Hâlâ memnun değilsen C2ME'ye geç, ScalableLux'ü unutma
```

**Adım 5'in altını çiziyorum.** Hiçbir mod "chunk zaten diskte hazır"
olmanın yerini tutmaz. Worldgen 2x hızlanır; pregen onu **sıfırlar**.
Bir gece pregen çalıştır, bu tartışma biter.
