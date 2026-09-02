"""
processor/tag_tools.py
======================
ASS tag çıkarma/geri yükleme ve satır sonu koruma araçları.
extract_tags, restore_tags, extract_tags_with_placeholders,
restore_tags_from_placeholders, protect_ass_newlines, restore_ass_newlines
"""
import re

def extract_tags(text):
    """
    Extracts {\\pos...} style tags from the text.
    Returns: (clean_text, tags_list)
    Sadece gerçek ASS tag'leri (backslash içerenler) döner.
    Inline comment'ler ({-san}, {bro wtf}) tamamen atlanır.
    """
    if _ASS_EXTRACTOR_AVAILABLE:
        # Yeni motor: comment blokları filtrelenir
        import re as _re
        _BLOCK = _re.compile(r'\{[^}]*\}')
        matches = []
        for m in _BLOCK.finditer(text):
            blk = m.group(0)
            if '\\' in blk:  # Sadece gerçek ASS tag'leri
                matches.append(blk)
        clean_text = _re.sub(r'\{[^}]*\}', '', text).strip()
        return clean_text, matches
    else:
        # Fallback: eski basit yöntem
        pattern = re.compile(r'\{.*?\}')
        matches = pattern.findall(text)
        clean_text = pattern.sub('', text).strip()
        return clean_text, matches

def restore_tags(text, tags):
    """
    Restores tags to the beginning of the text.
    """
    if not tags: return text
    tag_str = "".join(tags)
    return f"{tag_str}{text}"

def extract_tags_with_placeholders(text):
    """
    {\\...} tag bloklarini __T0__, __T1__... placeholder'larla degistirir.
    Tag'lerin orijinal metin icindeki konumlarini korur.
    Returns: (placeholder_text, tag_map_dict)

    [UPGRADE] ass_tag_extractor modulunu kullanir:
      - Gercek ASS tag bloklari (backslash icerenler) → __T0__ placeholder
      - Inline comment bloklari ({-san}, {bro wtf}, {wailing?}) → SILINDI
        (AI bu bloklari goremez, bozamaz, placeholder'a donusturemez)
    Source: libass/ass_parse.c — valid tags MUST start with backslash
    """
    if _ASS_EXTRACTOR_AVAILABLE:
        clean_text, tag_map = _ass_extract(text)
        return clean_text, tag_map
    else:
        # Fallback: eski yontem
        pattern = re.compile(r'\{[^}]*\}')
        tag_map = {}
        counter = [0]
        def replacer(m):
            tag_content = m.group(0)
            if '\\' not in tag_content:
                return ''
            key = f'__T{counter[0]}__'
            tag_map[key] = tag_content
            counter[0] += 1
            return key
        placeholder_text = pattern.sub(replacer, text)
        return placeholder_text, tag_map

def restore_tags_from_placeholders(text, tag_map):
    """
    __T0__, __T1__... placeholder'lari orijinal tag'lerle degistirir.
    Tag'ler orijinal konumlarina tam olarak yerlestrilir.
    AI placeholder'lari sildiyse eksik tag'ler basa eklenir.

    [UPGRADE] ass_tag_extractor'in fuzzy restore motorunu kullanir:
      - Exact match: __T0__ → tag
      - Fuzzy: __T 0__, __t0__, [T0], (T0) → tag
      - Pozisyon tag'leri (pos/move/org/an) eksikse → basa ekle
      - Son asama: kalan __Tn__ kalıntılarını temizle
    """
    if not tag_map:
        return text

    if _ASS_EXTRACTOR_AVAILABLE:
        restored, _missing = _ass_restore(text, tag_map)
        # Kalan __Txx__ kalıntıları temizle
        restored = re.sub(r'__[Tt]\d+__', '', restored)
        return restored
    else:
        # Fallback: eski yontem
        restored_keys = set()
        for key, tag in tag_map.items():
            if key in text:
                text = text.replace(key, tag)
                restored_keys.add(key)
            elif key.lower() in text.lower():
                pattern = re.compile(re.escape(key), re.IGNORECASE)
                if pattern.search(text):
                    text = pattern.sub(tag, text)
                    restored_keys.add(key)
        missing_tags = [tag_map[k] for k in tag_map if k not in restored_keys]
        if missing_tags:
            # Akıllı yerleştirme: açılış/kapanış çiftlerini tespit et
            # {\i1}...{\i0}, {\b1}...{\b0}, {\u1}...{\u0} gibi çiftler
            _OPEN_RE  = re.compile(r'\{\\([ibuscBIUS])1\}')
            _CLOSE_RE = re.compile(r'\{\\([ibuscBIUS])0\}')
            # Tüm missing tag'leri sona ekle (başa değil — daha az zararli)
            # Gerçek çift varsa orjinal metnin anahtar kelimeleriyle match dene
            for _mt in missing_tags:
                _om = _OPEN_RE.match(_mt)
                _cm = _CLOSE_RE.match(_mt)
                if _om or _cm:
                    # İtalik/bold/underline tag'i — sona ekle
                    text = text + _mt
                else:
                    # Konum tag'i (pos, move, an, clip) → BASA ekle
                    text = _mt + text
        text = re.sub(r'__[Tt]\d+__', '', text)
        return text

