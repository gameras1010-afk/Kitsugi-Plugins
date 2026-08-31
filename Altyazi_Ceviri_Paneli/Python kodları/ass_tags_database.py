r"""
ass_tags_database.py
====================
ASS Override Tag Veritabanı — Nexus Pro Translation Engine

Kaynak:
  - bubblesub/ass_tag_parser v2.4.1 — ass_parser.py (_PARSING_MAP tablosu)
    https://github.com/bubblesub/ass_tag_parser/blob/master/ass_tag_parser/ass_parser.py
  - bubblesub/ass_tag_parser — ass_struct.py (AssTag sınıfları)
    https://github.com/bubblesub/ass_tag_parser/blob/master/ass_tag_parser/ass_struct.py
  - Aegisub Resmi ASS Dokümantasyonu
    https://aegisub.org/docs/latest/ass_tags/

Bu dosya DOĞRUDAN yukarıdaki kaynaklardan kopyalanmış ve çeviri pipeline için
sınıflandırma (skip/translate/styling) bilgisi eklenmiştir.

Kategori Açıklamaları:
  'drawing'    → \p tag'i — çizim modu, hiçbir zaman çevrilmez
  'karaoke'    → \k \K \kf \ko — karaoke zamanlama, hiçbir zaman çevrilmez
  'position'   → \pos \move \org — konumlama, içerik varsa sign modu
  'clip'       → \clip \iclip — kırpma maskesi, görsel efekt
  'animation'  → \t \fad \fade — animasyon/geçiş
  'formatting' → \b \i \u \s — temel yazı biçimi, çeviriyle birlikte korunur
  'font'       → \fn \fs \fscx \fscy \fsp \fe — yazı tipi
  'color'      → \c \1c \2c \3c \4c — renk
  'alpha'      → \alpha \1a \2a \3a \4a — saydamlık
  'border'     → \bord \xbord \ybord — kenarlık
  'shadow'     → \shad \xshad \yshad — gölge
  'blur'       → \blur \be — kenar yumuşatma
  'rotation'   → \frx \fry \frz \fr — döndürme
  'shear'      → \fax \fay — eğme (italik benzeri)
  'alignment'  → \an \a — hizalama
  'style'      → \r — stil sıfırlama
  'wrapstyle'  → \q — satır sarma
  'baseline'   → \pbo — taban çizgisi kaydırma

skip_if_dominant:
  True  → Bu tag türü satırın baskın özelliğiyse çeviri atlanır
  False → Sadece biçimlendirme, çeviriyle birlikte korunur

visual_only:
  True  → Bu tag satırı görsel-ağırlıklı yapar (metin anlamını değiştirmez)
  False → Metin anlam içeriğine dokunmaz
"""

# =============================================================================
# ANA TAG TABLOSU
# Kaynak: ass_tag_parser/ass_parser.py _PARSING_MAP + \clip/\iclip işleyicisi
# Doğrudan kopyalanmış, sınıflandırma sütunları eklenmiştir.
# =============================================================================

