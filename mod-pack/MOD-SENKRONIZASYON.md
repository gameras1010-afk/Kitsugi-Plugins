# 🔄 SUNUCU → CLIENT OTOMATİK MOD SENKRONİZASYONU (AutoModpack)

**Tarih:** 2026-08-09 · **Doğrulandı:** Modrinth API — AutoModpack 4.0.6 neoforge, MC 1.21.1 ✅ (bugün yayınlandı)

## 🎯 Ne yapar (tam istediğin)

Sunucuya yeni bir mod/config/resource pack eklediğinde → **oyuncular sunucuya girerken otomatik indirir ve kurabilir.** Sunucu, mod paketinin metadata dosyasını + dosyalarını kendi HTTP sunucusunda barındırır; client, sunucuya bağlanınca metadata'yı okuyup eksik/güncel olmayan dosyaları **otomatik indirir**, gerekirse oyunu yeniden başlatmayı ister ve öyle girişe izin verir. Her açılışta güncelleme kontrolü de yapar.

## ✅ Doğrulama (API, 2026-08-09)

- Modrinth: `automodpack` · Loader: **neoforge** · Versiyon: **4.0.6** (release, bugün)
- Dosya: `automodpack-mc1.21.1-neoforge-4.0.6.jar` (~15.4 MB)
- Direct link: https://cdn.modrinth.com/data/k68glP2e/versions/e6HhD1Ik/automodpack-mc1.21.1-neoforge-4.0.6.jar

## 🛠️ Kurulum (basit)

### Sunucu tarafı
```bash
# 1) Jar'ı indir, mods/ klasörüne at:
cd /opt/mc/mods
wget https://cdn.modrinth.com/data/k68glP2e/versions/e6HhD1Ik/automodpack-mc1.21.1-neoforge-4.0.6.jar

# 2) Sunucuyu başlat → config/automodpack.toml oluşur:
#    - Host modpack'i "server" olarak ayarla (server tarafında dosyaları barındırır)
#    - HTTP portunu ayarla (varsayılan 8080 — güvenlik duvarından aç)
#    - mods/, config/, resourcepacks/ içindekiler otomatik pakete girer
# 3) Sunucu çalışırken mod ekle/çıkar → metadata otomatik güncellenir
```

### Client tarafı (oyuncular)
```bash
# Tek şart: oyuncunun client'ında da AutoModpack jar'ı olmalı (TEK elle kurulan mod bu)
# → automodpack-mc1.21.1-neoforge-4.0.6.jar → client mods/ klasörüne
# Sonra oyuncu sunucuya bağlanınca:
#    - Eksik modlar otomatik iner
#    - "Güncelleme var" derse oyunu yeniden başlatır
#    - Yeniden girer → sunucuya kabul ✅
```

## ⚠️ Önemli notlar (dürüst)

1. **İlk sefer:** Oyuncu AutoModpack'i en az bir kere elle kurmalı (bu mod olmadan "otomatik indirme" mantığı zaten çalışamaz — modsuz client sunucuya hiç bağlanamaz). Sonraki her şey otomatik.
2. **Güvenlik (RCE uyarısı):** Topluluk bu tarz "sunucudan kod indirme"yi güvenlik açısından tartışıyor. AutoModpack 4.0.6 bu yüzden **güvenlik yaması** aldı: Modrinth/CurseForge'a eşlenemeyen jar'lar için **10 saniyelik onay istiyor**. Yani yalnızca güvendiğin kaynaklardan mod koyduğun sürece risk düşük.
3. **Senin pakete uyum:** 209 modluk paketin (client modlar dahil) otomatik senkron olur. BetterEnd/BetterNether (Fabric via Connector), Essential, shader klasörü gibi özel dosyalar da sıradan "dosya" olduğu için taşınır.
4. **HTTP portu:** Sunucunun dosya barındırdığı port (8080) client'ların erişimine açık olmalı. Aynı LAN/port yönlendirme mantığı.
5. **Alternatif (daha "el ile"):** **Packwiz** — aynı işi yapar ama client'ın launcher'a bootstrap eklemesi gerekir (MultiMC/Prism tarzı); NeoForge'de Connector ister. AutoModpack daha "tak-çalıştır".
6. **Hazırda olan BetterCompatibilityChecker** (client paketinde) sadece "mod listesi uyuşmuyor" uyarısı verir, indirmez — AutoModpack ile birlikte çalışabilir (ikisi de durabilir).

## 📦 Kurulum özeti

| Taraf | Yap |
|---|---|
| Sunucu | jar'ı mods/'a at → config'te "server" modu + port ayarla → mod ekledikçe otomatik |
| Client | jar'ı mods/'a at (tek elle kurulan) → sunucuya gir → otomatik senkron + restart |

**Sonuç:** "Sunucuya mod ekledim, oyuncular otomatik alsın" hayali = **AutoModpack 4.0.6 (NeoForge 1.21.1)**. Doğrulandı, hazır.
