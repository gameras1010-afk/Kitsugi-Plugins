"""
ass_style_conventions.py
========================
ASS Format - Kapsayici Stil ve Icerik Sozlugu
Kaynak: Community deep research (GitHub, Doom9, VideoHelp, encode.moe, fansubbing wiki)
        + GJM/Chyuu/SubsPlease/HorribleSubs/Commie/UTW gercek fansub analizi
        + Karaokes.moe + Aegisub dokumantasyonu
        + Deep research: Duo/Choir/Singer/NCOP/NCED/Creditless vb.

Bu dosya cevirilmemesi gereken *her seyi* tanimlar:
  - Fansub gruplarinin gercek stil adlari (HorribleSubs, GJM, Chyuu, SubsPlease, CR...)
  - Event (Dialogue) alanlarindaki meta bilgiler (Actor, Comment, Layer, Effect)
  - Metin icerigi kaliplari (sadece sayi, sembol, koordinat vb.)
  - Gradient/mask satiri tespiti

Kaynak referanslari:
  - Aegisub subtitle_format_ass.cpp : Events format = Layer,Start,End,Style,Actor,...
  - libass ass_parse.c               : Banner/Scroll/Karaoke effect alani
  - pysubs2 ssastyle.py              : V4+ Styles format alanlari
  - bubblesub/ass_tag_parser         : Tag kategorileri
  - Fansubbing wiki (miraheze.org)   : Grup stil adlari
  - encode.moe typesetting guide     : Typeset karar mantigi
  - VideoHelp/Doom9 ASS threads      : Gercek dosya ornekleri
  - Karaokes.moe                     : Karaoke stil adlari
"""

# =============================================================================
# BOLUM 1: STIL ADI KALIPLARI
# Kaynak: Gercek fansub gruplari ve streaming platformlarindan analiz
# =============================================================================

# ── CEVIRIYE GITMEYECEK stil adlari ──────────────────────────────────────────
# Tam kelime eslesimi (buyuk/kucuk harf duyarsiz, -_ ile bolunur)

SKIP_STYLE_WORDS = {
    # ── Karaoke / Romaji ──────────────────────────────────────────────────────
    # GJM, HorribleSubs, SubsPlease, Chyuu, commie, vivid, FFF, Underwater
    'kara',       # Chyuu, FFF — karaoke satiri
    'karaoke',    # Genel
    'kar',        # Kisaltma
    'k',          # K-OP, K-ED (KFX karaoke temelli stil — Karaokes.moe)
    'romaji',     # Japonca romaji transcription
    'rom',        # Kisaltma (OP1-ROM, ED-ROM)
    'romanized',  # Romanized versiyonu
    'romanization', # Romanizasyon
    'furigana',   # Japonca hece okuma yardimcisi
    'ruby',       # CSS ruby gibi - ust hece notasyonu
    # NOT: 'song', 'lyric', 'lyrics' buradan kaldirildi —
    # bunlar Ingilizce sarki stili olabilir (Song, Insert Song, Lyric-EN)

    # ── Japonca / Dogu Asya dilleri ──────────────────────────────────────────
    'jpn',        # Japonca
    'jp',         # Kisaltma
    'jap',        # Japonca
    'jpnese',     # Uzun form
    'japanese',   # Tam form
    'kana',       # Hiragana/katakana
    'kanji',      # Kanji karakterler
    'chn',        # Cinese
    'cn',         # Kisaltma
    'zh',         # ISO Cin (Mandarin)
    'chinese',    # Tam form
    'kor',        # Korece
    'kr',         # Kisaltma
    'korean',     # Tam form
    'chi',        # Cinese (alternatif)

    # ── Produksiyon kredileri ─────────────────────────────────────────────────
    'credit',     # Genel kredi satiri
    'credits',    # Cok satirli kredi
    'credit2',    # Ikinci kredi blogu
    'staff',      # Yapim ekibi
    'cast',       # Oyuncu listesi

    # ── Ceviri notlari ────────────────────────────────────────────────────────
    'tlnote',     # Translation Note
    'trnote',     # Variant
    'ednote',     # Editor notu
    'tl',         # TL note kisaltmasi

    # ── Ruby / Furigana / Memory (Japonca) ───────────────────────────────────
    'mem',        # Memory/flashback Japonca
    'memory',     # Tam form

    # ── Arka plan muzigi ─────────────────────────────────────────────────────
    'bgm',        # Background Music notasyonu (instrumental)
    'music',      # Muzik stili (instrumental)

    # ── GJM ozel (Good Job! Media) ───────────────────────────────────────────
    'insjp',      # Insert - JP
    'insrom',     # Insert - Romaji
    'inskana',    # Insert - Kana
    'insmem',     # Insert - Memory (Japonca)
    'inskai',     # Insert - Kanji
    'kai',        # GJM Kanji kisaltmasi (InsKai)
}

