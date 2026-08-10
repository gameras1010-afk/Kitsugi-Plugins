# 🔧 C2ME OpenCL — AÇILACAK, STABİL YAPILANDIRMA (RX 550 / Polaris)

**Tarih:** 2026-08-07 · **Durum:** 🔧 Hedef — OpenCL'i crash OLMADAN çalıştırmak.

- Amaç: RX 550 (Polaris) + Rusticl ile GPU ivmelendirmesini açık tutmak, ama
  "driver binding" hatalarından kaynaklanan çökmeleri bitirmek.
- Çökmenin asıl sebebi genelde: birden fazla OpenCL platform (Clover + Rusticl)
  varken LWJGL'nin yanlış olanı bağlaması + eski C2ME'de yama yokken -31 hatası.

## 🔧 STABİL ÇALIŞTIRMA ADIMLARI (sırayla uygula)

Sırayla uygula (her adımda tek neden kontrol et):

### 1) Yama scriptiyle düzelt (tek komut)
C2ME güncellenince eski bytecode yaması **silinir** → `-31` geri döner. Artık otomatik:
```bash
cd /opt/mc
python3 patch_lwjgl.py          # mods/ içindeki c2me accel-opencl jar'ını bulup yamalar
python3 patch_lwjgl.py --check  # "YAMALI (4294967295L)" görmelisin
```

### 2) Tek OpenCL platform kalsın (binding hatasının ana sebebi)
Sunucuda hem **Clover** hem **Rusticl** ICD'si varsa LWJGL yanlış platformu bağlayabilir:
```bash
ls /etc/OpenCL/vendors/         # içinde "mesa.icd" ve "clover.icd" AYNI ANDA var mı?
# Clover'ı devre dışı bırak (sadece Rusticl kalsın):
sudo mkdir -p /etc/OpenCL/vendors-disabled
sudo mv /etc/OpenCL/vendors/clover.icd /etc/OpenCL/vendors-disabled/ 2>/dev/null || true
# kontrol:
clinfo -l                       # SADECE "AMD Radeon RX 550 ... (RUSTICL)" görünmeli
```

### 3) fp64 + doğru env ile başlat
`run.sh` / systemd unit'ine ekle:
```
RUSTICL_FEATURES=fp64
```
(Clover'ın OpenCL 1.1'i C2ME-OCL'yi "does not support OpenCL 1.2" diye kapatır; Rusticl+fp64 = OpenCL 3.0.)

### 4) C2ME config'inde fallback + paralellik
`config/c2me.toml` (ilk çalıştırmada oluşur):
```toml
openclAccel.allowIncompatibilityFallback = true   # GPU başlamazsa CPU'ya düş (crash değil)
globalExecutorParallelism = 5                     # 6 çekirdekten 5'i chunk işine
```

### 5) C2ME + C2ME-OCL sürümleri EŞLEŞMELİ
İkisi de aynı sürüm (ör. 0.4.0-alpha.0.116). Uyuşmazsa OpenCL modülü sessizce devre dışı kalır:
```bash
ls mods/ | grep -i c2me
# c2me-neoforge-mc1.21.1-0.4.0-alpha.0.116.jar
# c2me-neoforge-opts-accel-opencl-mc1.21.1-0.4.0-alpha.0.116.jar
```

### 6) Log'dan gerçek hatayı yakala
```bash
grep -iE "opencl|cl_|rusticl|clover|accel" logs/latest.log | tail -40
```
Şu satırları ara:
- `OpenCL error [-31]` → yama + tek ICD + fp64 (adım 1-3)
- `Compiling program NOISE_KERNEL ... (3/7)` → **çalışıyor!** GPU aktif
- `allowIncompatibilityFallback` mesajı → GPU başlamadı, CPU'ya düştü (log'da neden yazar)

### 7) Çalışmıyorsa son çare: Mesa'yı 26.1+ yap
Ubuntu 24.04'te kisak-mesa fresh PPA (C2ME resmi notu: "Mesa 26.1 branch RDNA3/4'te çalışıyor, GCN'de anything can happen"):
```bash
sudo add-apt-repository -y ppa:kisak/kisak-mesa
sudo apt full-upgrade -y
RUSTICL_FEATURES=fp64 clinfo -l     # hala "RUSTICL" görünüyor
```
Geri dönüş: `sudo ppa-purge ppa:kisak/kisak-mesa`

> 💡 **GCN gerçeği:** Polaris'te Rusticl çalışabilir ama "anything can happen" kategorisinde. Eğer worldgen sırasında kernel crash (segfault/driver lockup) oluyorsa, en stabil kombinasyon: **patch + tek ICD + fp64 + fallback=true + kopya dünyada test**. Crash devam ederse OpenCL'yi kapalı tutmak (şu anki durum) en güvenlisi — C2ME CPU threading zaten çok iyi çalışıyor.

