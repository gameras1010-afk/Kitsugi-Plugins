# Mod Önerileri — 237 Modluk Kurulumunda Ne Eksik?

> **Analiz edilen:** 237 mod + 42 shader, 1.21.1 NeoForge
> **Yöntem:** Listeni kategorize ettim, sonra hangi kategorinin **tamamen boş**
> olduğuna baktım. Zaten sahip olduğun şeyin muadilini önermiyorum.

---

## Kısa Cevap (uzun okumak istemiyorsan)

Listende **oyun içeriği doymuş durumda.** 60+ içerik modu, 12 Yung's yapı modu,
5 Macaw seti, Twilight Forest + Aether + BetterEnd + BetterNether, Apotheosis,
Terralith + BOP + BOWG... İçerik tarafına bir şey eklemek **katkı değil, risk.**

Boş olan tek yer şu: **çok oyunculu sunucu altyapısı.**

| Kategori | Listendeki durum |
|---|---|
| İçerik / yapı / mob | 🟢 Doymuş (60+ mod) |
| Performans | 🟢 Doymuş (C2ME, Lithium, ModernFix, FerriteCore, ServerCore...) |
| Client QoL | 🟢 Doymuş (JEI, Jade, Journeymap, IPN...) |
| **Yedekleme** | 🔴 **HİÇ YOK** |
| **Arazi koruma (claim)** | 🔴 **HİÇ YOK** |
| **Kim ne kırdı (logging/rollback)** | 🔴 **HİÇ YOK** |
| **Yetki sistemi** | 🔴 **HİÇ YOK** |
| **`/home` `/tpa` `/rtp`** | 🔴 **HİÇ YOK** |
| **Web haritası** | 🔴 **HİÇ YOK** |

**Sadece 3 mod kur, gerisi lüks:**
1. **FTB Backups 3** — yedek yok, bu bir zaman bombası
2. **CoreProtectNeo** — kim ne kırdı/aldı, geri al
3. **FTB Essentials + Teams + Chunks** — `/home`, `/tpa`, arazi koruma

---

# BÖLÜM 1 — MUTLAKA KURULMASI GEREKENLER

## 🔴 1. FTB Backups 3 — Yedek

**Bu listede yedek modu YOK.** 237 modluk bir kurulumda bu, "arabada fren yok"
demek. Modlardan biri güncellenince, bir chunk bozulunca ya da biri kazara
`/fill` yapınca dönecek yerin yok.

r/admincraft'ta tam bu soru soruluyor ve cevap net:

> *"Honestly there's no real mod that 'prevents NBT corruption' reliably.
> The actual answer is just FTB Backups 2 with frequent snapshots. On a public
> modpack corruption will happen eventually, and being able to roll back a
> single region instead of nuking the whole world is what saves you."*

**Hangisi:** FTB Backups **3** (1.21.1+ için aktif geliştirilen sürüm).
FTB Backups 2 artık LTS — sadece bugfix alıyor.

- 🔗 https://www.curseforge.com/minecraft/mc-mods/ftb-backups-3
- **Bağımlılık:** yok (FTB Library zaten sende var)
- **Taraf:** sadece sunucu

**Neden bu:** Diskte yer kalmadığında yedek almayı reddediyor. Bu önemli —
disk dolarken yedek almak dünyayı bozar. Ayrıca cron notasyonuyla zamanlama
ve `/backup snapshot` ile silinmeyen manuel yedek var.

```
/backup create      → hemen yedek al
/backup snapshot    → otomatik temizlikten korunan yedek
```

**Alternatif:** Advanced Backups (Modrinth) — 1.21.1 NeoForge destekli,
differential backup yapıyor. FTB Library'n zaten var diye FTB'yi öneriyorum.

> ⚠️ **Crafty Controller kuracaksan** (bkz. `UZAKTAN-YONETIM.md`): Crafty'nin
> kendi yedeği de var. **İkisini aynı anda çalıştırma** — aynı anda dünya
> dosyalarını okurlarsa yedek bozuk çıkar. Birini seç.

---

## 🔴 2. CoreProtectNeo — Kim Ne Kırdı, Geri Al

Bu, arkadaş grubunda **yedekten daha sık işine yarayacak** mod.

Yedek "her şeyi 3 saat öncesine döndür" der. Ama senin sorunun genelde
"kim bodrumu su bastı" ve "sandıktan elmaslar nereye gitti" olacak. Bunlara
sadece bir logger cevap verir.

