# Bozuk Chunk'lar — Sebep ve Çözüm

> Kapıların yarım açılması, chunk'ların kesik kesik olması,
> bir chunk'ın çok aşağıda / birkaç chunk'ın çok yukarıda kalması.

**Bu rastgele bir bug değil. Sebebi belli ve senin config'inde.**

---

## 🔴 SEBEP: İki C2ME ayarı

Sana verdiğim `c2me.toml`'da bu iki satır açıktı. **Hatam.**
Performans için açmıştım, dünya bütünlüğü riskini yeterince tartmamışım.

### `reduceLockRadius = true` ← ASIL SUÇLU

C2ME'nin **kendi config açıklamasında** birebir şu yazıyor:

> *"Whether to allow reducing lock radius **(faster but UNSAFE)
> (YOU HAVE BEEN WARNED)**"*

Mod yazarı büyük harfle "UYARILDIN" yazmış. Sebebi şu:

Normalde bir chunk üretilirken komşu chunk'lar **kilitlenir** ki iki
thread aynı sınıra aynı anda yazmasın. `reduceLockRadius` bu kilit
yarıçapını küçültür — chunk'lar birbirini beklemez, **hızlanır**,
ama sınırda tutarsızlık oluşur.

**Kanıt — C2ME issue #508 (Ocak 2026):**
> *"We have a problem with a builder on our server... It goes away by
> disabling this config in C2ME: `reduceLockRadius = false`"*

Yapılar bozuluyor, ayar kapatılınca düzeliyor. Birebir senin durumun.

Aynı repoda ayrıca: *"Potential deadlock in acquiring chunk locks for
features chunks"* — iki chunk birbirinin kilidini bekleyip kilitleniyor.

### `allowThreadedFeatures = true` ← İKİNCİ SUÇLU

"Feature" = ağaç, cevher, mağara, bitki, **ve yapı parçaları.**

Bunların kritik özelliği: **chunk sınırlarını aşarlar.** Bir ağaç iki
chunk'a yayılır, bir yapı dört chunk'a. Paralel üretilirken thread A
chunk'ı "bitti" sayıp kaydeder, thread B'nin oraya yazacağı yarım kalır.

**Sonuç:** yarım ağaç, yarım kapı, kesik yapı. Tam olarak gördüğün şey.

---

## ✅ ÇÖZÜM — 2 adım

### Adım 1: Ayarları kapat

`config/c2me.toml`:

```toml
[threadedWorldGen]
enabled = true               # ← bu KALSIN, sorun bu değil
allowThreadedFeatures = false   # ← false yap
reduceLockRadius = false        # ← false yap
asyncScheduling = true          # ← kalsın
```

> **Ne kaybediyorsun?** Worldgen ~%15-25 yavaşlar.
> **Ne kazanıyorsun?** Dünya bozulmaz. Bu takas tartışmasız.

`enabled = true` kalıyor — **paralel worldgen'i kaybetmiyorsun.**
Sadece riskli iki alt-ayarı kapatıyoruz.

### Adım 2: Bozuk chunk'ları sil

Kapatmak **yeni** chunk'ları düzeltir. Zaten bozulmuş olanlar diskte
öyle duruyor, kendi kendine düzelmez.

**MCA Selector** ile temizle: https://github.com/Querz/mcaselector

1. **Sunucuyu `/stop` ile kapat. Dünya klasörünü yedekle.**
2. MCA Selector'ü aç → `File > Open World` → `world/region`
3. Bozuk bölgeleri seç (haritada göz atarak bulabilirsin)
4. `Selection > Delete selected chunks`
5. Kaydet, sunucuyu başlat — silinen chunk'lar **doğru ayarlarla**
   yeniden üretilir

> ⚠️ İçinde yapın varsa silme! Sadece bozuk, boş araziyi sil.

**Alternatif — hiç yapın yoksa:** dünyayı komple silip baştan üret.
En temizi bu. Ayarlar artık doğru olduğu için tekrar olmayacak.

