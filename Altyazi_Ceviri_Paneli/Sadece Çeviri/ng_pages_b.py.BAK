"""
ng_pages_b.py — QA Report + Settings + Tema & Ses sayfaları
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from ng_pages_a import get_prefs, state, nbtn

# ── TEMA & SES sayfası ────────────────────────────────────────────────────────
def build_theme_page():
    from ng_app import THEME_DEFS, _theme, _sound, _sidebar, apply_theme_js
    from ng_config import load_prefs, save_prefs

    cur = _theme["current"]

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🎨 Tema &amp; Ses Ayarları</div>')
        ui.html('<div class="ph-sub">Renk paleti, görsel efektler ve ses sistemi</div>')

    with ui.element("div").style("padding:0 28px 20px;display:flex;flex-direction:column;gap:20px"):

        # ── Tema kartları ──
        with ui.element("div").classes("card"):
            ui.html(f'<div class="card-title">🎨 RENK PALETİ — {len(THEME_DEFS)} TEMA</div>')
            with ui.element("div").style(
                "display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:4px"
            ):
                for tid, td in THEME_DEFS.items():
                    is_t = (tid == cur)

                    def set_theme(t=tid):
                        _theme["current"] = t
                        td2 = THEME_DEFS[t]
                        p = load_prefs()
                        p["ui_theme"] = t
                        save_prefs(p)
                        ui.run_javascript(f"""
                            {apply_theme_js(t)}

                            // Checkmark'ları güncelle
                            document.querySelectorAll('.theme-check-overlay').forEach(function(el) {{
                                el.style.display = 'none';
                            }});
                            var chk = document.getElementById('theme-check-{t}');
                            if(chk) chk.style.display = 'flex';

                            // Kart border/shadow
                            document.querySelectorAll('.theme-card-wrapper').forEach(function(el) {{
                                el.style.border = '2px solid rgba(255,255,255,0.08)';
                                el.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
                            }});
                            var ac = document.getElementById('theme-card-{t}');
                            if(ac) {{
                                ac.style.border = '2px solid {td2["border"]}';
                                ac.style.boxShadow = '0 0 20px {td2["badge"]}, 0 4px 20px rgba(0,0,0,0.3)';
                            }}

                            // Sidebar AKTİF TEMA badge
                            var badge = document.getElementById('active-theme-badge');
                            if(badge) {{
                                badge.style.borderColor = '{td2["border"]}';
                                badge.style.boxShadow = '0 0 14px {td2["badge"]}';
                            }}
                            var grad = document.getElementById('active-theme-gradient');
                            if(grad) grad.style.background = 'linear-gradient(135deg,{td2["g1"]},{td2["g2"]})';
                            var bg = document.getElementById('active-theme-bg');
                            if(bg) bg.style.background = '{td2["g3"]}';
                            var icon = document.getElementById('active-theme-icon');
                            if(icon) icon.textContent = '{td2["icon"]}';
                            var nm = document.getElementById('active-theme-name');
                            if(nm) nm.textContent = '{td2["name"]}';
                            // Logo .logo-title-gradient class var(--accent1/2) kullanir

                            if(window.NexusSound) NexusSound.themeChange();
                        """)
                        ui.timer(0.15, _sidebar.refresh, once=True)
                        ui.notify(f"Tema: {THEME_DEFS[t]['name']} ✓", type="positive")

                    # Kart wrapper — ID ile
                    chk_display = "flex" if is_t else "none"
                    border_style = td["border"] if is_t else "rgba(255,255,255,0.08)"
                    shadow_style = f"0 0 20px {td['badge']}, 0 4px 20px rgba(0,0,0,0.3)" if is_t else "0 4px 12px rgba(0,0,0,0.2)"

                    with ui.element("div").style(
                        f"border-radius:14px;overflow:hidden;cursor:pointer;"
                        f"border:2px solid {border_style};"
                        f"box-shadow:{shadow_style};"
                        f"transition:all 0.3s cubic-bezier(.4,0,.2,1)"
                    ).props(f'id="theme-card-{tid}"').classes("theme-card-wrapper").on("click", set_theme):
                        # Gradient banner + checkmark
                        ui.html(
                            f'<div style="height:64px;background:linear-gradient(135deg,{td["g1"]},{td["g2"]});'
                            f'position:relative;display:flex;align-items:center;justify-content:center">'
                            f'<span style="font-size:28px;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.4))">{td["icon"]}</span>'
                            f'<div id="theme-check-{tid}" class="theme-check-overlay" '
                            f'style="display:{chk_display};position:absolute;top:8px;right:10px;'
                            f'background:rgba(255,255,255,0.25);border-radius:50%;width:22px;height:22px;'
                            f'align-items:center;justify-content:center;font-size:13px;font-weight:700">✓</div>'
                            f'</div>'
                        )
                        # İsim & renk bantları
                        ui.html(
                            f'<div style="padding:12px 14px;background:{td["g3"]}">'
                            f'<div style="font-size:14px;font-weight:{"800" if is_t else "600"};'
                            f'color:{"#e2e8f0" if is_t else "#a9b1d6"}">{td["name"]}</div>'
                            f'<div style="font-size:11px;color:#4a4f7a;margin-top:3px">{td["sub"]}</div>'
                            f'<div style="display:flex;gap:6px;margin-top:8px">'
                            f'<div style="width:20px;height:8px;border-radius:99px;background:{td["g1"]}"></div>'
                            f'<div style="width:20px;height:8px;border-radius:99px;background:{td["g2"]}"></div>'
                            f'<div style="flex:1;height:8px;border-radius:99px;background:{td["g3"]};'
                            f'border:1px solid rgba(255,255,255,0.1)"></div>'
                            f'</div></div>'
                        )

        # ── Görsel Efektler ──
        with ui.element("div").classes("card"):
            ui.html(f'<div class="card-title">✨ GÖRSEL EFEKTLER</div>')
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:12px"):
                _vfx_toggle("Aurora Arka Plan",      "Animasyonlu neon arka plan efekti", True, "document.body.style.setProperty('--aurora-opacity', v ? '1' : '0')")
                _vfx_toggle("Scan-line Overlay",     "İnce CRT tarama çizgileri",         True, "document.body.classList.toggle('no-scanline', !v)")
                _vfx_toggle("Glassmorphism",         "Kartlarda cam efekti + blur",        True, "")
                _vfx_toggle("3D Kart Hover",         "Hover'da yukarı kalkma animasyonu", True, "")
                _vfx_toggle("Sayfa Geçiş Animasyonu","Fade + scale geçiş efekti",         True, "")
                _vfx_toggle("Neon Glow",             "Aktif elemanlarda parlama efekti",  True, "")

        # ── Ses Sistemi ──
        with ui.element("div").classes("card card-cyan"):
            ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">🔊 SES SİSTEMİ</div>')
            snd_on = _sound["on"]

            with ui.element("div").style(
                f"border-radius:12px;padding:14px 18px;margin-bottom:14px;"
                f"background:{'rgba(16,185,129,0.12)' if snd_on else 'rgba(239,68,68,0.08)'};"
                f"border:1px solid {'rgba(16,185,129,0.35)' if snd_on else 'rgba(239,68,68,0.25)'};"
                f"display:flex;align-items:center;justify-content:space-between;cursor:pointer"
            ).on("click", lambda: (
                _sound.update({"on": not _sound["on"]}),
                ui.run_javascript("if(window.NexusSound) NexusSound.toggle();"),
                save_prefs({"ui_sound": _sound["on"]}),   # prefs.json'a kaydet
                ui.notify("Ses açıldı 🔊" if _sound["on"] else "Ses kapatıldı 🔇", type="positive"),
                _sidebar.refresh()
            )):
                with ui.element("div"):
                    ui.html(
                        f'<div style="font-size:15px;font-weight:700;color:{"#10b981" if snd_on else "#ef4444"}">'
                        f'{"🔊 Ses Sistemi Açık" if snd_on else "🔇 Ses Sistemi Kapalı"}</div>'
                        f'<div style="font-size:11px;color:{C["MUTED"]};margin-top:3px">'
                        f'Web Audio API &mdash; harici dosya gerekmez</div>'
                    )
                ui.html(
                    f'<div style="width:52px;height:28px;border-radius:99px;'
                    f'background:{"#10b981" if snd_on else "rgba(255,255,255,0.1)"};'
                    f'position:relative;transition:all 0.3s;flex-shrink:0">'
                    f'<div style="position:absolute;top:4px;'
                    f'{"right:4px" if snd_on else "left:4px"};width:20px;height:20px;'
                    f'border-radius:50%;background:white;transition:all 0.3s;'
                    f'box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div></div>'
                )

            ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:{C["MUTED"]};margin-bottom:10px">SES EFEKTLERİNİ TEST ET</div>')
            _SOUNDS = [
                ("click",          "🖱️ Tık",           "Nav & buton tıklaması"),
                ("pageTransition", "🌊 Sayfa Geçişi",  "Swoosh efekti"),
                ("success",        "✅ Başarı",         "Tamamlandı melodisi"),
                ("error",          "❌ Hata",           "Hata uyarısı"),
                ("powerUp",        "⚡ Güç Açılışı",   "Çeviri başlat"),
                ("powerDown",      "🔻 Güç Kapanışı",  "Durdurma efekti"),
                ("notify",         "🔔 Bildirim",       "Yumuşak zil"),
                ("themeChange",    "🎨 Tema",           "Tema chime"),
                ("save",           "💾 Kaydet",         "Ayar kaydetme"),
                ("fetch",          "📡 Veri Çek",       "API çekme"),
            ]
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:8px"):
                for sid, slabel, sdesc in _SOUNDS:
                    with ui.element("div").style(
                        f"border-radius:10px;padding:10px 12px;"
                        f"background:{C['PANEL']};border:1px solid {C['BORDER']};"
                        f"display:flex;align-items:center;justify-content:space-between;gap:8px"
                    ):
                        with ui.element("div"):
                            ui.html(f'<div style="font-size:12px;font-weight:600;color:{C["TEXT"]}">{slabel}</div>')
                            ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">{sdesc}</div>')
                        def test_sound(s=sid):
                            ui.run_javascript(f"if(window.NexusSound) NexusSound.{s}();")
                        nbtn("▶", click=test_sound, variant="icon", size="sm")

        # ── Bilgi ──
        with ui.element("div").classes("card").style("padding:16px"):
            ui.html(f"""
            <div style="display:flex;align-items:start;gap:14px">
              <div style="font-size:28px">ℹ️</div>
              <div>
                <div style="font-size:13px;font-weight:700;color:{C["TEXT"]};margin-bottom:6px">
                  Web Audio API Ses Sistemi
                </div>
                <div style="font-size:12px;color:{C["SUB"]};line-height:1.7">
                  Tüm sesler <strong style="color:{C["CYAN"]}">Web Audio API</strong> ile üretilir — harici dosya gerekmez, tamamen offline çalışır.<br>
                  Tema &amp; arka plan tercihlerin <strong style="color:{C["PURPLE2"]}">user_preferences.json</strong> dosyasına kaydedilir.
                </div>
              </div>
            </div>""")

        # ── Özel Arka Plan ──────────────────────────────────────────────────────
        _build_bg_section()


def _build_bg_section():
    """Tema sayfasındaki özel arka plan resmi bölümü."""
    from ng_config import load_prefs, save_prefs

    prefs = load_prefs()
    bg_path    = prefs.get("bg_image_path", "")
    bg_enabled = prefs.get("bg_enabled",    False)
    bg_blur    = prefs.get("bg_blur",       0)
    bg_dark    = prefs.get("bg_dark",       0.55)

    with ui.element("div").classes("card card-purple"):
        ui.html(f'<div class="card-title">🖼️ ÖZEL ARKA PLAN RESMİ</div>')

        # Önizleme çubuğu
        preview_bar = ui.element("div").style(
            f"height:80px;border-radius:10px;margin-bottom:16px;"
            f"background:{'url(????) center/cover' if bg_path else 'color-mix(in srgb,var(--accent1) 5%,transparent)'};"
            f"border:1px solid {C['BORDER']};display:flex;align-items:center;justify-content:center;"
            f"overflow:hidden;position:relative;"
        )
        with preview_bar:
            ui.html(
                f'<div id="bg-preview-bar" style="position:absolute;inset:0;'
                f'background:{"center/cover no-repeat" if not bg_path else "transparent"};'
                f'display:flex;align-items:center;justify-content:center">'
                f'<span style="font-size:12px;color:{C["MUTED"]};z-index:1">'
                f'{"📷 " + bg_path.split(chr(92))[-1] if bg_path else "Henüz resim seçilmedi"}'
                f'</span></div>'
            )

        # Dosya yolu + butonlar
        with ui.element("div").style("display:flex;gap:8px;margin-bottom:14px;align-items:center"):
            path_inp = ui.input(
                placeholder="Resim yolu: C:\\Users\\...\\wallpaper.jpg"
            ).style(
                f"flex:1;background:{C['PANEL']};border:1px solid {C['BORDER']};"
                f"border-radius:9px;padding:9px 12px;color:{C['TEXT']};font-size:12px;"
                f"font-family:Consolas,monospace"
            )
            path_inp.value = bg_path

            def browse_file():
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    root = tk.Tk(); root.withdraw(); root.attributes("-topmost", True)
                    chosen = filedialog.askopenfilename(
                        title="Arka Plan Resmi Seç",
                        filetypes=[
                            ("Resim dosyaları", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
                            ("Tüm dosyalar",    "*.*"),
                        ]
                    )
                    root.destroy()
                    if chosen:
                        path_inp.value = chosen
                        ui.notify(f"Seçildi: {chosen.split('/')[-1]}", type="positive")
                except Exception as e:
                    ui.notify(f"Hata: {e}", type="negative")

            nbtn("📁 GÖZAT", click=browse_file, size="sm")

        # ── Toggle ──
        with ui.element("div").style(
            f"border-radius:10px;padding:10px 14px;margin-bottom:12px;"
            f"background:{'color-mix(in srgb,var(--accent1) 12%,transparent)' if bg_enabled else 'rgba(255,255,255,0.03)'};"
            f"border:1px solid {'color-mix(in srgb,var(--accent1) 35%,transparent)' if bg_enabled else C['BORDER']};"
            f"display:flex;align-items:center;justify-content:space-between"
        ) as toggle_row:
            ui.html(
                f'<div><div style="font-size:13px;font-weight:600;color:{C["TEXT"]}">Arka Planı Etkinleştir</div>'
                f'<div style="font-size:11px;color:{C["MUTED"]};margin-top:2px">Seçili resmi uygula</div></div>'
            )
            enabled_state = [bg_enabled]
            toggle_btn = ui.element("button").classes(f"toggle-switch {'on' if bg_enabled else ''}")

            def toggle_enabled(ts=toggle_btn, row=toggle_row, es=enabled_state):
                es[0] = not es[0]
                if es[0]:
                    ts.classes(add="on")
                    row.style(
                        f"border-radius:10px;padding:10px 14px;margin-bottom:12px;"
                        f"background:color-mix(in srgb,var(--accent1) 12%,transparent);border:1px solid color-mix(in srgb,var(--accent1) 35%,transparent);"
                        f"display:flex;align-items:center;justify-content:space-between"
                    )
                else:
                    ts.classes(remove="on")
                    row.style(
                        f"border-radius:10px;padding:10px 14px;margin-bottom:12px;"
                        f"background:rgba(255,255,255,0.03);border:1px solid {C['BORDER']};"
                        f"display:flex;align-items:center;justify-content:space-between"
                    )
            toggle_btn.on("click", toggle_enabled)

        # ── Blur Slider ──
        ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:{C["MUTED"]};margin-bottom:6px">BLUR MİKTARI <span id="blur-val-label">{int(bg_blur)}px</span></div>')
        blur_slider = ui.slider(min=0, max=30, step=1, value=int(bg_blur)).style(
            "width:100%;margin-bottom:14px"
        )
        blur_slider.on("update:model-value", lambda e: ui.run_javascript(
            "var v=" + str(e.args) + ";var layer=document.getElementById('bg-image-layer');"
            "if(layer&&layer.style.display!=='none'){layer.style.filter='blur('+v+'px)';layer.style.margin='-'+(v*2)+'px';}"
            "var lbl=document.getElementById('blur-val-label');if(lbl)lbl.textContent=v+'px';"
        ))

        # ── Karartma Slider ──
        dark_pct = int(bg_dark * 100)
        ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:{C["MUTED"]};margin-bottom:6px">KARARTMA <span id="dark-val-label">{dark_pct}%</span></div>')
        dark_slider = ui.slider(min=0, max=90, step=5, value=dark_pct).style(
            "width:100%;margin-bottom:18px"
        )
        dark_slider.on("update:model-value", lambda e: ui.run_javascript(
            "var v=" + str(e.args) + ";var overlay=document.getElementById('bg-dark-overlay');"
            "if(overlay)overlay.style.background='rgba(0,0,0,'+(v/100)+')'; "
            "var lbl=document.getElementById('dark-val-label');if(lbl)lbl.textContent=v+'%';"
        ))

        # ── Uygula / Temizle ──
        with ui.element("div").style("display:flex;gap:10px"):
            def apply_bg():
                path = path_inp.value.strip()
                if not path:
                    ui.notify("Önce bir resim seçin!", type="warning")
                    return
                if not os.path.exists(path):
                    ui.notify("Dosya bulunamadı!", type="negative")
                    return
                try:
                    blur_val = int(blur_slider.value)
                    dark_val = round(dark_slider.value / 100.0, 2)

                    # Prefs'e kaydet
                    p = load_prefs()
                    p["bg_image_path"] = path
                    p["bg_enabled"]    = True
                    p["bg_blur"]       = blur_val
                    p["bg_dark"]       = dark_val
                    save_prefs(p)
                    enabled_state[0] = True

                    # /api/bgimage endpoint'i üzerinden yükle (base64 yok!)
                    ui.run_javascript(
                        f"applyBgSettings('/api/bgimage?t='+Date.now(),"
                        f"{blur_val},{dark_val},true);"
                    )
                    fname = path.replace("\\", "/").split("/")[-1]
                    ui.notify(f"✅ Arka plan uygulandı: {fname}", type="positive")
                except Exception as e:
                    ui.notify(f"Hata: {e}", type="negative")

            def clear_bg():
                p = load_prefs()
                p["bg_image_path"] = ""
                p["bg_enabled"]    = False
                save_prefs(p)
                enabled_state[0] = False
                path_inp.value   = ""
                ui.run_javascript("applyBgSettings(null, 0, 0, false);")
                ui.notify("Arka plan kaldırıldı", type="info")

            nbtn("✅ UYGULA & KAYDET", click=apply_bg, full=True, style="flex:1")
            nbtn("🗑️ TEMİZLE",          click=clear_bg, variant="danger")



# ── SETTINGS sayfası ─────────────────────────────────────────────────────────
def build_settings():
    prefs = get_prefs()
    tcfg  = load_trans_cfg()

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">⚙️ Ayarlar</div>')
        ui.html('<div class="ph-sub">Tercihler, API, çeviri ve algılama motoru</div>')

    with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:0 28px 20px;overflow-y:auto;max-height:calc(100vh - 180px)"):

        # ── Sol Sütun ──────────────────────────────────────────
        with ui.element("div").style("display:flex;flex-direction:column;gap:16px"):

            # ── Pipeline & API Ayarları ──
            with ui.element("div").classes("card card-cyan"):
                from ng_config import load_prefs as _lp2, save_prefs as _sp8
                _adv = _lp2()
                ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">⚙️ PİPELİNE &amp; API AYARLARI</div>')

                with ui.element("div").style("display:flex;flex-wrap:wrap;gap:20px;align-items:flex-start;margin-bottom:14px"):

                    # font_size_mode
                    with ui.element("div").style("display:flex;flex-direction:column;gap:4px"):
                        _c_cyan = C["CYAN"]; _c_muted = C["MUTED"]
                        ui.html(f'<span style="font-size:10px;font-weight:700;color:{_c_cyan}">🔤 FONT BOYUTU MODU</span>')
                        _fsm_opts = ["normalize", "preserve", "custom"]
                        fsm_sel = ui.select(options=_fsm_opts, value=_adv.get("font_size_mode","normalize"), label="").style("min-width:150px")
                        _cfs_visible = [_adv.get("font_size_mode","normalize") == "custom"]
                        cfs_wrap = ui.element("div").style(f"display:{'flex' if _cfs_visible[0] else 'none'};flex-direction:column;gap:2px;margin-top:4px")
                        with cfs_wrap:
                            ui.html(f'<span style="font-size:10px;color:{_c_muted}">Özel boyut:</span>')
                            cfs_inp = ui.number(value=_adv.get("custom_font_size", 80), min=40, max=200, step=5).style("width:100px")
                            def on_cfs(e, w=cfs_wrap):
                                from ng_config import save_prefs as _s, load_prefs as _l
                                p = _l(); p["custom_font_size"] = int(e.args or cfs_inp.value); _s(p)
                            cfs_inp.on("change", on_cfs)
                        def on_fsm(e, cw=cfs_wrap, vis=_cfs_visible):
                            from ng_config import save_prefs as _s, load_prefs as _l
                            # e.args: str | dict | list — hepsini güvenle işle
                            _raw = e.args
                            if isinstance(_raw, str):
                                v = _raw
                            elif isinstance(_raw, dict):
                                v = _raw.get('value') or _raw.get('label') or fsm_sel.value
                            elif isinstance(_raw, list) and _raw:
                                v = _raw[0] if isinstance(_raw[0], str) else fsm_sel.value
                            else:
                                v = fsm_sel.value
                            if not v:
                                return
                            p = _l(); p["font_size_mode"] = v; _s(p)
                            is_custom = (v == "custom")
                            vis[0] = is_custom
                            cw.style(f"display:{'flex' if is_custom else 'none'};flex-direction:column;gap:2px;margin-top:4px")
                        fsm_sel.on("update:model-value", on_fsm)

                    # max_line_length
                    with ui.element("div").style("display:flex;flex-direction:column;gap:4px;min-width:180px"):
                        with ui.element("div").style("display:flex;justify-content:space-between;margin-bottom:2px"):
                            ui.html(f'<span style="font-size:10px;font-weight:700;color:{C["GREEN"]}">📏 MAX SATIR UZUNLUĞU</span>')
                            mll_lbl = ui.label(str(_adv.get("max_line_length", 75))).style(f"font-size:12px;font-weight:800;color:{C['GREEN']}")
                        mll_sl = ui.slider(min=40, max=150, step=5, value=_adv.get("max_line_length", 75)).style("width:180px")
                        def on_mll(e):
                            from ng_config import save_prefs as _s, load_prefs as _l
                            v = int(e.args); mll_lbl.set_text(str(v))
                            p = _l(); p["max_line_length"] = v; _s(p)
                        mll_sl.on("update:model-value", on_mll)

                # API Endpoint
                with ui.element("div").style("margin-bottom:12px"):
                    ui.html(f'<div style="font-size:10px;font-weight:700;color:{C["PURPLE"]};margin-bottom:6px">🌐 API ENDPOINT</div>')
                    api_inp = ui.input(
                        placeholder="https://openrouter.ai/api/v1/chat/completions",
                        value=_adv.get("api_endpoint", "https://openrouter.ai/api/v1/chat/completions")
                    ).style(
                        f"width:100%;background:{C['PANEL']};border:1px solid {C['BORDER']};"
                        "border-radius:9px;padding:8px 12px;color:#e2e8f0;"
                        "font-family:Consolas,monospace;font-size:11px"
                    )
                    def on_api_endpoint(e):
                        from ng_config import save_prefs as _s, load_prefs as _l
                        v = e.value or api_inp.value
                        if v: p = _l(); p["api_endpoint"] = v; _s(p)
                    api_inp.on("change", on_api_endpoint)

                # Kalite kontrol togglelar
                ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:{C["MUTED"]};margin-bottom:8px">✅ KALİTE KONTROLLERİ</div>')
                _qa_items = [
                    ("write_language_header",    "📝 Dil Başlığı (ASS)",    True),
                    ("check_timing_overlaps",    "⏱ Zamanlama Kontrolü",    True),
                    ("validate_cps_cpl",         "📊 CPS/CPL Doğrulama",    True),
                    ("collapse_animation_frames","🎬 Animasyon Birleştir",  True),
                ]
                _act2 = "display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:11px;font-weight:600;background:color-mix(in srgb,var(--accent1) 20%,transparent);border:1px solid color-mix(in srgb,var(--accent1) 55%,transparent);color:var(--accent1)"
                _ina2 = f"display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:11px;font-weight:600;background:{C['PANEL']};border:1px solid {C['BORDER']};color:{C['MUTED']}"
                with ui.element("div").style("display:flex;flex-wrap:wrap;gap:8px"):
                    for _qk, _ql, _qd in _qa_items:
                        _qv = [_adv.get(_qk, _qd)]
                        def _make_qa(k, v, lbl, a=_act2, i=_ina2):
                            _c_mu = C["MUTED"]
                            _da = '<span style="width:6px;height:6px;border-radius:50%;background:var(--accent1);flex-shrink:0"></span>'
                            _di = f'<span style="width:6px;height:6px;border-radius:50%;background:{_c_mu};flex-shrink:0"></span>'
                            _c = ui.html(f'<div style="{a if v[0] else i}">{_da if v[0] else _di}{lbl}</div>')
                            def _tog(c=_c, k=k, v=v, a=a, i=i, da=_da, di=_di, l=lbl):
                                from ng_config import save_prefs as _s, load_prefs as _l
                                v[0] = not v[0]; p = _l(); p[k] = v[0]; _s(p)
                                c.set_content(f'<div style="{a if v[0] else i}">{da if v[0] else di}{l}</div>')
                            _c.on("click", _tog)
                        _make_qa(_qk, _qv, _ql)

            # Çeviri toggleları
            with ui.element("div").classes("card"):
                ui.html('<div class="card-title">ÇEVİRİ AYARLARI</div>')
                toggles_left = [
                    ("use_fandom_glossary",   "Fandom Sözlük",       "Wiki'den çekilen terimleri kullan"),
                    ("generate_html_report",  "HTML Rapor",          "Çeviri sonrası kalite raporu üret"),
                    ("use_episode_context",   "Bölüm Bağlamı",       "Bölümler arası terminoloji tutarlılığı"),
                    ("force_translate",       "Zorla Çevir",         "Cache'i yoksay, her seferinde çevir"),
                    ("natural_dialogue",      "Doğal Diyalog",       "Daha akıcı Türkçe çeviri"),
                    ("only_english",          "Sadece İngilizce",    "Yalnızca İngilizce satırları çevir"),
                    ("nsfw_mode",             "NSFW Modu",           "Sansürsüz & jargon çevirisi"),
                    ("protect_positioning",   "Konum Koruması",      "ASS positioning tag'larını koru"),
                ]
                saved_toggles_left = {}
                for key, label, hint in toggles_left:
                    v = prefs.get(key, False)
                    saved_toggles_left[key] = _settings_toggle(key, label, hint, v, prefs)

            # Algılama motoru toggleları
            with ui.element("div").classes("card"):
                ui.html(f'<div class="card-title" style="color:{C["YELLOW"]}">🎛 ALGILAMA MOTORU</div>')

                # ── İçerik Türü Seçimi ──────────────────────────────────────────
                # Bu seçim: hangi API'ların sorgulanacağını ve hangi offline DB'lerin
                # indirileceğini belirler (anime→AniDB+manami, film→TMDB Film, dizi→TVMaze)
                with ui.element("div").style(
                    f"border-radius:10px;padding:12px 14px;margin-bottom:12px;"
                    f"background:color-mix(in srgb,{C['YELLOW']} 8%,transparent);"
                    f"border:1px solid color-mix(in srgb,{C['YELLOW']} 30%,transparent)"
                ):
                    ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:{C["YELLOW"]};margin-bottom:8px">🎌 İÇERİK TÜRÜ</div>')
                    _ct_opts = {
                        "auto":   "🤖 Otomatik (Önerilen)",
                        "anime":  "🎌 Anime",
                        "series": "📺 Batı Dizisi",
                        "movie":  "🎬 Film",
                    }
                    _cur_ct = prefs.get("content_type", "auto")
                    with ui.element("div").style("display:flex;gap:8px;flex-wrap:wrap"):
                        _ct_btns = {}
                        _act_ct  = f"padding:6px 14px;border-radius:99px;font-size:11px;font-weight:700;cursor:pointer;border:none;background:color-mix(in srgb,{C['YELLOW']} 80%,transparent);color:#000"
                        _ina_ct  = f"padding:6px 14px;border-radius:99px;font-size:11px;font-weight:600;cursor:pointer;border:1px solid {C['BORDER']};background:{C['PANEL']};color:{C['MUTED']}"
                        for _k, _lbl in _ct_opts.items():
                            _b = ui.html(f'<span style="{_act_ct if _k == _cur_ct else _ina_ct}">{_lbl}</span>')
                            _ct_btns[_k] = _b
                        def _on_ct(k, btns=_ct_btns, a=_act_ct, i=_ina_ct):
                            from ng_config import save_prefs as _sp, load_prefs as _lp
                            p = _lp(); p["content_type"] = k; _sp(p)
                            for _bk, _bv in btns.items():
                                _bv.set_content(f'<span style="{a if _bk==k else i}">{_ct_opts[_bk]}</span>')
                            ui.notify(f"İçerik türü: {_ct_opts[k]}", type="positive")
                        for _k in _ct_opts:
                            _ct_btns[_k].on("click", lambda e, k=_k: _on_ct(k))
                    ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:6px">🤖 Otomatik: Dosya adından AI ile tespit edilir &nbsp;|&nbsp; Manuel: Elle zorla seçim</div>')
                # ────────────────────────────────────────────────────────────────

                det_toggles = [
                    ("use_style_suffix_detection", "Stil Suffix Algılama", "EN/JP/KARA etiketlerine bak"),
                    ("romaji_block",               "Romaji Bloğu",         "Japonca hece satırlarını atla"),
                    ("use_song_lyrics_pass",        "Şarkı Sözü Geçişi",   "Ayrı şiirsel prompt kullan"),
                    ("use_karaoke_collapse",        "Karaoke Collapse",     "Hece grubunu tek satıra birleştir"),
                    ("force_no_style",              "Stili Yoksay",         "Sadece içerik analizi kullan"),
                    ("content_detect",              "İçerik Dedektörü",    "content_detector.py motorunu aktif et"),
                    ("cps_shorten",                 "CPS Kısaltma",         "Hızlı satırları AI ile kısalt"),
                ]
                for key, label, hint in det_toggles:
                    v = prefs.get(key, True)
                    _settings_toggle(key, label, hint, v, prefs)

        # ── Sağ Sütun ─────────────────────────────────────────
        with ui.element("div").style("display:flex;flex-direction:column;gap:16px"):

            # API Key yönetimi
            with ui.element("div").classes("card"):
                ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">🔑 API KEY YÖNETİMİ</div>')
                api_ok, api_ex = api_counts()
                with ui.element("div").style("display:flex;gap:10px;margin-bottom:14px"):
                    ui.html(f'<span class="chip chip-green">✅ {api_ok} Aktif</span>')
                    ui.html(f'<span class="chip chip-red">❌ {api_ex} Tükenmiş</span>')

                new_key = ui.input(placeholder="Yeni API anahtarı yapıştır...").style(
                    f"width:100%;background:{C['PANEL']};color:{C['TEXT']};"
                    f"border:1px solid {C['BORDER']};border-radius:9px;padding:8px 12px;margin-bottom:10px"
                )
                with ui.element("div").style("display:flex;gap:8px"):
                    def add_key():
                        k = new_key.value.strip()
                        if not k: ui.notify("Anahtar boş!", type="warning"); return
                        with open(API_FILE,"a",encoding="utf-8") as f:
                            f.write(f"\n{k}")
                        new_key.set_value("")
                        ui.notify("Anahtar eklendi ✅", type="positive")

                    def reset_exhausted():
                        try:
                            ex = []
                            if os.path.exists(EX_FILE):
                                with open(EX_FILE,"r",encoding="utf-8") as f:
                                    ex = [l.strip() for l in f if l.strip()]
                            if ex:
                                with open(API_FILE,"a",encoding="utf-8") as f:
                                    for k in ex: f.write(f"\n{k}")
                                open(EX_FILE,"w").close()
                                ui.notify(f"{len(ex)} anahtar geri yüklendi ✅", type="positive")
                            else:
                                ui.notify("Tükenmiş anahtar yok", type="info")
                        except Exception as e:
                            ui.notify(f"Hata: {e}", type="negative")

                    nbtn("➕ Ekle",                  click=add_key,         size="sm")
                    nbtn("🔄 Tükenmişleri Sıfırla", click=reset_exhausted, size="sm", variant="ghost")

            # Sistem prompt
            with ui.element("div").classes("card"):
                ui.html('<div class="card-title">💬 SİSTEM PROMPT</div>')
                prompt_ta = ui.textarea(
                    value=tcfg.get("system_prompt","")
                ).style(
                    f"width:100%;background:{C['PANEL']};color:{C['TEXT']};"
                    f"border:1px solid {C['BORDER']};border-radius:9px;padding:10px 12px;"
                    "font-size:12px;font-family:'JetBrains Mono',monospace;min-height:120px"
                )

            # Çeviri parametreleri
            with ui.element("div").classes("card"):
                ui.html('<div class="card-title">🔧 ÇEVİRİ PARAMETRELERİ</div>')
                with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px"):
                    delay_inp  = _num_field("API Gecikmesi (sn)", tcfg.get("delay_between_calls",0))
                    retries_inp= _num_field("Max Tekrar",         tcfg.get("max_retries",6))
                    batch_inp  = _num_field("Batch Boyutu",       tcfg.get("batch_size",10))
                    linelen_inp= _num_field("Max Satır Uzunluğu", prefs.get("max_line_length",75))

            # Kaydet butonu
            def save_all():
                from ng_config import load_prefs as _lp_sa, save_prefs as _sp_sa
                _p = _lp_sa()  # taze oku — diğer widget'ların anlık kayıtlarıyla çakışma olmasın
                # Pipeline ayarları
                _fsm = fsm_sel.value
                if _fsm:
                    _p["font_size_mode"] = _fsm
                if _fsm == "custom" and cfs_inp.value:
                    try:
                        _p["custom_font_size"] = int(cfs_inp.value)
                    except Exception:
                        pass
                _p["max_line_length"] = int(linelen_inp.value or 75)
                _api_ep = api_inp.value.strip()
                if _api_ep:
                    _p["api_endpoint"] = _api_ep
                _sp_sa(_p)
                # Çeviri cfg
                tcfg["delay_between_calls"] = float(delay_inp.value or 0)
                tcfg["max_retries"]         = int(retries_inp.value or 6)
                tcfg["batch_size"]          = int(batch_inp.value or 10)
                tcfg["system_prompt"]       = prompt_ta.value
                save_trans_cfg(tcfg)
                ui.notify("Ayarlar kaydedildi ✅", type="positive")
                try:
                    ui.run_javascript("if(window.NexusSound) NexusSound.save();")
                except Exception:
                    pass

            nbtn("💾  Tüm Ayarları Kaydet", click=save_all, size="lg", full=True)


# ── Yardımcı fonksiyonlar ─────────────────────────────────────────────────────
def _qa_stat(icon, label, value, color):
    with ui.element("div").style(
        f"background:{C['CARD']};border:1px solid {C['BORDER']};border-radius:12px;"
        "padding:16px;text-align:center"
    ):
        ui.html(f'<div style="font-size:24px">{icon}</div>')
        ui.html(f'<div style="font-size:20px;font-weight:800;color:{color};margin-top:4px">{value}</div>')
        ui.html(f'<div style="font-size:11px;color:{C["SUB"]};margin-top:2px">{label}</div>')



def _vfx_toggle(label, hint, initial, js_code):
    """Görsel efekt toggle — yerel state, JS ile CSS değişkeni toggle eder."""
    is_on = [initial]
    with ui.element("div").style(
        f"border-radius:10px;padding:10px 14px;"
        f"background:{C['PANEL']};border:1px solid {C['BORDER']};"
        f"display:flex;align-items:center;gap:10px;cursor:pointer"
    ):
        with ui.element("div").style("flex:1"):
            ui.html(f'<div style="font-size:12px;font-weight:600;color:{C["TEXT"]}">{label}</div>')
            ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">{hint}</div>')
        btn = ui.element("button").classes(f"toggle-switch {'on' if initial else ''}")

def _settings_toggle(key: str, label: str, hint: str, initial: bool, prefs: dict):
    """Settings sayfası toggle satırı — prefs'e anında kaydeder."""
    is_on = [bool(initial)]

    _act_s = "display:inline-flex;align-items:center;gap:6px;padding:5px 14px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:11px;font-weight:600;background:color-mix(in srgb,var(--accent1) 20%,transparent);border:1px solid color-mix(in srgb,var(--accent1) 55%,transparent);color:var(--accent1)"
    _ina_s = f"display:inline-flex;align-items:center;gap:6px;padding:5px 14px;border-radius:99px;cursor:pointer;transition:all 0.2s;font-size:11px;font-weight:600;background:{C['PANEL']};border:1px solid {C['BORDER']};color:{C['MUTED']}"
    _dot_a = '<span style="width:6px;height:6px;border-radius:50%;background:var(--accent1);flex-shrink:0"></span>'
    _dot_i = f'<span style="width:6px;height:6px;border-radius:50%;background:{C["MUTED"]};flex-shrink:0"></span>'

    with ui.element("div").style(
        f"border-radius:10px;padding:10px 14px;margin-bottom:8px;"
        f"background:{C['PANEL']};border:1px solid {C['BORDER']};"
        "display:flex;align-items:center;justify-content:space-between;gap:10px"
    ):
        with ui.element("div").style("flex:1"):
            ui.html(f'<div style="font-size:12px;font-weight:600;color:{C["TEXT"]}">{label}</div>')
            if hint:
                ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">{hint}</div>')

        chip = ui.html(
            f'<div style="{_act_s if is_on[0] else _ina_s}">'
            f'{_dot_a if is_on[0] else _dot_i}'
            f'{"Açık" if is_on[0] else "Kapalı"}</div>'
        )

        def _toggle(c=chip, k=key, v=is_on, a=_act_s, i=_ina_s, da=_dot_a, di=_dot_i):
            from ng_config import save_prefs as _s, load_prefs as _l
            v[0] = not v[0]
            p = _l(); p[k] = v[0]; _s(p)
            c.set_content(
                f'<div style="{a if v[0] else i}">'
                f'{da if v[0] else di}'
                f'{"Açık" if v[0] else "Kapalı"}</div>'
            )
        chip.on("click", _toggle)
    return chip


