# Eksik Gedik — Performans Dışı Katman + Ekstrem Fikirler

> Şimdiye kadarki her doküman **performans** üzerineydi.
> Bu doküman performans DIŞINDA kalan ve gerçekten eksik olan şeyleri
> ve "güzel özellik" fikirlerini içerir.
>
> Öncelik sırası gerçek: 🔴 = bugün kur, 🟡 = yakında, 🟢 = keyif.

---

## 🔴 KRİTİK EKSİK #1 — Backup modu YOK

**Bu listede backup modu hiç yoktu. En büyük açık bu.**

Neden kritik, üç sebep birden:

1. **C2ME alpha aşamasında.** Upstream'in kendi uyarısı birebir:
   > *"C2ME is currently in **alpha** stage and pretty experimental...
   > **backup your worlds**"*
2. Zaten **bozuk chunk yaşadın.** Bir kez olan tekrar olur.
3. MCA Selector ile chunk sileceksin — **yedeksiz chunk silmek geri dönüşsüz.**

Şu an bir şey ters giderse dünyayı kaybedersin. Kabul edilemez.

### Seçenek A — FTB Backups 2  ★ tavsiyem

`curseforge.com/minecraft/mc-mods/ftb-backups-2`
Dosya: `ftbbackups2-neoforge-1.21-1.0.28.jar`

Neden bu:

| Özellik | Neden senin için önemli |
|---|---|
| **Disk alanı kontrolü** | Backup öncesi yeterli alan var mı bakar. Yoksa yapmaz. **Disk dolarken backup almak dünyayı bozar** — bu koruma birebir senin senaryon |
| Cron notasyonlu zamanlama | "Sadece geceleri", "her 2 saatte" gibi tam kontrol |
| Oyuncu yoksa backup almaz | Boş sunucuda disk yakmaz |
| Sessiz mod | Oyunculara spam yok, sadece op görür |
| `/backup snapshot` | Otomatik temizlikten korunan kalıcı yedek |

**MCA Selector'a girmeden önce `/backup snapshot` çek.** Tam da bunun için var.

> Not: FTB Backups **3** de var (1.21.1+ destekliyor) ve yeni özellikler
> oraya gidiyor; 2 artık LTS/sadece-bugfix. 2 hâlâ tamamen sağlam,
> istersen 3'ü kur — mantık aynı.

### Seçenek B — Fastback (incremental, Git tabanlı)

`curseforge.com/minecraft/mc-mods/fastback` · NeoForge destekli

Sadece **değişen** parçaları kaydeder. Zip'lemekten hızlı ve çok daha az
yer kaplar — yani **daha sık** yedek alabilirsin. Dezavantajı: Git tabanlı,
kurtarma FTB'deki "zip'i aç kopyala" kadar aptal-korumalı değil.

**Karar:** Panik anında basit olan kazanır → **FTB Backups.**

### Yedek diskte durmasın

```bash
# Aynı NVMe'de duran yedek, disk ölünce yedek değildir.
rsync -a --delete /path/to/backups/ /mnt/baska-disk/mc-backup/
```
Haftada bir harici diske/başka makineye at. 3-2-1 kuralı.

---

## 🔴 KRİTİK EKSİK #2 — Rollback / grief logu YOK

