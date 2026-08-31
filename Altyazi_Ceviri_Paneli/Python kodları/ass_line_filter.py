"""
ass_line_filter.py
==================
ASS subtitle line classifier — hangi satirlarin ceviriye GITMEMESI gerektigini belirler.

Kaynak: ass-tag-parser v2.4.1 (bubblesub/ass_tag_parser — MIT Lisansi)
        Aegisub ASS Override Tags Dokumantasyonu (aegisub.org)
        ASS/SSA Format Spesifikasyonu (libass referans implementasyonu)

Kapsanan kategoriler:
  1. ASS Drawing Mode   : \p1..\p9  — vektor grafik koordinatlari (HICBIR ZAMAN cevirme)
  2. Karaoke Tags       : \k \K \kf \ko — sarki/karaoke zamanlama satirlari
  3. Style-Name Filter  : ROM, JPN, KARA, RUBY, FURIGANA vb. stil adlari
  4. TimestampFix Guard : Ayni timestamp grubunda draw satiri "kurtarma"yi engelle
  5. Digit Density      : Koordinat/sayisal veri orani yuksek satirlari engelle
"""

import re
from typing import Optional

# ── [YENİ] ASS Content Classifier + Tag Veritabanı ───────────────────────────
# ass_tags_database.py : GitHub bubblesub/ass_tag_parser + Aegisub docs'tan
#                        doğrudan kopyalanmış ASS tag sözlüğü
# ass_content_classifier.py : Bu sözlüğü kullanarak satır kararı veren motor
try:
    from ass_content_classifier import (
        classify_line as _clf_classify,
        is_non_translatable_extended as _clf_non_tr,
        is_sign_line as _clf_is_sign,
        ClassificationResult,
    )
    _CLF_OK = True
except ImportError:
    _CLF_OK = False
    def _clf_non_tr(raw, style='', rx=1920, ry=1080): return False
    def _clf_is_sign(raw, style='', rx=1920, ry=1080): return False
    def _clf_classify(raw, style='', rx=1920, ry=1080, meta=None): return None

# ── Backend: ass_tag_parser (GitHub: bubblesub/ass_tag_parser) ──────────────
try:
    from ass_tag_parser import (
        parse_ass,
        AssTagDraw,          # \p1, \p2 ... \p9 — drawing mode
        AssTagKaraoke,       # \k, \K, \kf, \ko  — karaoke timing
        AssTagClipVector,    # \clip(m...) — vektor klipler (metin olabilir, skip etme)
        AssText,             # Gercek metin bolumu
    )
    _ATP_OK = True
except ImportError:
    _ATP_OK = False

# ── Style-Name Skip Patterns (Aegisub community standartlari) ────────────────
# Asagidaki stil adlari iceren satirlar HICBIR ZAMAN ceviriye gitmez.
# Kara/karaoke: animasyonlu sarki satirlari
# ROM/Romaji  : Japonca romaji transkripsiyon
# JPN/JP      : Japonca karakter satirlari (hiragana/katakana/kanji goruntusu)
# RUBY/Furigana: Furigana okuma yardimcilari
# INS - JP    : CrappySubs/fansub "insert - japanese" satirlari
_SKIP_STYLE_RE = re.compile(
    r'(?i)'
    r'(?:'
    r'\brom(?:aji)?\b'           # romaji, rom
    r'|\bjpn?\b'                 # jp, jpn
    r'|\bjap(?:anese)?\b'        # jap, japanese
    r'|\bkana\b'                 # kana (hiragana/katakana)
    r'|\bkanji\b'                # kanji
    r'|\bkara(?:oke)?\b'         # kara, karaoke
    r'|\bruby\b'                 # ruby furigana
    r'|\bfurigana\b'             # furigana
    r'|\bins\s*-\s*jp\b'         # "INS - JP" (CrappySubs pattern)
    r'|\bins\s*-\s*rom\b'        # "INS - ROM"
    r'|\bins\s*-\s*kana\b'       # "INS - Kana"
    r'|\bins\s*-\s*mem\b'        # "INS - Mem" (memory karaoke)
    r')'
)

# Drawing command regex (fallback, ass_tag_parser yoksa)
_DRAW_TAG_RE  = re.compile(r'\\p[1-9]')
_DRAW_CMD_RE  = re.compile(r'(?<![a-zA-Z])([mlbsnpc])\s+[-\d.]+\s+[-\d.]+', re.IGNORECASE)
_KARA_TAG_RE  = re.compile(r'\\[kK][fot]?\d')


def _digit_density(text: str) -> float:
    """Metindeki sayi+nokta+eksi karakterlerinin orani. Drawing koordinat tespiti icin."""
    if not text:
        return 0.0
    numeric = sum(1 for c in text if c.isdigit() or c in '.-')
    return numeric / len(text)


