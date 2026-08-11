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

C2ME aynı makinede 5-6 thread kullanır. **"Moonrise amk çok yavaş" dediğin
şey buydu.** Kod kalitesi değil, thread sayısı. 1 vs 6.

Bu düzeltilince ~3x hızlanma alacaksın ve muhtemelen C2ME'ye hiç ihtiyacın
kalmayacak.

---

## Neyi neden böyle ayarladım

### `worker-threads: 3`

Thread bütçen (toplam **6**, hyperthreading YOK):

| Thread | İş |
|---|---|
| 1 | Ana tick thread — aç kalırsa TPS düşer |
| 3 | Chunk worker ← **buraya yatırım yapıyoruz** |
| 2 | GC + netty + Ubuntu + I/O |

**Neden 3, neden 6 değil?** i5-9400F'te **SMT yok**. Her worker thread gerçek
bir fiziksel çekirdeği tamamen işgal eder. 12-thread'lik bir CPU'da 6 worker
yazabilirsin çünkü SMT sayesinde ana thread yine çalışır. Sende yazamazsın —
sunucu chunk'ları hızlı üretir ama oyun donar.

**1 → 3 zaten 3x.** Açgözlü olma.

### `io-threads: 2`

Moonrise'ın notu: `>1` sadece SSD'de mantıklı, HDD'de negatif ölçekleniyor.
Sende **NVMe** var → 1'in üstüne çıkmak doğru.

Ama 6 thread'e 4 I/O thread'i fazla. **2** doğru. I/O thread'leri çoğunlukla
disk bekler, CPU yemez — o yüzden 3+2+1=6 olması sorun değil.

### `player-max-gen-rate: 5.0` ← genel pakette `-1.0` idi

**Bunu senin için değiştirdim.** SMT olmadığı için, limitsiz bırakırsan yeni
araziye uçan tek bir oyuncu 3 worker'ı da kilitler ve sunucunun geri kalanı
(mob, redstone, hopper) durur. 12-thread'lik CPU'da bu risk düşük, sende yüksek.

- Tek başına oynuyorsan → `8.0`
- 2-5 kişi → `5.0` (mevcut)
- 5+ kişi → `3.0`

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
8 yapma. `view-distance=10` güvenli çünkü `auto-config-send-distance: true`
sunucu zorlanınca kendisi düşürüyor.

Tek başına oynuyorsan `view-distance=12` deneyebilirsin.

---

## population-gen-parallelism kararı

```yaml
population-gen-parallelism: false   # şu an böyle
```

Moonrise'ın açma koşulu: "~10 worker thread sürekli chunk üretiyorsa".
Sende **3** worker var → teknik olarak eşiğin altındasın.

**Önce `worker-threads: 3`'ün etkisini gör.** Muhtemelen yeterli gelecek.
Hâlâ yavaşsa ve worldgen modun yoksa (BOP/Terralith/YUNG's yok) yedek alıp
`true` dene.

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
1. [ ] cpupower governor = performance          ← en kolay %10-15
2. [ ] config/moonrise.yml kopyala (worker-threads: 3)
3. [ ] start.sh içindeki NEOFORGE_VERSION'ı düzelt
4. [ ] server.properties: view=10, sim=6
5. [ ] Sunucuyu aç, /spark tps → ÖLÇ
6. [ ] 15 dk yeni araziye uç
```

**Adım 5'ten sonra bana MSPT değerini söyle.** Öncesi/sonrası farkı göreceğiz.

---

## Sonra: pregen (asıl çözüm)

```bash
# server.properties geçici:
#   max-tick-time=-1
#   view-distance=4
#   simulation-distance=4
#   spawn-monsters=false
# moonrise.yml geçici:
#   worker-threads: 4     ← oyuncu yokken 4 güvenli
```

```
/chunky world minecraft:overworld
/chunky center 0 0
/chunky radius 3000
/chunky start
```

**3000 seçtim, 5000 değil.** i5-9400F'te 5000 radius bir geceden uzun sürer.
3000 zaten 6000x6000 blokluk alan — normal bir sunucu için fazlasıyla yeterli.

Bitince ayarları geri al.

---

## C2ME'ye geçmeli miyim?

**Hayır, henüz değil.** Şu anki karşılaştırma adil değildi:

| | Thread |
|---|---|
| Moonrise (varsayılan) | **1** |
| C2ME | 5-6 |

Elbette C2ME hızlı geldi. `worker-threads: 3` yaptıktan sonra tekrar ölç.

Ayrıca C2ME'ye geçersen Starlight'ı kaybedersin → ScalableLux kurman gerekir
→ ve **6 thread'lik bir CPU'da** C2ME'nin agresif paralelliği ana tick
thread'ini aç bırakır. C2ME 12+ thread'lik CPU'larda parlar. Senin donanımın
aslında Moonrise'ın muhafazakâr yaklaşımına daha uygun — sadece varsayılanı
fazla muhafazakârdı.

Düzelttikten sonra hâlâ memnun değilsen `NEDEN-YAVAS.md`'deki geçiş rehberi
hazır bekliyor.
