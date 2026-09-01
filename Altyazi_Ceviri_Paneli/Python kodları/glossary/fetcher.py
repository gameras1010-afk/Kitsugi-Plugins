"""
glossary/fetcher.py
===================
Wiki sayfa içeriği çekme, term ve kategori sorguları.
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
