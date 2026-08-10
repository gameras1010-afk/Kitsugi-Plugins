# 🛡️ SUNUCU İYİLEŞTİRME FİKİRLERİ (2026-08-09) — öncelik sırasıyla

Sunucu: 1.21.1 NeoForge · i5-9400F / 16GB · 209 mod · C2ME(CPU) + Lithium + ServerCore + Spark + LivePanel

---

## 🔥 1. GÜNLÜK OTOMATİK RESTART (EN FAYDALISI)

209 modluk pakette uzun süre açık kalan sunucu **bellek sızıntısı + kaynak şişmesi** yaşar (özellikle 10G heap + native modlar). Günde 1 kez restart = her sabah tertemiz.

```bash
# systemd timer (sabah 05:00 — backup 04:15'ten sonra, mantıklı sıra):
sudo tee /etc/systemd/system/mc-restart.service >/dev/null <<'EOF'
[Unit]
Description=Kitsugi MC restart
[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl restart kitsugi-mc
EOF
sudo tee /etc/systemd/system/mc-restart.timer >/dev/null <<'EOF'
[Unit]
Description=Gunluk MC restart
[Timer]
OnCalendar=*-*-* 05:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now mc-restart.timer
```

**Oyunculara duyuru (chat):** restart öncesi 10-5-1 dk uyarı — LivePanel'de yok ama basit bir "restart uyarı" için Sunucuya `/say` script'i ya da mevcut bir mod; en basiti cron'da restart öncesi `rcon` ile `/say`.

## 🌍 2. WORLD BORDER (dünya sınırı) — dünya/backup/RAM kontrolü

209 mod + Terralith/BOP/BWG ile keşif büyüdükçe: dünya şişer → backup büyür → chunk gen yükü artar. **Sınır koy** (ör. 8000 blok yarıçap = 16k x 16k, çok geniş):
```mcfunction
/worldborder set 16000
/worldborder center 0 0
# ve oyuncuları bilgilendir: sınırda "yavaşlatma" varsayılan
```
→ Region dosya sayısı + backup boyutu + RAM kontrol altında. İleride büyütmek istersen komutla genişletilir.

## 📦 3. DRIVE YEDEĞİNE mods + config DAHİL ET

Şu an `backup-drive.sh` sadece `world/` alıyor. `mods/` + `config/` küçük ama **geri dönüş için altın değerinde** (mod listesi + ayarlar). Script'e ekle:
```bash
# backup-drive.sh içine (sıkıştırma satırına ek):
tar -czf "$TMP_DIR/mc-backup-$DATE.tar.gz" \
  -C "$(dirname "$WORLD_DIR")" "$(basename "$WORLD_DIR")" \
  -C /opt/mc mods config
```
→ Tek yedekte hem dünya hem mod kurulumu. (KEEP=5 hesabında mods+config ~1-2GB ekler — yine de 15GB'ın içinde.)

## 🧪 4. AYLIK GERİ YÜKLEME TESTİ

Yedeğin gerçekten çalıştığını kanıtla (ayda 1):
```bash
rclone copy drive:mc-backups/$(rclone lsf drive:mc-backups | tail -1) /tmp/restore-test/
tar -xzf /tmp/restore-test/*.tar.gz -C /tmp/restore-test/world-test/
# dünyayı 2-3 dk ayrı bir sunucu dizininde aç (port farklı) → spawn'ı ziyaret et → kapat
```
→ "Yedek var ama restore edemiyorum" senaryosu asla yaşanmaz.

## 🔐 5. GÜVENLİK (kısa ama kritik)

```bash
# Firewall: sadece gerekli portlar
sudo apt install -y ufw
sudo ufw allow 25565/tcp        # Minecraft
sudo ufw allow 8080/tcp         # AutoModpack (client'lar indirsin)
sudo ufw allow from 192.168.1.0/24 to any port 22  # SSH sadece yerel ağ
sudo ufw enable

# RCON: sadece localhost + güçlü şifre (server.properties)
rcon.port=25575
rcon.password=<uzun-rastgele>
# ve firewall'da 25575'i AÇMA (rcon zaten 127.0.0.1'e bağlıysa dışarıdan kapalı)

# systemd crash koruması (zaten kurulu — Restart=on-failure kontrol et):
# /etc/systemd/system/kitsugi-mc.service içinde:
# Restart=on-failure
# RestartSec=10
```

## 📝 6. LOG ROTATION

`logs/` klasörü şişer (özellikle crash/verbose modlarla):
```bash
sudo tee /etc/logrotate.d/minecraft >/dev/null <<'EOF'
/opt/mc/logs/*.log /opt/mc/logs/*.gz {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
EOF
```

## 📊 7. GECE SPARK RAPORU (otomatik ölçüm)

Gece 3'te otomatik spark profiler kaydet → sabah bakarsın:
```bash
# cron (rcon ile):
30 3 * * * rcon-cli "spark profiler start --timeout 120" 2>/dev/null || true
# ya da basitçe: günlük restart sonrası spark tps'i logla
0 6 * * * echo "$(date) $(/usr/bin/rcon-cli 'spark tps')" >> /var/log/mc-tps.log 2>/dev/null || true
```
(rcon-cli yoksa `mcrcon` kur — backup scriptinde zaten opsiyonel var.)

---

## 📌 ÖNCELİK TABLOSU

| # | Fikir | Maliyet | Değer |
|---|---|---|---|
| 1 | Günlük otomatik restart | 5 dk | 🔥 En yüksek — bellek/takılma önler |
| 2 | World border | 1 dk | Yüksek — dünya/backup/RAM kontrolü |
| 3 | Yedeğe mods+config | 2 dk | Yüksek — geri dönüş güvencesi |
| 4 | Aylık restore testi | 10 dk | Yüksek — güven |
| 5 | UFW + RCON güvenlik | 10 dk | Yüksek |
| 6 | Log rotation | 2 dk | Orta |
| 7 | Gece spark raporu | 5 dk | Orta |

**Tavsiye:** 1, 2, 3'ü bugün yap (toplam ~10 dk). 4, 5'i bu hafta. 6, 7 fırsat bulunca.
