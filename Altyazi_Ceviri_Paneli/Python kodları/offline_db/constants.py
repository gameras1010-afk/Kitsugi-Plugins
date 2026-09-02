"""
offline_db/constants.py
=======================
Yol sabitleri, TTL değerleri ve meta yönetimi.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List

"""
offline_db_manager.py — Çevrimdışı Anime/Film/Dizi Veri Kaynakları Yöneticisi
==============================================================================
Pipeline'a internetsiz fallback + zenginleştirilmiş metadata sağlar.

Yönetilen veri kaynakları:
  1. AniDB Titles XML     → anime başlıkları + sinonimler   (TTL: 24 saat)
  2. manami-project       → çapraz referans + etiketler     (TTL: 7 gün)
  3. TMDB Movie Export    → 500k+ film başlığı + ID         (TTL: 24 saat)
  4. TMDB TV Export       → 150k+ dizi başlığı + ID         (TTL: 24 saat)

Her çeviriye başlamadan önce TTL kontrolü yapılır:
  • Dosya yoksa: anında indirilir (senkron, ilk çalıştırma)
  • Süresi dolmuşsa: arka planda indirilir (asenkron, kullanıcıyı bekletmez)
  • Güncel ise: direkt kullanılır

Bütünleşme noktaları:
  • media_identifier.py → fetch_media_metadata() öncesi offline lookup (anime+film+dizi)
  • fandom_glossary.py  → _make_slug_candidates() sinonim zenginleştirme
