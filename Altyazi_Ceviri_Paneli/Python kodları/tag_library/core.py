"""
tag_library/core.py
===================
TagProfile, analyze.
"""
from __future__ import annotations  # Python <3.10 uyumu — MUTLAKA ilk satır
import re
from typing import Optional, List, Dict, Tuple, Set

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