ASS_TAG_DATABASE = {
    # ── DRAWING MODE ─────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 533: (r"\p", AssTagDraw, _positive_int_arg)
    # \p0 = drawing OFF, \p1+ = drawing ON → vektör çizim modunu açar
    r"\p": {
        "name": "Drawing Mode",
        "class": "AssTagDraw",
        "category": "drawing",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Enables drawing mode (\\p1+). Line content becomes vector draw commands.",
        "aegisub_ref": "https://aegisub.org/docs/latest/ass_tags/#drawing-mode",
    },
    r"\pbo": {
        "name": "Baseline Offset",
        "class": "AssTagBaselineOffset",
        "category": "baseline",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Moves text baseline by Y pixels. Used with drawing mode.",
    },

    # ── KARAOKE ──────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 514-517
    # \k = fill sweep, \K = border sweep, \kf = gradient fill, \ko = outline wipe
    r"\k": {
        "name": "Karaoke (Fill Sweep)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Karaoke timing tag. Duration in centiseconds. Fill sweeps left to right.",
        "karaoke_type": 1,
    },
    r"\K": {
        "name": "Karaoke (Border Sweep)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Karaoke timing tag. Border sweeps across text.",
        "karaoke_type": 2,
    },
    r"\kf": {
        "name": "Karaoke (Gradient Fill)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Karaoke timing tag. Fill gradient sweeps left to right.",
        "karaoke_type": 3,
    },
    r"\ko": {
        "name": "Karaoke (Outline Wipe)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Karaoke timing tag. Outline wipes across text.",
        "karaoke_type": 4,
    },

    # ── POSITION / MOVEMENT ───────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 486-488
    r"\pos": {
        "name": "Position",
        "class": "AssTagPosition",
        "category": "position",
        "skip_if_dominant": False,   # İçerik varsa sign modu, skip değil
        "visual_only": True,
        "translatable": True,        # Metni sign modu olarak çevir
        "description": "Sets absolute position of subtitle. \\pos(x,y)",
        "coordinate_tag": True,      # Koordinat analizi için işaret
    },
    r"\move": {
        "name": "Move",
        "class": "AssTagMove",
        "category": "position",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Moves subtitle from (x1,y1) to (x2,y2). \\move(x1,y1,x2,y2[,t1,t2])",
        "coordinate_tag": True,
    },
    r"\org": {
        "name": "Rotation Origin",
        "class": "AssTagRotationOrigin",
        "category": "position",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Sets the origin point for rotation. \\org(x,y)",
        "coordinate_tag": True,
    },

    # ── CLIP / ICLIP ─────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 541-584 (\clip ve \iclip ayrı işleniyor)
    r"\clip": {
        "name": "Clip Rectangle/Vector",
        "class": "AssTagClipRectangle or AssTagClipVector",
        "category": "clip",
        "skip_if_dominant": True,   # Çoğunlukla maske amaçlı
        "visual_only": True,
        "translatable": False,
        "description": "Clips rendering to rectangle or vector path. \\clip(x1,y1,x2,y2) or \\clip(path)",
    },
    r"\iclip": {
        "name": "Inverse Clip",
        "class": "AssTagClipRectangle or AssTagClipVector",
        "category": "clip",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "Inverse clip — renders ONLY outside the clipping region.",
    },

    # ── ANIMATION ────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 534: (r"\t", AssTagAnimation, _animation_args)
    r"\t": {
        "name": "Transform Animation",
        "class": "AssTagAnimation",
        "category": "animation",
        "skip_if_dominant": False,   # Kısa metinse sign, uzunsa çevir
        "visual_only": True,
        "translatable": True,        # Sahip olduğu metni çevir
        "description": "Animated transformation. \\t([t1,t2,][accel,]tags)",
        "animation_tag": True,
    },
    r"\fad": {
        "name": "Fade (Simple)",
        "class": "AssTagFade",
        "category": "animation",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Simple fade in/out. \\fad(fadeIn_ms, fadeOut_ms)",
    },
    r"\fade": {
        "name": "Fade (Complex)",
        "class": "AssTagFadeComplex",
        "category": "animation",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Complex fade. \\fade(a1,a2,a3,t1,t2,t3,t4)",
    },

    # ── FORMATTING ───────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 510-513
    r"\b": {
        "name": "Bold",
        "class": "AssTagBold",
        "category": "formatting",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Bold text. \\b1=on, \\b0=off, \\b400/700=weight",
    },
    r"\i": {
        "name": "Italic",
        "class": "AssTagItalic",
        "category": "formatting",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Italic text. \\i1=on, \\i0=off",
    },
    r"\u": {
        "name": "Underline",
        "class": "AssTagUnderline",
        "category": "formatting",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Underlined text. \\u1=on, \\u0=off",
    },
    r"\s": {
        "name": "Strikeout",
        "class": "AssTagStrikeout",
        "category": "formatting",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Strikeout text. \\s1=on, \\s0=off",
    },

    # ── FONT ─────────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 503-507
    r"\fn": {
        "name": "Font Name",
        "class": "AssTagFontName",
        "category": "font",
        "skip_if_dominant": True,   # Sadece font varsa görsel-only
        "visual_only": True,
        "translatable": True,       # Metnini çevir
        "description": "Font name. \\fnArial",
        "typeset_heavy": True,      # Yoğun typesetting işareti
    },
    r"\fs": {
        "name": "Font Size",
        "class": "AssTagFontSize",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Font size in points. \\fs60",
        "typeset_heavy": True,
    },
    r"\fscx": {
        "name": "Font X Scale",
        "class": "AssTagFontXScale",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Font horizontal scale percentage. \\fscx110",
        "typeset_heavy": True,
    },
    r"\fscy": {
        "name": "Font Y Scale",
        "class": "AssTagFontYScale",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Font vertical scale percentage. \\fscy110",
        "typeset_heavy": True,
    },
    r"\fsp": {
        "name": "Letter Spacing",
        "class": "AssTagLetterSpacing",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Additional space between letters in pixels. \\fsp2",
    },
    r"\fe": {
        "name": "Font Encoding",
        "class": "AssTagFontEncoding",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Font encoding (charset). \\fe1 (default)",
    },

    # ── COLOR ────────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 525-529
    r"\1c": {
        "name": "Primary Color",
        "class": "AssTagColor",
        "category": "color",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Primary (fill) color. \\1c&HBBGGRR& or \\c&HBBGGRR&",
        "color_target": 1,
    },
    r"\c": {
        "name": "Primary Color (Short)",
        "class": "AssTagColor",
        "category": "color",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Shortcut for \\1c. Primary fill color.",
        "color_target": 1,
    },
    r"\2c": {
        "name": "Secondary Color",
        "class": "AssTagColor",
        "category": "color",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Secondary color (karaoke pre-highlight). \\2c&HBBGGRR&",
        "color_target": 2,
    },
    r"\3c": {
        "name": "Outline Color",
        "class": "AssTagColor",
        "category": "color",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": True,
        "description": "Outline/border color. \\3c&HBBGGRR&",
        "color_target": 3,
        "typeset_heavy": True,
    },
    r"\4c": {
        "name": "Shadow Color",
        "class": "AssTagColor",
        "category": "color",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Shadow color. \\4c&HBBGGRR&",
        "color_target": 4,
        "typeset_heavy": True,
    },

    # ── ALPHA ────────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 520-524
    r"\alpha": {
        "name": "Alpha (All Channels)",
        "class": "AssTagAlpha",
        "category": "alpha",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Transparency for all color channels. \\alpha&H00& (opaque) to &HFF& (invisible)",
        "alpha_target": 0,
    },
    r"\1a": {"name": "Primary Alpha",   "class": "AssTagAlpha", "category": "alpha", "skip_if_dominant": False, "visual_only": True, "translatable": True, "alpha_target": 1},
    r"\2a": {"name": "Secondary Alpha", "class": "AssTagAlpha", "category": "alpha", "skip_if_dominant": False, "visual_only": True, "translatable": True, "alpha_target": 2},
    r"\3a": {"name": "Outline Alpha",   "class": "AssTagAlpha", "category": "alpha", "skip_if_dominant": False, "visual_only": True, "translatable": True, "alpha_target": 3, "typeset_heavy": True},
    r"\4a": {"name": "Shadow Alpha",    "class": "AssTagAlpha", "category": "alpha", "skip_if_dominant": False, "visual_only": True, "translatable": True, "alpha_target": 4, "typeset_heavy": True},

    # ── BORDER ───────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 476-478
    r"\bord": {
        "name": "Border Width",
        "class": "AssTagBorder",
        "category": "border",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Border/outline width in pixels. \\bord3",
        "typeset_heavy": True,
    },
    r"\xbord": {"name": "X Border", "class": "AssTagXBorder", "category": "border", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},
    r"\ybord": {"name": "Y Border", "class": "AssTagYBorder", "category": "border", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},

    # ── SHADOW ───────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 479-482
    r"\shad": {
        "name": "Shadow Width",
        "class": "AssTagShadow",
        "category": "shadow",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Shadow depth in pixels. \\shad2",
        "typeset_heavy": True,
    },
    r"\xshad": {"name": "X Shadow", "class": "AssTagXShadow", "category": "shadow", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},
    r"\yshad": {"name": "Y Shadow", "class": "AssTagYShadow", "category": "shadow", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},

    # ── BLUR ─────────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 508-509
    r"\blur": {
        "name": "Gaussian Blur",
        "class": "AssTagBlurEdgesGauss",
        "category": "blur",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Gaussian edge blur. \\blur0.6 (subtle) to \\blur5 (heavy)",
        "typeset_heavy": True,
    },
    r"\be": {
        "name": "Blur Edges",
        "class": "AssTagBlurEdges",
        "category": "blur",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Simple edge blur. Less smooth than \\blur.",
    },

    # ── ROTATION ─────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 491-502
    r"\frx": {
        "name": "X Rotation",
        "class": "AssTagXRotation",
        "category": "rotation",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Rotate text around X axis (degrees). \\frx45",
        "typeset_heavy": True,
    },
    r"\fry": {"name": "Y Rotation", "class": "AssTagYRotation", "category": "rotation", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},
    r"\frz": {
        "name": "Z Rotation",
        "class": "AssTagZRotation",
        "category": "rotation",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Rotate text around Z axis (most common rotation). \\frz45",
        "typeset_heavy": True,
    },
    r"\fr":  {"name": "Z Rotation (Short)", "class": "AssTagZRotation", "category": "rotation", "skip_if_dominant": False, "visual_only": True, "translatable": True, "typeset_heavy": True},

    # ── SHEAR ────────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 484-485
    r"\fax": {
        "name": "X Shear",
        "class": "AssTagXShear",
        "category": "shear",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Shear text horizontally. \\fax0.2",
    },
    r"\fay": {"name": "Y Shear", "class": "AssTagYShear", "category": "shear", "skip_if_dominant": False, "visual_only": True, "translatable": True},

    # ── EKSİK TAG'LER (libass ass_parse.c'den tespit edildi) ──────────────────
    # Kaynak: libass/ass_parse.c satır 827-833
    r"\kt": {
        "name": "Karaoke Timing Offset (v4++)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "ASS v4++ karaoke timing offset. Sets skip timing without advancing effect.",
        "karaoke_type": 0,
        "note": "Discovered in libass ass_parse.c - missing from ass_tag_parser",
    },

    # Kaynak: libass/ass_parse.c satır 440-442 — \fsc: scale reset (her iki eksen)
    r"\fsc": {
        "name": "Font Scale Reset",
        "class": "AssTagFontScale",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Resets both fscx and fscy to style default. No argument. libass-only.",
        "note": "Discovered in libass ass_parse.c - missing from ass_tag_parser v2.4.1",
    },

    # ── SATIR İÇİ ÖZEL KARAKTERLER (override bloğu dışında) ───────────────────────
    # Kaynak: Aegisub resmi dokümantasyonu — "Special characters" bölümü
    # Bu karakterler { } dışında, doğrudan metin akışında kullanılır
    r"\N": {
        "name": "Hard Line Break",
        "class": "AssTextLineBreakHard",
        "category": "text",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Forces a line break in all wrapping modes. Most common line break in ASS.",
        "aegisub_ref": "https://aegisub.org/docs/latest/ass_tags/#special-characters",
    },
    r"\n": {
        "name": "Soft Line Break",
        "class": "AssTextLineBreakSoft",
        "category": "text",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Soft line break. Only effective in wrapping mode 2 (\\q2). Otherwise becomes a space.",
    },
    r"\h": {
        "name": "Hard Space",
        "class": "AssTextHardSpace",
        "category": "text",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Non-breaking space. Prevents line wrapping at this position.",
    },

    # ── ALIGNMENT ────────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 530-531
    r"\an": {
        "name": "Alignment (NumPad)",
        "class": "AssTagAlignment",
        "category": "alignment",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Text alignment using numpad positions (1-9). \\an8 = top center.",
    },
    r"\a": {
        "name": "Alignment (Legacy SSA)",
        "class": "AssTagAlignment",
        "category": "alignment",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Legacy SSA alignment codes (1-3, 5-7, 9-11). Use \\an instead.",
        "legacy": True,
    },

    # ── STYLE RESET ──────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 519
    r"\r": {
        "name": "Reset Style",
        "class": "AssTagResetStyle",
        "category": "style",
        "skip_if_dominant": False,
        "visual_only": False,
        "translatable": True,
        "description": "Reset all overrides to style default. \\r or \\rStyleName",
    },

    # ── WRAP STYLE ───────────────────────────────────────────────────────────
    # Kaynak: ass_parser.py satır 518
    r"\q": {
        "name": "Wrap Style",
        "class": "AssTagWrapStyle",
        "category": "wrapstyle",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Line wrapping mode. \\q0=smart \\q1=EOL \\q2=no wrap \\q3=smart+lower",
    },

    # ── EKSİK TAG'LER (libass ass_parse.c'den tespit edildi) ──────────────────
    # Kaynak: libass/ass_parse.c satır 827-833
    r"\kt": {
        "name": "Karaoke Timing Offset (v4++)",
        "class": "AssTagKaraoke",
        "category": "karaoke",
        "skip_if_dominant": True,
        "visual_only": True,
        "translatable": False,
        "description": "ASS v4++ karaoke timing offset. Sets skip timing without advancing effect.",
        "karaoke_type": 0,
        "note": "Discovered in libass ass_parse.c - missing from ass_tag_parser",
    },

    # Kaynak: libass/ass_parse.c satır 440-442 — \fsc: scale reset (her iki eksen)
    r"\fsc": {
        "name": "Font Scale Reset",
        "class": "AssTagFontScale",
        "category": "font",
        "skip_if_dominant": False,
        "visual_only": True,
        "translatable": True,
        "description": "Resets both fscx and fscy to style default. No argument. libass-only.",
        "note": "Discovered in libass ass_parse.c - missing from ass_tag_parser v2.4.1",
    },
}


