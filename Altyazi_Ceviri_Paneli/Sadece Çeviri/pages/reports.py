"""
pages/reports.py
================
Çeviri raporu sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

def build_reports():
    """HTML rapor yonetim sayfasi - coklu dizin tarar, inline iframe goruntuler."""
    import glob
    from datetime import datetime as dt
    from ng_config import REPORTS_CENTRAL_DIR

    # Aranacak dizinler — merkezi reports/ önce gelir
    SEARCH_DIRS = [
        REPORTS_CENTRAL_DIR,                                               # ← MERKEZİ KLASÖR (her çeviriden kopyalanır)
        REPORT_DIR,                                                        # ng_config'den gelen REPORT_DIR
        BASE_DIR,                                                          # Sadece Çeviri/ kendisi
        os.path.join(BASE_DIR, "Çevrilenler"),                            # Çevrilenler/
        os.path.join(BASE_DIR, "Çevrilecekler"),                          # Çevrilecekler/
        PARENT_DIR,                                                        # Python kodları/
        os.path.join(PARENT_DIR, "reports"),                               # reports/ (parent)
    ]

    def _scan_reports():
        """Tüm dizinleri özyinelemeli tara, .html / .report.html dosyalarını döndür."""
        found = {}  # path -> (name, mtime, size, dir_label)

        def _label(d):
            """Dizin için kısa etiket üret."""
            try:
                rel = os.path.relpath(d, PARENT_DIR).replace("\\", "/")
                return rel + "/"
            except Exception:
                return os.path.basename(d) + "/"

        for d in SEARCH_DIRS:
            if not os.path.isdir(d):
                continue
            lbl = _label(d)
            # Alt klasörler dahil tüm .html dosyaları
            for root, dirs, files in os.walk(d):
                dirs[:] = [x for x in dirs if x != "__pycache__"]  # pycache atla
                for fname in files:
                    if not fname.lower().endswith(".html"):
                        continue
                    fpath = os.path.join(root, fname)
                    if fpath in found:
                        continue
                    # Alt klasör varsa etiket güncelle
                    sub_lbl = os.path.relpath(root, PARENT_DIR).replace("\\", "/") + "/"
                    found[fpath] = (
                        fname,
                        os.path.getmtime(fpath),
                        os.path.getsize(fpath),
                        sub_lbl,
                    )

        return sorted(found.items(), key=lambda x: x[1][1], reverse=True)

    reports = _scan_reports()

    with ui.element("div").classes("page-header").style(
        "display:flex;align-items:center;justify-content:space-between"
    ):
        with ui.element("div"):
            ui.html('<div class="ph-title">📄 Raporlar &amp; QA</div>')
            ui.html(f'<div class="ph-sub">HTML raporları görüntüle · QA kalite kontrolü çalıştır '
                    f'· <span style="color:{C["CYAN"]};font-size:10px">{REPORTS_CENTRAL_DIR}</span></div>')
        with ui.element("div").style("display:flex;gap:8px;align-items:center;margin-right:8px"):
            nbtn("📂 Klasör Aç", click=lambda: os.startfile(REPORTS_CENTRAL_DIR), variant="ghost", size="sm")
            # Yenile: sayfayı SPA state ile yenile (route yok, tek sayfa app)
            nbtn("🔄 Yenile",     click=lambda: ui.run_javascript("location.reload()"), variant="ghost", size="sm")

    with ui.element("div").style("padding:0 28px 28px;display:flex;flex-direction:column;gap:16px"):

        if not reports:
            # Boş durum — ama QA bölümünü yine de göster
            with ui.element("div").classes("card").style("text-align:center;padding:40px"):
                ui.html('<div style="font-size:40px;margin-bottom:12px">📭</div>')
                ui.html(f'<div style="font-size:14px;font-weight:700;color:{C["TEXT"]};margin-bottom:6px">Henüz HTML rapor yok</div>')
                ui.html(f'<div style="font-size:12px;color:{C["MUTED"]}">Çeviri sonrası otomatik üretilir ya da aşağıdan QA çalıştırın.</div>')

        # ── İstatistik satırı ──
        total_size = sum(r[1][2] for r in reports)
        size_str = f"{total_size/1024:.0f} KB" if total_size < 1024*1024 else f"{total_size/1024/1024:.1f} MB"
        with ui.element("div").style("display:flex;gap:12px;flex-wrap:wrap"):
            def _stat_chip(icon, val, lbl, col):
                ui.html(
                    f'<div style="display:flex;align-items:center;gap:8px;padding:8px 16px;'
                    f'border-radius:99px;background:{C["CARD"]};border:1px solid {C["BORDER"]}">'
                    f'<span style="font-size:16px">{icon}</span>'
                    f'<div><div style="font-size:13px;font-weight:800;color:{col}">{val}</div>'
                    f'<div style="font-size:10px;color:{C["MUTED"]}">{lbl}</div></div></div>'
                )
            _stat_chip("📄", str(len(reports)), "Toplam Rapor", C["CYAN"])
            _stat_chip("💾", size_str, "Toplam Boyut", C["GREEN"])
            _stat_chip("📁", str(len({r[1][3] for r in reports})), "Dizin", C["PURPLE"])

        # ── QA Çalıştır Kartı ──────────────────────────────────────────────────
        from ng_config import SCRIPT_QA
        _qa_state = {"running": False, "ok": "—", "warn": "—", "err": "—", "tag": "—"}

        with ui.element("div").classes("card card-cyan").style("padding:16px 20px"):
            ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">✅ QA KALİTE KONTROLÜ</div>')

            # Dosya seç + çalıştır
            with ui.element("div").style("display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap"):
                qa_path_inp = ui.input(
                    placeholder="ASS / SRT dosya yolu..."
                ).style(
                    f"flex:1;min-width:200px;background:{C['PANEL']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:{C['TEXT']};font-size:12px;"
                    f"font-family:Consolas,monospace"
                )

                def browse_ass():
                    try:
                        import tkinter as tk
                        from tkinter import filedialog
                        root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                        chosen = filedialog.askopenfilename(
                            title="ASS / SRT dosyası seç",
                            filetypes=[("Altyazı", "*.ass *.srt"), ("Tümü", "*.*")]
                        )
                        root.destroy()
                        if chosen:
                            qa_path_inp.value = chosen
                    except Exception as e:
                        ui.notify(f"Hata: {e}", type="negative")

                nbtn("📁", click=browse_ass, variant="icon", size="sm")

                # Stat etiketleri — canlı güncellenir
                qa_ok_lbl   = ui.html(f'<span class="chip chip-green">✅ —</span>')
                qa_warn_lbl = ui.html(f'<span class="chip chip-yellow">⚠️ —</span>')
                qa_err_lbl  = ui.html(f'<span class="chip chip-red">❌ —</span>')
                qa_tag_lbl  = ui.html(f'<span class="chip" style="background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.4);color:#a78bfa">🔠 —</span>')

            # Progress log kutusu
            qa_log = ui.element("div").style(
                f"background:{C['BG']};border:1px solid {C['BORDER']};border-radius:9px;"
                f"padding:10px 14px;font-family:Consolas,monospace;font-size:11px;"
                f"color:{C['SUB']};min-height:48px;max-height:120px;overflow-y:auto;"
                f"white-space:pre-wrap;margin-bottom:12px"
            )
            with qa_log:
                ui.html(f'<span style="color:{C["MUTED"]}">QA çalıştırmak için dosya seçin ve butona basın...</span>')

            async def run_qa():
                import asyncio
                fpath = qa_path_inp.value.strip()
                if not fpath:
                    ui.notify("Önce bir ASS/SRT dosyası seçin!", type="warning"); return
                if not os.path.exists(fpath):
                    ui.notify("Dosya bulunamadı!", type="negative"); return
                if _qa_state["running"]:
                    ui.notify("QA zaten çalışıyor...", type="info"); return

                _qa_state["running"] = True
                qa_log.clear()
                with qa_log:
                    ui.html(f'<span style="color:{C["CYAN"]}">QA başlatılıyor: {os.path.basename(fpath)}...</span>')

                try:
                    _no_win = 0x08000000 if os.name == "nt" else 0
                    proc = await asyncio.create_subprocess_exec(
                        "python", SCRIPT_QA, fpath,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        creationflags=_no_win,
                        cwd=PARENT_DIR,
                    )
                    stdout, _ = await proc.communicate()
                    output = stdout.decode("utf-8", errors="replace") if stdout else ""

                    # Log'u güncelle
                    qa_log.clear()
                    with qa_log:
                        ui.html(output.replace("\n", "<br>").replace(" ", "&nbsp;"))

                    # İstatistikleri parse et
                    import re as _re
                    def _find(pat):
                        m = _re.search(pat, output, _re.IGNORECASE)
                        return m.group(1) if m else "—"
                    ok   = _find(r'(?:basarili|ok|success)[^\d]*(\d+)')
                    warn = _find(r'(?:uyari|warn)[^\d]*(\d+)')
                    err  = _find(r'(?:hata|error)[^\d]*(\d+)')
                    tag  = _find(r'(?:tag|ass)[^\d]*(\d+)')

                    qa_ok_lbl.set_content(f'<span class="chip chip-green">✅ {ok}</span>')
                    qa_warn_lbl.set_content(f'<span class="chip chip-yellow">⚠️ {warn}</span>')
                    qa_err_lbl.set_content(f'<span class="chip chip-red">❌ {err}</span>')
                    qa_tag_lbl.set_content(f'<span class="chip" style="background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.4);color:#a78bfa">🔠 {tag}</span>')

                    if proc.returncode == 0:
                        ui.notify("QA tamamlandı ✅", type="positive")
                    else:
                        ui.notify("QA bitti (bazı hatalar var)", type="warning")

                except Exception as e:
                    qa_log.clear()
                    with qa_log:
                        ui.html(f'<span style="color:{C["RED"]}">Hata: {e}</span>')
                    ui.notify(f"QA hatası: {e}", type="negative")
                finally:
                    _qa_state["running"] = False

            nbtn("▶ QA ÇALIŞTIR", click=run_qa, full=True)

        _selected = {"path": reports[0][0] if reports else None}

        with ui.element("div").style("display:flex;gap:16px;height:calc(100vh - 320px);min-height:400px"):

            # ── Sol: Rapor Listesi ──
            with ui.element("div").classes("card").style(
                "width:320px;flex-shrink:0;display:flex;flex-direction:column;padding:0;overflow:hidden"
            ):
                # Başlık
                ui.html(f"""
                <div style="padding:12px 16px;background:{C['PANEL']};border-bottom:1px solid {C['BORDER']}">
                  <span style="font-size:11px;font-weight:800;color:{C['SUB']};letter-spacing:1.5px">
                    RAPORLAR ({len(reports)})
                  </span>
                </div>
                """)

                # ── Batch render: ilk 30 hemen, geri kalanı timer ile ──
                _BATCH_SIZE = 30
                _rpt_queue  = list(reports)   # kopyala
                _rpt_idx    = [0]
                _rpt_timer  = [None]

                with ui.element("div").style("flex:1;overflow-y:auto") as _list_wrap:

                    def _render_one_row(fpath, fname, mtime, size, dir_label):
                        ts     = dt.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M")
                        fsize  = f"{size/1024:.0f} KB"
                        is_sel = (fpath == _selected["path"])

                        with ui.element("div").style(
                            f"padding:12px 14px;border-bottom:1px solid {C['BORDER']};"
                            f"cursor:pointer;transition:background 0.15s;"
                            + (f"background:color-mix(in srgb,var(--accent1) 12%,transparent)"
                               if is_sel else "")
                        ) as row_div:
                            ui.html(
                                f'<div style="font-size:12px;font-weight:700;'
                                f'color:{"var(--accent1)" if is_sel else C["TEXT"]};'
                                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:240px">'
                                f'{fname}</div>'
                                f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:3px;display:flex;gap:8px">'
                                f'<span>📁 {dir_label}</span>'
                                f'<span>🕐 {ts}</span>'
                                f'<span>💾 {fsize}</span></div>'
                            )

                            def select_report(p=fpath, rd=row_div):
                                from urllib.parse import quote as _q
                                _selected["path"] = p
                                encoded_p = _q(p)
                                ui.run_javascript(
                                    "document.querySelectorAll('.rpt-row').forEach(function(el){"
                                    "  el.style.background='';"
                                    "});"
                                    f"var me=document.getElementById('rpt-{id(rd)}');"
                                    "if(me)me.style.background='color-mix(in srgb,var(--accent1) 12%,transparent)';"
                                    f"var ifr=document.getElementById('report-iframe');"
                                    f"if(ifr) ifr.src='/api/serve_report?path={encoded_p}&t='+Date.now();"
                                )
                                ui.notify(f"Rapor: {os.path.basename(p)}", type="info", timeout=1200)

                            row_div.props(f'id="rpt-{id(row_div)}"').classes("rpt-row")
                            row_div.on("click", select_report)

                    def _render_batch():
                        with _list_wrap:
                            end = min(_rpt_idx[0] + _BATCH_SIZE, len(_rpt_queue))
                            for i in range(_rpt_idx[0], end):
                                fp, (fn, mt, sz, dl) = _rpt_queue[i]
                                _render_one_row(fp, fn, mt, sz, dl)
                            _rpt_idx[0] = end
                        if _rpt_idx[0] >= len(_rpt_queue):
                            if _rpt_timer[0]:
                                _rpt_timer[0].cancel()

                    # İlk batch hemen
                    _render_batch()
                    # Geri kalanlar timer ile
                    if _rpt_idx[0] < len(_rpt_queue):
                        _rpt_timer[0] = ui.timer(0.05, _render_batch)


            # ── Sağ: iframe Görüntüleyici ──
            with ui.element("div").classes("card").style(
                "flex:1;display:flex;flex-direction:column;padding:0;overflow:hidden"
            ):
                # Araç çubuğu
                with ui.element("div").style(
                    f"padding:10px 16px;background:{C['PANEL']};border-bottom:1px solid {C['BORDER']};"
                    f"display:flex;align-items:center;gap:10px;flex-shrink:0"
                ):
                    ui.html(f'<span style="font-size:12px;font-weight:700;color:{C["SUB"]};flex:1">'
                            f'📄 Rapor Önizleme</span>')

                    def open_in_browser():
                        if _selected["path"] and os.path.exists(_selected["path"]):
                            os.startfile(_selected["path"])

                    def open_folder():
                        if _selected["path"]:
                            os.startfile(os.path.dirname(_selected["path"]))

                    def delete_report():
                        if _selected["path"] and os.path.exists(_selected["path"]):
                            try:
                                os.remove(_selected["path"])
                                ui.notify("Rapor silindi", type="warning")
                                ui.run_javascript(
                                    "var ifr=document.getElementById('report-iframe');"
                                    "if(ifr) ifr.src='about:blank';"
                                )
                            except Exception as e:
                                ui.notify(f"Silinemedi: {e}", type="negative")

                    nbtn("🌐 Tarayıcıda Aç", click=open_in_browser, size="sm", variant="ghost")
                    nbtn("📁 Klasörü Aç",   click=open_folder,     size="sm", variant="ghost")
                    nbtn("🗑️ Sil",           click=delete_report,   size="sm", variant="danger")

                # ── iframe container — JS inject ile NiceGUI wrapper sorununu aş ──
                from urllib.parse import quote as _urlquote
                first_path = reports[0][0] if reports else ""
                first_url  = "/api/serve_report?path=" + _urlquote(first_path) + "&t=0"

                # Placeholder div — JS bu div'in içine iframe'i inject eder
                _ifr_wrap = ui.element("div").style(
                    "flex:1;min-height:0;width:100%;overflow:hidden;"
                    "background:#fff"
                ).props('id="report-iframe-wrap"')

                # DOM yüklendikten sonra iframe'i inject et
                # height = 100vh - toolbar - header - stats - qa card - margin payı
                ui.run_javascript(f"""
                    (function() {{
                        var wrap = document.getElementById('report-iframe-wrap');
                        if(!wrap) return;
                        var ifr = document.createElement('iframe');
                        ifr.id    = 'report-iframe';
                        ifr.src   = '{first_url}';
                        ifr.style.cssText = 'width:100%;height:calc(100vh - 380px);min-height:360px;border:none;display:block;background:#fff';
                        wrap.appendChild(ifr);
                        // Pencere resize'a karşı yüksekliği güncelle
                        window._nxIfrResize = function() {{
                            ifr.style.height = Math.max(360, window.innerHeight - 380) + 'px';
                        }};
                        if(!window._nxIfrResizeBound) {{
                            window.addEventListener('resize', window._nxIfrResize);
                            window._nxIfrResizeBound = true;
                        }}
                    }})();
                """)



# ── VERİ KAYNAKLARI sayfası ───────────────────────────────────────────────────
