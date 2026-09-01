"""offline_db_manager.py — GERIYE DÖNÜK UYUMLULUK SHIM"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path: sys.path.insert(0, _HERE)
from offline_db import *  # noqa
from offline_db import (
    update_databases, lookup_anime, lookup_media, lookup_wikidata_by_title,
    fetch_anidb_characters, get_characters_for_title, fetch_tvmaze_characters,
    fetch_franchise_terms, fetch_tmdb_cast, get_synonyms, get_status_info,
    get_all_titles_for_slug,
)
