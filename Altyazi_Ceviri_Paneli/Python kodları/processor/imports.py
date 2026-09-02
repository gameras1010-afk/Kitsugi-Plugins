"""
processor/imports.py
====================
subtitle_processor.py'nin tüm import ve try/except bloklarını barındırır.
Diğer processor alt modülleri buradan import eder.
"""
import ass_vendor_setup  # noqa — _vendor/ dizinini path'e ekler
import os
import re
import traceback
import requests
import json
from colorama import Fore, Style
from tqdm import tqdm
import difflib


class SubtitleTranslationError(RuntimeError):
    """
    Subtitle çevirisi zorunlu iken başarısız olduğunda fırlatılır.

    HStream İndirici fail-safe mekanizması:
    Herhangi bir altyazı dosyası çevrilemediyse tüm batch durdurulur.
    Bu exception otomatik indirici.py'nin ana döngüsü tarafından
    yakalanmalı ve işlemi anlık olarak sonlandırmalıdır.
    """
    pass


# ── rapidfuzz: Hızlı ve doğru string similarity (difflib'den 10-100x hızlı) ─
try:
    from rapidfuzz import fuzz as _rfuzz, distance as _rdistance, process as _rfuzz_process
    _RAPIDFUZZ_OK = True
except ImportError:
    _rfuzz_process = None
    _RAPIDFUZZ_OK = False
import time

# [ASS Line Filter] ass_tag_parser tabanli guclu satir filtresi
# Kaynak: github.com/bubblesub/ass_tag_parser (MIT Lisansi)
try:
    from ass_line_filter import (
        is_drawing_line           as _alf_is_draw,
        is_karaoke_line           as _alf_is_kara,
        style_should_skip         as _alf_style_skip,
        timestamp_fix_safe_rescue as _alf_ts_safe,
    )
    _ALF_OK = True
except ImportError:
    _ALF_OK = False
    import re as _re_alf
    _alf_is_draw  = lambda t: bool(_re_alf.search(r'\\p[1-9]', t))
    _alf_is_kara  = lambda t: bool(_re_alf.search(r'\\[kK][fot]?\d', t))
    _alf_style_skip = lambda s: bool(_re_alf.search(
        r'(?i)\b(?:rom(?:aji)?|jpn?|kara(?:oke)?|ruby|furigana|ins\s*-\s*jp)\b', s))
    _alf_ts_safe  = lambda ev: (
        not _alf_is_draw(ev.get('text', ''))
        and not _alf_is_kara(ev.get('text', ''))
        and not _alf_style_skip(ev.get('style', ''))
    )


# ASS Tag Extraction Motoru — libass + Aegisub kaynaklı tam spec implementasyonu
try:
    from ass_tag_extractor import (
        extract_ass_tags as _ass_extract,
        restore_ass_tags as _ass_restore,
        strip_all_ass_tags,
        classify_block as _classify_ass_block,
        is_drawing_line,
        ASS_VALID_TAGS,
        split_into_segments as _seg_split,
        rejoin_from_segments as _seg_rejoin,
        merge_text_segments_for_batch as _seg_merge,
        split_translated_batch as _seg_split_result,
    )
    _ASS_EXTRACTOR_AVAILABLE = True
except ImportError:
    _ASS_EXTRACTOR_AVAILABLE = False
    strip_all_ass_tags = None

# [YENİ] ASS Kalite Dogrulama Motoru — CPS/CPL/effect/actor
try:
    from subtitle_validator import (
        validate_event   as _validate_event,
        validate_all     as _validate_all,
        validate_event_with_translation as _validate_event_with_tr,
        validate_color_preservation as _validate_color_preservation,
        summarize_validation as _summarize_validation,
        has_scroll_effect as _has_scroll_effect,
        _ass_time_to_ms,
    )
    _VALIDATOR_AVAILABLE = True
except ImportError:
    _VALIDATOR_AVAILABLE = False
    def _has_scroll_effect(e): return False
    def _validate_all(evs, **kw): return []
    def _validate_event_with_tr(ev, tr_text, **kw): return None
    def _validate_color_preservation(orig, tr): return {'ok': True, 'missing': [], 'extra': []}
    def _summarize_validation(r): return {}
    def _ass_time_to_ms(t): return 0

# [YENİ] ASS Tag Kütüphanesi — ass_tag_parser v2.4.1 tabanlı tam spec implementasyonu
# Kaynak: bubblesub/ass_tag_parser + Aegisub tag referansı
try:
    from ass_tag_library import (
        analyze          as _atl_analyze,
        strip_tags       as _atl_strip,
        is_draw_event    as _atl_is_draw,
        is_karaoke_event as _atl_is_kara,
        is_animated_event as _atl_is_anim,
        has_translatable_text as _atl_has_text,
        should_skip_translation as _atl_should_skip,
        extract_text_atp as _atl_extract,
        strip_animation_tags as _atl_strip_anim,
        is_fullline_karaoke as _atl_is_fullline,
        is_letter_by_letter_karaoke as _atl_is_letter,
        get_tag_summary  as _atl_tag_summary,
        library_info     as _atl_library_info,
    )
    _ATL_AVAILABLE = True
except ImportError:
    _ATL_AVAILABLE = False

