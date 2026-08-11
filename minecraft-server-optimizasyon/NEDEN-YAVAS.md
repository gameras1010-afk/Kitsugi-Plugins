# "Chunk yükleme hâlâ yavaş" — Neden ve Ne Yapılır

Bu doküman C2ME tabanlı kuruluma göre güncellenmiştir. Moonrise terk edildi.

---

## 1. Moonrise neden yetmedi

Moonrise'ın varsayılan worker thread formülü:

```
worker-threads = (çekirdek / 2) / 2
```

| CPU | Moonrise varsayılan worker |
|---|---|
| 4 çekirdek | 1 |
| **6 çekirdek (senin)** | **1** |
| 8 çekirdek | 2 |
| 16 çekirdek | 4 |

Bunu 3'e çıkardın, yine yetmedi. Çünkü asıl sorun sayı değil **mimari**:

| | C2ME | Moonrise |
|---|---|---|
| Ana hedef | **Worldgen'i paralelleştirmek** | Chunk sistemini düzenli/stabil yapmak |
| Kökeni | Sıfırdan, bu iş için yazıldı | Paper'dan port |
| Worldgen paralelliği | Tasarımın merkezi | Sonradan eklenmiş, muhafazakâr |
| Async IO | Var, `replaceImpl` ile optimize | Basit |

Moonrise "bozuk" değil — **sen worldgen hızı ölçüyorsun, Moonrise'ın
optimize etmediği şeyi.** Paper'ın önceliği tick stabilitesidir, worldgen
throughput'u değil.

**Karar: C2ME'de kalıyoruz.**

---

## 2. Ama muhtemelen C2ME'yi de tam kullanmıyorsun

İki ayar var ve **ikisi de varsayılan olarak yanlış**:

### a) `threadedWorldGen.enabled` — VARSAYILAN `false`

```toml
[threadedWorldGen]
enabled = true
```

**Bu kapalıyken C2ME'nin paralel worldgen'i hiç çalışmıyor.** C2ME kurulu
olması yetmiyor. Bu satırı açmadıysan, şu ana kadar C2ME'nin sadece IO ve
scheduling optimizasyonlarını kullandın — asıl özelliğini değil.

### b) `globalExecutorParallelism` — varsayılan senin makinende **3**

C2ME'nin Linux formülü:
```
max(1, min(cpus / 1.2 - 2, RAM sınırı))
   = 6 / 1.2 - 2 = 3
```

6 çekirdeğin var, C2ME 3 kullanıyor. **5 yap.**

Geliştiricinin (ishland) tavsiyesi:
> *"change globalExecutorParallelism to your thread count or slightly below...
> if you need fps and tps stability, you need to reserve a few threads"*

5 = 5 worker + 1 çekirdek ana tick/netty/GC'ye. i5-9400F'te SMT yok, o yüzden
6 yazamazsın — ana tick thread'i aç kalır ve TPS düşer.

---

## 3. Darboğazın gerçekten ne? — Teşhis

`/spark profiler start --thread * --not-combined`, 60 sn hiç gitmediğin
yöne uç, `/spark profiler stop`.

### Senaryo A — `NoiseBasedChunkGenerator` / `ChunkGenerator` üstte
→ **Worldgen darboğazı.** Yeni arazi üretiliyor.
→ Çözüm: `threadedWorldGen = true`, `globalExecutorParallelism = 5`,
   Fast Noise (Connector varsa), **pregen**.

### Senaryo B — `RegionFileStorage` / `ChunkSerializer` üstte
→ **Disk/IO darboğazı.** Zaten üretilmiş chunk'lar diskten okunuyor.
→ Çözüm: `ioSystem.replaceImpl = true`, `chunkDataCacheLimit = 16384`,
   heap'i düşük tutup **OS page cache**'e yer bırakmak.
→ ⚠️ Bu senaryoda worldgen modları sana **hiçbir şey vermez**.

### Senaryo C — `ThreadedLevelLightEngine` / `LightEngine` üstte
→ **Işık motoru darboğazı.**
→ Çözüm: **ScalableLux kur.** Moonrise'ı silince Starlight'ı kaybettin,
   ışık vanilla'ya döndü. Bu çok muhtemel bir senaryo.

### Senaryo D — `ServerEntity`, `ChunkMap.tick`, mob AI üstte
→ **Entity/tick darboğazı.** Chunk sistemiyle alakası yok.
→ Çözüm: ServerCore, Lithium, `simulation-distance` düşür.
→ ⚠️ C2ME burada işe yaramaz.

---

## 4. Karar ağacı

```
Chunk yavaş
│
├─ c2me.toml'da threadedWorldGen.enabled = true mu?
│  └─ HAYIR → BUNU AÇ. Başka hiçbir şey yapma, önce bunu test et.
│
├─ globalExecutorParallelism kaç?
│  ├─ 3 (varsayılan) → 5 yap
│  └─ 5 → devam et
│
├─ ScalableLux kurulu mu?
│  └─ HAYIR → KUR. Moonrise gitti, ışık motoru boşta.
│
├─ /spark profiler → hangi senaryo?
│  ├─ A (worldgen) → pregen çalıştır (asıl çözüm)
│  ├─ B (disk)     → heap'i 8G'de tut, cache limitlerini yükselt
│  ├─ C (ışık)     → ScalableLux
│  └─ D (entity)   → ServerCore + Lithium + sim-distance ↓
│
└─ Hepsini yaptın, hâlâ yavaş?
   └─ CPU limitine geldin. 6 thread bu kadar.
      Tek çare: PREGEN. Chunk üretimini sıfırla.
```

---

## 5. Pregen — tartışmayı bitiren şey

Optimizasyon chunk üretimini birkaç kat hızlandırır. **Pregen onu sıfırlar.**

Bittiğinde worldgen diye bir maliyet kalmaz; geriye sadece diskten okuma
kalır, o da NVMe'de mikrosaniye. Sonra Senaryo A'yı bir daha hiç görmezsin.

```bash
# server.properties geçici:
#   max-tick-time=-1
#   view-distance=4
#   simulation-distance=4
#   spawn-monsters=false
#   spawn-animals=false
#
# c2me.toml geçici (oyuncu yok, TPS önemsiz):
#   globalExecutorParallelism = 6
```

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 3000
/chunky start
```

Oyuncular yokken çalıştır. Bitince ayarları geri al.

**Bu, hangi modu kullandığından bağımsız olarak en büyük tek kazanç.**

---

## 6. Beklentiyi ayarla

C2ME'nin resmî benchmark'ları **16-80 thread'lik** makinelerde yapılıyor.
Sen 6 thread'desin. `globalExecutorParallelism = 5` ile alabileceğinin
neredeyse tamamını alıyorsun.

6 thread'lik bir CPU'da hiçbir mod sana 16 thread'lik sunucu hissi veremez.
Bu bir mod seçimi sorunu değil, donanım sınırı.

Yapabileceğin en büyük iyileştirme sırasıyla:

| # | Ne | Kazanç |
|---|---|---|
| 1 | **Pregen (Chunky)** | Worldgen maliyeti → 0 |
| 2 | `threadedWorldGen = true` | C2ME'nin asıl özelliği açılır |
| 3 | `globalExecutorParallelism = 5` | 3 → 5 worker |
| 4 | **ScalableLux** | Işık darboğazı kalkar |
| 5 | `cpupower governor = performance` | %10-15 (Ubuntu varsayılanı `powersave`) |
| 6 | Heap 8G'de kalsın | ~5 GB OS page cache = chunk RAM'den gelir |

İlk üçünü yap, sonra tekrar konuşalım.