# ============================================
# ASS ÖZEL KARAKTER KORUMASI (\N \n \h)
# ============================================
# \N = Hard Newline (satır sonu, kesinlikle kırılır)
# \n = Soft Newline (wrap moduna göre kırılır)
# \h = Hard Space (bölünmeyen boşluk)
# Bunlar çeviriye giderse AI siler ya da bozar — placeholder ile koruyoruz.
_ASS_SPECIAL_CHARS = [
    ('\\N', '__NL__'),  # Hard newline  (ASS: tek backslash + N)
    ('\\n', '__SL__'),  # Soft newline  (ASS: tek backslash + küçük n)
    ('\\h', '__HS__'),  # Hard space    (ASS: tek backslash + h)
]

def protect_ass_newlines(text):
    """
    ASS özel satır/boşluk karakterlerini placeholder'lara çevirir.
    Çeviriye göndermeden ÖNCE çağrılmalı.

    Dönüşümler:
      \\N → __NL__
      \\n → __SL__
      \\h → __HS__
      <br />, <br/>, <BR> vb. → __NL__  [FIX: kaynak HTML br desteği]

    Returns: (protected_text, True/False değişiklik oldu mu)
    """
    changed = False
    # [FIX] Kaynak dosyada <br /> varsa (başka araçtan üretilmiş satır vb.)
    # AI'ya göndermeden önce __NL__'e çevir. Restore sırasında \N olur.
    if '<br' in text.lower():
        new_text = re.sub(r'(?i)<br\s*/?>', '__NL__', text)
        if new_text != text:
            text = new_text
            changed = True
    for original, placeholder in _ASS_SPECIAL_CHARS:
        if original in text:
            text = text.replace(original, placeholder)
            changed = True
    return text, changed


def restore_ass_newlines(text):
    """
    protect_ass_newlines() ile değiştirilen placeholder'ları geri yükler.
    Çeviri sonrası MUTLAKA çağrılmalı.

    Dönüşümler:
      __NL__ → \\N
      __SL__ → \\n
      __HS__ → \\h

    [FIX] Restore sonrası art arda \\N\\N → \\N dedup.
    [FIX2] <br /> HTML etiketleri → \\N (AI cache/fuzzy path dahil her yerde).
    [FIX3] __NL____NL__ placeholder dedup restore öncesi.
    """
    # [FIX3] Placeholder dedup — restore öncesi (kaynak ASS'de \\N\\N varsa)
    if '__NL____NL__' in text or '__SL____SL__' in text:
        text = re.sub(r'(__NL__){2,}', '__NL__', text)
        text = re.sub(r'(__SL__){2,}', '__SL__', text)
    # [FIX2] <br /> HTML etiketlerini \\N'e çevir (AI'dan veya cache'den gelebilir)
    if '<br' in text.lower():
        text = re.sub(r'(?i)(<br\s*/?>\s*)+', r'\\N', text)
    # Placeholder'ları geri yükle
    for original, placeholder in _ASS_SPECIAL_CHARS:
        if placeholder in text:
            text = text.replace(placeholder, original)
    # [FIX] Çift/üçlü \\N kalıplarını tek \\N'e indir (kaynak veya AI kaynaklı)
    if '\\N\\N' in text:
        text = re.sub(r'(\\N){2,}', r'\\N', text)
    return text

