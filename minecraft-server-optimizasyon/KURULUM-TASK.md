# ✅ KURULUM TASK — Tab Info + MineTogether

> Sadece bu iki mod. Sırayla git, kutuları işaretle.
> **MC 1.21.1 · NeoForge**

---

## ⚠️ İNDİRMEDEN ÖNCE — 2 TUZAK

**1. Tab Info'nun `.jar`'ı NeoForge'da patlayabilir.**
Modrinth `tab-info-0.2.0+mod.jar` için **Fabric API** zorunlu bağımlılık gösteriyor.
NeoForge'da Fabric API yok → **`.zip` (datapack) sürümünü indir.** Bağımlılığı sıfır.

**2. MineTogether iki değil ÜÇ dosya.**
MineTogether → PolyLib ister → PolyLib de **Architectury API** ister. Zinciri kırma.

---

# 🟩 GÖREV 1 — Tab Info (sadece sunucu, 5 dk)

### 1.1 İndir
- [ ] https://modrinth.com/mod/tab-info → **Versions**
- [ ] **`tab-info-0.2.0.zip`** indir ← *datapack, 36 KB*

> ❗ `+mod.jar` olanı **indirme**. Aradığın `.zip`.

```
tab-info-0.2.0.zip
36.421 B
sha1: 15932aeb42d1937916fbc4e6c3d5c18b71f9388f
```

### 1.2 Kur
- [ ] Sunucuyu kapat
- [ ] `.zip`'i **`world/datapacks/`** içine at *(mods değil!)*

```
sunucu/
└── world/
    └── datapacks/
        └── tab-info-0.2.0.zip   ← buraya
```

> Dünya klasörün `world` değilse (`server.properties` → `level-name`) o klasörü kullan.

### 1.3 Başlat ve test
- [ ] Sunucuyu aç
- [ ] `/datapack list` → listede `tab-info` görünüyor mu?
- [ ] Oyuna gir, **Tab'a bas** → ölüm/kill/süre/konum dönüyor mu?

### 1.4 Ayarla
- [ ] `/function tab_info:config` → tıklayarak istemediğini kapat
- [ ] Bilgiler 2 sn'de bir döner, normal

### ✅ Görev 1 bitti
- [ ] Arkadaşlarına **hiçbir şey söylemene gerek yok** — onlarda otomatik görünür

**Sorun çıkarsa:** `.zip`'i sil, sunucuyu yeniden başlat. Tab'da boşluk kalırsa:
```
/scoreboard objectives setdisplay list
```

---

# 🟦 GÖREV 2 — MineTogether (sunucu + HERKES, 20 dk)

> ⚠️ Buradan sonrası **sende, arkadaşlarında ve sunucuda** aynı anda olmalı.
> Biri eksik kalırsa o kişi giremez.

### 2.1 Üç dosyayı indir
- [ ] **Architectury API** → https://modrinth.com/mod/architectury-api
      → 1.21.1 + **NeoForge** sürümü
- [ ] **PolyLib** → https://modrinth.com/mod/polylib
      → `polylib-2100.0.3-build.160-neoforge.jar`
- [ ] **MineTogether** → https://modrinth.com/mod/creeperhost-minetogether
      → `minetogether-neoforge-1.21-6.3.3.jar`

```
polylib-2100.0.3-build.160-neoforge.jar
1.296.954 B | sha1: 960ae5cf4b797a7e530f89bdc190f0051c668183

minetogether-neoforge-1.21-6.3.3.jar
4.882.766 B | sha1: 320cf996f8cafe85398ebcdbf34a7fed6298c6a4
```

> Architectury'yi zaten kullanıyor olabilirsin — `mods/` klasörüne bak,
> varsa **tekrar indirme**, iki kopya çakışma yapar.

### 2.2 Sunucuya kur
- [ ] Sunucuyu kapat
- [ ] 3 dosyayı da sunucunun **`mods/`** klasörüne at
- [ ] Başlat, logu oku:

```bash
grep -iE "error|conflict|incompatible|failed|exception|missing" logs/latest.log | head -30
```
- [ ] Çıktı temizse devam

### 2.3 Kendine kur
- [ ] Aynı 3 dosyayı **kendi** `mods/` klasörüne at
- [ ] Oyunu aç → çökmüyor mu?
- [ ] **Tuş ata:** Ayarlar → Kontroller → `MineTogether` ara
      → Chat / Friends tuşlarını seç *(mesela `O` ve `P`)*
- [ ] Tuşa bas → pencere açıldı mı?

### 2.4 Arkadaşlara dağıt
- [ ] 3 dosyayı bir klasöre koy, zip'le, gönder
- [ ] Not düş: *"mods klasörüne atın, Architectury varsa üzerine yazmayın"*
- [ ] Herkes girdi mi kontrol et

### 2.5 Test
- [ ] Arkadaşını **arkadaş listesine ekle**
- [ ] **DM at**, geliyor mu?
- [ ] Grup sohbeti dene

### ✅ Görev 2 bitti

**Hesap:** MineTogether'da giriş **opsiyonel**. Anonim UUID ile çalışır.
Hesap sadece profil adı + premium için. **Girmene gerek yok.**

---

## 🔴 SORUN ÇIKARSA

| Belirti | Sebep | Çözüm |
|---|---|---|
| Sunucu açılmıyor | Architectury eksik/çift | `mods/` kontrol, tek kopya bırak |
| "Missing dependency polylib" | PolyLib atlanmış | PolyLib'i ekle |
| Arkadaş giremiyor | Onda mod eksik | 3 dosyayı da attığını doğrula |
| Tab boş | Datapack yüklenmemiş | `/datapack list`, klasörü kontrol |
| MineTogether pencere açmıyor | Tuş atanmamış | Kontroller'den tuş ata |

**Her şeyi geri almak:** Attığın dosyaları sil, yeniden başlat. İkisi de dünyaya kalıcı iz bırakmaz.

---

## 📋 ÖZET

| | Nereye | Kim kurar |
|---|---|---|
| `tab-info-0.2.0.zip` | `world/datapacks/` | 🟢 sadece sunucu |
| Architectury API | `mods/` | 🔴 herkes |
| `polylib-*.jar` | `mods/` | 🔴 herkes |
| `minetogether-*.jar` | `mods/` | 🔴 herkes |

**Görev 1'i tek başına yapabilirsin. Görev 2 için arkadaşların müsait olduğu bir akşam seç.**