def _num_field(label: str, value):
    """Settings sayfası sayı alanı."""
    with ui.element("div").style("display:flex;flex-direction:column;gap:4px"):
        ui.html(f'<div style="font-size:10px;font-weight:700;color:{C["MUTED"]}">{label}</div>')
        inp = ui.number(value=value).style(
            f"width:100%;background:{C['PANEL']};color:{C['TEXT']};"
            f"border:1px solid {C['BORDER']};border-radius:9px;padding:8px 12px"
        )
    return inp


def build_about():

    import sys, nicegui as _ng

    def _sec_title(icon, title, color=None):
        col = color or C["CYAN"]
        ui.html(
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;'
            f'padding-bottom:10px;border-bottom:1px solid {C["BORDER"]}">'
            f'<span style="font-size:22px">{icon}</span>'
            f'<div style="font-size:13px;font-weight:800;letter-spacing:1px;color:{col}">{title}</div>'
            f'</div>'
        )

    def _item(num, baslik, aciklama, color=None):
        col = color or C["CYAN"]
        ui.html(
            f'<div style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid {C["BORDER"]}22">'
            f'<div style="min-width:28px;height:28px;border-radius:50%;'
            f'background:color-mix(in srgb,{col} 20%,transparent);'
            f'border:1px solid {col};display:flex;align-items:center;justify-content:center;'
            f'font-size:11px;font-weight:800;color:{col};flex-shrink:0">{num}</div>'
            f'<div><div style="font-size:13px;font-weight:700;color:{C["TEXT"]};margin-bottom:3px">{baslik}</div>'
            f'<div style="font-size:11px;color:{C["SUB"]};line-height:1.7">{aciklama}</div></div>'
            f'</div>'
        )

    def _badge(icon, text, col="#e2e8f0"):
        return (f'<span style="display:inline-flex;align-items:center;gap:5px;padding:5px 14px;'
                f'border-radius:99px;background:rgba(255,255,255,0.07);'
                f'font-size:11px;font-weight:700;color:{col}">{icon} {text}</span>')

    def _info_row(icon, label, value):
        ui.html(
            f'<div style="display:flex;gap:10px;padding:7px 0;'
            f'border-bottom:1px solid {C["BORDER"]}22;align-items:flex-start">'
            f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{icon}</span>'
            f'<div>'
            f'<span style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{label}: </span>'
            f'<span style="font-size:11px;color:{C["MUTED"]}">{value}</span>'
            f'</div></div>'
        )

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">ℹ️ Uygulama Hakkında</div>')
        ui.html('<div class="ph-sub">Nexus AI Altyazı Çeviri Paneli — Tam Kullanım Kılavuzu &amp; Özellik Rehberi</div>')

    with ui.element("div").style("padding:0 28px 28px;display:flex;flex-direction:column;gap:20px"):

        # ── Hero Banner ──────────────────────────────────────────────────────────
        ui.html(f"""
        <div style="border-radius:18px;padding:32px 36px;
             background:linear-gradient(135deg,
               color-mix(in srgb,var(--accent1) 22%,transparent),
               color-mix(in srgb,var(--accent2) 14%,transparent));
             border:1px solid color-mix(in srgb,var(--accent1) 38%,transparent)">
          <div style="font-size:11px;font-weight:800;letter-spacing:3px;color:var(--accent2);margin-bottom:8px">
            NEXUS PRO &middot; AI SUBTITLE ENGINE &middot; v3.0
          </div>
          <div style="font-size:26px;font-weight:900;margin-bottom:10px;
               background:linear-gradient(135deg,var(--accent1),var(--accent2));
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
            Altyazı Çeviri Paneli
          </div>
          <div style="font-size:13px;color:{C['SUB']};line-height:1.9;max-width:760px">
            Anime, dizi ve film altyazılarını <strong style="color:var(--accent1)">yapay zeka</strong> kullanarak
            otomatik olarak Türkçeye çeviren tam donanımlı bir masaüstü panelidir.<br>
            <strong style="color:var(--accent2)">OpenRouter API</strong> üzerinden GPT-4o, Claude, Gemini gibi büyük dil modellerine bağlanır.
            <strong style="color:var(--accent1)">ASS / SRT</strong> formatlarını destekler,
            tag'ları korur, kalite raporu üretir ve sözlük sistemi ile tutarlı çeviri sağlar.
          </div>
          <div style="margin-top:18px;display:flex;flex-wrap:wrap;gap:8px">
            {_badge("🐍", f"Python {sys.version[:6]}")}
            {_badge("🖥️", f"NiceGUI {_ng.__version__}")}
            {_badge("🌐", "OpenRouter API")}
            {_badge("📄", "ASS / SRT / SSA")}
            {_badge("🔒", "Çevrimdışı Arayüz")}
            {_badge("⚡", "FastAPI Backend")}
            {_badge("🎌", "Anime Odaklı")}
            {_badge("🤖", "Çoklu LLM Desteği")}
          </div>
        </div>
        """)

        # ── SATIR 1: Temel Özellikler + Çeviri Pipeline ──────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎯", "UYGULAMA NE İŞE YARAR?", C["CYAN"])
                _item(1, "Otomatik Altyazı Çevirisi",
                      "ASS veya SRT formatındaki altyazı dosyasını seçersiniz; uygulama her satırı "
                      "yapay zekaya gönderir, Türkçe çevirisini dosyaya yazar. Elle hiçbir şey yapmanıza gerek kalmaz.", C["CYAN"])
                _item(2, "Toplu (Batch) İşlem",
                      "Tek seferde birden fazla altyazı dosyasını işleyebilirsiniz. Klasör seçin, "
                      "uygulama sırayla ve hata toleranslı biçimde hepsini çevirir.", C["CYAN"])
                _item(3, "ASS Tag Koruması",
                      "Renk, konum, efekt, italik, kalın gibi tüm ASS biçim kodları çeviri sırasında "
                      "bozulmaz — parser bunları izole eder, AI sadece metni görür.", C["CYAN"])
                _item(4, "Kalite Kontrol Raporu (QA)",
                      "Çeviri bittikten sonra otomatik HTML raporu oluşturulur: zamanlama çakışmaları, "
                      "çok hızlı/yavaş satırlar (CPS), çok uzun satırlar (CPL) ve tag hataları raporlanır.", C["CYAN"])
                _item(5, "Akıllı Cache Sistemi",
                      "Daha önce çevrilen satırlar yerel olarak saklanır. Aynı dosyayı tekrar işlediğinizde "
                      "cache'deki satırlar için API çağrısı yapılmaz — hem hızlı hem ekonomik.", C["CYAN"])
                _item(6, "Çoklu API Anahtarı Rotasyonu",
                      "Birden fazla OpenRouter API anahtarı tanımlayabilirsiniz. Bir anahtar kotasını doldurunca "
                      "sistem otomatik olarak sıradakine geçer, çeviri durmadan devam eder.", C["CYAN"])
                _item(7, "Çoklu Çıkış Formatı",
                      "Çıktı formatını ASS, SRT, VTT veya ALL (hepsi aynı anda) olarak ayarlayabilirsiniz. "
                      "Orijinal ASS yapısı ve stil bilgisi korunur.", C["CYAN"])
                _item(8, "İçerik Tür Tespiti",
                      "Dosya adından Anime / Batı Dizisi / Film türünü otomatik algılar. "
                      "Buna göre hangi API'ların sorgulanacağını ve hangi offline veritabanlarının kullanılacağını belirler.", C["CYAN"])

            with ui.element("div").classes("card"):
                _sec_title("⚙️", "ÇEVİRİ PİPELİNE — ADIM ADIM", C["PURPLE"])
                _item(1, "Dosya Ayrıştırma (Parser)",
                      "ASS/SRT dosyası satır satır okunur. Her satırdaki ASS tag'ları çıkarılır, "
                      "saf metin ayrıştırılır. Romaji, karaoke ve stil suffix etiketleri bu aşamada tespit edilir.", C["PURPLE"])
                _item(2, "İçerik Dedektörü (content_detector)",
                      "Her satır; şarkı sözü, karaoke, yalnızca İngilizce, romaji ya da çeviri gerektirmeyen "
                      "içerik açısından sınıflandırılır. Gereksiz API çağrılarını önler.", C["PURPLE"])
                _item(3, "Fandom Sözlük Entegrasyonu",
                      "Anime/dizi adına göre Fandom Wiki'den otomatik olarak özel isimler, yer adları ve "
                      "organizasyon isimleri çekilir. Bu terimler termbase'e eklenir.", C["PURPLE"])
                _item(4, "Batch Gruplama",
                      "Satırlar ayarlanabilir batch boyutuna (varsayılan 10) ve max byte limitine (2000) "
                      "göre gruplara ayrılır. Her grup tek API çağrısıyla gönderilir.", C["PURPLE"])
                _item(5, "AI Çeviri + Termbase Doğrulaması",
                      "Sistem prompt + glossary + bölüm bağlamı ile LLM'e gönderilir. Cevap gelince "
                      "termbase'deki kritik terimler doğrulanır. Hata varsa API key rotation ile retry yapılır.", C["PURPLE"])
                _item(6, "Max Satır Uzunluğu & CPS Kısaltma",
                      "Çeviri 75 karakteri (ayarlanabilir) aşarsa satır otomatik bölünür ya da AI ile "
                      "kısaltılır. Çok hızlı satırlar (yüksek CPS) ayrıca işaretlenir.", C["PURPLE"])
                _item(7, "Tag Yeniden Birleştirme",
                      "Çevrilen metin orijinal ASS tag'larıyla yeniden birleştirilir. "
                      "Konum, renk ve efekt bilgileri eksiksiz korunur.", C["PURPLE"])
                _item(8, "Dosyaya Yazma & Rapor",
                      "Çevrilmiş satırlar orijinal dosya formatında kaydedilir. Ardından HTML kalite "
                      "raporu üretilir ve merkezi reports/ klasörüne kopyalanır.", C["PURPLE"])

        # ── SATIR 2: Sayfalar + Kritik Ayarlar ───────────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🗂️", "SAYFALAR VE BÖLÜMLERİ", C["CYAN"])
                _item(1, "🏠 Dashboard (Ana Sayfa)",
                      "Genel durum özeti, aktif API anahtarı sayısı, toplam terim sayısı ve son işlem "
                      "bilgileri burada görünür. Hızlı erişim butonları da buradadır.", C["CYAN"])
                _item(2, "🔄 Translate (Çeviri Sayfası)",
                      "Asıl iş burada yapılır. Altyazı dosyasını sürükle-bırak veya seçiciyle eklersiniz. "
                      "Model, batch boyutu, gecikme ayarları yapılır, 'Çeviriyi Başlat' ile işlem başlar. "
                      "İlerleme çubuğu ve log ekranı canlı güncellenir.", C["CYAN"])
                _item(3, "📚 Glossary (Sözlük / Termbase)",
                      "Seri adına göre kategorize edilmiş özel isimler, yer adları, organizasyon ve "
                      "teknik terimler buraya eklenir. Alfabetik, zamana göre veya terim sayısına göre "
                      "sıralama ve çift filtreli arama (Seri Adı + Wiki Slug) mevcuttur.", C["CYAN"])
                _item(4, "✅ QA Report (Raporlar)",
                      "Tüm HTML kalite raporlarını listeleyen sayfa. Merkezi reports/ klasörünü tarar. "
                      "QA aracını bu sayfadan da doğrudan çalıştırabilirsiniz.", C["CYAN"])
                _item(5, "🎨 Tema & Ses",
                      "9 hazır tema arasında geçiş yapılır. Ses efektleri, arka plan resmi, blur ve "
                      "karartma değerleri buradan ayarlanır.", C["CYAN"])
                _item(6, "⚙️ Settings (Ayarlar)",
                      "API anahtarları, çeviri parametreleri (batch boyutu, gecikme, max retry), sistem promptu, "
                      "font boyutu modu, max satır uzunluğu, pipeline toggle'ları ve algılama motoru "
                      "ayarları bu sayfada yönetilir.", C["CYAN"])

            with ui.element("div").classes("card"):
                _sec_title("🔧", "KRİTİK AYARLAR NE ANLAMA GELİR?", C["YELLOW"])
                _item(1, "Font Boyutu Modu",
                      "<b>normalize:</b> Tüm satırlarda aynı boyut kullanılır. "
                      "<b>preserve:</b> Orijinal dosyadaki boyutlar korunur. "
                      "<b>custom:</b> Siz belirlediğiniz sabit bir boyut uygulanır.", C["YELLOW"])
                _item(2, "Max Satır Uzunluğu",
                      "Bir altyazı satırının en fazla kaç karakter olacağını belirler (varsayılan 75). "
                      "Bu sayıyı aşan çeviriler otomatik bölünür ya da AI ile kısaltılır.", C["YELLOW"])
                _item(3, "API Endpoint",
                      "Hangi yapay zeka servisine bağlanılacağını gösterir. Varsayılan OpenRouter'dır "
                      "ancak uyumlu başka bir servis (Ollama, LiteLLM vb.) de kullanılabilir.", C["YELLOW"])
                _item(4, "Doğal Diyalog Modu",
                      "Aktif olduğunda yapay zekaya 'doğal, akıcı, ağdalı olmayan Türkçe kullan' talimatı "
                      "eklenir. Resmi çeviri yerine günlük konuşma diline yakın çeviriler üretilir.", C["YELLOW"])
                _item(5, "Zorla Çevir (Force Translate)",
                      "Normalde daha önce çevrilmiş satırlar cache'den gelir. Bu seçenek aktifse cache "
                      "yoksayılır ve her satır yeniden yapay zekaya gönderilir.", C["YELLOW"])
                _item(6, "NSFW Modu",
                      "Bazı modeller varsayılan olarak küfür veya argo içerikleri sansürler. "
                      "Bu mod aktifken sansürsüz, jargon dahil tam çeviri yapılır.", C["YELLOW"])
                _item(7, "Bölüm Bağlamı (Episode Context)",
                      "Bir serinin birden fazla bölümünü çevirirken önceki bölümlerdeki terimler hatırlanır. "
                      "Karakter isimlerinde ve teknik terimlerde çapraz bölüm tutarlılığı sağlanır.", C["YELLOW"])
                _item(8, "Karaoke & Şarkı Sözü Desteği",
                      "Anime opening/ending şarkılarındaki karaoke satırlarını tespit eder. "
                      "Bunları ayrı bir şiirsel prompt ile çevirir, normal diyalog ile karıştırmaz.", C["YELLOW"])

        # ── SATIR 3: Algılama Motoru + Pro İpuçları ──────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎛️", "ALGILAMA MOTORU TOGGLE'LARI", C["GREEN"])
                _item(1, "Stil Suffix Algılama",
                      "Dosya adındaki EN / JP / KARA gibi suffix'leri tanır. Örneğin dosya adı "
                      "'[EN]' içeriyorsa yalnızca İngilizce satırlar hedef alınır.", C["GREEN"])
                _item(2, "Romaji Bloğu",
                      "Japonca hece içeren satırları tespit eder ve çeviri dışında tutar. "
                      "Şarkı romanizasyonlarının bozulmasını önler.", C["GREEN"])
                _item(3, "Şarkı Sözü Geçişi",
                      "Şarkı sözü olarak algılanan satırlar ayrı bir şiirsel prompt ile işlenir. "
                      "Anlam kaybı olmadan daha lirik bir çeviri üretir.", C["GREEN"])
                _item(4, "Karaoke Collapse",
                      "Hece hece parçalanmış karaoke satırlarını tek bir tam satıra birleştirir, "
                      "ardından çevirir.", C["GREEN"])
                _item(5, "Stili Yoksay (force_no_style)",
                      "Stil suffix analizi devre dışı bırakılır. Tüm satırlar yalnızca içerik "
                      "analizi bazında işlenir.", C["GREEN"])
                _item(6, "İçerik Dedektörü (content_detect)",
                      "Her satır otomatik olarak kategori sınıflandırmasından geçer: "
                      "diyalog / şarkı / romaji / boş / sistem.", C["GREEN"])
                _item(7, "CPS Kısaltma",
                      "Saniyede karakter oranı çok yüksek olan satırları AI ile otomatik kısaltır. "
                      "İzleyicinin okuma hızına uygun altyazı üretir.", C["GREEN"])
                _item(8, "Konum Koruması",
                      "ASS dosyasındaki konum tag'larını çeviri sonrasında da korur. "
                      "Üst yazı / yan yazı gibi özel konumlar bozulmaz.", C["GREEN"])

            with ui.element("div").classes("card"):
                _sec_title("💡", "PRO İPUÇLARI", C["PINK"])
                ipuclari = [
                    ("Sözlüğü Önceden Doldurun",
                     "Çeviri başlatmadan önce Glossary sayfasına karakter isimlerini ekleyin. "
                     "Böylece isimler yanlış çevrilmez ve termbase doğrulaması devreye girer."),
                    ("Batch Boyutunu Küçültün",
                     "API hata veriyorsa Settings'te Batch Boyutu'nu küçültün (örn. 5). "
                     "Daha küçük gruplar daha az hata verir."),
                    ("Gecikme Ekleyin",
                     "Çok sayıda anahtar kullanıyorsanız 'API Gecikmesi'ni 0.5–1 saniyeye ayarlayın. "
                     "Rate limit (429) hatalarını önemli ölçüde azaltır."),
                    ("Tükenmiş Anahtarları Sıfırlayın",
                     "Settings → API Key Yönetimi → 'Tükenmişleri Sıfırla' butonu ile "
                     "tükenmiş anahtarları tekrar aktif listesine taşıyabilirsiniz."),
                    ("Fandom Wiki Bağlayın",
                     "Glossary sayfasında seri adını ve wiki slug'ını girerek Fandom'dan "
                     "otomatik terim çekin. Anime isimlerinde yanlış çeviriyi ortadan kaldırır."),
                    ("QA Raporunu İnceleyin",
                     "Çeviri bittikten sonra QA Report sayfasını açın. Kırmızı = hata, "
                     "sarı = uyarı, yeşil = başarılı. Zamanlama sorunlarını buradan görürsünüz."),
                    ("Sidebar'ı Daraltın",
                     "Ctrl+B kısayolu veya yan ok butonu ile sidebar'ı küçük ikon moduna alın, "
                     "çeviri log ekranı için daha fazla alan kazanın."),
                    ("Sistem Promptunu Özelleştirin",
                     "Settings → Sistem Prompt alanını düzenleyerek yapay zekanın çeviri tarzını "
                     "tamamen kendi isteğinize göre yönlendirin."),
                ]
                for idx, (baslik, acik) in enumerate(ipuclari, 1):
                    ui.html(
                        f'<div style="display:flex;gap:10px;padding:8px 0;'
                        f'border-bottom:1px solid {C["BORDER"]}22">'
                        f'<div style="min-width:22px;height:22px;border-radius:6px;'
                        f'background:color-mix(in srgb,{C["PINK"]} 20%,transparent);'
                        f'border:1px solid {C["PINK"]};display:flex;align-items:center;'
                        f'justify-content:center;font-size:10px;font-weight:800;'
                        f'color:{C["PINK"]};flex-shrink:0">{idx}</div>'
                        f'<div><div style="font-size:12px;font-weight:700;color:{C["TEXT"]};'
                        f'margin-bottom:2px">{baslik}</div>'
                        f'<div style="font-size:10px;color:{C["MUTED"]};line-height:1.6">{acik}</div>'
                        f'</div></div>'
                    )

        # ── SATIR 4: Temalar + Teknik Bilgiler ───────────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎨", "9 HAZIR TEMA", C["PURPLE"])
                temas = [
                    ("⬡", "Nexus",      "Cyberpunk · Mor & Cyan",    "#7c3aed"),
                    ("✿", "Sakura",     "Anime · Pembe & Rose",       "#c026d3"),
                    ("⊡", "Cyber",      "Matrix · Yeşil & Sarı",      "#00ff87"),
                    ("◈", "Midnight",   "Koyu · Mavi & İndigo",       "#3b82f6"),
                    ("◆", "Ember",      "Ateş · Turuncu & Kırmızı",  "#f97316"),
                    ("❄", "Arctic",     "Buz · Beyaz & Gümüş",       "#94a3b8"),
                    ("⚡", "Neon Tokyo", "Vaporwave · Pembe & Cyan",   "#ff0080"),
                    ("👑", "Gold Rush",  "Premium · Altın & Amber",    "#ffd700"),
                    ("🌑", "Blood Moon", "Gothic · Kızıl & Karanlık",  "#dc143c"),
                ]
                with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px"):
                    for icon, name, sub, col in temas:
                        ui.html(
                            f'<div style="border-radius:10px;padding:10px 12px;'
                            f'background:color-mix(in srgb,{col} 10%,transparent);'
                            f'border:1px solid color-mix(in srgb,{col} 35%,transparent)">'
                            f'<div style="font-size:18px;margin-bottom:4px">{icon}</div>'
                            f'<div style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{name}</div>'
                            f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">{sub}</div>'
                            f'</div>'
                        )

            with ui.element("div").classes("card"):
                _sec_title("📋", "TEKNİK BİLGİLER", C["CYAN"])
                teknikler = [
                    ("📄", "Giriş Formatları",        "ASS, SSA, SRT"),
                    ("📤", "Çıkış Formatları",         "ASS, SRT, VTT, ALL"),
                    ("🤖", "Desteklenen AI Modelleri", "GPT-4o, Claude 3.5, Gemini 2.0, DeepSeek, LLaMA, Phi-4 ve daha fazlası"),
                    ("🔑", "API Sistemi",              "Çoklu anahtar rotasyonu — tükenmiş anahtarlar exhausted_api_keys.txt'e taşınır"),
                    ("💾", "Ayar Dosyaları",           "user_preferences.json + translator_config.json"),
                    ("📊", "Kalite Raporu",            "HTML format — CPS/CPL/zamanlama/tag hata gösterimi"),
                    ("🌐", "Çevrimdışı Bileşenler",   "Ses sistemi (Web Audio API), temalar — internet gerektirmez"),
                    ("🖥️", "Arayüz Teknolojisi",       f"NiceGUI {_ng.__version__} (Python) tabanlı yerel pencere"),
                    ("⌨️", "Sidebar Kısayolu",         "Ctrl+B ile sidebar'ı daraltıp genişletebilirsiniz"),
                    ("🗄️", "Sözlük Formatı",           "series_glossary.json — seri bazlı, kategorize terim yönetimi"),
                    ("🌍", "Fandom Entegrasyonu",      "fandom_glossary.py — Wiki'den otomatik terim çekme"),
                    ("⚡", "Batch İşlem",               "Ayarlanabilir grup boyutu + max byte limiti ile toplu çeviri"),
                ]
                for icon, baslik, acik in teknikler:
                    ui.html(
                        f'<div style="display:flex;gap:10px;padding:7px 0;'
                        f'border-bottom:1px solid {C["BORDER"]}22;align-items:flex-start">'
                        f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{icon}</span>'
                        f'<div>'
                        f'<span style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{baslik}: </span>'
                        f'<span style="font-size:11px;color:{C["MUTED"]}">{acik}</span>'
                        f'</div></div>'
                    )

        # ── Footer ────────────────────────────────────────────────────────────────
        ui.html(f"""
        <div style="border-radius:14px;padding:22px 28px;text-align:center;
             background:color-mix(in srgb,var(--accent1) 8%,transparent);
             border:1px solid color-mix(in srgb,var(--accent1) 25%,transparent)">
          <div style="font-size:24px;margin-bottom:8px">🎌</div>
          <div style="font-size:13px;font-weight:800;color:{C['TEXT']};margin-bottom:6px">
            Nexus AI Altyazı Çeviri Paneli &mdash; v3.0
          </div>
          <div style="font-size:11px;color:{C['MUTED']};line-height:1.9">
            Yapay zeka ile güçlendirilmiş, tamamen Türkçe arayüzlü altyazı çeviri sistemi.<br>
            ASS / SRT / VTT &middot; OpenRouter API &middot; Çoklu LLM &middot; Çevrimdışı Arayüz
          </div>
          <div style="margin-top:14px;display:flex;justify-content:center;flex-wrap:wrap;gap:8px">
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🐍 Python {sys.version[:6]}</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🖼️ NiceGUI {_ng.__version__}</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">⚡ FastAPI</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🌐 OpenRouter</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🔒 Offline Arayüz</span>
          </div>
        </div>
        """)

