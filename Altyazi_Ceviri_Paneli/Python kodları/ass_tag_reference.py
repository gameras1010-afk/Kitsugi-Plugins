# -*- coding: utf-8 -*-
"""
ass_tag_reference.py
====================
ASS (Advanced SubStation Alpha) subtitle format — tam kapsamlı tag referansı
ve çeviri pipeline'ı için sınıflandırma/tespit fonksiyonları.

Kaynaklar:
  • Aegisub resmi dokümantasyonu (aegisub.org/docs/latest/ass_tags/)
  • libass kaynak kodu: ass_parse.c, ass_drawing.c, ass_types.h (github.com/libass/libass)
  • Unanimated fansub typesetting kılavuzu (unanimated.github.io/ts/)
  • Aegisub Karaoke Templater dokümantasyonu
  • pysubs2 library (tkarabela/pysubs2)
  • VSFilter/libass uyumluluk notları

Versiyon: 2026-04-27
"""

import re
from typing import Tuple, Dict, Set

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 1: TÜM ASS OVERRIDE TAG'LERİ — REGEX PATTERN SÖZLÜĞÜ
# Kaynak: libass/ass_parse.c → ass_parse_tags() fonksiyonu + Aegisub docs
# ─────────────────────────────────────────────────────────────────────────────

# Kapalı tag bloğu: {herhangi bir şey}
RE_TAG_BLOCK       = re.compile(r'\{[^}]*\}')
# Kapanmamış tag bloğu (satır sonu fragmenti — malformed ASS)
RE_UNCLOSED_TAG    = re.compile(r'\{[^}]*$')
# Herhangi bir tag bloğu (kapalı veya kapanmamış)
RE_ANY_TAG         = re.compile(r'\{[^}]*\}?')


# ── STİL / YAZI TİPİ TAG'LERİ ────────────────────────────────────────────────
RE_BOLD            = re.compile(r'\\b\d*\b')          # \b0 \b1 \b700
RE_ITALIC          = re.compile(r'\\i[01]?\b')         # \i0 \i1
RE_UNDERLINE       = re.compile(r'\\u[01]?\b')         # \u0 \u1
RE_STRIKEOUT       = re.compile(r'\\s[01]?\b')         # \s0 \s1

# ── BORDER & SHADOW ───────────────────────────────────────────────────────────
RE_BORD            = re.compile(r'\\bord[\d.]*')       # \bord2 \bord3.7
RE_XBORD           = re.compile(r'\\xbord[\d.]*')      # \xbord2   (vsfilter 2.39+)
RE_YBORD           = re.compile(r'\\ybord[\d.]*')      # \ybord2
RE_SHAD            = re.compile(r'\\shad-?[\d.]*')     # \shad0 \shad2
RE_XSHAD           = re.compile(r'\\xshad-?[\d.]*')    # \xshad-1
RE_YSHAD           = re.compile(r'\\yshad-?[\d.]*')    # \yshad3

# ── BLUR ──────────────────────────────────────────────────────────────────────
RE_BE              = re.compile(r'\\be[\d.]*')         # \be1 \be5
RE_BLUR            = re.compile(r'\\blur[\d.]*')       # \blur0.8 \blur3

# ── FONT ──────────────────────────────────────────────────────────────────────
RE_FN              = re.compile(r'\\fn[^\\}]+')        # \fnArial \fnDroid Sans
RE_FS              = re.compile(r'\\fs\d+')            # \fs60 \fs24
RE_FSCX            = re.compile(r'\\fscx[\d.]+')       # \fscx150 \fscx500
RE_FSCY            = re.compile(r'\\fscy[\d.]+')       # \fscy250
RE_FSP             = re.compile(r'\\fsp-?[\d.]+')      # \fsp-10 \fsp2
RE_FE              = re.compile(r'\\fe\d+')            # \fe1 \fe128

