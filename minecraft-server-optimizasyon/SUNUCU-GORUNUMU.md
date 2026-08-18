# 🎨 SUNUCU LİSTESİ GÖRÜNÜMÜ — MOTD, İKON, OYUNCU SAYISI

> **MOD GEREKMİYOR.** Ne sana ne arkadaşlarına.
> Bunların hepsi vanilla Minecraft'ın kendi özelliği.
> Sadece `server.properties` + 1 tane PNG dosyası.

---

## Çok oyunculu ekranında ne görünüyor?

```
┌──────┬─────────────────────────────────────────┬──────────┐
│      │  Kitsugi                                │   3/20   │  ← max-players
│ IKON │  Kırılan yeniden doğar                  │   ▏▎▍ 12ms│
│ 64x64│  ← MOTD (2 satır, renkli)               │          │
└──────┴─────────────────────────────────────────┴──────────┘
```

| Parça | Nereden gelir | Mod? |
|---|---|---|
| Sunucu adı (üst satır) | Oyuncunun kendi yazdığı isim — **sen kontrol edemezsin** | — |
| MOTD (2 satır açıklama) | `server.properties` → `motd=` | ❌ Yok |
| İkon (soldaki kare) | Sunucu kökünde `server-icon.png` | ❌ Yok |
| Oyuncu sayısı `3/20` | Otomatik. `20` = `max-players` | ❌ Yok |
| Ping çubukları | Otomatik | — |

---

# 1️⃣ MOTD — açıklama yazısı

`server.properties` dosyanı aç, `motd=` satırını bul.

### Renk kodları

`§` karakterini properties dosyasına doğrudan yazmak bazı editörlerde
bozulur. **Garanti yol:** `\u00A7` yaz. İkisi de aynı şey.

```properties
motd=\u00A76\u00A7lKITSUGI\u00A7r \u00A78» \u00A77Kirilan yeniden dogar\n\u00A7a1.21.1 NeoForge \u00A78| \u00A7bArkadas sunucusu
```

Bu şöyle görünür:
```
KITSUGI » Kirilan yeniden dogar
1.21.1 NeoForge | Arkadas sunucusu
```
(ilk satır altın sarısı kalın, ikinci satır yeşil/mavi)

### `\n` = alt satır. MOTD **en fazla 2 satır**, 3. satırı göstermez.

### Renk tablosu

| Kod | Renk | Kod | Renk |
|---|---|---|---|
| `\u00A70` | Siyah | `\u00A78` | Koyu gri |
| `\u00A71` | Koyu mavi | `\u00A79` | Mavi |
| `\u00A72` | Koyu yeşil | `\u00A7a` | Açık yeşil |
| `\u00A73` | Turkuaz | `\u00A7b` | Açık mavi |
| `\u00A74` | Koyu kırmızı | `\u00A7c` | Kırmızı |
| `\u00A75` | Mor | `\u00A7d` | Pembe |
| `\u00A76` | Altın | `\u00A7e` | Sarı |
| `\u00A77` | Gri | `\u00A7f` | Beyaz |

| Kod | Biçim |
|---|---|
| `\u00A7l` | **Kalın** |
| `\u00A7o` | *İtalik* |
| `\u00A7n` | Altı çizili |
| `\u00A7m` | ~~Üstü çizili~~ |
| `\u00A7k` | Karışan gizli yazı (efekt) |
| `\u00A7r` | **Sıfırla** — rengi bitirir |

⚠️ `\u00A7r` yazmazsan renk satır sonuna kadar devam eder.

### Hazır örnekler

**Sade ve şık:**
```properties
motd=\u00A76\u00A7lKITSUGI\n\u00A77Kirilan yeniden dogar
```

**Bilgi dolu:**
```properties
motd=\u00A7b\u00A7lKITSUGI \u00A78[\u00A7a1.21.1\u00A78]\n\u00A7eSurvival \u00A78| \u00A7dModlu \u00A78| \u00A77Sadece davetli
```

**Dikkat çekici:**
```properties
motd=\u00A78\u00A7m                                        \n\u00A76\u00A7l   K I T S U G I   \u00A7r\u00A77- kirilan yeniden dogar
```

