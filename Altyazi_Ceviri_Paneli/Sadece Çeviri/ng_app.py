"""
ng_app.py — Ana uygulama: sidebar + ui.refreshable router + tema + ses
"""
import os, sys
from datetime import datetime
from nicegui import ui, app

_DIR = os.path.dirname(os.path.abspath(__file__))
_PARENT_DIR = os.path.dirname(_DIR)   # Python kodları/ — termbase_manager, fandom_glossary vb.

if _DIR not in sys.path:
    sys.path.insert(0, _DIR)
if _PARENT_DIR not in sys.path:
    sys.path.insert(0, _PARENT_DIR)

from ng_config  import C, api_counts, load_glossary, total_terms, load_prefs, save_prefs
from ng_styles  import CSS
from ng_pages_a import build_dashboard, build_translate, build_glossary, state, refresh_status
from ng_pages_b import build_settings, build_theme_page, build_about, build_reports, build_datasources, build_notifications, build_api_keys, build_accounts

# ── ui.notify → her zaman top-left ────────────────────────────────────────────
_orig_notify = ui.notify
def _notify(*args, **kwargs):
    kwargs.setdefault("position", "top-right")
    kwargs.setdefault("close_button", True)
    return _orig_notify(*args, **kwargs)
ui.notify = _notify


# ── Durum ─────────────────────────────────────────────────────────────────────
_prefs_init = load_prefs()
_page  = {"key": "dashboard"}
_theme = {"current": _prefs_init.get("ui_theme", "nexus")}
_sound = {"on":      _prefs_init.get("ui_sound", True)}

THEME_DEFS = {
    "nexus":    {"icon":"⬡","name":"Nexus",   "sub":"Cyberpunk · Mor & Cyan",   "g1":"#7c3aed","g2":"#00d4ff","g3":"#1e2035","badge":"rgba(124,58,237,0.35)","border":"#7c3aed"},
    "sakura":   {"icon":"✿","name":"Sakura",  "sub":"Anime · Pembe & Rose",     "g1":"#c026d3","g2":"#f472b6","g3":"#1e1228","badge":"rgba(192,38,211,0.35)","border":"#c026d3"},
    "cyber":    {"icon":"⊡","name":"Cyber",   "sub":"Matrix · Yeşil & Sarı",    "g1":"#00ff87","g2":"#facc15","g3":"#062e28","badge":"rgba(0,255,135,0.25)", "border":"#00ff87"},
    "midnight": {"icon":"◈","name":"Midnight","sub":"Koyu · Mavi & İndigo",     "g1":"#3b82f6","g2":"#6366f1","g3":"#0f172a","badge":"rgba(59,130,246,0.3)", "border":"#3b82f6"},
    "ember":    {"icon":"◆","name":"Ember",   "sub":"Ateş · Turuncu & Kırmızı","g1":"#f97316","g2":"#ef4444","g3":"#1c0a00","badge":"rgba(249,115,22,0.3)", "border":"#f97316"},
    "arctic":   {"icon":"❄","name":"Arctic",  "sub":"Buz · Beyaz & Gümüş",     "g1":"#e2e8f0","g2":"#94a3b8","g3":"#0f172a","badge":"rgba(226,232,240,0.2)","border":"#94a3b8"},
    "neontokyo": {"icon":"⚡","name":"Neon Tokyo", "sub":"Vaporwave · Pembe & Cyan",  "g1":"#ff0080","g2":"#00ffff","g3":"#0d0018","badge":"rgba(255,0,128,0.35)",  "border":"#ff0080"},
    "goldrush":  {"icon":"👑","name":"Gold Rush",  "sub":"Premium · Altın & Amber",  "g1":"#ffd700","g2":"#ff8c00","g3":"#1a1000","badge":"rgba(255,215,0,0.3)",   "border":"#ffd700"},
    "bloodmoon": {"icon":"🌑","name":"Blood Moon", "sub":"Gothic · Kızıl & Karanlık", "g1":"#dc143c","g2":"#8b0000","g3":"#1a0005","badge":"rgba(220,20,60,0.35)",  "border":"#dc143c"},
}

NAV = [
    ("dashboard",     "🏠", "Dashboard"),
    ("translate",     "🔄", "Translate"),
    ("glossary",      "📚", "Glossary"),
    ("accounts",      "👥", "Hesaplar"),
    ("datasources",   "🌐", "Veri Kaynakları"),
    ("reports",       "📄", "Raporlar & QA"),
    ("apikeys",       "🔑", "API Anahtarları"),
    ("theme",         "🎨", "Tema & Ses"),
    ("settings",      "⚙️", "Settings"),
    ("notifications", "🔔", "Bildirimler"),
    ("about",         "ℹ️", "Uygulama Hakkında"),
]

PAGE_BUILDERS = {
    "dashboard":     build_dashboard,
    "translate":     build_translate,
    "glossary":      build_glossary,
    "accounts":      build_accounts,
    "datasources":   build_datasources,
    "reports":       build_reports,
    "apikeys":       build_api_keys,
    "theme":         build_theme_page,
    "settings":      build_settings,
    "notifications": build_notifications,
    "about":         build_about,
}

