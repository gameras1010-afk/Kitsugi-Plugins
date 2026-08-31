"""
tr_lang_detector.py — Türkçe Dil Tespit Modülü
================================================
Kaynaklar:
  - Wiktionary Turkish (63.8K kelime) — temiz sözlük
  - FrequencyWords corpus (2M+, frekans filtreli) — üst 300K
  - Türkçe özel karakterler (ğ,ş,ç,ö,ü,ı vb.)
  - Türkçe morfoloji: -in,-den,-da/-de,-ile,-için,-en,-an,-ler/-lar vb.

Kullanım:
  from tr_lang_detector import is_turkish, turkish_score
  if is_turkish("Benden uzak dur"):
      print("Türkçe!")
"""

import os, re, pickle

# ─── Yeni kütüphane entegrasyonları ───────────────────────────
# unicodedataplus: Unicode block analizi (TR vs JP karakter ayrımı)
try:
    import unicodedataplus as _udp
    _UDP_OK = True
except ImportError:
    import unicodedata as _udp  # stdlib fallback
    _UDP_OK = False

# lingua-py: Kısa metin için yüksek doğruluklu dil tespiti
try:
    from lingua import Language, LanguageDetectorBuilder
    _LINGUA_DETECTOR = (
        LanguageDetectorBuilder
        .from_languages(Language.TURKISH, Language.ENGLISH,
                        Language.JAPANESE, Language.KOREAN)
        .with_low_accuracy_mode()  # Hız için (kısa metin için yeterli)
        .build()
    )
    _LINGUA_OK = True
except Exception:
    _LINGUA_DETECTOR = None
    _LINGUA_OK = False

_BASE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────
# 1. Wiktionary kelime seti (63.8K — tam sözlük, güvenilir)
# ─────────────────────────────────────────────────────────────
_WIKI_SET: frozenset = frozenset()
_FREQ_SET: frozenset = frozenset()  # Frekans filtreli üst 300K
_LOADED = False

_WIKI_FILE = os.path.join(_BASE, 'tr_words_wiktionary.txt')
_FREQ_FILE = os.path.join(_BASE, 'tr_words_frequency.txt')
_PKL_FILE  = os.path.join(_BASE, 'tr_wordset_clean.pkl')

# Kesinlikle İngilizce olan yaygın kelimeler (corpus'tan çıkar)
_ENG_BLACKLIST = frozenset({
    'the','and','or','to','of','in','is','it','at','be','as','by',
    'we','he','she','they','you','me','my','i','a','an','on',
    'from','for','with','this','that','are','was','but','not',
    'have','has','had','will','what','how','when','who','why',
    'do','did','can','could','would','should','may','might',
    'all','one','two','if','so','up','out','get','go','see',
    'no','yes','ok','hi','hey','oh','wow','eh','ah','uh','mm',
    'clear','steer','born','into','from','love','life','time',
    'day','night','free','come','just','even','still','keep',
    'away','back','down','only','ever','year','long','feel',
    'know','take','make','like','give','tell','show','help',
    'live','want','need','ask','play','run','turn','stay',
    'end','start','stop','open','close','right','left','off',
    # Frekans corpus'unda bulunan İngilizce film/dizi kelimeleri
    'maybe','already','broken','world','heart','never','always',
    'together','beautiful','forever','nothing','everything','something',
    'remember','forget','dream','believe','moment','again','because',
    'really','little','people','always','every','please','sorry',
    'gonna','wanna','gotta','yeah','okay','hello','goodbye','baby',
    'your','their','them','these','those','here','there','where',
    'then','than','which','while','after','before','about','around',
    'think','thought','tried','trying','story','let','let',
    'over','under','same','last','next','new','old','true','false',
    'hold','find','look','call','walk','talk','move','feel',
    'way','world','place','face','hand','mind','soul','keep',
    'hurt','pain','hope','chance','light','dark','fire','star',
    'fight','fall','rise','stay','leave','hold','carry','lose',
    'win','hide','break','cut','catch','miss','wait','stand',
})

