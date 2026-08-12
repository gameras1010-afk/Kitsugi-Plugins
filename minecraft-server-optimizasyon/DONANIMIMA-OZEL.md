# Senin Makinen İçin Kesin Ayarlar

```
CPU   : Intel i5-9400F @ 2.90 GHz (6 çekirdek / 6 THREAD, turbo 4.10 GHz)
RAM   : 16 GB DDR4-2667 (2x8, dual channel ✅)
Disk  : Kioxia Exceria 480 GB NVMe (338 GB boş ✅)
GPU   : RX 550 (Lexa PRO) — sunucu için tamamen alakasız
OS    : Ubuntu 24.04.4 LTS, kernel 6.8
```

---

## 🔴 Sorunun kesin teşhisi

Moonrise'ın varsayılan worker thread formülü:

```
worker-threads = (çekirdek / 2) / 2
                = (6 / 2) / 2
                = 1
```

# Moonrise senin makinende TEK THREAD ile chunk üretiyordu.

Bunu 3'e çıkardık, yine de yetmedi. Sebebi basit: **Moonrise'ın mimarisi
worldgen'i paralelleştirmek için tasarlanmadı.** Paper'dan geliyor ve
Paper'ın önceliği worldgen hızı değil, tick stabilitesi. Moonrise chunk
sistemini *düzenli* yapar, *hızlı* yapmaz.

C2ME'nin tek işi ise worldgen'i paralelleştirmek. O yüzden C2ME'de kalıyoruz.

**Karar: Moonrise silindi. Tüm ayarlar C2ME'ye göre.**

---

## ⭐ EN ÖNEMLİ AYAR: `globalExecutorParallelism = 5`

Bu tek satır, bu dokümandaki her şeyden daha önemli.

### C2ME geliştiricisinin (ishland) resmî tavsiyesi

> *"change globalExecutorParallelism to your thread count or slightly below.
> Note: if you need fps and tps stability, you need to reserve a few threads
> for the rest of the system."*

### C2ME'nin KENDİ varsayılan formülü (Linux)

```
max(1, min(cpus / 1.2 - 2, RAM tabanlı sınır))
   = 6 / 1.2 - 2
   = 3
```

**C2ME kendi haline bırakılırsa senin makinende 3 thread açar.** Bu, mevcut
kurulumunda muhtemelen böyle çalışıyor — yani C2ME'yi de tam kapasite
kullanmıyorsun.

### Neden 5?

Thread bütçen (toplam **6**, hyperthreading YOK):

| Değer | Ne olur |
|---|---|
| 3 (varsayılan) | Gereksiz ihtiyatlı. CPU'nun yarısı boşta. |
| 4 | Muhafazakâr. TPS taş gibi, worldgen biraz yavaş. |
| **5** | ✅ **DOĞRU.** 5 worker + 1 çekirdek ana tick/netty/GC'ye kalır. |
| 6 | Ana tick thread'i CPU bulamaz. Chunk hızlı gelir ama TPS düşer. |

i5-9400F'te **SMT yok** — her worker gerçek bir fiziksel çekirdeği tamamen
işgal eder. 12 thread'lik bir CPU'da 12 yazabilirsin çünkü SMT sayesinde
ana thread yine çalışır. Sende yazamazsın.

**3 → 5 = %67 daha fazla worker.** Moonrise'ın 1'ine göre 5x.

### Nasıl ince ayar yaparsın

```
5 ile başla → /spark tps
  TPS sürekli 19.5 altı  → 4 yap
  TPS 20.0 sabit + chunk yavaş → 6 dene (riskli)
Chunky pregen sırasında (oyuncu yok) → geçici 6
```

---

## ⭐ İKİNCİ EN ÖNEMLİ: `threadedWorldGen.enabled = true`

```toml
[threadedWorldGen]
enabled = true   # VARSAYILAN: false
```

