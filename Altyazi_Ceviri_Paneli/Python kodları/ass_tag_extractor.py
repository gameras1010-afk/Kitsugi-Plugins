"""
ass_tag_extractor.py
====================
ASS/SSA altyazi tag koruma motoru -- Nexus Pro Translation Engine

Kaynak referanslar:
  - https://github.com/bubblesub/ass_tag_parser  (pip: ass-tag-parser)
  - https://github.com/libass/libass/blob/master/libass/ass_parse.c
  - https://aegisub.org/docs/latest/ass_tags/

Hibrit Mimari:
  1. BIRINCIL: ass-tag-parser kutuphanesi (pip install ass-tag-parser)
     -> Tam ASS spec parse, typed objeler, AnimationTag icindeki ic tagler
     -> AssTagComment, AssTagDrawingMode, AssTagPosition gibi kesin tipler
  2. FALLBACK: Regex motoru (baglimlilik yok, hep calisir)
     -> ass-tag-parser {\\**-san} gibi malformed bloklarda exception firlatir
     -> Bizim regex bu durumu gracefully handle eder (comment olarak siniflandirir)

Kullanim:
  extract_ass_tags(text)  -> (clean_text, tag_map)
  restore_ass_tags(translated, tag_map) -> (restored, missing)
  classify_block(content) -> 'tag' | 'comment' | 'empty'
  parse_ass_block(raw_block) -> list[AssTag] veya None
"""

import ass_vendor_setup  # noqa — _vendor/ dizinini path'e ekler
import re
from typing import Tuple, Dict, List, Optional, Any

# ── Backend 1: ass-tag-parser (pip install ass-tag-parser) ──────────────────
try:
    from ass_tag_parser import (
        parse_ass as _lib_parse_ass,
        AssTagComment as _AssTagComment,
        AssTagListOpening as _AssTagListOpening,
        AssTagListEnding as _AssTagListEnding,
        AssTagDraw as _AssTagDrawingMode,       # Drawing mode tag
        AssTagBaselineOffset as _AssTagDrawingBaseline,
        AssText as _AssText,
    )
    _LIB_AVAILABLE = True
except ImportError:
    _LIB_AVAILABLE = False
    _AssTagComment = None
    _AssTagDrawingMode = None
    _AssText = None

# ── Backend 2: Regex (her zaman aktif, fallback) ─────────────────────────────

# ─── Kaynak: libass/ass_parse.c + Aegisub docs ───────────────────────────────
# Tüm geçerli ASS override tag adları (backslash olmadan)
# Bunları bilmek şart değil (çünkü '\' kontrolü yeterli) ama
# tag doğrulama ve logging için kullanılır.

ASS_VALID_TAGS = frozenset({
    # Metin formatlama
    'i', 'b', 'u', 's',
    # Bulanıklık
    'be', 'blur',
    # Kenarlık
    'bord', 'xbord', 'ybord',
    # Gölge
    'shad', 'xshad', 'yshad',
    # Font
    'fn', 'fs', 'fscx', 'fscy', 'fsc', 'fsp', 'fe',
    # Döndürme
    'frx', 'fry', 'frz', 'fr',
    # Eğme
    'fax', 'fay',
    # Renk — Aegisub + libass
    'c', '1c', '2c', '3c', '4c',
    # Alfa
    'alpha', '1a', '2a', '3a', '4a',
    # Hizalama
    'an', 'a',
    # Konum & Hareket
    'pos', 'move', 'org',
    # Kırpma
    'clip', 'iclip',
    # Solma
    'fad', 'fade',
    # Animasyon transform
    't',
    # Karaoke
    'k', 'K', 'kf', 'ko', 'kt',
    # Stil sıfırlama
    'r',
    # Akıllı sarma
    'q',
    # Çizim modu
    'p', 'pbo',
    # VSFilter özelliği
    'feature',
})

# ASS içi özel karakter desenleri (override block'ların DIŞINDA yazılır)
# \N = sert satır sonu, \n = yumuşak satır sonu, \h = sert boşluk
ASS_SPECIAL_CHARS = re.compile(r'\\[Nnh]')

