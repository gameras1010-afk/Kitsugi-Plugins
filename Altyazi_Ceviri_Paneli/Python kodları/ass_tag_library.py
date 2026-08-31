# ass_tag_library.py
# ─────────────────────────────────────────────────────────────────────────────
# ASS (Advanced SubStation Alpha) Tag Kütüphanesi
# Backend  : ass_tag_parser v2.4.1 (bubblesub/ass_tag_parser)
# Referans : https://aegisub.org/docs/latest/ass_tags/
#            + libass/ass_parse.c (github.com/libass/libass)
#            + unanimated fansub typesetting guide
#
# Desteklenen tag'lerin TAM listesi (Aegisub + libass spec):
#   Metin Stili  : \b \i \u \s \fn \fs \fscx \fscy \fsp \fe
#   Renk/Alpha   : \c \1c \2c \3c \4c \alpha \1a \2a \3a \4a
#   Kenar/Gölge  : \bord \xbord \ybord \shad \xshad \yshad
#   Bulanıklık   : \blur \be
#   Karaoke      : \k \K \kf \ko \kt
#   Konumlandırma: \pos \move \org \an \a
#   Rotasyon     : \frx \fry \frz \fr
#   Eğim(Shear)  : \fax \fay
#   Animasyon    : \t(...)
#   Draw/Clip    : \p \p0 \pbo \clip \iclip (rect + vector)
#   Sarma/Sıfır  : \q \r
#   Özel karakter: \N \n \h
#   Inline-FX    : \-effectname (Karaoke Templater)
#   Effect field : Banner;delay Scroll up;y0;y1;delay Scroll down;...
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations  # Python <3.10 uyumu — MUTLAKA ilk satır
import ass_vendor_setup  # noqa — _vendor/ dizinini path'e ekler
import re
from typing import Dict, List, Optional, Set, Tuple

# ── Kapsamlı ASS Tag Referans Modülü (libass + Aegisub kaynaklı) ──────────────
try:
    from ass_tag_reference import (
        classify_line_translatability,
        classify_style        as atr_classify_style,
        classify_effect_field,
        should_skip_by_effect,
        is_drawing_line,
        is_vector_clip_junk,
        is_karaoke_per_char,
        has_hard_overrides,
        protect_special_chars,
        restore_special_chars,
        ass_color_to_rgba,
        rgba_to_ass_color,
        RE_TAG_BLOCK, RE_UNCLOSED_TAG, RE_CLIP_VECTOR,
        RE_DRAWING_ON, RE_ALL_KARAOKE, RE_CLIP_RECT,
        ANIMATABLE_TAGS, NON_ANIMATABLE_TAGS,
        SIGN_STYLE_KEYWORDS, KARAOKE_STYLE_KEYWORDS,
    )
    _ATR_AVAILABLE = True
except ImportError:
    _ATR_AVAILABLE = False

# ── Kütüphane import ──────────────────────────────────────────────────────────
try:
    import ass_tag_parser as _atp
    _ATP_AVAILABLE = True
except ImportError:
    _ATP_AVAILABLE = False

# ── Regex fallback (ass_tag_parser yoksa) ────────────────────────────────────
_TAG_STRIP_RE  = re.compile(r'\{[^}]*\}')
_DRAW_CMD_RE   = re.compile(r'\b(?:m|n|l|b|s|p|c)\s+-?\d+\s+-?\d+', re.IGNORECASE)
_KARAOKE_RE    = re.compile(r'\\[kK][fFoO]?\d*', re.IGNORECASE)
_KARA_TYPE_RE  = re.compile(r'\\(kf|ko|K|k)(\d*)', re.IGNORECASE)
_ANIM_RE       = re.compile(r'\\t\s*\(', re.IGNORECASE)
_DRAW_TAG_RE   = re.compile(r'\\p\s*[1-9]', re.IGNORECASE)
_POS_RE        = re.compile(r'\\pos\s*\(', re.IGNORECASE)
_MOVE_RE       = re.compile(r'\\move\s*\(', re.IGNORECASE)
_ALIGN_RE      = re.compile(r'\\an?\s*\d', re.IGNORECASE)
_COLOR_RE      = re.compile(r'\\[1-4]?c&H[0-9A-Fa-f]{6}&', re.IGNORECASE)
_ALPHA_RE      = re.compile(r'\\(?:alpha|[1-4]a)&H[0-9A-Fa-f]{2}&', re.IGNORECASE)
_BLUR_RE       = re.compile(r'\\(?:blur|be)\s*[\d.]+', re.IGNORECASE)
_BORD_RE       = re.compile(r'\\(?:bord|xbord|ybord)\s*[\d.]+', re.IGNORECASE)
_SHAD_RE       = re.compile(r'\\(?:shad|xshad|yshad)\s*[\d.]+', re.IGNORECASE)
_FADE_RE       = re.compile(r'\\fad(?:e)?\s*\(', re.IGNORECASE)
_CLIP_RE       = re.compile(r'\\(?:i?clip)\s*\(', re.IGNORECASE)
_ROT_RE        = re.compile(r'\\fr[xyzXYZ]?\s*-?[\d.]+', re.IGNORECASE)
_SHEAR_RE      = re.compile(r'\\fa[xy]\s*-?[\d.]+', re.IGNORECASE)
_FONT_RE       = re.compile(r'\\(?:fn|fs|fscx|fscy|fsp|fe)\b', re.IGNORECASE)
_BOLD_RE       = re.compile(r'\\b\d', re.IGNORECASE)
_ITALIC_RE     = re.compile(r'\\i[01]', re.IGNORECASE)
_RESET_RE      = re.compile(r'\\r(?:\w+)?', re.IGNORECASE)
_WRAP_RE       = re.compile(r'\\q\d', re.IGNORECASE)
_ORG_RE        = re.compile(r'\\org\s*\(', re.IGNORECASE)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TEMEL METİN ÇIKARIMI
# ═══════════════════════════════════════════════════════════════════════════════