# ── RAPORLAR sayfası ──────────────────────────────────────────────────────────
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
def build_datasources():
    """Dis veri kaynaklari (Jikan/AniList/TMDB vb.) acma-kapama yonetimi."""
    from ng_config import TRANS_CFG, load_trans_cfg, save_trans_cfg

    cfg = load_trans_cfg()
    ms  = cfg.get("media_sources", {
        "jikan": True, "anilist": True, "kitsu": True,
        "tvmaze": True, "tmdb": True, "ai_fill_gaps": True, "ai_fallback": True
    })

    def _save_cfg():
        cfg["media_sources"] = ms
        save_trans_cfg(cfg)
        ui.notify("Kaydedildi ✔", type="positive", timeout=1500)

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🌐 Veri Kaynakları</div>')
        ui.html('<div class="ph-sub">Medya meta-veri API\'leri · Açık kaynaklar · Bağlantı ayarları</div>')

    with ui.element("div").style("padding:0 28px 28px;display:flex;flex-direction:column;gap:18px"):

        # ── 1. Medya Kaynakları Toggle'ları ──────────────────────────────────
        SOURCES = [
            ("jikan",         "🎌 Jikan (MyAnimeList)",   "MAL'ın açık API'si — anime bilgisi, bölüm isimleri",          C["CYAN"]),
            ("anilist",       "📊 AniList",               "Anime/manga veritabanı — popüler, hızlı GraphQL API",         C["PURPLE"]),
            ("kitsu",         "🐱 Kitsu",                 "Anime/manga meta-verisi — başlık, açıklama, tür",             C["GREEN"]),
            ("tvmaze",        "📺 TVMaze",                "Dizi/TV bölüm bilgisi — özellikle yabancı diziler için",      C["YELLOW"]),
            ("tmdb",          "🎬 TMDB",                  "The Movie Database — film ve dizi meta-verisi (API key ister)",C["RED"]),
            ("ai_fill_gaps",  "🤖 AI Gap Doldur",         "Eksik meta-veriyi AI ile tamamla (ek token harcar)",          C["CYAN"]),
            ("ai_fallback",   "🔄 AI Fallback",           "Tüm kaynaklar boş kalırsa AI'dan al — son çare modu",         C["PURPLE"]),
        ]

        with ui.element("div").classes("card").style("padding:18px 22px"):
            ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">📡 MEDİA META-VERİ API\'LERİ</div>')
            ui.html(f'<div style="font-size:11px;color:{C["MUTED"]};margin-bottom:16px">'
                    f'Çeviri başlamadan önce medya başlığı, tür, bölüm ismi vb. bilgiler bu kaynaklardan çekilir.</div>')

            for key, label, hint, col in SOURCES:
                _val = [bool(ms.get(key, True))]

                with ui.element("div").style(
                    f"display:flex;align-items:center;justify-content:space-between;"
                    f"padding:10px 14px;border-radius:10px;margin-bottom:8px;"
                    f"background:{C['PANEL']};border:1px solid {C['BORDER']};transition:all 0.2s"
                ) as row:
                    # Sol: ikon + açıklama
                    with ui.element("div").style("flex:1;min-width:0"):
                        ui.html(f'<div style="font-size:13px;font-weight:700;color:{col}">{label}</div>')
                        ui.html(f'<div style="font-size:11px;color:{C["MUTED"]};margin-top:2px">{hint}</div>')

                    # Sağ: toggle switch
                    _on_s  = (f"display:inline-flex;align-items:center;gap:6px;padding:5px 14px;"
                              f"border-radius:99px;cursor:pointer;font-size:11px;font-weight:700;"
                              f"background:color-mix(in srgb,{col} 20%,transparent);"
                              f"border:1px solid color-mix(in srgb,{col} 55%,transparent);color:{col};"
                              f"transition:all 0.2s")
                    _off_s = (f"display:inline-flex;align-items:center;gap:6px;padding:5px 14px;"
                              f"border-radius:99px;cursor:pointer;font-size:11px;font-weight:700;"
                              f"background:{C['BG']};border:1px solid {C['BORDER']};color:{C['MUTED']};"
                              f"transition:all 0.2s")

                    def _dot(on, c=col):
                        clr = c if on else C["MUTED"]
                        return f'<span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>'

                    tog = ui.html(
                        f'<div style="{_on_s if _val[0] else _off_s}">'
                        f'{_dot(_val[0])} {"AKTİF" if _val[0] else "PASİF"}</div>'
                    )

                    def make_toggle(k=key, v=_val, t=tog, on=_on_s, off=_off_s, c=col):
                        def _toggle():
                            v[0] = not v[0]
                            ms[k] = v[0]
                            clr = c if v[0] else C["MUTED"]
                            dot = f'<span style="width:8px;height:8px;border-radius:50%;background:{clr};flex-shrink:0"></span>'
                            t.set_content(
                                f'<div style="{on if v[0] else off}">{dot} {"AKTİF" if v[0] else "PASİF"}</div>'
                            )
                            _save_cfg()
                        return _toggle
                    tog.on("click", make_toggle())

        # ── 2. TMDB API Key ───────────────────────────────────────────────────
        with ui.element("div").classes("card card-cyan").style("padding:16px 20px"):
            ui.html(f'<div class="card-title" style="color:{C["CYAN"]}">🎬 TMDB API ANAHTARI</div>')
            ui.html(f'<div style="font-size:11px;color:{C["MUTED"]};margin-bottom:12px">'
                    f'themoviedb.org üzerinden ücretsiz alınır — TMDB kaynağı için zorunlu.</div>')
            with ui.element("div").style("display:flex;gap:10px;align-items:center"):
                tmdb_inp = ui.input(
                    value=cfg.get("tmdb_api_key", ""),
                    placeholder="TMDB API key..."
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:9px 13px;color:{C['CYAN']};"
                    f"font-family:Consolas,monospace;font-size:12px"
                )
                def save_tmdb():
                    cfg["tmdb_api_key"] = tmdb_inp.value.strip()
                    save_trans_cfg(cfg)
                    ui.notify("TMDB key kaydedildi ✔", type="positive")
                nbtn("💾 Kaydet", click=save_tmdb, variant="ghost", size="sm")

        # ── 2b. Franchise Veritabanı API Anahtarları ─────────────────────────
        with ui.element("div").classes("card").style("padding:16px 20px"):
            ui.html(f'<div class="card-title" style="color:{C["PURPLE"]}">🎬 FRANCHİSE VERİTABANI API ANAHTARLARI</div>')
            ui.html(f'<div style="font-size:11px;color:{C["MUTED"]};margin-bottom:14px">'
                    f'Belirli evrenler için özel karakter/büyü/lokasyon veritabanları. '
                    f'PotterDB ve SWAPI ücretsiz — auth gerektirmez. '
                    f'The One API (LotR) ve Marvel için ücretsiz kayıt gerekir.</div>')

            # ─ PotterDB ─────────────────────────────────────────────────────
            with ui.element("div").style(
                f"display:flex;align-items:center;gap:10px;padding:10px 14px;"
                f"border-radius:10px;background:{C['PANEL']};border:1px solid {C['BORDER']};"
                f"margin-bottom:8px"
            ):
                ui.html(
                    f'<div style="flex:1">'
                    f'<div style="font-size:12px;font-weight:700;color:#f9c74f">⚗️ PotterDB (Harry Potter)</div>'
                    f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">'
                    f'api.potterdb.com — Karakterler + Büyüler + İksirler · Ücretsiz, auth yok</div>'
                    f'</div>'
                    f'<span style="padding:4px 12px;border-radius:99px;font-size:10px;font-weight:700;'
                    f'background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.4);color:#4ade80">'
                    f'✔ Auth Gerekmez</span>'
                )

            # ─ SWAPI ────────────────────────────────────────────────────────
            with ui.element("div").style(
                f"display:flex;align-items:center;gap:10px;padding:10px 14px;"
                f"border-radius:10px;background:{C['PANEL']};border:1px solid {C['BORDER']};"
                f"margin-bottom:8px"
            ):
                ui.html(
                    f'<div style="flex:1">'
                    f'<div style="font-size:12px;font-weight:700;color:#60a5fa">⭐ SWAPI (Star Wars)</div>'
                    f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">'
                    f'swapi.info / swapi.tech — Karakterler + Gezegenler + Gemiler · Ücretsiz, auth yok</div>'
                    f'</div>'
                    f'<span style="padding:4px 12px;border-radius:99px;font-size:10px;font-weight:700;'
                    f'background:rgba(34,197,94,0.15);border:1px solid rgba(34,197,94,0.4);color:#4ade80">'
                    f'✔ Auth Gerekmez</span>'
                )

            # ─ The One API (LotR) ────────────────────────────────────────────
            ui.html(f'<div style="font-size:11px;font-weight:700;color:#a78bfa;margin:12px 0 6px">💍 The One API (Lord of the Rings / Hobbit)</div>')
            ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-bottom:8px">'
                    f'the-one-api.dev üzerinden ücretsiz kayıt ile alınır. '
                    f'Tüm LotR/Hobbit karakterleri + alıntılar · Yoksa sadece TVmaze kullanılır.</div>')
            with ui.element("div").style("display:flex;gap:10px;align-items:center;margin-bottom:12px"):
                lotr_inp = ui.input(
                    value=cfg.get("lotr_api_key", ""),
                    placeholder="Bearer token (the-one-api.dev)...",
                    password=True
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:#a78bfa;"
                    f"font-family:Consolas,monospace;font-size:11px"
                )
                def save_lotr():
                    v = lotr_inp.value.strip()
                    cfg["lotr_api_key"] = v
                    save_trans_cfg(cfg)
                    # offline_db_manager'a da yaz
                    try:
                        import offline_db_manager as _odb
                        import os as _os
                        _odb_dir = _odb._DIR
                        _key_file = _os.path.join(_odb_dir, "lotr_api_key.txt")
                        with open(_key_file, "w", encoding="utf-8") as _f:
                            _f.write(v)
                    except Exception:
                        pass
                    ui.notify("LotR API key kaydedildi ✔", type="positive")
                nbtn("💾 Kaydet", click=save_lotr, variant="ghost", size="sm")
                ui.html(
                    f'<a href="https://the-one-api.dev/sign-up" target="_blank" '
                    f'style="font-size:10px;color:{C["CYAN"]};text-decoration:none;white-space:nowrap">'
                    f'🔗 Kayıt Ol</a>'
                )

            # ─ Marvel API ───────────────────────────────────────────────────
            ui.html(f'<div style="font-size:11px;font-weight:700;color:#f87171;margin-bottom:6px">🦸 Marvel API (MCU)</div>')
            ui.html(f'<div style="font-size:10px;color:{C["MUTED"]};margin-bottom:8px">'
                    f'developer.marvel.com üzerinden ücretsiz alınır (public key yeterli). '
                    f'Tüm Marvel karakterleri + seriler · İsteğe bağlı.</div>')
            with ui.element("div").style("display:flex;gap:10px;align-items:center;margin-bottom:4px"):
                marvel_inp = ui.input(
                    value=cfg.get("marvel_api_key", ""),
                    placeholder="Marvel Public API Key (developer.marvel.com)...",
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:#f87171;"
                    f"font-family:Consolas,monospace;font-size:11px"
                )
                def save_marvel():
                    v = marvel_inp.value.strip()
                    cfg["marvel_api_key"] = v
                    save_trans_cfg(cfg)
                    try:
                        import offline_db_manager as _odb
                        import os as _os
                        _key_file = _os.path.join(_odb._DIR, "marvel_api_key.txt")
                        with open(_key_file, "w", encoding="utf-8") as _f:
                            _f.write(v)
                    except Exception:
                        pass
                    ui.notify("Marvel API key kaydedildi ✔", type="positive")
                nbtn("💾 Kaydet", click=save_marvel, variant="ghost", size="sm")
                ui.html(
                    f'<a href="https://developer.marvel.com/" target="_blank" '
                    f'style="font-size:10px;color:{C["CYAN"]};text-decoration:none;white-space:nowrap">'
                    f'🔗 Kayıt Ol</a>'
                )


        # ── 2c. Wikidata P31 — Ücretsiz, Auth Gerektirmez ────────────────────
        with ui.element("div").classes("card").style("padding:16px 20px;margin-top:0"):
            ui.html(
                f'<div class="card-title" style="color:{C["GREEN"]}">🌐 WIKIDATA P31 TÜR TANIMA</div>'
            )
            ui.html(
                f'<div style="font-size:11px;color:{C["MUTED"]};margin-bottom:10px">'
                f'API anahtarı gerekmez — tamamen ücretsiz ve açık. '
                f'Aynı isimli içerikler arasından doğru olanı tür bilgisiyle (P31) seçer.<br>'
                f'Örnek: "Dark" → Q28443710 <span style="color:{C["GREEN"]}">television series</span> '
                f'(video game, album, borsa değil). Sonuçlar 60 gün cache\'lenir.</div>'
            )
            with ui.element("div").style("display:flex;gap:8px;flex-wrap:wrap;align-items:center"):
                # P31 tür-to-Wikidata ID özeti
                for label, qid, color in [
                    ("📺 Dizi",     "Q5398426",  C["CYAN"]),
                    ("🎬 Film",     "Q11424",    C["PURPLE"]),
                    ("🈴 Anime",    "Q63952888", C["GREEN"]),
                    ("🎌 Anime Film","Q20650540", C["YELLOW"]),
                ]:
                    ui.html(
                        f'<span style="background:{C["BG2"]};border:1px solid {C["BORDER"]};'
                        f'border-radius:6px;padding:3px 9px;font-size:10px;color:{color};'
                        f'font-family:Consolas,monospace">{label} → {qid}</span>'
                    )

            # Cache temizleme
            ui.html(
                f'<div style="margin-top:12px;font-size:11px;font-weight:700;color:{C["YELLOW"]}">'
                f'🗑 Wikidata P31 Cache Yönetimi</div>'
            )
            ui.html(
                f'<div style="font-size:10px;color:{C["MUTED"]};margin-bottom:8px">'
                f'Not-found cache\'leri temizlemek yeni başlıkların tekrar aranmasını sağlar.</div>'
            )
            _wd_cache_status = ui.html(
                f'<div style="font-size:10px;color:{C["MUTED"]}">Durum bilinmiyor...</div>'
            )

            async def refresh_wd_status():
                import os as _os2
                try:
                    import sys as _sys2
                    _sys2.path.insert(0, _scripts_dir)
                    import offline_db_manager as _odb2
                    _cd = _odb2._WIKIDATA_TITLE_CACHE_DIR
                    if _os2.path.exists(_cd):
                        files = _os2.listdir(_cd)
                        import json as _json2
                        found = sum(1 for f in files if _json2.load(open(
                            _os2.path.join(_cd, f), encoding='utf-8')).get('found', False))
                        not_found = len(files) - found
                        _wd_cache_status.set_content(
                            f'<div style="font-size:10px;color:{C["GREEN"]}">'
                            f'✅ {len(files)} kayıt: {found} bulundu, '
                            f'{not_found} not-found | '
                            f'Cache: {_cd}</div>'
                        )
                    else:
                        _wd_cache_status.set_content(
                            f'<div style="font-size:10px;color:{C["MUTED"]}">Cache henüz oluşmadı.</div>'
                        )
                except Exception as _e:
                    _wd_cache_status.set_content(
                        f'<div style="font-size:10px;color:{C["YELLOW"]}">⚠ {_e}</div>'
                    )

            async def clear_notfound_cache():
                import os as _os3, json as _json3
                try:
                    import sys as _sys3
                    _sys3.path.insert(0, _scripts_dir)
                    import offline_db_manager as _odb3
                    _cd = _odb3._WIKIDATA_TITLE_CACHE_DIR
                    cleared = 0
                    if _os3.path.exists(_cd):
                        for fn in _os3.listdir(_cd):
                            fp = _os3.path.join(_cd, fn)
                            try:
                                d = _json3.load(open(fp, encoding='utf-8'))
                                if not d.get('found', True):
                                    _os3.remove(fp)
                                    cleared += 1
                            except Exception:
                                pass
                    ui.notify(f"✔ {cleared} not-found cache silindi", type="positive")
                    await refresh_wd_status()
                except Exception as _e:
                    ui.notify(f"Hata: {_e}", type="negative")

            async def clear_all_wd_cache():
                import os as _os4, shutil as _sh
                try:
                    import sys as _sys4
                    _sys4.path.insert(0, _scripts_dir)
                    import offline_db_manager as _odb4
                    _cd = _odb4._WIKIDATA_TITLE_CACHE_DIR
                    if _os4.path.exists(_cd):
                        _sh.rmtree(_cd)
                    ui.notify("✔ Tüm Wikidata P31 cache temizlendi", type="positive")
                    await refresh_wd_status()
                except Exception as _e:
                    ui.notify(f"Hata: {_e}", type="negative")

            with ui.element("div").style("display:flex;gap:8px;flex-wrap:wrap"):
                nbtn("🔄 Durum", click=refresh_wd_status, variant="ghost", size="sm")
                nbtn("🧹 Not-Found Temizle", click=clear_notfound_cache, variant="ghost", size="sm")
                nbtn("🗑 Tümünü Sil", click=clear_all_wd_cache, variant="ghost", size="sm")

        # ── 3. API Sağlayıcı Bağlantıları ────────────────────────────────────
        with ui.element("div").classes("card").style("padding:16px 20px"):
            ui.html(f'<div class="card-title">🔗 API SAĞLAYICI BAĞLANTILARI</div>')

            # OpenRouter
            ui.html(f'<div style="font-size:11px;font-weight:700;color:{C["PURPLE"]};margin-top:8px;margin-bottom:6px">🌐 OpenRouter API</div>')
            with ui.element("div").style("display:flex;gap:10px;margin-bottom:12px"):
                or_url_inp = ui.input(
                    value=cfg.get("api_url", "https://openrouter.ai/api/v1/chat/completions"),
                    placeholder="OpenRouter API URL..."
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:{C['TEXT']};"
                    f"font-family:Consolas,monospace;font-size:11px"
                )
                def save_or_url():
                    v = or_url_inp.value.strip()
                    if v: cfg["api_url"] = v; save_trans_cfg(cfg)
                    ui.notify("OpenRouter URL kaydedildi ✔", type="positive")
                nbtn("💾", click=save_or_url, variant="icon", size="sm")

            # Antigravity
            ui.html(f'<div style="font-size:11px;font-weight:700;color:{C["CYAN"]};margin-bottom:6px">⚡ Antigravity API (Yerel)</div>')
            with ui.element("div").style("display:flex;gap:10px;margin-bottom:8px"):
                ag_url_inp = ui.input(
                    value=cfg.get("antigravity_url", "http://localhost:8045/v1/chat/completions"),
                    placeholder="Antigravity URL..."
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:{C['CYAN']};"
                    f"font-family:Consolas,monospace;font-size:11px"
                )
                ag_key_inp = ui.input(
                    value=cfg.get("antigravity_api_key", ""),
                    placeholder="AG API key...",
                    password=True
                ).style(
                    f"flex:1;background:{C['BG']};border:1px solid {C['BORDER']};"
                    f"border-radius:9px;padding:8px 12px;color:{C['CYAN']};"
                    f"font-family:Consolas,monospace;font-size:11px"
                )
                def save_ag():
                    cfg["antigravity_url"]    = ag_url_inp.value.strip()
                    cfg["antigravity_api_key"] = ag_key_inp.value.strip()
                    save_trans_cfg(cfg)
                    ui.notify("Antigravity ayarları kaydedildi ✔", type="positive")
                nbtn("💾", click=save_ag, variant="icon", size="sm")

        # ── 4. Bağlantı Testi ─────────────────────────────────────────────────
        with ui.element("div").classes("card").style("padding:16px 20px"):
            ui.html(f'<div class="card-title">🔌 BAĞLANTI TESTİ</div>')

            test_log = ui.element("div").style(
                f"background:{C['BG']};border:1px solid {C['BORDER']};border-radius:9px;"
                f"padding:10px 14px;font-family:Consolas,monospace;font-size:11px;"
                f"color:{C['SUB']};min-height:44px;max-height:160px;overflow-y:auto;"
                f"white-space:pre-wrap;margin-bottom:12px"
            )
            with test_log:
                ui.html(f'<span style="color:{C["MUTED"]}">Test başlatmak için butona basın...</span>')

            async def run_connection_test():
                import asyncio, httpx as _hx
                test_log.clear()

                # (name, method, url, body, headers, enabled, ok_codes)
                TESTS = [
                    ("Jikan (MAL)", "GET",
                     "https://api.jikan.moe/v4/anime/1",
                     None, {}, ms.get("jikan", True), {200}),

                    ("AniList", "POST",
                     "https://graphql.anilist.co",
                     '{"query":"{ Media(id:1) { id } }"}',
                     {"Content-Type": "application/json"},
                     ms.get("anilist", True), {200}),

                    ("Kitsu", "GET",
                     "https://kitsu.io/api/edge/anime?page[limit]=1",
                     None, {}, ms.get("kitsu", True), {200}),

                    ("TVMaze", "GET",
                     "https://api.tvmaze.com/shows/1",
                     None, {}, ms.get("tvmaze", True), {200}),

                    ("PotterDB", "GET",
                     "https://api.potterdb.com/v1/characters?page[size]=1",
                     None, {}, True, {200}),

                    ("SWAPI (Star Wars)", "GET",
                     "https://swapi.info/api/people/1/",
                     None, {}, True, {200}),

                    ("TMDB", "GET",
                     f"https://api.themoviedb.org/3/configuration?api_key={cfg.get('tmdb_api_key','')}",
                     None, {}, ms.get("tmdb", True), {200}),

                    ("The One API (LotR)", "GET",
                     "https://the-one-api.dev/v2/character",
                     None, {"Authorization": f"Bearer {cfg.get('lotr_api_key','')}"} if cfg.get('lotr_api_key') else {},
                     bool(cfg.get("lotr_api_key")), {200}),

                    ("Marvel API", "GET",
                     f"https://gateway.marvel.com/v1/public/characters?limit=1&apikey={cfg.get('marvel_api_key','')}",
                     None, {}, bool(cfg.get("marvel_api_key")), {200}),

                    ("Wikidata SPARQL", "GET",
                     "https://query.wikidata.org/sparql?query=SELECT%20%2A%20WHERE%7B%7D%20LIMIT%201&format=json",
                     None, {"Accept": "application/json",
                            "User-Agent": "AnimeSubtitleTranslator/3.0"},
                     True, {200}),

                    # OpenRouter: /models GET endpoint'i kullan (chat/completions sadece POST)
                    ("OpenRouter", "GET",
                     "https://openrouter.ai/api/v1/models",
                     None, {}, True, {200}),

                    # Antigravity: 401 de "çalışıyor" demek (auth gerekiyor)
                    ("Antigravity", "GET",
                     cfg.get("antigravity_url", "").replace("/chat/completions", "/models"),
                     None, {}, True, {200, 401, 403, 405}),
                ]

                with test_log:
                    for name, method, url, body, headers, enabled, ok_codes in TESTS:
                        if not enabled:
                            ui.html(f'<div style="color:{C["MUTED"]}">⏭ {name}: Devre dışı</div>')
                            continue
                        if not url or url.endswith("?api_key="):
                            ui.html(f'<div style="color:{C["YELLOW"]}">⚠ {name}: URL / API key eksik</div>')
                            continue
                        try:
                            async with _hx.AsyncClient(timeout=6.0) as client:
                                if method == "POST":
                                    r = await client.post(url, content=body, headers=headers)
                                else:
                                    r = await client.get(url, headers=headers)
                            is_ok = r.status_code in ok_codes
                            ok_c = C["GREEN"] if is_ok else C["YELLOW"]
                            icon = "✔" if is_ok else "⚠"
                            note = " (auth gerekli — çalışıyor)" if r.status_code == 401 else ""
                            ui.html(f'<div style="color:{ok_c}">{icon} {name}: HTTP {r.status_code}{note}</div>')
                        except Exception as e:
                            ui.html(f'<div style="color:{C["RED"]}">✘ {name}: {str(e)[:70]}</div>')
                        await asyncio.sleep(0.05)
                    ui.html(f'<div style="color:{C["MUTED"]};margin-top:6px">─── Test tamamlandı ───</div>')

            nbtn("▶ BAĞLANTI TESTİ BAŞLAT", click=run_connection_test, full=True)

        # ── 5. Önbellek Temizle ───────────────────────────────────────────────
        with ui.element("div").classes("card").style("padding:14px 20px"):
            ui.html(f'<div class="card-title">🗑️ ÖNBELLEK & CACHE</div>')
            with ui.element("div").style("display:flex;gap:10px;flex-wrap:wrap;margin-top:8px"):

                def clear_episode_cache():
                    try:
                        ep_file = os.path.join(PARENT_DIR, "episode_context.json")
                        if os.path.exists(ep_file):
                            import json as _j
                            with open(ep_file, "w", encoding="utf-8") as f:
                                _j.dump({}, f)
                            ui.notify("episode_context.json temizlendi", type="warning")
                        else:
                            ui.notify("Cache dosyası bulunamadı", type="info")
                    except Exception as e:
                        ui.notify(f"Hata: {e}", type="negative")

                def open_cache_folder():
                    os.startfile(PARENT_DIR)

                nbtn("🧹 Bölüm Cache Temizle", click=clear_episode_cache, variant="danger", size="sm")
                nbtn("📁 Cache Klasörü Aç",    click=open_cache_folder,   variant="ghost",  size="sm")