def is_drawing_line(raw_text: str) -> bool:
    """
    Bir ASS satiri drawing mode iceriyorsa True doner.
    
    \\p1..\\p9 tagleri AKTIF drawing modu aciklar.
    Bu satirlarin icerigi vektor koordinat verisidir — HICBIR ZAMAN cevirme.
    
    Kaynak: Aegisub ASS Tags Dok. — https://aegisub.org/docs/latest/ass_tags/
    'When drawing mode is enabled (\\p<scale>), the line text is interpreted
     as vector drawing commands rather than as subtitle text.'
    """
    if not raw_text:
        return False

    # Oncelik 1: ass_tag_parser (kesin, guvenilir)
    if _ATP_OK:
        try:
            items = parse_ass(raw_text)
            for item in items:
                if isinstance(item, AssTagDraw) and item.scale >= 1:
                    return True
        except Exception:
            pass  # parse hatasi → fallback regex

    # Oncelik 2: Regex fallback (ass_tag_parser yuklu degilse)
    tag_stripped = re.sub(r'\{[^}]*\}', '', raw_text).strip()
    has_draw_tag = bool(_DRAW_TAG_RE.search(raw_text))
    has_draw_cmd = bool(_DRAW_CMD_RE.search(tag_stripped))
    digit_ratio  = _digit_density(tag_stripped)
    
    if has_draw_tag and (has_draw_cmd or digit_ratio > 0.35):
        return True

    # Check if the tag-stripped text is pure vector/drawing coordinates
    # even without the \p tag (e.g. when tags were stripped or missing).
    if tag_stripped:
        vector_pattern = r'\b[mlb]\s+[\d\s.-]+'
        vector_matches = list(re.finditer(vector_pattern, tag_stripped))
        vector_len = sum(len(m.group(0)) for m in vector_matches)
        if vector_len > 0 and (vector_len / len(tag_stripped)) > 0.6:
            return True
        if re.match(r'^[mlb]\s+[-\d]', tag_stripped) and digit_ratio > 0.5:
            return True

    return False


def is_karaoke_line(raw_text: str) -> bool:
    """
    Bir ASS satiri karaoke timing tagi iceriyorsa True doner.
    
    \\k, \\K, \\kf, \\ko tagleri sarki/karaoke satirlaridir.
    Bu satirlar Japonca/Ingilizce sarki sozu icerdigi icin
    ayri bir isleme (SongPass) birakilmali, normal ceviriye GITMEMELI.
    
    Kaynak: Aegisub Karaoke Tags — https://aegisub.org/docs/latest/karaoke_timing_tutorial/
    """
    if not raw_text:
        return False

    if _ATP_OK:
        try:
            items = parse_ass(raw_text)
            return any(isinstance(item, AssTagKaraoke) for item in items)
        except Exception:
            pass

    return bool(_KARA_TAG_RE.search(raw_text))


def style_should_skip(style_name: str) -> bool:
    """
    Stil adi'na gore ceviriye gitmemesi gereken satirlari tespit eder.
    
    Anime fansubbing toplulugu standartlarina gore:
    - ROM/Romaji stiller: Japonca romanize transkripsiyon
    - JPN/JP stiller    : Japonca karakter satirlari
    - KARA/Karaoke      : Sarki animasyon satirlari
    - RUBY/Furigana     : Okuma yardimcisi satirlari
    - INS-JP vb.        : CrappySubs/fansub editor notlari (Japonca)
    """
    if not style_name:
        return False
    return bool(_SKIP_STYLE_RE.search(style_name))


def is_non_translatable(raw_text: str, style_name: str = '',
                         play_res_x: int = 1920, play_res_y: int = 1080) -> bool:
    """
    Ana filtre fonksiyonu. Bir satirin ceviriye GITMEMESI gerekiyorsa True.

    Kontrol katmanları (performans için kısa-devre):
      1. Stil adı          → hızlı string match
      2. Drawing tag       → ass_tag_parser veya regex
      3. Karaoke tag       → ass_tag_parser veya regex
      [YENİ - ass_tags_database sözlüğü üzerinden]
      4. Off-screen \\pos  → ekran dışı koordinat → ATLA
      5. Sembol satırı     → ♪ ♫ 〜 … → ATLA
      6. Copyright         → © Shueisha vb. → ATLA
      7. Typeset-heavy     → 4+ ağır tag + kısa metin → SIGN modu (False döner)
      8. Çizim maskesi     → \\an7\\pos(0,0) → ATLA

    Bu fonksiyon SubtitleProcessor'in TimestampFix mekanizmasında
    'kurtarma' yapmadan önce mutlaka çağrılmalıdır.
    """
    # ── Eski katmanlar (geriye dönük uyum) ──────────────────────────────────
    if style_should_skip(style_name):
        return True
    if is_drawing_line(raw_text):
        return True
    if is_karaoke_line(raw_text):
        return True

    # ── [YENİ] ass_tags_database sözlüğü tabanlı genişletilmiş filtre ────────
    if _CLF_OK:
        return _clf_non_tr(raw_text, style_name, play_res_x, play_res_y)

    return False


