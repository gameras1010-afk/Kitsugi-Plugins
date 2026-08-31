import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading
import time
import os
import sys
try: import _no_window  # noqa
except ImportError: pass
import json
import re
import queue

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Nexus IPC: Ana sayfa ile bağlantı ──
try:
    _IPC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ../ (Python kodları)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("nexus_ipc",
        os.path.join(_IPC_DIR, "nexus_ipc.py"))
    nexus_ipc = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(nexus_ipc)
except Exception:
    nexus_ipc = None

# ── Nexus Premium Chrome (blur, frameless, title bar) ──
try:
    import importlib.util as _ilu2
    _spec2 = _ilu2.spec_from_file_location("nexus_ctk_base",
        os.path.join(_IPC_DIR, "nexus_ctk_base.py"))
    _chrome_mod = _ilu2.module_from_spec(_spec2)
    _spec2.loader.exec_module(_chrome_mod)
    apply_nexus_chrome   = _chrome_mod.apply_nexus_chrome
    update_chrome_accent = _chrome_mod.update_chrome_accent
except Exception as _ce:
    print(f"[chrome] {_ce}")
    def apply_nexus_chrome(w, *a, **kw): pass
    def update_chrome_accent(*a, **kw): pass

# ── Nexus Ses Motoru ────────────────────────────────
_SND_BASE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds"))

def _play(name: str):
    def _w():
        try:
            import winsound
            # Önce nexus_ipc'den özel yol al
            if nexus_ipc:
                paths = nexus_ipc.get_sound_paths()
                p = paths.get(name, "")
            else:
                p = ""
            # Yoksa varsayılan
            if not p or not os.path.exists(p):
                p = os.path.join(_SND_BASE, name + ".wav")
            if os.path.exists(p):
                winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    threading.Thread(target=_w, daemon=True).start()

def _snd_hover():   _play("hover")
def _snd_click():   _play("click")
def _snd_success(): _play("success")

def _play_tone(tone_type: str):
    """WAV dosyasıyla ses çal — non-daemon thread, tam çalar."""
    _snd_map = {
        'start':     'start.wav',
        'file_done': 'file_done.wav',
        'done':      'done.wav',
        'stop':      'stop.wav',
        'error':     'error.wav',
    }
    wav_name = _snd_map.get(tone_type)
    if not wav_name:
        return
    wav_path = os.path.join(_SND_BASE, wav_name)
    def _seq():
        try:
            import winsound
            if os.path.exists(wav_path):
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    import threading as _t
    _t.Thread(target=_seq, daemon=False).start()




if getattr(sys, 'frozen', False):
    # EXE olarak çalışırken: EXE Python kodları\ içinde
    BASE_DIR   = os.path.dirname(sys.executable)
    PARENT_DIR = BASE_DIR
    # manual_translator.py hâlâ Sadece Çeviri\ klasöründe
    SCRIPT     = os.path.join(BASE_DIR, "Sadece Çeviri", "manual_translator.py")
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(BASE_DIR)
    SCRIPT     = os.path.join(BASE_DIR, "manual_translator.py")

PREFS_FILE = os.path.join(PARENT_DIR, "user_preferences.json")
TRANS_CFG  = os.path.join(PARENT_DIR, "translator_config.json")
API_FILE   = os.path.join(PARENT_DIR, "api_keys.txt")

BG      = "#0D0E15"   # Cyberpunk — derin gece
SIDEBAR = "#1A1B26"   # Cyberpunk — sidebar frame
PANEL   = "#1e1f2e"   # Panel arka planı
CARD    = "#252640"   # Kart arka planı
BORDER  = "#2a2a4a"   # Kenarlık
PURPLE  = "#00d4ff"   # Cyberpunk accent (neon cyan)
PURH    = "#009ab8"   # Accent hover (daha koyu)
GREEN   = "#10b981"   # Başarı yeşili
RED     = "#ef4444"   # Hata kırmızısı
YELLOW  = "#f59e0b"   # Uyarı sarısı
CYAN    = "#64ffda"   # Veri rengi (mint)
TEXT    = "#e2e8f0"   # Ana metin
SUB     = "#a9b1d6"   # İkincil metin


# Varsayılan OpenRouter modelleri — her zaman görünür
MODELS = [
    "google/gemini-2.0-flash-001",
    "google/gemini-2.5-pro-preview-03-25",
    "google/gemini-flash-1.5-8b",
    "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-nemo",
    "microsoft/phi-4",
]

def _reload_models_from_config():
    """
    Model listesini günceller:
    1) Antigravity API'sinden canlı modelleri çeker (bağlıysa)
    2) translator_config.json'daki ek modelleri ekler
    3) Her zaman OpenRouter varsayılanları listede kalır
    """
    global MODELS
    import requests as _req
    ag_prefix_models = []

    # -- 1) Antigravity API'sinden modelleri çek --
    try:
        with open(TRANS_CFG, "r", encoding="utf-8") as _f:
            _cfg = json.load(_f)
        _ag_key = _cfg.get("antigravity_api_key", "")
        _ag_url = _cfg.get("antigravity_url", "")
        if _ag_key and _ag_url:
            _base = _ag_url.replace("/v1/chat/completions", "").rstrip("/")
            _r = _req.get(_base + "/v1/models",
                          headers={"Authorization": f"Bearer {_ag_key}"}, timeout=4)
            if _r.status_code == 200:
                _live = [m.get("id","") for m in _r.json().get("data",[]) if m.get("id")]
                for _m in _live:
                    _disp = f"AG:{_m}" if not _m.startswith("AG:") else _m
                    if _disp not in ag_prefix_models:
                        ag_prefix_models.append(_disp)
    except Exception:
        pass

    # -- 2) Config'deki ek modelleri ekle --
    extra_models = []
    try:
        with open(TRANS_CFG, "r", encoding="utf-8") as _f:
            _cfg = json.load(_f)
        for k, v in _cfg.get("available_models", {}).items():
            is_ag = (v == "antigravity") or (isinstance(v, dict) and v.get("provider") == "antigravity")
            _disp = (k if k.startswith("AG:") else f"AG:{k}") if is_ag else k
            if _disp not in ag_prefix_models and _disp not in MODELS:
                if is_ag:
                    ag_prefix_models.append(_disp)
                else:
                    extra_models.append(_disp)
    except Exception:
        pass

    # -- 3) Birleştir: AG önce, sonra varsayılanlar --
    MODELS = list(dict.fromkeys(ag_prefix_models + extra_models + MODELS))

_reload_models_from_config()

ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

def _strip_ansi(s):
    return ANSI_RE.sub('', s)

def _color_tag(line):
    if '\x1b[32m' in line or '\x1b[92m' in line: return "green"
    if '\x1b[31m' in line or '\x1b[91m' in line: return "red"
    if '\x1b[33m' in line or '\x1b[93m' in line: return "yellow"
    if '\x1b[36m' in line or '\x1b[96m' in line: return "cyan"
    if '\x1b[35m' in line or '\x1b[95m' in line: return "magenta"
    if '\x1b[34m' in line or '\x1b[94m' in line: return "blue"
    return "white"

def load_prefs():
    defaults = {
        'translate': True, 'clean_sub': True, 'smart_merge': True,
        'sub_format': 'ASS', 'ai_model': 'google/gemini-2.0-flash-001',
        'custom_api_keys_path': None,
        'source_lang': 'English', 'target_lang': 'Turkish',
        'delay_sn': 0, 'per_file_delay': 15, 'max_byte_batch': 2000,
        'only_english': True, 'max_line_length': 75,
        'line_merge_mode': 'default', 'force_translate': True,
        'nsfw_mode': False, 'hentai_glossary': False,
        'natural_dialogue': True, 'protect_positioning': True,
        'font_size_mode': 'normalize', 'custom_font_size': 80,
        'simple_mode': True,
        # ── Yeni Özellikler ──────────────────────────────────────
        'use_fandom_glossary':   True,   # Fandom Wiki terminoloji sözlüğü
        'generate_html_report':  True,   # Çeviri sonrası HTML kalite raporu
        'use_episode_context':   True,   # Bölümler arası sliding window bağlamı
    }
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                defaults.update(json.load(f))
        except: pass
    return defaults

def save_prefs(p):
    with open(PREFS_FILE, 'w', encoding='utf-8') as f:
        json.dump(p, f, indent=4)

def load_trans_cfg():
    defaults = {
        'batch_size': 1, 'timeout': 600,
        'delay_between_calls': 0, 'max_retries': 6,
        'system_prompt': '', 'ignore_cache': False,
    }
    if os.path.exists(TRANS_CFG):
        try:
            with open(TRANS_CFG, 'r', encoding='utf-8') as f:
                defaults.update(json.load(f))
        except: pass
    return defaults

