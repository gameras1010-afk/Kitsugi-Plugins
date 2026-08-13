# Simple Voice Chat — Gerçek Teşhis

> Bu doküman, daha önce verilen "klasör kilidi + timeout 30 saniye" teşhisini
> **düzeltiyor.** O teşhisin bir kısmı doğru, bir kısmı **yanlış**.

---

## ⚠️ ÖNEMLİ DÜZELTME — MTU teorisinin zayıf noktası

Aşağıdaki Bölüm 3'te MTU çakışmasını "en olası sebep" diye sundum.
Sonradan Opus spesifikasyonunu (RFC 6716) kontrol ettim ve **teorinin
sandığım kadar güçlü olmadığını gördüm.** Dürüst olmak için burada
düzeltiyorum.

### Sorun ne

`mtu_size=1275` sayısı tesadüf değil. RFC 6716:

> *"The maximum representable length is 255\*4+255=**1275 bytes**.
> For 20 ms frames, this represents a bitrate of **510 kbit/s**, which is
> approximately the highest useful rate for lossily compressed
> **fullband stereo music**."*

Yani 1275 bir **tavan değeri** — Opus'un teorik olarak üretebileceği
en büyük paket. Gerçek konuşma paketleri buna hiç yaklaşmıyor:

| Bitrate | 20 ms frame boyutu |
|---|---|
| 24 kbps (VOIP tipik) | **~60 bayt** |
| 64 kbps (yüksek kalite) | **~160 bayt** |
| 510 kbps (stereo müzik, teorik tavan) | 1275 bayt |

SVC `codec=VOIP` kullanıyor ve konuşma için tipik paket **100-250 bayt**
civarında. Üstüne SVC'nin kendi başlığı ve şifreleme yükü binse bile
**1280'in çok altında.**

### Bu ne demek

Eğer paketler zaten ~200 baytsa, `mtu_size`'ı 1275'ten 1000'e çekmek
**hiçbir şeyi değiştirmez** — çünkü o tavana zaten hiç değilmiyordu.

`mtu_size=1000` **zararsız** (bırakabilirsin, ses kalitesini düşürmez).
Ama "kesin tanı" demek doğru değil. Ben öyle sunmuştum, hatalıydı.

### MTU teorisi hangi durumda hâlâ geçerli

- Biri müzik botu / `AUDIO` codec / yüksek bitrate kullanıyorsa
- Bir ses eklentisi (addon) büyük paket gönderiyorsa
- Tailscale **DERP relay** üzerinden gidiyorsa (efektif MTU daha da düşer)

DERP kontrolü — bu önemli:

```bash
tailscale status
```

Satırlarda `direct` yerine `relay "xxx"` görüyorsan trafik Tailscale'in
relay sunucularından dolaşıyor. **Bu gerçek bir gecikme ve paket kaybı
kaynağı** ve ses için MTU'dan çok daha ciddi bir sorun.

```bash
tailscale ping DIGER_MAKINE
```
`via DERP` diyorsa direkt bağlantı kurulamamış.

**Çare:** Tailscale'in UDP 41641 portunu sunucuda dışarı aç —
resmî dokümana göre bu direkt bağlantı ihtimalini ciddi artırıyor:

```bash
sudo ufw allow 41641/udp
```

### Şu an ne yapmalı

Sunucu açıldığında **önce test et.**

- **Ses düzeldiyse:** sebep muhtemelen `login_timeout` revert'i veya
  `voice_host` değişikliğiydi — MTU değil.
- **Düzelmediyse:** MTU'yu suçlama, aşağıdaki log adımına geç.

Her hâlükârda log'a bak:

```bash
grep -iE "voicechat|Dropping voice" logs/latest.log | tail -50
```

---

---

## 1. "Timeout'u 30 saniyeye çektik" — BU MUHTEMELEN HATALI

Simple Voice Chat'in server config'inde **"timeout" diye bir ayar yok.**
Sadece şu ikisi var, ve ikisi de sandığın şey değil:

### `login_timeout=10000`

Resmî dokümantasyondaki açıklaması:

> *"The amount of time the server should wait to check if the player has
> the mod installed (in milliseconds).*
> ***Only active when `force_voice_chat` is set to true***"

**`force_voice_chat` varsayılan olarak `false`.**

Yani sende `force_voice_chat=false` ise — ki varsayılan bu — bu değeri
10 saniyeden 30 saniyeye çekmek **kesinlikle hiçbir şey yapmaz.**
Kod o satırı hiç okumuyor bile. Bu ayar sadece "mod yüklü olmayan
oyuncuyu at" özelliği açıkken, o kontrolün ne kadar bekleyeceğini
belirliyor. Ses bağlantısının kopmasıyla **hiçbir ilgisi yok.**

### `keep_alive=1000`

Resmî açıklama:

> *"The frequency at which keep-alive packets are sent (in milliseconds).*
> ***Setting this to a higher value may result in timeouts***"

**Eğer 30 saniyeye çektiğin şey buysa, durumu düzeltmedin — bozdun.**

Bu ayar "ne kadar bekle" değil, "ne sıklıkla hayattayım paketi gönder"
demek. 1000 ms = saniyede bir. Bunu 30000 yaparsan sunucu 30 saniyede
bir haber veriyor, client 30 saniye sessizlik görüp bağlantıyı ölü
sayıyor. Dokümantasyon bunu **açıkça** uyarıyor.

### Ne yapman lazım

`config/voicechat/voicechat-server.properties` dosyasını aç ve bak:

```properties
keep_alive=1000          # ← 1000'de kalmalı. Değiştirdiysen GERİ AL.
login_timeout=10000      # ← force_voice_chat=false ise anlamsız, dokunma
force_voice_chat=false
```

---

