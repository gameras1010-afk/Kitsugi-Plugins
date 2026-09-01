"""
subtitle_processor.py  —  GERIYE DÖNÜK UYUMLULUK SHIM
=======================================================
Bu dosya artık sadece processor/ paketine yönlendirme yapar.
Gerçek kod: Python kodları/processor/ klasöründe.

Eski import'lar (from subtitle_processor import ...) kırılmasın diye
tüm public semboller buradan re-export edilir.
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Tüm public semboller processor paketinden re-export
from processor import *  # noqa
from processor import (
    process_and_replace_subtitle,
    SubtitleTranslationError,
    is_sign_style_name, get_style_suffix_behavior, is_song_style_name,
    collapse_animation_frames, broadcast_collapsed_frames,
    create_byte_based_batches,
    translate_song_lyrics_pass,
    _preprocess_collapse_karaoke, _collapse_and_translate_karaoke,
    extract_tags, restore_tags,
    extract_tags_with_placeholders, restore_tags_from_placeholders,
    protect_ass_newlines, restore_ass_newlines,
    has_censored_content, has_karaoke_tags,
    is_romaji_text, clean_brackets, is_credit_line,
    parse_ass_time, format_ass_time, convert_srt_vtt_to_ass,
    _get_dedup_key, _check_termbase_compliance, _build_tb_lookup_from_prefs,
    SONG_KEYWORDS, STYLE_SUFFIX_SKIP, STYLE_SUFFIX_FORCE_TRANSLATE,
    JP_CHARS, DRAWING_PATTERN, BRACKET_PATTERN,
)