# Geçerli ASS override bloğu: İçinde en az bir '\\' + harf var
# Örnek geçerli:   {\pos(100,50)\blur2}  → ✓ gerçek tag
# Örnek geçersiz:  {-san}                → ✗ inline comment
# Örnek geçersiz:  {bro wtf}             → ✗ inline comment
_HAS_TAG = re.compile(r'\\[a-zA-Z]')

# Tam ASS tag bloğu yakalama regex'i (iç içe `{` yok, ASS'de geçersiz)
_TAG_BLOCK = re.compile(r'\{[^}]*\}')

# Drawing mode açıksa sonraki metin çizim komutudur (m X Y l X Y...)
# [FIX] \pbo (baseline offset) da drawing modu ile ilgili - eklendi
_DRAWING_MODE_ON = re.compile(r'\\p(?:[1-9]|bo)')

# [FIX] Drawing komutları: 'c' argumansiz, diğerleri sayı gerektirir
# ASS drawing: m n l b s p = sayı gerekli, c = argumansiz (b-spline kapat)
_DRAWING_CONTENT = re.compile(r'\b(?:[mlbspn]\s+-?[\d.]+|c\b)')

# ASS içi özel karakterler — override block DIŞINDA yazılır
# \N = hard newline (satır sonu zorlanır)
# \n = soft newline (sadece \q2 modunda aktif)
# \h = non-breaking hard space
# Bu karakterler extract aşamasında korunmalı, AI'ya düz metin olarak gitmemeli
_ASS_INLINE_SPECIAL = re.compile(r'\\([Nnh])')
_INLINE_SPECIAL_MAP = {'N': '__ASSNL__', 'n': '__ASSn__', 'h': '__ASSh__'}
_INLINE_SPECIAL_RMAP = {v: '\\' + k for k, v in _INLINE_SPECIAL_MAP.items()}


def _classify_via_lib(content: str) -> Optional[str]:
    """
    ass-tag-parser kutuphanesiyle {content} blogu siniflandir.
    Basarisiz olursa None dondur (fallback icin).

    Returns: 'tag' | 'comment' | 'empty' | None
    """
    if not _LIB_AVAILABLE:
        return None
    if not content:
        return 'empty'
    try:
        nodes = _lib_parse_ass('{' + content + '}')
        has_real_tag = False
        has_comment = False
        for node in nodes:
            if isinstance(node, (_AssTagListOpening, _AssTagListEnding, _AssText)):
                continue
            if isinstance(node, _AssTagComment):
                has_comment = True
            else:
                has_real_tag = True
        if has_real_tag:
            return 'tag'
        if has_comment:
            return 'comment'
        return 'empty'
    except Exception:
        # Malformed blok (ornek: {\**-san}) → fallback regex'e birak
        return None


def classify_block(content: str) -> str:
    """
    Bir {content} blogunun cesidini belirle.

    Birincil: ass-tag-parser kutuphanesi (tam ASS spec, typed detection)
    Fallback:  Regex (\\[a-zA-Z] kuralı — libass mantigi)

    Returns:
        'tag'     — Gercek ASS override tag(lar) iceriyor (backslash prefix'li)
        'comment' — Inline comment (gorunmez, ceviri icin gerekli degil)
        'empty'   — Bos blok {}
    """
    if not content:
        return 'empty'
    # Birincil: kutuphane
    lib_result = _classify_via_lib(content)
    if lib_result is not None:
        return lib_result
    # Fallback: regex
    if _HAS_TAG.search(content):
        return 'tag'
    return 'comment'


def parse_ass_block(raw_block: str) -> Optional[List[Any]]:
    """
    Ham bir ASS blogundan ({...}) typed tag objelerini don.
    ass-tag-parser kutuphanesi gerektirir.

    Kullanim ornegi:
        nodes = parse_ass_block(r'{\pos(100,50)\blur3}')
        for node in nodes:
            if isinstance(node, AssTagPosition):
                print(f'x={node.x}, y={node.y}')

    Returns:
        Liste (AssTag objeleri) veya None (kutuphane yok / parse hatasi)
    """
    if not _LIB_AVAILABLE:
        return None
    try:
        return _lib_parse_ass(raw_block)
    except Exception:
        return None


