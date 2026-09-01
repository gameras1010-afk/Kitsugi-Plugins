"""
media_id/ai_tools.py
====================
AI destekli medya tanımlama.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional
from media_id.constants import *


def _ai_get_api_key():
    """api_keys.txt'den tum OpenRouter key'lerini doner. (key_list, endpoint)"""
    base = os.path.dirname(os.path.abspath(__file__))
    keys_path = os.path.join(base, "api_keys.txt")
    if os.path.exists(keys_path):
        try:
            with open(keys_path, "r", encoding="utf-8") as _f:
                _lines = [l.strip() for l in _f if l.strip() and not l.startswith("#")]
            if _lines:
                return _lines, "https://openrouter.ai/api/v1/chat/completions"
        except Exception:
            pass
    return [], None


def _ai_query_direct(prompt: str, max_tokens: int = 180, temperature: float = 0.0) -> str | None:
    """translator_config.json ve user_preferences.json ayarlarina gore AI'ya dogrudan istek gonderir."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    _tcfg = {}
    try:
        _cfg_path = os.path.join(base_dir, 'translator_config.json')
        if os.path.exists(_cfg_path):
            with open(_cfg_path, 'r', encoding='utf-8') as _f:
                _tcfg = json.load(_f)
    except Exception:
        pass

    _ag_url = _tcfg.get('antigravity_url', 'http://localhost:8045/v1/chat/completions')
    _ag_key = _tcfg.get('antigravity_api_key', '')
    _active_model_id = _tcfg.get('active_model_id', '')
    _avail_models = _tcfg.get('available_models', {})

    model_or = 'google/gemini-2.0-flash-lite:free'
    try:
        _pref_path = os.path.join(base_dir, 'user_preferences.json')
        if os.path.exists(_pref_path):
            with open(_pref_path, 'r', encoding='utf-8') as _f:
                _pref_data = json.load(_f)
            model_or = _pref_data.get('ai_model', model_or)
    except Exception:
        pass

    is_ag_preferred = (
        model_or.startswith('AG:')
        or _active_model_id.startswith('AG:')
        or _avail_models.get(model_or, {}).get('provider') == 'antigravity'
    )

    ag_model_name = 'gemini-2.5-flash'
    if model_or.startswith('AG:'):
        ag_model_name = model_or[3:]
    elif _avail_models.get(model_or, {}).get('provider') == 'antigravity':
        ag_model_name = model_or
    elif _active_model_id.startswith('AG:'):
        ag_model_name = _active_model_id[3:]
    else:
        ag_model_name = next(
            (k for k, v in _avail_models.items()
             if isinstance(v, dict) and v.get('provider') == 'antigravity'
             and 'flash' in k.lower() and 'pro' not in k.lower()),
            next((k for k, v in _avail_models.items()
                  if isinstance(v, dict) and v.get('provider') == 'antigravity'), 'gemini-2.5-flash')
        )

    def _try_antigravity() -> str | None:
        if not _ag_url or not _ag_key:
            return None
        try:
            print(f"[MediaID] Antigravity ile istek gonderiliyor: {ag_model_name} @ {_ag_url}")
            _headers = {"Authorization": f"Bearer {_ag_key}", "Content-Type": "application/json"}
            _payload = {
                "model": ag_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens, "temperature": temperature,
            }
            _resp = requests.post(_ag_url, headers=_headers, json=_payload, timeout=15)
            if _resp.status_code == 200:
                return _resp.json()["choices"][0]["message"]["content"].strip()
            print(f"[MediaID] Antigravity HTTP {_resp.status_code}: {_resp.text}")
        except Exception as e:
            print(f"[MediaID] Antigravity baglanti hatasi: {e}")
        return None

    def _try_keymanager() -> str | None:
        global _key_cursor
        keys_list, endpoint = _ai_get_api_key()
        if not keys_list or not endpoint:
            print("[MediaID] OpenRouter/Google key bulunamadi.")
            return None

        total = len(keys_list)
        for i in range(total):
            idx = (_key_cursor + i) % total
            api_key = keys_list[idx]
            try:
                print(f"[MediaID] OpenRouter/Google ile istek gonderiliyor (Key index: {idx}) @ {endpoint}")
                _headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                _payload = {
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens, "temperature": temperature,
                }
                _resp = requests.post(endpoint, headers=_headers, json=_payload, timeout=12)
                if _resp.status_code in (402, 429):
                    _key_cursor = (idx + 1) % total
                    continue
                if _resp.status_code != 200:
                    continue
                _key_cursor = idx
                return _resp.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                continue
        return None

    _text = None
    if is_ag_preferred:
        print("[MediaID] Yonlendirme: Antigravity Oncelikli.")
        _text = _try_antigravity()
        if not _text:
            print("[MediaID] Yonlendirme: Antigravity basarisiz, OpenRouter/Google deneniyor.")
            _text = _try_keymanager()
    else:
        print("[MediaID] Yonlendirme: OpenRouter/Google Oncelikli.")
        _text = _try_keymanager()
        if not _text:
            print("[MediaID] Yonlendirme: OpenRouter/Google basarisiz, Antigravity deneniyor.")
            _text = _try_antigravity()

    return _text


