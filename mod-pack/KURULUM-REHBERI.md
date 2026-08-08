# 🛠️ KURULUM REHBERİ — 1.21.1 NeoForge Geçişi (i5-9400F + RX 550X + Headless Ubuntu)

**Bu klasördekiler:**
- `indir_modlar.py` — modları resmi kaynaklardan indirip **ZIP'leyen** script (tek komut)
- `mod_manifest.json` — 1.20.1 listenin 1.21.1 NeoForge karşılıkları (mod listesi)
- `LINK_LISTESI.txt` — tüm modların sayfa linkleri (elle indirmek istersen)
- `MCModPaketi-workflow.yml` — (opsiyonel) GitHub Actions ile otomatik zip üretmek için
- `KURULUM-REHBERI.md` — bu dosya

> 💡 **ZIP'i nasıl alırım?** Script'i **interneti olan herhangi bir makinede** çalıştır:
> `python3 indir_modlar.py` → `MC-1211-ModPaketi.zip` (içinde `mods-server/`, `mods-client/`, bu rehber, link listesi) üretilir.
> Yedek PC'ye bağlanabildiğine göre orada da çalıştırabilirsin.

> ⚙️ **Alternatif (otomatik, GitHub'da):** `MCModPaketi-workflow.yml` dosyasını GitHub'da herhangi bir reponun
> `.github/workflows/` klasörüne at (bu repoya da web arayüzünden "Add file" ile ekleyebilirsin),
> sonra **Actions → MC Mod Paketi → Run workflow** → bitince **Artifacts**'tan `MC-1211-ModPaketi.zip`'i indir.
> (Bu sandbox'ın bot token'ı workflow yazma iznine sahip olmadığı için dosyayı ben buraya ekleyemiyorum — ama sen repo sahibi olarak ekleyebilirsin.)

---

## 0️⃣ ÖNCE MAKİNENİ TANI (RAM bilmiyorsun demiştin)

Sunucuda (yedek PC) şu komutları çalıştır:

```bash
free -h                          # RAM toplam + boş (16GB doğrulanmıştı)
lscpu | grep -E "Model name|CPU\(s\)|Thread"   # işlemci doğrulama (i5-9400F, 6 çekirdek)
lspci | grep -i vga              # GPU doğrulama (RX 550/550X Lexa PRO görünmeli)
```

**i5-9400F:** 6 çekirdek / 6 thread → Minecraft sunucusu için yeterli ve sağlam. C2ME chunk üretiminde 6 çekirdeğin tamamını kullanır (vanilla tek çekirdekti) — teleport/hızlı uçuş/pre-gen belirgin hızlanır. 🎉

**RAM tavsiyesi (bu paket için) — senin 16GB DDR4:**

| Toplam RAM | `-Xmx` önerisi | Not |
|---|---|---|
| 32 GB | 14–16G | Rahat |
| **16 GB (senin)** | **12G** | ✅ 4GB OS'e kalır — bu paket için ideal |
| 8 GB | 6G | Zorlanır — Twilight Forest + C2ME ağır |

Senin eski ayarın `-Xms12G -Xmx12G` idi — 16GB RAM'de **aynı ayarı koru** (`-Xms12G -Xmx12G`).

---

## 1️⃣ Java 21 kur (1.21.1 zorunlu kılar)

```bash
# Ubuntu 24.04+:
sudo apt update && sudo apt install -y openjdk-21-jre-headless

# Eski Ubuntu (22.04) ise:
sudo apt install -y wget apt-transport-https gpg
wget -qO- https://packages.adoptium.net/artifactory/api/gpg/key/public | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/adoptium.gpg
echo "deb https://packages.adoptium.net/artifactory/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/adoptium.list
sudo apt update && sudo apt install -y temurin-21-jre

java -version   # "version 21.x" görmelisin
```

---

## 2️⃣ NeoForge 21.1.x kur (sunucu)

```bash
# 1) https://neoforged.net/ adresinden "1.21.1" için en son installer'ı indir (örn. neoforge-21.1.x-installer.jar)
wget https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.193/neoforge-21.1.193-installer.jar

# 2) Sunucu dizininde:
java -jar neoforge-21.1.193-installer.jar --installServer

# 3) Bu komut şunları üretir: run.sh / run.bat + libraries/ + neoforge-21.1.193.jar
```

> Sürüm numarası 21.1.x değişebilir; neoforged.net'teki güncel "1.21.1" sürümünü kullan. Kurulum sonrası `run.sh`'i düzenleyip JVM ayarını yaz:

```bash
nano run.sh
# içinde -Xms12G -Xmx12G varsa kontrol et; yoksa şuna benzer satırı ekle:
# JAVA_OPTS="-Xms12G -Xmx12G"
```

---

## 3️⃣ Modları indir (script)

```bash
# Bu klasörde (interneti olan makinede):
python3 indir_modlar.py --dry-run    # önce ne bulacağını gör
python3 indir_modlar.py              # asıl indirme (birkaç dakika)
```

**Çıktı:**
- `mods-server/` → sunucuya gidecek tüm jar'lar (performans + içerik + kütüphaneler)
- `mods-client/` → client tarafına gidecek jar'lar (JEI, JourneyMap, Sodium, Iris, FancyMenu...)

**Manuel indirilecekler** (script bunları "manuel indirilecek" diye yazar):
- **Twilight Forest** → script `file_id`'si ile indirmeyi dener; olmazsa: https://www.curseforge.com/minecraft/mc-mods/the-twilight-forest/files (1.21.1 NeoForge, 4.8.3345)
- **Born in Chaos, Epic Terrain, Alex's Mobs** → CurseForge sayfalarından "1.21.1 NeoForge" dosyasını elle indir, `mods-server/`'a at
- **Baritone** → GitHub'dan 1.21.1 build (client)

**Eksik çıkan mod adlarını bana listele** — manifeste ekleyip düzeltirim.

---

## 4️⃣ DÜNYA TAŞIMA (SİLMEK YOK — güvenli protokol)

1. **Sunucuyu kapat.**
2. **Komple yedek** (farklı diske/konuma):
   ```bash
   cp -r world world_yedek_1201
   cp -r DIM-1 DIM-1_yedek 2>/dev/null; cp -r DIM1 DIM1_yedek 2>/dev/null
   cp level.dat server.properties config world_yedek_1201_ek 2>/dev/null
   ```
3. **Yeni sunucu dizininde** (NeoForge kurulu): `world/`'u yedekten kopyala (yükseltilmiş kopyayla çalış).
4. `mods-server/` içeriğini `mods/` klasörüne at. **ÖNEMLİ:** eski 1.20.1 jar'larını bu klasöre KARIŞTIRMA — hepsi 1.21.1 sürümü olmalı.
5. Eski `config/` klasörünü kopyalama — yeni sürüm kendi config'lerini üretsin (eski config = crash sebebi #1). Ayarlarını sonra yeniden yap.
6. **İlk çalıştırma:**
   ```bash
   ./run.sh nogui
   ```
   `world` klasörü yoksa diye şaşırma — eğer sunucu yeni dünya oluşturmaya çalışıyorsa `level-name`/klasör adını kontrol et (server.properties'teki `level-name` ile kopyaladığın klasör adı aynı olmalı).

---

## 5️⃣ TEST (2–3 gün, oyuncusuz veya 1-2 testçiyle)

```bash
# TPS/MSPT:
spark tps
# Profil:
spark profiler start --timeout 60
# Loglarda sorun ara:
grep -iE "error|exception|unknown|failed|missing" logs/latest.log | grep -v "INFO" | head -50
```

**Kontrol listesi:**
- [ ] TPS 20.0 / MSPT düşük (öncesiyle karşılaştır)
- [ ] "Unknown block/item/entity" yok (eski mod eşyası kaybı bu loglarda görünür)
- [ ] Twilight Forest kapısı açılıyor mu, boyut yükleniyor mu
- [ ] Terralith/BOP/BWG biyomları yeni bölgelerde ürüyor mu
- [ ] Teleport + hızlı uçuş → chunk yükleme hızı (C2ME etkisi!)
- [ ] `stop` komutuyla temiz kapanıyor mu

**Temizse:** kopyayı gerçek sunucu yap, eskiyi `world_yedek_1201` olarak sakla.
**Sorun varsa:** eski Forge 1.20.1 dizinini geri aç → 10 dakikada geri dönersin (yedek sağlam).

---

## 6️⃣ GPU (RX 550) — DERİN ARAŞTIRMA SONUCU (2026-08)

**Sorun:** "1.21.1 NeoForge dedicated sunucuda chunk üretimini GPU'ya taşıyan başka yol var mı?"

**Cevap: EVET ama tek bir gerçek yol var — C2ME OpenCL + Rusticl.** Araştırma bulguları:

### ✅ SENİN SORUNUN: "CPU çoklu çekirdek + GPU ikisi AYNI ANDA kullanılabilir mi?"

**EVET — bu sistem tam olarak böyle çalışıyor.** C2ME-OCL, chunk üretimini ikiye böler:

| İş | Nerede çalışır | Paralellik |
|---|---|---|
| **Noise + biome hesabı** (terrain şekli) | **GPU** (OpenCL, RX 550) | GPU'nun kendi paralel çekirdekleri |
| **Yapılar, blok yerleştirme, karver'lar, entity/blockentity yükü** | **CPU** (C2ME paralel executor) | `globalExecutorParallelism = 5` ile 5 çekirdek |

Bu iki iş **aynı anda koşar** — GPU noise'i hesaplarken CPU yapıları/işlemi sürdürür. Yani "hem çoklu çekirdek hem GPU" = C2ME-OCL'nin tasarımı. GPU, CPU'nun yerini almaz; **işin bir parçasını devralır**, CPU da kalanında 5 çekirdeği kullanır. 🎯

### ✅ SENİN SUNUCUNDA DOĞRULANDI (senin test çıktın)

- `RUSTICL_FEATURES=fp64 clinfo` → **cl_khr_fp64: YES** ✅
- Device: **AMD Radeon RX 550 (polaris12)** ✅
- NeoForge **21.1.238** yükseltildi ✅
- Server şu an kapalı, mods klasörü boş → temiz başlangıç için iyi

**⚠️ AMA kritik kontrol:** fp64'in **HANGİ sürücüden** geldiğini doğrula — C2ME-OCL'nin Linux'ta desteklediği yol **Rusticl**; sürücü **Clover** ise mod çalışmaz/crash yapar.

```bash
ls /etc/OpenCL/vendors/            # içinde "mesa.icd" görünmeli (Rusticl); "libamdocl64.so" ise ROCm/Clover karışık
clinfo | grep -iA2 "Platform Name" # Rusticl: "Mesa ... (RUSTICL)" / Clover: "(CLOVER)"
clinfo | grep -i "Device Name"     # "AMD Radeon RX 550 (RUSTICL)" olmalı
```

- C2ME-OCL'nin resmi notu: Rusticl için **Mesa 26.1+** şart (senin 23.2.1 düşük). fp64 görünse de **Kisak PPA ile Mesa'yı güncelle**:
  ```bash
  sudo add-apt-repository ppa:kisak/kisak-mesa -y && sudo apt update
  sudo apt full-upgrade -y && sudo apt install -y mesa-opencl-icd clinfo ocl-icd-opencl-dev
  RUSTICL_FEATURES=fp64 clinfo -l   # "AMD Radeon RX 550 (RUSTICL)" görmelisin
  ```
- Mesa güncellemesi riskli geliyorsa önce mevcut haliyle DENE (23.2.1 Rusticl+fp64 çalışabilir) — ama log'da `Rusticl` geçiyorsa devam, `Clover` geçiyorsa PPA şart.

### 🔬 DERİN ARAŞTIRMA v2 (2026-08) — "Başka mod / daha temiz yol var mı?"

**Kesin cevap: Sunucu tarafı GPU worldgen yapan TEK mod = C2ME-OCL.** Tarandı ve elendi:
- **Voxy / Voxy WorldGen** → client tarafı LOD modu, **server-side desteği YOK** (topluluk teyitli)
- **GPU servers** → sadece 1.21.8+ Fabric
- **TeraGen** → ölü/terk edilmiş
- **Mega-Minecraft** → mod değil, baştan yazılmış demo (CUDA)
- **VulkanMod** → sadece client render
- **Terrain Diffusion** → Fabric + CUDA/DirectML; Linux AMD'de çalışmaz

**Sürücü yolları matrisi (RX 550, OpenCL 1.2+ için) — tam liste:**

| Yol | OpenCL | C2ME-OCL sonucu | Risk |
|---|---|---|---|
| **kisak/turtle PPA → Mesa 25.x + Rusticl** | 3.0 (fp64 ile) | ✅ Denenebilir (resmi not: 26.1+ ideal, 25.x deneysel) | 🟠 Orta — **OS yükseltmesi GEREKMEZ**, 22.04'te çalışır; `ppa-purge` ile geri dönülür |
| ROCm 5.7 legacy (gfx803) | 2.0 | ❌ "Unsupported — driver crashes" (C2ME'nin kendi tablosu) | 🔴 Yüksek |
| amdgpu-pro (PAL) | 2.0 | ❌ "Unsupported — driver crashes" (aynı tablo) | 🔴 Yüksek |
| PoCL (CPU OpenCL) | 1.2/2.0 | ❌ Modun kendi FAQ'su: "PoCL ile neredeyse kesin crash — kaldırın" | 🔴 |
| Clover (mevcut Mesa 23) | 1.1 | ❌ 1.2+ şartını karşılamıyor | — |

**Yani: ROCm ve amdgpu-pro resmi olarak C2ME-OCL tarafından "crashes" işaretli — bu yüzden bunlar gerçekçi seçenek değil. Tek gerçekçi sürücü yolu: Rusticl (daha yeni Mesa).**

### 🎯 EN TEMİZ YOL (v2 tavsiyesi)

**1) Rusticl'i OS yükseltmeden dene (22.04'te):**
```bash
# NOT: 22.04 için "fresh" PPA kaldırıldı — "turtle" (stable) kullanılır:
sudo add-apt-repository -y ppa:kisak/turtle
sudo apt update
apt-cache policy mesa-vulkan-drivers   # ~kisak ve 25.x görünmeli (ör. 25.0.7~kisak3~j)
sudo apt install -y mesa-opencl-icd clinfo ocl-icd-opencl-dev
RUSTICL_FEATURES=fp64 clinfo -l        # "AMD Radeon RX 550 (RUSTICL)" görünmeli
# görünürse → config/c2me.toml: allowIncompatibilityFallback=true ile kopya dünyada dene
# görünmezse/bozulursa → sudo ppa-purge ppa:kisak/turtle (tam geri dönüş)
```

**2) SIFIR RİSK ALTERNATİF — "pregen offload" (aslında en temiz yöntem):**
Sunucudaki GPU'ya hiç dokunmadan, chunk üretimini başka makinede yap:
1. Aynı modpaketi (server modları) **oyun bilgisayarına** kur (GPU'su daha iyi)
2. Orada dünyayı (kopyasını) aç → `/chunky radius 2000` + start → dünyayı üret
3. `region` dosyalarını sunucuya kopyala → sunucu sadece "hazır dünyayı" yükler, worldgen yükü sıfır

Bu, topluluğun önerdiği standart yöntem ("Pre-gen on CPU is simply what is most common") — sunucu headless kaldığı için sürücü riski yok, sonuç "hazır dünya + TPS kaskatı".

| Proje | 1.21.1 NeoForge server? | Sonuç |
|---|---|---|
| **C2ME OpenCL** | ✅ Evet | **Tek gerçek yol.** Sadece noise + biome stage GPU'ya gider; gerisi CPU. Kendi sayfası: "80+% hızlanma, CPU-bound vanilla overworld'de" |
| Terrain Diffusion | ❌ Hayır | Fabric + **CUDA/DirectML** ister; Linux'ta AMD GCN için sürücü yok; AMD GPU'da crash raporları var |
| VulkanMod | ❌ Hayır | Sadece **client render** (Vulkan) — sunucuya faydası yok |
| "WorldGen" modları | ❌ Hayır | CPU tabanlı worldgen modları, GPU yok |
| GPU load (mutcho255) | ❌ Hayır | Sadece **1.20.1 Forge** |
| GPU servers | ❌ Hayır | Sadece **1.21.8+ Fabric** |

Reddit'te geliştiriciler de aynı şeyi söylüyor: "Sunucuda GPU worldgen'i tek yapan C2ME'nin OpenCL modülü; pre-gen CPU'da en yaygın ve sağlam yol."

### ⚠️ Ama dürüst değerlendirme (RX 550 için gerçekçi beklenti)

1. **C2ME'nin kendi tablosu:** AMD GCN (RX 550) = **"Unsupported — driver crashes"**; Rusticl satırı = **"Partial"**.
2. **C2ME'nin Rusticl kullanımı için yeni şartı:** **Mesa 26.1 ve üzeri** + fp64 açık. Ubuntu 24.04'te Mesa ~24.x gelir → **Kisak PPA** ile 26.1+ kurman gerekir.
3. **fp64:** RX 550 (Polaris) fp64'ü fp32'nin **1/16'sı** hızda yapar (~76 GFLOPS) — çalışsa bile hızlanma mütevazı olur.
4. **Mod uyumluluğu:** C2ME-OCL "custom density function kullanan datapack'lerde çalışmaz" ve "bazı worldgen modları katastrofik bozulur" diyor. Senin pakette **Terralith/BOP/BWG/Epic Terrain** var → bunlar GPU modülüyle uyumsuzluk riskinin en yüksek olduğu modlar.
5. **Ama iyi haber:** C2ME config'inde `openclAccel.allowIncompatibilityFallback = true` var → GPU başlatılamazsa **otomatik CPU'ya geri döner** (normal worldgen'e düşer, crash olmaz).

### 🎯 SONUÇ — "Bana göre en iyi yöntem" (2 katmanlı plan)

**KATMAN 1 — Ana plan (garantili, %0 risk): CPU C2ME + pre-generation**
- C2ME CPU modu: 6 çekirdek + **AVX2 SIMD** zaten dahili; worldgen'i çok hızlı yapar (modda SIMD hızlandırma uzun zamandır var).
- **Chunky ile dünyayı önceden üret** (`/chunky start`) → oyuncular gezerken worldgen yükü **sıfır** olur; TPS 20.0'da kaskatı kalır.
- Bu, GPU'suz "en iyi" ve kesinlikle en stabil yol.

**KATMAN 2 — GPU denemesi (istediğin şey; kontrollü dene):**
- Mesa 26.1+ kur (Kisak PPA) → `clinfo -l` → "RUSTICL" görünmeli
- `RUSTICL_FEATURES=fp64` ile başlat → `python3 indir_modlar.py --include-experimental` ile OpenCL jar'ını al
- `config/c2me.toml`: `openclAccel.allowIncompatibilityFallback = true` **YAP** (crash yerine CPU'ya düşer)
- **Kopya dünyada** dene; `/chunky start` ile öncesi/sonrası hız ölç
- Sonuç: ✅ hızlanma görürsen kalır, ❌ bozuk worldgen/crash görürsen jar'ı sil → Katman 1 zaten ayakta.

**Özet: Tek yol = C2ME-OCL + Rusticl. Ama "en iyi" = Katman 1 (CPU + pregen), GPU deneysel bonus. İkisi çakışmaz; ikisini birden yaparsın.**

### ADIMLAR (Katman 2 için)

```bash
# 1) Mesa 26.1+ (Kisak PPA - Ubuntu 24.04 için):
sudo add-apt-repository ppa:kisak/kisak-mesa -y && sudo apt update
sudo apt install -y mesa-opencl-icd ocl-icd-opencl-dev clinfo

# 2) GPU + fp64 kontrol:
RUSTICL_FEATURES=fp64 clinfo -l
RUSTICL_FEATURES=fp64 clinfo | grep -iE "Device Name|cl_khr_fp64"

# 3) OpenCL jar'ını pakete dahil et:
python3 indir_modlar.py --include-experimental

# 4) Sunucuyu fp64 + fallback ile başlat (run.sh içine):
# RUSTICL_FEATURES=fp64 JAVA_OPTS="-Xms12G -Xmx12G" ./run.sh nogui

# 5) config/c2me.toml:
# openclAccel.allowIncompatibilityFallback = true
# globalExecutorParallelism = 5

# 6) Kopya dünyada ölç:
/chunky start
spark tps
```

### 📋 KONTROL LİSTESİ (deneme öncesi)
- [ ] Yedek alındı (kopya dünyada deniyor)
- [ ] Mesa 26.1+ kurulu (24.x'te Rusticl desteği yetersiz)
- [ ] `clinfo` GPU + fp64 gösteriyor
- [ ] `allowIncompatibilityFallback = true` yapıldı (crash değil, CPU'ya düşer)
- [ ] Sonuç ölçüldü (Chunky saniye/tick karşılaştırma)

---

## 7️⃣ İNCE AYAR & İYİLEŞTİRME (kalan kısım — modlardan sonra)

**Mod tarafı bitti; kalan = ince ayar + rutinler.** Sırayla:

### A) JVM flag'leri (Aikar's - G1GC) — run.sh'e yaz
```bash
JAVA_OPTS="-Xms4G -Xmx10G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -XX:MinHeapFreeRatio=20 -XX:MaxHeapFreeRatio=40 -XX:G1PeriodicGCInterval=60000 -XX:+G1PeriodicGCInvokesConcurrent"
```
Java 21'de bazı flag'ler deprecation uyarısı verirse zararsızdır (yok say veya çıkar). GC ayarı, heap'te takılma/durmaları azaltır.

> 🔑 **RAM'i "kendi kafasına göre" kilitleyen ayar bu (AlwaysPreTouch YOK):**
> - `-Xms4G` → açılışta sadece 4G bloke edilir (10G değil)
> - `-Xmx10G` → ihtiyaç arttıkça 10G'e kadar **kademeli büyür** (JVM gerektiği kadar alır)
> - `MinHeapFreeRatio=20 / MaxHeapFreeRatio=40` → G1 boştayken heap'i küçültüp **sisteme geri verir**
> - `G1PeriodicGCInterval + G1PeriodicGCInvokesConcurrent` → boşta periyodik GC ile küçülme otomatikleşir
> - `-XX:+AlwaysPreTouch` **KONMAZ** (o, açılışta 10G'in tamamını fiziksel olarak kilitleyip sisteme geri vermezdi — 15.6GB RSS'nin ana sebebi)

### B) server.properties ince ayarı
```properties
view-distance=10          # sunucu chunk yükleme mesafesi (10 = iyi denge)
simulation-distance=5     # entity/tick mesafesi — EN BÜYÜK TPS TASARRUFU
spawn-protection=0
network-compression-threshold=256
sync-chunk-writes=true    # güvenlik için AÇIK kalsın
```
`simulation-distance=5` tek başına en çok işe yarayan ayar — entity'ler 5 chunk ötede tick etmez, TPS rahatlar.

### C) Chunky ile pre-generation (GPU'lu/GPU'suz asıl "chunk açma" yöntemi)
```bash
/chunky radius 2000        # spawn çevresi yarıçapı (istediğin kadar)
/chunky start
/chunky progress           # tamamlanınca dünya "hazır" — oyuncular gezerken üretim yükü yok
```
Pre-gen bittiğinde TPS 20.0'da kaskatı kalır; yeni keşiflerdeki yük sıfırlanır.

### D) Linux ince ayarları
```bash
sudo apt install -y linux-tools-common 2>/dev/null
sudo cpupower frequency-set -g performance   # CPU'yu tam hızda tut (i5-9400F boost)
echo 10 | sudo tee /proc/sys/vm/swappiness   # swap'i geç kullan
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
ulimit -n 65535                              # çok bağlantı için
```

### E) Ölçüm & takip rutini (haftada 1)
```bash
spark tps
spark health
spark profiler start --timeout 120
spark gc                                     # GC durması var mı bak
```
Önce/sonra sayılarını kaydet → hangi ayar ne kazandırdı görünür.

### F) Yedek & güncelleme rutini
```bash
# /opt/mc/backup.sh (cron: 0 4 * * * /opt/mc/backup.sh)
rsync -a --delete /opt/mc/world /opt/mc/backups/world-$(date +%F)
```
Modları ayda 1 güncelle (C2ME alpha sık çıkar — changelog'a bak); her güncellemede önce yedek.

### G) Opsiyonel (sonradan): ışık motoru optimizasyonu
1.21.1 NeoForge için ScalableLux/Starlight tarzı ışık motoru modu varsa eklenebilir — eklemeden önce bana sor (uyumluluk kontrolü yapayım). Varsayılan pakette yok.

---

## 8️⃣ CANLI SİSTEM PANELİ (LivePanel modu) — "reklam gibi şaşalı giriş" 🎨

İstediğin şey: sunucu girişinde canlı CPU/GPU/RAM/sıcaklık/çekirdek göstergesi → **yazdım, hazır.** `livepanel-mod/` klasöründe kaynak kod var. Derle (senin PC'nde, internetle):

```bash
cd livepanel-mod
gradle build        # JDK 21 + Gradle 8.6+ gerekir
# → build/libs/livepanel-1.0.0.jar → sunucunun mods/ klasörüne at
```

Ne gösterir (3 sn'de bir güncellenir):
- **MOTD** (sunucu listesi): gradyan `KITSUGI MC [CPU %] [RAM G]` + `[TPS] [GPU %] [x/y çekirdek]`
- **Action bar** (hotbar üstü): `TPS · MSPT · CPU · RAM · GPU · SICAKLIK · OYUNCU`
- **Sidebar skorboard** (sağ panel): TPS, MSPT, CPU% + çekirdek çubuğu `[████░░]`, RAM, GPU%, VRAM, CPU/GPU sıcaklık, oyuncu, uptime
- Komut: `/livepanel` ve `/livepanel reload`

Ayarlar: `config/livepanel.properties` (ilk çalıştırmada oluşur) — `intervalSeconds=3`, `sidebar/actionbar/motd/showGpu/showTemps/barSegments`.

> ℹ️ RX 550'de GPU busy % + VRAM, amdgpu sürücüsünün sysfs dosyalarından okunur (headless sunucuda da çalışır). MOTD API'si sürüme göre değişebilir, çalışmazsa actionbar+sidebar yine çalışır. Hazır alternatif: **TabTPS** (tab menüsü/bossbar'da TPS+RAM, NeoForge 1.21.1).

---

## 9️⃣ CLIENT TARAFI (oyuncuların bilgisayarı)

- Aynı NeoForge 1.21.1 kurulumu + `mods-client/` içeriği + `mods-server/` içeriği (client+server modları zaten içinde) → toplam `mods/` klasörü.
- Fabric modların (sinytra ile) otomatik çalışır — Connector + Forgified Fabric API jar'ları sunucu paketinde mevcut, client'a da aynen koy.
- Oculus yerine **Iris**, Xenon yerine **Sodium** geldi (client). Shader klasörünü (iris_shader_folder) Iris'te kullanırsın.

---

## 🗑️ KALDIRILAN MODLAR & ETKİLERİ (önceden bil)

| Mod | Etkisi | Öneri |
|---|---|---|
| MoreArmor | Zırh eşyaları kaybolur | Migrasyondan önce zırhları toplat; alternatif mod önerebilirim |
| LevelHearts | Oyuncular ekstra canı kaybeder | Migrasyondan önce can değerlerini kaydet; alternatif: Heart Canisters vb. |
| FantasyFurniture | Mobilya blokları kaybolur | Handcrafted zaten var; başka mobilya modu önerebilirim |
| More Mob Variants | Sadece görsel varyantlar | Kayıp yok, çıkarıldı |
| Spawners+ | Yükseltilmiş spawner'lar vanillaya dönebilir | 1.21.1 portu aranıyor; portu yoksa çıkarılacak |
| Legendary Item | Özel eşyalar kaybolur | Migrasyondan önce eşyaları toplat |
| Vote2023 / AudioImp / GPUMemLeakFix / BetterWorldLoading / Catalogue | Önemsiz client modları | Kayıp yok |
| Oculus/Xenon+Sodium eklentileri | Client render modları | Iris + Sodium ile değiştirildi |
| Better Compatibility Checker, BHMenu | Client | Kayıp yok |

> Kural: **Migrasyon günü** oyunculara "kritik eşyalarını (MoreArmor zırhı, LevelHearts canı, LegendaryItem, FantasyFurniture) sandıklara koymasın / envanterde tutsun" duyurusu yap — çünkü kaybolan eşyalar envanterdeyse de silinir; planlı davranırsak sıfıra yakın kayıp.

---

## ❓ SSS

**"Yeni içerikler (Trial Chambers, Mace...) eski dünyamda olacak mı?"**
Sadece **yeni keşfedilen chunk'larda** üretilir. Eski bölgeler aynen kalır.

**"Eski chunk'lar bozulur mu?"** Hayır — blok blok korunur. Modların yeni sürümüyle oluşan yeni chunk'lar sınırdan itibaren yeni generator ile üretilir (ufak görsel fark normal, Epic Terrain'de en belirgin).

**"Config'lerimi kaybeder miyim?"** Evet, bilinçli olarak: eski config = sürüm uyumsuzluğu. Yeni config üretilir, ayarlarını yeniden yaparsın.

**"VRAM'i (4GB) sunucu RAM'i niyetine kullanabilir miyiz?"**
Hayır — JVM heap'i yalnızca sistem RAM'inde çalışır; VRAM, GPU'nun kendi belleğidir ve CPU/JVM onu adresleyemez (GPU belleği CPU ile cache-coherent değildir; HSA/ROCm unified memory bile genel program belleği sağlamaz). Ama:
- C2ME-OCL çalışırken **noise hesabı zaten VRAM'de yapılır** — yani VRAM "sunucu işi" için zaten kullanılıyor (4GB bu iş için fazlasıyla yeterli).
- Gerçek "RAM niyetine" yöntem: **NVMe swap**. 16GB sistemde heap taşarsa çökme yerine yavaşlama sağlar:
  ```bash
  sudo fallocate -l 16G /swapfile && sudo chmod 600 /swapfile
  sudo mkswap /swapfile && sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  free -h   # Swap: 16G
  ```
- Paketteki ModernFix + FerriteCore zaten heap kullanımını azaltır; `-Xmx12G` 16GB sistem için doğru değerdir (14G yapma — JVM üstü + OS için boşluk gerekir).

**"Sunucudaki GPU, oyuncuların daha fazla chunk açmasını sağlar mı?"**
Hayır — render distance (oyuncunun ekranındaki chunk sayısı) **oyuncunun PC'sindeki GPU** ile çizilir; sunucudaki RX 550 bunu etkilemez. Sunucu GPU'su sadece **chunk üretimini** (yeni chunk'ların oluşmasını) hızlandırır — oyuncular keşfe çıktığında yeni chunk daha hızlı hazır olur, teleport daha akıcı olur.

**"Chunk yükleme (loading) GPU ile hızlanır mı?"**
Hayır — diskten okuma/yazma CPU + disk işidir; C2ME zaten bunu paralel yapıyor (paralel I/O). GPU sadece **üretimdeki noise/biome** kısmını alır. Üç işi ayırt et: **ÜRETİM = CPU+GPU birlikte** ✅ · **YÜKLEME = CPU (paralel I/O)** · **RENDER = oyuncunun GPU'su**.

**"Sunucu headless (kod tabanlı) — GUI gerekir mi?"** Hayır. `run.sh nogui` ile tamamen komut satırından yönetilir. `screen`/`tmux` ile arka planda çalıştırabilirsin:
```bash
tmux new -s mc -d "./run.sh nogui"
tmux attach -t mc
```

---

## 🔁 GERİ DÖNÜŞ (rollback)

1. Sunucuyu kapat.
2. Eski 1.20.1 dizinini aç (jar + mods + world yedeği orada duruyor).
3. `./run.sh nogui` — 1.20.1'e geri döndün. 1.21.1'de oluşan yeni chunk'lar eski sürümde **yüklenmez/bozuk görünür** — bu yüzden geri dönüş ancak test aşamasında mantıklı; dünya artık 1.21.1'de ilerlerse eski sürüme dönüş önerilmez.

**İyi şanslar! İndirmede çıkan sorunlu mod adlarını bana ilet, tek tek çözelim. 🚀**
