"""
pages/notifications.py
======================
Bildirimler sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

def build_notifications():
    import sys as _sys, os as _os, time as _time, json as _json, datetime as _dt

    _nb_dir = _os.path.normpath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
    if _nb_dir not in _sys.path:
        _sys.path.insert(0, _nb_dir)
    try:
        from notif_bus import get_history, clear_history, get_history_stats
        _hist_path = _os.path.join(_nb_dir, "_notif_history.jsonl")
    except ImportError:
        ui.html('<div style="color:#ef4444;padding:40px">notif_bus modulu bulunamadi</div>')
        return

    C2      = C
    _panel  = C2.get("PANEL",  "#0d0f1e")
    _border = C2.get("BORDER", "#1e2035")
    _text   = C2.get("TEXT",   "#e2e8f0")
    _muted  = C2.get("SUB",    "#4a4f7a")
    _green  = C2.get("GREEN",  "#10b981")
    _yellow = C2.get("YELLOW", "#f59e0b")
    _red    = C2.get("RED",    "#ef4444")
    _blue   = "#3b82f6"
    _cyan   = C2.get("CYAN",   "#00d4ff")

    TYPE_META = {
        "positive": {"color": _green,  "bg": "rgba(16,185,129,0.12)",  "border_col": "rgba(16,185,129,0.35)",  "icon": "✅", "label": "Başarı"},
        "warning":  {"color": _yellow, "bg": "rgba(245,158,11,0.12)",  "border_col": "rgba(245,158,11,0.35)",  "icon": "⚠️", "label": "Uyarı"},
        "negative": {"color": _red,    "bg": "rgba(239,68,68,0.12)",   "border_col": "rgba(239,68,68,0.35)",   "icon": "❌", "label": "Hata"},
        "info":     {"color": _blue,   "bg": "rgba(59,130,246,0.12)",  "border_col": "rgba(59,130,246,0.35)",  "icon": "ℹ️", "label": "Bilgi"},
    }

    _filter = {"type": "all", "search": ""}

    # ── Başlık ──────────────────────────────────────────────────────────
    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🔔 Bildirim Geçmişi</div>')
        ui.html('<div class="ph-sub">Pipeline olayları — çeviri, DB, API, QA bildirimleri</div>')

    with ui.element("div").style("padding:16px 28px 20px;display:flex;flex-direction:column;gap:14px"):

        # ── İSTATİSTİK KARTLARI ─────────────────────────────────────────
        def _render_stats():
            s = get_history_stats()
            last = _dt.datetime.fromtimestamp(s["last_ts"]).strftime("%d.%m %H:%M") if s["last_ts"] else "—"
            cards = [
                ("📊", s["total"],    _cyan,   "TOPLAM"),
                ("✅", s["positive"], _green,  "BAŞARI"),
                ("⚠️", s["warning"],  _yellow, "UYARI"),
                ("❌", s["negative"], _red,    "HATA"),
                ("ℹ️", s["info"],     _blue,   "BİLGİ"),
                ("🕐", last,          _muted,  "SON"),
            ]
            rows = '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:10px">'
            for ico, val, col, lbl in cards:
                rows += (
                    f'<div style="background:{_panel};border:1px solid {_border};border-radius:12px;'
                    f'padding:14px 10px;text-align:center;position:relative;overflow:hidden">'
                    f'<div style="position:absolute;inset:0;background:linear-gradient(135deg,{col}22,transparent);pointer-events:none"></div>'
                    f'<div style="font-size:18px;margin-bottom:4px">{ico}</div>'
                    f'<div style="font-size:22px;font-weight:800;color:{col};line-height:1">{val}</div>'
                    f'<div style="font-size:9px;font-weight:700;color:{_muted};letter-spacing:1.5px;margin-top:4px">{lbl}</div>'
                    f'</div>'
                )
            rows += '</div>'
            return rows

        stats_el = ui.html(_render_stats())

        # ── ARAÇ ÇUBUĞU ─────────────────────────────────────────────────
        with ui.element("div").classes("card").style("padding:12px 16px"):
            with ui.element("div").style("display:flex;align-items:center;gap:10px;flex-wrap:wrap"):

                _fa = ("padding:5px 14px;border-radius:99px;font-size:11px;font-weight:700;cursor:pointer;"
                       "background:color-mix(in srgb,var(--accent1) 22%,transparent);"
                       "border:1px solid var(--accent1);color:var(--accent1);transition:all 0.2s")
                _fi = (f"padding:5px 14px;border-radius:99px;font-size:11px;font-weight:700;cursor:pointer;"
                       f"background:{_panel};border:1px solid {_border};color:{_muted};transition:all 0.2s")

                _filt_items = [
                    ("all",      "🔔 Tümü"),
                    ("positive", "✅ Başarı"),
                    ("warning",  "⚠️ Uyarı"),
                    ("negative", "❌ Hata"),
                    ("info",     "ℹ️ Bilgi"),
                ]
                _filt_btns = {}
                for fkey, flbl in _filt_items:
                    btn_el = ui.html(f'<div style="{_fa if fkey == "all" else _fi}">{flbl}</div>')
                    _filt_btns[fkey] = (btn_el, flbl)

                list_wrap = [None]  # forward ref

                def _make_filt(k):
                    def _click():
                        _filter["type"] = k
                        for fk2, (fb2, lbl2) in _filt_btns.items():
                            fb2.set_content(f'<div style="{_fa if fk2 == k else _fi}">{lbl2}</div>')
                        if list_wrap[0]:
                            _render_list(list_wrap[0])
                    return _click
                for fkey, _ in _filt_items:
                    _filt_btns[fkey][0].on("click", _make_filt(fkey))

                ui.html(f'<div style="width:1px;height:28px;background:{_border};margin:0 4px"></div>')
                search_inp = ui.input(placeholder="🔍 Bildirim ara...").style(
                    f"flex:1;min-width:180px;background:{_panel};color:{_text};"
                    f"border:1px solid {_border};border-radius:9px;padding:6px 12px;font-size:12px"
                )
                def _on_search(e):
                    _filter["search"] = (e.args if isinstance(e.args, str) else search_inp.value).lower()
                    if list_wrap[0]:
                        _render_list(list_wrap[0])
                search_inp.on("update:model-value", _on_search)

                ui.html(f'<div style="width:1px;height:28px;background:{_border};margin:0 4px"></div>')

                def _refresh():
                    stats_el.set_content(_render_stats())
                    if list_wrap[0]:
                        _render_list(list_wrap[0])
                    ui.notify("Yenilendi ✓", type="positive", timeout=1500)

                def _export_json():
                    hist = get_history(limit=500)
                    if not hist:
                        ui.notify("Geçmiş boş", type="info"); return
                    out = _os.path.join(_nb_dir, "_notif_export.json")
                    with open(out, "w", encoding="utf-8") as f:
                        _json.dump(hist, f, ensure_ascii=False, indent=2)
                    ui.notify(f"Dışa aktarıldı: {_os.path.basename(out)}", type="positive", timeout=5000)

                def _export_txt():
                    hist = get_history(limit=500)
                    if not hist:
                        ui.notify("Geçmiş boş", type="info"); return
                    out = _os.path.join(_nb_dir, "_notif_export.txt")
                    with open(out, "w", encoding="utf-8") as f:
                        for n in reversed(hist):
                            ts = _dt.datetime.fromtimestamp(n.get("ts", 0)).strftime("%d.%m.%Y %H:%M:%S")
                            f.write(f"[{ts}] [{n.get('type','info').upper():8s}] {n.get('msg','')}\n")
                    ui.notify(f"TXT aktarıldı: {_os.path.basename(out)}", type="positive", timeout=5000)

                _clr_c = [False]
                def _clear_all():
                    if not _clr_c[0]:
                        _clr_c[0] = True
                        ui.notify("⚠️ Tüm geçmiş silinecek — onaylamak için tekrar tıklayın!", type="warning", timeout=3000)
                        def _cancel(): _clr_c[0] = False
                        ui.timer(3.0, _cancel, once=True)
                        return
                    _clr_c[0] = False
                    clear_history()
                    stats_el.set_content(_render_stats())
                    if list_wrap[0]:
                        _render_list(list_wrap[0])
                    ui.notify("🗑️ Bildirim geçmişi temizlendi", type="warning", timeout=3000)

                nbtn("🔄 Yenile",      click=_refresh,     variant="ghost",  size="sm")
                nbtn("📤 JSON",        click=_export_json, variant="ghost",  size="sm")
                nbtn("📄 TXT",         click=_export_txt,  variant="ghost",  size="sm")
                nbtn("🗑️ Tümünü Sil", click=_clear_all,   variant="danger", size="sm")

        # ── BİLDİRİM LİSTESİ ────────────────────────────────────────────
        _lw = ui.element("div").style("display:flex;flex-direction:column;gap:8px")
        list_wrap[0] = _lw

        def _render_list(container):
            hist = get_history(limit=200)
            ftype = _filter["type"]
            fsrch = _filter["search"]
            if ftype != "all":
                hist = [n for n in hist if n.get("type") == ftype]
            if fsrch:
                hist = [n for n in hist if fsrch in n.get("msg", "").lower()]
            with container:
                container.clear()
                if not hist:
                    ui.html(
                        f'<div style="text-align:center;padding:60px 20px;color:{_muted}">'
                        f'<div style="font-size:48px;margin-bottom:12px">🔕</div>'
                        f'<div style="font-size:16px;font-weight:700;margin-bottom:6px">Bildirim yok</div>'
                        f'<div style="font-size:12px">Çeviri başlatıldığında bildirimler burada görünecek</div>'
                        f'</div>'
                    )
                    return
                for n in hist:
                    ntype = n.get("type", "info")
                    meta  = TYPE_META.get(ntype, TYPE_META["info"])
                    msg   = n.get("msg", "")
                    ts    = n.get("ts", 0)
                    ts_str = _dt.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S") if ts else "—"
                    diff   = _time.time() - ts
                    if   diff < 60:    age = f"{int(diff)}sn önce"
                    elif diff < 3600:  age = f"{int(diff//60)}dk önce"
                    elif diff < 86400: age = f"{int(diff//3600)}sa önce"
                    else:              age = f"{int(diff//86400)}g önce"

                    ui.html(
                        f'<div style="display:flex;align-items:center;gap:12px;'
                        f'background:{meta["bg"]};border:1px solid {meta["border_col"]};'
                        f'border-left:3px solid {meta["color"]};border-radius:10px;'
                        f'padding:11px 16px;transition:all 0.2s">'
                        f'<span style="font-size:18px;flex-shrink:0">{meta["icon"]}</span>'
                        f'<div style="flex:1;min-width:0">'
                        f'<div style="font-size:13px;font-weight:600;color:{_text};'
                        f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{msg}</div>'
                        f'<div style="display:flex;align-items:center;gap:10px;margin-top:3px">'
                        f'<span style="font-size:10px;color:{meta["color"]};font-weight:700">{meta["label"]}</span>'
                        f'<span style="font-size:10px;color:{_muted}">{ts_str}</span>'
                        f'<span style="font-size:10px;color:{_muted};font-style:italic">{age}</span>'
                        f'</div></div>'
                        f'<span style="font-size:9px;font-weight:700;color:{meta["color"]};'
                        f'background:{meta["border_col"]};border-radius:6px;padding:2px 8px;letter-spacing:0.5px;flex-shrink:0">'
                        f'{ntype.upper()}</span>'
                        f'</div>'
                    )

        _render_list(_lw)

        # ── OTO-YENİLE (çeviri sırasında canlı) ─────────────────────────
        def _auto():
            stats_el.set_content(_render_stats())
            _render_list(_lw)
        ui.timer(4.0, _auto)

        # ── ALT BİLGİ ────────────────────────────────────────────────────
        ui.html(
            f'<div style="text-align:center;font-size:10px;color:{_muted};padding:8px 0">'
            f'📁 Geçmiş: <span style="font-family:Consolas,monospace">{_hist_path}</span>'
            f' &nbsp;·&nbsp; Son 200 gösteriliyor (max 500 saklanır)'
            f'</div>'
        )


# ── API ANAHTARLARI sayfası ───────────────────────────────────────────────────