def _ai_classify_media(filename: str):
    """
    Dosya adi AI'ya gonderilir: title + alt_title + search_hint + media_type + season doner.
    3 katmanli arama icin gerekli.
    """
    fn = os.path.splitext(os.path.basename(filename))[0]
    if fn in _AI_CLASSIFY_CACHE:
        return _AI_CLASSIFY_CACHE[fn]

    prompt = (
        "Analyze this video/subtitle filename and identify the media.\n"
        f"Filename: {fn}\n\n"
        "Return ONLY a JSON object (no markdown, no extra text):\n"
        '{\n'
        '  "title": "Title as recognized / Romaji if anime (e.g. Oshi no Ko)",\n'
        '  "alt_title": "Official English title if meaningfully different, else null",\n'
        '  "search_hint": "Best search query for MAL/AniList/TMDB",\n'
        '  "media_type": "anime OR series OR movie",\n'
        '  "season": 3,\n'
        '  "season_title": "Official title for THIS season only (e.g. Sword Art Online: Alicization for S3) or null",\n'
        '  "part": null\n'
        '}\n\n'
        "Rules:\n"
        "- title: Recognized title (Romaji for anime is fine).\n"
        "- alt_title: English ONLY if meaningfully different. null otherwise.\n"
        "  Example: 'Kimetsu no Yaiba' -> alt_title: 'Demon Slayer'\n"
        "  Example: 'Oshi no Ko' -> alt_title: null\n"
        "- search_hint: Form most likely to match on MAL/AniList/TMDB.\n"
        "  Abbreviated: 'TenSura' -> search_hint: 'Tensei shitara Slime Datta Ken'\n"
        "- media_type: anime=Japanese animation (including anime movies/films), series=live-action TV, movie=live-action film\n"
        "- season: integer or null (S03 -> 3)\n"
        "- season_title: Official title for this specific season if it differs from base title.\n"
        "  Examples: SAO S3 -> 'Sword Art Online: Alicization' | AoT S4 -> 'Attack on Titan: The Final Season'\n"
        "  If title doesn't change between seasons, set null.\n"
        "- part: integer or null (Movie 2 -> 2)\n"
        "- If unsure, write UNKNOWN\n"
        "JSON:"
    )

    _text = _ai_query_direct(prompt, max_tokens=180, temperature=0)
    if not _text:
        return None

    # 4. Yanıtı Parse Et
    try:
        if "```" in _text:
            _text = _text.split("\n", 1)[-1].rsplit("```", 1)[0]
        _text = _text.strip()

        _r = json.loads(_text)
        _title = (_r.get("title") or "").strip().strip('"').strip("'")
        _alt   = (_r.get("alt_title") or "").strip().strip('"').strip("'") or None
        _hint  = (_r.get("search_hint") or "").strip().strip('"').strip("'") or None
        _mtype = (_r.get("media_type") or "").strip().lower()
        _season       = _r.get("season")
        _season_title = (_r.get("season_title") or "").strip().strip(chr(34)).strip(chr(39)) or None
        _part         = _r.get("part")

        if not _title or "UNKNOWN" in _title.upper():
            return None
        if _mtype not in ("anime", "series", "movie"):
            _mtype = "unknown"
        try: _season = int(_season) if _season is not None else None
        except (ValueError, TypeError): _season = None
        try: _part = int(_part) if _part is not None else None
        except (ValueError, TypeError): _part = None

        if _alt and _alt.lower() == _title.lower(): _alt = None
        if _hint and _hint.lower() == _title.lower(): _hint = None

        _out = {
            "title": _title, "alt_title": _alt, "search_hint": _hint,
            "media_type": _mtype, "season": _season,
            "season_title": _season_title, "part": _part
        }
        _AI_CLASSIFY_CACHE[fn] = _out
        return _out
    except Exception as e:
        print(f"[MediaID] Yanit ayristirma hatasi: {e}")
    return None


