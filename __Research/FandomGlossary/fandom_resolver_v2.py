# -*- coding: utf-8 -*-
"""
Fandom Glossary v2 — Referans Resolver
=======================================
RAPOR.md'deki 4 katmanlı mimarinin çalışır iskeleti (stdlib-only).

K1: ID zenginleştirme + Wikidata QID ters araması (haswbstatement)
K2: Aday üretimi (Wikidata P4073/P6262 + traversal, Fandom unified-search, AI fallback hook)
K3: Hakemli doğrulama (blocklist, sitename fuzzy, karakter-problama, hub uyumu, skor eşiği)
K4: Terim çekme (cmnamespace=0&cmtype=page) + redirect canonicalization + dedupe

Tüm endpoint'ler 2026-08-28'de canlı doğrulandı. Notlar:
  * arm.haglund.dev artık `wikidata` alanı DÖNMÜYOR (include=wikidata -> 500).
  * unified-search resmi dokümante değildir; UA başlığı gönder, hata durumunda K2a/K2c'ye düş.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from difflib import SequenceMatcher

UA = {"User-Agent": "KitsugiGlossary/2.0 (fansub tooling; contact: github.com/gameras1010-afk)"}

# ----------------------------------------------------------------------------
# Ortak HTTP yardımcıları
# ----------------------------------------------------------------------------

def _get_json(url: str, timeout: int = 15) -> dict | list | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _norm(s: str) -> str:
    """casefold + aksansız + noktalama/boşluksuz normalize (dedupe & fuzzy anahtarı)."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", "", s).casefold()


