# 1.20.1 Forge Dünyasını 1.21.1 NeoForge'a Aktarma

> **Tek cümlelik cevap:** Dünyayı taşımana gerek yok. **Dünya klasörünü
> olduğu gibi yeni sunucuya kopyala, Minecraft chunk'ları kendi
> yükseltir.** Asıl iş dünyada değil, **mod listesinde**.

---

## Senin önerdiğin yöntem neden kötü

> "Aynı seed ile 1.21.1'de yeni dünya kurup yapıları taşıyalım."

Mantıklı geliyor ama araştırdığımda **üç ayrı yerden birden kırılıyor**.
Tek tek:

### 1. Aynı seed ≠ aynı arazi (modluda)

Vanilla'da doğru olurdu — 1.18'den beri noise tabanlı arazi sabit,
1.20.1 ile 1.21.1 aynı seed'de birebir aynı vanilla arazisini veriyor.

**Ama sende mod var.** Biyom ekleyen her mod worldgen'e karışıyor:

- TerraBlender'da her modun bir `region_weight`'i var. Mod sürümü
  değişince bu ağırlık değişebiliyor → biyom dağılımı kayıyor.
- Mod listesine bir şey eklenip çıkınca `Random` çağrı sırası kayıyor.
- Terralith'in kendi dokümantasyonu: *"Existing worlds will only
  generate Terralith biomes in unexplored chunks"* — yani zaten
  dikiş kabul ediliyor.

1.20.1 mod listen ile 1.21.1 mod listen **birebir aynı olamaz**
(sürümler farklı). Yani "aynı seed" dediğin dünya aynı çıkmayacak.
Yapıyı doğru koordinata koysan bile **altındaki arazi tutmayacak.**

### 2. Schematic sürümler arası çalışmıyor

Yapıları taşımanın yolu WorldEdit/Litematica. İkisi de sürüm
atlayınca patlıyor:

- WorldEdit: `IOException: Schematic file is missing a "Version" tag`
- Litematica: *"schematic is too new"*

Forumlarda insanların bulduğu tek çözüm **"önce dünyayı sürüm
dönüştür"** — yani zaten benim önerdiğim yola çıkıyorsun, ama
bir de yapıları elle sökmüş oluyorsun.

### 3. Mod blokları çeviride kayboluyor

WorldEdit'in eski schematic yolu sayısal ID kullanıyor; mod blokları
karşı tarafta bambaşka bloğa dönüşüyor. Amulet'i denedim diye bakan
biri de olmuş — Amulet'in resmî dokümanında bile:

> *"editing modded worlds is possible but can result in issues"*

Üstelik Amulet **entity'leri desteklemiyor** (mob, köylü, item frame,
armor stand hepsi gider) ve mod registry'sini okuyamıyor
(açık feature request, hâlâ kapanmadı).

Çalıştığı bildirilen tek yöntem: **mod bloklarını önce vanilla
placeholder'larla değiştirip taşımak.** Senin dünyanın ölçeğinde
bu haftalarca elle iş demek.

---

## Doğru yöntem: dünyayı yerinde yükselt

Minecraft'ın içinde **DataFixerUpper (DFU)** var. Sürüm atlarken
chunk'ları otomatik dönüştürüyor. Normal sürüm güncellemesinde
zaten bu çalışıyor — 1.20.1 → 1.21.1 onun için sıradan bir iş.

NeoForge göç dokümanlarının ortak ifadesi: **"world data is preserved"**.

### Peki mod blokları ne olacak?

Kritik nokta bu, net cevaplıyorum:

**DFU tanımadığı namespace'e dokunmuyor.** `create:cogwheel` diye bir
blok gördüğünde "bu benim değil" deyip **olduğu gibi bırakıyor**.
1.13'ten beri bloklar chunk içinde namespace'li string olarak
saklandığı için de global ID karışması yok.

Yani:

| Durum | Sonuç |
|---|---|
| Mod 1.21.1'de yüklü, registry adı aynı | ✅ Blok aynen korunur |
| Mod 1.21.1'de yüklü, registry adı değişmiş | ⚠️ Blok silinir (nadir) |
| Mod 1.21.1'de yok | ❌ Blok silinir |

**Sonuç: veri kaybı riskinin tamamı mod listesinden geliyor, dünyadan değil.**

Bu yüzden bütün mesai şuraya gitmeli: **her modun 1.21.1 NeoForge
karşılığını bulmak.** Onu hallettiysen dünya kendiliğinden geliyor.

---

## Uygulama

### 1. Yedek

```bash
/stop
tar -czf world_yedek_$(date +%F).tar.gz world/ world_nether/ world_the_end/
```

Eski 1.20.1 sunucusunun **komple** kopyası da dursun (mods + config dahil).
Geri dönmen gerekirse tek şansın bu — **yükseltilmiş dünya 1.20.1'de
bir daha açılmaz.**

### 2. Mod envanteri çıkar

```bash
ls eski_sunucu/mods/ | sed 's/-[0-9].*//' | sort > /tmp/modlar.txt
wc -l /tmp/modlar.txt
```

Her satır için 1.21.1 NeoForge build'i ara. Üç sonuç olur:

| Bulgu | Ne yap |
|---|---|
| 1.21.1 NeoForge sürümü var | ✅ İndir, geç |
| Sadece Fabric var | Alternatif ara veya feda et |
| Hiç yok / terk edilmiş | **Karar ver:** feda mı, alternatif mi |

**Feda edeceğin mod varsa** bunu bilerek yap ve not al — o modun
blokları dünyadan silinecek. Kritikse Bölüm "Mod feda etme" bölümüne bak.

### 3. Tek bir Forge jar bile kalmasın

`mods/` klasöründe Forge-only bir jar kalırsa NeoForge 1.21 **crash
ediyor**. Elle tek tek kontrol et. `start.sh` içindeki `BAD_MODS`
taraması bunu yakalıyor ama gözünle de bak.

### 4. Kaldırılan mod `level.dat`'ta iz bıraktıysa temizle

Bu gerçek bir mayın. Vaka: 1.20.1'de Immersive Portals kullanılmış,
sonra çıkarılmış. `level.dat`'ta kalan
`immersive_portals:normal_skyland_generator` anahtarı yüzünden
1.21.1'e yükseltirken oyun **datafix sırasında çöküyor**.

Custom dimension/generator ekleyen bir mod çıkardıysan:
**`datapackloaderrorfix`** modunu kur — geçersiz referansları
temizleyip dünyanın açılmasını sağlıyor.

### 5. Dünyayı kopyala ve aç

```bash
cp -r eski_sunucu/world      yeni_sunucu/
cp -r eski_sunucu/world_nether yeni_sunucu/   # varsa
cp -r eski_sunucu/world_the_end yeni_sunucu/  # varsa
```

`playerdata/`, `advancements/`, `stats/`, `data/` zaten `world/`
içinde — ayrıca uğraşmana gerek yok.