# ── CEVIRIYE ZORLA GIDECEK stil adlari ───────────────────────────────────────
# Skip listesini override eder
FORCE_TRANSLATE_STYLE_WORDS = {
    # Ingilizce sarki/cevirisi
    'eng',         # OP1-ENG, ED-ENG
    'en',          # Kisaltma
    'english',     # Tam form (Opening-English)
    'trans',       # Translation (sarki cevirisi)
    'translation', # Tam form
    'alt',         # Alternatif dialog
    'altdial',     # Alternatif diyalog

    # NCOP/NCED creditless Ingilizce versiyonlar
    'nc',          # NC-EN, NCOP-EN gibi kombinasyonlar
    'full',        # OP Full, ED Full (sarki sozu iceren tam versiyon)
    'clean',       # Clean OP, Clean-ED
    'creditless',  # Creditless versiyonlar

    # GJM Insert English
    'insen',       # GJM Insert - English
    'inseng',      # GJM Insert - English (uzun)

    # Diyalog tipleri — bunlar skip EDILMEZ ama sign tespiti devam eder
    'narration',   # Anlatici — cevirilmeli
    'narrator',    # Anlatici karakter
    'thought',     # ic monolog
    'flashback',   # Flashback diyalog
    'internal',    # ic ses
    'italics',     # Italik diyalog
    'italic',      # Variant
    'bold',        # Kalin diyalog
    'overlap',     # Cakisan diyalog
    'honorifics',  # Honorifik gosterim
}

# ── SIGN / Ekran yazisi stil adlari (ceviriye git, ama SIGN moduyla) ─────────
SIGN_STYLE_WORDS = {
    # Genel
    'sign',       # En yaygin sign stili
    'signs',      # Cok satirli
    'signstop',   # Alt grup varyasyonu
    'signsbottom',

    # Tipografi
    'typeset',    # Typeset satiri
    'ts',         # Kisaltma

    # Baslik / kart
    # NOT: 'title' buradan kaldirildi — SAO/genel animelerde 'title' stili
    # cevrilmesi gereken ekran metni icerir (Kara Kilic Ustasi vb.)
    # Sadece daha spesifik formlar sign sayilir:
    'titlecard',  # Tam form — kesinlikle sign karti
    'eptitle',    # Episode title (kisaltma)
    'episodetitle', # Tam form
    'episode',    # Bolum numarasi kartlari

    # Ekrandaki metin
    'onscreen',   # Ekranin uzerinde
    'screen',     # Varyant
    'ost',        # On-Screen Text (yayin kuruluslari kullanir)
    'caption',    # Alt yazi aciklamasi (hearing-impaired turunden)

    # Konum aciklamasi
    'location',   # Yer adi, sehir ismi
    'label',      # Etiket

    # Gorsel efekt
    'overlay',    # Katman ustu metin
    'board',      # Tahta, pano
    'banner',     # Yatay kaydirma

    # Efektler
    'effect',     # Efekt stili (genel)
    'effects',    # Cok satir
    'sfx',        # Sound effect / visual effect

    # Ceviri + sign kombinasyonu
    'os',         # Off-screen (cevirilmeli, sign modu)
    'offscreen',  # Tam form

    # Crunchyroll / Amazon / Netflix -spesifik
    'main',       # CR'de ana dialog stili (cevirilmeli ama check)
    'alt',        # Alternatif

    # Supers (Netflix terimi)
    'supers',     # Netflix superimposition
    'super',      # Kisaltma
}


