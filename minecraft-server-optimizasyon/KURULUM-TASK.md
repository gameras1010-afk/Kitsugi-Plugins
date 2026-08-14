# ✅ KURULUM TASK — Tab Info + Private Messages

> **MC 1.21.1 · NeoForge · offline-mode (korsan) sunucu**
> İki dosya. İkisi de **sadece sunucuya**. Arkadaşların hiçbir şey kurmaz.

---

## 🔴 ÖNCE: MineTogether İPTAL

**Kurma. Sana yaramaz.**

Kaynak koduna baktım (`MTSessionProvider.java`, MineTogether 1.21 dalı):

```java
beginAuth() → MojangUtils.joinServer(PI, U.getAccessToken());
```

Mod açılışta **Mojang oturum sunucusuna** access token gönderip doğrulama istiyor.
TLauncher / korsan launcher'da o token geçersiz → doğrulama başarısız → **sohbet ve arkadaş listesi hiç bağlanmaz.**

Modun zaten tek işi arkadaş listesi + DM. O gidince elinde **4.8 MB boş jar** kalıyor.
Üstelik senin + arkadaşlarının + sunucunun hepsine 3'er dosya kurdurtuyordu.

**Karar: MineTogether, PolyLib, Architectury → hiçbirini indirme.**

### Yerine ne geliyor?

**Private Messages** — aynı işi yapar, hesap istemez, kimse bir şey kurmaz.

| | MineTogether | Private Messages |
|---|---|---|
| Korsan hesapta çalışır mı | 🔴 **Hayır** | 🟢 Evet |
| Kim kurar | Sunucu + sen + herkes | 🟢 **Sadece sunucu** |
| Boyut | 4.8 MB + 2 bağımlılık | 🟢 37 KB, bağımlılık yok |
| DM | GUI'li | Komutla (`/msg`) |
| Offline mesaj | Yok | 🟢 **Var** |

Tek kaybın: şık pencere yerine komut kullanacaksın. Karşılığında herkesin kurulum derdi bitiyor.

---

# 🟩 GÖREV 1 — Tab Info (5 dk)

Tab'a basınca ölüm / kill / oynama süresi / konum / boyut gösterir.

### 1.1 İndir

⚠️ **`.jar` olanı İNDİRME** — o sürüm Fabric API istiyor, NeoForge'da yüklenmez.
Aradığın **`.zip`** (datapack).

- [ ] Direkt link:
```
https://cdn.modrinth.com/data/DuHZti8U/versions/435KwhWd/tab-info-0.2.0.zip
```
```
36.421 B | sha1: 15932aeb42d1937916fbc4e6c3d5c18b71f9388f
```

### 1.2 Kur
- [ ] Sunucuyu kapat
- [ ] `.zip`'i **`world/datapacks/`** içine at — *`mods/` değil!*

```
sunucu/
└── world/
    └── datapacks/
        └── tab-info-0.2.0.zip   ← buraya
```

> Dünya klasörün `world` değilse: `server.properties` → `level-name` neyse o klasör.

### 1.3 Test
- [ ] Sunucuyu aç
- [ ] `/datapack list` → `tab-info` görünüyor mu?
- [ ] Oyuna gir, **Tab'a bas** → bilgiler dönüyor mu? *(2 sn'de bir yenilenir, normal)*

### 1.4 Ayarla
- [ ] `/function tab_info:config` → istemediğin satırı tıklayarak kapat

### ✅ Bitti
Arkadaşlarına söylemene gerek yok, onlarda otomatik görünür.

**Geri alma:** `.zip`'i sil + restart. Tab'da artık kalırsa:
```
/scoreboard objectives setdisplay list
```

---

# 🟦 GÖREV 2 — Private Messages (5 dk)

Özel mesaj, cevaplama, offline mesaj, engelleme, kişisel not.

### 2.1 İndir
- [ ] Direkt link:
```
https://cdn.modrinth.com/data/CHpe5Yyf/versions/iz6zg7kc/private_messages-2.1.0.jar
```
```
37.715 B | sha1: f08dcc00877ca89a1dcaafa10c3327ff7b312d94
bağımlılık: YOK
```

### 2.2 Kur
- [ ] Sunucuyu kapat
- [ ] Jar'ı sunucunun **`mods/`** klasörüne at
- [ ] Başlat, logu oku:

```bash
grep -iE "error|conflict|incompatible|failed|exception|missing" logs/latest.log | head -30
```
- [ ] Temizse devam

### 2.3 Test
- [ ] `/msg <arkadaş> selam` → gitti mi?
- [ ] Karşı taraf **mesaja tıklasın** → cevap kutusu açılıyor mu?
- [ ] `/r selam sana da`
- [ ] Kendine mesaj at → nota kaydolur → `/pm notes`

### 2.4 Arkadaşlara duyur

Şunu at yeter, **kimse bir şey indirmeyecek:**

```
/msg <isim> <mesaj>   → özel mesaj
/r <mesaj>            → son mesaja cevap
/ignore <isim>        → o kişiden mesaj alma
/pm notes             → kendine not
```

Offline birine mesaj atarsan **girdiğinde alır.**
Kayıtlı veriler şifreli, sunucu sahibi bile okuyamıyor.

### ✅ Bitti

---

## 🔴 SORUN ÇIKARSA

| Belirti | Sebep | Çözüm |
|---|---|---|
| Tab boş | Datapack yüklenmemiş | `/datapack list`, `level-name` doğru mu |
| Tab'ı `mods/`e attım | Yanlış klasör | `world/datapacks/`'a taşı |
| `.jar` indirdim, yüklenmiyor | Fabric API istiyor | `.zip` sürümünü indir |
| `/msg` komutu yok | Jar `mods/`de değil | Klasörü ve logu kontrol et |
| Komut var ama gitmiyor | Karşı taraf `/ignore` yapmış | `/ignore` ile geri aç |

**Her şeyi geri almak:** İki dosyayı sil, restart. Dünyaya kalıcı iz bırakmazlar.

---

## 📋 ÖZET

| Dosya | Nereye | Kim kurar |
|---|---|---|
| `tab-info-0.2.0.zip` | `world/datapacks/` | 🟢 sadece sunucu |
| `private_messages-2.1.0.jar` | `mods/` | 🟢 sadece sunucu |

**Toplam 74 KB. Arkadaşların hiçbir şey yapmıyor. İkisi de 10 dakikada biter.**

---

## ⚠️ AYRI KONU — offline-mode güvenliği

`online-mode=false` olduğu için Tailscale ağındaki **herkes senin isminle girebilir.**
Girer, OP komutlarını kullanır, sandığını boşaltır.

Çözüm: **Auth** modu (`https://modrinth.com/mod/auth`) — sadece sunucu, hesap istemez.
Herkes `/register <şifre> <şifre>` yapar, sonra her girişte `/login <şifre>`.

Bu iki modla işin yok, ayrı bir iş. Ama ağa dışarıdan biri düşerse lazım olur.
