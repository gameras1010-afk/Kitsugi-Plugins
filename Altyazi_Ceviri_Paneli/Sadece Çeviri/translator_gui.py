import os
import sys
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PREFS_FILE  = os.path.join(SCRIPT_DIR, '..', 'user_preferences.json')

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PURPLE      = "#7c3aed"
PURPLE_L    = "#a855f7"
PURPLE_D    = "#5b21b6"
BG          = "#0f0f1a"
PANEL       = "#1a1a2e"
CARD        = "#16213e"
ENTRY_BG    = "#0d1117"
SUCCESS_C   = "#22c55e"
DANGER_C    = "#ef4444"
WARNING_C   = "#f59e0b"
TEXT        = "#e2e8f0"
MUTED       = "#64748b"

MODELS_DEFAULT = [
    "google/gemini-2.0-flash-001",
    "google/gemini-flash-1.5-8b",
    "deepseek/deepseek-r1",
    "microsoft/phi-4",
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
]


def load_prefs():
    d = {
        'translate': True, 'clean_sub': True, 'smart_merge': True,
        'sub_format': 'ASS', 'ai_model': 'google/gemini-2.0-flash-001',
        'custom_api_keys_path': None, 'source_lang': 'English',
        'target_lang': 'Turkish', 'per_file_delay': 15,
        'max_byte_batch': 2000, 'only_english': True,
        'max_line_length': 75, 'line_merge_mode': 'default',
        'max_retries': 6, 'force_translate': True,
        'nsfw_mode': False, 'hentai_glossary': False,
        'natural_dialogue': True, 'protect_positioning': True,
        'font_size_mode': 'normalize', 'custom_font_size': 80,
        'simple_mode': True,
    }
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                d.update(json.load(f))
        except:
            pass
    return d


def save_prefs(prefs):
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=4)
    except:
        pass