Sunucuyu aç. İlk açılış **uzun sürer** (chunk'lar yüklendikçe dönüşüyor).

### 6. (Opsiyonel) Toplu dönüştürme

Chunk'lar normalde yüklendikçe dönüşüyor. Hepsini peşin dönüştürmek
istersen:

```bash
java -jar server.jar --forceUpgrade --eraseCache --nogui
```

- `--forceUpgrade`: tüm chunk'ları offline dönüştürür
- `--eraseCache`: aydınlatma/height map cache'ini sıfırlar

⚠️ **Uyarılar:**
- Wiki'ye göre datapack scoreboard ve advancement'ları silebiliyor →
  önce yedeğin olsun
- Sadece **staging kopyada** çalıştır, canlıda değil
- Zorunlu değil. Normal açılış da aynı işi yapıyor, sadece yayarak.

### 7. İlk açılış log'unu oku

Bu adımı atlama. Log'da ara:

```
missing registry entry
No data fixer registered
Unknown block
Failed to parse
```

Her satır = kaybolan bir şey. Hangi mod olduğunu görüp karar verirsin.

### 8. Bir hafta test

Canlıya almadan önce staging kopyada gez: base'ler, madenler,
nether portalları, köyler. Mod makineleri hâlâ çalışıyor mu bak.

---

## Özel durum: dünya Spigot/Paper gördüyse

Dünya geçmişte bir kez Spigot veya Paper'da açıldıysa dikkat.

Spigot chunk'lara `lightPopulated=0` yazıyor. Vanilla/NeoForge
dönüştürücüsü bu bayrağı görünce chunk'ı **atlıyor** → `Sections`
ve `Entities` tag'i olmayan bozuk chunk çıkıyor (MC-133855).

**Belirtisi:** dönüşümden sonra bazı bölgeler boş/siyah.

**Çözüm:** Dönüşümü aynı platformda yap — dünya Spigot'taysa
önce Spigot'ta yükselt, sonra NeoForge'a taşı.

Senin dünyan hep Forge'daysa bu seni ilgilendirmiyor.

---

## Mod feda etmen gerekirse

1.21.1'de karşılığı olmayan bir mod varsa, blokları silinecek.
İki seçenek:

**A) Önceden vanilla'ya çevir (temiz).**
Eski 1.20.1 sunucusunda, henüz kapatmadan:

```
//replace giden_mod:blok minecraft:stone_bricks
```

Ne kaybettiğine **sen** karar vermiş olursun, boşluk kalmaz.

**B) `BMC Datafixer` modu.**
Modpack sürümleri arası mod çıkarırken blokları remap edip
silinmesini engelliyor (5.6M indirme). **Entity'leri remap etmiyor** —
mod mobları/makine entity'leri yine gider.

**Envanter notu:** Mod item'ları oyuncu envanterinde de duruyor.
Transferde kaybolan enchantlı item'ın dedicated sunucuda **timeout**
hatası çıkardığı vaka var. Taşımadan önce oyunculara "riskli mod
item'larını sandığa boşaltın" de; sorun çıkarsa o oyuncunun
`playerdata/<uuid>.dat`'ını sil (envantersiz girer ama girer).

---

## Karşılaştırma

| Yöntem | Mod bloğu | Yapılar | Arazi | Emek | Verdict |
|---|---|---|---|---|---|
| **Yerinde yükseltme** | ✅ Korunur (mod yüklüyse) | ✅ Tam | ✅ Dikiş yok | Düşük | **✅ BU** |
| Aynı seed + schematic | ❌ Bozulur | ⚠️ Sürüm hatası | ❌ Dikiş | Çok yüksek | ❌ |
| Aynı seed + chunk import | ⚠️ DataVersion sorunu | ⚠️ Kısmi | ❌ Dikiş | Yüksek | ❌ |
| Amulet | ⚠️ Garanti yok | ⚠️ Entity gider | — | Orta | ❌ |

---

## Akış

```
1. YEDEK (eski sunucunun tamamı)
   ↓
2. Mod listesini çıkar → her biri için 1.21.1 NeoForge build'i bul
   ↓
   └── Karşılığı olmayan var mı? → önce //replace ile vanilla'ya çevir
   ↓
3. mods/ içinde Forge jar kalmadığını doğrula
   ↓
4. Custom dimension modu çıkardıysan → datapackloaderrorfix kur
   ↓
5. world/ klasörünü olduğu gibi kopyala
   ↓
6. Aç. (İstersen önce --forceUpgrade --eraseCache)
   ↓
7. Log'da "missing registry entry" ara
   ↓
8. Bir hafta staging'de test → canlıya al
```

---

## Özet

**Dünya formatı senin sorunun değil. Mod listesi senin sorunun.**

Chunk'lar kendi kendine yükseliyor, yapıların yerinde kalıyor,
arazide dikiş oluşmuyor. Yapman gereken tek şey: her modun 1.21.1
NeoForge karşılığını kurmak ve ilk açılış log'unu okumak.

Elle chunk seçmek, schematic çıkarmak, koordinat hizalamak yok.