def strip_tags(text: str) -> str:
    """Tüm ASS override tag'lerini soyar, temiz metni döndürür.
    \\N \\n satır sonlarını boşluğa, \\h non-breaking space'e çevirir.
    [FIX] Kapanmamış tag fragment'leri de kaldırır: {\c&H... (kapanış } yok)
    """
    text = _TAG_STRIP_RE.sub('', text)
    text = re.sub(r'\{[^}]*$', '', text)  # Kapanmamış tag (satır sonu)
    text = text.replace('\\N', ' ').replace('\\n', ' ').replace('\\h', '\u00A0')
    return text.strip()


def extract_text_atp(text: str) -> str:
    """ass_tag_parser built-in ass_to_plaintext() ile güvenli metin çıkarımı.
    Önce cache'li built-in dener, hata varsa fallback.
    """
    if not _ATP_AVAILABLE:
        return strip_tags(text)
    try:
        # ass_to_plaintext: cache'li, regex-free, %100 spec uyumlu
        result = _atp.ass_to_plaintext(text)
        # Spec: \\N → newline, biz space istiyoruz
        result = result.replace('\n', ' ')
        return result.strip()
    except Exception:
        pass
    # Fallback: manuel parse
    try:
        parsed = _atp.parse_ass(text)
        parts = [item.text for item in parsed if isinstance(item, _atp.AssText)]
        result = ''.join(parts)
        result = result.replace('\\N', ' ').replace('\\n', ' ').replace('\\h', '\u00A0')
        return result.strip()
    except Exception:
        return strip_tags(text)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. TAG PROFİLİ (TagProfile)
# ═══════════════════════════════════════════════════════════════════════════════

class TagProfile:
    """Bir ASS satırının tam tag profilini tutar."""
    __slots__ = [
        'has_draw',       # \p1+ — vector drawing modu
        'has_karaoke',    # \k \K \kf \ko
        'has_animation',  # \t(...)
        'has_position',   # \pos(x,y)
        'has_move',       # \move(x1,y1,x2,y2)
        'has_alignment',  # \an \a
        'has_color',      # \1c \2c \3c \4c \c
        'has_alpha',      # \alpha \1a \2a \3a \4a
        'has_blur',       # \blur \be
        'has_border',     # \bord \xbord \ybord
        'has_shadow',     # \shad \xshad \yshad
        'has_fade',       # \fad \fade
        'has_clip',       # \clip \iclip
        'has_rotation',   # \frx \fry \frz \fr
        'has_shear',      # \fax \fay
        'has_font',       # \fn \fs \fscx \fscy \fsp \fe
        'has_bold',       # \b
        'has_italic',     # \i
        'has_reset',      # \r
        'has_origin',     # \org
        'has_tags',       # herhangi bir tag mevcut
        'plain_text',     # soyulmuş temiz metin
        'tag_names',      # tespit edilen AssTag sınıf adları listesi
        'karaoke_type',   # 'timing'|'fill'|'outline'|None
    ]

    def __init__(self):
        for slot in self.__slots__:
            if slot == 'plain_text':
                setattr(self, slot, '')
            elif slot == 'tag_names':
                setattr(self, slot, [])
            elif slot == 'karaoke_type':
                setattr(self, slot, None)
            else:
                setattr(self, slot, False)

    def __repr__(self):
        active = [s for s in self.__slots__
                  if s not in ('plain_text','tag_names','karaoke_type')
                  and getattr(self, s)]
        return f"<TagProfile text={repr(self.plain_text[:30])} flags={active}>"


