# Uzaktan Yönetim — Arkadaşların PC'yi Açsın, Sunucuyu Başlatsın

> **Hedef:** Sen evde olmasan bile, arkadaşların kendi bilgisayarlarından
> Tailscale üzerinden (1) yedek MC PC'sini **açabilsin**, (2) Minecraft
> sunucusunu **başlatabilsin**.
>
> **Şart:** Ev internete bağlı ve elektrik var.
>
> **Donanım:** i5-9400F / 16 GB / KIOXIA NVMe / MSI B365M PRO-VH / Ubuntu 24.04.4

---

## ⚠️ ÖNCE ŞUNU ANLA — Buradaki Tek Gerçek Problem

Senin isteğinin **%90'ı kolay**, **%10'u zor.** Zor olan kısım şu:

> **PC kapalıyken Tailscale de kapalıdır.**

Tailscale bir yazılımdır. PC kapandığında o da kapanır. Kapalı bir PC'ye
Tailscale üzerinden hiçbir şey gönderemezsin — çünkü orada dinleyen kimse yok.

Ve dahası, Tailscale'in resmî blogundan:

> *"Tailscale can't send WoL packets (sometimes called 'Magic Packets') over
> a Layer 2 connection, even if you have enabled subnet routing and it feels
> like you're on your local network."*
>
> — tailscale.com/blog/wake-on-lan-tailscale-upsnap

**Yani:** Tailscale Layer 3 (IP) çalışır. Wake-on-LAN paketi Layer 2 (MAC)
çalışır. Tailscale WoL paketi **gönderemez.** Bu bir bug değil, mimari.

### Bunun 3 çözümü var. Üçünü de anlatacağım, sonra hangisini seçeceğini söyleyeceğim.

| Yol | Ne gerekir | Maliyet | Güvenilirlik |
|---|---|---|---|
| **A. Akıllı priz** | Wi-Fi akıllı priz + BIOS ayarı | ~150-400 TL | ⭐⭐⭐⭐⭐ |
| **B. Aracı cihaz (WoL)** | Sürekli açık 2. cihaz (Pi/eski telefon) | 0-1500 TL | ⭐⭐⭐ |
| **C. PC'yi hiç kapatma** | Hiçbir şey | ~250 TL/ay elektrik | ⭐⭐⭐⭐ |

---

# BÖLÜM 1 — MİMARİ (Ne kuracağız)

```
   ARKADAŞIN TELEFONU/PC'Sİ
            │
            │  Tailscale (WireGuard, şifreli)
            │
   ┌────────┴────────────────────────────────┐
   │                                          │
   ▼                                          ▼
 [1] PC KAPALI ise                    [2] PC AÇIK ise
     Akıllı priz uygulaması               Tarayıcı →
     → prizi aç                           http://mcserver:8443
     → BIOS "AC Power On"                 (Crafty Controller)
     → PC boot                            → START butonu
     → Ubuntu açılır                      → Sunucu ayakta
     → Tailscale otomatik bağlanır
     → Crafty otomatik başlar
```

**Kilit fikir:** İki ayrı katman var ve bunları karıştırma.

