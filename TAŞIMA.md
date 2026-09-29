# 🚚 Yeni GitHub Hesabına Taşıma Rehberi

Bu rehber, **Kitsugi Beta** uygulaması ve eklenti deposunun eski hesabından
(`gameras1010-afk`) yeni hesabınıza taşınmasını adım adım anlatır.
Taşımadan sonra her şey bugünkü gibi otomatik çalışmaya devam eder.

---

## 🧠 Sistem Şu An Nasıl Çalışıyor? (Özet)

Sistemin **iki depo** ve **dört otomasyon** var:

### Depolar
| Depo | Ne işe yarıyor |
|---|---|
| **Kitsugi-Beta** | Uygulamanın kendisi (Android/TV). Kaynak kod + release APK'lar + `domain_fixes.json`. |
| **Kitsugi-Plugins** | Eklenti havuzu. `main` branch = Kotlin kaynak kodları, `builds` branch = hazır `.cs3` dosyaları + `repo.json` + `plugins.json`. |

### Otomasyonlar
| Otomasyon | Depo | Ne yapıyor |
|---|---|---|
| `Derleyici.yml` | Plugins | `main`'e push → **sadece değişen** plugin'leri derler → `.cs3` + `plugins.json`'u `builds` branch'ine push'lar. |
| `Kontrol.yml` | Plugins | Her 9 saatte domain kontrolü → bozuk domain bulursa otomatik PR açar. |
| `KraptorSync.yml` | Plugins | Her gün 09:00 (TSI) Kraptor eklenti versiyonlarını senkronize eder. |
| `update_domains.yml` | App | Her gün 06:00 (TSI) AI destekli domain taraması → `domain_fixes.json`'u günceller. Uygulama bu dosyayı canlı çekip bozuk site linklerini anında onarır. |

