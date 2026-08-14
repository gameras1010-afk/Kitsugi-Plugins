# ✅ KURULUM TASK — Chat Screen + Private Messages + Tab Info

> **MC 1.21.1 · NeoForge · offline-mode (korsan) sunucu**
> Aradığın şey: **tuşa bas → pencere açılsın → kişi seç → yazış.**
> Bu üçlü onu veriyor. Hesap yok, harici sunucu yok, her şey sende.

---

## 🎯 MANTIK — neden 2 mod birden

MineTogether tek modda hem pencereyi hem mesajlaşmayı yapıyordu.
Ama mesajlaşma kısmı **CreeperHost'un sunucusundaydı** ve orası Mojang'a soruyordu → sende çalışmaz.

Biz o işi ikiye bölüyoruz, ikisi de **senin sunucunda:**

```
      PENCERE (görünen kısım)          MESAJLAŞMA (arka plan)
      Chat Screen                       Private Messages
      client'ta, C tuşu                 sunucuda, /msg
              └──────────┬──────────────────────┘
                    ikisi birleşince
              MineTogether hissi, hesapsız
```

Chat Screen sen pencereden yazınca arkada `/msg` gönderiyor.
Private Messages o `/msg`'i taşıyor. **Sen komut görmüyorsun** — pencerede sohbet balonu görüyorsun.

---

## 📦 3 DOSYA

| Dosya | Nereye | Kim kurar | Boyut |
|---|---|---|---|
| `chatscreen-neoforge-1.21.1-0.1.2.jar` | `mods/` | 🔵 sen + arkadaşların | 43 KB |
| `private_messages-2.1.0.jar` | `mods/` | 🟢 sadece sunucu | 37 KB |
| `tab-info-0.2.0.zip` | `world/datapacks/` | 🟢 sadece sunucu | 36 KB |

**Toplam 116 KB.** MineTogether tek başına 4.8 MB'tı.

### 📮 Arkadaşlarına gidecek tek dosya
**Sadece `chatscreen-neoforge-1.21.1-0.1.2.jar` (43 KB).** Başka hiçbir şey gönderme.