# =============================================================================
# KATEGORİ GRUPLAMAları — Hızlı erişim için
# =============================================================================

# Bu kategorilerdeki tag'ler → satırı DRAWING/KARAOKE olarak işaretle → SKIP
ALWAYS_SKIP_CATEGORIES = frozenset(['drawing', 'karaoke'])

# Bu tag'ler "typeset_heavy" işaretli — bir satırda 4+ tane varsa → SIGN modu
TYPESET_HEAVY_TAGS = frozenset(
    tag for tag, info in ASS_TAG_DATABASE.items()
    if info.get('typeset_heavy', False)
)

# Koordinat içeren tag'ler → off-screen analizi için
COORDINATE_TAGS = frozenset(
    tag for tag, info in ASS_TAG_DATABASE.items()
    if info.get('coordinate_tag', False)
)

# Animasyon tag'leri
ANIMATION_TAGS = frozenset(
    tag for tag, info in ASS_TAG_DATABASE.items()
    if info.get('animation_tag', False)
)

# Sadece görsel, metni etkilemez
VISUAL_ONLY_TAGS = frozenset(
    tag for tag, info in ASS_TAG_DATABASE.items()
    if info.get('visual_only', False)
)

# Çevrilmesi kesinlikle mümkün olmayan tag'ler
NEVER_TRANSLATABLE_TAGS = frozenset(
    tag for tag, info in ASS_TAG_DATABASE.items()
    if not info.get('translatable', True)
)