def is_drawing_line(text: str) -> bool:
    """Satir bir ASS drawing (vektor cizim) satiri midir?"""
    if not text:
        return False
    if _LIB_AVAILABLE:
        # Kutuphane ile kesin tespit: AssTagDrawingMode ve level > 0
        try:
            nodes = _lib_parse_ass(text)
            for node in nodes:
                if isinstance(node, _AssTagDrawingMode) and node.scale > 0:
                    return True
        except Exception:
            pass
    # Fallback: regex
    if bool(_DRAWING_MODE_ON.search(text)):
        return True

    # Check if the tag-stripped text is pure vector/drawing coordinates
    # even without the \p tag (e.g. when tags were stripped or missing).
    tag_stripped = re.sub(r'\{[^}]*\}', '', text).strip()
    if tag_stripped:
        vector_pattern = r'\b[mlb]\s+[\d\s.-]+'
        vector_matches = list(re.finditer(vector_pattern, tag_stripped))
        vector_len = sum(len(m.group(0)) for m in vector_matches)
        if vector_len > 0 and (vector_len / len(tag_stripped)) > 0.6:
            return True
        # Count numeric density
        numeric = sum(1 for c in tag_stripped if c.isdigit() or c in '.-')
        digit_ratio = numeric / len(tag_stripped)
        if re.match(r'^[mlb]\s+[-\d]', tag_stripped) and digit_ratio > 0.5:
            return True

    return False


def extract_ass_tags(text: str) -> Tuple[str, Dict[str, str]]:
    """
    ASS metninden tag blokları çıkarır, yerlerine __T0__ placeholder koyar.
    Inline comment blokları ({-san}, {bro wtf}) silinir — AI görmez.

    Args:
        text: Ham ASS diyalog metni (override tagları içeren)

    Returns:
        (clean_text, tag_map)
        clean_text: Sadece çevrilecek düz metin + placeholder'lar
        tag_map:    { '__T0__': '{\\pos(100,50)}', '__T1__': '{\\blur2}', ... }

    Örnekler:
        '{\\i1}Hello{\\i0}{-san}' → ('__T0__Hello__T1__', {'__T0__': '{\\i1}', '__T1__': '{\\i0__}'})
        # Not: {-san} silindi, çünkü comment
    """
    tag_map: Dict[str, str] = {}
    tag_index = [0]  # mutable int

    comment_count = [0]

    def replace_block(m: re.Match) -> str:
        full_block = m.group(0)   # {content}
        content = full_block[1:-1]  # content
        kind = classify_block(content)

        if kind == 'tag':
            key = f'__T{tag_index[0]}__'
            tag_index[0] += 1
            tag_map[key] = full_block
            return key
        elif kind == 'comment':
            # Inline comment: sil, raporla (debug için sayı tut)
            comment_count[0] += 1
            return ''   # Görünmez zaten, silinir
        else:
            # Empty block {} — sil
            return ''

    clean_text = _TAG_BLOCK.sub(replace_block, text)

    # [FIX] Kapatılmamış tag fragmentleri: {\c&H... (kapanış } yok)
    # libass bu durumu tag olarak işler — biz de sileriz.
    # Örnek: ...)}l{\c&H00CCB1A5&  ← kapanmamış, _TAG_BLOCK yakalayamıyor
    clean_text = re.sub(r'\{[^}]*$', '', clean_text)

    # [YENİ] ASS içi özel karakterleri koru: \N \n \h
    # Bu karakterler override block DIŞINDA yazılır, AI onları silebilir.
    # __ASSNL__ / __ASSn__ / __ASSh__ olarak maskelenir, restore aşamasında geri gelir.
    def replace_special(m: re.Match) -> str:
        char = m.group(1)  # 'N', 'n', veya 'h'
        ph = _INLINE_SPECIAL_MAP.get(char)
        if ph:
            tag_map[ph] = '\\' + char  # Restore haritasına ekle
            return ph
        return m.group(0)

    clean_text = _ASS_INLINE_SPECIAL.sub(replace_special, clean_text)
    return clean_text, tag_map