_SOUNDS_JS = os.path.join(_DIR, "ng_sounds.js")

def _play(sound: str):
    ui.run_javascript(f"if(window.NexusSound) NexusSound.{sound}();")

def apply_theme_js(tid):
    td = THEME_DEFS[tid]
    return f"""
        document.documentElement.setAttribute('data-theme', '{tid}');
        localStorage.setItem('nexus_theme', '{tid}');
        document.documentElement.style.setProperty('--accent1',    '{td["g1"]}');
        document.documentElement.style.setProperty('--accent2',    '{td["g2"]}');
        document.documentElement.style.setProperty('--aurora1',    '{td["g1"]}33');
        document.documentElement.style.setProperty('--aurora2',    '{td["g2"]}22');
        if(window.nexusUpdateBtnGradient) nexusUpdateBtnGradient('{td["g1"]}', '{td["g2"]}');
        if(window.NexusSound) NexusSound.themeChange();
    """

# ── Arka plan resmi endpoint (base64 yok, doğrudan dosya serve) ───────────────
from fastapi.responses import FileResponse, Response as FResp

@app.get("/api/bgimage")
async def serve_bgimage():
    prefs = load_prefs()
    path  = prefs.get("bg_image_path", "")
    if path and os.path.exists(path):
        return FileResponse(path, headers={"Cache-Control": "no-store"})
    return FResp(status_code=404)

@app.get("/api/serve_report")
async def serve_report(path: str = ""):
    """HTML rapor dosyasını iframe için sun."""
    if not path:
        return FResp(status_code=400, content="path gerekli")

    real = os.path.realpath(path)

    # Güvenlik: izin verilen kök dizinler (proje + reports merkezi + sürücü kökü)
    from ng_config import PARENT_DIR as _PDIR, REPORTS_CENTRAL_DIR as _RCD
    _allowed_roots = []
    for _r in (_PDIR, _RCD):
        try:
            _rp = os.path.realpath(_r)
            # Windows: trailing sep yoksa ekle (C:\foo != C:\foobar karışmasın)
            if not _rp.endswith(os.sep):
                _rp += os.sep
            _allowed_roots.append(_rp)
        except Exception:
            pass

    # Dosya kendi başına .html ve var mı?
    if not os.path.isfile(real):
        return FResp(status_code=404, content="Dosya bulunamadi")
    if not real.lower().endswith(".html"):
        return FResp(status_code=403, content="Sadece HTML dosyalari")

    # İzin kontrolü: herhangi bir kök dizin altında mı?
    norm_real = real if real.endswith(os.sep) else (real + os.sep)
    ok = any(real.startswith(root) or (real + os.sep).startswith(root)
             for root in _allowed_roots)
    if not ok:
        # Son çare: Windows'ta büyük/küçük harf duyarsız karşılaştır
        ok = any(real.lower().startswith(root.lower()) for root in _allowed_roots)
    if not ok:
        return FResp(status_code=403, content="Yasak yol")

    return FileResponse(real, media_type="text/html",
                        headers={"Cache-Control": "no-store",
                                 "X-Frame-Options": "SAMEORIGIN"})