# ── DÖNDÜRME / DÖNÜŞÜM ───────────────────────────────────────────────────────
RE_FRX             = re.compile(r'\\frx-?[\d.]+')      # \frx45
RE_FRY             = re.compile(r'\\fry-?[\d.]+')      # \fry-30
RE_FRZ             = re.compile(r'\\frz-?[\d.]+')      # \frz342.4 \frz180
RE_FR              = re.compile(r'\\fr-?[\d.]+')       # \fr45 (alias for frz)
RE_FAX             = re.compile(r'\\fax-?[\d.]+')      # \fax0.3
RE_FAY             = re.compile(r'\\fay-?[\d.]+')      # \fay0.1

# ── RENK TAG'LERİ (BGR formatı: &HAABBGGRR&) ─────────────────────────────────
RE_COLOR_PRIMARY   = re.compile(r'\\1?c&H[0-9A-Fa-f]+&?')   # \c \1c
RE_COLOR_SECONDARY = re.compile(r'\\2c&H[0-9A-Fa-f]+&?')    # \2c (karaoke pre-highlight)
RE_COLOR_BORDER    = re.compile(r'\\3c&H[0-9A-Fa-f]+&?')    # \3c
RE_COLOR_SHADOW    = re.compile(r'\\4c&H[0-9A-Fa-f]+&?')    # \4c

# ── ALPHA TAG'LERİ ────────────────────────────────────────────────────────────
# 00=opak, FF=tamamen şeffaf (CSS'ten tersi!)
RE_ALPHA_ALL       = re.compile(r'\\alpha&H[0-9A-Fa-f]+&?') # \alpha (tümü)
RE_ALPHA_1         = re.compile(r'\\1a&H[0-9A-Fa-f]+&?')    # \1a primary
RE_ALPHA_2         = re.compile(r'\\2a&H[0-9A-Fa-f]+&?')    # \2a secondary
RE_ALPHA_3         = re.compile(r'\\3a&H[0-9A-Fa-f]+&?')    # \3a border
RE_ALPHA_4         = re.compile(r'\\4a&H[0-9A-Fa-f]+&?')    # \4a shadow

# ── HİZALAMA ─────────────────────────────────────────────────────────────────
# Numpad: 1=alt-sol 2=alt-orta 3=alt-sağ 4=orta-sol 5=orta 6=orta-sağ
#         7=üst-sol 8=üst-orta 9=üst-sağ
RE_AN              = re.compile(r'\\an[1-9]')           # \an2 (modern)
RE_A               = re.compile(r'\\a\d+')              # \a2  (legacy SSA)

# ── POZİSYON & HAREKET ───────────────────────────────────────────────────────
RE_POS             = re.compile(r'\\pos\([^)]+\)')       # \pos(320,240)
RE_MOVE            = re.compile(r'\\move\([^)]+\)')      # \move(x1,y1,x2,y2[,t1,t2])
RE_ORG             = re.compile(r'\\org\([^)]+\)')       # \org(320,240)

# ── KARAOKE TAG'LERİ ─────────────────────────────────────────────────────────
# Centisaniye cinsinden süre (100cs = 1 saniye)
RE_K               = re.compile(r'\\k\d+')              # \k50  (anlık renk)
RE_KF              = re.compile(r'\\kf\d+')             # \kf50 (sweep soldan sağa)
RE_KO              = re.compile(r'\\ko\d+')             # \ko50 (border anlık)
RE_KBIG            = re.compile(r'\\K\d+')              # \K50  (= \kf)
RE_KT              = re.compile(r'\\kt\d+')             # \kt100 (absolute start, v4++)
RE_ALL_KARAOKE     = re.compile(r'\\[kK][fot]?\d+')     # hepsi

# ── KIRPMA (CLIPPING) ────────────────────────────────────────────────────────
# Dikdörtgen clip: \clip(x1,y1,x2,y2) — 4 argüman, sayısal
RE_CLIP_RECT       = re.compile(r'\\i?clip\(\s*\d')     # \clip(100,50,400,300)
# Vektör clip: \clip(m x y l x y ...) — 'm' ile başlar (drawing commands)
RE_CLIP_VECTOR     = re.compile(r'\\i?clip\(\s*m\s')    # \clip(m 0 0 l 100 100)
# Sadece \clip (her ikisi)
RE_CLIP_ANY        = re.compile(r'\\i?clip\(')