**Bu varsayılan olarak KAPALI.** Açmazsan C2ME'nin asıl özelliğini —
paralel worldgen'i — hiç kullanmıyorsun demektir. `globalExecutorParallelism`
kaç olursa olsun fark etmez.

Yanına bunu da aç:
```toml
asyncScheduling = true         # ana thread'in zamanlama yükü azalır
```

**Ama bu ikisini AÇMA — `false` kalacak:**
```toml
allowThreadedFeatures = false  # AÇMA → yarım ağaç / yarım kapı / kesik yapı
reduceLockRadius      = false  # AÇMA → upstream: "UNSAFE, YOU HAVE BEEN WARNED"
```
Gerekçesi ve kanıtı: **`BOZUK-CHUNK-COZUMU.md`**.
`enabled = true` kaldığı için paralel worldgen'i yine de kullanıyorsun;
sadece riskli iki alt-ayar kapalı. Maliyet ~%15-25 worldgen hızı,
karşılığında dünya bozulmuyor.

Tam config: `config/c2me.toml` (satır satır yorumlu).

---

## 🔴 ScalableLux — atlanamaz

Moonrise'ı silince **Starlight'ı kaybettin.** Işık motoru vanilla'ya döndü.

C2ME dokümantasyonu birebir:
> *"It is **strongly recommended** to install ScalableLux, because lighting
> can easily become a bottleneck"*

ScalableLux'u C2ME'nin **kendi geliştiricisi** yazdı ve C2ME'ye özel entegre etti:
> *"Reduced scheduling overhead with proper chunk system integration with C2ME"*

Kurmazsan ışık hesabı yeni darboğazın olur ve C2ME'nin hızını hiç göremezsin.
**Bu, Moonrise'dan çıkmanın tek gerçek bedeliydi ve tam karşılığı var.**

---

## Moonrise gidince NE KAZANDIN

Moonrise kuruluyken kuramadığın modlar artık serbest:

| Mod | Moonrise varken | Şimdi |
|---|---|---|
| **ScalableLux** | ❌ Boot'ta uyumsuzluk hatası (`Tuinity/Moonrise#11`) | ✅ Zorunlu |
| **Fast Noise** | ❌ Biyomlar bozuluyordu | ✅ Uyumlu (Connector gerekir) |
| **ServerCore** | ⚠️ Chunk ayarları çakışıyordu | ✅ Kur |
| **Lithium collision** | ❌ Moonrise zorla kapatıyordu | ✅ **Tam kapasite** |
| **Lithium entity tracker** | ❌ Aynı | ✅ **Tam kapasite** |
| **Lithium random tick** | ❌ Aynı | ✅ **Tam kapasite** |

Son üç satır önemli: Moonrise'ın "collision/entity tracker/random tick
optimizasyonu" diye sattığı şeyleri **artık Lithium yapıyor.** Kaybetmedin.

---

## Neyi neden böyle ayarladım

### `MEMORY="8G"` ← genel pakette `12G` idi

**Bu en önemli değişiklik ve muhtemelen sezgine ters gelecek.**

16 GB'ın var, ama hepsini heap'e vermek chunk yüklemeyi **yavaşlatır**:

```
 8 GB  → JVM heap
~1 GB  → JVM overhead (metaspace, code cache, netty, thread stack)
~2 GB  → Ubuntu 24.04 + servisler
~5 GB  → OS PAGE CACHE   ←←← senin sorununu çözen şey
```

**Page cache** = Linux'un `.mca` region dosyalarını RAM'de tutması. Senin
şikayetin "chunk yavaş yükleniyor" idi. Page cache doluyken chunk'lar
diskten değil **RAM'den** gelir. 5 GB page cache ≈ oyuncunun etrafındaki
tüm bölgenin RAM'de durması.

12G heap yazarsan page cache 1 GB'a düşer → chunk yükleme yavaşlar.
**8G heap + bol cache, 12G heap + kuru cache'ten hızlıdır.**

