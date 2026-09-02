"""
processor/text_helpers.py
=========================
Metin analiz araçları: içerik tespiti, romaji, bracket temizleme,
ASS zaman formatları ve SRT/VTT→ASS dönüştürücü.
"""
import re
import os

# ============================================
# ROMAJI FILTRE (Kapsamli cumle duzeyinde)
# ============================================
try:
    from romaji_filter import is_romaji_sentence as _is_romaji_sentence_v2
    _ROMAJI_FILTER_LOADED = True
except ImportError:
    _is_romaji_sentence_v2 = None
    _ROMAJI_FILTER_LOADED = False

# ============================================
# ROMAJİ TESPİTİ (sadece Japonca şarkı sözlerini engelle)
# ============================================
# Japonca romaji kalıpları: "wa", "wo", "ga", "ni" gibi dilbilgisi ekleri
_ROMAJI_SUFFIXES = re.compile(
    r'\b(wa|wo|ga|ni|no|de|to|ka|na|mo|ya|ne|yo|sa|kara|made|demo|dake|'
    r'nomi|shika|ba|tara|tari|te|nde|ta|da|ru|ku|su|mu|nu|bu|gu|zu|'
    r'suru|shita|shite|shimau|shimatta|iru|ita|ite|iku|itta|itte|kuru|kita|kite|'
    r'miru|mita|mite|dekiru|dekita|naru|natta|natte|'
    r'mono|koto|toki|yori|hodo|gurai|bakari|noni|node|kedo|shi)\b',
    re.IGNORECASE
)

# İngilizce dilbilgisi kelimeleri — bunlar varsa cümle muhtemelen İngilizce
_ENG_GRAMMAR = {
    'the','be','of','and','a','in','that','have','it','for','not','on','with',
    'he','as','you','do','at','this','but','his','by','from','they','we','say',
    'her','she','or','an','will','my','one','all','would','there','their','what',
    'so','up','out','if','about','who','get','which','go','me','are','is','was',
    'were','okay','wait','how','too','make','time','come','see','look','just',
    'know','want','good','well','need','way','day','man','got','let','put','set',
    'run','try','him','its','here','when','then','them','than','very','been','has',
    'had','can','could','should','would','where','why','because','also','into',
    'after','before','over','between','through','take','said','like','some','than',
    'then','these','those','such','each','more','most','other','some','have','been'
}

# İngilizce ile romaji arasında çakışan kısa kelimeler — tek başına romaji kanıtı değil
_ROMAJI_OVERLAP = {
    'no','to','de','sa','ya','ta','mo','ka','na','ne','ba',
    'ru','ku','su','mu','nu','bu','gu','zu','da','te','shi'
}

# ─────────────────────────────────────────────────────────────────────────────
# [KRiTiK] ingilizce icerik tespiti — Her zaman cevir zamani
# ─────────────────────────────────────────────────────────────────────────────
# ─── Sansür ve Karaoke Kontrol ──────────────────────────────────────────────
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