# ── ÇİZİM MODU ────────────────────────────────────────────────────────────────
# \p1 = çizim modunu aç (scale=1), \p2 = scale=2, ... \p0 = kapat
RE_DRAWING_ON      = re.compile(r'\\p([1-9])\b')        # \p1 \p2 \p4
RE_DRAWING_OFF     = re.compile(r'\\p0\b')              # \p0 (çizim mod kapat)
RE_PBO             = re.compile(r'\\pbo-?[\d.]+')       # \pbo-5 (baseline offset)

# ── FADE / SOLMA ─────────────────────────────────────────────────────────────
RE_FAD             = re.compile(r'\\fad\([^)]+\)')      # \fad(200,400) — basit
RE_FADE            = re.compile(r'\\fade\([^)]+\)')     # \fade(a1,a2,a3,t1,t2,t3,t4)

# ── ANİMASYON ────────────────────────────────────────────────────────────────
# \t([t1,t2,][accel,]<tags>) — animasyon transform
RE_TRANSFORM       = re.compile(r'\\t\([^)]*\)')        # \t(\frz360)
RE_TRANSFORM_FULL  = re.compile(r'\\t\(')               # sadece başlangıç tespiti

# ── SATIR SARMA & RESET ───────────────────────────────────────────────────────
RE_Q               = re.compile(r'\\q[0-3]')            # \q0 \q2 (wrap style)
RE_RESET           = re.compile(r'\\r[^\\}]*')          # \r \rStyleName

# ── INLINE-FX (Karaoke Templater özel) ───────────────────────────────────────
# \-effectname — geçersiz ama Templater tarafından işlenir
RE_INLINE_FX       = re.compile(r'\\-[a-zA-Z][^\\}]*') # \-flash \-pulse

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 2: ÇİZİM KOMUTU PATTERN'LARI
# Kaynak: Aegisub docs/drawing + libass/ass_drawing.c
# ─────────────────────────────────────────────────────────────────────────────

# \p1 içerik alanında GEÇEN çizim komutları:
DRAWING_COMMANDS = {
    'm': 'move to (close path)',        # m x y — başlangıç noktası
    'n': 'move to (open path)',         # n x y — harekete git (kapanmaz)
    'l': 'line to',                     # l x y — düz çizgi
    'b': 'cubic bezier',                # b x1 y1 x2 y2 x3 y3 — bezier eğrisi
    's': 'cubic b-spline',              # s x1 y1 x2 y2 ... — spline
    'p': 'extend b-spline',             # p x y — spline uzatma
    'c': 'close b-spline',              # c — spline kapat
}

# Çizim verisi içeren satır tespiti (hem \p1 çizimi hem \clip(m ...) maskesi)
RE_DRAWING_DATA    = re.compile(r'\b[mnlbspc]\s+-?[\d.]+\s+-?[\d.]+')

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3: \t (TRANSFORM) ANİMASYON İÇİNDE KULLANILABİLEN TAG'LER
# Kaynak: Aegisub docs + libass/ass_parse.c → complex_tag("t") dalı
# NOT: \pos, \move, \clip, \iclip, \org ANIMATE EDİLEMEZ \t ile!
# ─────────────────────────────────────────────────────────────────────────────

ANIMATABLE_TAGS = frozenset({
    'fscx', 'fscy',                     # font ölçeği
    '1c', '2c', '3c', '4c', 'c',       # renkler
    'alpha', '1a', '2a', '3a', '4a',   # alpha kanalları
    'frx', 'fry', 'frz', 'fr',         # rotasyon
    'xbord', 'ybord', 'bord',          # border
    'xshad', 'yshad', 'shad',          # shadow
    'be', 'blur',                       # blur
    'fsp', 'fax', 'fay',               # spacing + shear
    'fs',                               # font size (nadiren animatable)
})

