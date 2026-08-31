"""ng_styles.py — Premium CSS: glassmorphism, aurora, 3D, ses, 3 tema"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Tema değişkenleri ── */
:root {
    --bg:#0D0E15; --sidebar:#12131f; --panel:#1a1b2e; --card:#1e2035;
    --border:#2a2b4a; --purple:#7c3aed; --purple2:#9d5ff5;
    --cyan:#00d4ff; --cyan2:#64ffda; --green:#10b981;
    --red:#ef4444; --yellow:#f59e0b; --pink:#ec4899;
    --text:#f0f4ff; --sub:#dde3f5; --muted:#bec8e8;
    --glass:rgba(255,255,255,0.04);
    --glow-p:0 0 24px rgba(124,58,237,0.5);
    --glow-c:0 0 24px color-mix(in srgb,var(--accent2) 50%,transparent);
    --accent1:#7c3aed; --accent2:#00d4ff;
    --aurora1:rgba(124,58,237,0.30); --aurora2:rgba(0,212,255,0.20);
}
[data-theme="sakura"] {
    --bg:#0f0a14; --sidebar:#160d1c; --panel:#1e1228; --card:#231530;
    --border:#3a1f4a; --purple:#c026d3; --purple2:#e879f9;
    --cyan:#f472b6; --cyan2:#fda4af; --green:#86efac;
    --accent1:#c026d3; --accent2:#f472b6;
    --aurora1:rgba(192,38,211,0.32); --aurora2:rgba(244,114,182,0.22);
}
[data-theme="cyber"] {
    --bg:#020b0a; --sidebar:#021a16; --panel:#042520; --card:#062e28;
    --border:#0d4a3a; --purple:#00ff87; --purple2:#34d399;
    --cyan:#facc15; --cyan2:#fde68a; --green:#00ff87;
    --accent1:#00ff87; --accent2:#facc15;
    --aurora1:rgba(0,255,135,0.25); --aurora2:rgba(250,204,21,0.18);
}
[data-theme="midnight"] {
    --bg:#070c18; --sidebar:#0a1020; --panel:#0f1628; --card:#141e35;
    --border:#1e3060; --purple:#3b82f6; --purple2:#6366f1;
    --cyan:#818cf8; --cyan2:#a5b4fc; --green:#34d399;
    --accent1:#3b82f6; --accent2:#6366f1;
    --aurora1:rgba(59,130,246,0.30); --aurora2:rgba(99,102,241,0.22);
}
[data-theme="ember"] {
    --bg:#120700; --sidebar:#1c0a00; --panel:#250f02; --card:#2e1505;
    --border:#5c2a0a; --purple:#f97316; --purple2:#fb923c;
    --cyan:#ef4444; --cyan2:#fca5a5; --green:#fbbf24;
    --accent1:#f97316; --accent2:#ef4444;
    --aurora1:rgba(249,115,22,0.30); --aurora2:rgba(239,68,68,0.22);
}
[data-theme="arctic"] {
    --bg:#0a0e1a; --sidebar:#0d1220; --panel:#121828; --card:#171f30;
    --border:#2a3a5a; --purple:#e2e8f0; --purple2:#cbd5e1;
    --cyan:#94a3b8; --cyan2:#cbd5e1; --green:#34d399;
    --accent1:#e2e8f0; --accent2:#94a3b8;
    --aurora1:rgba(226,232,240,0.18); --aurora2:rgba(148,163,184,0.14);
}
[data-theme="neontokyo"] {
    --bg:#0d0018; --sidebar:#130020; --panel:#1a0030; --card:#200040;
    --border:#3a0060; --purple:#ff0080; --purple2:#ff66b2;
    --cyan:#00ffff; --cyan2:#80ffff; --green:#00ff87;
    --red:#ff0080; --yellow:#ffff00;
    --accent1:#ff0080; --accent2:#00ffff;
    --aurora1:rgba(255,0,128,0.30); --aurora2:rgba(0,255,255,0.20);
}
[data-theme="goldrush"] {
    --bg:#1a1000; --sidebar:#201400; --panel:#2a1c00; --card:#332400;
    --border:#5a3c00; --purple:#ffd700; --purple2:#ffe566;
    --cyan:#ff8c00; --cyan2:#ffb347; --green:#ffd700;
    --red:#ef4444; --yellow:#ffd700;
    --accent1:#ffd700; --accent2:#ff8c00;
    --aurora1:rgba(255,215,0,0.28); --aurora2:rgba(255,140,0,0.20);
}
[data-theme="bloodmoon"] {
    --bg:#1a0005; --sidebar:#200008; --panel:#2a000c; --card:#340010;
    --border:#5c0018; --purple:#dc143c; --purple2:#ff4466;
    --cyan:#8b0000; --cyan2:#cc0000; --green:#10b981;
    --red:#dc143c; --yellow:#f59e0b;
    --accent1:#dc143c; --accent2:#8b0000;
    --aurora1:rgba(220,20,60,0.32); --aurora2:rgba(139,0,0,0.20);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--text);overflow:hidden}

/* ── Aurora animasyonlu arka plan ── */
body::before {
    content:'';position:fixed;inset:0;z-index:3;pointer-events:none;
    background:
        radial-gradient(ellipse 90% 70% at 15% -10%, var(--aurora1), transparent 55%),
        radial-gradient(ellipse 70% 55% at 85% 110%, var(--aurora2), transparent 55%),
        radial-gradient(ellipse 50% 40% at 50% 50%, var(--aurora1), transparent 70%);
    animation:aurora 10s ease-in-out infinite alternate;
    transition:background 0.8s ease;
}
@keyframes aurora {
    0%  {transform:scale(1)    rotate(0deg);  opacity:1}
    33% {transform:scale(1.06) rotate(1deg);  opacity:0.9}
    66% {transform:scale(0.97) rotate(-1deg); opacity:0.95}
    100%{transform:scale(1.04) rotate(2deg);  opacity:0.85}
}

/* ── Particle/scan overlay ── */
body::after {
    content:'';position:fixed;inset:0;z-index:4;pointer-events:none;
    background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(255,255,255,0.012) 2px,rgba(255,255,255,0.012) 4px);
}

/* ── Z-index katmanı ── */
/* bg-image-layer:1, bg-dark-overlay:2, aurora/scan:3-4, content:10 */
.sidebar,.main-content,.status-bar,.page-topbar{position:relative;z-index:10}

/* ── Scrollbar ── */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
::-webkit-scrollbar-thumb:hover{background:var(--accent1)}

/* ── Sidebar ── */
.sidebar {
    width:220px;min-width:220px;height:100vh;
    background:rgba(0,0,0,0.35);
    backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
    border-right:1px solid rgba(255,255,255,0.10);
    display:flex;flex-direction:column;overflow:hidden;
    box-shadow:4px 0 30px rgba(0,0,0,0.25);
    /* Collapse animasyonu */
    transition:width 0.32s cubic-bezier(0.4,0,0.2,1),
               min-width 0.32s cubic-bezier(0.4,0,0.2,1),
               opacity 0.28s ease,
               border-right-color 0.3s ease;
    flex-shrink:0;
}
.sidebar.nx-mini {
    width:60px !important;
    min-width:60px !important;
}
/* Mini modda gizlenenler */
.sidebar.nx-mini .sidebar-logo,
.sidebar.nx-mini .nav-section-label,
.sidebar.nx-mini .nav-pill,
.sidebar.nx-mini .sidebar-footer,
.sidebar.nx-mini #active-theme-badge,
.sidebar.nx-mini [style*="AKT"],
.sidebar.nx-mini .nx-sidebar-label,
.sidebar.nx-mini .nx-mini-hide {
    display:none !important;
}
/* Mini modda nav butonları — sadece ikon ortada */
.sidebar.nx-mini .nav-btn {
    justify-content:center !important;
    padding:10px 0 !important;
    gap:0 !important;
}
.sidebar.nx-mini .nav-btn .nx-nav-text {
    display:none !important;
}
/* Mini modda sadece görünenler */
.nx-mini-only { display:none !important; }
.sidebar.nx-mini .nx-mini-only { display:flex !important; }
/* Mini mod tema butonu hover */
.sidebar.nx-mini .nx-mini-only div:hover {
    transform: scale(1.12) !important;
    filter: brightness(1.15) !important;
}
/* API paneli hover efekti */
.nx-api-panel { transition: border-color 0.25s, box-shadow 0.25s; }
.nx-api-panel:hover {
    border-color: color-mix(in srgb,var(--accent1) 50%,transparent) !important;
    box-shadow: 0 0 18px color-mix(in srgb,var(--accent1) 18%,transparent);
}
/* Toggle butonu mini modda 60px'de */
#nx-sb-toggle.nx-sb-mini {
    left:60px;
}
/* Sidebar toggle butonu */
#nx-sb-toggle {
    position:fixed;
    top:50%;
    left:220px;
    transform:translate(-50%,-50%);
    z-index:99999;
    width:20px;
    height:56px;
    border-radius:0 10px 10px 0;
    background:color-mix(in srgb,var(--accent1) 18%,rgba(13,14,21,0.92));
    border:1px solid color-mix(in srgb,var(--accent1) 55%,transparent);
    border-left:none;
    cursor:pointer;
    display:flex;
    align-items:center;
    justify-content:center;
    color:var(--accent1);
    font-size:10px;
    line-height:1;
    letter-spacing:-1px;
    box-shadow:3px 0 18px rgba(0,0,0,0.45),
               0 0 12px color-mix(in srgb,var(--accent1) 20%,transparent);
    transition:left 0.32s cubic-bezier(0.4,0,0.2,1),
               background 0.2s ease,
               box-shadow 0.2s ease;
    user-select:none;
    writing-mode:vertical-rl;
    padding:0;
}
#nx-sb-toggle:hover {
    background:color-mix(in srgb,var(--accent1) 32%,rgba(13,14,21,0.95));
    box-shadow:3px 0 24px rgba(0,0,0,0.5),
               0 0 20px color-mix(in srgb,var(--accent1) 35%,transparent);
}
#nx-sb-toggle.nx-sb-closed {
    left:0px;
}
.sidebar::after {
    content:'';position:absolute;top:0;right:0;width:1px;height:100%;
    background:linear-gradient(180deg,transparent 0%,var(--accent1) 40%,var(--accent2) 60%,transparent 100%);
    opacity:0.5;animation:sidebarGlow 4s ease-in-out infinite alternate;
}
@keyframes sidebarGlow{0%{opacity:0.2}100%{opacity:0.7}}
.sidebar-logo{padding:22px 20px 14px;border-bottom:1px solid rgba(255,255,255,0.08)}
.logo-badge{font-size:9px;font-weight:700;letter-spacing:2.5px;color:var(--accent1);text-transform:uppercase;display:flex;align-items:center;gap:6px;margin-bottom:8px}
.logo-badge::before{content:'';width:7px;height:7px;border-radius:50%;background:var(--accent1);box-shadow:0 0 8px var(--accent1);animation:pulse 2s infinite;flex-shrink:0}
/* Gradient metin — CSS var kullanır, tema değişince otomatik güncellenir */
.logo-title-gradient{
    font-size:19px;font-weight:800;line-height:1.2;letter-spacing:-0.5px;
    background:linear-gradient(135deg,var(--accent1),var(--accent2));
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
}
.logo-title{font-size:17px;font-weight:800;color:var(--text);line-height:1.2;letter-spacing:-0.3px}
.logo-sub{
    font-size:10px;
    color:var(--muted);
    margin-top:2px;
    text-shadow: 0 0 8px var(--accent1), 0 0 20px var(--accent1);
}

/* ── Nav ── */
.nav-section{padding:10px 10px 0;flex:1;overflow-y:auto}
.nav-section-label{
    font-size:9px;font-weight:700;letter-spacing:1.8px;
    color:var(--muted);text-transform:uppercase;padding:8px 8px 4px;
    text-shadow: 0 0 10px var(--accent1), 0 0 22px var(--accent1);
}
.nav-btn {
    width:100%;display:flex;align-items:center;gap:10px;
    padding:10px 14px;border-radius:11px;margin-bottom:2px;
    cursor:pointer;transition:all 0.22s cubic-bezier(.4,0,.2,1);
    border:1px solid transparent;background:transparent;
    color:var(--sub);font-size:13px;font-weight:500;
    text-align:left;font-family:inherit;
    position:relative;overflow:hidden;
}
.nav-btn::before {
    content:'';position:absolute;inset:0;opacity:0;
    background:linear-gradient(135deg,rgba(255,255,255,0.06),transparent);
    transition:opacity 0.2s;
}
.nav-btn:hover::before{opacity:1}
.nav-btn:hover{background:color-mix(in srgb,var(--accent1) 10%,transparent);color:var(--text);border-color:color-mix(in srgb,var(--accent1) 20%,transparent);transform:translateX(2px)}
.nav-btn.active {
    background:linear-gradient(135deg,color-mix(in srgb,var(--accent1) 22%,transparent),color-mix(in srgb,var(--accent2) 10%,transparent));
    color:var(--text);border-color:color-mix(in srgb,var(--accent1) 45%,transparent);
    box-shadow:0 0 20px color-mix(in srgb,var(--accent1) 15%,transparent),inset 0 1px 0 rgba(255,255,255,0.08);
}
.nav-btn.active::after {
    content:'';position:absolute;left:0;top:20%;bottom:20%;width:3px;
    background:linear-gradient(180deg,var(--accent1),var(--accent2));
    border-radius:0 3px 3px 0;box-shadow:0 0 10px var(--accent1);
}
.nav-icon{font-size:16px;width:20px;text-align:center}
.nav-pill{margin-left:auto;font-size:9px;font-weight:700;padding:2px 7px;border-radius:99px;background:color-mix(in srgb,var(--accent1) 30%,transparent);color:var(--purple2)}
.sidebar-footer{padding:12px 14px 18px;border-top:1px solid rgba(255,255,255,0.05)}
.api-stat{font-size:10px;color:var(--sub);display:flex;align-items:center;gap:6px;margin-bottom:4px}
.api-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}

/* ── Ana içerik ── */
.main-content{flex:1;height:100vh;overflow:hidden;display:flex;flex-direction:column;background:transparent}
.page-container{display:flex;flex-direction:column;width:100%;padding:0}

/* ── Page header (başlık bölümü) ── */
.page-header {
    padding: 24px 28px 20px;
    background: rgba(0,0,0,0.50);
    backdrop-filter: blur(28px);
    -webkit-backdrop-filter: blur(28px);
    border-bottom: 1px solid rgba(255,255,255,0.08);
    position: relative;
    margin-bottom: 0;
}
.page-header::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 28px; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent1), var(--accent2) 60%, transparent);
    opacity: 0.75;
}
.ph-title {
    font-size: 28px;
    font-weight: 800;
    color: var(--text);
    text-shadow: 0 2px 12px rgba(0,0,0,0.8), 0 1px 3px rgba(0,0,0,0.9);
    letter-spacing: -0.3px;
    line-height: 1.15;
}
.ph-sub {
    font-size: 13px;
    color: var(--sub);
    margin-top: 5px;
    text-shadow:
        0 1px 4px rgba(0,0,0,0.8),
        0 0 12px var(--accent2),
        0 0 28px var(--accent2);
}

/* ── Status bar ── */
.status-bar {
    height:32px;min-height:32px;
    background:rgba(0,0,0,0.30);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);
    border-top:1px solid rgba(255,255,255,0.08);
    display:flex;align-items:center;padding:0 20px;gap:16px;
    font-size:11px;color:var(--sub);
}
.status-dot{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 2s infinite}
.status-sep{width:1px;height:14px;background:rgba(255,255,255,0.08)}

/* ── Topbar ── */
.page-topbar {
    padding:8px 28px;display:flex;align-items:center;justify-content:space-between;
    border-bottom:1px solid rgba(255,255,255,0.07);
    background:rgba(0,0,0,0.25);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    position:sticky;top:0;z-index:10;
}
.topbar-title{
    font-size:13px;font-weight:600;color:var(--sub);
    text-shadow: 0 0 10px var(--accent2), 0 0 22px var(--accent2);
}
.topbar-time{
    font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;
    text-shadow: 0 0 8px var(--accent2), 0 0 18px var(--accent2);
}

/* ── Glassmorphism kartlar ── */
.card {
    background:rgba(0,0,0,0.30);
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,0.10);
    border-radius:14px;padding:20px;
    transition:all 0.3s cubic-bezier(.4,0,.2,1);
    position:relative;overflow:hidden;
}
.card::before {
    content:'';position:absolute;top:0;left:0;right:0;height:1px;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent);
}
.card:hover {
    border-color:rgba(255,255,255,0.18);
    box-shadow:0 8px 32px rgba(0,0,0,0.4),0 0 0 1px rgba(255,255,255,0.06);
    transform:translateY(-1px);
}
.card-purple{border-color:color-mix(in srgb,var(--accent1) 35%,transparent);background:rgba(0,0,0,0.32)}
.card-cyan{border-color:color-mix(in srgb,var(--accent2) 25%,transparent);background:rgba(0,0,0,0.30)}
.card-green{border-color:rgba(16,185,129,0.25);background:rgba(0,0,0,0.30)}
.card-title {
    font-size:11px;font-weight:700;letter-spacing:0.8px;
    color:var(--sub);text-transform:uppercase;margin-bottom:14px;
    display:flex;align-items:center;gap:8px;
}
.card-title::before{content:'';flex:0 0 3px;height:14px;border-radius:2px;background:linear-gradient(180deg,var(--accent1),var(--accent2));box-shadow:0 0 8px var(--accent1)}

/* ── Drop zone ── */
.drop-zone {
    border:2px dashed var(--border);border-radius:14px;padding:36px 20px;
    text-align:center;cursor:pointer;transition:all 0.3s ease;
    background:color-mix(in srgb,var(--accent1) 2%,transparent);position:relative;overflow:hidden;
}
.drop-zone::before {
    content:'';position:absolute;inset:0;opacity:0;transition:opacity 0.3s;
    background:radial-gradient(circle at 50% 50%,color-mix(in srgb,var(--accent1) 8%,transparent),transparent 70%);
}
.drop-zone:hover{border-color:var(--accent1);border-style:solid;box-shadow:0 0 30px color-mix(in srgb,var(--accent1) 20%,transparent),inset 0 0 30px color-mix(in srgb,var(--accent1) 5%,transparent)}
.drop-zone:hover::before{opacity:1}
.drop-icon{font-size:34px;margin-bottom:10px;filter:drop-shadow(0 0 8px color-mix(in srgb,var(--accent1) 50%,transparent))}
.drop-text{font-size:14px;color:var(--sub)}
.drop-sub{
    font-size:11px;color:var(--muted);margin-top:4px;
    text-shadow: 0 0 8px var(--accent1), 0 0 18px var(--accent1);
}
.drop-path{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--cyan);margin-top:10px;word-break:break-all}

/* ══════════════════════════════════════════════════════════════
   PREMIUM NATIVE BUTONLAR (.nx-btn)
   Quasar'dan bağımsız, %100 tema rengine uyumlu
   ══════════════════════════════════════════════════════════════ */
.nx-btn {
    display:inline-flex;align-items:center;justify-content:center;gap:8px;
    padding:0 22px;height:42px;border-radius:12px;cursor:pointer;
    font-family:inherit;font-size:14px;font-weight:700;letter-spacing:0.6px;
    color:#fff;text-shadow:0 1px 4px rgba(0,0,0,0.45);
    border:1px solid rgba(255,255,255,0.18);
    background:linear-gradient(160deg,var(--accent1) 0%,var(--accent2) 100%);
    box-shadow:
        0 4px 20px rgba(0,0,0,0.45),
        0 1px 0 rgba(255,255,255,0.22) inset,
        0 -1px 0 rgba(0,0,0,0.25) inset;
    position:relative;overflow:hidden;
    transition:all 0.22s cubic-bezier(.4,0,.2,1);
    outline:none;user-select:none;
}
.nx-btn::before {
    content:'';position:absolute;top:0;left:0;right:0;height:46%;
    background:linear-gradient(180deg,rgba(255,255,255,0.24) 0%,transparent 100%);
    pointer-events:none;
}
.nx-btn::after {
    content:'';position:absolute;inset:0;border-radius:12px;
    background:radial-gradient(circle at 50% 0%, rgba(255,255,255,0.12), transparent 60%);
    pointer-events:none;
}
.nx-btn:hover {
    transform:translateY(-2px);
    filter:brightness(1.12);
    box-shadow:
        0 8px 32px rgba(0,0,0,0.55),
        0 0 24px var(--accent1),
        0 1px 0 rgba(255,255,255,0.25) inset !important;
}
.nx-btn:active { transform:translateY(0) !important; filter:brightness(0.9) !important; }

/* Boyutlar */
.nx-btn-sm  { height:32px;padding:0 14px;font-size:12px;border-radius:9px;gap:5px; }
.nx-btn-sm::before { height:42%; }
.nx-btn-lg  { height:52px;padding:0 32px;font-size:16px;border-radius:14px; }
.nx-btn-icon{ width:38px;height:38px;padding:0;border-radius:10px;font-size:15px; }
.nx-btn-icon.nx-btn-sm { width:30px;height:30px;font-size:13px;border-radius:8px; }
.nx-btn-full{ width:100%;justify-content:center; }

/* Renk varyantları */
.nx-btn-danger{
    background:linear-gradient(160deg,#ef4444 0%,#b91c1c 100%);
    box-shadow:0 4px 20px rgba(239,68,68,0.4),0 1px 0 rgba(255,255,255,0.2) inset;
}
.nx-btn-danger:hover{ box-shadow:0 8px 30px rgba(239,68,68,0.6),0 1px 0 rgba(255,255,255,0.25) inset !important; }
.nx-btn-success{
    background:linear-gradient(160deg,#10b981 0%,#059669 100%);
    box-shadow:0 4px 20px rgba(16,185,129,0.35),0 1px 0 rgba(255,255,255,0.2) inset;
}
.nx-btn-success:hover{ box-shadow:0 8px 30px rgba(16,185,129,0.55),0 1px 0 rgba(255,255,255,0.25) inset !important; }
.nx-btn-ghost{
    background:rgba(255,255,255,0.07);
    border-color:rgba(255,255,255,0.15);
    box-shadow:0 2px 10px rgba(0,0,0,0.2);
    color:var(--text);text-shadow:none;
}
.nx-btn-ghost:hover{
    background:rgba(255,255,255,0.12);
    box-shadow:0 4px 16px rgba(0,0,0,0.3),0 0 12px var(--accent1) !important;
}

/* ── Premium butonlar (eski .btn sınıfı) ── */
.btn {
    display:inline-flex;align-items:center;gap:8px;
    padding:10px 22px;border-radius:10px;font-size:14px;
    font-weight:600;cursor:pointer;transition:all 0.22s cubic-bezier(.4,0,.2,1);
    border:none;font-family:inherit;position:relative;overflow:hidden;
}
.btn::after {
    content:'';position:absolute;top:50%;left:50%;width:0;height:0;
    background:rgba(255,255,255,0.15);border-radius:50%;
    transform:translate(-50%,-50%);transition:width 0.4s,height 0.4s,opacity 0.4s;
    opacity:0;
}
.btn:active::after{width:200px;height:200px;opacity:0}
.btn-primary{background:linear-gradient(135deg,var(--accent1),#5b21b6);color:white;box-shadow:0 4px 15px color-mix(in srgb,var(--accent1) 35%,transparent),inset 0 1px 0 rgba(255,255,255,0.15)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 8px 30px color-mix(in srgb,var(--accent1) 55%,transparent),inset 0 1px 0 rgba(255,255,255,0.2)}
.btn-primary:active{transform:translateY(0)}
.btn-success{background:linear-gradient(135deg,var(--green),#059669);color:white;box-shadow:0 4px 15px rgba(16,185,129,0.3),inset 0 1px 0 rgba(255,255,255,0.12)}
.btn-success:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(16,185,129,0.5)}
.btn-cyan{background:linear-gradient(135deg,#0891b2,#06b6d4);color:white;box-shadow:0 4px 15px color-mix(in srgb,var(--accent2) 25%,transparent)}
.btn-cyan:hover{transform:translateY(-2px);box-shadow:0 8px 25px color-mix(in srgb,var(--accent2) 45%,transparent)}
.btn-ghost{background:rgba(255,255,255,0.04);color:var(--sub);border:1px solid rgba(255,255,255,0.08)}
.btn-ghost:hover{border-color:var(--accent1);color:var(--text);background:color-mix(in srgb,var(--accent1) 10%,transparent);transform:translateY(-1px)}
.btn-sm{padding:6px 14px;font-size:12px}
.btn-lg{padding:13px 28px;font-size:15px}
.btn-full{width:100%;justify-content:center}
.btn-red{background:linear-gradient(135deg,var(--red),#b91c1c);color:white;box-shadow:0 4px 15px rgba(239,68,68,0.3)}
.btn-red:hover{transform:translateY(-2px);box-shadow:0 8px 25px rgba(239,68,68,0.5)}

/* ── Log konsolu ── */
.log-console{background:rgba(0,0,0,0.45);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}
.log-header{background:rgba(255,255,255,0.05);padding:10px 16px;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(255,255,255,0.06)}
.log-dot{width:11px;height:11px;border-radius:50%}
.log-body{padding:14px 16px;height:200px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.7}

/* ── Form elemanları ── */
.field-label{
    font-size:10px;font-weight:700;color:var(--muted);margin-bottom:6px;
    letter-spacing:1px;text-transform:uppercase;
    text-shadow: 0 0 10px var(--accent1), 0 0 22px var(--accent1);
}
.field-input,.field-select {
    width:100%;background:rgba(0,0,0,0.35);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
    border:1px solid rgba(255,255,255,0.10);border-radius:9px;
    padding:10px 14px;color:var(--text);font-size:13px;
    font-family:inherit;outline:none;transition:all 0.2s;
}
.field-input:focus,.field-select:focus{border-color:var(--accent1);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent1) 15%,transparent),0 0 15px color-mix(in srgb,var(--accent1) 10%,transparent)}

/* ── Slider ── */
input[type=range]{-webkit-appearance:none;width:100%;height:4px;border-radius:2px;background:rgba(255,255,255,0.1);outline:none;cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;border-radius:50%;background:var(--accent1);cursor:pointer;box-shadow:0 0 10px var(--accent1);transition:transform 0.15s,box-shadow 0.15s}
input[type=range]::-webkit-slider-thumb:hover{transform:scale(1.3);box-shadow:0 0 18px var(--accent1)}

/* ── Premium toggle ── */
.toggle-row{display:flex;align-items:center;justify-content:space-between;padding:11px 16px;border-radius:10px;transition:background 0.2s}
.toggle-row:hover{background:rgba(255,255,255,0.03)}
.toggle-info{flex:1;min-width:0}
.toggle-label{font-size:13px;font-weight:500;color:var(--text)}
.toggle-hint{
    font-size:11px;color:var(--muted);margin-top:2px;
    text-shadow: 0 0 8px var(--accent2), 0 0 18px var(--accent2);
}
.toggle-switch{width:44px;height:23px;border-radius:99px;background:rgba(255,255,255,0.1);cursor:pointer;position:relative;transition:all 0.28s cubic-bezier(.4,0,.2,1);flex-shrink:0;margin-left:12px;border:none;outline:none}
.toggle-switch.on{background:linear-gradient(135deg,var(--accent1),var(--accent2));box-shadow:0 0 16px color-mix(in srgb,var(--accent1) 50%,transparent)}
.toggle-switch::after{content:'';position:absolute;top:3px;left:3px;width:17px;height:17px;border-radius:50%;background:white;transition:transform 0.28s cubic-bezier(.4,0,.2,1);box-shadow:0 1px 4px rgba(0,0,0,0.3)}
.toggle-switch.on::after{transform:translateX(21px)}

/* ── Tablo ── */
.data-table{width:100%;border-collapse:collapse}
.data-table th{
    text-align:left;font-size:10px;font-weight:700;color:var(--muted);
    letter-spacing:1px;text-transform:uppercase;padding:10px 16px;
    border-bottom:1px solid rgba(255,255,255,0.07);
    text-shadow: 0 0 10px var(--accent1), 0 0 22px var(--accent1);
}
.data-table td{padding:12px 16px;font-size:13px;color:var(--text);border-bottom:1px solid rgba(255,255,255,0.04);vertical-align:middle}
.data-table tr{cursor:pointer;transition:background 0.15s}
.data-table tr:hover td{background:color-mix(in srgb,var(--accent1) 7%,transparent)}

/* ── Badge/chip ── */
.chip{display:inline-block;font-size:10px;font-weight:700;padding:3px 10px;border-radius:99px;letter-spacing:0.3px}
.chip-purple{background:color-mix(in srgb,var(--accent1) 20%,transparent);color:var(--purple2);border:1px solid color-mix(in srgb,var(--accent1) 30%,transparent)}
.chip-cyan{background:color-mix(in srgb,var(--accent2) 15%,transparent);color:var(--cyan);border:1px solid color-mix(in srgb,var(--accent2) 25%,transparent)}
.chip-green{background:rgba(16,185,129,0.2);color:var(--green);border:1px solid rgba(16,185,129,0.3)}
.chip-yellow{background:rgba(245,158,11,0.2);color:var(--yellow);border:1px solid rgba(245,158,11,0.3)}
.chip-pink{background:rgba(236,72,153,0.2);color:var(--pink);border:1px solid rgba(236,72,153,0.3)}
.chip-red{background:rgba(239,68,68,0.2);color:var(--red);border:1px solid rgba(239,68,68,0.3)}

/* ── Stat kartları ── */
.stat-card{
    background:rgba(0,0,0,0.30);
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
    border:1px solid rgba(255,255,255,0.10);
    border-radius:14px;padding:18px;display:flex;align-items:center;gap:14px;
    transition:all 0.28s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden;
}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.15),transparent)}
.stat-card:hover{transform:translateY(-3px);border-color:rgba(255,255,255,0.18);box-shadow:0 12px 40px rgba(0,0,0,0.4)}
.stat-icon{width:48px;height:48px;border-radius:13px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;position:relative}
.stat-icon::after{content:'';position:absolute;inset:0;border-radius:13px;box-shadow:inset 0 1px 0 rgba(255,255,255,0.15)}
.stat-num{font-size:26px;font-weight:800;color:var(--text);line-height:1;letter-spacing:-0.5px}
.stat-label{
    font-size:11px;color:var(--sub);margin-top:3px;
    text-shadow: 0 0 8px var(--accent2), 0 0 18px var(--accent2);
}

/* ── Sayfa geçiş animasyonu ── */
@keyframes pageIn{from{opacity:0;transform:translateY(10px) scale(0.99)}to{opacity:1;transform:translateY(0) scale(1)}}
.page-container > *{animation:pageIn 0.35s cubic-bezier(.4,0,.2,1) both}

/* ── GLOBAL MUTED/SUB TEXT GLOW — tüm sayfalarda geçerli ── */
/* CSS class-based elementler */
.logo-sub,
.nav-section-label,
.ph-sub,
.field-label,
.toggle-hint,
.drop-sub,
.topbar-time,
.topbar-title,
.stat-label,
.data-table th,
.card-title,
.api-stat {
    text-shadow:
        0 0 6px var(--accent1),
        0 0 14px var(--accent1),
        0 1px 3px rgba(0,0,0,0.9) !important;
}

/* ph-sub cyan glow */
.ph-sub {
    text-shadow:
        0 0 8px var(--accent2),
        0 0 20px var(--accent2),
        0 1px 3px rgba(0,0,0,0.9) !important;
}

/* ── Animasyonlar ── */
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(0.85)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes glow{0%,100%{box-shadow:var(--glow-p)}50%{box-shadow:var(--glow-c)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
.animate-in{animation:fadeIn 0.35s ease both}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.1);border-top-color:var(--accent1);border-radius:50%;animation:spin 0.8s linear infinite}

/* ── Gradient text ── */
.gradient-text{background:linear-gradient(135deg,var(--accent1),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}

/* ── Shimmer yükleme ── */
.shimmer{background:linear-gradient(90deg,var(--panel) 25%,rgba(255,255,255,0.06) 50%,var(--panel) 75%);background-size:200% 100%;animation:shimmer 1.5s infinite}

/* ── Tema geçiş ── */
*{transition:background-color 0.4s ease,border-color 0.4s ease,color 0.3s ease,box-shadow 0.3s ease}
button,input,select,textarea{transition:all 0.22s cubic-bezier(.4,0,.2,1) !important}

/* ── NiceGUI / Quasar override ── */
.nicegui-content{padding:0 !important}
header.q-header{display:none !important}
.q-page{padding:0 !important}
.q-card{background:transparent !important;box-shadow:none !important}
body>.q-page-container{background:var(--bg) !important}

/* ── Quasar Input / Select — TAM İNTERAKTİF (seçilebilir, yazılabilir) ── */
/* pywebview'da Quasar kendi içinde -webkit-user-select:none uygulayabiliyor */
.q-field__native,
.q-field__input,
.q-field input,
.q-field textarea,
.q-select__input,
input[type="text"],
input[type="number"],
input[type="email"],
input[type="password"],
input[type="search"],
input[type="url"],
textarea {
    user-select: text !important;
    -webkit-user-select: text !important;
    -moz-user-select: text !important;
    cursor: text !important;
    pointer-events: all !important;
}
/* Select dropdown da tıklanabilir olsun */
.q-field__control,
.q-select .q-field__control {
    pointer-events: all !important;
    cursor: pointer !important;
}
/* Input wrapper'ı da seçilebilir yap */
.q-field {
    user-select: text !important;
    -webkit-user-select: text !important;
}

:root                    { --q-primary:#7c3aed; --q-secondary:#00d4ff; }
[data-theme="nexus"]     { --q-primary:#7c3aed; --q-secondary:#00d4ff; }
[data-theme="sakura"]    { --q-primary:#c026d3; --q-secondary:#f472b6; }
[data-theme="cyber"]     { --q-primary:#00ff87; --q-secondary:#facc15; }
[data-theme="midnight"]  { --q-primary:#3b82f6; --q-secondary:#6366f1; }
[data-theme="ember"]     { --q-primary:#f97316; --q-secondary:#ef4444; }
[data-theme="arctic"]    { --q-primary:#94a3b8; --q-secondary:#e2e8f0; }
[data-theme="neontokyo"] { --q-primary:#ff0080; --q-secondary:#00ffff; }
[data-theme="goldrush"]  { --q-primary:#ffd700; --q-secondary:#ff8c00; }
[data-theme="bloodmoon"] { --q-primary:#dc143c; --q-secondary:#8b0000; }

/* Body arka plan rengi tema ile değişsin */
body { background: var(--bg) !important; }

/* Quasar buton içini (wrapper) gradient ile doldur */
.q-btn .q-btn__wrapper {
    background: linear-gradient(135deg, var(--q-primary), var(--q-secondary)) !important;
    border-radius: 10px !important;
}
.q-btn {
    color: #fff !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.35) !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    overflow: hidden !important;
}
.q-btn:hover .q-btn__wrapper {
    filter: brightness(1.18) !important;
}
.q-btn::before { box-shadow: none !important; }

/* Slider & toggle accent rengi */
.q-slider__track-container--h .q-slider__track { background: var(--q-primary) !important; }
.q-slider__thumb { color: var(--q-primary) !important; }
.q-toggle__inner--truthy { color: var(--q-primary) !important; }

/* ══════════════════════════════════════════════════════════════
   PREMIUM NOTIFICATIONS (Quasar q-notification override)
   ══════════════════════════════════════════════════════════════ */

/* Bildirim listesini sağ üste sabitle */
.q-notifications__list--top-right,
.q-notifications__list--bottom,
.q-notifications__list {
    top: 72px !important;
    right: 14px !important;
    left: auto !important;
    bottom: auto !important;
    max-width: 340px !important;
}

/* Ana bildirim kutusu */
.q-notification {
    background: rgba(0,0,0,0.72) !important;
    backdrop-filter: blur(22px) !important;
    -webkit-backdrop-filter: blur(22px) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 14px !important;
    box-shadow:
        0 8px 32px rgba(0,0,0,0.55),
        0 1px 0 rgba(255,255,255,0.08) inset !important;
    color: #e2e8f0 !important;
    font-family: 'Inter','Segoe UI',sans-serif !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    min-width: 270px !important;
    max-width: 340px !important;
    padding: 0 !important;
    overflow: hidden !important;
    animation: notifySlideIn 0.3s cubic-bezier(.2,.8,.3,1) both !important;
}
@keyframes notifySlideIn {
    from { opacity:0; transform:translateX(20px) scale(0.96); }
    to   { opacity:1; transform:translateX(0) scale(1); }
}

/* Wrapper içi padding */
.q-notification__wrapper {
    padding: 12px 14px !important;
    border-radius: 14px !important;
}

/* İkon */
.q-notification__icon { font-size: 18px !important; margin-right: 10px !important; }

/* Mesaj */
.q-notification__message { font-size: 13px !important; font-weight: 500 !important; line-height: 1.5 !important; }

/* Kapat butonu */
.q-notification__actions .q-btn {
    color: rgba(255,255,255,0.6) !important;
    background: transparent !important;
    box-shadow: none !important;
    min-height: 20px !important;
    padding: 2px 6px !important;
    font-size: 11px !important;
}
.q-notification__actions .q-btn:hover {
    color: #fff !important;
    transform: none !important;
}

/* Tip renkleri — sol kenar çizgisi */
.q-notification--positive {
    border-left: 3px solid #10b981 !important;
    background: linear-gradient(135deg, rgba(16,185,129,0.18), rgba(0,0,0,0.72)) !important;
}
.q-notification--negative {
    border-left: 3px solid #ef4444 !important;
    background: linear-gradient(135deg, rgba(239,68,68,0.18), rgba(0,0,0,0.72)) !important;
}
.q-notification--warning {
    border-left: 3px solid #f59e0b !important;
    background: linear-gradient(135deg, rgba(245,158,11,0.18), rgba(0,0,0,0.72)) !important;
}
.q-notification--info {
    border-left: 3px solid #3b82f6 !important;
    background: linear-gradient(135deg, rgba(59,130,246,0.18), rgba(0,0,0,0.72)) !important;
}
.q-notification--ongoing {
    border-left: 3px solid var(--accent1) !important;
    background: linear-gradient(135deg, color-mix(in srgb,var(--accent1) 18%,transparent), rgba(0,0,0,0.72)) !important;
}
"""

SOUNDS_JS_PATH = None  # ng_app.py tarafından set edilir

def get_css():
    return CSS
