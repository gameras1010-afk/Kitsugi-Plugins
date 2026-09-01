"""
offline_db/franchise.py
=======================
Franchise özel veri: LOTR, Marvel, PotterDB, SWAPI.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

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