**NeoForge'da bu boşluk uzun süre boştu.** Ledger (Fabric/Quilt) NeoForge'a
port edilmedi — GitHub issue #336'da bu açıkça yazıyor:

> *"At the moment, there is no mod for NeoForge that can log and roll back
> actions. Ledger does not work through Sinytra Connector."*

Ama artık **CoreProtectNeo** var — özellikle NeoForge 1.21.1 için yazılmış:

- 🔗 https://modrinth.com/mod/coreprotectneo
- **Taraf:** **sadece sunucu** — arkadaşlarının kurmasına gerek yok
- **Veritabanı:** SQLite, yerel. MySQL kurmana gerek yok.

```
/co i                          → inspector aç, bloğa tıkla, geçmişini gör
/co near 10                    → çevrendeki son hareketler
/co rollback area 20 2h        → 20 blok yarıçapında son 2 saati geri al
/co rollback inventory 1h      → envanteri geri al
```

**Neden bu, Ledger değil:** Ledger NeoForge'da çalışmıyor. Modrinth'te
"Indexor" (Ledger for Forge) diye bir alternatif de var ve NeoForge
destekliyor — ama CoreProtectNeo özellikle 1.21.1 NeoForge için yazılmış
ve container/envanter loglaması per-slot çalışıyor.

> ⚠️ **Disk uyarısı:** Blok loglaması yer kaplar. 500 GB NVMe'nde sorun
> olmaz ama config'den log saklama süresini 30 güne indirmen mantıklı.

**Alternatif:** Indexor (`ledger-for-forge`) — Forge/NeoForge/Fabric üçünü de
destekliyor, `/ledger rollback` öncesi **önizleme** gösteriyor. Bu özellik
CoreProtectNeo'da yok ve gerçekten faydalı. İkisinden birini seç, ikisini
birden kurma.

---

## 🔴 3. FTB Essentials + FTB Teams + FTB Chunks — Komutlar ve Arazi

Listende `ftb-library`, `ftb-quests`, `ftb-teams` **zaten var.** Yani altyapının
yarısı kurulu, sadece iki mod eksik.

### FTB Essentials — `/home`, `/tpa`, `/rtp`, `/back`

```
/sethome üs          /home üs
/tpa oyuncu          /tpaccept
/back                → son öldüğün yere dön
/rtp                 → rastgele ışınlanma
/spawn               /warp
```

Bunlar olmadan arkadaşların koordinat yazıp yürüyor. 237 modluk bir dünyada
bu işkence.

- 🔗 https://www.curseforge.com/minecraft/mc-mods/ftb-essentials
- **Bağımlılık:** FTB Library ✅ (sende var)

> ⚠️ **EssentialsX kurmaya çalışma.** O bir Bukkit/Paper *plugin*'i, NeoForge
> *mod*'u değil. `mods/` klasörüne atarsan hiçbir şey olmaz.

### FTB Chunks — Arazi Koruma

FTB Teams **zaten sende var** ama tek başına claim yapmıyor — sadece takım
sistemi. FTB Chunks onun üstüne claim'i ekliyor.

- 🔗 https://www.curseforge.com/minecraft/mc-mods/ftb-chunks
- **Sürüm:** `2101.1.14` (1.21.1 NeoForge)
- **Bağımlılık:** FTB Library ✅ + FTB Teams ✅ (ikisi de sende var)

> 🚨 **FORCE-LOAD TUZAĞI — bunu okumadan kurma.**
>
> FTB Chunks varsayılanları: oyuncu başına **500 claim + 25 force-load chunk**,
> ve parti modu üyelerin hakkını **toplayabiliyor.** 5 kişilik bir takım
> kalıcı olarak **125 force-loaded chunk** tutar.
>
> Senin i5-9400F'inde bu TPS'i yere çakar. C2ME'yi bu yüzden kurmadın.
>
> **Kurar kurmaz config'i değiştir:**
> ```toml
> # config/ftbchunks/ftbchunks-server.snbt
> max_claimed_chunks: 200
> max_force_loaded_chunks: 5      # 25 DEĞİL
> ```

### Alternatif: Open Parties and Claims

FTB'yi sevmiyorsan tek modda claim + parti veriyor. **Ama:** hem sunucuya hem
**her oyuncunun client'ına** kurulması gerekiyor. FTB Chunks'ta bu şart değil.
FTB Teams zaten sende olduğu için FTB Chunks daha az iş.