@ui.page("/")
def main_page():
    prefs = load_prefs()

    # Ses script
    if os.path.exists(_SOUNDS_JS):
        with open(_SOUNDS_JS, "r", encoding="utf-8") as f:
            ui.add_head_html(f"<script>{f.read()}</script>")

    ui.add_head_html(f"<style>{CSS}</style>")
    ui.add_head_html("""<style>
    body{font-family:'Inter','Segoe UI',system-ui,sans-serif!important}
    code,.drop-path{font-family:'JetBrains Mono','Consolas',monospace!important}

    /* ── Premium Scrollbar ──────────────────────────────────────── */
    ::-webkit-scrollbar{width:7px;height:7px}
    ::-webkit-scrollbar-track{
        background:rgba(255,255,255,.03);
        border-radius:4px;
        margin:4px;
    }
    ::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,var(--accent1),var(--accent2));
        border-radius:4px;
        border:1px solid rgba(0,0,0,.4);
        box-shadow:0 0 8px var(--accent1)44;
    }
    ::-webkit-scrollbar-thumb:hover{
        box-shadow:0 0 14px var(--accent1)88;
        filter:brightness(1.25);
    }
    ::-webkit-scrollbar-corner{background:transparent}

    @keyframes nxFadeIn{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
    @keyframes nxGlow{0%,100%{box-shadow:0 0 8px var(--accent1)44}50%{box-shadow:0 0 18px var(--accent1)88}}

    /* ── Top / Bottom Scroll Buttons ──────────────────────────── */
    #nx-btn-top,#nx-btn-bot{
        position:fixed;right:10px;z-index:99999;
        width:30px;height:30px;border-radius:10px;
        background:rgba(0,0,0,.55);
        backdrop-filter:blur(16px) saturate(1.8);
        -webkit-backdrop-filter:blur(16px) saturate(1.8);
        border:1px solid var(--accent1)66;
        box-shadow:0 2px 16px rgba(0,0,0,.5),0 0 10px var(--accent1)22;
        color:var(--accent1);font-size:13px;
        cursor:pointer;outline:none;
        display:flex;align-items:center;justify-content:center;
        transition:all .2s cubic-bezier(.4,0,.2,1);
        animation:nxFadeIn .3s ease;
    }
    #nx-btn-top{top:4px;}
    #nx-btn-bot{bottom:36px;}
    #nx-btn-top:hover,#nx-btn-bot:hover{
        background:linear-gradient(135deg,var(--accent1)44,var(--accent2)33);
        border-color:var(--accent1)cc;
        box-shadow:0 4px 24px rgba(0,0,0,.6),0 0 20px var(--accent1)55;
        transform:scale(1.1) translateY(-1px);
        color:#fff;
    }
    #nx-btn-top:active,#nx-btn-bot:active{transform:scale(.92)}


    /* ── Scrollbar-entegre ok butonları ─────────────────────────── */
    #nx-btn-top,#nx-btn-bot{
        right:0;width:22px;height:22px;border-radius:4px;
    }
    #nx-btn-top{top:0;}
    #nx-btn-bot{bottom:30px;}
    </style>""")
    # ── Quasar renk paletini tema ile eşleştir (butonlar v.s.) ──
    td_init = THEME_DEFS.get(_theme["current"], THEME_DEFS["nexus"])
    ui.colors(
        primary   = td_init["g1"],
        secondary = td_init["g2"],
        positive  = "#10b981",
        negative  = "#ef4444",
        info      = "#3b82f6",
        warning   = "#f59e0b",
    )

    # ── Buton stilini Quasar yüklendikten SONRA enjekte et ──
    # (Quasar kendi CSS'ini dinamik olarak enjekte ettiği için
    #  biz de onun SONRASINDA enjekte ediyoruz ki override çalışsın)
    ui.add_head_html(f"""<script>
    document.addEventListener('DOMContentLoaded', function() {{
        var s = document.createElement('style');
        s.id  = 'nexus-btn-override';
        s.innerHTML = `
            .q-btn .q-btn__wrapper {{
                background: linear-gradient(160deg,
                    color-mix(in srgb, var(--q-primary) 90%, white 10%) 0%,
                    var(--q-primary) 40%,
                    var(--q-secondary) 100%) !important;
                border-radius: 10px !important;
                position: relative !important;
                overflow: hidden !important;
            }}
            .q-btn .q-btn__wrapper::before {{
                content: '' !important;
                position: absolute !important;
                top: 0 !important; left: 0 !important; right: 0 !important;
                height: 40% !important;
                background: linear-gradient(180deg, rgba(255,255,255,0.22) 0%, transparent 100%) !important;
                border-radius: 10px 10px 0 0 !important;
                pointer-events: none !important;
            }}
            .q-btn {{
                border-radius: 10px !important;
                box-shadow:
                    0 4px 18px rgba(0,0,0,0.45),
                    0 1px 0 rgba(255,255,255,0.18) inset !important;
                font-weight: 700 !important;
                letter-spacing: 0.5px !important;
                text-shadow: 0 1px 3px rgba(0,0,0,0.5) !important;
                overflow: hidden !important;
                transition: all 0.22s cubic-bezier(.4,0,.2,1) !important;
                color: #fff !important;
            }}
            .q-btn:hover {{
                transform: translateY(-2px) !important;
                box-shadow:
                    0 8px 28px rgba(0,0,0,0.55),
                    0 0 20px color-mix(in srgb, var(--q-primary) 50%, transparent),
                    0 1px 0 rgba(255,255,255,0.2) inset !important;
            }}
            .q-btn:hover .q-btn__wrapper {{
                filter: brightness(1.12) !important;
            }}
            .q-btn:active {{
                transform: translateY(0) !important;
            }}
            .q-btn::before {{ box-shadow: none !important; }}
            .q-btn--flat .q-btn__wrapper,
            .q-btn--outline .q-btn__wrapper {{
                background: transparent !important;
            }}
            .q-btn--flat, .q-btn--outline {{ box-shadow: none !important; }}
        `;
        document.head.appendChild(s);

        if(window.Quasar) {{
            Quasar.setCssVar('primary',   '{td_init["g1"]}');
            Quasar.setCssVar('secondary', '{td_init["g2"]}');
        }}
    }});

    window.nexusUpdateBtnGradient = function(g1, g2) {{
        if(window.Quasar) {{
            Quasar.setCssVar('primary',   g1);
            Quasar.setCssVar('secondary', g2);
        }}
        document.documentElement.style.setProperty('--q-primary',   g1);
        document.documentElement.style.setProperty('--q-secondary', g2);
    }};
    </script>""")

    prefs2     = load_prefs()          # fresh read
    bg_enabled = prefs2.get("bg_enabled",    False)
    bg_blur    = prefs2.get("bg_blur",       0)
    bg_dark    = prefs2.get("bg_dark",       0.55)
    bg_path    = prefs2.get("bg_image_path", "")
    bg_ok      = bg_enabled and bool(bg_path) and os.path.exists(bg_path)

    ui.add_head_html(f"""<script>
    (function(){{
        // OTOMATIK URETILDI — THEME_DEFS ile eslesir
        var themes = {{
            nexus:     {{a1:'#7c3aed',a2:'#00d4ff',au1:'rgba(124,58,237,0.30)',au2:'rgba(0,212,255,0.20)'}},
            sakura:    {{a1:'#c026d3',a2:'#f472b6',au1:'rgba(192,38,211,0.32)',au2:'rgba(244,114,182,0.22)'}},
            cyber:     {{a1:'#00ff87',a2:'#facc15',au1:'rgba(0,255,135,0.25)',au2:'rgba(250,204,21,0.18)'}},
            midnight:  {{a1:'#3b82f6',a2:'#6366f1',au1:'rgba(59,130,246,0.30)',au2:'rgba(99,102,241,0.22)'}},
            ember:     {{a1:'#f97316',a2:'#ef4444',au1:'rgba(249,115,22,0.30)',au2:'rgba(239,68,68,0.22)'}},
            arctic:    {{a1:'#e2e8f0',a2:'#94a3b8',au1:'rgba(226,232,240,0.18)',au2:'rgba(148,163,184,0.14)'}},
            neontokyo: {{a1:'#ff0080',a2:'#00ffff',au1:'rgba(255,0,128,0.30)',  au2:'rgba(0,255,255,0.20)'}},
            goldrush:  {{a1:'#ffd700',a2:'#ff8c00',au1:'rgba(255,215,0,0.28)',  au2:'rgba(255,140,0,0.20)'}},
            bloodmoon: {{a1:'#dc143c',a2:'#8b0000',au1:'rgba(220,20,60,0.32)',  au2:'rgba(139,0,0,0.20)'}}
        }};
        var t = localStorage.getItem('nexus_theme') || '{_theme["current"]}';
        document.documentElement.setAttribute('data-theme', t);
        var td = themes[t];
        if(td) {{
            document.documentElement.style.setProperty('--accent1',    td.a1);
            document.documentElement.style.setProperty('--accent2',    td.a2);
            document.documentElement.style.setProperty('--aurora1',    td.au1);
            document.documentElement.style.setProperty('--aurora2',    td.au2);
            document.documentElement.style.setProperty('--q-primary',  td.a1);
            document.documentElement.style.setProperty('--q-secondary',td.a2);
        }}

        // Arka plan resmi — URL ile (base64 yok, performanslı)
        window.__nexusBgEnabled = {'true' if bg_ok else 'false'};
        window.__nexusBgBlur    = {bg_blur};
        window.__nexusBgDark    = {bg_dark};

        window.applyBgSettings = function(imgUrl, blur, dark, enabled) {{
            var layer   = document.getElementById('bg-image-layer');
            var overlay = document.getElementById('bg-dark-overlay');
            if(!layer) return;
            if(enabled && imgUrl) {{
                // Body bg'yi şeffaf yap — katman görünsün
                document.body.style.backgroundColor = 'transparent';
                document.documentElement.style.backgroundColor = 'transparent';
                layer.style.backgroundImage = 'url(' + imgUrl + ')';
                layer.style.filter          = 'blur(' + blur + 'px)';
                var m = Math.ceil(blur) * 2 + 10;
                layer.style.top    = '-' + m + 'px';
                layer.style.left   = '-' + m + 'px';
                layer.style.right  = '-' + m + 'px';
                layer.style.bottom = '-' + m + 'px';
                layer.style.display = 'block';
                if(overlay) {{
                    overlay.style.background = 'rgba(0,0,0,' + dark + ')';
                    overlay.style.display    = 'block';
                }}
            }} else {{
                document.body.style.backgroundColor = '';
                document.documentElement.style.backgroundColor = '';
                layer.style.display = 'none';
                if(overlay) overlay.style.background = 'rgba(0,0,0,0)';
            }}
        }};

        document.addEventListener('DOMContentLoaded', function() {{
            if(window.__nexusBgEnabled) {{
                applyBgSettings('/api/bgimage?t=' + Date.now(),
                                window.__nexusBgBlur,
                                window.__nexusBgDark, true);
            }}
        }});
    }})();
    </script>""")


    # ── Arka plan katmanları (en alt z-index) ──
    ui.add_body_html("""<div id="bg-image-layer" style="
        display:none;position:fixed;top:0;left:0;right:0;bottom:0;z-index:1;
        background-size:cover;background-position:center;background-repeat:no-repeat;
        transition:filter 0.4s ease;
    "></div>
    <div id="bg-dark-overlay" style="
        display:block;position:fixed;inset:0;z-index:2;pointer-events:none;
        background:rgba(0,0,0,0);transition:background 0.4s ease;
    "></div>""")
    ui.add_body_html("""<button id="nx-sb-toggle" onclick="nxSidebarToggle()" title="Sidebar (Ctrl+B)">&#9664;</button>""")

    # ── Floating Nav: ⬆ (sağ üst) + A-Z strip (sağ orta) + ⬇ (sağ alt) ───────
    ui.add_body_html("""
    <button id="nx-btn-top" onclick="nxScrollTop()" title="Sayfanın Başına Git">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="18 15 12 9 6 15"></polyline>
        </svg>
    </button>

    <button id="nx-btn-bot" onclick="nxScrollBot()" title="Sayfanın Sonuna Git">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
    </button>
    """)

    ui.add_head_html("""
    <script>
    (function(){
        function getScroller(){
            return document.getElementById('nx-main-scroll') || document.documentElement;
        }
        window.nxScrollTop = function(){
            getScroller().scrollTo({top:0, behavior:'smooth'});
        };
        window.nxScrollBot = function(){
            var s = getScroller();
            s.scrollTo({top:s.scrollHeight, behavior:'smooth'});
        };

        // ── Alphabet Strip ────────────────────────────────────────────
        window.nxBuildAlphaNav = function(){
            var strip = document.getElementById('nx-alpha-strip');
            if(!strip) return;
            strip.innerHTML = '';

            var els = document.querySelectorAll('[data-nx-series]');
            if(els.length === 0){ strip.classList.remove('visible'); return; }

            // Mevcut harfleri topla
            var letterMap = {};
            els.forEach(function(el){
                var name = el.getAttribute('data-nx-series') || '';
                var L = name.trim()[0];
                if(!L) return;
                L = L.toUpperCase();
                if(!letterMap[L]) letterMap[L] = el;
            });

            // Sadece var olan harfleri göster
            var letters = Object.keys(letterMap).sort();
            letters.forEach(function(L, idx){
                if(idx > 0){
                    var sep = document.createElement('div');
                    sep.className = 'nx-al-sep';
                    strip.appendChild(sep);
                }
                var btn = document.createElement('button');
                btn.className = 'nx-al';
                btn.textContent = L;
                btn.title = letterMap[L].getAttribute('data-nx-series');
                btn.onclick = function(){
                    letterMap[L].scrollIntoView({behavior:'smooth', block:'start'});
                };
                strip.appendChild(btn);
            });

            strip.classList.add('visible');
        };

        window.nxClearAlphaNav = function(){
            var strip = document.getElementById('nx-alpha-strip');
            if(strip){ strip.innerHTML = ''; strip.classList.remove('visible'); }
        };


        // ── Term Filtre (Glossary) ────────────────────────────────────────
        window._nxTabState = {};
        window.nxTermFilter = function(q){
            q = q.trim().toLowerCase();
            var rc = document.getElementById('nx-ts-rc');
            if(!q){
                document.querySelectorAll('.nx-detail-div').forEach(function(dd){
                    if(!dd.getAttribute('data-was-open')) dd.style.display='none';
                });
                document.querySelectorAll('[data-nxtab-prefix]').forEach(function(card){
                    var prefix = card.getAttribute('data-nxtab-prefix');
                    var saved  = window._nxTabState[prefix];
                    var all    = document.querySelectorAll('[data-nxtab-prefix="'+prefix+'"]');
                    var first  = true;
                    all.forEach(function(c){
                        c.style.display = saved ? (c.id===saved?'block':'none') : (first?'block':'none');
                        first = false;
                    });
                });
                document.querySelectorAll('.nx-term-row').forEach(function(r){ r.style.display=''; });
                if(rc) rc.style.display='none';
                return;
            }
            // Tab state kaydet
            document.querySelectorAll('[data-nxtab-chip-prefix]').forEach(function(b){
                if(b.hasAttribute('data-active')){
                    var p=b.getAttribute('data-nxtab-chip-prefix');
                    if(!window._nxTabState[p])
                        window._nxTabState[p]='nxcat_'+p+'_'+b.getAttribute('data-nxtab-cat');
                }
            });
            // Tüm accordion'ları aç
            document.querySelectorAll('.nx-detail-div').forEach(function(dd){
                dd.setAttribute('data-was-open', dd.style.display!=='none'?'1':'');
                dd.style.display='block';
            });
            // Tüm kategori kartlarını göster
            document.querySelectorAll('[data-nxtab-prefix]').forEach(function(c){ c.style.display='block'; });
            // Filtrele
            var total=0,visible=0;
            document.querySelectorAll('.nx-term-row').forEach(function(r){
                total++;
                if((r.getAttribute('data-term')||'').toLowerCase().indexOf(q)!==-1){
                    r.style.display='';visible++;
                } else { r.style.display='none'; }
            });
            if(rc){ rc.textContent=visible+'/'+total; rc.style.display='block'; }
        };

        // ── Category Tab Switch ────────────────────────────────────────
        window.nxTabSwitch = function(prefix, catId){
            // id prefix pattern ile tüm kartları gizle
            document.querySelectorAll('[id^="nxcat_'+prefix+'_"]').forEach(function(el){
                el.style.display = 'none';
            });
            // Seçilen kartı göster
            var target = document.getElementById('nxcat_'+prefix+'_'+catId);
            if(target) target.style.display = 'block';
            // Chip stillerini güncelle (inline style + data-active)
            document.querySelectorAll('[data-nxtab-chip-prefix]').forEach(function(b){
                if(b.getAttribute('data-nxtab-chip-prefix') !== prefix) return;
                var clr = b.getAttribute('data-color') || '#a78bfa';
                b.removeAttribute('data-active');
                b.style.background = clr+'0d';
                b.style.borderColor = clr+'28';
                b.style.opacity    = '0.7';
                b.style.boxShadow  = 'none';
            });
            var chip = document.querySelector(
                '[data-nxtab-chip-prefix="'+prefix+'"][data-nxtab-cat="'+catId+'"]'
            );
            if(chip){
                var clr = chip.getAttribute('data-color') || '#a78bfa';
                chip.setAttribute('data-active','1');
                chip.style.background  = clr+'40';
                chip.style.borderColor = clr+'99';
                chip.style.opacity     = '1';
                chip.style.boxShadow   = '0 0 12px '+clr+'33';
            }
        };

        // ── Event Delegation: chip tıklamaları ────────────────────────
        document.addEventListener('click', function(e){
            var btn = e.target.closest('[data-nxtab-chip-prefix]');
            if(!btn) return;
            var prefix = btn.getAttribute('data-nxtab-chip-prefix');
            var catId  = btn.getAttribute('data-nxtab-cat');
            if(prefix && catId) window.nxTabSwitch(prefix, catId);
        }, true);
    })();
    </script>
    """)



    ui.add_head_html("""<script>
    (function() {
        // 'mini' = sadece ikonlar (60px) | 'full' = tam acik (220px)
        var NX_SB_MODE = localStorage.getItem('nx_sidebar') || 'full';

        window.nxApplySidebar = function(mode) {
            var sb  = document.querySelector('.sidebar');
            var btn = document.getElementById('nx-sb-toggle');
            if (!sb || !btn) return;
            if (mode === 'mini') {
                sb.classList.add('nx-mini');
                btn.classList.add('nx-sb-mini');
                btn.innerHTML = '&#9654;';  // ▶ genislet
                btn.title = "Sidebar'i Genislet (Ctrl+B)";
            } else {
                sb.classList.remove('nx-mini');
                btn.classList.remove('nx-sb-mini');
                btn.innerHTML = '&#9664;';  // ◀ daralt
                btn.title = "Sidebar'i Daralt (Ctrl+B)";
            }
        };

        window.nxSidebarToggle = function() {
            NX_SB_MODE = (NX_SB_MODE === 'mini') ? 'full' : 'mini';
            localStorage.setItem('nx_sidebar', NX_SB_MODE);
            nxApplySidebar(NX_SB_MODE);
            if (window.NexusSound) NexusSound.notify();
        };

        // Baslangic durumunu uygula
        function initSidebar() {
            var sb = document.querySelector('.sidebar');
            if (!sb) { setTimeout(initSidebar, 80); return; }
            nxApplySidebar(NX_SB_MODE);
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() { setTimeout(initSidebar, 100); });
        } else {
            setTimeout(initSidebar, 100);
        }

        // Klavye kisayolu: Ctrl+B
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                window.nxSidebarToggle();
            }
        });
    })();
    </script>""")


    with ui.element("div").style(
        "display:flex;width:100vw;height:100vh;overflow:hidden;"
        "position:relative;z-index:10"
    ):
        _sidebar()
        with ui.element("div").style(
            "flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden;"
            "position:relative;z-index:10"
        ):
            with ui.element("div").style("flex:1;overflow-y:auto;position:relative;z-index:10").props('id="nx-main-scroll"'):
                _content()
            _statusbar()