## 2. "Klasör root'tu, config oluşmamıştı" — DOĞRU AMA ETKİSİ ABARTILMIŞ

Klasörün `root` sahipliğinde olması **gerçek bir sorun** ve düzeltmen iyi.
Ama şu kısım yanlış:

> *"Mod körlemeye, hiçbir ayar olmadan çalışıyordu."*

Config dosyası yoksa mod **varsayılan değerlerle** çalışır. Varsayılanlar
da gayet makul: `port=24454`, `keep_alive=1000`, `bind_address=` (boş),
`mtu_size=1024`. İnsanların %90'ı bu dosyaya hiç dokunmadan sorunsuz
kullanıyor.

Yani "config yok" tek başına ses kopmasını açıklamıyor.
**Ama şunu açıklıyor:** senin `port` veya `bind_address` ayarların
kaydedilmiyordu. Eğer daha önce port değiştirdiysen o değişiklik
diske yazılmamıştı. Düzeltmen bu yüzden doğru bir hamle.

**Doğrulama:** klasör iznini düzelttikten sonra dosya gerçekten oluştu mu?

```bash
ls -la config/voicechat/
cat config/voicechat/voicechat-server.properties
```

Dosya orada değilse iş bitmemiş demektir. Sahibi sunucuyu çalıştıran
kullanıcı olmalı:

```bash
sudo chown -R minecraft:minecraft config/voicechat/
```

---

## 3. Tailscale MTU — muhtemel ama kesin değil

> ⚠️ Yukarıdaki düzeltmeyi oku. Bu bölümdeki mantık **teorik olarak
> doğru** ama pratikte konuşma paketleri 1275'e hiç ulaşmadığı için
> tek başına yeterli açıklama olmayabilir. `mtu_size=1000` zararsız,
> bırakabilirsin — ama "kesin tanı" değil.

### Rakamlar

| Katman | Değer |
|---|---|
| Normal ethernet MTU | 1500 bayt |
| **Tailscale MTU** | **1280 bayt** (sabit) |
| IP + UDP başlığı | 28 bayt |
| Tailscale içinde kalan gerçek alan | **~1252 bayt** |

Tailscale bunu tesadüfen seçmiyor — kaynak koddaki yorum:

> *"1280 is the smallest MTU allowed for IPv6, which is a sensible
> 'probably works everywhere' setting until we develop proper PMTU
> discovery."*

### Çakışma

Simple Voice Chat'in `mtu_size` varsayılanı sürüme göre **1024 veya 1275**.

**1275 ise:** 1275 + 28 = **1303 bayt** → Tailscale'in 1280'ine sığmıyor
→ paket parçalanıyor veya **sessizce düşüyor.**

Tailscale'in kendi dokümanı bu davranışı doğruluyor:

> *"If there are other interfaces which might send a packet larger than
> this, those packets **might get dropped silently**."*

Ve Simple Voice Chat'in `mtu_size` açıklaması zaten çareyi söylüyor:

> *"The maximum size that audio packets are allowed to have (in bytes).
> **Lower this if audio packets do not arrive reliably.**"*

### Yapılacak

```properties
mtu_size=1000
```

Bu 1000 + 28 = 1028 bayt → Tailscale'in 1280'ine rahat sığıyor,
üstüne pay bile kalıyor. Ses kalitesi düşmez, sadece Opus paketleri
biraz daha küçük parçalara bölünür.

**Bu tek satır senin sorununu çözebilir.** Önce bunu dene.

### MTU'yu doğrula

```bash
ip link show tailscale0        # MTU: 1280 görmelisin
```

---

## 4. VPN uyarısı — resmî dokümanda yazıyor

Simple Voice Chat'in kendi troubleshooting sayfası, bağlanamama
sebeplerini sayarken şunu diyor:

> *"This issue can also occur **if you are using a VPN**."*

Tailscale bir VPN (WireGuard tabanlı mesh). Yani modun geliştiricisi
bu senaryoyu bilinen problemli durum olarak listelemiş.

### `voice_host` tuzağı

Tailscale kullanıyorsan bu ayara dikkat:

```properties
voice_host=
```

Sunucu, client'a "ses için şu adrese bağlan" diye bir adres söylüyor.
Boşsa Minecraft bağlantısının geldiği adresi kullanıyor — Tailscale'de
genelde doğrusu bu.

**Ama** buraya yanlışlıkla public IP veya `localhost` yazıldıysa,
client Tailscale ağının dışına bağlanmaya çalışır ve zaman aşımına uğrar.
Dokümantasyonun kendi uyarısı: *"Do NOT change this value unless you
know what it does."*

Boş olduğundan emin ol. Sorun devam ederse sunucunun Tailscale IP'sini
(`100.x.y.z`) elle yazmayı dene.

### `bind_address`

```properties
bind_address=
```

Boş bırak. Boşken tüm arayüzlere bağlanıyor — Tailscale arayüzü dahil.
Buraya spesifik bir IP yazarsan diğer arayüzden gelen bağlantılar ölür.

---

## 5. "Can't keep up" — evet gerçek, ama ses üzerindeki etkisi anlatıldığı gibi değil

```
Can't keep up! Running 2009ms or 40 ticks behind
```

Bu 40 tick geride kalmış demek. Gerçek bir performans sorunu ve
ayrıca ele alınmalı. **Ama** "sunucu kasarsa ses de kasar" ifadesi
mekanizmayı yanlış anlatıyor.

Simple Voice Chat sesi **ana sunucu thread'inde işlemiyor.** Kendi
UDP soketi ve kendi thread'i var (`VoiceChatPacketProcessingThread`).
Bu yüzden TPS 20'den 8'e düşse bile ses akmaya devam eder.

TPS düşüşünün sese **gerçek** etkisi iki tane:

