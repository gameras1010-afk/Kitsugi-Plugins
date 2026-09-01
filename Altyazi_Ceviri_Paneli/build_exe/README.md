# Nexus AI Subtitle Engine — Dağıtım Seçenekleri

## 📦 Seçenek A: Portable Klasör (TAVSİYE EDİLEN)
**"Her şey içinde, Python dahil, hiçbir şey sisteme kurulmaz"**

### Nasıl Yapılır?
1. `kur_portable.bat` → çift tıkla (internete bağlı olmalısın)
2. 5-10 dakika bekle
3. `Nexus_Portable/` klasörü hazır!

### Klasör Yapısı
```
Nexus_Portable/
├── BAŞLAT.bat              ← Çift tıkla, çalışır!
├── BAŞLAT_konsol.bat       ← Hata ayıklama modu
├── python/                 ← Python 3.11 gömülü (sisteme kurulmaz)
│   ├── python.exe
│   └── Lib/site-packages/  ← nicegui, pysubs2, requests...
├── app/                    ← Uygulama kodları
│   ├── ng_app.py
│   ├── ng_config.py
│   └── ...
└── data/                   ← Ayarlar, glossary, API key (burada kalır)
    ├── api_keys.txt
    ├── user_preferences.json
    └── series_glossary.json
```

### Avantajlar
- ✅ Python sisteme kurulmaz
- ✅ USB'ye at, başka PC'de çalıştır
- ✅ Klasörü taşı, her şey gelir
- ✅ Kaldırmak için klasörü sil, bitti
- ✅ ~200 MB

---

## 💿 Seçenek B: Tek EXE (PyInstaller)
**"Tek dosya, her şey içinde"**

### Nasıl Yapılır?
1. `build_exe.bat` → çift tıkla
2. 3-5 dakika bekle  
3. `dist/Nexus.exe` hazır!

### Avantajlar
- ✅ Tek dosya dağıt
- ✅ Python gerekmez
- ✅ ~150 MB

### Dezavantajlar
- ❌ İlk açılış 5-10 saniye yavaş (dosyaları çıkarıyor)
- ❌ Antivirüs bazen şüpheleniyor (normal)

---

## 🔄 Her İki Yöntemi Kullan
İkisi birden yapılabilir:
- Nexus_Portable → günlük kullanım
- Nexus.exe → başkasına göndermek için
