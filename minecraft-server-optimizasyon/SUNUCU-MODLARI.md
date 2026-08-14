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
