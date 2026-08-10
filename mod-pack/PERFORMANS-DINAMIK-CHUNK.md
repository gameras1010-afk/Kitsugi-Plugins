# 🖥️ PERFORMANS & DİNAMİK CHUNK MESAFESİ — i5-9400F / 16GB (2026-08-09)

## 1️⃣ "10 chunk ile ne kadar iyi, kaç kullanıcı?"

İki ayar var, karıştırma:
- **view-distance** = oyuncunun etrafında **yüklenen** chunk sayısı (render için sunucuya gider)
- **simulation-distance** = oyuncunun etrafında **tick eden** (mob, redstone, growth) chunk sayısı → **TPS'i en çok etkileyen bu**

**Senin makinede (i5-9400F 6C/6T, 16GB, C2ME+Lithium+ModernFix+ServerCore) gerçekçi tablo:**

| view / sim | 1-5 oyuncu | 6-10 oyuncu | 11-15 oyuncu | 16+ oyuncu |
|---|---|---|---|---|
| 10 / 5 | 🟢 rahat (TPS 20) | 🟢 iyi | 🟡 MSPT yükselir | 🟠 sim'i düşür |
| 12 / 6 | 🟢 çok iyi | 🟡 kabul | 🟠 yorulur | 🔴 düşür |
| 8 / 4 | 🟢 mükemmel | 🟢 iyi | 🟢 iyi | 🟡 kabul |

**Pratik öneri:** Varsayılan `view=10, sim=5` → **10-15 eşzamanlı oyuncuya kadar iyi.** 16+ için sim=4'e in. (Modların yoğunluğu, mob farmlar, redstone fark yaratır — sayılar tahmindir, `/spark tps` ile kendi limitini bul.)

## 2️⃣ "Yalnızken 12, kalabalıklaşınca 1'er düşsün" → EVET, OTOMATİK

**Sen zaten kurulu olan ServerCore ile yapıyorsun** (mod listende `servercore-neoforge-1.5.19+1.21.1.jar` var). ServerCore'un **Dynamic View Distance** özelliği tam senin istediğin mantık:

**config/servercore.toml:**
```toml
[dynamicViewDistance]
enabled = true
# TPS iyiyken mesafeyi artırır, TPS düşünce kademeli azaltır
maxViewDistance = 12        # tek başına / boş sunucu: 12 chunk
minViewDistance = 4         # çok kalabalık / lag: en düşük 4
maxSimulationDistance = 6   # sim de otomatik (opsiyonel)
minSimulationDistance = 3
# TPS eşiği: (bazı sürümlerde) targetTickTime = 50  → 20 TPS hedefi
```

**Nasıl çalışır:** Sunucu TPS'i sürekli ölçer → TPS 20'ye yakınken mesafeler **maksimuma** çıkar (yalnızken 12) → oyuncu sayısı artıp TPS düşmeye başlayınca **kademeli 1'er 1'er azaltır** (11 → 10 → 9...) → TPS toparlanınca tekrar artırır. Tam senin "1 1 düşsün" mantığın.

**Alternatif mod:** "Dynamic View and Simulation Distances" (someaddon) aynı işi yapar ama **1.21.1 NeoForge sürümü Modrinth'te doğrulanamadı** — ServerCore zaten kurulu olduğu için ona gerek yok.

## 3️⃣ Kullanım

```bash
# 1) Sunucuyu aç (ServerCore config ilk açılışta oluşur)
# 2) config/servercore.toml düzenle → dynamicViewDistance.enabled = true, min/max'ı yaz
# 3) Sunucuyu yeniden başlat (config değişikliği restart ister)
# 4) İzle: /spark tps ile TPS'e bak; oyuncular girip çıkınca /servercore view diye komutla
#    (ServerCore'un kendi komutlarıyla güncel mesafeyi görebilirsin)
```

## 4️⃣ Özet

| Soru | Cevap |
|---|---|
| 10 chunk kaç kullanıcı? | **10-15 eşzamanlı** iyi; 16+ için sim=4 |
| Otomatik "yalnızken 12, kalabalıkta düşsün" var mı? | ✅ **Evet — ServerCore (kurulu)** dynamicViewDistance |
| Ek mod gerekli mi? | ❌ Hayır, ServerCore zaten pakette |
| TPS ölçümü | `/spark tps` ile doğrula, min/max'ı kendine göre ayarla |
