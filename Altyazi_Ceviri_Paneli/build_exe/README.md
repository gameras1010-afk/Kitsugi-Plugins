# Nexus EXE Derleme

## Windows'ta EXE Oluşturma

1. `build_exe.bat` dosyasına çift tıklayın
2. 3-5 dakika bekleyin
3. `dist/Nexus.exe` hazır!

## Gereksinimler
- Python 3.10+ (PATH'e eklenmiş)
- İnternet bağlantısı (ilk kurulumda paket indirilir)

## Ne Yapar?
- `dist/Nexus.exe` → tek dosya, Python kurulumu gerekmez
- Çift tıklayınca kendi penceresinde açılır
- Tarayıcı açılmaz
- Görev çubuğunda görünür

## Dosya Boyutu
~120-180 MB (NiceGUI + Chromium gömülü)

## Sorun Giderme
- **Antivirüs uyarısı**: PyInstaller ile yapılan EXE'lerde normal, güvenli
- **İlk açılış yavaş**: ~3-5 saniye normal (dosyaları çıkarıyor)
- **Pencere açılmıyor**: `dist/Nexus.exe --console` ile konsol modunda çalıştır