# =============================================================================
# STİL ADI SKIP SÖZLÜĞÜ
# Fansub gruplarının kullandığı ASS stil adı kalıpları — çeviri dışı
# =============================================================================

SKIP_STYLE_SUFFIXES = {
    # Romaji / Japonca / Çince / Korece sarkılar
    'ROM',   'ROMAJI',
    'JPN',   'JP',      'JAP',   'JPNESE',
    'CHN',   'CN',      'ZH',
    'KOR',   'KR',
    # Prodüksiyon kredileri
    'CREDIT', 'STAFF', 'CREDITS', 'CREDIT2',
    # Çeviri notları
    'NOTE',  'TL',    'TLNOTE', 'TRNOTE',
    # Karaoke / Sarkı
    'KARA',  'KARAOKE', 'KAR',
    # Sarkı sözleri (Japonca)
    'LYRICS', 'LYRIC',
    # Arka plan müziği
    'BGM',   'MUSIC',
    # Ruby / Furigana metni (ASS'de üst hece notasyonu)
    'FURIGANA', 'RUBY',
    # Ins - JP / Ins - ROM vb. (CrappySubs/GJM pattern)
    'INSJP', 'INSROM', 'INSKANA', 'INSMEM',
    # Tipografi çerçevesi (sadece koordinat içeren)
    'TYPESET', 'TS',  # Bu stil sign içerebilir — ama çok büyük ihtimalle değil
    # Hafıza / flashback Japonca
    'MEM',  'MEMORY',
}

