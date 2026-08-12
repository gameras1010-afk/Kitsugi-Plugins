# Görev Listesi — Uzaktan Yönetim Kurulumu

> Bu, `UZAKTAN-YONETIM.md`'nin uygulama dosyası. Orada **neden**, burada
> **nasıl** var. Sırayla git, her adımı işaretle.
>
> **Toplam süre:** ~2.5 saat (alışverişi saymazsak ~90 dakika)

---

## 🛒 AŞAMA 0 — Alışveriş

- [ ] **Akıllı priz al**

| Model | Tahmini fiyat | Not |
|---|---|---|
| TP-Link Tapo P100 | ~200-300 TL | Yeterli |
| TP-Link Tapo P110 | ~350-450 TL | Güç ölçer, PC açık mı anlarsın |
| Shelly Plug S | ~500-700 TL | Yerel API, bulut şart değil |

> **P110'u öneririm.** Güç ölçümü sayesinde arkadaşın uygulamadan
> "45 W çekiyor" görüp PC'nin gerçekten açık olduğunu anlar.

- [ ] Prizi **doğrudan duvara** tak (çoklu priz üzerinden değil)
- [ ] PC'nin fişini akıllı prize tak
- [ ] Telefona uygulamayı kur, prizi tanıt, adını **"MC Sunucu"** yap

---

## 🔧 AŞAMA 1 — BIOS (MSI B365M PRO-VH)

Süre: ~10 dk. PC'yi aç, **DEL**'e basılı tut, **F7** ile Advanced Mode.

- [ ] **1.1** `Settings → Advanced → Power Management Setup`
      → **ErP Ready** → `Disabled`

> Bu ayar açıkken anakart kapalıyken standby gücünü keser.
> Hem WoL hem otomatik açılma ölür. Kartında `EuP 2013` yazıyorsa o da aynı şey.

- [ ] **1.2** Aynı menü → **Restore after AC Power Loss** → `Power On`

> 🚨 **`Last State` SEÇME.** Bu adımın tamamı buna bağlı.
> Last State = "kapalıydıysa kapalı kalsın" → priz açılınca PC açılmaz.

- [ ] **1.3** `Settings → Advanced → Wake Up Event Setup`
      → **Resume By PCI-E Device** → `Enabled`
- [ ] **1.4** Aynı menüde **Resume By Onboard LAN** varsa → `Enabled`
- [ ] **1.5** `Settings → Advanced → Integrated Peripherals`
      → **Onboard LAN Controller** → `Enabled`
- [ ] **1.6** **F10** → Yes → kaydet ve çık

### Doğrulama
- [ ] PC normal açıldı mı? → Evet ise devam.

---

## 💾 AŞAMA 2 — Ubuntu Boot Sağlamlaştırma

Süre: ~10 dk. **Bu aşamayı atlarsan er ya da geç PC uzaktan açılmaz.**

- [ ] **2.1** GRUB'u düzenle

```bash
sudo cp /etc/default/grub /etc/default/grub.bak
sudo nano /etc/default/grub
```

Şu satırları ekle/düzelt:
```bash
GRUB_TIMEOUT=3
GRUB_TIMEOUT_STYLE=menu
GRUB_RECORDFAIL_TIMEOUT=3
```

- [ ] **2.2** Uygula
```bash
sudo update-grub
```

