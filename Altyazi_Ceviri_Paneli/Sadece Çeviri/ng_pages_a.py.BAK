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
def build_dashboard():

    refresh_status()
    api_ok, api_ex = state["status_api"]
    terms_n = state["status_terms"]
    g = get_glossary()

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🏠 Genel Bakış</div>')
        ui.html('<div class="ph-sub">Sistem durumu ve hızlı erişim</div>')

    # ── Stat kartları ──
    with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:0 28px 16px"):
        _stat_card("🔑", "Aktif API Anahtarı", str(api_ok), C["GREEN"], "rgba(16,185,129,0.15)")
        _stat_card("⚡", "Tükenmiş Anahtar", str(api_ex), C["RED"], "rgba(239,68,68,0.1)")
        _stat_card("📚", "Sözlük Terimi", str(terms_n), C["PURPLE"], "rgba(124,58,237,0.12)")

    # ── 2. satır ──
    with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:0 28px 16px"):
        _stat_card("📖", "Seri Sayısı", str(len(g)), C["CYAN"], "rgba(0,212,255,0.1)")
        api_total = api_ok + api_ex
        pct = int(api_ok / api_total * 100) if api_total else 0
        _stat_card("📊", "API Sağlığı", f"%{pct}", C["YELLOW"], "rgba(245,158,11,0.1)")
        motor_label = "⚙️ Çalışıyor" if state.get("running") else "Hazır"
        motor_color = C["YELLOW"] if state.get("running") else C["GREEN"]
        motor_bg    = "rgba(245,158,11,0.1)" if state.get("running") else "rgba(16,185,129,0.1)"
        _stat_card("🤖", "Motor Durumu", motor_label, motor_color, motor_bg)

    # ── Hızlı başlat kartı ──
    with ui.element("div").style("padding:0 28px 16px"):
        with ui.element("div").style(
            f"background:linear-gradient(135deg,rgba(124,58,237,0.15),rgba(0,212,255,0.08));"
            f"border:1px solid rgba(124,58,237,0.35);border-radius:16px;padding:24px;"
            f"display:flex;align-items:center;justify-content:space-between"
        ):
            with ui.element("div"):
                ui.html(f'<div style="font-size:18px;font-weight:700;color:{C["TEXT"]}">\U0001f504 \u00c7eviriyi Ba\u015flat</div>')
                ui.html(f'<div style="font-size:13px;color:{C["SUB"]};margin-top:4px">Translate sayfas\u0131na ge\u00e7 \u2192 dosya se\u00e7 \u2192 \u00e7evir</div>')
            # JS ile sidebar Translate nav butonunu tikla
            _go_btn = ui.element("button").classes("nx-btn nx-btn-lg").on(
                "click",
                lambda: ui.run_javascript(
                    "document.querySelectorAll('.nav-btn').forEach(function(b){"
                    "  if(b.innerText && b.innerText.toLowerCase().indexOf('translate')>=0) b.click();"
                    "});"
                )
            )
            with _go_btn:
                ui.html("\u25b6 Translate Sayfas\u0131na Git")


    # ── Sözlük özeti ──
    with ui.element("div").style("padding:0 28px 20px"):
        with ui.element("div").classes("card"):
            ui.html(f'<div class="card-title">&#128218; Sözlük Özeti</div>')
            if not g:
                ui.html(f'<div style="color:{C["MUTED"]};font-size:13px;text-align:center;padding:20px">Henüz seri eklenmemiş. Glossary sayfasından wiki çekin.</div>')
            else:
                with ui.element("div").style("display:flex;flex-wrap:wrap;gap:8px"):
                    for sname, data in g.items():
                        terms = data.get("terms", {})
                        count = sum(len(v) for v in terms.values())
                        ui.html(
                            f'<div style="background:{C["PANEL"]};border:1px solid {C["BORDER"]};'
                            f'border-radius:10px;padding:10px 16px;min-width:150px">'
                            f'<div style="font-size:13px;font-weight:600;color:{C["TEXT"]}">{sname}</div>'
                            f'<div style="font-size:11px;color:{C["MUTED"]};margin-top:3px">{count} terim</div>'
                            f'</div>'
                        )



# ── TRANSLATE sayfası ─────────────────────────────────────────────────────────

