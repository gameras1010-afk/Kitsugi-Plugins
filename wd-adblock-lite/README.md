# WebDisplays AdBlock Lite (wd-adblock-lite) — MCEF için eklentisiz reklam filtresi

**Tek cümle:** Chrome eklentisi yüklemek motorca yasak; ama uBlock'un işinin özü olan
**istek iptali + boş-JSON stub + cosmetic/JS enjeksiyonu** CEF'in *açık* API'leriyle
yapılabiliyor — bu mod tam olarak bunu yapıyor, **MCEF'i de WebDisplays'i de forklamadan**.

## Neden "bozmadan" olur (kaynak-kodu kanıtları, Eyl 2026)
| Kanca | Kanıt | Durum |
|---|---|---|
| `CefClient.addRequestHandler()` (java-cef, tek-slot) | MCEF ve WebDisplays **hiçbir yerde çağırmıyor** | → slot boş, biz alıyoruz |
| `CefRequest.setURL()` (istek hedefini stub'a çevirme) | java-cef `CefRequest.java:365` abstract public | → çalışır |
| `onBeforeResourceLoad → true` (alt-istek iptali) | java-cef `CefResourceRequestHandler:49` | → çalışır |
| `MCEFClient.addLoadHandler()` (JS enjeksiyon kanalı) | MCEF `MCEFClient.java:62` public; WD'nin ses kontrolü **aynı** `executeJavaScript`'i kullanıyor | → motor bunu zaten yapıyor |
| `mcef.properties` config | yalnızca 4 anahtar, CEF switch'leri hardcoded | → proxy/eklenti config'ten girilemez, bu mod gerekçeli |

## Dosyalar
```
wd-adblock-lite/
├── build.gradle / settings.gradle          # NeoForge 21.1.215, Java 21, ModDevGradle 2.0.78
├── libs/                                   # (sen koyacaksın) mcef-neoforge.jar — derleme için
└── src/main/java/com/example/wdablite/
    ├── WdAdblockLiteMod.java               # MCEF gec-doğduktan sonra handler'ları bağlar (crash-safe)
    ├── Rules.java                          # config/wd-adblock-lite/rules.txt (regex; @ = stub)
    ├── AdBlockRequestHandler.java          # iptal + stub (data:application/json,{})
    └── CosmeticInjector.java               # YT/Twitch'e CSS gizleme + ad-showing skipper JS
```

## Derleme (10 dk, oyuncunun/ID makinesinde — sandıkta maven yok)
1. **JDK 21** + **Gradle 8.8+** kur.
2. Modrinth/CurseForge'dan **MCEF (neoforge, 1.21.1)** jar'ını indir, `libs/mcef-neoforge.jar` olarak koy
   (yalnızca `compileOnly`; oyun içinde jar'ın kendisi mods/'ta olacak).
3. `gradle wrapper --gradle-version 8.10` (bir kez), sonra `./gradlew build`.
4. `build/libs/wd-adblock-lite-0.1.0.jar` → **yalnız client**'ların `mods/` klasörüne (sunucuya GEREK YOK,
   manifest client-only; ama sunucuya koyarsan da bir şey bozulmaz).
5. Oyunu aç → `config/wd-adblock-lite/rules.txt` kendiliğinden oluşur. Log'da
   `attached to MCEF — N aktif kural` satırını gör (ilk ekran açılışında).

## Kural dosyası (rules.txt)
- Satır = tam URL'e karşı regex (case-insensitive).
- `@` öneki → iptal etme, **boş JSON'a yönlendir** (YouTube'un reklam-API'leri için; oynatıcı takılmaz).
- `#` yorum. Boş satır yok sayılır. Bir kural listesi kilitlerse `#` ile pasifleştir.

## Ne keser / ne kesmez (dürüst sınırlar)
✅ YouTube pre/mid-roll (stub + ad-showing skip kombinasyonu), overlay/banner reklamlar, klasik tracker
   ağları (doubleclick, googlesyndication, adnxs, taboola…), banner dosyası imzaları.
⚠️ Twitch: yalnızca overlay/banner kesilir — Twitch'in **stream içine gömdüğü** reklam m3u8'in
   parçasıdır, hiçbir istek filtresi bunu sökemez (uBlock da sökemez; o ayrı tekniğe bakar).
❌ Tam EasyList motoru, cosmetic filterlist lisanı, scriptlet kütüphanesi yok — **kürasyonlu** liste.
❌ YouTube sınıfları/endpoint'leri değiştirirse rules.txt + CosmeticInjector.JS güncellenmeli
   (tek dosya, tek satır — bu zaten uBlock'un da çalışma şekli).
ℹ️ Yasal not: kendi sunucunda kendi oyuncuların kullanımı; YouTube ToS yorumu sana kalmış —
   alternatif olarak Piped zinciri raporda duruyor (o hiç kod istemez).

## Test checklist (staging)
1. WebDisplays ekranında `youtube.com/watch?v=...` aç → reklam spinner'ı yerine doğrudan içerik;
   reklam gelirse ≤1sn içinde atlanır (skipper JS).
2. F7 log'da `attached to MCEF` satırı + kural sayısı > 0.
3. `piped.video` ve bir wiki sayfası **hiç etkilenmemiş** olmalı (regresyon kontrolü).
4. MinePad'de de aynı filtre geçerli (aynı CefClient'i paylaşır — bonus).

## v0.2 — YT SUITE (SponsorBlock + Return YouTube Dislike + Enhancer portu)
- Endpoint/seçiciler DOĞRUDAN kaynak repolardan: `ajayyy/SponsorBlock` (`GET /api/skipSegments/<videoID>?categories=[..]` + `videoID` süzme — kendi kodundaki gibi), `Anarios/return-youtube-dislike` **resmî UserScript**'i (votes API + `like-button-view-model`), `YouTube-Enhancer/extension` (`setPlaybackQualityRange(q,q)`, `setVolume(0-100)`, `ytp-size-button` + `theater` attribue kontrolü).
- Mekanizma: Chrome eklentisi paketi GEREKMEZ — tek `executeJavaScript` payload'ı. (RYD zaten kendisi UserScript olarak dağıtılıyor; aynı teknik.)
- Ayar: `config/wd-adblock-lite/yt-suite.txt` → `sponsorblock`, `ryd`, `quality=4k|1440|1080|720|off`, `volume=0-100`, `speed=1.0`, `theater=false`, `sbCategories=sponsor,selfpromo,...`
- Dosyalar: `src/main/resources/ytsuite.js` + `YtSuite.java` + `YtSuiteCfg.java`; enjeksiyon `CosmeticInjector.onLoadEnd` üzerinden (SPA'da video değişimi 750ms'lik döngüyle takip).
- Kapsam dışı (bilinçli): RYD oy senkronu, SponsorBlock segment gönderme/oy UI'ı, Enhancer'ın >%100 WebAudio boost'u ve ayar menüleri — hepsi chrome.* API / UI altyapısı ister; ekranda 50 satır chat/oy UI'ı anlamsız.

## v0.2.1 — SPA-navigation fixi
Artik yalnizca sayfa yuklenisinde degil, ADRES DEGISIMINDE de enjekte edilir (google.com uzerinden YouTubea tiklaninca script atlanma derdi kapandi). Enjeksiyon idempotent (window guard) + 3sn spam kilidi.