NON_ANIMATABLE_TAGS = frozenset({
    'pos', 'move', 'clip', 'iclip', 'org',  # pozisyon
    'fn', 'fe',                              # font name/encoding
    'an', 'a',                               # hizalama
    'q',                                     # wrap style
    'r',                                     # reset
    'p', 'pbo',                              # çizim modu
    'fad', 'fade',                           # fade (zaten zamanlı)
    'k', 'K', 'kf', 'ko', 'kt',            # karaoke
    'b', 'i', 'u', 's',                     # bold/italic (font değişimi)
})

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 4: FANSUB STYLE İSİMLERİ & SINIFLANDIRMA
# Kaynak: Unanimated typesetting guide + community conventions
# ─────────────────────────────────────────────────────────────────────────────

# Bu style adlarında çeviriye GÖNDEREBİLECEK satırlar (sign/tabela)
SIGN_STYLE_KEYWORDS = frozenset({
    'sign', 'signs', 'sign-',
    'title', 'caption', 'insert',
    'note', 'tlnote', 'tl-note',
    'flashback', 'flash',
    'prev', 'next', 'eyecatch',
    'ep-title', 'episode',
})

# Bu style adlarında ŞARKI olabilir (karaoke), dikkatli ol
KARAOKE_STYLE_KEYWORDS = frozenset({
    'op', 'ed', 'karaoke', 'kara', 'song',
    'opening', 'ending', 'credit', 'credits',
    'lyric', 'lyrics', 'oped',
})

# Bu style adlarında NORMAL DİYALOG var
DIALOGUE_STYLE_KEYWORDS = frozenset({
    'default', 'dialogue', 'main', 'overlap',
    'alt', 'italics', 'italic', 'thought',
    'narration', 'narrator', 'internal',
    'flashback', 'dream',
    'en-', 'tr-', 'jp-',
})


def classify_style(style_name: str) -> str:
    """Style adına göre kategori döndürür: 'sign'|'karaoke'|'dialogue'|'unknown'"""
    s = style_name.lower()
    for kw in SIGN_STYLE_KEYWORDS:
        if kw in s:
            return 'sign'
    for kw in KARAOKE_STYLE_KEYWORDS:
        if kw in s:
            return 'karaoke'
    for kw in DIALOGUE_STYLE_KEYWORDS:
        if kw in s:
            return 'dialogue'
    return 'unknown'


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 5: TAG TEMİZLEME FONKSİYONLARI
# ─────────────────────────────────────────────────────────────────────────────

def strip_all_tags(text: str) -> str:
    """Tüm ASS tag'lerini soy (kapalı + kapanmamış + özel karakterler)."""
    text = RE_TAG_BLOCK.sub('', text)
    text = RE_UNCLOSED_TAG.sub('', text)
    text = text.replace(r'\N', ' ').replace(r'\n', ' ').replace(r'\h', ' ')
    return text.strip()


def tag_to_text_ratio(text: str) -> float:
    """Tag karakter / metin karakter oranı. 5.0+ = ağır typeset."""
    tag_content = ''.join(RE_TAG_BLOCK.findall(text))
    t = len(tag_content)
    m = len(strip_all_tags(text))
    if m == 0:
        return float('inf')
    return t / m


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 6: ÇEVİRİ KARAR FONKSİYONLARI
# ─────────────────────────────────────────────────────────────────────────────

def is_drawing_line(text: str) -> bool:
    r"""\p1/\p2+ çizim modu = pure vector, metin yok."""
    return bool(RE_DRAWING_ON.search(text))


