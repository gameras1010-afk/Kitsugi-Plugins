"""
media_id/apis.py
================
API sorguları: Jikan, AniList, Kitsu, TVmaze, TMDB.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional
from media_id.constants import *

def _safe_get(url: str, **kwargs) -> dict | None:
    """GET isteği yap, hata olursa None döner."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def _safe_post(url: str, **kwargs) -> dict | None:
    """POST isteği yap, hata olursa None döner."""
    try:
        r = requests.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ── 5a. Jikan v4 (MAL) ──────────────────────────────────────

def _query_jikan(title: str) -> dict | None:
    """Jikan v4 API ile anime ara (Official MAL API fallback'i ile)."""
    _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
    
    def _query_official_mal_api(q_str: str) -> list | None:
        client_id = "9dfa9b926eecef62128b6d464c7e33b9"
        url = "https://api.myanimelist.net/v2/anime"
        headers = {
            "X-MAL-CLIENT-ID": client_id,
            "User-Agent": "KitsugiAnimeList/1.0"
        }
        params = {
            "q": q_str,
            "limit": 5,
            "fields": "id,title,alternative_titles,start_date,mean,num_episodes,media_type,genres,nsfw,synopsis"
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                results = []
                for item in data.get("data", []):
                    node = item.get("node", {})
                    genres_mapped = [{"name": g.get("name")} for g in node.get("genres", [])]
                    
                    aired_year = None
                    start_date = node.get("start_date")
                    if start_date and len(start_date) >= 4:
                        try:
                            aired_year = int(start_date[:4])
                        except ValueError:
                            pass
                    
                    alt = node.get("alternative_titles") or {}
                    titles_mapped = [{"type": "Default", "title": node.get("title")}]
                    if alt.get("en"):
                        titles_mapped.append({"type": "English", "title": alt.get("en")})
                    if alt.get("ja"):
                        titles_mapped.append({"type": "Japanese", "title": alt.get("ja")})
                    synonyms = alt.get("synonyms") or []
                    for syn in synonyms:
                        titles_mapped.append({"type": "Synonym", "title": syn})
                    
                    results.append({
                        "mal_id": node.get("id"),
                        "title": node.get("title"),
                        "title_english": alt.get("en") or node.get("title"),
                        "title_japanese": alt.get("ja") or "",
                        "titles": titles_mapped,
                        "type": (node.get("media_type") or "TV").upper(),
                        "episodes": node.get("num_episodes"),
                        "score": node.get("mean"),
                        "synopsis": node.get("synopsis"),
                        "genres": genres_mapped,
                        "themes": [],
                        "status": node.get("status") or "",
                        "aired": {"prop": {"from": {"year": aired_year}}}
                    })
                return results
        except Exception:
            pass
        return None

    words = title.split()
    # Kelime kelime azaltarak dene
    for i in range(len(words), 0, -1):
        q = " ".join(words[:i])
        url = f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(q)}&limit=5"
        data = _safe_get(url)
        
        candidates = None
        if data and data.get("data"):
            candidates = data["data"]
        else:
            candidates = _query_official_mal_api(q)
            
        if candidates:
            # Jikan zaten alaka sirasina gore siraliyor.
            # Sadece eksik veriyi (score=None VE episodes=None) filtrele — geri kalanlarin ilkini al.
            valid = [c for c in candidates
                     if c.get("score") is not None or c.get("episodes") is not None]

            # [FIX] Kelime ortusumu dogrulamasi: donulen animenin basligi
            # sorgunun onemli kelimeleriyle ortusmuyor mu? → reddet.
            # Ornek: 'dealing' sorusu → 'ItaKiss' → 'dealing' gecmiyor → RED
            _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                        title.lower()).split()
                        if w not in _STOP_W and len(w) >= 3}
            def _title_ok(entry):
                """Anime basliginin sorgu kelimeleriyle uyumunu kontrol et."""
                if not _q_words:
                    return True  # Kisa sorgu - dogrulama atla
                all_titles = ' '.join([
                    (entry.get('title') or ''),
                    (entry.get('title_english') or ''),
                    (entry.get('title_japanese') or ''),
                ] + [(s.get('title') or '') for s in (entry.get('titles') or [])]).lower()
                all_titles = re.sub(r'[^a-z0-9 ]', '', all_titles)
                overlap = {w for w in _q_words if w in all_titles}
                # Require substantial keyword overlap to prevent false positive matches
                return len(overlap) >= min(len(_q_words), 2)

            # Gecerli adaylardan sadece sorguyla uyumlu olanlar
            valid_ok = [c for c in valid if _title_ok(c)]
            all_ok   = [c for c in candidates if _title_ok(c)]

            if not valid_ok and not all_ok:
                # Bu sorgu uzunlugunda hicbir sonuc uyumlu degil → kisalt
                time.sleep(REQUEST_DELAY)
                continue

            def _get_overlap_score(entry):
                all_titles = ' '.join([
                    (entry.get('title') or ''),
                    (entry.get('title_english') or ''),
                    (entry.get('title_japanese') or ''),
                ] + [(s.get('title') or '') for s in (entry.get('titles') or [])]).lower()
                all_titles = re.sub(r'[^a-z0-9 ]', '', all_titles)
                overlap = {w for w in _q_words if w in all_titles}
                return len(overlap)

            if valid_ok:
                a = max(valid_ok, key=lambda c: (_get_overlap_score(c), -valid.index(c)))
            else:
                a = max(all_ok, key=lambda c: (_get_overlap_score(c), -candidates.index(c)))
            mal_id = a.get("mal_id")


            # Karakterleri çek (ayrı endpoint)
            characters = []
            if mal_id:
                time.sleep(REQUEST_DELAY)
                char_data = _safe_get(
                    f"https://api.jikan.moe/v4/anime/{mal_id}/characters"
                )
                if char_data:
                    for c in (char_data.get("data") or [])[:10]:
                        cname = (c.get("character") or {}).get("name", "")
                        if cname:
                            # "Hoshino, Aqua" → "Aqua Hoshino"
                            parts = [p.strip() for p in cname.split(",")]
                            characters.append(" ".join(reversed(parts)))

            genres = [g.get("name") for g in (a.get("genres") or [])]
            themes = [t.get("name") for t in (a.get("themes") or [])]
            all_genres = list(dict.fromkeys(genres + themes))  # tekrarsız

            # title_english yoksa title kullan; MAL bazen "[Title]" formatinda doner
            _jikan_title_raw = a.get("title_english") or a.get("title") or title
            title_en = re.sub(r"^\[|\]$", "", _clean_title(_jikan_title_raw)).strip()
            title_jp = a.get("title_japanese") or ""
            media_type = a.get("type") or "TV"   # TV, Movie, OVA, ONA…
            episodes  = a.get("episodes") or "?"
            status    = a.get("status") or ""
            synopsis  = (a.get("synopsis") or "")[:600]
            score     = a.get("score")
            year      = (a.get("aired") or {}).get("prop", {}).get("from", {}).get("year")

            return {
                "title":       title_en,
                "title_jp":    title_jp,
                "type":        media_type,
                "episodes":    episodes,
                "status":      status,
                "genres":      all_genres,
                "characters":  characters,
                "synopsis":    synopsis,
                "score":       score,
                "year":        year,
                "source":      "Jikan/MAL",
                "mal_id":      mal_id,
            }
        time.sleep(REQUEST_DELAY)
    return None