# Çeviri ZORLA yapılacak suffix'ler (skip listesine rağmen)
FORCE_TRANSLATE_SUFFIXES = {
    'ENG', 'EN',    # Ingilizce sarki çevirisi
    'ALT',          # Alternatif diyalog
    'TL',           # Çeviri satırı (bazı gruplar TL kullanır)
    'TRANS',        # Translation
}

# Sign/Ekran yazısı stil adı kalıpları
SIGN_STYLE_KEYWORDS = {
    'sign', 'signs', 'title', 'caption', 'typeset',
    'detail', 'onscreen', 'location', 'overlay',
    'label', 'banner', 'board', 'screen', 'text',
    'effects', 'effect', 'sfx',
}

# Sarki stili temel kelimeleri
SONG_STYLE_KEYWORDS = {
    'op', 'ed', 'song', 'opening', 'ending', 'insert',
    'romaji', 'rom', 'kara', 'karaoke', 'lyric', 'lyrics',
    'music', 'jap', 'jpn', 'oped', 'inssong', 'insong', 'bgm',
}

# ASS Effect alanı — libass ass_parse.c'den (satır 930-970)
# Bu değerler event'in 9. alanında (Effect) bulunabilir
# Banner/Scroll: animasyonlu geçiş efektleri — metin var ama özel render
EFFECT_FIELD_PATTERNS = {
    # Tam isme göre (case-insensitive)
    'banner':       'scroll',    # Banner; delay[; lefttoright[; fadeawaywidth]]
    'scroll up':    'scroll',    # Scroll up; y0; y1; delay[; fadeawayheight]
    'scroll down':  'scroll',    # Scroll down; y0; y1; delay[; fadeawayheight]
    'karaoke':      'karaoke',   # Legacy karaoke effect
    'paint':        'drawing',   # Legacy paint (çok nadir)
}


