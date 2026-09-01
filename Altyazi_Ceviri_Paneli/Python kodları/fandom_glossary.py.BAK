# fandom_glossary.py
# ─────────────────────────────────────────────────────────────────────────────
# Anime/dizi seri sözlüğü oluşturucu — Fandom Wiki MediaWiki API kullanır.
#
# Çalışma mantığı:
#   1. Anime adı verilir  ("Sword Art Online")
#   2. Fandom wiki subdomaini bulunur  (swordartonline.fandom.com)
#   3. MediaWiki API ile kategoriler sorgulanır:
#        Characters, Skills, Locations, Terminology, Weapons…
#   4. Terme listesi series_glossary.json'a kaydedilir
#   5. Translator prompt'una "bu terimleri ASLA çevirme" bloğu eklenir
#
# Neden bu API?
#   · Ücretsiz – API key gerekmez
#   · Tutarlı  – MediaWiki onlarca yıldır değişmedi
#   · Güncel   – Community tarafından sürekli güncelleniyor
#   · Kapsamlı – Her popüler anime'nin Fandom wikisi var
# ─────────────────────────────────────────────────────────────────────────────

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

@dataclass
class Candidate:
    slug: str                    # fandom subdomain (thecampione)
    lang_path: str = ""          # "" (root) veya "es", "ja" ...
    base_score: float = 0.0
    source: str = ""             # wikidata | unified-search | ai
    hub: str = ""                # unified-search 'hub' alanı
    page_count: int = 0
    wiki_name: str = ""
    bonuses: dict = field(default_factory=dict)

    @property
    def api_base(self) -> str:
        root = f"https://{self.slug}.fandom.com"
        return f"{root}/{self.lang_path}" if self.lang_path else root

# Offline DB — güvenli import
try:
    import offline_db_manager as _offdb
    _OFFLINE_DB_OK = True
except ImportError:
    _OFFLINE_DB_OK = False

# ── Sabitler ─────────────────────────────────────────────────────────────────
# Glossary dosyası: her zaman fandom_glossary.py ile aynı dizinde (Python kodları/) kalır.
# os.getcwd() KULLANILMAZ — script farklı klasörden (Sadece Çeviri/) çalışabilir.
def _glossary_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "series_glossary.json")

REQUEST_TIMEOUT  = 4     # saniye (düşürüldü: 8→4, paralel isteklerde yeterli)
MAX_TERMS_PER_CAT = 200  # kategori başına maks. terim
MAX_PROMPT_TERMS  = 80   # prompt'a enjekte edilecek maks. terim

# ── Cache TTL (Time-To-Live) ──────────────────────────────────────────────────────────────────────
CACHE_TTL_DAYS     = 30  # Gerecek terimler 30 gunde bir yenilenir
NOT_FOUND_TTL_DAYS = 1   # "bulunamadi" kaydi 1 gun sonra tekrar denenir

# ── Oturum içi bellek cache (aynı session'da disk+HTTP tekrarı önler) ──────────────────────
# Her worker/process'e ait; multiprocessing'de her process kendi cache'ini taşır.
_session_cache: Dict[str, Optional[Dict]] = {}
_CANONICAL_TITLE_CACHE: Dict[str, str] = {}

def _load_canonical_titles():
    global _CANONICAL_TITLE_CACHE
    try:
        cache = _load_cache()
        _CANONICAL_TITLE_CACHE = cache.get("__canonical_titles__", {})
    except Exception:
        _CANONICAL_TITLE_CACHE = {}

def _save_canonical_title(query: str, canon: str):
    global _CANONICAL_TITLE_CACHE
    query_key = query.lower().strip()
    _CANONICAL_TITLE_CACHE[query_key] = canon
    try:
        cache = _load_cache()
        if "__canonical_titles__" not in cache:
            cache["__canonical_titles__"] = {}
        cache["__canonical_titles__"][query_key] = canon
        _save_cache(cache)
    except Exception:
        pass

def _get_canonical_anime_title(query: str, media_type: str = 'auto', verbose: bool = True) -> str:
    if media_type in ('series', 'movie'):
        return query

    query_clean = query.strip()
    query_key = query_clean.lower()

    global _CANONICAL_TITLE_CACHE
    if not _CANONICAL_TITLE_CACHE:
        _load_canonical_titles()
    if query_key in _CANONICAL_TITLE_CACHE:
        return _CANONICAL_TITLE_CACHE[query_key]

    details = resolve_media_details(query_clean, media_type, verbose)
    canon = details['titles'][0] if details['titles'] else query_clean
    
    # Keyword overlap check to avoid false positives
    _STOP = {'the','a','an','is','of','in','to','with','and','or','for',
             'by','at','on','no','na','wa','ga','wo','ni','de','mo','ka'}
    _q_words = {w for w in re.sub(r'[^a-z0-9 ]', '', query_clean.lower()).split() if w not in _STOP and len(w) >= 3}
    _entry_words = {w for w in re.sub(r'[^a-z0-9 ]', '', canon.lower()).split() if w not in _STOP and len(w) >= 3}

    has_overlap = bool(_q_words & _entry_words) if (_q_words and _entry_words) else True
    if not has_overlap:
        for qw in _q_words:
            for ew in _entry_words:
                if qw.startswith(ew) or ew.startswith(qw):
                    has_overlap = True
                    break
            if has_overlap:
                break

    if not has_overlap:
        if verbose:
            print(f"[Glossary] AniList result '{canon}' rejected for '{query_clean}' due to no keyword overlap")
        return query_clean

    if verbose:
        print(f"[Glossary] AniList canonical title resolved: '{query_clean}' -> '{canon}'")
    _save_canonical_title(query_clean, canon)
    return canon


# ── Blacklist (Kara Liste) Sistemi ───────────────────────────────────────────
# Geçersiz veya bulunamayan wiki adreslerini geçici olarak saklar, gereksiz HTTP isteklerini önler.
def _blacklist_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "fandom_blacklist.json")

BLACKLIST_TTL_DAYS = 7
_blacklist_lock = threading.Lock()

def _load_blacklist() -> dict:
    path = _blacklist_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_blacklist(data: dict) -> None:
    path = _blacklist_path()
    import tempfile
    _tmp_path = None
    try:
        dir_name = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.tmp',
            dir=dir_name, delete=False
        ) as _tmp:
            json.dump(data, _tmp, ensure_ascii=False, indent=2)
            _tmp_path = _tmp.name
        os.replace(_tmp_path, path)
    except Exception as e:
        print(f"[Glossary] Blacklist yazılamadı: {e}")
        try:
            if _tmp_path and os.path.exists(_tmp_path):
                os.unlink(_tmp_path)
        except Exception:
            pass

def _is_slug_blacklisted(slug: str) -> bool:
    if not slug:
        return True
    slug_norm = slug.lower().strip()
    with _blacklist_lock:
        blacklist = _load_blacklist()
        if slug_norm in blacklist:
            ts_str = blacklist[slug_norm]
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age_days = (datetime.now(timezone.utc) - ts).days
                if age_days < BLACKLIST_TTL_DAYS:
                    return True
                else:
                    # TTL dolmuş, sil
                    del blacklist[slug_norm]
                    _save_blacklist(blacklist)
            except Exception:
                del blacklist[slug_norm]
                _save_blacklist(blacklist)
    return False

def _add_to_blacklist(slug: str) -> None:
    if not slug:
        return
    slug_norm = slug.lower().strip()
    with _blacklist_lock:
        blacklist = _load_blacklist()
        blacklist[slug_norm] = datetime.now(timezone.utc).isoformat()
        _save_blacklist(blacklist)



def _normalize_title(title: str) -> str:
    """
    Cache key için başlığı normalize eder.
    Amacı: Farklı varyantların aynı cache key'e düşmesini sağlamak.

    Dönüşümler:
      [CrappySubs] Oshi no Ko  →  oshi no ko
      Oshi No Ko Season 3      →  oshi no ko
      Oshi no Ko S03E11        →  oshi no ko
      Fuuka.S01                →  fuuka
      Sword Art Online         →  sword art online
    """
    t = title.strip()
    # 1. Fansub / grup prefix kaldır: [CrappySubs], [SubsPlease], {HorribleSubs} vb.
    t = re.sub(r'^[\[\{\(][^\]\}\)]*[\]\}\)]\s*', '', t)
    # 2. Season / Part / bölüm sonu kaldır
    t = re.sub(
        r'[\s._]*(?:Season\s*\d+|S\d{1,2}(?:E\d+)?|Part\s*\d+|'  # Season 3 / S03 / S03E11 / Part 2
        r'\d{1,2}(?:st|nd|rd|th)\s*Season|'                        # 2nd Season
        r'Cour\s*\d+|\d+\.?\s*Sezon).*$',                          # Cour 2 / 2. Sezon
        '', t, flags=re.IGNORECASE
    ).strip()
    # 3. Nokta / alt çizgi / tire → boşluk (Fuuka.S01 için)
    t = re.sub(r'[._-]+', ' ', t)
    # 4. Çoklu boşluk temizle + lowercase
    return ' '.join(t.split()).lower().strip()

# Her wiki'de farklı kategori adları kullanılabilir — hepsini dene
CATEGORY_GROUPS = {
    "characters": [
        "Characters", "Main_Characters", "Major_Characters",
        "Supporting_Characters", "Cast", "Protagonists",
        "Personajes", "Personaje", "Personnages", "キャラクター", "登場人物",
        "Titans", "Titan",
    ],
    "organizations": [
        "Organizations", "Groups", "Factions", "Guilds",
        "Companies", "Schools", "Productions", "Agencies",
        "Teams", "Clans",
        "Organizaciones", "Organización", "Organisations", "组织", "組織", "ギルド", "学校",
    ],
    "skills": [
        "Skills", "Sword_Skills", "Abilities", "Magic", "Techniques",
        "Powers", "Spells", "Arts", "Combat_Techniques",
        "Habilidades", "Habilidad", "Capacidades", "Magia", "Técnicas", "Técnica",
        "スキル", "能力", "魔法", "技",
    ],
    "locations": [
        "Locations", "Places", "Areas", "Worlds", "Realms",
        "Dungeons", "Cities", "Towns",
        "Lugares", "Ubicaciones", "Ubicación", "Lieux", "場所", "位置", "世界",
    ],
    "items": [
        "Items", "Weapons", "Equipment", "Objects", "Artifacts",
        "Tools", "Gear",
        "Objetos", "Objeto", "Armas", "Arma", "Objets", "アイテム", "武器",
    ],
    "terminology": [
        "Terminology", "Terms", "Glossary", "Concepts",
        "Game_Mechanics", "Mechanics",
        "Story_Arcs", "Arcs",
        "Terminología", "Conceptos", "Sagas", "用語", "用語集",
    ],
}

HEADERS = {
    "User-Agent": "KitsugiGlossary/2.0 (fansub tooling; contact: github.com/gameras1010-afk)"
}

# ── K1 — Kimlik Çözümleme ve ID Zenginleştirme ───────────────────────────────
_RESOLVED_MEDIA_DETAILS: Dict[str, dict] = {}

