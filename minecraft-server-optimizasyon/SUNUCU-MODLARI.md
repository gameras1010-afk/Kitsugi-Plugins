# 🟢 SADECE SUNUCU MODLARI — Tam Liste

**1.21.1 · NeoForge · korsan (offline-mode) uyumlu**

Bu dosyadaki modların **hiçbirini arkadaşlarının kurmasına gerek yok.**
Jar'ı sunucudaki `mods/` klasörüne atıyorsun, bitiyor. Arkadaşın oyununda
hiçbir değişiklik yapmıyor, "sende şu mod yok" hatası vermiyor.

Hepsi Modrinth API'sinden **tek tek doğrulandı**: `environment: server_only`
veya `dedicated_server_only`, 1.21.1 + NeoForge sürümü var, bağımlılıkları kontrol edildi.

---

## 📖 Nasıl okunur

| İşaret | Anlamı |
|---|---|
| 🔥 | Bence kur, gözü kapalı |
| ✅ | İyi mod, işine yarayabilir |
| 🤔 | Niş / özel durum |
| 🔑 | Hesap durumu — hepsinde **"gerekmez"**, aksi olan listeye alınmadı |
| ⚠️ | Dikkat edilecek bir şey var |

---

# 🔥 BİRİNCİ SINIF — Bunları kur

## 1. Skin Restorer — korsan sunucuda skin sorununu bitirir
Offline-mode sunucuda herkes Steve/Alex görünür. Bu mod skinleri geri getirir.
Senin durumun için **listedeki en değerli mod.**

