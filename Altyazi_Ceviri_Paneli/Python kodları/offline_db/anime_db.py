"""
offline_db/anime_db.py
======================
AniDB XML + manami-project indirme ve yükleme.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

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