---

# 2️⃣ İKON — soldaki kare resim

## Kurallar (bunlara uymazsan görünmez)

| Şart | Değer |
|---|---|
| Dosya adı | **`server-icon.png`** — birebir, harfi harfine |
| Boyut | **64 × 64 piksel** — tam olarak. 63 veya 65 olmaz |
| Format | PNG |
| Yer | Sunucu **kök klasörü** — `server.jar` ile aynı yerde. `mods/` değil, `config/` değil |

## Sana bir tane hazırladım

`server-icon.png` — bu klasörde, 64×64, hazır. Kintsugi temalı
(altın çatlaklı taş blok). Beğenmezsen kendin yaparsın.

## Kendi resmini 64×64 yapmak

**Yol 1 — site:** `resizeimage.net` → 64×64 → PNG indir

**Yol 2 — Paint (Windows):**
Resmi aç → Yeniden Boyutlandır → **Piksel** seç →
"En boy oranını koru" işaretini **KALDIR** → 64 / 64 yaz →
Farklı Kaydet → PNG → adı `server-icon.png`

---

# 3️⃣ OYUNCU SAYISI

```properties
max-players=20
```

Soldaki sayı (kaç kişi online) otomatik gelir, dokunamazsın.
Sağdaki sayı bu satır.

💡 `20` yazmak sunucuya yük bindirmez — sadece bir üst sınır.
Ama listede "3/20" yerine "3/8" yazması daha samimi durur, sana kalmış.

---

# 4️⃣ FAZLADAN AYARLAR

```properties
# Oyuncu listesinin üstüne gelince isimler görünsün mü?
# false yaparsan "Anonim oyuncular" der — gizlilik için
enable-status=true

# Sunucu listesinde oyuncu isimleri gözüksün mü
hide-online-players=false
```

---

# ✅ UYGULAMA

1. Sunucuyu **kapat**
2. `server.properties` aç, `motd=` satırını değiştir, kaydet
3. `server-icon.png` dosyasını sunucu kök klasörüne at
4. Sunucuyu **aç**
5. Oyunda sunucu listesinden **yenile** butonuna bas

### Görünmüyorsa

| Sorun | Sebep |
|---|---|
| İkon gelmiyor | Boyut 64×64 değil · dosya adı yanlış · yanlış klasörde |
| İkon eski kalmış | Client önbelleği — sunucuyu listeden **sil ve yeniden ekle** |
| MOTD'de `§` görünüyor | `\u00A7` yerine gerçek `§` yazmışsın, editör bozmuş |
| MOTD'de `\n` yazıyor | Properties dosyasında `\n` düz metin olmalı, gerçek satır atlama değil |
| Hiçbiri değişmedi | Sunucuyu yeniden başlatmadın |

---

# 🎨 DAHA FAZLASINI İSTERSEN (opsiyonel, mod)

Yukarıdakiler yetmezse — RGB gradient renkler, her yenilemede
**rastgele MOTD**, sahte oyuncu sayısı gibi şeyler istiyorsan:

```
MiniMOTD 2.1.3  ·  minimotd-neoforge-mc1.21.1-2.1.3.jar  ·  1.6 MB
modrinth.com/mod/minimotd
```

**Doğrulandı:** `client_side: unsupported`, `environment: server_only`,
`loaders: ["neoforge"]`, `game_versions: ["1.21.1"]`, bağımlılık **yok**.
MIT lisans, 233.514 indirme, jpenilla (güvenilir geliştirici).

🔑 Hesap gerekmez. **Arkadaşların hiçbir şey kurmaz** — sadece sunucuya atılır.

Ne ekler:
- `<gradient:#ff0000:#0000ff>KITSUGI</gradient>` gibi RGB geçişli renkler
- Rastgele MOTD listesi (her yenilemede farklı yazı)
- Oyuncu sayısını sahte gösterme
- Birden fazla ikon arasında rastgele seçim

⚠️ **Ama gerek yok.** Vanilla `§` kodları %90 iş görür. Bu mod sadece
gradient ve rastgelelik için. Önce vanilla'yı dene, yetmezse bak.
