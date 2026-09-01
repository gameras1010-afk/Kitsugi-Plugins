"""
pages/datasources.py
====================
Veri kaynakları sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

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
