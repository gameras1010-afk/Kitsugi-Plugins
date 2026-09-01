"""
glossary/wiki_api.py
====================
Fandom MediaWiki API yardımcıları:
candidates_from_*, slugify, verify, pick_language_variant, find_wiki_slug.
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
from glossary.models import Candidate, REQUEST_TIMEOUT

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
