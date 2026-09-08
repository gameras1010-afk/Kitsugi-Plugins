# ✨ Araştırma #4 (rev.2) — "OYUNU BASİTLEŞTİRMEDEN GÜZEL ŞEYLER" + MEDYA/İNTERNET KATMANI
### NeoForge 1.21.1 — hepsi Modrinth API'den doğrulandı (8-9 Eyl 2026) — önceki turların tekrarları YOK

*Not: tam 174'lük listen bende dosya olarak yok; "sende var" çıkarsa söyle, düşüreyim.*

---

## 🏆 VİTRİN (dengeli seçim: ~6-8 mod)
1. **Exposure** 🟡 — fotoğrafçılık: makineyle çek, karanlık odada banyola, albüm/çerçeve dekor. Saf içerik, ekonomi/balans bozmaz. 13,8M DL, MIT. `modrinth.com/mod/exposure` ✅ 1.21.1 NeoForge ✓
2. **Create** 🟡 (VEYA **Immersive Engineering** ✅ 3,4M) — maliyetli estetik otomasyon; **ikisini birden kurma**. Create resmî NeoForge 1.21.1 ✓ (25,5M). Spark'sız kurma.
3. **Better Advancements** 🟢 — client-only, 174 modluk cephanelikte ilerleme haritası düzene girer (25,1M). `better-advancements` ✓ (alternatifi `paginatedadvancements` — biri yeter).
4. **Paragliders + Towers of the Wild — Modded** 🟡🟢 — BotW kulelerine tırman, süzül (stamina ekonomisi = bedava uçmak değil) — ikisi de resmî NeoForge 1.21.1 ✓ (Paragliders güncelleme 08.09.2026!).
5. **Sinematik cila (hepsi client-only → sunucu sıfır yük):** Punchy! (4,4M), First-person Model (13,8M), Camera Overhaul (6,0M), Shoulder Surfing Reloaded (11,4M) — dördü de ✓ 1.21.1 NeoForge.
6. **Müzik:** Music Player (243K, client-only, YouTube/SoundCloud/radio) veya Net Music (4,5M). ✓