def build_translate():
    prefs  = get_prefs()
    models = get_models()
    log_box = [None]

    # log_q: thread-safe queue, her zaman hazir
    import queue as _q_mod
    if "log_q" not in state or state["log_q"] is None:
        state["log_q"] = _q_mod.Queue()

    # ── Quasar ve özel bileşenler — tema renkleriyle uyumlu CSS ────────────────
    ui.add_head_html("""<style>
    /* ── Dropdown menu ── */
    .q-menu{background:#0d1117!important;border:1px solid color-mix(in srgb,var(--accent1) 55%,transparent)!important;border-radius:12px!important;box-shadow:0 8px 32px rgba(0,0,0,.75)!important;backdrop-filter:blur(20px)!important;max-height:320px!important;overflow-y:auto!important}
    .q-menu::-webkit-scrollbar{width:5px}
    .q-menu::-webkit-scrollbar-track{background:rgba(255,255,255,.04)}
    .q-menu::-webkit-scrollbar-thumb{background:color-mix(in srgb,var(--accent1) 55%,transparent);border-radius:4px}
    .q-menu .q-item{color:#a9b1d6!important;padding:8px 16px!important;font-size:13px!important}
    .q-menu .q-item:hover,.q-menu .q-item--active{background:color-mix(in srgb,var(--accent1) 22%,transparent)!important;color:#e2e8f0!important}
    .q-menu .q-item--active{color:var(--accent1)!important;font-weight:700!important}
    /* ── Form fields ── */
    .q-field__native,.q-field__input{color:#e2e8f0!important}
    .q-field--outlined .q-field__control{border-color:color-mix(in srgb,var(--accent1) 40%,transparent)!important;border-radius:10px!important}
    .q-field--outlined:hover .q-field__control{border-color:color-mix(in srgb,var(--accent1) 70%,transparent)!important}
    .q-field--outlined.q-field--focused .q-field__control{border-color:var(--accent1)!important;box-shadow:0 0 0 2px color-mix(in srgb,var(--accent1) 22%,transparent)!important}
    .q-field__label{color:#6b7280!important;font-size:11px!important}
    .q-select__dropdown-icon{color:var(--accent1)!important}
    /* ── Sliders ── */
    .q-slider__track{background:linear-gradient(90deg,var(--accent1),var(--accent2))!important}
    .q-slider__thumb{color:var(--accent1)!important}
    /* ── Linear progress (Quasar) — tema rengi ── */
    .q-linear-progress__track{background:rgba(255,255,255,0.08)!important}
    .q-linear-progress__model{background:linear-gradient(90deg,var(--accent1),var(--accent2))!important}
    /* ── Toggle switch (app custom) ── */
    .toggle-switch.on{background:linear-gradient(135deg,var(--accent1),var(--accent2))!important;border-color:var(--accent1)!important}
    /* ── Chip active state ── */
    .chip-active{background:color-mix(in srgb,var(--accent1) 22%,transparent)!important;border-color:color-mix(in srgb,var(--accent1) 55%,transparent)!important;color:var(--accent1)!important}
    </style>""")

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🔄 Translate — Çeviri Motoru</div>')
        ui.html('<div class="ph-sub">Dosya seç → ayarla → çeviriyi başlat</div>')

    with ui.element("div").style("padding:0 28px 20px;display:flex;flex-direction:column;gap:12px"):

        # ── 1. KAYNAK DOSYA ──────────────────────────────────────────────────────
        _cyan = C["CYAN"]; _cyan2 = C["CYAN2"]; _border = C["BORDER"]
        with ui.element("div").classes("card card-cyan").style("padding:14px 18px"):
            ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:{_cyan};margin-bottom:10px">📁 KAYNAK DOSYA / KLASÖR</div>')
            with ui.element("div").style("display:flex;gap:8px;align-items:center"):
                path_inp = ui.input(
                    placeholder="Dosya veya klasör yolu... (veya buraya yazın)",
                    value=state.get("path") or prefs.get("last_path", "")
                ).style(
                    f"flex:1;background:#080912;color:{_cyan2};"
                    f"border:1px solid {_border};border-radius:10px;padding:10px 14px;"
                    "font-family:Consolas,monospace;font-size:12px"
                )
                # path_inp el değiştirilince state'e yaz
                def on_path_typed(e):
                    state["path"] = e.value
                path_inp.on("change", on_path_typed)
                def pick_folder_t():
                    import tkinter as tk; from tkinter import filedialog
                    r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
                    p = filedialog.askdirectory(title="Klasör Seç"); r.destroy()
                    if p:
                        state["path"] = p; path_inp.set_value(p)
                        from ng_config import save_prefs as _sp2
                        prefs["last_path"] = p; _sp2(prefs)
                        if state.get("log_q"): state["log_q"].put(f"[KLASÖR] {p}")
                        ui.notify(f"Klasör: ...{p[-35:]}", type="positive")
                def pick_file_t():
                    import tkinter as tk; from tkinter import filedialog
                    r = tk.Tk(); r.withdraw(); r.attributes("-topmost", True)
                    p = filedialog.askopenfilenames(title="Dosya Seç", filetypes=[
                        ("Tüm Desteklenenler","*.ass *.srt *.mkv *.mp4 *.avi *.mov *.wmv *.ts *.m2ts *.flv *.webm *.m4v"),
                        ("Altyazı","*.ass *.srt"),("Video","*.mkv *.mp4 *.avi *.mov"),("Tüm","*.*")
                    ]); r.destroy()
                    if p:
                        joined = p[0] if len(p) == 1 else ";".join(p)
                        state["path"] = joined; path_inp.set_value(joined)
                        from ng_config import save_prefs as _sp2
                        prefs["last_path"] = joined; _sp2(prefs)
                        if state.get("log_q"):
                            state["log_q"].put(f"[DOSYA] {len(p)} dosya seçildi:")
                            for fp in p: state["log_q"].put(f"  → {fp}")
                        ui.notify(f"{len(p)} dosya seçildi", type="positive")
                nbtn("📁 KLASÖR", click=pick_folder_t)
                nbtn("📄 DOSYA / VIDEO", click=pick_file_t, variant="ghost")

        # ── 2. AYARLAR (2-sütun) ─────────────────────────────────────────────────
        _purple = C["PURPLE"]; _green = C["GREEN"]; _yellow = C["YELLOW"]
        _panel = C["PANEL"]; _muted = C["MUTED"]

        # ── API SAĞLAYICI TOGGLE ──────────────────────────────────────────────────
        _ag_magenta_t = "#d946ef"
        _or_blue_t    = "#3b82f6"

        # Mevcut sağlayıcıyı tespit et
        def _detect_current_provider():
            try:
                from ng_config import load_trans_cfg as _ltc_p
                _cfg_p = _ltc_p()
                _avail_p = _cfg_p.get("available_models", {})
                _cur_m   = prefs.get("ai_model", "")
                if (_avail_p.get(_cur_m, {}).get("provider") == "antigravity"
                        or _cur_m.startswith("AG:")):
                    return "antigravity"
            except Exception:
                pass
            return "openrouter"

        _active_prov = [_detect_current_provider()]  # mutable list

        def _make_prov_style(prov, active):
            if prov == active:
                if prov == "antigravity":
                    return (f"flex:1;padding:10px 0;border-radius:10px;cursor:pointer;"
                            f"background:linear-gradient(135deg,{_ag_magenta_t}22,{_ag_magenta_t}44);"
                            f"border:2px solid {_ag_magenta_t};text-align:center;transition:all 0.25s")
                else:
                    return (f"flex:1;padding:10px 0;border-radius:10px;cursor:pointer;"
                            f"background:linear-gradient(135deg,{_or_blue_t}22,{_or_blue_t}44);"
                            f"border:2px solid {_or_blue_t};text-align:center;transition:all 0.25s")
            return (f"flex:1;padding:10px 0;border-radius:10px;cursor:pointer;"
                    f"background:rgba(0,0,0,0.25);border:2px solid rgba(255,255,255,0.08);"
                    f"text-align:center;transition:all 0.25s;opacity:0.55")

        _prov_or_html  = [None]
        _prov_ag_html  = [None]
        _prov_badge    = [None]

        def _render_prov_html(active):
            _or_s  = _make_prov_style("openrouter",  active)
            _ag_s  = _make_prov_style("antigravity", active)
            _or_col = _or_blue_t if active == "openrouter" else "#6b7280"
            _ag_col = _ag_magenta_t if active == "antigravity" else "#6b7280"
            _prov_or_html[0].set_content(
                f'<div style="{_or_s}">'
                f'<div style="font-size:16px;margin-bottom:2px">🌐</div>'
                f'<div style="font-size:11px;font-weight:800;color:{_or_col};letter-spacing:0.5px">OpenRouter</div>'
                f'<div style="font-size:9px;color:#9ca3af;margin-top:1px">Ücretsiz / ücretli keyler</div>'
                f'</div>'
            )
            _prov_ag_html[0].set_content(
                f'<div style="{_ag_s}">'
                f'<div style="font-size:16px;margin-bottom:2px">⚡</div>'
                f'<div style="font-size:11px;font-weight:800;color:{_ag_col};letter-spacing:0.5px">Antigravity</div>'
                f'<div style="font-size:9px;color:#9ca3af;margin-top:1px">43 hesap · yerel proxy</div>'
                f'</div>'
            )
            # Badge
            if active == "antigravity":
                _prov_badge[0].set_content(
                    f'<span style="font-size:10px;color:{_ag_magenta_t};font-weight:700">'
                    f'⚡ Aktif: Antigravity Tools — RPM=8, Delay=2.5sn otomatik</span>'
                )
            else:
                _prov_badge[0].set_content(
                    f'<span style="font-size:10px;color:{_or_blue_t};font-weight:700">'
                    f'🌐 Aktif: OpenRouter — API keyler üzerinden çeviri</span>'
                )

        with ui.element("div").classes("card").style(
            "padding:12px 16px;margin-bottom:2px"
        ):
            ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;'
                    f'color:#e2e8f0;margin-bottom:10px">🔌 AKTİF ÇEVİRİ API\'Sİ</div>')

            with ui.element("div").style("display:flex;gap:10px;margin-bottom:8px"):
                _prov_or_html[0] = ui.html("")
                _prov_ag_html[0] = ui.html("")

            _prov_badge[0] = ui.html("")
            _render_prov_html(_active_prov[0])

            # OpenRouter seç
            def _switch_to_openrouter():
                from ng_config import save_prefs as _sp5, load_trans_cfg as _ltc5
                _cfg5   = _ltc5()
                _avail5 = _cfg5.get("available_models", {})
                # İlk OpenRouter modelini bul
                _or_model = next(
                    (k for k, v in _avail5.items()
                     if isinstance(v, dict) and v.get("provider") in ("openrouter", "google")),
                    prefs.get("ai_model", "google/gemini-2.0-flash-001")
                )
                # OpenRouter'da model yoksa mevcut modeli koru
                if not _or_model or _avail5.get(_or_model, {}).get("provider") == "antigravity":
                    _or_model = "google/gemini-2.0-flash-001"
                prefs["ai_model"]            = _or_model
                prefs["simple_mode"]         = True
                prefs["account_rpm_limit"]   = 20
                prefs["batch_delay_seconds"] = 3.0
                _sp5(prefs)
                model_sel.set_value(_or_model)
                rpm_lbl.set_text("20"); rpm_sl.set_value(20)
                bdel_lbl.set_text("3.0"); bdel_sl.set_value(3.0)
                _active_prov[0] = "openrouter"
                _render_prov_html("openrouter")
                ui.notify("🌐 OpenRouter aktif — normal ayarlar yüklendi", type="info", timeout=3000)

            # Antigravity seç
            def _switch_to_antigravity():
                from ng_config import save_prefs as _sp6, load_trans_cfg as _ltc6
                _cfg6   = _ltc6()
                _avail6 = _cfg6.get("available_models", {})
                _act6   = _cfg6.get("active_model_id", "").replace("AG:", "")
                # Tercih: active_model_id > gemini-2.5-flash > ilk AG model
                _ag_model = (
                    _act6 if (_act6 and _avail6.get(_act6, {}).get("provider") == "antigravity")
                    else next(
                        (k for k, v in _avail6.items()
                         if isinstance(v, dict) and v.get("provider") == "antigravity"
                         and "flash" in k and "lite" not in k),
                        next((k for k, v in _avail6.items()
                              if isinstance(v, dict) and v.get("provider") == "antigravity"), None)
                    )
                )
                if not _ag_model:
                    ui.notify("Antigravity modeli bulunamadı — translator_config.json kontrol edin",
                              type="warning", timeout=4000)
                    return
                prefs["ai_model"]            = _ag_model
                prefs["simple_mode"]         = False
                prefs["account_rpm_limit"]   = 8
                prefs["batch_delay_seconds"] = 2.5
                _sp6(prefs)
                model_sel.set_value(_ag_model)
                rpm_lbl.set_text("8");   rpm_sl.set_value(8)
                bdel_lbl.set_text("2.5"); bdel_sl.set_value(2.5)
                _active_prov[0] = "antigravity"
                _render_prov_html("antigravity")
                ui.notify(f"⚡ Antigravity aktif → {_ag_model} (RPM=8, Delay=2.5sn)",
                          type="positive", timeout=4000)

            _prov_or_html[0].on("click", _switch_to_openrouter)
            _prov_ag_html[0].on("click", _switch_to_antigravity)

        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:12px"):

            # Sol: Aktif Seri + AI Model + DİL SEÇİMİ
            with ui.element("div").classes("card").style("padding:14px 16px;display:flex;flex-direction:column;gap:14px"):
                with ui.element("div"):
                    ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:{_purple};margin-bottom:6px">🎯 AKTİF SERİ</div>')
                    g = load_glossary()
                    series_opts = ["(Seri Seçme)"] + list(g.keys())
                    series_sel = ui.select(options=series_opts, value=series_opts[0], label="").style("width:100%")
                    series_info = ui.label("Seri seçilmedi").style(f"font-size:10px;color:{_muted};margin-top:3px")
                    def on_series_change(e):
                        sel = e.args if isinstance(e.args, str) else series_sel.value
                        if sel and sel != "(Seri Seçme)":
                            data = g.get(sel, {}); terms = data.get("terms", {})
                            count = sum(len(v) for v in terms.values())
                            series_info.set_text(f"✔ {count} terim hazır")
                            series_info.style(f"font-size:10px;color:{_green};margin-top:3px")
                        else:
                            series_info.set_text("Seri seçilmedi")
                            series_info.style(f"font-size:10px;color:{_muted};margin-top:3px")
                    series_sel.on("update:model-value", on_series_change)
                with ui.element("div"):
                    _c2 = C["CYAN"]
                    ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:{_c2};margin-bottom:6px">🤖 AI MODELİ</div>')
                    model_sel = ui.select(options=models, value=prefs.get("ai_model", models[0]), label="").style("width:100%")
                    def on_model_change(e):
                        from ng_config import save_prefs as _sp
                        v = e.args if isinstance(e.args, str) else model_sel.value
                        if v: prefs["ai_model"] = v; _sp(prefs)
                    model_sel.on("update:model-value", on_model_change)
                # ── DİL SEÇİMİ (sola taşındı) ───────────────────────────────
                with ui.element("div"):
                    ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:{_green};margin-bottom:6px">🌍 DİL SEÇİMİ</div>')
                    with ui.element("div").style("display:grid;grid-template-columns:1fr 20px 1fr;gap:6px;align-items:center"):
                        src_sel = ui.select(["English","Japanese","Korean","Chinese"], value=prefs.get("source_lang","English"), label="Kaynak").style("width:100%")
                        ui.html('<div style="text-align:center;color:#555;padding-top:14px;font-size:14px">→</div>')
                        tgt_sel = ui.select(["Turkish","English","German","French","Spanish"], value=prefs.get("target_lang","Turkish"), label="Hedef").style("width:100%")
                    def on_src_change(e):
                        from ng_config import save_prefs as _sp
                        v = e.args if isinstance(e.args, str) else src_sel.value
                        if v: prefs["source_lang"] = v; _sp(prefs)
                    def on_tgt_change(e):
                        from ng_config import save_prefs as _sp
                        v = e.args if isinstance(e.args, str) else tgt_sel.value
                        if not v: return
                        _lang_iso = {"Turkish":"tr","English":"en","German":"de",
                                     "French":"fr","Spanish":"es","Japanese":"ja",
                                     "Korean":"ko","Chinese":"zh"}
                        prefs["target_lang"] = v
                        prefs["target_language_code"] = _lang_iso.get(v, "tr")
                        _sp(prefs)
                    src_sel.on("update:model-value", on_src_change)
                    tgt_sel.on("update:model-value", on_tgt_change)

            # Sağ: BATCH + GECİKME + BATCH GECİKMESİ + API LİMİT
            with ui.element("div").classes("card").style("padding:14px 16px;display:flex;flex-direction:column;gap:12px"):
                with ui.element("div"):
                    with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"):
                        ui.html(f'<span style="font-size:10px;font-weight:700;color:{_purple}">⚙️ BATCH</span>')
                        batch_lbl = ui.label(str(prefs.get("batch_size", 10))).style(f"font-size:13px;font-weight:800;color:{_purple}")
                    batch_sl = ui.slider(min=1, max=50, value=prefs.get("batch_size", 10)).style("width:100%")
                    def on_batch_change(e):
                        from ng_config import save_prefs as _sp, save_trans_cfg as _stc, load_trans_cfg as _ltc
                        v = int(e.args); batch_lbl.set_text(str(v))
                        prefs["batch_size"] = v; _sp(prefs)
                        _tc = _ltc(); _tc["batch_size"] = v; _stc(_tc)
                    batch_sl.on("update:model-value", on_batch_change)



                with ui.element("div"):
                    with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;margin-bottom:2px"):
                        ui.html(
                            '<span style="font-size:10px;font-weight:700;color:#f97316">🔄 BATCH GECİKMESİ (sn)</span>'
                            '<span title="Her BATCH tamamlandıktan sonra bir sonraki batch başlamadan önce beklenen süre. '
                            'API rate-limit (429) hatalarını önlemek için kullanılır. '
                            'Önerilen: 3-5 sn (yüksek RPM limitinde 0 yapılabilir)" '
                            'style="font-size:11px;color:#888;cursor:help;margin-left:4px">ⓘ</span>'
                        )
                        bdel_lbl = ui.label(f'{prefs.get("batch_delay_seconds", 3):.1f}').style("font-size:13px;font-weight:800;color:#f97316")
                    bdel_sl = ui.slider(min=0, max=15, step=0.5, value=prefs.get("batch_delay_seconds", 3)).style("width:100%")
                    def on_bdel_change(e):
                        from ng_config import save_prefs as _sp
                        v = float(e.args); bdel_lbl.set_text(f"{v:.1f}")
                        prefs["batch_delay_seconds"] = v; _sp(prefs)
                    bdel_sl.on("update:model-value", on_bdel_change)
                with ui.element("div"):
                    with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"):
                        ui.html(f'<span style="font-size:10px;font-weight:700;color:#ef4444">🔴 API LİMİT (RPM)</span>')
                        rpm_lbl = ui.label(str(prefs.get("account_rpm_limit", 20))).style("font-size:13px;font-weight:800;color:#ef4444")
                    rpm_sl = ui.slider(min=10, max=200, step=5, value=prefs.get("account_rpm_limit", 20)).style("width:100%")
                    def on_rpm_change(e):
                        from ng_config import save_prefs as _sp
                        v = int(e.args); rpm_lbl.set_text(str(v))
                        prefs["account_rpm_limit"] = v; _sp(prefs)
                    rpm_sl.on("update:model-value", on_rpm_change)
                    ui.html('<span style="font-size:9px;color:#888;margin-top:2px;display:block">OpenRouter global RPM (tüm keyler toplam)</span>')


        # ── ANTİGRAVİTY PANEL ────────────────────────────────────────────────────
        import requests as _req_ag, threading as _th_ag, json as _json_ag
        _ag_magenta   = "#d946ef"
        _ag_magenta_d = "rgba(217,70,239,0.15)"

        with ui.element("div").classes("card").style(
            f"padding:14px 18px;border:1px solid {_ag_magenta}44;"
            f"background:linear-gradient(135deg,rgba(217,70,239,0.08),rgba(0,0,0,0.3));"
            "position:relative;overflow:hidden"
        ):
            # ── Başlık + Durum ─────────────────────────────────────────────────
            _ag_status_dot  = [None]
            _ag_status_lbl  = [None]
            _ag_acct_lbl    = [None]

            with ui.element("div").style("display:flex;align-items:center;gap:10px;margin-bottom:12px"):
                ui.html(
                    f'<span style="font-size:16px">⚡</span>'
                    f'<span style="font-size:11px;font-weight:800;letter-spacing:1.5px;color:{_ag_magenta}">'
                    f'ANTİGRAVİTY TOOLS</span>'
                )
                # Durum indikatörü (dinamik)
                _ag_status_dot[0] = ui.html(
                    '<span id="ag-dot" style="width:9px;height:9px;border-radius:50%;'
                    'background:#6b7280;display:inline-block;margin-left:4px"></span>'
                )
                _ag_status_lbl[0] = ui.label("Kontrol ediliyor...").style(
                    f"font-size:10px;color:#9ca3af;font-weight:600"
                )
                _ag_acct_lbl[0] = ui.label("").style(
                    f"font-size:10px;color:{_ag_magenta};font-weight:700;margin-left:auto"
                )

            # ── AG Durum Kontrolü ───────────────────────────────────────────
            def _check_ag_status():
                try:
                    from ng_config import load_trans_cfg as _ltc2
                    _cfg2 = _ltc2()
                    _url2 = _cfg2.get("antigravity_url","http://localhost:8045/v1/chat/completions")
                    _health = _url2.replace("/v1/chat/completions","").replace("/v1","") + "/health"
                    r = _req_ag.get(_health, timeout=3)
                    if r.status_code in (200, 404):
                        # 404 da olsa servis çalışıyor demektir (bazı sürümler /health yok)
                        _data = {}
                        try: _data = r.json()
                        except Exception: pass
                        n_acc = _data.get("accounts", _data.get("count", ""))
                        _ag_status_dot[0].set_content(
                            '<span id="ag-dot" style="width:9px;height:9px;border-radius:50%;'
                            'background:#10b981;display:inline-block;box-shadow:0 0 6px #10b981"></span>'
                        )
                        _ag_status_lbl[0].set_text("Çalışıyor ✓")
                        _ag_status_lbl[0].style(f"font-size:10px;color:#10b981;font-weight:700")
                        if n_acc:
                            _ag_acct_lbl[0].set_text(f"🔑 {n_acc} hesap aktif")
                    else:
                        raise ConnectionError(f"HTTP {r.status_code}")
                except Exception:
                    # Servis yok → Antigravity'nin /v1/models endpoint'ini dene
                    try:
                        from ng_config import load_trans_cfg as _ltc3
                        _cfg3 = _ltc3()
                        _url3 = _cfg3.get("antigravity_url","http://localhost:8045/v1/chat/completions")
                        _models_url = _url3.replace("/chat/completions","").rstrip("/") + "/models"
                        r2 = _req_ag.get(_models_url, timeout=3,
                                         headers={"Authorization":f"Bearer {_cfg3.get('antigravity_api_key','')}"})
                        if r2.status_code == 200:
                            _ag_status_dot[0].set_content(
                                '<span id="ag-dot" style="width:9px;height:9px;border-radius:50%;'
                                'background:#10b981;display:inline-block;box-shadow:0 0 6px #10b981"></span>'
                            )
                            _ag_status_lbl[0].set_text("Çalışıyor ✓")
                            _ag_status_lbl[0].style(f"font-size:10px;color:#10b981;font-weight:700")
                            return
                    except Exception:
                        pass
                    _ag_status_dot[0].set_content(
                        '<span id="ag-dot" style="width:9px;height:9px;border-radius:50%;'
                        'background:#ef4444;display:inline-block"></span>'
                    )
                    _ag_status_lbl[0].set_text("Çalışmıyor — Antigravity Manager'ı başlatın")
                    _ag_status_lbl[0].style("font-size:10px;color:#ef4444;font-weight:600")
                    _ag_acct_lbl[0].set_text("")

            # Arkaplanda kontrol et (UI thread'ini bloklamasın)
            _th_ag.Thread(target=_check_ag_status, daemon=True).start()

            # ── API Ayarları (2 sütun) ─────────────────────────────────────
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px"):
                with ui.element("div"):
                    ui.html(f'<div style="font-size:9px;font-weight:700;color:{_ag_magenta};margin-bottom:4px;letter-spacing:1px">🌐 API URL</div>')
                    from ng_config import load_trans_cfg as _ltc_ag, save_trans_cfg as _stc_ag
                    _ag_cur_url = _ltc_ag().get("antigravity_url", "http://localhost:8045/v1/chat/completions")
                    ag_url_inp = ui.input(value=_ag_cur_url).style(
                        f"width:100%;background:rgba(0,0,0,0.4);color:#e2e8f0;"
                        f"border:1px solid {_ag_magenta}44;border-radius:8px;padding:6px 10px;font-size:11px;font-family:monospace"
                    )
                    def on_ag_url_change(e):
                        v = ag_url_inp.value.strip()
                        if v:
                            _cfg = _ltc_ag(); _cfg["antigravity_url"] = v; _stc_ag(_cfg)
                    ag_url_inp.on("blur", on_ag_url_change)

                with ui.element("div"):
                    ui.html(f'<div style="font-size:9px;font-weight:700;color:{_ag_magenta};margin-bottom:4px;letter-spacing:1px">🔑 API KEY</div>')
                    _ag_cur_key = _ltc_ag().get("antigravity_api_key", "")
                    _ag_key_display = (_ag_cur_key[:8] + "..." + _ag_cur_key[-6:]) if len(_ag_cur_key) > 16 else _ag_cur_key
                    ag_key_inp = ui.input(value=_ag_key_display, password=False).style(
                        f"width:100%;background:rgba(0,0,0,0.4);color:#e2e8f0;"
                        f"border:1px solid {_ag_magenta}44;border-radius:8px;padding:6px 10px;font-size:11px;font-family:monospace"
                    )
                    def on_ag_key_change(e):
                        v = ag_key_inp.value.strip()
                        if v and "..." not in v:  # Maskelenmiş değer değilse kaydet
                            _cfg = _ltc_ag(); _cfg["antigravity_api_key"] = v; _stc_ag(_cfg)
                    ag_key_inp.on("blur", on_ag_key_change)

            # ── AG Model Hızlı Seç ─────────────────────────────────────────
            ui.html(f'<div style="font-size:9px;font-weight:700;color:{_ag_magenta};margin-bottom:6px;letter-spacing:1px">🤖 AG MODEL HIZLI SEÇ</div>')
            _ag_model_map = {
                "⚡ Gemini 2.5 Flash (Hızlı)":           "gemini-2.5-flash",
                "🧠 Gemini 2.5 Pro (Kaliteli)":          "gemini-2.5-pro",
                "⚡ Gemini 3 Flash (En Hızlı)":          "gemini-3-flash",
                "🏆 Gemini 3 Pro High (En Kaliteli)":    "gemini-3-pro-high",
                "🎯 Gemini 3 Pro Low (Dengeli)":         "gemini-3-pro-low",
                "🌟 Gemini 3.1 Pro High (Premium)":      "gemini-1.1-pro-high",
                "🌟 Gemini 3.1 Pro Low (Premium Hızlı)": "gemini-1.1-pro-low",
                "🎭 Claude Sonnet 4.6":                  "claude-sonnet-4-6",
                "🎭 Claude Opus 4.6 Thinking":           "claude-opus-4-6-thinking",
            }

            _cur_model = prefs.get("ai_model","")
            # Mevcut model AG mi?
            _cur_ag_label = next((lbl for lbl, mid in _ag_model_map.items() if mid == _cur_model), None)
            with ui.element("div").style("display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px"):
                for _lbl, _mid in _ag_model_map.items():
                    _is_selected = (_mid == _cur_model)
                    _chip_style = (
                        f"padding:5px 10px;border-radius:99px;font-size:11px;font-weight:600;"
                        f"cursor:pointer;transition:all 0.2s;border:1px solid {_ag_magenta};"
                        + (f"background:{_ag_magenta};color:#fff;" if _is_selected
                           else f"background:{_ag_magenta_d};color:{_ag_magenta};")
                    )
                    def _make_ag_chip(label=_lbl, model_id=_mid):
                        chip = ui.html(f'<div style="{_chip_style}">{label}</div>')
                        def _select_ag_model(c=chip, lid=label, mid=model_id):
                            from ng_config import save_prefs as _sp3
                            prefs["ai_model"] = mid
                            prefs["simple_mode"] = False   # AG kendi yönetir
                            # BAN ÖNLEME: 43 hesap × 8 RPM = 344 RPM — güvenli limit
                            prefs["account_rpm_limit"]   = 8
                            prefs["batch_delay_seconds"] = 2.5  # İnsani görünüm için
                            _sp3(prefs)
                            model_sel.set_value(mid)
                            rpm_lbl.set_text(str(8))
                            rpm_sl.set_value(8)
                            bdel_lbl.set_text("2.5")
                            bdel_sl.set_value(2.5)
                            ui.notify(f"✅ {lid} seçildi — Antigravity aktif (RPM=8, Delay=2.5sn)", type="positive", timeout=4000)
                        chip.on("click", _select_ag_model)
                    _make_ag_chip()

            # ── Ban Önleme Bilgi Kutusu ────────────────────────────────────
            ui.html(
                f'<div style="background:rgba(217,70,239,0.08);border:1px solid {_ag_magenta}33;'
                f'border-radius:8px;padding:8px 12px;font-size:10px;color:#d1d5db;line-height:1.7">'
                f'<b style="color:{_ag_magenta}">🛡 Ban Önleme:</b> '
                f'Antigravity <b>43 hesaba</b> yük dağıtır. '
                f'43 × 8 RPM = <b>344 RPM</b> güvenli kapasite. '
                f'Model seçince <b>RPM=8, Delay=2.5sn</b> otomatik uygulanır. '
                f'<b>Ana Gmail hesabını bağlama</b> — sadece burner/test hesaplar kullan! '
                f'<br><span style="color:#f59e0b">⚠ User-Agent Override: Antigravity Manager arayüzünde aktif et.</span>'
                f'</div>'
            )

            # ── Güvenli AG Ayarları Butonu ─────────────────────────────────
            with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;margin-top:8px"):
                def _apply_safe_ag_settings():
                    from ng_config import save_prefs as _sp4, save_trans_cfg as _stc4, load_trans_cfg as _ltc4
                    # Güvenli RPM + Delay
                    prefs["account_rpm_limit"]   = 8
                    prefs["batch_delay_seconds"] = 2.5
                    prefs["simple_mode"]         = False  # AG kendi yönetir
                    _sp4(prefs)
                    _tc4 = _ltc4()
                    _tc4["batch_delay_seconds"] = 2.5
                    _stc4(_tc4)
                    # Slider'ları güncelle
                    rpm_lbl.set_text("8")
                    rpm_sl.set_value(8)
                    bdel_lbl.set_text("2.5")
                    bdel_sl.set_value(2.5)
                    ui.notify("🛡 Güvenli AG ayarları uygulandı: RPM=8, Delay=2.5sn", type="positive", timeout=4000)

                nbtn("🛡 Güvenli Ayarları Uygula", click=_apply_safe_ag_settings,
                     variant="ghost", size="sm")
                def _refresh_ag():
                    _ag_status_lbl[0].set_text("Kontrol ediliyor...")
                    _ag_status_lbl[0].style("font-size:10px;color:#9ca3af;font-weight:600")
                    _th_ag.Thread(target=_check_ag_status, daemon=True).start()
                nbtn("🔄 Durumu Yenile", click=_refresh_ag, variant="ghost", size="sm")

        _sub = C["SUB"]

        with ui.element("div").classes("card").style("padding:12px 16px"):
            ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:{_sub};margin-bottom:8px">⚡ SEÇENEKLER</div>')
            with ui.element("div").style("display:flex;flex-wrap:wrap;gap:8px"):
                _opt_items = [
                    ("use_fandom_glossary",    "📚 Fandom Sözlük",      True),
                    ("generate_html_report",   "📊 HTML Rapor",          True),
                    ("use_episode_context",    "🔗 Bölüm Bağlamı",      True),
                    ("force_translate",        "🔄 Zorla Çevir",          True),
                    ("nsfw_mode",              "🔞 NSFW Modu",            False),
                    ("protect_positioning",    "📌 Konum Koru",           True),
                    ("only_english",           "🇬🇧 Sadece İngilizce",    True),
                    ("romaji_block",           "🈲 Romaji Bloğu",         True),
                    ("natural_dialogue",       "💬 Doğal Diyalog",        True),
                    ("clean_sub",              "🧹 Altyazı Temizle",     True),
                    ("content_detect",         "🔍 İçerik Tespiti",       True),
                    ("simple_mode",            "⚡ Basit Mod",             True),
                    # ── Yeni eklenenler ──
                    ("rescue_pass",              "🚑 Kurtarma Geçişi",        True),
                    ("smart_merge",              "🔀 Akıllı Birleştir",        True),
                    ("use_song_lyrics_pass",     "🎵 Şarkı Geçişi",            True),
                    ("translate_song_lyrics",    "🎶 Şarkı Çevir",             True),
                    ("use_karaoke_collapse",     "🎤 Karaoke Birleştir",       True),
                    ("use_style_suffix_detection","🏷 Stil Soneki Tespiti",  True),
                    ("translate",                "🔤 Çeviriyi Etkinleştir",     True),
                    ("hentai_glossary",          "🔞 Yetişkin Sözlük",        False),
                    ("force_no_style",           "📹 Sadece İçerik Analizi",    False),
                    ("ignore_song_style_for_romaji", "🎵 Romaji Stil Yoksay", False),
                ]
                _act_s = "display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:12px;font-weight:600;background:color-mix(in srgb,var(--accent1) 20%,transparent);border:1px solid color-mix(in srgb,var(--accent1) 55%,transparent);color:var(--accent1)"
                _ina_s = f"display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:12px;font-weight:600;background:{_panel};border:1px solid {_border};color:{_muted}"
                for opt_key, opt_lbl, opt_def in _opt_items:
                    val = [prefs.get(opt_key, opt_def)]
                    def make_chip(k, v, lbl, a=_act_s, i=_ina_s):
                        da = '<span style="width:7px;height:7px;border-radius:50%;background:var(--accent1);flex-shrink:0"></span>'
                        di = f'<span style="width:7px;height:7px;border-radius:50%;background:{_muted};flex-shrink:0"></span>'
                        chip = ui.html(f'<div style="{a if v[0] else i}">{da if v[0] else di}{lbl}</div>')
                        def toggle(c=chip, k=k, v=v, a=a, i=i, da=da, di=di, l=lbl):
                            from ng_config import save_prefs as _sp2
                            v[0] = not v[0]; prefs[k] = v[0]
                            if k == "romaji_block":
                                prefs["skip_romaji_mode"] = v[0]
                            _sp2(prefs)
                            c.set_content(f'<div style="{a if v[0] else i}">{da if v[0] else di}{l}</div>')
                        chip.on("click", toggle)
                    make_chip(opt_key, val, opt_lbl)

        # ── 3b. GELİŞMİŞ AYARLAR (max_byte_batch, max_retries, line_merge_mode) ──────
        _orange = C.get("ORANGE", "#f97316")
        with ui.element("div").classes("card").style("padding:12px 16px"):
            ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.2px;color:{_orange};margin-bottom:10px">🔧 GELİŞMİŞ AYARLAR</div>')
            with ui.element("div").style("display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start"):

                # max_byte_batch slider
                with ui.element("div").style("display:flex;flex-direction:column;gap:4px;min-width:200px"):
                    with ui.element("div").style("display:flex;justify-content:space-between;margin-bottom:2px"):
                        ui.html(f'<span style="font-size:10px;font-weight:700;color:{_purple}">📦 BYTE BATCH</span>')
                        mbb_lbl = ui.label(str(prefs.get("max_byte_batch", 2000))).style(
                            f"font-size:12px;font-weight:800;color:{_purple}")
                    mbb_sl = ui.slider(min=500, max=6000, step=500, value=prefs.get("max_byte_batch", 2000)).style("width:200px")
                    def on_mbb_change(e):
                        from ng_config import save_prefs as _sp5
                        v = int(e.args); mbb_lbl.set_text(str(v))
                        prefs["max_byte_batch"] = v; _sp5(prefs)
                    mbb_sl.on("update:model-value", on_mbb_change)

                # max_retries slider
                with ui.element("div").style("display:flex;flex-direction:column;gap:4px;min-width:140px"):
                    with ui.element("div").style("display:flex;justify-content:space-between;margin-bottom:2px"):
                        ui.html(f'<span style="font-size:10px;font-weight:700;color:{_yellow}">🔁 MAX RETRY</span>')
                        mrt_lbl = ui.label(str(prefs.get("max_retries", 6))).style(
                            f"font-size:12px;font-weight:800;color:{_yellow}")
                    mrt_sl = ui.slider(min=1, max=15, step=1, value=prefs.get("max_retries", 6)).style("width:140px")
                    def on_mrt_change(e):
                        from ng_config import save_prefs as _sp6
                        v = int(e.args); mrt_lbl.set_text(str(v))
                        prefs["max_retries"] = v; _sp6(prefs)
                    mrt_sl.on("update:model-value", on_mrt_change)

                # line_merge_mode dropdown
                with ui.element("div").style("display:flex;flex-direction:column;gap:4px"):
                    ui.html(f'<span style="font-size:10px;font-weight:700;color:{_green}">🔀 SATIR BİRLEŞTİRME</span>')
                    _lmm_opts = ["default", "aggressive", "conservative", "none"]
                    lmm_sel = ui.select(
                        options=_lmm_opts,
                        value=prefs.get("line_merge_mode", "default"),
                        label=""
                    ).style("min-width:160px")
                    def on_lmm_change(e):
                        from ng_config import save_prefs as _sp7
                        v = e.args if isinstance(e.args, str) else lmm_sel.value
                        if v: prefs["line_merge_mode"] = v; _sp7(prefs)
                    lmm_sel.on("update:model-value", on_lmm_change)

        # ── 3c. ÇIKTI FORMAT + DOSYA ARASI GECİKME ──────────────────────────────
        with ui.element("div").classes("card").style("padding:10px 16px"):
            with ui.element("div").style("display:flex;align-items:center;gap:14px;flex-wrap:wrap"):
                # Sub format buton grubu
                ui.html(f'<span style="font-size:10px;font-weight:700;color:{_muted};letter-spacing:1px">📁 ÇIKTI</span>')
                _fmt_cur = [prefs.get("sub_format", "ASS")]
                _fmt_btns = {}
                for _fmt in ["ASS", "SRT", "VTT", "ALL"]:
                    _is_sel = _fmt_cur[0].upper() == _fmt
                    _fs = (f"padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;"
                           f"background:{'color-mix(in srgb,var(--accent1) 22%,transparent)' if _is_sel else _panel};"
                           f"border:1px solid {'var(--accent1)' if _is_sel else _border};"
                           f"color:{'var(--accent1)' if _is_sel else _muted}")
                    _btn = ui.html(f'<div style="{_fs}">{_fmt}</div>')
                    _fmt_btns[_fmt] = _btn
                def _set_fmt(f, cur=_fmt_cur, btns=_fmt_btns):
                    from ng_config import save_prefs as _sp3
                    cur[0] = f; prefs["sub_format"] = f; _sp3(prefs)
                    for _f2, _b2 in btns.items():
                        _sel2 = _f2 == f
                        _fs2 = (f"padding:4px 12px;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;"
                                f"background:{'color-mix(in srgb,var(--accent1) 22%,transparent)' if _sel2 else _panel};"
                                f"border:1px solid {'var(--accent1)' if _sel2 else _border};"
                                f"color:{'var(--accent1)' if _sel2 else _muted}")
                        _b2.set_content(f'<div style="{_fs2}">{_f2}</div>')
                for _fmt in ["ASS", "SRT", "VTT", "ALL"]:
                    _fmt_btns[_fmt].on("click", lambda e, f=_fmt: _set_fmt(f))

                # Dosya arası gecikme slider
                ui.html(f'<span style="font-size:10px;font-weight:700;color:{_muted};letter-spacing:1px;margin-left:8px">⏱ DOSYA ARASI</span>')
                _pfd_cur = [prefs.get("per_file_delay", 15)]
                pfd_lbl = ui.label(str(int(_pfd_cur[0])) + " sn").style(f"font-size:11px;font-weight:700;color:{C['GREEN']};min-width:36px")
                pfd_sl = ui.slider(min=0, max=120, step=5, value=_pfd_cur[0]).style("width:120px")
                def on_pfd_change(e, cur=_pfd_cur):
                    from ng_config import save_prefs as _sp4
                    v = int(e.args); cur[0] = v
                    pfd_lbl.set_text(str(v) + " sn")
                    prefs["per_file_delay"] = v; _sp4(prefs)
                pfd_sl.on("update:model-value", on_pfd_change)

        from ng_config import load_trans_cfg as _ltc
        _tcfg = _ltc()
        _pp = (_tcfg.get("system_prompt", "") or "")[:90]
        if _pp:
            _pp_esc = _pp.replace("<","&lt;").replace(">","&gt;")
            ui.html(
                f'<div style="background:#080912;border:1px solid {_border};border-radius:10px;'
                f'padding:8px 14px;display:flex;align-items:center;gap:10px;overflow:hidden">'
                f'<span style="font-size:10px;font-weight:700;color:{_muted};white-space:nowrap">💬 PROMPT</span>'
                f'<span style="font-family:Consolas,monospace;font-size:11px;color:{_cyan2};overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">{_pp_esc}...</span>'
                f'<span style="font-size:10px;color:{_muted};white-space:nowrap">→ Settings</span></div>'
            )

        # ── 5. PROGRESS ──────────────────────────────────────────────────────────
        prog_wrap = ui.html(
            '<div id="nx-prog-wrap" style="display:none">'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">'
            f'<span style="font-size:10px;font-weight:700;letter-spacing:1px;color:{_muted}">İLERLEME</span>'
            '<span id="nx-prog-lbl" style="font-size:10px;color:{_muted}"></span>'
            '</div>'
            '<div style="width:100%;height:8px;border-radius:4px;background:rgba(255,255,255,0.07);overflow:hidden">'
            '<div id="nx-prog-bar" style="height:100%;width:0%;border-radius:4px;'
            'background:linear-gradient(90deg,var(--accent1),var(--accent2));'
            'transition:width 0.4s ease;box-shadow:0 0 8px color-mix(in srgb,var(--accent1) 60%,transparent)">'
            '</div></div></div>'
        )
        # Proxy nesnesi — do_start/do_stop/do_qa eski prog API'sini çağırıyor
        class _ProgProxy:
            def set_value(self, v):
                pct = int(v * 100)
                ui.run_javascript(
                    f"var b=document.getElementById('nx-prog-bar');if(b)b.style.width='{pct}%';"
                    f"var w=document.getElementById('nx-prog-wrap');if(w)w.style.display='{'' if v>0 else 'none'}';"
                )
        prog = _ProgProxy()
        class _LblProxy:
            def set_text(self, t):
                ui.run_javascript(
                    f"var l=document.getElementById('nx-prog-lbl');if(l)l.textContent={__import__('json').dumps(t)};"
                )
        prog_lbl = _LblProxy()

        # ── 6. AKSIYON BUTONLARI ─────────────────────────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr auto auto auto;gap:8px;align-items:center"):
            start_btn = nbtn("▶  ÇEVİRİYİ BAŞLAT", size="lg", style="width:100%")
            stop_btn  = nbtn("■  Durdur",      variant="ghost",   size="lg")
            qa_btn    = nbtn("✅  QA Kontrol",  variant="success", size="lg")
            reset_btn = nbtn("🔄", variant="danger", size="sm",
                             style="width:40px;height:40px;padding:0;border-radius:50%;flex-shrink:0")

        # ── 7. CANLI LOG ──────────────────────────────────────────────────────────
        import html as _html_mod, json as _json_mod
        _existing = state.get("log_lines", [])
        _init_text = "\n".join(_existing[-500:]) if _existing else "[ Sistem hazir -- dosya secip ceviriyi baslatabilirsiniz ]"
        _init_html = _html_mod.escape(_init_text)

        ui.html(
            f'<div style="border-radius:12px 12px 0 0;background:rgba(8,9,18,0.95);'
            f'border:1px solid {_border};border-bottom:none;'
            f'padding:8px 14px;display:flex;align-items:center;gap:8px">'
            f'<span style="width:10px;height:10px;border-radius:50%;background:#ef4444;flex-shrink:0"></span>'
            f'<span style="width:10px;height:10px;border-radius:50%;background:#f59e0b;flex-shrink:0"></span>'
            f'<span style="width:10px;height:10px;border-radius:50%;background:#10b981;flex-shrink:0"></span>'
            f'<span style="font-size:11px;font-weight:600;color:#6b7280;margin-left:4px">🖥 ceviri motoru — canlı log</span>'
            f'<span style="font-size:10px;color:#374151;margin-left:auto">(metin seç → CTRL+C)</span>'
            f'<button id="nx-autoscroll-btn" '
            f'title="Otomatik kaydırmayı aç/kapat" '
            f'style="background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.4);'
            f'color:#10b981;border-radius:6px;padding:2px 8px;font-size:11px;'
            f'cursor:pointer;font-family:inherit;transition:all 0.2s">&#9660; Scroll</button>'
            f'</div>'
            f'<div id="nx-log-wrap" style="height:260px;overflow-y:auto;background:#080912;'
            f'border:1px solid {_border};border-top:none;border-radius:0 0 12px 12px;'
            f'padding:12px 16px;cursor:text;user-select:text;-webkit-user-select:text">'
            f'<pre id="nx-log-pre" style="margin:0;white-space:pre-wrap;word-break:break-all;'
            f'font-family:Consolas,monospace;font-size:12px;color:{_cyan2};'
            f'line-height:1.55;user-select:text">{_init_html}</pre>'
            f'</div>'
        )

        class _LogProxy:
            def push(self, msg):
                _m = str(msg).replace("\x0c","").replace("\r","").strip()
                if _m:
                    ll = state.setdefault("log_lines", [])
                    ll.append(_m)
                    if len(ll) > 800: del ll[:len(ll)-800]
                    ui.run_javascript(f"if(window.nxLogPush) window.nxLogPush({_json_mod.dumps(_m)})")
            def clear(self):
                state["log_lines"] = []
                ui.run_javascript("(function(){var p=document.getElementById('nx-log-pre');if(p)p.textContent='';})();")
        log_el = _LogProxy()
        log_box[0] = log_el

        def _define_log_js():
            ui.run_javascript(
                "window.nxAutoScroll = true;"
                "window.nxToggleAutoScroll = function() {"
                "  window.nxAutoScroll = !window.nxAutoScroll;"
                "  var btn = document.getElementById('nx-autoscroll-btn');"
                "  if(btn) {"
                "    if(window.nxAutoScroll) {"
                "      btn.innerHTML = '&#9660; Scroll';"
                "      btn.style.background = 'rgba(16,185,129,0.15)';"
                "      btn.style.borderColor = 'rgba(16,185,129,0.4)';"
                "      btn.style.color = '#10b981';"
                "      var w=document.getElementById('nx-log-wrap');if(w)w.scrollTop=w.scrollHeight;"
                "    } else {"
                "      btn.innerHTML = '&#128205; Dondur';"
                "      btn.style.background = 'rgba(245,158,11,0.15)';"
                "      btn.style.borderColor = 'rgba(245,158,11,0.4)';"
                "      btn.style.color = '#f59e0b';"
                "    }"
                "  }"
                "};"
                # Event listener programatik bagla (Vue onclick'i strip ediyor)
                "var _asBtn=document.getElementById('nx-autoscroll-btn');"
                "if(_asBtn) _asBtn.addEventListener('click', window.nxToggleAutoScroll);"
                "window.nxLogPush=function(t){"
                "var p=document.getElementById('nx-log-pre');"
                "var w=document.getElementById('nx-log-wrap');"
                "if(!p||!w)return;"
                "p.textContent+=(p.textContent?'\\n':'')+t;"
                "var l=p.textContent.split('\\n');"
                "if(l.length>520){p.textContent=l.slice(l.length-500).join('\\n');}"
                "if(window.nxAutoScroll !== false) w.scrollTop=w.scrollHeight;"
                "};"
                "var w=document.getElementById('nx-log-wrap');if(w)w.scrollTop=w.scrollHeight;"
            )
        ui.timer(0.4, _define_log_js, once=True)

        _log_ansi = __import__("re").compile(r"\x1b\[[0-9;]*[mGKHF]")
        def _page_log_poll():
            import json as _j
            q = state.get("log_q")
            if not q: return
            batch = []
            try:
                for _ in range(200):
                    raw = q.get_nowait()
                    if raw is None: continue
                    line = _log_ansi.sub("", str(raw)).strip()
                    line = line.replace("\x0c","").replace("\r","").strip()
                    if line: batch.append(line)
            except Exception: pass
            if batch:
                ll = state.setdefault("log_lines", [])
                ll.extend(batch)
                if len(ll) > 800: del ll[:len(ll)-800]
                ui.run_javascript(f"if(window.nxLogPush) window.nxLogPush({_j.dumps(chr(10).join(batch))})")

                # ── Ses tetikleyici — log pattern → NexusSound ──────────────
                _sound_js = None
                for _ln in batch:
                    _lu = _ln.upper()
                    # Başarı: returncode=0 veya TAMAMLANDI / BASARI / DONE
                    if "[BITTI] RETURNCODE=0" in _lu:
                        _sound_js = "NexusSound.success()"; break
                    # Hata: returncode!=0 veya CRITICAL ERROR / READER ERR
                    elif "[BITTI] RETURNCODE=" in _lu:   # non-zero
                        _sound_js = "NexusSound.error()"; break
                    elif any(k in _lu for k in ("[CRITICAL ERROR]", "[READER ERR]", "[READER2 ERR]")):
                        _sound_js = "NexusSound.error()"; break
                    elif any(k in _lu for k in ("HATA:", "[ HATA ]", "[HATA]")):
                        if not _sound_js: _sound_js = "NexusSound.error()"
                    # Başlatma: translator process başladı
                    elif "[BASLATILIYOR]" in _lu or "OTOMATIK ISLEM BASLIYOR" in _lu:
                        if not _sound_js: _sound_js = "NexusSound.powerUp()"
                    elif "[OK] PID=" in _lu and "BASLATILDI" in _lu:
                        if not _sound_js: _sound_js = "NexusSound.powerUp()"
                    # Durdurma / iptal
                    elif "DURDURULDU" in _lu:
                        if not _sound_js: _sound_js = "NexusSound.powerDown()"
                    # Bildirim: dosya bulundu, sıradaki dosya, wiki vb
                    elif any(k in _lu for k in ("BULUNAN DOSYALAR", "[SIRADAKI]", "[BILGI]",
                                                  "WIKI GUNCELLENDI", "SOZLUK GUNCELLENDI")):
                        if not _sound_js: _sound_js = "NexusSound.notify()"
                    # Log tick: hafif tick (sadece aktif process satırları için %12 ihtimalle)
                    elif state.get("running") and _ln and not _ln.startswith("="):
                        if not _sound_js: _sound_js = "NexusSound.logTick()"

                if _sound_js:
                    ui.run_javascript(f"if(window.NexusSound){{ {_sound_js} }}")

                # ── Glossary log izleyici — bildirim ────────────────────────
                # "[Glossary] 'X' → 420 terim Gemini'ye gönderildi" gibi satırlar
                for _ln in batch:
                    _lu = _ln.upper()
                    if "[GLOSSARY]" in _lu and ("TERİM" in _lu or "TERIM" in _lu or "WIKI" in _lu):
                        # Çok kısa/hatalı satırlar geç
                        if len(_ln.strip()) > 15:
                            ui.notify(
                                f"📚 {_ln.strip()[:100]}",
                                type="positive", timeout=5000, position="top-right"
                            )
                            break  # Bir batch'te max 1 bildirim
                # ────────────────────────────────────────────────────────────

        def _proc_done_watcher():
            if state.get("_proc_done"):
                state["_proc_done"] = False
                pending = state.get("_pending_paths", [])
                if pending:
                    # Sonraki dosyayı otomatik başlat
                    next_path = pending.pop(0)
                    state["_pending_paths"] = pending
                    _lq("=" * 56)
                    _lq(f"[SIRADAKI] {os.path.basename(next_path)} başlatılıyor...")
                    _lq("=" * 56)
                    env = os.environ.copy()
                    env["PYTHONUNBUFFERED"] = "1"; env["PYTHONIOENCODING"] = "utf-8"; env["NO_COLOR"] = "1"
                    import subprocess as _sp2, threading as _th2
                    _script2 = SCRIPT_TRANSLATOR
                    proc2 = _sp2.Popen(
                        ["python", "-u", _script2, next_path],
                        stdout=_sp2.PIPE, stderr=_sp2.STDOUT, stdin=_sp2.DEVNULL,
                        cwd=os.path.dirname(_script2), env=env,
                        text=False, bufsize=0, creationflags=0x08000000,
                    )
                    state["proc"] = proc2; state["running"] = True
                    def _reader2(proc=proc2):
                        import re as _re2
                        _ansi2 = _re2.compile(rb'\x1b\[[0-9;]*[mGKHF]')
                        try:
                            buf = b""
                            while True:
                                chunk = proc.stdout.read(256)
                                if not chunk: break
                                buf += chunk
                                while b"\n" in buf:
                                    lb, buf = buf.split(b"\n", 1)
                                    ls = _ansi2.sub(b"", lb).decode("utf-8", errors="replace").strip()
                                    if ls: state["log_q"].put(ls)
                        except Exception as ex:
                            state["log_q"].put(f"[READER2 ERR] {ex}")
                        finally:
                            try: proc.wait(timeout=30)
                            except Exception: pass
                            state["running"] = False; state["proc"] = None; state["_proc_done"] = True
                    _th2.Thread(target=_reader2, daemon=True).start()
                else:
                    # Tüm dosyalar bitti
                    prog.set_value(1.0)
                    prog_lbl.set_text("Tamamlandı ✓")
                    # Start butonunu tekrar aktif et
                    start_btn.props(remove="disabled")
                    start_btn.style("opacity:1;cursor:pointer")
                    ui.notify("İşlem tamamlandı!", type="positive")
                    # ── HTML raporları merkezi klasöre kopyala ─────────────
                    try:
                        _src = state.get("path", "").strip()
                        _copied = collect_html_reports(_src)
                        if _copied:
                            _lq(f"[RAPORLAR] {len(_copied)} HTML rapor 'reports/' klasörüne kopyalandı")
                            for _c in _copied:
                                _lq(f"  ✔ {os.path.basename(_c)}")
                            ui.notify(
                                f"📄 {len(_copied)} HTML rapor 'reports/' klasörüne kopyalandı",
                                type="info", timeout=5000
                            )
                    except Exception as _ce:
                        _lq(f"[UYARI] Rapor kopyalama hatası: {_ce}")
        ui.timer(0.5, _proc_done_watcher)
        ui.timer(0.2, _page_log_poll)

        # ── Bildirim Bus Poller — pipeline'dan gelen push_notif'leri göster ──
        def _notif_bus_poll():
            try:
                import sys as _sys, os as _os
                # notif_bus modülünü doğrudan içe aktar (NiceGUI'nın çalıştığı klasörde)
                _nb_path = _os.path.join(_os.path.dirname(__file__), '..', 'notif_bus.py')
                _nb_path = _os.path.normpath(_nb_path)
                if _nb_path not in _sys.path and _os.path.dirname(_nb_path) not in _sys.path:
                    _sys.path.insert(0, _os.path.dirname(_nb_path))
                from notif_bus import flush_notifs
                for _n in flush_notifs():
                    _msg  = _n.get('msg', '')
                    _type = _n.get('type', 'info')
                    _to   = _n.get('timeout', 4000)
                    if _msg:
                        ui.notify(_msg, type=_type, timeout=_to, position='top-right')
            except Exception:
                pass
        ui.timer(1.5, _notif_bus_poll)
        # ──────────────────────────────────────────────────────────────────────

        if state["running"] and state.get("proc") is None:
            state["running"] = False


        def do_start():
            import subprocess, threading

            _q = state.get("log_q")
            def _lq(msg):
                if _q: _q.put(msg)

            try:
                # Stuck state auto-fix
                if state["running"] and state.get("proc") is None:
                    state["running"] = False
                    _lq("[AUTO-RESET] State temizlendi")

                if state["running"]:
                    ui.notify("Baska islem calisiyor!", type="warning"); return

                # Butonu disable et — cift tiklama onlemek icin
                start_btn.props(add="disabled")
                start_btn.style("opacity:0.55;cursor:not-allowed")
                ui.run_javascript("if(window.NexusSound) NexusSound.powerUp()")

                path_raw = state.get("path", "").strip() or path_inp.value.strip()
                if not path_raw:
                    ui.notify("Dosya/klasör seçin!", type="negative")
                    start_btn.props(remove="disabled"); start_btn.style("opacity:1;cursor:pointer")
                    return

                # Çoklu dosya seçimi: ";" ile ayrılmış birden fazla yol
                paths = [p.strip() for p in path_raw.split(";") if p.strip()]
                # Translator sadece 1 arg alıyor — klasörse direkt, dosyaysa ilkini kullan
                # (birden fazla dosya varsa her biri sırayla ayrı process olarak çalıştırılacak)
                path = paths[0]

                state["running"] = True
                _lq("=" * 56)
                if len(paths) > 1:
                    _lq(f"[BASLATILIYOR] {len(paths)} dosya sırayla işlenecek")
                    for i, p in enumerate(paths):
                        _lq(f"  [{i+1}] {p}")
                else:
                    _lq(f"[BASLATILIYOR] {path}")
                _lq("=" * 56)

                env = os.environ.copy()
                env["PYTHONUNBUFFERED"]  = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                env["NO_COLOR"]         = "1"

                _script = SCRIPT_TRANSLATOR
                _cwd    = os.path.dirname(_script)

                # ── Komut argümanı oluştur ───────────────────────────────────
                if len(paths) == 1:
                    # Tek yol: klasör veya dosya → direkt geç
                    path_arg  = paths[0]
                    cmd_args  = ["python", "-u", _script, path_arg]
                    state["_pending_paths"] = []
                    if os.path.isdir(path_arg):
                        _lq(f"[KLASÖR] {path_arg}")
                        _lq("  → Tüm alt dosyalar taranacak, bağlam korunacak")
                    else:
                        _lq(f"[DOSYA] {os.path.basename(path_arg)}")
                else:
                    # Çoklu dosya → --files modu: TEK process, TAM bağlam!
                    cmd_args = ["python", "-u", _script, "--files"] + paths
                    state["_pending_paths"] = []   # queue artık gerekli değil
                    _lq(f"[TOPLU ÇALIŞMA] {len(paths)} dosya — TEK process, bağlam/context KORUNUYOR")
                    for i, p in enumerate(paths, 1):
                        _lq(f"  [{i:02d}] {os.path.basename(p)}")
                    _lq("─" * 40)

                _lq(f"[DEBUG] CMD: python -u {os.path.basename(_script)} {cmd_args[3] if len(cmd_args)>3 else ''} ...")

                proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    cwd=_cwd,
                    env=env,
                    text=False,
                    bufsize=0,
                    creationflags=0x08000000,
                )
                state["proc"] = proc
                _lq(f"[OK] PID={proc.pid} baslatildi, output bekleniyor...")

                def _reader():
                    import re as _re
                    _ansi = _re.compile(rb'\x1b\[[0-9;]*[mGKHF]')
                    try:
                        buf = b""
                        while True:
                            chunk = proc.stdout.read(256)
                            if not chunk:
                                break
                            buf += chunk
                            while b"\n" in buf:
                                line_b, buf = buf.split(b"\n", 1)
                                line_b = _ansi.sub(b"", line_b)
                                line_s = line_b.decode("utf-8", errors="replace").strip()
                                line_s = line_s.replace("\x0c", "").replace("\r", "")
                                if line_s:
                                    state["log_q"].put(line_s)
                        if buf:
                            line_s = _ansi.sub(b"", buf).decode("utf-8", errors="replace").strip()
                            if line_s:
                                state["log_q"].put(line_s)
                    except Exception as ex:
                        state["log_q"].put(f"[READER ERR] {ex}")
                    finally:
                        try: proc.wait(timeout=30)
                        except Exception: pass
                        rc = proc.returncode
                        state["log_q"].put("=" * 56)
                        state["log_q"].put(f"[BITTI] returncode={rc}")
                        # UI updates via flag — NOT direct call from thread
                        state["running"] = False
                        state["proc"]    = None
                        state["_proc_done"] = True

                threading.Thread(target=_reader, daemon=True).start()

            except Exception as _ex:
                import traceback
                _lq(f"[CRITICAL ERROR] {_ex}")
                _lq(traceback.format_exc()[:500])
                state["running"] = False
                state["proc"]    = None
                # Hata durumunda da butonu geri ac
                start_btn.props(remove="disabled")
                start_btn.style("opacity:1;cursor:pointer")

        def do_stop():
            proc = state.get("proc")
            if proc:
                try: proc.terminate()
                except Exception: pass
            state["running"]        = False
            state["proc"]           = None
            state["_pending_paths"] = []    # Bekleyen dosyaları iptal et
            state["_proc_done"]     = False
            _stop_msg = "■ Durduruldu — Tekrar başlatabilirsiniz"
            log_el.push(_stop_msg)
            state.setdefault("log_lines", []).append(_stop_msg)
            prog.set_value(0)
            # Start butonunu geri aç
            start_btn.props(remove="disabled")
            start_btn.style("opacity:1;cursor:pointer")
            ui.run_javascript("if(window.NexusSound) NexusSound.powerDown()")
            ui.notify("Durduruldu", type="info")

        def do_qa():
            import re as _re, queue as _queue, threading, subprocess
            _ansi = _re.compile(r'\x1b\[[0-9;]*[mGKHF]')
            # Stuck state auto-fix
            if state["running"] and state.get("proc") is None:
                state["running"] = False
            if state["running"]:
                ui.notify("Baska islem calisiyor!", type="warning"); return
            path = state.get("path", "").strip() or path_inp.value.strip()
            if not path:
                ui.notify("Dosya/klasor secin!", type="negative"); return
            state["running"] = True
            for _ql in ["=" * 56, f"QA KONTROL: {path}", "=" * 56]:
                log_el.push(_ql)
                state.setdefault("log_lines", []).append(_ql)
            _q  = _queue.Queue()
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            env["NO_COLOR"]         = "1"
            CW = 0x08000000 if os.name == "nt" else 0
            proc = subprocess.Popen(
                ["python", "-u", SCRIPT_QA, path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=os.path.dirname(SCRIPT_QA),
                env=env, text=True, encoding="utf-8",
                errors="replace", bufsize=1,
                creationflags=CW,
            )
            state["proc"] = proc
            def _reader():
                try:
                    for raw in proc.stdout: _q.put(raw.rstrip())
                except: pass
                finally:
                    proc.wait(); _q.put(None)
            threading.Thread(target=_reader, daemon=True).start()
            _timer = [None]
            def _poll():
                try:
                    for _ in range(50):
                        item = _q.get_nowait()
                        if item is None:
                            rc = proc.returncode
                            _done_msg = f"[OK] QA bitti — kod {rc}"
                            log_el.push(_done_msg)
                            state.setdefault("log_lines", []).append(_done_msg)
                            state["running"] = False; state["proc"] = None
                            state["_proc_done"] = True
                            if _timer[0]: _timer[0].cancel()
                            return
                        line = _ansi.sub("", item)
                        if line:
                            log_el.push(line)
                            state.setdefault("log_lines", []).append(line)
                except: pass
            _timer[0] = ui.timer(0.1, _poll)

        _reset_pending = [False]
        def do_reset():
            """Reset — cift tiklama onay gerektirir"""
            if not _reset_pending[0]:
                _reset_pending[0] = True
                ui.notify("⚠️ Log ve süreç sıfırlanacak — emin misiniz? Onaylamak için tekrar tıklayın!",
                          type="warning", timeout=3000)
                def _cancel():
                    _reset_pending[0] = False
                ui.timer(3.0, _cancel, once=True)
                return
            _reset_pending[0] = False
            proc = state.get("proc")
            if proc:
                try: proc.terminate()
                except Exception: pass
            state["running"]    = False
            state["proc"]       = None
            state["_proc_done"] = False
            state["log_lines"]  = []   # Log gecmisini temizle
            prog.set_value(0)
            prog_lbl.set_text("")
            log_el.clear()
            log_el.push("[ Sifirlandi -- yeni ceviriye hazir ]")
            # Start butonunu da geri ac
            start_btn.props(remove="disabled")
            start_btn.style("opacity:1;cursor:pointer")
            ui.notify("Sifirlandi, tekrar baslatabilirsiniz", type="positive")

        start_btn.on("click", do_start)
        stop_btn.on("click",  do_stop)
        reset_btn.on("click", do_reset)
        qa_btn.on("click",    do_qa)

        # ── ANTİGRAVİTY CANLI API İZLEME ──────────────────────────────────────
        _ag_logs_state = {
            "logs": [], 
            "paused": False, 
            "filter": "", 
            "filter_type": "Tümü", 
            "account_filter": "Tüm Hesaplar",
            "loading": False
        }

        # NiceGUI dialog for details
        with ui.dialog() as _ag_detail_dialog, ui.card().style("width:700px; max-width:90vw; background:#0d1117; color:#c9d1d9; border:1px solid #30363d"):
            _detail_title = ui.html("").style("font-size:16px; font-weight:bold; border-bottom:1px solid #30363d; padding-bottom:8px; width:100%")
            _detail_content = ui.html("").style("width:100%; display:flex; flex-direction:column; gap:12px")
            with ui.row().style("justify-content: flex-end; width:100%"):
                ui.button("Kapat", on_click=_ag_detail_dialog.close).props("flat").style("color:#58a6ff")

        def _show_log_detail(log_id):
            """İlgili log id'sine sahip kaydın detayını modalda açar."""
            _target = None
            for _l in _ag_logs_state["logs"]:
                if _l.get("id") == log_id:
                    _target = _l
                    break
            if not _target:
                return
            
            _st = _target.get("status", 0)
            _ok = 200 <= _st < 400
            _sc = "background:#00b074;color:#fff" if _ok else "background:#ea3838;color:#fff"
            _method = _target.get("method", "POST")
            _mdl = _target.get("model") or "-"
            _map = _target.get("mapped_model") or ""
            _mdl_str = f"{_mdl} =&gt; {_map}" if _map and _map != _mdl else _mdl
            _path = _target.get("url") or "-"
            _acc = _target.get("account_email") or "-"
            _dur = _target.get("duration") or 0
            
            # Detaylı request/response body çekimi için config'den url belirle
            import urllib.request as _ur, json as _jj, os as _os2
            _req_body = "Mevcut değil"
            _res_body = "Mevcut değil"
            try:
                cfg_path = _os2.path.expanduser(r"~\.antigravity_tools\gui_config.json")
                if _os2.path.exists(cfg_path):
                    with open(cfg_path, encoding="utf-8") as _f:
                        _cfg = _jj.load(_f)
                    _key = _cfg.get("proxy", {}).get("api_key", "")
                    _port = _cfg.get("proxy", {}).get("port", 8045)
                    if _key:
                        _det_url = f"http://localhost:{_port}/api/logs" # Bazı durumlarda tüm veri log içinde zaten gelir
                        # Gelen log nesnesinde request_body/response_body var mı kontrol et
                        if "request_body" in _target and _target["request_body"]:
                            _req_body = _target["request_body"]
                        if "response_body" in _target and _target["response_body"]:
                            _res_body = _target["response_body"]
            except Exception:
                pass

            # JSON formatlama
            def _pretty_json(txt):
                if not txt:
                    return "Boş"
                try:
                    return _jj.dumps(_jj.loads(txt), indent=2, ensure_ascii=False)
                except Exception:
                    return str(txt)

            _detail_title.set_content(f"""
                <div style="display:flex; align-items:center; gap:8px">
                    <span style="padding:2px 8px; border-radius:12px; font-size:12px; {_sc}">{_st}</span>
                    <span style="font-weight:bold">{_method}</span>
                    <span style="font-size:13px; color:#8b949e">{_path}</span>
                </div>
            """)
            
            _detail_content.set_content(f"""
                <div style="font-size:12px; line-height:1.6">
                    <div style="margin-bottom:8px"><b>Model:</b> <span style="color:#58a6ff">{_mdl_str}</span></div>
                    <div style="margin-bottom:8px"><b>Hesap:</b> {_acc}</div>
                    <div style="margin-bottom:8px"><b>Süre:</b> {_dur}ms</div>
                    <div style="margin-bottom:12px"><b>Protokol:</b> {_target.get("protocol","").upper()}</div>
                    
                    <div style="margin-top:12px">
                        <b style="color:#8b949e">Request Payload:</b>
                        <pre style="background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; overflow:auto; max-height:150px; font-family:Consolas,monospace; font-size:11px">{_pretty_json(_req_body)}</pre>
                    </div>
                    
                    <div style="margin-top:12px">
                        <b style="color:#8b949e">Response Payload:</b>
                        <pre style="background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; overflow:auto; max-height:150px; font-family:Consolas,monospace; font-size:11px">{_pretty_json(_res_body)}</pre>
                    </div>
                </div>
            """)
            
            _ag_detail_dialog.open()

        # NiceGUI global ref to dynamically populate detailed rows clicking
        app.native.settings.setdefault("api_log_click", _show_log_detail) if hasattr(app, "native") else None
        
        def _format_tokens(val):
            if val is None:
                return "-"
            if val >= 1000:
                return f"{val/1000:.1f}k"
            return str(val)

        # Sync worker for fetching logs in background thread
        def _fetch_ag_logs_sync_worker():
            import urllib.request as _ur, json as _jj, os as _os2
            try:
                cfg_path = _os2.path.expanduser(r"~\.antigravity_tools\gui_config.json")
                if not _os2.path.exists(cfg_path):
                    return None
                with open(cfg_path, encoding="utf-8") as _f:
                    _cfg = _jj.load(_f)
                _key  = _cfg.get("proxy", {}).get("api_key", "")
                _port = _cfg.get("proxy", {}).get("port", 8045)
                if not _key:
                    return None
                _url = f"http://localhost:{_port}/api/logs?limit=50&offset=0"
                _req = _ur.Request(_url, headers={"Authorization": f"Bearer {_key}"})
                _resp = _ur.urlopen(_req, timeout=2)
                return _jj.loads(_resp.read())
            except Exception:
                return None

        async def _fetch_ag_logs():
            if _ag_logs_state["paused"]:
                return
            if _ag_logs_state.get("loading"):
                return
            _ag_logs_state["loading"] = True
            _render_ag_logs()
            
            import asyncio
            _data = await asyncio.to_thread(_fetch_ag_logs_sync_worker)
            
            _ag_logs_state["loading"] = False
            if isinstance(_data, list):
                _ag_logs_state["logs"] = _data
                # Hesap dropdown listesini güncelle
                _emails = set()
                for _l in _data:
                    _em = _l.get("account_email")
                    if _em:
                        _emails.add(_em)
                _opt = ["Tüm Hesaplar"] + sorted(list(_emails))
                _acc_select.options = _opt
                _acc_select.update()
            
            _render_ag_logs()

        def _trigger_fetch_ag_logs():
            import asyncio
            asyncio.create_task(_fetch_ag_logs())

        def _clear_ag_logs():
            """Antigravity proxy loglarını temizler."""
            import urllib.request as _ur, json as _jj, os as _os2
            try:
                cfg_path = _os2.path.expanduser(r"~\.antigravity_tools\gui_config.json")
                if not _os2.path.exists(cfg_path):
                    return
                with open(cfg_path, encoding="utf-8") as _f:
                    _cfg = _jj.load(_f)
                _key  = _cfg.get("proxy", {}).get("api_key", "")
                _port = _cfg.get("proxy", {}).get("port", 8045)
                if not _key:
                    return
                _req = _ur.Request(
                    f"http://localhost:{_port}/api/logs/clear", 
                    headers={"Authorization": f"Bearer {_key}"},
                    method="POST"
                )
                _ur.urlopen(_req, timeout=2)
                ui.notify("Proxy logları temizlendi", type="positive")
                _ag_logs_state["logs"] = []
                _render_ag_logs()
            except Exception as _e:
                ui.notify(f"Loglar silinemedi: {_e}", type="negative")

        def _render_ag_logs():
            _logs = _ag_logs_state["logs"]
            _rows = []
            
            # Filtreleme
            _txt_filter = _ag_logs_state["filter"].lower().strip()
            _type_filter = _ag_logs_state["filter_type"]
            _acc_filter = _ag_logs_state["account_filter"]
            
            _filtered = []
            for _l in _logs:
                _st = str(_l.get("status", 0))
                _mdl = (_l.get("model") or "").lower()
                _map = (_l.get("mapped_model") or "").lower()
                _path = (_l.get("url") or "").lower()
                _prot = (_l.get("protocol") or "").lower()
                _acc = (_l.get("account_email") or "")
                
                # Arama filtresi
                if _txt_filter and not any(_txt_filter in x for x in (_st, _mdl, _map, _path)):
                    continue
                
                # Hesap filtresi
                if _acc_filter != "Tüm Hesaplar" and _acc != _acc_filter:
                    continue
                
                # Hızlı filtre türleri
                if _type_filter == "Hata" and not (400 <= int(_st) < 600):
                    continue
                elif _type_filter == "Sohbet" and "completions" not in _path:
                    continue
                elif _type_filter == "Gemini" and "gemini" not in _mdl and "gemini" not in _prot:
                    continue
                elif _type_filter == "Claude" and "claude" not in _mdl and "anthropic" not in _prot:
                    continue
                elif _type_filter == "Görseller" and "images" in _path:
                    continue
                
                _filtered.append(_l)

            for _l in _filtered[:20]:
                _id  = _l.get("id", "")
                _st  = _l.get("status", 0)
                _ok  = 200 <= _st < 400
                _sc  = "background:#00b074;color:#fff" if _ok else "background:#ea3838;color:#fff"
                _method = _l.get("method", "POST")
                _mdl = _l.get("model") or "-"
                _map = _l.get("mapped_model") or ""
                _mdl_str = f"{_mdl} =&gt; {_map}" if _map and _map != _mdl else _mdl
                _acc = _l.get("account_email") or "-"
                _acc_display = _acc[:3] + "***" + _acc[_acc.find("@"):] if "@" in _acc else _acc
                _path = _l.get("url") or "-"
                _dur = _l.get("duration") or 0
                
                # Token formatting
                _inp = _l.get("input_tokens")
                _out = _l.get("output_tokens")
                _tok_str = f"Giriş: {_format_tokens(_inp)}<br>Çıkış: {_format_tokens(_out)}" if _inp is not None else "-"
                
                # Protocol Badge
                _prot = (_l.get("protocol") or "").upper()
                _prot_col = {"OPENAI": "background:#198754", "ANTHROPIC": "background:#d97706", "GEMINI": "background:#0d6efd"}.get(_prot, "background:#6c757d")
                _prot_label = "Claude" if _prot == "ANTHROPIC" else ("OpenAI" if _prot == "OPENAI" else ("Gemini" if _prot == "GEMINI" else _prot))
                
                import datetime as _dt
                try:
                    _ts = _dt.datetime.fromtimestamp(_l.get("timestamp", 0) / 1000).strftime("%H:%M:%S")
                except Exception:
                    _ts = "-"
                
                # Satıra tıklanınca pop-up açacak şekilde onClick ekledik
                _rows.append(f"""
                <tr style="border-bottom:1px solid #21262d;transition:background .15s;cursor:pointer"
                    onmouseover="this.style.background='#161b22'"
                    onmouseout="this.style.background='transparent'"
                    onclick="window.agShowDetail('{_id}')">
                  <td style="padding:10px 8px;vertical-align:middle">
                    <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;
                                 font-weight:700;{_sc}">{_st}</span>
                  </td>
                  <td style="padding:10px 8px;font-size:11px;color:#8b949e;font-weight:bold;vertical-align:middle">{_method}</td>
                  <td style="padding:10px 8px;font-size:11px;color:#58a6ff;font-family:Consolas,monospace;
                             max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle" title="{_mdl_str}">{_mdl_str}</td>
                  <td style="padding:10px 8px;vertical-align:middle">
                    <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:10px;
                                 font-weight:700;color:#fff;{_prot_col}">{_prot_label}</span>
                  </td>
                  <td style="padding:10px 8px;font-size:11px;color:#8b949e;max-width:140px;
                             overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle" title="{_acc}">{_acc_display}</td>
                  <td style="padding:10px 8px;font-size:11px;color:#8b949e;font-family:Consolas,monospace;
                             max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:middle" title="{_path}">{_path}</td>
                  <td style="padding:10px 8px;font-size:10px;color:#c9d1d9;line-height:1.3;vertical-align:middle">{_tok_str}</td>
                  <td style="padding:10px 8px;font-size:11px;color:#c9d1d9;text-align:right;vertical-align:middle">{_dur}ms</td>
                  <td style="padding:10px 8px;font-size:11px;color:#8b949e;font-family:Consolas,monospace;text-align:right;vertical-align:middle">{_ts}</td>
                </tr>""")
            
            if _ag_logs_state.get("loading"):
                _html = (
                    '<tr><td colspan="9" style="padding:30px;text-align:center;color:#58a6ff;font-size:12px">'
                    '<div style="display:inline-block; width:12px; height:12px; border:2px solid #58a6ff; '
                    'border-top-color:transparent; border-radius:50%; animation:spin-loader 0.8s linear infinite; '
                    'margin-right:8px; vertical-align:middle"></div>'
                    '<style>@keyframes spin-loader { to { transform: rotate(360deg); } }</style>'
                    'Loglar yükleniyor...</td></tr>'
                )
            else:
                _html = "".join(_rows) if _rows else '<tr><td colspan="9" style="padding:30px;text-align:center;color:#8b949e;font-size:12px">Eşleşen log bulunamadı...</td></tr>'
            _ag_table.set_content(f"""
            <table style="width:100%;border-collapse:collapse;color:#c9d1d9">
              <thead>
                <tr style="border-bottom:1px solid #30363d;text-align:left">
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:65px">Durum</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:60px">Metot</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:240px">Model</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:80px">Protokol</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:140px">Hesap</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:180px">Yol</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;width:100px">Token'lar</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;text-align:right;width:90px">Süre</th>
                  <th style="padding:8px;font-size:11px;font-weight:600;color:#8b949e;text-align:right;width:85px">Zaman</th>
                </tr>
              </thead>
              <tbody>{_html}</tbody>
            </table>""")

        # JS callback bridge to call show detail modal
        ui.add_head_html("""
        <script>
            window.agShowDetail = function(logId) {
                // NiceGUI run_method triggers python logic
                console.log("Log clicked:", logId);
                // Call back to Python custom handler
                var el = document.getElementById("ag_detail_trigger");
                if (el) {
                    el.value = logId;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        </script>
        """)

        # Hidden input for JS-to-Python bridge
        _dialog_trigger = ui.input().style("display:none; width:0; height:0").classes("ag_detail_trigger")
        _dialog_trigger.props('id="ag_detail_trigger"')
        _dialog_trigger.on("input", lambda e: _show_log_detail(e.value) if e.value else None)

        # Widget container (Tıpkı resimdeki gibi koyu tonlar)
        with ui.element("div").style(
            "margin-top:20px;border-radius:12px;overflow:hidden;"
            "border:1px solid #30363d;background:#0d1117;padding:16px"
        ):
            # Toolbar
            with ui.element("div").style("display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap"):
                # "Kaydediliyor" Pulse Badge
                ui.html("""
                <div style="display:flex;align-items:center;gap:8px;background:#ea3838;color:#fff;
                             padding:6px 14px;border-radius:6px;font-size:12px;font-weight:bold;letter-spacing:0.5px">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#fff;
                               animation:pulse 1.2s infinite"></span>
                  Kaydediliyor
                </div>
                <style>
                  @keyframes pulse {
                    0% { opacity: 0.3; }
                    50% { opacity: 1; }
                    100% { opacity: 0.3; }
                  }
                </style>
                """)
                
                # Search input
                _search_inp = ui.input(
                    placeholder="Model, yol veya duruma göre filtrele...",
                    on_change=lambda e: (exec('_ag_logs_state["filter"] = e.value'), _render_ag_logs())
                ).style(
                    "flex:1;min-width:200px;background:#161b22;color:#c9d1d9;"
                    "border:1px solid #30363d;border-radius:6px;padding:4px 12px;font-size:12px"
                )

                # Account Selector Dropdown (Resimdeki "Tüm Hesaplar" dropdown'ı)
                _acc_select = ui.select(
                    options=["Tüm Hesaplar"], 
                    value="Tüm Hesaplar",
                    on_change=lambda e: (exec('_ag_logs_state["account_filter"] = e.value'), _render_ag_logs())
                ).style(
                    "background:#161b22; color:#c9d1d9; border:1px solid #30363d; border-radius:6px;"
                    "padding:4px 8px; font-size:12px; min-width:140px"
                )
                
                # Pause button
                _pause_lbl = [None]
                def _toggle_ag_pause():
                    _ag_logs_state["paused"] = not _ag_logs_state["paused"]
                    lbl = "▶ Devam" if _ag_logs_state["paused"] else "⏸ Duraklat"
                    if _pause_lbl[0]:
                        _pause_lbl[0].set_content(lbl)
                _pbtn = ui.element("button").style(
                    "padding:6px 14px;border-radius:6px;font-size:12px;font-weight:600;"
                    "background:#21262d;border:1px solid #30363d;color:#c9d1d9;cursor:pointer"
                ).on("click", _toggle_ag_pause)
                with _pbtn:
                    _pause_lbl[0] = ui.html("⏸ Duraklat")

                # Refresh button (circular icon style)
                _ref_btn = ui.element("button").style(
                    "padding:6px 10px;border-radius:6px;font-size:14px;font-weight:600;"
                    "background:#21262d;border:1px solid #30363d;color:#c9d1d9;cursor:pointer"
                ).on("click", _fetch_ag_logs)
                with _ref_btn:
                    ui.html("🔄")

                # Clear button (trash bin icon style)
                _clr_btn = ui.element("button").style(
                    "padding:6px 10px;border-radius:6px;font-size:14px;font-weight:600;"
                    "background:#ea3838;border:1px solid #30363d;color:#fff;cursor:pointer"
                ).on("click", _clear_ag_logs)
                with _clr_btn:
                    ui.html("🗑️")

            # Hızlı Filtre Barı (Tıpkı resimdeki gibi)
            with ui.element("div").style("display:flex;align-items:center;gap:8px;margin-bottom:14px;font-size:11px;color:#8b949e"):
                ui.html('<span style="font-weight:bold;text-transform:uppercase;letter-spacing:0.5px">HIZLI FİLTRELER:</span>')
                _filter_btns = {}
                
                def _set_type_filter(val):
                    _ag_logs_state["filter_type"] = val
                    for k, btn in _filter_btns.items():
                        if k == val:
                            btn.style("background:#005cc5;color:#fff;border-color:#0366d6")
                        else:
                            btn.style("background:#21262d;color:#c9d1d9;border-color:#30363d")
                    _render_ag_logs()

                for f_name in ["Tümü", "Hata", "Sohbet", "Gemini", "Claude", "Görseller"]:
                    _btn = ui.element("button").style(
                        "padding:2px 10px;border-radius:10px;font-size:11px;cursor:pointer;border:1px solid #30363d;"
                        + ("background:#005cc5;color:#fff;border-color:#0366d6" if f_name == "Tümü" else "background:#21262d;color:#c9d1d9")
                    ).on("click", lambda e, name=f_name: _set_type_filter(name))
                    with _btn:
                        ui.html(f_name)
                    _filter_btns[f_name] = _btn

            # Log table container
            _ag_table = ui.html("").style(
                "display:block;max-height:350px;overflow-y:auto;overflow-x:auto;"
                "border-top:1px solid #30363d;padding-top:10px"
            )

        # Başlangıçta veriyi çek, sonra 5 saniyede bir güncelle
        _trigger_fetch_ag_logs()
        ui.timer(5.0, _trigger_fetch_ag_logs)



# ── GLOSSARY sayfası ─────────────────────────────────────────────────────────
def build_glossary():
    glossary = get_glossary()
    selected = {"series": None}
    detail_col = [None]
    _refresh_cb = [None]   # render_rows callback'i — fonksiyon tanımlandıktan sonra doldurulur
    _search_ref = [None]   # search_inp referansı
    # Sıralama tercihini prefs'ten yükle — kapat/aç döngüsünde kaybolmaz
    _saved_sort = load_prefs().get("glossary_sort_mode", "az")
    _sort_mode  = [_saved_sort]  # az | za | date_desc | date_asc | terms_desc | terms_asc
    _sort_btns  = {}             # sort_key -> ui element referansı

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">📚 Glossary / Sözlük</div>')
        ui.html('<div class="ph-sub">Fandom Wiki terminoloji sözlükleri</div>')

    with ui.element("div").style("padding:16px 28px 20px;display:flex;flex-direction:column;gap:16px"):

        # ── Üst bar: Arama + Wiki çekme ──
        with ui.element("div").classes("card").style("padding:16px 20px"):

            # ── Satır 1: Gelişmiş Arama Barı (Seri adı + Wiki slug) ──────────
            with ui.element("div").style("position:relative;margin-bottom:10px"):
                ui.html(
                    '<div style="position:absolute;left:14px;top:50%;transform:translateY(-50%);'
                    'font-size:16px;pointer-events:none;z-index:2">🔍</div>'
                )
                search_inp = ui.input(
                    placeholder="Seri adı veya wiki slug ara... (örn: sword art, oshinoko)"
                ).style(
                    f"width:100%;box-sizing:border-box;padding:11px 14px 11px 44px;"
                    f"background:linear-gradient(135deg,rgba(255,255,255,.07),rgba(255,255,255,.03));"
                    f"backdrop-filter:blur(10px);"
                    f"border:1px solid var(--accent1)55;border-radius:12px;"
                    f"color:{C['TEXT']};font-size:13px;font-family:inherit;"
                    f"outline:none;transition:all .25s;"
                    f"box-shadow:0 2px 16px rgba(0,0,0,.25)"
                ).props('id="nx-series-search" autocomplete="off" clearable')
                _search_ref[0] = search_inp
                # Sonuç sayacı etiketi
                _result_lbl = [None]
                _result_lbl[0] = ui.html('').style(
                    "position:absolute;right:44px;top:50%;transform:translateY(-50%);"
                    "font-size:11px;color:var(--accent2);font-weight:700;pointer-events:none"
                )

            # ── Satır 2: Wiki slug input + Wiki butonları ─────────────────────
            with ui.element("div").style("display:flex;gap:10px;margin-bottom:10px"):
                wiki_inp = ui.input(placeholder="Wiki slug girin (örn: oshinoko)").style(
                    f"flex:1;background:{C['PANEL']};color:{C['TEXT']};"
                    f"border:1px solid {C['BORDER']};border-radius:9px;padding:8px 14px"
                )

            # ── Satır 3: Premium Term Arama Barı ─────────────────────────────
            ui.html('<div style="position:relative;margin-bottom:10px">'
                    '<div style="position:absolute;left:14px;top:50%;transform:translateY(-50%);'
                    'font-size:15px;pointer-events:none;z-index:1">🔎</div>'
                    '<input id="nx-term-search" type="text"'
                    ' placeholder="Terim ara... (Yetenekler, Karakterler, Avalanche...)"'
                    ' oninput="nxTermFilter(this.value)" autocomplete="off"'
                    ' style="width:100%;box-sizing:border-box;padding:11px 14px 11px 42px;'
                    'background:linear-gradient(135deg,rgba(255,255,255,.06),rgba(255,255,255,.03));'
                    'backdrop-filter:blur(10px);border:1px solid var(--accent1)44;border-radius:12px;'
                    'color:#e2e8f0;font-size:13px;font-family:inherit;outline:none;transition:all .2s;'
                    'box-shadow:0 2px 16px rgba(0,0,0,.3)"/>'
                    '<span id="nx-ts-rc" style="position:absolute;right:14px;top:50%;'
                    'transform:translateY(-50%);font-size:11px;color:var(--accent2);'
                    'font-weight:600;pointer-events:none;display:none"></span>'
                    '</div>')

            # ── Satır 4: Sıralama Kontrolleri ────────────────────────────────
            with ui.element("div").style(
                "display:flex;align-items:center;gap:6px;flex-wrap:wrap;"
                "padding:10px 14px;border-radius:10px;"
                f"background:rgba(255,255,255,.03);border:1px solid {C['BORDER']};"
                "margin-bottom:10px"
            ):
                ui.html(
                    f'<span style="font-size:11px;font-weight:700;color:{C["MUTED"]};'
                    f'letter-spacing:1px;margin-right:6px">SIRALA:</span>'
                )

                SORT_OPTIONS = [
                    ("az",         "A → Z",       "🔤"),
                    ("za",         "Z → A",       "🔤"),
                    ("date_desc",  "Yeni Önce",   "📅"),
                    ("date_asc",   "Eski Önce",   "📅"),
                    ("terms_desc", "Çok Terim",   "📊"),
                    ("terms_asc",  "Az Terim",    "📊"),
                ]

                def _make_sort_btn(sk, label, icon):
                    _is_active = sk == _sort_mode[0]
                    _active_style = (
                        "background:linear-gradient(135deg,var(--accent1)44,var(--accent2)22);"
                        "border-color:var(--accent1)99;color:var(--accent1);font-weight:700;"
                        "box-shadow:0 0 10px var(--accent1)33;"
                    ) if _is_active else (
                        f"background:rgba(255,255,255,.04);border-color:{C['BORDER']};"
                        f"color:{C['MUTED']};"
                    )
                    btn = ui.html(
                        f'<button id="nx-sort-{sk}" '
                        f'style="display:inline-flex;align-items:center;gap:4px;'
                        f'padding:5px 12px;border-radius:20px;font-size:11px;'
                        f'cursor:pointer;outline:none;transition:all .18s;border:1px solid;'
                        f'{_active_style}font-family:inherit;">'
                        f'{icon} {label}</button>'
                    )
                    _sort_btns[sk] = btn
                    return btn

                _sort_btn_els = {}
                for _sk, _lbl, _ico in SORT_OPTIONS:
                    _b = _make_sort_btn(_sk, _lbl, _ico)
                    _sort_btn_els[_sk] = _b

                def _apply_sort(new_mode):
                    _sort_mode[0] = new_mode
                    # Tercihi diske kaydet — kapat/aç döngüsünde kalıcı
                    try:
                        save_prefs({"glossary_sort_mode": new_mode})
                    except Exception:
                        pass
                    # Tüm butonları sıfırla
                    for _sk2, _lbl2, _ico2 in SORT_OPTIONS:
                        _btn_el = _sort_btn_els.get(_sk2)
                        if not _btn_el:
                            continue
                        _is_act = (_sk2 == new_mode)
                        _act_s = (
                            "background:linear-gradient(135deg,var(--accent1)44,var(--accent2)22);"
                            "border-color:var(--accent1)99;color:var(--accent1);font-weight:700;"
                            "box-shadow:0 0 10px var(--accent1)33;"
                        ) if _is_act else (
                            f"background:rgba(255,255,255,.04);border-color:{C['BORDER']};"
                            f"color:{C['MUTED']};"
                        )
                        ui.run_javascript(
                            f"var _b=document.getElementById('nx-sort-{_sk2}');"
                            f"if(_b){{_b.style.cssText=_b.style.cssText.replace(/background:[^;]+;/g,'').replace(/border-color:[^;]+;/g,'').replace(/color:[^;]+;/g,'').replace(/font-weight:[^;]+;/g,'').replace(/box-shadow:[^;]+;/g,'');" +
                            f"_b.style.cssText+='{_act_s}';}}"
                        )
                    # Listeyi yenile
                    _s = _search_ref[0]
                    if _refresh_cb[0]:
                        _refresh_cb[0](_s.value.strip() if _s else "")

                # Her sıralama butonuna click olayı bağla
                for _sk, _lbl, _ico in SORT_OPTIONS:
                    _sort_btn_els[_sk].on("click", lambda e, k=_sk: _apply_sort(k))

            # ── Satır 5: Wiki işlem butonları ────────────────────────────────
            with ui.element("div").style("display:flex;gap:10px;align-items:center;flex-wrap:wrap"):

                async def _run_wiki_cmd(wname: str, extra_flags: list, notify_msg: str):
                    cmd = ["python", SCRIPT_GLOSSARY, "--wiki", wname] + extra_flags
                    _no_win = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
                    proc = await asyncio.create_subprocess_exec(
                        *cmd, cwd=os.path.dirname(SCRIPT_GLOSSARY),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        creationflags=_no_win
                    )
                    _out, _ = await proc.communicate()
                    state["glossary"] = None
                    if _out:
                        for _ln in _out.decode("utf-8", errors="replace").splitlines():
                            if _ln.strip():
                                state.setdefault("log_lines", []).append(_ln.strip())
                    ui.notify(notify_msg, type="positive", timeout=4000)
                    # Sayfayı başa atmak yerine sadece listeyi yenile
                    state["glossary"] = None
                    nonlocal glossary
                    glossary = get_glossary()
                    if _refresh_cb[0]:
                        _s = _search_ref[0]
                        _refresh_cb[0](_s.value.strip() if _s else "")

                async def fetch_wiki():
                    wname = wiki_inp.value.strip().lower().replace(" ", "")
                    if not wname:
                        ui.notify("Wiki slug girin!", type="warning"); return
                    g_cur = get_glossary()
                    already = [sn for sn, sd in g_cur.items()
                               if sd.get("wiki", "").lower().replace(" ", "") == wname]
                    if already:
                        _e = g_cur[already[0]]
                        _tot = sum(len(v) for v in _e.get("terms", {}).values())
                        ui.notify(f"'{wname}' mevcut ({_tot} terim) — Merge ile güncelleniyor...",
                                  type="info", timeout=4000)
                        await _run_wiki_cmd(wname, ["--merge"],
                                            f"'{wname}' guncellendi! Yeni terimler eklendi.")
                    else:
                        ui.notify(f"'{wname}' cekiliyor...", type="info")
                        await _run_wiki_cmd(wname, [], f"'{wname}' eklendi!")

                async def force_update_wiki():
                    wname = wiki_inp.value.strip().lower().replace(" ", "")
                    if not wname:
                        ui.notify("Wiki slug girin!", type="warning"); return
                    ui.notify(f"'{wname}' sifirdan cekiliyor...", type="info")
                    await _run_wiki_cmd(wname, ["--force"], f"'{wname}' tamamen yenilendi!")

                async def dedupe_glossary():
                    g = get_glossary()
                    seen_slug = {}  # slug -> (name, term_count)
                    to_delete = []
                    for sname, sdata in g.items():
                        slug = sdata.get("wiki", "").lower().replace(" ", "")
                        if not slug: continue
                        cur_terms = sum(len(v) for v in sdata.get("terms", {}).values())
                        if slug in seen_slug:
                            prev_name, prev_terms = seen_slug[slug]
                            # Daha fazla terim içereni tut; eşitse daha uzun/spesifik ismi tut
                            if cur_terms > prev_terms or (cur_terms == prev_terms and len(sname) > len(prev_name)):
                                to_delete.append(prev_name)
                                seen_slug[slug] = (sname, cur_terms)
                            else:
                                to_delete.append(sname)
                        else:
                            seen_slug[slug] = (sname, cur_terms)
                    if not to_delete:
                        ui.notify("Zaten temiz - tekrar yok", type="positive"); return
                    for d in to_delete:
                        if d in g: del g[d]
                    with open(GLOSSARY_FILE, "w", encoding="utf-8") as _f:
                        json.dump(g, _f, indent=2, ensure_ascii=False)
                    state["glossary"] = None
                    ui.notify(f"Temizlendi: {len(to_delete)} tekrar silindi", type="positive", timeout=5000)
                    # Sayfayı başa atmak yerine listeyi yenile
                    state["glossary"] = None
                    nonlocal glossary
                    glossary = get_glossary()
                    if _refresh_cb[0]:
                        _s = _search_ref[0]
                        _refresh_cb[0](_s.value.strip() if _s else "")

                nbtn("📥 WIKI ÇEK / GÜNCELLE", click=fetch_wiki)
                nbtn("🔄 Sıfırdan Çek", click=force_update_wiki, variant="ghost", size="sm")
                nbtn("🧹 Temizle", click=dedupe_glossary, variant="ghost", size="sm")

        # ── İstatistik kartları (reaktif — render_rows her çalışınca güncellenir) ──
        _lbl_series = [None]
        _lbl_terms  = [None]
        _lbl_avg    = [None]
        with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:12px"):
            with ui.element("div").classes("card").style("text-align:center;padding:20px"):
                _lbl_series[0] = ui.html('')
                ui.html(f'<div style="font-size:12px;color:{C["SUB"]};margin-top:6px;font-weight:600;letter-spacing:1px">TOPLAM SERİ</div>')
            with ui.element("div").classes("card").style("text-align:center;padding:20px"):
                _lbl_terms[0] = ui.html('')
                ui.html(f'<div style="font-size:12px;color:{C["SUB"]};margin-top:6px;font-weight:600;letter-spacing:1px">TOPLAM TERİM</div>')
            with ui.element("div").classes("card").style("text-align:center;padding:20px"):
                _lbl_avg[0] = ui.html('')
                ui.html(f'<div style="font-size:12px;color:{C["SUB"]};margin-top:6px;font-weight:600;letter-spacing:1px">ORT. TERİM/SERİ</div>')

        def _refresh_stats():
            """Glossary verisinden istatistikleri yeniden hesaplar ve kartları günceller."""
            _cur = get_glossary()
            _sc  = len(_cur)
            _tt  = sum(sum(len(v) for v in d.get('terms',{}).values()) for d in _cur.values())
            _avg = round(_tt / _sc, 1) if _sc else 0
            if _lbl_series[0]:
                _lbl_series[0].set_content(f'<div style="font-size:32px;font-weight:800;color:var(--accent1);line-height:1">{_sc}</div>')
            if _lbl_terms[0]:
                _lbl_terms[0].set_content(f'<div style="font-size:32px;font-weight:800;color:var(--accent2);line-height:1">{_tt}</div>')
            if _lbl_avg[0]:
                _lbl_avg[0].set_content(f'<div style="font-size:32px;font-weight:800;color:{C["GREEN"]};line-height:1">{_avg}</div>')
            # Status bar terim sayacını da güncelle
            _sb_lbl = state.get("_status_term_lbl")
            if _sb_lbl:
                try:
                    _sb_lbl.set_content(f'<span>&#128218; {_tt} terim</span>')
                except Exception:
                    pass
            # [FIX] Sol panel nav-pill sayacını güncelle (Glossary 2 → doğru sayı)
            _sidebar_refresh = state.get("_sidebar_refresh")
            if _sidebar_refresh:
                try:
                    _sidebar_refresh()
                except Exception:
                    pass

        _refresh_stats()  # İlk yüklemede doldur

        # ── Seri listesi — inline accordion ──
        CAT_COLORS = {
            "characters":   ("chip-purple", "Karakterler",  "🧑"),
            "organizations":("chip-cyan",   "Organizasyon", "🏢"),
            "skills":       ("chip-cyan",   "Yetenekler",   "⚡"),
            "locations":    ("chip-green",  "Lokasyonlar",  "📍"),
            "items":        ("chip-yellow", "Eşyalar",      "📦"),
            "terminology":  ("chip-pink",   "Terimler",     "📝"),
        }

        rows_container = ui.element("div").style("display:flex;flex-direction:column;gap:10px")

        def render_rows(filter_text=""):
            _refresh_cb[0] = render_rows  # callback'i kaydet (her yeniden tanımda güncelle)
            _refresh_stats()              # İstatistikleri her yenilemede güncelle
            nonlocal glossary
            # Cache'den al — zaten yüklüyse disk I/O yok
            glossary = get_glossary()
            rows_container.clear()
            with rows_container:
                # ── Filtre: seri adı VEYA wiki slug ──────────────────────────
                _ft = filter_text.lower().strip()
                if _ft:
                    filtered = {
                        k: v for k, v in glossary.items()
                        if _ft in k.lower()
                        or _ft in v.get("wiki", "").lower()
                    }
                else:
                    filtered = dict(glossary)

                # ── Sonuç sayacını güncelle ────────────────────────────────
                if _result_lbl[0]:
                    _total_g = len(glossary)
                    _found_g = len(filtered)
                    if _ft:
                        _result_lbl[0].set_content(
                            f'<span style="font-size:11px;color:var(--accent2);font-weight:700">{_found_g}/{_total_g} seri</span>'
                        )
                    else:
                        _result_lbl[0].set_content('')

                # ── Sıralama ──────────────────────────────────────────────
                _sm = _sort_mode[0]
                def _sort_key(item):
                    sn, sd = item
                    _cnt = sum(len(v) for v in sd.get("terms", {}).values())
                    _dt  = sd.get("fetched_at", "") or ""
                    if _sm in ("az", "za"):    return sn.lower()
                    elif _sm == "date_desc":   return _dt
                    elif _sm == "date_asc":    return _dt
                    elif _sm == "terms_desc":  return _cnt
                    elif _sm == "terms_asc":   return _cnt
                    return sn.lower()

                _reverse = _sm in ("za", "date_desc", "terms_desc")
                filtered_items = sorted(filtered.items(), key=_sort_key, reverse=_reverse)

                if not filtered_items:
                    ui.html(f'<div style="text-align:center;padding:30px;color:{C["MUTED"]}">Sonuç bulunamadı</div>')
                    return

                # ── Termbase varlık haritası — döngü dışında TEK seferde tara ──────
                import os as _os, re as _re, json as _json, sys as _sys
                _py_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
                if _py_dir not in _sys.path:
                    _sys.path.insert(0, _py_dir)
                _tb_dir = _os.path.join(_py_dir, 'termbase')
                # Termbase klasöründeki tüm dosya isimlerini bir set'e al (O(1) arama)
                try:
                    _tb_files = set(_os.listdir(_tb_dir)) if _os.path.isdir(_tb_dir) else set()
                except Exception:
                    _tb_files = set()
                try:
                    from termbase_manager import _split_title_season as _spl
                    _spl_ok = True
                except Exception:
                    _spl_ok = False
                    def _spl(s): return s, None
                # ────────────────────────────────────────────────────────────────────

                # ── Tek seri kartı render fonksiyonu (batch çağrısı için) ──
                def _render_one_series(sname, data):
                    terms   = data.get("terms", {})
                    count   = sum(len(v) for v in terms.values())
                    fetched = data.get("fetched_at", "")[:10] or "—"
                    wiki    = data.get("wiki", "—")

                    # Termbase varlık kontrolü — sadece set membership (O(1), disk yok)
                    try:
                        _clean_sn, _season_n = _spl(sname)
                        if wiki and wiki != "—":
                            _safe = _re.sub(r'[^a-z0-9]', '_', wiki.lower())[:50].rstrip('_')
                        else:
                            _safe = _re.sub(r'[^a-z0-9]', '_', _clean_sn.lower())[:50].rstrip('_')
                        
                        _has_tb = (
                            f'{_safe}_base.json' in _tb_files
                            or any(f'{_safe}_s{i}_chars.json' in _tb_files for i in range(1, 6))
                            or f'{_safe}_s1.json' in _tb_files
                            or f'{_safe}.json' in _tb_files
                        )
                        if _season_n:
                            _has_tb = _has_tb or f'{_safe}_s{_season_n}_chars.json' in _tb_files
                        
                        # Fallback to clean name safe just in case
                        _safe_clean = _re.sub(r'[^a-z0-9]', '_', _clean_sn.lower())[:50].rstrip('_')
                        if not _has_tb and _safe_clean != _safe:
                            _has_tb = (
                                f'{_safe_clean}_base.json' in _tb_files
                                or any(f'{_safe_clean}_s{i}_chars.json' in _tb_files for i in range(1, 6))
                                or f'{_safe_clean}_s1.json' in _tb_files
                                or f'{_safe_clean}.json' in _tb_files
                            )
                            if _season_n:
                                _has_tb = _has_tb or f'{_safe_clean}_s{_season_n}_chars.json' in _tb_files
                            if _has_tb:
                                _safe = _safe_clean

                        _tb_lookup = {}
                        if _has_tb:
                            _files_to_load = [
                                f'{_safe}_base.json',
                                f'{_safe}.json',
                                f'{_safe}_s1.json'
                            ]
                            for i in range(1, 6):
                                _files_to_load.append(f'{_safe}_s{i}_chars.json')
                            if _season_n:
                                _files_to_load.append(f'{_safe}_s{_season_n}_chars.json')

                            for _fn in _files_to_load:
                                if _fn in _tb_files:
                                    try:
                                        with open(_os.path.join(_tb_dir, _fn), 'r', encoding='utf-8') as _f:
                                            _jd = _json.load(_f)
                                            _tdata = _jd.get("terms", _jd)
                                            for _cat_k, _cat_v in _tdata.items():
                                                if isinstance(_cat_v, dict):
                                                    for _en, _tr in _cat_v.items():
                                                        if _en and _tr:
                                                            _tb_lookup[_en.lower()] = _tr
                                                elif isinstance(_cat_v, str):
                                                    _tb_lookup[_cat_k.lower()] = _cat_v
                                    except Exception:
                                        pass
                    except Exception:
                        _has_tb    = False
                        _tb_lookup = {}

                    _open       = [False]
                    _sname_safe = sname.replace(" ","_").replace("|","_").replace(".","_")

                    with rows_container:
                        with ui.element("div").classes("card").style("overflow:hidden;padding:0"):

                            with ui.element("div").style(
                                f"display:flex;align-items:center;padding:14px 18px;gap:12px;"
                                f"border-bottom:1px solid {C['BORDER']}00;cursor:pointer;"
                                "transition:background 0.15s"
                            ) as header_row:

                                expand_icon = ui.html('<span style="font-size:14px;transition:transform 0.2s">▶</span>')

                                with ui.element("div").style("flex:1;min-width:0"):
                                    ui.html(f'<div data-nx-series="{sname}" style="font-size:14px;font-weight:700;color:{C["TEXT"]}">{sname}</div>')
                                    ui.html(f'<div style="font-size:11px;color:{C["MUTED"]};margin-top:2px">'
                                            f'wiki: <span style="color:{C["CYAN"]}">{wiki}</span>'
                                            f' &nbsp;·&nbsp; {fetched}</div>')

                                ui.html(f'<span class="chip chip-purple">{count} terim</span>')

                                async def _merge_this(w=wiki):
                                    if not w or w == "—":
                                        ui.notify("Bu serinin wiki slug'u yok!", type="warning"); return
                                    ui.notify(f"'{w}' merge ile guncelleniyor...", type="info")
                                    await _run_wiki_cmd(w, ["--merge"], f"'{w}' guncellendi!")
                                nbtn("🔄 Güncelle", click=_merge_this, variant="ghost", size="sm")

                                _tb_label = "📖 Termbase" if _has_tb else "📝 Termbase Oluştur"
                                async def _build_tb(s=sname, w=wiki):
                                    try:
                                        import sys as _s2, os as _o2, asyncio as _aio
                                        _py_dir2 = _o2.path.dirname(_o2.path.dirname(_o2.path.abspath(__file__)))
                                        _s2.path.insert(0, _py_dir2)
                                        from termbase_manager import pre_translate_terms, _split_title_season
                                        _clean_s, _sn2 = _split_title_season(s)
                                        ui.notify(f"'{_clean_s}' termbase oluşturuluyor...", type="info", timeout=4000)
                                        loop = _aio.get_running_loop()
                                        await loop.run_in_executor(
                                            None,
                                            lambda: pre_translate_terms(_clean_s, season_num=_sn2, verbose=True, force_refresh=True)
                                        )
                                        ui.notify(f"'{_clean_s}' termbase hazır!", type="positive")
                                        if _refresh_cb[0]:
                                            _sr = _search_ref[0]
                                            _refresh_cb[0](_sr.value.strip() if _sr else "")
                                    except Exception as _e:
                                        ui.notify(f"Termbase hata: {_e}", type="negative")
                                nbtn(_tb_label, click=_build_tb, variant="ghost", size="sm")

                                async def _del_this(s=sname):
                                    import re as _re2, os as _os2, sys as _sys2
                                    graw = load_glossary()
                                    canonical_titles_map = graw.get("__canonical_titles__", {})
                                    def _get_display_name(title_or_key):
                                        if not title_or_key:
                                            return ""
                                        tk = title_or_key.strip().lower()
                                        canon = canonical_titles_map.get(tk, title_or_key)
                                        clean_title, _ = _spl(canon)
                                        return clean_title.strip()

                                    to_delete_keys = [
                                        k for k in graw.keys()
                                        if k != "__canonical_titles__"
                                        and (_get_display_name(k).lower() == s.lower() or k.lower() == s.lower())
                                    ]
                                    if to_delete_keys:
                                        for k in to_delete_keys:
                                            graw.pop(k, None)
                                        with open(GLOSSARY_FILE, "w", encoding="utf-8") as _f:
                                            json.dump(graw, _f, indent=2, ensure_ascii=False)
                                    state["glossary"] = None

                                    # ── fandom_glossary session cache + disk cache temizle ──
                                    # Aksi hâlde translator çalışınca build_glossary() cache'den
                                    # okuyup girişi series_glossary.json'a geri yazar.
                                    try:
                                        _py_dir_fg = _os2.path.dirname(_os2.path.dirname(_os2.path.abspath(__file__)))
                                        if _py_dir_fg not in _sys2.path:
                                            _sys2.path.insert(0, _py_dir_fg)
                                        import fandom_glossary as _fg
                                        # Session cache'i temizle (bellekte tutulan kopyayı sil)
                                        _keys_to_del = [k for k in list(_fg._session_cache.keys())
                                                        if s.lower() in k.lower() or (wiki and wiki != "—" and wiki.lower() in k.lower())]
                                        for _k in _keys_to_del:
                                            _fg._session_cache.pop(_k, None)
                                        # Disk cache'den (series_glossary.json) de aynı wiki'ye işaret eden
                                        # tüm girişleri temizle (deduplicate loop'unun geri getirme ihtimali)
                                        if wiki and wiki != "—":
                                            _disk = _fg._load_cache()
                                            _disk_changed = False
                                            for _dk in list(_disk.keys()):
                                                if _dk == "__canonical_titles__":
                                                    continue
                                                _dv = _disk.get(_dk, {})
                                                if isinstance(_dv, dict) and (_dv.get("wiki", "") or "").lower() == wiki.lower():
                                                    del _disk[_dk]
                                                    _disk_changed = True
                                            if _disk_changed:
                                                _fg._save_cache(_disk)
                                    except Exception:
                                        pass

                                    # Collect possible safe filename prefixes to delete
                                    _safe_slugs = []
                                    if wiki and wiki != "—":
                                        _safe_slugs.append(_re2.sub(r'[^a-z0-9]', '_', wiki.lower())[:50].rstrip('_'))
                                    _clean_s, _ = _spl(s)
                                    _safe_slugs.append(_re2.sub(r'[^a-z0-9]', '_', _clean_s.lower())[:50].rstrip('_'))
                                    _safe_slugs.append(_re2.sub(r'[^a-z0-9]', '_', s.lower())[:50].rstrip('_'))
                                    # Deduplicate prefixes
                                    _safe_slugs = list(set(_safe_slugs))
                                    
                                    _tb_dir2 = _os2.path.join(PARENT_DIR, "termbase")
                                    _deleted_tb = []
                                    if _os2.path.isdir(_tb_dir2):
                                        for _fn in _os2.listdir(_tb_dir2):
                                            _matches = any(_fn.startswith(_slug) for _slug in _safe_slugs)
                                            if _matches and (_fn.endswith("_base.json") or "_chars" in _fn or _fn.endswith(".json")):
                                                try:
                                                    _os2.remove(_os2.path.join(_tb_dir2, _fn))
                                                    _deleted_tb.append(_fn)
                                                except Exception:
                                                    pass
                                    _tb_info = f" + {len(_deleted_tb)} termbase" if _deleted_tb else ""
                                    ui.notify(f"'{s}' silindi{_tb_info}", type="warning")
                                    glossary.pop(s, None)
                                    if _refresh_cb[0]:
                                        _sr = _search_ref[0]
                                        _refresh_cb[0](_sr.value.strip() if _sr else "")
                                nbtn("🗑 Sil", click=_del_this, variant="danger", size="sm")

                            # Lazy detail panel
                            _sname_safe2 = sname.replace(" ","_").replace("|","_").replace(".","_")
                            detail_div = ui.element("div").classes("nx-detail-div").style("display:none;padding:16px 18px;gap:12px;flex-direction:column")
                            _detail_rendered = [False]

                            def _render_detail(
                                dd=detail_div, trms=terms, sn=sname,
                                htb=_has_tb, tbl=_tb_lookup, snfs=_sname_safe2
                            ):
                                with dd:
                                    if not trms:
                                        ui.html(f'<div style="color:{C["MUTED"]};font-size:13px;padding:12px">Terim bulunamadı</div>')
                                        return
                                    cat_order = [(cat, *CAT_COLORS.get(cat, ("chip-purple", cat.capitalize(), "📌")))
                                                 for cat in trms.keys()]
                                    if cat_order:
                                        _am = {"chip-purple":"#a78bfa","chip-cyan":"#22d3ee",
                                               "chip-green":"#4ade80","chip-yellow":"#facc15","chip-pink":"#f472b6"}
                                        tab_html = '<div style="display:flex;flex-wrap:wrap;gap:5px;padding:10px 14px 8px;border-bottom:1px solid rgba(255,255,255,.06)">'
                                        for _idx, (_jcat, _jcls, _jlbl, _jico) in enumerate(cat_order):
                                            _jclr     = _am.get(_jcls, "#a78bfa")
                                            _jcnt     = len(trms.get(_jcat, []))
                                            _cat_safe = _jcat.replace(" ","_").replace("|","_")
                                            _is_first = _idx == 0
                                            _pfc = 0
                                            if tbl:
                                                _itms = trms.get(_jcat, [])
                                                _tc   = sum(1 for it in _itms if tbl.get(it.lower(),'').lower() not in ('', it.lower()))
                                                _pfc  = round(_tc / len(_itms) * 100) if _itms else 0
                                            _active_bg   = f"background:{_jclr}40;border-color:{_jclr}99;box-shadow:0 0 12px {_jclr}33" if _is_first else f"background:{_jclr}0d;border-color:{_jclr}28;opacity:.7"
                                            _data_active = ' data-active="1"' if _is_first else ''
                                            tab_html += (
                                                f'<button data-nxtab-chip-prefix="{snfs}" data-nxtab-cat="{_cat_safe}" data-color="{_jclr}"{_data_active} '
                                                f'style="display:inline-flex;align-items:center;gap:4px;padding:4px 11px;border-radius:20px;font-size:11px;font-weight:600;cursor:pointer;outline:none;transition:all .18s cubic-bezier(.4,0,.2,1);color:{_jclr};border:1px solid;{_active_bg}">'
                                                f'{_jico} {_jlbl}<span style="opacity:.7;font-size:10px">({_jcnt})</span>'
                                                + (f'<span style="background:{_jclr}33;color:{_jclr};padding:0 4px;border-radius:6px;font-size:9px;font-weight:700">%{_pfc}</span>' if htb and _pfc > 0 else '')
                                                + '</button>'
                                            )
                                        tab_html += '</div>'
                                        ui.html(tab_html)
                                    if htb:
                                        ui.html(
                                            f'<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;margin:6px 0 4px;'
                                            f'background:linear-gradient(135deg,rgba(127,255,176,.08),rgba(100,200,255,.05));border:1px solid rgba(127,255,176,.2)">'
                                            f'<span style="font-size:16px">🔤</span>'
                                            f'<span style="font-size:12px;color:#7fffb0;font-weight:600">Termbase aktif</span>'
                                            f'<span style="font-size:11px;color:{C["MUTED"]};margin-left:4px">— Sol: İngilizce &nbsp;|&nbsp; Sağ: Türkçe &nbsp;|&nbsp; <b style="color:{C["CYAN"]}">Terime tıkla → kopyala</b></span>'
                                            f'</div>'
                                        )
                                    else:
                                        ui.html(
                                            f'<div style="padding:8px 12px;border-radius:8px;margin:6px 0 4px;'
                                            f'background:rgba(255,200,0,.06);border:1px solid rgba(255,200,0,.15);font-size:11px;color:{C["MUTED"]}">'
                                            f'⚠ Termbase yok — "📝 Termbase Oluştur" butonuna bas</div>'
                                        )
                                    _am2 = {"chip-purple":"#a78bfa","chip-cyan":"#22d3ee","chip-green":"#4ade80","chip-yellow":"#facc15","chip-pink":"#f472b6"}
                                    cats_html = ""
                                    for _cat_idx, (cat, items) in enumerate(trms.items()):
                                        chip_cls, label, icon = CAT_COLORS.get(cat, ("chip-purple", cat.capitalize(), "📌"))
                                        _accent = _am2.get(chip_cls, "#a78bfa")
                                        _tr_count = sum(1 for it in items if tbl.get(it.lower(), '').lower() not in ('', it.lower())) if tbl else 0
                                        _pct = round(_tr_count / len(items) * 100) if items else 0
                                        _pct_color = "#4ade80" if _pct >= 80 else "#facc15" if _pct >= 40 else "#ef4444"
                                        _cat_safe    = cat.replace(" ","_").replace("|","_")
                                        _card_id     = f"nxcat_{snfs}_{_cat_safe}"
                                        _card_display = "block" if _cat_idx == 0 else "none"
                                        cats_html += (
                                            f'<div id="{_card_id}" data-nxtab-prefix="{snfs}"'
                                            f' style="display:{_card_display};border-radius:10px;overflow:hidden;border:1px solid {_accent}22;margin-bottom:8px;margin-top:6px">'
                                            f'<div style="display:flex;align-items:center;gap:8px;padding:10px 14px;background:linear-gradient(135deg,{_accent}18,{_accent}08);border-bottom:1px solid {_accent}22">'
                                            f'<span style="font-size:15px">{icon}</span>'
                                            f'<span style="font-size:13px;font-weight:700;color:{_accent}">{label}</span>'
                                            f'<span style="margin-left:auto;display:flex;align-items:center;gap:6px">'
                                            f'<span style="font-size:11px;padding:2px 8px;border-radius:10px;background:{_accent}22;color:{_accent}">{len(items)}</span>'
                                            + (f'<span style="font-size:11px;padding:2px 8px;border-radius:10px;background:{_pct_color}22;color:{_pct_color};font-weight:700">%{_pct}</span>' if htb else '')
                                            + f'</span></div><div style="padding:8px">'
                                        )
                                        if htb:
                                            cats_html += (
                                                f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0;padding:4px 8px 6px;font-size:10px;font-weight:700;letter-spacing:.5px;color:{C["MUTED"]};border-bottom:1px solid {_accent}15;margin-bottom:4px">'
                                                f'<span>🇬🇧 İNGİLİZCE</span><span>🇹🇷 TÜRKÇE</span></div>'
                                            )
                                        cats_html += f'<div style="max-height:400px;overflow-y:auto;scrollbar-width:thin;scrollbar-color:{_accent}44 transparent">'
                                        _copy_js_base = (
                                            "navigator.clipboard.writeText(this.innerText);"
                                            "let t=document.createElement('span');t.textContent='✓';t.style.cssText='position:absolute;right:2px;top:0;font-size:10px;color:#4ade80;pointer-events:none';"
                                            "this.style.position='relative';this.appendChild(t);setTimeout(()=>t.remove(),900)"
                                        )
                                        for i, item in enumerate(items):
                                            _tr = tbl.get(item.lower(), '') if tbl else ''
                                            _translated = _tr and _tr.lower() != item.lower()
                                            _bg = "rgba(255,255,255,.02)" if i % 2 == 0 else "transparent"
                                            if htb:
                                                _tr_d = _tr if _tr else item
                                                _trc  = "#7fffb0" if _translated else C["MUTED"]
                                                _trs  = "font-weight:600" if _translated else "opacity:.5"
                                                cats_html += (
                                                    f'<div class="nx-term-row" data-term="{item.lower()} {_tr_d.lower()}"'
                                                    f' style="display:grid;grid-template-columns:1fr 1fr;gap:0;padding:5px 8px;border-radius:6px;background:{_bg};transition:background .1s"'
                                                    f' onmouseover="this.style.background=\'rgba(255,255,255,.05)\'" onmouseout="this.style.background=\'{_bg}\'">'
                                                    f'<span onclick="{_copy_js_base}" title="Kopyala" style="font-size:12px;color:{C["TEXT"]};padding-right:8px;border-right:1px solid {_accent}20;cursor:pointer;position:relative" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{item}</span>'
                                                    f'<span onclick="{_copy_js_base}" title="Kopyala" style="font-size:12px;color:{_trc};{_trs};padding-left:8px;cursor:pointer;position:relative" onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{_tr_d}</span>'
                                                    f'</div>'
                                                )
                                            else:
                                                cats_html += (
                                                    f'<div class="nx-term-row" data-term="{item.lower()}"'
                                                    f' onclick="{_copy_js_base}" title="Kopyala"'
                                                    f' style="padding:5px 8px;border-radius:6px;background:{_bg};font-size:12px;color:{C["TEXT"]};cursor:pointer"'
                                                    f' onmouseover="this.style.textDecoration=\'underline\'" onmouseout="this.style.textDecoration=\'none\'">{item}</div>'
                                                )
                                        cats_html += '</div></div></div>'
                                    ui.html(cats_html)

                            def _toggle(
                                dd=detail_div, ei=expand_icon, hr=header_row,
                                op=_open, dr=_detail_rendered, rdf=_render_detail
                            ):
                                op[0] = not op[0]
                                if op[0]:
                                    if not dr[0]:
                                        dr[0] = True
                                        rdf()
                                    dd.style("display:block;padding:16px 18px")
                                    ei.set_content('<span style="font-size:14px;transform:rotate(90deg);display:inline-block">▶</span>')
                                    hr.style(
                                        f"display:flex;align-items:center;padding:14px 18px;gap:12px;"
                                        f"background:color-mix(in srgb,var(--accent1) 8%,transparent);"
                                        f"border-bottom:1px solid {C['BORDER']};cursor:pointer;transition:background 0.15s"
                                    )
                                else:
                                    dd.style("display:none;padding:16px 18px")
                                    ei.set_content('<span style="font-size:14px;transition:transform 0.2s">▶</span>')
                                    hr.style(
                                        f"display:flex;align-items:center;padding:14px 18px;gap:12px;"
                                        f"border-bottom:1px solid {C['BORDER']}00;cursor:pointer;transition:background 0.15s"
                                    )
                            header_row.on("click", _toggle)

                # ── Batch render: 8'er 8'er, event loop'a yield ederek ──────────
                BATCH = 8
                def _render_batch(idx=0):
                    chunk = filtered_items[idx:idx + BATCH]
                    for _sn, _sd in chunk:
                        _render_one_series(_sn, _sd)
                    nxt = idx + BATCH
                    if nxt < len(filtered_items):
                        ui.timer(0.0, lambda i=nxt: _render_batch(i), once=True)

                _render_batch(0)
        # İlk yüklemeyi event loop'a defer et — sayfa anında açılır, liste arkadan gelir
        _loading_el = ui.html(
            '<div style="text-align:center;padding:40px;color:var(--muted);font-size:14px">'
            '<div style="display:inline-block;width:28px;height:28px;border:3px solid rgba(255,255,255,0.1);'
            'border-top:3px solid var(--accent1);border-radius:50%;'
            'animation:spin 0.8s linear infinite;margin-bottom:12px"></div>'
            '<br>Sözlük yükleniyor...</div>'
        )
        def _deferred_render():
            _loading_el.delete()
            render_rows()
        ui.timer(0.0, _deferred_render, once=True)

        def _on_search_input(e):
            val = ""
            if isinstance(e.args, str):
                val = e.args
            elif isinstance(e.args, dict):
                val = e.args.get("value", "") or ""
            elif isinstance(e.args, list) and e.args:
                val = str(e.args[0]) if e.args[0] else ""
            render_rows(val.strip())
        search_inp.on("input", _on_search_input)

        # ── Anlık Güncelleme: Çeviri sırasında yeni veri gelince otomatik yenile ──
        # glossary JSON dosyasının mtime'ı değişince → listeyi + sayaçları güncelle
        _last_mtime = [0.0]
        _timer_ref   = [None]
        _page_alive  = [True]

        def _watch_glossary_file():
            """2sn'de bir dosya mtime kontrol et — değiştiyse sayfayı yenile."""
            if not _page_alive[0]:
                if _timer_ref[0]:
                    _timer_ref[0].cancel()
                return
            try:
                import os as _os
                # series_glossary.json mtime
                _m1 = _os.path.getmtime(GLOSSARY_FILE) if _os.path.exists(GLOSSARY_FILE) else 0.0
                # termbase/ klasörü — *_base.json dosyaları
                _tb_dir = _os.path.join(PARENT_DIR, "termbase")
                _m2 = 0.0
                if _os.path.isdir(_tb_dir):
                    for _fn in _os.listdir(_tb_dir):
                        if _fn.endswith("_base.json") or _fn.endswith("_chars.json"):
                            _fp = _os.path.join(_tb_dir, _fn)
                            _fm = _os.path.getmtime(_fp)
                            if _fm > _m2:
                                _m2 = _fm
                _cur_mtime = max(_m1, _m2)

                if _cur_mtime and _cur_mtime != _last_mtime[0]:
                    if _last_mtime[0] > 0:
                        # Dosya değişti → yenile + bildir
                        state["glossary"] = None   # cache'i invalidate et
                        _s = _search_ref[0]
                        _filter = _s.value.strip() if _s else ""
                        _refresh_cb[0](_filter) if _refresh_cb[0] else None
                        # Bildirim göster
                        _cur = get_glossary()
                        _new_tt = sum(sum(len(v) for v in d.get("terms",{}).values()) for d in _cur.values())
                        ui.notify(
                            f"📚 Glossary güncellendi! {len(_cur)} seri · {_new_tt} terim",
                            type="positive", timeout=4000, position="top-right"
                        )
                    _last_mtime[0] = _cur_mtime
            except Exception:
                pass

        _timer_ref[0] = ui.timer(2.0, _watch_glossary_file)
        # İlk mtime'ı ayarla (bildirim tetiklenmesin)
        try:
            import os as _os2
            _m1_init = _os2.path.getmtime(GLOSSARY_FILE) if _os2.path.exists(GLOSSARY_FILE) else 0.0
            _tb_dir2 = _os2.path.join(PARENT_DIR, "termbase")
            _m2_init = 0.0
            if _os2.path.isdir(_tb_dir2):
                for _fn2 in _os2.listdir(_tb_dir2):
                    if _fn2.endswith("_base.json") or _fn2.endswith("_chars.json"):
                        _fm2 = _os2.path.getmtime(_os2.path.join(_tb_dir2, _fn2))
                        if _fm2 > _m2_init:
                            _m2_init = _fm2
            _last_mtime[0] = max(_m1_init, _m2_init)
        except Exception:
            pass




# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────
def _stat_card(icon, label, value, color, bg):
    with ui.element("div").style(
        f"background:{C['CARD']};border:1px solid {C['BORDER']};border-radius:14px;"
        f"padding:18px;display:flex;align-items:center;gap:14px;transition:all 0.25s"
    ):
        ui.html(f'<div style="width:46px;height:46px;border-radius:12px;background:{bg};'
                f'display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0">{icon}</div>')
        ui.html(f'<div><div style="font-size:24px;font-weight:800;color:{color}">{value}</div>'
                f'<div style="font-size:11px;color:{C["SUB"]};margin-top:2px">{label}</div></div>')


def _append_log(log_el, msg, style="white"):
    if log_el:
        log_el.push(msg)


async def _run_proc(cmd, log_el, btn, btn_reset_text):
    """
    Windows'ta asyncio subprocess + PIPE güvenilir değil.
    subprocess.Popen + run_in_executor kullan → 100% stream garantisi.
    """
    import re as _re
    import subprocess
    _ansi = _re.compile(r'\x1b\[[0-9;]*[mGKHF]')
    _script_dir = os.path.dirname(SCRIPT_TRANSLATOR)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"]  = "1"
    env["PYTHONIOENCODING"]  = "utf-8"
    env["NO_COLOR"]          = "1"   # colorama'ya renk kullanma de

    try:
        CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,   # input() çağrılarını anında EOF yap
            cwd=_script_dir,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        state["proc"] = proc

        loop = asyncio.get_running_loop()

        def _read_line():
            """Bloklu readline — executor thread'inde çalışır."""
            return proc.stdout.readline()

        while True:
            line = await loop.run_in_executor(None, _read_line)
            if not line:          # EOF → process bitti
                break
            line = _ansi.sub("", line.rstrip())
            if line and log_el:
                log_el.push(line)

        proc.wait()
        rc = proc.returncode
        _append_log(log_el, f"{'✅' if rc == 0 else '⚠️'} İşlem bitti — çıkış kodu: {rc}")

    except Exception as e:
        _append_log(log_el, f"❌ _run_proc Hata: {e}")
    finally:
        state["running"] = False
        state["proc"]    = None
        btn.set_text(btn_reset_text)


def _select_series(series_name, detail_panel, glossary):
    if detail_panel is None:
        return
    detail_panel.clear()
    data  = glossary.get(series_name, {})
    terms = data.get("terms", {})
    total = sum(len(v) for v in terms.values())
    wiki  = data.get("wiki", "—")
    fetched = data.get("fetched_at", "")[:10] if data.get("fetched_at") else "—"
    CAT_COLORS = {
        "characters": ("chip-purple", "Karakterler", "🧑"),
        "skills":     ("chip-cyan",   "Yetenekler",  "⚡"),
        "locations":  ("chip-green",  "Lokasyonlar", "📍"),
        "items":      ("chip-yellow", "Eşyalar",     "📦"),
        "terminology":("chip-pink",   "Terimler",    "📝"),
    }
    with detail_panel:
        # Başlık satırı
        with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;margin-bottom:20px"):
            with ui.element("div"):
                ui.html(f'<div style="font-size:18px;font-weight:800;color:var(--accent1)">{series_name}</div>')
                ui.html(f'<div style="font-size:12px;color:{data["C"]["SUB"] if "C" in data else "#888"};margin-top:3px">Wiki: {wiki} · Son güncelleme: {fetched}</div>' if False else
                        f'<div style="font-size:12px;color:#888;margin-top:3px">Wiki: {wiki} · Son güncelleme: {fetched}</div>')
            ui.html(f'<span style="font-size:28px;font-weight:800;color:var(--accent2)">{total}</span><span style="font-size:11px;color:#888;display:block;text-align:center">TERIM</span>')

        # Kategori kartları grid
        with ui.element("div").style("display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px"):
            for cat, items in terms.items():
                chip_cls, label, icon = CAT_COLORS.get(cat, ("chip-purple", cat.capitalize(), "📌"))
                with ui.element("div").classes("card").style("padding:14px"):
                    ui.html(
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
                        f'<span style="font-size:18px">{icon}</span>'
                        f'<span style="font-size:13px;font-weight:700;color:var(--text)">{label}</span>'
                        f'<span class="chip {chip_cls}" style="margin-left:auto">{len(items)}</span>'
                        f'</div>'
                    )
                    with ui.element("div").style("display:flex;flex-wrap:wrap;gap:4px;max-height:120px;overflow-y:auto"):
                        for item in items[:30]:
                            ui.html(f'<span class="chip {chip_cls}" style="font-size:10px">{item}</span>')
                        if len(items) > 30:
                            ui.html(f'<span class="chip chip-purple" style="font-size:10px">+{len(items)-30} daha</span>')