def load_available_models():
    try:
        cfg_path = os.path.join(SCRIPT_DIR, '..', 'translator_config.json')
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        names = [v.get('model_name', k)
                 for k, v in cfg.get('available_models', {}).items()]
        if names:
            return names
    except:
        pass
    return MODELS_DEFAULT


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎌  Altyazı Çevirici")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        self.prefs      = load_prefs()
        self.running    = False
        self.path_var   = tk.StringVar()

        self._build()

    # ──────────────────────────────── BUILD ────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar()
        self._main_area()

    # ─────────────────────────────── SIDEBAR ───────────────────────────────

    def _sidebar(self):
        sb = ctk.CTkFrame(self, width=260, fg_color=PANEL, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(99, weight=1)

        # Logo / title
        logo = ctk.CTkFrame(sb, fg_color=PURPLE_D, corner_radius=0, height=64)
        logo.grid(row=0, column=0, sticky="ew")
        logo.grid_propagate(False)
        ctk.CTkLabel(logo, text="🎌  Altyazı Çevirici",
                     font=ctk.CTkFont("Segoe UI", 15, "bold"),
                     text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # Navigation buttons
        self.nav_btns = {}
        nav_items = [
            ("🏠  Ana Ekran",   "home"),
            ("⚙️   Temel Ayarlar", "basic"),
            ("🔬  Gelişmiş",    "adv"),
            ("🔑  API Yönetimi","api"),
        ]
        for i, (label, key) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                sb, text=label, anchor="w",
                font=ctk.CTkFont("Segoe UI", 13),
                fg_color="transparent", hover_color=PURPLE_D,
                text_color=TEXT, height=42, corner_radius=8,
                command=lambda k=key: self._show_page(k)
            )
            btn.grid(row=i, column=0, padx=10, pady=3, sticky="ew")
            self.nav_btns[key] = btn

        # Status card at bottom
        self.status_card = ctk.CTkFrame(sb, fg_color=CARD, corner_radius=10)
        self.status_card.grid(row=99, column=0, padx=10, pady=14, sticky="sew")
        self.status_dot = ctk.CTkLabel(self.status_card, text="●  Hazır",
                                       text_color=SUCCESS_C,
                                       font=ctk.CTkFont("Segoe UI", 12, "bold"))
        self.status_dot.pack(padx=12, pady=6)
        self.model_lbl = ctk.CTkLabel(self.status_card,
                                      text=self.prefs.get('ai_model','—'),
                                      text_color=MUTED,
                                      font=ctk.CTkFont("Segoe UI", 9),
                                      wraplength=220)
        self.model_lbl.pack(padx=12, pady=(0,8))

    # ─────────────────────────────── MAIN ──────────────────────────────────

    def _main_area(self):
        self.pages: dict[str, ctk.CTkFrame] = {}
        container = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        for key, builder in [
            ("home",  self._page_home),
            ("basic", self._page_basic),
            ("adv",   self._page_adv),
            ("api",   self._page_api),
        ]:
            frame = ctk.CTkFrame(container, fg_color=BG, corner_radius=0)
            frame.grid(row=0, column=0, sticky="nsew")
            builder(frame)
            self.pages[key] = frame

        self._show_page("home")

    def _show_page(self, key):
        for k, f in self.pages.items():
            f.tkraise() if k == key else None
        self.pages[key].tkraise()
        for k, btn in self.nav_btns.items():
            btn.configure(fg_color=PURPLE if k == key else "transparent")

    # ─────────────────────────────── HOME PAGE ─────────────────────────────

    def _page_home(self, parent):
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # ── Path picker card ──
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=14)
        card.grid(row=0, column=0, padx=20, pady=(20, 8), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text="📁  Klasör veya Dosya Seç",
                     font=ctk.CTkFont("Segoe UI", 13, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, columnspan=3,
                                               padx=16, pady=(14, 6), sticky="w")

        path_entry = ctk.CTkEntry(card, textvariable=self.path_var,
                                  placeholder_text="Klasör yolu buraya gelecek…",
                                  font=ctk.CTkFont("Consolas", 11),
                                  fg_color=ENTRY_BG, border_color=PURPLE_D,
                                  text_color=TEXT, height=38, corner_radius=8)
        path_entry.grid(row=1, column=0, padx=(16,6), pady=6, sticky="ew")

        ctk.CTkButton(card, text="Klasör", width=90, height=38,
                      fg_color=PURPLE, hover_color=PURPLE_D, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 12, "bold"),
                      command=self._pick_folder).grid(row=1, column=1, padx=3, pady=6)

        ctk.CTkButton(card, text="Dosya", width=80, height=38,
                      fg_color=CARD, hover_color=PURPLE_D, corner_radius=8,
                      font=ctk.CTkFont("Segoe UI", 12),
                      command=self._pick_file).grid(row=1, column=2, padx=(3,16), pady=6)

        # ── Action buttons ──
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=3, padx=16, pady=(4, 16), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶   ÇEVİRİYİ BAŞLAT",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            fg_color=PURPLE, hover_color=PURPLE_D,
            height=46, corner_radius=10,
            command=self._start)
        self.start_btn.grid(row=0, column=0, padx=(0,6), sticky="ew")

        self.scan_btn = ctk.CTkButton(
            btn_row, text="🔍  Otomatik Tara (CWD)",
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=CARD, hover_color=PURPLE_D,
            height=46, corner_radius=10,
            command=self._auto_scan)
        self.scan_btn.grid(row=0, column=1, padx=(6,0), sticky="ew")

        # ── Progress ──
        self.progress = ctk.CTkProgressBar(parent, height=6,
                                           fg_color=CARD,
                                           progress_color=PURPLE)
        self.progress.grid(row=1, column=0, padx=20, pady=2, sticky="ew")
        self.progress.set(0)

        # ── Log box ──
        log_frame = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=14)
        log_frame.grid(row=2, column=0, padx=20, pady=(4,20), sticky="nsew")
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(log_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(10,4))
        ctk.CTkLabel(hdr, text="📋  Çıktı / Log",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=PURPLE_L).pack(side="left")
        ctk.CTkButton(hdr, text="🗑  Temizle", width=90, height=26,
                      fg_color=CARD, hover_color=PURPLE_D, corner_radius=6,
                      font=ctk.CTkFont("Segoe UI", 10),
                      command=self._clear_log).pack(side="right")

        self.log_box = tk.Text(
            log_frame, bg="#080810", fg=TEXT,
            font=("Consolas", 9), relief="flat",
            state="disabled", wrap="word",
            insertbackground=TEXT,
            selectbackground=PURPLE_D,
            borderwidth=0, highlightthickness=0
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

        sb = ctk.CTkScrollbar(log_frame, command=self.log_box.yview,
                              button_color=PURPLE_D, button_hover_color=PURPLE)
        sb.grid(row=1, column=1, sticky="ns", pady=(0,10), padx=(0,6))
        self.log_box.configure(yscrollcommand=sb.set)

        self._setup_log_tags()
        self._redirect_stdout()

    # ─────────────────────────────── BASIC PAGE ────────────────────────────

    def _page_basic(self, parent):
        parent.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(parent, text="⚙️  Temel Ayarlar",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, padx=24, pady=(20,10), sticky="w")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                        scrollbar_button_color=PURPLE_D)
        scroll.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        scroll.grid_columnconfigure((0,1), weight=1)

        # Model
        self._card_label(scroll, "🤖  AI Modeli", 0, 0, colspan=2)
        self.model_var = tk.StringVar(value=self.prefs.get('ai_model', MODELS_DEFAULT[0]))
        ctk.CTkComboBox(scroll, values=load_available_models(),
                        variable=self.model_var, state="readonly",
                        fg_color=ENTRY_BG, button_color=PURPLE,
                        dropdown_fg_color=PANEL,
                        font=ctk.CTkFont("Segoe UI", 11),
                        width=340, height=36
                        ).grid(row=1, column=0, columnspan=2, padx=16, pady=(2,12), sticky="w")

        # Format + Mod yan yana
        self._card_label(scroll, "📄  Çıktı Formatı", 2, 0)
        self._card_label(scroll, "🚀  Basit Mod (Simple Mode)", 2, 1)
        self.format_var = tk.StringVar(value=self.prefs.get('sub_format','ASS'))
        ctk.CTkComboBox(scroll, values=['ASS','SRT','VTT','ALL'],
                        variable=self.format_var, state="readonly",
                        fg_color=ENTRY_BG, button_color=PURPLE,
                        dropdown_fg_color=PANEL, width=140, height=34
                        ).grid(row=3, column=0, padx=16, pady=(2,14), sticky="w")

        self.simple_var = ctk.BooleanVar(value=self.prefs.get('simple_mode', True))
        ctk.CTkSwitch(scroll, text="", variable=self.simple_var,
                      progress_color=PURPLE, button_color=PURPLE_L
                      ).grid(row=3, column=1, padx=16, pady=(2,14), sticky="w")

        # Toggles grid
        toggles = [
            ('translate',           '🌐  AI Çeviri Yap'),
            ('clean_sub',           '🧹  Altyazı Temizliği'),
            ('smart_merge',         '🔗  Akıllı Birleştirme'),
            ('only_english',        '🇬🇧  Sadece İngilizce'),
            ('force_translate',     '🔄  Zorla Çevir (No Cache)'),
            ('natural_dialogue',    '💬  Doğal Türkçe Diyalog'),
            ('protect_positioning', '📍  Konumlandırma Koruması'),
            ('nsfw_mode',           '🔞  +18 / NSFW Modu'),
            ('hentai_glossary',     '📖  Hentai Sözlüğü (120+)'),
        ]
        self.toggle_vars = {}
        r = 4
        for i, (key, label) in enumerate(toggles):
            col = i % 2
            if col == 0 and i > 0:
                r += 1
            var = ctk.BooleanVar(value=self.prefs.get(key, False))
            self.toggle_vars[key] = var
            card = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=10)
            card.grid(row=r, column=col, padx=8, pady=5, sticky="ew")
            ctk.CTkSwitch(card, text=label, variable=var,
                          progress_color=PURPLE, button_color=PURPLE_L,
                          font=ctk.CTkFont("Segoe UI", 11)
                          ).pack(padx=14, pady=10, anchor="w")

        r += 2
        # Font modu
        self._card_label(scroll, "🔤  Font Boyutu Modu", r, 0)
        r += 1
        self.font_mode_var = tk.StringVar(value=self.prefs.get('font_size_mode','normalize'))
        ctk.CTkComboBox(scroll, values=['preserve','normalize','custom'],
                        variable=self.font_mode_var, state="readonly",
                        fg_color=ENTRY_BG, button_color=PURPLE,
                        dropdown_fg_color=PANEL, width=180, height=34
                        ).grid(row=r, column=0, padx=16, pady=(2,14), sticky="w")

        r += 1
        ctk.CTkButton(scroll, text="💾  Ayarları Kaydet",
                      fg_color=PURPLE, hover_color=PURPLE_D,
                      font=ctk.CTkFont("Segoe UI", 13, "bold"),
                      height=42, corner_radius=10,
                      command=self._save).grid(row=r, column=0, columnspan=2,
                                               padx=16, pady=16, sticky="ew")

    # ─────────────────────────────── ADVANCED PAGE ─────────────────────────

    def _page_adv(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="🔬  Gelişmiş Ayarlar",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, padx=24, pady=(20,10), sticky="w")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                        scrollbar_button_color=PURPLE_D)
        scroll.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        scroll.grid_columnconfigure((0,1), weight=1)

        fields = [
            ('source_lang',    'Kaynak Dil',              'English'),
            ('target_lang',    'Hedef Dil',               'Turkish'),
            ('per_file_delay', 'Dosya Arası Bekleme (sn)', 15),
            ('max_byte_batch', 'Max Byte/Batch',           2000),
            ('max_line_length','Max Satır Uzunluğu',       75),
            ('max_retries',    'Max Tekrar (Retries)',      6),
        ]
        self.adv_vars = {}
        for i, (key, label, default) in enumerate(fields):
            col = i % 2
            row = (i // 2) * 2
            self._card_label(scroll, label, row, col)
            var = tk.StringVar(value=str(self.prefs.get(key, default)))
            self.adv_vars[key] = var
            ctk.CTkEntry(scroll, textvariable=var,
                         fg_color=ENTRY_BG, border_color=PURPLE_D,
                         text_color=TEXT, height=36, width=180
                         ).grid(row=row+1, column=col, padx=16, pady=(2,14), sticky="w")

        r = (len(fields) // 2) * 2 + 2
        self._card_label(scroll, "Satır Birleştirme Modu", r, 0)
        r += 1
        self.merge_var = tk.StringVar(value=self.prefs.get('line_merge_mode','default'))
        ctk.CTkComboBox(scroll, values=['default','aggressive','conservative','none'],
                        variable=self.merge_var, state="readonly",
                        fg_color=ENTRY_BG, button_color=PURPLE,
                        dropdown_fg_color=PANEL, width=200, height=34
                        ).grid(row=r, column=0, padx=16, pady=(2,14), sticky="w")

        r += 1
        ctk.CTkButton(scroll, text="💾  Kaydet",
                      fg_color=PURPLE, hover_color=PURPLE_D,
                      font=ctk.CTkFont("Segoe UI", 13, "bold"),
                      height=42, corner_radius=10,
                      command=self._save).grid(row=r, column=0, columnspan=2,
                                               padx=16, pady=16, sticky="ew")

    # ─────────────────────────────── API PAGE ──────────────────────────────

    def _page_api(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(parent, text="🔑  API Yönetimi",
                     font=ctk.CTkFont("Segoe UI", 16, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, padx=24, pady=(20,10), sticky="w")

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                        scrollbar_button_color=PURPLE_D)
        scroll.grid(row=1, column=0, padx=16, pady=(0,16), sticky="nsew")
        parent.grid_rowconfigure(1, weight=1)
        scroll.grid_columnconfigure(0, weight=1)

        # API Dosyası
        card1 = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=12)
        card1.grid(row=0, column=0, padx=6, pady=8, sticky="ew")
        card1.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card1, text="📂  API Anahtarları Dosyası",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, columnspan=2,
                                               padx=14, pady=(12,4), sticky="w")
        default_keys = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'api_keys.txt'))
        self.api_path_var = tk.StringVar(
            value=self.prefs.get('custom_api_keys_path') or default_keys)
        ctk.CTkEntry(card1, textvariable=self.api_path_var,
                     fg_color=ENTRY_BG, border_color=PURPLE_D,
                     text_color=TEXT, height=36
                     ).grid(row=1, column=0, padx=(14,6), pady=4, sticky="ew")
        ctk.CTkButton(card1, text="Seç", width=70, fg_color=PURPLE,
                      hover_color=PURPLE_D, corner_radius=8,
                      command=self._pick_api_file
                      ).grid(row=1, column=1, padx=(0,14), pady=4)
        ctk.CTkButton(card1, text="👁  Anahtarları Görüntüle",
                      fg_color="transparent", hover_color=PURPLE_D,
                      border_color=PURPLE, border_width=1,
                      font=ctk.CTkFont("Segoe UI", 11),
                      height=34, corner_radius=8,
                      command=self._show_keys
                      ).grid(row=2, column=0, columnspan=2, padx=14, pady=(4,14), sticky="w")

        # Yeni Key Ekle
        card2 = ctk.CTkFrame(scroll, fg_color=CARD, corner_radius=12)
        card2.grid(row=1, column=0, padx=6, pady=8, sticky="ew")
        card2.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card2, text="➕  Yeni API Anahtarı Ekle",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=PURPLE_L).grid(row=0, column=0, columnspan=2,
                                               padx=14, pady=(12,4), sticky="w")
        self.new_key_var = tk.StringVar()
        ctk.CTkEntry(card2, textvariable=self.new_key_var,
                     placeholder_text="sk-or-v1-...",
                     show="*",
                     fg_color=ENTRY_BG, border_color=PURPLE_D,
                     text_color=TEXT, height=36
                     ).grid(row=1, column=0, padx=(14,6), pady=4, sticky="ew")
        ctk.CTkButton(card2, text="Ekle", width=70, fg_color=PURPLE,
                      hover_color=PURPLE_D, corner_radius=8,
                      command=self._add_key
                      ).grid(row=1, column=1, padx=(0,14), pady=4)
        ctk.CTkLabel(card2, text="Birden fazla anahtar için virgülle ayır",
                     font=ctk.CTkFont("Segoe UI", 9), text_color=MUTED
                     ).grid(row=2, column=0, columnspan=2, padx=14, pady=(0,12), sticky="w")

    # ─────────────────────────────── HELPERS ───────────────────────────────

    def _card_label(self, parent, text, row, col, colspan=1):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont("Segoe UI", 11),
                     text_color=MUTED
                     ).grid(row=row, column=col, columnspan=colspan,
                            padx=16, pady=(10,2), sticky="w")

    def _setup_log_tags(self):
        pairs = [
            ("green",  SUCCESS_C), ("red",    DANGER_C),
            ("yellow", WARNING_C), ("cyan",   "#22d3ee"),
            ("magenta",PURPLE_L),  ("blue",   "#60a5fa"),
            ("white",  TEXT),      ("grey",   MUTED),
        ]
        for name, color in pairs:
            self.log_box.tag_configure(name, foreground=color)

    def _redirect_stdout(self):
        import re
        log = self.log_box
        ansi = {
            '31':'red','91':'red','32':'green','92':'green',
            '33':'yellow','93':'yellow','34':'blue','94':'blue',
            '35':'magenta','95':'magenta','36':'cyan','96':'cyan',
            '37':'white','90':'grey',
        }

        class _Redir:
            def write(_, text):
                log.configure(state="normal")
                parts = re.split(r'\x1b\[([0-9;]*)m', text)
                tag = "white"
                for i, part in enumerate(parts):
                    if i % 2 == 0:
                        if part:
                            log.insert(tk.END, part, tag)
                    else:
                        codes = part.split(';')
                        for c in codes:
                            if c in ('0',''):
                                tag = "white"
                            elif c in ansi:
                                tag = ansi[c]
                log.see(tk.END)
                log.configure(state="disabled")
                log.update_idletasks()
            def flush(_): pass

        sys.stdout = _Redir()

    def _log(self, msg, tag="white"):
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, msg, tag)
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state="disabled")

    def _pick_folder(self):
        p = filedialog.askdirectory(title="Çevrilecek Klasörü Seç")
        if p:
            self.path_var.set(p)

    def _pick_file(self):
        p = filedialog.askopenfilename(
            title="Dosya Seç",
            filetypes=[("Altyazı/Video","*.ass *.ssa *.srt *.vtt *.mkv *.mp4 *.avi *.webm"),
                       ("Tümü","*.*")])
        if p:
            self.path_var.set(p)

    def _pick_api_file(self):
        p = filedialog.askopenfilename(title="API Dosyası Seç",
                                       filetypes=[("Metin","*.txt"),("Tümü","*.*")])
        if p:
            self.api_path_var.set(p)

    def _add_key(self):
        raw = self.new_key_var.get().strip()
        if not raw:
            return
        target = self.api_path_var.get().strip() or os.path.join(SCRIPT_DIR,'..','api_keys.txt')
        try:
            keys = [k.strip() for k in raw.split(',') if k.strip()]
            with open(target, 'a', encoding='utf-8') as f:
                for k in keys:
                    f.write(f"\n{k}")
            self.new_key_var.set('')
            self._log(f"✓ {len(keys)} anahtar eklendi.\n", "green")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def _show_keys(self):
        target = self.api_path_var.get().strip()
        if not os.path.exists(target):
            messagebox.showwarning("Uyarı", "Dosya bulunamadı.")
            return
        with open(target, 'r', encoding='utf-8') as f:
            content = f.read()
        win = ctk.CTkToplevel(self)
        win.title("API Anahtarları")
        win.geometry("620x440")
        win.configure(fg_color=PANEL)
        tb = tk.Text(win, bg=ENTRY_BG, fg=TEXT, font=("Consolas", 10),
                     relief="flat", borderwidth=0)
        tb.pack(fill="both", expand=True, padx=12, pady=12)
        tb.insert(tk.END, content)
        tb.configure(state="disabled")

    def _save(self):
        self.prefs['ai_model']        = self.model_var.get()
        self.prefs['sub_format']      = self.format_var.get()
        self.prefs['simple_mode']     = bool(self.simple_var.get())
        self.prefs['font_size_mode']  = self.font_mode_var.get()
        self.prefs['line_merge_mode'] = self.merge_var.get()
        for key, var in self.toggle_vars.items():
            self.prefs[key] = bool(var.get())
        for key, var in self.adv_vars.items():
            raw = var.get().strip()
            try:
                self.prefs[key] = float(raw) if '.' in raw else int(raw)
            except ValueError:
                self.prefs[key] = raw
        default_keys = os.path.normpath(os.path.join(SCRIPT_DIR,'..','api_keys.txt'))
        api_p = self.api_path_var.get().strip()
        self.prefs['custom_api_keys_path'] = None if api_p == default_keys else api_p
        save_prefs(self.prefs)
        self.model_lbl.configure(text=self.prefs.get('ai_model','—'))
        self._log("✓ Ayarlar kaydedildi.\n", "green")

    def _set_busy(self, busy: bool):
        self.running = busy
        state = "disabled" if busy else "normal"
        self.start_btn.configure(state=state,
                                 fg_color=MUTED if busy else PURPLE)
        self.scan_btn.configure(state=state)
        if busy:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
            self.status_dot.configure(text="⏳  Çeviri Yapılıyor…", text_color=WARNING_C)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")
            self.progress.set(0)
            self.status_dot.configure(text="●  Hazır", text_color=SUCCESS_C)

    def _run(self, path, auto):
        try:
            self._save()
            from manual_translator import scan_and_process_directory
            scan_and_process_directory(path, self.prefs, auto_scan_mode=auto)
        except Exception as e:
            print(f"[HATA] {e}")
        finally:
            self.after(0, lambda: self._set_busy(False))

    def _start(self):
        if self.running:
            return
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("Uyarı", "Önce klasör veya dosya seçin.")
            return
        if not os.path.exists(path):
            messagebox.showerror("Hata", f"Geçersiz yol:\n{path}")
            return
        self._set_busy(True)
        threading.Thread(target=self._run, args=(path, False), daemon=True).start()

    def _auto_scan(self):
        if self.running:
            return
        self._set_busy(True)
        threading.Thread(target=self._run, args=(os.getcwd(), True), daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()
