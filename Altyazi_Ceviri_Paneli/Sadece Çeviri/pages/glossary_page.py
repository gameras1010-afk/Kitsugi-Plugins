"""
pages/glossary_page.py
======================
Sözlük sayfası.
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
from pages.helpers import get_prefs, get_glossary, state, nbtn

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