def _is_english_content(text: str) -> bool:
    """
    Metin ingilizce mi? Evet ise -> KESINLIKLE CEVIR, hicbir skip kurali gecersiz.

    Kapsam: tabela, karaoke, sign, kisa satir, OP/ED sozu — farketmez.
    Romaji (Japonca transliterasyon) False, gercek ingilizce True doner.

    Algoritma:
      1. Bos / cok kisa → False
      2. Turkce ozel karakter (g-breve, s-cedilla vb.) varsa → kesin TR → False
      3. Yalnizca muzik sembolu (musika notasi ~) → False
      4. Romaji filter → Japonca ise False
      5. Anime isim filtresinden gecmiyor (tum kelime isim) → False
      6. content_detector freq analizi → romaji ise False
      7. TR frekans DB: kelime cogunlugu Turkce → False (zaten cevrilmis)
      8. ASCII alfabetik karakter orani >= %85 → Ingilizce → True
    """
    if not text:
        return False
    # Placeholder kalintilari temizle
    clean = re.sub(r'__[A-Za-z0-9]+__', '', text).strip()
    # Sadece sembol/muzik notu → Ingilizce degil
    if not re.search(r'[a-zA-Z]', clean):
        return False

    # ── [1] TURK'CE OZEL KARAKTER ERKEN CIKIS (EN ONEMLI) ────────────────────
    # Metnin herhangi bir yerinde Turkce ozel harf varsa → kesinlikle Turkce → False
    # Bu kontrolun en basta olmasi zorunlu — diger tum kontroller ondan once firlamakta
    _TR_CHARS_SET = frozenset('\u011f\u015f\xe7\xf6\xfc\u0131\u0130\u011e\u015e\xc7\xd6\xdc')
    if any(c in _TR_CHARS_SET for c in clean):
        return False

    # Cok kisa (1-2 karakter) → belirsiz
    alpha_chars = re.findall(r'[a-zA-Z]', clean)
    if len(alpha_chars) < 3:
        return False
    # Romaji filtresi: Romaji ise Ingilizce degil
    try:
        if is_romaji_text(clean):
            return False
    except Exception:
        pass
    # Melodic filler (la la la, na na na) → Japonca sarki dolgusu
    _words_only = re.findall(r'[a-z]+', clean.lower())
    _MELODIC = {'la', 'na', 'da', 'ra', 'ya', 'wa', 'ha', 'ba', 'pa', 'ta', 'ka', 'ga', 'sa', 'ma'}
    if _words_only and all(w in _MELODIC for w in _words_only):
        return False

    # ── Anime Karakter Ismi Kontrolu ─────────────────────────────────────────
    # Cumlenin TUMU sadece anime isimleri ise → proper noun → ceviri gerekmez.
    # Ama anime ismi + Ingilizce kelime varsa → gercek diyalog → True.
    try:
        from content_detector import is_anime_name as _is_aname
        _aw = re.findall(r"[a-zA-Z']+", clean)
        if _aw:
            _anime_hits = sum(1 for _aw_w in _aw if _is_aname(_aw_w))
            if _anime_hits == len(_aw):  # Tum kelimeler anime ismi → False
                return False
    except Exception:
        pass

    # ── content_detector Frekans Tabanli Kontrol ─────────────────────────────
    # score_text_romaji: > 0.70 → Romaji/JP (atla)
    # NOT: < 0.10 → True kismini KALDIRDIK — TR kelimeleri de dusuk romaji skoruna sahip
    try:
        from content_detector import score_text_romaji as _srom
        _rom_score, _rom_reason = _srom(clean)
        if _rom_score > 0.70:
            return False  # Romaji/Japonca, cevirme
    except Exception:
        pass

    # ── Turkce Frekans Kontrolu ──────────────────────────────────────────────
    # Eger kelimelerin cogunlugu GERCEKTEN Turkce ise → zaten cevrilmis.
    # KURAL: Yalnizca TR DB'de yuksek FAKAT EN DB'de DUSUK frekanslı kelimeler sayilir.
    # Bu sayede "game", "over", "look" gibi iki listede de olan kelimeler atlanir.
    _TR_EXCLUSIVE_SHORT = frozenset({
        # Saf Turkce, Ingilizce dictionary'sinde kesinlikle olmayan kisalar
        'bir','bu','ne','ve','da','mi','ki','ben','sen','biz','siz','onlar',
        'evet','hayir','tamam','ama','ile','icin','gibi','daha','cok',
        'var','yok','git','gel','dur','bak','bil','yap','sor','ver',
        'neden','nasil','nerede','nereye','simdi','sonra','once',
        'hadi','evet','tamam','belki','zaten','artik','sadece',
    })
    try:
        from content_detector import _tr_freq_score as _trf, _en_freq_score as _enf
        _all_words = re.findall(r"[a-zA-Z]+", clean)
        if _all_words:
            _tr_hits = 0
            for _w in _all_words:
                _wl = _w.lower()
                # Saf Turkce kisa kelimeler → kesin TR (Ingilizce'de bu anlamda kullanilmaz)
                if _wl in _TR_EXCLUSIVE_SHORT:
                    _tr_hits += 1
                # Uzun kelimeler: TR frekansi yuksek VE EN frekansi dusuk ise TR
                elif len(_w) >= 4:
                    _trs = _trf(_w)
                    _ens = _enf(_w)
                    # TR frekansi yuksek + EN frekansi yoksa veya cok dusuksa → TR kelimesi
                    if _trs >= 0.50 and _ens < 0.25:
                        _tr_hits += 1
            _tr_ratio = _tr_hits / len(_all_words)
            if _tr_ratio >= 0.40:  # Kelimelerin %40+ kesin Turkce → zaten cevrilmis
                return False
    except Exception:
        pass

    # ASCII alfabetik orani: %85+ ise Ingilizce
    total_alpha = sum(1 for c in clean if c.isalpha())
    ascii_alpha = sum(1 for c in clean if c.isascii() and c.isalpha())
    if total_alpha == 0:
        return False
    return (ascii_alpha / total_alpha) >= 0.85


