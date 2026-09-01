# Nexus AI Altyazı Çeviri Paneli — Dağıtım Yöntemleri

## 🏆 Seçenek 1: Setup.exe — Kurulum Sihirbazı (TAVSİYE)
**"İleri → İleri → Bitir — Kurulum bitti, masaüstünden başlat"**

### Nasıl yapılır?
1. `installer/hazirla_installer.bat` → çift tıkla (internet gerekli, ~10 dk)
2. `installer/Output/setup_nexus_v3.exe` oluşur
3. Bu exe'yi istediğin yere kopyala, çift tıkla → kur!

### Kullanıcı deneyimi
```
setup_nexus_v3.exe çift tıkla
  ↓
"Hoş geldiniz" ekranı
  ↓
Kurulum klasörü seç (varsayılan: C:\Program Files\NexusAI\)
  ↓
İleri → Kur → Bitir
  ↓
Masaüstünde "Nexus AI" kısayolu
Program Ekle/Kaldır'da görünür
```

### Ne kurulur?
- Python 3.11 (sadece bu program için, sisteme dokunmaz)
- Tüm Python paketleri (nicegui, pysubs2 vb.)
- FFmpeg araçları
- Nexus AI kodları
- Ayarlar → `%APPDATA%\NexusAI\` (kaldırınca silinmez)

---

## 📦 Seçenek 2: Portable Klasör
**"Hiçbir şey kurulmaz, USB'ye at, her yerde çalışır"**

### Nasıl yapılır?
1. `kur_portable.bat` → çift tıkla
2. `Nexus_Portable/` klasörü oluşur
3. `BAŞLAT.bat` → çalışır!

---

## 💿 Seçenek 3: Tek EXE (PyInstaller)
**"Tek dosya — Nexus.exe"**

### Nasıl yapılır?
1. `build_exe.bat` → çift tıkla
2. `dist/Nexus.exe` hazır

---

## Karşılaştırma

| | Setup.exe | Portable | EXE |
|--|-----------|---------|-----|
| Kurulum | İleri→Bitir | Tek bat | Yok |
| Boyut | ~350 MB | ~300 MB | ~150 MB |
| AppData ayarları | ✅ | ❌ (data/ içinde) | ❌ |
| Program Ekle/Kaldır | ✅ | ❌ | ❌ |
| Masaüstü kısayol | ✅ otomatik | ❌ elle | ❌ |
| USB taşınabilir | ❌ | ✅ | ✅ |
| Antivirüs sorunu | ❌ yok | ❌ yok | ⚠️ nadir |
