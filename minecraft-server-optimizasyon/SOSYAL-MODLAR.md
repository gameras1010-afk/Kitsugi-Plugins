# SOSYAL MODLAR — Oyuncu Takibi + Özel Sohbet

**Soru:** Sunucudaki kişilerin en son ne zaman girdiğini kayıt altında tutan,
"şu saatte oyundaydı" diyen bir mod + etkileşim sayfası var mı? Bir de
kullanıcı seçip özel sohbet edebileceğim bir mod?

**Kısa cevap:** İkisi de var. Ama **özel sohbet için mod kurmana muhtemelen
gerek yok — o özellik Minecraft'ta zaten var** (aşağıda B0). Asıl kuracağın
şey oyuncu takibi.

Hepsi 1.21.1 NeoForge için doğrulandı. Tarih: 2026-08-14.

---

# A) OYUNCU TAKİBİ — "En son ne zaman girdi?"

## A0. Önce kararı ver: hangi seviyede takip istiyorsun?

Üç farklı seviye var, ihtiyacına göre biri yeterli:

| Seviye | Ne verir | Önerilen |
|---|---|---|
| **1. Basit** | Oyun içi `/seen Ahmet` → "2 gün önce girdi" | **Player Last Seen** |
| **2. Oynanış süresi** | Kim kaç saat oynadı, günlük/haftalık, sıralama | **Server Playtime Tracker** |
| **3. Web paneli** 🌐 | Tarayıcıda açılan grafik/istatistik sayfası | **Player Statistics** ⚠️ (uyarı var) |

**Tavsiyem: 1 + 2'yi kur, 3'ü atla.** Sebebini A3'te yazdım.

---

## A1. 🔴 Player Last Seen — `/seen` komutu (EN ÇOK İSTEDİĞİN ŞEY)

**Bu tam olarak tarif ettiğin şey.** Vanilla'da olmayan "last seen" özelliği.

```
/seen Ahmet   → Ahmet en son 2026-05-15 14:30'da görüldü (yaklaşık 1 gün önce).
                ayrıca görüldü: 2026-05-13 22:10 (yaklaşık 3 gün önce)
/seen Mehmet  → Mehmet şu anda oyunda.
```