def is_romaji_text(text):
    """
    Metnin Japonca romaji (sarkısozu, vb.) olup olmadigini tespit eder.
    Returns True  -> Romaji (atlanmali)
    Returns False -> Ingilizce veya baska -> CEVIR

    Strateji:
    1. 8+ kelime     -> asla romaji, cevir
    2. <3 kelime     -> belirsiz, cevir
    3. Ingilizce gram. kelimesi -> Ingilizce, cevir
    4. Guclu (3+harf) romaji ekleri yogunsa -> Romaji
    5. Guclu romaji + yuksek toplam yogunluk -> Romaji
    6. Japonca'ya has (non-English, non-overlap) kelimeler varsa -> Romaji
    """
    if not text or not text.strip():
        return False

    # === KAPSAMLI ROMAJI FILTRE (romaji_filter.py) ===
    # Cumle duzeyinde, 600+ sozluk + hece analizi ile calisir
    if _ROMAJI_FILTER_LOADED:
        return _is_romaji_sentence_v2(text)
    # === GERI DONUS: eski kelime tabanli mantik ===

    words = re.findall(r'[a-zA-Z]+', text.lower())
    if not words:
        return False

    # Kural 1: Uzun İngilizce cümle
    if len(words) >= 8:
        return False

    # Kural 2: Çok kısa
    if len(words) < 3:
        return False

    # Kural 3: İngilizce dilbilgisi kelimesi varsa → İngilizce cümle
    # "Ta... Take... ya!" → 'take' İngilizce'de var → False (çevir)
    # Dikkat: 'take' elin almasında "ta-ke" okunur ama İngilizce'de de kelime
    eng_count = sum(1 for w in words if w in _ENG_GRAMMAR)
    if eng_count >= 1:
        return False

    # Romaji eki eşleşmeleri
    romaji_matches = _ROMAJI_SUFFIXES.findall(text.lower())
    if not romaji_matches:
        return False

    total_ratio = len(romaji_matches) / max(len(words), 1)
    strong_romaji = [m for m in romaji_matches if len(m) >= 3 and m not in _ROMAJI_OVERLAP]
    strong_ratio = len(strong_romaji) / max(len(words), 1)

    # Kural 4: Güçlü (3+ harf) romaji ekleri yoğun → Japonca
    # Kural 5: Güçlü romaji VAR + toplam yoğunluk yüksek → Japonca
    # "kore wa nan desu ka": kore/nan/desu (strong) + wa/ka (overlap) → total=5/5=1.0
    if len(strong_romaji) >= 1 and total_ratio >= 0.50:
        return True

    # Kural 6: Japonca'ya özgü kelimeler (ne İngilizce ne overlap)
    # "suki da yo kimi no koto" → suki, kimi, koto İngilizce değil
    jp_specific = [w for w in words
                   if w not in _ENG_GRAMMAR
                   and w not in _ROMAJI_OVERLAP
                   and len(w) >= 3]
    if len(jp_specific) >= 1 and total_ratio >= 0.40:
        return True

    return False


def clean_brackets(text):
    # Remove content within () or [] if it contains Japanese or seems like meta info
    # 1. Remove standard JP parentheticals
    text = JP_PATTERN_NORMAL.sub('', text)
    text = JP_PATTERN_FULL.sub('', text)

    # 2. General Bracket Cleaner for comments (heuristic)
    # Strip [...] totally as it's usually meta/sound effects not needed or JP comments.
    text = re.sub(r'\[.*?\]', '', text)

    # 3. Strip parentheses containing credit keywords
    for kw in CREDIT_KEYWORDS:
        text = re.sub(r'\([^)]*?' + re.escape(kw) + r'.*?\)', '', text, flags=re.IGNORECASE)

    # 4. Clean extra spaces
    text = " ".join(text.split())
    return text

def is_credit_line(text: str, style_name: str = "", has_pos: bool = False,
                   word_count: int = 0, **kwargs) -> bool:
    """
    Kredi satiri tespit mekanizmasi DEVRE DISI.
    Yanlis pozitif (false-positive) nedeniyle kaldirildi.
    Her satir cevirilecek, hicbir sey silinmeyecek.
    """
    return False