def save_trans_cfg(cfg):
    existing = {}
    if os.path.exists(TRANS_CFG):
        try:
            with open(TRANS_CFG, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except: pass
    existing.update(cfg)
    with open(TRANS_CFG, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=4)

def _label(parent, text, size=13, bold=False, color=TEXT, **kw):
    return ctk.CTkLabel(parent, text=text,
        font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
        text_color=color, **kw)

def _entry(parent, var, w=260, **kw):
    return ctk.CTkEntry(parent, textvariable=var, width=w,
        fg_color=CARD, border_color=BORDER, text_color=TEXT,
        corner_radius=8, **kw)

def _btn(parent, text, cmd, color=PURPLE, hover=PURH, w=160, **kw):
    return ctk.CTkButton(parent, text=text, command=cmd,
        fg_color=color, hover_color=hover, corner_radius=10,
        font=ctk.CTkFont(size=13, weight="bold"),
        width=w, **kw)

def _switch(parent, text, var, **kw):
    return ctk.CTkSwitch(parent, text=text, variable=var,
        fg_color=BORDER, progress_color=PURPLE,
        font=ctk.CTkFont(size=13), text_color=TEXT,
        width=46, height=24, **kw)

def _card(parent, accent=None, **kw):
    """Temasal örnek gibi renkli-border premium kart."""
    bc = accent if accent else PURPLE
    return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=14,
        border_color=bc, border_width=2, **kw)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Manuel Çevirici — GUI")
        self.geometry("1480x780")
        self.minsize(1200, 660)
        self.configure(fg_color=BG)

        self.prefs = load_prefs()
        self._proc = None
        self._queue = queue.Queue()
        self._pages = {}
        self._cur = None
        self._nav_btns = {}

        # Layout once kurulur (overrideredirect sirasi onemli)
        self._build_sidebar()
        self._build_detect_panel()   # ← Algılama Motoru sol paneli
        self._build_content()
        self._show("home")
        self.after(80, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Chrome: _build_sidebar'dan SONRA (CTk+overrideredirect uyumu)
        self._title_bar = apply_nexus_chrome(
            self,
            tool_name="Manuel Çeviri",
            tool_subtitle="AI Altyazı Çeviri Motoru  ·  v2.0",
            on_close=self._on_close,
            accent=PURPLE,
        )

        # ── Nexus IPC: Başlangıçta tema yükle + canlı izle ──
        if nexus_ipc:
            try:
                self._apply_nexus_state(nexus_ipc.read_state())
            except Exception:
                pass
            self._nexus_watcher = nexus_ipc.StateWatcher(
                on_change=self._apply_nexus_state, poll_ms=2000)
            self._nexus_watcher.start(self)

    def _apply_nexus_state(self, state: dict):
        """Nexus ana sayfasından tema/ses değişimi gelince çağrılır.
        Tema değişince tüm sayfaları temizleyip yeniden çizer."""
        global BG, SIDEBAR, PANEL, CARD, BORDER, PURPLE, PURH, TEXT, SUB, GREEN, RED, YELLOW, CYAN
        if not nexus_ipc:
            return

        new_theme = state.get("theme")
        old_theme = getattr(self, "_current_theme", None)
        colors    = nexus_ipc.get_colors(new_theme)

        # Global renkleri güncelle
        BG      = colors["BG"]
        SIDEBAR = colors["SIDEBAR"]
        PANEL   = colors["PANEL"]
        CARD    = colors["CARD"]
        BORDER  = colors["BORDER"]
        PURPLE  = colors["PURPLE"]
        PURH    = colors["PURH"]
        TEXT    = colors["TEXT"]
        SUB     = colors["SUB"]
        GREEN   = colors["GREEN"]
        RED     = colors["RED"]
        YELLOW  = colors["YELLOW"]
        CYAN    = colors["CYAN"]
        self._current_theme = new_theme

        try:
            # ── Ana pencere + sidebar rengi ──
            self.configure(fg_color=BG)
            if hasattr(self, "_sb"):
                self._sb.configure(fg_color=SIDEBAR)
            if hasattr(self, "_content"):
                self._content.configure(fg_color=BG)

            # ── Başlık çubuğu accent ──
            if hasattr(self, "_title_bar"):
                update_chrome_accent(self._title_bar, PURPLE)

            # ── Eğer tema değiştiyse: tüm sayfa cache'ini temizle ─
            #    Sayfalar yeniden build edilince yeni renkleri kullanır ──
            if old_theme != new_theme:
                cur = self._cur
                # Mevcut sayfayı ekrandan kaldır
                for pg in self._pages.values():
                    try:
                        pg.pack_forget()
                        pg.destroy()
                    except Exception:
                        pass
                self._pages.clear()
                # Aktif sayfayı yeniden göster (yeni renklerle build edilir)
                self._cur = None
                if cur:
                    self.after(50, lambda: self._show(cur))

            # ── Nav butonlarını güncelle ──
            for k, b in self._nav_btns.items():
                if k == self._cur or k == getattr(self, "_cur", None):
                    b.configure(fg_color=PURPLE, text_color="#000000",
                                hover_color=CARD)
                else:
                    b.configure(fg_color="transparent", text_color=SUB,
                                hover_color=CARD)
        except Exception as _e:
            print(f"[apply_state] {_e}")


    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=252, fg_color=SIDEBAR, corner_radius=0)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        self._sb = sb

        # ── ⬡ NEXUS PRO Logo (temasal_arayuz_ornek.py logo_label gibi) ──
        ctk.CTkLabel(sb, text="⬡  NEXUS PRO",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PURPLE).pack(anchor="w", padx=20, pady=(22, 0))
        ctk.CTkLabel(sb, text="Manuel Çeviri",
            font=ctk.CTkFont(size=21, weight="bold"),
            text_color=TEXT).pack(anchor="w", padx=20, pady=(2, 0))
        ctk.CTkLabel(sb, text="AI Altyazı Çeviri Motoru  ·  v2.0",
            font=ctk.CTkFont(size=10), text_color=SUB).pack(
            anchor="w", padx=20, pady=(2, 0))

        # Separator
        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(
            fill="x", padx=12, pady=(14, 8))

        nav = [
            ("home",     "🏠  Ana Ekran"),
            ("prefs",    "⚙️  Tercihler"),
            ("ai",       "🤖  AI & API"),
            ("advanced", "🔧  Gelişmiş Ayarlar"),
            ("tools",    "🛠  Veri & Araçlar"),
            ("test",     "🧪  Canlı Test"),
            ("reset",    "♻️  Sıfırla"),
        ]
        for key, label in nav:
            b = ctk.CTkButton(sb, text=label,
                command=lambda k=key: self._show(k),
                fg_color="transparent",
                hover_color=CARD,
                text_color=SUB,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                height=44,
                corner_radius=10)
            b.pack(fill="x", padx=10, pady=2)
            b.bind("<Enter>", lambda e: _snd_hover())
            self._nav_btns[key] = b

        # Alt: IPC bağlantı göstergesi
        # ── Canlı Sistem Kalbi (nexus_main.py gibi) ──
        ctk.CTkFrame(sb, height=1, fg_color=BORDER).pack(
            fill="x", padx=12, pady=(8, 4), side="bottom")

        sysf = ctk.CTkFrame(sb, fg_color="transparent")
        sysf.pack(side="bottom", fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(sysf, text="⚡ Canlı Sistem Kalbi",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=YELLOW).pack(anchor="w", pady=(0, 4))

        # CPU bar
        cpu_row = ctk.CTkFrame(sysf, fg_color="transparent")
        cpu_row.pack(fill="x", pady=1)
        ctk.CTkLabel(cpu_row, text="CPU", font=ctk.CTkFont(size=9),
            text_color=SUB, width=28, anchor="w").pack(side="left")
        self._cpu_bar = ctk.CTkProgressBar(cpu_row, height=5,
            progress_color=PURPLE, fg_color=BORDER, corner_radius=3)
        self._cpu_bar.set(0)
        self._cpu_bar.pack(side="left", fill="x", expand=True, padx=(4,6))
        self._cpu_lbl = ctk.CTkLabel(cpu_row, text="%0",
            font=ctk.CTkFont(size=9), text_color=SUB, width=28, anchor="e")
        self._cpu_lbl.pack(side="right")

        # RAM bar
        ram_row = ctk.CTkFrame(sysf, fg_color="transparent")
        ram_row.pack(fill="x", pady=1)
        ctk.CTkLabel(ram_row, text="RAM", font=ctk.CTkFont(size=9),
            text_color=SUB, width=28, anchor="w").pack(side="left")
        self._ram_bar = ctk.CTkProgressBar(ram_row, height=5,
            progress_color="#a855f7", fg_color=BORDER, corner_radius=3)
        self._ram_bar.set(0)
        self._ram_bar.pack(side="left", fill="x", expand=True, padx=(4,6))
        self._ram_lbl = ctk.CTkLabel(ram_row, text="%0",
            font=ctk.CTkFont(size=9), text_color=SUB, width=28, anchor="e")
        self._ram_lbl.pack(side="right")

        # DSK bar
        dsk_row = ctk.CTkFrame(sysf, fg_color="transparent")
        dsk_row.pack(fill="x", pady=1)
        ctk.CTkLabel(dsk_row, text="DSK", font=ctk.CTkFont(size=9),
            text_color=SUB, width=28, anchor="w").pack(side="left")
        self._dsk_bar = ctk.CTkProgressBar(dsk_row, height=5,
            progress_color=CYAN, fg_color=BORDER, corner_radius=3)
        self._dsk_bar.set(0)
        self._dsk_bar.pack(side="left", fill="x", expand=True, padx=(4,6))
        self._dsk_lbl = ctk.CTkLabel(dsk_row, text="%0",
            font=ctk.CTkFont(size=9), text_color=SUB, width=28, anchor="e")
        self._dsk_lbl.pack(side="right")

        ctk.CTkLabel(sysf, text="● Nexus IPC Bağlı",
            font=ctk.CTkFont(size=9), text_color=GREEN).pack(
            anchor="w", pady=(4, 0))

        # Sistem monitörü thread'i başlat
        threading.Thread(target=self._sys_monitor_loop, daemon=True).start()


    def _build_detect_panel(self):
        """Sabit sol algılama motoru paneli — slide animasyonlu."""
        self._det_open     = True
        self._det_target_w = 268
        self._det_anim_id  = None

        dp = ctk.CTkFrame(self, width=268, fg_color=SIDEBAR,
                          corner_radius=0)
        dp.pack(side="left", fill="y")
        dp.pack_propagate(False)
        self._det_panel = dp

        # ── Sağ kenarda sabit toggle tab (panel kapansa bile görünür) ──
        ts = ctk.CTkFrame(self, width=18, fg_color=SIDEBAR, corner_radius=0)
        ts.pack(side="left", fill="y")
        ts.pack_propagate(False)
        self._det_tab = ctk.CTkButton(
            ts, text="◄", width=18, height=72,
            fg_color=BORDER, hover_color=YELLOW,
            text_color=YELLOW,
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=0,
            command=self._toggle_det_panel
        )
        self._det_tab.place(relx=0.5, rely=0.5, anchor="center")

        # ── Başlık ──
        ctk.CTkFrame(dp, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=(12,0))
        hdr = ctk.CTkFrame(dp, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 6))
        ctk.CTkLabel(hdr, text="🎛  Algılama Motoru",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=YELLOW).pack(side="left")
        ctk.CTkLabel(hdr, text=" motor ",
            font=ctk.CTkFont(size=9),
            fg_color=YELLOW, text_color="#000000",
            corner_radius=5).pack(side="right", padx=2)
        ctk.CTkFrame(dp, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=(0, 8))

        # ── Togglelar ──
        _det_toggles = [
            ("use_style_suffix_detection",
             "Stil Suffix Algılama",
             "EN/JP/KARA etiketlerine bak",
             True),
            ("romaji_block",
             "Romaji Bloğu",
             "Japonca hece satırlarını atla",
             True),
            ("skip_romaji_mode",
             "İçerik Tabanlı Romaji",
             "Stil adına bakmadan içerik analizi",
             True),
            ("use_song_lyrics_pass",
             "Şarkı Sözü Geçişi",
             "Ayrı şiirsel prompt kullan",
             True),
            ("use_karaoke_collapse",
             "Karaoke Collapse",
             "Hece grubunu tek satıra birleştir",
             True),
            ("force_no_style",
             "Stil Adını Yoksay",
             "Sadece içerik analizi kullan",
             False),
            ("content_detect",
             "İçerik Dedektörü",
             "content_detector.py motorunu aktif et",
             True),
            ("ignore_song_style_for_romaji",
             "Stilsiz Romaji Tespiti",
             "Sözlük + unicode → stil adına gerek yok",
             False),
            ("cps_shorten",
             "CPS Kısaltma",
             "⚡ Hızlı satırları AI ile kısalt (yavaşlar)",
             False),
        ]

        self._det_vars = {}
        det_scroll = ctk.CTkScrollableFrame(
            dp, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=YELLOW)
        det_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        for key, label, hint, default in _det_toggles:
            val = self.prefs.get(key, default)
            v = tk.BooleanVar(value=bool(val))
            self._det_vars[key] = v

            item = ctk.CTkFrame(det_scroll,
                fg_color=PANEL, corner_radius=10,
                border_width=1, border_color=BORDER)
            item.pack(fill="x", pady=4, padx=2)

            top_row = ctk.CTkFrame(item, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=(8, 2))

            ctk.CTkLabel(top_row, text=label,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)

            sw = ctk.CTkSwitch(top_row, text="", variable=v,
                fg_color=BORDER, progress_color=YELLOW,
                width=40, height=20,
                command=lambda k=key, var=v: self._det_toggle(k, var))
            sw.pack(side="right")

            ctk.CTkLabel(item, text=hint,
                font=ctk.CTkFont(size=9),
                text_color=SUB, anchor="w",
                wraplength=220).pack(anchor="w", padx=10, pady=(0, 8))

        # ── Alt: Hızlı Sıfırla butonu ──
        ctk.CTkFrame(dp, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=(4, 6))
        ctk.CTkButton(dp, text="↺  Varsayılana Dön",
            command=self._det_reset_defaults,
            fg_color="transparent", hover_color=CARD,
            text_color=SUB, height=32,
            font=ctk.CTkFont(size=11), corner_radius=8,
            border_width=1, border_color=BORDER).pack(
            fill="x", padx=10, pady=(0, 14))

    def _det_reset_defaults(self):
        """Algılama motoru toggle'larını varsayılana döndür."""
        defaults = {
            'use_style_suffix_detection': True,
            'romaji_block':               True,
            'skip_romaji_mode':           True,
            'use_song_lyrics_pass':       True,
            'use_karaoke_collapse':       True,
            'force_no_style':             False,
            'content_detect':             True,
            'ignore_song_style_for_romaji': False,
            'cps_shorten':                False,
        }
        for k, v in defaults.items():
            if k in self._det_vars:
                self._det_vars[k].set(v)
            self.prefs[k] = v
        save_prefs(self.prefs)

    def _toggle_det_panel(self):
        """Algılama motoru panelini slide animasyonuyla aç/kapat."""
        if self._det_anim_id:
            self.after_cancel(self._det_anim_id)
            self._det_anim_id = None
        self._det_open = not self._det_open
        self._det_target_w = 268 if self._det_open else 0
        self._det_tab.configure(text="◄" if self._det_open else "►")
        self._animate_det_panel()

    def _animate_det_panel(self):
        """~60fps smooth slide animasyonu (panel genişliği 0 ↔ 268)."""
        try:
            current_w = self._det_panel.winfo_width()
        except Exception:
            return
        target = self._det_target_w
        diff   = target - current_w
        if abs(diff) <= 3:
            self._det_panel.configure(width=target)
            return
        # Eäsing: hız başlangıçta yüksek, sona doğru yavaşlar
        step = max(6, abs(diff) // 4)
        step = min(step, 40)
        new_w = current_w + (step if diff > 0 else -step)
        new_w = max(0, min(new_w, 268))
        self._det_panel.configure(width=new_w)
        self._det_anim_id = self.after(12, self._animate_det_panel)  # ~83fps

    def _build_content(self):
        # content bg = BG (koyu) → kartlar SIDEBAR (açık) üstünde parlasın
        self._content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self._content.pack(side="right", fill="both", expand=True)

    def _show(self, key):
        _snd_click()
        if self._cur and self._cur in self._pages:
            self._pages[self._cur].pack_forget()
        if self._cur and self._cur in self._nav_btns:
            self._nav_btns[self._cur].configure(
                fg_color="transparent", text_color=SUB)
        self._cur = key
        if key in self._nav_btns:
            self._nav_btns[key].configure(
                fg_color=PURPLE, text_color="#000000")
        if key not in self._pages:
            builder = {
                "home":     self._build_home,
                "prefs":    self._build_prefs,
                "ai":       self._build_ai,
                "advanced": self._build_advanced,
                "tools":    self._build_tools,
                "test":     self._build_test,
                "reset":    self._build_reset,
            }.get(key)
            if builder:
                try:
                    self._pages[key] = builder()
                except Exception as _build_err:
                    import traceback as _tb
                    err_page = ctk.CTkFrame(self._content, fg_color=BG)
                    _label(err_page, f"⚠️  Sayfa yüklenemedi: {key}",
                           size=15, bold=True, color=RED).pack(pady=(40, 12))
                    _label(err_page, str(_build_err),
                           size=12, color=YELLOW).pack(padx=24)
                    self._pages[key] = err_page
                    print(f"[BUILD_PAGE_ERROR] {key}: {_build_err}")
                    _tb.print_exc()
        if key in self._pages:
            self._pages[key].pack(fill="both", expand=True)

    def _scroll_frame(self, parent):
        sf = ctk.CTkScrollableFrame(
            parent, fg_color=BG,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=PURPLE)
        return sf

    def _page_header(self, parent, icon, title, subtitle=""):
        """Nexus ana sayfası gibi premium sayfa başlığı."""
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(20, 14))
        ctk.CTkLabel(bar, text=f"{icon}  {title}",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT).pack(side="left")
        if subtitle:
            ctk.CTkLabel(bar, text=subtitle,
                font=ctk.CTkFont(size=12), text_color=SUB).pack(
                side="left", padx=(14,0), pady=(6,0))
        ctk.CTkFrame(parent, height=1, fg_color=BORDER).pack(
            fill="x", padx=20, pady=(0, 10))

    def _save_btn(self, parent, text, cmd, row=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=(16, 4))
        _btn(f, text, cmd, w=280).pack(anchor="w", padx=4)

    def _ok(self, msg):
        messagebox.showinfo("Tamam", msg, parent=self)

    def _err(self, msg):
        messagebox.showerror("Hata", msg, parent=self)

    # ═══════════════════════════════════════════════ HOME ═══
    def _build_home(self):
        page = ctk.CTkFrame(self._content, fg_color=BG, corner_radius=0)

        # ── Büyük Premium Başlık ──
        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(22, 6))
        ctk.CTkLabel(hdr, text="📝  Manuel Çeviri",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=TEXT).pack(side="left")
        ctk.CTkLabel(hdr, text="  ·  Altyazı dosyalarını AI ile çevir",
            font=ctk.CTkFont(size=13), text_color=SUB).pack(
            side="left", pady=(8, 0))
        ctk.CTkFrame(page, height=1, fg_color=BORDER).pack(
            fill="x", padx=20, pady=(4, 14))

        # ── Dosya / Klasör Seç Kartı (border_width=2, CYAN) ──
        path_card = ctk.CTkFrame(page,
            fg_color=SIDEBAR, corner_radius=14,
            border_width=2, border_color=CYAN)
        path_card.pack(fill="x", padx=20, pady=(0, 12))

        # Kart başlığı
        ph = ctk.CTkFrame(path_card, fg_color="transparent")
        ph.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(ph, text="📂  Klasör / Dosya Seç",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=CYAN).pack(side="left")
        # Renkli etiket (temasal_arayuz_ornek.py tag_lbl gibi)
        tag = ctk.CTkLabel(ph, text=" girdi ", font=ctk.CTkFont(size=10),
            fg_color=CYAN, text_color="#000000", corner_radius=6)
        tag.pack(side="right", padx=4)

        row_f = ctk.CTkFrame(path_card, fg_color="transparent")
        row_f.pack(fill="x", padx=16, pady=(0, 14))
        row_f.columnconfigure(0, weight=1)

        self._path_var = tk.StringVar()
        e = ctk.CTkEntry(row_f, textvariable=self._path_var,
            placeholder_text="Klasör veya dosya yolu seçin…",
            fg_color="#0b0c17", border_color=BORDER,
            text_color=TEXT, corner_radius=10, height=40)
        e.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(row_f, text="📁 Klasör",
            command=self._pick_folder,
            fg_color=CYAN, hover_color="#4db8a0",
            text_color="#000000", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, height=40, width=110).pack(side="left", padx=(0, 6))
        ctk.CTkButton(row_f, text="📄 Dosya",
            command=self._pick_file,
            fg_color="#1d4ed8", hover_color="#1e40af",
            text_color="white", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, height=40, width=110).pack(side="left")

        # ── Kontrol Kartı (border_width=2, GREEN) ──
        ctrl_card = ctk.CTkFrame(page,
            fg_color=SIDEBAR, corner_radius=14,
            border_width=2, border_color=GREEN)
        ctrl_card.pack(fill="x", padx=20, pady=(0, 12))

        ch = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ch.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(ch, text="▶  Kontrol Paneli",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=GREEN).pack(side="left")
        tag2 = ctk.CTkLabel(ch, text=" kontrol ", font=ctk.CTkFont(size=10),
            fg_color=GREEN, text_color="#000000", corner_radius=6)
        tag2.pack(side="right", padx=4)

        ctrl = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 6))

        self._start_btn = ctk.CTkButton(ctrl, text="▶  BAŞLAT",
            command=self._start, fg_color=GREEN, hover_color="#059669",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10, height=46, width=180)
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = ctk.CTkButton(ctrl, text="⏹  DURDUR",
            command=self._stop, fg_color=RED, hover_color="#dc2626",
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10, height=46, width=180)
        self._stop_btn.pack(side="left", padx=(0, 16))
        self._stop_btn.configure(state="disabled")

        self._status = ctk.CTkLabel(ctrl, text="● Hazır",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=SUB)
        self._status.pack(side="left")

        self._prog = ctk.CTkProgressBar(ctrl_card, mode="indeterminate",
            progress_color=PURPLE, fg_color="#0b0c17", height=6, corner_radius=3)
        self._prog.pack(fill="x", padx=16, pady=(8, 14))

        # (Algılama Motoru artık sol sabit panelde — det_panel)

        # ── Canlı Log Kartı (border_width=2, PURPLE) ──
        log_card = ctk.CTkFrame(page,
            fg_color=SIDEBAR, corner_radius=14,
            border_width=2, border_color=PURPLE)
        log_card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        lh = ctk.CTkFrame(log_card, fg_color="transparent")
        lh.pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(lh, text="📋  Canlı Log",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=PURPLE).pack(side="left")
        ctk.CTkButton(lh, text="🗑 Temizle",
            command=self._clear_log,
            fg_color=BORDER, hover_color=CARD,
            text_color=SUB, width=90, height=30,
            font=ctk.CTkFont(size=11), corner_radius=8).pack(side="right")

        ctk.CTkFrame(log_card, height=1, fg_color=BORDER).pack(
            fill="x", padx=12, pady=(0, 6))

        self._log = tk.Text(log_card, bg="#080910", fg=TEXT,
            font=("Consolas", 11), wrap="word",
            bd=0, highlightthickness=0, insertbackground=TEXT,
            state="disabled", cursor="arrow")
        sb2 = ctk.CTkScrollbar(log_card, command=self._log.yview,
            button_color=BORDER, button_hover_color=PURPLE)
        self._log.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self._log.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 12))

        for tag, col in [
            ("green",   GREEN), ("red",  RED),    ("yellow", YELLOW),
            ("cyan",    CYAN),  ("magenta","#a855f7"), ("blue","#60a5fa"),
            ("white",   TEXT)
        ]:
            self._log.tag_configure(tag, foreground=col)

        return page


    def _pick_folder(self):
        p = filedialog.askdirectory(title="Çevrilecek Klasörü Seç", parent=self)
        if p:
            self._path_var.set(p)

    def _pick_file(self):
        p = filedialog.askopenfilename(
            title="Çevrilecek Dosyayı Seç",
            filetypes=[("Altyazı/Video", "*.ass *.ssa *.srt *.vtt *.mkv *.mp4 *.avi *.webm"),
                       ("Tümü", "*.*")],
            parent=self)
        if p:
            self._path_var.set(p)

    def _start(self):
        path = self._path_var.get().strip()
        if not path:
            self._err("Lütfen önce bir klasör veya dosya seçin!")
            return
        if not os.path.exists(path):
            self._err(f"Yol bulunamadı:\n{path}")
            return
        if self._proc and self._proc.poll() is None:
            return

        # Rapor tarayıcısı için alias: son kullanılan giriş yolu
        self._input_path = self._path_var

        # ── Arka planda Fandom Sözlük ön yüklemesi ──────────────────────────
        # Dosya/klasör adından seri adı tahmini yapılır → build_glossary çağrılır.
        # Cache yoksa sessizce çeker, varsa anında listeler.
        try:
            import re as _re
            _name = os.path.basename(path.rstrip("/\\"))
            # "Oshi no Ko - S03E01.ass" → "Oshi no Ko"  |  "SAO/" → "SAO"
            _series_guess = _re.split(
                r'\s*[-–]\s*(?:[Ss]\d{1,2}|[Ee]\d{1,3}|Season|Episode|\d{2,4}$)|'
                r'\s+(?:S\d{1,2}E\d{1,3}|\d{3,4}p|\[)',
                _name, maxsplit=1
            )[0]
            _series_guess = _re.sub(r'\.(ass|srt|vtt|mkv|mp4|avi)$', '',
                                    _series_guess, flags=_re.IGNORECASE).strip()
            if _series_guess and len(_series_guess) >= 3:
                self._auto_fetch_glossary_if_needed(_series_guess)
                # Input alanına da doldur (Veri & Araçlar sekmesinde hazır olsun)
                if hasattr(self, '_gls_series_var') and not self._gls_series_var.get():
                    self._gls_series_var.set(_series_guess)
        except Exception:
            pass
        # ────────────────────────────────────────────────────────────────────

        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._status.configure(text="Çalışıyor…", text_color=GREEN)
        self._prog.start()
        _play_tone('start')  # Başlat sesi
        threading.Thread(target=self._run, args=(path,), daemon=True).start()

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        _play_tone('stop')  # Durdur sesi
        self._on_done()

    def _det_toggle(self, key, var):
        """Algılama motoru toggle'ı anında prefs'e kaydet."""
        self.prefs[key] = var.get()
        save_prefs(self.prefs)
        state = "ACIK" if var.get() else "KAPALI"
        self._log_write(f"[Motor] {key} = {state}\n", "yellow")

    def _run(self, path):
        env = os.environ.copy()
        env["PYTHONPATH"] = PARENT_DIR + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        try:
            # ── Python yorumlayıcısını bul ──────────────────────────────────────
            # PyInstaller --onefile EXE'de sys.executable = EXE'nin kendisi.
            # O yüzden frozen modda gerçek python.exe'yi bulmamız şart.
            import sys as _sys
            import shutil as _shutil

            if getattr(_sys, 'frozen', False):
                # Önce PATH'da ara
                py_cmd = (_shutil.which('python') or
                          _shutil.which('python3') or
                          _shutil.which('py'))
                # Bulamazsa bilinen kurulum yollarına bak
                if not py_cmd:
                    _candidates = [
                        r'C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe',
                        r'C:\Python311\python.exe',
                        r'C:\Python\python.exe',
                        r'C:\Program Files\Python311\python.exe',
                    ]
                    for _c in _candidates:
                        if os.path.exists(_c):
                            py_cmd = _c
                            break
                if not py_cmd:
                    py_cmd = 'python'  # son çare
            else:
                py_cmd = _sys.executable or 'python'
            # ───────────────────────────────────────────────────────────────────

            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
            self._queue.put((f"[GUI] Python: {py_cmd}\n", "cyan"))
            self._queue.put((f"[GUI] Script: {SCRIPT}\n", "cyan"))
            self._proc = subprocess.Popen(
                [py_cmd, SCRIPT, path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                env=env,
                cwd=os.path.dirname(SCRIPT),
                creationflags=flags,
            )
            try:
                self._proc.stdin.write("\n")
                self._proc.stdin.flush()
                self._proc.stdin.close()
            except Exception:
                pass
            for line in self._proc.stdout:
                tag = _color_tag(line)
                self._queue.put((_strip_ansi(line), tag))
            self._proc.wait()
        except Exception as e:
            self._queue.put((f"[GUI HATA] {e}\n", "red"))
        self._queue.put(("__DONE__", ""))

    def _poll(self):
        try:
            while True:
                text, tag = self._queue.get_nowait()
                if text == "__DONE__":
                    _play_tone('done')   # Doğal bitiş sesi
                    self._on_done()
                elif text.strip() == "[SOUND:file_done]":
                    _play_tone('file_done')  # Subprocess'tan gelen dosya başarı sinyali
                    # Log'a yazma — bu sadece ses tetikleyici
                elif text.strip() == "[SOUND:error]":
                    _play_tone('error')      # Subprocess'tan gelen hata sinyali
                    # Log'a yazma — bu sadece ses tetikleyici
                else:
                    # ── [FIX] Çok uzun satırları kırp ────────────────────────
                    # Binlerce karakter içeren satırlar (LLLLL.../watermark/şifreli)
                    # Tkinter Text widget kelime-sarma hesabını blokluyor.
                    # 500+ karakter ise ısa bir özet göster, tümü değil.
                    if len(text) > 500:
                        stripped = text.rstrip()
                        # Önce DEBUG satırı mı yoksa normal uzun mu anla
                        if stripped.startswith('[DEBUG]'):
                            # [DEBUG] Input/Output → tamamen gizle, sadece uzunluğu göster
                            preview = stripped[:80].replace('\n', ' ')
                            text = f"{preview}... [{len(stripped)} karakter, gösterilmedi]\n"
                        else:
                            # Diğer uzun satırlar: ilk 300 + son 50 karakter
                            text = stripped[:300] + f" ... [+{len(stripped)-300} karakter] ..." + stripped[-50:] + "\n"
                    # ─────────────────────────────────────────────────────
                    self._log_write(text, tag)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _on_done(self):
        self._prog.stop()
        self._start_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._status.configure(text="Tamamlandı", text_color=CYAN)

        # ── Otomatik süreç temizleme (asılı kalan alt süreçler) ──────────────
        self.after(1500, self._kill_proc_tree)  # 1.5s bekle → son yazmaları al
        # ─────────────────────────────────────────────────────────────────────

        # ── [GUI Stats] _last_run_stats.json oku ve log'a yaz ─────────────────
        try:
            import json as _js, os as _os
            _sp = _os.path.join(PARENT_DIR, "_last_run_stats.json")
            if _os.path.exists(_sp):
                with open(_sp, encoding='utf-8') as _sf:
                    _st = _js.load(_sf)
                _force = _st.get('force_mode', False)
                _fuzzy_line = (
                    f"  🔍 Fuzzy TM   : {_st.get('fuzzy_hits',0)} cache hit (benzerlik ≥87%)"
                    + ("  ⚠️ Cache devre dışı (Zorla Çevir modu)" if _force else "")
                )
                _lines  = [
                    f"",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"  ✅  ÇEVİRİ TAMAMLANDI — {_st.get('output_file','?')}",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"  📝 Çevrilen   : {_st.get('translated',0)} / {_st.get('total',0)} satır",
                    f"  ⏭  Atlanan    : {_st.get('skipped',0)} satır (şarkı/romaji/işaret)",
                    _fuzzy_line,
                    f"  ✂️  CPS Kısalt : {_st.get('cps_shortened',0)} satır",
                    f"  🎵 Şarkı Satırı: {_st.get('song_lines',0)} satır",
                    f"  ⏱  Süre        : {_st.get('duration_sec',0):.1f} saniye",
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                    f"",
                ]
                for _ln in _lines:
                    self._log_write(_ln + "\n", "cyan")
        except Exception:
            pass
        # ─────────────────────────────────────────────────────────────────────

    def _kill_proc_tree(self):
        """
        İşlem bittikten sonra asılı kalan alt süreçleri temizler.
        psutil mevcutsa tam process tree öldürme yapar.
        Yoksa fallback: taskkill ile hedef PID'i öldürür.
        Mevcut GUI prosesine (kendi PID'i) dokunmaz.
        """
        if self._proc is None:
            return

        my_pid = os.getpid()
        target_pid = self._proc.pid if self._proc else None

        # psutil ile tam process tree temizleme
        try:
            import psutil
            if target_pid:
                try:
                    parent = psutil.Process(target_pid)
                    children = parent.children(recursive=True)
                    # Önce çocukları öldür
                    for child in children:
                        if child.pid != my_pid:
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                    # Sonra parent'i öldür
                    if parent.pid != my_pid:
                        try:
                            parent.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Ek güvenlik: asılı kalan zombie python prosesleri logla
            zombie_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                try:
                    if proc.info['status'] == psutil.STATUS_ZOMBIE:
                        zombie_count += 1
                except Exception:
                    pass
            if zombie_count > 0:
                self._log_write(f"[GUI] {zombie_count} zombie süreç temizlendi.\n", "yellow")

        except ImportError:
            # psutil yoksa taskkill fallback (Windows)
            if target_pid and os.name == 'nt':
                try:
                    subprocess.Popen(
                        ["taskkill", "/F", "/PID", str(target_pid), "/T"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    )
                except Exception:
                    pass

        self._proc = None  # handle'ı serbest bırak


    def _sys_monitor_loop(self):
        """Sidebar CPU/RAM/DSK barlarını günceller."""
        try:
            import psutil
        except ImportError:
            return
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1) / 100
                ram = psutil.virtual_memory().percent / 100
                dsk = psutil.disk_usage("/").percent / 100
                self.after(0, lambda c=cpu, r=ram, d=dsk: self._update_sys_bars(c, r, d))
            except Exception:
                pass
            time.sleep(2)

    def _update_sys_bars(self, cpu, ram, dsk):
        try:
            self._cpu_bar.set(cpu)
            self._cpu_lbl.configure(text=f"%{int(cpu*100)}")
            self._ram_bar.set(ram)
            self._ram_lbl.configure(text=f"%{int(ram*100)}")
            self._dsk_bar.set(dsk)
            self._dsk_lbl.configure(text=f"%{int(dsk*100)}")
        except Exception:
            pass

    def _on_close(self):
        """
        Uygulama kapatılınca TÜM arka plan işlemlerini temizler.
        ─────────────────────────────────────────────────────────
        1. Çeviri subprocess ve çocukları → PID bazlı kill (python.exe'nin
           tamamını öldürme — sadece bu uygulama başlattığı süreç)
        2. Nexus IPC watcher durdur
        3. FFmpeg / yt-dlp / ffprobe gibi yardımcı araçları temizle
        4. Güvenli destroy
        """
        import os as _os2, sys as _sys2

        # ── 1. Çeviri subprocess PID ağacını öldür ──────────────────────────
        _proc_pid = None
        if self._proc and self._proc.poll() is None:
            _proc_pid = self._proc.pid
            try:
                # Windows: psutil varsa tüm çocuk süreçleri de öldür
                import psutil as _psu
                _parent = _psu.Process(_proc_pid)
                _children = _parent.children(recursive=True)
                for _ch in _children:
                    try: _ch.kill()
                    except Exception: pass
                try: _parent.kill()
                except Exception: pass
            except ImportError:
                # psutil yoksa sadece ana süreci sonlandır
                try:
                    if _os2.name == 'nt':
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(_proc_pid), "/T"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            timeout=3
                        )
                    else:
                        self._proc.kill()
                except Exception:
                    pass
            except Exception:
                try: self._proc.kill()
                except Exception: pass
            self._proc = None

        # ── 2. Nexus IPC state watcher durdur ──────────────────────────────
        try:
            if hasattr(self, "_nexus_watcher") and self._nexus_watcher:
                self._nexus_watcher.stop()
        except Exception:
            pass

        # ── 3. Yardımcı araçları temizle (sadece medya/araç süreçleri) ─────
        _media_tools = ["ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe",
                        "chromedriver.exe"]
        for _tool in _media_tools:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", _tool, "/T"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=2,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                )
            except Exception:
                pass

        # ── 4. GUI'yi temizle ve çık ────────────────────────────────────────
        try:
            self.destroy()
        except Exception:
            pass
        # Olası hayatta kalan thread'ler için zorla çık
        _sys2.exit(0)

    def _log_write(self, text, tag):
        self._log.configure(state="normal")
        self._log.insert("end", text, tag)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    # ═══════════════════════════════════════════════ TERCIHLER ═══
    def _build_prefs(self):
        page = self._scroll_frame(self._content)
        # ── Premium Başlık ──
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", padx=24, pady=(20, 4))
        ctk.CTkLabel(bar, text="⚙️  Tercihler & Özellikler",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=TEXT).pack(side="left")
        ctk.CTkLabel(bar, text="Tercihlerinizi düzenleyin",
            font=ctk.CTkFont(size=12), text_color=SUB).pack(
            side="left", padx=(14,0), pady=(6,0))
        ctk.CTkFrame(page, height=1, fg_color=BORDER).pack(
            fill="x", padx=20, pady=(4, 12))

        p = self.prefs

        # ── Temel Seçenekler Kartı (CYAN) ──
        c1 = _card(page, accent=CYAN)
        c1.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(c1, text="⚡  Temel Seçenekler",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=CYAN).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14,8), sticky="w")

        toggles = [
            ("translate",           "AI Çeviri Yap"),
            ("clean_sub",           "Altyazı Temizliği (Clean Sub)"),
            ("smart_merge",         "Akıllı Birleştirme (Smart Merge)"),
            ("only_english",        "Sadece İngilizce Çevir (diğer dilleri atla)"),
            ("romaji_block",        "🎵 Romaji Satırlarını Atla (Şarkı/Romaji çevrilmez)"),
            ("force_translate",     "Zorla Çevir (No Cache)"),
            ("protect_positioning", "Konumlandırma/Karaoke Koruması"),
            ("natural_dialogue",    "Doğal Türkçe Diyalog"),
            ("nsfw_mode",           "+18 Hentai Modu (Argoyu Aç)"),
            ("hentai_glossary",     "Hentai Sözlüğü (120+ Terim)"),
            ("simple_mode",         "Basit & Stabil Mod (Her Dosya Yeni Oturum)"),
            ("use_fandom_glossary", "🎌 Fandom Wiki Sözlüğü (Seri terminolojisi)"),
            ("generate_html_report","📊 HTML Kalite Raporu Oluştur"),
            ("use_episode_context", "🔗 Bölüm Arası Bağlam (Cross-Episode)"),
        ]
        self._pref_vars = {}
        for i, (key, label) in enumerate(toggles):
            v = tk.BooleanVar(value=bool(p.get(key, False)))
            self._pref_vars[key] = v
            row_f = ctk.CTkFrame(c1, fg_color="transparent")
            row_f.grid(row=i+1, column=0, columnspan=2,
                       padx=12, pady=2, sticky="ew")
            row_f.columnconfigure(0, weight=1)
            ctk.CTkLabel(row_f, text=label,
                font=ctk.CTkFont(size=13), text_color=TEXT,
                anchor="w").grid(row=0, column=0, padx=4, sticky="w")
            ctk.CTkSwitch(row_f, text="", variable=v,
                fg_color=BORDER, progress_color=PURPLE,
                width=46, height=24).grid(row=0, column=1, padx=8)

        # ── Format & Dil Kartı (PURPLE) ──
        c2 = _card(page, accent=PURPLE)
        c2.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(c2, text="🌐  Format & Dil",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PURPLE).grid(
            row=0, column=0, columnspan=4, padx=16, pady=(14,8), sticky="w")
        self._fmt_var   = tk.StringVar(value=p.get("sub_format","ASS"))
        self._src_var   = tk.StringVar(value=p.get("source_lang","English"))
        self._tgt_var   = tk.StringVar(value=p.get("target_lang","Turkish"))
        self._merge_var = tk.StringVar(value=p.get("line_merge_mode","default"))
        rows_fmt = [
            ("Çıktı Formatı",     self._fmt_var,   ["ASS","SRT","VTT","ALL"]),
            ("Kaynak Dil",        self._src_var,   ["English","Japanese","Chinese","Korean","Spanish","French","German"]),
            ("Hedef Dil",         self._tgt_var,   ["Turkish","English","Japanese","Chinese","Korean","Spanish","French","German"]),
            ("Satır Birleştirme", self._merge_var, ["default","aggressive","conservative","none"]),
        ]
        for i, (label, var, values) in enumerate(rows_fmt):
            ctk.CTkLabel(c2, text=label, font=ctk.CTkFont(size=13),
                text_color=TEXT, anchor="w").grid(
                row=i+1, column=0, padx=16, pady=6, sticky="w")
            ctk.CTkComboBox(c2, variable=var, values=values,
                fg_color=CARD, border_color=BORDER, text_color=TEXT,
                button_color=PURPLE, dropdown_fg_color=PANEL,
                width=180, corner_radius=8).grid(
                row=i+1, column=1, padx=(8,16), pady=6, sticky="w")

        # ── Sayısal Değerler Kartı (YELLOW) ──
        c3 = _card(page, accent=YELLOW)
        c3.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(c3, text="🗓  Sayısal Değerler",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=YELLOW).grid(
            row=0, column=0, columnspan=4, padx=16, pady=(14,8), sticky="w")
        num_fields = [
            ("delay_sn",        "Gecikme (sn)",              "0"),
            ("per_file_delay",  "Dosya Arası Bekleme (sn)",  "15"),
            ("max_byte_batch",  "Max Byte/Batch",            "2000"),
            ("max_line_length", "Max Satır Uzunluğu",        "75"),
        ]
        self._num_vars = {}
        for i, (key, label, default) in enumerate(num_fields):
            ctk.CTkLabel(c3, text=label, font=ctk.CTkFont(size=13),
                text_color=TEXT, anchor="w").grid(
                row=i+1, column=0, padx=16, pady=6, sticky="w")
            v = tk.StringVar(value=str(p.get(key, default)))
            self._num_vars[key] = v
            _entry(c3, v, w=120).grid(row=i+1, column=1, padx=(8,16), pady=6, sticky="w")

        # ── Font Kartı (GREEN) ──
        c4 = _card(page, accent=GREEN)
        c4.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkLabel(c4, text="🎨  Font Boyutu Ayarları",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=GREEN).grid(
            row=0, column=0, columnspan=4, padx=16, pady=(14,8), sticky="w")
        ctk.CTkLabel(c4, text="Font Boyutu Modu",
            font=ctk.CTkFont(size=13), text_color=TEXT).grid(
            row=1, column=0, padx=16, pady=6, sticky="w")
        self._font_mode_var = tk.StringVar(value=p.get("font_size_mode","normalize"))
        ctk.CTkComboBox(c4, variable=self._font_mode_var,
            values=["preserve","normalize","custom"],
            fg_color=CARD, border_color=BORDER, text_color=TEXT,
            button_color=PURPLE, dropdown_fg_color=PANEL,
            width=180, corner_radius=8).grid(row=1, column=1, padx=(8,16), pady=6, sticky="w")
        ctk.CTkLabel(c4, text="Özel Font Boyutu (30-150)",
            font=ctk.CTkFont(size=13), text_color=TEXT).grid(
            row=2, column=0, padx=16, pady=6, sticky="w")
        self._font_size_var = tk.StringVar(value=str(p.get("custom_font_size",80)))
        _entry(c4, self._font_size_var, w=100).grid(
            row=2, column=1, padx=(8,16), pady=6, sticky="w")

        # ── Kaydet Butonu ──
        save_f = ctk.CTkFrame(page, fg_color="transparent")
        save_f.pack(fill="x", padx=20, pady=(8, 24))
        ctk.CTkButton(save_f, text="💾  Tercihleri Kaydet",
            command=self._save_prefs, fg_color=PURPLE,
            hover_color=PURH, font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=10, height=44, width=280).pack(side="left")
        return page


    def _save_prefs(self):
        p = self.prefs
        for key, var in self._pref_vars.items():
            p[key] = var.get()
        p['sub_format']     = self._fmt_var.get()
        p['source_lang']    = self._src_var.get()
        p['target_lang']    = self._tgt_var.get()
        p['line_merge_mode']= self._merge_var.get()
        p['font_size_mode'] = self._font_mode_var.get()
        for key, var in self._num_vars.items():
            try:
                p[key] = float(var.get()) if '.' in var.get() else int(var.get())
            except: pass
        try:
            v = int(self._font_size_var.get())
            if 30 <= v <= 150:
                p['custom_font_size'] = v
        except: pass
        save_prefs(p)
        self._ok("Tercihler kaydedildi!")

    # ═══════════════════════════════════════════════ AI & API ═══
    def _build_ai(self):
        page = self._scroll_frame(self._content)
        self._page_header(page, "🤖", "AI & API Yönetimi",
                         "Model seçimi ve API anahtar yönetimi")

        # ── Model Seçimi Kartı (PURPLE) ──
        c1 = _card(page, accent=PURPLE)
        c1.pack(fill="x", padx=20, pady=(0, 12))
        c1.columnconfigure(1, weight=1)
        ctk.CTkLabel(c1, text="🤖  Model Seçimi",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=PURPLE).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14,8), sticky="w")

        self._model_var = tk.StringVar(value=self.prefs.get('ai_model', MODELS[0] if MODELS else ""))
        ctk.CTkLabel(c1, text="AI Modeli", font=ctk.CTkFont(size=13),
            text_color=TEXT).grid(row=1, column=0, padx=16, pady=8, sticky="w")

        self._model_btn = ctk.CTkButton(c1, textvariable=self._model_var,
            fg_color=CARD, border_width=2, border_color=BORDER,
            text_color=TEXT, hover_color=PURH,
            width=340, corner_radius=10, anchor="w",
            command=lambda: self._open_model_picker())
        self._model_btn.grid(row=1, column=1, padx=(8,16), pady=8, sticky="w")

        btn_f1 = ctk.CTkFrame(c1, fg_color="transparent")
        btn_f1.grid(row=2, column=0, columnspan=2, padx=14, pady=(0,14), sticky="w")
        ctk.CTkButton(btn_f1, text="💾 Modeli Kaydet",
            command=lambda: [self.prefs.update({'ai_model': self._model_var.get()}),
                             save_prefs(self.prefs),
                             self._ok(f"Model: {self._model_var.get()}")],
            fg_color=PURPLE, hover_color=PURH,
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, height=38, width=180).pack(side="left", padx=(0,8))

        ctk.CTkButton(btn_f1, text="🔄 Modelleri Yenile",
            command=lambda: [_reload_models_from_config(),
                             self._ok("Model listesi güncellendi!")],
            fg_color=CARD, hover_color=BORDER,
            text_color=SUB, font=ctk.CTkFont(size=13),
            corner_radius=10, height=38, width=180).pack(side="left")

        # ── API Anahtarları Kartı (CYAN) ──
        c2 = _card(page, accent=CYAN)
        c2.pack(fill="x", padx=20, pady=(0, 12))
        c2.columnconfigure(0, weight=1)

        self._api_stats = _label(c2, self._get_key_stats(), color=SUB)
        self._api_stats.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")

        _label(c2, "Yeni Anahtar Ekle (virgülle ayır)").grid(
            row=2, column=0, padx=16, pady=(4, 2), sticky="w")
        self._new_key_var = tk.StringVar()
        _entry(c2, self._new_key_var, w=480, placeholder_text="sk-or-... , sk-or-...").grid(
            row=3, column=0, padx=16, pady=(0, 8), sticky="w")

        btn_f = ctk.CTkFrame(c2, fg_color="transparent")
        btn_f.grid(row=4, column=0, padx=16, pady=(0, 8), sticky="w")
        _btn(btn_f, "➕ Ekle",      self._add_keys,  w=130).pack(side="left", padx=(0, 8))
        _btn(btn_f, "🔄 Yenile",   self._refresh_keys, w=130,
             color=PURH, hover=PURPLE).pack(side="left")

        _btn(c2, "🗑 Tüm Anahtarları Sil", self._clear_keys, w=268,
             color=RED, hover="#dc2626").grid(row=6, column=0, padx=16, pady=(4, 14), sticky="w")

        def _open_model_picker():
            """Model seçici popup — fare tekerleği + scrollbar + AG renk desteği"""
            top = ctk.CTkToplevel(self)
            top.title("🤖  Model Seçimi")
            top.geometry("520x620")
            top.minsize(400, 400)
            top.transient(self)
            top.grab_set()
            top.configure(fg_color="#0a0a14")
            top.attributes("-topmost", True)

            # Başlık
            hdr = ctk.CTkFrame(top, fg_color="#12121f", corner_radius=0)
            hdr.pack(fill="x")
            ctk.CTkFrame(hdr, fg_color="#7c3aed", height=3).pack(fill="x")
            ctk.CTkLabel(hdr, text="🤖  AI Modeli Seçin",
                         font=ctk.CTkFont(size=14, weight="bold"),
                         text_color="#7c3aed").pack(anchor="w", padx=14, pady=(10, 4))
            count_lbl = ctk.CTkLabel(hdr, text=f"{len(MODELS)} model mevcut",
                                     font=ctk.CTkFont(size=11), text_color="#94a3b8")
            count_lbl.pack(anchor="w", padx=14, pady=(0, 8))

            # Arama kutusu
            search_frame = ctk.CTkFrame(top, fg_color="#1a1a35",
                                         corner_radius=8, border_width=1,
                                         border_color="#2a2a4a")
            search_frame.pack(fill="x", padx=12, pady=(10, 6))
            ctk.CTkLabel(search_frame, text="🔍", font=ctk.CTkFont(size=13),
                         text_color="#94a3b8").pack(side="left", padx=(10, 4))
            search_var = tk.StringVar()
            search_entry = ctk.CTkEntry(
                search_frame, textvariable=search_var,
                placeholder_text="Model ara... (örn: gemini, claude, gpt)",
                fg_color="transparent", border_width=0,
                text_color="#e2e8f0", height=36)
            search_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
            search_entry.focus()

            # Scrollable model listesi
            sf = ctk.CTkScrollableFrame(
                top, fg_color="#0a0a14",
                scrollbar_button_color="#2a2a4a",
                scrollbar_button_hover_color="#7c3aed")
            sf.pack(fill="both", expand=True, padx=12, pady=(0, 6))

            # Alt bilgi
            footer = ctk.CTkFrame(top, fg_color="#12121f", corner_radius=0)
            footer.pack(fill="x", side="bottom")
            ctk.CTkFrame(footer, fg_color="#2a2a4a", height=1).pack(fill="x")
            ctk.CTkLabel(footer,
                         text="AG: önekli modeller Antigravity Manager üzerinden çalışır",
                         font=ctk.CTkFont(size=10), text_color="#94a3b8").pack(
                anchor="w", padx=14, pady=6)

            def _on_mousewheel(event):
                try:
                    if event.num == 4:
                        sf._parent_canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        sf._parent_canvas.yview_scroll(1, "units")
                    else:
                        sf._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                except Exception:
                    pass

            sf.bind("<MouseWheel>", _on_mousewheel)
            top.bind("<MouseWheel>", _on_mousewheel)

            btns = []
            def _set_m(m):
                self._model_var.set(m)
                self._model_btn.configure(text=m)
                top.destroy()

            def _build_list(*args):
                for b in btns:
                    b.destroy()
                btns.clear()
                q = search_var.get().lower()
                filtered = [m for m in MODELS if q in m.lower()]
                count_lbl.configure(text=f"{len(filtered)} / {len(MODELS)} model")
                for m in filtered:
                    is_selected = (self._model_var.get() == m)
                    is_ag = m.startswith("AG:")
                    if is_ag:
                        btn_color = "#7c3aed" if is_selected else "#1e1040"
                        hover_color = "#6d28d9"
                        display_text = f"✦ {m}"
                    else:
                        btn_color = "#7c3aed" if is_selected else "transparent"
                        hover_color = "#2a2a4a"
                        display_text = m
                    btn = ctk.CTkButton(
                        sf, text=display_text, anchor="w",
                        fg_color=btn_color, hover_color=hover_color,
                        text_color="#ffffff",
                        font=ctk.CTkFont(size=12, weight="bold" if is_ag else "normal"),
                        height=34, corner_radius=6,
                        command=lambda x=m: _set_m(x))
                    btn.bind("<MouseWheel>", _on_mousewheel)
                    btn.pack(fill="x", pady=2, padx=2)
                    btns.append(btn)

            search_var.trace_add("write", _build_list)
            _build_list()

        self._open_model_picker = _open_model_picker  # metoda ata
        self._key_list = tk.Listbox(c2, bg=PANEL, fg=TEXT,
                                    font=("Consolas", 10), selectbackground=PURPLE,
                                    bd=0, highlightthickness=0, height=8)
        self._key_list.grid(row=5, column=0, padx=16, pady=(0, 4), sticky="ew")
        self._load_key_list()


        _btn(c2, "🗑 Seçili Anahtarı Sil", self._del_key, w=220,
             color=RED, hover="#dc2626").grid(row=6, column=0, padx=16, pady=(4, 14), sticky="w")

        c3 = _card(page)
        c3.pack(fill="x", pady=(0, 12))
        c3.columnconfigure(0, weight=1)
        
        _label(c3, "🚀 Antigravity Manager (Yerel API Proxy)", bold=True, color=CYAN).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14, 6), sticky="w")
            
        ctk.CTkLabel(c3, text="Sınırsız çeviri için yerel Antigravity Manager proxy'sine bağlanın.\nVarsayılan: localhost:8045",
                     font=ctk.CTkFont(size=12), text_color=SUB, justify="left").grid(
            row=1, column=0, columnspan=2, padx=16, pady=(4, 8), sticky="w")
            
        def _ag_connect():
            dialog = ctk.CTkInputDialog(text="Antigravity IP:PORT (örn: localhost:8045):", title="Antigravity Bağlantısı")
            url_input = dialog.get_input()
            if url_input is None: return
            url_input = url_input.strip()
            if not url_input: url_input = "localhost:8045"
            if not url_input.startswith("http"): url_input = "http://" + url_input
            if not url_input.endswith("/v1/chat/completions"):
                url_input = url_input.rstrip("/") + "/v1/chat/completions"

            # [YENİ] Mevcut key'i önceden yükle — boşsa da sor
            _existing_cfg = {}
            if os.path.exists(TRANS_CFG):
                try:
                    with open(TRANS_CFG, "r", encoding="utf-8") as _f: _existing_cfg = json.load(_f)
                except: pass
            _existing_key = _existing_cfg.get("antigravity_api_key", "")

            # [YENİ] URL girdikten hemen sonra API Key sor (önceden dolu olsa bile göster)
            key_dialog2 = ctk.CTkInputDialog(
                text=f"Antigravity API Key:\n(Boş bırakırsan key gerektirmeyen moda geçilir)\nMevcut: {'****' + _existing_key[-4:] if len(_existing_key) > 4 else 'Yok'}",
                title="API Key")
            entered_key = key_dialog2.get_input()
            if entered_key is None: return  # iptal
            entered_key = entered_key.strip()
            # Boşsa mevcut key'i koru
            if not entered_key and _existing_key:
                entered_key = _existing_key

            import requests as _req
            models_url = url_input.replace("/v1/chat/completions", "").rstrip("/") + "/v1/models"
            headers = {"Authorization": f"Bearer {entered_key}"} if entered_key else {}

            try:
                r = _req.get(models_url, headers=headers, timeout=5)
                if r.status_code == 401:
                    self._err("❌ API Key geçersiz (401)!\nAntigravity Manager → API Proxy'den doğru key'i kopyalayın.")
                    return
                data = r.json()
                models = [f"AG: {m.get('id', '')}" if not str(m.get('id', '')).startswith("AG:") else m.get('id', '') for m in data.get("data", [])]

                if models:
                    cfg = {}
                    if os.path.exists(TRANS_CFG):
                        with open(TRANS_CFG, "r", encoding="utf-8") as f: cfg = json.load(f)
                    cfg["antigravity_url"] = url_input
                    if entered_key:
                        cfg["antigravity_api_key"] = entered_key  # [YENİ] Her zaman kaydet
                    if "available_models" not in cfg: cfg["available_models"] = {}
                    for m in models:
                        raw_id = m.replace("AG: ", "").replace("AG:", "")
                        cfg["available_models"][m] = {"model_name": raw_id, "provider": "antigravity"}
                    with open(TRANS_CFG, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=4, ensure_ascii=False)
                    for m in models:
                        if m not in MODELS: MODELS.insert(0, m)
                    key_msg = f"🔑 Key kaydedildi." if entered_key else "ℹ️ Key kullanılmadı."
                    self._ok(f"✅ Bağlantı başarılı!\n{len(models)} model eklendi.\n{key_msg}")
                else:
                    self._err("Model listesi boş döndü.")
            except Exception as e:
                self._err(f"Bağlantı başarısız: {e}\n\nAntigravity Manager'ın açık olduğundan emin olun.")

        _btn(c3, "⚡ Otomatik Bağlan & Modelleri Çek", _ag_connect, w=280).grid(row=2, column=0, padx=16, pady=(8, 14), sticky="w")

        return page

    def _get_key_stats(self):
        try:
            if os.path.exists(API_FILE):
                with open(API_FILE, 'r', encoding='utf-8') as f:
                    keys = [l.strip() for l in f if l.strip() and not l.startswith('#')]
                return f"{len(keys)} aktif anahtar mevcut"
        except: pass
        return "Anahtar dosyası okunamadı"

    def _load_key_list(self):
        self._key_list.delete(0, "end")
        try:
            if os.path.exists(API_FILE):
                with open(API_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        k = line.strip()
                        if k and not k.startswith('#'):
                            masked = k[:10] + "…" + k[-4:] if len(k) > 16 else k
                            self._key_list.insert("end", masked)
        except: pass

    def _refresh_keys(self):
        self._load_key_list()
        self._api_stats.configure(text=self._get_key_stats())

    def _add_keys(self):
        raw = self._new_key_var.get().strip()
        if not raw:
            return
        keys = [k.strip() for k in raw.split(',') if k.strip()]
        try:
            with open(API_FILE, 'a', encoding='utf-8') as f:
                for k in keys:
                    f.write(f"\n{k}")
            self._new_key_var.set("")
            self._refresh_keys()
            self._ok(f"{len(keys)} anahtar eklendi.")
        except Exception as e:
            self._err(str(e))

    def _del_key(self):
        sel = self._key_list.curselection()
        if not sel:
            return
        idx = sel[0]
        try:
            with open(API_FILE, 'r', encoding='utf-8') as f:
                lines = [l for l in f if l.strip() and not l.startswith('#')]
            if 0 <= idx < len(lines):
                lines.pop(idx)
                with open(API_FILE, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                self._refresh_keys()
        except Exception as e:
            self._err(str(e))

    def _clear_keys(self):
        if not messagebox.askyesno("Tüm Anahtarları Sil",
                "Tüm API anahtarları silinecek.\nEmin misiniz?", parent=self):
            return
        try:
            with open(API_FILE, 'w', encoding='utf-8') as f:
                f.write('')
            self._refresh_keys()
            self._ok("Tüm anahtarlar silindi.")
        except Exception as e:
            self._err(str(e))

    # ═══════════════════════════════════════════════ ADVANCED ═══
    def _build_advanced(self):
        page = self._scroll_frame(self._content)
        _label(page, "Gelişmiş Çeviri Ayarları", size=20, bold=True).pack(anchor="w", pady=(0, 16))

        cfg = load_trans_cfg()

        c1 = _card(page)
        c1.pack(fill="x", pady=(0, 12))
        c1.columnconfigure(1, weight=1)

        _label(c1, "Config.json Parametreleri", bold=True, color=CYAN).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14, 6), sticky="w")

        fields = [
            ("batch_size",            "Batch Boyutu (Satır)",        str(cfg.get('batch_size', 1))),
            ("timeout",               "Zaman Aşımı / Timeout (sn)",  str(cfg.get('timeout', 600))),
            ("delay_between_calls",   "API Gecikme (sn)",            str(cfg.get('delay_between_calls', 0))),
            ("max_retries",           "Max Tekrar (Retries)",        str(cfg.get('max_retries', 6))),
        ]
        self._adv_vars = {}
        for i, (key, label, default) in enumerate(fields):
            _label(c1, label).grid(row=i+1, column=0, padx=16, pady=6, sticky="w")
            v = tk.StringVar(value=default)
            self._adv_vars[key] = v
            _entry(c1, v, w=140).grid(row=i+1, column=1, padx=8, pady=6, sticky="w")

        _label(c1, "Zorla Çevir (No Cache)").grid(
            row=len(fields)+1, column=0, padx=16, pady=6, sticky="w")
        self._ignore_cache_var = tk.BooleanVar(value=bool(cfg.get('ignore_cache', False)))
        _switch(c1, "", self._ignore_cache_var).grid(
            row=len(fields)+1, column=1, padx=8, pady=6, sticky="w")

        c2 = _card(page)
        c2.pack(fill="x", pady=(0, 12))
        _label(c2, "Sistem Prompt (System Prompt)", bold=True, color=CYAN).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._prompt_box = ctk.CTkTextbox(c2, height=160,
            fg_color=PANEL, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(size=12), corner_radius=8)
        self._prompt_box.pack(fill="x", padx=16, pady=(0, 14))
        self._prompt_box.insert("1.0", cfg.get('system_prompt', ''))

        # ── Media / Context Identification ──────────────────────────────────
        msrc = cfg.get('media_sources', {})

        c3 = _card(page)
        c3.pack(fill="x", pady=(0, 12))
        c3.columnconfigure(1, weight=1)
        _label(c3, "🎬  Medya Tespiti & Context Kaynakları", bold=True, color=CYAN).grid(
            row=0, column=0, columnspan=2, padx=16, pady=(14, 6), sticky="w")
        ctk.CTkLabel(c3,
            text="Altyazı çevirisinden önce anime/dizi/film bilgisi hangi kaynaklardan çekilsin?",
            font=ctk.CTkFont(size=11), text_color=SUB).grid(
            row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="w")

        # TMDB API Key
        _label(c3, "TMDB API Key").grid(row=2, column=0, padx=16, pady=(4, 4), sticky="w")
        self._tmdb_key_var = tk.StringVar(value=cfg.get('tmdb_api_key', ''))
        _entry(c3, self._tmdb_key_var, w=360,
               placeholder_text="tmdb v3 read api key (film/dizi için)").grid(
            row=2, column=1, padx=(8, 16), pady=(4, 4), sticky="w")

        # Kaynak toggle'ları
        src_toggles = [
            ("jikan",        "Jikan / MyAnimeList  (anime — ücretsiz, key gereksiz)"),
            ("anilist",      "AniList GraphQL      (anime — ücretsiz, key gereksiz)"),
            ("kitsu",        "Kitsu                (anime — ücretsiz, key gereksiz)"),
            ("tvmaze",       "TVMaze               (Batı dizileri — ücretsiz)"),
            ("tmdb",         "TMDB                 (film & dizi — TMDB key gerekli)"),
            ("ai_fill_gaps", "AI ile Eksik Alanları Tamamla  (API üzerinden)"),
            ("ai_fallback",  "AI Geri Dönüş — hiç kaynak bulamazsa AI kullan"),
        ]
        self._msrc_vars = {}
        for idx, (key, lbl) in enumerate(src_toggles):
            v = tk.BooleanVar(value=bool(msrc.get(key, True)))
            self._msrc_vars[key] = v
            _switch(c3, lbl, v).grid(row=3+idx, column=0, columnspan=2,
                                      padx=16, pady=3, sticky="w")

        self._save_btn(page, "💾  Gelişmiş Ayarları Kaydet", self._save_advanced)
        return page

    def _save_advanced(self):
        cfg = {}
        for key, var in self._adv_vars.items():
            try:
                s = var.get()
                cfg[key] = float(s) if '.' in s else int(s)
            except: pass
        cfg['ignore_cache']   = self._ignore_cache_var.get()
        cfg['system_prompt']  = self._prompt_box.get("1.0", "end").rstrip()
        # ── Media sources ──────────────────────────────────────────
        tmdb_key = self._tmdb_key_var.get().strip()
        if tmdb_key:
            cfg['tmdb_api_key'] = tmdb_key
        cfg['media_sources'] = {k: v.get() for k, v in self._msrc_vars.items()}
        # -─────────────────────────────────────────────────────────
        try:
            save_trans_cfg(cfg)
            self._ok("Gelişmiş ayarlar kaydedildi!")
        except Exception as e:
            self._err(str(e))

    # ═══════════════════════════════════════════════ CANLI TEST ═══
    def _build_test(self):
        page = ctk.CTkFrame(self._content, fg_color=BG)
        _label(page, "Canlı Çeviri Testi", size=20, bold=True).pack(anchor="w", pady=(0, 6))
        _label(page, "Tek satır İngilizce metin yazın, anında Türkçe çevirisini görün.",
               color=SUB).pack(anchor="w", pady=(0, 16))

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x")

        # Model info card
        info_card = _card(top)
        info_card.pack(fill="x", pady=(0, 12))
        self._test_model_lbl = _label(info_card,
            f"Aktif Model: {self.prefs.get('ai_model', '—')}", color=CYAN, size=13)
        self._test_model_lbl.pack(anchor="w", padx=16, pady=(12, 4))
        _label(info_card,
            "Not: Model ve API ayarları 'AI & API' sayfasından değiştirilebilir.",
            color=SUB, size=11).pack(anchor="w", padx=16, pady=(0, 12))

        # Input card
        in_card = _card(top)
        in_card.pack(fill="x", pady=(0, 12))
        _label(in_card, "Test Metni (İngilizce)", bold=True, color=CYAN).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._test_input = ctk.CTkTextbox(in_card, height=80,
            fg_color=PANEL, border_color=BORDER, text_color=TEXT,
            font=ctk.CTkFont(size=13), corner_radius=8)
        self._test_input.pack(fill="x", padx=16, pady=(0, 10))

        btn_row = ctk.CTkFrame(in_card, fg_color="transparent")
        btn_row.pack(anchor="w", padx=16, pady=(0, 14))
        self._test_btn = _btn(btn_row, "▶  Çevir", self._run_test,
                              color=GREEN, hover="#059669", w=140)
        self._test_btn.pack(side="left", padx=(0, 10))
        _btn(btn_row, "🗑 Temizle", self._clear_test, color=PANEL,
             hover=CARD, w=110).pack(side="left")

        self._test_status = _label(btn_row, "", color=SUB)
        self._test_status.pack(side="left", padx=12)

        # Result card
        res_card = _card(page)
        res_card.pack(fill="x", pady=(0, 12))
        _label(res_card, "Çeviri Sonucu (Türkçe)", bold=True, color=PURPLE).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._test_result = ctk.CTkTextbox(res_card, height=100,
            fg_color=PANEL, border_color=BORDER, text_color=GREEN,
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=8,
            state="disabled")
        self._test_result.pack(fill="x", padx=16, pady=(0, 14))

        # History card
        hist_card = _card(page)
        hist_card.pack(fill="both", expand=True)
        _label(hist_card, "Test Geçmişi", bold=True, color=CYAN).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._test_hist = tk.Text(hist_card, bg="#08080f", fg=TEXT,
            font=("Consolas", 11), wrap="word",
            bd=0, highlightthickness=0, state="disabled")
        hs = ctk.CTkScrollbar(hist_card, command=self._test_hist.yview,
            button_color=BORDER, button_hover_color=PURPLE)
        self._test_hist.configure(yscrollcommand=hs.set)
        hs.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self._test_hist.pack(fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        self._test_hist.tag_configure("en",  foreground=CYAN)
        self._test_hist.tag_configure("tr",  foreground=GREEN)
        self._test_hist.tag_configure("sep", foreground=BORDER)
        self._test_hist.tag_configure("err", foreground=RED)

        return page

    def _clear_test(self):
        self._test_input.delete("1.0", "end")
        self._test_result.configure(state="normal")
        self._test_result.delete("1.0", "end")
        self._test_result.configure(state="disabled")

    def _run_test(self):
        text = self._test_input.get("1.0", "end").strip()
        if not text:
            return
        self._test_btn.configure(state="disabled")
        self._test_status.configure(text="Çeviriliyor…", text_color=YELLOW)
        threading.Thread(target=self._do_test, args=(text,), daemon=True).start()

    def _do_test(self, text):
        env = os.environ.copy()
        env["PYTHONPATH"]      = PARENT_DIR + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"]      = "1"
        try:
            import subprocess
            cmd = [sys.executable, os.path.join(PARENT_DIR, "translator.py"), "--test", text]
            res = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT, encoding="utf-8")
            result, original = res.strip(), text
        except Exception as e:
            result, original = f"[HATA] {str(e)}", text

        self._test_btn.configure(state="normal")
        is_err = result.startswith("[HATA]")
        self._test_status.configure(
            text="Hata!" if is_err else "Tamamlandı",
            text_color=RED if is_err else GREEN)

        self._test_result.configure(state="normal")
        self._test_result.delete("1.0", "end")
        self._test_result.insert("1.0", result)
        self._test_result.configure(state="disabled",
            text_color=RED if is_err else GREEN)

        self._test_hist.configure(state="normal")
        self._test_hist.insert("end", f"EN: {original}\n", "en")
        self._test_hist.insert("end", f"TR: {result}\n",   "err" if is_err else "tr")
        self._test_hist.insert("end", "─" * 60 + "\n",    "sep")
        self._test_hist.see("end")
        self._test_hist.configure(state="disabled")

    # ═══════════════════════════════════════════════ ARAÇLAR ═══
    def _build_tools(self):
        page = self._scroll_frame(self._content)
        _label(page, "🛠  Veri & Araçlar", size=20, bold=True).pack(anchor="w", pady=(0,4))
        _label(page, "Fandom sözlüğü, bölüm bağlamı ve çeviri raporlarını yönet.",
               color=SUB, size=12).pack(anchor="w", pady=(0,16))

        # ── CARD 1: Fandom Wiki Sözlüğü ─────────────────────────────────────
        c1 = _card(page)
        c1.pack(fill="x", pady=(0,12))
        _label(c1, "🎌  Fandom Wiki Sözlüğü", bold=True, color=CYAN).pack(anchor="w", padx=16, pady=(14,4))
        _label(c1, "Anime/dizi için karakter, beceri, lokasyon ve terim listesi otomatik çekilir.",
               color=SUB, size=11).pack(anchor="w", padx=16, pady=(0,8))

        fr = ctk.CTkFrame(c1, fg_color="transparent")
        fr.pack(fill="x", padx=16, pady=(0,6))
        self._gls_series_var = tk.StringVar()
        _entry(fr, self._gls_series_var, w=270,
               placeholder_text="Örn: Sword Art Online").pack(side="left", padx=(0,8))
        self._gls_fetch_btn = _btn(fr, "🔍 Çek", self._fetch_glossary, w=90)
        self._gls_fetch_btn.pack(side="left", padx=(0,6))
        _btn(fr, "🔄 Yenile", lambda: self._fetch_glossary(force=True),
             w=120, color="#1d4ed8", hover="#1e40af").pack(side="left")

        self._gls_status = _label(c1, "", color=SUB, size=12)
        self._gls_status.pack(anchor="w", padx=16, pady=(0,6))

        _label(c1, "Cache'teki Seriler:", color=TEXT, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(2,2))
        self._gls_list_frame = ctk.CTkScrollableFrame(
            c1, fg_color=PANEL, height=130, corner_radius=8)
        self._gls_list_frame.pack(fill="x", padx=16, pady=(0,14))
        self._refresh_glossary_list()

        # ── CARD 2: Bölüm Bağlamı ────────────────────────────────────────────
        c2 = _card(page)
        c2.pack(fill="x", pady=(0,12))
        _label(c2, "🔗  Bölüm Arası Bağlam", bold=True, color=CYAN).pack(
            anchor="w", padx=16, pady=(14,4))
        _label(c2, "Bölüm bittikten sonra bir sonraki bölüm için saklanan son çeviri satırları.",
               color=SUB, size=11).pack(anchor="w", padx=16, pady=(0,8))

        _label(c2, "Kaydedilen Seri/Bölümler:", color=TEXT, size=12, bold=True).pack(
            anchor="w", padx=16, pady=(2,2))
        self._ep_list_frame = ctk.CTkScrollableFrame(
            c2, fg_color=PANEL, height=110, corner_radius=8)
        self._ep_list_frame.pack(fill="x", padx=16, pady=(0,8))

        er = ctk.CTkFrame(c2, fg_color="transparent")
        er.pack(anchor="w", padx=16, pady=(0,14))
        _btn(er, "🔄 Yenile", self._refresh_ep_list, w=100,
             color=PANEL, hover=CARD).pack(side="left", padx=(0,8))
        _btn(er, "🗑 Tümünü Temizle", self._clear_all_ep,
             w=180, color=RED, hover="#dc2626").pack(side="left")
        self._refresh_ep_list()

        # ── CARD 3: Son Çeviri Raporları ──────────────────────────────────────
        c3 = _card(page)
        c3.pack(fill="x", pady=(0,12))
        _label(c3, "📊  Son Çeviri Raporları", bold=True, color=CYAN).pack(
            anchor="w", padx=16, pady=(14,4))
        _label(c3, "Her çeviri sonrası oluşturulan HTML kalite raporları. Çift tıkla veya Aç'a bas.",
               color=SUB, size=11).pack(anchor="w", padx=16, pady=(0,8))

        self._rpt_list_frame = ctk.CTkScrollableFrame(
            c3, fg_color=PANEL, height=130, corner_radius=8)
        self._rpt_list_frame.pack(fill="x", padx=16, pady=(0,8))
        _btn(c3, "🔄 Raporları Tara", self._refresh_report_list,
             w=180, color=PANEL, hover=CARD).pack(anchor="w", padx=16, pady=(0,14))
        self._refresh_report_list()

        return page

    # ── Fandom Sözlük yardımcıları ───────────────────────────────────────────
    def _auto_fetch_glossary_if_needed(self, series_title: str):
        """Çeviri başlarken seri adı biliniyorsa Fandom sözlüğünü arka planda çeker.
        Cache'te zaten varsa hiçbir şey yapmaz (hızlı)."""
        if not series_title or not series_title.strip():
            return
        series_title = series_title.strip()

        def _bg():
            try:
                import sys as _s
                if PARENT_DIR not in _s.path:
                    _s.path.insert(0, PARENT_DIR)
                from fandom_glossary import build_glossary
                entry = build_glossary(series_title, force_refresh=False, verbose=False)
                if entry and entry.get("terms"):
                    total = sum(len(v) for v in entry["terms"].values())
                    # GUI listesini ana thread'de güncelle
                    self.after(0, self._refresh_glossary_list)
                    self.after(0, lambda: print(
                        f"[Glossary] '{series_title}' → {total} terim (cache'den yüklendi)"))
                else:
                    # Yoksa çek (sessiz)
                    entry2 = build_glossary(series_title, force_refresh=False, verbose=True)
                    if entry2 and entry2.get("terms"):
                        self.after(0, self._refresh_glossary_list)
            except Exception as _e:
                print(f"[Glossary-Auto] {_e}")

        threading.Thread(target=_bg, daemon=True).start()

    def _refresh_glossary_list(self):
        for w in self._gls_list_frame.winfo_children():
            w.destroy()
        gls_file = os.path.join(PARENT_DIR, "series_glossary.json")
        if not os.path.isfile(gls_file):
            _label(self._gls_list_frame, "Henüz sözlük çekilmemiş.",
                   color=SUB, size=12).pack(anchor="w", padx=8, pady=4)
            return
        try:
            data = json.load(open(gls_file, "r", encoding="utf-8"))
        except Exception:
            _label(self._gls_list_frame, "Dosya okunamadı.",
                   color=RED, size=12).pack(anchor="w", padx=8)
            return
        if not data:
            _label(self._gls_list_frame, "Cache boş.",
                   color=SUB, size=12).pack(anchor="w", padx=8, pady=4)
            return
        for title, entry in data.items():
            wiki  = entry.get("wiki") or "—"
            total = sum(len(v) for v in entry.get("terms", {}).values())
            row = ctk.CTkFrame(self._gls_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            _label(row, f"  📚 {title}   wiki:{wiki}   {total} terim",
                   size=12, color=TEXT).pack(side="left", padx=4)
            _btn(row, "Sil", lambda t=title: self._delete_glossary(t),
                 w=60, color=RED, hover="#dc2626").pack(side="right", padx=4)

    def _delete_glossary(self, title):
        gls_file = os.path.join(PARENT_DIR, "series_glossary.json")
        try:
            data = json.load(open(gls_file, "r", encoding="utf-8"))
            data.pop(title, None)
            # Atomic yazma: önce temp dosyaya, sonra os.replace → crash güvenli
            import tempfile
            _tmp = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', suffix='.tmp',
                    dir=os.path.dirname(gls_file), delete=False
                ) as _f:
                    json.dump(data, _f, ensure_ascii=False, indent=2)
                    _tmp = _f.name
                os.replace(_tmp, gls_file)
            except Exception as _we:
                if _tmp and os.path.exists(_tmp):
                    try: os.unlink(_tmp)
                    except Exception: pass
                raise _we
            self._refresh_glossary_list()
            self._gls_status.configure(text=f"'{title}' silindi.", text_color=YELLOW)
        except Exception as e:
            self._err(str(e))

    def _fetch_glossary(self, force=False):
        series = self._gls_series_var.get().strip()
        if not series:
            self._err("Lütfen bir seri adı girin!")
            return
        self._gls_fetch_btn.configure(state="disabled")
        self._gls_status.configure(
            text=f"'{series}' için wiki aranıyor...", text_color=YELLOW)

        def _do():
            try:
                import sys as _s
                if PARENT_DIR not in _s.path:
                    _s.path.insert(0, PARENT_DIR)
                from fandom_glossary import build_glossary
                entry = build_glossary(series, force_refresh=force, verbose=False)
                if entry and entry.get("terms"):
                    total = sum(len(v) for v in entry["terms"].values())
                    msg, col = f"✅ {entry['wiki']}.fandom.com — {total} terim", GREEN
                else:
                    msg, col = f"❌ '{series}' için wiki bulunamadı.", RED
            except Exception as e:
                msg, col = f"Hata: {e}", RED
            self.after(0, lambda: [
                self._gls_status.configure(text=msg, text_color=col),
                self._gls_fetch_btn.configure(state="normal"),
                self._refresh_glossary_list(),
            ])
        threading.Thread(target=_do, daemon=True).start()

    # ── Episode Context yardımcıları ─────────────────────────────────────────
    def _refresh_ep_list(self):
        for w in self._ep_list_frame.winfo_children():
            w.destroy()
        ep_file = os.path.join(PARENT_DIR, "episode_context.json")
        if not os.path.isfile(ep_file):
            _label(self._ep_list_frame, "Henüz bölüm bağlamı kaydedilmemiş.",
                   color=SUB, size=12).pack(anchor="w", padx=8, pady=4)
            return
        try:
            data = json.load(open(ep_file, "r", encoding="utf-8"))
        except Exception:
            _label(self._ep_list_frame, "Dosya okunamadı.",
                   color=RED, size=12).pack(anchor="w", padx=8)
            return
        if not data:
            _label(self._ep_list_frame, "Cache boş.",
                   color=SUB, size=12).pack(anchor="w", padx=8, pady=4)
            return
        for key, entry in data.items():
            ep    = entry.get("episode", "?")
            pairs = len(entry.get("pairs", []))
            row = ctk.CTkFrame(self._ep_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            _label(row, f"  🔗 {key}   E{ep}   {pairs} çift",
                   size=12, color=TEXT).pack(side="left", padx=4)
            _btn(row, "Sil", lambda k=key: self._delete_ep(k),
                 w=60, color=RED, hover="#dc2626").pack(side="right", padx=4)

    def _delete_ep(self, key):
        ep_file = os.path.join(PARENT_DIR, "episode_context.json")
        try:
            data = json.load(open(ep_file, "r", encoding="utf-8"))
            data.pop(key, None)
            json.dump(data, open(ep_file, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            self._refresh_ep_list()
        except Exception as e:
            self._err(str(e))

    def _clear_all_ep(self):
        if not messagebox.askyesno("Tümünü Temizle",
                "Tüm bölüm bağlamları silinecek.\nEmin misiniz?", parent=self):
            return
        ep_file = os.path.join(PARENT_DIR, "episode_context.json")
        try:
            json.dump({}, open(ep_file, "w", encoding="utf-8"), indent=2)
            self._refresh_ep_list()
            self._ok("Tüm bölüm bağlamları temizlendi.")
        except Exception as e:
            self._err(str(e))

    # ── Rapor yardımcıları ───────────────────────────────────────────────────
    def _refresh_report_list(self):
        for w in self._rpt_list_frame.winfo_children():
            w.destroy()

        # Arama dizinleri: PARENT_DIR + Desktop + son kullanılan çıktı klasörleri
        search_dirs = [PARENT_DIR, os.path.expanduser("~/Desktop")]

        # Son kullanılan giriş yolundan Çevrilenler/ klasörünü bul
        try:
            _src = self._input_path.get().strip() if hasattr(self, '_input_path') else ""
            if _src and os.path.exists(_src):
                _base = _src if os.path.isdir(_src) else os.path.dirname(_src)
                _out = os.path.join(_base, "Çevrilenler")
                if os.path.isdir(_out) and _out not in search_dirs:
                    search_dirs.append(_out)
                if _base not in search_dirs:
                    search_dirs.append(_base)
        except Exception:
            pass

        # Yaygın anime dizin köklerini de tara (D:/Anime, E:/Anime vb.)
        for _drive in ("D:/", "E:/", "C:/Users/Administrator/Videos"):
            _anime = os.path.join(_drive, "Anime")
            if os.path.isdir(_anime) and _anime not in search_dirs:
                search_dirs.append(_anime)

        reports = []
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.endswith(".report.html"):
                            full = os.path.join(root, f)
                            reports.append((full, os.path.getmtime(full)))
                    if len(reports) >= 50:
                        break
            except Exception:
                pass
        reports.sort(key=lambda x: x[1], reverse=True)
        if not reports:
            _label(self._rpt_list_frame, "Henüz rapor oluşturulmamış. Bir çeviri yapın.",
                   color=SUB, size=12).pack(anchor="w", padx=8, pady=4)
            return
        import datetime
        for path, mtime in reports[:15]:
            fname = os.path.basename(path)
            dt    = datetime.datetime.fromtimestamp(mtime).strftime("%d.%m %H:%M")
            row = ctk.CTkFrame(self._rpt_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            _label(row, f"  📄 {fname}  [{dt}]", size=11, color=TEXT).pack(
                side="left", padx=4)
            _btn(row, "Aç", lambda p=path: self._open_report(p),
                 w=60, color=PURPLE, hover=PURH).pack(side="right", padx=4)

    def _open_report(self, path):
        try:
            import subprocess
            if os.name == "nt":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self._err(f"Rapor açılamadı: {e}")

    # ═══════════════════════════════════════════════ RESET ═══
    def _build_reset(self):
        page = ctk.CTkFrame(self._content, fg_color=BG)
        _label(page, "Ayarları Sıfırla", size=20, bold=True).pack(anchor="w", pady=(0, 16))

        c = _card(page)
        c.pack(fill="x", pady=(0, 12))
        _label(c, "⚠️  Tüm tercihler varsayılan değerlere döndürülür.", color=YELLOW, size=14).pack(
            padx=16, pady=(16, 8), anchor="w")
        _label(c, "Bu işlem geri alınamaz.", color=SUB).pack(
            padx=16, pady=(0, 16), anchor="w")
        _btn(c, "🔄  SIFIRLA", self._do_reset, color=RED, hover="#dc2626", w=200).pack(
            padx=16, pady=(0, 16), anchor="w")
        return page

    def _do_reset(self):
        if not messagebox.askyesno("Sıfırla",
                "Tüm ayarlar varsayılan değerlere sıfırlanacak.\nEmin misiniz?",
                parent=self):
            return
        try:
            if os.path.exists(PREFS_FILE):
                os.remove(PREFS_FILE)
            self.prefs = load_prefs()
            self._pages.clear()
            for k, b in self._nav_btns.items():
                b.configure(fg_color="transparent", text_color=SUB)
            self._cur = None
            self._show("home")
            self._ok("Ayarlar sıfırlandı.")
        except Exception as e:
            self._err(str(e))


if __name__ == "__main__":
    app = App()
    app.mainloop()