- **Katman 1 — Gücü verme (PC'yi açma):** Tailscale'in DIŞINDA olmak zorunda.
- **Katman 2 — Sunucuyu başlatma:** Tailscale'in İÇİNDE, güvenli.

---

# BÖLÜM 2 — PC'Yİ UZAKTAN AÇMA

## 🥇 YOL A — Akıllı Priz (ÖNERİLEN)

Bu yolun mantığı: PC'yi elektrikten kesip tekrar veriyorsun, BIOS da
"elektrik gelince otomatik aç" diye ayarlı olduğu için PC kendiliğinden
açılıyor.

### Neden bu en iyi yol

- Tailscale'e, aracı cihaza, hiçbir şeye bağımlı değil
- Priz kendi Wi-Fi'siyle üreticinin bulutuna bağlı — PC kapalıyken bile çalışır
- **Donmuş/kilitlenmiş PC'yi de kurtarır** (WoL bunu yapamaz)
- Arkadaşına priz uygulamasında "misafir" yetkisi verebilirsin

### Ne alacaksın

| Model | Not |
|---|---|
| **TP-Link Tapo P100 / P110** | En yaygın, Türkiye'de kolay bulunur. P110 güç ölçümü de yapar |
| **Shelly Plug S** | Yerel API'si var (bulut olmadan da çalışır), ileri seviye |
| Herhangi bir Tuya/Smart Life prizi | Ucuz, çalışır ama uygulaması reklamlı |

> **Önemli:** PC'nin çektiği gücü kontrol et. i5-9400F + RX 550 sistemi
> yükte ~150-200 W çeker. 10 A / 2300 W'lık standart bir akıllı priz fazlasıyla
> yeter. Ama **çoklu priz üzerinden değil, doğrudan duvara** tak.

### ADIM A1 — BIOS Ayarları (MSI B365M PRO-VH)

PC'yi aç, hemen **DEL** tuşuna basılı tut. BIOS'a girince **F7** ile
Advanced Mode'a geç.

MSI'ın resmî dokümanı (msi.com/support/technical_details/MB_Wake_On_LAN)
ve MSI FAQ mb-503'e göre:

#### 1. ErP Ready'yi kapat (BU KRİTİK)

```
Settings → Advanced → Power Management Setup → ErP Ready → [Disabled]
```

> **Neden:** ErP, AB'nin enerji direktifi. PC kapalıyken anakartın
> 0.5 W'tan az çekmesini zorlar. Bunu yapmak için anakart **standby
> gücünü keser** — yani hem WoL hem "elektrik gelince aç" özelliği ölür.
> Bazı MSI kartlarında `EuP 2013` yazar, o da aynı şey, onu da kapat.

#### 2. Elektrik gelince otomatik açılmayı aç

```
Settings → Advanced → Power Management Setup
  → Restore after AC Power Loss → [Power On]
```

> ⚠️ **Buradaki en yaygın hata:** Bu ayarın 3 seçeneği olur:
> `Power Off` / `Power On` / `Last State`.
>
> **`Last State` SEÇME.** "Last State" = "elektrik kesilmeden önce ne
> haldeyse ona dön". PC'yi düzgün kapattıysan son hâli "kapalı"dır,
> priz açılınca **açılmaz.** Bu tam olarak serverfault.com/questions/214354
> ve r/sysadmin'de insanların takıldığı tuzak.
>
> **Mutlaka `Power On` seç.**

#### 3. (Bonus) Wake-on-LAN'ı da aç — Yol B için lazım olacak

```
Settings → Advanced → Wake Up Event Setup
  → Resume By PCI-E Device → [Enabled]
```

MSI FAQ mb-2287'ye göre bazı kartlarda ayrıca:
```
  → Resume By Onboard LAN → [Enabled]
```

```
Settings → Advanced → Integrated Peripherals
  → Onboard LAN Controller → [Enabled]
```

#### 4. Kaydet

**F10** → Yes → PC yeniden başlar.

### ADIM A2 — Ubuntu Tarafı: GRUB Tuzağı (ÇOK ÖNEMLİ)

Bu adımı atlarsan **er ya da geç PC açılmaz ve sen sebebini bulamazsın.**

Ubuntu'da `recordfail` diye bir mekanizma var: eğer bir önceki açılış
düzgün tamamlanmadıysa (elektrik kesintisi, priz kapatma vs.), GRUB
menüsünde durup **süresiz olarak klavye girdisi bekler.**

Launchpad Bug #1443735 bunu aynen böyle tanımlıyor:

> *"On a headless server system, a user who does not have easy access to
> the console may find the system fails to come up after a power cut
> because the boot is blocked on a console menu prompt that does not time out."*

Yani: prizi kapatıp açtın → PC açıldı → **GRUB menüsünde takıldı** →
Ubuntu hiç başlamadı → Tailscale yok → arkadaşın "abi olmadı" diyor.
Sen de gidip monitör takmak zorunda kalıyorsun. **Kesinlikle yaşarsın.**

Çözüm:

```bash
sudo nano /etc/default/grub
```

Şu satırları ekle veya düzelt:

```bash
GRUB_TIMEOUT=3
GRUB_RECORDFAIL_TIMEOUT=3
GRUB_TIMEOUT_STYLE=menu
```

Kaydet (Ctrl+O, Enter, Ctrl+X), sonra:

```bash
sudo update-grub
```

> `GRUB_RECORDFAIL_TIMEOUT=3` → "önceki açılış bozuksa bile 3 saniye
> bekle, sonra normal aç." Bu tek satır seni büyük dertten kurtarır.

### ADIM A3 — Diski fsck'te takılmaktan kur

Ani güç kesintisinden sonra ext4 bazen "manual fsck" isteyip yine
konsolda bekleyebilir. Bunu da otomatikleştir:

```bash
sudo nano /etc/default/rcS
```

İçine (yoksa oluştur):
```
FSCKFIX=yes
```

### ADIM A4 — Test Et (Bunu ATLAMA)

```bash
# 1. Düzgün kapat
sudo poweroff

# 2. Akıllı prizi telefondan KAPAT
# 3. 15 saniye bekle (PSU kondansatörleri boşalsın)
# 4. Akıllı prizi telefondan AÇ
# 5. PC kendiliğinden açılmalı
```

Açılmıyorsa: BIOS'ta `Last State` seçili kalmıştır ya da `ErP Ready`
hâlâ `Enabled`'dır. Geri dön ve kontrol et.

---

## 🥈 YOL B — Aracı Cihaz + Wake-on-LAN

Akıllı priz almak istemiyorsan bu var. Ama **sürekli açık kalacak ikinci
bir cihaza** ihtiyacın var: Raspberry Pi, eski bir telefon (Termux ile),
mini PC, ya da Tailscale destekleyen bir router.

### Neden ikinci cihaz şart

r/Tailscale'de bu soru sürekli soruluyor, cevap hep aynı:

> *"WOL directly over Wireguard/tailscale isn't supported. You can use
> tailscale to access a system that is always online on your local network
> then do WOL from that."*

Aracı cihaz Tailscale'de durur (hep açık), sen ona Tailscale'den bağlanırsın,
o da **yerel ağdan** MC PC'sine magic packet atar. Layer 2 sorunu böyle çözülür.

### Kurulum (Raspberry Pi / eski Linux cihaz)

```bash
# Aracı cihazda:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo apt install -y wakeonlan
```

MC PC'sinin MAC adresini öğren (MC PC'sinde çalıştır):
```bash
ip link show | grep -A1 "state UP" | grep link/ether
```