1. **Konum güncellemeleri gecikir.** Kimin nerede olduğu ana thread'den
   geliyor. TPS düşünce mesafeye bağlı ses (proximity) yanlış hesaplanır —
   yanındaki adamı uzaktan duyarsın.
2. **CPU açlığı.** Tüm çekirdekler doluysa ses thread'i de sıra bekler.

Ve sunucu gerçekten boğulduğunda mod bunu **açıkça söylüyor**:

```
[voicechat] Dropping voice chat packets! Your Server might be overloaded!
[voicechat] Packet queue has 624 packets
```

**Log'unda bu satır var mı?** Yoksa TPS düşüşü senin ses sorununun
sebebi değil. Varsa sebep o.

```bash
grep -i "Dropping voice chat packets" logs/latest.log
grep -i "voicechat" logs/latest.log | tail -50
```

---

## 6. Sıralı kontrol listesi

Yukarıdan aşağı, en olasıdan:

### Adım 1 — keep_alive'ı geri al (30 saniye)

```bash
grep keep_alive config/voicechat/voicechat-server.properties
```
1000 değilse 1000 yap. Bu değiştirildiyse sorunun sebebi bu.

### Adım 2 — mtu_size düşür (en olası çözüm)

```properties
mtu_size=1000
```
Sunucuyu yeniden başlat, test et.

### Adım 3 — Log'a bak

```bash
grep -iE "voicechat|Dropping voice" logs/latest.log | tail -50
```

Ne göreceğin ve ne anlama geldiği:

| Log satırı | Anlamı |
|---|---|
| `Voice chat server started at ...` | Sunucu tarafı sağlam, sorun ağda |
| `Dropping voice chat packets!` | Sunucu aşırı yüklü, TPS'i düzelt |
| `Operation not permitted (sendto failed)` | Firewall/işletim sistemi UDP'yi engelliyor |
| `Failed to bind` | `bind_address` yanlış |
| `Address already in use` | Port çakışması (query portuna dikkat) |
| Hiçbir voicechat satırı yok | Mod yüklenmemiş |

### Adım 4 — UDP portunu test et (TCP değil, UDP)

Client makineden:
```bash
nc -vzu SUNUCU_TAILSCALE_IP 24454
```

Tailscale üzerinden bağlanılıyorsa `ufw` da Tailscale arayüzüne izin vermeli:
```bash
sudo ufw allow in on tailscale0
sudo ufw allow 24454/udp
```

### Adım 5 — `query.port` çakışması

`server.properties` içinde:
```properties
enable-query=true
query.port=25565
```

Query UDP kullanıyor. Ses portuyla çakışırsa mod bağlanamaz.
Resmî dokümantasyon bu yüzden ses portunu Minecraft portuyla
aynı yapmayı **kesinlikle** önermiyor:

> *"it is strongly recommended NOT to use the same port number
> because UDP on it is also used by default for the server query.
> **Doing so may crash the server!**"*

### Adım 6 — Sürüm eşleşmesi

Simple Voice Chat loader ve MC sürümü başına ayrı jar dağıtıyor.
Yanlış build **sessizce** başarısız oluyor — hata vermiyor, sadece
çalışmıyor. Sunucudaki ve client'taki jar sürümü aynı mı, ve ikisi de
1.21.1 NeoForge build'i mi, kontrol et.

---

## 7. Config referansı (doğru değerler)

Dosya: `config/voicechat/voicechat-server.properties`
(Forge/NeoForge + SVC 2.4.0 üstü için bu yol. Eski sürümlerde `.toml` idi.)

```properties
port=24454              # Minecraft portuyla AYNI OLMASIN
bind_address=           # Boş bırak
mtu_size=1000           # ← Tailscale için düşürüldü (varsayılan 1024/1275)
keep_alive=1000         # ← DEĞİŞTİRME. Yükseltmek timeout YAPAR.
voice_host=             # Boş. Sorun sürerse Tailscale IP'si dene.
codec=VOIP              # Konuşma için doğrusu bu
max_voice_distance=48.0
force_voice_chat=false
login_timeout=10000     # force_voice_chat=false iken ETKİSİZ
allow_pings=true
```

---

## Özet — önceki teşhisin karnesi

| İddia | Durum |
|---|---|
| Klasör root'tu, config oluşmamıştı | ✅ Doğru, düzeltilmesi iyi |
| "Mod ayarsız, körlemesine çalışıyordu" | ⚠️ Abartı — config yoksa varsayılanlar geçerli ve makul |
| "Timeout 10 sn'ydi, 30'a çektik" | ❌ **Yanlış.** `login_timeout` sadece `force_voice_chat=true` iken çalışır. `keep_alive`'ı yükselttiysen **timeout'a sebep oldun** |
| "Can't keep up sesi etkiliyor" | ⚠️ Kısmen — ses ayrı thread'de. Etkisi sadece konum gecikmesi + CPU açlığı. `Dropping voice chat packets` log'u yoksa sebep bu değil |
| **Tailscale MTU 1280 vs mtu_size** | ⚠️ Bakılmamıştı, ama tek başına yeterli açıklama değil — konuşma paketleri zaten ~200 bayt. Bkz. baştaki düzeltme |
| **`voice_host` elle IP yazılmıştı** | ✅ **Bu gerçek bir hataydı.** Boşaltılması muhtemelen asıl düzeltme |
| **Tailscale DERP relay** | ❓ Hâlâ kontrol edilmedi — `tailscale status` çıktısına bak |

### En olası sebep sıralaması (güncel)

1. **`voice_host=100.70.34.111` sabitlenmişti** → boşaltıldı ✅
   Sunucu her client'a "ses için şu IP'ye bağlan" diyordu. Tailscale
   IP'si olsa bile o adrese ulaşamayan biri varsa (farklı tailnet
   yolu, DERP üzerinden gelen, ya da IP değişmişse) ses kurulmuyordu.