"""

import os
import re
import sys
import json
import gzip
import time
import datetime
import threading
import requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List

# ── Encoding fix (Windows) ────────────────────────────────────────────────────
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ── Sabitler ──────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _DIR = os.path.dirname(sys.executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

ANIDB_JSON_PATH     = os.path.join(_DIR, 'offline_anidb.json')
MANAMI_JSON_PATH    = os.path.join(_DIR, 'offline_manami.json')
TMDB_MOVIE_PATH     = os.path.join(_DIR, 'offline_tmdb_movies.json')
TMDB_TV_PATH        = os.path.join(_DIR, 'offline_tmdb_tv.json')
IMDB_BASICS_PATH    = os.path.join(_DIR, 'offline_imdb_basics.json')
IMDB_AKAS_PATH      = os.path.join(_DIR, 'offline_imdb_akas.json')
WIKI_CHARS_PATH     = os.path.join(_DIR, 'offline_wikidata_chars.json')
WIKI_ENTITIES_PATH  = os.path.join(_DIR, 'offline_wikidata_entities.json')  # mekan+esya+org
META_PATH           = os.path.join(_DIR, 'offline_db_meta.json')
# Kelime frekans sözlükleri (data/ dizini)
_DATA_DIR           = os.path.join(_DIR, 'data')
EN_FREQ_PATH        = os.path.join(_DATA_DIR, 'english_freq.bin')
TR_FREQ_PATH        = os.path.join(_DATA_DIR, 'turkish_freq.bin')
ANIME_NAMES_PATH    = os.path.join(_DATA_DIR, 'anime_names.txt.gz')
# TVmaze karakter cache dizini (per-show)
TVMAZE_CACHE_DIR    = os.path.join(_DIR, 'tvmaze_cache')
# Franchise-specific cache dizini (potterdb, swapi, lotr)
FRANCHISE_CACHE_DIR = os.path.join(_DIR, 'franchise_cache')
# TMDB cast cache dizini (film + dizi cast)
TMDB_CAST_CACHE_DIR = os.path.join(_DIR, 'tmdb_cast_cache')
TMDB_CAST_TTL_DAYS  = 30
TMDB_CAST_API_KEY_PATH = os.path.join(_DIR, 'tmdb_api_key.txt')
TMDB_API_BASE       = "https://api.themoviedb.org/3"

ANIDB_TTL_HOURS      = 24 * 7   # AniDB 403 blogu nedeniyle 7 gun (manami 7 gunluk veriyi zaten kapsıyor)
MANAMI_TTL_DAYS      = 7
TMDB_TTL_HOURS       = 24
IMDB_TTL_DAYS        = 7
WIKI_TTL_DAYS        = 7
WIKI_ENTITIES_TTL    = 30   # mekan/esya/org nadiren degisir
WORD_FREQ_TTL_DAYS   = 30
ANIME_NAMES_TTL_DAYS = 7
TVMAZE_CHAR_TTL_DAYS = 30   # per-show cache
FRANCHISE_TTL_DAYS   = 30   # potterdb/swapi nadiren degisir
DOWNLOAD_TIMEOUT     = 90

# AniDB — resmi HTTPS endpoint (HTTP artik 403 veriyor)
# AniDB throttle kurali: max 1 istek/24 saat, User-Agent zorunlu
ANIDB_URL        = "https://anidb.net/api/anime-titles.xml.gz"
ANIDB_URL_MIRROR = "http://anidb.net/api/anime-titles.xml.gz"  # fallback (eski, deprecated)
MANAMI_URL  = ("https://github.com/manami-project/anime-offline-database"
               "/releases/latest/download/anime-offline-database-minified.json")
# TMDB günlük export — ücretsiz, API key yok
# Format: https://files.tmdb.org/p/exports/movie_ids_MM_DD_YYYY.json.gz
def _tmdb_export_url(kind: str) -> str:
    """kind: 'movie_ids' veya 'tv_series_ids'"""
    d = datetime.datetime.utcnow() - datetime.timedelta(days=1)  # dün = mevcut export
    return f"https://files.tmdb.org/p/exports/{kind}_{d.month:02d}_{d.day:02d}_{d.year}.json.gz"

# AniDB icin ozel User-Agent (robot blogu onlemek icin)
# Kayitli client ismi zorunlu: https://anidb.net/software/add
HEADERS = {"User-Agent": "AnimeSubtitleTranslator/3.0 (offline-db-manager)"}
ANIDB_HEADERS = {
    "User-Agent": "AnimeSubtitleTranslator/3.0 anime-titles-downloader",
    "Accept-Encoding": "gzip",
}
IMDB_URL_BASE  = "https://datasets.imdbws.com"
WIKI_SPARQL    = "https://query.wikidata.org/sparql"

# ── Modül düzeyinde bellek cache ──────────────────────────────────────────────────────
_anidb_cache:         Optional[Dict] = None
_manami_cache:        Optional[Dict] = None
_tmdb_movie_cache:    Optional[Dict] = None
_tmdb_tv_cache:       Optional[Dict] = None
_imdb_basics_cache:   Optional[Dict] = None
_imdb_akas_cache:     Optional[Dict] = None
_wiki_chars_cache:    Optional[List] = None
_wiki_entities_cache: Optional[set]  = None  # mekan+esya+org proper noun seti
_load_lock = threading.Lock()



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 1: META / TTL YÖNETİMİ
# ─────────────────────────────────────────────────────────────────────────────

def _load_meta() -> dict:
    try:
        if os.path.exists(META_PATH):
            with open(META_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_meta(meta: dict):
    try:
        with open(META_PATH, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _needs_update(key: str, ttl_hours: float) -> bool:
    path_map = {
        'anidb':          ANIDB_JSON_PATH,
        'manami':         MANAMI_JSON_PATH,
        'tmdb_movies':    TMDB_MOVIE_PATH,
        'tmdb_tv':        TMDB_TV_PATH,
        'imdb_basics':    IMDB_BASICS_PATH,
        'imdb_akas':      IMDB_AKAS_PATH,
        'wiki_chars':     WIKI_CHARS_PATH,
        'wiki_entities':  WIKI_ENTITIES_PATH,
        'word_freq_en':   EN_FREQ_PATH,
        'word_freq_tr':   TR_FREQ_PATH,
        'anime_names':    ANIME_NAMES_PATH,
    }
    path = path_map.get(key, '')
    if not path or not os.path.exists(path):
        return True
    meta = _load_meta()
    last = meta.get(key, {}).get('updated_at')
    if not last:
        return True
    try:
        dt = datetime.datetime.fromisoformat(last)
        hours_passed = (datetime.datetime.now() - dt).total_seconds() / 3600
        return hours_passed >= ttl_hours
    except Exception:
        return True


def _mark_updated(key: str, version: str = ''):
    meta = _load_meta()
    meta[key] = {
        'updated_at': datetime.datetime.now().isoformat(),
        'version': version,
    }
    _save_meta(meta)


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 2: AniDB TITLES İNDİRME + PARSE
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(title: str) -> str:
    """Karşılaştırma için başlığı küçük harf + sadece alfanumerik."""
    return re.sub(r'[^a-z0-9]', '', title.lower().strip())