# =============================================================================
# ÇEVRİLMEYECEK İÇERİK TANI KALIPLARları
# Metin içeriğine göre (stil adından BAĞIMSIZ) tespit
# =============================================================================

import re as _re

# Müzik notası / sembol satırı
SYMBOL_ONLY_PATTERN = _re.compile(
    r'^[\s♪♫♬♩♭♮♯〜～…—–\-·•\*\+\=\|/\\○●◎△▲▽▼□■◇◆★☆※¶§]+$'
)

# Copyright / Telif bildirimi
COPYRIGHT_PATTERN = _re.compile(
    r'(?i)(?:\xa9|'  + '\u00a9' + r'|©|copyright|\(c\)\s*\d|production\s+committee|'
    r'all\s+rights\s+reserved|shueisha|kodansha|aniplex|'
    r'crunchyroll|funimation|sentai\s+filmworks)',
)

# Japonca karakter içeriyor (kanji, hiragana, katakana)
JP_CHAR_PATTERN = _re.compile(
    r'[\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\uFF00-\uFFEF'
    r'\u4E00-\u9FAF\u3400-\u4DBF]'
)

# Drawing komutları (p tag olmasa da vector data olabilir)
# Kaynak: Aegisub resmi - Drawing commands: m n l b s p c
DRAWING_CMD_PATTERN = _re.compile(
    r'^\s*(?:[mlbnscpNP]\s+-?\d+\s+-?\d+[\s,]*)+\s*$',
    _re.IGNORECASE
)

# Ofscreen pozisyon tespiti için
POS_COORD_PATTERN = _re.compile(
    r'\\pos\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*\)'
)
MOVE_COORD_PATTERN = _re.compile(
    r'\\move\(\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)'
    r'\s*,\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)'
)


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def get_tag_info(tag_name: str) -> dict:
    """
    Tag adından veritabanı bilgisini getir.
    tag_name: '\\blur', '\\pos', '\\k' gibi
    """
    return ASS_TAG_DATABASE.get(tag_name, {})


def get_tag_category(tag_name: str) -> str:
    """Tag'in kategorisini döndür. Bilinmiyorsa 'unknown'."""
    return ASS_TAG_DATABASE.get(tag_name, {}).get('category', 'unknown')


def is_drawing_tag(tag_name: str) -> bool:
    """\\p tag'i mi? (drawing mode)"""
    return get_tag_category(tag_name) == 'drawing'


def is_karaoke_tag(tag_name: str) -> bool:
    """Karaoke tag'i mi?"""
    return get_tag_category(tag_name) == 'karaoke'


def is_typeset_heavy(tag_name: str) -> bool:
    """Typesetting ağır tag mi? (yoğun tag tespiti için)"""
    return ASS_TAG_DATABASE.get(tag_name, {}).get('typeset_heavy', False)


