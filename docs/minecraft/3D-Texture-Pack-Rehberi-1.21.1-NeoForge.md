# 1.21.1 / NeoForge — 3D Eşya & Yemek Texture Pack Rehberi

> Hazırlanma tarihi: 2026-09-18
> Hedef: 67 eşyalı modun (Cataclysm, Aether, Twilight Forest, Farmer's Delight, BetterEnd, Cyclic vb.) 3D model + animasyon kapsaması.
> Tüm paketler **%100 client-side**, sunucuya hiçbir şey kurulmuyor.

---

## ⚠️ ÖNCE DÜRÜST GERÇEK (bunu okumadan kurulum yapma)

Önceki mesajda geçen bazı şeyleri tek tek doğruladım. Sonuç:

| İddia | Gerçek durum |
|---|---|
| `Actually 3D Stuff (HMI Edition)` 1.21.1'de kullanılabilir | ⚠️ **Kısmen.** Modrinth'teki resmî proje artık **sadece 1.21.9–1.21.11**. 1.21.1 için **eski 1.21.1–1.21 arşiv sürümü** var ama o **Pommel + Sinytra Connector** (yani Fabric köprüsü) istiyor. Saf NeoForge'da sorunsuz değil. |
| `Pommel` NeoForge'da çalışır | ❌ **Hayır.** Pommel **sadece Fabric**. NeoForge'da Sinytra Connector olmadan yüklenmez. |
| `Hold My Items` (orijinal) NeoForge'da çalışır | ❌ Orijinal **sadece Fabric**. NeoForge için **ReFoxed** (1.21.1 NeoForge 1.0.4) veya **Reforged** (holdmyitemsnf-1.21.1v2.1) portları kullanılır. |
| "Tag sistemi sayesinde 67 modun %100'ü otomatik kapsanır" | ⚠️ **Yarı doğru.** *Tutuş açısı / animasyon* gerçekten tag tabanlıdır → evet, modlu kılıç/kazma/kalkan otomatik doğru duruşa girer. Ama **3D MODEL** tag ile gelmez. Model = her item ID'si için ayrı `models/item/*.json` gerekir. Yani bir resource pack o modu ismen desteklemiyorsa o eşya **2D kalır**. |
| Cataclysm, Aether, Twilight, BetterEnd için hazır 3D pack var | ❌ **1.21.1 için yok.** Bu modlar için yayınlanmış özel 3D model paketi bulunamadı (Cataclysm için var olan pack tam tersini yapıyor: 3D'yi 2D'ye çeviriyor). |

**Özet:** "Sunucudaki tek bir eşya bile boşta kalmıyor" **mümkün değil**. Aşağıdaki kurulum gerçekçi olarak:
- **Animasyon / tutuş açısı:** ~%95+ kapsama (tag tabanlı, tüm modlar)
- **Gerçek 3D model:** Vanilla %100 + Farmer's Delight ~%90 + diğer modlar için değişken (çoğu 2D kalır)

---

## ✅ KATMAN 1 — MOD TABANI (NeoForge 1.21.1)

Resource pack'lerin çalışması için bunlar şart:

| Mod | Kaynak | Not |
|---|---|---|
| **Hold My Items – ReFoxed** | CurseForge `hold-my-items-refoxed` → `holdmyitems-1.21.1-NeoForge-1.0.4.jar` | NeoForge portu, MIT. Elde görünür kollar + kılıç/balta/yay/trident/kalkan/kazma/kürek animasyonları. |
| **Hold My Items – Reforged** (alternatif) | CurseForge `hold-my-items-reforged` → `holdmyitemsnf-1.21.1v2.1.jar` | ReFoxed'a alternatif. **İkisini birden kurma.** |
| ↳ Modlu alet fix | GitHub `akorutant/holdmyitems-reforged-tool-compat` → `holdmyitemsnf-1.21.1-v2.2.0-source-compat.jar` | ⭐ **Senin için kritik.** Reforged 1.21.1 eski `forge:tools` tag'ine bakıyor, NeoForge `c:tools` kullanıyor → **modlu aletlerde animasyon çalışmıyordu.** Bu build onu düzeltiyor. Cyclic / Aether / Twilight aletleri için bunu kullan. |
| **Not Enough Animations** | Modrinth `not-enough-animations` (neoforge, 1.21.1) | 3. şahıs: yemek, içmek, kalkan, yay, merdiven. Zaten kurulu demiştin ✔ |
| **Eating Animation [Forge/NeoForge]** | Modrinth `eating-animations` | Isırma animasyonu. Alttaki uyumluluk packlerinin ön koşulu. |

> ❌ **Pommel kurma.** Fabric-only. NeoForge'da işe yaramaz, `Actually 3D Stuff` 1.21.1 sürümü de bu yüzden senin sunucunda tam çalışmaz.

---

## ✅ KATMAN 2 — ANA 3D EŞYA PAKETİ (birini seç)

| Pack | Modrinth slug | 1.21.1 | Lisans | Neden |
|---|---|---|---|---|
| ⭐ **MB-3D Items Pack** | `mb3d-items-pack` | ✔ | **MIT** | Oyundaki **her vanilla eşyayı** 3D'ye çevirir, vanilla stiline sadık, mod gerektirmez. En güvenli ana temel. Lisansı açık olduğu için eklemeyi kendin de genişletebilirsin. |
| **p1kl's 3D Items** | `p1kls-3d-items` | ✔ | ARR | HMI + Punchy! ile özel uyumlu, daha "karakterli" modeller. |
| **Actually 3D Blocks & Items!** | `actually-3d-blocks-and-items` | ✔ | CC-BY-4.0 | Blok tarafı da 3D (fırın, tezgah, çiçek, ray, mantar, kabak, mace, totem). Eşya paketinin **üstüne** değil, yanına koyulur. |
| **InFGG's 3D+** | `infgg3d+` | ✔ | CC-BY-NC | Kalkanı ekranı kaplamayacak şekilde küçültür + 3D. `More Vanilla Shields` ile birlikte iyi gider. |

**Önerim:** `MB-3D Items Pack` (ana) + `Actually 3D Blocks & Items!` (blok katmanı).

---

## ✅ KATMAN 3 — YEMEK 3D + ISIRMA ANİMASYONU

| Pack | Kaynak | Kapsam |
|---|---|---|
| ⭐ **Fresh Food** | Modrinth `fresh-food` | 1.21.1 ✔. Hem **3D yemek modelleri** hem **ısırma animasyonu**. 2.4M indirme. Vanilla yemeklerin tamamı. |
| **Eating Animations x Farmer's Delight Add-ons** | Modrinth `eating-animations-x-farmers-delight-add-ons` | 1.21.1 ✔. Farmer's Delight + addon'ları (Aquaculture Delight dahil) ısırmalı. |
| **Eating Animations More Mod Compatibility** | Modrinth `eating-animation-more-mod-compatibility` | 1.21.1 ✔. Aether / Twilight Forest / BetterEnd / Naturalist yemekleri. ⭐ senin listendeki modlar için **tam isabet.** |
| **Eating Animations for Farmer's Delight** (alternatif) | Modrinth `eating-animations-for-farmers-delight` | LGPL-3.0, güncel tutuluyor. Yukarıdakiyle çakışabilir, birini seç. |
| **Farmer's 3D** | CurseForge `farmers-3d` | FD yemeklerinin **gerçek 3D modelleri** (hamburger, pie, ham, kelp roll, dumplings...). "Normal" dosyasını indir. |
| **REVIVED Farmer's Delight crops 3D** | CurseForge `revived-farmers-delight-crops-3d` | FD tarlaları/ekinleri 3D + wild crops. |
| **Display Delight** (mod, opsiyonel) | CurseForge `display-delight`, **1.21.1 NeoForge ✔** | FD ve 16 addon'unun **her yemeğini yere 3D koyabilme**. Bu bir mod, resource pack değil — ama masaya tabak dizmek istiyorsan bu. |

---

## ✅ KATMAN 4 — ORTAM / BLOK 3D (senin modlarınla çakışmaz)

| Pack | Slug | Not |
|---|---|---|
| **Motschen's Better Leaves** | `better-leaves` | 1.21.1 ✔, MIT. **Yüksek mod uyumu** — BOP, Oh The Biomes We've Gone, Twilight, BetterEnd yapraklarını da kapsar. |
| **(Bee's) Fancy Crops** | `fancy-crops` | 1.21.1 ✔, mod uyumlu 3D ekinler. |
| **3D Crops Revamped** | `3d-crops` | 1.21.1 ✔ |
| **Better Lanterns** | `better-lanterns` | 1.21.1 ✔ — HMI lantern fiziğiyle çok iyi gider. |
| **RAY's 3D Rails** | `rays-3d-rails` | 1.21.1 ✔, MIT |
| **RAY's 3D Ladders** | `rays-3d-ladders` | 1.21.1 ✔, MIT |
| **Better 3D Beds** | `better-3d-beds` | 1.21.1 ✔ — Comforts / uyku tulumu temasıyla uyumlu |
| **Fine 3D Doors** | `fine-3d-doors` | 1.21.1 ✔, kapı kolları/menteşeler |
| **Traben's 3D Arrow models** | `trabens-3d-arrow-models` | 1.21.1 ✔ — **EMF veya OptiFine gerekir.** Aether/Twilight/Aquaculture okları için. |
| **Cubic Sun & Moon** | `cubic-sun-moon` | 1.21.1 ✔, gökyüzü modlarıyla uyumlu |

---

## 📐 RESOURCE PACK SIRALAMASI (üstteki kazanır)

```
1. Eating Animations More Mod Compatibility     ← en üst (mod-spesifik)
2. Eating Animations x Farmer's Delight Add-ons
3. Farmer's 3D
4. REVIVED Farmer's Delight crops 3D
5. Fresh Food
6. InFGG's 3D+            (kalkan tercih ediyorsan)
7. MB-3D Items Pack       ← ana 3D temel
8. Actually 3D Blocks & Items!
9. Better Lanterns / Fine 3D Doors / Better 3D Beds
10. RAY's 3D Rails / RAY's 3D Ladders
11. Fancy Crops / 3D Crops Revamped
12. Better Leaves
13. Cubic Sun & Moon
14. Traben's 3D Arrow models                    ← en alt
```

---

## 🕳️ AÇIKTA KALAN MODLAR (3D modeli olmayanlar)

Bunlar için **hazır 1.21.1 3D pack yok** — eşyaları 2D kalır, ama **tutuş açısı ve savurma animasyonu HMI sayesinde yine doğru çalışır**:

Cataclysm · The Aether · Twilight Forest · Born in Chaos · Aquamirae · BetterEnd · Alex's Mobs · Cyclic · Advanced Netherite · Aquaculture 2 · Mowzie's Mobs · Deeper and Darker · Quark · More Vanilla Shields · Naturalist · Environmental · Better Archeology · Supplementaries · Carry On · Patchouli

### Bunları da 3D yapmak istersen (tek yol)
Kendi add-on pack'ini yazmak gerekir. İskelet:

```
Kitsugi3D/
├─ pack.mcmeta                 { "pack": { "pack_format": 34, "description": "Kitsugi 3D" } }
└─ assets/
   ├─ cataclysm/models/item/the_incinerator.json
   ├─ aether/models/item/valkyrie_lance.json
   └─ twilightforest/models/item/fiery_sword.json
```

Her dosya `"parent": "minecraft:item/handheld"` yerine BlockBench'te çizilmiş `elements` bloğu içerir + `display` bölümünde `thirdperson_righthand` / `firstperson_righthand` açıları verilir. 1.21.1'de `pack_format = 34`.

> Not: Cataclysm zaten eşyalarının bir kısmını **kendi içinde 3D** olarak gönderiyor (o yüzden "Cataclysm Reimagined" paketi onları 2D'ye indirmek için var). Yani Cataclysm senin için zaten büyük ölçüde 3D.

---

## 🧾 KISA KURULUM ÖZETİ

1. `mods/` → ReFoxed **veya** Reforged(+tool-compat fix) + Eating Animation + NEA
2. `resourcepacks/` → yukarıdaki 14 paketi at
3. Oyun içi sıralamayı yukarıdaki listeye göre diz
4. Pommel / Sinytra Connector / Actually 3D Stuff **kurma** (NeoForge'da kırık)
5. Traben's 3D Arrows istiyorsan **EMF** modunu da ekle

Sunucu tarafında **hiçbir şey değişmiyor** — hepsi client-side, TPS'e etkisi sıfır.
