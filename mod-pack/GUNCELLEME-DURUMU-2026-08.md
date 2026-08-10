# 🔄 GÜNCELLEME DURUMU — 209 MOD (2026-08-07, API ile doğrulandı)

## ✅ Kontrol edilen KRİTİK modlar (kurulu = en güncel, güncelleme GEREKMİYOR)

| Mod | Kurulu | API'deki en güncel | Durum |
|---|---|---|---|
| C2ME (NeoForge) | 0.4.0-alpha.0.116 | 0.4.0-alpha.0.116 | ✅ Güncel |
| ModernFix | 5.27.20+mc1.21.1 | 5.27.20+mc1.21.1 | ✅ Güncel |
| Lithium | 0.15.4 | 0.15.4 | ✅ Güncel |
| Quark | 4.1-482 | 4.1-482 | ✅ Güncel |
| Aether | 1.21.1-1.5.10 | 1.21.1-1.5.10 | ✅ Güncel |
| Supplementaries | 1.21.1-3.8.8 | 1.21.1-3.8.8 | ✅ Güncel |
| FerriteCore | 7.0.3 | 7.0.3 | ✅ Güncel |
| Every Compat | 1.21-2.11.48 | 1.21-2.11.48 | ✅ Güncel |

**Sonuç:** Paketin ana modları güncel. Geri kalan ~200 mod için script **indirme anında en güncel 1.21.1 NeoForge sürümünü** otomatik seçer (release > beta > alpha önceliği) — ayrıca elle kontrol etmene gerek yok.

## 🛠️ Güncellemek için tek komut

```bash
# mod-pack/ klasöründe (interneti olan makinede — sunucu veya ana PC):
python3 indir_modlar.py
# → en güncel sürümleri indirir, SHA1 doğrular
# → mods-server/ (hepsi) + mods-client/ (client-only) klasörlerine ayırır
# → MC-1211-ModPaketi.zip üretir (mods + rehber + link listesi)

# DENEYSEL OpenCL jar'ı DAHİL etmek istersen (şu an kapalı — tavsiye edilmez):
# python3 indir_modlar.py --include-experimental
```

Sonra: `mods-server/*.jar` → sunucunun `mods/` klasörüne kopyala (eskilerin üstüne yazar), client tarafına da `mods-client/*.jar`. **Önce yedek al, sonra güncelle.**

## 📋 Önemli notlar (bu paket için)

1. **BetterEnd/BetterNether/BCLib/WorldWeaver/Wunderlib** = Fabric sürümleri → `mods/`'a at, **Connector** zaten kurulu olduğu için çalışır.
2. **CurseForge-only 19 mod** (Twilight, Alex's Mobs, Born in Chaos, Epic Terrain, FTB Quests/Teams/Library, Dungeon Crawl, Ore Excavation, Goblin Traders, Extra Golems, ServerCore, Loot Integrations, More Mobs, GlitchCore, ItemPhysic, Domum Ornamentum, More&More Armor, Farmer's Structures) → script curse.tools üzerinden indirir; bir tanesi takılırsa `LINK_LISTESI.txt`'te manuel link çıkar.
3. **C2ME OpenCL jar'ı kurulu ama devre dışı** (Polaris crash riski) — manifestte `experimental` işaretli, script onu **atlar**. İstemiyorsan `mods/`'dan silmen yeterli.
4. **Noisium 2.7.0** listede var (C2ME OpenCL kapalıyken sorun çıkarmaz; OpenCL'i açarsan çakışır — o zaman Noisium'u çıkar).

## 🧪 Güncelleme sonrası doğrulama

```bash
# Sunucuyu yeniden başlat:
sudo systemctl restart kitsugi-mc
# TPS + hata kontrolü:
/spark tps
grep -iE "error|exception|failed" logs/latest.log | tail -20
```
Takılan bir mod olursa: `logs/latest.log`'daki "Found mod file ... failed" satırını buraya at → çözelim.