Oyuncu varsa (Annuus'u düşündüğüne göre var) er ya da geç biri bir şey
patlatır, çalar ya da siler. Backup **tüm dünyayı** geri alır —
"şu adamın son 2 saatte kırdığı blokları" geri alamaz.

**NeoForge'da bu alan zayıf.** Ledger (Fabric standardı) NeoForge'da yok,
Sinytra Connector üzerinden de çalışmıyor. Gerçekten çalışan iki seçenek:

| Mod | Link | Not |
|---|---|---|
| **Indexor** (eski adı "Ledger for Forge") | `curseforge.com/minecraft/mc-mods/ledger-for-forge` | Blok geçmişi, sandık logu, patlama snapshot'ı, oyuncu bazlı rollback. **Tüm ağır işler async** → tick'i bloklamaz. `/ledger inspect` ile bloğa bakıp geçmişini görürsün |
| **GriefLogger + GLRA** | `modrinth.com/mod/glra` | GLRA açıkça **NeoForge 21.1.213 / MC 1.21.1** hedefliyor — sürüm uyumu net. Tick başına batch işler, chunk'ı yüklediğinden emin olur |

**Tavsiyem: Indexor.** Tek mod, rollback dahil, async.

⚠️ İkisi de SQLite'a yazar → **NVMe'nde ekstra IO.** C2ME `ioSystem`
zaten diski kullanıyor. Kurduktan sonra `/spark tps` ile bir kez doğrula.

---

## 🟡 EKSİK #3 — İzin sistemi (op vermeden yetki)

Şu an tek yetki mekanizman `op`. Op vermek = **her şeyi** vermek,
`/stop` dahil. Arkadaşına "sadece /tpa kullanabilsin" diyemiyorsun.

**LuckPerms** — `LuckPerms-NeoForge-5.4.140.jar` (MC 1.21–1.21.1)
`modrinth.com/plugin/luckperms`

Grup yap (`player`, `builder`, `admin`), her gruba sadece gerekeni ver.
`/lp editor` ile tarayıcıda sürükle-bırak düzenlersin.

⚠️ **Bilinen sorun:** LuckPerms issue #3963 — NeoForge'da bazı mod
komutlarıyla *"Capability has not been initialised"* hatası (Mekanism ile
raporlanmış). 5.4.140 eski bir sürüm (1.21.1 için son). Kurunca ilk gün
mod komutlarını bir kez test et.

Performans etkisi: **sıfır.** Sadece login'de izin okur.

---

## 🟡 EKSİK #4 — Dünya sınırı (world border)

Bu, **performansı doğrudan ilgilendiren** ve listede olmayan tek şey.

Sınır yoksa oyuncu 50.000 blok uzağa yürür, sonsuza kadar **yeni chunk
ürettirir.** C2ME'nin en pahalı işi tam olarak bu. Sınır koyarsan:

- Chunky ile **bir kez** pregen edersin, sonra worldgen maliyeti ~sıfır
- Disk boyutu tahmin edilebilir olur
- Chunk duvarı riski biter (herkes aynı üretilmiş alanda)

```
/worldborder set 12000        # merkez 0,0 → ±6000 blok
/worldborder warning distance 100
```

Sonra Chunky'yi sınırdan besle — elle radius girmekten iyi:
```
/chunky worldborder
/chunky start
```

**Nether'i unutma:** 8:1 oranı yüzünden Nether sınırı `12000/8 = 1500`
olmalı. Yoksa oyuncu Nether'den sınırın dışına çıkar.
```
/chunky world minecraft:the_nether
/chunky radius 1500
/chunky start
```

### Pregen radius kararı (senin donanımın)

Topluluk tavsiyesi 5.000–10.000 arası başlamak. Chunky wiki'nin kendi
sözü: *"If in doubt start with a smaller radius like 5000."*

| Radius | Chunk | Yorum |
|---|---|---|
| 3000 | ~112 K | Küçük grup, hızlı biter |
| **5000** | ~312 K | ★ **Başlangıç için doğru yer** |
| 10000 | ~1.25 M | Disk ve süre ciddi artar |

**Ekstrem uyarı:** i5-9400F 6 çekirdek. Pregen sırasında CPU **%100**
olacak. Oyuncular varken başlatma — Chunky wiki de "before players join"
diyor. Gece başlat, sabah bak.

---

## 🟢 GÜZEL ÖZELLİK #1 — Web haritası (BlueMap)

Sunucunun 3D haritası, tarayıcıdan gezilebilir. Google Earth gibi.
Oyuncuların en çok "vay be" dediği şey budur.

`curseforge.com/minecraft/mc-mods/bluemap` — **server-only mod**,
oyuncunun bir şey kurmasına gerek yok, linke tıklar.

Resmî sözü:
> *"BlueMap renders **asynchronously** to your MinecraftServer-Thread.
> At no time will it block your server-thread directly."*

🔴 **AMA — senin donanımında ciddi uyarı var.** Cümlenin devamı:
> *"...**as long as your CPU is not fully utilized**"*

Sende 6 çekirdek/6 thread var ve C2ME zaten `globalExecutorParallelism = 5`
ile bunları kullanıyor. BlueMap'in ilk tam render'ı **saatlerce %100 CPU**
demek. Async olması "bedava" demek değil — **boş çekirdek yoksa async
işe yaramaz.**

**Yapılacak sıra (bu sırayı bozma):**
1. Önce Chunky pregen'i **bitir**
2. Sonra BlueMap'i kur, ilk render'ı **gece / oyuncusuz** çalıştır
3. `core.conf` → render thread sayısını **2'de sınırla** (varsayılan tüm çekirdekler)
4. İlk render bitince sürekli maliyet çok düşük (sadece değişen chunk)

Alternatif hafif: **Dynmap** (2D, daha az CPU ama daha çirkin).

---

## 🟢 GÜZEL ÖZELLİK #2 — Proximity voice chat

**Simple Voice Chat** — mesafeye göre sesli konuşma. Yanındakini duyarsın,
uzaklaşınca sesi kısılır. Bir SMP'yi en çok değiştiren tek mod budur.

`modrinth.com/mod/simple-voice-chat` (NeoForge 1.21.1 var)

🔴 **Port uyarısı — 1 numaralı kurulum hatası:**
Ses trafiği **UDP 24454** üzerinden gider. Oyun portu (25565 TCP) ayrı.
Router/firewall'da **ikisini birden** açman lazım:
```bash
sudo ufw allow 25565/tcp
sudo ufw allow 24454/udp
```
Açmazsan mod yüklenir, kimse konuşamaz ve sebebini bulamazsın.

⚠️ **Oyuncuların da client'a kurması gerekir** (Annuus gibi).
Sunucu CPU maliyeti düşük — ses paketleri ana thread'e girmez.

---

## 🟢 GÜZEL ÖZELLİK #3 — Distant Horizons (EKSTREM)

İstediğin "ekstrem şey" buysa: oyuncular **binlerce blok** öteyi görür.
Uzak arazi düşük detaylı (LOD) model olarak çizilir. Görsel olarak
akılalmaz — dağın tepesine çıkıp ufku görmek gibi.

DH **2.3+** ile artık **sunucu tarafı** çalışıyor: sunucu LOD üretip
client'lara gönderiyor, herkes aynı manzarayı görüyor.

🔴 **Ama senin durumunda kurma. Şimdilik.** Üç sebep:

1. **Chunky ile birlikte tehlikeli.** DH geliştiricisinin kendi sözü:
   > *"When using chunky, you should **remove DH from the mods folder**
   > and add it back when you finish. That is the only method that works
   > 100% of the time."*
   Devamı daha net: DH'yi bırakırsan *"a risk of holes in LODs"* ve
   **"chance for corruption"**. Sen zaten chunk bozulmasından yeni çıktın.
2. Sunucu tarafı desteği hâlâ **deneysel** — DH ekibi büyük sunucularda
   önermiyor.
3. LOD üretimi **CPU ister**. 6 çekirdeğin zaten C2ME'de.

**Doğru sıra:** pregen bitsin → dünya stabil olsun → 1 ay sorunsuz
geçsin → *sonra* DH'yi düşün.

---

## 📋 SONUÇ — ne yapacaksın

### Bugün (30 dakika)
```
1. FTB Backups 2 kur, cron ayarla, bir kez /backup start ile test et
2. /backup snapshot  ← MCA Selector'a girmeden ÖNCE
3. MCA Selector ile bozuk chunk'ları temizle
```

### Bu hafta
```
4. /worldborder set 12000   (+ Nether 1500)
5. Chunky pregen: radius 5000, GECE, oyuncusuz
6. Indexor (rollback) kur → /spark tps ile IO etkisini doğrula
7. LuckPerms kur, mod komutlarını test et
```

### Keyif (pregen bittikten SONRA)
```
8. Simple Voice Chat  (+ UDP 24454 aç!)   ← en yüksek "vay be"/maliyet oranı
9. BlueMap, render thread = 2, ilk render gece
```

### Şimdilik hayır
```
✗ Distant Horizons  → pregen + 1 ay stabilite sonrası
```

---

## Neden bu doküman performans modu içermiyor

Çünkü **performans tarafında gerçek bir boşluk kalmadı.** `BOSLUK-ANALIZI.md`
zaten Moonrise'ın 11 maddesini tek tek karşıladı; kalan tek açık
"reduce TPS catchup" ve onun NeoForge 1.21.1'de karşılığı yok.

Daha fazla optimizasyon modu eklemek bu noktadan sonra **negatif getiri**:
her mod bir mixin, her mixin bir çakışma riski. Buradan sonraki en büyük
performans kazancı mod değil, **Chunky pregen + world border** — yani
yukarıdaki 4 ve 5 numara.

Asıl eksik performans değildi: **yedek, rollback ve izin.** Yani sunucuyu
hızlı tutmak değil, **kaybetmemek.**