@ui.refreshable
def _content():
    with ui.element("div").classes("page-container animate-in"):
        PAGE_BUILDERS.get(_page["key"], build_dashboard)()

@ui.refreshable
def _sidebar():
    # [FIX] state'e refresh referansını yaz — ng_pages_a._refresh_stats bunu kullanır
    state["_sidebar_refresh"] = _sidebar.refresh
    api_ok, api_ex = api_counts()
    g   = load_glossary()
    nt  = total_terms(g)
    cur = _page["key"]
    snd = _sound["on"]
    # Her zaman diskten oku — save_prefs sonrası kesinlikle doğru değer
    _prefs_fresh = load_prefs()
    thm = _prefs_fresh.get("ui_theme", "nexus")
    _theme["current"] = thm   # in-memory dict'i de senkronize et
    td_cur = THEME_DEFS.get(thm, THEME_DEFS["nexus"])

    with ui.element("div").classes("sidebar"):

        # ── Logo ──
        ui.html(f"""
        <div class="sidebar-logo">
          <div class="logo-badge">NEXUS PRO</div>
          <div id="sidebar-logo-text" class="logo-title-gradient">
            Altyaz&#305;<br>&#199;evirici
          </div>
          <div class="logo-sub">AI Subtitle Engine &middot; v3.0</div>
        </div>""")

        # ── Navigasyon ──
        with ui.element("div").classes("nav-section"):
            ui.html('<div class="nav-section-label">NAV&#304;GASYON</div>')
            for key, icon, name in NAV:
                is_active = (key == cur)
                extra = ""
                if key == "glossary" and len(g):
                    extra = f'<span class="nav-pill">{len(g)}</span>'
                def on_nav(k=key):
                    old = _page["key"]
                    _page["key"] = k
                    # Sidebar refresh YOK — sadece JS ile aktif class guncelle
                    ui.run_javascript(
                        "document.querySelectorAll('.nav-btn').forEach(function(b){ b.classList.remove('active'); });"
                        f"var _nb=document.getElementById('nav-btn-{k}'); if(_nb) _nb.classList.add('active');"
                    )
                    # Glossary dışına geçince A-Z strip'i gizle
                    if k != "glossary":
                        ui.run_javascript("if(window.nxClearAlphaNav) nxClearAlphaNav();")
                    _content.refresh()
                    if k != old:
                        _play("pageTransition")
                btn = ui.element("button").classes(
                    f"nav-btn {'active' if is_active else ''}"
                ).props(f'id="nav-btn-{key}"').on("click", on_nav)
                with btn:
                    ui.html(f'<span class="nav-icon">{icon}</span>')
                    ui.html(f'<span class="nx-nav-text" style="flex:1">{name}</span>')
                    if extra:
                        ui.html(extra)

        # Kücük sabit bosluk
        ui.element("div").style("min-height:10px;max-height:10px")

        # ── Aktif Tema ──────────────────────────────────────────────────────
        def go_theme():
            _page["key"] = "theme"
            _sidebar.refresh()
            _content.refresh()
            ui.run_javascript("setTimeout(function(){ if(window.nxApplySidebar) nxApplySidebar(localStorage.getItem('nx_sidebar')||'full'); }, 80);")
            _play("pageTransition")

        # Full mod: mevcut kart
        ui.html(f'<div class="nx-mini-hide" style="padding:4px 14px 4px;font-size:9px;font-weight:700;letter-spacing:2px;color:var(--muted);text-transform:uppercase">AKT&#304;F TEMA</div>')
        with ui.element("div").classes("nx-mini-hide").style("padding:0 10px 8px"):
            with ui.element("div").style(
                f"border-radius:10px;overflow:hidden;cursor:pointer;"
                f"border:1px solid {td_cur['border']};"
                f"box-shadow:0 0 12px {td_cur['badge']};transition:all 0.25s"
            ).props('id="active-theme-badge"').on("click", go_theme):
                ui.html(
                    f'<div id="active-theme-gradient" style="height:14px;background:linear-gradient(135deg,{td_cur["g1"]},{td_cur["g2"]})"></div>'
                    f'<div id="active-theme-bg" style="padding:7px 10px;background:{td_cur["g3"]};display:flex;align-items:center;gap:8px">'
                    f'<span id="active-theme-icon" style="font-size:15px">{td_cur["icon"]}</span>'
                    f'<div><div id="active-theme-name" style="font-size:11px;font-weight:700;color:#e2e8f0">{td_cur["name"]}</div>'
                    f'<div style="font-size:9px;color:#4a4f7a">Tema &amp; Ses &rarr;</div></div>'
                    f'</div>'
                )

        # Mini mod: kompakt gradient buton — ikon + kısa isim
        with ui.element("div").classes("nx-mini-only").style(
            "display:none;flex-direction:column;align-items:center;"
            "padding:6px 0 10px;gap:0"
        ).on("click", go_theme):
            ui.html(
                f'<div title="Tema: {td_cur["name"]}" style="'
                f'width:40px;height:40px;border-radius:12px;cursor:pointer;'
                f'background:linear-gradient(135deg,{td_cur["g1"]},{td_cur["g2"]});'
                f'display:flex;align-items:center;justify-content:center;'
                f'font-size:18px;'
                f'box-shadow:0 0 14px {td_cur["badge"]},0 2px 8px rgba(0,0,0,0.5);'
                f'border:2px solid {td_cur["border"]};'
                f'transition:all 0.25s;position:relative;overflow:hidden">'
                f'<span style="position:relative;z-index:1;filter:drop-shadow(0 1px 3px rgba(0,0,0,0.6))">{td_cur["icon"]}</span>'
                f'</div>'
            )


        # ── Sistem Durumu ──
        ui.html(f"""
        <div class="sidebar-footer">
          <div style="font-size:9px;font-weight:700;letter-spacing:1.5px;
               color:var(--muted);text-transform:uppercase;margin-bottom:8px">
            S&#304;STEM DURUMU
          </div>
          <div class="api-stat">
            <span class="api-dot" style="background:var(--green)"></span>
            {api_ok} aktif API anahtar&#305;
          </div>
          <div class="api-stat">
            <span class="api-dot" style="background:var(--red)"></span>
            {api_ex} t&#252;kenmi&#351; anahtar
          </div>
          <div class="api-stat">
            <span class="api-dot" style="background:var(--accent2)"></span>
            {nt} s&#246;zl&#252;k terimi
          </div>
          <div style="font-size:9px;color:var(--muted);margin-top:8px;font-family:Consolas,monospace">
            NiceGUI {__import__("nicegui").__version__} &middot; Python {sys.version[:6]}
          </div>
        </div>""")

    # ── Sidebar yeniden render edilince mini modu koru ─────────────────────
    # setTimeout ile DOM tamamen render olduktan sonra modu uygula
    ui.run_javascript(
        "setTimeout(function(){"
        "  if(window.nxApplySidebar) nxApplySidebar(localStorage.getItem('nx_sidebar')||'full');"
        "}, 80);"
    )


