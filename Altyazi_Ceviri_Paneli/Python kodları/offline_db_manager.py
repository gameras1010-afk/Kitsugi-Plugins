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


def _download_anidb(verbose: bool = True) -> bool:
    """
    AniDB Titles XML'i indir, parse et, JSON'a kaydet.
    403 dönerse: mevcut veri korunur (manami zaten kapsıyor), sessizce geçilir.
    """
    if verbose:
        print("[OfflineDB] AniDB Titles indiriliyor...", flush=True)
    try:
        # Önce HTTPS dene, 403 gelirse mirror'u dene
        for url in [ANIDB_URL, ANIDB_URL_MIRROR]:
            r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=ANIDB_HEADERS, stream=True)
            if r.status_code == 200:
                break
            if r.status_code == 403:
                # AniDB bot bloğu — mevcut veri varsa koru, yoksa manami devreye girer
                if os.path.exists(ANIDB_JSON_PATH):
                    if verbose:
                        print("[OfflineDB] AniDB 403 → mevcut veri korunuyor (manami devrede)", flush=True)
                    try:
                        from notif_bus import push_notif as _pn
                        _pn('⚠️ AniDB 403 → mevcut veri korunuyor', 'warning', 5000)
                    except Exception: pass
                    # TTL'yi 7 güne uzat (sık tekrar denemeyi engelle)
                    _mark_updated('anidb', 'kept_403')
                else:
                    if verbose:
                        print("[OfflineDB] AniDB 403 → veri yok, manami devreye giriyor", flush=True)
                    try:
                        from notif_bus import push_notif as _pn
                        _pn('⚠️ AniDB 403 → manami devreye giriyor', 'warning', 5000)
                    except Exception: pass
                return True   # Hata değil, sessizce geç
            # Diğer HTTP hataları
            if verbose:
                print(f"[OfflineDB] AniDB indirme hatası: HTTP {r.status_code} ({url})")
            continue
        else:
            return False   # Her iki URL de başarısız

        xml_bytes = gzip.decompress(r.content)
        root = ET.fromstring(xml_bytes)
    except Exception as e:
        # 403 olmayan network/parse hatası — eski veri varsa koru
        if os.path.exists(ANIDB_JSON_PATH):
            if verbose:
                print(f"[OfflineDB] AniDB hata: {e} → mevcut veri korunuyor")
            _mark_updated('anidb', 'kept_error')
            return True
        if verbose:
            print(f"[OfflineDB] AniDB parse hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    for anime in root.findall('anime'):
        aid = anime.get('aid', '')
        titles_by_lang: Dict[str, List[str]] = {}
        all_titles: List[str] = []
        for t in anime.findall('title'):
            text = (t.text or '').strip()
            if not text:
                continue
            lang = t.get('{http://www.w3.org/XML/1998/namespace}lang', 'x-jat')
            ttype = t.get('type', '')
            titles_by_lang.setdefault(lang, []).append(text)
            all_titles.append(text)

        if not all_titles:
            continue

        # Ana başlık: İngilizce > x-jat (romaji) > ilk bulduğu
        main = (titles_by_lang.get('en', [None])[0] or
                titles_by_lang.get('x-jat', [None])[0] or
                all_titles[0])
        synonyms = [t for t in all_titles if t != main]

        entry = {
            'aid':      aid,
            'title':    main,
            'synonyms': synonyms,
            'langs':    {lang: titles for lang, titles in titles_by_lang.items()},
        }

        # Tüm başlıklardan lookup oluştur (her alternatif ada erişim)
        for title in all_titles:
            key = _normalize(title)
            if key and key not in db:
                db[key] = entry

    try:
        with open(ANIDB_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('anidb', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] AniDB OK: {len(db):,} başlık indexlendi.")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'✅ AniDB OK: {len(db):,} başlık indexlendi', 'positive', 5000)
            except Exception: pass
        return True
    except Exception as e:
        print(f"[OfflineDB] AniDB kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3: manami-project İNDİRME + PARSE
# ─────────────────────────────────────────────────────────────────────────────

def _download_manami(verbose: bool = True) -> bool:
    """manami-project JSON'ını indir, parse et, optimize formatla kaydet."""
    if verbose:
        print("[OfflineDB] manami-project indiriliyor...", flush=True)
    try:
        r = requests.get(MANAMI_URL, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS)
        if r.status_code != 200:
            print(f"[OfflineDB] manami indirme hatası: HTTP {r.status_code}")
            return False
        data = r.json()
    except Exception as e:
        print(f"[OfflineDB] manami parse hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    for anime in data.get('data', []):
        title   = (anime.get('title') or '').strip()
        syns    = [s for s in (anime.get('synonyms') or []) if s]
        tags    = anime.get('tags') or []
        studios = anime.get('studios') or []
        atype   = anime.get('type', 'UNKNOWN')
        status  = anime.get('status', 'UNKNOWN')
        score   = (anime.get('score') or {}).get('arithmeticMean')
        sources = anime.get('sources') or []
        season_info = anime.get('animeSeason') or {}

        # MAL/AniDB/AniList ID'lerini çıkar
        mal_url    = next((s for s in sources if 'myanimelist' in s), '')
        anidb_url  = next((s for s in sources if 'anidb' in s), '')
        anilist_url= next((s for s in sources if 'anilist' in s), '')

        entry = {
            'title':    title,
            'synonyms': syns,
            'tags':     tags[:15],     # Max 15 etiket
            'studios':  studios,
            'type':     atype,
            'status':   status,
            'score':    score,
            'year':     season_info.get('year'),
            'season':   season_info.get('season'),
            'mal_url':  mal_url,
            'anidb_url':anidb_url,
            'anilist_url': anilist_url,
        }

        # Tüm başlıklardan lookup
        for t in ([title] + syns):
            key = _normalize(t)
            if key and key not in db:
                db[key] = entry

    try:
        with open(MANAMI_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('manami', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] manami OK: {len(db):,} başlık indexlendi.")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'✅ Manami DB OK: {len(db):,} anime indexlendi', 'positive', 5000)
            except Exception: pass
        return True
    except Exception as e:
        print(f"[OfflineDB] manami kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 4: VERİTABANI YÜKLEME (Bellek cache)
# ─────────────────────────────────────────────────────────────────────────────

def _load_anidb() -> Dict:
    global _anidb_cache
    if _anidb_cache is not None:
        return _anidb_cache
    with _load_lock:
        if _anidb_cache is not None:
            return _anidb_cache
        if os.path.exists(ANIDB_JSON_PATH):
            try:
                with open(ANIDB_JSON_PATH, 'r', encoding='utf-8') as f:
                    _anidb_cache = json.load(f)
                return _anidb_cache
            except Exception:
                pass
    return {}


def _load_manami() -> Dict:
    global _manami_cache
    if _manami_cache is not None:
        return _manami_cache
    with _load_lock:
        if _manami_cache is not None:
            return _manami_cache
        if os.path.exists(MANAMI_JSON_PATH):
            try:
                with open(MANAMI_JSON_PATH, 'r', encoding='utf-8') as f:
                    _manami_cache = json.load(f)
                return _manami_cache
            except Exception:
                pass
    return {}


def _invalidate_cache():
    global _anidb_cache, _manami_cache, _tmdb_movie_cache, _tmdb_tv_cache
    global _imdb_basics_cache, _imdb_akas_cache, _wiki_chars_cache
    _anidb_cache       = None
    _manami_cache      = None
    _tmdb_movie_cache  = None
    _tmdb_tv_cache     = None
    _imdb_basics_cache = None
    _imdb_akas_cache   = None
    _wiki_chars_cache  = None


# ───────────────────────────────────────────────────────────────
# BÖLÜM 3b: TMDB DAILY EXPORT ÜÜSETSiZ İNDIRME + PARSE
# film: movie_ids_MM_DD_YYYY.json.gz  |  dizi: tv_series_ids_MM_DD_YYYY.json.gz
# Her satır: {"id":..., "original_title":"...", "popularity":...}
# ───────────────────────────────────────────────────────────────

def _download_tmdb(kind: str, out_path: str, meta_key: str, verbose: bool = True) -> bool:
    """
    TMDB günlük export indir ve {normalized_title: {id, title, type}} JSON olarak kaydet.
    kind: 'movie_ids' veya 'tv_series_ids'
    """
    label = 'Film' if kind == 'movie_ids' else 'TV/Dizi'
    if verbose:
        print(f"[OfflineDB] TMDB {label} export indiriliyor...", flush=True)
    url = _tmdb_export_url(kind)
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            # Dünün dosyası yoksa avantünkü dene
            d2 = datetime.datetime.utcnow() - datetime.timedelta(days=2)
            url2 = f"https://files.tmdb.org/p/exports/{kind}_{d2.month:02d}_{d2.day:02d}_{d2.year}.json.gz"
            r = requests.get(url2, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
            if r.status_code != 200:
                print(f"[OfflineDB] TMDB {label} indirme hatası: HTTP {r.status_code}")
                return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] TMDB {label} hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    title_field = 'original_title' if kind == 'movie_ids' else 'original_name'
    media_type  = 'movie' if kind == 'movie_ids' else 'series'

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        tmdb_id  = obj.get('id')
        title    = (obj.get(title_field) or '').strip()
        pop      = obj.get('popularity', 0)
        if not title or not tmdb_id:
            continue
        entry = {
            'id':    tmdb_id,
            'title': title,
            'type':  media_type,
            'popularity': pop,
        }
        norm = _normalize(title)
        if norm and norm not in db:
            db[norm] = entry

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated(meta_key, f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] TMDB {label} OK: {len(db):,} başlık indexlendi.")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'✅ TMDB {label} OK: {len(db):,} başlık', 'positive', 5000)
            except Exception: pass
        return True
    except Exception as e:
        print(f"[OfflineDB] TMDB {label} kaydetme hatası: {e}")
        return False


def _load_tmdb_movies() -> Dict:
    global _tmdb_movie_cache
    if _tmdb_movie_cache is not None:
        return _tmdb_movie_cache
    with _load_lock:
        if _tmdb_movie_cache is not None:
            return _tmdb_movie_cache
        if os.path.exists(TMDB_MOVIE_PATH):
            try:
                with open(TMDB_MOVIE_PATH, 'r', encoding='utf-8') as f:
                    _tmdb_movie_cache = json.load(f)
                return _tmdb_movie_cache
            except Exception:
                pass
    return {}


def _load_tmdb_tv() -> Dict:
    global _tmdb_tv_cache
    if _tmdb_tv_cache is not None:
        return _tmdb_tv_cache
    with _load_lock:
        if _tmdb_tv_cache is not None:
            return _tmdb_tv_cache
        if os.path.exists(TMDB_TV_PATH):
            try:
                with open(TMDB_TV_PATH, 'r', encoding='utf-8') as f:
                    _tmdb_tv_cache = json.load(f)
                return _tmdb_tv_cache
            except Exception:
                pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3c: IMDB BASICS + AKAS
# ─────────────────────────────────────────────────────────────────────────────

def _download_imdb_basics(verbose: bool = True) -> bool:
    """IMDB title.basics — sadece film/dizi (tvEpisode değil), animation genre ağırlıklı."""
    if verbose:
        print("[OfflineDB] IMDB Basics indiriliyor (streaming)...", flush=True)
    url = f"{IMDB_URL_BASE}/title.basics.tsv.gz"
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            print(f"[OfflineDB] IMDB Basics hatası: HTTP {r.status_code}")
            return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] IMDB Basics indirme hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    KEEP_TYPES = {'movie', 'tvSeries', 'tvMiniSeries', 'tvMovie', 'tvSpecial', 'short'}
    lines = raw.split(b'\n')
    header = lines[0].decode('utf-8', errors='replace').split('\t')
    idx = {h: i for i, h in enumerate(header)}

    for line in lines[1:]:
        row = line.decode('utf-8', errors='replace').split('\t')
        if len(row) < 5:
            continue
        try:
            ttype = row[idx.get('titleType', 1)]
            if ttype not in KEEP_TYPES:
                continue
            tconst   = row[idx.get('tconst', 0)]
            primary  = (row[idx.get('primaryTitle', 2)] or '').strip()
            original = (row[idx.get('originalTitle', 3)] or '').strip()
            year     = row[idx.get('startYear', 5)]
            genres   = row[idx.get('genres', 8)]
            if not primary or primary == r'\N':
                continue
            entry = {
                'id':       tconst,
                'title':    primary,
                'original': original if original != primary else '',
                'type':     ttype,
                'year':     year if year != r'\N' else '',
                'genres':   genres if genres != r'\N' else '',
            }
            for t in set([primary, original]):
                if not t or t == r'\N':
                    continue
                key = _normalize(t)
                if key and key not in db:
                    db[key] = entry
        except Exception:
            continue

    try:
        with open(IMDB_BASICS_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('imdb_basics', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] IMDB Basics OK: {len(db):,} başlık indexlendi.")
        return True
    except Exception as e:
        print(f"[OfflineDB] IMDB Basics kaydetme hatası: {e}")
        return False


def _download_imdb_akas(verbose: bool = True) -> bool:
    """IMDB title.akas — sadece TR (Türkçe) ve JA (Japonca) satırlar stream-parse edilir."""
    if verbose:
        print("[OfflineDB] IMDB Akas indiriliyor (streaming, büyük dosya)...", flush=True)
    url = f"{IMDB_URL_BASE}/title.akas.tsv.gz"
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            print(f"[OfflineDB] IMDB Akas hatası: HTTP {r.status_code}")
            return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] IMDB Akas indirme hatası: {e}")
        return False

    # {normalized_localized_title: {imdb_id, title, region, lang}}
    db: Dict[str, dict] = {}
    KEEP_REGIONS = {'TR', 'JP', 'US'}   # TR=Türkçe, JP=Japonca, US=İngilizce
    lines = raw.split(b'\n')
    header = lines[0].decode('utf-8', errors='replace').split('\t')
    idx = {h: i for i, h in enumerate(header)}

    for line in lines[1:]:
        row = line.decode('utf-8', errors='replace').split('\t')
        if len(row) < 4:
            continue
        try:
            region = (row[idx.get('region', 3)] or '').strip()
            if region not in KEEP_REGIONS:
                continue
            tconst = row[idx.get('titleId', 0)]
            title  = (row[idx.get('title', 2)] or '').strip()
            lang   = (row[idx.get('language', 4)] or '').strip()
            if not title or title == r'\N':
                continue
            entry = {
                'imdb_id': tconst,
                'title':   title,
                'region':  region,
                'lang':    lang,
            }
            key = _normalize(title)
            if key and key not in db:
                db[key] = entry
        except Exception:
            continue

    try:
        with open(IMDB_AKAS_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('imdb_akas', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] IMDB Akas OK: {len(db):,} yerel başlık indexlendi (TR+JP+US).")
        return True
    except Exception as e:
        print(f"[OfflineDB] IMDB Akas kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3c-EXTRA: WIKIDATA BAŞLIK → DOĞRU ENTİTY (P31 TÜR FİLTRESİ)
# ─────────────────────────────────────────────────────────────────────────────
# Wikidata'da her şeyin "instance of" (P31) özelliği var:
#   Q5398426  = television series (herhangi bir dizi)
#   Q11424    = film
#   Q63952888 = anime television series
#   Q20650540 = anime film
#   Q24856    = film series
#   Q83267    = fiction (genel)
# Bu sayede "Dark" → TV dizisi entity'sini, borsa dark pool'larını değil, buluruz.
# ─────────────────────────────────────────────────────────────────────────────

_WIKIDATA_TITLE_CACHE_DIR = os.path.join(_DIR, 'wikidata_title_cache')

# Wikidata P31 değerleri → bizim tür sistemimize map
_P31_TYPE_MAP = {
    # TV Dizi
    'Q5398426':  'series',   # television series
    'Q1366112':  'series',   # web series
    'Q3464665':  'series',   # television program
    'Q15416':    'series',   # television show
    'Q21191270': 'series',   # television series episode (parent)
    'Q1257444':  'series',   # TV miniseries
    # Anime
    'Q63952888': 'anime',    # anime television series
    'Q21174398': 'anime',    # anime OVA
    'Q20650540': 'anime',    # anime film
    'Q220898':   'anime',    # anime
    # Film
    'Q11424':    'movie',    # film
    'Q202866':   'movie',    # animated film
    'Q29168811': 'movie',    # documentary film
    'Q24856':    'movie',    # film series
    'Q506240':   'movie',    # television film
}

# Tür → hangi P31 ID'leri kabul edilir
_TYPE_ALLOWED_P31 = {
    'series': {'Q5398426','Q1366112','Q3464665','Q15416','Q1257444','Q21191270'},
    'anime':  {'Q63952888','Q21174398','Q20650540','Q220898','Q5398426'},
    'movie':  {'Q11424','Q202866','Q29168811','Q24856','Q506240','Q20650540'},
    'unknown': None,  # None = hepsi kabul
}


def lookup_wikidata_by_title(title: str, media_type: str = 'unknown',
                              verbose: bool = False) -> Optional[dict]:
    """
    Wikidata SPARQL ile başlık + P31 tür filtresi kullanarak doğru entity'yi bulur.
    "Dark" (TV dizisi) ile "Aquis Dark Pool" (borsa) arasındaki farkı P31'e göre ayırt eder.

    Döndürür:
        {
            'qid':        'Q28259127',
            'title':      'Dark',
            'type':       'series',           # bizim tür sistemimiz
            'p31_labels': ['television series', 'German television series'],
            'characters': ['Jonas Kahnwald', ...],
            'locations':  ['Winden', ...],
        }
    veya None
    """
    os.makedirs(_WIKIDATA_TITLE_CACHE_DIR, exist_ok=True)
    safe = re.sub(r'[^a-z0-9]', '_', title.lower())[:60]
    cache_path = os.path.join(_WIKIDATA_TITLE_CACHE_DIR, f"{safe}_{media_type}.json")

    # Cache kontrolü (TTL 60 gün)
    if os.path.exists(cache_path):
        try:
            age = (time.time() - os.path.getmtime(cache_path)) / 86400
            if age < 60:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if not cached.get("found"):
                        return None
                    return cached
        except Exception:
            pass

    # Tür kısıtı — Python tarafında P31 map ile filtrele (SPARQL filter query'yi kırıyor)
    allowed = _TYPE_ALLOWED_P31.get(media_type)  # None = hepsi kabul

    # Başlık kaçış
    title_esc = title.replace('"', '\\"')

    # 1. ADIM: rdfs:label ile kesin eşleşme — tipe filtre YOK, Python'da yapılır
    QUERY_EXACT = (
        'SELECT DISTINCT ?item ?itemLabel ?p31 ?p31Label WHERE {'
        f' ?item rdfs:label "{title_esc}"@en .'
        ' ?item wdt:P31 ?p31 .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 30'
    )
    # 2. ADIM: skos:altLabel ile dene
    QUERY_ALT = (
        'SELECT DISTINCT ?item ?itemLabel ?p31 ?p31Label WHERE {'
        f' ?item skos:altLabel "{title_esc}"@en .'
        ' ?item wdt:P31 ?p31 .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 30'
    )

    headers = {
        "User-Agent": "AnimeSubtitleTranslator/3.0 (wikidata-title-lookup)",
        "Accept":     "application/json",
    }

    best_qid = None
    best_type = None
    p31_labels = []
    _current_priority = -1  # Şu ana kadar seçilen P31'in önceliği

    # P31 öncelik tablosu — döngü dışında (bir kere oluştur)
    _P31_PRIORITY = {
        'Q5398426':  1000,  # television series
        'Q63952888': 1000,  # anime television series
        'Q11424':    1000,  # film
        'Q1257444':  900,   # TV miniseries
        'Q1366112':  900,   # web series
        'Q202866':   900,   # animated film
        'Q20650540': 900,   # anime film
        'Q220898':   850,   # anime (genel)
        'Q506240':   800,   # television film
        'Q24856':    700,   # film series
        'Q29168811': 700,   # documentary film
        'Q3464665':  600,   # television program
        'Q15416':    500,   # television show
        'Q21191270': 100,   # television series episode (düşük öncelik)
    }

    for qname, query in [("exact", QUERY_EXACT), ("alt", QUERY_ALT)]:
        try:
            resp = requests.get(
                WIKI_SPARQL,
                params={"query": query, "format": "json"},
                headers=headers,
                timeout=20,
            )
            if resp.status_code != 200:
                continue
            bindings = resp.json().get("results", {}).get("bindings", [])
            if not bindings:
                continue

            for b in bindings:
                qid   = b.get("item", {}).get("value", "").split("/")[-1]
                p31   = b.get("p31",  {}).get("value", "").split("/")[-1]
                p31_l = b.get("p31Label", {}).get("value", "")

                mapped = _P31_TYPE_MAP.get(p31)
                if not mapped:
                    continue  # Bilinmeyen P31 (borsa, müzik, gen...) → atla

                # Tür kısıtı: eğer allowed varsa ve bu P31 izin verilenlerden değilse atla
                if allowed and p31 not in allowed:
                    continue

                # Öncelik sırası: kesin tür (Q5398426 televizyon dizisi) > geniş tür (Q21191270 bölüm)
                # P31 öncelik puanı: en yüksek = en kesin (1000), en düşük = en belirsiz (1)
                _P31_PRIORITY = {
                    # Kesin türler — yüksek öncelik
                    'Q5398426':  1000,  # television series
                    'Q63952888': 1000,  # anime television series
                    'Q11424':    1000,  # film
                    'Q1257444':  900,   # TV miniseries
                    'Q1366112':  900,   # web series
                    'Q202866':   900,   # animated film
                    'Q20650540': 900,   # anime film
                    'Q220898':   850,   # anime (genel)
                    'Q506240':   800,   # television film
                    'Q24856':    700,   # film series
                    'Q29168811': 700,   # documentary film
                    'Q3464665':  600,   # television program
                    'Q15416':    500,   # television show
                    # Düşük öncelik — bölüm veya genel
                    'Q21191270': 100,   # television series episode
                }
                priority = _P31_PRIORITY.get(p31, 200)

                # Daha önce bulunan varsa sadece daha yüksek öncelikliyse güncelle
                if priority > _current_priority:
                    best_qid  = qid
                    best_type = mapped
                    _current_priority = priority
                if p31_l and p31_l not in p31_labels:
                    p31_labels.append(p31_l)

            if best_qid:
                if verbose:
                    print(f"[Wikidata] '{title}' → {best_qid} ({best_type}) via {qname}")
                break

        except Exception as e:
            if verbose:
                print(f"[Wikidata] Sorgu hatası ({qname}): {e}")
            time.sleep(2)

    if not best_qid:
        # Not-found kaydı — 7 gün TTL (kısa)
        _save_json(cache_path, {"found": False, "title": title})
        return None

    # 3. ADIM: Bu QID'den karakter ve lokasyon çek
    characters = []
    locations  = []

    # Karakter sorgusu — iki strateji:
    # a) P1441 (fictional character part of): standart bağlantı
    # b) P161 (cast member): gerçek oyuncu değil — bu ikisi farklı, P1441 tercihli
    # c) Hem P1441 hem P179 (part of series) ile UNION
    QUERY_CHARS_A = (
        'SELECT DISTINCT ?charLabel WHERE {'
        ' { ?char wdt:P31 wd:Q95074 .'    # fictional character
        f'   ?char wdt:P1441 wd:{best_qid} . }}'
        ' UNION'
        ' { ?char wdt:P31 wd:Q15711870 .'  # anime character
        f'   ?char wdt:P1441 wd:{best_qid} . }}'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 100'
    )
    QUERY_LOCS = (
        'SELECT DISTINCT ?locLabel WHERE {'
        ' ?loc wdt:P31/wdt:P279* wd:Q17334923 .'  # fictional location
        f' ?loc wdt:P1441 wd:{best_qid} .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 50'
    )
    for q, lst, label_key in [(QUERY_CHARS_A, characters, "charLabel"),
                               (QUERY_LOCS,   locations,  "locLabel")]:
        try:
            r = requests.get(
                WIKI_SPARQL,
                params={"query": q, "format": "json"},
                headers=headers, timeout=20,
            )
            if r.status_code == 200:
                for b in r.json().get("results", {}).get("bindings", []):
                    lbl = b.get(label_key, {}).get("value", "").strip()
                    if lbl and not lbl.startswith("Q") and len(lbl) > 1:
                        lst.append(lbl)
            time.sleep(0.5)
        except Exception:
            pass

    result = {
        "found":      True,
        "qid":        best_qid,
        "title":      title,
        "type":       best_type,
        "p31_labels": p31_labels,
        "characters": characters,
        "locations":  locations,
    }
    _save_json(cache_path, result)
    if verbose:
        print(f"[Wikidata] {title}: {len(characters)} karakter, {len(locations)} lokasyon ({p31_labels[:2]})")
    return result


def _save_json(path: str, data: dict) -> None:
    """Güvenli JSON yazımı."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.tmp',
                                         dir=os.path.dirname(path), delete=False) as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tmp = tf.name
        os.replace(tmp, path)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3d: WIKIDATA ANİME KARAKTERLERİ (SPARQL)
# ─────────────────────────────────────────────────────────────────────────────


def _download_wikidata_chars(verbose: bool = True) -> bool:
    """
    Wikidata SPARQL → tüm kurgusal karakter adlarını indir.
    Q15711870 = 'anime character' (özel)
    Q95074    = 'fictional character' (geniş: anime + film + dizi hepsi)

    Sonuç: fandom_glossary'e ve build_translation_context'e
    'asla çevirme' koruması için kullanılır.
    """
    if verbose:
        print("[OfflineDB] Wikidata kurgusal karakterler indiriliyor (SPARQL)...", flush=True)

    # İki sorgu: önce anime-spesifik, sonra genel kurgusal karakterler
    QUERIES = [
        ("anime-char Q15711870", "SELECT ?char ?charLabel WHERE { ?char wdt:P31 wd:Q15711870. SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } } LIMIT %d OFFSET %d"),
        ("fictional-char Q95074", "SELECT ?char ?charLabel WHERE { ?char wdt:P31 wd:Q95074. SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } } LIMIT %d OFFSET %d"),
    ]
    PAGE_SIZE = 10000
    MAX_PAGES = 120
    all_chars: set = set()
    sparql_headers = {
        "User-Agent": "AnimeSubtitleTranslator/3.0 (wikidata-chars)",
        "Accept":     "application/json",
    }

    for qname, QUERY in QUERIES:
        if verbose:
            print(f"[OfflineDB]   Sorgu: {qname}...", flush=True)
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            q = QUERY % (PAGE_SIZE, offset)
            try:
                resp = requests.get(
                    WIKI_SPARQL,
                    params={"query": q, "format": "json"},
                    headers=sparql_headers,
                    timeout=90,
                )
                if resp.status_code == 429:
                    time.sleep(30)
                    continue
                if resp.status_code != 200:
                    if verbose:
                        print(f"[OfflineDB] Wikidata HTTP {resp.status_code} — {qname} durduruluyor")
                    break
                data = resp.json()
                bindings = data.get("results", {}).get("bindings", [])
                if not bindings:
                    break
                for b in bindings:
                    label = b.get("charLabel", {}).get("value", "").strip()
                    # Q123 ID'li etiket yok = atla; 1 karakterlik = atla; sayı = atla
                    if label and not label.startswith("Q") and len(label) > 1 and not label.isdigit():
                        all_chars.add(label)
                if verbose and page % 5 == 0:
                    print(f"[OfflineDB]   Sayfa {page+1}: toplam {len(all_chars):,} karakter")
                if len(bindings) < PAGE_SIZE:
                    break
                time.sleep(1.5)
            except Exception as e:
                if verbose:
                    print(f"[OfflineDB] Wikidata hata (sayfa {page}): {e}")
                time.sleep(5)
                break

    if not all_chars:
        return False

    chars_list = sorted(all_chars)
    try:
        with open(WIKI_CHARS_PATH, 'w', encoding='utf-8') as f:
            json.dump(chars_list, f, ensure_ascii=False)
        _mark_updated('wiki_chars', f"{len(chars_list)}_chars")
        if verbose:
            print(f"[OfflineDB] Wikidata Chars OK: {len(chars_list):,} karakter kaydedildi.")
        return True
    except Exception as e:
        print(f"[OfflineDB] Wikidata kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3e: ANİDB PER-ANİME KARAKTER LAZY-LOAD
# ─────────────────────────────────────────────────────────────────────────────

_ANIDB_CHAR_CACHE_DIR = os.path.join(_DIR, 'offline_anidb_chars')

def _get_anidb_aid(title: str) -> Optional[str]:
    """AniDB Titles dump'tan anime title → AID (AniDB ID) bul."""
    key = _normalize(title)
    if not key:
        return None
    anidb = _load_anidb()
    entry = anidb.get(key)
    if entry:
        return str(entry.get('aid', ''))
    # Manami'de de dene
    manami = _load_manami()
    entry = manami.get(key)
    if entry:
        return str(entry.get('anidb', ''))
    return None


def fetch_anidb_characters(title: str, verbose: bool = True) -> List[str]:
    """
    Belirli bir anime için AniDB HTTP API'den karakter adlarını çek.
    Sonuç disk'e cache'lenir (per-anime JSON).
    Rate limit: 1 istek / 2 saniye → ilk çağrıda birkaç sn bekler.

    Döndürür: ['Kirito', 'Asuna', 'Klein', ...]
    """
    os.makedirs(_ANIDB_CHAR_CACHE_DIR, exist_ok=True)
    key = _normalize(title)
    if not key:
        return []

    # Disk cache kontrol
    safe_name = re.sub(r'[^\w]', '_', key)[:60]
    cache_file = os.path.join(_ANIDB_CHAR_CACHE_DIR, f"{safe_name}.json")
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            age_days = (time.time() - mtime) / 86400
            if age_days < 30:  # 30 gün geçerli
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('characters', [])
        except Exception:
            pass

    # AniDB AID bul
    aid = _get_anidb_aid(title)
    if not aid:
        if verbose:
            print(f"[OfflineDB] AniDB AID bulunamadı: '{title}'")
        return []

    # AniDB HTTP API
    # Not: client/clientver kayıt gerektirir ama titles dump ile cross-ref yapılabilir
    # En kolay yol: AniDB wiki sayfasından XML parse
    try:
        url = f"https://api.anidb.net:9000/httpapi?request=anime&aid={aid}&client=httpapi&clientver=1&protover=1"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "AnimeSubtitleTranslator/3.0"})
        if resp.status_code != 200:
            if verbose:
                print(f"[OfflineDB] AniDB API HTTP {resp.status_code} — AID {aid}")
            return []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        chars = []
        # AniDB XML: <characters><character>...<name><kanji/><latin/></name>...
        for char_elem in root.iter('character'):
            name_elem = char_elem.find('name')
            if name_elem is None:
                continue
            latin = name_elem.findtext('latin', '').strip()
            kanji = name_elem.findtext('kanji', '').strip()
            if latin and latin not in chars:
                chars.append(latin)
            elif kanji and kanji not in chars:
                chars.append(kanji)

        if not chars:
            # Fallback: <romanji> veya <name> direkt
            for char_elem in root.iter('character'):
                n = char_elem.findtext('name', '').strip()
                if n and n not in chars:
                    chars.append(n)

        # Disk'e kaydet
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'aid': aid, 'title': title, 'characters': chars,
                       'fetched_at': datetime.datetime.now().isoformat()}, f, ensure_ascii=False)
        if verbose:
            print(f"[OfflineDB] AniDB karakter lazy-load: '{title}' → {len(chars)} karakter")
        return chars

    except Exception as e:
        if verbose:
            print(f"[OfflineDB] AniDB karakter hata: {e}")
        return []


def get_characters_for_title(title: str, media_type: str = 'anime') -> List[str]:
    """
    Bir başlık için tüm kaynaklardan karakter adlarını toplar.
    Önce disk cache, sonra AniDB lazy-load, sonra Wikidata genel listesi.

    Kullanım yerleri:
      - build_translation_context() → CHARACTERS satırı
      - fandom_glossary.get_prompt_terms() → ek karakter
      - ass_qa_checker → retry sırasında proper noun koruması
    """
    chars: List[str] = []

    if media_type == 'anime':
        # 1. AniDB lazy-load (seri-spesifik)
        anidb_chars = fetch_anidb_characters(title, verbose=False)
        chars.extend(anidb_chars)

    # 2. Wikidata genel listesi (500k+ kurgusal karakter — doğrulama filtresi)
    wiki_chars = _load_wiki_chars()
    # Bunları direkt eklemeyiz (çok büyük), sadece lookup için kullanılır
    # → get_wikidata_char_set() ile erişilir

    # Tekrar kaldır
    seen = set()
    result = []
    for c in chars:
        cn = c.strip()
        if cn and cn.lower() not in seen:
            seen.add(cn.lower())
            result.append(cn)
    return result


def get_wikidata_char_set() -> set:
    """
    Wikidata karakter listesini set olarak döner.
    Hızlı `in` kontrolü için kullanılır:
    → "Bu kelime bilinen bir kurgusal karakter adı mı?"
    """
    return set(_load_wiki_chars())


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3e-2: WIKIDATA GENIŞ VARLIK SETİ (mekan, eşya, organizasyon, araç)
# ─────────────────────────────────────────────────────────────────────────────

def _download_wikidata_entities(verbose: bool = True) -> bool:
    """
    Kurgusal mekan, silah/esya, arac, organizasyon adlarini indir.
    Animelerin otesinde film ve dizilerdeki proper noun'lari kapsar.
    TTL: 30 gun | Dosya: offline_wikidata_entities.json
    """
    if verbose:
        print("[OfflineDB] Wikidata genis varlik seti indiriliyor...", flush=True)

    QUERIES = [
        ('Q17537576', 'Kurgusal Mekan'),
        ('Q188145',   'Kurgusal Silah/Esya'),
        ('Q1958614',  'Kurgusal Arac'),
        ('Q43229',    'Kurgusal Organizasyon'),
    ]
    QUERY_TMPL = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31/wdt:P279* wd:%s.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT %d OFFSET %d
    """
    PAGE_SIZE = 5000
    MAX_PAGES = 20
    all_entities: set = set()
    sparql_hdrs = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}

    for qid, label in QUERIES:
        if verbose:
            print(f"[OfflineDB]   {label} ({qid})...")
        for page in range(MAX_PAGES):
            q = QUERY_TMPL % (qid, PAGE_SIZE, page * PAGE_SIZE)
            try:
                resp = requests.get(WIKI_SPARQL, params={"query": q, "format": "json"},
                                    headers=sparql_hdrs, timeout=60)
                if resp.status_code != 200:
                    break
                bindings = resp.json().get("results", {}).get("bindings", [])
                if not bindings:
                    break
                for b in bindings:
                    lbl = b.get("itemLabel", {}).get("value", "").strip()
                    if lbl and not lbl.startswith("Q") and len(lbl) > 1:
                        all_entities.add(lbl)
                if len(bindings) < PAGE_SIZE:
                    break
                time.sleep(1.5)
            except Exception as e:
                if verbose:
                    print(f"[OfflineDB]   {label} hata: {e}")
                break
        if verbose:
            print(f"[OfflineDB]   {label}: toplam {len(all_entities):,}")

    if not all_entities:
        return False
    try:
        lst = sorted(all_entities)
        with open(WIKI_ENTITIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(lst, f, ensure_ascii=False)
        _mark_updated('wiki_entities', f"{len(lst)}_entities")
        if verbose:
            print(f"[OfflineDB] Wikidata Entities OK: {len(lst):,} varlik")
        return True
    except Exception as e:
        print(f"[OfflineDB] Wikidata entities kaydetme hatasi: {e}")
        return False


def _load_wiki_entities() -> set:
    global _wiki_entities_cache
    if _wiki_entities_cache is not None:
        return _wiki_entities_cache
    with _load_lock:
        if _wiki_entities_cache is not None:
            return _wiki_entities_cache
        if os.path.exists(WIKI_ENTITIES_PATH):
            try:
                with open(WIKI_ENTITIES_PATH, 'r', encoding='utf-8') as f:
                    _wiki_entities_cache = set(json.load(f))
                return _wiki_entities_cache
            except Exception:
                pass
    _wiki_entities_cache = set()
    return _wiki_entities_cache


def get_wikidata_entity_set() -> set:
    """Kurgusal mekan, esya, arac, org adlarini set olarak doner."""
    return _load_wiki_entities()


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3f: KELIME FREKANS SÖZLÜKLERİ + ANİME İSİM LİSTESİ
# hermitdave/FrequencyWords → EN + TR frekans
# ryuuganime/animanga-wordlist + Jikan → Anime isim listesi
# ─────────────────────────────────────────────────────────────────────────────

def _download_word_freqs(verbose: bool = True) -> bool:
    """
    EN + TR kelime frekans sözlüklerini günceller.
    Kaynak: hermitdave/FrequencyWords (GitHub raw)
    Çıktı: data/english_freq.bin + data/turkish_freq.bin (pickle)
    TTL: 30 gün
    """
    import pickle
    os.makedirs(_DATA_DIR, exist_ok=True)
    if verbose:
        print("[OfflineDB] EN+TR Frekans sözlükleri güncelleniyor...", flush=True)

    URLS = {
        'en': "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
        'tr': "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/tr/tr_50k.txt",
    }
    PATHS = {'en': EN_FREQ_PATH, 'tr': TR_FREQ_PATH}
    TR_CORE = ['bir','bu','ne','ve','için','mi','de','o','ben','çok','ama','evet',
               'var','da','mı','değil','şey','hayır','daha','sen','kadar','bana',
               'gibi','yok','bunu','onu','iyi','tamam','beni','seni','her','benim']
    success = True
    for lang, url in URLS.items():
        try:
            resp = requests.get(url, timeout=30, headers=HEADERS)
            if resp.status_code != 200:
                if verbose: print(f"[OfflineDB] FrequencyWords {lang} HTTP {resp.status_code}")
                success = False; continue
            freq = {}
            for line in resp.text.splitlines():
                parts = line.strip().split()
                if len(parts) == 2:
                    try:
                        w, c = parts[0].lower(), int(parts[1])
                        if 1 <= len(w) <= 30:
                            freq[w] = c
                    except ValueError:
                        pass
            if lang == 'tr':
                for w in TR_CORE:
                    if w not in freq: freq[w] = 1000
            with open(PATHS[lang], 'wb') as f:
                pickle.dump(freq, f, protocol=pickle.HIGHEST_PROTOCOL)
            if verbose:
                print(f"[OfflineDB] {lang.upper()} frekans OK: {len(freq):,} kelime")
        except Exception as e:
            if verbose: print(f"[OfflineDB] FrequencyWords {lang} hata: {e}")
            success = False

    if success:
        _mark_updated('word_freq_en', 'hermitdave_50k')
        _mark_updated('word_freq_tr', 'hermitdave_50k')
    return success


def _download_anime_names(verbose: bool = True) -> bool:
    """
    Anime karakter/başlık isimlerini günceller (content_detector için).
    Kaynak: ryuuganime/animanga-wordlist + Jikan API top characters
    Çıktı: data/anime_names.txt.gz
    TTL: 7 gün
    """
    os.makedirs(_DATA_DIR, exist_ok=True)
    if verbose:
        print("[OfflineDB] Anime isim listesi güncelleniyor...", flush=True)

    names: set = set()

    # 1. ryuuganime animanga-wordlist
    RYUU_URLS = [
        "https://raw.githubusercontent.com/ryuuganime/animanga-wordlist/main/dictionaries/characters.txt",
        "https://raw.githubusercontent.com/ryuuganime/animanga-wordlist/main/dictionaries/anime.txt",
    ]
    for url in RYUU_URLS:
        try:
            resp = requests.get(url, timeout=20, headers=HEADERS)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    for w in re.split(r'[\s\-_/,]+', line):
                        w = w.strip().lower()
                        if w and re.match(r'^[a-z]{2,25}$', w):
                            names.add(w)
        except Exception as e:
            if verbose: print(f"[OfflineDB] ryuuganime hata: {e}")

    # 2. Jikan API top characters (3 sayfa)
    for page in range(1, 4):
        try:
            resp = requests.get(
                f"https://api.jikan.moe/v4/top/characters?page={page}",
                timeout=15, headers=HEADERS
            )
            if resp.status_code == 200:
                data = resp.json()
                for char in data.get('data', []):
                    name = char.get('name', '')
                    for part in re.split(r'[,\s]+', name):
                        part = part.strip().lower()
                        if part and re.match(r'^[a-z]{2,20}$', part):
                            names.add(part)
            time.sleep(0.5)
        except Exception:
            break

    # 3. Wikidata karakter listesinden de ekle
    if os.path.exists(WIKI_CHARS_PATH):
        try:
            with open(WIKI_CHARS_PATH, 'r', encoding='utf-8') as f:
                wiki = json.load(f)
            for name in wiki:
                for part in name.split():
                    p = part.strip().lower()
                    if p and re.match(r'^[a-z]{2,25}$', p):
                        names.add(p)
        except Exception:
            pass

    # Genel İngilizce kelimeleri filtrele
    _STOP = {'an','or','is','it','if','in','on','at','to','be','by','he','we',
              'me','hi','so','no','ok','go','do','my','up','oh','ai','ma','le',
              'la','re','de','en','un','el','lo','as','am','us','yo','the','and'}
    names -= _STOP
    names = {n for n in names if re.match(r'^[a-z]{2,25}$', n)}

    if not names:
        return False

    try:
        import gzip as _gz
        with _gz.open(ANIME_NAMES_PATH, 'wt', encoding='utf-8', compresslevel=9) as f:
            for n in sorted(names):
                f.write(n + '\n')
        _mark_updated('anime_names', f"{len(names)}_names")
        if verbose:
            print(f"[OfflineDB] Anime isim listesi OK: {len(names):,} isim")
        return True
    except Exception as e:
        if verbose: print(f"[OfflineDB] anime_names kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# YÜKLEME FONKSİYONLARI — IMDB + Wikidata
# ─────────────────────────────────────────────────────────────────────────────

def _load_imdb_basics() -> Dict:
    global _imdb_basics_cache
    if _imdb_basics_cache is not None:
        return _imdb_basics_cache
    with _load_lock:
        if _imdb_basics_cache is not None:
            return _imdb_basics_cache
        if os.path.exists(IMDB_BASICS_PATH):
            try:
                with open(IMDB_BASICS_PATH, 'r', encoding='utf-8') as f:
                    _imdb_basics_cache = json.load(f)
                return _imdb_basics_cache
            except Exception:
                pass
    return {}

def _load_imdb_akas() -> Dict:
    global _imdb_akas_cache
    if _imdb_akas_cache is not None:
        return _imdb_akas_cache
    with _load_lock:
        if _imdb_akas_cache is not None:
            return _imdb_akas_cache
        if os.path.exists(IMDB_AKAS_PATH):
            try:
                with open(IMDB_AKAS_PATH, 'r', encoding='utf-8') as f:
                    _imdb_akas_cache = json.load(f)
                return _imdb_akas_cache
            except Exception:
                pass
    return {}

def _load_wiki_chars() -> List:
    global _wiki_chars_cache
    if _wiki_chars_cache is not None:
        return _wiki_chars_cache
    with _load_lock:
        if _wiki_chars_cache is not None:
            return _wiki_chars_cache
        if os.path.exists(WIKI_CHARS_PATH):
            try:
                with open(WIKI_CHARS_PATH, 'r', encoding='utf-8') as f:
                    _wiki_chars_cache = json.load(f)
                return _wiki_chars_cache
            except Exception:
                pass
    return []


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3g: TVMAZE LAZY-LOAD (Dizi Karakterleri)
# api.tvmaze.com — ucretsiz, auth yok, CC BY-SA
# AniDB'nin dizi karsiligi — per-show disk cache + TTL
# ─────────────────────────────────────────────────────────────────────────────

def fetch_tvmaze_characters(show_title: str, verbose: bool = False) -> List[str]:
    """
    TVmaze'den bir dizi icin karakter listesini ceker.
    Lazy-load: ilk istekte API'dan al, sonra disk cache'den don.
    TTL: 30 gun per-show.
    Ornek: fetch_tvmaze_characters("Breaking Bad") -> ["Walter White", "Jesse Pinkman", ...]
    """
    os.makedirs(TVMAZE_CACHE_DIR, exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9]', '_', show_title.lower())[:60]
    cache_path = os.path.join(TVMAZE_CACHE_DIR, f"{safe_name}.json")

    # Cache gecerliyse diskten don
    if os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            age_days = (time.time() - mtime) / 86400
            if age_days < TVMAZE_CHAR_TTL_DAYS:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('characters', [])
        except Exception:
            pass

    TVMAZE_HDR = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}
    try:
        # 1. Diziyi ara
        search_url = f"https://api.tvmaze.com/search/shows?q={requests.utils.quote(show_title)}"
        resp = requests.get(search_url, timeout=15, headers=TVMAZE_HDR)
        if resp.status_code != 200 or not resp.json():
            return []
        show_id = resp.json()[0]['show']['id']

        # 2. Cast listesini cek
        cast_url = f"https://api.tvmaze.com/shows/{show_id}/cast"
        resp2 = requests.get(cast_url, timeout=15, headers=TVMAZE_HDR)
        if resp2.status_code != 200:
            return []

        chars = []
        for entry in resp2.json():
            char_name = entry.get('character', {}).get('name', '').strip()
            if char_name and char_name not in chars:
                chars.append(char_name)

        # 3. Diske kaydet
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'show': show_title, 'show_id': show_id,
                       'characters': chars, 'fetched': datetime.datetime.now().isoformat()}, f,
                      ensure_ascii=False)
        if verbose:
            print(f"[TVmaze] '{show_title}': {len(chars)} karakter")
        return chars

    except Exception as e:
        if verbose:
            print(f"[TVmaze] Hata ({show_title}): {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3h: FRANCHISE-SPECIFIC API (PotterDB, SWAPI)
# PotterDB: Harry Potter — ucretsiz, auth yok
# SWAPI: Star Wars — ucretsiz, auth yok
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_lotr(api_key: str, verbose: bool = False) -> dict:
    """The One API — Lord of the Rings / Hobbit karakterleri + konumlar."""
    result = {}
    BASE = "https://the-one-api.dev/v2"
    HDR  = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    # Karakterler
    try:
        r = requests.get(f"{BASE}/character?limit=500", headers=HDR, timeout=15)
        if r.status_code == 200:
            docs = r.json().get("docs", [])
            chars = [d["name"] for d in docs
                     if d.get("name") and d["name"] != "MINOR_CHARACTER"
                     and len(d["name"]) <= 40 and ' ' in d["name"]]
            result["characters"] = chars[:200]
            if verbose:
                print(f"[LotR] Karakterler: {len(chars)}")
    except Exception as e:
        if verbose:
            print(f"[LotR] Karakter hatasi: {e}")

    # Konumlar
    try:
        r = requests.get(f"{BASE}/location?limit=200", headers=HDR, timeout=15)
        if r.status_code == 200:
            docs = r.json().get("docs", [])
            locs = [d["name"] for d in docs if d.get("name") and len(d["name"]) <= 40]
            result["locations"] = locs[:100]
            if verbose:
                print(f"[LotR] Konumlar: {len(locs)}")
    except Exception as e:
        if verbose:
            print(f"[LotR] Konum hatasi: {e}")

    return result


def _fetch_marvel(api_key: str, verbose: bool = False) -> dict:
    """Marvel API — MCU/616 evren karakterleri."""
    result = {}
    import hashlib, time as _t
    BASE = "https://gateway.marvel.com/v1/public"

    chars = []
    try:
        offset, limit = 0, 100
        while offset < 300:  # max 300 karakter
            params = {"apikey": api_key, "limit": limit, "offset": offset}
            r = requests.get(f"{BASE}/characters", params=params, timeout=15)
            if r.status_code != 200:
                break
            data = r.json().get("data", {})
            results = data.get("results", [])
            if not results:
                break
            for ch in results:
                name = ch.get("name", "").strip()
                if name and len(name) <= 40:
                    chars.append(name)
            if len(results) < limit:
                break
            offset += limit
            time.sleep(0.3)

        result["characters"] = chars
        if verbose:
            print(f"[Marvel] Karakterler: {len(chars)}")
    except Exception as e:
        if verbose:
            print(f"[Marvel] Karakter hatasi: {e}")

    return result


def fetch_franchise_terms(title: str, verbose: bool = False) -> dict:
    """
    Franchise'a ozgu API'den karakter, lokasyon, esya verilerini ceker.
    Dispatch: basliga gore dogru API'ye yonlendirir.
    Returns: {"characters": [...], "locations": [...], "items": [...], "skills": [...]}
    Sonuclar franchise_cache/ dizinine TTL=30g ile cache'lenir.
    """
    os.makedirs(FRANCHISE_CACHE_DIR, exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9]', '_', title.lower())[:60]
    cache_path = os.path.join(FRANCHISE_CACHE_DIR, f"{safe_name}.json")

    # Cache gecerliyse diskten don
    if os.path.exists(cache_path):
        try:
            age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
            if age_days < FRANCHISE_TTL_DAYS:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f).get('terms', {})
        except Exception:
            pass

    title_low = title.lower()
    terms = {}

    # ── Harry Potter → PotterDB ─────────────────────────────────────────────
    hp_keywords = {'harry potter', 'potter', 'hogwarts', 'fantastic beasts',
                   'wizarding world', 'grindelwald', 'dumbledore'}
    sw_keywords = {'star wars', 'jedi', 'sith', 'mandalorian', 'clone wars',
                   'rebels', 'ahsoka', 'obi-wan', 'boba fett'}
    lotr_keywords = {'lord of the rings', 'hobbit', 'middle earth', 'lotr',
                     'fellowship', 'two towers', 'return of the king', 'silmarillion',
                     'rings of power'}
    marvel_keywords = {'marvel', 'avengers', 'spider-man', 'iron man', 'thor',
                       'captain america', 'black widow', 'guardians of the galaxy',
                       'doctor strange', 'x-men', 'fantastic four', 'deadpool'}

    if any(kw in title_low for kw in hp_keywords):
        terms = _fetch_potterdb(verbose=verbose)
    elif any(kw in title_low for kw in sw_keywords):
        terms = _fetch_swapi(verbose=verbose)
    elif any(kw in title_low for kw in lotr_keywords):
        # The One API — key varsa kullan
        _lotr_key_path = os.path.join(_DIR, 'lotr_api_key.txt')
        _lotr_key = ''
        if os.path.exists(_lotr_key_path):
            try:
                with open(_lotr_key_path, 'r', encoding='utf-8') as _f:
                    _lotr_key = _f.read().strip()
            except Exception:
                pass
        if _lotr_key:
            terms = _fetch_lotr(api_key=_lotr_key, verbose=verbose)
        elif verbose:
            print("[Franchise] LotR API key bulunamadı — Veri Kaynakları > The One API kısmından girin.")
    elif any(kw in title_low for kw in marvel_keywords):
        # Marvel API — key varsa kullan
        _marvel_key_path = os.path.join(_DIR, 'marvel_api_key.txt')
        _marvel_key = ''
        if os.path.exists(_marvel_key_path):
            try:
                with open(_marvel_key_path, 'r', encoding='utf-8') as _f:
                    _marvel_key = _f.read().strip()
            except Exception:
                pass
        if _marvel_key:
            terms = _fetch_marvel(api_key=_marvel_key, verbose=verbose)
        elif verbose:
            print("[Franchise] Marvel API key bulunamadı — Veri Kaynakları > Marvel API kısmından girin.")

    # Sonucu cachele
    if terms:
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({'title': title, 'terms': terms,
                           'fetched': datetime.datetime.now().isoformat()}, f, ensure_ascii=False)
        except Exception:
            pass

    return terms


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3i: TMDB CAST API — Film + Dizi Oyuncu/Karakter Listesi
# API key: tmdb_api_key.txt dosyasından okunur (https://www.themoviedb.org/settings/api)
# Auth yok (v3 read-only key yeterli), ücretsiz kayıt gerektirir.
# TTL: 30 gün, tmdb_cast_cache/{title}_{type}.json
# ─────────────────────────────────────────────────────────────────────────────

def _tmdb_api_key() -> str:
    """tmdb_api_key.txt dosyasından API key'i okur. Yoksa boş string döner."""
    try:
        if os.path.exists(TMDB_CAST_API_KEY_PATH):
            key = open(TMDB_CAST_API_KEY_PATH, 'r', encoding='utf-8').read().strip()
            return key if len(key) > 10 else ''
    except Exception:
        pass
    return ''


def fetch_tmdb_cast(
    title: str,
    media_type: str = 'movie',   # 'movie' | 'tv' | 'auto'
    season_num: int = None,
    verbose: bool = False,
) -> List[str]:
    """
    TMDB API'den film veya dizi cast listesini çeker.

    Dönüş: karakter isimlerinin listesi (oyuncu değil), boş liste = bulunamadı.

    API key gerektiriyor:
      1. https://www.themoviedb.org/signup adresinden ücretsiz hesap aş
      2. https://www.themoviedb.org/settings/api adresinden v3 key al
      3. Key'i buraya kaydet: {TMDB_CAST_API_KEY_PATH}

    Cache: tmdb_cast_cache/{title}_{type}[_sN].json  |  TTL: 30 gün
    Sezon: media_type='tv' ve season_num verilirse sezona özel cast çekilir.
    """
    api_key = _tmdb_api_key()
    if not api_key:
        if verbose:
            print("[TMDB] API key bulunamadı — tmdb_api_key.txt dosyasına ekleyin.")
        return []

    os.makedirs(TMDB_CAST_CACHE_DIR, exist_ok=True)
    safe = re.sub(r'[^a-z0-9]', '_', title.lower().strip())[:50]
    type_tag = media_type if media_type != 'auto' else 'auto'
    season_tag = f"_s{season_num}" if season_num else ''
    cache_path = os.path.join(TMDB_CAST_CACHE_DIR, f"{safe}_{type_tag}{season_tag}.json")

    # ── Disk cache ───────────────────────────────────────────────────────────
    if os.path.exists(cache_path):
        try:
            age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
            if age_days < TMDB_CAST_TTL_DAYS:
                cached = json.load(open(cache_path, 'r', encoding='utf-8'))
                chars = cached.get('characters', [])
                if verbose:
                    print(f"[TMDB] Disk cache: '{title}' → {len(chars)} karakter")
                return chars
        except Exception:
            pass

    HDR = {
        'User-Agent': 'AnimeSubtitleTranslator/3.0',
        'Accept': 'application/json',
    }

    def _get(url: str, params: dict) -> Optional[dict]:
        try:
            r = requests.get(url, params={**params, 'api_key': api_key},
                             timeout=15, headers=HDR)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    # ── Media type belirleme ───────────────────────────────────────────────────────
    if media_type == 'auto':
        # Önce movie dene, yoksa tv
        search_types = ['movie', 'tv']
    elif media_type in ('movie', 'film'):
        search_types = ['movie']
    else:
        # tv, series, anime vs
        search_types = ['tv']

    tmdb_id   = None
    found_type = None
    for stype in search_types:
        data = _get(f"{TMDB_API_BASE}/search/{stype}",
                    {'query': title, 'language': 'en-US', 'page': 1})
        if not data:
            continue
        results = data.get('results', [])
        if not results:
            continue

        # En iyi eşleşme: tam başlık öncelikli
        title_low = title.lower()
        best = None
        for r in results:
            r_title = (r.get('title') or r.get('name') or '').lower()
            if r_title == title_low:
                best = r; break
        if not best:
            best = results[0]  # ilk sonucu kullan

        tmdb_id    = best['id']
        found_type = stype
        break

    if not tmdb_id:
        if verbose:
            print(f"[TMDB] '{title}' bulunamadı.")
        return []

    # ── Credits çek ─────────────────────────────────────────────────────────────
    if found_type == 'tv' and season_num:
        # Sezona özel credits (daha temiz)
        credits = _get(
            f"{TMDB_API_BASE}/tv/{tmdb_id}/season/{season_num}/credits",
            {'language': 'en-US'}
        )
    elif found_type == 'tv':
        credits = _get(
            f"{TMDB_API_BASE}/tv/{tmdb_id}/credits",
            {'language': 'en-US'}
        )
    else:
        credits = _get(
            f"{TMDB_API_BASE}/movie/{tmdb_id}/credits",
            {'language': 'en-US'}
        )

    if not credits:
        return []

    # Cast listesini dönüştür: karakter ismi öncelikli, oyuncu adı fallback
    chars = []
    seen  = set()
    for member in credits.get('cast', []):
        char_name  = (member.get('character') or '').strip()
        actor_name = (member.get('name')      or '').strip()

        # Karakter adı filtresi: "Self", "Narrator", "(voice)" gibi generic olanları atla
        skip_kw = ('self', 'narrator', 'host', 'uncredited', 'cameo',
                   '(voice)', 'archive footage', '(young)', 'young ')
        if any(kw in char_name.lower() for kw in skip_kw):
            char_name = ''

        name = char_name if char_name else actor_name
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        chars.append(name)

    # Disk cache'e yaz
    if chars:
        try:
            json.dump(
                {'title': title, 'tmdb_id': tmdb_id, 'type': found_type,
                 'season': season_num, 'characters': chars},
                open(cache_path, 'w', encoding='utf-8'),
                ensure_ascii=False,
            )
        except Exception:
            pass
        if verbose:
            print(f"[TMDB] '{title}' ({found_type}) → {len(chars)} karakter (id={tmdb_id})")

    return chars



def _fetch_potterdb(verbose: bool = False) -> dict:
    """PotterDB API — Harry Potter karakterler, buyuler, iksirler."""
    BASE = "https://api.potterdb.com/v1"
    HDR  = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}
    result = {"characters": [], "skills": [], "items": []}

    # Karakterler
    try:
        chars = []
        page = 1
        while page <= 5:  # max 5 sayfa
            r = requests.get(f"{BASE}/characters?page[number]={page}&page[size]=100",
                             timeout=15, headers=HDR)
            if r.status_code != 200:
                break
            data = r.json().get("data", [])
            if not data:
                break
            for item in data:
                    name = item.get("attributes", {}).get("name", "").strip()
                    attrs = item.get("attributes", {})
                    # Filtrele: rakamla baslayanlar, cok uzunlar, aciklamali olanlar
                    if not name or len(name) > 50:
                        continue
                    if name[0].isdigit():
                        continue
                    skip_kw = ('spectator','match','tournament','ceremony',
                               'student','class','member','crowd','mourner',
                               'attendee','unnamed','unknown','various')
                    if any(kw in name.lower() for kw in skip_kw):
                        continue
                    chars.append(name)
            if len(data) < 100:
                break
            page += 1
            time.sleep(0.5)
        # Bilinen onemliler one: en az 2 kelimeli gercek isimler once
        full_names  = [c for c in chars if ' ' in c and len(c) <= 30]
        short_names = [c for c in chars if ' ' not in c and len(c) <= 20]
        result["characters"] = (full_names + short_names)[:200]
        if verbose:
            print(f"[PotterDB] Karakterler: {len(chars)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Karakter hatasi: {e}")

    # Buyuler (skills olarak)
    try:
        spells = []
        r = requests.get(f"{BASE}/spells?page[size]=200", timeout=15, headers=HDR)
        if r.status_code == 200:
            for item in r.json().get("data", []):
                name = item.get("attributes", {}).get("name", "").strip()
                if name:
                    spells.append(name)
        result["skills"] = spells
        if verbose:
            print(f"[PotterDB] Buyuler: {len(spells)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Buyu hatasi: {e}")

    # Iksirler (items olarak)
    try:
        potions = []
        r = requests.get(f"{BASE}/potions?page[size]=200", timeout=15, headers=HDR)
        if r.status_code == 200:
            for item in r.json().get("data", []):
                name = item.get("attributes", {}).get("name", "").strip()
                if name:
                    potions.append(name)
        result["items"] = potions
        if verbose:
            print(f"[PotterDB] Iksirler: {len(potions)}")
    except Exception as e:
        if verbose:
            print(f"[PotterDB] Iksir hatasi: {e}")

    return result


def _fetch_swapi(verbose: bool = False) -> dict:
    """SWAPI — Star Wars karakterler, gezegenler, gemiler, turler."""
    MIRRORS = [
        "https://swapi.info/api",
        "https://swapi.tech/api",
        "https://swapi.dev/api",
    ]
    BASE = None
    for mirror in MIRRORS:
        try:
            r = requests.get(f"{mirror}/people/", timeout=8,
                             headers={"User-Agent": "AnimeSubtitleTranslator/3.0"})
            if r.status_code == 200:
                BASE = mirror
                break
        except Exception:
            continue

    if not BASE:
        if verbose:
            print("[SWAPI] Hicbir mirror erisilebilir degil.")
        return {}

    if verbose:
        print(f"[SWAPI] Mirror: {BASE}")

    HDR  = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}
    result = {"characters": [], "locations": [], "items": [], "terminology": []}

    ENDPOINTS = [
        ("people",    "characters"),
        ("planets",   "locations"),
        ("starships", "items"),
        ("species",   "terminology"),
    ]
    for endpoint, key in ENDPOINTS:
        collected = []
        url = f"{BASE}/{endpoint}/"
        while url and len(collected) < 500:
            try:
                r = requests.get(url, timeout=15, headers=HDR)
                if r.status_code != 200:
                    break
                data = r.json()
                # swapi.info direkt array; swapi.dev/swapi.tech {results:[...]} doner
                if isinstance(data, list):
                    items_list = data
                    url = None
                else:
                    items_list = data.get("results", [])
                    url = data.get("next")
                for item in items_list:
                    name = (item.get("name") or "").strip()
                    if name and name.lower() not in ("unknown", "n/a", ""):
                        collected.append(name)
                time.sleep(0.3)
            except Exception as e:
                if verbose:
                    print(f"[SWAPI] {endpoint} hata: {e}")
                break
        result[key] = collected
        if verbose:
            print(f"[SWAPI] {endpoint}: {len(collected)}")

    return result


# ─────────────────────────────────────────────────────────────────────────────

# BÖLÜM 5: GÜNCELLEME YÖNETİCİSİ
# ─────────────────────────────────────────────────────────────────────────────

def update_databases(force: bool = False, verbose: bool = True, include_movies: bool = False):
    """
    Tüm veritabanlarını TTL'ye göre günceller.
    force=True       → hepsini yeniden indir.
    include_movies   → TMDB Film DB'sini de indir (varsayılan: False).
                       Anime TV dizisi çevirisi için film verisi gereksiz.
                       Sadece film/karma içerik çevirisi için True yap.
    İlk çalıştırmada senkron, sonrakilerde arka planda.
    """
    checks = [
        # (key, ttl_hours, path, label, fn, fn_args)
        ('anidb',          ANIDB_TTL_HOURS,            ANIDB_JSON_PATH,    'AniDB Titles',              _download_anidb,           ()),
        ('manami',         MANAMI_TTL_DAYS * 24,        MANAMI_JSON_PATH,   'manami-project',            _download_manami,          ()),
        # TMDB Film: 850k+ başlık → anime TV modu için GEREKSIZ, opsiyonel
        # include_movies=True ile aktif edilir (film/karma içerik modu)
        *([('tmdb_movies', TMDB_TTL_HOURS, TMDB_MOVIE_PATH, 'TMDB Film', _download_tmdb, ('movie_ids', TMDB_MOVIE_PATH, 'tmdb_movies'))]
          if include_movies else []),
        ('tmdb_tv',        TMDB_TTL_HOURS,              TMDB_TV_PATH,       'TMDB TV/Dizi',              _download_tmdb,            ('tv_series_ids', TMDB_TV_PATH,    'tmdb_tv')),
        ('imdb_basics',    IMDB_TTL_DAYS * 24,          IMDB_BASICS_PATH,   'IMDB Basics',               _download_imdb_basics,     ()),
        ('imdb_akas',      IMDB_TTL_DAYS * 24,          IMDB_AKAS_PATH,     'IMDB Akas (TR+JP)',         _download_imdb_akas,       ()),
        ('wiki_chars',     WIKI_TTL_DAYS * 24,          WIKI_CHARS_PATH,    'Wikidata Karakterler',      _download_wikidata_chars,  ()),
        ('wiki_entities',  WIKI_ENTITIES_TTL * 24,      WIKI_ENTITIES_PATH, 'Wikidata Varliklar',        _download_wikidata_entities, ()),
        # Kelime frekans sözlükleri (content_detector için)
        ('word_freq_en',   WORD_FREQ_TTL_DAYS * 24,     EN_FREQ_PATH,       'EN Frekans Sözlüğü',       _download_word_freqs,      ()),
        ('word_freq_tr',   WORD_FREQ_TTL_DAYS * 24,     TR_FREQ_PATH,       'TR Frekans Sözlüğü',       _download_word_freqs,      ()),
        ('anime_names',    ANIME_NAMES_TTL_DAYS * 24,   ANIME_NAMES_PATH,   'Anime İsim Listesi',        _download_anime_names,     ()),
    ]
    # word_freq_en ve word_freq_tr aynı fonksiyon — sadece bir kez çalışsın
    _ran_word_freqs = False
    any_needed = False
    for key, ttl, path, label, fn, args in checks:
        needed = force or _needs_update(key, ttl)
        if not needed:
            continue
        # EN/TR frekans aynı fonksiyon, ikinci geçişte atla
        if fn is _download_word_freqs:
            if _ran_word_freqs:
                continue
            _ran_word_freqs = True
        any_needed = True
        first_run = not os.path.exists(path)
        if first_run:
            if verbose:
                print(f"[OfflineDB] İlk kurulum: {label} indiriliyor (bekleyin)...")
            fn(*args, verbose=verbose)
            _invalidate_cache()
        else:
            if verbose:
                print(f"[OfflineDB] {label} güncelleniyor (arka planda)...")
            threading.Thread(
                target=lambda f=fn, a=args: [f(*a, verbose=True), _invalidate_cache()],
                daemon=True,
            ).start()

    if not any_needed and verbose:
        print("[OfflineDB] Tüm veritabanları güncel. (10 kaynak)")



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 6: LOOKUP FONKSİYONLARI (Pipeline bütünleşme)
# ─────────────────────────────────────────────────────────────────────────────

def lookup_anime(title: str) -> Optional[dict]:
    """Anime başlığını AniDB + manami'de arar."""
    key = _normalize(title)
    if not key:
        return None
    manami = _load_manami()
    entry  = manami.get(key)
    if entry:
        return _manami_to_meta(entry, title)
    anidb  = _load_anidb()
    entry  = anidb.get(key)
    if entry:
        return _anidb_to_meta(entry, title)
    return None


def lookup_media(title: str, media_type: str = 'unknown') -> Optional[dict]:
    """
    Film/dizi başlığını TMDB offline export'tan arar.
    media_type: 'movie', 'series', 'unknown'
    """
    key = _normalize(title)
    if not key:
        return None

    if media_type in ('movie', 'unknown'):
        entry = _load_tmdb_movies().get(key)
        if entry:
            return {
                'title':               entry.get('title', title),
                'type':                'MOVIE',
                'resolved_media_type': 'movie',
                'episodes':   1,
                'status':     '',
                'genres':     [],
                'characters': [],
                'synopsis':   '',
                'score':      None,
                'year':       None,
                'source':     'OfflineDB/TMDB-Movie',
                'tmdb_id':    entry.get('id'),
                '_offline':   True,
            }

    if media_type in ('series', 'unknown'):
        entry = _load_tmdb_tv().get(key)
        if entry:
            return {
                'title':               entry.get('title', title),
                'type':                'TVSERIES',
                'resolved_media_type': 'series',
                'episodes':   '?',
                'status':     '',
                'genres':     [],
                'characters': [],
                'synopsis':   '',
                'score':      None,
                'year':       None,
                'source':     'OfflineDB/TMDB-TV',
                'tmdb_id':    entry.get('id'),
                '_offline':   True,
            }

    # IMDB Basics fallback (TMDB'de bulunmayan eski/nadir içerikler)
    imdb_entry = _load_imdb_basics().get(key)
    if imdb_entry:
        genres_raw  = imdb_entry.get('genres', '')
        imdb_type   = imdb_entry.get('type', '').lower()  # titleType: tvSeries, movie, short…

        # IMDB titleType → standart tip
        _TYPE_MAP = {
            'tvseries':       'TVSERIES',
            'tvminiseries':   'TVSERIES',
            'tvspecial':      'TVSERIES',
            'tvepisode':      'TVSERIES',
            'tvmovie':        'MOVIE',
            'movie':          'MOVIE',
            'short':          'MOVIE',
            'videogame':      'OTHER',
            'video':          'MOVIE',
        }
        norm_type = _TYPE_MAP.get(imdb_type, imdb_type.upper())

        # media_type parametresinden gelen bağlam türüne öncelik ver (kullanıcı biliyor)
        if media_type in ('series', 'tv', 'anime'):
            norm_type = 'TVSERIES' if media_type != 'anime' else 'ANIME'
        elif media_type == 'movie':
            norm_type = 'MOVIE'

        return {
            'title':               imdb_entry.get('title', title),
            'type':                norm_type,
            'resolved_media_type': 'anime'  if norm_type == 'ANIME'
                                   else 'series' if norm_type == 'TVSERIES'
                                   else 'movie'  if norm_type == 'MOVIE'
                                   else 'unknown',
            'episodes':   '?',
            'status':     '',
            'genres':     [g.strip() for g in genres_raw.split(',') if g.strip()] if genres_raw else [],
            'characters': [],
            'synopsis':   '',
            'score':      None,
            'year':       imdb_entry.get('year', ''),
            'source':     'OfflineDB/IMDB-Basics',
            'imdb_id':    imdb_entry.get('id'),
            '_offline':   True,
        }

    return None


def lookup_by_turkish_title(tr_title: str) -> Optional[dict]:
    """
    Türkçe başlıktan orijinal (genellikle İngilizce) başlığı bulur.
    Örnek: 'Zor Ölüm' -> {imdb_id: 'tt0087182', title: 'Zor Ölüm', region: 'TR'}
    """
    key = _normalize(tr_title)
    if not key:
        return None
    return _load_imdb_akas().get(key)


def get_anime_characters() -> List[str]:
    """
    Tüm Wikidata anime karakterlerinin ad listesini döner.
    fandom_glossary.py'deki 'asla çevirme' koruması için kullanılır.
    """
    return _load_wiki_chars()


def get_synonyms(title: str) -> List[str]:
    """
    Bir başlığa ait TÜM alternatif isimler.
    fandom_glossary._make_slug_candidates() için kullanılır.
    """
    key = _normalize(title)
    if not key:
        return []

    syns: List[str] = []

    manami = _load_manami()
    if key in manami:
        e = manami[key]
        syns = [e.get('title', '')] + (e.get('synonyms') or [])

    if not syns:
        anidb = _load_anidb()
        if key in anidb:
            e = anidb[key]
            syns = [e.get('title', '')] + (e.get('synonyms') or [])

    # Tekrarları kaldır, boşları at
    seen = set()
    result = []
    for s in syns:
        sn = s.strip()
        if sn and sn.lower() not in seen:
            seen.add(sn.lower())
            result.append(sn)
    return result


def get_all_titles_for_slug(title: str) -> List[str]:
    """
    Fandom slug tespiti için başlığın TÜM isim varyantlarını döner
    (İngilizce, Romaji, Japonca, kısa isimler dahil).
    """
    syns = get_synonyms(title)
    if not syns:
        syns = [title]

    # Japonca + özel karakterleri filtrele (slug'da kullanılamaz)
    latin_only = []
    for s in syns:
        if re.search(r'[\u3000-\u9fff\uff00-\uffef]', s):
            continue  # Japonca/Çince karakterli → atla
        latin_only.append(s)

    return latin_only or syns


def get_status_info() -> dict:
    """Dashboard için mevcut durum bilgisi."""
    meta = _load_meta()
    anidb_meta  = meta.get('anidb', {})
    manami_meta = meta.get('manami', {})

    def _age_str(updated_at: str) -> str:
        if not updated_at:
            return 'hiç indirilmedi'
        try:
            dt  = datetime.datetime.fromisoformat(updated_at)
            hrs = (datetime.datetime.now() - dt).total_seconds() / 3600
            if hrs < 1:
                return f'{int(hrs*60)} dk önce'
            elif hrs < 24:
                return f'{hrs:.1f} saat önce'
            else:
                return f'{hrs/24:.1f} gün önce'
        except Exception:
            return '?'

    anidb_count   = len(_load_anidb())        if os.path.exists(ANIDB_JSON_PATH)   else 0
    manami_count  = len(_load_manami())       if os.path.exists(MANAMI_JSON_PATH)  else 0
    movies_count  = len(_load_tmdb_movies())  if os.path.exists(TMDB_MOVIE_PATH)   else 0
    tv_count      = len(_load_tmdb_tv())      if os.path.exists(TMDB_TV_PATH)      else 0
    basics_count  = len(_load_imdb_basics())  if os.path.exists(IMDB_BASICS_PATH)  else 0
    akas_count    = len(_load_imdb_akas())    if os.path.exists(IMDB_AKAS_PATH)    else 0
    wiki_count         = len(_load_wiki_chars())    if os.path.exists(WIKI_CHARS_PATH)    else 0
    wiki_entities_count = len(_load_wiki_entities()) if os.path.exists(WIKI_ENTITIES_PATH) else 0

    # EN/TR frekans sözlükleri
    def _count_pickle(path):
        if not os.path.exists(path): return 0
        try:
            import pickle
            with open(path, 'rb') as f:
                return len(pickle.load(f))
        except Exception:
            return 0

    def _count_gz(path):
        if not os.path.exists(path): return 0
        try:
            import gzip as _gz
            with _gz.open(path, 'rt', encoding='utf-8') as f:
                return sum(1 for l in f if l.strip() and not l.startswith('#'))
        except Exception:
            return 0

    en_freq_count    = _count_pickle(EN_FREQ_PATH)
    tr_freq_count    = _count_pickle(TR_FREQ_PATH)
    anime_name_count = _count_gz(ANIME_NAMES_PATH)

    tmdb_movie_meta  = meta.get('tmdb_movies', {})
    tmdb_tv_meta     = meta.get('tmdb_tv', {})
    imdb_basics_meta = meta.get('imdb_basics', {})
    imdb_akas_meta   = meta.get('imdb_akas', {})
    wiki_meta        = meta.get('wiki_chars', {})
    wiki_ent_meta    = meta.get('wiki_entities', {})
    wfen_meta        = meta.get('word_freq_en', {})
    wftr_meta        = meta.get('word_freq_tr', {})
    anames_meta      = meta.get('anime_names', {})

    return {
        'anidb': {
            'exists':       os.path.exists(ANIDB_JSON_PATH),
            'entries':      anidb_count,
            'age_str':      _age_str(anidb_meta.get('updated_at', '')),
            'needs_update': _needs_update('anidb', ANIDB_TTL_HOURS),
        },
        'manami': {
            'exists':       os.path.exists(MANAMI_JSON_PATH),
            'entries':      manami_count,
            'age_str':      _age_str(manami_meta.get('updated_at', '')),
            'needs_update': _needs_update('manami', MANAMI_TTL_DAYS * 24),
        },
        'tmdb_movies': {
            'exists':       os.path.exists(TMDB_MOVIE_PATH),
            'entries':      movies_count,
            'age_str':      _age_str(tmdb_movie_meta.get('updated_at', '')),
            'needs_update': _needs_update('tmdb_movies', TMDB_TTL_HOURS),
        },
        'tmdb_tv': {
            'exists':       os.path.exists(TMDB_TV_PATH),
            'entries':      tv_count,
            'age_str':      _age_str(tmdb_tv_meta.get('updated_at', '')),
            'needs_update': _needs_update('tmdb_tv', TMDB_TTL_HOURS),
        },
        'imdb_basics': {
            'exists':       os.path.exists(IMDB_BASICS_PATH),
            'entries':      basics_count,
            'age_str':      _age_str(imdb_basics_meta.get('updated_at', '')),
            'needs_update': _needs_update('imdb_basics', IMDB_TTL_DAYS * 24),
        },
        'imdb_akas': {
            'exists':       os.path.exists(IMDB_AKAS_PATH),
            'entries':      akas_count,
            'age_str':      _age_str(imdb_akas_meta.get('updated_at', '')),
            'needs_update': _needs_update('imdb_akas', IMDB_TTL_DAYS * 24),
        },
        'wiki_chars': {
            'exists':       os.path.exists(WIKI_CHARS_PATH),
            'entries':      wiki_count,
            'age_str':      _age_str(wiki_meta.get('updated_at', '')),
            'needs_update': _needs_update('wiki_chars', WIKI_TTL_DAYS * 24),
        },
        'wiki_entities': {
            'exists':       os.path.exists(WIKI_ENTITIES_PATH),
            'entries':      wiki_entities_count,
            'age_str':      _age_str(wiki_ent_meta.get('updated_at', '')),
            'needs_update': _needs_update('wiki_entities', WIKI_ENTITIES_TTL * 24),
        },
        'word_freq_en': {
            'exists':       os.path.exists(EN_FREQ_PATH),
            'entries':      en_freq_count,
            'age_str':      _age_str(wfen_meta.get('updated_at', '')),
            'needs_update': _needs_update('word_freq_en', WORD_FREQ_TTL_DAYS * 24),
        },
        'word_freq_tr': {
            'exists':       os.path.exists(TR_FREQ_PATH),
            'entries':      tr_freq_count,
            'age_str':      _age_str(wftr_meta.get('updated_at', '')),
            'needs_update': _needs_update('word_freq_tr', WORD_FREQ_TTL_DAYS * 24),
        },
        'anime_names': {
            'exists':       os.path.exists(ANIME_NAMES_PATH),
            'entries':      anime_name_count,
            'age_str':      _age_str(anames_meta.get('updated_at', '')),
            'needs_update': _needs_update('anime_names', ANIME_NAMES_TTL_DAYS * 24),
        },
    }



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 7: FORMAT DÖNÜŞTÜRÜCÜLER
# ─────────────────────────────────────────────────────────────────────────────

def _manami_to_meta(entry: dict, original_query: str) -> dict:
    """manami entry → media_identifier metadata formatı."""
    title  = entry.get('title') or original_query
    syns   = entry.get('synonyms') or []
    tags   = entry.get('tags') or []
    score  = entry.get('score')
    year   = entry.get('year')

    # MAL ID'yi çıkar (URL'den)
    mal_id = None
    mal_url = entry.get('mal_url', '')
    if mal_url:
        m = re.search(r'/anime/(\d+)', mal_url)
        if m:
            mal_id = int(m.group(1))

    # manami type → resolved_media_type
    _manami_type = entry.get('type', 'TV').upper()
    _resolved = (
        'movie' if _manami_type in ('MOVIE',)
        else 'anime'  # TV, OVA, ONA, SPECIAL, MUSIC hepsi anime
    )
    return {
        'title':               title,
        'title_jp':            '',
        'type':                _manami_type,
        'resolved_media_type': _resolved,
        'episodes':   '?',
        'status':     entry.get('status', ''),
        'genres':     tags[:6],
        'characters': [],
        'synopsis':   '',
        'score':      score,
        'year':       year,
        'source':     'OfflineDB/manami',
        'mal_id':     mal_id,
        'synonyms':   syns,
        '_offline':   True,
    }


def _anidb_to_meta(entry: dict, original_query: str) -> dict:
    """AniDB entry → media_identifier metadata formatı."""
    title = entry.get('title') or original_query
    syns  = entry.get('synonyms') or []
    return {
        'title':               title,
        'title_jp':            (entry.get('langs') or {}).get('ja', [None])[0] or '',
        'type':                'TV',
        'resolved_media_type': 'anime',   # AniDB = her zaman anime
        'episodes':   '?',
        'status':     '',
        'genres':     [],
        'characters': [],
        'synopsis':   '',
        'score':      None,
        'year':       None,
        'source':     'OfflineDB/AniDB',
        'aid':        entry.get('aid'),
        'synonyms':   syns,
        '_offline':   True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 8: CLI ARAÇ (python offline_db_manager.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Offline Anime DB Yöneticisi'
    )
    parser.add_argument('--update', action='store_true', help='Güncelleme kontrolü yap')
    parser.add_argument('--force',  action='store_true', help='Zorla güncelle')
    parser.add_argument('--status', action='store_true', help='Durum göster')
    parser.add_argument('--lookup', metavar='TITLE', help='Başlık ara')
    parser.add_argument('--synonyms', metavar='TITLE', help='Sinonimler')
    args = parser.parse_args()

    if args.status or not any(vars(args).values()):
        s = get_status_info()
        print("\n=== OfflineDB Durum ===")
        print(f"AniDB Titles:    {'✓' if s['anidb']['exists'] else '✗'} "
              f"{s['anidb']['entries']:,} giriş | "
              f"{s['anidb']['age_str']} | "
              f"{'GÜNCELLEME GEREKLİ' if s['anidb']['needs_update'] else 'güncel'}")
        print(f"manami-project:  {'✓' if s['manami']['exists'] else '✗'} "
              f"{s['manami']['entries']:,} giriş | "
              f"{s['manami']['age_str']} | "
              f"{'GÜNCELLEME GEREKLİ' if s['manami']['needs_update'] else 'güncel'}")

    if args.update or args.force:
        update_databases(force=args.force, verbose=True)

    if args.lookup:
        result = lookup_anime(args.lookup)
        if result:
            print(f"\n[{args.lookup}] → {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"\n[{args.lookup}] → bulunamadı")

    if args.synonyms:
        syns = get_synonyms(args.synonyms)
        print(f"\n[{args.synonyms}] sinonimler: {syns}")