# ═══════════════════════════════════════════════════════════════════
# SEGMENT-BASED TAG PRESERVATION
# ═══════════════════════════════════════════════════════════════════
# Endüstri standardı: Tag'ler ASLA AI'ya gönderilmez.
# Metin tag sınırlarında segmentlere bölünür, sadece text segmentleri
# çevrilir, tag'ler orijinal pozisyonlarında geri birleştirilir.
# ──────────────────────────────────────────────────────────────────
# Referans: XLIFF standartı, CAT tool masking, llm-subtrans yaklaşımı
# ═══════════════════════════════════════════════════════════════════

_TAG_SPLIT_RE = re.compile(r'(\{[^}]*\})')   # {tag} sınırında böl


def split_into_segments(text: str) -> dict:
    """
    ASS metnini TAG ve TEXT segmentlerine böler.

    Tag'ler API'ya hiç gönderilmez — sadece metin segmentleri çevrilir.
    Örnek:
        "{\i0}Dig Deep!{\i1} prep meeting at 11:30."
        →  structure: [('TAG','{\i0}'),('TXT','Dig Deep!'),('TAG','{\i1}'),('TXT',' prep meeting at 11:30.')]
        →  text_segments: ['Dig Deep!', ' prep meeting at 11:30.']

    Returns:
        {
            'structure': list of ('TAG', str) | ('TXT', str) tuples,
            'text_segments': list of translatable text strings (non-empty),
            'has_tags': bool,          # inline etiket var mı?
            'eligible': bool,          # segment modu için uygun mu? (>1 text seg AND has_tags)
        }
    """
    if not text:
        return {'structure': [('TXT', '')], 'text_segments': [''],
                'has_tags': False, 'eligible': False}

    parts = _TAG_SPLIT_RE.split(text)
    structure = []
    text_segments = []

    for part in parts:
        if not part:
            continue
        if part.startswith('{') and part.endswith('}'):
            # Gerçek ASS tag mi, inline comment mi?
            content = part[1:-1]
            if _HAS_TAG.search(content):
                structure.append(('TAG', part))
            # else: inline comment → sil (extract_ass_tags gibi)
        else:
            structure.append(('TXT', part))
            if part.strip():  # Boş string değilse segment listesine ekle
                text_segments.append(part)

    has_tags = any(kind == 'TAG' for kind, _ in structure)
    # Segment modu için: en az 1 TAG + en az 1 non-empty TXT segment olmalı
    eligible = has_tags and len(text_segments) >= 1

    return {
        'structure': structure,
        'text_segments': text_segments,
        'has_tags': has_tags,
        'eligible': eligible,
    }


def rejoin_from_segments(translated_segments: List[str], structure: list) -> str:
    """
    Çevrilmiş metin segmentlerini orijinal TAG yapısına göre birleştirir.

    Tag'ler değişmeden, çevrilmiş text segmentleri sırasıyla yerleştirilir.

    Args:
        translated_segments: Çevrilmiş text'ler (split_into_segments'in
                              text_segments listesiyle birebir eşleşmeli)
        structure: split_into_segments'den dönen ('TAG'|'TXT', str) tuple listesi

    Returns:
        Tag'ler + çevrilmiş metin birleşik string

    Örnek:
        structure  = [('TAG','{\i0}'),('TXT','Dig Deep!'),('TAG','{\i1}'),('TXT',' prep meeting')]
        translated = ['Dig Deep!', ' 11:30'da hazırlık']
        →  "{\i0}Dig Deep!{\i1} 11:30'da hazırlık"
    """
    if not translated_segments:
        # Hiç çeviri yok — TAG'leri koru, TXT'i orijinal bırak
        return ''.join(v for _, v in structure)

    seg_iter = iter(translated_segments)
    result_parts = []

    for kind, value in structure:
        if kind == 'TAG':
            result_parts.append(value)     # Tag olduğu gibi
        else:
            if value.strip():              # Non-empty TXT → çevrilmiş versiyonu kullan
                try:
                    translated = next(seg_iter)
                    # Orijinal boşluk prefix/suffix'ini koru
                    leading  = value[:len(value) - len(value.lstrip())]
                    trailing = value[len(value.rstrip()):]
                    result_parts.append(leading + translated.strip() + trailing)
                except StopIteration:
                    result_parts.append(value)  # Çeviri eksik → orijinal
            else:
                result_parts.append(value)     # Tamamen boş → orijinal bırak

    return ''.join(result_parts)