def _statusbar():
    api_ok, _ = api_counts()
    g = load_glossary()
    nt = total_terms(g)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    with ui.element("div").classes("status-bar"):
        ui.html('<span class="status-dot"></span>')
        ui.html(f'<span style="color:var(--green)">Sistem Haz&#305;r</span>')
        ui.html('<span class="status-sep"></span>')
        ui.html(f'<span>&#128273; {api_ok} aktif anahtar</span>')
        ui.html('<span class="status-sep"></span>')
        # Reaktif terim sayacı — her sayfada güncel değer görünsün
        _term_lbl = ui.html(f'<span>&#128218; {nt} terim</span>')
        state["_status_term_lbl"] = _term_lbl   # diğer sayfalar güncelleyebilsin
        ui.html(
            f'<span id="nx-clock" style="margin-left:auto;font-family:Consolas,monospace;font-size:11px">'
            f'{now}</span>'
        )
        # Canlı saat — her saniye güncelle
        ui.run_javascript("""
            if(!window._nxClockStarted) {
                window._nxClockStarted = true;
                setInterval(function() {
                    var el = document.getElementById('nx-clock');
                    if(el) {
                        var d = new Date();
                        var pad = function(n){ return n<10?'0'+n:n; };
                        el.textContent = pad(d.getDate())+'.'+pad(d.getMonth()+1)+'.'+d.getFullYear()+
                                         ' '+pad(d.getHours())+':'+pad(d.getMinutes());
                    }
                }, 1000);
            }
        """)


