# LivePanel — Canlı Sistem Paneli Modu (MC 1.21.1 NeoForge)

Sunucu girişinde ve oyun içinde canlı sistem metrikleri:
**TPS, MSPT, CPU %, çekirdek kullanımı (per-core + çubuk), RAM, GPU busy %, VRAM, CPU/GPU sıcaklığı, oyuncu sayısı, uptime** — varsayılan **3 saniyede bir** güncellenir.

## Nerede gösterir? (hangi yer = hangi ayar)

| Yer | Ayar (config/livepanel.properties) | Açıklama |
|---|---|---|
| **Sunucu listesi (MOTD)** — multiplayer ekranındaki "reklam gibi" giriş | `motd=true` | `server.setMotd()` ile güncellenir; her ping'de taze |
| **Oyun içi actionbar** (hotbar üstü) | `actionbar=true` | 3 sn'de bir |
| **Oyun içi sidebar skorboard** (sağ panel) | `sidebar=true` | 3 sn'de bir |

> Yalnızca tek yerde görünmesini istersen: diğerlerini `false` yap. Örn. sadece sunucu listesinde:
> ```properties
> motd=true
> actionbar=false
> sidebar=false
> ```
> Not: 1. resimde gördüğün yerde çıkıyorsa ve 2. resimdeki yerde (muhtemelen sunucu listesi/MOTD)
> çıkmıyorsa sebep eski refleksiyon yöntemiydi — yeni sürüm `server.setMotd()` kullanır,
> sunucu listesinde kesin çalışır. Güncellemek için `gradle build` sonrası jar'ı yeniden deploy et.

## Derleme (senin PC'nde — internet gerekir)

```bash
# 1) JDK 21 kur (1.21.1 zorunlu):
sudo apt install -y openjdk-21-jdk

# 2) Gradle 8.6+ kur (Ubuntu 24.04: 8.7 gelir):
sudo apt install -y gradle
# (yoksa https://gradle.org/releases/ adresinden binary indir, PATH'e ekle)

# 3) Bu klasörde:
cd livepanel-mod
gradle build

# 4) Çıktı:
#    build/libs/livepanel-1.0.0.jar  →  sunucunun mods/ klasörüne kopyala
```

> 💡 Gradle yoksa: NeoForge MDK 1.21.1'i (neoforged.net) indirip onun `gradlew`'ini kullanabilirsin:
> MDK'nın `src` klasörü yerine bu projenin `src/main` içeriğini kopyala, `build.gradle` yerine buradakini kullan, `./gradlew build`.

## İlk çalıştırma

Sunucu açılınca `config/livepanel.properties` oluşur. Ayarlar:

```properties
intervalSeconds=3     # güncelleme aralığı (1-5 önerilir)
sidebar=true          # sağ panel
actionbar=true        # hotbar üstü
motd=true             # sunucu listesi
showGpu=true          # GPU metrikleri (RX 550'de amdgpu sysfs okur)
showTemps=true        # sıcaklıklar (coretemp + amdgpu)
barSegments=6         # çekirdek çubuğu segmenti
```

## Notlar

- **MOTD kısmı:** Bazı NeoForge sürümlerinde `setDescription` API'si değişebilir — çalışmazsa zararsızca atlanır; actionbar + sidebar her sürümde çalışır.
- **Sıcaklık:** Intel `coretemp` + AMD `amdgpu` hwmon sysfs'inden okunur; sürücü yoksa satır görünmez.
- **GPU busy %:** amdgpu sürücüsü `gpu_busy_percent` verir; headless sunucuda da çalışır. Yoksa `-` gösterilir.
- **Derleme hatası olursa:** hata mesajını bana yapıştır — tek tek düzeltirim (API sürüm farkları olabilir).
- **Hazır alternatif:** "TabTPS" modu (NeoForge 1.21.1) tab menüsü + bossbar'da TPS/RAM gösterir ama CPU/GPU/sıcaklık yok. İkisini birlikte de kullanabilirsin.

## Kaldırma

Jar'ı `mods/` klasöründen sil → tüm panel kaybolur (skorboard objective'si bir sonraki restart'ta temizlenir).
