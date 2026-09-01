"""
fandom_glossary.py  —  GERIYE DÖNÜK UYUMLULUK SHIM
====================================================
Gerçek kod: Python kodları/glossary/ klasöründe.
Eski import'lar (from fandom_glossary import ...) kırılmasın diye
tüm semboller buradan re-export edilir.
"""
import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from glossary import *  # noqa
from glossary import (
    Candidate,
    resolve_media_details, find_wikidata_qid,
    find_wiki_slug, build_glossary,
    get_prompt_terms, get_prompt_injection,
    get_merged_injection, list_cached_series, delete_cached_series,
    _normalize_title, _norm, _fuzzy, clean_wikitext,
    _load_cache, _save_cache, _make_slug_candidates,
    _get_canonical_anime_title, _jikan_get_characters,
    _anilist_get_characters,
)
