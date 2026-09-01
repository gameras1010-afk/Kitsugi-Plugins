"""media_identifier.py — GERIYE DÖNÜK UYUMLULUK SHIM"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path: sys.path.insert(0, _HERE)
from media_id import *  # noqa
from media_id import (
    parse_episode_info, detect_media_type, _clean_title,
    fetch_media_metadata, identify_from_file, _build_search_titles,
    score_subtitle_quality, build_translation_context,
)