def _fuzzy(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


# ----------------------------------------------------------------------------
# K1 — Kimlik Çözümleme
# ----------------------------------------------------------------------------

# Wikidata external-id property'leri (öncelik sırasıyla denenir)
WD_ID_PROPS = [
    ("anilist", "P8729"),
    ("myanimelist", "P4086"),
    ("themoviedb_tv", "P4983"),
    ("themoviedb_movie", "P4947"),
    ("imdb", "P345"),
]


def enrich_ids(source: str, media_id: str | int) -> dict:
    """animeapi.my.id ile tüm platform ID'lerini topla (ARM'dan daha zengin).
    source: myanimelist | anilist | kitsu | anidb | animeplanet | ...
    """
    data = _get_json(f"https://animeapi.my.id/{source}/{media_id}")
    if isinstance(data, dict):
        return data
    # Yedek: ARM v2 (wikidata isteme! -> 500)
    data = _get_json(
        f"https://arm.haglund.dev/api/v2/ids?source={source}&id={media_id}"
    )
    return data if isinstance(data, dict) else {}


def find_wikidata_qid(ids: dict) -> str | None:
    """haswbstatement ters araması: SPARQL'siz, tek GET ile ID -> QID."""
    for key, prop in WD_ID_PROPS:
        raw = ids.get(key.replace("_tv", "").replace("_movie", ""))
        if key.startswith("themoviedb"):
            raw = ids.get("themoviedb")
        if not raw:
            continue
        q = urllib.parse.quote(f"haswbstatement:{prop}={raw}")
        data = _get_json(
            "https://www.wikidata.org/w/api.php?action=query&list=search"
            f"&srsearch={q}&format=json&formatversion=2"
        )
        try:
            hits = data["query"]["search"]
            if hits:
                return hits[0]["title"]  # ör. "Q89195494"
        except (KeyError, TypeError):
            pass
    return None


# ----------------------------------------------------------------------------
# K2 — Aday üretimi
# ----------------------------------------------------------------------------

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


_TRAVERSAL = "wdt:P144|wdt:P179|wdt:P361|wdt:P8345|wdt:P4969|^wdt:P4969|^wdt:P144"

def _parse_fandom_id(value: str) -> tuple[str, str]:
    """P4073/P6262 değerini (slug, lang) olarak çöz.
    'frieren' -> ('frieren', '') ; 'es.sherlockholmes:James' -> ('sherlockholmes', 'es')
    """
    value = value.split(":", 1)[0]  # P6262 -> subdomain kısmı
    if "." in value:
        lang, slug = value.split(".", 1)
        if len(lang) <= 7:  # bcp47 kısa kod varsayımı
            return slug, ("" if lang == "en" else lang)
    return value, ""


def candidates_from_wikidata(qid: str) -> list[Candidate]:
    """Direkt P4073/P6262 + 2 seviye ilişki traversal'ı (tek SPARQL)."""
    query = f"""
    SELECT DISTINCT ?fandom ?article WHERE {{
      BIND(wd:{qid} AS ?item)
      ?item (({_TRAVERSAL})?)/(({_TRAVERSAL})?) ?related .
      OPTIONAL {{ ?related wdt:P4073 ?fandom }}
      OPTIONAL {{ ?related wdt:P6262 ?article }}
      FILTER(BOUND(?fandom) || BOUND(?article))
    }} LIMIT 20"""
    url = ("https://query.wikidata.org/sparql?format=json&query="
           + urllib.parse.quote(query))
    data = _get_json(url, timeout=30)
    out: dict[str, Candidate] = {}
    try:
        for b in data["results"]["bindings"]:
            for key, score in (("fandom", 0.95), ("article", 0.90)):
                if key in b:
                    slug, lang = _parse_fandom_id(b[key]["value"])
                    c = out.setdefault(slug, Candidate(slug, lang, score, "wikidata"))
                    c.base_score = max(c.base_score, score)
    except (KeyError, TypeError):
        pass
    return list(out.values())


def candidates_from_fandom_search(titles: list[str], media_hub: str,
                                  limit: int = 8) -> list[Candidate]:
    """Fandom resmi unified-search — AI slug tahmininin yerini alan ana yol.
    titles: ana başlık + synonym'ler (romaji, İngilizce...). Her biri ayrı sorgu.
    """
    seen: dict[str, Candidate] = {}
    votes: dict[str, int] = {}
    for t in titles[:4]:  # istek sayısını sınırla
        q = urllib.parse.quote(t)
        data = _get_json(
            "https://services.fandom.com/unified-search/community-search"
            f"?query={q}&lang=en&limit={limit}"
        )
        if not isinstance(data, dict):
            continue
        for r in data.get("results", []):
            m = re.match(r"https?://([a-z0-9-]+)\.fandom\.com", r.get("url", ""))
            if not m:
                continue
            slug = m.group(1)
            votes[slug] = votes.get(slug, 0) + 1
            if slug not in seen:
                seen[slug] = Candidate(
                    slug=slug, base_score=0.55, source="unified-search",
                    hub=r.get("hub", ""), page_count=int(r.get("pageCount") or 0),
                    wiki_name=r.get("name", ""),
                )
        time.sleep(0.3)
    for slug, c in seen.items():
        if votes[slug] >= 2:
            c.bonuses["multi_synonym"] = 0.10
        if c.hub and media_hub and c.hub == media_hub:
            c.bonuses["hub_match"] = 0.15
        elif c.hub and media_hub and c.hub != media_hub:
            c.bonuses["hub_mismatch"] = -0.20
        if c.page_count >= 100:
            c.bonuses["big_wiki"] = 0.05
        best_name = max((_fuzzy(c.wiki_name.replace(" Wiki", ""), t) for t in titles),
                        default=0.0)
        if best_name >= 0.75:
            c.bonuses["name_match"] = 0.15
    return list(seen.values())


# ----------------------------------------------------------------------------
# K3 — Hakemli doğrulama
# ----------------------------------------------------------------------------

# Crossover / meta wiki'ler: karakter problamasını bile geçerler (hero.fandom.com
# testte Campione karakterlerinin 3/3'üne sahipti). Kesin veto.
CROSSOVER_BLOCKLIST = re.compile(
    r"^(hero|heroes|villains?|protagonist|antagonists?|characters?|allfiction|"
    r"listofdeaths|love-interest|vsbattles|powerlisting|superpower|"
    r"deathbattle.*|fictional-battle.*|dubbing.*|.*-fanon|fanon.*|ideas)$"
)

ACCEPT_THRESHOLD = 0.75


def _mw_query(api_base: str, **params) -> dict | None:
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = f"{api_base}/api.php?" + urllib.parse.urlencode(params)
    return _get_json(url)


def get_siteinfo(api_base: str) -> dict | None:
    data = _mw_query(api_base, action="query", meta="siteinfo",
                     siprop="general|interwikimap")
    try:
        return data["query"]
    except (KeyError, TypeError):
        return None


def probe_pages(api_base: str, names: list[str]) -> float:
    """Karakter/nadir-terim problaması: sayfaların kaçı mevcut? (redirects=1)"""
    if not names:
        return -1.0
    data = _mw_query(api_base, action="query",
                     titles="|".join(names[:20]), redirects="1")
    try:
        pages = data["query"]["pages"]
    except (KeyError, TypeError):
        return -1.0
    hits = sum(1 for p in pages if not p.get("missing"))
    return hits / len(pages) if pages else 0.0


def name_variants(full_names: list[str]) -> list[str]:
    """'Godou Kusanagi' -> hem kendisi hem 'Kusanagi Godou' (romaji sıra farkı)."""
    out: list[str] = []
    for n in full_names:
        out.append(n)
        parts = n.split()
        if len(parts) == 2:
            out.append(f"{parts[1]} {parts[0]}")
    return out


def verify(cand: Candidate, titles: list[str], probe_names: list[str],
           rare_terms: list[str] | None = None) -> float:
    """Skoru hesapla; veto durumunda -1 döner."""
    if CROSSOVER_BLOCKLIST.match(cand.slug):
        return -1.0

    score = cand.base_score + sum(cand.bonuses.values())

    si = get_siteinfo(cand.api_base)
    if not si:
        return -1.0
    sitename = si["general"].get("sitename", "")
    best = max((_fuzzy(sitename.replace(" Wiki", ""), t) for t in titles), default=0)
    if best >= 0.70:
        score += 0.10
    elif best < 0.35 and cand.source != "wikidata":
        score -= 0.15

    # Karakter problaması — asıl pozitif kanıt
    variants = name_variants(probe_names)
    ratio = probe_pages(cand.api_base, variants)
    if ratio >= 0.5:
        score += 0.25
    elif ratio == 0.0 and probe_names:
        return -1.0  # tek karakter bile yoksa bu wiki bu yapım değildir

    # Nadir/ayırt edici terim (crossover'ları karakterler bile ayıramaz)
    if rare_terms:
        if probe_pages(cand.api_base, rare_terms) > 0:
            score += 0.10

    return score


# ----------------------------------------------------------------------------
# K4 — Terim çekme + temizlik
# ----------------------------------------------------------------------------

SUBPAGE_RE = re.compile(r"/")
JUNK_TITLE_RE = re.compile(
    r"^(List of |Category:|Template:)|\((disambiguation|gallery)\)$", re.I)


def pick_language_variant(api_base_root: str, target_lang: str) -> str:
    """interwikimap'ten hedef dilin alt-yolunu bul; yoksa root'u döndür."""
    si = get_siteinfo(api_base_root)
    if si:
        for iw in si.get("interwikimap", []):
            if iw.get("bcp47") == target_lang and iw.get("local"):
                return f"{api_base_root}/{iw['prefix']}"
    return api_base_root


def fetch_category_terms(api_base: str, category: str) -> list[str]:
    """Filtreli categorymembers — duplicate/çöp kaynağını kesen çağrı."""
    terms, cont = [], {}
    while True:
        data = _mw_query(api_base, action="query", list="categorymembers",
                         cmtitle=f"Category:{category}",
                         cmnamespace="0", cmtype="page", cmlimit="500", **cont)
        if not data:
            break
        for m in data.get("query", {}).get("categorymembers", []):
            t = m["title"]
            if SUBPAGE_RE.search(t) or JUNK_TITLE_RE.search(t):
                continue
            terms.append(t)
        cont = data.get("continue") or {}
        if not cont:
            break
    return terms


def canonicalize(api_base: str, terms: list[str]) -> dict[str, list[str]]:
    """Redirect'leri çöz: {kanonik_başlık: [alias'lar]}  — 'Godou' ve
    'Kusanagi Godou' tek kayda düşer, alias'lar çeviri için saklanır."""
    canon: dict[str, list[str]] = {}
    for i in range(0, len(terms), 50):
        batch = terms[i:i + 50]
        data = _mw_query(api_base, action="query",
                         titles="|".join(batch), redirects="1")
        if not data:
            continue
        q = data.get("query", {})
        rmap = {r["from"]: r["to"] for r in q.get("redirects", [])}
        for t in batch:
            target = rmap.get(t, t)
            canon.setdefault(target, [])
            if t != target:
                canon[target].append(t)
    # normalize-dedupe (aksan/harf farkı)
    seen: dict[str, str] = {}
    result: dict[str, list[str]] = {}
    for title, aliases in canon.items():
        key = _norm(title)
        if key in seen:
            result[seen[key]].extend([title] + aliases)
        else:
            seen[key] = title
            result[title] = aliases
    return result


# ----------------------------------------------------------------------------
# Orkestrasyon
# ----------------------------------------------------------------------------

def resolve_fandom_wiki(source: str, media_id: str | int, titles: list[str],
                        probe_names: list[str], media_hub: str = "anime",
                        target_lang: str = "en",
                        overrides: dict[str, str] | None = None,
                        ai_slug_fn=None) -> Candidate | None:
    """Tam akış. `overrides`: {'anilist:12293': 'thecampione'} manuel harita.
    `ai_slug_fn`: son çare AI tahmini için opsiyonel callback -> list[str]."""
    key = f"{source}:{media_id}"
    if overrides and key in overrides:
        return Candidate(slug=overrides[key], base_score=1.0, source="override")

    ids = enrich_ids(source, media_id)

    cands: list[Candidate] = []
    qid = find_wikidata_qid(ids or {source: media_id})
    if qid:
        cands += candidates_from_wikidata(qid)
    cands += candidates_from_fandom_search(titles, media_hub)
    if not cands and ai_slug_fn:
        cands += [Candidate(slug=s, base_score=0.30, source="ai")
                  for s in (ai_slug_fn(titles) or [])]

    best, best_score = None, ACCEPT_THRESHOLD
    for c in sorted(cands, key=lambda c: -c.base_score):
        s = verify(c, titles, probe_names)
        if s >= best_score:
            best, best_score = c, s
    if best and target_lang != "en" and not best.lang_path:
        root = f"https://{best.slug}.fandom.com"
        api = pick_language_variant(root, target_lang)
        if api != root:
            best.lang_path = api.rsplit("/", 1)[-1]
    return best  # None => "eşleşme yok" (negatif cache'e yaz, tahmine düşme!)


if __name__ == "__main__":
    # Duman testi: Campione! (AniList 12293) -> beklenen: thecampione
    cand = resolve_fandom_wiki(
        source="anilist", media_id=12293,
        titles=["Campione!", "Campione! Matsurowanu Kamigami to Kamigoroshi no Maou"],
        probe_names=["Godou Kusanagi", "Erica Blandelli", "Yuri Mariya"],
        media_hub="anime",
    )
    if cand:
        print(f"WIKI: {cand.api_base}  (kaynak={cand.source})")
        terms = fetch_category_terms(cand.api_base, "Characters")
        canon = canonicalize(cand.api_base, terms)
        print(f"{len(canon)} kanonik terim; örnek:")
        for t, aliases in list(canon.items())[:10]:
            print(" -", t, f"(alias: {aliases})" if aliases else "")
    else:
        print("Eşleşme yok — negatif cache'e yazılır, tahmin YAPILMAZ.")
