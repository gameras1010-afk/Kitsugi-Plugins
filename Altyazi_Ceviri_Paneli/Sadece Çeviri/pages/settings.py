"""
pages/settings.py
=================
Ayarlar sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, state, nbtn

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