# ============================================
# KARAOKE TAG KORUMASI (\k \kf \ko \K)
# ============================================
# Karaoke tag'leri: {\k50}Kelime {\kf30}Kelime2 gibi yapılardır.
# \k = syllable timing, \kf = fill karaoke, \ko = outline karaoke, \K = sweep karaoke
# SORUN: Bu tag'ler __T0__ sistemiyle SADECE kapalı {} bloğu olarak korunuyor.
# Ama karaoke satırları birden fazla kelime-timing çifti içerir:
#   {\k50}Hel {\k40}lo {\k60}World
#   Her {} bloğu ayrı __T0__, __T1__, __T2__ olur → doğru çalışıyor.
# 
# Asıl sorun: Bu satırlar has_karaoke=True ile TAMAMEN ATLANIYOR!
# FIX: Karaoke timing tag'leri __T__ sistemiyle korunuyor (extract_tags_with_placeholders
# zaten bunu yapıyor), sadece skip mantığını değiştirmemiz gerekiyor.
#
# ÖZEL DURUM — {\k} tag'siz metin içindeki "inline karaoke":
# Bazen karaoke şöyle gelir: {\1c&H00FFFF&\k50}Hel{\k40}lo
# Burada ilk {} bloğu hem stil hem timing içeriyor. Bu da __T__ ile korunuyor.
#
# SONUÇ: extract_tags_with_placeholders zaten karaoke tag'lerini de kapsıyor.
# Sadece "karaoke satırlarını atla" kararını kaldırıp çeviri akışına bırakmak yeterli.
# Şarkı sözü (is_song_symbol ♪) veya song_style ise yine atlanır.

# Sansür tespiti: AI bazen küfürlü kelimeleri s*k, f**k, b*tch gibi maskeler
# Bu durum tespit edilince retry mekanizması tetiklenir
_CENSORED_PATTERN = re.compile(
    r'\b\w*\*+\w*\b',  # En az bir * içeren kelime: s*k, f**k, b*tch, a**hole
    re.IGNORECASE
)

def has_censored_content(text):
    """
    Çeviri sonucunda sansürlenmiş (yıldızlı) kelime var mı kontrol eder.
    Örnekler: s*k, f**k, b*tch, a**hole, şi* gibi kalıplar.
    Returns True → Sansür tespit edildi, retry gerekli.
    """
    if not text:
        return False
    # En az bir harf + en az bir * + opsiyonel harf içeren kelime
    matches = _CENSORED_PATTERN.findall(text)
    # Sadece * içeren kısa "kelimeler" (örn: "***" tek başına) da sansür sayılır
    return len(matches) > 0

def has_karaoke_tags(text):
    """
    Metinde karaoke timing tag'i var mi kontrol eder.
    Sadece gercek karaoke timing tag'leri:
      \\k50   = syllable timing
      \\kf30  = fill karaoke
      \\ko20  = outline karaoke
      \\K100  = sweep karaoke

    [FIX] Eski regex r'\\\\[Kkf]{1,2}o?\\d*' yanlistir:
      \\fk (font skew) ve \\b1 (bold) de eslesiyordu!
    Yeni regex: k harfiyle baslayan + opsiyonel f/o + zorunlu rakam
    veya buyuk K + zorunlu rakam. Boylece \\fk, \\b, \\fs gibi
    harflerle baslayan diger tagler hic eslesmiyor.

    NOT: Bu fonksiyon sadece tespit icin, skip karari vermez.
    Karaoke satirlari tag'ler korunarak cevriliyor.
    """
    # {\\k50}, {\\kf30}, {\\ko20}, {\\K100} eslesir
    # {\\fk}, {\\b1}, {\\fs40} ESLESMEZ (k/K ile baslayan sadece)
    return bool(re.search(r'\\k[fo]?\d+|\\K\d+', text))