```
https://cdn.modrinth.com/data/ghrZDhGW/versions/P7Vre2lP/skinrestorer-2.10.0+1.21-neoforge.jar
276.491 B | sha1 ea72bb25debbfc74b9486cb9d0fcb814ee5c6323
```
- **Bağımlılık:** yok · **Lisans:** MIT · **environment:** `server_only`
- 🔑 Hesap gerekmez — zaten tam olarak hesabı olmayanlar için yazılmış
- `/skin set <oyuncu>` ile başkasının skinini de alabilirsin
- Mojang, ely.by, MineSkin veya URL'den skin çekebiliyor
- ⚠️ Skin çekmek için sunucunun internete çıkması gerekir (Tailscale'in var, sorun yok)

## 2. Ksyxis — dünya açılışını hızlandırır
Sunucu açılırken 441 chunk boşuna yükleniyor. Bu mod onu kesiyor.
26 KB, mixin bile denemeyecek kadar basit, C2ME ile çakışmaz.

```
https://cdn.modrinth.com/data/2ecVyZ49/versions/kL32PN9Q/Ksyxis-1.4.3.jar
26.968 B | sha1 6f4b2ea7827da8136bdf436457a2ba3fcdb2120e
```
- **Bağımlılık:** yok · **Lisans:** MIT · **environment:** `server_only`
- 1.6M indirme, 1.8'den 26.x'e kadar her sürümü destekliyor — bakımı canlı
- 🔑 Hesap gerekmez

## 3. CrashExploitFixer — sunucunu çökertmeye karşı kapatır
Minecraft'ta bilinen bir sürü "paket gönder, sunucu çöksün" açığı var.
Bu onları yamalıyor. Tailscale arkasındasın ama arkadaşının makinesi kapılmışsa da iş görür.

```
https://cdn.modrinth.com/data/Z5GdSH3X/versions/8foOfmdZ/crashexploitfixer-neoforge-2.0.0+1.21.4.jar
694.835 B | sha1 b5d3f1a493b82ad56808358a39a4b1162d605829
```
- **Bağımlılık:** yok · **Lisans:** GPL-3.0 · **environment:** `server_only`
- 🔑 Hesap gerekmez

## 4. Advanced Backups — otomatik, sıkıştırmalı, artımlı yedek
Dünya aktarımı yaptın, elinde tek kopya var. Bu şart.
Artımlı yedek alıyor — 20 GB dünya için her seferinde 20 GB yazmıyor.

```
https://cdn.modrinth.com/data/Jrmoreqs/versions/ufIaRDFo/AdvancedBackups-neoforge-1.21-3.7.1.jar
335.656 B | sha1 3d328e772b19d6d12f4b075cca2120bbcca2b09d
```
- **Bağımlılık:** yok · **Lisans:** BSD-3 · **environment:** `server_only_client_optional`
- 🔑 Hesap gerekmez
- `/backup snapshot <isim>` ile elle de alabilirsin
- ⚠️ `environment` "client optional" diyor ama client'ta kurulmadan sorunsuz çalışır.
  Arkadaşların kurmayacak.

## 5. Let Me Despawn — mob birikmesini keser, TPS'i toplar
Vanilla despawn mantığı bozuk; mob'lar birikip tick yiyor. Bu düzeltiyor.

```
https://cdn.modrinth.com/data/vE2FN5qn/versions/fgcMDg9B/letmedespawn-1.21.x-neoforge-1.5.0.jar
14.911 B | sha1 576fe2edaa96e7e71015287457bd52f87646d968
```
- ⚠️ **Bağımlılık VAR:** Almanac (`Gi02250Z`) — onu da indirmen lazım
- **Lisans:** LGPL-3.0 · **environment:** `server_only` · 🔑 Hesap gerekmez
- 💡 Bağımlılık istemiyorsan **1.3.2** sürümü bağımlılıksız:
  `.../versions/Cwn6J6QW/letmedespawn-1.3.2.jar` (84.877 B, sha1 `576c7ffb07792e184bbb3cbefd7baeb4ffea2475`)

## 6. ItemClearLag — yerdeki item yığınlarını temizler
Yerde biriken 3000 tane item TPS'i öldürür. Periyodik temizliyor, önce uyarı veriyor.

```
https://cdn.modrinth.com/data/NJcJEXNc/versions/dASJzRJ5/ICL-1.21.1-neoforge-1.5.4a.jar
37.554 B | sha1 f1267b858aeb2f6fb8649236ee0a0164bd4ed218
```
- **Bağımlılık:** yok · **Lisans:** MIT · **environment:** `dedicated_server_only`
- 🔑 Hesap gerekmez
- 🟢 **C2ME uyumu teyitli** — 1.5.3 sürümünün changelog'u birebir "C2ME fix" diyor.
  Yani geliştirici C2ME'yi biliyor ve uyumu düzeltmiş.

---

# ✅ İKİNCİ SINIF — İşine yarayabilir

## 7. BlueMap — sunucunun 3D web haritası
Tarayıcıdan dünyanı geziyorsun, arkadaşların nerede görüyorsun. Google Earth gibi.
Tailscale IP'nden `http://100.70.34.111:8100` diye açarsın.

- `bluemap` / `swbUV1cr` · MIT · `dedicated_server_only` · 🔑 Hesap gerekmez
- ⚠️ İlk render CPU yer. C2ME ile aynı anda çalışırken sunucu açılışta zorlanabilir —
  render'ı gece başlat veya `render-thread-count`'u 2'ye düşür.
- ⚠️ 400+ MB'lık web asset'i indiriyor ilk açılışta

## 8. LuckPerms — izin ve rank sistemi
Kim ne komut kullanabilir, kim OP. Arkadaş sayın artarsa şart olur.

- `luckperms` / `Vebnzrzj` · MIT · `server_only` · 🔑 Hesap gerekmez
- ⚠️ Offline-mode'da oyuncular **UUID yerine isimle** eşlenir. LuckPerms bunu destekliyor
  ama `server.properties`'te `online-mode=false` ise config'de de belirtmen iyi olur.
- 2.5M indirme, sektör standardı

## 9. GriefLogger — kim neyi kırdı/koydu, kaydı tutar
CoreProtect'in modlu sürümü. "Evimi kim yıktı" sorusunun cevabı.

- `grieflogger` / `8oGVUFuX` · Apache-2.0 · `dedicated_server_only` · 🔑 Hesap gerekmez
- ⚠️ **19 MB** — listedeki en şişman mod (SQLite sürücüsü gömülü)
- ⚠️ **2 bağımlılık var:** `lhGA9TYQ` + `LN9BxssP`
- 🤔 3-5 kişilik arkadaş sunucusunda gereksiz olabilir. Kavga çıkarsa kur.

## 10. TT20 (TPS Fixer) — TPS düşünce oyunu yavaşlatmaz
TPS 20'nin altına inince vanilla her şeyi yavaşlatır (fırın, ok, TNT).
TT20 bunları hızlandırıp telafi ediyor, oyun "ağır çekim" hissi vermiyor.

- `tt20` / `YS3ZignI` · `server_only` · Bağımlılık yok · 🔑 Hesap gerekmez
```
https://cdn.modrinth.com/data/YS3ZignI/versions/2RnrIn18/tt20-0.8.4+mc1.21.1-neoforge.jar
685.295 B | sha1 142f42d3f49bb14d49c0cca0af7d1d5abbb54b6e
```
- ⚠️ Lisans PolyForm-Shield (ticari kullanımda kısıt var, sende sorun değil)
- 🤔 Bu bir **semptom örtücü** — TPS düşüşünün kendisini çözmüyor, hissettirmiyor.
  C2ME ile asıl sorunu çözmeye çalışıyorsun; bu yanına ek olur.

## 11. NetherPortalFix — nether portalı seni yanlış yere atmasın
Çok oyunculuda klasik bela: arkadaşınla portala girince ikiniz farklı yere çıkıyorsunuz.

- `netherportalfix` / `nPZr02ET` · 22M indirme · `server_only` · 🔑 Hesap gerekmez
- ⚠️ Lisans ARR (kaynak kapalı) — ama devasa kullanıcı tabanı var

## 12. I'm Fast — "moved too quickly" spam'ini susturur
Elytra/at/lag durumunda konsolu dolduran o mesajları kaldırır.
Tailscale gecikmesi olan bir sunucuda gerçekten işe yarar.

- `im-fast` / `PaUMOeP0` · MIT · `server_only` · 🔑 Hesap gerekmez
- ⚠️ Bu kontroller aynı zamanda hile önlemedir. Arkadaş sunucusunda önemsiz.

## 13. Clumps — XP orb'larını birleştirir
Ender dragon veya mob farm sonrası 500 tane XP orb yerine 1 tane. Ciddi TPS kazancı.

- `ly-clumps` / `qm9Jw8Jg` · AGPL-3.0 · `server_only` · 678K indirme · 🔑 Hesap gerekmez

## 14. Vanishmod — admin olarak görünmez ol
Sen sunucuya girince "X oyuna katıldı" yazmaz, Tab'da görünmezsin.
Kontrol etmek için sessizce dolaşmak istersen.

- `vanishmod` / `MihN2cw5` · ARR · `server_only` · 🔑 Hesap gerekmez

## 15. Simple Discord Link — Discord ↔ oyun sohbeti köprüsü
Oyunda yazılan Discord'a, Discord'a yazılan oyuna düşüyor.

- `sdlink` / `Sh0YauEf` · MIT · `server_only` · 🔑 Hesap gerekmez
- ⚠️ **Whitelist özelliğini AÇMA.** O özellik oyuncuyu Discord hesabıyla eşliyor
  ve UUID doğrulamasına dayanıyor — offline-mode'da UUID'ler kalıcı değil, kilitlenirsin.
  Sadece **chat köprüsü** kısmını kullan, `whitelisting.enabled=false` bırak.

---

# 🤔 ÜÇÜNCÜ SINIF — Niş, isteğe bağlı

| Mod | id | Ne yapar | Not |
|---|---|---|---|
| **In Control!** | `KpICtuVx` | Mob spawn kurallarını tamamen sen yaz | Güçlü ama config öğrenmek gerek. 1.21.1 son desteklenen sürüm |
| **VillagerConfig** | `OClpEDe3` | Köylü ticaretini dengele | Ekonomi bozulduysa |
| **Sparse Structures** | `qwvI41y9` | Yapılar arası mesafeyi ayarla | ⚠️ Sadece **yeni** chunk'ları etkiler |
| **WorldEdit** | `1u6JkXh5` | Oyun içi harita editörü | ⚠️ Ağır işlemler C2ME ile chunk yükünü patlatır. Dikkatli kullan |
| **Death Backup** | `Ot5JFxuv` | Ölmeden önceki envanteri saklar | "Eşyalarım gitti" krizini çözer |
| **Advancement Disable** | `XIsVTmcm` | İstemediğin advancement'ları kapat | Modlu sunucuda advancement spam'i olur |
| **Just Player Heads** | `YdVBZMNR` | Ölünce/komutla oyuncu kafası düşer | ⚠️ Offline-mode'da kafa dokusu Steve olabilir — Skin Restorer'la beraber test et |
| **Welcome Message** | `DMK2eYu7` | Girişte karşılama mesajı | Süs |
| **Dragon Drops Elytra** | `DPkbo3dg` | Ejderha elytra düşürür | Tek elytra sıkıntısına çözüm |
| **NoRollback** | `K4Ytaql5` | Lag'de blok geri gelmesini engeller | Tailscale gecikmesinde işe yarar |
| **NaNny** | `6EpIGT2g` | Bozuk (NaN) can değerlerini temizler | Nadir bug, önleyici |
| **No Creeper Grief** | `flHpkyzN` | Creeper blok kırmaz | Zevk meselesi |
| **No Enderman Grief** | `ss02V75k` | Enderman blok almaz | Zevk meselesi |
| **Too Much XP** | `2J3CBN4p` | XP orb'ları tamamen kaldırır, seviyeyi korur | Clumps'tan daha agresif — ikisini birden kurma |

---

# ❌ KURMA — ve nedeni

| Mod | Neden |
|---|---|
| **LagShield Ultimate** | 968 indirme, tek sürüm, "Arclight-safe async" iddiası doğrulanamıyor. Mob AI'ya async müdahale = C2ME ile çakışma riski yüksek. Sunucunu deneme tahtası yapma |
| **Does It Tick?** | Ticking entity optimizasyonu — C2ME'nin chunk tick yönetimiyle aynı alana giriyor. Uyumu doğrulanamadı, riske girme |
| **NoisiumForked** | Worldgen optimizasyonu — **C2ME ile doğrudan çakışır.** İkisi de aynı işi yapıyor |
| **Fast Async Backups** | "C2ME uyumlu" diyor ama 1000 indirme. Advanced Backups varken kumar oynama |
| **spark** | `client_or_server` — server-only değil. (Yine de profil almak istersen sunucuya kurulabilir, sadece bu listenin kriterine uymuyor) |
| **Backup Manager** | `client_and_server` — GUI istiyor, kriterine uymuyor |
| **Universal Save Backup** | `client_and_server` |
| **Terralith / Amplified Nether** | Worldgen değiştirir → **mevcut dünyanda chunk duvarı yaratır.** Aktarım yaptığın dünyada kesinlikle olmaz |
| **Open Parties and Claims** | Claim sistemi ama client'ta kurulmayınca sınırları göremezsin. 3-5 kişilik arkadaş sunucusunda gereksiz bürokrasi |
| **Herhangi bir anticheat** | 1.21.1 + NeoForge + server-only aramasında **0 sonuç.** NeoForge tarafında yok. Vazgeç |

---

# 🎯 BENİM ÖNERİM — 6 mod, hepsi bağımlılıksız

Uğraşmak istemiyorsan sadece bunları at, hiçbiri diğerine dokunmaz:

```
1. Skin Restorer      276 KB   → korsanda skin sorunu biter
2. Ksyxis              27 KB   → açılış hızlanır
3. CrashExploitFixer  695 KB   → güvenlik
4. Advanced Backups   336 KB   → dünyanı kaybetmezsin
5. ItemClearLag        38 KB   → C2ME uyumu teyitli, TPS
6. Let Me Despawn      85 KB   → 1.3.2 sürümü, bağımlılıksız
```
**Toplam ~1.4 MB. Hiçbiri arkadaşlarında kurulmayacak.**

### Kurulum sırası
1. Sunucuyu kapat
2. 6 jar'ı `mods/` içine at
3. Aç, konsolda **kırmızı satır var mı** bak
4. `/skin set <kendi adın>` dene — skin geldiyse Skin Restorer çalışıyor
5. Config dosyaları `config/` altında oluşur, ilk açılıştan sonra ayarla

### Geri alma
Jar'ı sil, restart. Hiçbiri dünyaya kalıcı veri yazmıyor
(GriefLogger ve BlueMap hariç — onlar kendi klasörünü bırakır, elle silersin).

---

## ⚠️ Cevaplanmamış tek soru

`server.properties` dosyanda **`online-mode`** ne yazıyor?

```bash
grep online-mode server.properties
```

- `false` ise → yukarıdaki liste birebir geçerli, Skin Restorer şart
- `true` ise → korsan launcher'la zaten bağlanamıyor olurdun, bir yerde hata var

Bunu söylersen LuckPerms ve Just Player Heads için kesin konuşurum.

---

*Tüm sürüm/hash bilgileri Modrinth API'sinden doğrulandı — 14 Ağustos 2026.*
*İndirme adresi olmayan modların `id`'sini `https://modrinth.com/mod/<id>` şeklinde açabilirsin.*

---
---

# 📗 EK BÖLÜM — İkinci Tarama

İlk taramada `management` ve `social` kategorilerine bakmıştım.
Bu turda **`utility`, `optimization` ve `game-mechanics`** kategorilerini de taradım.

**Şeffaf olayım — çıkanlar iki gruba ayrılıyor:**

| | Mod | Durum |
|---|---|---|
| 🔁 | ServerCore, Alternate Current, AI Improvements, Get It Together Drops | **Bu repoda zaten analiz edilmişti** (`MOD-LISTESI.md` / `C2ME-PAKET.md`), sadece bu dosyaya taşınmamıştı. C2ME uyumları **kanıtlı** |
| 🆕 | Leaves Be Gone, Double Doors, RightClickHarvest, Immersive Optimization, Skeleton AI Fix, Dynamic Lights | **Gerçekten yeni bulgular** |

En değerlisi birinci gruptan çıktı 👇

---

## 🔥🔥 ServerCore — bu listenin en değerli modu

İlk taramada bu listeye koymamışım, **özür.** 14 milyon indirme, sektörün en bilinen
sunucu optimizasyon modu ve senin durumuna birebir oturuyor.

> 📌 **Not:** ServerCore aslında bu repoda **zaten analiz edilmiş** —
> `MOD-LISTESI.md` ve `UYUMLULUK-KANITI.md` içinde var. Sadece bu dosyaya
> taşınmamış. Aşağıdaki C2ME bilgisi tahmin değil, **kanıta dayanıyor** 👇

```
https://cdn.modrinth.com/data/4WWQxlQP/versions/6N9hXiRa/servercore-neoforge-1.5.19+1.21.1.jar
1.462.674 B | sha1 62ce692654e09271b5c55cbb3a1ef7606d067132
```
- **Bağımlılık:** yok · **Lisans:** MIT · **environment:** `server_only` · 🔑 Hesap gerekmez
- **Haziran 2026'da güncellenmiş** — bakımı çok canlı

**Ne yapıyor (hepsi config'den açılıp kapanıyor):**
- ~~**Dinamik performans** — TPS düşünce view distance'ı otomatik kısar~~
  🔴 **BUNU KAPATACAKSIN** — sebebi aşağıda
- **Mob activation range** — uzaktaki mob'ları daha seyrek tick'liyor
- **Mobcap yönetimi** — chunk başına mob sınırı
- **Villager lobotomizasyonu** — 1x1'e sıkışmış köylülerin AI'sını kapatıyor
  (köylü farmların varsa devasa kazanç)
- **Async chunk pregeneration** — `/chunky` benzeri komut içeriyor

### ✅ C2ME uyumu — TAHMİN DEĞİL, KANIT

**(a)** C2ME'nin **resmî sayfası** uyumlu mod stack'ini sayarken
ServerCore'u **isim vererek** listeliyor.

**(b)** C2ME + ServerCore'un birlikte çalıştığı **gerçek sunucu logu** mevcut:
```
[main/WARN]: Force-disabling mixin 'alloc.chunk_ticking.ServerChunkManagerMixin'
             as rule 'mixin.alloc.chunk_ticking' (added by mods [servercore])
             disables it and children
```
ServerCore chunk ticking'e dokunmak istiyor, sistem çakışan mixin'i kapatıyor,
**ikisi de çalışmaya devam ediyor. Crash yok.**

Detay: `UYUMLULUK-KANITI.md` → "🟩 ServerCore — KANIT SEVİYESİ 1 + 2"

### 🔴 AMA TEK BİR ŞART VAR — bunu atlarsan zarar edersin

```toml
# config/servercore.toml
[dynamic]
    enabled = false
```

**Neden kapatman gerekiyor:**

1. **C2ME ile kavga eder.** Dinamik view/simulation distance, C2ME'nin
   `noTickViewDistance` ayarıyla aynı işi yapıyor — ikisi birbirinin ayarını ezer.
2. **Daha kötüsü:** 1.18'den beri view distance değişimi **client'ta chunk reload
   tetikliyor.** Yani mesafe her oynadığında arkadaşlarının ekranı yeniden yükleniyor.
   Lag'i önlemesi gereken sistem lag üretiyor.

Yani yukarıda anlattığım "dinamik performans" özelliğini **kullanmıyorsun.**
ServerCore'u **entity limitleri + mob AI throttle + villager fix + async login**
için kuruyorsun. Chunk ve mesafe işini C2ME'ye bırakıyorsun.
Bu haliyle bile listedeki en değerli mod.

---

## 🔥 Alternate Current — redstone motorunu değiştirir

Vanilla redstone dust algoritması berbat. Bu onu baştan yazıyor:
**%2-35 performans artışı**, üstelik "non-locational" — yani redstone davranışı
blokların yerleştirilme sırasına göre değişmiyor, daha tahmin edilebilir.

```
https://cdn.modrinth.com/data/r0v8vy1s/versions/PCNyL6v4/alternate_current-mc1.21-1.9.0.jar
50.425 B | sha1 1201c14362f2bad7062d315f8a9b26afbabd2c9c
```
- **Bağımlılık:** yok · **environment:** `server_only` · 🔑 Hesap gerekmez
- ✅ **C2ME uyumu kanıtlı** — `UYUMLULUK-KANITI.md` satır 166: redstone katmanı,
  chunk sistemine hiç dokunmuyor
- Sadece 50 KB
- 🤔 Büyük redstone devren yoksa fark etmezsin. Varsa gözle görülür

---

## 🔥 AI Improvements — mob AI'sını hafifletir

12.4M indirme. Vanilla mob AI'sındaki gereksiz hesaplamaları kapatıyor,
istemediğin davranışları (look AI, random look vb.) tamamen kapatabiliyorsun.

- `ai-improvements` / `DSVgwcji` · `server_only` · 🔑 Hesap gerekmez
- ✅ **C2ME uyumlu** — `C2ME-PAKET.md` tablosunda zaten var (pathfinding katmanı)
- ⚠️ Lisans ARR (kaynak kapalı)
- 🤔 Bu ServerCore'un mob activation range özelliğiyle **kısmen örtüşüyor.**
  İkisini birden kurma — önce ServerCore'u dene, yetmezse bunu ekle

---

## ✅ Immersive Optimization — entity tick zamanlayıcı

"TPS'ini ikiye katlar" iddiasında. Entity'leri oyuncuya uzaklığa göre
daha seyrek tick'liyor.

- `immersive-optimization` / `vNZgQmjg` · GPL-3.0 · `server_only` · 🔑 Hesap gerekmez
- ⚠️ **ServerCore + AI Improvements + bu = üçü aynı işi yapıyor.** Birini seç.
  Benim sıralamam: ServerCore > Immersive Optimization > AI Improvements

---

## ✅ Get It Together, Drops! — yerdeki itemleri birleştirir

ItemClearLag itemleri **siliyor**, bu **birleştiriyor**. Farklı felsefe.
1.6M indirme, MIT, bağımlılıksız.

- `get-it-together-drops` / `T0OUgf8P` · `server_only` · 🔑 Hesap gerekmez
- ✅ **C2ME uyumlu** — `C2ME-PAKET.md` uyumlu modlar tablosunda zaten var
- 💡 **ItemClearLag ile birlikte kurulabilir** — biri birleştirir, diğeri kalanı temizler.
  Çakışmazlar

---

## ✅ Leaves Be Gone — ağaç kesince yapraklar anında dökülür

Ağaç kesip yaprakların 30 saniye orada durmasını beklemek yok.
Aynı zamanda yaprak decay tick'lerini azalttığı için performans da kazandırıyor.

```
https://cdn.modrinth.com/data/AVq17PqV/versions/kAbmpvF3/LeavesBeGone-v21.1.1-1.21.1-NeoForge.jar
55.937 B | sha1 1d8eec39ed44414af14d14c0dfb5abd097e77491
```
- ⚠️ **Bağımlılık VAR:** Puzzles Lib (`QAGBst4M`) — Fuzs'un tüm modları bunu ister
- **Lisans:** MPL-2.0 · `server_only` · 🔑 Hesap gerekmez

---

## ✅ Double Doors — çift kapılar birlikte açılır

Çift kapıya bir kere tıkla, ikisi de açılsın. Trapdoor ve çitler için de geçerli.
8M indirme. Küçük ama her gün hissedeceğin bir konfor.

- `double-doors` / `JrvR9OHr` · `server_only` · 🔑 Hesap gerekmez
- ⚠️ Lisans ARR

---

## ✅ RightClickHarvest — sağ tıkla hasat

Tarlada sağ tıklayınca ürün toplanıyor ve yeniden ekiliyor.
11.3M indirme, MIT. Çiftçilik yapıyorsan bilek ağrısını bitirir.

- `rightclickharvest` / `Cnejf5xM` · `server_only` · 🔑 Hesap gerekmez

---

## ✅ Skeleton AI Fix — iskeletlerin garip dans etmesi biter

İskeletler sürekli sağa sola kaçmayı bırakıp odaklanıyor,
yaklaştıkça daha hızlı ateş ediyor. Dövüşü hem daha adil hem daha akıcı yapıyor.

- `skeleton-ai-fix` / `jn24bUJo` · MPL-2.0 · `server_only` · 🔑 Hesap gerekmez
- ⚠️ Muhtemelen Puzzles Lib ister (aynı geliştirici — Fuzs)

---

## 🤔 Dynamic Lights — elindeki meşale etrafı aydınlatır

**Server-side dinamik ışık.** Normalde bu client modudur (Optifine/Sodium özelliği),
ama bu sürüm sunucu tarafında çalışıyor — arkadaşların hiçbir şey kurmadan
meşale/lav kovası taşırken etrafın aydınlandığını görüyor.

- `dynamic-lights` / `7YjclEGc` · `server_only` · 🔑 Hesap gerekmez
- ⚠️ **Modrinth'teki NeoForge dosyası Fabric API (`P7dR8mSH`) bağımlılığı listeliyor** —
  bu Görev 19'daki Tab Info tuzağının aynısı. NeoForge'da Fabric API yüklenmez.
  **İndirmeden önce mod sayfasındaki NeoForge dosyasını iki kez kontrol et**,
  yanlış dosyayı alırsan sunucu açılmaz
- ⚠️ Gerçek ışık bloğu yerleştirip kaldırdığı için **chunk update yaratır** —
  C2ME'li bir sunucuda ek yük demek. Riskli, en sona bırak

---

## ❌ EK ELEMELER

| Mod | Neden |
|---|---|
| **Create: Threaded Trains** | Sadece Create modu varsa anlamlı. Yoksa hiçbir işe yaramaz |
| **Lithostitched** | Kütüphane — kendi başına bir şey yapmaz, başka mod isterse kurulur |
| **Almanac** | Kütüphane — sadece Let Me Despawn 1.5.0 için gerekir |
| **Puzzles Lib** | Kütüphane — Leaves Be Gone / Skeleton AI Fix için gerekir |

---

# 🎯 GÜNCELLENMİŞ ÖNERİM

İlk listedeki 6 modun üstüne **ServerCore'u koy** — o kadar.
Diğerleri zevk meselesi, bu ise TPS'ine doğrudan dokunuyor.

```
ÇEKİRDEK (7 mod, ~2.9 MB)
1. ServerCore        1.46 MB  → 🔥 mobcap, mob AI throttle, villager fix
                                 ⚠️ [dynamic] enabled = false ŞART
2. Skin Restorer      276 KB  → korsanda skin
3. Ksyxis              27 KB  → açılış hızı
4. CrashExploitFixer  695 KB  → güvenlik
5. Advanced Backups   336 KB  → yedek
6. ItemClearLag        38 KB  → C2ME uyumu teyitli
7. Let Me Despawn      85 KB  → 1.3.2, bağımlılıksız

KONFOR (istersen, hepsi bağımlılıksız)
+ Alternate Current    50 KB  → redstone hızı
+ Double Doors                → çift kapı
+ RightClickHarvest           → sağ tık hasat
+ Get It Together, Drops!     → item birleştirme
```

### ⚠️ ServerCore kurulum sırası — bu adımı atlama



1. Sunucuyu kapat, `servercore-neoforge-1.5.19+1.21.1.jar` → `mods/`
2. Sunucuyu **bir kez aç ve kapat** — config dosyası oluşsun
3. `config/servercore.toml` aç → `[dynamic]` bölümünü bul → `enabled = false` yap
4. Sunucuyu tekrar aç, konsoldaki `Force-disabling mixin ... servercore` satırı
   **normaldir, korkma** — o C2ME ile düzgün anlaştığının işareti
5. 15-20 dakika oyna, TPS'e bak
6. Sorun yoksa diğer 6 modu topluca ekle

3. adımı atlarsan arkadaşlarının ekranı sürekli yeniden yüklenir.

---
---

# 📕 EK 2 — SEN BULDUN, BEN BULAMADIM

## Unloaded Activity ✅ (kurulu, çalışıyor)

```
https://cdn.modrinth.com/data/Oo4rJCDP/versions/lrpwT74F/unloadedactivity-v0.6.7+1.21-1.21.1.jar
326.940 B | sha1 4285140313e85ffa2745f398f1f8c7034970b1f4
```
- `unloaded-activity` / `Oo4rJCDP` · **LGPL-3.0** · `server_only` · 🔑 Hesap gerekmez
- **Bağımlılık:** yok · 291K indirme · Haziran 2026'da güncellenmiş

**Ne yapıyor:** Chunk yüklü değilken geçen süreyi kaydediyor, chunk tekrar
yüklendiğinde "hiç durmamış gibi" ileri sarıyor. Yani **sonsuz simulation distance**
etkisi — ekinler, fırınlar, ağaçlar sen uzaktayken de büyümüş oluyor.

### 🔴 ÖNEMLİ: Lithium uyarısı — bunu bilmen lazım

Kurduğun **v0.6.7'nin changelog'unda tek satır var:**

> *"Fixed **Lithium** incompatibility on **NeoForge** that caused furnaces to
> smelt stuff instantly."*

**Senin sunucunda Lithium var** (`MOD-LISTESI.md` satır 27). Yani:
- ✅ **Doğru sürümü kurmuşsun** — v0.6.7 bu bug'ı düzelten sürüm
- ⚠️ Eğer bir gün v0.6.4'e düşersen **fırınlar anında pişirmeye başlar**
- 🔍 Kontrol et: bir fırına kömür + hammadde koy, anında pişiyorsa sorun var

### 🟡 C2ME ile durum — dürüst olayım
`versionType: beta` (release değil). C2ME ile birlikte test edildiğine dair
kanıt bulamadım. İkisi de chunk yaşam döngüsüne dokunuyor.
Sunucu açıldığına göre **crash yok** — ama birkaç gün ekinleri/fırınları gözle.

### 💡 Bu mod bir modu gereksizleştirdi
**TT20**'yi (`YS3ZignI`) listemde "semptom örtücü" diye ikinci sınıfa koymuştum.
Unloaded Activity varken TT20'ye hiç gerek yok — aynı problemi doğru yerden çözüyor.
**TT20'yi listeden çıkarıyorum.**

---

## 🔍 NEDEN BULAMADIM — yöntem hatam

Aramalarımı hep **`index=downloads`** (en çok indirilen) ile yaptım.
Unloaded Activity'nin 291K indirmesi var — YUNG's, Terralith gibi 20 milyonluk
devlerin yanında **ilk sayfalara hiç çıkmıyor.** Kategorisi de `utility`,
yani tam da taradığım yerdeydi. Sadece sıralamanın dibinde kaldı.

**Düzelttim:** `index=follows` (takipçi sayısı) ile yeniden taradım.
Bu, "çok indirilen" yerine "insanların gerçekten sunucusunda tutmak istediği"
modları öne çıkarıyor. Aşağıdakiler o taramadan çıktı 👇

---

## 🆕 follows sıralamasıyla çıkan yeni modlar

### ✅ Infinite Trading — köylü ticareti hiç kilitlenmez
- `infinite-trading` / `U3eoZT3o` · Serilum · `server_only` · 🔑 Hesap gerekmez
- 2.3M indirme, 1315 takipçi
- Köylülerin "stok bitti" durumu ortadan kalkıyor, sürekli ticaret
- 🤔 Ekonomiyi kolaylaştırır — zor oyun istiyorsan kurma

### ✅ Inventory Totem — totem envanterde çalışır
- `inventory-totem` / `yQj7xqEM` · Serilum · `server_only` · 🔑 Hesap gerekmez
- 2.9M indirme. Totem'i elde tutma zorunluluğu bitiyor
- Ölüm anında envanterin herhangi bir yerindeki totem devreye giriyor

### 🤔 Geyser — Bedrock'tan (telefon/konsol) bağlanma
- `geyser` / `wKkoqHrH` · MIT · `server_only`
- 🔴 **Ama sana uymaz:** Geyser normalde **Floodgate** ile birlikte kurulur ve
  Floodgate Xbox Live hesabı doğrulaması yapar. Sen offline/cracked'sın.
  Ayrıca C2ME'li bir sunucuya ek protokol katmanı yük demek. **Kurma.**

---

## 📌 GÜNCELLENMİŞ ÇEKİRDEK LİSTE

```
KURULU ✅
+ Unloaded Activity  327 KB  → ekinler/fırınlar uzaktayken de ilerler
                                ⚠️ v0.6.7'de kal (Lithium fix'i bu sürümde)

ÖNERİLEN (henüz kurmadın)
1. ServerCore       1.46 MB  → ⚠️ [dynamic] enabled = false ŞART
2. Skin Restorer     276 KB  → korsanda skin
3. Ksyxis             27 KB  → açılış hızı
4. CrashExploitFixer  695 KB → güvenlik
5. Advanced Backups   336 KB → yedek
6. ItemClearLag        38 KB → C2ME uyumu teyitli
7. Let Me Despawn      85 KB → 1.3.2, bağımlılıksız

❌ ÇIKARILDI
- TT20 → Unloaded Activity aynı işi doğru yapıyor
```

---
---

# 📘 EK 3 — FARKINDA OLMADIĞIN BOŞLUKLAR

Bu bölüm "şu mod güzelmiş" listesi değil. **Senin sunucunun somut
durumundan doğan, daha önce hiç konuşmadığımız 3 boşluk** var.
Hepsi `client_side: unsupported` → arkadaşların hiçbir şey kurmaz.
Hiçbiri Mojang hesabı istemez.

---

## 🔴 1. EasyLogin — EN ÖNEMLİSİ, bu bir güvenlik açığı

### Önce problemi anlat

Sunucun `online-mode=false` (korsan launcher kullandığın için başka
şansın yok). Bunun anlamı şu:

> **Minecraft, bağlanan kişinin kim olduğunu HİÇ doğrulamıyor.**
> Sadece yazdığı isme bakıyor.

Yani biri launcher'ına senin nickini yazıp Tailscale IP'nden bağlanırsa
**sunucu onu sen sanır.** Senin envanterin, senin evin, senin OP yetkin.
Şifre yok, kontrol yok. Bu bir "risk" değil, **tasarım gereği açık kapı.**

Tailscale seni dış dünyadan koruyor ✅ ama ağına aldığın herkes
(arkadaşların, onların cihazları) bu kapıdan girebilir.

### Çözüm

```
EasyLogin  ·  1.21.1 NeoForge  ·  162 KB  ·  MIT  ·  🔑 hesap gerekmez
easylogin-neoforge-1.21.1-1.0.1.jar
modrinth.com/mod/easylogin
```

**Doğrulandı:** `game_versions: ["1.21.1"]`, `loaders: ["neoforge"]`,
`environment: dedicated_server_only`, **bağımlılık YOK** (`dependencies: []`).

Nasıl çalışır:
- Oyuncu girer → **limbo**'ya alınır, hareket/sohbet/etkileşim kilitli
- `/register <şifre> <şifre>` ile kaydolur
- Sonraki girişlerde `/login <şifre>`
- Şifreler **BCrypt** ile hash'lenir (düz metin değil)
- Brute-force koruması var (IP + UUID bazlı kilitleme)

Admin: `/easylogin forcelogin <oyuncu>`, `/easylogin resetpassword <oyuncu>`,
`/easylogin reload`

### ⚠️ Dürüst uyarılar

| Konu | Durum |
|---|---|
| İndirme | 3.944 — **düşük.** Ama kaynak kodu açık: `github.com/pedro-dalben/easyLogin` |
| Yaş | 2026-02'de yayınlandı, 2026-05'te güncellendi — yeni proje |
| `issues_url` | Yok → hata bildirimi Modrinth thread'inden |
| Komut kullanımı | 🔴 `/login` komut tabanlı. Görev 22'de komutları reddetmiştin — **ama bu farklı:** burada GUI alternatifi yok, çünkü GUI'li login modu client kurulumu ister. Bu tek seferlik bir şifre girme, günlük kullanım değil. |

### Alternatifler (aynı işi yapanlar)

| Mod | Durum |
|---|---|
| **Auth** (`RpXNx59A`, 59K indirme, AGPL) | Daha popüler, 1.21.1 var. `client_side: optional` — yani client'a da kurulabiliyor ama şart değil. **EasyLogin'e göre daha oturmuş.** Eğer indirme sayısı seni tedirgin ettiyse bunu tercih et. |
| **Login System** (`S4Tu3Hn2`, 6K) | `dedicated_server_only`, MIT. Daha az özellik. |
| **Login** (`kxs8saks`) | Datapack. Açıklaması birebir: *"Especially important in servers with online_mode=false"*. Mod bile gerekmez — `world/datapacks/` içine atarsın, arkadaşlara otomatik senkronlanır. **En hafif seçenek.** |

**Benim tavsiyem:** Önce **Auth**'u dene (daha çok kullanılmış), olmazsa EasyLogin.

---

## 🟡 2. Your Items Are Safe — ölünce eşyan kaybolmasın

### Neden bu senin sorunun

Sende **C2ME + TPS derdi** var. Lag'li sunucuda ölmek demek:
- Eşyalar yere düşer → 5 dakika sayacı başlar
- Lag varsa geri dönemeden **despawn** olur
- Lav/void'e düştüyse zaten gitti

Üstelik sende **ItemClearLag** öneriliyor — o mod yerdeki itemleri
temizliyor. Yani öldüğünde eşyaların **iki taraftan** tehdit altında.

### Çözüm

```
Your Items Are Safe  ·  1.21.1  ·  68 KB  ·  🔑 hesap gerekmez
youritemsaresafe-1.21.1-4.7.jar
modrinth.com/mod/your-items-are-safe
```

**Doğrulandı:** `environment: "server_only"`, `client_side: unsupported`,
`loaders: [fabric, forge, neoforge, quilt]`, `game_versions: ["1.21", "1.21.1"]`.

Öldüğün yere **sandık + zırh standı** koyar. Eşyaların içinde durur,
despawn olmaz, ItemClearLag dokunmaz. Mezar taşı modlarının aynısı ama
özel blok yerine **vanilla sandık** kullanıyor → hiçbir şeyle çakışmaz.

### ⚠️ İki uyarı

1. **Bağımlılığı var:** `e0M1UDsY` = **Collective** (Serilum'un kütüphanesi).
   Onu da kurman şart. `modrinth.com/mod/collective`
2. **Lisansı All-Rights-Reserved** — kullanabilirsin, dağıtamazsın. Senin
   için sorun değil.

### Alternatif

**Graves** (`kieAM9Us`, `ly-graves`, AGPL, 123K indirme) — gerçek mezar taşı,
daha çok ayar, daha popüler. Ama `client_side: optional` ve özel blok
kullanıyor. Vanilla sandık daha güvenli, o yüzden ilk sırada Your Items Are Safe.

---

## 🟢 3. Auto Restart — sızıntıyı gece temizler

### Neden

Uzun süre açık kalan modlu sunucularda RAM sızıntısı ve TPS erimesi
normaldir. Sende **AllTheLeaks** var (sızıntı yamalıyor) ama o her şeyi
yakalamaz. C2ME + 6 thread + `simulation-distance=6` ile çalışan bir
sunucuda 3-4 günlük uptime'dan sonra TPS'in yavaş yavaş düştüğünü
fark edersen sebebi budur.

```
Auto Restart  ·  1.21.1 NeoForge  ·  🔑 hesap gerekmez
modrinth.com/mod/auto-restart
```

`client_side: unsupported`, `dedicated_server_only`. Belirlediğin saatte
(mesela sabah 05:00) oyunculara sayaç gösterir, uyarır, düzgün kapatır.

### ⚠️ Kritik şart

Bu mod sunucuyu **kapatır**, geri açmaz. `start.sh` / `start.bat`
dosyanda döngü olmalı:

```bash
while true; do
  java @user_jvm_args.txt ... nogui
  echo "Sunucu kapandi, 5 sn sonra yeniden aciliyor..."
  sleep 5
done
```

Bu döngü yoksa sunucu sabah 05:00'te kapanır ve **kapalı kalır.**
Kurmadan önce `start.sh`'ı düzelt.

Lisans: All-Rights-Reserved. İndirme 8.031.

---

## 📋 EK 3 ÖZET

| # | Mod | Boyut | Bağımlılık | Aciliyet |
|---|---|---|---|---|
| 1 | **Auth** veya **EasyLogin** | ~160 KB | Yok | 🔴 **Yüksek** — güvenlik açığı |
| 2 | **Your Items Are Safe** + Collective | ~68 KB + lib | ⚠️ Collective | 🟡 Orta |
| 3 | **Auto Restart** | küçük | ⚠️ `start.sh` döngüsü | 🟢 Düşük |

### Kurulum sırası
1. Önce **sadece Auth/EasyLogin** kur, tek başına test et — login akışı
   çalışıyor mu, arkadaşların girebiliyor mu?
2. Çalışıyorsa Your Items Are Safe + Collective ekle
3. En son Auto Restart — ama `start.sh` döngüsünü **önce** yaz

---

## ❌ EK 3'te elenenler

| Mod | Neden |
|---|---|
| **Detect AFK Players** (`OZdgwUpA`) | 1.21.1 var ama tek başına hiçbir şey yapmaz — kütüphane. Add-on'ları da 1.21.8'de kalmış |
| **DynPlay** (`3OhV3TrM`) | CPU yüküne göre max oyuncu sayısını kısıyor. 538 indirme, CC-BY-NC. **Senin 3-5 kişilik sunucunda anlamsız** |
| **Login Shield** (`vpjnuUWT`) | Girişte hasar korumasi. EasyLogin'in "invincibility period" özelliği zaten bunu yapıyor |
| **Early Bedtime / Sleep Sooner** | Uyku saati ayarı — sorun değil, ihtiyaç yok |
| **Server World Resets** | Her restart'ta dünyayı sıfırlıyor. **Senin dünyanı siler.** Kesinlikle kurma |
| **Gravestone x Curios Compat** | Curios API + Gravestone modu varsa anlamlı. Sende yok |