### Uygulamanın "otomatik" davranışları (koda gömülü)
1. **Otomatik yükletme:** Uygulama ilk açılışta eklenti deposunu otomatik ekler
   (`CloudstreamRepoRepository.seedDefaultRepoIfEmpty()` → `repo.json` URL'si).
2. **Otomatik plugin güncelleme:** Eklenti sekmesi açıldıkça
   `syncAndAutoUpdate()` çalışır (30 dk'da bir) → `plugins.json`'daki yeni
   sürümleri görüp kurulu eklentileri kendisi günceller.
3. **Otomatik uygulama güncelleme:** Her açılışta
   `api.github.com/repos/<SAHİP>/Kitsugi-Beta/releases/latest` kontrol edilir,
   yeni release varsa FOSS/GMS flavor'ına uygun APK indirilip teklif edilir.
4. **Otomatik domain onarımı:** `domain_fixes.json` canlı olarak çekilir.

> ⚠️ **Tüm bu URL'ler eski sahibe (`gameras1010-afk`) SABİT yazılıdır.**
> Taşıma = yeni hesaba her şeyi kopyalamak **+ bu URL'leri yeni hesaba çevirmek**.
> `.cs3` dosyalarının içine URL gömülü **değildir** (sadece `manifest.json` +
> `classes.dex` içerir); o yüzden **eksenleri yeniden derlemek gerekmez**,
> sadece JSON manifest'ler ve kaynak kodlar güncellenir.

---

## ✅ Taşıma Adımları

### 1) Yeni hesapta iki repo oluştur
Yeni hesabınızda **public** olarak:
- `Kitsugi-Beta`
- `Kitsugi-Plugins`

> Repo isimlerinin aynı kalması en kolayı — koddaki referansların büyük kısmı
> yalnızca "sahip" adını değiştirmeyi gerektirir. İsim değiştirmek isterseniz
> `migrate_urls.py` bunu da destekler (bkz. alttaki kullanım).

### 2) Arena'ya yeni hesabı bağla
Arena arayüzünde mevcut GitHub bağlantısını **kapatıp yeni hesabınızla
tekrar bağlayın**. (Bu oturum şu an eski hesaba bağlı; yeni hesaba push
yapabilmem için bağlantının yeni hesapta olması şart.)

### 3) Benden iste: "taşımayı yap"
Yeni hesabın kullanıcı adını verip bağlantıyı yaptıktan sonra ben şunları yaparım:
1. İki repo da boşsa onları oluştururum (ya da sizinkilere push'larım).
2. `Kitsugi-Plugins` → `main` **ve** `builds` branch'lerinin tamamını push'larım
   (kaynaklar, `.cs3` dosyaları, `repo.json`, `plugins.json`, tüm workflow'lar).
3. `Kitsugi-Beta` → `main` branch'ini push'larım.
4. `migrate_urls.py` ile **her iki depoda da** (main + builds dahil) tüm
   `gameras1010-afk` referanslarını yeni hesabınıza yazarım:
   - `repo.json`, `plugins.json`, `prebuilt_plugins.json` (builds branch)
   - `README.md`, `build_changed.py`, `sync_prebuilt.py`, `tools/*`, Altyazi paneli dosyaları
   - App tarafında: `KitsugiUpdateRepository.kt` (self-update sahibi),
     `CloudstreamRepoRepository.kt` (varsayılan repo + eski repo yönlendirmesi),
     `CloudstreamExtensionTab.kt`, `CloudstreamUrlHelper.kt`, `CsStreamRunner.kt`
     (domain_fixes.json URL'i), `AboutScreen.kt`, testler, `scripts/check_domains.py`
5. App deposuna **yeni `build_release.yml`** workflow'u eklenmiş olur:
   `v*` tag'i atınca (ya da manuel tetikleyince) FOSS+GMS APK'ları derleyip
   otomatik **GitHub Release** oluşturur.
6. İlk release'i tetiklerim → yeni APK (sürüm numarası artırılmış halde) yeni
   hesabınızda yayınlanır.
7. Her şeyi doğrularım (raw URL'ler, workflow çalışmaları) ve size raporum.

### 4) Cihazınıza yeni APK'yı bir kez kurun
- Yeni hesabın `Kitsugi-Beta` release'inden yeni APK'yı indirip kurun
  (mevcut sürüm üstüne kurulur; verileriniz kalır).
- **Bu tek elle işlem.** Bundan sonra:
  - Uygulama kendi kendisini yeni hesabın release'lerinden günceller ✅
  - Eklentiler yeni hesabın `builds` deposundan otomatik yüklenir/güncellenir ✅
  - Domain onarımları yeni hesabın `domain_fixes.json`'ından akarsa ✅

> 📌 Eski hesap tamamen silinene kadar **eski APK'lar eski hesap üzerinden
> çalışmaya devam eder** (eksenler de self-update de eski URL'lere bakıyor).
> Yani geçiş acil değil — yeni APK'yı rahatça kurabilirsiniz.

### 5) (Opsiyonel) GitHub Secrets
Eski hesaba erişiminizi geri alabilirseniz:
- `Kitsugi-Beta` deposunun **Settings → Secrets → `OPENROUTER_API_KEYS`**
  değerini kopyalayıp yeni depoya ekleyin. Yoksa da sorun olmaz: domain
  kontrolü AI olmadan (sadece HTTP tarama ile) çalışmaya devam eder.

---

## 🛠️ migrate_urls.py (URL değiştirici araç)

Manuel yapmak isterseniz (ya da ben yapmazsam) her iki depoda da çalıştırın:

```bash
# Reposunda ismi degistirmezseniz (onerilen):
python3 migrate_urls.py yeni-hesabim

# Repo adlari da degisecekse:
python3 migrate_urls.py yeni-hesabim Kitsugi-Plugins=yeni-eklentiler Kitsugi-Beta=yeni-app

# Once ne degisecekse gormek icin:
python3 migrate_urls.py yeni-hesabim --dry-run

# builds branch icin (yalnizca Kitsugi-Plugins):
git checkout builds
python3 migrate_urls.py yeni-hesabim
git checkout main
```

Çalıştırdıktan sonra `git diff` ile inceleyin, commit + push edin.

---

## 🔍 Doğrulama Kontrol Listesi

Taşıma sonrası hepsi `200` dönmeli:

```
https://raw.githubusercontent.com/<YENI>/Kitsugi-Plugins/builds/repo.json
https://raw.githubusercontent.com/<YENI>/Kitsugi-Plugins/builds/plugins.json
https://raw.githubusercontent.com/<YENI>/Kitsugi-Beta/main/domain_fixes.json
https://api.github.com/repos/<YENI>/Kitsugi-Beta/releases/latest
```

- [ ] `repo.json` içindeki `pluginLists` yeni hesabı gösteriyor
- [ ] `plugins.json` içindeki `url` + `repositoryUrl` alanları yeni hesabı gösteriyor
- [ ] Yeni hesabda `main` + `builds` branch'leri mevcut
- [ ] `Derleyici.yml` bir push'ta ayağa kalkıp `builds`'e yazabiliyor (deneme push'u)
- [ ] App release'inde FOSS + GMS APK var
- [ ] Cihazda yeni APK kurulu → uygulama kendi kendine güncelleme teklifi verebiliyor

---

## ⚠️ Dikkat Edilecekler

1. **Eski hesabı hemen silmeyin.** Eski APK'lar kurulu cihazlar eski hesabı
   kullanıyor. Yeni APK'yı kurduktan ve birkaç gün sorunsuz çalıştırdıktan
   sonra eski hesabı silebilirsiniz.
2. **Release'ler taşınmaz.** GitHub release'leri hesaplar arası otomatik
   kopyalanmaz; CI ile yeni release oluşturulur (ilk release = yeni APK).
3. **Eski release APK'ları** (`v2.4.143` vb.) yeni hesapta bulunmaz; bu
   sorun değildir çünkü self-update her zaman "latest"e bakar ve yeni
   release ondan yenidir.
