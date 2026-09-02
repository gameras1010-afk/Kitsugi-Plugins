"""
pages/helpers.py
================
Paylaşılan yardımcılar: nbtn, get_prefs, get_glossary, state, refresh_status.
"""
import os, json, asyncio, subprocess, threading
from datetime import datetime
from nicegui import ui, app
from ng_config import (
    C, SCRIPT_TRANSLATOR, SCRIPT_QA, SCRIPT_GLOSSARY,
    GLOSSARY_FILE, PREFS_FILE, PARENT_DIR, BASE_DIR,
    api_counts, load_glossary, total_terms, load_prefs, save_prefs,
    get_models, REPORTS_CENTRAL_DIR, collect_html_reports,
)

"""
ng_pages_a.py — Dashboard + Glossary sayfaları
"""
import os, json, asyncio, subprocess, threading
from datetime import datetime
from nicegui import ui, app
from ng_config import (
    C, SCRIPT_TRANSLATOR, SCRIPT_QA, SCRIPT_GLOSSARY,
    GLOSSARY_FILE, PREFS_FILE, PARENT_DIR, BASE_DIR,
    api_counts, load_glossary, total_terms, load_prefs, save_prefs,
    get_models, REPORTS_CENTRAL_DIR, collect_html_reports,
)

# ── Native premium buton yardımcısı ─────────────────────────────────────────
# Quasar'ı bypass eder, tam CSS kontrolü sağlar
def nbtn(label: str, *,
         click=None,
         variant: str = "",   # "" | "danger" | "success" | "ghost" | "icon"
         size: str = "",       # "" | "sm" | "lg"
         full: bool = False,
         style: str = ""):
    classes = "nx-btn"
    if variant: classes += f" nx-btn-{variant}"
    if size:    classes += f" nx-btn-{size}"
    if full:    classes += " nx-btn-full"

    btn = ui.element("button").classes(classes)
    if style:
        btn.style(style)
    with btn:
        ui.html(label)
    if click:
        btn.on("click", click)
    return btn


# ── Paylaşımlı uygulama durumu ──────────────────────────────────────────────
state = {
    "path": "",
    "running": False,
    "proc": None,
    "log_lines": [],        # Kalici log satirlari (sayfa yenilenince restore edilir)
    "log_q": None,          # Thread-safe queue (build_translate icinde init edilir)
    "_proc_done": False,
    "prefs": None,
    "glossary": None,
    "selected_series": None,
    "status_api": (0, 0),
    "status_terms": 0,
}

def get_prefs():
    if state["prefs"] is None:
        state["prefs"] = load_prefs()
    return state["prefs"]

_glossary_cache     = {}          # son sonuç
_glossary_cache_key = None        # (glossary_mtime, tb_dir_mtime) tuple