def parse_ass_time(time_str):
    """ASS zaman formatını (h:mm:ss.cs) saniyeye çevirir"""
    try:
        parts = time_str.split(':')
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s
    except:
        return 0.0

def format_ass_time(seconds):
    """Saniyeyi ASS zaman formatına (h:mm:ss.cs) çevirir"""
    try:
        h = int(seconds // 3600)
        rem = seconds % 3600
        m = int(rem // 60)
        s = rem % 60
        return f"{h}:{m:02d}:{s:05.2f}"
    except:
        return "0:00:00.00"

def convert_srt_vtt_to_ass(lines, is_vtt=False):
    """
    SRT veya VTT formatındaki altyazıları ASS formatına çevirir.
    Returns: ASS format lines (list)
    """
    try:
        # ASS Header oluştur
        ass_lines = [
            "[Script Info]",
            "Title: Converted Subtitle",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "PlayResX: 1920",
            "PlayResY: 1080",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            "Style: Default,Arial,80,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]
        
        # SRT/VTT parse et
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # VTT header'ı atla
            if line.upper().startswith('WEBVTT') or line.upper().startswith('NOTE'):
                i += 1
                continue
            
            # Boş satırları atla
            if not line:
                i += 1
                continue
            
            # Sayı satırını atla (SRT için)
            if line.isdigit():
                i += 1
                if i >= len(lines):
                    break
                line = lines[i].strip()
            
            # Zaman satırını bul
            if '-->' in line:
                # Zamanları parse et
                time_parts = line.split('-->')
                if len(time_parts) != 2:
                    i += 1
                    continue
                
                start_time = time_parts[0].strip()
                end_time = time_parts[1].strip().split()[0]  # VTT'de position bilgisi olabilir
                
                # SRT/VTT formatını ASS formatına çevir
                def convert_time_to_ass(time_str):
                    """
                    SRT: 00:00:19,102 veya VTT: 00:00:19.102
                    ASS: 0:00:19.10
                    """
                    # Virgülü noktaya çevir (SRT için)
                    time_str = time_str.replace(',', '.')
                    
                    # Zamanı parçala: HH:MM:SS.mmm
                    try:
                        if '.' in time_str:
                            time_part, ms_part = time_str.split('.')
                        else:
                            time_part = time_str
                            ms_part = '00'
                        
                        # HH:MM:SS'i parçala
                        parts = time_part.split(':')
                        if len(parts) == 3:
                            h, m, s = parts
                        elif len(parts) == 2:
                            h = '0'
                            m, s = parts
                        else:
                            return time_str
                        
                        # Milisaniyeyi 2 haneye düşür (ASS formatı)
                        ms_part = ms_part[:2].ljust(2, '0')
                        
                        # Saat kısmındaki gereksiz sıfırları kaldır
                        h = str(int(h))
                        
                        # ASS formatı: h:mm:ss.cs (centiseconds)
                        return f"{h}:{m}:{s}.{ms_part}"
                    except:
                        return time_str
                
                start_time = convert_time_to_ass(start_time)
                end_time = convert_time_to_ass(end_time)
                
                # Metin satırlarını topla
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                    # Sayı satırını atla (bazen metin içinde numara olabilir)
                    if not lines[i].strip().isdigit():
                        text_lines.append(lines[i].strip())
                    i += 1
                
                if text_lines:
                    # Metni birleştir (\N ile)
                    text = '\\N'.join(text_lines)
                    
                    # <br> / <br /> taglarını ASS \N satır sonuna çevir (silme!)
                    text = re.sub(r'<br\s*/?>', r'\\N', text, flags=re.IGNORECASE)
                    # Art arda \N\N → tek \N
                    text = re.sub(r'(\\N){2,}', r'\\N', text)
                    # Kalan diger HTML taglerini temizle (<i>, <b>, <u> vs.)
                    text = re.sub(r'<(?!br)[^>]+>', '', text)
                    
                    # ASS dialogue satırı oluştur
                    dialogue = f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}"
                    ass_lines.append(dialogue)
            else:
                i += 1
        
        return ass_lines
        
    except Exception as e:
        print(f"{Fore.RED}   [!] Format dönüşüm hatası: {e}{Style.RESET_ALL}")
        return None