def count_typeset_heavy_in_text(raw_text: str) -> int:
    """
    Ham ASS metnindeki typeset_heavy tag sayısını döndür.
    Örnek: '{\\blur0.6\\pos(960,50)\\fn Arial\\3c&H000&}' → 4
    """
    count = 0
    for tag, info in ASS_TAG_DATABASE.items():
        if info.get('typeset_heavy', False):
            # tag adı regex-safe şekilde ara
            tag_name = tag.replace('\\', '').replace('(', '')
            if _re.search(_re.escape(tag.replace('\\', '\\\\')) + r'[\d(]', raw_text):
                count += 1
    return count


def extract_tag_names_from_text(raw_text: str) -> set:
    """
    Ham ASS metnindeki {...} bloklarından tag isimlerini çıkar.
    Returns: {'blur', 'pos', 'fn', '3c', 'bord', ...}

    Örnekler:
      {\\blur0.6\\bord3\\fn FOT\\3c&H000&\\fs60} -> {'blur', 'bord', 'fn', '3c', 'fs'}
      {\\k80} -> {'k'}
      {\\fscx110\\frz2} -> {'fscx', 'frz'}
    """
    names = set()
    # ASS tag ismi: rakamla başlayabilir (1c, 2c, 3c, 4c, 1a, 2a...)
    # veya harfle başlar (blur, pos, fn...), ardından rakam değeri gelir
    # Regex: \\(rakam?harf+) şeklinde — sonraki & ( rakam'ı almaz
    _TAG_FULL_RE = _re.compile(r'\\(\d?[a-zA-Z]+)(?=[\d&.(\\]|$)')
    for blk in _re.finditer(r'\{([^}]*)\}', raw_text):
        for tag in _TAG_FULL_RE.finditer(blk.group(1)):
            names.add(tag.group(1).lower())
    return names


def classify_by_tag_content(raw_text: str) -> str:
    """
    Ham ASS metnindeki tag içeriğine göre hızlı sınıflandırma.

    Returns:
        'drawing'  → \\p1+ içeriyor
        'karaoke'  → \\k \\K \\kf \\ko içeriyor
        'sign'     → 4+ typeset_heavy tag içeriyor
        'normal'   → sadece biçimlendirme tag'leri
        'empty'    → tag yok
    """
    if not raw_text or not raw_text.strip():
        return 'empty'

    # Drawing modu
    if _re.search(r'\\p[1-9]', raw_text):
        return 'drawing'

    # Karaoke
    if _re.search(r'\\[kK][fot]?\d', raw_text):
        return 'karaoke'

    # Typeset ağır analiz
    tag_names = extract_tag_names_from_text(raw_text)
    heavy = sum(1 for n in tag_names if n in {
        'blur', 'bord', 'xbord', 'ybord', 'shad', 'xshad', 'yshad',
        'fn', 'fs', 'fscx', 'fscy', 'fsp', 'frz', 'frx', 'fry',
        'fax', 'fay', '3c', '4c', '1a', '2a', '3a', '4a', 'alpha',
    })
    if heavy >= 4:
        return 'sign'

    if not tag_names:
        return 'empty'

    return 'normal'


def database_info() -> dict:
    """Veritabanı özet bilgisi."""
    cats = {}
    for info in ASS_TAG_DATABASE.values():
        c = info.get('category', 'unknown')
        cats[c] = cats.get(c, 0) + 1
    return {
        'total_tags': len(ASS_TAG_DATABASE),
        'never_translatable': len(NEVER_TRANSLATABLE_TAGS),
        'typeset_heavy_tags': len(TYPESET_HEAVY_TAGS),
        'coordinate_tags': len(COORDINATE_TAGS),
        'categories': cats,
        'source': 'bubblesub/ass_tag_parser + Aegisub docs',
    }


# =============================================================================
# Modül yüklenince kısa özet bas
# =============================================================================
if __name__ == '__main__':
    info = database_info()
    print(f"[ASS Tag DB] {info['total_tags']} tag yüklendi")
    print(f"  Kaynak: {info['source']}")
    print(f"  Çevrilmez: {info['never_translatable']} tag")
    print(f"  Typeset-heavy: {info['typeset_heavy_tags']} tag")
    print(f"  Koordinat: {info['coordinate_tags']} tag")
    print(f"  Kategoriler: {info['categories']}")
