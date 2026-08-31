"""
romaji_detector.py
==================
Japoncadan Latin harfleriyle yazılmış (romaji) heceleri İngilizce kelimelerden
kesin olarak ayırt eden dedektör modülü.

Kullanım:
    from romaji_detector import is_romaji, score_romaji, classify_kara_group

Strateji (4 katman):
  1. Tam romaji hece eşleştirme    — Bilinen tüm Japonca romaji heceleri
  2. Fonotaktik kurallara uyum     — CV, CCV, V yapısına uyuyor mu?
  3. İngilizce kelime listesi      — Kesin İngilizce mı?
  4. Grup analizi                  — Birleşik metin oranı + bağlam
"""

import re

# ── unicodedataplus: CJK/Hiragana/Katakana block tespiti ─────────────────────
try:
    import unicodedataplus as _udp_rom
    _UDP_ROM_OK = True
except ImportError:
    import unicodedata as _udp_rom
    _UDP_ROM_OK = False

# ── fugashi: Japonca morfoloji analizi ───────────────────────────────────────
try:
    import fugashi
    _FUGASHI_TAGGER = fugashi.Tagger()
    _FUGASHI_OK = True
except Exception:
    _FUGASHI_TAGGER = None
    _FUGASHI_OK = False

_CJK_RANGES = [(0x3040, 0x30FF), (0x4E00, 0x9FFF), (0xFF00, 0xFFEF)]

def _has_cjk_chars(text: str) -> bool:
    """Metinde Japonca/Çince/Korece karakter var mı?"""
    for ch in text:
        cp = ord(ch)
        for lo, hi in _CJK_RANGES:
            if lo <= cp <= hi:
                return True
    return False
from typing import List, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 1. TAM ROMAJI HECE LİSTESİ (Hepburn sistemi + varyantlar)
#    Kaynak: Hepburn romanization, Kunrei-shiki, Nihon-shiki
# ─────────────────────────────────────────────────────────────────────────────

# Tek vokal
_VOWELS = {'a', 'i', 'u', 'e', 'o'}

# Uzatma
_LONG_VOWELS = {'aa', 'ii', 'uu', 'ee', 'oo', 'ou'}