| Özellik | Değer |
|---|---|
| Sürüm | **1.21.1 NeoForge ✅** (Forge ve Fabric de var) |
| Taraf | **Sadece sunucu** — arkadaşların hiçbir şey kurmuyor |
| Bağımlılık | **Yok** |
| Kayıt | Oyuncu başına **son 3 giriş**, restart'ta silinmiyor |
| Erişim | Herkese açık (EssentialsX'teki `/seen` gibi) |

**Neden bunu seçtim:** Mixin yok, config yok, blok/eşya eklemiyor. Sadece bir
login/logout dinleyicisi + kalıcı veri + tek komut. **237 modun arasına
girdiğinde çakışma ihtimali pratikte sıfır.** Senin modpack'in kadar dolu bir
kurulumda bu çok önemli.

🔗 https://modrinth.com/mod/player-last-seen

⚠️ **Bilmen gereken:** `/seen` herkese açık — yani arkadaşların birbirinin ne
zaman online olduğunu görebiliyor. Küçük bir arkadaş grubuysa sorun değil,
ama "kimse kimseyi izlemesin" istiyorsan bu mod uygun değil.

⚠️ **Tek eksiği:** Sadece **son 3** giriş tutuyor. Aylık geçmiş arşivi
istiyorsan A2'ye bak.

---

## A2. 🟡 Server Playtime Tracker — kim ne kadar oynadı

`/seen` "ne zaman girdi"yi söylüyor, bu da **"ne kadar oynadı"yı**.

```
/playtime                    → toplam süren + bu oturum
/playtime today              → bugün ne kadar oynadın
/playtime Ahmet              → Ahmet'in toplam süresi (offline olsa bile)
/playtime Ahmet history      → Ahmet'in son 7 günü
/playtime leaderboard        → en çok oynayan 10 kişi
/playtime Ahmet day 2026-08-10 → belirli bir gündeki süresi
```

| Özellik | Değer |
|---|---|
| Sürüm | **1.21.1 NeoForge ✅** (`playtimetracker-neoforge-1.21.1-1.0.1.jar`) |
| Taraf | **Sadece sunucu** |
| Kayıt | World klasöründe **JSON**, 5 dakikada bir otomatik kayıt |
| Ekstra | Gece yarısı geçişinde süreyi iki güne bölüyor |

⚠️ **Kurulumdan sonra mutlaka yap:** Saat dilimi varsayılan
**America/New_York**. Türkiye saati için config'den düzelt, yoksa "bugün"
hesabı 7 saat kayık olur.

⚠️ **Emin değilim:** Config dosyasının tam adını/yolunu doğrulayamadım
(proje sayfasında yazmıyor). İlk açılıştan sonra `config/` klasörüne bak,
saat dilimi ayarı orada olacak.

🔗 https://www.curseforge.com/minecraft/mc-mods/server-playtime-tracker

---

## A3. 🌐 "Etkileşim sayfası" (web paneli) — dikkat

Web arayüzü istediğini yazmışsın. Burada dürüst olayım:

### Player Statistics — istediğin sayfa bu, ama…

Web sayfası mod'un **içinde geliyor**. Sunuyor:
- Genel sunucu istatistikleri (oyuncu sayısı, toplam süre, üretilen eşya…)
- **Hall of Fame** — TOP 15 oyuncu
- **Tüm oyuncular + en son ne zaman online oldukları** (arama & sıralama)
- Oyuncu başına detay sayfası, mobil uyumlu

🚨 **Ama: Fabric-only, en son 1.21.4.** NeoForge sürümü **yok**.
**Senin sunucuna kurulamaz.** Aradığın şeye en çok benzeyen bu, o yüzden
yazdım — ama olmuyor.

### Plan (Player Analytics) — sektör standardı, o da olmuyor

En bilinen analiz aracı. Web paneli, aktivite ısı haritaları, retention
grafikleri… **Fabric ve Bukkit/Spigot var, NeoForge yok.** r/admincraft'ta
Forge kullanıcıları yıllardır aynı cevabı alıyor: "Forge için yapmıyorlar."

### ✅ Zaten sende olan çözüm: Crafty Controller

**`UZAKTAN-YONETIM.md`'de kurmayı planladığımız Crafty Controller
web panelinde bu var:** oturum geçmişi, oyuncu listesi, kimin ne zaman
bağlandığı — hepsi tarayıcıdan, `https://sunucu:8443`.

Yani ayrı bir "istatistik web modu" kurmana **gerek yok.** Crafty'yi kur,
web tarafı hallolur. `/seen` + `/playtime` de oyun içi tarafı kapatır.

⚠️ **Emin değilim:** Crafty'nin oyuncu geçmişi ekranının ne kadar detaylı
olduğunu (grafik var mı, kaç gün geriye gidiyor) test etmedim. Kurunca
bakarsın — ama en azından "kim ne zaman girdi" bilgisi panelde var.

---

## A4. Elemediğim ama seçmediklerim — neden

| Mod | Neden seçmedim |
|---|---|
| **Last Played Logger** | 1.21.1 NeoForge ✅ **var** ve 12.4K indirme ile en olgunu. **Ama Google Sheets API kurulumu gerekiyor**: Google Cloud projesi, OAuth, `credentials.json`, ilk açılışı masaüstünde yapma… Sırf "en son ne zaman girdi" için bu zulüm. Google tablosunda görmek istersen değer, yoksa `/seen` çok daha kolay |
| **Player Logger** | 1.21.1 NeoForge ✅ ama **MySQL zorunlu** + geliştiricinin kendi notu: *"bu bir üniversite ödevi"* + *"veritabanı bağlanamazsa sunucu durabilir"*. **Sunucunu riske atma** |
| **IntegratedPlaytime** | Özellik canavarı (33 rütbe, AFK tespiti, GUI, LuckPerms). **Ama Forge 1.20.1 — NeoForge 1.21.1 yok** |
| **PlaytimeLogger** | Fabric 1.20.1 |
| **ForgeDash** | NeoForge web paneli, oyuncu takibi + oturum geçmişi var. **Ama GitHub'da, CurseForge/Modrinth'te değil; MC sürümü belirtilmemiş.** Crafty varken riske girme |

---

# B) ÖZEL SOHBET (DM)

## B0. 🚨 ÖNCE BUNU OKU: Bu özellik zaten oyunda var

Mod aramadan önce şunu dene:

```
/msg Ahmet selam kanka
/tell Ahmet selam
/w Ahmet selam
```

**Bu komutlar vanilla Minecraft'ta var ve çalışıyor.** Sadece o kişi görür.

**Yani "kullanıcı seçip özel sohbet" özelliği için mod kurman gerekmeyebilir.**
Önce bunu test et. Eksik bulduğun bir şey varsa aşağıya bak.

Vanilla `/msg`'de olmayan şeyler:
- ❌ `/r` (son yazana hızlı cevap) — her seferinde ismi yazman gerekir
- ❌ Kapalı listeden oyuncu seçme (menü/GUI)
- ❌ Bildirim sesi
- ❌ Birini susturma / rahatsız etmeyin modu
- ❌ **Kayıt tutma** (sen "sunucuda kaydını tutabilecek şekilde" demiştin)

Bunlardan biri lazımsa devam et.

---

## B1. 🔴 En pratik: FTB Essentials (zaten kurulacaklar listesinde!)

`MOD-ONERILERI.md`'de zaten önerdiğim **FTB Essentials** DM komutlarını
getiriyor — `/msg`, `/r` dahil. **Yeni mod kurmadan** vanilla `/msg`'nin
eksiklerinin çoğu kapanıyor.

**Ayrıca `/commandspy` özelliği var** — istediğin "kayıt" işini kısmen görür:
admin olarak oyuncuların çalıştırdığı komutları görebilirsin.

⚠️ **Ama dikkat:** FabricEssentials'ın config'inde `msg`/`tell`/`w`
varsayılan olarak **commandspy'dan muaf** tutuluyor (gizlilik için).
FTB Essentials'ta da benzer bir ayar olması muhtemel.

⚠️ **Emin değilim:** FTB Essentials'ın 1.21.1 NeoForge sürümünde `/msg` ve
`/r` komutlarının **kesin olarak** bulunduğunu resmî komut listesinden
doğrulayamadım — FTB'nin wiki'si komut listesini tam vermiyor. Zaten kuracağın
mod olduğu için **önce kur, `/msg` ve `/r`'yi dene**, sonra karar ver.

---

## B2. 🟡 GUI'li DM istiyorsan: RpEssentials

Tam bir `/msg` sistemi + üstüne çok şey:

```
/msg, /tell, /w, /whisper  → özel mesaj
/r <mesaj>                 → son yazana cevap
```
- Mesajlarda **"Cevaplamak için tıkla"** butonu
- LuckPerms prefix/suffix + renk kodu desteği
- **`/whois` ve "Last Connection" (son bağlantı) sistemi** ← A bölümündeki
  takip ihtiyacını da kısmen karşılıyor
- Uyarı (warn) sistemi, staff moderasyon araçları, **loglama**

| Özellik | Değer |
|---|---|
| Sürüm | **1.21.1 NeoForge 21.1.219+ ✅** (`rpessentials-4.2.0.jar`) |
| Taraf | Client & Server |
| Bağımlılık | Zorunlu yok (LuckPerms/Curios opsiyonel) |
| Config | Çalışırken yeniden yüklenebiliyor (`/rpessentials config reload`) |

🚨 **Ciddi uyarı:** Bu bir **rol yapma (RP) sunucu modu**. Yanında meslek/lisans
sistemi, mesafeye göre isim gizleme, ölüm RP'si, bölge sistemi geliyor. Sen
sadece DM istiyorsan **çok ağır kaçar** ve 237 modun arasında çakışma yüzeyi büyük.
Ayrıca lisansı **All Rights Reserved**.

**Sadece "DM + son bağlantı kaydı"nı bir arada tek modda istiyorsan** mantıklı.
Yoksa B1 yeter.

🔗 https://www.curseforge.com/minecraft/mc-mods/rp-essentials

---

## B3. ❌ Private Chat (YacBek) — İSTEDİĞİN BU, AMA KURULAMAZ

Tarif ettiğin şeye **birebir uyan** mod bu:
- **Y tuşu** → menü açılıyor, online oyuncu listesinden birini seçiyorsun
- Mesaj gelince **sesli pop-up bildirim**
- Okunmamış mesajda **yeşil nokta**
- **R tuşu** → hızlı cevap
- Rahatsız Etmeyin (DND) modu, oyuncu susturma

🚨 **Ama tek dosyası var: `Private Chat - 1.0.0 - (Forge).jar`, Minecraft
1.20.6, sadece Forge.** NeoForge 1.21.1 sürümü **yok**. Dosya listesini
kontrol ettim — 1 dosya, 1.20.1–1.20.6 arası.

**Kuramazsın.** Ama aradığın tam olarak buysa CurseForge'da projeyi takibe al,
belki günceller. (Toplam 124 indirme — pek umutlanma.)

---

## B4. Diğerleri (neden olmadı)

| Mod | Durum |
|---|---|
| **Private Messages** (Son1kX) | Çok iyi özellikler: `/ignore`, notlar, **offline mesaj**, şifreli veri. **Ama Fabric 1.21.8** — NeoForge yok |
| **Client Chat Channels** | Client-side, kanalları `/msg`'ye çeviriyor. Herkesin kurması gerekir |
| **CustomMessage / SimpleMessage / DirectMessage** | Hepsi **Bukkit/Spigot plugin'i**. NeoForge sunucuda çalışmaz |

---

# C) SONUÇ — Ne yapacaksın

## Kesin öneri (2 jar, 5 dakika)

| # | Mod | Ne için | Sürüm |
|---|---|---|---|
| 1 | **Player Last Seen** | `/seen Ahmet` → en son ne zaman girdi | 1.21.1 NeoForge ✅ |
| 2 | **Server Playtime Tracker** | `/playtime` → kim kaç saat oynadı | 1.21.1 NeoForge ✅ |

İkisi de **server-only**, arkadaşların hiçbir şey kurmuyor. Bağımlılık yok.

## Özel sohbet için

1. **Önce `/msg Ahmet selam` yaz.** Çalışıyorsa iş bitti, mod kurma.
2. `/r` eksikliği rahatsız ediyorsa → **FTB Essentials** (zaten kurulacaktı)
3. Menüden seçmeli GUI şartsa → maalesef 1.21.1 NeoForge'da **yok**

## Web paneli için

**Crafty Controller'ı kur** (`UZAKTAN-YONETIM.md`). NeoForge 1.21.1 için
oyuncu istatistiği web modu **yok** — Plan da Player Statistics de Fabric.

## Mod sayısı

237 → **239**. `MOD-ONERILERI.md`'deki 6 mod da kurulursa **245**.

---

# D) KURULUM

```bash
# 1. Sunucuyu durdur
# 2. İki jar'ı mods/ klasörüne at
# 3. Sunucuyu aç, logu kontrol et:
grep -iE "error|conflict|incompatible|failed" logs/latest.log | head -20
```

**Tek tek kur.** Önce Player Last Seen, sunucuyu aç, logu kontrol et, sonra
diğeri. İkisini birden atıp sorun çıkarsa hangisi olduğunu bilemezsin.

**Test:**
```
/seen <arkadaşının_adı>
/playtime
/msg <arkadaşının_adı> test
```

⚠️ **Player Last Seen'i tek kişilik dünyada test ediyorsan:** dünyadan çıkıp
tekrar girmen gerekiyor, yoksa veri boş görünür (geliştiricinin kendi notu).

---

# E) KAYNAKÇA

| Konu | Kaynak |
|---|---|
| Player Last Seen | https://modrinth.com/mod/player-last-seen |
| Server Playtime Tracker | https://www.curseforge.com/minecraft/mc-mods/server-playtime-tracker |
| RpEssentials | https://www.curseforge.com/minecraft/mc-mods/rp-essentials |
| Private Chat (1.20.6 Forge) | https://www.curseforge.com/minecraft/mc-mods/private-chat/files/all |
| Player Statistics (Fabric) | https://www.curseforge.com/minecraft/mc-mods/player-statistics |
| Last Played Logger | https://www.curseforge.com/minecraft/mc-mods/last-played-logger |
| Player Logger | https://www.curseforge.com/minecraft/mc-mods/player-logger |
| Plan / Player Analytics | https://www.curseforge.com/minecraft/mc-mods/plan-player-analytics |
| FTB Essentials changelog | https://github.com/FTBTeam/FTB-Essentials/blob/main/CHANGELOG.md |
| ForgeDash | https://github.com/Framepersecond/ForgeDash |

**Doğrulama yöntemi:** Her modun CurseForge/Modrinth **dosya listesi**
kontrol edildi — sadece açıklamadaki sürüm iddiasına güvenilmedi.
Private Chat'in 1.21.1 sürümü olmadığı bu şekilde tespit edildi.