> Vanilla/hafif modsan (20-30 mod) **6G** bile yeter, page cache 7 GB olur.
> 100+ mod ve log'da GC uyarısı görüyorsan 10G'ye çık.

### `-XX:ParallelGCThreads=4`

Java 6 çekirdekte varsayılan olarak ~6 GC thread'i açar. GC çalıştığında
ana tick thread'inin **ve** 3 chunk worker'ının CPU'sunu tamamen çalar.
4'e sabitledim.

### `-XX:+UseNUMA` kaldırıldı

Tek soketli masaüstü sistem, NUMA yok. Genel scriptte vardı, seninkinden çıkardım.

### `G1HeapRegionSize=8M`, `G1NewSizePercent=30/40`

8G heap değerleri. Genel paketteki 16M ve 40/50 sadece 12G+ heap için doğru.

---

## `server.properties`

```properties
view-distance=10
simulation-distance=6
```

6 thread için doğru denge. `simulation-distance` maliyeti **kübik** büyür —
8 yapma.

`view-distance=10` C2ME ile **ucuz**, çünkü `noTickViewDistance` özelliği
uzaktaki chunk'ları oyuncuya gönderir ama **tick'lemez** — içindeki mob,
redstone, su akışı hesaplanmaz. Görsel mesafe bedava, simülasyon değil.

Tek başına oynuyorsan `view-distance=12` deneyebilirsin.

```properties
sync-chunk-writes=false    # C2ME ioSystem.async ile birlikte şart
max-tick-time=60000
```

---

## `maxConcurrentChunkLoads` kararı

```toml
[noTickViewDistance]
maxConcurrentChunkLoads = 3
```

Aynı anda kaç chunk yüklenebileceği. Değiş tokuş:

| Değer | Sonuç |
|---|---|
| Düşük (2-3) | Daha iyi latency, chunk'lar düzenli akar |
| Yüksek (5+) | Daha hızlı toplu yükleme, tick lag riski |

6 thread için **3** doğru. "Chunk yavaş yükleniyor" hissi devam ederse
4'e çıkar ama `/spark tps` ile MSPT'yi izle — 50 ms'i geçiyorsa geri in.

---

## Ubuntu tarafı — bunlar da fark yaratır

### 1. CPU governor'ı performance yap

Ubuntu varsayılanı `powersave`. i5-9400F'in turbo'su 4.10 GHz, ama governor
`powersave` iken 2.90 GHz'de sürünür. Minecraft **tek thread performansına**
çok duyarlı.

```bash
sudo apt install linux-tools-common linux-tools-$(uname -r)
sudo cpupower frequency-set -g performance

# kontrol:
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Kalıcı yapmak için:
```bash
sudo apt install cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
```

**Bu tek başına %10-15 verebilir.** Kaçırma.

### 2. Swappiness düşür

```bash
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

`AlwaysPreTouch` ile 8G heap'i baştan alıyoruz; kernel'in bunu swap'a
atmasını istemiyoruz.

### 3. GUI'yi kapat (masaüstü Ubuntu ise)

```bash
sudo systemctl set-default multi-user.target
sudo reboot
```

GNOME ~1 GB RAM + sürekli CPU yer. Yedek PC'yi sunucu olarak kullanıyorsan
gereksiz. Geri almak: `sudo systemctl set-default graphical.target`

### 4. NVMe kontrolü

```bash
# TRIM aktif mi?
sudo systemctl status fstrim.timer

# Disk gerçekten hızlı mı?
sudo hdparm -Tt /dev/nvme0n1
```

Kioxia Exceria QLC değil TLC — iyi. 338 GB boş, doluluk sorunu yok.

---

## Uygulama sırası