# Temel CV heceleri (150+ adet)
_ROMAJI_SYLLABLES = {
    # ── A satırı ──
    'a', 'i', 'u', 'e', 'o',
    # ── K satırı ──
    'ka', 'ki', 'ku', 'ke', 'ko',
    'kya', 'kyu', 'kyo',
    # ── S satırı ──
    'sa', 'shi', 'si', 'su', 'se', 'so',
    'sha', 'shu', 'she', 'sho', 'syi',
    # ── T satırı ──
    'ta', 'chi', 'ti', 'tsu', 'tsi', 'te', 'to',
    'cha', 'chu', 'che', 'cho', 'tchi', 'ttsu',
    # ── N satırı ──
    'na', 'ni', 'nu', 'ne', 'no',
    'nya', 'nyu', 'nyo',
    # ── H satırı ──
    'ha', 'hi', 'fu', 'hu', 'he', 'ho',
    'hya', 'hyu', 'hyo',
    # ── M satırı ──
    'ma', 'mi', 'mu', 'me', 'mo',
    'mya', 'myu', 'myo',
    # ── Y satırı ──
    'ya', 'yu', 'yo',
    # ── R satırı ──
    'ra', 'ri', 'ru', 're', 'ro',
    'rya', 'ryu', 'ryo',
    # ── W satırı ──
    'wa', 'wi', 'we', 'wo',
    # ── G satırı (daku-on) ──
    'ga', 'gi', 'gu', 'ge', 'go',
    'gya', 'gyu', 'gyo',
    # ── Z satırı ──
    'za', 'ji', 'zi', 'zu', 'ze', 'zo',
    'ja', 'ju', 'jo', 'jya', 'jya', 'jyu', 'jyo',
    # ── D satırı ──
    'da', 'di', 'du', 'de', 'do',
    'dya', 'dyu', 'dyo',
    # ── B satırı ──
    'ba', 'bi', 'bu', 'be', 'bo',
    'bya', 'byu', 'byo',
    # ── P satırı ──
    'pa', 'pi', 'pu', 'pe', 'po',
    'pya', 'pyu', 'pyo',
    # ── N (özel, tek başına) ──
    'n', 'nn',
    # ── Çift ünsüz (geminate) ──
    'kk', 'ss', 'tt', 'pp', 'cc',
    # ── Uzun vokal ──
    'aa', 'ii', 'uu', 'ee', 'oo', 'ou',
    # ── Ekstra / yaygın ──
    'tsu', 'chi', 'shi', 'sha', 'sho', 'shu',
    'tte', 'tta', 'tto', 'sse', 'ssa',
    'tte', 'kke', 'ppe', 'bbe', 'nne',
    # ── Katakana borrowed sounds ──
    'fa', 'fi', 'fe', 'fo',
    'va', 'vi', 'vu', 've', 'vo',
    'tsa', 'tse', 'tso',
    'che', 'je',
    'di', 'du', 'tu', 'ti',
    # ── Tek karakter heceleri ──
    'A', 'I', 'U', 'E', 'O', 'N',
    # ── Kısaltılmış / romaji-like ──
    'nai', 'nee', 'nao',
    'sou', 'dou', 'kou', 'tou', 'nou', 'rou', 'mou',
    'iru', 'aru', 'oru',
    'mono', 'koto',
    # ── Sık karşılaşılan birleşimler ──
    'shi', 'chi', 'tsu', 'sha', 'shu', 'sho',
    'cha', 'cho', 'chu', 'nya', 'nyu', 'nyo',
    'mat', 'mas', 'tten', 'tte',
    'mau', 'iau', 'dau',
    'arui', 'sore', 'kore', 'dare', 'nani',
    'mada', 'mite', 'kite', 'shite',
    'demo', 'demo', 'kara', 'made', 'tara',
    'zut', 'zutto',
    'ita', 'ite', 'itta',
    'kan', 'tan', 'ran', 'nan', 'ban', 'man', 'pan',
    'kin', 'tin', 'rin', 'nin', 'bin', 'min', 'pin',
    'tei', 'sei', 'kei', 'hei', 'rei', 'bei', 'mei',
    'kai', 'sai', 'tai', 'nai', 'bai', 'mai', 'pai',
    'rai', 'wai',
    'zon', 'kon', 'ton', 'non', 'bon', 'mon', 'pon',
    'sun', 'run', 'mun', 'nun', 'bun', 'pun', 'kun', 'gun',
    'sho', 'shou',
    'Nee',  # "nee" = ねえ (hey)
    'Boku', 'boku',
    'Kimi', 'kimi',
    'Mite', 'mite',
    'Suki', 'suki',
    'Doko', 'doko',
    'Nani', 'nani',
    'shite', 'shita',
    'waite', 'aite',
}
# Küçük harf normalize edilmiş set
_ROMAJI_LOWER = {s.lower() for s in _ROMAJI_SYLLABLES}

# ─────────────────────────────────────────────────────────────────────────────
# 2. JAPONCA FONOTAKTİK REGEX
#    Japonca romaji: V, CV, CCV (shi, chi, tsu), N sonu, geminatlar
# ─────────────────────────────────────────────────────────────────────────────
_JP_PHONOTACTIC = re.compile(
    r'^(?:'
    # Özel heceler
    r'tsu|chi|shi|sha|shu|sho|cha|cho|chu|'
    r'nya|nyu|nyo|mya|myu|myo|rya|ryu|ryo|'
    r'hya|hyu|hyo|bya|byu|byo|pya|pyu|pyo|'
    r'kya|kyu|kyo|gya|gyu|gyo|'
    r'ja|ji|ju|jo|jya|jyu|jyo|'
    # Çift ünsüz (geminate)
    r'[kstpbmnh]{2}|'
    # CCV (özel + vokal)
    r'[kstpbmndghrzwfy][aeiou]|'
    # Tek vokal
    r'[aeiou]|'
    # n özel
    r'n(?![aeiou])|nn|'
    # 3 harfli (mat, rai, kan vb.)
    r'[kstpbmndhrzwfy][aeiou][tnrs]?|'
    # Uzun vokal
    r'(?:aa|ii|uu|ee|oo|ou)'
    r')+$',
    re.IGNORECASE
)

