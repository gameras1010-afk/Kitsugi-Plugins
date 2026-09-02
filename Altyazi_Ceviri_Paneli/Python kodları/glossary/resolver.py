"""
glossary/resolver.py
====================
resolve_media_details ve find_wikidata_qid.
"""
import os
import re
import json
import time
import threading
import requests
import urllib.parse
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from glossary.models import REQUEST_TIMEOUT, _session_cache

def resolve_media_details(query: str, media_type: str = 'auto', verbose: bool = True) -> dict:
    query_clean = query.strip()
    query_key = query_clean.lower()
    
    global _RESOLVED_MEDIA_DETAILS
    if query_key in _RESOLVED_MEDIA_DETAILS:
        return _RESOLVED_MEDIA_DETAILS[query_key]
        
    details = {
        "anilist_id": None,
        "mal_id": None,
        "tmdb_id": None,
        "titles": [query_clean],
        "characters": [],
        "media_type": media_type
    }
    
    # 1. Yerel offline veritabanı sorgusu (Ağ isteği yapmadan)
    if _OFFLINE_DB_OK:
        try:
            if media_type in ('anime', 'auto', 'unknown'):
                meta = _offdb.lookup_anime(query_clean)
                if meta:
                    if meta.get('mal_id'):
                        details['mal_id'] = int(meta['mal_id'])
                    if meta.get('anilist_url'):
                        m = re.search(r'/anime/(\d+)', meta['anilist_url'])
                        if m:
                            details['anilist_id'] = int(m.group(1))
                    if meta.get('title'):
                        details['titles'].append(meta['title'])
                    if meta.get('synonyms'):
                        details['titles'].extend(meta['synonyms'])
                    details['media_type'] = 'anime'
            
            if not details['anilist_id'] and not details['mal_id'] and media_type in ('movie', 'series', 'auto'):
                meta = _offdb.lookup_media(query_clean, 'movie' if media_type == 'movie' else ('series' if media_type == 'series' else 'unknown'))
                if meta:
                    if meta.get('tmdb_id'):
                        details['tmdb_id'] = int(meta['tmdb_id'])
                    if meta.get('title'):
                        details['titles'].append(meta['title'])
                    details['media_type'] = 'movie' if meta.get('type') == 'MOVIE' else 'series'
        except Exception as e:
            if verbose:
                print(f"[Glossary] Çevrimdışı veritabanı hatası: {e}")
                
    # 2. AniList GraphQL ile çevrimiçi zenginleştirme (ID bulunamadıysa)
    if media_type in ('anime', 'auto') and not details['anilist_id']:
        gql = """
        query ($search: String) {
          Media(search: $search, type: ANIME) {
            id
            idMal
            title {
              romaji
              english
              native
            }
            synonyms
            characters(sort: ROLE, perPage: 12) {
              nodes {
                name {
                  full
                }
              }
            }
          }
        }
        """
        try:
            r = requests.post(
                "https://graphql.anilist.co",
                json={"query": gql, "variables": {"search": query_clean}},
                timeout=REQUEST_TIMEOUT + 1,
                headers=HEADERS
            )
            if r.status_code == 200:
                mdata = r.json().get("data", {}).get("Media")
                if mdata:
                    details['anilist_id'] = mdata.get('id')
                    details['mal_id'] = mdata.get('idMal')
                    titles = mdata.get('title', {})
                    for t_key in ('romaji', 'english', 'native'):
                        t_val = titles.get(t_key)
                        if t_val:
                            details['titles'].append(t_val)
                    syns = mdata.get('synonyms', [])
                    if syns:
                        details['titles'].extend(syns)
                    chars = mdata.get('characters', {}).get('nodes', [])
                    details['characters'] = [c['name']['full'] for c in chars if c.get('name', {}).get('full')]
                    details['media_type'] = 'anime'
                    if verbose:
                        print(f"[Glossary] AniList çevrimiçi çözüldü: AniList ID {details['anilist_id']}, MAL ID {details['mal_id']}")
        except Exception as e:
            if verbose:
                print(f"[Glossary] AniList çevrimiçi sorgu hatası: {e}")

    # 2b. AniList başarısız/eksik → Jikan/MAL fallback (karakter + başlık + ID)
    if media_type in ('anime', 'auto', 'unknown') and not details['characters'] and not details['anilist_id']:
        _jikan_mal_id = details.get('mal_id')
        _jikan_query = query_clean
        _jikan_ok = False
        try:
            if _jikan_mal_id:
                _jr = requests.get(
                    f"https://api.jikan.moe/v4/anime/{_jikan_mal_id}",
                    timeout=REQUEST_TIMEOUT, headers=HEADERS
                )
                if _jr.status_code == 200:
                    _jd = _jr.json().get('data', {})
                    _jikan_ok = True
                else:
                    _jd = {}
            else:
                _jr = requests.get(
                    f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(_jikan_query)}&limit=1",
                    timeout=REQUEST_TIMEOUT, headers=HEADERS
                )
                if _jr.status_code == 200:
                    _jresults = _jr.json().get('data', [])
                    _jd = _jresults[0] if _jresults else {}
                    _jikan_ok = bool(_jd)
                    if _jd:
                        _jikan_mal_id = _jd.get('mal_id')
                else:
                    _jd = {}

            if _jikan_ok and _jd:
                if not details['mal_id'] and _jd.get('mal_id'):
                    details['mal_id'] = _jd['mal_id']
                for _t in (_jd.get('title_english'), _jd.get('title_japanese'),
                           _jd.get('title'), *[s.get('title','') for s in (_jd.get('titles') or [])]):
                    if _t and _t not in details['titles']:
                        details['titles'].append(_t)
                for _syn in (_jd.get('synonyms') or []):
                    if _syn and _syn not in details['titles']:
                        details['titles'].append(_syn)
                if _jikan_mal_id:
                    import time as _time
                    _time.sleep(0.5)
                    _cr = requests.get(
                        f"https://api.jikan.moe/v4/anime/{_jikan_mal_id}/characters",
                        timeout=REQUEST_TIMEOUT, headers=HEADERS
                    )
                    if _cr.status_code == 200:
                        _chars = []
                        for _c in (_cr.json().get('data') or [])[:12]:
                            _cname = (_c.get('character') or {}).get('name', '')
                            if _cname:
                                _parts = [p.strip() for p in _cname.split(',')]
                                _chars.append(' '.join(reversed(_parts)))
                        details['characters'] = _chars
                if verbose:
                    print(f"[Glossary] Jikan/MAL fallback çözüldü: MAL ID {details['mal_id']}, {len(details['characters'])} karakter")
        except Exception as _je:
            if verbose:
                print(f"[Glossary] Jikan/MAL fallback hatası: {_je}")

    # 2c. Jikan da başarısız → Kitsu fallback (başlık zenginleştirme)
    if media_type in ('anime', 'auto', 'unknown') and not details['characters'] and not details['anilist_id']:
        try:
            _kr = requests.get(
                "https://kitsu.app/api/edge/anime",
                params={"filter[text]": query_clean, "page[limit]": "1",
                        "fields[anime]": "titles,abbreviatedTitles,episodeCount"},
                headers={**HEADERS, "Accept": "application/vnd.api+json"},
                timeout=REQUEST_TIMEOUT
            )
            if _kr.status_code == 200:
                _kdata = _kr.json().get('data', [])
                if _kdata:
                    _kitem = _kdata[0]
                    _katts = _kitem.get('attributes', {})
                    _ktitles = _katts.get('titles', {})
                    for _ktval in _ktitles.values():
                        if _ktval and _ktval not in details['titles']:
                            details['titles'].append(_ktval)
                    for _kabb in (_katts.get('abbreviatedTitles') or []):
                        if _kabb and _kabb not in details['titles']:
                            details['titles'].append(_kabb)
                    if verbose:
                        print(f"[Glossary] Kitsu fallback çözüldü: {list(_ktitles.values())[:2]}")
        except Exception as _ke:
            if verbose:
                print(f"[Glossary] Kitsu fallback hatası: {_ke}")


                
    # 3. TMDB veya TVMaze ile batı dizisi/film çözümü
    if media_type in ('movie', 'series', 'auto') and not details['anilist_id'] and not details['tmdb_id']:
        if media_type in ('series', 'auto'):
            try:
                r = requests.get(
                    'https://api.tvmaze.com/search/shows',
                    params={'q': query_clean},
                    timeout=REQUEST_TIMEOUT,
                    headers=HEADERS,
                )
                if r.status_code == 200:
                    results = r.json()
                    if results:
                        show = results[0].get('show', {})
                        name = show.get('name', '').strip()
                        if name:
                            details['titles'].append(name)
                        show_id = show.get('id')
                        if show_id:
                            c_r = requests.get(f'https://api.tvmaze.com/shows/{show_id}/characters', timeout=REQUEST_TIMEOUT, headers=HEADERS)
                            if c_r.status_code == 200:
                                details['characters'] = [c.get('person', {}).get('name') for c in c_r.json() if c.get('person', {}).get('name')][:12]
                        details['media_type'] = 'series'
            except Exception:
                pass
                
        tmdb_key = ''
        try:
            _cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translator_config.json')
            if os.path.exists(_cfg):
                tmdb_key = json.load(open(_cfg, encoding='utf-8')).get('tmdb_api_key', '')
        except Exception:
            pass
            
        if tmdb_key and not details['tmdb_id']:
            is_movie = (media_type == 'movie')
            endpoint = 'movie' if is_movie else 'tv'
            title_field = 'title' if is_movie else 'name'
            orig_field = 'original_title' if is_movie else 'original_name'
            try:
                r = requests.get(
                    f'https://api.themoviedb.org/3/search/{endpoint}',
                    params={'api_key': tmdb_key, 'query': query_clean, 'language': 'en-US'},
                    timeout=REQUEST_TIMEOUT,
                    headers=HEADERS,
                )
                if r.status_code == 200:
                    results = r.json().get('results', [])
                    if results:
                        first = results[0]
                        details['tmdb_id'] = first.get('id')
                        name = first.get(title_field, '').strip()
                        orig = first.get(orig_field, '').strip()
                        if name:
                            details['titles'].append(name)
                        if orig and orig != name and not re.search(r'[\u0400-\u9fff]', orig):
                            details['titles'].append(orig)
                        details['media_type'] = 'movie' if is_movie else 'series'
                        
                        c_r = requests.get(
                            f'https://api.themoviedb.org/3/{endpoint}/{details["tmdb_id"]}/credits',
                            params={'api_key': tmdb_key},
                            timeout=REQUEST_TIMEOUT,
                            headers=HEADERS
                        )
                        if c_r.status_code == 200:
                            cast = c_r.json().get('cast', [])
                            # Anime filmlerde cast 'name'=oyuncu, 'character'=karakter ismi
                            # (voice) suffix varlığı → anime/animasyon → karakter ismini kullan
                            _is_voice_cast = any(
                                '(voice)' in (c.get('character') or '').lower()
                                for c in cast[:5]
                            )
                            if _is_voice_cast:
                                # karakter isminden " (voice)" suffix'ini temizle
                                _chars = []
                                for c in cast:
                                    ch = (c.get('character') or '').replace('(voice)', '').replace('(Voice)', '').strip()
                                    if ch:
                                        _chars.append(ch)
                                details['characters'] = _chars[:12]
                            else:
                                details['characters'] = [c.get('name') for c in cast if c.get('name')][:12]
            except Exception:
                pass

    unique_titles = []
    for t in details['titles']:
        t_clean = t.strip()
        if t_clean and t_clean not in unique_titles:
            unique_titles.append(t_clean)
    details['titles'] = unique_titles
    
    _RESOLVED_MEDIA_DETAILS[query_key] = details
    return details

WD_ID_PROPS = [
    ("anilist", "P8729"),
    ("myanimelist", "P4086"),
    ("themoviedb_tv", "P4983"),
    ("themoviedb_movie", "P4947"),
    ("imdb", "P345"),
]

def find_wikidata_qid(ids: dict) -> Optional[str]:
    """haswbstatement ters araması: SPARQL'siz, tek GET ile ID -> QID."""
    for key, prop in WD_ID_PROPS:
        raw = ids.get(key.replace("_tv", "").replace("_movie", ""))
        if key.startswith("themoviedb"):
            raw = ids.get("themoviedb")
        if not raw:
            continue
        q = urllib.parse.quote(f"haswbstatement:{prop}={raw}")
        url = (
            "https://www.wikidata.org/w/api.php?action=query&list=search"
            f"&srsearch={q}&format=json&formatversion=2"
        )
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                hits = data.get("query", {}).get("search", [])
                if hits:
                    return hits[0]["title"]
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. WIKI SLUG BULMA
# ─────────────────────────────────────────────────────────────────────────────