def merge_text_segments_for_batch(text_segments: List[str],
                                   separator: str = ' ⟦SEP⟧ ') -> str:
    """
    Birden fazla text segmentini tek bir batch girişine birleştirir.
    AI tüm segmentleri bağlamsal olarak çevirir, SEP ayracı korunur.

    Kullanım:
        merged = merge_text_segments_for_batch(['Dig Deep!', ' prep meeting'])
        # → 'Dig Deep! ⟦SEP⟧  prep meeting'
        # AI çevirir, sonra split_translated_batch() ile ayrıştırılır
    """
    return separator.join(seg.strip() for seg in text_segments)


_SEP_SPLIT_RE = re.compile(r'\s*⟦SEP⟧\s*')


def split_translated_batch(translated: str,
                             expected_count: int) -> List[str]:
    """
    merge_text_segments_for_batch ile birleştirilmiş çeviriyi tekrar ayırır.

    Args:
        translated: AI çeviri sonucu
        expected_count: Beklenen segment sayısı (orijinaldeki kadar)

    Returns:
        Çevrilmiş segmentler listesi; count uyuşmazsa graceful fallback
    """
    parts = _SEP_SPLIT_RE.split(translated.strip())
    if len(parts) == expected_count:
        return parts
    # Uyuşmazlık: tüm çeviriyi ilk segmente yükle, diğerleri boş
    result = [translated.strip()] + [''] * (expected_count - 1)
    return result[:expected_count]