def _norm(s: str) -> str:
    """casefold + aksansız + noktalama/boşluksuz normalize (dedupe & fuzzy anahtarı)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", "", s).casefold()

def _fuzzy(a: str, b: str) -> float:
    from difflib import SequenceMatcher
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

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

def _make_slug_candidates(title: str, media_type: str = 'auto') -> List[str]:
    """
    Medyadan olası Fandom wiki slug'larını üretir.
    Offline DB + medya türüne göre doğru API ile tüm başlık varyantları derlenir.

    media_type:
      'anime'        → Jikan/MAL: EN + romaji + synonyms
      'series'       → TVMaze:    Batı dizisi resmi başlığı
      'movie'        → TMDB:      Film resmi başlığı
      'unknown'/'auto' → Jikan → TVMaze → TMDB sırasıyla dener

    KURAL: Her tür YALNIZCA kendi veritabanını sorgular — veri karışmaz.
    """
    t = title.lower().strip()
    _mt = (media_type or 'auto').lower()
    candidates = []

    def _slug_variants(text: str):
        """Bir başlıktan slug varyantları üret (nospace + hyphen + ilk kelime)."""
        tl = text.lower().strip()
        if not tl:
            return
        nospace = re.sub(r'[^a-z0-9]', '', tl)
        if nospace and len(nospace) >= _MIN_SLUG_LEN:
            candidates.append(nospace)
        hyphen = re.sub(r'[^a-z0-9]+', '-', tl).strip('-')
        if hyphen and hyphen != nospace and len(hyphen) >= _MIN_SLUG_LEN:
            candidates.append(hyphen)
        # İlk anlamlı kelime: "Mikadono-san Shimai..." → "mikadono"
        first_w = re.sub(r'[^a-z0-9]', '', tl.split()[0]) if tl.split() else ''
        if len(first_w) >= _MIN_SLUG_LEN and first_w not in candidates:
            candidates.append(first_w)

    # 1) Ana başlık varyantları
    _slug_variants(t)

    # 2) Özel karakterleri kaldır ama boşlukları koru → ilk kelime(ler)
    words = re.sub(r'[^a-z0-9\s]', '', t).split()
    if words:
        if words[0] not in candidates:
            candidates.append(words[0])
        if len(words) >= 2:
            joined = ''.join(words[:2])
            if joined not in candidates:
                candidates.append(joined)

    # 3) Yaygın ön ek/sonek çıkar (the, a, an, season)
    clean = re.sub(r'\b(the|a|an|season\s*\d+)\b', '', t).strip()
    slug_clean = re.sub(r'[^a-z0-9]', '', clean)
    if slug_clean and slug_clean not in candidates:
        candidates.append(slug_clean)

    # 4) Offline DB'den tüm sinonimler (AniDB + manami — yerel, hızlı)
    if _OFFLINE_DB_OK:
        try:
            syn_titles = _offdb.get_all_titles_for_slug(title)
            for syn in syn_titles:
                _slug_variants(syn)
        except Exception:
            pass

    # 5) Medya türüne göre gerçek-zamanlı API — KURAL: karışma yok!
    #    anime   → Jikan (EN+romaji+synonyms)
    #    series  → TVMaze (resmi Batı dizi başlığı)
    #    movie   → TMDB (film başlığı)
    #    unknown/auto → Jikan önce, yoksa TVMaze, yoksa TMDB
    _api_titles: List[str] = []
    if _mt == 'anime':
        _api_titles = _jikan_get_all_titles(title)
    elif _mt == 'series':
        _api_titles = _tvmaze_get_canonical_title(title)
    elif _mt == 'movie':
        _api_titles = _tmdb_get_canonical_title(title, is_movie=True)
    else:  # unknown / auto
        _api_titles = _jikan_get_all_titles(title)
        if not _api_titles:
            _api_titles = _tvmaze_get_canonical_title(title)
        if not _api_titles:
            _api_titles = _tmdb_get_canonical_title(title, is_movie=False)
        if not _api_titles:
            _api_titles = _tmdb_get_canonical_title(title, is_movie=True)

    for alt in _api_titles:
        # [ALTIN KURAL] MAL external'dan gelen dogrudan Fandom slug'u
        if alt.startswith('__FANDOM_SLUG__:'):
            _direct = alt.split(':', 1)[1].strip()
            if _direct and len(_direct) >= _MIN_SLUG_LEN and _direct not in candidates:
                candidates.insert(0, _direct)  # EN BASA ekle — ilk denenir
            continue
        _slug_variants(alt)

    # Tekrar + boş + ambiguous eleyin
    seen = set()
    result = []
    for s in candidates:
        if s and len(s) >= _MIN_SLUG_LEN and s not in _AMBIGUOUS_SLUGS and s not in seen:
            seen.add(s)
            result.append(s)
    return result


# Yanlış pozitif riski yüksek çok kısa / genel slug'lar
# ("the", "is", "sword", "spice", "plastic", "made" gibi)
_MIN_SLUG_LEN = 5
_AMBIGUOUS_SLUGS = frozenset({
    'the', 'is', 'a', 'an', 'sword', 'spice', 'plastic', 'made',
    'log', 'high', 'love', 'blue', 'black', 'white', 'red', 'new',
    'one', 'two', 'zero', 'infinite', 'absolute', 'strike', 'grand',
    'trinity', 'dark', 'star', 'magic', 'angel', 'demon', 'dragon',
    'fire', 'ice', 'wind', 'earth', 'heaven', 'hell', 'rose', 'blood',
})


_WIKI_API_ENDPOINTS: dict = {}

def _get_fandom_api_url(slug: str) -> Optional[str]:
    if not slug or len(slug) < _MIN_SLUG_LEN or slug in _AMBIGUOUS_SLUGS:
        return None
    slug_lower = slug.lower()
    if slug_lower in _WIKI_API_ENDPOINTS:
        return _WIKI_API_ENDPOINTS[slug_lower]

    if _is_slug_blacklisted(slug):
        return None

    # 1. Kök dizin API kontrolü
    url = f"https://{slug}.fandom.com/api.php"
    try:
        r = requests.get(url + "?action=query&meta=siteinfo&format=json", timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r.status_code == 200 and "query" in r.json():
            _WIKI_API_ENDPOINTS[slug_lower] = url
            return url
    except Exception:
        pass

    # 2. Dil alt klasörleri kontrolü (İngilizce dışındaki wikiler için örn: es/api.php, tr/api.php, ja/api.php)
    for lang in ['tr', 'es', 'ja', 'fr', 'de', 'pl', 'ru', 'it', 'pt', 'zh']:
        lang_url = f"https://{slug}.fandom.com/{lang}/api.php"
        try:
            r = requests.get(lang_url + "?action=query&meta=siteinfo&format=json", timeout=REQUEST_TIMEOUT, headers=HEADERS)
            if r.status_code == 200 and "query" in r.json():
                _WIKI_API_ENDPOINTS[slug_lower] = lang_url
                return lang_url
        except Exception:
            pass

    return None


def _check_wiki(slug: str) -> bool:
    """Verilen slug'ın gerçek bir Fandom wiki'si olup olmadığını kontrol eder."""
    api_url = _get_fandom_api_url(slug)
    if api_url:
        return True
    _add_to_blacklist(slug)
    return False


def _check_wiki_and_get_real_slug(slug: str) -> Optional[str]:
    """
    Slug'ı doğrular ve gerçek/kanonik slug'ı (yönlendirmeleri takip ederek) döndürür.
    Döner: gerçek slug (string) veya None
    """
    if not slug or len(slug) < _MIN_SLUG_LEN or slug in _AMBIGUOUS_SLUGS:
        return None
    if _is_slug_blacklisted(slug):
        return None

    # Doğrudan meta=siteinfo sorgusuyla yönlendirmeyi takip et
    url = f"https://{slug}.fandom.com/api.php?action=query&meta=siteinfo&format=json"
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r.status_code == 200 and "query" in r.json():
            general = r.json().get("query", {}).get("general", {})
            server_url = general.get("server", "") or r.url
            m = re.search(r'https://([^.]+)\.fandom\.com', server_url)
            if m:
                real_slug = m.group(1).lower()
                if real_slug and len(real_slug) >= _MIN_SLUG_LEN:
                    return real_slug
            return slug.lower()
    except Exception:
        pass

    # Eski wikia.com API — taşınan wikiler için gerçek slug'ı bul
    url_wikia = f"https://{slug}.wikia.com/api.php?action=query&meta=siteinfo&format=json"
    try:
        r2 = requests.get(url_wikia, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        if r2.status_code == 200 and "query" in r2.json():
            base = r2.json().get("query", {}).get("general", {}).get("base", "")
            m = re.search(r'https://([^.]+)\.fandom\.com', base)
            if m:
                real_slug = m.group(1).lower()
                if real_slug and len(real_slug) >= _MIN_SLUG_LEN:
                    return real_slug
    except Exception:
        pass

    _add_to_blacklist(slug)
    return None


# ─── AI Destekli Slug Tespiti ─────────────────────────────────────────────────
# ── media_identifier.py ile AYNI key-rotator altyapısı ──────────────────────
# api_keys.txt'deki TÜM key'ler sırayla denenir.
# 402/429 (kota doldu) → sıradaki key'e geç.
# Başka hata → aynı key'de devam (geçici ağ sorunu olabilir).
# Bu, media_identifier._ai_classify_media() ile birebir aynı mantık.

_WIKI_AI_KEY_CURSOR = 0   # Modül geneli cursor (session boyunca ilerler)

def _get_all_api_keys():
    """api_keys.txt'deki tüm geçerli OpenRouter key'lerini döner."""
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_keys.txt')
    if not os.path.exists(key_file):
        return [], None
    try:
        with open(key_file, 'r', encoding='utf-8') as f:
            keys = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        if keys:
            return keys, "https://openrouter.ai/api/v1/chat/completions"
    except Exception:
        pass
    return None


def _verify_wiki_relevance(slug: str, anime_title: str, verbose: bool = True) -> bool:
    """
    Checks if a Fandom subdomain (slug) is actually relevant to the anime_title.
    Queries the wiki's siteinfo, Main Page (with redirect resolution),
    and falls back to search API if direct keywords match is ambiguous.
    """
    if not slug:
        return False

    title = anime_title.lower().strip()
    syns = []
    if _OFFLINE_DB_OK:
        try:
            syns = [s.lower().strip() for s in _offdb.get_all_titles_for_slug(anime_title) if s]
        except Exception:
            pass
    all_titles = list(set([title] + syns))

    url = _get_fandom_api_url(slug)
    if not url:
        return False
    
    try:
        # Fetch siteinfo
        r_si = requests.get(
            url,
            params={
                "action": "query",
                "meta": "siteinfo",
                "siprop": "general",
                "format": "json"
            },
            headers=HEADERS,
            timeout=8
        )
        if r_si.status_code != 200:
            return False
        si_data = r_si.json()
        if "query" not in si_data:
            return False
            
        general = si_data.get("query", {}).get("general", {})
        sitename = general.get("sitename", "").lower()
        base_url = general.get("base", "").lower()

        # Fetch Main Page (with redirects=1)
        r_mp = requests.get(
            url,
            params={
                "action": "query",
                "prop": "revisions",
                "titles": "Main Page",
                "redirects": 1,
                "rvprop": "content",
                "rvslots": "main",
                "format": "json"
            },
            headers=HEADERS,
            timeout=8
        )
        main_page_content = ""
        if r_mp.status_code == 200:
            pages = r_mp.json().get("query", {}).get("pages", {})
            for page_val in pages.values():
                main_page_content = (
                    page_val.get("revisions", [{}])[0]
                    .get("slots", {}).get("main", {})
                    .get("*", "") or ""
                ).lower()

        # Extract keywords
        stopwords = {
            'the', 'is', 'a', 'an', 'of', 'in', 'to', 'with', 'and', 'or', 'for',
            'by', 'at', 'on', 'no', 'na', 'wa', 'ga', 'wo', 'ni', 'de',
            'wiki', 'wikia', 'fandom', 'com', 'series', 'season', 'manga', 'anime'
        }
        
        keywords = set()
        for t in all_titles:
            clean_t = re.sub(r'[^a-z0-9 ]', ' ', t)
            for w in clean_t.split():
                if w not in stopwords and len(w) >= 3:
                    keywords.add(w)

        if not keywords:
            return False

        wiki_text = f"{sitename} {base_url} {main_page_content}"

        # 0. Slug to Title comparison (ignoring punctuation/spaces)
        clean_slug = re.sub(r'[^a-z0-9]', '', slug.lower())
        for t in all_titles:
            clean_t = re.sub(r'[^a-z0-9]', '', t.lower())
            if clean_slug and clean_t and (clean_slug == clean_t or clean_t.startswith(clean_slug) or clean_slug.startswith(clean_t)):
                if verbose:
                    print(f"[Glossary] Relevance match found via exact/sub slug match: '{slug}' <-> '{t}'")
                return True

        # A. Check exact phrase match (ignoring punctuation)
        for t in all_titles:
            clean_phrase = re.sub(r'[^a-z0-9 ]', ' ', t.lower()).strip()
            clean_phrase = ' '.join(clean_phrase.split())
            if clean_phrase and clean_phrase in wiki_text:
                if verbose:
                    print(f"[Glossary] Relevance match found via exact phrase: '{t}'")
                return True

        # B. Check keyword overlap
        matching_keywords = {w for w in keywords if w in wiki_text}
        distinctive_matches = {w for w in matching_keywords if w not in slug}

        if len(matching_keywords) >= 2:
            if verbose:
                print(f"[Glossary] Relevance match found via multiple keywords: {matching_keywords}")
            return True
        if len(keywords) == 1 and list(keywords)[0] in matching_keywords:
            if verbose:
                print(f"[Glossary] Relevance match found via single title keyword: {matching_keywords}")
            return True
        if distinctive_matches:
            if verbose:
                print(f"[Glossary] Relevance match found via distinctive keywords: {distinctive_matches}")
            return True

        # C. Search Fallback: Check if the title actually exists inside the wiki articles
        try:
            r_search = requests.get(
                url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": anime_title,
                    "format": "json"
                },
                headers=HEADERS,
                timeout=8
            )
            if r_search.status_code == 200:
                search_data = r_search.json()
                totalhits = search_data.get("query", {}).get("searchinfo", {}).get("totalhits", 0)
                if totalhits >= 2:
                    if verbose:
                        print(f"[Glossary] Relevance match found via search totalhits={totalhits} for '{anime_title}'")
                    return True
        except Exception:
            pass

        if verbose:
            print(f"[Glossary] Relevance check failed for slug '{slug}' (keywords: {keywords}, matching: {matching_keywords})")
        return False

    except Exception as e:
        if verbose:
            print(f"[Glossary] Error during relevance check for slug '{slug}': {e}")
        return False


def _ai_find_wiki_slug(anime_title: str, verbose: bool = True) -> Optional[str]:
    """
    media_identifier.py ile AYNI key-rotator altyapısıyla AI'ya slug tahmin ettirir.

    - api_keys.txt'deki TÜM key'ler sırayla denenir
    - 402/429 (kota doldu) → sıradaki key'e geç (media_identifier ile aynı)
    - Model: google/gemini-2.5-flash
    - HTTP doğrulaması zorunlu → halüsinasyon kabul edilmez
    """
    global _WIKI_AI_KEY_CURSOR

    keys_list, endpoint = _get_all_api_keys()
    if not keys_list or not endpoint:
        return None

    prompt = (
        "You are an expert Fandom Wiki locator and database.\n"
        f"We need to find the official Fandom wiki subdomain for the media title: '{anime_title}'.\n\n"
        "Follow these steps to find the correct subdomain:\n"
        "1. Recall your knowledge of the official Fandom wiki dedicated to this franchise.\n"
        "2. Identify the exact home page URL of this wiki. (e.g., https://naruto.fandom.com/wiki/Naruto_Wiki)\n"
        "3. Extract the subdomain from this URL (e.g., 'naruto').\n"
        "4. If there is no dedicated wiki, check if it has a shared or major franchise wiki (e.g. a manga/movie that shares a wiki, or dubbing wiki).\n"
        "5. Provide up to 5 possible subdomain candidates in order of confidence, including Romaji name, English name, and any variations.\n"
        "6. If you cannot confidently find or recall any Fandom wiki for this media, return an empty list.\n\n"
        "Return ONLY a JSON object with the following fields (no markdown, no other text):\n"
        "{\n"
        '  "reasoning": "Brief explanation of how you retrieved the wiki from your database",\n'
        '  "candidates": ["subdomain1", "subdomain2", ...]\n'
        "}\n\n"
        "Examples:\n"
        "{\n"
        '  "reasoning": "Naruto has its own official wiki, but could be named naruto or narutopedia.",\n'
        '  "candidates": ["naruto", "narutopedia"]\n'
        "}\n\n"
        "JSON:"
    )

    total = len(keys_list)
    for i in range(total):
        idx = (_WIKI_AI_KEY_CURSOR + i) % total
        api_key = keys_list[idx]
        try:
            resp = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "google/gemini-2.5-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.0,
                },
                timeout=15,
            )

            if resp.status_code in (402, 429):
                # Kota doldu — sıradaki key'e geç
                _WIKI_AI_KEY_CURSOR = (idx + 1) % total
                continue

            if resp.status_code != 200:
                continue  # Geçici hata

            # Başarılı — cursor burada sabit kal
            _WIKI_AI_KEY_CURSOR = idx

            raw = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if "```" in raw:
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

            candidates = []
            try:
                data = json.loads(raw)
                candidates = data.get("candidates", [])
            except Exception:
                # Fallback parser: extract anything that looks like words
                candidates = [c.strip().lower() for c in re.findall(r'"([a-z0-9\-]+)"', raw.lower()) 
                              if c not in ('reasoning', 'candidates', 'unknown')]

            for slug in candidates:
                slug = slug.strip().lower()
                if not slug or slug == 'unknown' or len(slug) < 3:
                    continue

                if verbose:
                    print(f"[Glossary] AI slug onerisi: '{slug}' -- dogrulanıyor...")

                real_slug = _check_wiki_and_get_real_slug(slug)
                if not real_slug:
                    if verbose:
                        print(f"[Glossary] AI slug dogrulanamadi: {slug}.fandom.com mevcut degil")
                    continue

                if _verify_wiki_relevance(real_slug, anime_title, verbose=verbose):
                    if verbose:
                        print(f"[Glossary] AI slug dogrulandi: {real_slug}.fandom.com")
                    return real_slug

            # If all candidates fail validation
            return None

        except Exception:
            continue

    return None



# ─────────────────────────────────────────────────────────────────────────────
# 1b. JIKAN API (MyAnimeList) — Sezon-Spesifik Karakter Listesi
# ─────────────────────────────────────────────────────────────────────────────
# MAL'da her anime sezonu ayrı entry → sezon_title ile arama yaparak
# sadece o sezonda yer alan karakterler çekilir. Kirlenme olmaz.

_JIKAN_BASE      = "https://api.jikan.moe/v4"
_JIKAN_CACHE: Dict[str, Optional[List[str]]] = {}          # Oturum içi bellek
_JIKAN_DISK_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jikan_cache")
_JIKAN_DISK_TTL  = 30   # Disk cache gün süresi


def _jikan_get_characters(
    season_title: str,
    series_title: Optional[str] = None,
    verbose: bool = True,
) -> Optional[List[str]]:
    """
    Jikan API (MAL wrapper) üzerinden sezon-spesifik karakter listesi çeker.

    Arama sırası:
      1. season_title  ("Sword Art Online: Alicization" gibi tam başlık)
      2. series_title  ("Sword Art Online" genel başlık — fallback)

    Cache sırası:
      1. Oturum içi bellek  (_JIKAN_CACHE dict)
      2. Disk cache         (jikan_cache/{slug}.json, TTL=30 gün)
      3. Jikan API          (HTTP)
    """
    import time as _time

    os.makedirs(_JIKAN_DISK_DIR, exist_ok=True)

    def _disk_path(query: str) -> str:
        safe = re.sub(r'[^a-z0-9]', '_', query.lower().strip())[:60]
        return os.path.join(_JIKAN_DISK_DIR, f"{safe}.json")

    def _search_and_fetch(query: str) -> Optional[List[str]]:
        mem_key = f"jikan:{query.lower().strip()}"

        # 1. Oturum belleği
        if mem_key in _JIKAN_CACHE:
            return _JIKAN_CACHE[mem_key]

        # 2. Disk cache
        dpath = _disk_path(query)
        if os.path.exists(dpath):
            try:
                age_days = (_time.time() - os.path.getmtime(dpath)) / 86400
                if age_days < _JIKAN_DISK_TTL:
                    chars = json.load(open(dpath, "r", encoding="utf-8")).get("characters")
                    _JIKAN_CACHE[mem_key] = chars
                    if verbose and chars:
                        print(f"[Glossary] Jikan disk cache: '{query}' → {len(chars)} karakter")
                    return chars
            except Exception:
                pass

        # 2.5 AniList GraphQL check (Hızlı ve yüksek limitli)
        try:
            al_chars = _anilist_get_characters(query, verbose=verbose)
            if al_chars:
                try:
                    with open(dpath, "w", encoding="utf-8") as f:
                        json.dump({"characters": al_chars}, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                _JIKAN_CACHE[mem_key] = al_chars
                return al_chars
        except Exception:
            pass

        # 3. Jikan API -- 500/502/503/504 icin retry + exponential backoff
        # Gecici sunucu hatalarinda _JIKAN_CACHE[mem_key]=None YAZILMAZ.
        # Sadece gercek "sonuc yok" (404/bos data) durumunda None cache'e yazilir.
        _TRANSIENT = {500, 502, 503, 504}
        _MAX_RETRY  = 3

        for _attempt in range(_MAX_RETRY):
            try:
                sr = requests.get(
                    f"{_JIKAN_BASE}/anime",
                    params={"q": query, "limit": 3, "type": "tv"},
                    timeout=REQUEST_TIMEOUT + 2,
                    headers=HEADERS,
                )

                # 429 Rate-limit: bekle, tekrar dene
                if sr.status_code == 429:
                    _w = 2.0 * (2 ** _attempt)
                    if verbose:
                        print(f"[Glossary] Jikan rate-limit (429): '{query}' -> {_w:.0f}s bekleniyor...")
                    _time.sleep(_w)
                    continue

                # Gecici sunucu hatasi: cache'e None YAZMA, retry yap
                if sr.status_code in _TRANSIENT:
                    _w = 1.0 * (2 ** _attempt)
                    if verbose:
                        print(f"[Glossary] Jikan gecici hata ({sr.status_code}): '{query}' "
                              f"-> deneme {_attempt + 1}/{_MAX_RETRY}, {_w:.0f}s bekleniyor...")
                    _time.sleep(_w)
                    continue

                # Diger HTTP hatalari (ornek: 404) -> gercek hata, None cache'e yaz
                if sr.status_code != 200:
                    if verbose:
                        print(f"[Glossary] Jikan hata ({sr.status_code}): '{query}' -> atlaniyor.")
                    _JIKAN_CACHE[mem_key] = None
                    return None

                entries = sr.json().get("data", [])
                if not entries:
                    _JIKAN_CACHE[mem_key] = None
                    return None

                # En iyi eslesmeyi sec (tam baslik oncelikli)
                mal_id = None
                ql = query.lower()
                for e in entries:
                    titles = [t.get("title", "").lower() for t in e.get("titles", [])]
                    if any(ql == t for t in titles):
                        mal_id = e["mal_id"]; break
                if not mal_id:
                    mal_id = entries[0]["mal_id"]

                _time.sleep(0.35)  # Jikan rate limit: 3 req/s

                cr = requests.get(
                    f"{_JIKAN_BASE}/anime/{mal_id}/characters",
                    timeout=REQUEST_TIMEOUT + 2,
                    headers=HEADERS,
                )

                # Karakter endpoint'i gecici hata verebilir
                if cr.status_code in _TRANSIENT:
                    _w = 1.0 * (2 ** _attempt)
                    if verbose:
                        print(f"[Glossary] Jikan karakter gecici hata ({cr.status_code}): "
                              f"mal_id={mal_id} -> deneme {_attempt + 1}/{_MAX_RETRY}, {_w:.0f}s bekleniyor...")
                    _time.sleep(_w)
                    continue

                cr.raise_for_status()
                chars_raw = cr.json().get("data", [])

                chars = []
                for c in chars_raw:
                    role = c.get("role", "")
                    if role not in ("Main", "Supporting"):
                        continue
                    name = c.get("character", {}).get("name", "").strip()
                    if not name:
                        continue
                    # MAL format: "Kirigaya, Kazuto" -> "Kazuto Kirigaya"
                    if "," in name:
                        parts = [p.strip() for p in name.split(",", 1)]
                        name = f"{parts[1]} {parts[0]}" if len(parts) == 2 else name
                    chars.append(name)

                result = chars if chars else None
                _JIKAN_CACHE[mem_key] = result

                # [FIX] Ayni mal_id'ye ait tum baslik varyantlarini da cache'e yaz
                if result and entries:
                    try:
                        selected_entry = next(
                            (e for e in entries if e.get("mal_id") == mal_id), None
                        )
                        if selected_entry:
                            for t_obj in selected_entry.get("titles", []):
                                t_str = t_obj.get("title", "").strip()
                                if t_str:
                                    alias_key = f"jikan:{t_str.lower().strip()}"
                                    if alias_key not in _JIKAN_CACHE:
                                        _JIKAN_CACHE[alias_key] = result
                    except Exception:
                        pass

                # Disk'e yaz
                if result:
                    try:
                        json.dump(
                            {"query": query, "mal_id": mal_id, "characters": result},
                            open(dpath, "w", encoding="utf-8"),
                            ensure_ascii=False,
                        )
                    except Exception:
                        pass
                    if verbose:
                        print(f"[Glossary] Jikan: '{query}' -> {len(result)} karakter (mal_id={mal_id})")
                return result

            except requests.exceptions.Timeout:
                _w = 1.0 * (2 ** _attempt)
                if verbose:
                    print(f"[Glossary] Jikan timeout: '{query}' -> deneme {_attempt + 1}/{_MAX_RETRY}, "
                          f"{_w:.0f}s bekleniyor...")
                _time.sleep(_w)
                continue

            except Exception as exc:
                if verbose:
                    print(f"[Glossary] Jikan hata: '{query}' -> {exc}")
                # Gecici ag hatasi mi? (500/connection reset vb.)
                _exc_str = str(exc).lower()
                _is_transient = any(
                    k in _exc_str
                    for k in ("500", "502", "503", "504", "connection", "reset", "internal server")
                )
                if _is_transient and _attempt < _MAX_RETRY - 1:
                    _time.sleep(1.0 * (2 ** _attempt))
                    continue
                # Gercek hata -> None cache'e yaz
                _JIKAN_CACHE[mem_key] = None
                return None

        # Tum denemeler basarisiz -- GECICI HATA: cache'e None YAZMA
        # Bir sonraki cagri yeniden deneyebilsin.
        if verbose:
            print(f"[Glossary] Jikan tum denemeler basarisiz: '{query}' -> Jikan atlaniyor.")
        return None

    # Arama sırası: season_title → series_title
    for q in filter(None, [season_title, series_title]):
        result = _search_and_fetch(q)
        if result:
            return result
    return None



def _anilist_get_characters(query: str, verbose: bool = True) -> Optional[List[str]]:
    """
    AniList GraphQL API üzerinden karakter listesi çeker.
    Jikan API çöktüğünde fallback olarak çalışır.
    """
    gql = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        id
        characters(perPage: 35) {
          nodes {
            name { full }
          }
        }
      }
    }
    """
    try:
        r = requests.post(
            "https://graphql.anilist.co",
            json={"query": gql, "variables": {"search": query}},
            timeout=REQUEST_TIMEOUT + 3
        )
        if r.status_code == 200:
            data = r.json()
            media = data.get("data", {}).get("Media")
            if media:
                nodes = media.get("characters", {}).get("nodes") or []
                chars = [node["name"]["full"] for node in nodes if node.get("name", {}).get("full")]
                if chars:
                    if verbose:
                        print(f"[Glossary] AniList karakter fallback: '{query}' → {len(chars)} karakter bulundu")
                    return chars
        elif r.status_code == 429:
            if verbose:
                print(f"[Glossary] AniList rate-limit (429) karakter araması için")
    except Exception as e:
        if verbose:
            print(f"[Glossary] AniList karakter fallback hatası: {e}")
    return None