def analyze(text: str) -> TagProfile:
    """Bir ASS satırını tam olarak analiz eder, TagProfile döndürür."""
    p = TagProfile()
    p.plain_text = strip_tags(text)
    p.has_tags   = bool(_TAG_STRIP_RE.search(text))

    if not p.has_tags:
        return p

    # ── ass_tag_parser ile yüksek güvenilirlik ────────────────────────────────
    if _ATP_AVAILABLE:
        try:
            parsed = _atp.parse_ass(text)
            tag_names = []
            for item in parsed:
                if not isinstance(item, _atp.AssTag):
                    continue
                cls = type(item).__name__
                tag_names.append(cls)

                if   cls == 'AssTagDraw':                                 p.has_draw      = True
                elif cls == 'AssTagKaraoke':
                    p.has_karaoke = True
                    # karaoke type tespiti meta.text üzerinden
                    if item.meta:
                        m = _KARA_TYPE_RE.search(item.meta.text)
                        if m and p.karaoke_type is None:
                            p.karaoke_type = KARA_TYPES.get(m.group(1), 'timing')
                elif cls == 'AssTagAnimation':                            p.has_animation = True
                elif cls == 'AssTagPosition':                             p.has_position  = True
                elif cls == 'AssTagMove':                                 p.has_move      = True
                elif cls == 'AssTagAlignment':                            p.has_alignment = True
                elif cls == 'AssTagColor':                                p.has_color     = True
                elif cls == 'AssTagAlpha':                                p.has_alpha     = True
                elif cls in ('AssTagBlurEdgesGauss','AssTagBlurEdges'):   p.has_blur      = True
                elif cls in ('AssTagBorder','AssTagXBorder','AssTagYBorder'): p.has_border = True
                elif cls in ('AssTagShadow','AssTagXShadow','AssTagYShadow'): p.has_shadow = True
                elif cls in ('AssTagFade','AssTagFadeComplex'):           p.has_fade      = True
                elif cls in ('AssTagClipRectangle','AssTagClipVector'):   p.has_clip      = True
                elif cls in ('AssTagXRotation','AssTagYRotation','AssTagZRotation'): p.has_rotation = True
                elif cls in ('AssTagXShear','AssTagYShear'):              p.has_shear     = True
                elif cls in ('AssTagFontName','AssTagFontSize','AssTagFontXScale',
                             'AssTagFontYScale','AssTagFontEncoding','AssTagLetterSpacing'):
                                                                          p.has_font      = True
                elif cls == 'AssTagBold':                                 p.has_bold      = True
                elif cls == 'AssTagItalic':                               p.has_italic    = True
                elif cls == 'AssTagResetStyle':                           p.has_reset     = True
                elif cls == 'AssTagRotationOrigin':                       p.has_origin    = True

            p.tag_names = tag_names
            return p
        except Exception:
            pass  # regex fallback'e düş

    # ── Regex fallback ────────────────────────────────────────────────────────
    raw = text
    p.has_draw      = bool(_DRAW_TAG_RE.search(raw))
    p.has_karaoke   = bool(_KARAOKE_RE.search(raw))
    p.has_animation = bool(_ANIM_RE.search(raw))
    p.has_position  = bool(_POS_RE.search(raw))
    p.has_move      = bool(_MOVE_RE.search(raw))
    p.has_alignment = bool(_ALIGN_RE.search(raw))
    p.has_color     = bool(_COLOR_RE.search(raw))
    p.has_alpha     = bool(_ALPHA_RE.search(raw))
    p.has_blur      = bool(_BLUR_RE.search(raw))
    p.has_border    = bool(_BORD_RE.search(raw))
    p.has_shadow    = bool(_SHAD_RE.search(raw))
    p.has_fade      = bool(_FADE_RE.search(raw))
    p.has_clip      = bool(_CLIP_RE.search(raw))
    p.has_rotation  = bool(_ROT_RE.search(raw))
    p.has_shear     = bool(_SHEAR_RE.search(raw))
    p.has_font      = bool(_FONT_RE.search(raw))
    p.has_bold      = bool(_BOLD_RE.search(raw))
    p.has_italic    = bool(_ITALIC_RE.search(raw))
    p.has_reset     = bool(_RESET_RE.search(raw))
    p.has_origin    = bool(_ORG_RE.search(raw))
    if p.has_karaoke:
        m = _KARA_TYPE_RE.search(raw)
        if m:
            p.karaoke_type = KARA_TYPES.get(m.group(1), 'timing')
    return p


# ═══════════════════════════════════════════════════════════════════════════════
# 3. KRİTİK SORU FONKSİYONLARI (pipeline için)
# ═══════════════════════════════════════════════════════════════════════════════

def is_draw_event(text: str) -> bool:
    r"""\\p1 (veya daha yüksek) ile çizilmiş vector art mı?
    Bu eventlerin text alanı metin değil drawing komutu içerir.
    Kesinlikle çevrilmemeli.
    """
    # \p tag kontrolü
    if _DRAW_TAG_RE.search(text):
        return True
    # Tag'siz raw draw command kontrolü
    clean = _TAG_STRIP_RE.sub('', text).strip()
    if _DRAW_CMD_RE.search(clean) and len(re.sub(r'[^a-zA-Z]', '', clean)) < 8:
        return True
    return False


def is_karaoke_event(text: str) -> bool:
    r"""\\k, \\K, \\kf, \\ko karaoke tag'i içeriyor mu?"""
    return bool(_KARAOKE_RE.search(text))


def is_animated_event(text: str) -> bool:
    r"""\\t(...) animasyon tag'i içeriyor mu?"""
    return bool(_ANIM_RE.search(text))


def is_pure_fx_event(text: str) -> bool:
    """Draw + animasyon kombinasyonu → saf görsel efekt satırı (çevrilmez)."""
    return is_draw_event(text) and is_animated_event(text)


