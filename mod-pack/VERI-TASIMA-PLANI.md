# 📦 TAM VERİ TAŞIMA PLANI — 1.20.1 Forge → 1.21.1 NeoForge (SIFIRDAN KURULUM + %100 TAŞIMA)

**Tarih:** 2026-08-07 · **Uygulayan:** sen · **Yedek PC:** i5-9400F / 16GB / NVMe / RX 550 / Ubuntu 24.04
**Hedef:** 1.21.1 NeoForge tarafını SIFIRLA → temiz kur → eski 1.20.1 sunucusundaki **dünya, oyuncu, eşya, başarım, istatistik, mod verisi, ayarlar — akla gelebilecek HER ŞEY** eksiksiz taşı.

---

## ⚠️ 0) TEMEL GERÇEKLER (önce bunları bil)

1. **Dünya formatı 1.20.1 → 1.21.1 ileri uyumludur.** Chunk'lar, playerdata, advancements, stats — hepsi aynı format; Minecraft 1.21.1 bunları **açılışta otomatik yükseltir** (level.dat data version artırılır). SİLMEK YOK, dönüştürmek YOK.
2. **Tek yönlü:** 1.21.1'de yükseltilen dünya, 1.20.1'de AÇILMAZ. Bu yüzden 1.20.1'in **orijinal kopyası** sonsuza dek saklanır (rollback anahtarı).
3. **Mod blokları/eşyaları:** Registry ID'si değişmeyen modlar (aynı aile, 1.21.1 sürümü) → **bloklar ve envanter korunur.** ID'si değişen / portu olmayan modlar → o blok/eşyalar **kaybolur** (aşağıda "KAYIP LİSTESİ").
4. **Eski config KOPYALANMAZ** (sürüm uyumsuzluğu = crash #1). Yeni config üretilir; özel ayarlar **elle** yeniden yapılır.
5. **Mod verileri (world/data/*.dat, mod-namespace kayıtları)** — aynı modun 1.21.1 sürümü kuruluysa **taşınır ve korunur.**

---

## 📥 1) ESKİ 1.20.1 SUNUCUSUNDAN TAM YEDEK (ilk ve en kritik adım)

> 🛑 Önce: 1.20.1 sunucusunu **tamamen kapat** (`stop` → `Done` çıkana kadar bekle → process öldüğünden emin ol).

```bash
# Sunucu dizininde (ör. /opt/mc1201):
cd /opt/mc1201

# 1) Dünya + tüm veri klasörlerini komple kopyala (her şey — tek komut):
mkdir -p /opt/mc1201-yedek-TAM
rsync -a --info=progress2 \
  world/ \
  /opt/mc1201-yedek-TAM/world/
#  (world/ içinde: region, entities, poi, playerdata, advancements, stats, data, datapacks, level.dat, session.lock hepsi gider)

# 2) Üst dizindeki dünya-ekleri (varsa DIM klasörleri world/ içindedir; kontrol):
ls world/ | grep -iE "DIM"        # DIM-1 (nether), DIM1 (end) world/ altında olmalı

# 3) Sunucu yönetim dosyaları:
cp server.properties ops.json whitelist.json banned-players.json banned-ips.json usercache.json \
   /opt/mc1201-yedek-TAM/ 2>/dev/null || true

# 4) Mod config'leri (TAŞIMA değil, REFERANS için sakla — eski ayarlarını görüp elle uygulayacaksın):
cp -r config /opt/mc1201-yedek-TAM/config-eski-ref 2>/dev/null || true

# 5) Mod listesi kanıtı:
ls mods/ > /opt/mc1201-yedek-TAM/mod-listesi-1201.txt

# 6) DOĞRULA — yedek gerçekten tam mı:
du -sh /opt/mc1201-yedek-TAM/world        # ham dünya boyutu (5-20GB olabilir)
ls /opt/mc1201-yedek-TAM/world/playerdata | head     # oyuncu UUID dosyaları var mı?
ls /opt/mc1201-yedek-TAM/world/level.dat              # level.dat var mı?
```

✅ **Doğrulama:** `playerdata/` içinde oyuncu UUID'leri + `level.dat` + `region/` dolu görüyorsan yedek tamdır.

---

## 🧹 2) 1.21.1 TARAFINI SIFIRLA (deneme verilerini at, temiz kurulum)

> 🛑 1.21.1 sunucusunu kapat: `sudo systemctl stop kitsugi-mc`

```bash
# 1) 1.21.1 dizininde deneme dünyasını ve tüm geçici verileri TEMİZLE:
cd /opt/mc1211   # (1.21.1 sunucu dizinin)

# ÖNCE bir anlık yedek (yanlışlıkla önemli bir şey silinmesin diye):
mkdir -p /opt/mc1211-atilmadan-once
mv world /opt/mc1211-atilmadan-once/ 2>/dev/null || true
mv config /opt/mc1211-atilmadan-once/ 2>/dev/null || true

# 2) mods klasörünü de temizle (doğru 1.21.1 paketini koyacağız):
mkdir -p /opt/mc1211-atilmadan-once/mods-eski
mv mods/* /opt/mc1211-atilmadan-once/mods-eski/ 2>/dev/null || true

# 3) Sıfır durum doğrula:
ls -la /opt/mc1211/    # world YOK, config YOK, mods boş olmalı
```

---

## 🧱 3) TEMİZ 1.21.1 NEOFORGE KURULUMU

```bash
# 1) Java 21 doğrula (24.04'te kurduk; 25 varsa da 21+ çalışır — tutarlı kalsın):
java -version

# 2) NeoForge 21.1.x installer ile temiz kur (sunucu dizininde):
#    (neoforged.net → 1.21.1 → en son sürüm, ör. 21.1.193+)
java -jar neoforge-21.1.x-installer.jar --installServer

# 3) Mod paketini indir + kur (mod-pack/ scripti):
python3 indir_modlar.py
cp mods-server/* /opt/mc1211/mods/
cp mods-client/* /opt/mc1211/mods/    # (client'lar da aynı mods'a — sunucu yok sayar; istersen sadece server)

# 4) run.sh JVM ayarları (RAM bölümündeki kararımız):
#    -Xms4G -Xmx10G + G1GC (AlwaysPreTouch YOK) — rehber 7. bölüm
```

---

## 📦 4) VERİ TAŞIMA (1.20.1 yedeğinden 1.21.1'e) — SIRA KRİTİK

> 🛑 1.21.1 sunucusu **KAPALI** iken yap. Dünya klasörünü yerleştirirken `level-name` eşleşmesine dikkat.

```bash
cd /opt/mc1211

# 1) DÜNYA (overworld + nether + end + tüm alt klasörler) — tek seferde:
rsync -a /opt/mc1201-yedek-TAM/world/ world/
#    Bu şunları taşır:
#    - world/region/*.mca            → overworld chunk'lar (binalar, kazılar, TÜM eşya/sandık içerikleri)
#    - world/DIM-1/region/*.mca      → nether
#    - world/DIM1/region/*.mca       → end
#    - world/entities/, world/poi/   → entity'ler, ilgi noktaları
#    - world/playerdata/*.dat        → oyuncuların ENVANTERİ, konumu, sağlığı, XP'si
#    - world/advancements/*.json     → başarımlar
#    - world/stats/*.json            → istatistikler
#    - world/data/*.dat              → mod verileri (harita, zaman, gamerule kayıtları vb.)
#    - world/datapacks/              → özel datapack'ler (varsa)
#    - world/level.dat, level.dat_mcr → dünya seviyesi (spawn, gamerule, time, weather)

# 2) SUNUCU YÖNETİMİ:
cp /opt/mc1201-yedek-TAM/ops.json /opt/mc1201-yedek-TAM/whitelist.json /opt/mc1201-yedek-TAM/banned-*.json /opt/mc1211/ 2>/dev/null || true
cp /opt/mc1201-yedek-TAM/usercache.json /opt/mc1211/ 2>/dev/null || true

# 3) server.properties — YENİDEN YAZ (eskiyi birebir kopyalama; level-name kontrol):
nano server.properties
#    level-name=world   ← klasör adıyla aynı olmalı (kopyaladığımız klasör "world" ise tamam)
#    simulation-distance=5
#    view-distance=10
#    spawn-protection=0
#    (ip/port/whitelist/online-mode ayarlarını eski yedeğe bakarak elle yaz)

# 4) KAYIP MOD VERİLERİNİ ÇIKARMA — yapma: eski config klasörünü KOPYALAMA!
#    (config yerine yeni sürüm kendi config'lerini üretsin; özel ayarlarını
#     config-eski-ref'ten bakıp elle uygula — özellikle yapı/yumurtlama ayarları)

# 5) DOĞRULA (taşımadan sonra):
du -sh world/
ls world/playerdata | wc -l          # oyuncu sayısı (eski sunucudaki kadar)
ls world/region | wc -l              # overworld region dosyası sayısı
```

---

## 🚀 5) İLK AÇILIŞ + YÜKSELTME (level.dat otomatik)

```bash
# 1) İlk çalıştırma — log'u CANLI izle:
cd /opt/mc1211
./run.sh nogui 2>&1 | tee /tmp/ilk-acilis.log
#    veya systemd kullanıyorsan:
sudo systemctl start kitsugi-mc
journalctl -u kitsugi-mc -f

# 2) Bu satırlara dikkat:
#    - "Preparing level 'world'"  → dünya bulundu ✅
#    - "Loaded X advancements" / "Loaded X recipes"
#    - "Time elapsed: X ms"       → chunk yükleme normal sürüyor
#    - "Unknown block id: ..."    → kayıp mod blokları (aşağıdaki KAYIP LİSTESİ)
#    - "Done (X.XXXs)!"           → sunucu hazır ✅

# 3) TPS/performans:
spark tps        # 20.0 beklenir
spark health
```

---

## ✅ 6) DOĞRULAMA LİSTESİ (her şey taşındı mı?)

| Kontrol | Nasıl | Beklenen |
|---|---|---|
| Dünya spawn | `/tp @s 0 100 0` gibi, eski binaları ziyaret et | Binalar/kazılar AYNEN duruyor |
| Sandıklar | Eski sandıkları aç | TÜM eşyalar duruyor (mod ID'leri korunduysa) |
| Oyuncu envanteri | Bir oyuncu giriş yapsın | Eşyaları, konumu, canı, XP'si aynı |
| Başarımlar | Oyuncu hesabına bak | Başarımlar duruyor |
| Nether/End | `/execute in minecraft:the_nether run tp @s 0 80 0` | Nether portalları/binalar duruyor |
| Gamerule/time | `/time query daytime` | Eski dünya saati korunmuş |
| Mod verileri | Mod blokları (Quark, Twilight vb.) yerinde | Korunmuş |
| "Unknown block" | `grep -i "unknown block" /tmp/ilk-acilis.log` | Sadece KAYIP LİSTESİ'ndeki modlar |
| TPS | `/spark tps` | 20.0 |

---

## ⚠️ 7) KAYIP LİSTESİ (bilinçli kabul — portu olmayan modlar)

Bu modların **blok/eşyaları** taşınamaz (1.21.1 sürümleri yok — API ile doğrulandı):

| Mod | Etki | Açıklama |
|---|---|---|
| **Fantasy's Furniture** | Yerleştirilmiş mobilyalar unknown/air | `grep -i "unknown block"` ile bul, `/fill ... air replace <id>` ile temizle (GERI-KAZANILAN-MODLAR.md'de) |
| **Legendary Item** | Envanterdeki efsanevi eşyalar kaybolur | Port yok; oyunculara duyur, alternatif ara |
| **Majrusz (Library+Ench+ProgDiff)** | O eşyalar/büyümeler kaybolur | Port yok; yazarı bekle |
| **MoreArmor / LevelHearts** (daha önce çıkmıştı) | Zırh / ekstra can kaybı | Oyunculara duyur |

> **Oyun içi duyuru (migrasyon öncesi):** "Taşınamayacak modların eşyalarını (Fantasy Furniture, Legendary Item, Majrusz, MoreArmor, LevelHearts) envanterde tutmayın" — ama dünya zaten olduğu gibi taşınıyor; bu sadece o eşyaların kaybolacağını bilinçlendirme.

---

## 🔁 8) ROLLBACK (bir şey bozulursa)

| Senaryo | Yap |
|---|---|
| 1.21.1 açılışta crash | `sudo systemctl stop kitsugi-mc` → 1.21.1 dizinini `/opt/mc1211-atilmadan-once` ile geri al → 1.20.1 yedeğini KARIŞTIRMA |
| Dünya bozuk görünüyor | 5. adımdaki log'u incele → büyük ihtimal "Unknown block" → temizle |
| Her şey kötü | `/opt/mc1201-yedek-TAM` hâlâ duruyor → 1.20.1'i geri aç (dünya orijinal, hiç değişmedi) |

> 🛡️ **Kural:** `mc1201-yedek-TAM` klasörüne **asla dokunma** — o senin tek gerçek anahtarın. Taşıma bittikten ve 2-3 gün sorunsuz çalıştıktan sonra bile silme (en az 1 ay sakla).

---

## 🗓️ 9) ZAMAN ÇİZELGESİ & SIRA

1. **Gün 1 (akşam):** 1.20.1 kapat → TAM yedek (Adım 1) → doğrula
2. **Gün 1-2:** 1.21.1 sıfırla (Adım 2) → temiz kur (Adım 3) → modları indir/kur
3. **Gün 2:** Veri taşıma (Adım 4) → ilk açılış + log (Adım 5) → doğrulama (Adım 6)
4. **Gün 2-5:** 1-2 testçi ile oyun içi doğrulama (envanter, binalar, nether/end, mod blokları)
5. **Gün 5+:** Sorun yoksa duyuru + tam açılış; yedeği 1 ay sakla

---

## 📋 10) KONTROL LİSTESİ (checkbox — tek tek işaretle)

- [ ] 1.20.1 sunucusu tamamen kapatıldı (`Done` çıktı)
- [ ] `rsync` ile world komple yedeklendi (`mc1201-yedek-TAM`)
- [ ] playerdata UUID'leri yedekte görünüyor
- [ ] level.dat yedekte var
- [ ] server.properties / ops / whitelist / usercache yedeklendi
- [ ] config REFERANS olarak saklandı (config-eski-ref)
- [ ] 1.21.1 durduruldu (`systemctl stop kitsugi-mc`)
- [ ] 1.21.1 deneme dünyası/config/mods taşındı (atilmadan-once) → dizin temiz
- [ ] NeoForge 21.1.x temiz kuruldu
- [ ] Modlar indirildi + mods/ klasörüne kondu (1.21.1 paketi)
- [ ] JVM ayarları yazıldı (Xms4G-Xmx10G, G1GC, AlwaysPreTouch YOK)
- [ ] world yedeği 1.21.1 dizinine rsync ile taşındı
- [ ] ops/whitelist/usercache kopyalandı
- [ ] server.properties yeniden yazıldı (level-name=world, sim-distance=5)
- [ ] İlk açılış log'u izlendi (Done, Unknown block, TPS)
- [ ] `/spark tps` = 20.0
- [ ] Testçi oyuncu: envanter + konum + başarım doğrulandı
- [ ] Eski bina/sandık/nether/end ziyaret edildi
- [ ] Kayıp modlar oyunculara duyuruldu
- [ ] mc1201-yedek-TAM 1 ay saklanacak (silmek yok)
