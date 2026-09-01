"""
glossary/characters.py
======================
Jikan ve AniList karakter listesi çekme.
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