# ── 5b. AniList GraphQL ─────────────────────────────────────


def _extract_year_from_filename(filepath: str) -> int | None:
    """Dosya adindan yapim yilini cikarir. Ornek: Ace.Ventura.1994.mkv -> 1994"""
    m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', os.path.basename(filepath))
    return int(m.group(1)) if m else None

_ANILIST_QUERY = """
query ($search: String, $idMal: Int, $id: Int) {
  Media(search: $search, idMal: $idMal, id: $id, type: ANIME) {
    id
    title { romaji english native }
    format
    episodes
    status
    genres
    tags { name }
    description(asHtml: false)
    averageScore
    startDate { year }
    characters(role: MAIN, perPage: 10) {
      nodes { name { full } }
    }
    relations {
      edges {
        relationType
        node { id title { romaji english } startDate { year } format }
      }
    }
  }
}
"""

def _query_anilist(title: str, mal_id: int | None = None, anilist_id: int | None = None) -> dict | None:
    """AniList GraphQL ile anime ara."""
    if anilist_id:
        variables = {"id": anilist_id}
    elif mal_id:
        variables = {"idMal": mal_id}
    else:
        variables = {"search": title}
    data = _safe_post(
        "https://graphql.anilist.co",
        json={"query": _ANILIST_QUERY, "variables": variables}
    )
    if not data:
        return None
    media = (data.get("data") or {}).get("Media")
    if not media:
        return None

    # Validate overlap if we did a search query (not by ID)
    if not anilist_id and not mal_id:
        _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                    'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
        _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                    title.lower()).split()
                    if w not in _STOP_W and len(w) >= 3}
        if _q_words:
            _titles_obj = media.get("title") or {}
            _syns = media.get("synonyms") or []
            _all_titles_str = ' '.join(filter(None, [
                _titles_obj.get("english"),
                _titles_obj.get("romaji"),
                _titles_obj.get("native")
            ] + _syns)).lower()
            _all_titles_str = re.sub(r'[^a-z0-9 ]', '', _all_titles_str)
            _overlap = {w for w in _q_words if w in _all_titles_str}
            if len(_overlap) < min(len(_q_words), 2):
                return None

    titles  = media.get("title") or {}
    title_en = titles.get("english") or titles.get("romaji") or title
    title_jp = titles.get("native") or ""
    genres  = (media.get("genres") or [])[:6]
    tags    = [(t.get("name") or "") for t in (media.get("tags") or [])][:4]
    all_genres = list(dict.fromkeys(genres + tags))
    synopsis   = (media.get("description") or "")[:600]
    chars_raw  = ((media.get("characters") or {}).get("nodes") or [])
    characters = [
        (c.get("name") or {}).get("full", "")
        for c in chars_raw
        if (c.get("name") or {}).get("full")
    ]

    return {
        "title":      title_en,
        "title_jp":   title_jp,
        "type":       media.get("format") or "TV",
        "episodes":   media.get("episodes") or "?",
        "status":     media.get("status") or "",
        "genres":     all_genres,
        "characters": characters,
        "synopsis":   synopsis,
        "score":      media.get("averageScore"),
        "year":       (media.get("startDate") or {}).get("year"),
        "source":     "AniList",
        "_anilist_id": media.get("id"),
        "_sequel_id":  next((
            e["node"]["id"] for e in
            ((media.get("relations") or {}).get("edges") or [])
            if e.get("relationType") == "SEQUEL"
            and (e.get("node") or {}).get("format") in ("TV","TV_SHORT","ONA",None)
        ), None),
    }