def _anilist_get_all_titles(query: str, verbose: bool = True) -> List[str]:
    """
    AniList GraphQL API üzerinden anime başlıklarını ve sinonimlerini çeker.
    Jikan API çöktüğünde fallback olarak çalışır.
    """
    gql = """
    query ($search: String) {
      Media(search: $search, type: ANIME) {
        title { romaji english native }
        synonyms
      }
    }
    """
    titles: List[str] = []
    try:
        r = requests.post(
            "https://graphql.anilist.co",
            json={"query": gql, "variables": {"search": query}},
            timeout=REQUEST_TIMEOUT + 3
        )
        if r.status_code == 200:
            data = r.json()
            media = data.get("data", {}).get("Media")
            if media:
                t_obj = media.get("title") or {}
                synonyms = media.get("synonyms") or []
                candidates = [t_obj.get("english"), t_obj.get("romaji")] + synonyms
                
                # Check overlap to prevent matching random anime to western series
                _STOP = {'the','a','an','is','of','in','to','with','and','or','for',
                         'by','at','on','no','na','wa','ga','wo','ni','de','mo','ka'}
                _q_words = {w for w in re.sub(r'[^a-z0-9 ]', '',
                            query.lower()).split() if w not in _STOP and len(w) >= 3}
                _all_entry_text = ' '.join(c.lower() for c in candidates if c)
                _entry_words = set(re.sub(r'[^a-z0-9 ]', '', _all_entry_text).split())
                if _q_words and len(_q_words & _entry_words) < min(len(_q_words), 2):
                    if verbose:
                        print(f"[Glossary] AniList sonucu alakasiz bulundu (reddedildi): {candidates[:2]}")
                    return []
                
                seen = set()
                for c in candidates:
                    if not c:
                        continue
                    c_strip = c.strip()
                    if re.search(r'[\u3000-\u9fff\uff00-\uffef\u3040-\u30ff]', c_strip):
                        continue
                    if c_strip.lower() not in seen:
                        seen.add(c_strip.lower())
                        titles.append(c_strip)
                if verbose and titles:
                    print(f"[Glossary] AniList baslik varyantlari ({query}): {titles}")
    except Exception as e:
        if verbose:
            print(f"[Glossary] AniList baslik fallback hatası: {e}")
    return titles


# ─────────────────────────────────────────────────────────────────────────────
# 1c. GERÇEK ZAMANLI BAŞLIK ÇÖZÜCÜLER — Medya türüne göre doğru API
#   anime   → Jikan/MAL  (EN + romaji + synonyms)
#   series  → TVMaze     (Batı dizisi)
#   movie   → TMDB       (film)
# Her tür YALNIZCA KENDİ veritabanını sorgular. Veri KARISIMI ÖNLENIR.
# ─────────────────────────────────────────────────────────────────────────────

_TITLES_DISK_TTL = 30  # Başlık cache gün süresi


