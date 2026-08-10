# 🔮 APOTHEOSIS — "Majrusz boşluğunu dolduran" büyü sistemi (1.21.1 NeoForge)

**Tarih:** 2026-08-09 · **Doğrulandı:** Apotheosis 1.21.1-8.7.0 (neoforge, 2 Ağu 2026) + Placebo 1.21.1-9.9.2 ✅

## ❗ ÖNCE DÜRÜST CEVAP: "Birebir aynı mod var mı?" → **HAYIR, YOK** (kanıtlı)

Derin araştırma sonucu (2026-08-09):

1. **Modrinth API:** `majruszs-enchantments` için 1.21.1 ve 1.21 filtreli sorgu → **boş dizi** (sürüm yok)
2. **CurseForge:** Son dosya 1.20.1 / Nisan 2024 (`1.10.8`); 1.21 dosyası yok
3. **GitHub (resmi):** `Majrusz/MajruszsEnchantmentsMod` → son commit **2 yıl önce** (Nisan 2024, "Merged 1.10.8 release"); repo `1.20.X` branch'inde; **1.21 portu/PR'ı/fork'u yok** (21 fork var ama hepsi eski sürümlerde)
4. **Yazar (Majrusz17) modu bıraktı** — 1.20.1'den sonra hiçbir sürüm güncellenmedi

**Yani: "birebir aynı mod" diye bir şey 1.21.1'de yok ve görünürde de gelmeyecek** (yazar aktif değil). Bu yüzden "aynı büyüleri" beklemek yerine, iki gerçekçi seçenek var:
- **A) Apotheosis** (eklendi): 40+ yeni büyü + seviye sınırı kaldırma + affix + boss + zindan — Majrusz DEĞİL ama büyü sistemini doldurur
- **B) Apotheosis'siz vanilla + Quark** (Quark zaten pakette — kendi Telekinesis vb. büyüleri var): daha sade, ama Majrusz'un çeşitliliği olmaz

> Not: Majrusz'un **Telekinesis** büyüsünün benzeri **Quark'ta zaten pakette var** (Quark'ın kendi telekinesis'i). Smelter/Harvester gibi büyüler ise Apotheosis/vanilla tarafında farklı adlarla yaklaşık karşılık bulur. Birebir kopya yok.

## 🎯 Senin istediğin: "Majrusz'un boş bıraktığı her yeri doldursun"

Apotheosis bunu şöyle yapıyor — **büyü sisteminin TAMAMINI devralır** (Majrusz'un yerini doldurur):

| Yer / Sistem | Apotheosis ne yapar |
|---|---|
| **Büyü masası** | Daha yüksek seviye büyüler, **seviye sınırı kaldırılmış büyüler**, daha fazla seçenek → "boş masa" hissi olmaz |
| **Köylü kitapları** | Köylüler **Apotheosis kitapları** satar (farklı kütüphaneci trade'leri) → "kitap satmıyor" hissi olmaz |
| **Kitap/kalem** | Yeni büyüler eklenir; **boş/büyüsüz kitaplar anlam kazanır** |
| **Zindan ganimeti** | Apotheosis zindanları + ganimet → büyü kitabı akışı her yerde |
| **Eşya özellikleri (affix)** | Silahlar/zırhlar rastgele güçlü **affix'ler** kazanır → "özel eşya" hissi |
| **Boss'lar** | Apotheosis boss'ları dünyada gezer, güçlü ganimet düşürür |

**Önemli gerçek:** Apotheosis "eski Majrusz büyülerini geri getirmez" (o büyülerin registry'si 1.21.1'de yok — zaten geçişte silindiler). Ama **büyü arayışı/trade/keşif boşluğunu kendi 40+ büyüsüyle doldurur** — yani oyuncular "büyü basacak bir şey yok" hissini yaşamaz. Vanilla büyüler (Sharpness, Mending...) hep korunur; Apotheosis onların üstüne biner.

## 🛠️ Kurulum (manifeste eklendi)

- **Apotheosis** + **Placebo** (zorunlu dep) manifeste eklendi → `indir_modlar.py` çalıştırınca hepsi iner.
- Apotheosis'in diğer zorunlu dep'leri: Placebo + (Placebo otomatik çeker). Opsiyonel olanlar (JEI, curios vs.) zaten pakette.
- Jar'ları `mods/`'a at, sunucuyu yeniden başlat.

## ⚠️ Dürüst beklenti yönetimi

- **"Majrusz büyülerim geri gelsin"** → Hayır, geri gelmez (yazar bıraktı, registry yok). Bu hiçbir modla olmaz.
- **"Büyü hayatı dolu dolu devam etsin"** → Evet, Apotheosis bunu fazlasıyla yapar (40+ büyü + affix + boss + zindan).
- **Vanilla büyüler** → ✅ HİÇ etkilenmez, korunur.
- **Köylüler** → Vanilla + Apotheosis kitapları satar; Majrusz kitapları yerine Apotheosis kitapları gelir.
- **Uyum:** Quark, Twilight, Aether vb. ile çakışma bilinmiyor (popüler kombinasyon). Yine de kopya dünyada test et → `/spark tps` + birkaç zindan/kitapçı gezip doğrula.

## ✅ Sonuç

**"Boş büyülerin olduğu her yeri bu mod doldursun"** = Apotheosis tam bu iş için. Ekliyoruz; `indir_modlar.py` çalıştır, jar'ları mods'a at, sunucuyu aç — büyü masası, köylüler, ganimet hepsi dolu dolu. Eski Majrusz büyüleri için üzülme — yeni sistem daha derin. 💪