```
1.  [ ] DÜNYA YEDEĞİ AL                          ← atlamak yok

2.  [ ] mods/ içinden SİL:
        Moonrise*.jar
        MoonriseCompats*.jar
        generator-accelerator*.jar

3.  [ ] config/moonrise.yml SİL  (kalıntı bırakma)

4.  [ ] EKLE:
        c2me-neoforge-mc1.21.1-0.3.0+alpha.0.91.jar
        ScalableLux 0.2.0+neoforge        ← ATLAMA
        ServerCore
        Structure Layout Optimizer + Resourceful Config

5.  [ ] cpupower governor = performance          ← en kolay %10-15

6.  [ ] Sunucuyu AÇ → KAPAT   (config/c2me.toml oluşsun)

7.  [ ] c2me.toml düzenle:
        globalExecutorParallelism = 5
        [threadedWorldGen] enabled = true         ← EN KRİTİK
        allowThreadedFeatures = false             ← AÇMA (chunk bozar)
        reduceLockRadius      = false             ← AÇMA (chunk bozar)
        asyncScheduling = true
        [ioSystem] replaceImpl = true
        [ioSystem] chunkDataCacheLimit = 16384
        [generalOptimizations.autoSave] mode = "ENHANCED"

8.  [ ] start.sh içindeki NEOFORGE_VERSION'ı düzelt

9.  [ ] server.properties: view=10, sim=6, sync-chunk-writes=false

10. [ ] Aç, /spark tps → ÖLÇ

11. [ ] 15 dk yeni araziye uç → chunk hızını hisset
```

**Adım 10'dan sonra bana MSPT değerini söyle.** Öncesi/sonrası farkı göreceğiz.

---

## Sonra: pregen (asıl çözüm)

Hiçbir mod, "chunk zaten üretilmiş" olmanın yerini tutmaz. C2ME worldgen'i
birkaç kat hızlandırır; **pregen onu tamamen ortadan kaldırır.**

Bittiğinde kalan tek iş chunk'ı diskten okumak — NVMe'de mikrosaniye.
**Bu, hangi modu kullandığından bağımsız olarak en büyük kazanç.**

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
#
# start.sh'ta zaten var:
#   -Dchunky.maxWorkingCount=768
```

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 3000
/chunky start
```

**3000 seçtim, 5000 değil.** i5-9400F'te 5000 radius bir geceden uzun sürer.
3000 zaten 6000x6000 blokluk alan — normal bir sunucu için fazlasıyla yeterli.

Bitince ayarları geri al, `globalExecutorParallelism = 5` yap.

---

## Beklenti — dürüst konuşalım

C2ME'nin gücü **thread sayısıyla** ölçeklenir. Resmî benchmark'ları 16-80
thread'lik makinelerde yapılıyor. Sen 6 thread'desin.

`globalExecutorParallelism = 5` ile:
- Moonrise'ın varsayılan **1** thread'ine göre → **5x** worker
- C2ME'nin kendi varsayılan **3**'üne göre → **%67** daha fazla

Fark net hissedilecek. **Ama 6 thread'lik bir CPU'da hiçbir mod sana 16
thread'lik sunucu hissi veremez.** Fizik kanunu, mod seçimi değil.

Bu yüzden **pregen şart.** Yukarıdaki adımı atlama.

---

## Ölçüm — nereye bakacaksın

```
/spark profiler start --thread * --not-combined
# 60 sn HİÇ gitmediğin yöne uç (chunk üretimini zorla)
/spark profiler stop
/spark tps
/spark health
```

| Profilde üstte görünen | Anlamı / Çözüm |
|---|---|
| `NoiseBasedChunkGenerator` | Worldgen. `threadedWorldGen.enabled` gerçekten `true` mu? |
| `ThreadedLevelLightEngine` | **ScalableLux kurmayı unutmuşsun** |
| `RegionFileStorage` | Disk. `ioSystem.replaceImpl = true` mu? |
| `ServerChunkCache.tick` | `globalExecutorParallelism` düşük, 5'e çek |
| `ServerEntity` / `ChunkMap.tick` | Entity tracker → ServerCore kur |

**Sonucu bana at**, ince ayar yaparız.
