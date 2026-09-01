"""
glossary/titles.py
==================
Canonical title API'leri: Jikan, TVMaze, TMDB.
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