def is_sign_line_extended(raw_text: str, style_name: str = '',
                           play_res_x: int = 1920, play_res_y: int = 1080) -> bool:
    """
    [YENİ] Sign (ekran yazısı) satırı mı? → translate_sign modu.
    Normal dialogue değil ama çevrilmeli (kısa, tek satır, özel prompt).
    ass_content_classifier üzerinden kontrol → ass_tags_database sözlüğü.
    """
    if not _CLF_OK:
        return False
    return _clf_is_sign(raw_text, style_name, play_res_x, play_res_y)


def classify_ass_line(raw_text: str, style_name: str = '',
                       play_res_x: int = 1920, play_res_y: int = 1080,
                       event_meta: dict = None):
    """
    [YENİ] Tam sınıflandırma sonucu döndür (ClassificationResult).
    Sonuç: action ('skip'/'translate'/'translate_sign'), reason, clean_text, tag_map
    ass_content_classifier.classify_line() — tüm kurallar ass_tags_database'den.
    """
    if not _CLF_OK:
        return None
    return _clf_classify(raw_text, style_name, play_res_x, play_res_y, event_meta)


def timestamp_fix_safe_rescue(ev: dict) -> bool:
    """
    TimestampFix'in bir event'i 'kurtarmasi' guvenli mi?
    
    Kullanim:
        if timestamp_fix_safe_rescue(ev) and _is_english_content(ev_raw):
            ev['skip_translation'] = False  # kurtarmak guvenli
    
    Doğrudan sahne arkasi kontrolu:
      - Orijinal raw_text'te drawing tag var mi?
      - Style adi skip listesinde mi?
      - Koordinat yogunlugu cok yuksek mi?
    
    Returns: True ise kurtarmak GUVENLI, False ise KURTARMA (draw/kara satiri)
    """
    raw = ev.get('text', '')
    style = ev.get('style', '')

    # 1. Stil adi kontrolu
    if style_should_skip(style):
        return False

    # 2. Drawing tag kontrolu (raw_text uzerinde — tag temizlenmeden once)
    if is_drawing_line(raw):
        return False

    # 3. Karaoke tag kontrolu
    if is_karaoke_line(raw):
        return False

    # 4. Digit density: tag temizlenmis metin cok sayisal mi?
    tag_stripped = re.sub(r'\{[^}]*\}', '', raw).replace('\\N', ' ').replace('\\n', ' ').strip()
    if len(tag_stripped) > 5 and _digit_density(tag_stripped) > 0.40:
        return False

    return True


# ── Modul test / dogrulama ──────────────────────────────────────────────────
if __name__ == '__main__':
    from colorama import Fore, Style, init
    init()

    tests = [
        # (raw_text, style, beklenen_nontranslatable, label)
        (r'{\p1\an7\move(-130,33,266,-55)\c&HBC4369&}m 462.4 336.53 l 462.61 226.84', 'Default', True,  'p1 vector draw'),
        (r'{\an7\c&HD5E4E7&\p1\move(-126,32,266,-56,25,2778)}m 282.3 772.5',           'Default', True,  'p1 draw + move'),
        (r'{\p4}m 0 0 b 50 0 100 50 100 100',                                           'Default', True,  'p4 bezier draw'),
        (r'{\k80}At{\k60}tack {\k70}No.1',                                              'Default', True,  'karaoke \\k'),
        (r'{\K50}WA{\K60}TA{\K40}SHI',                                                  'Default', True,  'karaoke \\K (WA)'),
        (r'{\an5\pos(100,200)}Hello World!',                                             'Default', False, 'normal styled dialogue'),
        (r'[SIGN] __T0__Oshi no Ko',                                                    'Signs',   False, 'sign with text'),
        (r'Hello World',                                                                 'INS - JP', True, 'style INS - JP'),
        (r'Watashi wa',                                                                  'ROM',     True,  'style ROM'),
        (r'{\an5}Attack No. 1',                                                          'JPN',     True,  'style JPN'),
        (r'{\an5}Ruby Hoshino',                                                          'Ruby',    True,  'style Ruby'),
        (r'{\clip(m 0 0 l 100 100)}Real text here',                                     'Default', False, 'clip vector but has real text'),
    ]

    print(f'\n{"="*65}')
    print(f'  ass_line_filter.py — Kapsamli Test (backend: {"ass_tag_parser" if _ATP_OK else "regex fallback"})')
    print(f'{"="*65}')
    passed = 0
    for raw, style, expected, label in tests:
        result = is_non_translatable(raw, style)
        ok = result == expected
        if ok:
            passed += 1
        color = Fore.GREEN if ok else Fore.RED
        mark  = '✓' if ok else '✗'
        print(f'  {color}[{mark}]{Style.RESET_ALL} {label:<42} skip={result} (beklenen={expected})')

    print(f'\n  Sonuc: {passed}/{len(tests)} test gecti.')
    print(f'{"="*65}\n')