---

## 🟠 Üçüncü risk: ENHANCED autosave

Config'inde `autoSave.mode = "ENHANCED"` var. Bu **performans için iyi**
ama bir riski var:

C2ME issue takipçisinden birebir:
> *"**Chunk Corruption After Power Cut to Server** — Going to that
> location in the world I noticed that the chunks around there were
> **scrambled up**."*

ENHANCED, kaydetmeyi sunucunun boş vaktine erteler. Sunucu temiz
kapanmazsa o bekleyen chunk'lar kaybolur veya yarım yazılır.

### Kural

| Yapılacak | Yapılmayacak |
|---|---|
| Konsola `/stop` yaz | Pencereyi kapatmak |
| Kapanmasını bekle | `kill -9` / `Ctrl+C` spam |
| UPS varsa iyi olur | Elektrik kesintisinde çaresizsin |

**Daha önce sunucu düzgün kapanmadıysa** — çöktüyse, elektrik gittiyse,
pencereyi kapattıysan — bozuk chunk'ların sebebi kısmen budur.

Kesinti riskin varsa güvenli tarafa geç:
```toml
[generalOptimizations.autoSave]
mode = "VANILLA"
```

---

## 🟡 Dördüncü ihtimal: zfastnoise

Şu an dünyayı zfastnoise ile üretiyorsun. Modun kendi iddiası:

> *"Does the mod change world generation? The mod maintains
> **vanilla parity**... Do keep in mind, **Vanilla non-determinism**."*

Vanilla parity iyi. Ama şu soru kritik:

**Dünyanın bir kısmını zfastnoise OLMADAN mı ürettin?**

Eğer dünyayı önce zfastnoise'suz oluşturup sonra modu eklediysen —
ya da tersi — eski ve yeni chunk'lar **farklı üretilmiş** olur ve
aralarında **chunk duvarı** oluşur. Bu, senin tarif ettiğin
"bir chunk aşağıda, birkaç chunk yukarıda" görüntüsünün klasik sebebi.

Aynı şey **herhangi bir worldgen modunu** dünya oluşturulduktan sonra
eklemek/çıkarmak için geçerli.

**Kural:** worldgen modlarını dünya oluşturmadan ÖNCE kur, sonra dokunma.

---

## 🔍 Hangisi olduğunu nasıl anlarsın

| Görüntü | Sebep |
|---|---|
| Yarım ağaç, yarım kapı, kesik yapı — **her yerde dağınık** | `allowThreadedFeatures` + `reduceLockRadius` |
| **Düz bir hat** boyunca arazi yüksekliği zıplıyor | Worldgen modu sonradan eklendi/çıkarıldı |
| Belirli bir bölgede karmakarışık, bloklar saçma | Temiz olmayan kapanma + ENHANCED autosave |
| Chunk hiç yüklenmiyor, siyah/boş | Radium gibi uyumsuz mod (senin listende yok) |

Log'a da bak:

```bash
grep -iE "Failed to save chunk|scrambled|Chunk file at|ERROR.*chunk" logs/latest.log
```

---

## 📋 Sıralı yapılacaklar

```
1. Sunucuyu /stop ile kapat
2. Dünya klasörünü YEDEKLE (kopyala, taşıma)
3. c2me.toml:
     allowThreadedFeatures = false
     reduceLockRadius      = false
4. servercore.toml:
     [dynamic] enabled = false
5. MCA Selector ile bozuk chunk'ları sil
   (veya yapın yoksa dünyayı baştan üret)
6. Sunucuyu başlat
7. /chunky radius 3000 + /chunky start  → bir gece bekle
8. Oyna
```

7. adım önemli: **pregen'i doğru ayarlarla yapınca** hem hızı geri
kazanırsın hem de tüm arazi tek seferde, tutarlı şekilde üretilir.
Sonradan chunk duvarı oluşmaz.
