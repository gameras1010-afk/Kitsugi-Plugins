# 🔍 ÇAKIŞMA / UYUMSUZLUK KONTROLÜ — "Güncelleyince hata çıkar mı?"

**Kısa cevap:** Modların hepsi 1.21.1 NeoForge için doğrulandı ve güncel; bu yüzden **büyük çakışma riski yok**. Ama "garanti" diye bir şey yok — kontrol edilir. İşte 3 katmanlı kontrol:

---

## 🛠️ KATMAN 1 — ÖN KONTROL (sunucuyu açmadan)

### A) Otomatik tarayıcı (yeni — script)
```bash
# mods/ klasörünü tara:
python3 conflict_checker.py /opt/mc/mods
# → ❌ SORUN   : duplicate mod id / eksik zorunlu dep / bilinen çakışma çifti
# → ⚠️ UYARI   : olası riskler (elle bak)
# → ✅ temiz   : devam et
```

### B) Elle bakılacak bilinen çakışma çiftleri (bu pakette kontrol edildi)
| Çift | Durum |
|---|---|
| **C2ME OpenCL + Noisium** | ❌ Mixin çakışması — **OpenCL modülünü açarsan Noisium'u çıkar** (şu an OpenCL kapalı → sorun yok) |
| **Sodium + Xenon** | ❌ İkisi aynı işi yapar — pakette sadece Sodium var ✅ |
| **Iris + Oculus** | ❌ İkisi aynı işi yapar — pakette sadece Iris var ✅ |
| **Lithium + Canary/Radium** | ❌ Aynı iş — pakette sadece Lithium var ✅ |
| **JEI + EMI/REI** | ⚠️ Birlikte olabilir ama önerilmez — pakette sadece JEI var ✅ |
| **BetterEnd/BetterNether + C2ME-OCL** | ⚠️ Yoğun worldgen — OpenCL kapalıyken sorun yok; açarsan kopya dünyada test |

### C) Bağımlılık eşleşmesi (elle kontrolü hızlı yol)
- Modrinth sayfasında her mod "Dependencies" listesini gösterir; script'in `--json` çıktısı eksik dep varsa söyler.
- Kurulu kütüphaneler: Architectury, Balm, ClothConfig, GeckoLib, Citadel, TerraBlender, Bookshelf, ResourcefulLib, Moonlight, CristelLib, LibraryFerret, FLIB, CoroUtil, CorgiLib, PuzzlesLib, Collective, U-Team-Core, FTB Library, owo-lib, Zeta — hepsi listede var ✅

---

## 🚀 KATMAN 2 — İLK AÇILIŞ KONTROLÜ (log'dan)

```bash
# Sunucuyu başlat:
sudo systemctl start kitsugi-mc
# (veya ./run.sh nogui)

# 1) GENEL hata taraması (en önemli):
grep -iE "mixin.*(fail|error)|conflict|incompatible|Missing or unsupported mandatory dependencies|NoSuchMethod|NoClassDefFound|ClassNotFound" \
  logs/latest.log | head -40

# 2) Mod yükleme hataları:
grep -iE "failed to (load|apply)|error loading mod|found mod file.*(failed|error)" logs/latest.log | head -20

# 3) Çakışma özelinde:
grep -iE "mixin apply failed|mod.*conflict|duplicate mod|same mod id" logs/latest.log | head -20
```

**Temizse:** hiçbir satır çıkmaz (veya sadece önemsiz WARN). `Done (X.XXXs)!` görürsen modlar yüklendi.

---

## 🧪 KATMAN 3 — OYUN İÇİ DOĞRULAMA

```bash
# 1) TPS sağlıklı mı:
/spark tps
/spark health

# 2) Profil (30 sn):
/spark profiler start
# bekle
/spark profiler stop

# 3) Dünyada gezin: birkaç biyom (Terralith/BOP/BWG), yapı (YUNG's), boyut (Aether/Twilight/End)
#    → crash yoksa + TPS 20'de kalıyorsa paket uyumlu demektir

# 4) Herhangi bir crash olursa:
ls crash-reports/ | tail
#    → son crash dosyasını bana at (içindeki "Mod File: xxx" satırı suçluyu söyler)
```

---

## 🔧 Çakışma bulunursa ne yap?

| Durum | Çözüm |
|---|---|
| Eksik zorunlu dep | `conflict_checker` hangi dep'in eksik olduğunu söyler → indir, mods/'a at |
| Duplicate mod id | İki jar aynı modu içeriyor → birini sil (eski sürüm olanı) |
| Bilinen çakışma çifti | Script söyler → birini çıkar (ör. Noisium, OpenCL açıkken) |
| Mixin apply failed | Crash log'daki "Mod File" satırına bak → o modu güncelle/çıkar |
| TPS düşük / takılma | `/spark profiler` çıktısıyla en çok CPU yiyen modu bul → ayarla/çıkar |

---

## ✅ BU PAKET İÇİN SONUÇ (şu an)

- Sunucu **8.6s'de açılıyor, sıfır crash, TPS 20** → mevcut durum uyumlu.
- Güncelleme = sürüm yenileme (zaten güncel doğrulandı) → **yeni çakışma beklemiyorum.**
- Tek dikkat: **OpenCL modülünü açarsan** Noisium'u çıkar + BetterEnd/BetterNether'ı kopya dünyada test et.
- Güncelleme sonrası KATMAN 2'deki grep'leri çalıştır → çıktıyı bana at, yorumlayayım.