---

## Kök neden (LWJGL sign-extension bug)

- C2ME-OCL açılınca: `OpenCL error [-31] (CL_INVALID_DEVICE_TYPE)` → GPU ivmelendirmesi devreye girmiyor, CPU codegen'e düşüyor.
- Log: `does not support OpenCL 1.2` benzeri / `CL_INVALID_DEVICE_TYPE`.

## Kök neden (LWJGL sign-extension bug)

1. LWJGL 3, tüm cihazları sorgulamak için `CL_DEVICE_TYPE_ALL` filtresini **`-1L`** (Java `long`) olarak gönderir.
2. Java native tarafa geçerken 64-bit'e **işaret genişletme (sign extension)** uygular → değer native tarafta `0xFFFFFFFFFFFFFFFF` olur.
3. Mesa **Rusticl** katı kurallı: üst bitleri tanımlı olmayan bu değeri reddeder → `-31` döner. (Eski AMD/NVIDIA sürücüleri sessizce tolere ederdi.)

## Yama (bytecode patch)

- Yer: C2ME mod jar'ının içindeki nested **`lwjgl-opencl-3.3.3.jar`** → `CL.class`.
- Değişiklik: bytecode içindeki `-1L` sabiti
  - `\x05\xff\xff\xff\xff\xff\xff\xff\xff`
  - → işaretsiz 32-bit karşılığı `4294967295L`:
  - `\x05\x00\x00\x00\x00\xff\xff\xff\xff`
- Nasıl yapıldı: nested jar'ı aç → `CL.class`'ı hex editor / script ile yama → jar'ı geri paketle → C2ME jar'ının içine geri koy.

## Doğrulama (çalıştığı kanıtı)

```
RUSTICL_FEATURES=fp64 clinfo -l
  Platform #0: rusticl
    Device #0: AMD Radeon RX 550 / 550 Series (radeonsi, polaris12, ACO, DRM 3.57, 6.8.0-137-generic)

[ChunkMap/]: OpenCL codegen for world minecraft:overworld finished in 506.6 ms
[CLServerWorldContext/]: Compiling program for minecraft:overworld for device OpenCL Device AMD Radeon RX 550 ...
[c2me-clc-0/INFO]: Compiling program NOISE_KERNEL for minecraft:overworld ... (3/7)
```
→ Overworld/Nether/End için shader'lar derlendi ve karta yüklendi. ✅

## ⚠️ ÖNEMLİ: Mod güncellemesi yamayı SİLER

C2ME alpha sürümü sık çıkar; **her C2ME güncellemesinden sonra bu yamayı yeniden uygula.** Güncelleme rutinini şöyle yap:
1. Yedek al
2. Yeni C2ME jar'ını indir
3. Yukarıdaki yamayı tekrar uygula (script haline getirmek istersen `patch_lwjgl.py` yazabilirim)
4. Sunucuyu başlat, log'da `NOISE_KERNEL ... (3/7)` satırını gör

## GPU % neden 0 görünüyor? (beklenen, sorun değil)

- RX 550'de chunk başına noise hesabı **mikrosaniyeler** sürüyor → iş anında bitiyor, GPU uykuya dönüyor.
- Chunky ~1 chunk/sn ürettiği için `gpu_busy_percent` ~%0 kalıyor. Bu, "GPU çalışmıyor" değil; "GPU işini o kadar hızlı yapıyor ki boşta bekliyor" demek.
- **Asıl kazanç:** noise hesapları CPU'nun elinden alındı → CPU kalan aşamalara (yapılar/bloklar/carving) odaklanıyor; ikisi paralel çalışıyor.
- GPU'nun gerçekten meşgul olduğu senaryo: çok oyuncu aynı anda farklı bölgelerde yeni chunk keşfederken (yüksek paralellik). Tek başına chunky'de görünmez.

## Sistem özeti (bu başarıyla birlikte)

| Parça | Değer |
|---|---|
| OS | Ubuntu 24.04 LTS (kernel 6.8.0-137) |
| Mesa / Rusticl | 24+ / rusticl + fp64 ✅ |
| Java | OpenJDK 25.0.3 |
| GPU | RX 550 (polaris12) — C2ME-OCL aktif ✅ |
| Swap | 36GB (4+32) aktif |
| CPU governor | performance (@reboot cron) |
| Servis | systemd kitsugi-mc |
| Modlar | 93, sıfır crash |
