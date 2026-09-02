"""
pages/accounts.py
=================
Hesaplar sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

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