def _jikan_get_all_titles(query: str, verbose: bool = False) -> List[str]:
    """
    Jikan API'den anime başlıklarını çeker: EN + romaji + synonyms.
    SADECE ANİME için! Batı dizisi/film için çağrılmamalı.
    Disk cache: jikan_cache/{safe}.titles.json (TTL=30 gün)
    """
    import time as _t
    os.makedirs(_JIKAN_DISK_DIR, exist_ok=True)
    safe = re.sub(r'[^a-z0-9]', '_', query.lower().strip())[:60]
    cache_path = os.path.join(_JIKAN_DISK_DIR, f"{safe}.titles.json")

    # Disk cache kontrolü
    if os.path.exists(cache_path):
        try:
            age_days = (_t.time() - os.path.getmtime(cache_path)) / 86400
            if age_days < _TITLES_DISK_TTL:
                return json.load(open(cache_path, 'r', encoding='utf-8')).get('titles', [])
        except Exception:
            pass

    # AniList GraphQL ile başlıkları çekmeyi dene (Hızlı ve limitsiz)
    try:
        al_titles = _anilist_get_all_titles(query, verbose=verbose)
        if al_titles:
            try:
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump({'titles': al_titles}, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return al_titles
    except Exception:
        pass

    # ── Sorgu kelimelerini çıkar (stop word'ler hariç) ─────────────────────
    _STOP = {'the','a','an','is','of','in','to','with','and','or','for',
             'by','at','on','no','na','wa','ga','wo','ni','de','mo','ka'}
    _q_words = {w for w in re.sub(r'[^a-z0-9 ]', '',
                query.lower()).split() if w not in _STOP and len(w) >= 3}

    titles: List[str] = []
    try:
        sr = requests.get(
            f"{_JIKAN_BASE}/anime",
            params={"q": query, "limit": 5},
            timeout=REQUEST_TIMEOUT + 2,
            headers=HEADERS,
        )
        if sr.status_code == 429:  # rate-limit: kısa bekle
            _t.sleep(2.0)
            sr = requests.get(f"{_JIKAN_BASE}/anime", params={"q": query, "limit": 5},
                              timeout=REQUEST_TIMEOUT + 2, headers=HEADERS)
        if sr.status_code != 200:
            return titles

        entries = sr.json().get('data', [])
        if not entries:
            return titles

        # En iyi eslesmeyi sec: tam isim uyumu oncelikli, sonra kelime ortusumu
        best = None
        ql = query.lower().strip()
        # Adim 1: Tam baslik eslesimi
        for e in entries:
            for t_obj in e.get('titles', []):
                if t_obj.get('title', '').lower().strip() == ql:
                    best = e
                    break
            if best:
                break

        # KRITIK DOGRULAMA: Jikan sonucu sorguyla iliskili mi?
        # Jikan bazen 1. sonuc olarak alakasiz anime dondurur
        # (ornek: 'dealing with mikadono' -> MAL 64091 'Aisanai to Iwaremashitemo').
        # TUM 5 sonucu kontrol et — dogru anime 2. veya 3. sirada olabilir!
        if _q_words and not best:
            for e in entries:
                _all_entry_text = ' '.join(
                    t_obj.get('title', '').lower()
                    for t_obj in e.get('titles', [])
                )
                _entry_words = set(re.sub(r'[^a-z0-9 ]', '', _all_entry_text).split())
                if _q_words & _entry_words:
                    best = e  # Bu entry sorguyla iliskili!
                    break

        if not best:
            # Hicbir entry sorguyla iliskili degil.
            # FALLBACK: Her onemli kelimeyi ayri ayri Jikan'da dene
            # Ornek: "dealing with mikadono sisters" basarisiz → "mikadono" dene
            _kw_fallback = sorted(
                (w for w in _q_words if len(w) >= 5),
                key=len, reverse=True  # En uzun kelimeyi once dene
            )
            for _kw in _kw_fallback[:3]:  # Max 3 kelime dene
                _t.sleep(0.4)  # Jikan rate limit
                try:
                    _kr = requests.get(
                        f"{_JIKAN_BASE}/anime",
                        params={"q": _kw, "limit": 3},
                        timeout=REQUEST_TIMEOUT + 2,
                        headers=HEADERS,
                    )
                    if _kr.status_code != 200:
                        continue
                    _kw_entries = _kr.json().get('data', [])
                    for _ke in _kw_entries:
                        _ke_text = ' '.join(
                            t.get('title', '').lower()
                            for t in _ke.get('titles', [])
                        )
                        _ke_words = set(re.sub(r'[^a-z0-9 ]', '', _ke_text).split())
                        # Bu entry sorguyla iliskili mi?
                        if _q_words & _ke_words:
                            best = _ke
                            if verbose:
                                print(f"[Glossary] Jikan anahtar kelime fallback: "
                                      f"'{_kw}' -> MAL {_ke.get('mal_id')}")
                            break
                except Exception:
                    continue
                if best:
                    break

        if not best:
            # Gercekten bulunamadi
            if verbose:
                print(f"[Glossary] Jikan RED: '{query}' -> hicbir yontemle bulunamadi.")
            return titles  # [] -- yanlis veriyi cache'e YAZMA

        # ── [ALTIN KURAL] MAL ID → /external → Doğrudan Fandom URL ────────────
        # Bu yöntem slug tahminine gerek bırakmaz: MAL sayfasındaki "External Links"
        # alanında Fandom wikisi varsa URL'yi direkt alırız → %100 doğru slug.
        _mal_id = best.get('mal_id')
        if _mal_id:
            try:
                _t.sleep(0.4)  # Jikan rate-limit
                _ext_r = requests.get(
                    f"{_JIKAN_BASE}/anime/{_mal_id}/external",
                    timeout=REQUEST_TIMEOUT + 2, headers=HEADERS,
                )
                if _ext_r.status_code == 200:
                    import re as _re2
                    for _item in (_ext_r.json().get('data') or []):
                        _eurl = _item.get('url', '')
                        # fandom.com URL'si mi?
                        _fm = _re2.search(r'https?://([^./]+)\.fandom\.com', _eurl)
                        if _fm:
                            _direct_slug = _fm.group(1)
                            if verbose:
                                print(f"[Glossary] MAL external → Fandom slug: "
                                      f"'{_direct_slug}' ({_eurl})")
                            # Bu slug'ı titles listesine EN BAŞA ekle — slug candidate
                            # sistemi önce bunu deneyecek (find_wiki_slug'da kullanılır)
                            titles.insert(0, f"__FANDOM_SLUG__:{_direct_slug}")
                            break
            except Exception:
                pass  # External link çekilemezse devam et — slug tahminine dön
        # ────────────────────────────────────────────────────────────────────────

        # Tum baslik varyantlarini topla (Japonca native haric)
        seen_t: set = set()
        for t_obj in best.get('titles', []):
            t_str = t_obj.get('title', '').strip()
            if not t_str or t_str.lower() in seen_t:
                continue
            # Japonca/Çince/Kore karakterleri içeriyorsa atla
            if re.search(r'[\u3000-\u9fff\uff00-\uffef\u3040-\u30ff]', t_str):
                continue
            titles.append(t_str)
            seen_t.add(t_str.lower())

        # Disk'e kaydet
        try:
            json.dump({'query': query, 'titles': titles},
                      open(cache_path, 'w', encoding='utf-8'), ensure_ascii=False)
        except Exception:
            pass
        if verbose and titles:
            print(f"[Glossary] Jikan baslik varyantlari ({query}): {titles}")
    except Exception:
        pass
    return titles


def _tvmaze_get_canonical_title(query: str, verbose: bool = False) -> List[str]:
    """
    TVMaze API'den Batı dizisi resmi başlığını çeker.
    SADECE BATI DİZİLERİ için — anime için çağrılmamalı!
    """
    titles: List[str] = []
    try:
        r = requests.get(
            'https://api.tvmaze.com/search/shows',
            params={'q': query},
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        if r.status_code != 200:
            return titles
        results = r.json()
        if not results:
            return titles
        show = results[0].get('show', {})
        name = show.get('name', '').strip()
        if name:
            titles.append(name)
        if verbose and titles:
            print(f"[Glossary] TVMaze başlık ({query}): {titles}")
    except Exception:
        pass
    return titles


def _tmdb_get_canonical_title(query: str, is_movie: bool = False, verbose: bool = False) -> List[str]:
    """
    TMDB API'den film veya dizi resmi başlığını çeker.
    TMDB API key gereklidir (translator_config.json: 'tmdb_api_key').
    """
    titles: List[str] = []
    tmdb_key = ''
    try:
        _cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'translator_config.json')
        if os.path.exists(_cfg):
            tmdb_key = json.load(open(_cfg, encoding='utf-8')).get('tmdb_api_key', '')
    except Exception:
        pass
    if not tmdb_key:
        return titles

    endpoint    = 'movie' if is_movie else 'tv'
    title_field = 'title' if is_movie else 'name'
    orig_field  = 'original_title' if is_movie else 'original_name'
    try:
        r = requests.get(
            f'https://api.themoviedb.org/3/search/{endpoint}',
            params={'api_key': tmdb_key, 'query': query, 'language': 'en-US'},
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        if r.status_code != 200:
            return titles
        results = r.json().get('results', [])
        if not results:
            return titles
        name = results[0].get(title_field, '').strip()
        orig = results[0].get(orig_field, '').strip()
        if name:
            titles.append(name)
        # Orijinal başlık Latince ise ekle (Japonca/Arap vb. atla)
        if orig and orig != name and not re.search(r'[\u0400-\u9fff]', orig):
            titles.append(orig)
        if verbose and titles:
            print(f"[Glossary] TMDB {'film' if is_movie else 'dizi'} başlık ({query}): {titles}")
    except Exception:
        pass
    return titles


# ── K2 — Aday Üretimi (Candidate Generation) ──────────────────────────────────
_TRAVERSAL = "wdt:P144|wdt:P179|wdt:P361|wdt:P8345|wdt:P4969|^wdt:P4969|^wdt:P144"

def _parse_fandom_id(value: str) -> Tuple[str, str]:
    """P4073/P6262 değerini (slug, lang) olarak çöz."""
    value = value.split(":", 1)[0]
    if "." in value:
        lang, slug = value.split(".", 1)
        if len(lang) <= 7:
            return slug, ("" if lang == "en" else lang)
    return value, ""

def candidates_from_wikidata(qid: str) -> List[Candidate]:
    """Direkt P4073/P6262 + 2 seviye ilişki traversal'ı (tek SPARQL)."""
    query = f"""
    SELECT DISTINCT ?fandom ?article WHERE {{
      BIND(wd:{qid} AS ?item)
      ?item (({_TRAVERSAL})?)/(({_TRAVERSAL})?) ?related .
      OPTIONAL {{ ?related wdt:P4073 ?fandom }}
      OPTIONAL {{ ?related wdt:P6262 ?article }}
      FILTER(BOUND(?fandom) || BOUND(?article))
    }} LIMIT 20"""
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(query)
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            out: Dict[str, Candidate] = {}
            for b in data["results"]["bindings"]:
                for key, score in (("fandom", 0.95), ("article", 0.90)):
                    if key in b:
                        slug, lang = _parse_fandom_id(b[key]["value"])
                        c = out.setdefault(slug, Candidate(slug, lang, score, "wikidata"))
                        c.base_score = max(c.base_score, score)
            return list(out.values())
    except Exception:
        pass
    return []

def slugify(text: str) -> str:
    """Metni Fandom slug formatına (küçük harf, noktalama işaretsiz, tireli) dönüştürür."""
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def candidates_from_slugify_probe(titles: List[str]) -> List[Candidate]:
    """Başlıkların slugify edilmiş hallerini doğrudan probe ederek aday üretir.
    
    Not: "Ao Buta" → "ao-buta" (tireli) probe edilir, 404 alırsa
    tiresiz versiyonu "aobuta" da denenir (Fandom'da bazı wikiler tiresiz subdomain kullanır).
    """
    cands = []
    seen_slugs = set()
    for title in titles:
        slug = slugify(title)
        if len(slug) >= _MIN_SLUG_LEN and slug not in seen_slugs:
            if len(seen_slugs) >= 8: # Sınırla: en fazla 8 benzersiz slug'ı probe et
                break
            seen_slugs.add(slug)
            real_slug = _check_wiki_and_get_real_slug(slug)
            if real_slug:
                cands.append(Candidate(
                    slug=real_slug,
                    lang_path="",
                    base_score=0.85,
                    source="slugify-probe"
                ))
            elif '-' in slug:
                # Tireli slug başarısız → tiresiz versiyonu dene (ör: "ao-buta" → "aobuta")
                slug_no_dash = slug.replace('-', '')
                if len(slug_no_dash) >= _MIN_SLUG_LEN and slug_no_dash not in seen_slugs:
                    seen_slugs.add(slug_no_dash)
                    real_slug2 = _check_wiki_and_get_real_slug(slug_no_dash)
                    if real_slug2:
                        cands.append(Candidate(
                            slug=real_slug2,
                            lang_path="",
                            base_score=0.82,  # Tireli versiyona göre hafif düşük puan
                            source="slugify-probe"
                        ))
    return cands

def candidates_from_fandom_search(titles: List[str], media_hub: str, limit: int = 8) -> List[Candidate]:
    """Fandom resmi unified-search — AI slug tahmininin yerini alan ana yol (lang kaldırıldı, global arar)."""
    seen: Dict[str, Candidate] = {}
    votes: Dict[str, int] = {}
    for t in titles[:4]:
        q = urllib.parse.quote(t)
        try:
            url = f"https://services.fandom.com/unified-search/community-search?query={q}&limit={limit}"
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                for item in data.get("results", []):
                    # URL ve dil kodunu doğru eşleştiren yeni regex
                    m = re.search(r"https?://([a-z0-9-]+)\.fandom\.com/(?:([a-z]{2,3}(?:-[a-z]{2,4})?)/?)?", item.get("url", ""))
                    if not m:
                        continue
                    slug = m.group(1)
                    lang_path = m.group(2) or ""
                    key = f"{slug}:{lang_path}"
                    votes[key] = votes.get(key, 0) + 1
                    if key not in seen:
                        seen[key] = Candidate(
                            slug=slug, lang_path=lang_path, base_score=0.55, source="unified-search",
                            hub=item.get("hub", ""), page_count=int(item.get("pageCount") or 0),
                            wiki_name=item.get("name", ""),
                        )
        except Exception:
            pass
        time.sleep(0.3)
        
    for key, c in seen.items():
        if votes[key] >= 2:
            c.bonuses["multi_synonym"] = 0.10
        if c.hub and media_hub and c.hub == media_hub:
            c.bonuses["hub_match"] = 0.15
        elif c.hub and media_hub and c.hub != media_hub:
            c.bonuses["hub_mismatch"] = -0.20
        if c.page_count >= 100:
            c.bonuses["big_wiki"] = 0.05
        best_name = max((_fuzzy(c.wiki_name.replace(" Wiki", ""), t) for t in titles), default=0.0)
        if best_name >= 0.75:
            c.bonuses["name_match"] = 0.15
    return list(seen.values())

# ── K3 — Hakemli Doğrulama (Verification) ────────────────────────────────────
ACCEPT_THRESHOLD = 0.75

CROSSOVER_BLOCKLIST = re.compile(
    r"^(hero|heroes|villains?|protagonist|antagonists?|characters?|allfiction|"
    r"listofdeaths|love-interest|vsbattles|powerlisting|superpower|"
    r"deathbattle.*|fictional-battle.*|dubbing.*|.*-fanon|fanon.*|ideas)$"
)

_SUBPAGE_BLOCKLIST_RE = re.compile(
    r"/(Relationships|Image Gallery|Gallery|History|Quotes|Trivia|Abilities|Synopsis)$",
    re.IGNORECASE
)

def _mw_query(api_base: str, **params) -> Optional[dict]:
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = f"{api_base}/api.php?" + urllib.parse.urlencode(params)
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def get_siteinfo(api_base: str) -> Optional[dict]:
    data = _mw_query(api_base, action="query", meta="siteinfo", siprop="general|interwikimap|statistics")
    try:
        return data["query"]
    except (KeyError, TypeError):
        return None

def probe_pages(api_base: str, names: List[str]) -> float:
    """Karakter/nadir-terim problaması: sayfaların kaçı mevcut? (redirects=1)"""
    if not names:
        return -1.0
    data = _mw_query(api_base, action="query", titles="|".join(names[:20]), redirects="1")
    try:
        pages = data["query"]["pages"]
    except (KeyError, TypeError):
        return -1.0
    hits = sum(1 for p in pages if not p.get("missing"))
    return hits / len(pages) if pages else 0.0

def name_variants(full_names: List[str]) -> List[str]:
    """'Godou Kusanagi' -> hem kendisi hem 'Kusanagi Godou' (romaji sıra farkı)."""
    out: List[str] = []
    for n in full_names:
        out.append(n)
        parts = n.split()
        if len(parts) == 2:
            out.append(f"{parts[1]} {parts[0]}")
    return out

def verify(cand: Candidate, titles: List[str], probe_names: List[str],
           rare_terms: List[str] | None = None) -> float:
    """Skoru hesapla; veto durumunda -1 döner."""
    if CROSSOVER_BLOCKLIST.match(cand.slug):
        return -1.0

    score = cand.base_score + sum(cand.bonuses.values())

    si = get_siteinfo(cand.api_base)
    if not si:
        return -1.0
    sitename = si["general"].get("sitename", "")
    best = max((_fuzzy(sitename.replace(" Wiki", ""), t) for t in titles), default=0)

    # Ad doğrulama kontrolü: Wikidata harici kaynaklardan gelen adaylarda sitename veya slug 
    # başlıkların hiçbiriyle makul derecede benzemiyorsa veto et.
    if cand.source != "wikidata":
        best_slug = max((_fuzzy(cand.slug, t) for t in titles), default=0)
        if max(best, best_slug) < 0.38:
            return -1.0

    if best >= 0.70:
        score += 0.10
    elif best < 0.35 and cand.source != "wikidata":
        score -= 0.15

    # Karakter problaması
    variants = name_variants(probe_names)
    ratio = probe_pages(cand.api_base, variants)
    if ratio >= 0.5:
        score += 0.25
    elif ratio == 0.0 and probe_names:
        return -1.0

    if rare_terms:
        if probe_pages(cand.api_base, rare_terms) > 0:
            score += 0.10

    # Wiki boyutu (makale sayısı) ödülü/cezası
    stats = si.get("statistics", {})
    articles = int(stats.get("articles") or 0)
    if articles >= 50:
        score += 0.15
    elif articles >= 20:
        score += 0.05
    elif articles < 15:
        score -= 0.15

    # Dil skorlaması: İngilizce/Root wiki (lang_path == "") tercih edilir, diğerleri cezalandırılır.
    if cand.lang_path == "":
        score += 0.15
    else:
        score -= 0.15

    return score

def pick_language_variant(api_base_root: str, target_lang: str) -> str:
    """interwikimap'ten hedef dilin alt-yolunu bul; yoksa root'u döndür."""
    si = get_siteinfo(api_base_root)
    if si:
        for iw in si.get("interwikimap", []):
            if iw.get("bcp47") == target_lang and iw.get("local"):
                iw_url = iw.get("url", "")
                if "/wiki/$1" in iw_url:
                    api_url = iw_url.replace("/wiki/$1", "/api.php")
                    if api_url.startswith("http://"):
                        api_url = api_url.replace("http://", "https://")
                    return api_url
    return api_base_root

def _load_overrides() -> dict:
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "overrides.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def find_wiki_slug(title: str, media_type: str = 'auto', use_ai_fallback: bool = True) -> Optional[str]:
    """
    Medyadan Fandom wiki subdomainini bulur (v2 deterministik).
    """
    query_clean = title.strip()
    query_key = query_clean.lower()
    
    # 0. Manuel override denetimi
    overrides = _load_overrides()
    if query_key in overrides:
        slug = overrides[query_key]
        _WIKI_API_ENDPOINTS[slug.lower()] = f"https://{slug}.fandom.com/api.php"
        return slug
        
    details = resolve_media_details(query_clean, media_type=media_type, verbose=True)
    for source_name, id_val in (('anilist', details['anilist_id']), ('mal', details['mal_id']), ('tmdb', details['tmdb_id'])):
        if id_val:
            key = f"{source_name}:{id_val}"
            if key in overrides:
                slug = overrides[key]
                _WIKI_API_ENDPOINTS[slug.lower()] = f"https://{slug}.fandom.com/api.php"
                return slug

    # 1. Başlıklar ve karakter problama listesi
    titles = details['titles']
    probe_names = details['characters']
    
    hub_map = {
        "anime": "anime",
        "series": "tv",
        "movie": "movies",
    }
    media_hub = hub_map.get(details['media_type'], "anime")
    
    # 2. Aday Üretimi (K2)
    cands: List[Candidate] = []
    
    ids = {}
    if details['anilist_id']:
        ids['anilist'] = details['anilist_id']
    if details['mal_id']:
        ids['myanimelist'] = details['mal_id']
    if details['tmdb_id']:
        ids['themoviedb'] = details['tmdb_id']
        
    qid = find_wikidata_qid(ids)
    if qid:
        cands.extend(candidates_from_wikidata(qid))
        
    cands.extend(candidates_from_slugify_probe(titles))
    cands.extend(candidates_from_fandom_search(titles, media_hub))
    
    # 3. Hakemli Doğrulama (K3)
    best_cand: Optional[Candidate] = None
    best_score = ACCEPT_THRESHOLD
    
    for c in sorted(cands, key=lambda x: -x.base_score):
        score = verify(c, titles, probe_names)
        if score > best_score:
            best_cand = c
            best_score = score
            
    if best_cand:
        slug = best_cand.slug
        api_base = best_cand.api_base
        if not api_base.endswith("/"):
            api_base += "/"
        _WIKI_API_ENDPOINTS[slug.lower()] = api_base + "api.php"
        print(f"[Glossary] Fandom wiki doğrulandı: '{slug}' ({best_cand.source}, skor: {best_score:.2f})")
        return slug
        
    # 4. Fallback (AI - son çare)
    if use_ai_fallback:
        print(f"[Glossary] Eşik aşan aday bulunamadı. Yapay zeka ile aranıyor...")
        ai_slug = _ai_find_wiki_slug(title)
        if ai_slug:
            real = _check_wiki_and_get_real_slug(ai_slug)
            if real:
                print(f"[Glossary] Yapay zeka eşleşmesi doğrulandı: '{real}'")
                return real
                
    print(f"[Glossary] '{title}' için uygun Fandom wiki bulunamadı.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. KATEGORİ SORGUSU
# ─────────────────────────────────────────────────────────────────────────────

import re
from typing import Tuple

def clean_wikitext(text: str) -> str:
    # 1. Strip comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # 2. Strip templates (nested up to 5 levels)
    for _ in range(5):
        text = re.sub(r"\{\{[^{}]*\}\}", "", text, flags=re.DOTALL)
    # 3. Strip tables
    text = re.sub(r"\{\|.*?\|\}", "", text, flags=re.DOTALL)
    # 4. Strip files/images/categories links
    text = re.sub(r"\[\[(?:File|Image|Kategori|Category|Dosya):.*?\]\]", "", text, flags=re.IGNORECASE)
    # 5. Clean up links: [[Target|Display]] -> Display, [[Target]] -> Target
    text = re.sub(r"\[\[[^|\]]+\|([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    # 6. Formatting: '''bold''' -> bold, ''italic'' -> italic
    text = re.sub(r"'''+", "", text)
    text = re.sub(r"''+", "", text)
    # 7. Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # 8. Clean up extra spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200]

def _fetch_term_summaries(slug: str, titles: List[str]) -> Dict[str, str]:
    """Terimlerin ilk paragraflarını (lead section 0) Fandom API'sinden çekip temizler."""
    summaries = {}
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvsection": "0",
            "titles": "|".join(batch),
            "format": "json"
        }
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, pinfo in pages.items():
                title = pinfo.get("title")
                revs = pinfo.get("revisions", [])
                if title and revs:
                    content = revs[0].get("*", "")
                    if content:
                        summaries[title] = clean_wikitext(content)
        except Exception:
            pass
    return summaries

def _query_category_with_details(slug: str, category: str) -> Dict[str, Dict[str, any]]:
    """Fandom wiki'deki bir kategorinin üyelerini ve bağlı kategorilerini çeker."""
    results = {}
    gcmcontinue = None
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    titles = []
    
    while True:
        params = {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmlimit": 500,
            "gcmnamespace": 0,
            "gcmtype": "page",
            "format": "json",
        }
        if gcmcontinue:
            params["gcmcontinue"] = gcmcontinue
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            data = r.json()
        except Exception:
            break
        pages = data.get("query", {}).get("pages", {})
        for pid, pinfo in pages.items():
            title = pinfo.get("title", "")
            if _SUBPAGE_BLOCKLIST_RE.search(title):
                continue
            if not (2 <= len(title) <= 60):
                continue
            _title_lower = title.lower()
            _skip_meta = {
                'characters', 'story arcs', 'arcs', 'terminology', 'glossary',
                'locations', 'items', 'weapons', 'skills', 'abilities',
                'organizations', 'groups', 'factions', 'guilds',
            }
            if _title_lower in _skip_meta:
                continue
            titles.append(title)
            
        if len(titles) >= MAX_TERMS_PER_CAT:
            break
        cont = data.get("continue", {}).get("gcmcontinue")
        if cont:
            gcmcontinue = cont
        else:
            break
            
    if not titles:
        return results

    # 2. Sayfaların kategorilerini 40'arlı batch'ler halinde sorgula (clcontinue takibi ile)
    page_categories = {}
    for i in range(0, len(titles), 40):
        batch = titles[i:i+40]
        clcontinue = None
        while True:
            params = {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "categories",
                "cllimit": 500,
                "format": "json"
            }
            if clcontinue:
                params["clcontinue"] = clcontinue
            try:
                r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
                data = r.json()
                pages = data.get("query", {}).get("pages", {})
                for pid, pinfo in pages.items():
                    t = pinfo.get("title")
                    if t:
                        cats = [c.get("title", "") for c in pinfo.get("categories", [])]
                        page_categories.setdefault(t, []).extend(cats)
            except Exception:
                break
            
            cont = data.get("continue", {}).get("clcontinue")
            if cont:
                clcontinue = cont
            else:
                break
                
    # Kategorileri tekilleştir
    for t in page_categories:
        page_categories[t] = list(set(page_categories[t]))

    # 3. Negatif kategorileri filtrele ve sonuçları oluştur
    for title in titles:
        cats = page_categories.get(title, [])
        is_cast_or_crew = False
        for cat_title in cats:
            cat_lower = cat_title.lower()
            if any(x in cat_lower for x in [
                "cast", "crew", "actor", "actress", "director", "producer", "writer",
                "real people", "real-life", "reparto", "staff", "seiyuu", "voice actor",
                "personaggi reali", "real person", "personaggi storici"
            ]):
                is_cast_or_crew = True
                break
        if is_cast_or_crew:
            continue
            
        results[title] = {
            "categories": cats,
            "raw_title": title
        }
        
    return results

def _get_subcategories(slug: str, category: str) -> List[str]:
    """Kategorinin alt kategorilerini bulur (Namespace 14, type=subcat)."""
    subcats = []
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 50,
        "cmnamespace": 14,
        "cmtype": "subcat",
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        data = r.json()
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            title = m.get("title", "")
            if title.startswith("Category:"):
                subcats.append(title.split(":", 1)[1])
    except Exception:
        pass
    return subcats

def _query_all_pages(slug: str) -> Dict[str, Dict[str, any]]:
    """Kategori bulunamazsa veya boşsa, wiki'deki tüm asıl makaleleri (ns=0) düz liste olarak çeker."""
    results = {}
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    params = {
        "action": "query",
        "list": "allpages",
        "aplimit": 100,
        "apnamespace": 0,
        "apfilterredir": "nonredirects",
        "format": "json",
    }
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
        data = r.json()
        pages = data.get("query", {}).get("allpages", [])
        for p in pages:
            title = p.get("title", "")
            if _SUBPAGE_BLOCKLIST_RE.search(title):
                continue
            if not (2 <= len(title) <= 60):
                continue
            results[title] = {
                "categories": [],
                "raw_title": title
            }
    except Exception:
        pass
    return results

def canonicalize(api_base: str, terms: List[str]) -> Dict[str, List[str]]:
    """
    Redirect'leri çözerek kirliliği önler.
    Kanonik isimler ile alias'ları eşleştirir: {canonical_title: [aliases]}
    """
    api_base = api_base.replace("/api.php", "").rstrip("/")
    canon: Dict[str, List[str]] = {}
    for i in range(0, len(terms), 50):
        batch = terms[i:i + 50]
        data = _mw_query(api_base, action="query", titles="|".join(batch), redirects="1")
        if not data:
            continue
        q = data.get("query", {})
        rmap = {r["from"]: r["to"] for r in q.get("redirects", [])}
        for t in batch:
            target = rmap.get(t, t)
            canon.setdefault(target, [])
            if t != target:
                canon[target].append(t)
    seen: Dict[str, str] = {}
    result: Dict[str, List[str]] = {}
    for title, aliases in canon.items():
        key = _norm(title)
        if key in seen:
            result[seen[key]].extend([title] + aliases)
        else:
            seen[key] = title
            result[title] = aliases
    return result

def _fetch_page_redirects(slug: str, titles: List[str]) -> Dict[str, List[str]]:
    """Kanonik sayfaların yönlendirmelerini (alias'larını) prop=redirects kullanarak çeker."""
    redirects_map = {}
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]
        params = {
            "action": "query",
            "prop": "redirects",
            "rdlimit": 100,
            "rdnamespace": 0,
            "titles": "|".join(batch),
            "format": "json"
        }
        try:
            r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT, headers=HEADERS)
            data = r.json()
            pages = data.get("query", {}).get("pages", {})
            for pid, pinfo in pages.items():
                title = pinfo.get("title")
                reds = pinfo.get("redirects", [])
                if title and reds:
                    alias_list = [
                        rd.get("title") for rd in reds
                        if rd.get("title") and not _SUBPAGE_BLOCKLIST_RE.search(rd.get("title"))
                    ]
                    if alias_list:
                        redirects_map[title] = alias_list
        except Exception:
            pass
    return redirects_map

def _fetch_all_terms(slug: str) -> Tuple[Dict[str, List[str]], Dict[str, Dict[str, any]]]:
    """Wiki'deki tüm ilgili kategorilerden terimleri toplar, redirect'leri çözerek alias'ları hasat eder ve metadata toplar."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    SUFFIXES = ["", " (Anime)", " (Manga)", " (Novel)", " (Live Action)", " (TV Series)", " (Video Game)"]
    group_raw_details: Dict[str, Dict[str, any]] = {g: {} for g in CATEGORY_GROUPS}
    _lock = threading.Lock()
    subcat_tasks = []

    def fetch_main_cat(group, cat):
        # 1. Alt kategorileri paralel çekmek için listeye ekle
        subcats = _get_subcategories(slug, cat)
        if subcats:
            with _lock:
                for sc in subcats:
                    subcat_tasks.append((group, sc))
        # 2. Kategorinin üyelerini çek
        details = _query_category_with_details(slug, cat)
        if details:
            with _lock:
                for title, info in details.items():
                    if title not in group_raw_details[group]:
                        group_raw_details[group][title] = info
                    else:
                        existing_cats = set(group_raw_details[group][title].get("categories", []))
                        existing_cats.update(info.get("categories", []))
                        group_raw_details[group][title]["categories"] = list(existing_cats)

    # Ana kategorileri oluştur
    main_candidates = []
    for group, cat_names in CATEGORY_GROUPS.items():
        for cat in cat_names:
            for sfx in SUFFIXES:
                main_candidates.append((group, f"{cat}{sfx}"))

    unique_main = []
    seen_main = set()
    for g, c in main_candidates:
        if (g, c) not in seen_main:
            seen_main.add((g, c))
            unique_main.append((g, c))

    # Phase 1: Ana kategorileri paralel sorgula
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(fetch_main_cat, g, c) for g, c in unique_main]
        for f in as_completed(futures):
            pass

    # Phase 2: Alt kategorileri paralel sorgula
    unique_subcats = []
    seen_sub = set()
    for g, c in subcat_tasks:
        if (g, c) not in seen_sub:
            seen_sub.add((g, c))
            unique_subcats.append((g, c))

    def fetch_subcat(group, cat):
        details = _query_category_with_details(slug, cat)
        if details:
            with _lock:
                for title, info in details.items():
                    if title not in group_raw_details[group]:
                        group_raw_details[group][title] = info
                    else:
                        existing_cats = set(group_raw_details[group][title].get("categories", []))
                        existing_cats.update(info.get("categories", []))
                        group_raw_details[group][title]["categories"] = list(existing_cats)

    if unique_subcats:
        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(fetch_subcat, g, c) for g, c in unique_subcats]
            for f in as_completed(futures):
                pass
    total_found = sum(len(d) for d in group_raw_details.values())
    if total_found < 5:
        all_pages = _query_all_pages(slug)
        if all_pages:
            group_raw_details["terminology"].update(all_pages)
    api_base = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    final_terms: Dict[str, List[str]] = {}
    metadata: Dict[str, Dict[str, any]] = {}
    all_titles_to_summarize = []
    
    # 1. İlk olarak, kategorilerden toplanan sayfalardan canonical/alias eşleşmesini yap
    for group, raw_map in group_raw_details.items():
        if not raw_map:
            continue
        try:
            canon_map = canonicalize(api_base, list(raw_map.keys()))
            flat = []
            seen = set()
            for canon_title, aliases in canon_map.items():
                if canon_title not in seen:
                    seen.add(canon_title)
                    flat.append(canon_title)
                    all_titles_to_summarize.append(canon_title)
                    cats = set(raw_map.get(canon_title, {}).get("categories", []))
                    # Filtrelenmiş alias'ları topla
                    valid_aliases = []
                    for al in aliases:
                        if _SUBPAGE_BLOCKLIST_RE.search(al):
                            continue
                        valid_aliases.append(al)
                        cats.update(raw_map.get(al, {}).get("categories", []))
                    metadata[canon_title] = {
                        "aliases": valid_aliases,
                        "categories": sorted(list(cats)),
                        "abstract": ""
                    }
            final_terms[group] = flat
        except Exception:
            final_terms[group] = list(raw_map.keys())
            for title in raw_map.keys():
                metadata[title] = {
                    "aliases": [],
                    "categories": sorted(raw_map[title].get("categories", [])),
                    "abstract": ""
                }
                all_titles_to_summarize.append(title)

    # 2. İkinci adım: prop=redirects kullanarak kanonik sayfaların diğer tüm yönlendirmelerini (alias'larını) hasat et
    all_canon_titles = [t for t, info in metadata.items() if "canonical" not in info]
    # Aaron Douglas ve Abraham Lim gibi ilk filtreden sızan alias yönlendirmelerini önlemek için canon listesini de temiz tut
    all_canon_titles = [t for t in all_canon_titles if t in metadata]
    if all_canon_titles:
        try:
            rd_map = _fetch_page_redirects(slug, all_canon_titles)
            for title, aliases in rd_map.items():
                if title in metadata:
                    # Sadece geçerli olan alias'ları filtrele
                    valid_aliases = [al for al in aliases if ":" not in al and "/" not in al]
                    existing_aliases = set(metadata[title].get("aliases", []))
                    existing_aliases.update(valid_aliases)
                    metadata[title]["aliases"] = sorted(list(existing_aliases))
                    
                    # Bu yeni hasat edilen alias'ları da metadata'ya ekle
                    for al in valid_aliases:
                        if al not in metadata:
                            metadata[al] = {
                                "canonical": title,
                                "categories": metadata[title].get("categories", []),
                                "abstract": ""
                            }
                            # İlgili kategori grubundaki terim listelerine bu alias'ı ekle
                            for group, terms_list in final_terms.items():
                                if title in terms_list and al not in terms_list:
                                    terms_list.append(al)
        except Exception:
            pass

    # 3. Kategori listelerini son halleriyle sırala
    final_terms = {g: sorted(list(set(v))) for g, v in final_terms.items() if v}

    # 4. Üçüncü adım: Terim Özetlerini (Abstracts) Çek
    if all_titles_to_summarize:
        try:
            summaries = _fetch_term_summaries(slug, all_titles_to_summarize)
            for title, abstract in summaries.items():
                if title in metadata:
                    metadata[title]["abstract"] = abstract
                    for al in metadata[title].get("aliases", []):
                        if al in metadata:
                            metadata[al]["abstract"] = abstract
        except Exception:
            pass
    return final_terms, metadata


# ─────────────────────────────────────────────────────────────────────────────
# 3. CACHE  (series_glossary.json)
# ─────────────────────────────────────────────────────────────────────────────

def _load_cache() -> dict:
    path = _glossary_path()
    if not os.path.isfile(path):
        return {}
    try:
        raw = json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        return {}

    # ── Otomatik deduplicate: aynı wiki slug → en çok terim içereni tut ──────
    # Ayrıca key formatını normalize et: "sword art online|" → "sword art online"
    seen_slug: dict = {}   # wiki_slug → (key, term_count)
    cleaned: dict   = {}

    for k, v in raw.items():
        if k == "__canonical_titles__":
            cleaned[k] = v
            continue
        if not isinstance(v, dict):
            continue

        # Key normalizeasyonu: "sword art online|" gibi trailing pipe/s temizle
        _nk = k.rstrip("|").rstrip()
        # "sword art online|s1" → olduğu gibi bırak (geçerli format)
        # "sword art online|"   → "sword art online" yap (bozuk format)
        if _nk.endswith("|s") or (k.endswith("|") and not k.endswith("|s")):
            _nk = k.rstrip("|").rstrip()

        wiki_slug = (v.get("wiki") or "").lower().replace(" ", "")
        term_count = sum(len(x) for x in v.get("terms", {}).values())

        if wiki_slug and wiki_slug in seen_slug:
            prev_key, prev_count = seen_slug[wiki_slug]
            if term_count > prev_count:
                # Yenisi daha iyi → eskiyi çıkar, yenisini ekle
                cleaned.pop(prev_key, None)
                cleaned[_nk] = v
                seen_slug[wiki_slug] = (_nk, term_count)
            # else: eskisi daha iyi → yenisi atlanır
        else:
            cleaned[_nk] = v
            if wiki_slug:
                seen_slug[wiki_slug] = (_nk, term_count)

    # Eğer temizleme yapıldıysa diske kaydet
    if cleaned != raw:
        try:
            _save_cache(cleaned)
        except Exception:
            pass

    return cleaned


def _save_cache(data: dict) -> None:
    """
    Atomic cache yazisi: onceden tempfile'a yaz, sonra os.replace() ile yer degistir.
    Bu sayede guc kesilmesi / crash durumunda dosya yarim kalmaz, her zaman tutarli kalir.
    """
    # 0 tane terim barındıran wikileri cache'ten filtrele
    filtered = {}
    for k, v in data.items():
        if k == "__canonical_titles__":
            filtered[k] = v
            continue
        if not isinstance(v, dict):
            continue
        wiki_slug = (v.get("wiki") or "").lower().replace(" ", "")
        term_count = sum(len(x) for x in v.get("terms", {}).values())
        if wiki_slug and term_count == 0:
            continue
        filtered[k] = v
    data = filtered

    path = _glossary_path()
    import tempfile
    _tmp_path = None
    try:
        dir_name = os.path.dirname(path)
        # Gecici dosyayi hedef dizinde olustur (farkli disk/partition sorunu olmasin)
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.tmp',
            dir=dir_name, delete=False
        ) as _tmp:
            json.dump(data, _tmp, ensure_ascii=False, indent=2)
            _tmp_path = _tmp.name
        # Atomic replace: eski dosyanin ustune gecici dosyayi koy
        os.replace(_tmp_path, path)
    except Exception as e:
        print(f"[Glossary] Cache yazılamadı: {e}")
        # Temizlik: tempfile kalmissa sil
        try:
            if _tmp_path and os.path.exists(_tmp_path):
                os.unlink(_tmp_path)
        except Exception:
            pass


def get_wiki_last_modified(slug: str) -> Optional[datetime]:
    """Wiki'deki en son değişikliğin zamanını döndürür."""
    url = _get_fandom_api_url(slug) or f"https://{slug}.fandom.com/api.php"
    params = {
        "action": "query",
        "list": "recentchanges",
        "rclimit": 1,
        "rcprop": "timestamp",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, timeout=5, headers=HEADERS)
        rc = r.json().get("query", {}).get("recentchanges", [])
        if rc:
            ts = rc[0].get("timestamp")
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    return None

def _is_fresh(entry: dict) -> bool:
    """
    Veri mevcut ve gecerliyse True doner.
    TTL sistemi:
      - wiki=None (bulunamadi): NOT_FOUND_TTL_DAYS gunden genczyse gecerli (7 gun)
      - wiki=slug: CACHE_TTL_DAYS gunden genczyse veya recentchanges ile degisiklik olmadigi teyit edildiyse gecerli (30 gun)
    """
    fetched_str = entry.get("fetched_at")
    if not fetched_str:
        return False

    try:
        fetched = datetime.fromisoformat(fetched_str)
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - fetched).days
    except Exception:
        return False

    slug = entry.get("wiki")
    if slug is None:
        return age_days < NOT_FOUND_TTL_DAYS

    # Standart TTL kontrolü
    if age_days < CACHE_TTL_DAYS:
        return True

    # Akıllı Cache Kontrolü: 30 gün dolmuşsa recentchanges'e bak
    last_mod = get_wiki_last_modified(slug)
    if last_mod:
        stale_days = (datetime.now(timezone.utc) - last_mod).days
        if stale_days > 365:
            print(f"[Glossary] UYARI: '{slug}' wikisi 1 yıldan uzun süredir güncellenmemiş (Stale Wiki)!")
            entry["stale"] = True

        if last_mod < fetched:
            # Biz çektikten sonra wiki güncellenmemiş → fetched_at'i şimdiye "touch" et ve taze kabul et
            entry["fetched_at"] = datetime.now(timezone.utc).isoformat()
            print(f"[Glossary] '{slug}' wikisi son çekimden beri güncellenmediği için cache taze kabul edildi (recentchanges).")
            return True

    return False