if __name__ == "__main__":

    # ── Temiz Kapatma: pencere/tarayıcı kapandığında TÜM arka plan temizle ──
    import signal as _sig, sys as _sys_ng

    def _clean_shutdown():
        """
        NiceGUI native penceresi kapatılınca çağrılır.
        Tüm arka plan süreçleri ve thread'ler temizlenir.
        """
        import subprocess as _sp_ng, os as _os_ng
        # 1. Çeviri süreçlerini öldür (ng_pages_a.py: state["proc"] key'i kullanır)
        try:
            from ng_pages_a import state as _st_ng
            # ng_pages_a.py state["proc"] key'ine kaydeder — bunu oku
            _sub = _st_ng.get("proc")
            if _sub and hasattr(_sub, "pid") and hasattr(_sub, "poll"):
                if _sub.poll() is None:   # hala çalışıyor mu?
                    try:
                        _sp_ng.run(
                            ["taskkill", "/F", "/PID", str(_sub.pid), "/T"],
                            stdout=_sp_ng.DEVNULL, stderr=_sp_ng.DEVNULL, timeout=3
                        )
                    except Exception:
                        try: _sub.kill()
                        except Exception: pass
                _st_ng["proc"] = None   # state'i temizle
        except Exception:
            pass

        # 2. Medya araçlarını temizle
        for _tool in ["ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe", "chromedriver.exe"]:
            try:
                _sp_ng.run(
                    ["taskkill", "/F", "/IM", _tool, "/T"],
                    stdout=_sp_ng.DEVNULL, stderr=_sp_ng.DEVNULL,
                    timeout=2,
                    creationflags=0x08000000  # CREATE_NO_WINDOW
                )
            except Exception:
                pass

        # 3. Python prosesini tamamen kapat (daemon thread'ler de ölür)
        _sys_ng.exit(0)

    app.on_shutdown(_clean_shutdown)

    # SIGINT / SIGTERM sinyallerinde de temiz kapat
    def _sig_handler(signum, frame):
        _clean_shutdown()
    try:
        _sig.signal(_sig.SIGINT,  _sig_handler)
        _sig.signal(_sig.SIGTERM, _sig_handler)
    except Exception:
        pass

    ui.run(
        native      = True,
        window_size = (1300, 840),
        title       = "Altyazi Ceviri Paneli",
        reload      = False,
        port        = 8765,
        show        = False,
        dark        = True,
        favicon     = "🎌",
    )
