"""
glossary/store.py
=================
Sözlük cache load/save ve freshness kontrolü.
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