def _extract_characters_from_umbrella_page(wiki_slug: str, page_title: str) -> List[str]:
    """Umbrella wiki sayfasının wikitext'inden oyuncu/karakter listesini parse eder."""
    url = f"https://{wiki_slug}.fandom.com/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": page_title,
        "rvprop": "content",
        "rvslots": "main",
        "format": "json",
        "formatversion": 2
    }
    try:
        r = requests.get(url, params=params, timeout=10, headers=HEADERS).json()
        pages = r.get("query", {}).get("pages", [])
        if not pages or not pages[0].get("revisions"):
            return []
        wikitext = pages[0].get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("content", "")
        
        # Heading'leri tarayarak Cast/Characters bölümlerini bul
        headings = list(re.finditer(r'(==+)([^=]+)(==+)', wikitext))
        cast_sections = []
        for i, match in enumerate(headings):
            heading_text = match.group(2).strip().lower()
            if any(w in heading_text for w in ["cast", "character", "main", "supporting", "family", "others", "appearances"]):
                start_pos = match.end()
                end_pos = len(wikitext)
                heading_level = len(match.group(1))
                for next_match in headings[i+1:]:
                    next_level = len(next_match.group(1))
                    if next_level <= heading_level:
                        end_pos = next_match.start()
                        break
                cast_sections.append(wikitext[start_pos:end_pos])
                
        if not cast_sections:
            cast_sections = [wikitext]
            
        characters = []
        # Pattern: * [[Actor]] as Character
        pattern = re.compile(
            r'\*\s*(?:\[\[([^\]|]+)(?:\|[^\]]*)?\]\]|([^\[*:]+?))\s+as\s+(?:\[\[([^\]|]+)(?:\|[^\]]*)?\]\]|([^<:\n\(\{\[]+))',
            re.IGNORECASE
        )
        
        for section in cast_sections:
            for line in section.splitlines():
                m = pattern.search(line)
                if m:
                    actor = m.group(1) or m.group(2)
                    character = m.group(3) or m.group(4)
                    if actor and character:
                        character = character.strip()
                        character = re.sub(r'<[^>]+>', '', character)
                        character = re.sub(r'\{\{[^\}]+\}\}', '', character)
                        character = re.sub(r'\[\[[^\]|]+\|([^\]]+)\]\]', r'\1', character)
                        character = re.sub(r'\[\[([^\]]+)\]\]', r'\1', character)
                        character = character.split(':')[0].split(',')[0].strip()
                        character = re.sub(r'\([^\)]+\)', '', character).strip()
                        if character and 2 <= len(character) <= 60:
                            if character not in characters:
                                characters.append(character)
                                
        return characters
    except Exception:
        return []