# [YENİ] ASS Tag Referans Modülü — libass/ass_parse.c + Aegisub kaynaklı
# Tam override tag listesi, çizim modu, vektör clip, karaoke, effect alanı
try:
    from ass_tag_reference import (
        is_drawing_line           as _atr_is_draw,
        is_vector_clip_junk       as _atr_is_clip_junk,
        should_skip_by_effect     as _atr_skip_effect,
        classify_line_translatability as _atr_classify,
        protect_special_chars     as _atr_protect,
        restore_special_chars     as _atr_restore,
    )
    _ATR_AVAILABLE = True
except ImportError:
    _ATR_AVAILABLE = False
    def _atr_is_draw(t):         return bool(re.search(r'\\p[1-9]\b', t))
    def _atr_is_clip_junk(t):    return (False, '')
    def _atr_skip_effect(e):     return (False, '')
    def _atr_classify(t, s=''):  return ('translate', 'fallback')
    def _atr_protect(t):         return t
    def _atr_restore(t):         return t

# [YENİ] Romaji Dedektor — 4 katmanlı Japonca/İngilizce ayırıcı
try:
    from romaji_detector import (
        classify_kara_group        as _rom_classify_group,
        classify_full_line         as _rom_classify_line,
        style_is_definitely_romaji as _rom_style_is_jp,
        style_is_definitely_english as _rom_style_is_eng,
        is_romaji                  as _rom_is_romaji,
        score_romaji               as _rom_score,
        split_mixed_line           as _rom_split_mixed,
        join_mixed_segments        as _rom_join_mixed,
    )
    _ROMAJI_DETECTOR_OK = True
except ImportError:
    _ROMAJI_DETECTOR_OK = False
    def _rom_classify_group(syls, style='', merged=''): return ('uncertain', 0.5, 'no_detector')
    def _rom_classify_line(text, style=''): return ('uncertain', 0.5, 'no_detector')
    def _rom_style_is_jp(s): return bool(re.search(r'(?:^|[^a-zA-Z])(?:JP|JPN|ROM|ROMAJI|RO)(?:[^a-zA-Z]|$)', s, re.IGNORECASE))
    def _rom_style_is_eng(s): return bool(re.search(r'(?:^|[^a-zA-Z])(?:EN|ENG)(?:[^a-zA-Z]|$)', s, re.IGNORECASE))
    def _rom_is_romaji(syls, t=0.65): return False
    def _rom_score(syls): return 0.5
    def _rom_split_mixed(text, style=''): return [('english', text)]
    def _rom_join_mixed(segs, tr): return tr

# [YENİ] Adaptif Pattern Öğrenici — her dosya sonunda öğrenilen pattern'leri kalıcı kaydet
try:
    from ass_skip_learner import pipeline_end_save as _learner_save
    _LEARNER_OK = True
except ImportError:
    _LEARNER_OK = False
    def _learner_save(): pass

# [YENİ] Content Detector — stil adına bakmadan içerik tabanlı tespit
try:
    from content_detector import (
        classify_event           as _cd_classify_event,
        classify_text            as _cd_classify_text,
        classify_style           as _cd_classify_style,
        is_song_event_by_content as _cd_is_song,
        is_karaoke_syllable      as _cd_is_kara_syllable,
        score_text_romaji        as _cd_score_romaji,
    )
    _CONTENT_DETECTOR_OK = True
except ImportError:
    _CONTENT_DETECTOR_OK = False
    def _cd_classify_event(*a, **kw): return ('uncertain', 0.4, 'no_cd')
    def _cd_classify_text(t, **kw): return ('unknown', 0.4, 'no_cd')
    def _cd_classify_style(s): return ('generic', 0.3, 'no_cd')
    def _cd_is_song(*a, **kw): return (False, 0, 'no_cd')
    def _cd_is_kara_syllable(t, d=0): return (False, 'no_cd')
    def _cd_score_romaji(t): return (0.5, 'no_cd')

from utils import log_error, extract_episode_number, auto_split_line, should_merge_lines, save_as_srt, save_as_vtt, is_garbage_line

try:
    from translator import SubtitleTranslator
except ImportError:
    print("translator.py bulunamadı! Çeviri özellikleri devre dışı.")
    SubtitleTranslator = None

try:
    from settings import load_translation_cache, save_translation_cache
except ImportError:
    # Fallback: Define dummy functions if not available
    def load_translation_cache(): return {}
    def save_translation_cache(cache): pass

# Validation helpers
try:
    from subtitle_position_helpers import validate_and_fix_position_tags, normalize_alignment_tags
except ImportError:
    # Fallback: Define dummy functions if not available
    def validate_and_fix_position_tags(text): return text
    def normalize_alignment_tags(text): return text

# [YENİ] Çeviri Doğrulama Motoru — verify_translation() entegrasyonu
try:
    from translation_verifier import verify_translation as _verify_translation, TranslationResult as _TranslationResult
    _VERIFIER_AVAILABLE = True
except ImportError:
    _VERIFIER_AVAILABLE = False
    def _verify_translation(src, cand, **kw):
        class _FakeResult:
            is_valid = True; score = 1.0; reason = 'verifier_offline'; signals = {}
        return _FakeResult()

# [YENİ] srt_equalizer — CPS aşımı otomatik satır bölme desteği
try:
    import srt_equalizer as _srt_eq
    _SRT_EQUALIZER_OK = True
except ImportError:
    _SRT_EQUALIZER_OK = False