2. **Klasör izni** → config yazılamıyordu, değişiklikler kaydolmuyordu ✅
3. **Tailscale DERP relay** → henüz kontrol edilmedi
4. **MTU** → zararsız değişiklik, düşük ihtimal

**Test et, sonra log'u at.**

---
---

# EK BÖLÜM — "Bir süre sonra kopuyor" (Tailscale + SVC)

> Bu bölüm, yukarıdaki teşhisten **sonra** eklendi. Yeni bilgi:
> ses **hiç bağlanmıyor değil** — **bağlanıyor, bir süre çalışıyor, sonra kopuyor**.
> Bu tamamen farklı bir arıza sınıfı ve yukarıdaki `voice_host` teşhisi
> bunu **açıklamıyor**. `voice_host` yanlışsa ses **baştan** kurulmaz.

## E0. Semptomun kendisi bir kanıt

Kullanıcının tarifi: **Minecraft bağlantısı ayakta kalıyor, sadece ses düşüyor.**

Bu tesadüf değil, protokol farkından geliyor:

| Katman | Protokol | Kopunca ne olur |
|---|---|---|
| Minecraft oyun bağlantısı | **TCP** 25565 | Gecikmeyi yutar, paket kaybını tekrar gönderir. 30 sn'ye kadar donar ama **düşmez** |
| Simple Voice Chat sesi | **UDP** 24454 | Gecikme/kayıp = paket çöpe. `keep_alive` cevapsız kalınca **anında "disconnected"** |

Kaynak (SVC resmî wiki, `port` alanı):
*"Audio packets are always transmitted via the **UDP** protocol on the port
number specified here, **independently of other networking used for the game server**."*
— https://modrepo.de/minecraft/voicechat/wiki/server_config

**Çıkarım:** Aradaki yolda **UDP'ye özel** bir şey bozuluyor, genel bir
"internet koptu" durumu yok. Genel kopma olsaydı MC de düşerdi.
Bu, şüpheliyi doğrudan **Tailscale'in taşıma katmanına** indiriyor.

---

## E1. ASIL MEKANİZMA — Tailscale direct → DERP düşüşü

Tailscale iki farklı şekilde veri taşır:

| Yol | Nasıl çalışır | Ses için sonuç |
|---|---|---|
| **direct** (peer-to-peer) | WireGuard, **UDP**, kaynak port 41641. NAT hole-punching ile kurulur | ✅ Ses sorunsuz |
| **DERP** (relay) | WireGuard paketleri **TCP/443 TLS içine sarılır**, Tailscale'in sunucusundan geçer | ❌ **Ses ölür** |

Tailscale resmî dokümanı, tam olarak senin semptomunu tarif ediyor:

> *"it might take a long time to establish a direct connection, **or the devices
> might establish a direct connection and then revert to a relayed one**"*
> — Tailscale Docs, "Poor performance in a tailnet"

### Neden DERP'e düşünce ses ölüyor da MC yaşıyor?

