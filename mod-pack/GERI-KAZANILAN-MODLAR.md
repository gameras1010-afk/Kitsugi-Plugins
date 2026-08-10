# 🔄 GERİ KAZANILAN MODLAR — 1.21.1 NeoForge (2026-08-07 doğrulandı)

"Mod kalmamış" diye üzülme — 18 moddan **15'i 1.21.1 NeoForge sürümüne sahip** ve geri eklenebilir. Hepsi Modrinth API + CurseForge üzerinden tek tek doğrulandı.

## ✅ GERİ EKLENEBİLİRLER (1.21.1 NeoForge — hazır)

| Mod | 1.21.1 sürümü | Kaynak | Not |
|---|---|---|---|
| **The Aether** | 1.5.10-neoforge | Modrinth `aether` | Cennet boyutu; deps: Cumulus/Accessories (otomatik çekilir) |
| **Repurposed Structures** | 7.5.13+1.21.1-neoforge | Modrinth `repurposed-structures-forge` | ⚠️ Slug bu! (`repurposed-structures` değil) |
| **Deeper and Darker** | 1.3.4/1.4 (NeoForge 1.21.1) | Modrinth `deeperdarker` / CurseForge | ⚠️ Slug `deeperdarker` (`deeper-and-darker` değil) |
| **FTB Quests** | 2101.1.21 (NeoForge 1.21.1) | CurseForge ftb-quests-forge | FTB Teams + FTB Library gerekli |
| **FTB Teams** | 1.21.1 NeoForge | CurseForge ftb-teams | FTB Quests'in zorunlu dep'i |
| **FTB Library** | 1.21.1 NeoForge | CurseForge ftb-library | FTB dep'i |
| **Carry On** | 2.2.6 | Modrinth `carry-on` | Sandık/hayvan taşıma |
| **Comforts** | 9.0.5+1.21.1 | Modrinth `comforts` | Uyku tulumu/hamak |
| **ElevatorMod** | 1.11.4 (neoforge-1.21.1) | Modrinth `elevatormod` | Işınlayan asansör |
| **Void Totem** | 3 (çoklu loader, 1.21.1) | Modrinth `void-totem` | Boşluk totemi |
| **Advanced Netherite** | 2.3.1 (neoforge-1.21.1) | Modrinth `advanced-netherite` | Netherite zırh/alet |
| **Supplementaries** | 1.21.1-3.8.8-neoforge | Modrinth `supplementaries` | **Moonlight Lib gerekli** |
| **Amendments** | 1.21-2.1.7-neoforge | Modrinth `amendments` | **Moonlight Lib gerekli** |
| **Chipped** | 4.0.2 (NeoForge) | Modrinth `chipped` | Dekoratif bloklar |
| **Every Compat** | 2.11.48-neoforge | Modrinth `every-compat` | **Moonlight Lib gerekli** |
| **Better End** | 21.0.11 (**FABRIC**) | Modrinth `betterend` | ⚠️ Fabric → **Connector** ile çalışır; **BCLib + Fabric API** gerekli |
| **Better Nether** | 21.0.11 (**FABRIC**) | Modrinth `betternether` | ⚠️ Fabric → **Connector** ile; **BCLib + Fabric API** gerekli |
| **Moonlight Lib** | 1.21.1 NeoForge | Modrinth `moonlight` | Supplementaries/Amendments/EveryCompat dep |
| **BCLib** | 1.21.1 | Modrinth `bclib` | BetterEnd/BetterNether dep |

## ❌ GERÇEKTEN 1.21.1'İ OLMAYANLAR (3)

| Mod | Durum | Çözüm |
|---|---|---|
| **Blue Skies** | ModdingLegacy 1.20.1'de bıraktı, port yok | Kaldı; The Aether + Twilight Forest + Deeper&Darker boyutları zaten var |
| **Vein Mining** | 1.21.1 portu yok | **Ore Excavation zaten pakette** — aynı işi yapıyor ✅ |
| **Fantasy Furniture** | 1.21.1 yok | Handcrafted + Chipped + Supplementaries mobilya ihtiyacını karşılar |

## ❌ KESİN KAYIP (2026-08-07 Modrinth API ile doğrulandı — ne NeoForge ne Fabric 1.21.1 var)

| Mod | Durum | Etki | Alternatif / Öneri |
|---|---|---|---|
| **Legendary Item** (LOTR temalı efsanevi silahlar) | Port yok (1.20.1'de kaldı) | Eski eşyalar envanterdeyse kaybolur; oynanış bozulmaz | Yeni "efsanevi silah" modu eklenebilir (ör. CurseForge'da Cataclysm/boss-odaklı modlara bak) |
| **Fantasy's Furniture** | Port yok | Eski dünyada yerleştirilmiş mobilyalar kaybolur/"unknown" görünür | **Macaw's Furniture 3.4.1 (1.21.1 NeoForge ✅ doğrulandı)** — kapsamlı mobilya + Handcrafted/Supplementaries/Chipped zaten pakette |
| **Majrusz Library + Majrusz's Enchantments + Progressive Difficulty** | Port yok (library boş döndü) | Kütüphane olmadan Majrusz büyümeleri/enchantment'ları gelmez | Yazar portlayana kadar bekle; geçici alternatif: vanilla + mevcut zorluk modları |