def restore_ass_tags(translated: str, tag_map: Dict[str, str],
                     original_text: str = '') -> Tuple[str, List[str]]:
    """
    AI çevirisindeki __T0__ placeholder'larını orijinal ASS tag'leriyle değiştirir.
    AI'nın bozduğu / kaldırdığı placeholder'ları da kurtarır.
    [YENİ] __ASSNL__ __ASSn__ __ASSh__ özel karakter placeholder'ları da restore edilir.

    Args:
        translated:     AI'dan gelen çeviri metni
        tag_map:        extract_ass_tags'den dönen tag haritası
        original_text:  Orijinal ASS metni (kurtarma için)

    Returns:
        (restored_text, missing_tags)
        restored_text: Tag'ler yerine konulmuş nihai metin
        missing_tags:  AI'nın yok saydığı __Tn__ key listesi (boşsa mükemmel)
    """
    if not tag_map:
        # Sadece özel karakter restore kontrolü
        result = translated
        for ph, orig in _INLINE_SPECIAL_RMAP.items():
            result = result.replace(ph, orig)
        return result, []

    restored = translated
    missing = []

    # 0. PASS: Özel karakter placeholder'ları önce restore et
    for ph, orig in _INLINE_SPECIAL_RMAP.items():
        restored = restored.replace(ph, orig)

    # 1. PASS: Mevcut placeholder'ları yerine koy
    # Not: __ASSNL__ / __ASSn__ / __ASSh__ pass 0'da zaten restore edildi,
    # bunları missing sayma (tag_map'e eklenmişlerdi ama zaten gitti).
    _special_phs = set(_INLINE_SPECIAL_RMAP.keys())
    for key, tag in tag_map.items():
        if key in _special_phs:
            continue  # Zaten pass 0'da restore edildi
        if key in restored:
            restored = restored.replace(key, tag)
        else:
            missing.append(key)

    # 2. AI bazen __T0__ yerine __T 0__ veya _T0_ yazar — fuzzy düzelt
    if missing:
        for key in list(missing):
            # Normalize: __T0__ → T0, __T1__ → T1 ...
            idx = key.replace('__T', '').replace('__', '')
            patterns = [
                f'__T {idx}__',    # boşluklu: __T 0__
                f'__t{idx}__',     # küçük harf: __t0__
                f'__T{idx} __',    # sonda boşluk
                f'[T{idx}]',       # köşeli: [T0]
                f'(T{idx})',       # parantezli
                f'T{idx}',        # sadece T0
            ]
            found = False
            for pat in patterns:
                if pat in restored:
                    restored = restored.replace(pat, tag_map[key])
                    missing.remove(key)
                    found = True
                    break

    # 3. Hâlâ eksik tag'ler varsa → akıllı yerleştirme
    if missing:
        # Sıralı tag listesi: tag_map key sırası orijinal pozisyon sırasına eşit
        # (extract_ass_tags __T0__, __T1__, __T2__... sırayla atar)
        # Sadece __T0__, __T1__... formatındaki key'leri sırala.
        # __ASSNL__, __ASSn__, __ASSh__ gibi rakam içermeyen special key'ler
        # pass 0'da zaten restore edildi, bunları sort'a sokma (re.search → None → crash!)
        all_keys_sorted = sorted(
            [k for k in tag_map.keys() if re.search(r'\d+', k)],
            key=lambda k: int(re.search(r'\d+', k).group())
        )
        n_all = len(all_keys_sorted)
        trans_len = len(restored)

        _POS_TAGS = (r'\pos', r'\move', r'\org', r'\an', r'\clip', r'\iclip',
                     r'\fad', r'\fade')
        _STYLE_OPEN  = re.compile(r'\{\\([ibusBIUS])1\}')   # {\i1} {\b1} vs.
        _STYLE_CLOSE = re.compile(r'\{\\([ibusBIUS])0\}')   # {\i0} {\b0} vs.

        # Pozisyon tag'leri → başa
        for key in missing:
            tag = tag_map[key]
            if any(x in tag for x in _POS_TAGS):
                restored = tag + restored

        # Stil tag'leri → orantısal pozisyon ile yerleştir
        style_missing = [k for k in missing
                         if not any(x in tag_map[k] for x in _POS_TAGS)]

        if style_missing:
            # Her eksik tag için orijinal metindeki orantısal pozisyonu hesapla
            tag_positions = {}  # key → float (0.0 - 1.0)
            for i, key in enumerate(all_keys_sorted):
                # __T0__ ilk tag → pos=0.0, son tag → pos=1.0
                tag_positions[key] = i / max(n_all - 1, 1)

            # Eksik stil tag'lerini orantısal pozisyona göre ekle
            # En yüksek pos'tan en düşüğe doğru insert (sırayı bozmamak için)
            inserts = []  # (float pos, str tag)
            for key in style_missing:
                pos = tag_positions.get(key, 0.0)
                inserts.append((pos, tag_map[key]))

            # Pozisyona göre sırala ve metne ekle
            inserts.sort(key=lambda x: x[0])
            words = restored.split(' ')
            n_words = len(words)
            result_parts = list(words)

            for pos, tag in inserts:
                insert_idx = min(int(pos * n_words), n_words - 1)
                # Kelime sınırında tag'i ekle
                if _STYLE_CLOSE.match(tag):
                    # Kapanış tag'i: kelimenin SONUNA ekle
                    result_parts[insert_idx] = result_parts[insert_idx] + tag
                else:
                    # Açılış tag'i: kelimenin BAŞINA ekle
                    result_parts[insert_idx] = tag + result_parts[insert_idx]

            restored = ' '.join(result_parts)

    return restored, missing



def get_clean_text_for_translation(text: str) -> Tuple[str, Dict[str, str], int]:
    """
    Çeviri için hazır metin döndürür. (Tek çağrıyla her şey)

    Returns:
        (clean_text, tag_map, comment_count)
    """
    clean, tag_map = extract_ass_tags(text)

    # \N \n \h özel karakterleri koru (bunlar override block dışında)
    # Bunlar zaten clean_text'e geçiyor, AI'ye gönderilir
    # AI genellikle onları korur ama emin olmak için senti koru:
    # Yerlerine \\N gibi çift-backslash placeholder koymuyoruz
    # çünkü AI "\\N" → "\\türkçe" yapabilir. Direkt bırak.

    # Comment sayısını döndür (debugging)
    # Tag_map boş ve clean_text boşsa zaten skip
    return clean, tag_map, 0  # comment_count ayrı track edilmiyorsa 0