def _resolve_via_umbrella_wikis(titles: List[str], verbose: bool = True) -> Optional[Dict]:
    """Adanmış wikisi olmayan içerikleri kdrama, netflix vb. merkezi umbrella wikilerde arar."""
    umbrella_wikis = ["kdrama", "netflix", "dramas", "television", "series"]
    for title in titles:
        title_clean = title.strip()
        if not title_clean:
            continue
        for wiki in umbrella_wikis:
            # 1. Doğrudan sayfa kontrolü
            url = f"https://{wiki}.fandom.com/api.php"
            params = {
                "action": "query",
                "titles": title_clean,
                "prop": "info",
                "format": "json",
                "formatversion": 2
            }
            try:
                r = requests.get(url, params=params, timeout=8, headers=HEADERS).json()
                pages = r.get("query", {}).get("pages", [])
                if pages and not pages[0].get("missing"):
                    p_title = pages[0].get("title")
                    if verbose:
                        print(f"[Umbrella] Doğrudan sayfa eşleşmesi: '{p_title}' ({wiki}.fandom.com)")
                    chars = _extract_characters_from_umbrella_page(wiki, p_title)
                    if chars:
                        return {
                            "wiki": f"umbrella:{wiki}:{p_title}",
                            "fetched_at": datetime.now(timezone.utc).isoformat(),
                            "terms": {"characters": chars},
                            "metadata": {c: {"aliases": [], "categories": [], "abstract": ""} for c in chars}
                        }
            except Exception:
                pass

            # 2. Arama ve yakın eşleştirme fallback'i
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": title_clean,
                "srlimit": 5,
                "format": "json",
                "formatversion": 2
            }
            try:
                r = requests.get(url, params=search_params, timeout=8, headers=HEADERS).json()
                results = r.get("query", {}).get("search", [])
                for res in results:
                    p_title = res.get("title")
                    if title_clean.lower() in p_title.lower() or p_title.lower() in title_clean.lower():
                        if verbose:
                            print(f"[Umbrella] Arama sonucu yakın eşleşme: '{p_title}' ({wiki}.fandom.com)")
                        chars = _extract_characters_from_umbrella_page(wiki, p_title)
                        if chars:
                            return {
                                "wiki": f"umbrella:{wiki}:{p_title}",
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "terms": {"characters": chars},
                                "metadata": {c: {"aliases": [], "categories": [], "abstract": ""} for c in chars}
                            }
            except Exception:
                pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