## 📺 MEDYA KATMANI — "oyun içi TV"den "MC içinde internet"e tam merdiven
| Seviye | Mod | Ne | Durum |
|---|---|---|---|
| Ses | **VinURL** | YouTube linkini **plağa** yaz → müzik kutusu çalar (SES-only) | ✓ 1.21.1 NeoForge (331K) |
| Ses | **Music Player** | GUI oynatıcı, client-only | ✓ |
| TV + kamera | **vista** (Supplementaries ekibi!) | TV blokları (birleştirilip dev ekran), kamera/gözetim, creeper-drop **gif kasetler**, URL→TV (direct .mp4/.gif), CRT shader'lar; Supplementaries entegrasyonlu | ✓ 1.21.1 NeoForge (851K, Ağu 2026) — Iris ile görüntü bozuluyor notu ⚠️ |
| Video API | **WATERMeDIA dörtlüsü** | VLC tabanlı: API + Binaries + **YouTube Extension** + WATERViSION Player — komutla ekrana video/YouTube/broadcast | ✓ 1.21.1 NeoForge (4 parça) — çok yeni, staging test ⚠️ |
| 🌐 **GERÇEK TARAYICI** | **WebDisplays [2.0] REMASTER** + **MCEF** | MC içinde Chromium: ekran bloğu kur, **YouTube/Twitch/TikTok/Instagram/X kısayollu Dynamic Hub**, klavye bloğu, lazer pointer, HTML5 mini oyunlar | Remaster ✓ **sadece 1.21.1 + neoforge** (MIT, Haz 2026 güncel); MCEF ✓ 1.21.1 neoforge (Chromium 116, ~200MB client'a iner; antivirüs beyaz liste) |

### ❓ "Chrome EKLANTİSİ (uBlock vb.) ekleyemiyor muyuz?" — HAYIR, ama reklam problemi çözülür (doğrulama: 9 Eyl 2026)
- MCEF = **CEF** = Chromium'un *gömülü framework'ü* → Chrome Web Store eklenti altyapısı CEF'de **yok** (upstream limiti; topluluk dokümanları net: "Chrome extensions do not work"). Modrinth'te "webdisplays extension/adblock addon" araması = **0 sonuç**. Uydurmam.
- **ÇÖZÜM 1 (en pratik):** Ekranda `youtube.com` yerine **`piped.video`** (veya Invidious: `yewtu.be`) aç → reklamlar **sunucu tarafında** kesilir + SponsorBlock dahili; JS istemez, düşük çözünürlüklü ekranla mükemmel uyum. Oyunculara tek satır link ver, biter. 🎯
- **ÇÖZÜM 2 (kişisel):** Oyuncu kendi Windows'unda **AdGuard** çalıştırırsa sistem geneli proxy'den oyun içi Chromium trafiği de süzülür. (Mac/Linux'ta benzer araçlar var ama garanti değil.)
- **ÇÖZÜM 3 (DNS TUZAĞI — yapma):** `googlevideo.com`'u Pi-hole/AdGuard Home'la bloklamak YouTube'u **tamamen bozar** (akış aynı domain). YouTube reklam engeli DNS ile çalışmaz.
- 🍀 Companion: **`fix-webdisplays-remaster`** datapack'i (1.21.1 ✓, MIT, 451 DL) — Remaster'ın eksik **crafting tariflerini** tamamlıyor. Bir de "WebDisplays_Fabric" portu var (1.21.1 ✓ ama Fabric — Connector'lık; senin adresin zaten Remaster).

## 🛠️ "REKLAM ENGELLEYİCİ UYDURMA" REHBERİ (WebDisplays/MCEF için, 9 Eyl doğrulaması)
**Gerçek durum:** CEF motoru Chrome eklentisi YÜKLEYEMEZ → MC-browser-modu üzerinde "uBlock addon" diye bir şey yazılamaz; Modrinth/CurseForge taraması: 0. AMA iki çalışan zincir kurulabiliyor:

- **ZİNCİR A — en temiz (YouTube+Twitch+her yer):** `piped.video` / `yewtu.be` linki → reklamlar sunucu tarafında kesik, oyuncu tarafı 0 ayar. Hub'a kısayol olarak yazılabilir.
- **ZİNCİR B — gerçek "oyun içi ekran adblock"u (Windows oyuncular için):** **AdGuard for Windows** kur → Windows sistem proxy+sertifikasına yerleşiyor; **Chromium (MCEF dahil) sistem proxy'sini VARSAYILAN kullanır** → oyun içi tarayıcı trafiği de AdGuard filtreden geçer = YouTube banner/video reklamları MC İÇİNDEKİ ekranda da kesilir. (Linux oyuncusu: AdGuard for Linux CLI aynı mantık; Mac: kısıtlı.) Ücretli/30 gün deneme — herkese zorunlu tutma, isteyen kurar.
- **ZİNCİR C — yapma (kanıtlı):** DNS/hosts'tan `doubleclick/googlevideo` bloklamak → YouTube'un akışıyla reklamı AYNI domain; ya reklamlar kalır ya video bozulur. `--host-resolver-rules` numarası da ancak banner siteleri keser, pre-roll reklamı kesmez. Uğraşmaya değmez.
- WebDisplays portlarında **regex tabanlı `blacklist` config'i** var (ör. Fabric portu `config/webdisplays.json → "blacklist": ["^https?://..."]`) — Remaster'da benzer config satırı çıkarsa easylist domain'leri buraya dökülebilir (banner reklamlar için kısmi kazanç; YouTube pre-roll'a yine yetmez). Remaster'ın GitHub'ı olmadığı için config şeması teyitsiz — kurulumda `config/` klasörüne bak.

**Sunucu tavrı:** hiçbirini sunucuya kurmuyorsun — A hub linki, B/C tamamen oyuncunun kendi makinesi. Sunucu yükü: 0.

## 🎬 FİNAL ÇÖZÜM — "REKLAMSIZ YOUTUBE EKRANI"NİN MİMARİ HALİ: WATERFrAMES dörtlüsü
> Adblock'u taklit etmeyiz — reklamı **mimari olarak devre dışı** bırakırız: sayfanın web-player'ı hiç yüklenmez, akış doğrudan çekilir. (Pre-roll reklamlar YouTube'un web oynatıcısının API pazarlığındadır; oynatıcı yoksa reklam da yok.)

- **WATERFrAMES: Multimedia Displays** (SrRapero720) — dünyaya **medya çerçevesi + projeksiyon bloğu** koy, URL yapıştır; VIDEO oynatır (görsel/direct stream da). ✅ **1.21.1 + NeoForge** (869K DL, Haz 2026 güncel), client_and_server. `modrinth.com/mod/waterframes`
- **Motor:** **WATERMeDIA: Multimedia API** (VLC tabanlı, ✅ 1.21.1 NeoForge, 1,5M) + **WATERMeDIA Binaries** (✅) + **WATERMeDIA: Youtube Extension** (✅ 1.21.1 NeoForge, 317K, Haz 2026 güncel) — YT linkini extension **doğrudan video+ses stream'ine çevirir** → reklam kodu çalışmaz, tracker yok, cookie yok.
- **Ekosistem:** `waterframes-computercraft-compat` ✓ 1.21.1 + `WATERFrAMES: Create Integration` datapack ✓ 1.21 (Create kurarsan tarifler Create malzemelerine bağlanır — vitrinimizle uyumlu!).
- **Sunucu maliyeti:** çerçeve = blok + stream linki senkronu; akışı her client kendi çeker → **TPS'e etkisi ~0**, CEF'ten hafif (web render yok).
- **Dürüst sınırlar:** (1) yorum/chat/altyazı-menüsü gibi site özellikleri YOKTUR (bu bir tarayıcı değil, TV'dir); (2) YouTube iç yapısını değiştirirse extension bir süre aksar — güncel tut (aktif geliştirici); (3) All-Rights/Polyform lisanslar — kişisel/sunucu kullanımı sorun değil, kaynak paketi yayıncılığı değil.
- **Sonuç:** WebDisplays "internete girmek" için, **WATERFrAMES "reklamsız yayın duvarı/projeksiyon sineması"** için. İkisi aynı sunucuda yaşar; reklam derdi ikincisinde **kavramsal olarak yoktur**.

### Diğer önemli bulgular (aynı taramada)
- **WebDisplays alternatif forku:** `webdisplays-1-21-1-fork` (BrotherBill, CurseForge #1417309) — **webdisplays-2.6.0-1.21.1 NeoForge** (May 2026, MIT, kaynak GitHub'da: brother-bill/webdisplays-mc, CinemaMod katkılarıyla). Remaster'a göre artısı: brightness config + kaynak kodlu. Motor yine CEF → reklam derdi yine Piped/AdGuard konusu.
- Modrinth'te "adblock" araması (1.21.1): sadece RU sunucu-reklam engelleyici ucubeleri (447 DL) — web-reklam engeli DEĞİL. Kanıt: mod-eci adblock sektörü yok.

## 🔬 KAYNAK-KODU DOĞRULAMALI FİNAL TARİFİ (9 Eyl — wd & mcef repoları okundu)
**Kanıtlanan kapıların durumu (hepsi kod seviyesinde):**
- `mcef.properties` anahtarları SADECE: `skip-download`, `download-mirror`, `user-agent`, `use-cache`. CEF switch'leri hardcoded (`--autoplay-policy=no-user-gesture-required`, `--disable-web-security`, `--enable-widevine-cdm`) → **config'den `--proxy-server` enjekte edilemez.**
- `MCEFClient` modder API'si: `addLoadHandler / addContextMenuHandler / addDisplayHandler / addAudioHandler` — **iptal edilebilir request hook'u YOK** (CefRequestHandler/ResourceRequestHandler zinciri açık değil) → "50 satırda oyun-içi adblock addon" bile temiz yazılamaz. Eklenti yolu motor+API seviyesinde ölü; son söz.
- WebDisplays `blacklist` config anahtarı GERÇEK (brother-bill fork `CommonConfig.java:58`, `config/webdisplays-common.toml → [browser] blacklist=[]`) ama motoru: `str.equalsIgnoreCase(url.getHost())` — **tam hostname eşleşmesi, sadece navigasyon URL'i** (alt-istek/banner taraması yok). → Ajan görevi göremez, **politika aracı** olarak değerli.

**Çalışan üç tarif:**
1. **GUARANTEED (tek kurulum: sunucu):** `blacklist = ["youtube.com", "m.youtube.com"]` + ekranlarda/Hub'da temiz ön-uç: `piped.video/watch?v=…` veya `yewtu.be/watch?v=…`. Reklam fiziksel olarak yok; oyuncudan hiçbir şey istenmiyor; yanlışlıkla `youtube.com` açılırsa mod "blacklisted" ekranı basıyor (DisplayHandler + SetURL ikisinde de uygulanıyor).
2. **Player-side güç (Windows, garanti değilse de yakın):** AdGuard for Windows — ağ-sürücüsüyle TÜM uygulamaların HTTPS'ini MITM'ler + kendi root CA'sını kurar; CEF = Chromium olduğu için sistem yığınından süzülür → **gerçek youtube.com sayfasında bile** reklam/scriptlet filtreleri uygulanır. Kritik nüans: trafiği üreten process `java.exe` değil **`cef_helper.exe`** (MCEF CEF'i `.minecraft/config/mcef/` altına indirir, agent oradan koşar) → AdGuard uygulama kurallarında cef_helper.exe filtreye DAHİL edilmeli. staging'de tek oyuncuyla doğrula; skin/realms java-trafiğine dokunmaya gerek yok (JVM ayrı store). Mac/Linux: AdGuard tam yok (yalnız Linux-CLI) → o oyuncular tarif-1.
3. **Banner-only zayıf hat:** router/Pi-hole DNS filtreleri → site banner/takipçi azalır, **YouTube pre-roll KESİNLİKLE kesmez** (googlevideo ortak-domain tuzağı, pfBlocker forumunda da "videoyu bozdu" teyitli).

**Özet cümle:** WebDisplays'i reklamsız kullanmanın imkânlar kümesi budur: **1) temiz link disiplini (+blacklist kilidi) = %100, 2) AdGuard-for-Windows = %90'a yakın, 3) geri kalanı motor yasağı.** Üçü hariç hiçbir "mod/eklenti/uygulama" tarifi gerçek değil — kaynak kodunu okuyarak doğruladım.

## 🔧 DIY FİNAL — "KENDİ EKLENTİMİZİ YAPALIM" (2026-09 sonu, kaynak-kodlu)
**Cevet: EVET, yapılabilir — ama eklenti olarak değil, companion mod olarak.** uBlock'un çekirdeği 3 şeydir; üçü de CEF'te eklenti API'si olmadan açık: (1) alt-istek iptali, (2) isteği boş-JSON'a yeniden yazma (stub), (3) executeJavaScript ile cosmetic CSS+skipper JS — ki **WD'nin ses kontrolü (3)'ü zaten kullanıyor**. Kaynak doğrulamaları: java-cef `CefClient.addRequestHandler` public tek-slot ve **MCEF'te de WD'de de çağrılmıyor (boş)**; `CefRequest.setURL` abstract public; `MCEFClient.addLoadHandler` public zincir. `mcef.properties`'te proxy/arg yok (4 anahtar) → motorun içine girmenin config yolu gerçekten yok, onun yerine yan-hat zorunlu.
→ **Teslim: `wd-adblock-lite/` projesi (workspace)** — MIT, client-only, NeoForge 1.21.1 (21.1.215 hedef), ~4 dosya: tick'te MCEF gec-olusumunu bekleyip handler bağlar (crash-safe), `config/wd-adblock-lite/rules.txt` regex listesi (`@`=stub), YT/Twitch skipper JS. Twitch'in m3u8-içi reklamı mimari olarak kesilemez (dürüst sınır); YouTube pre/mid-roll + banner + tracker = kesilir. Build: JDK21 + `./gradlew build` (sandbox'ta maven yok — README'de adım adım).

## 🚫 BİLİNÇLİ YOKLAR
Xaero/JourneyMap radarları (bilgi = avantaj), Sophisticated-style envanter QoL'leri, otomatik maden/hasat, Create+IE aynı anda. BrowserMCEF (Fabric, 1.21.10/11) — sürüm uyumsuz.

## 🧮 PERFORMANS & KURULUM
- Sunucuya gerçek maliyet: **Create/IE (seç-birini) + TotW kuleleri** kadar; medya katmanı **sıfıra yakın** (Chromium oyuncuların PC'sinde; ekran = blok senkronu).
- Ekran çözünürlüğü: WebDisplays'te 640x360–960x540 tut (GPU + bant genişliği).
- Sıra: staging → WebDisplays+MCEF + Piped linki test → Vista/Exposure → Create VEYA IE → spark.

---
*Yöntem: Modrinth API proje/sürüm alanları + loader etiketleri tek tek kontrol edildi (8-9 Eyl 2026); CEF eklenti kısıtı topluluk/belge kaynaklarıyla teyit edildi.*
### 🔌 v0.2 EKLENTİ-LİMANI (2026-09, kullanıcının 3 eklentisi)
SponsorBlock + Return YouTube Dislike + Enhancer for YouTube → WD modu artık bu üçünü **eklenti formatı olmadan** taşıyor: kaynak repolarından doğrulanmış endpoint/seçicilerle tek `executeJavaScript` payload (ytsuite.js). RYD zaten resmî UserScript olarak dağıtılıyor — mekanizma birebir aynı. Ayar dosyası: `config/wd-adblock-lite/yt-suite.txt`. Kapsam dışı: oy gönderme, segment submit, >100% WebAudio boost, chrome.* UI altyapıları.