def validate_tag_restoration(original: str, restored: str,
                              tag_map: Dict[str, str]) -> Dict:
    """
    Tag restorasyon kalitesini kontrol et.

    Returns:
        {
          'ok': bool,
          'missing_tags': list,
          'extra_placeholders': list,  # hâlâ __Tn__ kalan
          'score': float  # 0.0 - 1.0
        }
    """
    extra = re.findall(r'__T\d+__', restored)
    missing = [k for k in tag_map if k not in restored and tag_map[k] not in restored]

    total = len(tag_map)
    ok_count = total - len(missing)
    score = ok_count / total if total > 0 else 1.0

    return {
        'ok': len(extra) == 0 and len(missing) == 0,
        'missing_tags': missing,
        'extra_placeholders': extra,
        'score': score,
    }


# ─── Yardımcı: Tüm ASS tag adlarını regex olarak döndür ────────────────────
def build_tag_name_regex() -> re.Pattern:
    """
    Tüm geçerli ASS tag adları için birleşik regex oluştur.
    Örnek: r'\\(bord|xbord|ybord|blur|...)(?=\d|&|\(|\\|})'
    """
    # Uzun isimleri önce koy (greedy olmayan alternatif için önemli)
    sorted_tags = sorted(ASS_VALID_TAGS, key=len, reverse=True)
    pattern = r'\\(' + '|'.join(re.escape(t) for t in sorted_tags) + r')(?=[\d&(\\}]|$)'
    return re.compile(pattern)


_TAG_NAME_RE = build_tag_name_regex()


def has_valid_ass_tag(block_content: str) -> bool:
    """
    Blok içeriği bilinen ASS tag adı içeriyor mu?
    classify_block() daha hızlı ama bu daha kesin.
    """
    return bool(_TAG_NAME_RE.search(block_content))


def strip_all_ass_tags(text: str) -> str:
    """
    Çeviri kalitesi ölçümü için: Metnden TÜM tag'leri ve comment'leri sil.
    Sadece okunabilir metin kalsın.
    """
    # Override blokları kaldır
    clean = _TAG_BLOCK.sub('', text)
    # [FIX] Kapatılmamış tag fragment'leri de kaldır (satır sonu)
    clean = re.sub(r'\{[^}]*$', '', clean)
    # ASS özel satır karakterlerini boşluğa çevir
    clean = ASS_SPECIAL_CHARS.sub(' ', clean)
    # Çoklu boşlukları birleştir
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


# ─── TEST ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    tests = [
        # Gerçek tag + inline comment
        (r'So Himekawa{\**-san} was conceived \Nwhen he was... eleven?{bro wtf }',
         'Himekawa-san olmadan'),
        # Kompleks animasyon tag + honorifik
        (r'{\t(2783,3085,\1c&H000000&\3c&HFFFFFF&)}Should Aqua{\**-kun} find him',
         'Animasyon tag'),
        # Karaoke
        (r'{\k120}Su{\k80}ba{\k60}ra{\k100}shi',
         'Karaoke'),
        # Pozisyon + renk
        (r'{\pos(100.5,200.3)\1c&H00FF00&\blur3}Hello World',
         'Pozisyon+renk+blur'),
        # Sadece inline comment
        (r'{well f*ck me i\'m not typesetting that}',
         'Sadece comment'),
        # Drawing mode
        (r'{\p1}m 0 0 l 100 0 100 100 0 100',
         'Drawing mode'),
        # Çoklu tag blokları
        (r'{\an8\fscx150\fscy150}Kimura Market{\r}',
         'Çoklu tag'),
    ]

    print('=' * 70)
    print('ASS TAG EXTRACTOR TEST')
    print('=' * 70)
    for text, label in tests:
        clean, tag_map, _ = get_clean_text_for_translation(text)
        print(f'\n[{label}]')
        print(f'  Orijinal : {text[:80]}')
        print(f'  Temiz    : {clean}')
        print(f'  Tag Haritası: {tag_map}')

        # Simüle: AI temiz metni döndürüyor (değiştirmeden)
        restored, missing = restore_ass_tags(clean, tag_map, text)
        print(f'  Restore  : {restored[:80]}')
        if missing:
            print(f'  KAYIP TAG: {missing}')