- `private_messages-2.1.0.jar` → sunucu modu. Arkadaşın client'ında işi yok.
- `tab-info-0.2.0.zip` → **datapack.** Datapack'ler sunucuya bağlanınca oyuncuya
  **otomatik senkronlanır** — arkadaşın indirmesine, kurmasına gerek yok, hatta
  `mods/` klasörüne atarsa **yanlış** olur (datapack `mods/`'a atılmaz, hiç yüklenmez).
  Sen `world/datapacks/` içine koy, bitti; herkes Tab'da görür.

---

# 🟩 GÖREV 1 — Private Messages (sunucu, 5 dk)

> Önce bu. Chat Screen'in çalışması için `/msg` komutunun sunucuda **olması şart.**

### 1.1 İndir
```
https://cdn.modrinth.com/data/CHpe5Yyf/versions/iz6zg7kc/private_messages-2.1.0.jar
```
```
37.715 B | sha1: f08dcc00877ca89a1dcaafa10c3327ff7b312d94
bağımlılık: YOK · dedicated_server_only
```

### 1.2 Kur
- [ ] Sunucuyu kapat
- [ ] Jar'ı sunucunun **`mods/`** klasörüne at
- [ ] Başlat:
```bash
grep -iE "error|conflict|incompatible|failed|exception|missing" logs/latest.log | head -30
```
- [ ] Temizse devam

### 1.3 Test — bu adımı atlama
- [ ] Oyuna gir, `/msg <arkadaş> test` yaz
- [ ] Gitti mi? **Gittiyse Chat Screen de çalışacak demektir.**

> ⚠️ Gitmiyorsa Görev 2'ye geçme. Önce burayı çöz.

---

# 🟦 GÖREV 2 — Chat Screen (client, 10 dk)

> İşte istediğin pencere bu.

### 2.1 İndir
```
https://cdn.modrinth.com/data/byIp8S9t/versions/Cwfq7nzn/chatscreen-neoforge-1.21.1-0.1.2.jar
```
```
43.189 B | sha1: b00f597e765d4a1f54775d8d689a0f3ee4393345
bağımlılık: YOK · client_only · MIT lisans
```

> ℹ️ Sürüm `0.1.2` **beta** etiketli ve tek geliştirici yazmış.
> Client-only olduğu için en kötü ihtimalde **senin oyunun** etkilenir, sunucu/dünya değil.
> Sevmezsen jar'ı sil, hiçbir iz kalmaz.

### 2.2 Kendine kur
- [ ] Jar'ı **kendi** `mods/` klasörüne at *(sunucuya DEĞİL — client-only)*
- [ ] Oyunu aç, sunucuya gir
- [ ] **C tuşuna bas** → pencere açıldı mı?
- [ ] Tuşu değiştirmek istersen: Ayarlar → Kontroller

### 2.3 Pencerede ne var
- [ ] **Server chat** sekmesi → normal genel sohbet
- [ ] **Personal chat** → online oyuncu seç → 🎯 **özel yazışma, sohbet görünümünde**
- [ ] **Team chat** → takımdaysan (`/teammsg`)

### 2.4 Arkadaşlara dağıt
- [ ] Sadece **`chatscreen-neoforge-1.21.1-0.1.2.jar`** gönder — tek dosya, 43 KB
- [ ] "mods klasörüne at, C'ye bas" de, o kadar
- [ ] Kurmayan da sunucuya girebilir — sadece pencereyi görmez, `/msg` ile yazar
- [ ] ❌ **Tab Info zip'ini gönderme.** Datapack sunucudan otomatik gelir;
      arkadaşın kurmasına gerek yok, `mods/`'a atarsa zaten çalışmaz.

### 2.5 Test
- [ ] C → arkadaşını seç → yaz
- [ ] O sana pencereden cevap versin
- [ ] İkinizde de sohbet akıyor mu?

---

# 🟨 GÖREV 3 — Tab Info (sunucu, 5 dk, opsiyonel)

Tab'a basınca ölüm / kill / oynama süresi / konum.

⚠️ **`.jar` olanı İNDİRME** — Fabric API istiyor, NeoForge'da yüklenmez. **`.zip`** olan lazım.

✅ **Bu tamamen senlik bir iş.** Datapack'i sadece sen sunucuya koyuyorsun.
Arkadaşların hiçbir şey indirmiyor — sunucu bağlantı sırasında datapack içeriğini
kendisi gönderiyor, Tab herkeste otomatik dolu geliyor.

### 3.1 İndir
```
https://cdn.modrinth.com/data/DuHZti8U/versions/435KwhWd/tab-info-0.2.0.zip
```
```
36.421 B | sha1: 15932aeb42d1937916fbc4e6c3d5c18b71f9388f
```

### 3.2 Kur
- [ ] Sunucuyu kapat
- [ ] `.zip`'i **`world/datapacks/`** içine at — *`mods/` değil!*

```
sunucu/
└── world/
    └── datapacks/
        └── tab-info-0.2.0.zip
```
> Dünya klasörün `world` değilse: `server.properties` → `level-name` neyse o.

### 3.3 Test
- [ ] `/datapack list` → `tab-info` var mı?
- [ ] Tab'a bas
- [ ] `/function tab_info:config` → istemediğini kapat

**Geri alma:** sil + restart. Tab'da artık kalırsa `/scoreboard objectives setdisplay list`

---

## 🔴 SORUN ÇIKARSA

| Belirti | Sebep | Çözüm |
|---|---|---|
| C'ye basıyorum, pencere yok | Tuş çakışması | Kontroller'den başka tuş ata |
| Pencere açılıyor, mesaj gitmiyor | Sunucuda `/msg` yok | Görev 1'i yap |
| Pencere açılıyor, mesaj **gelmiyor** | Sunucu mesaj formatını değiştiriyor | `private-messages.json` → format satırlarını sadeleştir |
| Arkadaşta pencere yok | Jar'ı kurmamış | 43 KB'lık dosyayı tekrar gönder |
| Tab boş | Datapack yüklenmemiş | `/datapack list`, `level-name` kontrol |
| Tab'ı `mods/`e attım | Yanlış klasör | `world/datapacks/`'a taşı |

**Her şeyi geri almak:** 3 dosyayı sil, restart. Dünyaya kalıcı iz bırakmazlar.

---

## ❌ KURMA — ve nedeni

| Mod | Neden |
|---|---|
| **MineTogether** | `MTSessionProvider.java` → `MojangUtils.joinServer(uuid, accessToken)`. Açılışta Mojang'a doğrulama yolluyor, korsanda patlıyor. Sohbet hiç bağlanmaz. |
| **PolyLib / Architectury** | Sadece MineTogether için gerekiyordu, o gidince gereksiz |
| **Essential Mod** | Mojang oturumu **zorunlu**, hiçbir özellik açılmaz |
| **FriendMod** | "FriendMod services" = yine harici sunucu, aynı tuzak |
| **MikasRevs Phone** | Telefon var ama ARR lisans, 1.4 MB, herkes kuracak — Chat Screen 43 KB ile aynı işi yapıyor |

**Kural:** Mesajlaşması **başkasının sunucusundan** geçen hiçbir mod sende çalışmaz.
Bu üçlünün hepsi senin makinende.

---

## 📋 KURULUM SIRASI

```
1. Private Messages  → sunucu mods/       → /msg test et
2. Chat Screen       → sen + arkadaşlar   → C tuşu
3. Tab Info          → world/datapacks/   → Tab tuşu
```

**Sıra önemli.** Önce 1 çalışmadan 2'yi kurma — pencere açılır ama mesaj gitmez, boşuna uğraşırsın.

---

## ⚠️ AYRI KONU — offline-mode güvenliği

`online-mode=false` olduğu için Tailscale ağındaki **herkes senin isminle girebilir** — OP komutları, sandığın, hepsi.

Çözüm: **Auth** modu → `https://modrinth.com/mod/auth`
Sadece sunucu, hesap istemez. `/register <şifre> <şifre>` sonra her girişte `/login <şifre>`.

Bu üç modla ilgisi yok, ayrı iş. Ama ağa dışarıdan biri düşerse lazım.
