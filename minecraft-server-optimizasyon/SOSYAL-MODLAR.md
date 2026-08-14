# SOSYAL MODLAR — Oyuncu Takibi + Web Paneli + Özel Sohbet

**Soru:** Kim en son ne zaman girdi diye kayıt tutan bir mod + etkileşim
sayfası (web paneli) + kullanıcı seçip özel sohbet edebileceğim bir mod.
Hepsi 1.21.1 NeoForge için.

## ✅ SONUÇ: Üçünü de tek modda yapan bir şey var — **Paradigm Essentials**

İlk taramamda bunu bulamamıştım, haklıydın. Bu sefer **Modrinth'in API'sini
doğrudan sorguladım** (`versions:1.21.1` + `categories:neoforge` filtresiyle),
elle arama yapmadım. Sonuçlar aşağıda, hepsinin **jar dosya adı ve SHA1'i
doğrulanmış** durumda.

**Araştırma tarihi:** 2026-08-14

---

# 🏆 BİRİNCİ ÖNERİ: Paradigm Essentials

**Üç isteğini de tek başına karşılıyor.** Modrinth ID: `s4i32SJd`

```
Dosya : Paradigm-neoforge-1.21.1-2.3.1b.jar
Boyut : 1.367.756 bayt (1.3 MB)
SHA1  : fa7e84cccd45ffdc1f4cbb798c55c70678848195
Yayın : 2026-08-12   ← iki gün önce güncellenmiş
Ortam : dedicated_server_only  → SADECE SUNUCU
Bağımlılık: YOK  (dependencies: [])
```

🔗 https://modrinth.com/mod/paradigm

## Neden bu?

### 1️⃣ Web paneli — "etkileşim sayfası" ✅

Mod'un **içinde gömülü web paneli** var, harici bir şey kurmuyorsun:

> *"Paradigm includes a built-in **local web dashboard** for server
> administration and configuration. **No external panel required.
> It runs with your server all locally.**"*

Panelde olanlar:
- Sunucu genel durumu ve anlık çalışma bilgisi
- **Moderasyon ve ceza geçmişi** (kim ne zaman ne yaptı)
- **Audit history** (denetim geçmişi)
- Config editörleri, izin/grup yönetimi, MOTD editörü
- Komut ayarları ve bekleme süreleri

Kurulum: `/paradigm dashboard open` → sana **tek kullanımlık güvenli
giriş linki** veriyor.

🔒 **Güvenlik:** Panel varsayılan olarak `127.0.0.1`'e bağlı (dışarı kapalı).
Oturum doğrulama, tek kullanımlık token, CSRF koruması, origin kontrolü ve
rate limiting var. Bu **ciddi bir iş** — çoğu küçük mod bunu yapmaz.

### 2️⃣ Özel sohbet ✅

> - Private messages with `/msg`
> - Quick replies with `/reply` or `/r`
> - Player mentions using `@PlayerName`
> - Staff chat `/sc`
> - **Private group chats `/groupchat`**  ← grup sohbeti de var
> - Custom join and leave messages

Yani `/msg` + `/r` + **@mention** + **grup sohbeti**. Senin istediğin
"kullanıcı seçip özel sohbet"in tam karşılığı.

### 3️⃣ Kayıt tutma ✅

- **Storage:** JSON / SQLite / MySQL / MariaDB (seçebiliyorsun)
- **Audit logging** — JSONL dosyasında veya SQL'de
- **Punishment history** — kalıcı ceza/uyarı geçmişi
- `/whois` komutu

### Bonus: zaten planladığımız şeyleri de kapsıyor

| Zaten planlanan | Paradigm'de var mı |
|---|---|
| FTB Essentials (`/home`, `/back`, `/tpa`, `/warp`, `/rtp`) | ✅ hepsi var |
| FTB Ranks (izin/grup sistemi) | ✅ kendi grup sistemi + **LuckPerms göçü** |
| Zamanlanmış yeniden başlatma | ✅ var (script gerekiyor) |
| Duyurular, MOTD, tablist, hologram | ✅ var |