def get_glossary():
    """series_glossary.json + termbase/ (base + chars) birleştirerek döndürür.
    mtime tabanlı cache: dosyalar değişmediyse disk I/O sıfır."""
    import os as _os, json as _json, re as _re

    global _glossary_cache, _glossary_cache_key

    # ── mtime hesapla ─────────────────────────────────────────────────────────
    from ng_config import GLOSSARY_FILE as _GF, PARENT_DIR as _PD
    tb_dir = _os.path.join(_PD, "termbase")
    try:
        _gmt = _os.path.getmtime(_GF) if _os.path.exists(_GF) else 0.0
    except Exception:
        _gmt = 0.0
    try:
        _tmt = max(
            (_os.path.getmtime(_os.path.join(tb_dir, f)) for f in _os.listdir(tb_dir)),
            default=0.0
        ) if _os.path.isdir(tb_dir) else 0.0
    except Exception:
        _tmt = 0.0

    cache_key = (_gmt, _tmt)
    if cache_key == _glossary_cache_key and _glossary_cache:
        return _glossary_cache   # ← hızlı yol: disk I/O yok

    # ── Tam okuma ─────────────────────────────────────────────────────────────
    result = {}
    lookup = {}  # canon_key -> display_name

    raw = load_glossary()
    canonical_titles_map = {}
    if raw:
        canonical_titles_map = raw.get("__canonical_titles__", {})

    def get_canonical_display_name(title_or_key):
        if not title_or_key:
            return ""
        tk = title_or_key.strip().lower()
        canon = canonical_titles_map.get(tk, title_or_key)
        from termbase_manager import _split_title_season
        clean_title, _ = _split_title_season(canon)
        return clean_title.strip()

    # 1. series_glossary.json (ham Fandom data)
    if raw:
        for k, v in raw.items():
            if k == "__canonical_titles__":
                continue
            if not isinstance(v, dict):
                continue
            
            display_name = get_canonical_display_name(k)
            if not display_name:
                continue
            canon_key = display_name.lower().strip()
            
            if canon_key in lookup:
                display_name = lookup[canon_key]
            else:
                lookup[canon_key] = display_name

            wiki_slug = (v.get("wiki") or "").lower().strip()
            
            if display_name not in result:
                result[display_name] = {
                    "wiki": wiki_slug or canon_key,
                    "fetched_at": v.get("fetched_at", ""),
                    "terms": {}
                }
            else:
                # Merge wiki slug if it's cleaner/shorter
                curr_slug = result[display_name].get("wiki", "")
                if wiki_slug and (not curr_slug or curr_slug == canon_key or "__" in curr_slug) and "__" not in wiki_slug:
                    result[display_name]["wiki"] = wiki_slug

            existing_terms = result[display_name].setdefault("terms", {})
            for cat, items in v.get("terms", {}).items():
                existing_terms.setdefault(cat, [])
                if isinstance(items, list):
                    for item in items:
                        if item not in existing_terms[cat]:
                            existing_terms[cat].append(item)

    # 2. *_base.json — yapı: {"meta":{...}, "terms":{cat: {EN:TR,...}}}
    if _os.path.isdir(tb_dir):
        for fname in _os.listdir(tb_dir):
            if not fname.endswith("_base.json"):
                continue
            try:
                tb_data = _json.load(open(_os.path.join(tb_dir, fname), encoding="utf-8"))
                meta = tb_data.get("meta", {})
                series_key = (meta.get("anime") or "").lower().strip()
                if not series_key:
                    series_key = fname.replace("_base.json", "").replace("_", " ")

                display_name = get_canonical_display_name(series_key)
                if not display_name:
                    continue
                canon_key = display_name.lower().strip()

                if canon_key in lookup:
                    display_name = lookup[canon_key]
                else:
                    lookup[canon_key] = display_name

                wiki_slug = fname.replace("_base.json", "").lower().strip()

                terms_block = tb_data.get("terms", {})
                if not terms_block:
                    continue

                if display_name not in result:
                    result[display_name] = {
                        "wiki": wiki_slug or canon_key,
                        "fetched_at": meta.get("translated_at", ""),
                        "terms": {}
                    }
                else:
                    # Update/merge wiki slug
                    curr_slug = result[display_name].get("wiki", "")
                    if wiki_slug and (not curr_slug or curr_slug == canon_key or "__" in curr_slug) and "__" not in wiki_slug:
                        result[display_name]["wiki"] = wiki_slug

                existing_terms = result[display_name].setdefault("terms", {})

                for cat, items in terms_block.items():
                    existing_terms.setdefault(cat, [])
                    if isinstance(items, dict):
                        for en in items.keys():
                            if en not in existing_terms[cat]:
                                existing_terms[cat].append(en)
                    elif isinstance(items, list):
                        for item in items:
                            if item not in existing_terms[cat]:
                                existing_terms[cat].append(item)
            except Exception:
                pass

        # 3. *_chars.json — yapı: {"meta":{...}, "characters":{EN:TR,...}}
        for fname in _os.listdir(tb_dir):
            if not fname.endswith("_chars.json"):
                continue
            try:
                ch_data = _json.load(open(_os.path.join(tb_dir, fname), encoding="utf-8"))
                meta = ch_data.get("meta", {})
                series_key = (meta.get("anime") or "").lower().strip()
                if not series_key:
                    series_key = _re.sub(r'_s\d+_chars$', '', fname.replace(".json", "")).replace("_", " ")

                display_name = get_canonical_display_name(series_key)
                if not display_name:
                    continue
                canon_key = display_name.lower().strip()

                if canon_key in lookup:
                    display_name = lookup[canon_key]
                else:
                    lookup[canon_key] = display_name

                wiki_slug = _re.sub(r'_s\d+_chars$', '', fname.replace(".json", "")).lower().strip()

                chars = ch_data.get("characters", {})
                if not chars:
                    continue

                if display_name not in result:
                    result[display_name] = {
                        "wiki": wiki_slug or canon_key,
                        "fetched_at": meta.get("translated_at", ""),
                        "terms": {}
                    }
                else:
                    # Update/merge wiki slug
                    curr_slug = result[display_name].get("wiki", "")
                    if wiki_slug and (not curr_slug or curr_slug == canon_key or "__" in curr_slug) and "__" not in wiki_slug:
                        result[display_name]["wiki"] = wiki_slug

                existing_terms = result[display_name].setdefault("terms", {})
                existing_terms.setdefault("characters", [])
                for en in chars.keys():
                    if en not in existing_terms["characters"]:
                        existing_terms["characters"].append(en)
            except Exception:
                pass

    _glossary_cache     = result
    _glossary_cache_key = cache_key
    state["glossary"]   = result
    return result




def refresh_status():
    state["status_api"] = api_counts()
    g = get_glossary()
    state["status_terms"] = total_terms(g)

# ── DASHBOARD sayfası (sadece istatistik / overview) ──────────────────────────
