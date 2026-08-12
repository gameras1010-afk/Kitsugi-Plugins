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