Aracı cihazdan uyandırma:
```bash
wakeonlan AA:BB:CC:DD:EE:FF
# veya
wakeonlan -i 192.168.1.255 AA:BB:CC:DD:EE:FF
```

### Arkadaşların için web arayüzü: UpSnap

Arkadaşına SSH öğretmeyeceksin. UpSnap tarayıcıdan tek tıkla WoL atar:

```bash
docker run -d --name upsnap --restart unless-stopped \
  --network host \
  -v upsnap-data:/app/pb_data \
  ghcr.io/seriousm4x/upsnap:4
```

Sonra arkadaşın Tailscale'den `http://<aracı-cihaz>:8090` adresine girip
butona basar.

### Linux tarafında WoL'u kalıcı aç

Ubuntu'da NIC'in WoL ayarı reboot'ta sıfırlanabilir:

```bash
# Destekliyor mu bak
sudo ethtool enp3s0 | grep -i wake
# "Supports Wake-on: pumbg" ve "Wake-on: g" görmelisin
```

`Wake-on: d` (disabled) diyorsa kalıcı olarak aç:

```bash
sudo nano /etc/systemd/network/50-wired.link
```

```ini
[Match]
MACAddress=AA:BB:CC:DD:EE:FF

[Link]
NamePolicy=kernel database onboard slot path
MACAddressPolicy=persistent
WakeOnLan=magic
```

> ⚠️ Proxmox forumundaki deneyimlere göre `WakeOnLan=magic` dışında
> (`broadcast`, `unicast` vb.) değerler **PC'nin kapanır kapanmaz tekrar
> açılmasına** sebep olabiliyor. Sadece `magic` kullan.

### Yol B'nin dezavantajları — dürüst olalım