# ─────────────────────────────────────────────────────────────────────────────
# 3. KESİN İNGİLİZCE KELİME LİSTESİ
#    Romaji ile karışabilecek kısa İngilizce kelimeler dahil edildi
# ─────────────────────────────────────────────────────────────────────────────
_ENGLISH_WORDS = {
    # Çok sık, tartışmalı (no, to, me, be, ne, na, ha)
    # bunlar romaji DE olabilir ama İngilizce'de de var
    # → Bu listeye SADECE kesin İngilizce olanlar girer
    # Kısa ama kesin İngilizce
    'the', 'and', 'but', 'for', 'are', 'not', 'can',
    'did', 'was', 'has', 'have', 'this', 'that', 'with',
    'from', 'they', 'been', 'will', 'what', 'when', 'where',
    'how', 'why', 'who', 'him', 'his', 'her', 'its',
    'our', 'your', 'you', 'we', 'he', 'she', 'it',
    'all', 'any', 'one', 'two', 'may', 'let', 'put',
    'get', 'got', 'set', 'say', 'see', 'off', 'out',
    'own', 'new', 'old', 'big', 'few', 'far', 'too',
    'yet', 'nor', 'then', 'than', 'even', 'just', 'only',
    'over', 'after', 'into', 'also', 'more', 'most',
    'such', 'same', 'still', 'back', 'next', 'last',
    'well', 'keep', 'know', 'want', 'come', 'here',
    'tell', 'feel', 'find', 'give', 'look', 'make',
    'take', 'turn', 'walk', 'work', 'live', 'love',
    'move', 'need', 'play', 'show', 'stop', 'stay',
    'wait', 'walk', 'down', 'left', 'right', 'time',
    'away', 'call', 'hold', 'went', 'goes', 'said',
    'like', 'made', 'much', 'long', 'hand', 'part',
    'face', 'hear', 'them', 'very', 'some', 'days',
    'help', 'hope', 'home', 'life', 'real', 'true',
    'does', 'done', 'able', 'once', 'ever', 'else',
    'kind', 'mind', 'side', 'door', 'eyes', 'head',
    'heart', 'night', 'light', 'might', 'again', 'never',
    'always', 'every', 'anoth', 'these', 'those', 'their',
    # Romaji ile karışan ama sabit İngilizce:
    'mine', 'fine', 'line', 'wine', 'pine', 'nine', 'vine',
    'born', 'corn', 'horn', 'torn', 'worn', 'fore', 'more',
    'core', 'bore', 'lore', 'sore', 'wore', 'broke', 'steer',
    'clear', 'maybe', 'already', 'broken', 'touch', 'karma',
    'pray', 'serenade', 'punish', 'believe', 'implore',
    'frozen', 'unmoving', 'anchored', 'betrayal', 'secrets',
    # "Born", "Don't" vb. cümle başları
    'born', "don't", "isn't", "wasn't", "i'm", "i'll", "i've",
    "you're", "we're", "they're", "it's", "that's", "who's",
}
_ENGLISH_LOWER = {w.lower().strip("'\".,!?") for w in _ENGLISH_WORDS}

