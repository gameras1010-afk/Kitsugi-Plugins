#!/bin/bash
# ============================================================
# backup-drive.sh — Aternos mantığı: Google Drive'a otomatik yedek
# 1) dünyayı sıkıştır  2) Drive'a yükle  3) eski yedekleri sil (rotasyon)
#
# Kurulum:
#   chmod +x backup-drive.sh
#   crontab -e  ->  15 4 * * * /opt/mc/backup-drive.sh >> /var/log/mc-backup.log 2>&1
# ============================================================

# ---- AYARLAR (kendine göre düzenle) ----
WORLD_DIR="/opt/mc/world"             # dünya klasörünün TAM YOLU
DRIVE_REMOTE="drive"                  # rclone remote adı
DRIVE_FOLDER="mc-backups"             # Drive'daki hedef klasör
KEEP=5                                # Drive'da tutulacak yedek sayısı
TMP_DIR="/tmp/mc-backups"             # geçici alan
LOG="/var/log/mc-backup.log"
RCON_HOST="127.0.0.1"                 # (opsiyonel) save-off için
RCON_PORT=25575
RCON_PASS=""                          # server.properties rcon.password

# ---- SIKIŞTIRMA SEVİYESİ ----
# Dünya verisi (.mca) ZATEN gzip'li → aşırı sıkıştırma çok az kazandırır,
# sunucuya CPU/RAM yükü bindirir. En iyisi HIZLI mod:
#   gzip -1  (önerilen: hızlı, sunucuyu üzmez)
#   gzip -6  (varsayılan denge)
#   zstd -3  (kuruluysa: gzip'ten hızlı + iyi oran; --ultra YAPMA)
#   xz -9e   (SUNUCUDA KULLANMA: dakikalar sürer, tüm çekirdekleri/RAM'i yer)
COMPRESS_CMD="gzip -1"

# ---- Başla ----
DATE=$(date +%Y-%m-%d_%H%M)
mkdir -p "$TMP_DIR"
echo "===== $DATE başladı =====" >> "$LOG"

# ---- 0) (Opsiyonel) RCON ile save-off: dünya yazarken tutarlı kopya ----
if [ -n "$RCON_PASS" ] && command -v mcrcon >/dev/null 2>&1; then
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASS" "save-off save-all" >> "$LOG" 2>&1
  sleep 2
fi

# ---- 1) Dünyayı sıkıştır ----
WORLD_PARENT=$(dirname "$WORLD_DIR")
WORLD_NAME=$(basename "$WORLD_DIR")
if tar --use-compress-program="$COMPRESS_CMD" -cf "$TMP_DIR/mc-backup-$DATE.tar.gz" -C "$WORLD_PARENT" "$WORLD_NAME" 2>>"$LOG"; then
  echo "Sıkıştırıldı: $(du -h "$TMP_DIR/mc-backup-$DATE.tar.gz" | cut -f1)" >> "$LOG"
else
  echo "HATA: tar başarısız — çıkılıyor" >> "$LOG"
  exit 1
fi

# ---- 2) (Opsiyonel) save-on ----
if [ -n "$RCON_PASS" ] && command -v mcrcon >/dev/null 2>&1; then
  mcrcon -H "$RCON_HOST" -P "$RCON_PORT" -p "$RCON_PASS" "save-on" >> "$LOG" 2>&1
fi

# ---- 3) Drive'a yükle (klasör yoksa oluşturur) ----
rclone copy "$TMP_DIR/mc-backup-$DATE.tar.gz" "$DRIVE_REMOTE:$DRIVE_FOLDER" -v >> "$LOG" 2>&1
if [ $? -ne 0 ]; then
  echo "HATA: rclone yükleme başarısız" >> "$LOG"
  exit 1
fi
echo "Yüklendi: mc-backup-$DATE.tar.gz" >> "$LOG"

# ---- 4) Rotasyon: KEEP'ten fazlasını sil (en yenileri kalır) ----
rclone lsf "$DRIVE_REMOTE:$DRIVE_FOLDER" | sort | head -n -$KEEP | while read -r f; do
  rclone delete "$DRIVE_REMOTE:$DRIVE_FOLDER/$f"
  echo "Eski yedek silindi: $f" >> "$LOG"
done

# ---- 5) Geçici temizlik ----
rm -f "$TMP_DIR/mc-backup-$DATE.tar.gz"

# ---- 6) Özet ----
echo "Kalan Drive yedekleri:" >> "$LOG"
rclone lsf "$DRIVE_REMOTE:$DRIVE_FOLDER" >> "$LOG" 2>&1
echo "===== $DATE bitti =====" >> "$LOG"
