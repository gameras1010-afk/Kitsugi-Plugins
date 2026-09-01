"""
pages/dashboard.py
==================
Dashboard sayfası.
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
from pages.helpers import get_prefs, get_glossary, state, nbtn, refresh_status

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