# ─────────────────────────────────────────────────────────────────────────────
# 4. STYLE NAME BASED OVERRIDE
# ─────────────────────────────────────────────────────────────────────────────
_STYLE_ROM_RE  = re.compile(r'(?:^|[^a-zA-Z])(?:rom?|romaji|ro)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_STYLE_JP_RE   = re.compile(r'(?:^|[^a-zA-Z])(?:JP|JPN|japanese|nihon)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_STYLE_ENG_RE  = re.compile(r'(?:^|[^a-zA-Z])(?:EN|ENG|ENGLISH)(?:[^a-zA-Z]|$)', re.IGNORECASE)
_STYLE_KARA_RE = re.compile(r'kara(?:oke)?', re.IGNORECASE)


def style_is_definitely_romaji(style_name: str) -> bool:
    """Stil adı kesin romaji mi?"""
    return bool(_STYLE_ROM_RE.search(style_name) or _STYLE_JP_RE.search(style_name))


def style_is_definitely_english(style_name: str) -> bool:
    """Stil adı kesin İngilizce şarkı mı?"""
    return bool(_STYLE_ENG_RE.search(style_name))


# ─────────────────────────────────────────────────────────────────────────────
# 5. TEMEL HECE ANALİZİ
# ─────────────────────────────────────────────────────────────────────────────

def score_syllable(syl: str) -> Tuple[float, str]:
    """
    Tek bir heceyi analiz eder.
    Returns: (romaji_score 0.0–1.0, reason)
      1.0 = kesinlikle romaji
      0.0 = kesinlikle İngilizce
      0.5 = belirsiz
    """
    s = syl.strip().lower()
    if not s:
        return 0.5, 'empty'

    # Kesin İngilizce kelimesi mi?
    if s in _ENGLISH_LOWER:
        # ama romaji olarak da tanınan kısa kelimeler → skor düşük ama 0 değil
        if s in _ROMAJI_LOWER:
            return 0.4, 'both_eng_and_romaji'
        return 0.0, 'english_word'

    # Kesin romaji listesinde mi?
    if s in _ROMAJI_LOWER:
        return 1.0, 'known_romaji'

    # Fonotaktik uyum
    if _JP_PHONOTACTIC.match(s):
        return 0.85, 'phonotactic_match'

    # Tamamen Latin ama kısa (1-3 harf) → muhtemelen romaji
    if re.match(r'^[a-z]{1,3}$', s):
        return 0.7, 'short_latin'

    # Büyük harf ile başlıyor (cümle başı İngilizce)
    if syl[0].isupper() and len(s) > 3:
        return 0.2, 'capitalized_long'

    # 4+ harf, seslisiz ünsüz kümesi (İngilizce karakteristik)
    consonant_cluster = re.search(r'[bcdfghjklmnpqrstvwxyz]{3,}', s)
    if consonant_cluster:
        return 0.1, 'consonant_cluster'

    return 0.5, 'uncertain'


def score_romaji(syllables: List[str]) -> float:
    """
    Hece listesi için genel romaji skoru hesapla.
    Returns: 0.0 (kesin İngilizce) → 1.0 (kesin romaji)
    """
    if not syllables:
        return 0.5

    scores = [score_syllable(s)[0] for s in syllables if s.strip()]
    if not scores:
        return 0.5

    return sum(scores) / len(scores)


def is_romaji(syllables: List[str], threshold: float = 0.65) -> bool:
    """
    Hece listesinin romaji olup olmadığını belirle.
    threshold: bu değerin üzerindeki ortalama skor = romaji
    """
    return score_romaji(syllables) >= threshold


# ─────────────────────────────────────────────────────────────────────────────
# 6. GRUP ANALİZİ (birleşik metin + bağlam)
# ─────────────────────────────────────────────────────────────────────────────

_ENG_WORD_RE   = re.compile(r'\b(?:the|and|but|for|are|not|with|this|that|from|have|been|will|what|when|where|how|why|who|clear|steer|maybe|already|broken|touch|born|don|touch)\b', re.IGNORECASE)
_APOSTROPHE_RE = re.compile(r"[a-z]'[a-z]", re.IGNORECASE)  # don't, i've, it's


def classify_kara_group(
    syllables: List[str],
    style_name: str = '',
    merged_text: str = '',
) -> Tuple[str, float, str]:
    """
    Karaoke hece grubunu sınıflandır.

    Args:
        syllables:   Bireysel hece/kelime listesi
        style_name:  ASS stil adı (bonus bilgi)
        merged_text: Zaten birleştirilmişse (opsiyonel)

    Returns:
        (label, confidence, reason)
        label: 'romaji' | 'english' | 'uncertain'
        confidence: 0.0–1.0
        reason: açıklama string'i
    """
    # 1. Stil adından kesin karar
    if style_is_definitely_romaji(style_name):
        return ('romaji', 1.0, f'style_name:{style_name}')
    if style_is_definitely_english(style_name):
        return ('english', 1.0, f'style_name:{style_name}')

    # 2. Birleşik metin analizi
    merged = merged_text or ' '.join(s.strip() for s in syllables if s.strip())

    # İngilizce apostrophe (don't, i've) → kesin İngilizce
    if _APOSTROPHE_RE.search(merged):
        return ('english', 0.95, "apostrophe_in_merged")

    # Bilinen İngilizce kelime kalıpları
    eng_matches = _ENG_WORD_RE.findall(merged)
    if len(eng_matches) >= 2:
        return ('english', 0.9, f"eng_words:{eng_matches[:3]}")

    # 3. Hece bazlı skor
    rom_score = score_romaji(syllables)
    detail = [(s, score_syllable(s)) for s in syllables[:6]]

    # 4. Ortalama hece uzunluğu
    avg_len = sum(len(s.strip()) for s in syllables) / max(len(syllables), 1)

    # Romaji heceleri genelde 1-3 harf
    if avg_len <= 3.0 and rom_score >= 0.65:
        return ('romaji', rom_score, f'avg_len={avg_len:.1f} score={rom_score:.2f}')

    # Uzun hecelerde İngilizce eğilimi
    if avg_len >= 5.0 and rom_score < 0.5:
        return ('english', 1.0 - rom_score, f'avg_len={avg_len:.1f} score={rom_score:.2f}')

    # Belirsiz bölge
    if rom_score >= 0.65:
        return ('romaji', rom_score, f'score_only={rom_score:.2f}')
    elif rom_score <= 0.35:
        return ('english', 1.0 - rom_score, f'score_only={rom_score:.2f}')
    else:
        return ('uncertain', 0.5, f'ambiguous={rom_score:.2f}')


# ─────────────────────────────────────────────────────────────────────────────
# 7. KARAOKESİZ TEK SATIR ANALİZİ (full-line stil)
# ─────────────────────────────────────────────────────────────────────────────

def classify_full_line(text: str, style_name: str = '') -> Tuple[str, float, str]:
    """
    Tam bir metin satırının romaji mi İngilizce mi olduğunu belirle.
    Tek kelimelik veya çok kelimelik satırlar için.
    """
    if style_is_definitely_romaji(style_name):
        return ('romaji', 1.0, f'style:{style_name}')
    if style_is_definitely_english(style_name):
        return ('english', 1.0, f'style:{style_name}')

    words = text.strip().split()
    if not words:
        return ('uncertain', 0.5, 'empty')

    # Apostrophe = İngilizce
    if _APOSTROPHE_RE.search(text):
        return ('english', 0.95, 'apostrophe')

    # İngilizce kelime yoğunluğu
    eng_matches = _ENG_WORD_RE.findall(text)
    if len(words) >= 3 and len(eng_matches) >= 1:
        ratio = len(eng_matches) / len(words)
        if ratio >= 0.3:
            return ('english', 0.8 + ratio * 0.2, f'eng_ratio={ratio:.2f}')

    # Hece skoru
    return classify_kara_group(words, style_name, text)


# ─────────────────────────────────────────────────────────────────────────────
# 8. KARMA SATIR BÖLME — Romaji + İngilizce aynı satırda
#
#    "Sekai wa utsukushii The world is beautiful"
#      → [('romaji','Sekai wa utsukushii'), ('english','The world is beautiful')]
#
#    Kullanım:
#      from romaji_detector import split_mixed_line, join_mixed_segments
#      segs = split_mixed_line(text)
#      # → [('romaji', ...), ('english', ...)]
#      translated_eng = translate(' '.join(t for l,t in segs if l=='english'))
#      result = join_mixed_segments(segs, translated_eng)
# ─────────────────────────────────────────────────────────────────────────────

def split_mixed_line(
    text: str,
    style_name: str = '',
    window: int = 3,
    rom_thresh: float = 0.60,
    eng_thresh: float = 0.35,
) -> list:
    """
    Karışık romaji+İngilizce satırı segmentlere böler.

    Her kelimeyi bağlamsal bir pencere (window) içinde skorlar,
    ardından ardışık aynı etiketli kelimeleri birleştirir.

    Returns:
        [(lang, text), ...]
        lang: 'romaji' | 'english' | 'uncertain'
    """
    words = text.strip().split()
    if not words:
        return [('uncertain', text)]

    # Tüm satır tek dilde mi? → hızlı yol
    quick = classify_full_line(text, style_name)
    if quick[0] != 'uncertain' and quick[1] >= 0.85:
        # Kesin karar → segmentlere gerek yok
        return [(quick[0], text)]

    # Kelime başına skor
    word_labels = []
    for idx, word in enumerate(words):
        # Bağlamsal pencere: kendisi + komşular
        lo = max(0, idx - window // 2)
        hi = min(len(words), idx + window // 2 + 1)
        ctx_words = words[lo:hi]
        ctx_text  = ' '.join(ctx_words)

        sc = score_romaji(ctx_words)
        # Apostrophe → kesin İngilizce
        if _APOSTROPHE_RE.search(word):
            label = 'english'
        # Kesin İngilizce kelime listesi
        elif word.rstrip("'\".,!?;:").lower() in _ENGLISH_LOWER and word.rstrip("'\".,!?;:").lower() not in _ROMAJI_LOWER:
            label = 'english'
        # Kesin romaji hece listesi (tek kelime, kısa)
        elif word.lower() in _ROMAJI_LOWER and len(word) <= 5:
            label = 'romaji'
        elif sc >= rom_thresh:
            label = 'romaji'
        elif sc <= eng_thresh:
            label = 'english'
        else:
            # Belirsiz → komşu etikete bak (smooth later)
            label = 'uncertain'
        word_labels.append((word, label, sc))

    # Belirsiz kelimeleri en yakın kesin etikete göre düzelt
    labels = [l for _, l, _ in word_labels]
    for i in range(len(labels)):
        if labels[i] == 'uncertain':
            # Önce sağa bak
            for j in range(i + 1, min(i + 4, len(labels))):
                if labels[j] != 'uncertain':
                    labels[i] = labels[j]
                    break
            # Hâlâ belirsizse sola bak
            if labels[i] == 'uncertain':
                for j in range(i - 1, max(i - 4, -1), -1):
                    if labels[j] != 'uncertain':
                        labels[i] = labels[j]
                        break
            if labels[i] == 'uncertain':
                labels[i] = 'english'  # fallback

    # Ardışık aynı etiketlileri grupla
    segments = []
    cur_label = labels[0]
    cur_words = [words[0]]
    for i in range(1, len(words)):
        if labels[i] == cur_label:
            cur_words.append(words[i])
        else:
            segments.append((cur_label, ' '.join(cur_words)))
            cur_label = labels[i]
            cur_words = [words[i]]
    segments.append((cur_label, ' '.join(cur_words)))

    return segments


def join_mixed_segments(
    segments: list,
    translated_english: str,
) -> str:
    """
    split_mixed_line() sonucunu çevrilmiş İngilizce ile birleştirir.

    Args:
        segments:           split_mixed_line() çıktısı
        translated_english: API'den gelen Türkçe metin
                            (sadece İngilizce segmentlerin çevirisi)

    Returns:
        Tam satır: romaji olduğu yerde + Türkçe çeviri

    Örnek:
        segs = [('romaji','Sekai wa'), ('english','The world')]
        join_mixed_segments(segs, 'Bu dünya') → 'Sekai wa Bu dünya'
    """
    # İngilizce segment sayısı
    eng_segs = [t for l, t in segments if l == 'english']
    if not eng_segs:
        return ' '.join(t for _, t in segments)

    # Birden fazla İngilizce segment varsa → tek çeviriyi orantılı böl
    # (genellikle 1 veya 2 İngilizce blok olur)
    tr_parts = translated_english.strip().split(' / ')
    if len(tr_parts) < len(eng_segs):
        # Yeterli bölüm yoksa: tüm çeviriyi tek parça olarak kullan
        tr_parts = [translated_english.strip()] * len(eng_segs)

    tr_iter = iter(tr_parts)
    result_parts = []
    for lang, text in segments:
        if lang == 'english':
            result_parts.append(next(tr_iter, text))
        else:
            result_parts.append(text)

    return ' '.join(result_parts)


# ─────────────────────────────────────────────────────────────────────────────
# SELF TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 65)
    print("  ROMAJI DEDEKTÖR TEST")
    print("=" * 65)

    # Hece grupları testi
    test_groups = [
        # (syllables, style, expected, description)
        (['U', 'ma', 're', 'te', 'shi', 'mat', 'ta'],   'ED1-JP-ButDark', 'romaji', 'Japonca romaji heceleri'),
        (['Nee', 'zut', 'to', 'zut', 'to', 'so', 'ba'], 'ED1-JP',        'romaji', 'Japonca ねえ ずっと そば'),
        (['shi', 'mat', 'Arui', 'shi'],                  'ED1-JP',        'romaji', 'Romaji karışık'),
        (['Steer', 'clear', 'from', 'me'],               'OP1 - ENG',     'english', 'İngilizce açık şarkı'),
        (['Or', 'maybe', 'already', 'broken'],           'ED1-EN',        'english', 'İngilizce 4 kelime'),
        (['Born', 'into', 'this'],                       'ED1-EN',        'english', 'İngilizce kısa'),
        (['Don', "touch", 'me'],                         'ED1-EN',        'english', 'İngilizce short'),
        (['No', 'one', 'else'],                          'ED1-EN',        'english', 'İngilizce ambiguous'),
        (['ka', 'ra', 'no', 'ko', 'ro'],                 'ED1-JP',        'romaji', 'Türkçe/Japonca benzer'),
        (['ma', 'su', 'mi', 'ta'],                       'ED1-JP',        'romaji', 'Japonca fiil çekimi'),
    ]

    ok = 0; fail = 0
    for syls, sty, expected, desc in test_groups:
        label, conf, reason = classify_kara_group(syls, sty)
        status = 'OK' if label == expected else 'FAIL'
        if status == 'OK': ok += 1
        else: fail += 1
        merged = ' '.join(syls)
        print(f"\n  [{status}] {desc}")
        print(f"    Stil  : {sty}")
        print(f"    Heceler: {syls}")
        print(f"    Sonuç : {label} ({conf:.2f}) — {reason}")
        print(f"    Beklenen: {expected}")

    print(f"\n{'='*65}")
    print(f"  Sonuç: {ok}/{ok+fail} OK  |  FAIL: {fail}")
    print("=" * 65)

    # Full-line testi
    print("\n[Full-line testi]")
    full_tests = [
        ('Steer clear from me', 'OP1 - ENG', 'english'),
        ('No one else', 'ED1-EN', 'english'),
        ('Umaretemita', 'ED1-JP', 'romaji'),
        ('Nee zutto soba ni', 'ED1-JP', 'romaji'),
        ('Even if I grow weary', 'ED1-EN', 'english'),
        ("Don't touch me", 'ED1-EN', 'english'),
    ]
    for text, sty, expected in full_tests:
        label, conf, reason = classify_full_line(text, sty)
        status = 'OK' if label == expected else 'FAIL'
        print(f"  [{status}] {text!r:40s} → {label} ({conf:.2f})")