---

# BÖLÜM 2 — ÇOK İŞE YARAYACAKLAR

## 🟡 4. BlueMap — Web Haritası

Tarayıcıdan 3D dünya haritası. Arkadaşların kimin nerede olduğunu, kimin ne
inşa ettiğini görür. Journeymap'in yaptığı iş değil bu — Journeymap kişisel
minimap, BlueMap **paylaşılan** harita.

- 🔗 https://github.com/BlueMap-Minecraft/BlueMap/releases
- **Sürüm:** 1.21.1 için son destekli sürüm **v5.7**
- **Port:** 8100 (yapılandırılabilir)
- **Taraf:** sadece sunucu

**Tailscale ile mükemmel uyuyor** — port forward etmene gerek yok:

```json
// Tailscale ACL'ine ekle
{ "src": ["autogroup:shared"], "dst": ["tag:mcserver"],
  "ip": ["tcp:25565", "udp:24454", "tcp:8443", "tcp:8100"] }
```

> ⚠️ **İlk render CPU yer.** 6 çekirdeğin var ve MC sunucusu zaten aç.
> `core.conf` → `render-thread-count: 2` yap ve ilk render'ı sunucu
> kapalıyken çalıştır. Sonrasında sadece değişen chunk'ları günceller,
> yükü hafif olur.

> ⚠️ Distant Horizons + BlueMap + 42 shader = disk dolabilir. `500 GB`'ın var
> ama BlueMap render'ı büyük dünyalarda 10-30 GB olabiliyor.

---

## 🟡 5. FTB Ranks — Yetki Sistemi

Şu an sunucuda ya **OP'sun ya da hiçbir şey.** Ara kademe yok. Arkadaşına
`/tp` vermek istiyorsan OP vermen gerekiyor — o da `/gamemode creative`
yazabiliyor demek.

FTB Ranks bunu çözer, hem FTB Essentials'la hem FTB Chunks'la konuşur:

```
/ranks add vip
/ranks permission add vip ftbessentials.home.max 5
/ranks permission add vip ftbchunks.max_claimed 300
/ranks add_player Ahmet vip
```

- 🔗 https://www.curseforge.com/minecraft/mc-mods/ftb-ranks
- **Bağımlılık:** FTB Library ✅

**Alternatif: LuckPerms.** Daha güçlü, endüstri standardı, web editörü var.
Ama FTB paketini zaten kuruyorsan FTB Ranks daha az sürtünme. LuckPerms'i
seçersen FTB Chunks ile konuşması için **FTB XMod Compat** de lazım.

---

## 🟡 6. Spark — Zaten Sende Var, Ama Kullanmıyorsun

`spark-1.10.124-neoforge.jar` listende **var.** Ama daha önce "sunucu yavaş"
derken hiç spark raporu paylaşmadın.

Bir daha lag olduğunda tahmin yürütme, ölç:

```
/spark profiler start --timeout 300
# ... 5 dakika oyna, lag'i yaşa ...
/spark profiler stop
```

Çıkan linki bana at, hangi modun yediğini tam olarak görürüz. `NEDEN-YAVAS.md`
ve `SES-CHAT-TESHIS.md`'de yaptığımız tahmin yürütmelerin yerine bu geçer.

---

# BÖLÜM 3 — LİSTENDE GÖRDÜĞÜM SORUNLAR

Bunlar öneri değil, **uyarı.** Mod eklemeden önce bunlara bak.

## 🚨 A. `adorabuild-structures-2.11.0-neoforge-1.21.3.jar` — YANLIŞ SÜRÜM

Dosya adında **`1.21.3`** yazıyor. Senin sunucun **1.21.1.**

1.21.3 ile 1.21.1 arasında registry değişiklikleri var. Bu mod ya hiç
yüklenmiyor (ve sen fark etmedin), ya da sessizce bozuk davranıyor.

```bash
grep -i "adorabuild" logs/latest.log
```

Doğru sürümü indir ya da kaldır.

## 🚨 B. `more_mobs-v1.5.10-mc1.14-26.2.9-mod.jar` — ÇOK ŞÜPHELİ

Dosya adında **`mc1.14`** geçiyor. 1.14 modu 1.21.1'de çalışmaz. `26.2.9`
kısmı da tuhaf. Bu dosyanın ne olduğunu doğrula, muhtemelen yanlış indirilmiş.