def _ai_identify_title(raw_filename: str, translator=None) -> str | None:
    """Yapay zekaya dosya adindan medya basligini tespit ettirir."""
    try:
        prompt = (
            f"What anime, movie or TV series is this subtitle/video filename from?\n"
            f"Filename: {raw_filename}\n\n"
            "Rules:\n"
            "- Return ONLY the exact title (nothing else)\n"
            "- If anime: return the official English title\n"
            "- If you cannot determine it, return: UNKNOWN\n"
            "Title:"
        )
        if translator is not None:
            result = translator.translate_single_line(prompt)
        else:
            result = _ai_query_direct(prompt, max_tokens=100)

        if result and "UNKNOWN" not in result.upper() and len(result.strip()) < 100:
            return result.strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _ai_fill_gaps(metadata: dict, translator=None) -> dict:
    """API'dan gelen metadata'da eksik alanlari yapay zeka ile doldur."""
    title = metadata.get("title", "")
    missing = []
    if not metadata.get("genres"):
        missing.append("genres (comma-separated list)")
    if not metadata.get("characters"):
        missing.append("main characters (comma-separated list of 5-8 names)")
    if not metadata.get("synopsis"):
        missing.append("a 2-sentence synopsis")

    if not missing:
        return metadata

    try:
        prompt = f'For the anime/series: "{title}"\nProvide ONLY the following:\n'
        for i, m in enumerate(missing, 1):
            prompt += f"{i}. {m}\n"
        prompt += "\nRespond in this exact format:\n"
        for i, m in enumerate(missing, 1):
            prompt += f"{i}. [answer]\n"

        if translator is not None:
            result = translator.translate_single_line(prompt)
        else:
            result = _ai_query_direct(prompt, max_tokens=300)

        if not result:
            return metadata

        rlines = [l.strip() for l in result.strip().split("\n") if l.strip()]
        for i, field_desc in enumerate(missing):
            if i < len(rlines):
                val = re.sub(r'^\d+\.\s*', '', rlines[i]).strip()
                if "genres" in field_desc:
                    metadata["genres"] = [g.strip() for g in val.split(",") if g.strip()]
                elif "characters" in field_desc:
                    metadata["characters"] = [c.strip() for c in val.split(",") if c.strip()]
                elif "synopsis" in field_desc:
                    metadata["synopsis"] = val
    except Exception as e:
        print(f"{Fore.YELLOW}[MediaID] AI fill hatasi: {e}{Style.RESET_ALL}")

    return metadata


def _try_source(name: str, fn, *args) -> tuple:
    """Tek kaynak denemesi. (metadata, source_name) doner."""
    print(f"{Fore.CYAN}   [MediaID] {name} sorgulanıyor...{Style.RESET_ALL}", end=' ', flush=True)
    try:
        result = fn(*args)
        if result:
            print(f"{Fore.GREEN}Bulundu!{Style.RESET_ALL}")
            return result, name
        else:
            print(f"{Fore.YELLOW}Bulunamadi.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Hata: {e}{Style.RESET_ALL}")
    time.sleep(REQUEST_DELAY)
    return None, None