# 4. ANA API
# ─────────────────────────────────────────────────────────────────────────────

def build_glossary(
    anime_title: str,
    force_refresh: bool = False,
    verbose: bool = True,
    season_num: int = None,
    metadata_chars: list = None,   # TVMaze/TMDB'den gelen karakter listesi (fallback)
    media_type: str = 'auto',      # 'anime' | 'series' | 'movie' | 'unknown' | 'auto'
) -> Optional[Dict]:
    """
    Anime serisi için sözlük oluşturur / cache'den döndürür (v2 stable ID cache).
    """
    details = resolve_media_details(anime_title, media_type=media_type, verbose=verbose)
    title_clean = details['titles'][0] if details['titles'] else anime_title
    key = _normalize_title(title_clean)

    # 0. Manuel override denetimi
    slug = None
    overrides = _load_overrides()
    if key in overrides:
        slug = overrides[key]
    else:
        for source_name, id_val in (('anilist', details['anilist_id']), ('mal', details['mal_id']), ('tmdb', details['tmdb_id'])):
            if id_val:
                okey = f"{source_name}:{id_val}"
                if okey in overrides:
                    slug = overrides[okey]
                    break

    # 1. Stable cache key belirleme
    if details.get('anilist_id'):
        stable_key = f"anilist:{details['anilist_id']}"
    elif details.get('tmdb_id'):
        stable_key = f"tmdb:{details['tmdb_id']}"
    elif details.get('mal_id'):
        stable_key = f"mal:{details['mal_id']}"
    else:
        stable_key = f"title:{key}"

    if season_num and isinstance(season_num, int) and season_num >= 2:
        stable_key = f"{stable_key}|s{season_num}"

    # 2. Oturum içi in-memory cache
    if not force_refresh and stable_key in _session_cache:
        _cached_entry = _session_cache[stable_key]
        if verbose and _cached_entry:
            _tot = sum(len(v) for v in _cached_entry.get("terms", {}).values())
            print(f"[Glossary] '{anime_title}' (stable_key: '{stable_key}') oturum belleğinden yüklendi ({_tot} terim)")
        return _cached_entry

    cache = _load_cache()

    # 3. Eski cache migrasyonu
    old_key = key
    if season_num and isinstance(season_num, int) and season_num >= 2:
        old_key = f"{old_key}|s{season_num}"
        
    if old_key in cache and stable_key not in cache:
        cache[stable_key] = cache.pop(old_key)
        _save_cache(cache)
        if verbose:
            print(f"[Glossary] Cache key migrasyonu: '{old_key}' -> '{stable_key}'")

    # 4. Cache hit kontrolü
    if stable_key in cache and not force_refresh:
        entry = cache[stable_key]
        if entry.get('wiki') is None and _is_fresh(entry):
            _session_cache[stable_key] = None
            if verbose:
                print(f"[Glossary] '{stable_key}' -> not-found cache (TTL içinde), atlanıyor.")
            return None
        if _is_fresh(entry):
            cached_wiki = entry.get("wiki")
            if not slug or slug.lower() == (cached_wiki or "").lower():
                _session_cache[stable_key] = entry
                if verbose:
                    total = sum(len(v) for v in entry.get("terms", {}).values())
                    print(f"[Glossary] '{stable_key}' kalıcı cache'den yüklendi ({total} terim, wiki: {cached_wiki})")
                return entry

    # 5. Wiki slug bulma veya doğrulama
    if not slug:
        cached_slug = cache.get(stable_key, {}).get("wiki")
        if cached_slug:
            if _verify_wiki_relevance(cached_slug, title_clean, verbose=verbose):
                slug = cached_slug
            else:
                if verbose:
                    print(f"[Glossary] Cache'teki hatalı wiki temizleniyor: {cached_slug}")
                cache.pop(stable_key, None)
                _save_cache(cache)

    if not slug:
        slug = find_wiki_slug(title_clean, media_type=media_type)

    # 6. Fandom cross-wiki fallback
    if not slug and media_type in ('anime', 'auto', 'unknown'):
        try:
            _dub_r = requests.get(
                "https://dubbing.fandom.com/api/v1/Search/List",
                params={"query": anime_title, "limit": 3, "namespaces": "0"},
                timeout=8, headers=HEADERS,
            )
            if _dub_r.status_code == 200:
                _dub_items = _dub_r.json().get("items", [])
                _ck2 = {w for w in re.sub(r'[^a-z0-9 ]', '', (anime_title or key).lower()).split()
                        if len(w) >= 4}
                for _di in _dub_items:
                    _dtitle = _di.get("title", "").lower()
                    _doverlap = {w for w in _ck2 if w in _dtitle}
                    if _doverlap or any(w in _dtitle for w in _ck2):
                        if verbose:
                            print(f"[Glossary] Fandom cross-wiki bulundu: dubbing.fandom.com/wiki/{_di.get('title', '')}")
                        slug = 'dubbing'
                        break
        except Exception:
            pass

    if not slug:
        # 6.2. Umbrella wikis (merkezi k-drama, netflix vb. wiki) fallback'i
        umbrella_entry = _resolve_via_umbrella_wikis(details.get('titles', [title_clean]), verbose=verbose)
        if umbrella_entry:
            cache[stable_key] = umbrella_entry
            _save_cache(cache)
            _session_cache[stable_key] = umbrella_entry
            return umbrella_entry

    if not slug:
        if verbose:
            print(f"[Glossary] '{anime_title}' için Fandom wiki bulunamadı — atlanıyor.")
        if metadata_chars:
            _chars_clean = [c.strip() for c in metadata_chars if c and c.strip()]
            if _chars_clean:
                _fb_entry = {
                    "wiki":       None,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "terms":      {"characters": _chars_clean},
                }
                cache[stable_key] = _fb_entry
                _save_cache(cache)
                _session_cache[stable_key] = _fb_entry
                return _fb_entry
        cache[stable_key] = {"wiki": None, "fetched_at": datetime.now(timezone.utc).isoformat(), "terms": {}}
        _save_cache(cache)
        _session_cache[stable_key] = None
        return None

    # 6.5. Franchise-level cache: Aynı wiki slug'ına sahip başka bir key cache'te var mı?
    if not force_refresh:
        for k, cached_entry in cache.items():
            if cached_entry and cached_entry.get("wiki") == slug and cached_entry.get("terms"):
                if verbose:
                    print(f"[Glossary] '{stable_key}' için mevcut '{slug}' wikisi önbellekten kopyalanarak yeniden kullanıldı (franchise).")
                entry = dict(cached_entry)
                cache[stable_key] = entry
                _save_cache(cache)
                _session_cache[stable_key] = entry
                return entry

    # 7. Slug bulundu → kategorileri çek ve canonicalize et
    if verbose:
        print(f"[Glossary] '{stable_key}' wiki bulundu: {slug}.fandom.com → kategoriler çekiliyor...")

    terms, metadata = _fetch_all_terms(slug)
    total = sum(len(v) for v in terms.values())
    if verbose:
        print(f"[Glossary] '{stable_key}' → {total} terim çekildi (wiki: {slug})")

    entry = {
        "wiki":       slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "terms":      terms,
        "metadata":   metadata,
    }
    cache[stable_key] = entry
    _save_cache(cache)
    _session_cache[stable_key] = entry
    return entry


def get_prompt_terms(
    anime_title: str,
    media_type: str = 'auto',
    known_type: str = None,
    season_num: int = None,
    season_title: str = None,   # "Sword Art Online: Alicization" gibi sezona özel başlık
    metadata_chars: list = None,  # TVMaze/TMDB karakterleri (Fandom bulamazsa fallback)
) -> dict:
    """
    Gemini'ye gidecek olan filtrelenmiş terim sözlüğünü döndürür.
    Returns: {"characters": [...], "skills": [...], ...}

    Karakter kaynağı: Jikan API (sezon-spesifik, temiz).
    Jikan başarısız olursa Fandom karakterleri kullanılır (fallback).
    Lokasyon/skill/terminology/org → her zaman Fandom'dan gelir.
    """
    # media_type → build_glossary'e ilet (doğru API seçimi için)
    _resolved_type = known_type or media_type or 'auto'
    entry = build_glossary(anime_title, verbose=False, season_num=season_num,
                           metadata_chars=metadata_chars, media_type=_resolved_type)
    terms = entry.get("terms", {}) if entry else {}


    # Arc filtresi kaldırıldı (hardcoded SAO/AoT/Naruto tablosu evrensel değildi).
    # Karakterler → Jikan (sezon-spesifik, evrensel).
    # Lokasyon/terminology/skill/org → Fandom (tüm animeler için filtresiz).


    # ── Karakter Bazlı Sezon Filtresi: Jikan API (Evrensel) ────────────────────
    # Fandom wiki tüm sezonu tek listede tutar → kirlenme olur.
    # Çözüm: Jikan/MAL'da her sezon ayrı entry → o sezondaki karakterleri çek,
    # Fandom listesini bu set ile filtrele.
    # season_title → media_identifier'dan gelir ("SAO: Alicization" gibi).
    _jikan_chars_applied = False
    # Jikan sadece anime icin! Bati dizilerinde (media_type/known_type='series') atla
    _is_western_series = (known_type == 'series' or media_type == 'series')
    if season_num and isinstance(season_num, int) and terms.get('characters') and not _is_western_series:
        # Jikan'dan bu sezondaki karakterleri çek
        # season_title: fonksiyon parametresinden gelir ("Sword Art Online: Alicization")
        # Yoksa anime_title ile dene (fallback)
        _jikan_query  = season_title or anime_title
        _jikan_series = anime_title if season_title else None

        _jikan_chars = _jikan_get_characters(
            season_title=_jikan_query,
            series_title=_jikan_series,
        )

        if _jikan_chars:
            # Jikan set'i → Fandom karakterlerini bu set ile filtrele
            _jikan_set = {c.lower() for c in _jikan_chars}
            # Tam eşleşme veya Jikan adı Fandom adının alt kümesi ise kabul et
            filtered_chars = []
            for _char in terms['characters']:
                _cl = _char.lower()
                # Tam eşleşme
                if _cl in _jikan_set:
                    filtered_chars.append(_char); continue
                # Kısmi eşleşme: Jikan adı Fandom adında geçiyor mu? (tam sözcük)
                if any(_jn in _cl or _cl in _jn for _jn in _jikan_set if len(_jn) > 3):
                    filtered_chars.append(_char); continue
            _removed = len(terms['characters']) - len(filtered_chars)
            if _removed > 0:
                print(f"[Glossary] Jikan filtresi: {_removed} yabancı karakter atıldı "
                      f"({len(filtered_chars)} karakter kaldı)")
            terms['characters'] = filtered_chars
            _jikan_chars_applied = True
        else:
            # Jikan yoksa / hata → Fandom'un mevcut listesini koru (arc filtresi zaten var)
            if season_num:
                print(f"[Glossary] Jikan bulunamadı — Fandom karakter listesi kullanılıyor (kirlenme riski)")
    # ─────────────────────────────────────────────────────────────────────────


    # ── Fandom wiki kalite kapısı ──────────────────────────────────────────────
    # Eğer bilinen tür TVSERIES veya MOVIE ise ve Fandom'dan < 3 karakter geldiyse,
    # wiki yanlış slug'a gitmiş demektir → organization/location/items verileri atılır.
    _fandom_char_count = len(terms.get('characters', []))
    _known_is_show = (known_type or '').upper() in ('TVSERIES', 'MOVIE', 'TV')
    _fandom_trusted = not _known_is_show or _fandom_char_count >= 3
    if not _fandom_trusted:
        # Sadece karakter listesini koru, diğer kategoriler büyük ihtimalle yanlış wikiden
        terms = {'characters': terms.get('characters', [])}

    _LIMITS = {
        "characters":     30,
        "organizations":  20,
        "skills":         25,
        "locations":      20,
        "items":          15,
        "terminology":    15,
    }
    # Kötü organizasyon verisi filtresi: gerçek hayat şirket/borsa/finans isimleri
    _NOISE_PATTERNS = (
        'exchange', 'plc', 'ltd', 'inc', 'corp', 'llc', 'gmbh', 'a.s.',
        'order book', 'dark pool', 'clsa', 'aquis', 'kick at', '- dark',
        'equities', 'securities', 'capital', ' ag ', ' sa ', ' nv ',
    )

    def _is_noisy(term: str) -> bool:
        t = term.lower()
        return any(p in t for p in _NOISE_PATTERNS)

    result = {}
    for key, limit in _LIMITS.items():
        lst = terms.get(key, [])
        if lst:
            if key == "characters":
                # Tam isim (2+ kelime) olanlar once, sonra tek kelimeli
                full  = [c for c in lst if ' ' in c.strip()]
                short = [c for c in lst if ' ' not in c.strip()]
                result[key] = (full + short)[:limit]
            else:
                # Gürültülü (finans/şirket) verileri filtrele
                clean = [t for t in lst if not _is_noisy(t)]
                result[key] = sorted(clean, key=len)[:limit] if clean else []
                if not result[key]:
                    del result[key]

    # ── 2. Franchise-specific API (PotterDB / SWAPI) — Fandom'u override eder ─
    try:
        import offline_db_manager as _odb
        franchise = _odb.fetch_franchise_terms(anime_title)
        if franchise:
            for key in _LIMITS:
                fvals = franchise.get(key, [])
                if not fvals:
                    continue
                existing = result.get(key, [])
                if not existing:
                    result[key] = fvals[:_LIMITS[key]]
                else:
                    # Franchise API verileri ONCELIKLI — Fandom'dan gelen geri kalanlari ekle
                    existing_set = {v.lower() for v in fvals}
                    fandom_rest = [v for v in existing if v.lower() not in existing_set]
                    result[key] = (fvals + fandom_rest)[:_LIMITS[key]]
    except Exception:
        pass


    # ── 3. TVmaze lazy-load: Ana karakterleri one al, Fandom wiki ile tamamla ──
    try:
        import offline_db_manager as _odb
        tv_chars = _odb.fetch_tvmaze_characters(anime_title)
        if tv_chars:
            existing = result.get("characters", [])
            existing_low = {c.lower() for c in tv_chars}
            # TVmaze ana karakterleri one, Fandom artiklari arkaya
            fandom_rest = [c for c in existing if c.lower() not in existing_low]
            result["characters"] = (tv_chars + fandom_rest)[:30]
    except Exception:
        pass

    # ── 4. AniDB lazy-load: anime için karakter yoksa ─────────────────────────
    if not result.get("characters"):
        try:
            import offline_db_manager as _odb
            anidb_chars = _odb.get_characters_for_title(anime_title, media_type='anime')
            if anidb_chars:
                result["characters"] = anidb_chars[:30]
        except Exception:
            pass

    # ── 4b. TMDB Cast: film/dizi için karakter yoksa veya azsa ─────────────────
    # Anime için: TMDB anime bilmez → atla
    # Film/Dizi için: Fandom yoksa veya < 5 karakter → TMDB dene
    _is_movie_or_tv = (known_type or media_type or '').upper() in (
        'MOVIE', 'FILM', 'TVSERIES', 'TV', 'SERIES'
    )
    _tmdb_needed = _is_movie_or_tv and len(result.get("characters", [])) < 5
    if _tmdb_needed:
        try:
            import offline_db_manager as _odb
            # media_type eşleştir
            _tmdb_mtype = (
                'movie' if (known_type or media_type or '').upper() in ('MOVIE', 'FILM')
                else 'tv'
            )
            _tmdb_chars = _odb.fetch_tmdb_cast(
                anime_title,
                media_type=_tmdb_mtype,
                season_num=season_num,
                verbose=True,
            )
            if _tmdb_chars:
                existing    = result.get("characters", [])
                existing_lw = {c.lower() for c in existing}
                new_chars   = [c for c in _tmdb_chars if c.lower() not in existing_lw]
                result["characters"] = (existing + new_chars)[:30]
                print(f"[Glossary] TMDB: {len(_tmdb_chars)} karakter yüklendi "
                      f"({_tmdb_mtype}, sezon={season_num or 'tümü'})")
        except Exception:
            pass

    # ── 5. Wikidata entity seti: eksik lokasyon/esya/org'ları enjekte et ─────
    # SADECE anime veya unknown için (TVSERIES/MOVIE için Wikidata org/loc genelde yanlış)
    _skip_wikidata_entities = (known_type or '').upper() in ('TVSERIES', 'MOVIE', 'TV', 'SERIES')
    if not _skip_wikidata_entities:
        try:
            import offline_db_manager as _odb
            entity_set = _odb.get_wikidata_entity_set()
            if entity_set:
                title_words = [w for w in anime_title.lower().split() if len(w) > 3]
                for key in ("locations", "items", "organizations"):
                    if not result.get(key) and entity_set and title_words:
                        matches = [
                            e for e in entity_set
                            if len(e) > 4
                            and sum(1 for w in title_words if w in e.lower()) >= min(2, len(title_words))
                            and not _is_noisy(e)
                        ]
                        if matches:
                            result[key] = matches[:_LIMITS.get(key, 15)]
        except Exception:
            pass

    # ── 5b. Wikidata P31 TÜR FİLTRELİ arama ────────────────────────────────────────────
    _need_wikidata_lookup = (
        not result.get("characters") or len(result.get("characters", [])) < 3
    )
    if _need_wikidata_lookup:
        try:
            import offline_db_manager as _odb
            _kt = (known_type or media_type or '').upper().strip()
            _wikidata_mt = (
                'anime'  if _kt in ('ANIME',)              else
                'series' if _kt in ('SERIES','TVSERIES','TV') else
                'movie'  if _kt in ('MOVIE','FILM')        else
                media_type if media_type != 'auto' else 'unknown'
            )
            _wd = _odb.lookup_wikidata_by_title(anime_title, media_type=_wikidata_mt)
            if _wd and _wd.get("found"):
                wd_chars = _wd.get("characters", [])
                if wd_chars:
                    existing   = result.get("characters", [])
                    exist_low  = {c.lower() for c in wd_chars}
                    fandom_rest = [c for c in existing if c.lower() not in exist_low]
                    result["characters"] = (wd_chars + fandom_rest)[:30]
                wd_locs = _wd.get("locations", [])
                if wd_locs and not result.get("locations"):
                    result["locations"] = wd_locs[:20]
        except Exception:
            pass

    # ── 6. Wikidata karakter seti fallback ────────────────────────────────────
    existing_chars = set(c.lower() for c in result.get("characters", []))
    if len(existing_chars) < 10:
        try:
            import offline_db_manager as _odb
            wiki_set = _odb.get_wikidata_char_set()
            wiki_matches = [
                c for c in wiki_set
                if len(c) > 2 and c.lower() not in existing_chars
                and any(part in c.lower() for part in anime_title.lower().split()[:3])
            ]
            if wiki_matches:
                current = result.get("characters", [])
                result["characters"] = (current + wiki_matches[:10])[:30]
        except Exception:
            pass

    return result