# ── 5c. Kitsu ───────────────────────────────────────────────



def _query_anilist_season(title: str, season_num: int) -> dict | None:
    """
    AniList Relations API ile sezon zincirini takip eder.
    Ornek: Oshi no Ko season=3 -> S1 -> SEQUEL -> S2 -> SEQUEL -> S3
    """
    if season_num <= 1:
        return _query_anilist(title)

    base = _query_anilist(title)
    if not base:
        return None

    current_id = base.get("_anilist_id")
    if not current_id:
        return None

    print(f"{Fore.CYAN}   [AniList] Sezon zinciri: S1 (ID:{current_id})...{Style.RESET_ALL}")

    for step in range(1, season_num):
        step_data = _query_anilist(None, anilist_id=current_id)
        if not step_data:
            print(f"{Fore.YELLOW}   [AniList] S{step+1} bulunamadi.{Style.RESET_ALL}")
            return None
        next_id = step_data.get("_sequel_id")
        if not next_id:
            print(f"{Fore.YELLOW}   [AniList] S{step+1} devam yok.{Style.RESET_ALL}")
            return None
        print(f"{Fore.CYAN}   [AniList] S{step+1} ID: {next_id}{Style.RESET_ALL}")
        current_id = next_id
        time.sleep(REQUEST_DELAY)

    result = _query_anilist(None, anilist_id=current_id)
    if result:
        if not result.get("characters") and base.get("characters"):
            result["characters"] = base["characters"]
        print(f"{Fore.GREEN}   [AniList] Sezon {season_num} bulundu!{Style.RESET_ALL}")
    return result

