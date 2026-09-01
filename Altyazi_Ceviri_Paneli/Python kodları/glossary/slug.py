"""
glossary/slug.py
================
Fandom slug üretme, wiki doğrulama, AI fallback.
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