DERP, UDP olan WireGuard trafiğini **TCP'nin içine** koyar
(kaynak: r/Tailscale — *"If UDP is blocked, Tailscale tunnels encrypted
WireGuard traffic over TCP"*). Bu **TCP head-of-line blocking** demektir:
tek bir paket düşerse, arkasındaki **bütün** paketler o paket yeniden
gelene kadar bekler.

Yani ses paketlerin sırası şöyle olur:
```
[ses][ses][KAYIP][ses][ses][ses]   ← TCP hepsini bekletir
                 ↓
        200 ms → 800 ms → 2 sn gecikme birikir
                 ↓
   SVC keep_alive (1000 ms) cevapsız kalır → "Voice chat disconnected"
```
MC ise zaten TCP ve gecikmeye toleranslı — sadece biraz "lag" hissedersin, düşmezsin.

**Bu, gözlemlenen semptomu tam olarak açıklayan tek mekanizma.**

---

## E2. DERP'e düşüşün 4 somut sebebi (hepsi kaynaklı)

### A) Windows UDP soket kilitlenmesi — ⭐ EN GÜÇLÜ ADAY

Tailscale'de **uzun ömürlü, bilinen bir Windows hatası** var:
boşta kalan UDP soketleri kilitleniyor ve **tüm direct UDP trafiğini
öldürüyor** — servis yeniden başlatılana kadar.

> *"Idle UDP sockets can timeout and stall — **blocking all UDP traffic**.
> Engineering was able to track down those `ReceiveIPv4` errors to an upstream
> Go bug in how UDP sockets are handled by default on Windows systems...
> This socket reset behavior... **prevented the node from receiving any direct
> UDP traffic from peers** [until] the Tailscale service was restarted."*
> — r/Tailscale, Tailscale mühendisliğinden alıntı
> Düzeltme PR'ı: `wgengine/magicsock: disable SIO_UDP_NETRESET on Windows` (#12927), **v1.72.0**'da yayınlandı

**Neden bu senin vakana birebir uyuyor:**
- Arkadaşların **Windows** kullanıyor ✅
- "Bir süre sonra" kopuyor (soket boşta kalınca kilitleniyor) ✅
- **Sadece UDP** ölüyor, TCP (Minecraft) yaşıyor ✅
- Tailscale'i kapat-aç düzeltiyor ✅

### B) Ağ olayı sonrası DERP'te takılıp kalma (self-heal yok)

Wi-Fi düşüp kalkması, mobil↔Wi-Fi geçişi veya ISP'nin IP yenilemesi
sonrası client DERP'e düşüyor ve **kendiliğinden direct'e geri dönmüyor**:

> *"There are some conditions under which a Tailscale client will not correctly
> identify that a connection to its home DERP has been lost. Failing to identify
> this state results in **loss of connectivity with peers**..."*
> — tailscale/tailscale **issue #15776**

> *"There are some cases where after switching to another DERP server, tailscale
> clients keep connecting to the old DERP server, and **they can't establish new
> connections**... **things do not self-heal**."*
> — tailscale/tailscale **issue #8568**

### C) Symmetric (hard) NAT — direct hiç sağlam kurulamıyor

Bazı modemler/CGNAT'lar her hedef için farklı dış port veriyor;
hole-punching baştan imkânsız oluyor, bağlantı DERP'te kalıyor.

Teşhisi tek satır: `tailscale netcheck` çıktısında
**`MappingVariesByDestIP: true`** → symmetric NAT.
> *"Look for the MappingVariesByDestIP field: **if true, you have symmetric NAT,
> and hole punching will likely fail**."* — Tailscale Blog, "Peer Relays"

### D) Aynı ağda birden fazla Tailscale cihazı = port çakışması

> *"If so, **only one can use port 41641 at a time**, every other gonna switch to
> another random port and could be blocked by the firewall again"*
> — r/Tailscale (Tailscale kurucusu bradfitz'in de katıldığı başlık)

Sunucu PC + senin PC'n aynı evdeyse, biri 41641'i kapar, diğeri rastgele
porta düşer ve DERP'e gider.

---

## E3. ÖNCE BUNU YAP — ayırt edici tek test

Ses koptuğu **anda**, oyunu kapatmadan, kopan kişinin PC'sinde:

```
tailscale ping <sunucu-tailscale-adı>
```

| Çıktı | Anlamı | Yapılacak |
|---|---|---|
| `pong ... via 192.168.x.x:41641` veya bir IP:port | **direct** — yol sağlam | Sebep Tailscale değil → E6'ya git |
| `pong ... via DERP(fra)` | **relay'e düşmüş** | ✅ **Teşhis doğrulandı** → E4'ü uygula |
| `direct connection not established` | Hiç direct kuramıyor | Symmetric NAT → E4-3 ve E5 |

**İkinci ayırt edici test:** Ses koptuğunda **Minecraft'ı değil, Tailscale'i**
yeniden başlat (`sağ tık → Exit` → tekrar aç). Ses geri geliyorsa
sebep **kesin olarak Tailscale**, SVC değil.

Destekleyici komutlar:
```bash
tailscale status          # peer satırında "direct" mi "relay <şehir>" mi
tailscale netcheck        # MappingVariesByDestIP, UDP: true/false, DERP gecikmeleri
```

---

## E4. KALICI ÇÖZÜM (palyatif değil, sırayla)

### 1. Tailscale'i HER cihazda güncelle — en yüksek fayda/emek oranı

Windows UDP soket hatası **v1.72.0**'da düzeltildi. Ayrıca:

| Sürüm | Düzeltme (resmî changelog) |
|---|---|
| **v1.72.0** | Windows `SIO_UDP_NETRESET` UDP soket kilitlenmesi (PR #12927) |
| **v1.76.0** | *"Clients lacking UDP connectivity no longer skip performing fallback latency measurements with DERP servers."* |
| **v1.62.0** | *"DERP server region no longer changes if connectivity to the new DERP region is degraded."* |
| **v1.40.0** | *"Improvements... to reduce the likelihood of a **spurious loss of direct connections**"* (#7877) |

Sürüm kontrolü: `tailscale version` — **1.72'nin altındaysa sebep büyük
ihtimalle budur.** Sunucu dahil herkes güncellenmeli; tek eski client
kendi bağlantısını bozar.

### 2. Sunucu tarafında UDP 41641'i sabitle ve aç

Tek tarafın portu açık olması genelde yeterli — ve o taraf **sunucu** olmalı:

> *"It's good to have it open where you can because sometimes you have a really
> hard NAT and **having someone on the other side with the port opened does help
> a lot**... I can guarantee you that **having open ports in at least one side of
> the connection can usually guarantee a connection**"* — r/Tailscale

Sunucuda (Linux):
```bash
sudo ufw allow 41641/udp
sudo ufw reload
```
Modemde: **41641/UDP → sunucu PC'nin yerel IP'si** yönlendirmesi.
Alternatif olarak modemde **NAT-PMP veya UPnP**'yi aç — Tailscale deliği
kendisi açar (resmî doküman pfSense/OPNsense için bunu öneriyor).

**Dikkat (E2-D):** Evde birden fazla Tailscale cihazı varsa 41641'i
**sadece sunucuya** yönlendir; diğerleri rastgele porta düşsün.

### 3. Doğrulama: endpoint gerçekten ilan ediliyor mu

https://login.tailscale.com/admin/machines → sunucu makinesine tıkla.
Endpoint listesinde **`<WAN_IP>:41641`** görünmüyorsa yönlendirme
çalışmıyor demektir (bkz. tailscale/tailscale issue #14494).

### 4. Symmetric NAT çıktıysa: Peer Relay

`MappingVariesByDestIP: true` ise port açmak **çözmez** — hole-punching
zaten imkânsız. Bu durumda DERP'e mahkûm olmak yerine **kendi relay'ini**
kur. Tailscale'in bağlanma sırası:

> *"Direct connection (preferred) → **peer relay connection** (dedicated capacity)
> → DERP relayed connection (shared infrastructure)"* — Tailscale Docs

Kendi peer relay'in, paylaşımlı DERP'ten kat kat düşük gecikme verir
(Tailscale'in kendi blog örneğinde **12.5×** hızlanma).
Kurulum: iyi bağlantılı bir node'da `--relay-server-port` ile aç.

### 5. Router özel ayarları (marka bazlı, resmî tablo)

| Firewall / Router | Tailscale davranışı | Çözüm |
|---|---|---|
| **UniFi Gateway** | DERP'e düşüyor | **"Allow peer-to-peer traffic"** aç / *Threat categories → **P2P** işaretini kaldır* |
| **pfSense / OPNsense** | DERP'e düşüyor | **NAT-PMP** aç veya statik NAT port mapping |
| **Fortinet** | DERP'e düşüyor | Portu rastgeleleştir; SSL inspection'ı kapat |
| **Cisco** | DERP'e düşüyor | Firewall portu aç |
| **Sophos / Check Point** | Direct çalışıyor | — |

Kaynak: https://tailscale.com/docs/integrations/firewalls

---

## E5. `mtu_size` — ÖNEMLİ SAYISAL DÜZELTME

Yukarıdaki bölümde MTU teorisini "zayıf" diye geri çekmiştim. **Bu hâlâ
büyük ölçüde doğru** (konuşma paketleri ~200 bayt), ama resmî wiki'den
gelen yeni bir sayı var ve matematiği paylaşmak gerekiyor:

**SVC'nin güncel varsayılanı `mtu_size=1275`** (eski sürümlerde 1024 idi).
Kaynak: https://modrepo.de/minecraft/voicechat/wiki/server_config

**Tailscale'in MTU'su sabit 1280'dir** ve değiştirilemez:
> *"Tailscale uses a maximum transmission unit (MTU) of 1280. If there are other
> interfaces which might send a packet larger than this, **those packets might get
> dropped silently**."* — r/Tailscale, Tailscale docs alıntısı
> *"Tailscale **always** sets its MTU to 1280."* — tailscale/tailscale issue #16820

Hesap:
```
1275 (SVC yükü) + 8 (UDP başlığı) + 20 (IP başlığı) = 1303 bayt
1303 > 1280  →  Tailscale tünelinden geçemez, SESSİZCE DÜŞER
```

**Dürüst değerlendirme:** Normal konuşmada Opus/VOIP paketleri bu boyuta
**çıkmaz**, o yüzden bu **ana sebep değil**. Ama sınırın **28 bayt
üstünde** olması bedava bir risk. Bir satırlık sigorta:

```properties
mtu_size=1000
```

Wiki uyarısı: *"Setting this to lower values might cause issues"* — bu yüzden
1000'in altına inme. 1000 hem 1280 sınırının çok altında hem de sorun
çıkarmayacak kadar yüksek.

---

## E6. `tailscale ping` "direct" diyorsa (Tailscale suçsuzsa)

Bu durumda sebep SVC/sunucu tarafında. Sırayla:

1. **Sürüm eşleşmesi** — client ve sunucudaki SVC sürümü **birebir** aynı olmalı.
   Uyuşmazlık **sessizce** başarısız olur, hata vermez. Herkesin
   `voicechat-neoforge-1.21.1-<X>.jar` sürümü aynı mı, tek tek doğrula.

2. **Sunucu log'unda ses ile ilgili ne var:**
   ```bash
   grep -iE "voicechat|Dropping voice|keep.?alive|timed out" logs/latest.log
   ```
   `Dropping voice chat packets` satırı **varsa** → sunucu CPU açlığı çekiyor,
   SVC thread'i zamanında paket gönderemiyor. O zaman konu ağ değil, TPS.

3. **UDP erişim testi** (oyuncunun PC'sinden, ses çalışırken ve koptuktan sonra):
   ```
   nc -vzu <sunucu-tailscale-ip> 24454
   ```

4. **`bind_address` boş mu** — Tailscale arayüzü ayrı bir IP verir.
   Alan doluysa SVC sadece o arayüzü dinler ve Tailscale'den gelen
   paketleri **hiç görmez**. Boş bırak (= tüm arayüzler).

---

## E7. Bu bölümün güven karnesi

Kullanıcının kuralı: emin olmadığım şeyi emin gibi yazmayacağım.

| İddia | Güven | Dayanak |
|---|---|---|
| Ses UDP, MC TCP — bu yüzden sadece ses düşüyor | ✅ **Kesin** | SVC resmî wiki, protokol tanımı |
| DERP relay TCP/443 üzerinden gider | ✅ **Kesin** | Tailscale dokümantasyonu + davranış |
| "Direct kurulup sonra relay'e dönme" bilinen bir durum | ✅ **Kesin** | Tailscale resmî docs, birebir alıntı |
| Windows UDP soket kilitlenmesi tüm direct UDP'yi öldürür | ✅ **Kesin** | Tailscale mühendisliği + PR #12927, v1.72.0 |
| **Senin vakanda sebep Windows soket hatası** | ⚠️ **Güçlü tahmin, doğrulanmadı** | E3 testi + `tailscale version` gerekli |
| DERP'e düşüş ağ olayından sonra self-heal etmiyor | ✅ **Kesin** | issue #15776, #8568 |
| Symmetric NAT teşhisi `MappingVariesByDestIP` ile yapılır | ✅ **Kesin** | Tailscale blog + docs |
| Tek tarafta 41641 açmak yeterli olabilir | 🟡 **Genelde doğru** | Tailscale KB + saha raporları; garanti değil |
| `mtu_size=1275` + Tailscale 1280 → 1303 bayt taşar | ✅ **Matematik kesin** | Wiki varsayılanı + Tailscale sabit MTU |
| **Bu taşmanın senin sorununun sebebi olduğu** | ❌ **Hayır** | Konuşma paketleri ~200 bayt. Sadece ucuz sigorta |
| `keep_alive` değerini **artırmak** çözer | ❌ **Yanlış** | Wiki: *"Setting this to a higher value **may result in timeouts**"* |

---

## E8. Tek sayfalık eylem planı

```
1. tailscale version           → herkeste. 1.72'nin altındakiler GÜNCELLENSİN.
2. Ses koptuğu anda:
   tailscale ping <sunucu>     → "via DERP" mi diyor?
   tailscale netcheck          → MappingVariesByDestIP: true mu?
3. Tailscale'i kapat-aç        → ses geldi mi? (geldiyse suçlu Tailscale, kesin)
4. Sunucuda:
   sudo ufw allow 41641/udp
   Modemde 41641/UDP → sunucu IP'si   (veya NAT-PMP/UPnP aç)
5. admin/machines'te <WAN_IP>:41641 endpoint'i görünüyor mu, doğrula.
6. voicechat-server.properties:
   mtu_size=1000               (1275 → 1000, bedava sigorta)
   bind_address=               (boş)
   voice_host=                 (boş)
   keep_alive=1000             (SAKIN ARTIRMA)
7. Hâlâ varsa ve netcheck symmetric NAT diyorsa → Peer Relay kur.
```

**Not:** 1–5 arası hiçbir adım Minecraft'a dokunmuyor. Sorun ağ katmanında;
mod ayarlarıyla oynayarak çözülmez — Görev 9'da onu denedik, çözmedi.

---
---

# EK BÖLÜM 2 — NİHAİ ÇÖZÜM: Sesi Tailscale'den tamamen çıkar

> Bu bölüm, "41641'i açtık, firewall kurallarını yazdık, hâlâ düşüyor"
> aşamasından sonra yazıldı. **41641 açmak bu vakada işe yaramaz.**
> Aşağıda neden yaramadığı ve ne yapılması gerektiği var.

## F0. Kanıt: yapılan işlerin neden hiçbiri tutmadı

Arkadaşın `tailscale ping` çıktısı şuydu:

```
pong from ... via 159.146.42.120:19216
                                 ^^^^^
```

**Port 41641 değil, 19216.**

Bu tek satır her şeyi açıklıyor:

| Yapılan | Neden boşa gitti |
|---|---|
| `New-NetFirewallRule ... -LocalPort 41641 -Protocol UDP` | Bağlantı **19216**'dan geçiyor. 41641 kuralı hiç devreye girmiyor |
| Modemde 41641 yönlendirmesi | Aynı sebep. ISP/modem NAT'ı **rastgele port** atıyor |
| Ağı "Private" yapmak | Windows firewall zaten sorun değildi; sorun **dışarıda**, ISP NAT'ında |
| `tailscaled.exe` tam yetki | Paket zaten çıkıyor; **geri dönemiyor** |

**19216 gibi rastgele bir port = arkadaşın modemi/ISP'si her oturuma yeni
dış port veriyor.** Bu porta kural yazamazsın, çünkü her seferinde değişiyor.

## F1. Kopmanın gerçek mekanizması (bu vakaya özel)

Tailscale'in **açık ve kapatılmamış** iki bug'ı tam bunu tarif ediyor:

> **"Endpoints are not refreshed after stateful NAT timeout"**
> *"Nodes behind stateful cone NAT with **random port assignment** do not refresh
> their endpoints **after the first UDP session timed out**. Peers... cannot
> establish a direct connection using **outdated endpoints**."*
> — tailscale/tailscale **issue #12256** (hâlâ AÇIK)

> *"Whenever my static IP PPPoE connection re-connects, any previously established
> UDP connections cannot be re-established... **Tailscale never seems to recover
> from this, and permanently falls back to a DERP relay.**"*
> — tailscale/tailscale **issue #18328**
> (`randomizeClientPort` bunu çözmüyor — sadece **açılışta** portu rastgeleliyor)

Yani olan şu:

```
1. tailscale ping     → NAT'ta 19216 deliği açılır, direct kurulur → SES ÇALIŞIR ✅
2. Birkaç dakika      → ISP'nin UDP conntrack'i 19216'yı düşürür
3. Tailscale endpoint'i YENİLEMİYOR (bug #12256) → eski 19216'ya konuşmaya devam
4. Cevap gelmez       → DERP (TCP/443) relay'e düşer
5. DERP = TCP head-of-line blocking → ses paketleri birikir → SVC timeout
6. MC TCP olduğu için yaşamaya devam eder → "sadece ses düştü" ❌
```

Tailscale'in **kendi dokümanı** 5. adımı doğruluyor:
> *"If heavy packets per second... of traffic are relaying over these DERP TCP
> connections, there is a **higher potential for head-of-line blocking**—and in
> the extreme case: a **TCP meltdown**."*
> — Tailscale Docs, "Troubleshoot hard NAT issues"

### Neden `tailscale ping` "çözdü" sanıldı

Ping **NAT deliğini yeniden açtı**. Bu bir tamir değil, **elle delik açma**.
Delik NAT timeout'una kadar (30 sn – birkaç dk) yaşar, sonra aynı döngü başlar.
İşte "bir süre sonra düşüyor"un sebebi tam olarak bu.

**Sonuç: bu, ayarla düzelecek bir şey değil. Tailscale'in açık bir bug'ı +
arkadaşın ISP'sinin NAT davranışı. Sizin tarafınızdan kapatılamaz.**

---

## F2. ÇÖZÜM — Sesi Tailscale'in içinden geçirme

Kilit fikir: **Minecraft Tailscale'de kalsın, ses Tailscale'i hiç kullanmasın.**

SVC'de bunu yapmak için tasarlanmış bir alan zaten var: **`voice_host`**.
Bu alan client'a *"sesi şu adrese gönder"* der ve **Minecraft bağlantısından
tamamen bağımsızdır.**

> *"`voice_host`: The hostname that clients should use to connect to the voice chat.
> This may also include a port, e.g. `'example.com:24454'`"*
> — SVC resmî wiki

Böylece:

```
Minecraft  →  Tailscale (100.70.34.111:25565)  TCP   ← dokunma, çalışıyor
Ses        →  doğrudan public IP :24454        UDP   ← Tailscale'i baypas eder
```

Ses artık NAT hole-punching'e, DERP'e, endpoint yenilemeye **hiç bağımlı değil.**
Sorunun tüm sınıfı ortadan kalkar.

### Yöntem A — Modemde port açabiliyorsan (TERCİH EDİLEN)

Sunucu senin evinde, modeme erişimin var. Yapılacak:

**1) Modemde tek bir yönlendirme:**
```
Dış port: 24454   Protokol: UDP   →   Sunucu PC'nin yerel IP'si : 24454
```
⚠️ Protokolü **UDP** seç. Çoğu modem varsayılan olarak TCP açar, o işe yaramaz.

**2) Sunucuda firewall:**
```bash
sudo ufw allow 24454/udp
sudo ufw reload
```

**3) `config/voicechat/voicechat-server.properties`:**
```properties
port=24454
bind_address=*
voice_host=<SENIN_PUBLIC_IP>:24454
mtu_size=1000
keep_alive=1000
```

**4) Sunucuyu tam yeniden başlat** (`/reload` yetmez).

**IP'n değişiyorsa:** public IP yerine bir **DDNS adı** kullan
(No-IP, DuckDNS — ücretsiz). `voice_host` hostname kabul ediyor:
```properties
voice_host=senin-adin.duckdns.org:24454
```
Böylece IP değişse de ses kopmaz. **Bunu yap, yoksa IP değiştiği gün yine kopar.**

**Doğrulama:** oyuncunun PC'sinden
```
nc -vzu <public-ip> 24454
```

### Yöntem B — Modemde port açamıyorsan (CGNAT / operatör engeli)

O zaman sesi bir **UDP tüneli** üzerinden ver. playit.gg bunu ücretsiz yapıyor
ve **resmî SVC entegrasyonu var** (playit'in kendi dokümanında bölüm olarak duruyor).

> Bu playit'e geçmek **değil.** Minecraft yine Tailscale'de kalıyor.
> Sadece ses için tek bir UDP tüneli açıyorsun.

1. playit.gg'de **yeni bir tünel** oluştur — Protocol: **`MC: Simple Voice Chat`**,
   Local IP: `127.0.0.1`, Local Port: `24454`
   ⚠️ Bu, Minecraft tünelinden **ayrı** bir tünel olmalı. Mevcut MC tünelini değiştirme.
2. Sana `147.185.221.181:25732` gibi bir **IP:port** verir
3. Config:
```properties
port=24454
bind_address=*
voice_host=147.185.221.181:25732
```
(kendi adresini yaz). `port=24454` **değiştirilmez** — resmî rehber sadece
`voice_host`'u değiştiriyor.
4. playit agent'ı sunucuda **servis olarak** çalıştır (yoksa her restartta elle açman gerekir):
```bash
sudo systemctl enable --now playit
```

Kaynak: https://playit.gg/support/svc-minecraft/

### Yöntem C — Tailscale'de kalmak şartsa: Peer Relay

Yukarıdaki ikisi de olmuyorsa, DERP yerine **kendi relay'ini** koy.
Tailscale'in bağlanma sırası: direct → **peer relay** → DERP.
Peer relay **UDP** taşır, DERP'in TCP head-of-line blocking'i olmaz.

İyi bağlantılı bir node'da (tercihen İstanbul'da ucuz bir VPS) peer relay aç.

⚠️ **Emin değilim:** Peer Relay görece yeni bir özellik; kurulum adımlarını ve
Tailscale sürüm gereksinimini doğrulayamadım. Tailscale'in resmî
bağlanma sırasının **direct → peer relay → DERP** olduğu teyitli
(`tailscale.com/docs/integrations/firewalls`), ama bu senaryoda ne kadar
kazandıracağını **ölçmedim**. A veya B çalışıyorsa buna hiç girme.

Bu en zahmetli seçenek. **Önce A'yı dene.**

---

## F3. Yapılmaması gerekenler (denendi, sonuç vermez)

| Yapma | Neden |
|---|---|
| 41641'e firewall kuralı yazmak | Bağlantı 19216'dan geçiyor, kural devreye girmiyor |
| `randomizeClientPort: true` | Portu **sadece açılışta** rastgeliyor, NAT timeout'unu çözmüyor (issue #18328) |
| `keep_alive`'ı artırmak | Wiki: *"may result in **timeouts**"* — sorunu büyütür |
| Her kopmada `tailscale ping` atmak | Palyatif. NAT deliğini elle açmak; birkaç dk sonra aynı yere gelirsin |
| Windows firewall / "Private ağ" ayarları | Sorun Windows'ta değil, ISP NAT'ında. Paket çıkıyor, **geri dönemiyor** |
| Tailscale'i kapat-aç | Geçici. Yeni delik açar, yine kapanır |

---

## F4. Özet

**Teşhis:** Arkadaşın ISP'si UDP oturumlarına rastgele port veriyor ve zaman
aşımına uğratıyor. Tailscale bu durumda endpoint'ini yenilemiyor (açık bug
#12256) ve kalıcı olarak DERP'e düşüyor. DERP TCP olduğu için ses ölüyor,
MC yaşıyor.

**Bu sizin tarafınızdan ayarla düzeltilemez.**

**Çözüm:** `voice_host` ile sesi Tailscale'in dışına çıkar. Modemde
**24454/UDP** aç, `voice_host=<DDNS-adresin>:24454` yaz. Ses artık
NAT traversal'a bağımlı olmaz, kopma sınıfı tamamen ortadan kalkar.

**Süre:** 10 dakika. **Dokunulan yer:** modemde 1 kural + config'de 3 satır.