def _query_kitsu(title: str) -> dict | None:
    """Kitsu API ile anime ara."""
    url  = f"https://kitsu.io/api/edge/anime?filter[text]={requests.utils.quote(title)}&page[limit]=1"
    data = _safe_get(url, headers={"Accept": "application/vnd.api+json"})
    if not data or not data.get("data"):
        return None
    a    = data["data"][0].get("attributes", {})
    titles = a.get("titles") or {}
    
    # Check overlap to prevent matching random anime to western series/movies
    _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
    _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                title.lower()).split()
                if w not in _STOP_W and len(w) >= 3}
    if _q_words:
        _syns = a.get("abbreviatedTitles") or []
        _all_titles_str = ' '.join(filter(None, [
            titles.get("en"),
            titles.get("en_us"),
            titles.get("ja_jp"),
            a.get("canonicalTitle")
        ] + _syns)).lower()
        _all_titles_str = re.sub(r'[^a-z0-9 ]', '', _all_titles_str)
        _overlap = {w for w in _q_words if w in _all_titles_str}
        if len(_overlap) < min(len(_q_words), 2):
            return None

    title_en = titles.get("en") or titles.get("en_us") or a.get("canonicalTitle") or title
    title_jp = titles.get("ja_jp") or ""
    genres_raw = a.get("categories", {})  # Kitsu'da kategoriler ayrı endpoint'te
    synopsis   = (a.get("synopsis") or a.get("description") or "")[:600]
    ep_count   = a.get("episodeCount") or "?"
    status     = a.get("status") or ""
    subtype    = a.get("subtype") or "TV"
    year       = (a.get("startDate") or "")[:4] or None

    slug       = data["data"][0].get("id", "")  # Kitsu numeric ID (slug olarak kullanılır)
    # Canonical slug (URL için): attributes.slug varsa o, yoksa numeric id
    kitsu_slug = a.get("slug") or str(slug)
    # Kapak görseli
    poster_imgs = a.get("posterImage") or {}
    kitsu_cover = (poster_imgs.get("large") or poster_imgs.get("medium")
                   or poster_imgs.get("small") or "")

    return {
        "title":        title_en,
        "title_jp":     title_jp,
        "type":         subtype.upper(),
        "episodes":     ep_count,
        "status":       status,
        "genres":       [],
        "characters":   [],
        "synopsis":     synopsis,
        "score":        a.get("averageRating"),
        "year":         int(year) if year and year.isdigit() else None,
        "source":       "Kitsu",
        "_kitsu_slug":  kitsu_slug,
        "_kitsu_cover": kitsu_cover,
        "kitsu_url":    f"https://kitsu.io/anime/{kitsu_slug}" if kitsu_slug else "",
        "cover_url":    kitsu_cover,
    }

# ── 5d. TVMaze ──────────────────────────────────────────────

def _query_tvmaze(title: str) -> dict | None:
    """TVMaze API ile dizi/film ara."""
    url  = f"https://api.tvmaze.com/search/shows?q={requests.utils.quote(title)}"
    data = _safe_get(url)
    if not data or not isinstance(data, list):
        return None
    show = data[0].get("show") if data else None
    if not show:
        return None

    show_id  = show.get("id")
    genres   = show.get("genres") or []
    synopsis = re.sub(r'<[^>]+>', '', show.get("summary") or "")[:600]
    title_en = show.get("name") or title
    # Karakter listesi: /shows/{id}/cast endpoint
    characters = []
    if show_id:
        time.sleep(REQUEST_DELAY)
        cast_data = _safe_get(f"https://api.tvmaze.com/shows/{show_id}/cast")
        if cast_data and isinstance(cast_data, list):
            for c in cast_data[:10]:
                cname = (c.get("character") or {}).get("name", "")
                if not cname:
                    cname = (c.get("person") or {}).get("name", "")
                if cname:
                    characters.append(cname)

    return {
        "title":      title_en,
        "title_jp":   "",
        "type":       show.get("type") or "TV",
        "episodes":   "?",
        "status":     show.get("status") or "",
        "genres":     genres,
        "characters": characters,
        "synopsis":   synopsis,
        "score":      show.get("rating", {}).get("average"),
        "year":       (show.get("premiered") or "")[:4] or None,
        "source":     "TVMaze",
        "network":    (show.get("network") or {}).get("name") or "",
    }

# ── 5e. TMDB ────────────────────────────────────────────────

