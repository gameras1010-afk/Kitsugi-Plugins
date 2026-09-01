"""
pages/theme.py
==============
Tema ve arkaplan ayarları.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

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