def get_prompt_injection(
    anime_title: str,
    media_type: str = 'auto',
    known_type: str = None,
    season_num: int = None,
    season_title: str = None,   # "SAO: Alicization" gibi sezona özel başlık
) -> str:
    """
    Terminoloji blogunu referans formatinda dondurur.
    Kategoriye göre net kurallar:
      - Characters / invented words → ASLA çevirme
      - Organizations / Skills / Locations / Items → açıklayıcı İngilizce kelimeler Türkçeye çevrilebilir
    """
    filtered = get_prompt_terms(
        anime_title,
        media_type=media_type,
        known_type=known_type,
        season_num=season_num,
        season_title=season_title,
    )
    if not filtered:
        return ""

    if not any(filtered.get(k) for k in (
        'characters', 'organizations', 'skills', 'locations', 'items', 'terminology'
    )):
        return ""

    title_line = f"SERIES REFERENCE \u2014 {anime_title}"
    rule_line = "Translate all of the following terms into Turkish."

    out = [title_line, rule_line]

    # NOT: 'characters' burada YOK — zaten media context'te CHARACTERS: satırı var.
    # "Translate all" kuralı karakter isimlerine de uygulanmasın diye kasıtlı çıkarıldı.
    _CAT_CONFIG = [
        ('organizations', 'Groups/Organizations'),
        ('skills',        'Skills/Abilities'),
        ('locations',     'Locations'),
        ('items',         'Items/Weapons'),
        ('terminology',   'Special Terms/Story Arcs'),
    ]
    # NOT: Eski _MAX_INJECT_PER_CAT=35 ve _MAX_GLOSSARY_CHARS=1800 kısıtlamaları
    # KALDIRILDI — PATF (glossary_prescanner.py) artık tüm boyut kontrolünü yapıyor.
    # Bu fonksiyon artık sadece fallback / rapor amaçlı çağrılır.

    for key, label in _CAT_CONFIG:
        lst = filtered.get(key, [])
        if lst:
            out.append("  " + label + ": " + ", ".join(lst))

    if len(out) <= 2:
        return ""

    return "\n".join(out)


def get_merged_injection(
    anime_title: str,
    media_type: str = 'auto',
    known_type: str = None,
    season_num: int = None,
    season_title: str = None,
) -> str:
    """
    Fandom wiki terimleri + series_glossary.json MANUEL girisleri birlestirir.
    media_type: 'anime'|'series'|'movie'|'auto'
    season_title: "SAO: Alicization" gibi sezona ozel baslik — Jikan aramasinda kullanilir.
    """
    base = get_prompt_injection(
        anime_title,
        media_type=media_type,
        known_type=known_type,
        season_num=season_num,
        season_title=season_title,
    )
    manual_keep: list = []
    manual_tr: dict = {}
    try:
        path = _glossary_path()
        if os.path.isfile(path):
            data = json.load(open(path, "r", encoding="utf-8"))
            tn = _normalize_title(anime_title)
            entry = None
            for k, v in data.items():
                if _normalize_title(k) == tn:
                    entry = v
                    break
            if not entry:
                for k, v in data.items():
                    kn = _normalize_title(k)
                    if kn in tn or tn in kn:
                        entry = v
                        break
            if entry:
                manual_keep = entry.get("keep", [])
                manual_tr   = entry.get("translate", {})
    except Exception:
        pass
    extras = []
    if manual_keep:
        joined = ", ".join(manual_keep)
        extras.append("MANUAL — NEVER translate: " + joined)
    if manual_tr:
        for term, tr in manual_tr.items():
            extras.append("MANUAL — " + repr(term) + " → " + repr(tr))
    if not base and not extras:
        return ""
    parts = []
    if base:
        parts.append(base)
    if extras:
        parts.append("\n".join(extras))
    return "\n".join(parts)


def list_cached_series() -> None:
    """Cache'teki tüm serileri listeler."""
    cache = _load_cache()
    if not cache:
        print("[Glossary] Cache boş.")
        return
    print(f"[Glossary] Cache'te {len(cache)} seri:")
    for title, entry in cache.items():
        wiki  = entry.get("wiki", "—")
        total = sum(len(v) for v in entry.get("terms", {}).values())
        age   = "?" 
        try:
            fetched = datetime.fromisoformat(entry["fetched_at"])
            age = f"{(datetime.now(timezone.utc) - fetched).days}g önce"
        except Exception:
            pass
        print(f"  · {title:<40} wiki:{wiki:<25} {total:>4} terim  [{age}]")


def delete_cached_series(anime_title: str) -> None:
    """Belirli bir serinin cache kaydını siler (yeniden çekilmesini zorlar)."""
    cache = _load_cache()
    if anime_title in cache:
        del cache[anime_title]
        _save_cache(cache)
        print(f"[Glossary] '{anime_title}' cache'den silindi.")
    else:
        print(f"[Glossary] '{anime_title}' cache'de bulunamadı.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="Fandom Wiki sözlük çekici / güncelleyici"
    )
    parser.add_argument("--wiki",   help="Doğrudan wiki slug (örn: oshinoko)")
    parser.add_argument("--title",  help="Anime adı — slug otomatik bulunur")
    parser.add_argument("--force",  action="store_true",
                        help="TTL görmezden gel, her zaman yeniden çek")
    parser.add_argument("--merge",  action="store_true",
                        help="Çekilen yeni terimleri mevcut kayda EKLE (üstüne yazma)")
    # Geriye uyumluluk: argümansız eski kullanım → başlık pozisyonel
    parser.add_argument("title_pos", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Başlığı belirle
    if args.wiki:
        # Slug verildi → slug'dan build_glossary çağır ama önce cache key normalize
        # Önce mevcut cache'te bu slug var mı bak
        _slug = args.wiki.lower().replace(" ", "")
        _cache = _load_cache()

        # Mevcut kayıt — merge için
        _existing_entry = None
        _existing_key   = None
        for _k, _v in _cache.items():
            # None veya dict olmayan entry'leri atla (bozuk cache kaydı)
            if not isinstance(_v, dict):
                continue
            if (_v.get("wiki") or "").lower().replace(" ", "") == _slug:
                _existing_entry = _v
                _existing_key   = _k
                break

        if _existing_entry and not args.force and not args.merge:
            # Zaten var, force/merge değil → bilgi ver, çıkma
            _tot = sum(len(v) for v in _existing_entry.get("terms", {}).values())
            print(f"[Glossary] '{_slug}' zaten mevcut ({_tot} terim, "
                  f"tarih: {_existing_entry.get('fetched_at','?')[:10]}). "
                  f"Güncellemek için --force veya --merge kullanın.")
            sys.exit(0)

        print(f"\n{'='*60}")
        print(f"{'GÜNCELLİYOR' if (_existing_entry and args.merge) else 'ÇEKİYOR'}: "
              f"wiki={_slug}" + (" [MERGE]" if args.merge else "") + (" [FORCE]" if args.force else ""))
        print(f"{'='*60}\n")

        # Direkt slug ile çek — slug'ı slug candidate olarak kullanmak için
        # _fetch_all_terms slug'ı direkt alır
        _new_terms, _new_metadata = _fetch_all_terms(_slug)
        _tot_new   = sum(len(v) for v in _new_terms.values())
        print(f"  Çekilen: {_tot_new} yeni terim")

        if args.merge and _existing_entry:
            # Merge: eski terimlerle yeni terimleri birleştir (union), sorted listele
            _old_terms = _existing_entry.get("terms", {})
            _old_metadata = _existing_entry.get("metadata", {})
            _merged = {}
            all_cats = set(list(_old_terms.keys()) + list(_new_terms.keys()))
            _added_count = 0
            for _cat in all_cats:
                _old_set = set(_old_terms.get(_cat, []))
                _new_set = set(_new_terms.get(_cat, []))
                _added_count += len(_new_set - _old_set)
                _merged[_cat] = sorted(_old_set | _new_set)
            _tot_merged = sum(len(v) for v in _merged.values())
            print(f"  Merge sonucu: {_tot_merged} terim ({_added_count} yeni eklendi)")

            # Merge metadata
            _merged_metadata = dict(_old_metadata)
            _merged_metadata.update(_new_metadata)

            _new_entry = {
                "wiki":       _slug,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "terms":      _merged,
                "metadata":   _merged_metadata,
            }
        else:
            _new_entry = {
                "wiki":       _slug,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "terms":      _new_terms,
                "metadata":   _new_metadata,
            }

        # Cache'e kaydet — var olan key'i güncelle, yoksa slug adıyla ekle
        _save_key = _existing_key if _existing_key else _slug
        _cache[_save_key] = _new_entry
        _save_cache(_cache)
        _tot_saved = sum(len(v) for v in _new_entry['terms'].values())
        print(f"\n[OK] '{_save_key}' guncellendi -> {_tot_saved} terim kaydedildi.")


    else:
        # --title veya pozisyonel argüman
        _title_parts = []
        if args.title:
            _title_parts = [args.title]
        elif args.title_pos:
            _title_parts = args.title_pos
        title = " ".join(_title_parts) if _title_parts else "Sword Art Online"

        print(f"\n{'='*60}")
        print(f"TEST: {title}" + (" [FORCE]" if args.force else ""))
        print(f"{'='*60}\n")

        entry = build_glossary(title, force_refresh=args.force, verbose=True)

        if entry:
            print(f"\n{'─'*60}")
            print("PROMPT INJECTION PREVIEW:")
            print(f"{'─'*60}")
            print(get_prompt_injection(title))
        else:
            print("Glossary oluşturulamadı.")