def _query_tmdb(title: str, api_key: str, year_hint: int = None, media_type: str = 'auto') -> dict | None:
    """The Movie Database (TMDB) ile dizi/film ara. API key gerekli.
    media_type: 'tv' → TV önce ara | 'movie' → Film önce ara | 'auto' → Film önce (eski davranis)
    """
    if not api_key:
        return None

    # TMDB genre_id -> isim tablosu (search endpoint sadece integer ID verir)
    _GENRE_MAP = {
        28:'Action', 12:'Adventure', 16:'Animation', 35:'Comedy', 80:'Crime',
        99:'Documentary', 18:'Drama', 10751:'Family', 14:'Fantasy', 36:'History',
        27:'Horror', 10402:'Music', 9648:'Mystery', 10749:'Romance',
        878:'Science Fiction', 10770:'TV Movie', 53:'Thriller', 10752:'War',
        37:'Western', 10759:'Action & Adventure', 10762:'Action & Adventure',
        10763:'News', 10764:'Reality', 10765:'Sci-Fi & Fantasy',
        10766:'Soap', 10767:'Talk', 10768:'War & Politics',
    }
    def _gids(ids):
        return [_GENRE_MAP[g] for g in (ids or []) if g in _GENRE_MAP]

    result = None

    # media_type'a gore arama sirasi belirle
    # 'tv'  → TV önce, film fallback
    # 'movie' veya 'auto' → Film önce, TV fallback
    _search_tv_first = (media_type == 'tv')
    _yr = f"&year={year_hint}" if year_hint else ""

    def _fetch_movie():
        url = (
            f"https://api.themoviedb.org/3/search/movie"
            f"?api_key={api_key}&query={requests.utils.quote(title)}&language=en-US&page=1{_yr}"
        )
        data = _safe_get(url)
        if not data or not data.get("results"):
            return None
        r = data["results"][0]
        movie_id = r.get("id")
        chars = []
        if movie_id:
            time.sleep(REQUEST_DELAY)
            cr = _safe_get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
                f"?api_key={api_key}&language=en-US"
            )
            if cr:
                _cast = cr.get("cast") or []
                # Anime filmlerde cast.character "(voice)" suffix içerir → karakter adını al
                _is_voice = any('(voice)' in (c.get('character') or '').lower() for c in _cast[:5])
                if _is_voice:
                    chars = [
                        (c.get('character') or '').replace('(voice)', '').replace('(Voice)', '').strip()
                        for c in _cast[:8]
                        if (c.get('character') or '').strip()
                    ]
                else:
                    chars = [c.get("name") for c in _cast[:8] if c.get("name")]
        return {
            "title":      r.get("title") or title,
            "title_jp":   r.get("original_title") if r.get("original_language") == "ja" else "",
            "type":       "Movie",
            "episodes":   1,
            "status":     "Released",
            "genres":     _gids(r.get("genre_ids")),
            "characters": chars,
            "synopsis":   (r.get("overview") or "")[:600],
            "score":      r.get("vote_average"),
            "year":       (r.get("release_date") or "")[:4] or None,
            "source":     "TMDB",
        }

    def _fetch_tv():
        url = (
            f"https://api.themoviedb.org/3/search/tv"
            f"?api_key={api_key}&query={requests.utils.quote(title)}&language=en-US&page=1"
        )
        data = _safe_get(url)
        if not data or not data.get("results"):
            return None
        r = data["results"][0]
        show_id = r.get("id")
        chars = []
        if show_id:
            time.sleep(REQUEST_DELAY)
            cr = _safe_get(
                f"https://api.themoviedb.org/3/tv/{show_id}/credits"
                f"?api_key={api_key}&language=en-US"
            )
            if cr:
                chars = [c.get("name") for c in (cr.get("cast") or [])[:8] if c.get("name")]
        return {
            "title":      r.get("name") or title,
            "title_jp":   r.get("original_name") if r.get("original_language") == "ja" else "",
            "type":       "TV",
            "episodes":   r.get("episode_count") or "?",
            "status":     r.get("status") or "",
            "genres":     _gids(r.get("genre_ids")),
            "characters": chars,
            "synopsis":   (r.get("overview") or "")[:600],
            "score":      r.get("vote_average"),
            "year":       (r.get("first_air_date") or "")[:4] or None,
            "source":     "TMDB",
        }

    if _search_tv_first:
        result = _fetch_tv() or _fetch_movie()
    else:
        result = _fetch_movie() or _fetch_tv()

    return result


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BOLUM 6: YAPAY ZEKA ISTEKLERI
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_AI_CLASSIFY_CACHE = {}
_key_cursor = 0  # Session boyunca hangi key'den devam edilecegi (sirali ilerleme)