def has_translatable_text(text: str, min_len: int = 3) -> bool:
    """Satırda çevrilebilir gerçek metin var mı?
    · Draw event → False
    · Tag soyulmuş metin min_len'den kısa → False
    · En az bir harf yoksa → False
    """
    if is_draw_event(text):
        return False
    clean = strip_tags(text)
    if len(clean) < min_len:
        return False
    return bool(re.search(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]', clean))


def should_skip_translation(text: str, style: str = '') -> Tuple[bool, str]:
    """Pipeline fast-path: bu satır çeviriye GİRMEMELİ mi?

    Returns:
        (skip: bool, reason: str)
        reason: 'draw'|'drawing_p1'|'empty'|'too_short'|'no_letters'|
                'vector_clip_letter'|'vector_clip_repeat'|
                'iclip_typeset_junk'|'ok'
    """
    if is_draw_event(text):
        return True, 'draw'

    # [NEW] \p1/\p2+ çizim modu — içerik tamamen vektör, metin yok
    if re.search(r'\\p[1-9]\b', text):
        return True, 'drawing_p1'

    clean = strip_tags(text).strip()  # kapanmamış tag'ler de soyuldu
    if not clean:
        return True, 'empty'
    if len(clean) < 2:
        return True, 'too_short'

    # [NEW] Per-karakter typeset savunmasi (GENEL KURAL):
    # {\blur\frz\pos(...)}A{*\frz334.024}o  VEYA  {\fs22.5}I {*\fs22.356}B{*\fs22.284}e ...
    # Tag ne olursa olsun: tag bloklari arasi TUM parcalar <=2 kar. VE 4+ parca → SKIP.
    _pc_lib = [f.strip() for f in re.split(r'\{[^}]*\}', text) if f.strip()]
    if len(_pc_lib) >= 4 and all(len(f) <= 2 for f in _pc_lib):
        return True, 'per_char_typeset'

    # [NEW] \clip(m) / \iclip(m) vektör kırpma + typeset junk tespiti
    # Kapsanan senaryolar:
    #   A) tek harf:        ec='l'       → len<=2
    #   B) tek harf tekrar: ec='lllll...' → unique_chars<=1
    # Gerçek tabela metni: 'Blade Throw' → unique_chars>1 → geçer
    if re.search(r'\\i?clip\(m\s', text):
        _ec = re.sub(r'\{[^}]*\}', '', text)   # kapalı tag'ler
        _ec = re.sub(r'\{[^}]*$',  '', _ec)     # kapanmamış tag
        _ec = _ec.strip()
        if not _ec or len(_ec) <= 2:
            return True, 'vector_clip_letter'
        if len(set(_ec.lower().replace(' ', ''))) <= 1:
            return True, 'vector_clip_repeat'

    # [NEW] Tag/metin oranı çok yüksek → pure typeset junk (son savunma katmanı)
    # Classifier'dan önce çalışır; her ikisi de yakalamalı.
    _tg_blocks = re.findall(r'\{[^}]*\}', text)
    _tg_len = sum(len(t) for t in _tg_blocks)
    _cl_len = len(clean)
    if _cl_len > 0 and _tg_len / _cl_len >= 8 and _cl_len <= 15:
        return True, 'tag_text_ratio_junk'

    if not re.search(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]', clean):
        return True, 'no_letters'
    return False, 'ok'


# ═══════════════════════════════════════════════════════════════════════════════
# 4. TAG DÖNÜŞÜM ARAÇLARI
# ═══════════════════════════════════════════════════════════════════════════════

def strip_animation_tags(text: str, keep_static: bool = True) -> str:
    r"""Animasyon tag'lerini soyar, statik tag'leri isteğe bağlı korur.
    keep_static=True → \\pos, \\an, renk, font gibi sabit tag'leri koru.
    """
    if not keep_static:
        return strip_tags(text)

    result_prefix = ''
    for block in re.finditer(r'\{[^}]*\}', text):
        block_text = block.group(0)
        # Animasyon komutları içermiyor mu?
        if not re.search(r'\\t\s*\(|\\blur|\\bord|\\move\s*\(|\\fad|\\fade|\\shad', block_text, re.IGNORECASE):
            if re.search(r'\\pos\s*\(|\\an\d|\\[1-4]?c&H|\\fs\d|\\fn', block_text, re.IGNORECASE):
                result_prefix += block_text

    plain = strip_tags(text)
    return result_prefix + plain


def remove_animation_tags_compose(text: str) -> str:
    """ass_tag_parser round-trip ile animasyon tag'lerini çıkarır.
    \\t(...) eventleri kaldırılır, diğer tag'ler korunarak geri compose edilir.
    En temiz ve güvenilir yöntem.
    """
    if not _ATP_AVAILABLE:
        return strip_animation_tags(text)
    try:
        parsed = _atp.parse_ass(text)
        filtered = [item for item in parsed
                    if not isinstance(item, _atp.AssTagAnimation)]
        return _atp.compose_ass(filtered)
    except Exception:
        return strip_animation_tags(text)


def extract_static_tags(text: str) -> Tuple[str, str]:
    r"""Statik tag'leri ve temiz metni ayrı ayrı döndürür.

    Returns:
        (static_tag_prefix, plain_text)
        static_tag_prefix : \\pos \\an renk vb. (animasyon hariç)
        plain_text         : tag'siz temiz metin
    """
    if not _ATP_AVAILABLE:
        return '', strip_tags(text)
    try:
        parsed = _atp.parse_ass(text)
        static_items = []
        text_parts   = []

        ANIMATION_TYPES = (
            _atp.AssTagAnimation,
            _atp.AssTagMove,
            _atp.AssTagFade,
            _atp.AssTagFadeComplex,
        )
        STATIC_KEEP = (
            _atp.AssTagPosition,
            _atp.AssTagAlignment,
            _atp.AssTagColor,
            _atp.AssTagAlpha,
            _atp.AssTagFontSize,
            _atp.AssTagRotationOrigin,
            _atp.AssTagBorder,
            _atp.AssTagShadow,
        )

        in_block   = False
        block_buf  = []

        for item in parsed:
            if isinstance(item, _atp.AssTagListOpening):
                in_block  = True
                block_buf = [item]
            elif isinstance(item, _atp.AssTagListEnding):
                in_block = False
                keep = [i for i in block_buf if isinstance(i, STATIC_KEEP)]
                if keep:
                    static_items.extend([block_buf[0]] + keep + [item])
            elif isinstance(item, _atp.AssText):
                text_parts.append(item.text)
            elif in_block:
                block_buf.append(item)

        prefix = _atp.compose_ass(static_items) if static_items else ''
        plain  = ' '.join(text_parts).replace('\\N', ' ').replace('\\n', ' ').strip()
        return prefix, plain
    except Exception:
        return '', strip_tags(text)


def get_draw_commands(text: str) -> Optional[List[str]]:
    r"""\\p1 ile etkinleştirilen draw command'leri döndürür.
    Draw event değilse None döner.
    """
    if not is_draw_event(text):
        return None
    if _ATP_AVAILABLE:
        try:
            parsed = _atp.parse_ass(text)
            for item in parsed:
                if isinstance(item, _atp.AssTagDraw) and hasattr(item, 'path') and item.path:
                    return [_atp.compose_draw_commands(item.path)]
        except Exception:
            pass
    clean = _TAG_STRIP_RE.sub('', text).strip()
    return clean.split() if clean else []


# ═══════════════════════════════════════════════════════════════════════════════
# 5. KARAOKE ARAÇLARI
# ═══════════════════════════════════════════════════════════════════════════════

# Karaoke tipleri:
#   \k   → 'timing'  — fill başta sıfır
#   \K   → 'fill'    — \kf ile aynı (alias)
#   \kf  → 'fill'    — soldan sağa dolum animasyonu
#   \ko  → 'outline' — sadece kontur, fill yok
KARA_TYPES: Dict[str, str] = {
    'k':  'timing',
    'K':  'fill',
    'kf': 'fill',
    'ko': 'outline',
}


def get_karaoke_text(text: str) -> str:
    r"""Karaoke tag'li satırdan temiz metni çıkarır."""
    return extract_text_atp(text)


def get_karaoke_type(text: str) -> Optional[str]:
    r"""Satırdaki karaoke tipini döndürür: 'timing'|'fill'|'outline'|None."""
    m = _KARA_TYPE_RE.search(text)
    if not m:
        return None
    return KARA_TYPES.get(m.group(1), 'timing')


def count_karaoke_syllables(text: str) -> int:
    r"""Bir karaoke satırındaki hece/\\k tag sayısını döndürür."""
    return len(_KARAOKE_RE.findall(text))


def is_letter_by_letter_karaoke(text: str) -> bool:
    """Harf/hece bazlı karaoke mi (event başına 1-2 karakter)?"""
    clean = strip_tags(text)
    return len(clean.strip()) <= 2


def is_fullline_karaoke(text: str, word_threshold: int = 3) -> bool:
    """Tam cümle içeren karaoke satırı mı (3+ kelime)?"""
    clean = strip_tags(text)
    return len(clean.split()) >= word_threshold


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SINIFLANDIRMA SABİTLERİ
# ═══════════════════════════════════════════════════════════════════════════════

TAG_CATEGORIES: Dict[str, str] = {
    # Karaoke
    'AssTagKaraoke':         'karaoke',
    # Animasyon (zaman bazlı değişim)
    'AssTagAnimation':       'animation',
    'AssTagMove':            'animation',
    'AssTagFade':            'animation',
    'AssTagFadeComplex':     'animation',
    # Draw (vector art)
    'AssTagDraw':            'draw',
    'AssTagBaselineOffset':  'draw',
    # Pozisyon / Düzen
    'AssTagPosition':        'layout',
    'AssTagAlignment':       'layout',
    'AssTagRotationOrigin':  'layout',
    'AssTagClipRectangle':   'layout',
    'AssTagClipVector':      'layout',
    # Renk / Görsel
    'AssTagColor':           'visual',
    'AssTagAlpha':           'visual',
    'AssTagBlurEdgesGauss':  'visual',
    'AssTagBlurEdges':       'visual',
    'AssTagBorder':          'visual',
    'AssTagXBorder':         'visual',
    'AssTagYBorder':         'visual',
    'AssTagShadow':          'visual',
    'AssTagXShadow':         'visual',
    'AssTagYShadow':         'visual',
    # Font
    'AssTagFontName':        'font',
    'AssTagFontSize':        'font',
    'AssTagFontXScale':      'font',
    'AssTagFontYScale':      'font',
    'AssTagFontEncoding':    'font',
    'AssTagLetterSpacing':   'font',
    # Metin stili
    'AssTagBold':            'style',
    'AssTagItalic':          'style',
    'AssTagUnderline':       'style',
    'AssTagStrikeout':       'style',
    'AssTagWrapStyle':       'style',
    'AssTagResetStyle':      'style',
    # Rotasyon / Eğim
    'AssTagXRotation':       'rotation',
    'AssTagYRotation':       'rotation',
    'AssTagZRotation':       'rotation',
    'AssTagXShear':          'rotation',
    'AssTagYShear':          'rotation',
}

TRANSLATION_BLOCKING_TAGS: Set[str] = {'draw'}
TRANSLATION_PRESERVE_TAGS: Set[str] = {'layout', 'visual'}


def get_tag_summary(text: str) -> Dict[str, List[str]]:
    """Satırdaki tag'leri kategoriye göre gruplar.

    Returns:
        {'karaoke': [...], 'animation': [...], 'visual': [...], ...}
    """
    result: Dict[str, List[str]] = {}
    if not _ATP_AVAILABLE:
        return result
    try:
        parsed = _atp.parse_ass(text)
        for item in parsed:
            if isinstance(item, _atp.AssTag):
                cls = type(item).__name__
                cat = TAG_CATEGORIES.get(cls, 'other')
                result.setdefault(cat, []).append(cls)
    except Exception:
        pass
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 7. KAYNAK BİLGİSİ
# ═══════════════════════════════════════════════════════════════════════════════

_LIBRARY_INFO = {
    'backend':    'ass_tag_parser' if _ATP_AVAILABLE else 'regex-only',
    'version':    '2.4.1'          if _ATP_AVAILABLE else 'N/A',
    'source':     'https://github.com/bubblesub/ass_tag_parser',
    'reference':  'https://aegisub.org/docs/latest/ass_tags/',
    'tag_count':  len(TAG_CATEGORIES),
}

# ═══════════════════════════════════════════════════════════════════════════════
# 8. RENK / ALPHA YARDIMCI FONKSiYONLARI (pysubs2 + PyonFX)
# ═══════════════════════════════════════════════════════════════════════════════
# ASS renk formati: &HBBGGRR& (B=blue G=green R=red, her biri 2 hex digit)
# Alpha format : &HXX& (00=tam opak, FF=tam saydam)

try:
    from pyonfx import Convert as _PFX_Convert
    _PFX_AVAILABLE = True
except ImportError:
    _PFX_AVAILABLE = False

try:
    from pysubs2 import Color as _P2_Color
    _P2_AVAILABLE = True
except ImportError:
    _P2_AVAILABLE  = False

_ASS_COLOR_RE = re.compile(r'&H([0-9A-Fa-f]{6})&')
_ASS_ALPHA_RE2 = re.compile(r'&H([0-9A-Fa-f]{2})&')


def ass_color_to_rgb(ass_color: str) -> Tuple[int, int, int]:
    """ASS renk string'ini (\\&HBBGGRR\\&) RGB tuple'a çevirir.

    >>> ass_color_to_rgb('&H00FF00&')   # pure green in ASS BGR
    (0, 255, 0)
    >>> ass_color_to_rgb('&H0000FF&')   # pure red in ASS BGR
    (255, 0, 0)
    """
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.color_ass_to_rgb(ass_color)
        except Exception:
            pass
    m = _ASS_COLOR_RE.search(ass_color)
    if not m:
        return (0, 0, 0)
    hex6 = m.group(1)  # BBGGRR
    b = int(hex6[0:2], 16)
    g = int(hex6[2:4], 16)
    r = int(hex6[4:6], 16)
    return (r, g, b)


def rgb_to_ass_color(r: int, g: int, b: int) -> str:
    """RGB değerlerini ASS renk string'ine (&HBBGGRR&) çevirir."""
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.color_rgb_to_ass((r, g, b))
        except Exception:
            pass
    return f'&H{b:02X}{g:02X}{r:02X}&'


def ass_color_to_hsv(ass_color: str) -> Tuple[int, int, int]:
    """ASS renk string'ini HSV'ye çevirir."""
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.color_ass_to_hsv(ass_color)
        except Exception:
            pass
    r, g, b = ass_color_to_rgb(ass_color)
    return _rgb_to_hsv(r, g, b)


def _rgb_to_hsv(r: int, g: int, b: int) -> Tuple[int, int, int]:
    """Saf Python HSV dönüşümü (PyonFX fallback)."""
    rf, gf, bf = r/255.0, g/255.0, b/255.0
    mx, mn = max(rf,gf,bf), min(rf,gf,bf)
    diff = mx - mn
    v = int(mx * 100)
    s = int((diff / mx * 100) if mx != 0 else 0)
    if diff == 0:
        h = 0
    elif mx == rf:
        h = int(60 * ((gf-bf)/diff % 6))
    elif mx == gf:
        h = int(60 * ((bf-rf)/diff + 2))
    else:
        h = int(60 * ((rf-gf)/diff + 4))
    return (h % 360, s, v)


def ass_alpha_to_dec(ass_alpha: str) -> int:
    """ASS alpha string'ini (&HXX&) 0-255 decimal'e çevirir.
    0 = tam opak, 255 = tam saydam.
    """
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.alpha_ass_to_dec(ass_alpha)
        except Exception:
            pass
    m = _ASS_ALPHA_RE2.search(ass_alpha)
    return int(m.group(1), 16) if m else 0


def dec_to_ass_alpha(dec: int) -> str:
    """0-255 decimal alpha'yı ASS alpha string'ine (&HXX&) çevirir."""
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.alpha_dec_to_ass(dec)
        except Exception:
            pass
    return f'&H{max(0, min(255, int(dec))):02X}&'


def blend_ass_colors(color1: str, color2: str, pct: float) -> str:
    """İki ASS rengi arasında lineer interpolasyon yapar.

    Args:
        pct: 0.0 = %100 color1, 1.0 = %100 color2
    """
    r1, g1, b1 = ass_color_to_rgb(color1)
    r2, g2, b2 = ass_color_to_rgb(color2)
    r = int(r1 + (r2-r1)*pct)
    g = int(g1 + (g2-g1)*pct)
    b = int(b1 + (b2-b1)*pct)
    return rgb_to_ass_color(r, g, b)


def pysubs2_color_to_ass(color) -> str:
    """pysubs2.Color nesnesinden ASS renk string'ine çevirir."""
    if _P2_AVAILABLE and isinstance(color, _P2_Color):
        return f'&H{color.b:02X}{color.g:02X}{color.r:02X}&'
    return '&H000000&'


def pysubs2_color_to_ass_alpha(color) -> str:
    """pysubs2.Color'dan alpha çıkarır (&HXX&)."""
    if _P2_AVAILABLE and isinstance(color, _P2_Color):
        return f'&H{color.a:02X}&'
    return '&H00&'


# ═══════════════════════════════════════════════════════════════════════════════
# 9. ZAMAN YARDIMCI FONKSiYONLARI (PyonFX + pysubs2)
# ═══════════════════════════════════════════════════════════════════════════════

def ms_to_ass_time(ms: int) -> str:
    """Millisecond'u ASS zaman damgasına (0:00:00.00) çevirir."""
    if _PFX_AVAILABLE:
        try:
            return _PFX_Convert.time(ms)
        except Exception:
            pass
    ms = max(0, int(ms))
    h  = ms  // 3600000
    ms %= 3600000
    m  = ms  // 60000
    ms %= 60000
    s  = ms  // 1000
    cs = (ms % 1000) // 10
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def ass_time_to_ms(ts: str) -> int:
    """ASS zaman damgasını (0:00:00.00) millisecond'a çevirir."""
    if _PFX_AVAILABLE:
        try:
            result = _PFX_Convert.time(ts)
            if isinstance(result, int):
                return result
        except Exception:
            pass
    # Manuel parse: H:MM:SS.cs
    ts = ts.strip()
    m = re.match(r'(\d+):(\d+):(\d+)[.,](\d+)', ts)
    if not m:
        return 0
    h, mi, s, cs = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    return (h*3600 + mi*60 + s)*1000 + cs*10


def ms_to_frames(ms: int, fps: float = 23.976) -> int:
    """Millisecond'u frame numarasına çevirir."""
    return int(ms * fps / 1000)


def frames_to_ms(frames: int, fps: float = 23.976) -> int:
    """Frame numarasını millisecond'a çevirir."""
    return int(frames * 1000 / fps)


def karaoke_cs_to_ms(centiseconds: int) -> int:
    r"""\\k tag'i centisecond değerini millisecond'a çevirir.
    ASS formatında \\k100 = 1000ms = 1 saniye.
    """
    return centiseconds * 10


def ms_to_karaoke_cs(ms: int) -> int:
    r"""Millisecond'u \\k tag centisecond değerine çevirir."""
    return ms // 10


# ═══════════════════════════════════════════════════════════════════════════════
# 10. INTERPOLASYON + HIZLANMA (PyonFX Utils)
# ═══════════════════════════════════════════════════════════════════════════════
# PyonFX easing fonksiyonlari:
# 'in_back', 'out_back', 'in_out_back',
# 'in_bounce', 'out_bounce', 'in_out_bounce',
# 'in_circ', 'out_circ', 'in_out_circ',
# 'in_cubic', 'out_cubic', 'in_out_cubic',
# 'in_elastic', 'out_elastic', 'in_out_elastic',
# 'in_expo', 'out_expo', 'in_out_expo',
# 'in_quad', 'out_quad', 'in_out_quad',
# 'in_quart', 'out_quart', 'in_out_quart',
# 'in_quint', 'out_quint', 'in_out_quint',
# 'in_sine', 'out_sine', 'in_out_sine'

try:
    from pyonfx import Utils as _PFX_Utils
    _PFX_UTILS_AVAILABLE = True
except ImportError:
    _PFX_UTILS_AVAILABLE = False


def interpolate_value(pct: float, val1, val2, acc=1.0):
    """iki değer arasında interpolasyon yapar.

    val1/val2: sayı (int/float), ASS renk string'i (&HBBGGRR&),
               veya ASS alpha string'i (&HXX&)
    acc: hızlanma katsayısı (1.0=lineer) veya PyonFX easing ismi

    >>> interpolate_value(0.5, 0, 100)          -> 50.0
    >>> interpolate_value(0.5, '&H0000FF&', '&HFF0000&')  -> mix renk
    """
    if _PFX_UTILS_AVAILABLE:
        try:
            return _PFX_Utils.interpolate(pct, val1, val2, acc)
        except Exception:
            pass
    # Fallback: lineer interpolasyon
    if isinstance(val1, str) and isinstance(val2, str):
        # Renk veya alpha interpolasyon
        if _ASS_COLOR_RE.search(val1):
            r1,g1,b1 = ass_color_to_rgb(val1)
            r2,g2,b2 = ass_color_to_rgb(val2)
            return rgb_to_ass_color(
                int(r1+(r2-r1)*pct), int(g1+(g2-g1)*pct), int(b1+(b2-b1)*pct)
            )
        if _ASS_ALPHA_RE2.search(val1):
            a1 = ass_alpha_to_dec(val1)
            a2 = ass_alpha_to_dec(val2)
            return dec_to_ass_alpha(int(a1 + (a2-a1)*pct))
    return val1 + (val2 - val1) * pct


def accelerate_pct(pct: float, acc=1.0) -> float:
    """Bir yüzde değerine hızlanma fonksiyonu uygular.

    acc: float (1.0=lineer, >1.0=yavaş başla hızlı bitir)
         veya PyonFX easing ismi: 'in_quad', 'out_sine', vb.
    """
    if _PFX_UTILS_AVAILABLE:
        try:
            return _PFX_Utils.accelerate(pct, acc)
        except Exception:
            pass
    if isinstance(acc, (int, float)):
        return pct ** acc
    return pct  # bilinmeyen easing fallback


# ═══════════════════════════════════════════════════════════════════════════════
# 11. KAYNAK BILGiSi
# ═══════════════════════════════════════════════════════════════════════════════

    """Kütüphane bilgilerini yazdırır."""
    print(f"[ASSTagLib] Backend : {_LIBRARY_INFO['backend']} v{_LIBRARY_INFO['version']}")
    print(f"[ASSTagLib] Tag sayısı: {_LIBRARY_INFO['tag_count']}")
    print(f"[ASSTagLib] Kaynak  : {_LIBRARY_INFO['source']}")
    print(f"[ASSTagLib] Ref     : {_LIBRARY_INFO['reference']}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST (python ass_tag_library.py)
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    library_info()
    print()

    # ── Temel testler ─────────────────────────────────────────────────────────
    TESTS = [
        (r'{\k50}N{\k30}o {\k40}one',                   'Karaoke \k hece'),
        (r'{\kf500}Ma{\kf300}gi{\kf200}cal',             'Karaoke \kf fill'),
        (r'{\ko100}Out{\ko100}line',                     'Karaoke \ko outline'),
        (r'{\p1}m 0 0 l 100 0 l 100 100',               'Draw \p1 vector'),
        (r'm 0 0 m 100 100 N m 0 0 m 100 100 o',        'Raw draw cmd'),
        (r'{\t(0,500,\blur10\bord5)}glow text',          'Animasyon \t'),
        (r'{\pos(640,360)\c&H00FFFF&}Hello World',       'Pozisyon + renk'),
        (r'{\an8\blur3}Dialogue',                        'Statik + blur'),
        (r'{\fad(200,300)\pos(640,360)}Fade in',         'Fade + pos'),
        (r'{\1c&H0000FF&\3c&HFFFFFF&\bord2}Colored',    'Multi-color+bord'),
        (r'{\frz-30\pos(320,180)}Rotated',               'Rotasyon + pos'),
        (r'{\fax0.2\fay-0.1}Sheared text',              'Shear'),
        (r'{\r}Reset style',                             'Reset'),
        (r'Even if the world hasn\'t forgotten yet',     'Temiz metin'),
        (r'{\alpha&H80&\pos(640,400)}Transparent',       'Alpha + pos'),
    ]

    print('=' * 65)
    for text, label in TESTS:
        p    = analyze(text)
        skip, reason = should_skip_translation(text)
        ktype = get_karaoke_type(text)
        syl   = count_karaoke_syllables(text) if p.has_karaoke else 0

        print(f"[{label}]")
        print(f"  Metin   : {repr(p.plain_text[:40])}")
        active = [s[4:] for s in TagProfile.__slots__
                  if s.startswith('has_') and s not in ('has_tags',) and getattr(p, s)]
        print(f"  Aktif   : {active}")
        print(f"  Skip    : {skip} ({reason})")
        if ktype:
            print(f"  KaraTyp : {ktype}  syllables={syl}")
        if p.tag_names:
            print(f"  Tags    : {p.tag_names[:5]}")
        print()

    # ── Round-trip test ──────────────────────────────────────────────────────
    print('── Round-trip: animasyon at, pozisyon koru ──')
    orig = r'{\t(0,500,\blur10\bord5)\pos(640,360)}Hello World'
    composed = remove_animation_tags_compose(orig)
    prefix, plain = extract_static_tags(orig)
    print(f"  Orig    : {orig}")
    print(f"  Composed: {composed}")
    print(f"  Prefix  : {repr(prefix)}")
    print(f"  Plain   : {repr(plain)}")