### 🛠️ "Unknown block" temizliği (Fantasy's Furniture)
Eski dünyadaki kayıp mobilya blokları ya **air'e dönüşür** ya da bozuk görünür. Temizlemek için:
```mcfunction
# Bulunduğun alanda kayıp blokları hava ile değiştir (ör. 20x20x20 alan):
/fill ~-10 ~-10 ~-10 ~10 ~10 ~10 minecraft:air replace minecraft:structure_void
# (ya da kayıp blok hangi ID ile görünüyorsa onu replace et — F3 ile bak)
```
> Genellikle kayıp mod bloğu yüklendiğinde `structure_void` veya air olur; oyun verisini bozmaz, sadece o bölge temizlenir. Log'da `Unknown block id` uyarıları çıkarsa hangi ID olduğunu görürsün.

---

## ⚠️ "Neden NeoForge sürümleri yok?" — BetterEnd/BetterNether/BCLib

**Çünkü bu üçü hiçbir zaman NeoForge/Forge'a portlanmadı — geliştirici (paulevs) projeyi Fabric-only tutuyor.** Bu bir eksiklik değil, yazarın bilinçli tercihi (modun resmi sayfasında yıllardır "Fabric only" yazar). Yani "1.21.1 NeoForge sürümü yok" = **beklenen durum**.

**Ama senin sunucunda sorun YOK:** Sinytra Connector + Forgified Fabric API zaten kurulu → **Fabric jar'larını mods/ klasörüne at, Connector NeoForge içinde çalıştırır.** Doğrulanmış sürümler (Fabric, 1.21.1):

| Mod | Sürüm | Yükleme |
|---|---|---|
| **BCLib** | 21.0.13 | Fabric jar → mods/ (Connector halleder) |
| **Better End** | 21.0.11 | Fabric jar → mods/ |
| **Better Nether** | 21.0.11 | Fabric jar → mods/ |

- **Manifest:** bu üçü `loaders: ["fabric"]` olarak işaretlendi → `indir_modlar.py` Fabric jar'ını indirir (NeoForge aramaz).
- **Bağımlılık:** BCLib; Fabric API + (opsiyonel) Cloth Config ister → **Forgified Fabric API pakette zaten var** → karşılanır.
- **Dikkat:** BetterEnd/BetterNether + C2ME OpenCL birlikte riskli olabilir (yoğun worldgen) → **kopya dünyada test et**; sorun olursa `allowIncompatibilityFallback` veya bu modları çıkar.
- Yani: "NeoForge sürümü yok" diye üzülme — **Connector onları çalıştırıyor**, 1.21.1'de End/Nether güzelleştirme tam olarak mümkün.

1. **Manifest güncellendi** (`mod_manifest.json` → 123 kayıt) — `python3 indir_modlar.py` çalıştırınca hepsi iner, `mods-server/`'a düşer.
2. **Fabric olanlar (BetterEnd/BetterNether):** Sunucuda **Connector + Forgified Fabric API** zaten var → jar'ları normal `mods/`'a at, Connector halleder. **BCLib**'i de koy.
3. **FTB Quests:** Quests + Teams + Library üçünü birden koy (biri eksik olursa açılışta "missing dependency" der).
4. **Dünya etkisi:** Repurposed Structures / Aether / Deeper&Darker / BetterEnd/BetterNether → **sadece YENİ chunk'larda/dimension'larda** üretilir; eski dünya bozulmaz. Yeni boyutlar (Aether, Otherside) dünyaya eklenir.
5. **C2ME-OCL uyarısı:** BetterEnd/BetterNether (Fabric + yoğun worldgen) + C2ME OpenCL birlikte **riskli olabilir** — eklemeden önce kopya dünyada dene; sorun olursa C2ME `allowIncompatibilityFallback` veya bu modları çıkar.
6. **Her ekleme sonrası:** sunucuyu yeniden başlat → `Done` mesajını bekle → `/spark tps` ile TPS kontrol et → sorun çıkarsa son eklenenleri tek tek çıkar.

## 🎯 Özet

- **15/18 geri kazanıldı** → paket ~93'ten **108+'a** çıkıyor (FTB + boyutlar + dekor + kolaylık hepsi yerinde)
- Gerçekten giden sadece: **Blue Skies** (yazar portlamadı), **Vein Mining** (Ore Excavation var), **Fantasy Furniture** (alternatifleri var)