# =============================================================================
# BOLUM 2: ACTOR ALANI KALIPLARI
# =============================================================================

ACTOR_SKIP_PATTERNS = {
    '[tl note]', '[tl]', '[tlnote]',
    '[editor]', '[edit]',
    '[timer]', '[time]',
    '[qc]',
    '[typesetter]', '[ts]',
    '[fansub]',
    '[note]',
    '[author]',
    '', 'n/a', 'na',
}

ACTOR_SIGN_PATTERNS = {
    'sign', 'typeset', 'ts', 'ost', 'caption', 'onscreen',
}


# =============================================================================
# BOLUM 3: METIN ICERIGI KALIPLARI
# =============================================================================

import re as _re

NUMBER_DOMINANT_PATTERN = _re.compile(
    r'^[\d\s:.\-+±°%/,×xX]*(?:km|m|cm|mm|kg|g|lb|ft|mi|mph|kph|'
    r'km/h|m/s|hz|khz|°[CF]?|No\.|#\d|\d+st|\d+nd|\d+rd|\d+th)?[\s.]*$',
    _re.IGNORECASE
)

COORDINATE_TEXT_PATTERN = _re.compile(
    r'^[\s\d.+\-,×xX:()*/\\<>=!&|^~@#$%]+$'
)

PUNCT_ONLY_PATTERN = _re.compile(
    r'^[\s!"#$%&\'()*+,\-./:;<=>?@\[\]^_`{|}~\u2010-\u2027\u2030-\u205e]+$'
)

CJK_DOMINANT_PATTERN = _re.compile(
    r'^[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\uFF00-\uFFEF'
    r'\u4E00-\u9FAF\u3400-\u4DBF\uAC00-\uD7AF\s\d.,!?♪♫…—–\-]+$'
)

LINEBREAK_ONLY_PATTERN = _re.compile(
    r'^(?:\\[NnhH]|\s)+$'
)

URL_PATH_PATTERN = _re.compile(
    r'^(?:https?://|ftp://|www\.|/[\w/.\-]+\.(?:com|org|net|jp|co|tv))',
    _re.IGNORECASE
)

TIMESTAMP_ONLY_PATTERN = _re.compile(
    r'^\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*$'
)

ELLIPSIS_ONLY_PATTERN = _re.compile(
    r'^[\s.…\-—–]+$'
)

HEX_CODE_PATTERN = _re.compile(
    r'^[0-9A-Fa-f]{6,}$'
)


# =============================================================================
# BOLUM 4: GRADIENT/MASK SATIRI TESPITI
# =============================================================================

def is_gradient_cluster(events: list, idx: int, threshold: int = 5) -> bool:
    if not events or idx >= len(events):
        return False
    ev = events[idx]
    start = ev.get('start', '')
    end   = ev.get('end',   '')
    if not start or not end:
        return False
    count = sum(
        1 for e in events
        if e.get('start') == start and e.get('end') == end
    )
    return count >= threshold


# =============================================================================
# BOLUM 5: LAYER ALANI ANALIZI
# =============================================================================

LAYER_SIGN_THRESHOLD   = 10
LAYER_DRAWING_THRESHOLD = 100


# =============================================================================
# BOLUM 6: AKTOR ALANI STANDART LISTE
# =============================================================================

KNOWN_ACTOR_SIGN_VALUES = {
    '[sign]', '[signs]', '[ts]', '[typeset]',
    '[ost]', '[caption]', '[onscreen]',
    '[insert]', '[sfx]',
}


# =============================================================================
# BOLUM 7: YARDIMCI FONKSIYONLAR
# =============================================================================

