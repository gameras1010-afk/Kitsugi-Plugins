"""
pages/api_keys.py
=================
API anahtarları yönetimi.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

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