def is_vector_clip_junk(text: str) -> Tuple[bool, str]:
    r"""\\clip/\\iclip(m...) + anlamsız metin kombinasyonu tespiti.

    Yakalanan senaryolar:
      A) boş metin                   → vector_clip_empty
      B) <=2 karakter (l, e, T)      → vector_clip_single_char
      C) tek harf tekrarı (llllll)   → vector_clip_repeat_char
      D) tek kelime + ağır typeset   → vector_clip_title_typeset
         (Örnek: "Track", "Online", "Sword" — OP/ED title segment'leri)
         Koşullar: clip(m) + pos + (fscx≥200 VEYA frz) + ≤8 char + ≤1 kelime
      E) mid-word color-split        → vector_clip_midword_split
         (Örnek: T{\\c&H..&}rack — kelime tag'le ikiye bölünmüş)
    """
    if not RE_CLIP_VECTOR.search(text):
        return False, ''

    ec = RE_TAG_BLOCK.sub('', text)
    ec = RE_UNCLOSED_TAG.sub('', ec).strip()

    # A: boş
    if not ec:
        return True, 'vector_clip_empty'
    # B: 1-2 karakter
    if len(ec) <= 2:
        return True, 'vector_clip_single_char'
    # C: tek harf tekrarı
    if len(set(ec.lower().replace(' ', ''))) <= 1:
        return True, 'vector_clip_repeat_char'

    # D: OP/ED title typeset — tek kelime + ağır görsel tag'ler
    # Koşul: clip(m) ZATEN var + pos VEYA move + (fscx≥200 VEYA frz) + ≤1 kelime + ≤12 char
    has_pos   = bool(re.search(r'\\pos\(', text))
    has_fscx  = bool(re.search(r'\\fscx([2-9]\d{2,}|\d{4,})', text))  # fscx>=200
    has_fscy  = bool(re.search(r'\\fscy([2-9]\d{2,}|\d{4,})', text))  # fscy>=200
    has_frz   = bool(re.search(r'\\frz-?[\d.]+', text))
    is_heavy_typeset = has_pos and (has_fscx or has_fscy or has_frz)
    word_count = len(ec.split())
    if is_heavy_typeset and word_count <= 1 and len(ec) <= 12:
        return True, 'vector_clip_title_typeset'

    # E: mid-word color-split — aynı kelime tag'le ikiye bölünmüş
    # Örnek: raw="}T{\\c&H..&}rack" → ec="Track" ama tag_count/char_count oranı yüksek
    # Tespit: \c veya \1c renk değişimi var + kalan metin tek kelime + büyük harf içeriyor
    has_color_change = bool(re.search(r'\\[1-4]?c&H', text))
    if has_color_change and word_count <= 1 and has_pos and len(ec) <= 15:
        # Büyük harfle başlayan tek kelime + renk split = title typeset
        if ec[0].isupper() and re.match(r'^[A-Za-z]+$', ec):
            return True, 'vector_clip_midword_split'

    return False, ''



def is_karaoke_per_char(text: str) -> Tuple[bool, float]:
    r"""Per-karakter karaoke yoğunluk tespiti (ratio >= 0.33 → per-char)."""
    k_count = len(RE_ALL_KARAOKE.findall(text))
    if k_count == 0:
        return False, 0.0
    clean = strip_all_tags(text)
    char_count = len(clean.replace(' ', ''))
    if char_count == 0:
        return True, float('inf')
    ratio = k_count / char_count
    return ratio >= 0.33, ratio


def has_hard_overrides(text: str) -> bool:
    r"""libass ass_event_has_hard_overrides() eşdeğeri.
    \\pos, \\move, \\clip, \\iclip, \\org, \\pbo, \\p içeriyorsa True.
    """
    return bool(RE_POS.search(text) or RE_MOVE.search(text) or
                RE_CLIP_ANY.search(text) or RE_ORG.search(text) or
                RE_DRAWING_ON.search(text) or RE_PBO.search(text))


