"""
processor/__init__.py
=====================
subtitle_processor.py'nin yerine geçen modüler paket.

Dışarıdan kullanım (geriye dönük uyumluluk):
    from processor import process_and_replace_subtitle
    from processor import (
        is_sign_style_name, get_style_suffix_behavior, is_song_style_name,
        collapse_animation_frames, broadcast_collapsed_frames,
        create_byte_based_batches, translate_song_lyrics_pass,
        SubtitleTranslationError,
    )
"""

# Alt modüllerden public API'yi topla
from processor.pipeline.main import process_and_replace_subtitle
from processor.style_detect import (
    is_sign_style_name, get_style_suffix_behavior, is_song_style_name,
    SONG_KEYWORDS, STYLE_SUFFIX_SKIP, STYLE_SUFFIX_FORCE_TRANSLATE,
    JP_CHARS, DRAWING_PATTERN, BRACKET_PATTERN,
)
from processor.batch import (
    collapse_animation_frames, broadcast_collapsed_frames,
    create_byte_based_batches, _string_similarity,
)
from processor.song_detect import (
    is_likely_song_by_content, is_likely_karaoke_syllable_by_content,
)
from processor.song_translate import translate_song_lyrics_pass
from processor.karaoke import (
    _preprocess_collapse_karaoke, _collapse_and_translate_karaoke,
)
from processor.tag_tools import (
    extract_tags, restore_tags,
    extract_tags_with_placeholders, restore_tags_from_placeholders,
    protect_ass_newlines, restore_ass_newlines,
)
from processor.text_helpers import (
    has_censored_content, has_karaoke_tags, _is_english_content,
    is_romaji_text, clean_brackets, is_credit_line,
    parse_ass_time, format_ass_time, convert_srt_vtt_to_ass,
)
from processor.dedup import (
    _get_dedup_key, _check_termbase_compliance, _build_tb_lookup_from_prefs,
)

# SubtitleTranslationError — özel exception sınıfı
try:
    from processor.imports import SubtitleTranslationError
except ImportError:
    class SubtitleTranslationError(RuntimeError):
        pass

__all__ = [
    "process_and_replace_subtitle",
    "SubtitleTranslationError",
    "is_sign_style_name", "get_style_suffix_behavior", "is_song_style_name",
    "collapse_animation_frames", "broadcast_collapsed_frames",
    "create_byte_based_batches",
    "translate_song_lyrics_pass",
    "_preprocess_collapse_karaoke", "_collapse_and_translate_karaoke",
    "extract_tags", "restore_tags",
    "extract_tags_with_placeholders", "restore_tags_from_placeholders",
    "protect_ass_newlines", "restore_ass_newlines",
    "has_censored_content", "has_karaoke_tags",
    "is_romaji_text", "clean_brackets", "is_credit_line",
    "parse_ass_time", "format_ass_time", "convert_srt_vtt_to_ass",
    "_get_dedup_key", "_check_termbase_compliance", "_build_tb_lookup_from_prefs",
]