def is_text_non_translatable(pure_text: str) -> tuple:
    if not pure_text or not pure_text.strip():
        return True, 'empty_text'

    t = pure_text.strip()

    if LINEBREAK_ONLY_PATTERN.match(t):
        return True, 'linebreak_only'

    if PUNCT_ONLY_PATTERN.match(t):
        return True, 'punct_only'

    if ELLIPSIS_ONLY_PATTERN.match(t):
        return True, 'ellipsis_only'

    if TIMESTAMP_ONLY_PATTERN.match(t):
        return True, 'timestamp_only'

    if HEX_CODE_PATTERN.match(t):
        return True, 'hex_code'

    if URL_PATH_PATTERN.match(t):
        return True, 'url_or_path'

    if CJK_DOMINANT_PATTERN.match(t):
        return True, 'cjk_dominant'

    return False, 'has_translatable_text'


def classify_style_name(style_name: str) -> str:
    """
    Stil adini analiz et: 'skip' | 'translate' | 'sign' | 'unknown'

    Kural sirasi:
      1. FORCE_TRANSLATE → her zaman 'translate'
      2. SKIP_STYLE_WORDS → 'skip'
      3. SIGN_STYLE_WORDS → 'sign'
      4. Bilinmiyor → 'unknown'
    """
    if not style_name:
        return 'unknown'

    s = style_name.strip().upper()
    parts = set(_re.split(r'[-_\s]', s))
    parts_lower = {p.lower() for p in parts}
    s_clean_lower = _re.sub(r'[-_\s]', '', s).lower()

    # Oncelik 1: force translate (EN, ENG, ALT, FULL, CLEAN, NC, ENGLISH...)
    if parts_lower & FORCE_TRANSLATE_STYLE_WORDS:
        return 'translate'

    # Oncelik 2: skip sozlugu
    if parts_lower & SKIP_STYLE_WORDS:
        return 'skip'
    # Substring eslesimi (OP1ROM → ROM icerir → skip)
    for word in SKIP_STYLE_WORDS:
        if len(word) >= 3 and s_clean_lower.endswith(word):
            return 'skip'

    # Oncelik 3: sign modu
    if parts_lower & SIGN_STYLE_WORDS:
        return 'sign'
    for word in SIGN_STYLE_WORDS:
        if len(word) >= 4 and word in s_clean_lower:
            return 'sign'

    return 'unknown'


def classify_actor_field(actor: str) -> str:
    if not actor:
        return 'unknown'
    a_lower = actor.strip().lower()

    if a_lower in ACTOR_SKIP_PATTERNS:
        return 'unknown'

    if any(pat in a_lower for pat in ['tl', 'note', 'editor', 'timer', 'qc']):
        return 'unknown'

    if a_lower in KNOWN_ACTOR_SIGN_VALUES:
        return 'sign'
    for pat in ACTOR_SIGN_PATTERNS:
        if pat in a_lower:
            return 'sign'

    return 'unknown'


# =============================================================================
# BOLUM 8: KAPSAMLI FANSUB GRUBU STIL ADLARI REFERANSI
# Gercek gruplarin kullandigi bilinen stil adlari listesi
# Kaynak: GJM, Chyuu, HorribleSubs, SubsPlease, Crunchyroll, Netflix, commie,
#         UTW, Commie, FFF, Vivid, Underwater, EMBER, Erai-raws
# =============================================================================

