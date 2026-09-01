"""
glossary/cache.py
=================
Canonical title önbelleği, blacklist yönetimi, title normalizasyonu.
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

try:
    import ass_vendor_setup
except ImportError:
    pass
from glossary.models import (
    REQUEST_TIMEOUT, MAX_TERMS_PER_CAT, MAX_PROMPT_TERMS,
    CACHE_TTL_DAYS, NOT_FOUND_TTL_DAYS, _glossary_path,
    _session_cache, _CANONICAL_TITLE_CACHE,
)

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

