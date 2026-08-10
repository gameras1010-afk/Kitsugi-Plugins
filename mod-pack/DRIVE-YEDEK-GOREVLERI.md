# ☁️ GOOGLE DRIVE OTOMATİK YEDEKLEME — GÖREV LİSTESİ (TASK)
# Kime: Backup PC (Ubuntu 24.04 headless) + Ana PC (tarayıcılı)
# İlerlemeni burada işaretle: yapılan adımın başındaki [ ] -> [x]

## 🖥️ A) HAZIRLIK
- [ ] Ana PC'den Backup PC'ye SSH bağlantısı test edildi: `ssh kullanici@192.168.1.100`
- [ ] Backup PC'de rclone kuruldu: `sudo apt install -y rclone && rclone version`

## 🔑 B) GOOGLE DRIVE BAĞLANTISI (ana PC'nin tarayıcısıyla)
- [ ] Ana PC'ye rclone indirildi: https://rclone.org/downloads/ (Windows: rclone.exe zip)
- [ ] Ana PC'de `rclone authorize "drive"` çalıştırıldı → tarayıcıda Google hesabıyla onaylandı
- [ ] Çıkan **token** kopyalandı
- [ ] Backup PC'de `rclone config` ile: name `drive` → storage `drive` → client_id/secret boş → **"use web browser?" = n** → `config_token>`'a token yapıştırıldı → y/q
- [ ] Test: `rclone lsd drive:` → Drive klasörleri listeleniyor
- [ ] (Yedek yöntem B: URL yöntemi veya Google 403'e karşı kendi client ID'si oluşturma adımları — gerekirse rehberde)

## 📦 C) YEDEK SCRIPTİ
- [ ] `backup-drive.sh` sunucuya kopyalandı: `sudo cp backup-drive.sh /opt/mc/backup-drive.sh`
- [ ] `chmod +x /opt/mc/backup-drive.sh`
- [ ] `nano /opt/mc/backup-drive.sh` ile düzenlendi: `WORLD_DIR` (dünya yolu) + `DRIVE_REMOTE` (drive) + `DRIVE_FOLDER` (mc-backups) + `KEEP` (5)
- [ ] (Opsiyonel) RCON ile save-off için `RCON_PASS` dolduruldu (server.properties'teki rcon.password) — ya da mcrcon kuruldu
- [ ] Elle test: `sudo /opt/mc/backup-drive.sh` → `/var/log/mc-backup.log`'ta "Yüklendi" görünüyor
- [ ] Drive'da kontrol: drive.google.com → `mc-backups` klasöründe tar.gz var

## ⏰ D) OTOMATİK ZAMANLAMA (cron)
- [ ] `sudo crontab -e` → `15 4 * * * /opt/mc/backup-drive.sh >> /var/log/mc-backup.log 2>&1` eklendi
- [ ] Cron listesi kontrol: `sudo crontab -l`

## 📖 E) YÖNETİM & GERİ YÜKLEME (ana PC'den)
- [ ] Yedekleri Drive'dan görüntüleme: drive.google.com → mc-backups
- [ ] Listeleme komutu biliniyor: `rclone lsf drive:mc-backups`
- [ ] Geri yükleme adımları not alındı: `rclone copy drive:mc-backups/<dosya>.tar.gz /tmp/` → `tar -xzf` → sunucuya koy
- [ ] Rotasyon çalışıyor: KEEP(5) sonrası eski yedekler siliniyor (log'da "Eski yedek silindi" görülmeli)

## 🧪 F) TEST & DOĞRULAMA
- [ ] 2-3 gece sonra log kontrol: `/var/log/mc-backup.log`'ta başarılı kayıtlar var
- [ ] Drive'daki yedek sayısı KEEP'i aşmıyor
- [ ] Bir yedek gerçekten geri yüklenip sunucu açılabiliyor (kopya dizinde test)

## 🔄 G) ALTERNATİFLER (Google OAuth sorun çıkarırsa)
- [ ] pCloud (10GB, kullanıcı/şifre — headless kolay) veya Backblaze B2 (10GB, anahtar) kurulumu
- [ ] Script'te `drive:` yerine `pcloud:`/`b2:` değişikliği

## 📦 BOYUT HESABI & DÖNGÜ (15GB limiti)

| Dünya boyutu (ham) | Sıkıştırılmış yedek (~%60-70 küçülür) | KEEP=5 ile toplam |
|---|---|---|
| 1 GB | ~0.4 GB | ~2 GB ✅ |
| 2 GB | ~0.8 GB | ~4 GB ✅ |
| 3 GB | ~1.2 GB | ~6 GB ✅ |
| 5 GB | ~2 GB | ~10 GB ✅ |
| 8 GB | ~3 GB | ~15 GB ⚠️ sınıra dayanır |

**Döngü (eski → yeni, KEEP=5 varsayılan):**
```
Gece 1: A → [A]
Gece 2: B → [A,B]
Gece 3: C → [A,B,C]
Gece 4: D → [A,B,C,D]
Gece 5: E → [A,B,C,D,E]  (5 dolu)
Gece 6: F → [B,C,D,E,F]  ← A SİLİNDİ (en eski)
Gece 7: G → [C,D,E,F,G]  ← B silindi
```
Her zaman son KEEP günün yedeği durur; bir sonraki yedek gelince en eskisi otomatik silinir. Dosya adındaki tarih (YYYY-MM-DD_HHMM) alfabetik sıralandığı için kronoloji garantidir.

**KEEP önerisi (dünya boyutuna göre):**
- Küçük dünya (1-2GB): KEEP=7 → ~5.6GB (7 gün geri)
- Orta (2-5GB): KEEP=5 → ~4-10GB (5 gün geri)
- Büyük (5GB+): KEEP=3 → ~6GB (3 gün geri)
- 15GB dolarsa: ücretli 100GB (1.99$/ay) veya pCloud/B2'ye geçiş (script'te `drive:` → `pcloud:`/`b2:`)

## 🗜️ SIKIŞTIRMA SEVİYESİ (aşırı katı YAPMA — açıklama)

**Dünya verisi (.mca region dosyaları) ZATEN gzip ile sıkışık** → tar.gz üstüne aşırı sıkıştırma (xz -9e) çok az kazandırır (%10-20), ama sunucuya biner:
- xz -9e: dakikalar sürer, 6 çekirdeğin tamamını yakar (TPS/MSPT spike), 2-4GB RAM yer → **değmez**
- gzip -9: gzip -6'ya göre +%1-2, yine uzun sürer

**Önerilen:** `COMPRESS_CMD="gzip -1"` (script'te) — veri zaten sıkışık olduğu için hız > oran. İstersen `zstd -3` (kuruluysa, gzip'ten hızlı + iyi oran; `--ultra` yapma).

**Sunucu güvenliği (cron'a ekle):**
```
15 4 * * * nice -n 19 ionice -c3 /opt/mc/backup-drive.sh >> /var/log/mc-backup.log 2>&1
```
→ yedek işi en düşük öncelikle çalışır, sunucunun CPU'sunu asla aç bırakmaz.

**Asıl yer tasarrufu sıkıştırma değil, KEEP rotasyonudur** (15GB için yedek sayısını ayarla).

---
**Not:** 15GB limiti aşmamak için: tar.gz sıkıştırma + KEEP=5 rotasyonu yeterli (≈5GB). Büyük dünya + çok yedek gerekirse ücretli 100GB plan (1.99$/ay) veya ücretsiz alternatifler.