KNOWN_FANSUB_STYLES = {
    # ── Dialog stiller (CEVIRILMELI) ─────────────────────────────────────────
    'translate': [
        'Default', 'Dialogue', 'Main', 'Alt', 'Italics', 'Italic',
        'Bold', 'Top', 'Overlap', 'Flashback', 'Internal', 'Thought',
        'Narrator', 'Narration',
        'GJM_Main', 'GJM_Alt',
        'HorrSub_Default', 'CR_Main', 'Netflix_Default', 'Amazon_Default',
        'Honorifics', 'Staff intro',
        # Sarki / Vokal stilleri (Ingilizce - CEVIRILMELI)
        'Song', 'Song-EN', 'Lyric', 'Lyrics-EN',
        'Opening Song', 'Ending Song', 'Insert Song',
        'NCOP', 'NCED', 'NCOP1', 'NCED1',
        'Clean OP', 'Clean-ED', 'Creditless OP',
        'Intro', 'Outro',
        'Vocal', 'Singer', 'Main Singer', 'Sub Singer',
        'Chorus', 'Choir', 'Duo', 'Group', 'Harmony', 'Backing',
        'Theme', 'Main Theme', 'Theme Song',
        'OP Full', 'ED Full', 'OP Preview',
        'GJM_InsEN', 'GJM_InsENG',
    ],

    # ── Sign stiller (SIGN MODUYLA CEVIRILMELI) ───────────────────────────────
    'sign': [
        'Signs', 'Sign', 'Typeset', 'TS', 'Title', 'Caption',
        'OST', 'Supers', 'On-Screen Text', 'Location',
        'GJM_Signs', 'GJM_Typesets', 'Chyuu_Signs', 'HS_Signs', 'CR_Signs',
    ],

    # ── Skip stiller (HICBIR ZAMAN CEVIRME) ──────────────────────────────────
    'skip': [
        # Romaji / Japonca OP/ED
        'OP Romaji', 'OP1 Romaji', 'ED Romaji',
        'OP JP', 'ED JP', 'OP-ROM', 'ED-ROM', 'OP-JPN', 'ED-JPN',
        'OP-JP', 'ED-JP', 'OP-Kara', 'ED-Kara', 'OP-KARA',
        'K-OP', 'K-ED', 'Kara-OP', 'Kara-ED',  # Karaoke temelli KFX stilleri
        # GJM
        'GJM_Main_JP', 'GJM_Karaoke', 'GJM_Romaji',
        'GJM_InsJP', 'GJM_InsROM', 'GJM_InsKana', 'GJM_InsMem', 'GJM_InsKai',
        # Chyuu
        'Chyuu_OP_ROM', 'Chyuu_ED_ROM', 'Chyuu_Kara',
        # Kredi / Staff
        'Credits', 'Staff Credits', 'OP Credits', 'ED Credits',
        'Karaoke', 'Kara', 'BGM', 'Furigana', 'Ruby',
        'OP1-ROM', 'ED-JPN', 'TL Note',
    ],
}


# =============================================================================
# MODUL TESTI
# =============================================================================
if __name__ == '__main__':
    print('[ASS Style Conventions DB v2 — Deep Research Edition]')
    print(f'  Skip kelimeler:            {len(SKIP_STYLE_WORDS)}')
    print(f'  Force-translate kelimeler: {len(FORCE_TRANSLATE_STYLE_WORDS)}')
    print(f'  Sign kelimeler:            {len(SIGN_STYLE_WORDS)}')
    print(f'  Bilinen fansub gruplari:   {sum(len(v) for v in KNOWN_FANSUB_STYLES.values())} stil')
    print()

    test_styles = [
        ('Default',           'unknown'),
        ('Italics',           'translate'),
        ('Top',               'unknown'),
        ('Flashback',         'translate'),
        ('Narrator',          'translate'),
        ('ED1-EN',            'translate'),
        ('Opening-English',   'translate'),
        ('NCOP',              'unknown'),
        ('NCED-EN',           'translate'),
        ('Clean OP',          'translate'),
        ('GJM_InsEN',         'translate'),
        ('Signs',             'sign'),
        ('GJM_Signs',         'sign'),
        ('OST',               'sign'),
        ('Caption',           'sign'),
        ('Supers',            'sign'),
        ('OP-ROM',            'skip'),
        ('GJM_InsJP',         'skip'),
        ('Chyuu_Kara',        'skip'),
        ('ED Romaji',         'skip'),
        ('Credits',           'skip'),
        ('BGM',               'skip'),
        ('Karaoke',           'skip'),
        ('Furigana',          'skip'),
        ('OP1-ROM',           'skip'),
        ('ED-JPN',            'skip'),
        ('OP-KARA',           'skip'),
        ('K-OP',              'skip'),
    ]

    ok = 0
    for style, exp in test_styles:
        got = classify_style_name(style)
        chk = 'OK' if got == exp else 'FAIL'
        if got == exp: ok += 1
        print(f'  [{chk}] {exp:<12} {got:<12} {style}')

    print(f'\n  {ok}/{len(test_styles)} test gecti')