def classify_line_translatability(text: str, style: str = '') -> Tuple[str, str]:
    """Pipeline ana karar fonksiyonu.
    Returns: (decision, reason)
    decision: 'skip'|'translate'|'translate_sign'|'translate_karaoke'
    """
    if is_drawing_line(text):
        return 'skip', 'drawing_mode_p1'
    junk, reason = is_vector_clip_junk(text)
    if junk:
        return 'skip', reason
    clean = strip_all_tags(text)
    if not clean:
        return 'skip', 'empty_after_strip'
    if len(clean) < 2:
        return 'skip', 'too_short'
    if not re.search(r'[a-zA-ZğşçöüıİĞŞÇÖÜ\u3040-\u9fff\uac00-\ud7af]', clean):
        return 'skip', 'no_letters'
    # Invisible alpha: \1a&HFF& veya \alpha&HFF& = primary kanal TAMAMEN saydam
    # Bu katmanlar görsel olarak yoktur (maskeleme, glow alt katmanı).
    # NOT: outline/shadow (3a/4a) görünür olabilir, onları kontrol et.
    # Kaynak: ass_content_classifier.py A9 kuralı
    _has_inv_alpha = (
        bool(re.search(r'\\1a&H(FF|ff)&?', text)) or
        bool(re.search(r'\\alpha&H(FF|ff)&?', text))
    )
    if _has_inv_alpha:
        # Outline/shadow hala görünür olabilir, bunlar görsel katman değil
        _has_visible_outline = bool(re.search(r'\\[34]a&H[0-7][0-9A-Fa-f]&?', text))
        if not _has_visible_outline:
            return 'skip', 'invisible_alpha'

    is_pc, ratio = is_karaoke_per_char(text)
    if is_pc and ratio >= 0.8:
        return 'skip', f'per_char_karaoke_{ratio:.2f}'
    if style:
        cat = classify_style(style)
        if cat == 'karaoke':
            # Karaoke stili (ROM, KARA, JPN, ED-ROM, OP-JPN vb.) = cevirme
            # Bu satirlar romaji/Japonca icin, sadece EN stil varsa cevir
            return 'skip', 'karaoke_style_skip'
        if cat == 'sign':
            return 'translate_sign', 'sign_style'
    return 'translate', 'ok'


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 7: EFFECT ALANI — libass/ass_parse.c'den doğrulanan efektler
# ─────────────────────────────────────────────────────────────────────────────

def classify_effect_field(effect: str) -> str:
    """Events Effect alanı → 'banner'|'scroll_up'|'scroll_down'|
    'karaoke_template'|'empty'|'unknown'"""
    if not effect or not effect.strip():
        return 'empty'
    e = effect.strip()
    if e.startswith('Banner;'):
        return 'banner'
    if e.startswith('Scroll up;'):
        return 'scroll_up'
    if e.startswith('Scroll down;'):
        return 'scroll_down'
    if e.startswith('template') or e.startswith('code') or 'fx ' in e:
        return 'karaoke_template'
    return 'unknown'


def should_skip_by_effect(effect: str) -> Tuple[bool, str]:
    """Effect alanına göre çeviriye gitme kararı.
    Karaoke template satırları (Lua kod) ASLA çevrilmez.
    """
    cat = classify_effect_field(effect)
    if cat == 'karaoke_template':
        return True, 'karaoke_template_line'
    return False, cat


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 8: PLACEHOLDER SİSTEMİ
# ─────────────────────────────────────────────────────────────────────────────

PLACEHOLDER_MAP = {
    r'\N': '⏎',
    r'\n': '↵',
    r'\h': '⠀',
    r'\{': '❴',
    r'\}': '❵',
}
PLACEHOLDER_REVERSE = {v: k for k, v in PLACEHOLDER_MAP.items()}


def protect_special_chars(text: str) -> str:
    """\\N \\n \\h → pipeline-safe placeholder."""
    for seq, ph in PLACEHOLDER_MAP.items():
        text = text.replace(seq, ph)
    return text


def restore_special_chars(text: str) -> str:
    """Placeholder → orijinal \\N \\n \\h."""
    for ph, seq in PLACEHOLDER_REVERSE.items():
        text = text.replace(ph, seq)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 9: RENK FORMAT YARDIMCILARI
# ASS: &HAABBGGRR& — BGR sırası, HTML RGB'den tersi!
# ─────────────────────────────────────────────────────────────────────────────

def ass_color_to_rgba(ass_color: str) -> Tuple[int, int, int, int]:
    """&HAABBGGRR& → (R, G, B, A). A=0 opak, A=255 tam şeffaf."""
    s = ass_color.strip().lstrip('&H').rstrip('&').zfill(8)
    aa = int(s[0:2], 16)
    bb = int(s[2:4], 16)
    gg = int(s[4:6], 16)
    rr = int(s[6:8], 16)
    return (rr, gg, bb, aa)


def rgba_to_ass_color(r: int, g: int, b: int, a: int = 0) -> str:
    """(R, G, B, A) → &HAABBGGRR& ASS formatı."""
    return f'&H{a:02X}{b:02X}{g:02X}{r:02X}&'
