"""
glossary/builder.py
===================
build_glossary, get_prompt_terms, get_prompt_injection,
get_merged_injection, list/delete cached series, CLI.
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