- ❌ İkinci bir cihaz sürekli açık kalacak (elektrik + arıza riski)
- ❌ **PC donarsa kurtaramazsın** (WoL kapalı PC'yi açar, donmuşu değil)
- ❌ WoL notoriously güvenilmez — "incredibly finicky" (r/MoonlightStreaming)
- ❌ Ubuntu'nun bazı sürümlerinde `shutdown` sonrası NIC gücü kesiliyor
- ✅ Ek donanım maliyeti yok (Pi zaten varsa)

---

## 🥉 YOL C — PC'yi Hiç Kapatma

En basit çözüm, ve düşündüğünden daha mantıklı.

**Elektrik hesabı (Türkiye, 2026 mesken tarifesi ~3.0-3.5 TL/kWh):**

| Durum | Güç | Aylık |
|---|---|---|
| Boşta (idle, sunucu kapalı) | ~45 W | ~100-115 TL |
| MC sunucusu 5 kişi | ~95 W | ~210-240 TL |
| Tam yük | ~180 W | ~400-450 TL |

Ayda ~150-250 TL. Bir akıllı priz zaten ~250 TL. **Karar senin ama
"sürekli açık" seçeneği o kadar da pahalı değil.**

Ayrıca sunucu her zaman ayakta olmaz — Crafty'den kapalı tutarsın,
sadece MC sunucu process'i kapalı olur, PC açık kalır. Bu durumda
idle tüketim geçerli, yani ~110 TL/ay.

Bunu seçersen:

```bash
# Uykuya/hazırda beklemeye ASLA geçmesin
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

---

## 🏆 KARARIM: A + C KARIŞIMI

**Sana önerdiğim:**

1. **PC'yi normalde açık tut** (Yol C) — idle'da zaten ucuz
2. **Akıllı prizi yine de al** (Yol A) — kilitlenme/donma durumunda
   uzaktan kurtarma sigortası. Ayda bir donarsa bile prize değer.
3. BIOS'ta `Restore on AC Power Loss = Power On` yap → **elektrik
   kesintisinden sonra PC kendiliğinden geri gelir.** Bu tek başına
   çok değerli, Türkiye'de elektrik kesintisi olağan.

Yol B'yi (WoL + Pi) sadece elinde zaten boşta bir Raspberry Pi varsa yap.
Sırf bunun için Pi almaya değmez — akıllı priz hem ucuz hem daha güvenilir.

---

# BÖLÜM 3 — SUNUCUYU UZAKTAN BAŞLATMA

PC açık artık. Şimdi arkadaşın **MC sunucusunu** başlatabilmeli.

## Neden Crafty Controller

Arkadaşına SSH ve `screen` öğretmeyeceksin. Web paneli lazım.

| Seçenek | Karar |
|---|---|
| **Crafty Controller 4** | ✅ **BU.** Sadece Minecraft için, tek servis, hafif (~500 MB), modlu sunucu destekler |
| Pterodactyl | ❌ Panel + Wings daemon + veritabanı. Senin ölçeğin için aşırı |
| SSH + screen | ❌ Arkadaşın yapamaz |
| MCSManager | ⚠️ Alternatif, ama Crafty MC'ye daha odaklı |

Crafty'nin RAM ihtiyacı ~500 MB - 1 GB. Sende 16 GB var, JVM'e 8 GB
veriyorsun, yer bol.

> ⚠️ Crafty **root olarak çalışmaz** (docs.craftycontrol.com — güvenlik
> gereği). Kendi kullanıcısıyla çalışır, bu iyi bir şey.

## ADIM B1 — Crafty Kurulumu

```bash
curl -L https://get.craftycontrol.com | sudo bash
```

Kurulum bitince şifre burada:
```bash
sudo cat /var/opt/minecraft/crafty/crafty-4/app/config/default-creds.txt
```

Panel: `https://<ip>:8443`

## ADIM B2 — Mevcut Sunucunu Crafty'ye Aktar

Sıfırdan sunucu kurma — **var olanı içeri al.**

Crafty panelinde: **Servers → Create New Server → Import Server**

- **Server Path:** mevcut sunucu klasörünün tam yolu
- **Server JAR/Executable:** NeoForge'un `run.sh`'ı ya da doğrudan JAR

> ⚠️ **Crafty'nin kullanıcısının o klasöre erişimi olmalı.** Bu, senin
> daha önce yaşadığın "klasör root'tu, Simple Voice Chat config yazamadı"
> sorununun tıpatıp aynısı. Tekrar yaşama:

```bash
# Crafty hangi kullanıcı olarak çalışıyor
ps aux | grep -i crafty | head -1

# Sunucu klasörünü ona ver (kullanıcı adı genelde "crafty")
sudo chown -R crafty:crafty /yol/to/minecraft-server
sudo chmod -R u+rwX /yol/to/minecraft-server
```

## ADIM B3 — JVM Flag'lerini Crafty'ye Taşı

`start.sh`'taki flag'ler Crafty'de otomatik gelmez. Crafty'de
**Server → Config → Server Execution Command** alanına şunu yapıştır:

```
java -Xms8G -Xmx8G -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:ParallelGCThreads=4 -XX:ConcGCThreads=1 -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 -XX:ReservedCodeCacheSize=400M -XX:-DontCompileHugeMethods -XX:+UseVectorCmov -XX:+UseFastUnorderedTimeStamps -XX:AllocatePrefetchStyle=3 --add-modules=jdk.incubator.vector -Dchunky.maxWorkingCount=768 -Dio.netty.allocator.maxOrder=9 -Dio.netty.leakDetection.level=disabled -Dfile.encoding=UTF-8 -Djava.awt.headless=true -Dlog4j2.formatMsgNoLookups=true @libraries/net/neoforged/neoforge/21.1.XXX/unix_args.txt nogui
```

> ⚠️ `21.1.XXX` kısmını **kendi NeoForge sürümünle** değiştir.
> Doğru yolu bulmak için:
> ```bash
> ls libraries/net/neoforged/neoforge/
> ```

> ⚠️ **`start.sh` ile Crafty'yi AYNI ANDA kullanma.** İkisi de sunucuyu
> başlatırsa dünya dosyaları iki process tarafından açılır ve **dünyayı
> bozarsın.** Crafty'ye geçtiysen `start.sh`'ı elle çalıştırmayı bırak.

## ADIM B4 — Crafty'yi Boot'ta Otomatik Başlat

```bash
sudo systemctl enable crafty
sudo systemctl status crafty
```

Böylece: priz açıldı → PC boot → Crafty otomatik ayakta → arkadaşın
panele girip START'a basabilir.

### İstersen MC sunucusu da otomatik açılsın

Crafty panelinde: **Server → Config → Crafty Settings → Auto Start** ✅

Bunu açarsan arkadaşının panele girmesine bile gerek kalmaz — PC açılınca
MC sunucusu da açılır. **Ama:** sunucu her zaman RAM tüketir. Sen karar ver.

## ADIM B5 — Arkadaşlarına Sınırlı Hesap Aç

Crafty'de: **Panel Config → Users → Add User**

Rol olarak **sadece şu izinleri** ver:
- ✅ `Commands` (Start/Stop/Restart)
- ✅ `Logs` (log görebilsin)
- ❌ `Files` — **VERME.** Dosya yöneticisi = sunucu dosyalarını silebilir
- ❌ `Config` — **VERME.** Başlatma komutunu değiştirebilir
- ❌ `Backup` — **VERME.** Yedekleri silebilir

> Bu, senin `EKSIK-GEDIK.md`'de kurduğun LuckPerms mantığının panel
> tarafındaki karşılığı. Oyun içi yetki ayrı, panel yetkisi ayrı.

---

# BÖLÜM 4 — TAILSCALE'İ SAĞLAMLAŞTIRMA

Şu an Tailscale çalışıyor ama uzaktan-yönetim senaryosu için **iki ciddi
tuzağı** var.

## TUZAK 1 — Node Key 180 Günde Doluyor (SESSİZCE)

Tailscale resmî dokümanı (tailscale.com/docs/features/access-control/key-expiry):

> *"By default, new domains are set with an expiry period of 180 days.
> If reauthentication does not occur, keys expire and connections to/from
> the given endpoint will stop working."*

**Senin senaryonda bu felaket:** 180 gün sonra sunucunun anahtarı dolar,
Tailscale bağlantısı kesilir, **kimse bağlanamaz** ve sen de uzaktan
düzeltemezsin çünkü bağlanamıyorsun. Fiziksel olarak makinenin başına
gitmen gerekir.

### Çözüm — Sunucuyu etiketle (tag'le)

Tailscale'in kendi blogundan (tailscale.com/blog/tagged-key-expiry):

> *"Starting today, tagged devices will have key expiry disabled by default."*

Adım adım:

**1.** Tailscale admin konsolu → **Access Controls** → policy dosyasına ekle:

```json
{
  "tagOwners": {
    "tag:mcserver": ["autogroup:admin"]
  }
}
```

**2.** Sunucuda:

```bash
sudo tailscale up --advertise-tags=tag:mcserver
```

Bu komut yeniden kimlik doğrulama isteyecek (bir kere). Sonrasında
anahtar **hiç dolmaz.**

**3.** Kontrol et: Admin konsolu → Machines → sunucu satırında
`Expiry disabled` yazmalı.

> **Alternatif (daha basit ama daha az temiz):** Admin konsolu →
> Machines → sunucu → `⋯` → **Disable key expiry**. Tag olmadan da
> çalışır ama ACL yazamazsın.

## TUZAK 2 — Herkes Her Şeye Erişiyor

Varsayılan Tailscale ACL'i şudur:

```json
{"src": ["*"], "dst": ["*:*"]}
```

Yani tailnet'teki **herkes, her porta.** Arkadaşın SSH'a, Crafty'ye,
her şeye girebilir. Bunu daraltalım.

### Önerilen policy (Grants sözdizimi — Tailscale'in yeni önerisi)

Admin konsolu → **Access Controls** → şunu yapıştır:

```json
{
  "tagOwners": {
    "tag:mcserver": ["autogroup:admin"]
  },

  "groups": {
    "group:admins":  ["SENIN_MAILIN@gmail.com"],
    "group:oyuncular": [
      "arkadas1@gmail.com",
      "arkadas2@gmail.com"
    ]
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
      "src": ["group:oyuncular"],
      "dst": ["tag:mcserver"],
      "ip":  [
        "tcp:25565",
        "udp:24454",
        "tcp:8443"
      ]
    }
  ]
}
```

**Bu ne yapıyor:**

| Port | Ne için | Kime |
|---|---|---|
| `tcp:25565` | Minecraft | Oyuncular |
| `udp:24454` | Simple Voice Chat | Oyuncular |
| `tcp:8443` | Crafty paneli | Oyuncular |
| Diğer her şey (SSH dahil) | — | **Sadece sen** |

> **Simple Voice Chat portunu unutma.** `udp:24454` satırını silersen ses
> çalışmaz ve sen yine `SES-CHAT-TESHIS.md`'yi açıp saatlerce MTU
> araştırırsın. Ses UDP'dir, TCP değil.

> ⚠️ **`8443`'ü vermeden önce düşün.** Arkadaşın sunucuyu başlatabilsin
> istiyorsan vermek zorundasın. Ama Crafty'de o kullanıcıya **Files ve
> Config yetkisi verme** (Adım B5).

### Arkadaşların Tailscale hesabı yoksa: Sharing

Arkadaşını kendi tailnet'ine **üye yapmak zorunda değilsin.** Tailscale
"Node Sharing" var:

Admin konsolu → Machines → sunucu → `⋯` → **Share...** → e-posta gir

Paylaşılan kullanıcılar `autogroup:shared` grubuna düşer:

```json
{
  "src": ["autogroup:shared"],
  "dst": ["tag:mcserver"],
  "ip":  ["tcp:25565", "udp:24454", "tcp:8443"]
}
```

**Bu daha güvenli** — arkadaşın senin ağının üyesi olmaz, sadece o makineye
erişir.

## TUZAK 3 — DERP Relay (Ses Kalitesi İçin Kritik)

`SES-CHAT-TESHIS.md`'de bahsettiğim konu. Kontrol et:

```bash
tailscale status
```

Satırlarda `direct` değil `relay "fra"` gibi bir şey görüyorsan trafiğin
Tailscale relay sunucularından dolaşıyor → gecikme + paket kaybı → ses bozuk.

Düzeltme:
```bash
sudo ufw allow 41641/udp
```

## Tailscale SSH (senin için, kolaylık)

Kendine SSH anahtarı taşımadan bağlanmak istersen:

```bash
sudo tailscale set --ssh
```

Policy'ye ekle:

```json
{
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

Artık her yerden: `tailscale ssh kullanici@mcserver`

> ⚠️ Bu `tailscaled`'i o makinede bir **giriş yetkilisi** yapar. ACL'i
> `group:admins` ile sınırlı tut, oyunculara verme.

---

# BÖLÜM 5 — GÜVENLİK DUVARI (UFW)

Tailscale ACL'i tailnet içini kontrol eder. UFW ise makinenin kendisini korur.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Tailscale arayüzünden gelen her şeye izin (ACL zaten filtreliyor)
sudo ufw allow in on tailscale0

# Tailscale'in direkt bağlantı kurabilmesi için
sudo ufw allow 41641/udp

# Yerel ağdan SSH (acil durum erişimi — kendini kilitleme)
sudo ufw allow from 192.168.0.0/16 to any port 22 proto tcp

sudo ufw enable
sudo ufw status verbose
```

> ⚠️ **`sudo ufw allow 25565` YAPMA.** İnternete port açmıyorsun,
> Tailscale kullanıyorsun. Portu dünyaya açarsan Tailscale'in bütün
> güvenlik amacı boşa gider ve sunucun bot taramalarına maruz kalır.

> ⚠️ **Kendini kilitleme:** UFW'yi SSH oturumundayken açıyorsan,
> `allow in on tailscale0` satırını **enable'dan ÖNCE** yazdığından
> emin ol. Yoksa bağlantın kopar.

---

# BÖLÜM 6 — DAYANIKLILIK (Elektrik Kesintisi & Çökme)

## Otomatik yeniden başlatma

Crafty'de: **Server → Config → Crafty Settings → Crash Detection** ✅

Bu, `start.sh`'taki `while true` döngüsünün Crafty karşılığı.

## Elektrik kesintisi sonrası zinciri

```
Elektrik gitti
    ↓
Elektrik geldi
    ↓
BIOS: Restore on AC Power Loss = Power On   → PC açılır
    ↓
GRUB: GRUB_RECORDFAIL_TIMEOUT=3             → menüde takılmaz  ← ADIM A2
    ↓
Ubuntu boot
    ↓
tailscaled.service (enabled)                → Tailscale bağlanır
    ↓
crafty.service (enabled)                    → Panel ayakta
    ↓
Crafty Auto Start (açıksa)                  → MC sunucusu ayakta
```

**Bu zincirin her halkası önceki adımlarda kuruldu.** Bir tanesi eksikse
zincir kopar ve sen sebebini uzaktan bulamazsın.

Servisleri doğrula:
```bash
systemctl is-enabled tailscaled crafty
# ikisi de "enabled" demeli
```

## Swap uyarısı

35 GB swap'ın var. Bu **çok fazla** ve MC sunucusu için tehlikeli.
JVM heap'i swap'e düşerse TPS yere çakılır — hem de "neden yavaş"
diye anlayamazsın çünkü CPU boşta görünür.

```bash
# Swap kullanımını en aza indir
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-mc.conf
sudo sysctl --system
```

> Swap'i tamamen kapatma — OOM killer'ın sunucunu öldürmesindense
> yavaşlaması daha iyi. Ama `swappiness=10` ile kernel swap'e ancak
> mecbur kalınca dokunur.

## Yedek (bunu ATLAMA)

`EKSIK-GEDIK.md`'de anlattığım FTB Backups 2 hâlâ geçerli. Ama artık
Crafty'nin kendi yedeği de var:

**Server → Backups → Schedule** → günlük, 3 kopya sakla

> ⚠️ **Crafty yedeği ile mod yedeğini aynı anda çalıştırma.** İkisi de
> aynı anda dünya dosyalarını okursa yedek bozuk çıkabilir. Birini seç.
> Crafty'ninki daha pratik (panelden geri yükleyebilirsin).

---

# BÖLÜM 7 — ARKADAŞLARINA VERECEĞİN TALİMAT

Aşağısını kopyalayıp arkadaşlarına at. Onların bilmesi gereken tek şey bu.

---

## 📋 MC SUNUCUSUNA BAĞLANMA

**BİR KERELİK KURULUM:**

1. Tailscale'i indir: https://tailscale.com/download
2. Kur ve giriş yap (gelen davet mailindeki hesapla)
3. Tailscale'i **açık bırak**

**HER OYUN OTURUMU:**

1. Tailscale'in açık olduğundan emin ol
2. Tarayıcıdan `https://mcserver:8443` aç
   - "Güvenli değil" uyarısı normal, devam et
3. Kullanıcı adın + şifrenle gir
4. Sunucu **kırmızı** ise → yeşil **START** butonuna bas
5. 1-2 dakika bekle (mod yükleniyor)
6. Minecraft'ı aç → Multiplayer → Sunucu adresi: `mcserver:25565`

**PC KAPALIYSA (panel açılmıyorsa):**

1. Telefonda **Tapo** uygulamasını aç
2. "MC Sunucu" prizini **AÇ**
3. 2-3 dakika bekle
4. Yukarıdaki adımlara dön

**KURALLAR:**
- ❌ Panelde **Files** veya **Config** sekmelerine dokunma
- ❌ Sunucuyu keyfi restart etme, içeride insan olabilir
- ✅ Bir sorun olursa Stop → 10 sn bekle → Start

---

# BÖLÜM 8 — SORUN GİDERME

| Belirti | Sebep | Çözüm |
|---|---|---|
| Priz açıldı ama PC açılmıyor | BIOS `Last State` seçili | BIOS → `Power On` yap |
| Priz açıldı ama PC açılmıyor | `ErP Ready` = Enabled | BIOS → `Disabled` yap |
| PC açıldı ama Ubuntu gelmedi | GRUB recordfail | `GRUB_RECORDFAIL_TIMEOUT=3` (Adım A2) |
| PC açık, Tailscale'de görünmüyor | Node key doldu | `tailscale up --force-reauth` + tag'le (Tuzak 1) |
| Panel açılmıyor (`8443`) | Crafty servisi ölü | `sudo systemctl restart crafty` |
| Panel açılmıyor | ACL portu kapalı | ACL'e `tcp:8443` ekle |
| MC'ye bağlanamıyor | Sunucu kapalı | Panelden START |
| MC'ye bağlanamıyor | ACL portu kapalı | ACL'e `tcp:25565` ekle |
| Ses yok | ACL'de UDP yok | ACL'e `udp:24454` ekle |
| Ses kesik kesik | DERP relay | `sudo ufw allow 41641/udp` |
| Sunucu çok yavaş | Swap'e düştü | `vm.swappiness=10` (Bölüm 6) |
| Dünya bozuldu | İki process aynı anda | `start.sh` + Crafty'yi birlikte kullanma |

## Teşhis komutları

```bash
# Tailscale sağlıklı mı, relay mi kullanıyor
tailscale status
tailscale netcheck

# Servisler ayakta mı
systemctl status tailscaled crafty

# Boot'ta açılacak mı
systemctl is-enabled tailscaled crafty

# Portlar dinleniyor mu
sudo ss -tulpn | grep -E '25565|24454|8443'

# Son açılış ne zamandı, düzgün müydü
last -x reboot | head -5
journalctl -b -p err --no-pager | tail -20
```

---

# EK — TAM KONTROL LİSTESİ

`GOREV-LISTESI.md` dosyasında adım adım işaretlenebilir hâli var.

## Özet sıra

- [ ] **1.** Akıllı priz al ve tak
- [ ] **2.** BIOS: `ErP Ready` → Disabled
- [ ] **3.** BIOS: `Restore on AC Power Loss` → **Power On** (Last State DEĞİL)
- [ ] **4.** BIOS: `Resume By PCI-E Device` → Enabled
- [ ] **5.** GRUB: `GRUB_RECORDFAIL_TIMEOUT=3` + `update-grub`
- [ ] **6.** `FSCKFIX=yes`
- [ ] **7.** **TEST:** poweroff → priz kapat → priz aç → PC açılmalı
- [ ] **8.** Crafty kur
- [ ] **9.** Mevcut sunucuyu Import et
- [ ] **10.** Klasör izinlerini crafty kullanıcısına ver
- [ ] **11.** JVM flag'lerini Crafty'ye yapıştır (NeoForge sürümünü düzelt)
- [ ] **12.** `systemctl enable crafty`
- [ ] **13.** Arkadaşlar için sınırlı Crafty hesabı (Files/Config YOK)
- [ ] **14.** Tailscale: `tag:mcserver` etiketle → key expiry kapansın
- [ ] **15.** Tailscale ACL: portları daralt (25565 + 24454 + 8443)
- [ ] **16.** Arkadaşları Share ile davet et
- [ ] **17.** UFW kur (tailscale0 + 41641/udp)
- [ ] **18.** `vm.swappiness=10`
- [ ] **19.** Crafty yedek zamanlaması
- [ ] **20.** **TEST:** başka bir ağdan (mobil veri) baştan sona dene

---

## Kaynaklar

- Tailscale — WoL neden çalışmaz: tailscale.com/blog/wake-on-lan-tailscale-upsnap
- Tailscale — Key expiry: tailscale.com/docs/features/access-control/key-expiry
- Tailscale — Tagged nodes: tailscale.com/blog/tagged-key-expiry
- MSI — Wake on LAN ayarları: msi.com/support/technical_details/MB_Wake_On_LAN
- MSI FAQ mb-503 / mb-2287 — ErP + Resume By PCI-E
- Ubuntu Launchpad Bug #1443735 — GRUB recordfail headless hang
- Crafty Controller: docs.craftycontrol.com
