"""
glossary/__init__.py
====================
fandom_glossary.py'nin yerine geçen modüler paket.
Dışarıdan import edenler için public API — eski import'lar kırılmaz.
"""
from glossary.models import Candidate
from glossary.models import _glossary_path
from glossary.cache import (
    _load_canonical_titles, _save_canonical_title,
    _get_canonical_anime_title, _blacklist_path, _load_blacklist,
    _save_blacklist, _is_slug_blacklisted, _add_to_blacklist,
    _normalize_title, _norm, _fuzzy,
)
from glossary.resolver import resolve_media_details, find_wikidata_qid
from glossary.slug import (
    _make_slug_candidates, _get_fandom_api_url, _check_wiki,
    _check_wiki_and_get_real_slug, _get_all_api_keys,
    _verify_wiki_relevance, _ai_find_wiki_slug,
)
from glossary.characters import _jikan_get_characters, _anilist_get_characters, _anilist_get_all_titles
from glossary.titles import _jikan_get_all_titles, _tvmaze_get_canonical_title, _tmdb_get_canonical_title
from glossary.wiki_api import (
    _parse_fandom_id, candidates_from_wikidata, slugify,
    candidates_from_slugify_probe, candidates_from_fandom_search,
    _mw_query, get_siteinfo, probe_pages, name_variants,
    verify, pick_language_variant, _load_overrides, find_wiki_slug,
)
from glossary.fetcher import (
    clean_wikitext, _fetch_term_summaries, _query_category_with_details,
    _get_subcategories, _query_all_pages, canonicalize,
    _fetch_page_redirects, _fetch_all_terms,
)
from glossary.store import (
    _load_cache, _save_cache, get_wiki_last_modified, _is_fresh,
    _extract_characters_from_umbrella_page, _resolve_via_umbrella_wikis,
)
from glossary.builder import (
    build_glossary, get_prompt_terms, get_prompt_injection,
    get_merged_injection, list_cached_series, delete_cached_series,
)

__all__ = [
    "Candidate",
    "resolve_media_details", "find_wikidata_qid",
    "find_wiki_slug", "build_glossary",
    "get_prompt_terms", "get_prompt_injection", "get_merged_injection",
    "list_cached_series", "delete_cached_series",
    "_normalize_title", "_norm", "_fuzzy",
    "clean_wikitext", "_load_cache", "_save_cache",
    "_make_slug_candidates", "_get_canonical_anime_title",
    "_jikan_get_characters", "_anilist_get_characters",
]