**Yani `MOD-ONERILERI.md`'deki FTB Essentials + FTB Ranks ikilisi yerine
tek bu mod yeter.** İstersen modüler olarak istemediğin kısmı kapatıyorsun.

## ⚠️ Bu modun dürüst dezavantajları

| Konu | Durum |
|---|---|
| **Sürüm tipi** | **`beta`** — 2.3.1b bir beta sürümü. Kararlı sürüm istiyorsan **2.2.4** (`SMCHYEDX`) `release` etiketli |
| **İndirme sayısı** | 5.166 toplam, 2.3.1b'de sadece 15. **Az test edilmiş** |
| **Lisans** | CC-BY-NC-ND-4.0 |
| **Çakışma yüzeyi** | Büyük mod — 237 modun arasında en riskli aday bu. **Tek başına kur ve logu oku** |
| **SQLite bug'ı** | 2.3.1b'de *"database is locked"* hatası **düzeltildi** — yani 2.2.4'te bu hata **var**. İşte ikilem: eski=kararlı ama buglu, yeni=düzeltilmiş ama beta |

**Tavsiyem:** **2.3.1b'yi kur.** SQLite kilitlenme hatası sessizce veri
kaybettiriyor (izinler, cezalar, warp'lar kaydedilmiyor) — bu, beta olmaktan
daha kötü.

---

# 🥈 İKİNCİ SEÇENEK: Dash (ForgeDash) — sadece web paneli istiyorsan

Bir önceki dokümanda "GitHub'da, MC sürümü belirsiz" demiştim. **Yanılmışım —
Modrinth'te yayında ve 1.21.1 NeoForge destekliyor.** Düzeltiyorum.

```
Dosya : forgedash-4.0.jar
Boyut : 14.633.405 bayt (14 MB)
SHA1  : 4ee814f84e5c700e6c6c151f37e23a2b4dc60b33
Yayın : 2026-07-06
Tip   : release  ← beta değil
Ortam : dedicated_server_only
Bağımlılık: YOK
Port  : 8080 (varsayılan)
```

🔗 https://modrinth.com/mod/dash-dashboard

Paradigm'in panelinden **çok daha güçlü** bir panel:

- Canlı **TPS, MSPT, RAM, CPU, uptime, chunk** istatistikleri + grafikler
- **Uzaktan konsol** — komut çalıştırma, canlı log akışı
- **Oyuncu profilleri + oturum geçmişi + playtime takibi** ← tam istediğin
- Admin notları, envanter görüntüleme/düzenleme, kick/ban/freeze/teleport
- Dosya yöneticisi (yükleme, düzenleme, indirme)
- Yedekleme (manuel + zamanlanmış)
- **Modrinth tarayıcısı + mod güncelleme kontrolü**
- Discord webhook

Kurulum:
```
1. forgedash-4.0.jar → mods/
2. Sunucuyu başlat
3. Oyunda:  /dash register
4. Verdiği kurulum linkini aç, web hesabını oluştur
```

## 🚨 Kritik uyarı: Crafty ile çakışır

`UZAKTAN-YONETIM.md`'de **Crafty Controller** kurmayı planlamıştık.
**İkisi de aynı işi yapıyor.** İkisini birden kurma:

| | Crafty Controller | Dash (ForgeDash) |
|---|---|---|
| Ne | Sunucu dışı panel (systemd servisi) | Mod olarak sunucu içinde |
| Sunucuyu **açıp kapatabilir** | ✅ | ❌ (sunucu kapalıysa panel de kapalı) |
| Oyuncu oturum geçmişi | var | ✅ daha detaylı |
| Mod yönetimi / Modrinth | ❌ | ✅ |
| Olgunluk | Yıllardır kullanılıyor | **591 indirme** — yeni |

**Karar:** Uzaktan **güç/başlatma** yönetimi senin ana ihtiyacındı
(`UZAKTAN-YONETIM.md`). Sunucu çökerse Dash de çöker, Crafty ayağa kaldırır.
👉 **Crafty'de kal.** Dash'i sadece Crafty'den vazgeçersen düşün.

---

# 🥉 MİNİMAL YOL: sadece `/seen` istiyorsan

Büyük mod istemiyorsan, tek iş yapan ufak jar:

## Player Last Seen

```
Dosya : seen-0.1.0-neoforge-1.21.1.jar
Boyut : 11.334 bayt (11 KB!)
SHA1  : f14ea9c1f0ca16c088d6d5e474855781b6ac27ce
Ortam : server_only
Bağımlılık: YOK   ← NeoForge sürümünde Fabric API bile gerekmiyor
```

🔗 https://modrinth.com/mod/player-last-seen

```
/seen Ahmet   → Ahmet en son 2026-05-15 14:30'da görüldü (yaklaşık 1 gün önce)
/seen Mehmet  → Mehmet şu anda oyunda
```

⚠️ Sadece **son 3** girişi tutuyor. ⚠️ Lisans: All Rights Reserved
(açıklamada MIT yazıyor ama Modrinth'teki lisans alanı ARR — çelişki var).
⚠️ 174 indirme.

## Mogrul Playtime — scoreboard'a oynanış süresi

```
Modrinth: mogrul-play-time  |  1.21.1  |  dedicated_server_only
```
Oyuncuların dakika/saat/gün cinsinden süresini **scoreboard objesi** olarak
tutuyor. Tablist'te göstermek istersen işe yarar. Lisans: CC-BY-NC-ND.

## PlayTimeStatistics — tablist'te süre gösterimi

```
Modrinth: playtimestatistics  |  1.21.1 ✅  |  server_side: required
15.009 indirme  |  datapack+mod
```
Oynanış süresini **Tab listesinde ve oyuncu adının altında** gösteriyor.
Bu üçlünün en çok indirilmişi.

---

# ❌ ELENENLER — ve kesin sebepleri

Bu sefer hepsini **API'den dosya listesiyle** doğruladım, açıklama metnine
güvenmedim:

| Mod | Kesin durum |
|---|---|
| **Private Chat** (YacBek) | Tek dosya: `Private Chat - 1.0.0 - (Forge).jar`, **1.20.6 Forge**. 1.21.1 yok. Y tuşuyla GUI'li DM tam istediğindi, ama yok |
| **Plan / Player Analytics** | Fabric + Bukkit. **NeoForge sürümü yok** |
| **Player Statistics** (FNewell) | Fabric, en son 1.21.4. Web sayfası dahili ama **NeoForge yok** |
| **IntegratedPlaytime** | Forge 1.20.1. 33 rütbe, AFK tespiti, GUI — ama **1.21.1 NeoForge yok** |
| **Private Messages** (Son1kX) | Fabric 1.21.8 |
| **Player Logger** | 1.21.1 NeoForge **var** ✅ ama MySQL zorunlu + geliştirici notu: *"üniversite ödevi"*, *"DB bağlanamazsa sunucu durabilir"*. **Kurma** |
| **Last Played Logger** | 1.21.1 NeoForge **var** ✅ ama Google Cloud + OAuth + `credentials.json` kurulumu gerekiyor. Google Sheets'te görmek istemiyorsan gereksiz eziyet |
| **RpEssentials** | 1.21.1 NeoForge ✅, `/msg` + `/r` + `/whois` + son bağlantı var. **Ama rol yapma modu** — meslek/lisans sistemi, isim gizleme, ölüm RP'si geliyor. Paradigm daha temiz |
| **VoxelDash** | 1.21.1 NeoForge panel, Paradigm/Dash'e alternatif. **Emin değilim:** detaylarını incelemedim |

---

# 📋 KARAR TABLOSU — sen hangisini istiyorsun?

| İhtiyacın | Kur |
|---|---|
| **"Üçünü de istiyorum, tek modda"** | 🏆 **Paradigm Essentials 2.3.1b** |
| Sadece "kim ne zaman girdi" | Player Last Seen (11 KB) |
| Sadece güçlü web paneli | Dash 4.0 — **ama Crafty'yle çakışır** |
| Sadece DM | **Önce `/msg Ahmet selam` dene** — vanilla'da var. Yetmezse Paradigm |

## 🎯 Benim net tavsiyem

**Paradigm Essentials 2.3.1b'yi kur.** Sebep:

1. Üç isteğini de karşılıyor (takip + panel + DM)
2. **Server-only** — arkadaşların hiçbir şey kurmuyor
3. **Bağımlılık yok**
4. `MOD-ONERILERI.md`'deki **FTB Essentials + FTB Ranks'in yerine geçiyor**
   → net mod artışı sadece **+1**
5. Web paneli `127.0.0.1`'e bağlı, dışarı açık değil
6. 2 gün önce güncellenmiş, geliştirici aktif

**Ama beta olduğu için: tek başına kur, sunucuyu aç, logu oku.**

---

# 🔧 KURULUM

```bash
# 1. Sunucuyu durdur
# 2. Sadece Paradigm'i at:
#    Paradigm-neoforge-1.21.1-2.3.1b.jar  →  mods/
# 3. Sunucuyu aç
# 4. Logu kontrol et:
grep -iE "error|conflict|incompatible|failed|exception" logs/latest.log | head -30
```

**Oyun içi test:**
```
/paradigm help              → modül listesi
/msg <arkadaşın> selam      → özel mesaj
/r selam                    → hızlı cevap
/whois <arkadaşın>          → oyuncu bilgisi
/paradigm dashboard open    → web paneli giriş linki
```

## 🚨 Paneli Tailscale üzerinden açmak

Panel `127.0.0.1`'e bağlı, yani **sadece sunucu makinesinden** açılır.
Kendi bilgisayarından açmak istersen SSH tüneli kur:

```bash
ssh -L 8080:127.0.0.1:8080 kullanici@100.70.34.111
# sonra tarayıcıda: http://localhost:8080
```

⚠️ Paneli `0.0.0.0`'a açma. SSH tüneli hem güvenli hem de zaten Tailscale
üstünden çalışıyor.

⚠️ **Emin değilim:** Paradigm'in dashboard bind adresinin config'den
değiştirilip değiştirilemediğini doğrulayamadım. SSH tüneli her hâlükârda
en güvenli yol.

## Mod sayısı

237 → **238**. (FTB Essentials + FTB Ranks'ten vazgeçersen net **+1**.)

---

# 📚 KAYNAKÇA

**Yöntem:** Modrinth API v2, `facets=[["versions:1.21.1"],["categories:neoforge"]]`
filtresiyle sorgulandı. Her mod için `/version` endpoint'inden **gerçek jar
dosya adı, boyut, SHA1 ve `game_versions` alanı** okundu. Proje açıklamasındaki
sürüm iddialarına güvenilmedi.

| Mod | Kaynak |
|---|---|
| Paradigm Essentials | `api.modrinth.com/v2/project/paradigm` → 1.21.1/neoforge ✅ |
| Dash (ForgeDash) | `api.modrinth.com/v2/project/dash-dashboard` → 1.21.1/neoforge ✅ |
| Player Last Seen | `api.modrinth.com/v2/project/1qgfFnRL/version` → 5 build, biri neoforge-1.21.1 ✅ |
| Mogrul Playtime | Modrinth `mogrul-play-time`, 1.21.1 neoforge |
| PlayTimeStatistics | Modrinth `playtimestatistics`, 1.21.1 |
| Private Chat (elendi) | CurseForge dosya listesi: 1 dosya, 1.20.6 Forge |
| Plan (elendi) | CurseForge: Fabric/Bukkit, NeoForge yok |
| Player Statistics (elendi) | CurseForge: Fabric 1.21.4 |

---
---

# 🚨 EK BÖLÜM: "Tuşa basıp GUI'de sohbet / Tab'da son giriş görebilir miyim?"

**Soru:** *"Ses modundaki gibi bir tuşla, ya da Tab'a basınca çıkan listede
oyuncuya tıklayıp özel sayfada sohbet edebilecek miyim? Tab'a basınca online
sunuculardaki gibi en son kim girdi, kaç saat oynadı, son konumu görebilecek
miyim?"*

## ❌ Kısa cevap: HAYIR — ikisi de olmayacak. Sebebi teknik, mod eksikliği değil.

Yukarıda önerdiğim **Paradigm `dedicated_server_only`**. Bu ne demek?

> **Sunucu-only bir mod, senin oyun ekranına HİÇBİR ŞEY çizemez.**
> Tuş ataması yapamaz, pencere açamaz, buton koyamaz.

Sunucu sadece **paket** gönderir. Client'ta o modun kodu yoksa, çizecek kimse
yok. Simple Voice Chat'te `V` tuşuna basınca menü açılıyor çünkü **o mod
senin bilgisayarında da kurulu**. Paradigm'de öyle bir şey yok.

Yani Paradigm'de özel mesaj şöyle görünür — chat satırı olarak:

```
[Ben → Ahmet] selam naber
[Ahmet → Ben] iyidir sen
```

**Ayrı bir sohbet penceresi/sekmesi YOK.** Normal sohbetin içinde, renkli
satırlar olarak akar.

## 📊 Tab tuşu meselesi — kritik sınır

Tab listesi Minecraft'ın **vanilla** özelliği ve sunucu onu sınırlı biçimde
doldurabiliyor. Sunucu-only bir mod Tab'da **şunları yapabilir**:

| Yapılabilir ✅ | Yapılamaz ❌ |
|---|---|
| Üst/alt başlık (server adı, TPS, RAM, uptime, saat) | **Butona tıklamak** — Tab listesi tıklanabilir değil |
| Oyuncu adının yanına yazı eklemek (rütbe, AFK, süre) | **Offline oyuncuyu göstermek** |
| Sıralama (alfabetik / rütbeye göre) | **"En son ne zaman girdi" göstermek** |
| Ping, boyut (Nether/End) | **Son konum (koordinat) göstermek** |

### 🔴 En önemlisi: **Tab listesi sadece O AN ONLINE olanları gösterir.**

Bu Minecraft protokolünün kendisi. `PlayerInfoUpdate` paketi sadece bağlı
oyuncuları taşır. "En son kim girdi" Tab'da **hiçbir modla** gösterilemez —
çünkü o oyuncu listede yok ki.

Gördüğün büyük sunucularda Tab'da öyle bilgi varsa, o **online** oyuncuların
bilgisidir (rütbe, süre, ping). Offline "son giriş" bilgisi orada da yoktur;
o sunucularda `/seen` komutu veya web sitesi vardır.

---

# ✅ O ZAMAN GERÇEKTEN NE YAPABİLİRSİN — 3 yol

## YOL 1 — Tab'ı zenginleştir (online oyuncular için)

İki server-only mod, ikisi de arkadaşlarına hiçbir şey kurdurtmuyor:

### PlayTimeStatistics
```
Modrinth: playtimestatistics  |  1.21.1 ✅  |  server_side: required
15.009 indirme
```
👉 **Tab listesinde oyuncu adının yanında oynanış süresini gösterir.**
Senin "kaç saat oynadı" isteğinin Tab'daki karşılığı bu.

### Better TabList
```
Modrinth: better-tablist  |  1.21.1 ✅  |  server_only
6.021 indirme  |  config/tablist.toml
```
Placeholder listesi (doğrulandı): `#TPS` `#CTPS` `#MSPT` `#PLAYERCOUNT`
`#MAXPLAYERS` `#PLAYERNAME` `#PING` `#RANK` `#AFK` `#WORLD` `#MEMORY`
`#UPTIME` `#DATE` `#TIME`

Örnek config:
```toml
[appearance]
server_name = "Kitsugi"
header = ["#N   &l#SERVERNAME   #N&7Online: &e#PLAYERCOUNT&7/&e#MAXPLAYERS#N"]
footer = ["&7TPS: #CTPS &7| RAM: &#AA55FF#MEMORY &7| Uptime: &#FFAA00#UPTIME"]
display_name_format = "{name} &7#AFK"
[afk]
afk_enabled = true
afk_timeout = 300
```
⚠️ `#RANK` için FTB Ranks gerekiyor (opsiyonel). Lisans: All Rights Reserved.

**Sonuç Tab'da:** kim online, kaç saat oynamış, AFK mi, pingi kaç, hangi
boyutta, sunucu TPS'i ne. **Ama tıklanamaz ve offline oyuncu görünmez.**

**Offline "son giriş" için:** `/seen Ahmet` komutu (Player Last Seen) veya
web paneli. Tab'da olmaz, olamaz.

---

## YOL 2 — GUI'li DM gerçekten şartsa: **Essential Mod**

Tuşa basıp arkadaş listesinden seçip pencerede yazışmak istiyorsan, bunu
yapan tek olgun şey bu:

```
Modrinth: essential  |  1.21.1 ✅ NeoForge
client_side: required  |  server_side: UNSUPPORTED
39.888.004 indirme
```

Tuşa basıyorsun → arkadaş listesi açılıyor → tıklıyorsun → **ayrı sohbet
penceresi**. Tam tarif ettiğin şey.

### 🚨 Ama büyük "ama"lar var

| Sorun | Detay |
|---|---|
| **Client-side** | **Sen ve TÜM arkadaşların tek tek kurmak zorunda.** Sunucuya atmak işe yaramaz |
| **Sunucudan bağımsız** | Essential'ın kendi ağı üzerinden çalışır. Sunucun kapalıyken de yazışırsınız — ama **sunucu bu sohbetleri kaydetmez** |
| **Kayıt tutmaz** | Senin "sunucuda kayıt tutsun" isteğini karşılamaz |
| **Üçüncü taraf hesap** | Essential hesabı açmak gerekiyor |
| **Lisans** | All Rights Reserved, kapalı kaynak |
| **Mod çakışması** | Client tarafında karışıklık çıkarabiliyor (bilinen bir durum) |

**Dürüst değerlendirme:** 5 kişilik arkadaş sunucusunda GUI'li DM için
Discord zaten daha iyi. Essential'ı sırf bunun için kurdurtma.

---

## YOL 3 — Web paneli (senin "özel sayfa" fikrine en yakın olan)

Oyun içinde değil ama tarayıcıda gerçekten bir **sayfa** istiyorsan:

| İstediğin | Paradigm paneli | Dash paneli |
|---|---|---|
| Kim online | ✅ | ✅ |
| **Son giriş / oturum geçmişi** | ceza+audit geçmişi | ✅ **oyuncu profili + oturum geçmişi** |
| **Oynanış süresi** | ⚠️ emin değilim | ✅ |
| **Son konum** | `/near`, `/whois` var | ✅ (teleport/profil ekranında) |
| Panelden sohbet | ✅ chat sayfası | ✅ konsol/chat |

"Online sunuculardaki gibi oyuncu istatistik sayfası" tarifine **en yakın
olan Dash'in oyuncu profili ekranı.** Ama Crafty ile çakışıyor (yukarıda
anlattım).

⚠️ **Emin değilim:** Panellerin oyuncu profili ekranlarının ekran
görüntülerini inceleyemedim; hangi alanların tam olarak gösterildiğini
özellik listesinden okudum, gözümle görmedim.

---

# 🎯 DÜRÜST TAVSİYE — beklentini gerçeğe oturtayım

Hayalindeki şey (**Tab'a bas → oyuncuya tıkla → özel sohbet penceresi açılsın
→ orada son giriş, süre, konum yazsın**) **1.21.1 NeoForge'da mevcut hiçbir
modda yok.** Bunun için birinin client+server modu yazması lazım, yazan yok.

Elindeki gerçekçi paket:

```
mods/ klasörüne (arkadaşların hiçbir şey kurmuyor):
├── Paradigm-neoforge-1.21.1-2.3.1b.jar   → /msg, /r, /whois, web panel
├── playtimestatistics                     → Tab'da oynanış süresi
└── (opsiyonel) better-tablist             → Tab'da TPS/RAM/AFK/ping
```

**Sonuç:**
- Tab'a bastığında: online oyuncular + süreleri + AFK + ping + sunucu durumu
- `/seen Ahmet` → Ahmet en son ne zaman girdi
- `/msg Ahmet selam` → özel mesaj (chat satırı olarak, ayrı pencere değil)
- Tarayıcıdan panel → detaylı geçmiş

**Mod artışı: +2 (veya +3).**

Eğer "chat satırı yetmez, gerçekten ayrı pencere olsun" diyorsan — o zaman
tek yol Discord. Kimse mod kurmaz, geçmiş kalıcı kalır, telefondan da açılır.
Bunu sana mod satmamak için söylüyorum. 🍻

---
---

# 🔥 EK BÖLÜM 2: "Client mod da olur" — O ZAMAN İŞLER DEĞİŞİYOR

Client mod da kurabileceğini söyledin. Aramayı **client_and_server** dahil
baştan yaptım. **İki tane gerçek çözüm çıktı.**

---

## 🏆 A) Tab'a basınca istatistik → **Tab Info**

Bir önceki bölümde "Tab'da konum gösterilemez" demiştim. **Bu mod tam onu
yapıyor.** Düzeltiyorum.

```
Modrinth: tab-info  (id DuHZti8U)  |  🔗 modrinth.com/mod/tab-info
1.21.1 ✅ NeoForge (+ Fabric, Forge, Quilt, datapack)
environment: server_only   → arkadaşların HİÇBİR ŞEY kurmuyor
Lisans: LGPL-3.0-or-later (açık kaynak)  |  GitHub: nwrenger/tab-info
```

Resmi açıklama (birebir):

> *"Shows useful player stats like **deaths**, **kills**, **playtime**,
> **position**, and **current dimension** to **everyone** through a compact,
> configurable readout in the **player list**."*

**Yani Tab'a bastığında oyuncu listesinde:**

| Bilgi | Var mı |
|---|---|
| 💀 Ölüm sayısı | ✅ |
| ⚔️ Kill sayısı | ✅ |
| ⏱️ **Oynanış süresi** | ✅ |
| 📍 **Pozisyon (koordinat)** | ✅ ← "son konum" isteğin |
| 🌍 Boyut (Overworld/Nether/End) | ✅ |

Bilgiler **2 saniyede bir dönüyor** (hepsi sığsın diye). Çok oyunculu ve tek
oyunculu çalışıyor.

**Ayarlama — komutla açılan tıklanabilir panel:**
```mcfunction
/function tab_info:config     → her bilgiyi tek tek aç/kapa (fareyle tıklanır)
/function tab_info:about      → bilgi paneli
```

**Kaldırırsan Tab'da boşluk kalırsa:**
```mcfunction
/scoreboard objectives setdisplay list
```

⚠️ 938 indirme (yeni mod, Haziran 2026). Ama **açık kaynak (LGPL) ve GitHub'da**
— kodu okunabilir, riski düşük. Datapack olarak da çalışıyor.

⚠️ Hâlâ geçerli olan sınır: **Tab sadece online oyuncuları gösterir.** Offline
"en son ne zaman girdi" için `/seen` (Player Last Seen) gerekiyor. Bu
Minecraft protokolü, mod meselesi değil.

---

## 🏆 B) Tuşa basıp GUI'de özel sohbet → **MineTogether**

Tam tarif ettiğin şey: **tuş ataması → arkadaş listesi → tıkla → sohbet
penceresi.**

```
Modrinth: creeperhost-minetogether  (id Nu7Lnzkx)
🔗 modrinth.com/mod/creeperhost-minetogether

Dosya : minetogether-neoforge-1.21-6.3.3.jar
Boyut : 4.882.766 bayt (4.8 MB)
SHA1  : 320cf996f8cafe85398ebcdbf34a7fed6298c6a4
Tip   : release  |  game_versions: ["1.21","1.21.1"] ✅
environment: client_or_server_prefers_both
Lisans: GPL-3.0 (açık kaynak)  |  CreeperHost Ltd. — FTB App'i yapan firma
```

Resmi özellik listesi (birebir):

> *Friends lists · Global chat · **Group chat** · **Direct messages** ·
> Server list · World pre-generation · Private minigames · Server invites*

6.3.2 changelog'unda **kritik satır** (doğrulandı):

> *"Added **keybindings** for opening **Chat/Friends**/Settings."*

👉 **Tuş atamaları var.** Bir tuşa basıyorsun → arkadaş listesi/sohbet açılıyor.
Ses modundaki `V` mantığının aynısı. Ayrıca resim linki önizlemesi ve sağ tık
menüleri var.

### ⚠️ Zorunlu bağımlılık

```
PolyLib  (id 6lvkzFFj, slug: polylib)  → 1.21.1 ✅, BSD-4-Clause, 3M indirme
```
CreeperHost'un kendi kütüphanesi. **Bu da kurulmalı.**

### Kurulum — burada dikkat

```
Sunucuya (mods/):        minetogether-neoforge-1.21-6.3.3.jar + polylib
Senin bilgisayarına:     minetogether-neoforge-1.21-6.3.3.jar + polylib
Arkadaşlarına:           aynı ikisi
```
`client_or_server_prefers_both` — **herkeste olmalı.**

### ⚠️ Dürüst uyarılar

| Konu | Durum |
|---|---|
| **Son güncelleme** | **Kasım 2024.** 1.21.1'den sonrasına port edilmemiş. Senin sürümün için sorun değil ama geliştirme durmuş görünüyor |
| **Kendi platformu** | Sohbet CreeperHost'un **MineTogether ağı** üzerinden akıyor, senin sunucundan değil |
| **Kayıt tutmaz** | Sunucun bu DM'leri kaydetmez. "Sunucuda kayıt tutsun" isteğini karşılamaz |
| **Hesap** | MineTogether hesabı gerekiyor |
| **İndirme** | 1.21.1 NeoForge sürümü 2.174 indirme |
| **+2 mod** | MineTogether + PolyLib |

---

# 🎯 GÜNCEL NİHAİ PAKET

Client mod serbest olunca tablo şöyle:

| İstediğin | Mod | Nereye kurulur |
|---|---|---|
| **Tab'da süre/konum/ölüm/kill** | **Tab Info** | ✅ sadece sunucu |
| **Tuşla GUI'de özel sohbet** | **MineTogether + PolyLib** | ⚠️ sunucu **+ herkes** |
| Offline "en son ne zaman girdi" | Player Last Seen (`/seen`) | ✅ sadece sunucu |
| Sunucuda kayıtlı DM + web panel | Paradigm Essentials | ✅ sadece sunucu |

## Kurulum sırası (tek tek, her adımda log oku)

```bash
# ADIM 1 — en güvenli, en çok kazandıran (sadece sunucu)
mods/tab-info-*.jar
mods/seen-0.1.0-neoforge-1.21.1.jar
# → sunucuyu aç, Tab'a bas, /seen test et

# ADIM 2 — sunucuda kayıtlı DM + web panel (sadece sunucu)
mods/Paradigm-neoforge-1.21.1-2.3.1b.jar
# → /msg, /whois, /paradigm dashboard open

# ADIM 3 — GUI'li sohbet şartsa (HERKESE kurulacak)
mods/polylib-*.jar
mods/minetogether-neoforge-1.21-6.3.3.jar

# Her adımdan sonra:
grep -iE "error|conflict|incompatible|failed|exception" logs/latest.log | head -30
```

**Mod artışı:** Adım 1 → +2 · Adım 2 → +1 · Adım 3 → +2 = **toplam +5**
(FTB Essentials/Ranks'ten vazgeçersen +3)

## Son bir dürüstlük notu

**Tab Info kesinlikle kur** — server-only, açık kaynak, tam istediğin veriyi
Tab'a basıyor. Riski yok.

**MineTogether'ı** GUI şartsa kur, ama: Kasım 2024'ten beri güncellenmemiş,
sohbet üçüncü taraf ağdan geçiyor ve **sunucun kaydetmiyor**. Sen "sunucuda
kayıt tutsun" demiştin — o iş için **Paradigm** lazım (chat satırı olarak ama
kalıcı kayıtlı). İkisi farklı ihtiyaç, ikisini birden kurabilirsin.