## ⚠️ C. Sinytra Connector — Sunucuda Riskli

Listende `connector-2.0.0-beta.16` + `ConnectorExtras` + `forgified-fabric-api`
var. Bu, Fabric modlarını NeoForge'da çalıştırma katmanı.

**Beta sürüm** ve GitHub'da 1.21.1 sunucu tarafında **açık crash issue'ları var**
(#1346: "Any Fabric mod causes the server to crash on startup").

Connector'ı **hangi mod için** kurduğunu bil. Sırf "belki lazım olur" diye
duruyorsa **kaldır** — 237 modluk bir kurulumda ekstra transform katmanı
hem açılışı yavaşlatır hem crash yüzeyini büyütür.

Hangi modların Connector'a bağlı olduğunu görmek için:
```bash
grep -i "connector.*loading\|fabric mod" logs/latest.log | head -30
```

## ⚠️ D. `Chunksending-1.21-3.7.jar` + C2ME — Çakışma Riski

C2ME chunk yükleme/gönderme pipeline'ına dokunuyor. Chunksending de aynı işi
yapıyor. C2ME'nin NeoForge sürümü bazı chunk modlarını açıkça "discouraged"
işaretliyor (GitHub usefulmods#337: Better Chunk Loading ile uyumsuz).

Chunksending için doğrudan bir uyumsuzluk kanıtı **bulamadım** — bu yüzden
"kaldır" demiyorum. Ama açılış logunda şunu ara:

```bash
grep -i "discourage\|conflict\|incompatib" logs/latest.log
```

Bir şey çıkarsa Chunksending'i çıkarıp test et.

## ⚠️ E. BetterEnd + C2ME — BİLİNEN BUG

Bu ciddi. C2ME-neoforge GitHub **issue #50** tam senin mod kombinasyonun:

> *"Conflicts with BetterEnd 1.21.1 neoforge — Install the 4 mods you need for
> Better End and c2me... fly through new end biomes. Bad chunk is generated and
> nothing works anymore after that."*

Sende **hepsi var:** `BetterEnd-21.0.34`, `bclib-21.0.26`, `worldweaver-21.0.25`,
`wunderlib-21.0.10`, `c2me-...0.4.0-alpha.0.116`.

Issue'daki sürüm `0.3.0+alpha.0.89`, seninki `0.4.0-alpha.0.116` — yani
**daha yeni**, düzelmiş olabilir. Ama **End'de yeni bölge keşfe çıkmadan önce
mutlaka yedek al.** (Zaten FTB Backups 3'ü bu yüzden kur.)

Bu senin `BOZUK-CHUNK-COZUMU.md`'de yaşadığın sorunun muhtemel kaynaklarından
biri olabilir — ama **emin değilim**, End'de mi yaşandığını bilmiyorum.

## ⚠️ F. `epicterrain` + `Terralith` + `BOP` + `BOWG` + `TerraBlender`

Dört ayrı biome modu + bir terrain shape modu aynı anda. Bu çalışabilir
(TerraBlender bunun için var) ama:
- Worldgen ağırlaşır (C2ME'yi zaten bu yüzden kurdun)
- Biome geçişleri tuhaflaşabilir
- **Mod eklerken/çıkarırken chunk duvarı riski** — `CHUNK-DUVARI-GERCEK-COZUM.md`

Dünya kurulmuşsa dokunma. Ama bir daha worldgen modu **ekleme.**

---

# BÖLÜM 4 — İSTEĞE BAĞLI, GÜZEL OLUR

Bunlar "eksik" değil, "olsa hoş olur" kategorisi.

| Mod | Ne yapar | Neden senin sunucuna uyar |
|---|---|---|
| **Simple Discord Link** | MC chat ↔ Discord köprüsü | Arkadaşların oyunda olmadan sohbeti görür. `SimpleDiscordRichPresence` sende var ama o sadece "oynuyor" durumu gösterir, chat köprüsü değil |
| **Server Tab Info** | TAB listesinde TPS/ping | Arkadaşın "lag var mı" diye sormak yerine görür |
| **Vote Sleep / Comforts** | Çoğunluk yatınca gece geçer | `comforts` sende var ama vanilla uyku oranı 5 kişide sinir bozucu. `/gamerule playersSleepingPercentage 50` da yeter aslında |
| **Chunky Border** | Dünya sınırı | `EKSIK-GEDIK.md`'de bahsetmiştim. `Chunky` sende var, `/chunky worldborder` ile sınır koy — 500 GB diski sonsuz keşifle doldurma |
| **Text Placeholder API** | Diğer modların değişkenleri | Bazı mod kombinasyonları ister, hata verirse kur |

> **Vote sleep için mod kurmana gerek yok:**
> ```
> /gamerule playersSleepingPercentage 50
> ```

---

# BÖLÜM 5 — KURULUM SIRASI

Hepsini birden atma. **Aralarında sunucuyu aç, log oku.**

```
1. FTB Backups 3           → ÖNCE BU. Diğerlerini kurmadan yedek al.
   ↓ sunucuyu aç, /backup create çalışıyor mu
2. CoreProtectNeo          → /co i çalışıyor mu
   ↓ sunucuyu aç, bir blok kır, /co i ile gör
3. FTB Essentials          → /sethome /home çalışıyor mu
   ↓
4. FTB Chunks              → KURAR KURMAZ config'i düzelt (force-load 5)
   ↓ sunucuyu aç, claim yap, arkadaş kıramıyor mu test et
5. FTB Ranks               → rol oluştur
   ↓
6. BlueMap                 → ilk render'ı sunucu kapalıyken
```

Her adımda:
```bash
grep -iE "error|conflict|discourage|incompatible|failed" logs/latest.log | head -20
```

---

# BÖLÜM 6 — İNDİRME LİSTESİ

| Mod | Link | Bağımlılık | Sende var mı |
|---|---|---|---|
| FTB Backups 3 | curseforge.com/minecraft/mc-mods/ftb-backups-3 | — | ❌ |
| CoreProtectNeo | modrinth.com/mod/coreprotectneo | — | ❌ |
| FTB Essentials | curseforge.com/minecraft/mc-mods/ftb-essentials | FTB Library | ❌ |
| FTB Chunks 2101.1.14 | curseforge.com/minecraft/mc-mods/ftb-chunks | FTB Library + Teams | ❌ |
| FTB Ranks | curseforge.com/minecraft/mc-mods/ftb-ranks | FTB Library | ❌ |
| BlueMap v5.7 | github.com/BlueMap-Minecraft/BlueMap/releases | — | ❌ |
| FTB Library | — | — | ✅ `2101.1.35` |
| FTB Teams | — | — | ✅ `2101.1.10` |
| Spark | — | — | ✅ **kullan!** |
| Chunky | — | — | ✅ **worldborder için kullan** |

**Toplam eklenecek: 6 mod.** 237 → 243.

Hepsi **sunucu tarafı** (BlueMap, CoreProtectNeo, FTB Backups tamamen;
FTB Chunks/Essentials/Ranks client'ta da olmalı ama zaten FTB Library
dağıtıyorsun).

---

## Özet Hüküm

**İçerik modu ekleme.** 237 mod zaten fazlasıyla dolu ve her yeni içerik modu
worldgen'i ağırlaştırıp chunk duvarı riskini artırıyor.

**Eksik olan tek şey sunucu altyapısı** ve orada da sadece 3 tanesi gerçekten
kritik: **yedek, logging, claim.** Bunlar olmadan çok oyunculu sunucu
çalıştırmak, "hiçbir şey ters gitmesin" umuduyla oynamak demek.

Bir de şu iki dosya adını kontrol et: `adorabuild-structures-...1.21.3.jar`
ve `more_mobs-...mc1.14-...jar`. İkisi de yanlış sürüm gibi duruyor.

---

## Kaynaklar

- CoreProtectNeo: modrinth.com/mod/coreprotectneo
- Ledger NeoForge desteği yok: github.com/QuiltServerTools/Ledger/issues/336
- FTB Backups 2 LTS notu: github.com/FTBTeam/FTB-Backups-2
- FTB Chunks force-load varsayılanları: docs.feed-the-beast.com/mod-docs/mods/suite/Chunks
- C2ME + BetterEnd bug: github.com/RelativityMC/C2ME-neoforge/issues/50
- C2ME + chunk modu uyumsuzluğu: github.com/TheUsefulLists/usefulmods/issues/337
- Sinytra Connector sunucu crash: github.com/Sinytra/Connector/issues/1346
- BlueMap 1.21.1 son sürüm v5.7: github.com/BlueMap-Minecraft/BlueMap/releases/tag/v5.7