- [ ] **2.3** Doğrula (çıktıda `recordfail` timeout'u 3 olmalı)
```bash
grep -A3 'recordfail' /boot/grub/grub.cfg | head -20
```

- [ ] **2.4** fsck otomatik onarım
```bash
echo 'FSCKFIX=yes' | sudo tee -a /etc/default/rcS
```

- [ ] **2.5** Uykuyu tamamen kapat
```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

- [ ] **2.6** Swap'i baskıla (JVM heap swap'e düşerse TPS çöker)
```bash
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-mc.conf
sudo sysctl --system
cat /proc/sys/vm/swappiness    # 10 demeli
```

- [ ] **2.7** Tailscale boot'ta açılsın
```bash
sudo systemctl enable tailscaled
systemctl is-enabled tailscaled    # "enabled" demeli
```

---

## 🔌 AŞAMA 3 — GÜÇ TESTİ (KRİTİK — ATLAMA)

Süre: ~10 dk. Crafty kurmadan önce bunu geç.

- [ ] **3.1** Not al: MC PC'sinin Tailscale IP'si
```bash
tailscale ip -4
```
IP: `___________________`

- [ ] **3.2** Düzgün kapat
```bash
sudo poweroff
```

- [ ] **3.3** Telefondan akıllı prizi **KAPAT**
- [ ] **3.4** **15 saniye** bekle (PSU kondansatörleri boşalsın)
- [ ] **3.5** Telefondan akıllı prizi **AÇ**
- [ ] **3.6** ⏱️ Kronometre başlat, PC kendiliğinden açılmalı

Açılma süresi: `_______ saniye`

- [ ] **3.7** Başka bir cihazdan (telefon mobil veriyle) Tailscale'den ping at
```bash
tailscale ping <yukarıdaki-ip>
```

### ❌ PC açılmadıysa

| Kontrol | Nasıl |
|---|---|
| BIOS `Last State` mi seçili? | Aşama 1.2'ye dön |
| `ErP Ready` hâlâ Enabled mı? | Aşama 1.1'e dön |
| Priz gerçekten açıldı mı? | Uygulamada durumu kontrol et, prize lamba tak dene |
| BIOS ayarı kaydedildi mi? | CMOS pili bitmişse ayarlar uçar — pili değiştir |

### ⚠️ PC açıldı ama Ubuntu gelmediyse
Monitör tak, GRUB menüsünde bekliyordur → Aşama 2.1'i tekrar yap.

> **Bu test geçmeden ilerleme.** Geri kalan her şey PC'nin açılabilmesine bağlı.

---

## 🎮 AŞAMA 4 — Crafty Controller Kurulumu

Süre: ~20 dk (indirme dahil)

- [ ] **4.1** Mevcut sunucunun yolunu not al
```bash
# start.sh nerede
realpath ~/Kitsugi-Plugins/minecraft-server-optimizasyon/start.sh
# veya gerçek sunucu klasörün
```
Yol: `___________________________________`

- [ ] **4.2** ÖNCE YEDEK AL
```bash
cd <sunucu-klasörünün-üstü>
tar -czf ~/mc-yedek-$(date +%Y%m%d).tar.gz <sunucu-klasörü>/world*
ls -lh ~/mc-yedek-*.tar.gz
```

- [ ] **4.3** Çalışan sunucuyu durdur (varsa)
```bash
# start.sh çalışıyorsa terminalinde: stop  yaz, sonra Ctrl+C
ps aux | grep -i "[j]ava.*neoforge"   # boş dönmeli
```

- [ ] **4.4** Crafty'yi kur
```bash
curl -L https://get.craftycontrol.com | sudo bash
```

- [ ] **4.5** Şifreyi al ve bir yere kaydet
```bash
sudo cat /var/opt/minecraft/crafty/crafty-4/app/config/default-creds.txt
```
Kullanıcı: `admin`   Şifre: `___________________`

- [ ] **4.6** Servis durumu
```bash
sudo systemctl status crafty --no-pager
sudo systemctl enable crafty
```

- [ ] **4.7** Panele gir: `https://<tailscale-ip>:8443`
      (sertifika uyarısını "Gelişmiş → Devam Et" ile geç)
- [ ] **4.8** Şifreyi değiştir: sağ üst → Profile → Change Password

---

## 📦 AŞAMA 5 — Sunucuyu Crafty'ye Aktarma

Süre: ~20 dk

- [ ] **5.1** Crafty hangi kullanıcı olarak çalışıyor
```bash
ps -o user= -C python3 | sort -u
# veya
systemctl show crafty -p User
```
Kullanıcı: `_______________` (genelde `crafty`)

- [ ] **5.2** Sunucu klasörünü ona ver

> 🚨 Bu adımı atlarsan Crafty sunucuyu başlatamaz veya config yazamaz.
> **Bu, Simple Voice Chat'te yaşadığın "klasör root'tu" sorununun aynısı.**

```bash
sudo chown -R crafty:crafty <SUNUCU_YOLU>
sudo chmod -R u+rwX <SUNUCU_YOLU>
ls -ld <SUNUCU_YOLU>          # crafty crafty görmeli
ls -ld <SUNUCU_YOLU>/world    # crafty crafty görmeli
```

- [ ] **5.3** NeoForge sürümünü öğren (bir sonraki adımda lazım)
```bash
ls <SUNUCU_YOLU>/libraries/net/neoforged/neoforge/
```
Sürüm: `21.1.___________`

- [ ] **5.4** Crafty panelinde: **Servers → Create New Server → Import Server**
- [ ] **5.5** Formu doldur:

| Alan | Değer |
|---|---|
| Server Name | `Kitsugi` (ne istersen) |
| Server Path | Adım 5.1'deki tam yol |
| Import Type | `Import Server (from folder)` |
| Server Type | `Forge / NeoForge` |
| Min/Max RAM | `8G` / `8G` |

- [ ] **5.6** İçe aktarma bitince **Server → Config → Server Execution Command**
      alanına şunu yapıştır (tek satır):

```
java -Xms8G -Xmx8G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:ParallelGCThreads=4 -XX:ConcGCThreads=1 -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -XX:ReservedCodeCacheSize=400M -XX:-DontCompileHugeMethods -XX:+UseVectorCmov -XX:+UseFastUnorderedTimeStamps -XX:AllocatePrefetchStyle=3 --add-modules=jdk.incubator.vector -Dchunky.maxWorkingCount=768 -Dio.netty.allocator.maxOrder=9 -Dio.netty.leakDetection.level=disabled -Dfile.encoding=UTF-8 -Djava.awt.headless=true -Dlog4j2.formatMsgNoLookups=true @libraries/net/neoforged/neoforge/21.1.XXX/unix_args.txt nogui
```

- [ ] **5.7** 🚨 `21.1.XXX` kısmını Adım 5.3'teki gerçek sürümle **değiştir**
- [ ] **5.8** Kaydet → **START** → Logs sekmesinden izle
- [ ] **5.9** `Done (XX.XXXs)! For help, type "help"` satırını gördün mü?
- [ ] **5.10** Minecraft'tan bağlan, dünyanın geldiğini ve **yapılarının
      yerinde olduğunu** doğrula

### ⚠️ Açılmazsa
```bash
# Crafty'nin kendi logu
sudo tail -50 /var/opt/minecraft/crafty/crafty-4/logs/commander.log

# Sunucu logu
tail -50 <SUNUCU_YOLU>/logs/latest.log
```
En sık sebep: izinler (5.2) veya yanlış NeoForge sürümü (5.7).

- [ ] **5.11** Crafty ayarları:
  - **Crash Detection** ✅ (start.sh'taki `while true` karşılığı)
  - **Auto Start** — istersen ✅ (PC açılınca sunucu da açılsın)

- [ ] **5.12** 🚨 Artık `start.sh`'ı **elle çalıştırma.** İki process aynı
      dünyayı açarsa dünyayı bozarsın. Karışıklık olmasın diye:
```bash
mv <SUNUCU_YOLU>/start.sh <SUNUCU_YOLU>/start.sh.KULLANMA
```

---

## 🔐 AŞAMA 6 — Tailscale Sağlamlaştırma

Süre: ~20 dk

### 6A — Key expiry'yi kapat (180 gün sonra kilitlenmemek için)

- [ ] **6.1** Admin konsolu → https://login.tailscale.com/admin/acls
- [ ] **6.2** Policy'ye `tagOwners` ekle:
```json
"tagOwners": {
  "tag:mcserver": ["autogroup:admin"]
}
```
- [ ] **6.3** Save
- [ ] **6.4** Sunucuda etiketi uygula (yeniden giriş isteyecek, normal):
```bash
sudo tailscale up --advertise-tags=tag:mcserver
```
- [ ] **6.5** Doğrula: Admin → Machines → sunucu satırında
      **`Expiry disabled`** yazmalı

> Bu adımı atlarsan 180 gün sonra sunucu tailnet'ten düşer ve
> **uzaktan düzeltemezsin** — makinenin başına gitmen gerekir.

### 6B — Erişimi daralt

- [ ] **6.6** Admin → Access Controls → tam policy'yi yaz:

```json
{
  "tagOwners": {
    "tag:mcserver": ["autogroup:admin"]
  },

  "groups": {
    "group:admins": ["SENIN_MAILIN"]
  },

  "grants": [
    {
      "src": ["group:admins"],
      "dst": ["*"],
      "ip":  ["*"]
    },
    {
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "ip":  ["*"]
    },
    {
      "src": ["autogroup:shared"],
      "dst": ["tag:mcserver"],
      "ip":  ["tcp:25565", "udp:24454", "tcp:8443"]
    }
  ],

  "ssh": [
    {
      "action": "check",
      "src":    ["group:admins"],
      "dst":    ["tag:mcserver"],
      "users":  ["autogroup:nonroot", "root"]
    }
  ]
}
```

- [ ] **6.7** `SENIN_MAILIN` yerine gerçek Tailscale hesabın
- [ ] **6.8** Save → hata verirse Tailscale ekranda satır numarasını söyler

> 🚨 `"src": ["autogroup:member"], "dst": ["autogroup:self"]` satırını
> silme — yoksa **kendi cihazlarına erişimini kaybedersin.**

> 🚨 `udp:24454` = Simple Voice Chat. Silersen ses çalışmaz.

- [ ] **6.9** Portları doğrula
```bash
sudo ss -tulpn | grep -E '25565|24454|8443'
```

### 6C — Arkadaşları davet et

- [ ] **6.10** Admin → Machines → sunucu → `⋯` → **Share...**
- [ ] **6.11** Her arkadaşın e-postasını gir, davet linkini gönder

> Share, arkadaşını tailnet'e **üye yapmaz** — sadece bu makineye erişir.
> `autogroup:shared` grubuna düşerler, ACL'de zaten tanımladın.

### 6D — DERP kontrolü (ses kalitesi)

- [ ] **6.12**
```bash
tailscale status
```
`relay "..."` görüyorsan → `direct` olması lazım:
```bash
sudo ufw allow 41641/udp
tailscale netcheck
```

---

## 👥 AŞAMA 7 — Arkadaşlara Crafty Hesabı

Süre: ~10 dk

- [ ] **7.1** Crafty → **Panel Config → Roles → Add Role**
      - Ad: `Oyuncu`
      - Sunucu: Kitsugi
      - İzinler:

| İzin | Ver? |
|---|---|
| Commands (Start/Stop/Restart) | ✅ |
| Terminal (konsol görme) | ✅ |
| Logs | ✅ |
| **Files** | ❌ **VERME** — dosyaları silebilir |
| **Config** | ❌ **VERME** — başlatma komutunu bozabilir |
| **Backup** | ❌ **VERME** — yedekleri silebilir |
| **Players** | ⚠️ İstersen (ban/kick yetkisi) |
| **Schedules** | ❌ |

- [ ] **7.2** Her arkadaş için: **Panel Config → Users → Add User**
      → rol `Oyuncu`, `Superuser` ❌

| Arkadaş | Kullanıcı adı | Şifre verildi |
|---|---|---|
| | | ☐ |
| | | ☐ |
| | | ☐ |

- [ ] **7.3** Kendi hesabınla değil, **arkadaşın hesabıyla** giriş yapıp
      Files sekmesinin gerçekten görünmediğini doğrula

---

## 🛡️ AŞAMA 8 — Güvenlik Duvarı

Süre: ~5 dk

> ⚠️ SSH ile bağlıysan sıralamaya dikkat — `enable` en sonda.

- [ ] **8.1**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow in on tailscale0
sudo ufw allow 41641/udp
sudo ufw allow from 192.168.0.0/16 to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

- [ ] **8.2** 🚨 `sudo ufw allow 25565` **YAPMA.** Tailscale kullanıyorsun,
      portu internete açmanın anlamı yok — sadece bot taramalarını davet edersin.

- [ ] **8.3** UFW açıkken Tailscale hâlâ çalışıyor mu:
```bash
tailscale status
```

---

## 💾 AŞAMA 9 — Yedekleme

- [ ] **9.1** Crafty → **Server → Backups → Schedule**
      - Sıklık: Günlük, 04:00
      - Saklanacak kopya: 3
      - `Shutdown server during backup`: ❌ (küçük dünyada gerek yok)

- [ ] **9.2** Elle bir yedek al, gerçekten oluştuğunu gör
```bash
ls -lh /var/opt/minecraft/crafty/crafty-4/backups/
```

- [ ] **9.3** ⚠️ FTB Backups 2 modun varsa **birini kapat.** İki yedekleyici
      aynı anda dünya dosyalarını okursa yedek bozuk çıkabilir.

- [ ] **9.4** Yedekleri ara ara dışarı kopyala (aynı diskte durması yedek değildir)
```bash
rsync -av /var/opt/minecraft/crafty/crafty-4/backups/ /mnt/harici/mc-yedek/
```

---

## ✅ AŞAMA 10 — UÇTAN UCA TEST

Süre: ~20 dk. **Bu aşama bütün işin sınavı.**

> Testi **mobil veriyle**, ev Wi-Fi'sinden çıkmış hâlde yap. Yoksa
> yerel ağdan çalışıyor olabilir ve sen bunu fark etmezsin.

- [ ] **10.1** Sunucuyu düzgün kapat: Crafty → STOP
- [ ] **10.2** PC'yi kapat: `sudo poweroff`
- [ ] **10.3** Akıllı prizi kapat
- [ ] **10.4** Telefonda **Wi-Fi'yi kapat**, mobil veriye geç
- [ ] **10.5** Akıllı priz uygulamasından prizi **AÇ**
- [ ] **10.6** ⏱️ 3 dakika bekle
- [ ] **10.7** Telefonda Tailscale açık → tarayıcıdan `https://mcserver:8443`
- [ ] **10.8** Panel açıldı mı? ☐
- [ ] **10.9** **START** → sunucu ayağa kalktı mı? ☐
- [ ] **10.10** Minecraft'tan bağlan ☐
- [ ] **10.11** Ses çalışıyor mu (Simple Voice Chat) ☐
- [ ] **10.12** Bir arkadaşına aynı şeyi **kendi hesabıyla** yaptır ☐

### Toplam süre ölçümü

| Aşama | Süre |
|---|---|
| Priz açıldı → PC boot bitti | `______ sn` |
| PC boot → Crafty paneli açıldı | `______ sn` |
| START → `Done!` | `______ sn` |
| **TOPLAM** | `______` |

Beklenen toplam: **3-6 dakika** (mod sayısına göre)

---

## 📱 AŞAMA 11 — Arkadaşlara Teslim

- [ ] **11.1** `UZAKTAN-YONETIM.md` → Bölüm 7'yi kopyala, WhatsApp'tan at
- [ ] **11.2** Şunları ilet:
  - Tailscale davet linki
  - Crafty kullanıcı adı + şifre
  - Panel adresi: `https://mcserver:8443`
  - MC adresi: `mcserver:25565`
  - Akıllı priz uygulaması erişimi (Tapo → Home → Manage Members)
- [ ] **11.3** Birine baştan sona **bir kere yaptır**, izle. Takıldığı yer
      senin dokümanının eksik olduğu yerdir.

---

## 🔁 AŞAMA 12 — Periyodik Bakım

| Ne zaman | Ne yap |
|---|---|
| Haftalık | `tailscale status` → hepsi `direct` mi |
| Aylık | Yedeklerden birini gerçekten geri yükleyip dene |
| Aylık | `sudo apt update && sudo apt upgrade` |
| 6 ayda bir | Admin → Machines → hâlâ `Expiry disabled` mı |
| Elektrik kesintisi sonrası | PC kendi geldi mi, gelmediyse Aşama 1-2'yi denetle |

---

## 📊 İLERLEME

```
☐ Aşama 0  — Alışveriş
☐ Aşama 1  — BIOS
☐ Aşama 2  — Ubuntu boot
☐ Aşama 3  — GÜÇ TESTİ        ← burayı geçmeden ilerleme
☐ Aşama 4  — Crafty kurulum
☐ Aşama 5  — Sunucu aktarımı
☐ Aşama 6  — Tailscale
☐ Aşama 7  — Kullanıcılar
☐ Aşama 8  — Firewall
☐ Aşama 9  — Yedek
☐ Aşama 10 — UÇTAN UCA TEST   ← burayı geçince iş bitti
☐ Aşama 11 — Teslim
☐ Aşama 12 — Bakım
```

---

## En Sık Yapılan 5 Hata

1. **BIOS'ta `Last State` seçmek** — priz açılır, PC açılmaz
2. **GRUB recordfail'i atlamak** — PC açılır, Ubuntu gelmez
3. **Klasör izinlerini vermemek** — Crafty sunucuyu başlatamaz
4. **`start.sh` + Crafty'yi birlikte kullanmak** — dünya bozulur
5. **Tailscale key expiry'yi kapatmamak** — 180 gün sonra her şey durur

Detaylı sorun giderme: `UZAKTAN-YONETIM.md` → Bölüm 8