def _load():
    global _WIKI_SET, _FREQ_SET, _LOADED
    if _LOADED:
        return

    # Wiktionary (tam sözlük)
    if os.path.exists(_WIKI_FILE):
        with open(_WIKI_FILE, 'r', encoding='utf-8', errors='replace') as f:
            words = {l.strip().lower() for l in f if l.strip()}
        _WIKI_SET = frozenset(words - _ENG_BLACKLIST)

    # FrequencyWords (frekans filtrelemesi: en az 5 kez geçen)
    if os.path.exists(_FREQ_FILE):
        freq_words = set()
        with open(_FREQ_FILE, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    word = parts[0].lower()
                    try:
                        freq = int(parts[1])
                    except ValueError:
                        continue
                    # Frekans ≥ 5, 3+ karakter, İngilizce blacklist'te değil
                    if freq >= 5 and len(word) >= 3 and word not in _ENG_BLACKLIST:
                        freq_words.add(word)
        _FREQ_SET = frozenset(freq_words)

    # Cache'i kaydet
    combined = _WIKI_SET | _FREQ_SET
    try:
        with open(_PKL_FILE, 'wb') as f:
            pickle.dump((_WIKI_SET, _FREQ_SET), f, protocol=4)
    except Exception:
        pass

    _LOADED = True


# ─────────────────────────────────────────────────────────────
# 2. Türkçe özel karakter regex
# ─────────────────────────────────────────────────────────────

# Japonca (romaji) kelimeleri Turkce sanmamak icin

# ─── Unicode Block Analizi ─────────────────────────────────
# TR özel karakterleri: U+011F ğ, U+015F ş, U+00E7 ç vb.
# JP karakterleri: U+3040-U+30FF Hiragana/Katakana, U+4E00-U+9FFF CJK
_TR_UNICODE_BLOCKS = frozenset(range(0x011E, 0x0180))  # Latin Extended + TR
_JP_UNICODE_RANGES = [
    (0x3040, 0x30FF),   # Hiragana + Katakana
    (0x4E00, 0x9FFF),   # CJK Ideographs
    (0x3000, 0x303F),   # CJK Symbols
    (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth
]

def _has_jp_unicode(text: str) -> bool:
    """Türkçe olmayan Japonca/CJK Unicode karakteri var mı?"""
    for ch in text:
        cp = ord(ch)
        for lo, hi in _JP_UNICODE_RANGES:
            if lo <= cp <= hi:
                return True
    return False

def _count_tr_unicode_chars(text: str) -> int:
    """Kesinlikle Türkçe olan Unicode karakterlerin sayısı."""
    TR_SPECIFIC = set('ğşçöüıİĞŞÇÖÜ')
    return sum(1 for ch in text if ch in TR_SPECIFIC)

_JP_WORD_RE = __import__('re').compile(
    r'(nande|nani|nanka|naze|doko|dare|dozo|suki|kawaii|sugoi|'
    r'yokatta|arigatou|gomen|moshi|desu|masu|imasu|'
    r'watashi|boku|kimi|anata|anta|'
    r'hoshi|yume|kokoro|sakura|tsuki|hana|'
    r'senpai|kouhai|sensei|chan|kun|san|sama|'
    r'nee|naa|eto|ano)',
    __import__('re').IGNORECASE
)

_TR_CHARS_RE = re.compile(r'[ğşçöüıİĞŞÇÖÜ]')

# ─────────────────────────────────────────────────────────────
# 3. Türkçe morfolojik sonekler (güçlü göstergeler)
# ─────────────────────────────────────────────────────────────
# Uzun, belirsizliği az Türkçe ekleri
_TR_STRONG_SUFFIX = re.compile(
    r'(?:den|dan|deki|daki|teki|taki|nın|nin|nun|nün|'
    r'ların|lerin|ların|lerin|ları|leri|larım|lerim|'
    r'ıyor|iyor|uyor|üyor|acak|ecek|maktadır|mektedir|'
    r'masını|mesini|madan|meden|abilir|ebilir|abilmek|'
    r'dığında|diğinde|duğunda|düğünde|'
    r'sinden|sından|sinden|sundan|sünden|'
    r'ndan|nden|nda|nde|nla|nle|'
    r'ydım|ydın|ydı|ydık|ydınız|ydılar|'
    r'miş|mış|muş|müş|'
    r'ken|iken|ile|için|kadar|göre|karşı|rağmen|'
    # ASCII versiyonlar (özel karakter olmadan yazilmis)
    r'yorum|yorsun|yoruz|yorlar|yordu|yordum|'
    r'ecegim|eceksin|ecekler|acagim|acaksin|'
    r'iyorum|iyordu|iyorduk|'
    r'meli|meliyim|melisin|'
    r'seviyorum|biliyorum|gordum|geldim|istiyorum|'
    r'yapiyorum|anliyorum|dusunuyorum)$',
    re.IGNORECASE
)

# Kısa ama net Türkçe cümle yapıları
_TR_PHRASE_RE = re.compile(
    r'\b(?:ve|ile|bir|bu|şu|o|ben|sen|biz|siz|onlar|'
    r'benden|bana|senden|sana|onu|bunu|şunu|seni|beni|'
    r'evet|hayır|tamam|dur|git|gel|bak|var|yok|ne|kim|'
    r'gibi|daha|çok|az|en|hiç|her|bazı|birçok|tüm|'
    r'ama|fakat|lakin|veya|ya|ya da|hem|değil|ancak)\b',
    re.IGNORECASE
)


def _tokenize(text: str):
    return re.findall(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]+', text.lower())


def turkish_score(text: str) -> float:
    """
    Metnin Türkçe olma skorunu döndürür (0.0 – 1.0).
    0.4+ → muhtemelen Türkçe
    0.65+ → kesinlikle Türkçe
    """
    if not text or not text.strip():
        return 0.0

    _load()

    text_clean = text.strip()
    score = 0.0

    # [PRE-KONTROL 1] JP/CJK Unicode karakter tespiti (unicodedataplus)
    if '_has_jp_unicode' in dir() and _has_jp_unicode(text_clean):
        return 0.0  # Hiragana/Katakana/CJK → kesinlikle Türkçe değil

    # [PRE-KONTROL 2] JP kelime yoğunluğu → erken çık
    words_pre = re.findall(r'[a-zA-Z\u011f\u015f\u00e7\u00f6\u00fc\u0131]+', text_clean.lower())
    if words_pre and _JP_WORD_RE:
        jp_hits = sum(1 for w in words_pre if _JP_WORD_RE.fullmatch(w))
        if jp_hits >= 2 or (jp_hits >= 1 and len(words_pre) <= 4):
            return 0.0  # JP metin — kesinlikle TR değil

    # Katman 1: Türkçe özel karakter var mı?
    tr_char_count = len(_TR_CHARS_RE.findall(text_clean))
    if tr_char_count >= 2:
        score += 0.60
    elif tr_char_count == 1:
        score += 0.35

    # Katman 2: Türkçe morfoloji
    words = _tokenize(text_clean)
    if not words:
        return 0.0

    suffix_hits = sum(1 for w in words if _TR_STRONG_SUFFIX.search(w))
    if suffix_hits >= 2:
        score += 0.45
    elif suffix_hits == 1:
        score += 0.25

    # Katman 3: Türkçe cümle kalıpları
    phrase_hits = len(_TR_PHRASE_RE.findall(text_clean))
    if phrase_hits >= 3:
        score += 0.40
    elif phrase_hits >= 1:
        score += 0.20 * phrase_hits

    # Katman 4: Wiktionary (sözlük)
    wiki_hits = sum(1 for w in words if w in _WIKI_SET)
    wiki_ratio = wiki_hits / max(len(words), 1)
    if wiki_ratio >= 0.70:
        score += 0.50
    elif wiki_ratio >= 0.45:
        score += 0.30
    elif wiki_ratio >= 0.20:
        score += 0.12

    # Katman 5: FrequencyWords (corpus)
    # Dikkat: corpus'ta İngilizce kelimeler de olabilir.
    # Sadece Türkçe özel karakter YOKSA daha düşük ağırlık ver.
    freq_hits = sum(1 for w in words if w in _FREQ_SET and w not in _ENG_BLACKLIST)
    freq_ratio = freq_hits / max(len(words), 1)
    has_tr_chars = tr_char_count > 0
    if has_tr_chars:
        # Türkçe karakter varsa corpus hit'lerine güven
        if freq_ratio >= 0.65:
            score += 0.40
        elif freq_ratio >= 0.40:
            score += 0.20
    else:
        # Türkçe karakter YOK → corpus'a çok düşük ağırlık (false positive önleme)
        if freq_ratio >= 0.80:
            score += 0.15  # Sadece çok yüksek oran olduğunda minimal katkı

    # Katman 6: Türkçe karaktersiz ama yüksek corpus hit → penaltı
    # "Or maybe already broken" gibi saf İngilizce metinleri yakala
    if not has_tr_chars and suffix_hits == 0 and phrase_hits == 0 and wiki_hits == 0:
        # Hiçbir güçlü TR göstergesi yok — skor düşür
        score = max(0.0, score - 0.30)

    # Katman 7 (YENİ): lingua-py kısa metin tespiti
    # Sadece belirsiz metinlerde (score 0.1-0.6 arası, kısa metin)
    # ve lingua kuruluysa devreye gir
    if _LINGUA_OK and _LINGUA_DETECTOR and 5 <= len(text_clean) <= 40:
        if 0.05 <= score <= 0.65:  # Belirsiz bölge — lingua'ya sor
            try:
                _lingua_lang = _LINGUA_DETECTOR.detect_language_of(text_clean)
                if _lingua_lang == Language.TURKISH:
                    score = max(score, 0.55)  # TR boost
                elif _lingua_lang == Language.ENGLISH:
                    score = min(score, 0.15)  # EN penaltı
                elif _lingua_lang in (Language.JAPANESE, Language.KOREAN):
                    score = 0.0  # JP/KR → kesinlikle TR değil
            except Exception:
                pass  # lingua başarısız → mevcut score koru

    return min(score, 1.0)


def is_turkish(text: str, threshold: float = 0.25) -> bool:
    """
    Metnin Türkçe olup olmadığını döndürür.
    threshold=0.28 → hassas (daha az yanlış negatif, özel karsiz TR yakalar)
    threshold=0.45 → katı (daha az yanlış pozitif)
    """
    return turkish_score(text) >= threshold


def is_turkish_verbose(text: str, threshold: float = 0.25):
    """(is_turkish, score) döndürür — debug için."""
    _load()
    score = turkish_score(text)
    return score >= threshold, round(score, 3)


# ─────────────────────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _load()
    print(f"Wiktionary: {len(_WIKI_SET):,} kelime")
    print(f"FreqCorpus: {len(_FREQ_SET):,} kelime (freq≥5)")
    print()

    TESTS = [
        # Türkçe (özel karakter YOK ama Türkçe)
        ("Benden uzak dur",          True,  "TR özel kar.sız"),
        ("Bana dokunma!",            True,  "TR özel kar.sız"),
        ("Zaten onu biliyorum",      True,  "TR normal"),
        ("Evet, tamam, git",         True,  "TR kısa"),
        ("Seninle konuşmak istiyorum", True,"TR morfoloji"),
        ("Bu dünyaya geldim",        True,  "TR özel kar.lı"),
        # Kesin Türkçe
        ("Seni çok özledim",         True,  "TR özledim"),
        ("Ne zaman geleceksin?",     True,  "TR geleceksin"),
        # İngilizce
        ("Steer clear from me",      False, "EN şarkı"),
        ("Or maybe already broken",  False, "EN şarkı"),
        ("Born into this world",     False, "EN şarkı"),
        ("Don't touch me",           False, "EN apostrophe"),
        ("Even if I grow weary",     False, "EN uzun"),
        ("No one else only you",     False, "EN kısa"),
        ("Is what love truly is",    False, "EN şiir"),
    ]

    ok = 0; fail = 0
    for text, expected, desc in TESTS:
        result, score = is_turkish_verbose(text)
        mark = "OK" if result == expected else "FAIL"
        if result == expected: ok += 1
        else: fail += 1
        print(f"  [{mark}] {text:40s} → {'TR' if result else 'EN'} ({score:.2f}) — {desc}")

    print(f"\n  Sonuç: {ok}/{ok+fail} OK | FAIL: {fail}")