# ════════════════════════════════════════════════════════════════════════════
# 🔔  BİLDİRİM GEÇMİŞİ SAYFASI
# ════════════════════════════════════════════════════════════════════════════
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
def build_api_keys():
    from ng_config import API_FILE, EX_FILE

    def _read_keys(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [l.strip() for l in f if l.strip()]
        except Exception:
            return []

    def _save_keys(path, keys):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(keys))

    @ui.refreshable
    def _page_body():
        active_keys  = _read_keys(API_FILE)
        exhaust_keys = _read_keys(EX_FILE)
        total        = len(active_keys) + len(exhaust_keys)
        health_pct   = round(len(active_keys) / total * 100) if total > 0 else 0

        # ── Stat kartları ──────────────────────────────────────────────────────
        with ui.element("div").style(
            "display:grid;grid-template-columns:repeat(4,1fr);gap:16px;"
            "padding:0 28px 20px"
        ):
            # Aktif
            with ui.element("div").style(
                "border-radius:14px;padding:20px;position:relative;overflow:hidden;"
                "background:linear-gradient(135deg,rgba(16,185,129,0.18),rgba(16,185,129,0.06));"
                "border:1px solid rgba(16,185,129,0.35);"
                "box-shadow:0 4px 24px rgba(16,185,129,0.12)"
            ):
                ui.html(
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
                    f'color:#10b981;text-transform:uppercase;margin-bottom:8px">✅ Aktif Anahtarlar</div>'
                    f'<div style="font-size:36px;font-weight:900;color:#10b981;line-height:1">{len(active_keys)}</div>'
                    f'<div style="font-size:11px;color:rgba(16,185,129,0.7);margin-top:6px">Kullanıma hazır</div>'
                )
            # Tükenmiş
            with ui.element("div").style(
                "border-radius:14px;padding:20px;position:relative;overflow:hidden;"
                "background:linear-gradient(135deg,rgba(239,68,68,0.18),rgba(239,68,68,0.06));"
                "border:1px solid rgba(239,68,68,0.35);"
                "box-shadow:0 4px 24px rgba(239,68,68,0.12)"
            ):
                ui.html(
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
                    f'color:#ef4444;text-transform:uppercase;margin-bottom:8px">❌ Tükenmiş</div>'
                    f'<div style="font-size:36px;font-weight:900;color:#ef4444;line-height:1">{len(exhaust_keys)}</div>'
                    f'<div style="font-size:11px;color:rgba(239,68,68,0.7);margin-top:6px">Kota doldu</div>'
                )
            # Toplam
            with ui.element("div").style(
                "border-radius:14px;padding:20px;"
                "background:rgba(0,0,0,0.30);border:1px solid rgba(255,255,255,0.10)"
            ):
                ui.html(
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
                    f'color:var(--accent2);text-transform:uppercase;margin-bottom:8px">🔢 Toplam</div>'
                    f'<div style="font-size:36px;font-weight:900;color:var(--accent2);line-height:1">{total}</div>'
                    f'<div style="font-size:11px;color:var(--muted);margin-top:6px">Kayıtlı anahtar</div>'
                )
            # Sağlık
            health_col = "#10b981" if health_pct >= 60 else ("#f59e0b" if health_pct >= 30 else "#ef4444")
            with ui.element("div").style(
                "border-radius:14px;padding:20px;"
                f"background:linear-gradient(135deg,rgba(0,0,0,0.30),rgba(0,0,0,0.18));"
                f"border:1px solid {health_col}44"
            ):
                ui.html(
                    f'<div style="font-size:11px;font-weight:700;letter-spacing:1.5px;'
                    f'color:{health_col};text-transform:uppercase;margin-bottom:8px">⚡ API Sağlığı</div>'
                    f'<div style="font-size:36px;font-weight:900;color:{health_col};line-height:1">%{health_pct}</div>'
                    f'<div style="height:4px;border-radius:99px;background:rgba(255,255,255,0.1);margin-top:10px">'
                    f'  <div style="height:4px;border-radius:99px;width:{health_pct}%;'
                    f'background:{health_col};box-shadow:0 0 8px {health_col}88;transition:width 0.5s"></div>'
                    f'</div>'
                )

        # ── Ana içerik: 2 sütun ────────────────────────────────────────────────
        with ui.element("div").style(
            "display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:0 28px 28px"
        ):
            # ── SOL: Aktif anahtarlar listesi ──
            with ui.element("div").style("display:flex;flex-direction:column;gap:16px"):

                with ui.element("div").classes("card card-green"):
                    with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;margin-bottom:14px"):
                        ui.html(f'<div class="card-title" style="color:#10b981;margin-bottom:0">✅ AKTİF ANAHTARLAR ({len(active_keys)})</div>')
                        def _copy_all_active(keys=active_keys):
                            txt = "\n".join(keys)
                            ui.run_javascript(f'navigator.clipboard.writeText({repr(txt)})')
                            ui.notify(f"📋 {len(keys)} anahtar kopyalandı", type="positive", timeout=2000)
                        nbtn("📋 Tümünü Kopyala", click=_copy_all_active, size="sm", variant="ghost")

                    if not active_keys:
                        ui.html('<div style="text-align:center;padding:28px;color:var(--muted);font-size:13px">Henüz aktif anahtar yok</div>')
                    else:
                        with ui.element("div").style("display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto"):
                            for idx, k in enumerate(active_keys):
                                masked = k[:12] + "••••••••" + k[-4:] if len(k) > 18 else k[:6] + "••••"
                                with ui.element("div").style(
                                    "display:flex;align-items:center;gap:8px;padding:8px 12px;"
                                    "border-radius:9px;background:rgba(16,185,129,0.08);"
                                    "border:1px solid rgba(16,185,129,0.20)"
                                ):
                                    ui.html(f'<span style="width:8px;height:8px;border-radius:50%;background:#10b981;flex-shrink:0;box-shadow:0 0 6px #10b981"></span>')
                                    ui.html(
                                        f'<span style="flex:1;font-size:11px;color:#a7f3d0;'
                                        f'font-family:Consolas,monospace;overflow:hidden;'
                                        f'text-overflow:ellipsis;white-space:nowrap">{masked}</span>'
                                    )
                                    ui.html(f'<span style="font-size:9px;color:rgba(16,185,129,0.5);flex-shrink:0">#{idx+1}</span>')
                                    def _del_active(i=idx, all_k=list(active_keys)):
                                        all_k.pop(i)
                                        _save_keys(API_FILE, all_k)
                                        ui.notify("🗑️ Anahtar silindi", type="warning", timeout=2000)
                                        _page_body.refresh()
                                    with ui.element("button").style(
                                        "padding:2px 7px;border-radius:5px;font-size:10px;"
                                        "background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);"
                                        "color:#ef4444;cursor:pointer;flex-shrink:0"
                                    ).on("click", _del_active):
                                        ui.html("✕")

                # ── Yeni anahtar ekle ──
                with ui.element("div").classes("card"):
                    ui.html(f'<div class="card-title" style="color:var(--accent1)">➕ YENİ ANAHTAR EKLE</div>')

                    new_key_inp = ui.input(
                        placeholder="sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx..."
                    ).style(
                        f"width:100%;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.14);"
                        f"border-radius:9px;padding:10px 14px;color:#e2e8f0;"
                        f"font-family:Consolas,monospace;font-size:12px;margin-bottom:10px"
                    )

                    def _do_add():
                        k = new_key_inp.value.strip()
                        if not k:
                            ui.notify("Anahtar boş!", type="warning"); return
                        existing = _read_keys(API_FILE)
                        if k in existing:
                            ui.notify("Bu anahtar zaten mevcut!", type="warning"); return
                        existing.append(k)
                        _save_keys(API_FILE, existing)
                        new_key_inp.set_value("")
                        ui.notify("✅ Anahtar eklendi", type="positive")
                        _page_body.refresh()

                    nbtn("➕ Ekle", click=_do_add, full=True)

                    # Toplu ekleme
                    ui.html(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;color:var(--muted);margin:12px 0 6px">📋 TOPLU EKLEME (her satıra bir anahtar)</div>')
                    bulk_inp = ui.textarea(
                        placeholder="sk-or-v1-aaa...\nsk-or-v1-bbb...\nsk-or-v1-ccc..."
                    ).style(
                        f"width:100%;background:rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.14);"
                        f"border-radius:9px;padding:10px 14px;color:#e2e8f0;"
                        f"font-family:Consolas,monospace;font-size:11px;min-height:80px;margin-bottom:10px"
                    )

                    def _do_bulk_add():
                        raw = bulk_inp.value.strip()
                        if not raw:
                            ui.notify("Alan boş!", type="warning"); return
                        new_keys = [l.strip() for l in raw.splitlines() if l.strip()]
                        existing = _read_keys(API_FILE)
                        added = 0
                        for k in new_keys:
                            if k not in existing:
                                existing.append(k)
                                added += 1
                        _save_keys(API_FILE, existing)
                        bulk_inp.set_value("")
                        ui.notify(f"✅ {added} yeni anahtar eklendi ({len(new_keys)-added} mükerrer atlandı)", type="positive")
                        _page_body.refresh()

                    nbtn("📋 Toplu Ekle", click=_do_bulk_add, full=True, variant="ghost")

            # ── SAĞ: Tükenmiş anahtarlar + aksiyon butonları ──
            with ui.element("div").style("display:flex;flex-direction:column;gap:16px"):

                with ui.element("div").classes("card"):
                    with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;margin-bottom:14px"):
                        ui.html(f'<div class="card-title" style="color:#ef4444;margin-bottom:0">❌ TÜKENMİŞ ANAHTARLAR ({len(exhaust_keys)})</div>')

                    if not exhaust_keys:
                        ui.html('<div style="text-align:center;padding:28px;color:var(--muted);font-size:13px">Tükenmiş anahtar yok 🎉</div>')
                    else:
                        with ui.element("div").style("display:flex;flex-direction:column;gap:6px;max-height:300px;overflow-y:auto"):
                            for idx, k in enumerate(exhaust_keys):
                                masked = k[:12] + "••••••••" + k[-4:] if len(k) > 18 else k[:6] + "••••"
                                with ui.element("div").style(
                                    "display:flex;align-items:center;gap:8px;padding:8px 12px;"
                                    "border-radius:9px;background:rgba(239,68,68,0.07);"
                                    "border:1px solid rgba(239,68,68,0.18)"
                                ):
                                    ui.html(f'<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;flex-shrink:0;opacity:0.6"></span>')
                                    ui.html(
                                        f'<span style="flex:1;font-size:11px;color:#fca5a5;opacity:0.7;'
                                        f'font-family:Consolas,monospace;overflow:hidden;'
                                        f'text-overflow:ellipsis;white-space:nowrap">{masked}</span>'
                                    )

                # ── Kontrol butonları ──
                with ui.element("div").classes("card card-purple"):
                    ui.html(f'<div class="card-title">🔧 YÖNETİM İŞLEMLERİ</div>')
                    with ui.element("div").style("display:flex;flex-direction:column;gap:10px"):

                        def _reset_ex():
                            ex = _read_keys(EX_FILE)
                            if not ex:
                                ui.notify("Tükenmiş anahtar yok", type="info"); return
                            act = _read_keys(API_FILE)
                            act.extend(ex)
                            _save_keys(API_FILE, act)
                            _save_keys(EX_FILE, [])
                            ui.notify(f"♻️ {len(ex)} anahtar geri yüklendi", type="positive")
                            _page_body.refresh()

                        def _clear_ex():
                            ex = _read_keys(EX_FILE)
                            if not ex:
                                ui.notify("Tükenmiş anahtar yok", type="info"); return
                            _save_keys(EX_FILE, [])
                            ui.notify(f"🗑️ {len(ex)} tükenmiş anahtar silindi", type="warning")
                            _page_body.refresh()

                        def _clear_all_active():
                            act = _read_keys(API_FILE)
                            if not act:
                                ui.notify("Aktif anahtar yok", type="info"); return
                            _save_keys(API_FILE, [])
                            ui.notify(f"⚠️ {len(act)} aktif anahtar silindi", type="negative")
                            _page_body.refresh()

                        def _refresh_page():
                            _page_body.refresh()
                            ui.notify("🔄 Sayfa yenilendi", type="info", timeout=1500)

                        nbtn("♻️  Tükenmişleri Geri Yükle", click=_reset_ex, full=True,
                             style="margin-bottom:2px")
                        ui.html(f'<div style="font-size:10px;color:var(--muted);padding:0 4px 6px">'
                                f'Tükenmiş tüm anahtarları tekrar aktif listeye taşır</div>')

                        nbtn("🔄  Sayfayı Yenile", click=_refresh_page, full=True, variant="ghost",
                             style="margin-bottom:2px")

                        nbtn("🗑️  Tükenmişleri Sil", click=_clear_ex, full=True, variant="danger",
                             style="margin-bottom:2px")
                        ui.html(f'<div style="font-size:10px;color:var(--muted);padding:0 4px 6px">'
                                f'Tükenmiş listesini kalıcı olarak temizler</div>')

                        with ui.element("div").style(
                            "padding:10px;border-radius:9px;border:1px solid rgba(239,68,68,0.3);"
                            "background:rgba(239,68,68,0.06);margin-top:4px"
                        ):
                            ui.html('<div style="font-size:10px;font-weight:700;color:#ef4444;margin-bottom:6px">⚠️ TEHLİKELİ BÖLGE</div>')
                            nbtn("💣  Tüm Aktif Anahtarları Sil", click=_clear_all_active,
                                 full=True, variant="danger")
                            ui.html('<div style="font-size:9px;color:rgba(239,68,68,0.6);margin-top:4px">Bu işlem geri alınamaz!</div>')

                # ── Dosya yolları bilgisi ──
                with ui.element("div").classes("card").style("padding:14px 16px"):
                    ui.html(
                        f'<div style="font-size:10px;font-weight:700;color:var(--muted);'
                        f'letter-spacing:1px;text-transform:uppercase;margin-bottom:10px">📁 DOSYA KONUMLARI</div>'
                    )
                    for lbl, path in [("Aktif Anahtarlar", API_FILE), ("Tükenmiş Anahtarlar", EX_FILE)]:
                        ui.html(
                            f'<div style="margin-bottom:8px">'
                            f'<div style="font-size:10px;color:var(--sub);margin-bottom:2px">{lbl}</div>'
                            f'<div style="font-size:10px;font-family:Consolas,monospace;color:var(--accent2);'
                            f'word-break:break-all;padding:6px 8px;border-radius:6px;'
                            f'background:rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.08)">'
                            f'{path}</div></div>'
                        )

    # ── Sayfa başlığı ──
    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">🔑 API Anahtarları</div>')
        ui.html('<div class="ph-sub">OpenRouter API anahtarlarını yönet — ekle, sil, geri yükle</div>')

    with ui.element("div").style("padding:20px 0 0"):
        _page_body()


# ════════════════════════════════════════════════════════════════════════════
# 👥  ANTİGRAVİTY HESAPLAR SAYFASI
# ════════════════════════════════════════════════════════════════════════════
def build_accounts():
    import urllib.request as _ur, json as _jj, os as _os2, datetime as _dt
    from ng_config import load_prefs

    _state = {
        "accounts": [], 
        "current_account_id": "",
        "search": "", 
        "filter": "Tümü", 
        "selected_ids": set(),
        "page": 1,
        "per_page": 10,
        "loading": False
    }

    # API credentials helper
    def _get_api_info():
        try:
            cfg_path = _os2.path.expanduser(r"~\.antigravity_tools\gui_config.json")
            if not _os2.path.exists(cfg_path):
                return None, None
            with open(cfg_path, encoding="utf-8") as _f:
                _cfg = _jj.load(_f)
            return _cfg.get("proxy", {}).get("api_key", ""), _cfg.get("proxy", {}).get("port", 8045)
        except Exception:
            return None, None

    # Sync worker for fetching accounts to run in thread pool
    def _fetch_accounts_sync_worker():
        key, port = _get_api_info()
        if not key:
            return {"error": "Antigravity proxy konfigürasyonu bulunamadı!"}
        try:
            # 1. Fetch all accounts
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts",
                headers={"Authorization": f"Bearer {key}"}
            )
            _resp = _ur.urlopen(_req, timeout=3)
            _data = _jj.loads(_resp.read())
            
            # 2. Fetch current account
            _current_id = ""
            try:
                _req_curr = _ur.Request(
                    f"http://localhost:{port}/api/accounts/current",
                    headers={"Authorization": f"Bearer {key}"}
                )
                _resp_curr = _ur.urlopen(_req_curr, timeout=2)
                _curr_data = _jj.loads(_resp_curr.read())
                if isinstance(_curr_data, dict):
                    _current_id = _curr_data.get("id", "")
            except Exception:
                pass
            
            return {"data": _data, "current_id": _current_id}
        except Exception as _e:
            return {"error": f"Antigravity Proxy'ye bağlanılamadı: {_e}"}

    async def _fetch_accounts():
        import asyncio
        if _state.get("loading"):
            return
        _state["loading"] = True
        _body.refresh()
        
        res = await asyncio.to_thread(_fetch_accounts_sync_worker)
        
        _state["loading"] = False
        if "error" in res:
            ui.notify(res["error"], type="negative")
            _body.refresh()
            return
            
        _data = res["data"]
        _current_id = res["current_id"]
        
        if isinstance(_data, dict):
            _state["accounts"] = _data.get("accounts", [])
            _state["current_account_id"] = _data.get("current_account_id") or _current_id
        elif isinstance(_data, list):
            _state["accounts"] = _data
            _state["current_account_id"] = _current_id
        else:
            ui.notify("Hesaplar alınamadı (yanlış veri formatı)", type="warning")
            
        _body.refresh()

    def _trigger_fetch_accounts():
        import asyncio
        asyncio.create_task(_fetch_accounts())

    # Toggle proxy status
    def _toggle_proxy(account_id):
        key, port = _get_api_info()
        if not key: return
        try:
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/{account_id}/toggle-proxy",
                headers={"Authorization": f"Bearer {key}"},
                method="POST"
            )
            _ur.urlopen(_req, timeout=3)
            ui.notify("Proxy durumu güncellendi", type="positive")
            _fetch_accounts()
        except Exception as _e:
            ui.notify(f"Proxy değiştirilemedi: {_e}", type="negative")

    # Switch active account
    def _switch_account(account_id):
        key, port = _get_api_info()
        if not key: return
        try:
            _body_data = _jj.dumps({"accountId": account_id}).encode("utf-8")
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/switch",
                data=_body_data,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST"
            )
            _ur.urlopen(_req, timeout=3)
            ui.notify("Aktif hesap değiştirildi", type="positive")
            _fetch_accounts()
        except Exception as _e:
            ui.notify(f"Hesap değiştirilemedi: {_e}", type="negative")

    # Refresh single account quota
    def _refresh_single_quota(account_id):
        key, port = _get_api_info()
        if not key: return
        try:
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/{account_id}/quota",
                headers={"Authorization": f"Bearer {key}"}
            )
            _ur.urlopen(_req, timeout=3)
            ui.notify("Hesap kotası güncellendi", type="positive")
            _fetch_accounts()
        except Exception as _e:
            ui.notify(f"Kota güncellenemedi: {_e}", type="negative")

    # Delete single account
    def _delete_account(account_id, email):
        key, port = _get_api_info()
        if not key: return
        try:
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/{account_id}",
                headers={"Authorization": f"Bearer {key}"},
                method="DELETE"
            )
            _ur.urlopen(_req, timeout=3)
            ui.notify(f"{email} silindi", type="warning")
            _fetch_accounts()
        except Exception as _e:
            ui.notify(f"Silme hatası: {_e}", type="negative")

    # Edit account label
    def _update_label(account_id, current_label):
        async def _prompt():
            safe_lbl = (current_label or '').replace('"', '\\"')
            res = await ui.run_javascript('prompt("Hesap etiketi girin:", "%s")' % safe_lbl)
            if res is not None:
                key, port = _get_api_info()
                if not key: return
                try:
                    _body_data = _jj.dumps({"label": res.strip()}).encode("utf-8")
                    _req = _ur.Request(
                        f"http://localhost:{port}/api/accounts/{account_id}/label",
                        data=_body_data,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        method="POST"
                    )
                    _ur.urlopen(_req, timeout=3)
                    ui.notify("Etiket güncellendi", type="positive")
                    _fetch_accounts()
                except Exception as _e:
                    ui.notify(f"Etiket güncellenemedi: {_e}", type="negative")
        ui.timer(0.1, _prompt, once=True)

    # Show device fingerprints modal
    with ui.dialog() as _fingerprint_dialog, ui.card().style("width:550px; background:#0d1117; color:#c9d1d9; border:1px solid #30363d"):
        _fp_title = ui.html("").style("font-size:16px; font-weight:bold; border-bottom:1px solid #30363d; padding-bottom:8px; width:100%")
        _fp_content = ui.html("").style("width:100%; display:flex; flex-direction:column; gap:12px")
        with ui.row().style("justify-content: flex-end; width:100%"):
            ui.button("Kapat", on_click=_fingerprint_dialog.close).props("flat").style("color:#58a6ff")

    def _show_fingerprint(account_id):
        key, port = _get_api_info()
        if not key: return
        try:
            # Fetch profiles
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/{account_id}/device-profiles",
                headers={"Authorization": f"Bearer {key}"}
            )
            _resp = _ur.urlopen(_req, timeout=3)
            _data = _jj.loads(_resp.read())
            
            _target_email = ""
            for _a in _state["accounts"]:
                if _a.get("id") == account_id:
                    _target_email = _a.get("email", "")
                    break
            
            _fp_title.set_content(f"👣 Cihaz Parmak İzi Profilleri: {_target_email}")
            
            # Print profiles list
            _html_out = []
            if isinstance(_data, list) and len(_data) > 0:
                for idx, p in enumerate(_data):
                    _html_out.append(f"""
                    <div style="background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; margin-bottom:8px">
                      <div style="font-size:12px; font-weight:bold; color:#58a6ff">Profil #{idx+1}: {p.get('name', 'Bilinmeyen Cihaz')}</div>
                      <div style="font-size:11px; font-family:Consolas,monospace; color:#8b949e; margin-top:4px">
                        <b>Platform:</b> {p.get('platform', '-')}<br>
                        <b>User Agent:</b> {p.get('user_agent', '-')}<br>
                        <b>Cihaz ID:</b> {p.get('device_id', '-')}
                      </div>
                    </div>
                    """)
            else:
                _html_out.append('<div style="color:#8b949e; font-size:12px; padding:10px">Tanımlı parmak izi profili bulunamadı.</div>')
            
            _fp_content.set_content("".join(_html_out))
            _fingerprint_dialog.open()
        except Exception as _e:
            ui.notify(f"Profil bilgisi alınamadı: {_e}", type="negative")

    # Show account details modal dialog
    with ui.dialog() as _details_dialog, ui.card().style("width:550px; background:#0d1117; color:#c9d1d9; border:1px solid #30363d"):
        _det_title = ui.html("").style("font-size:16px; font-weight:bold; border-bottom:1px solid #30363d; padding-bottom:8px; width:100%")
        _det_content = ui.html("").style("width:100%; display:flex; flex-direction:column; gap:12px")
        with ui.row().style("justify-content: flex-end; width:100%"):
            ui.button("Kapat", on_click=_details_dialog.close).props("flat").style("color:#58a6ff")

    def _show_details(account_id):
        _target = None
        for _a in _state["accounts"]:
            if _a.get("id") == account_id:
                _target = _a
                break
        if not _target: return
        
        _det_title.set_content(f"🔍 Hesap Detayları: {_target.get('email')}")
        
        # Pretty print account data json
        _pretty = _jj.dumps(_target, indent=2, ensure_ascii=False)
        _det_content.set_content(f"""
            <div style="font-size:12px; line-height:1.6">
                <div style="margin-bottom:8px"><b>ID:</b> <span style="font-family:Consolas,monospace">{_target.get('id')}</span></div>
                <div style="margin-bottom:8px"><b>Email:</b> {_target.get('email')}</div>
                <div style="margin-bottom:8px"><b>Etiket:</b> {_target.get('label') or '-'}</div>
                <div style="margin-bottom:8px"><b>Rol / Tier:</b> {(_target.get('quota', {}).get('subscription_tier') or 'FREE').upper()}</div>
                <div style="margin-bottom:8px"><b>Proxy Durumu:</b> {"Aktif" if _target.get('proxy_enabled', True) else "Devre Dışı"}</div>
                
                <div style="margin-top:12px">
                    <b style="color:#8b949e">Ham Hesap Verisi (JSON):</b>
                    <pre style="background:#161b22; padding:10px; border-radius:6px; border:1px solid #30363d; overflow:auto; max-height:250px; font-family:Consolas,monospace; font-size:11px">{_pretty}</pre>
                </div>
            </div>
        """)
        _details_dialog.open()

    # Add account modal dialog
    with ui.dialog() as _add_dialog, ui.card().style("width:450px; background:#0d1117; color:#c9d1d9; border:1px solid #30363d"):
        ui.html('<div style="font-size:16px; font-weight:bold; border-bottom:1px solid #30363d; padding-bottom:8px">Yeni Hesap Ekle</div>')
        _email_inp = ui.input(placeholder="E-posta").style("width:100%; margin-top:12px; background:#161b22; color:#fff")
        _token_inp = ui.input(placeholder="Access Token / Refresh Token (Opsiyonel)").style("width:100%; margin-top:8px; background:#161b22; color:#fff")
        
        def _submit_new_account():
            email = _email_inp.value.strip()
            token = _token_inp.value.strip()
            if not email:
                ui.notify("E-posta boş bırakılamaz", type="warning")
                return
            key, port = _get_api_info()
            if not key: return
            try:
                _body_data = _jj.dumps({"email": email, "token": token}).encode("utf-8")
                _req = _ur.Request(
                    f"http://localhost:{port}/api/accounts",
                    data=_body_data,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    method="POST"
                )
                _ur.urlopen(_req, timeout=3)
                ui.notify(f"Hesap başarıyla eklendi: {email}", type="positive")
                _add_dialog.close()
                _email_inp.value = ""
                _token_inp.value = ""
                _trigger_fetch_accounts()
            except Exception as _e:
                ui.notify(f"Ekleme hatası: {_e}", type="negative")

        with ui.row().style("justify-content: flex-end; width:100%; margin-top:16px"):
            ui.button("İptal", on_click=_add_dialog.close).props("flat").style("color:#8b949e")
            ui.button("Ekle", on_click=_submit_new_account).style("background:#005cc5; color:#fff")

    # Bulk refresh quotas
    def _refresh_all_quotas():
        key, port = _get_api_info()
        if not key: return
        try:
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/refresh",
                headers={"Authorization": f"Bearer {key}"},
                method="POST"
            )
            _ur.urlopen(_req, timeout=5)
            ui.notify("Kotalar yenileniyor...", type="info")
            _trigger_fetch_accounts()
        except Exception as _e:
            ui.notify(f"Kota yenileme hatası: {_e}", type="negative")

    # Import from DB
    def _sync_from_db():
        key, port = _get_api_info()
        if not key: return
        try:
            _req = _ur.Request(
                f"http://localhost:{port}/api/accounts/sync/db",
                headers={"Authorization": f"Bearer {key}"},
                method="POST"
            )
            _ur.urlopen(_req, timeout=5)
            ui.notify("Veritabanından hesaplar senkronize ediliyor...", type="info")
            _trigger_fetch_accounts()
        except Exception as _e:
            ui.notify(f"Senkronizasyon hatası: {_e}", type="negative")

    # Main page body content (Refreshable)
    # Main page body content (Refreshable & Optimized with Pagination)
    @ui.refreshable
    def _body():
        _accounts = _state["accounts"]
        _current_active_id = _state["current_account_id"]
        _search_txt = _state["search"].lower().strip()
        _filt_val = _state["filter"]
        
        # 1. Apply Filtering
        _filtered = []
        for _a in _accounts:
            _em = (_a.get("email") or "").lower()
            _tier = (_a.get("quota", {}).get("subscription_tier") or "free").lower()
            
            # Search filter
            if _search_txt and _search_txt not in _em:
                continue
            
            # Tier filter
            if _filt_val == "PRO" and "pro" not in _tier:
                continue
            elif _filt_val == "ULTRA" and "ultra" not in _tier:
                continue
            elif _filt_val == "ÜCRETSİZ" and "pro" not in _tier and "ultra" not in _tier:
                continue
                
            _filtered.append(_a)

        # 2. Apply Pagination Slicing
        _total_filtered = len(_filtered)
        _total_pages = max(1, (_total_filtered + _state["per_page"] - 1) // _state["per_page"])
        
        if _state["page"] > _total_pages:
            _state["page"] = _total_pages
        if _state["page"] < 1:
            _state["page"] = 1

        _start_idx = (_state["page"] - 1) * _state["per_page"]
        _end_idx = _start_idx + _state["per_page"]
        _sliced = _filtered[_start_idx:_end_idx]

        # Top toolbar
        with ui.element("div").style("display:flex; align-items:center; gap:12px; margin-bottom:16px; flex-wrap:wrap; padding: 0 28px"):
            # Debounced search input (Prevents keypress lag!)
            def _on_search_change(e):
                _state["search"] = e.value
                _state["page"] = 1
                _body.refresh()

            ui.input(
                placeholder="Hesaplarda ara...",
                value=_state["search"],
                on_change=_on_search_change
            ).props("debounce=300").style("flex:1; min-width:200px; background:#161b22; color:#fff; border:1px solid #30363d; border-radius:6px; padding:4px 12px; font-size:12px")

            # Quick time filter placeholders
            with ui.row().style("gap:4px"):
                ui.button("5H", color="primary").props("flat dense").style("font-size:11px; background:#21262d; border:1px solid #30363d; color:#c9d1d9")
                ui.button("Weekly").props("flat dense").style("font-size:11px; color:#8b949e")

            # Tier selectors
            with ui.row().style("gap:6px; margin:0 8px"):
                _c_all = len(_accounts)
                _c_pro = sum(1 for x in _accounts if "pro" in (x.get("quota", {}).get("subscription_tier") or "").lower())
                _c_ult = sum(1 for x in _accounts if "ultra" in (x.get("quota", {}).get("subscription_tier") or "").lower())
                _c_fre = _c_all - _c_pro - _c_ult

                for name, count in [("Tümü", _c_all), ("PRO", _c_pro), ("ULTRA", _c_ult), ("ÜCRETSİZ", _c_fre)]:
                    _active = (_state["filter"] == name)
                    _bg = "background:#005cc5; color:#fff; border-color:#0366d6" if _active else "background:#21262d; color:#c9d1d9; border-color:#30363d"
                    def _set_filt(n=name):
                        _state["filter"] = n
                        _state["page"] = 1
                        _body.refresh()
                    ui.button(f"{name} {count}", on_click=lambda _n=name: _set_filt(_n)).props("flat dense").style(f"font-size:11px; border:1px solid #30363d; border-radius:6px; {_bg}")

            # Global actions
            ui.button("+", on_click=_add_dialog.open).props("flat dense").style("font-size:14px; background:#21262d; color:#58a6ff; border:1px solid #30363d; border-radius:6px; padding:4px 12px")
            ui.button("🔄", on_click=_trigger_fetch_accounts).props("flat dense").style("font-size:14px; background:#21262d; color:#fff; border:1px solid #30363d; border-radius:6px; padding:4px 12px")
            ui.button("⚡", on_click=_refresh_all_quotas).props("flat dense").style("font-size:14px; background:#f97316; color:#fff; border:1px solid #f97316; border-radius:6px; padding:4px 12px")
            ui.button("📂", on_click=_sync_from_db).props("flat dense").style("font-size:14px; background:#21262d; color:#fff; border:1px solid #30363d; border-radius:6px; padding:4px 12px")

        # Table container
        with ui.element("div").style("margin:0 28px 28px; background:#0d1117; border:1px solid #30363d; border-radius:8px; overflow:hidden"):
            ui.html("""
            <table style="width:100%; border-collapse:collapse; color:#c9d1d9; text-align:left">
              <thead>
                <tr style="border-bottom:1px solid #30363d; background:#161b22">
                  <th style="padding:12px; font-size:12px; font-weight:600; color:#8b949e; width:45px">::</th>
                  <th style="padding:12px; font-size:12px; font-weight:600; color:#8b949e; width:220px">E-POSTA</th>
                  <th style="padding:12px; font-size:12px; font-weight:600; color:#8b949e">MODEL KOTASI (KALAN SÜRE / DOLULUK)</th>
                  <th style="padding:12px; font-size:12px; font-weight:600; color:#8b949e; width:130px">SON KULLANIM</th>
                  <th style="padding:12px; font-size:12px; font-weight:600; color:#8b949e; text-align:right; width:220px">İŞLEMLER</th>
                </tr>
              </thead>
              <tbody id="ag-accounts-tbody">
            """)

            _rows = []
            for _a in _sliced:
                _aid = _a.get("id", "")
                _em = _a.get("email", "")
                _label = _a.get("label", "")
                _role = (_a.get("quota", {}).get("subscription_tier") or "free").upper()
                _is_proxy_off = not _a.get("proxy_enabled", True) or _a.get("proxy_disabled", False)
                _is_forbidden = _a.get("quota", {}).get("is_forbidden", False)
                
                _is_current = (_aid == _current_active_id)
                _current_badge = '<span style="display:inline-block; padding:1px 6px; border-radius:4px; font-size:9px; background:#005cc5; color:#fff; font-weight:bold; margin-right:4px">MEVCUT</span>' if _is_current else ""
                
                if _role == "ULTRA":
                    _role_class = "background:linear-gradient(to right, #7c3aed, #db2777); color:#fff; font-weight:bold"
                elif _role == "PRO":
                    _role_class = "background:linear-gradient(to right, #2563eb, #4f46e5); color:#fff; font-weight:bold"
                else:
                    _role_class = "background:rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.15); color:#8b949e"
                
                _proxy_badge = '<span style="display:inline-block; padding:1px 6px; border-radius:4px; font-size:9px; background:rgba(249,115,22,0.15); border:1px solid rgba(249,115,22,0.4); color:#f97316">Proxy Devre Dışı</span>' if _is_proxy_off else ""
                _forbidden_badge = '<span style="display:inline-block; padding:1px 6px; border-radius:4px; font-size:9px; background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4); color:#f87171">Yasaklı</span>' if _is_forbidden else ""
                _label_badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:4px; font-size:9px; background:rgba(88,166,255,0.1); border:1px solid rgba(88,166,255,0.25); color:#58a6ff">{_label}</span>' if _label else ""
                
                _models_list = _a.get("quota", {}).get("models", [])
                
                _quota_html_list = []
                for m_obj in _models_list:
                    m_name = m_obj.get("model_name", "Model")
                    _pct = m_obj.get("percentage", 100)
                    _color = "#ea3838" if _pct < 30 else ("#f97316" if _pct < 70 else "#00b074")
                    _time_left = m_obj.get("time_left") or m_obj.get("reset_time") or "N/A"
                    if "T" in _time_left:
                        try:
                            _time_left = _time_left.split("T")[1][:5]
                        except Exception:
                            pass
                    
                    _quota_html_list.append(f"""
                    <div style="position:relative; display:flex; align-items:center; justify-content:space-between; gap:10px; width:48%; background:rgba(255,255,255,0.03); padding:4px 8px; border-radius:6px; border:1px solid #30363d; overflow:hidden; margin-bottom:4px">
                      <div style="position:absolute; inset:0; right:auto; width:{_pct}%; background:{_color}; opacity:0.1; z-index:0"></div>
                      <span style="font-size:10px; color:#8b949e; font-family:Consolas,monospace; z-index:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80px">🤖 {m_name}</span>
                      <span style="font-size:10px; color:#8b949e; z-index:1">🕒 {_time_left}</span>
                      <span style="font-size:10px; font-weight:bold; color:{_color}; z-index:1">{_pct}%</span>
                    </div>
                    """)
                
                _quota_section = f'<div style="display:flex; flex-wrap:wrap; gap:4px; width:100%">' + "".join(_quota_html_list) + '</div>' if _quota_html_list else '<span style="color:#484f58; font-size:11px">Kota limiti tanımlı değil</span>'
                
                _last_used_val = _a.get("last_used") or 0
                _last_used_str = "-"
                if _last_used_val > 0:
                    try:
                        _last_used_str = _dt.datetime.fromtimestamp(_last_used_val).strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        pass
                
                _rows.append(f"""
                <tr style="border-bottom:1px solid #21262d; transition:background 0.15s" onmouseover="this.style.background='#161b22'" onmouseout="this.style.background='transparent'">
                  <td style="padding:12px; vertical-align:middle; color:#484f58; font-size:14px; cursor:grab">⠿</td>
                  <td style="padding:12px; vertical-align:middle">
                    <div style="font-weight:bold; font-size:13px; color:#c9d1d9">{_em}</div>
                    <div style="display:flex; align-items:center; margin-top:4px; gap:4px; flex-wrap:wrap">
                      {_current_badge}
                      <span style="display:inline-block; padding:1px 6px; border-radius:4px; font-size:9px; {_role_class}">{_role}</span>
                      {_proxy_badge}
                      {_forbidden_badge}
                      {_label_badge}
                    </div>
                  </td>
                  <td style="padding:12px; vertical-align:middle">{_quota_section}</td>
                  <td style="padding:12px; vertical-align:middle; font-size:11px; color:#8b949e; font-family:Consolas,monospace">{_last_used_str}</td>
                  <td style="padding:12px; vertical-align:middle; text-align:right">
                    <div style="display:inline-flex; gap:4px">
                      <button onclick="window.location.href='#'; ui_account_details('{_aid}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#8b949e; padding:4px 8px; font-size:11px; cursor:pointer" title="Detaylar">ℹ️</button>
                      <button onclick="window.location.href='#'; ui_account_fingerprint('{_aid}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#a855f7; padding:4px 8px; font-size:11px; cursor:pointer" title="Cihaz Parmak İzi">👣</button>
                      <button onclick="window.location.href='#'; ui_account_label('{_aid}', '{_label}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#eab308; padding:4px 8px; font-size:11px; cursor:pointer" title="Etiket Düzenle">🏷️</button>
                      <button onclick="window.location.href='#'; ui_account_switch('{_aid}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#58a6ff; padding:4px 8px; font-size:11px; cursor:pointer" title="Aktif Hesap Yap">⇄ Swap</button>
                      <button onclick="window.location.href='#'; ui_account_proxy_toggle('{_aid}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#fb923c; padding:4px 8px; font-size:11px; cursor:pointer" title="Proxy Aç/Kapat">🔌 Toggle</button>
                      <button onclick="window.location.href='#'; ui_account_quota_refresh('{_aid}')" style="background:#21262d; border:1px solid #30363d; border-radius:6px; color:#4ade80; padding:4px 8px; font-size:11px; cursor:pointer" title="Kotayı Yenile">🔄</button>
                      <button onclick="window.location.href='#'; ui_account_delete('{_aid}', '{_em}')" style="background:rgba(233,76,76,0.15); border:1px solid rgba(233,76,76,0.3); border-radius:6px; color:#ea3838; padding:4px 8px; font-size:11px; cursor:pointer" title="Hesabı Sil">🗑️</button>
                    </div>
                  </td>
                </tr>
                """)

            if _state.get("loading"):
                _tbody_content = (
                    '<tr><td colspan="5" style="padding:40px; text-align:center; color:#58a6ff; font-size:13px">'
                    '<div style="display:inline-block; width:14px; height:14px; border:2px solid #58a6ff; '
                    'border-top-color:transparent; border-radius:50%; animation:spin-loader 0.8s linear infinite; '
                    'margin-right:8px; vertical-align:middle"></div>'
                    '<style>@keyframes spin-loader { to { transform: rotate(360deg); } }</style>'
                    'Hesaplar yükleniyor...</td></tr>'
                )
            else:
                _tbody_content = "".join(_rows) if _rows else '<tr><td colspan="5" style="padding:40px; text-align:center; color:#8b949e; font-size:13px">Kayıtlı proxy hesabı bulunamadı.</td></tr>'
            ui.html(_tbody_content + "</tbody></table>")

            # Native hidden input to store selected account id/args securely
            ui.html('<input type="hidden" id="ag_target_acc_id" value="">')

            # JS event binding helper for list callbacks (Uses click signals for maximum reliability)
            ui.add_head_html("""
            <script>
                window.ui_account_details = function(accId) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_details");
                    if (inputEl && btnEl) {
                        inputEl.value = accId;
                        btnEl.click();
                    }
                };
                window.ui_account_fingerprint = function(accId) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_fingerprint");
                    if (inputEl && btnEl) {
                        inputEl.value = accId;
                        btnEl.click();
                    }
                };
                window.ui_account_label = function(accId, currentLabel) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_label");
                    if (inputEl && btnEl) {
                        inputEl.value = accId + "::" + currentLabel;
                        btnEl.click();
                    }
                };
                window.ui_account_switch = function(accId) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_switch");
                    if (inputEl && btnEl) {
                        inputEl.value = accId;
                        btnEl.click();
                    }
                };
                window.ui_account_proxy_toggle = function(accId) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_proxy_toggle");
                    if (inputEl && btnEl) {
                        inputEl.value = accId;
                        btnEl.click();
                    }
                };
                window.ui_account_quota_refresh = function(accId) {
                    var inputEl = document.getElementById("ag_target_acc_id");
                    var btnEl = document.getElementById("ag_btn_quota_refresh");
                    if (inputEl && btnEl) {
                        inputEl.value = accId;
                        btnEl.click();
                    }
                };
                window.ui_account_delete = function(accId, email) {
                    if (confirm(email + " hesabını silmek istediğinizden emin misiniz?")) {
                        var inputEl = document.getElementById("ag_target_acc_id");
                        var btnEl = document.getElementById("ag_btn_delete");
                        if (inputEl && btnEl) {
                            inputEl.value = accId;
                            btnEl.click();
                        }
                    }
                };
            </script>
            """)

            # Python Callbacks for action triggers
            async def _on_details_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _show_details(val)

            async def _on_fingerprint_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _show_fingerprint(val)

            async def _on_label_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val and "::" in val:
                    parts = val.split("::")
                    _update_label(parts[0], parts[1])

            async def _on_switch_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _switch_account(val)

            async def _on_proxy_toggle_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _toggle_proxy(val)

            async def _on_quota_refresh_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _refresh_single_quota(val)

            async def _on_delete_click():
                val = await ui.run_javascript('document.getElementById("ag_target_acc_id").value')
                if val: _delete_account(val, "Hesap")

            # Hidden NiceGUI buttons acting as clean API endpoints
            ui.button("Details", on_click=_on_details_click).style("display:none").props('id="ag_btn_details"')
            ui.button("Fingerprint", on_click=_on_fingerprint_click).style("display:none").props('id="ag_btn_fingerprint"')
            ui.button("Label", on_click=_on_label_click).style("display:none").props('id="ag_btn_label"')
            ui.button("Switch", on_click=_on_switch_click).style("display:none").props('id="ag_btn_switch"')
            ui.button("Proxy Toggle", on_click=_on_proxy_toggle_click).style("display:none").props('id="ag_btn_proxy_toggle"')
            ui.button("Quota Refresh", on_click=_on_quota_refresh_click).style("display:none").props('id="ag_btn_quota_refresh"')
            ui.button("Delete", on_click=_on_delete_click).style("display:none").props('id="ag_btn_delete"')

        # Pagination Footer (Fully Functional)
        with ui.element("div").style("display:flex; justify-content:space-between; align-items:center; padding: 12px 28px; font-size:12px; color:#8b949e"):
            ui.html(f"<div>{_total_filtered} kayıttan {_start_idx + 1} - {min(_end_idx, _total_filtered)} arası gösteriliyor</div>")
            
            with ui.row().style("align-items:center; gap:8px"):
                ui.html("<span>Sayfa başına</span>")
                def _change_per_page(e):
                    _state["per_page"] = int(e.value)
                    _state["page"] = 1
                    _body.refresh()
                ui.select({5: "5 öğe", 10: "10 öğe", 20: "20 öğe", 50: "50 öğe", 100: "100 öğe"}, value=_state["per_page"], on_change=_change_per_page).style("background:#161b22; color:#fff; border:1px solid #30363d; border-radius:4px; font-size:11px; padding:2px 6px")
            
            with ui.row().style("gap:4px; align-items:center"):
                def _prev_page():
                    if _state["page"] > 1:
                        _state["page"] -= 1
                        _body.refresh()
                def _next_page():
                    if _state["page"] < _total_pages:
                        _state["page"] += 1
                        _body.refresh()
                        
                _prev_dis = "opacity:0.4; cursor:not-allowed;" if _state["page"] <= 1 else "cursor:pointer;"
                _next_dis = "opacity:0.4; cursor:not-allowed;" if _state["page"] >= _total_pages else "cursor:pointer;"
                
                ui.button("<", on_click=_prev_page).props("flat dense").style(f"background:#21262d; border:1px solid #30363d; color:#c9d1d9; font-size:10px; {_prev_dis}")
                ui.html(f'<span style="padding:4px 8px; background:#005cc5; border-radius:4px; color:#fff; font-size:11px; font-weight:bold; font-family:monospace">{_state["page"]} / {_total_pages}</span>')
                ui.button(">", on_click=_next_page).props("flat dense").style(f"background:#21262d; border:1px solid #30363d; color:#c9d1d9; font-size:10px; {_next_dis}")

    # ── Sayfa başlığı ──
    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">👥 Hesaplar</div>')
        ui.html('<div class="ph-sub">Antigravity proxy hesaplarını yönet — ekle, sil, etiketle, değiştir</div>')

    # Init fetch
    _trigger_fetch_accounts()
    
    with ui.element("div").style("padding:20px 0 0"):
        _body()


