# ☁️ GOOGLE DRIVE OTOMATİK YEDEKLEME — KURULUM REHBERİ
# (rclone + Google Drive + cron + rotasyon — "Aternos mantığı")
# 2026-08-07 · Backup PC: Ubuntu 24.04 headless · Main PC: tarayıcılı

## 🖥️ Adım 0 — Ana PC'den yedek PC'ye bağlan (SSH)
Zaten bağlanıyorsun; kısaca hatırlatma:

# Windows'ta: Windows Terminal / PowerShell
ssh kullanici@192.168.1.100

# Linux/Mac'te:
ssh kullanici@192.168.1.100

> 💡 Ana PC'den yedek PC'ye her zaman aynı şekilde SSH ile giriyorsun.
> Drive kurulumu da bu SSH oturumu üzerinden yapılacak — ekstra bir
> "masaüstü" veya "uzak masaüstü" gerekmez.

## 🔑 Adım 1 — Backup PC'ye rclone kur
```bash
sudo apt install -y rclone
rclone version      # v1.6x+ görmelisin
```

## 🔐 Adım 2 — Google Drive'a bağlan (ana PC'nin tarayıcısıyla!)

### Yöntem A (ÖNERİLEN): Token'ı ana PC'de üret, backup PC'ye yapıştır
1. **Ana PC'nde** (Windows/Linux fark etmez) rclone'un tek dosyalık programını indir:
   - https://rclone.org/downloads/ → "Windows - Intel/AMD - 64 Bit" (zip içinden `rclone.exe`)
   - Linux ana PC için: tek binary, `chmod +x rclone && ./rclone`
2. Ana PC'de terminal aç, şunu çalıştır:
   ```
   rclone.exe authorize "drive"
   ```
   (Linux'ta: `./rclone authorize "drive"`)
3. **Tarayıcın otomatik açılır** → Google hesabınla giriş yap → izin ver.
4. Terminalde `Paste the following into your remote machine --->` ile başlayan
   uzun bir **token** (JSON gibi) çıkar. Onu kopyala.
5. **Backup PC'deki SSH oturumuna geç**:
   ```bash
   rclone config
   # n (new remote)
   # name> drive
   # Storage: "drive" (Google Drive) seç
   # client_id: boş bırak (Enter)
   # client_secret: boş bırak (Enter)
   # scope: boş bırak (Enter)  [drive]
   # service_account_file: boş bırak
   # "Use web browser to automatically authenticate rclone with remote?" → n  ← HAYIR DE!
   # "config_token>" istediğinde → ADIM 4'teki token'ı YAPIŞTIR
   # "Configure this as a Shared Drive?" → n
   # "Keep this remote?" → y
   # Quit
   ```
6. Test:
   ```bash
   rclone lsd drive:
   ```

### Yöntem B: Backup PC'de config aç, ana PC'de tarayıcıyla onayla
1. Backup PC'de: `rclone config` → `n` → name `drive` → `drive` → client_id/secret boş
2. "Use web browser...?" → **n** → sana uzun bir **URL** verir (127.0.0.1:53682...)
3. O URL'yi **ana PC'nin tarayıcısına** kopyala-yapıştır → Google girişi → izin ver
4. Tarayıcı "localhost"a bağlanamaz der → sayfadaki **authorization code**'u kopyala
5. Backup PC terminalindeki `config_token>`'a yapıştır → `y` → `q`
6. Test: `rclone lsd drive:`

> ⚠️ Google "403 access_denied / app not verified" derse (rclone'un varsayılan
> client ID'si bazen bloklanır):
> - https://console.cloud.google.com → proje oluştur → "Google Drive API"yi etkinleştir
> - OAuth consent screen → External → test user olarak kendi Google adresini ekle
> - Credentials → OAuth client ID → "Desktop app" oluştur → client_id + client_secret
> - Bunları rclone config'te ilgili sorulara yapıştır, sonra yine authorize akışı

## 📦 Adım 3 — Yedekleme scripti (backup-drive.sh)
Script: `mod-pack/backup-drive.sh` (bu klasörde) → /opt/mc/backup-drive.sh'ye kopyala:
```bash
sudo cp backup-drive.sh /opt/mc/backup-drive.sh
sudo chmod +x /opt/mc/backup-drive.sh
# İÇİNDEKİ WORLD_DIR ve DRIVE_FOLDER değerlerini kendine göre düzenle
nano /opt/mc/backup-drive.sh
```

## ⏰ Adım 4 — Cron (her gece 04:15)
```bash
sudo crontab -e
# satır ekle:
15 4 * * * /opt/mc/backup-drive.sh >> /var/log/mc-backup.log 2>&1
# kaydet, kapat. Test:
sudo /opt/mc/backup-drive.sh
```

## 📖 Adım 5 — Yedekleri yönetme (ana PC'den)
- **Görüntüle:** drive.google.com → `mc-backups` klasörü (ana PC'de tarayıcıyla)
- **Sunucudan listele:** `rclone lsf drive:mc-backups`
- **Elle geri yükle:**
  ```bash
  rclone copy drive:mc-backups/2026-08-07_0415.tar.gz /tmp/
  tar -xzf /tmp/2026-08-07_0415.tar.gz -C /opt/mc/
  ```
- **Rotasyon:** script KEEP değişkeni kadar (varsayılan 5) yedeği tutar, eskilerini siler

## 💾 Alan hesapları (15GB'a takılmamak için)
- Dünya `tar -czf` ile ~%50-70 küçülür (1-5GB dünya → 0.5-1.5GB yedek)
- KEEP=5 → en fazla ~5GB → 15GB'ın rahat içinde
- Yedek sadece `world/` (+ istenirse DIM klasörleri) içerir, log/backup hariç

## 🔄 Alternatifler (Google OAuth uğraştırırsa)
- **pCloud** (10GB ücretsiz): rclone'da kullanıcı adı/şifre ile bağlanır — OAuth tarayıcı akışı yok, headless için en kolayı
- **Backblaze B2** (10GB ücretsiz): account_id + application_key — aynı şekilde kolay
- **TeraBox** (1TB ücretsiz): rclone'da webdav ile; kurulumu biraz daha zahmetli
- Aynı script sadece `drive:` yerine `pcloud:` / `b2:` yazınca çalışır
