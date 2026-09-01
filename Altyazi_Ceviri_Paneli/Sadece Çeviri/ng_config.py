"""
ng_config.py — Renkler, sabitler, config yükleme/kaydetme
"""
import os, json, sys
from datetime import datetime

# ─── Dizin tespiti ────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # EXE çalışırken: kullanıcı verisi EXE'nin yanında
    BASE_DIR   = os.path.dirname(sys.executable)
    PARENT_DIR = BASE_DIR
    # _MEIPASS = PyInstaller'ın geçici çıkarma dizini (modüller burada)
    _MEIPASS = getattr(sys, '_MEIPASS', BASE_DIR)
    if _MEIPASS not in sys.path:
        sys.path.insert(0, _MEIPASS)
else:
    BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(BASE_DIR)

SCRIPT_TRANSLATOR  = os.path.join(BASE_DIR,   "manual_translator.py")
SCRIPT_QA          = os.path.join(PARENT_DIR, "ass_qa_checker.py")
SCRIPT_GLOSSARY    = os.path.join(PARENT_DIR, "fandom_glossary.py")
PREFS_FILE         = os.path.join(PARENT_DIR, "user_preferences.json")
TRANS_CFG          = os.path.join(PARENT_DIR, "translator_config.json")
API_FILE           = os.path.join(PARENT_DIR, "api_keys.txt")
EX_FILE            = os.path.join(PARENT_DIR, "exhausted_api_keys.txt")
GLOSSARY_FILE      = os.path.join(PARENT_DIR, "series_glossary.json")
REPORT_DIR         = os.path.join(BASE_DIR,   "Çevrilenler")

# Tüm HTML raporların toplandığı merkezi klasör (Sadece Çeviri/reports/)
REPORTS_CENTRAL_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_CENTRAL_DIR, exist_ok=True)   # yoksa oluştur


def collect_html_reports(source_path: str) -> list[str]:
    """
    source_path (dosya ya da klasör) yakınındaki Çevrilenler/ içindeki
    tüm .report.html dosyalarını REPORTS_CENTRAL_DIR'e kopyalar.
    Kopyalanan dosyaların yollarını döndürür.
    """
    import shutil, glob as _glob
    if not source_path or not os.path.exists(source_path):
        return []

    # Kaynak dizinini belirle
    src_dir = source_path if os.path.isdir(source_path) else os.path.dirname(source_path)

    # Taranacak yerler: kaynak dizin + Çevrilenler/ alt klasörü
    search_roots = [
        src_dir,
        os.path.join(src_dir, "Çevrilenler"),
        os.path.join(src_dir, "Çevrilecekler"),
    ]

    copied = []
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        # Özyinelemeli tara
        for dirpath, _, files in os.walk(root):
            for fname in files:
                if not fname.lower().endswith(".html"):
                    continue
                src_file = os.path.join(dirpath, fname)
                dst_file = os.path.join(REPORTS_CENTRAL_DIR, fname)
                # Eğer aynı dosya zaten varsa üzerine yaz (daha yeniyse)
                try:
                    if (not os.path.exists(dst_file) or
                            os.path.getmtime(src_file) > os.path.getmtime(dst_file)):
                        shutil.copy2(src_file, dst_file)
                        copied.append(dst_file)
                except Exception:
                    pass
    return copied

# ─── Cyberpunk renk paleti (glassmorphic) ────────────────────────────────────
C = {
    "BG":        "#0D0E15",
    "BG2":       "#161825",
    "SIDEBAR":   "rgba(0,0,0,0.35)",
    "PANEL":     "rgba(0,0,0,0.40)",
    "CARD":      "rgba(0,0,0,0.30)",
    "BORDER":    "rgba(255,255,255,0.10)",
    "PURPLE":    "#7c3aed",
    "PURPLE2":   "#9d5ff5",
    "CYAN":      "#00d4ff",
    "CYAN2":     "#64ffda",
    "GREEN":     "#10b981",
    "RED":       "#ef4444",
    "YELLOW":    "#f59e0b",
    "PINK":      "#ec4899",
    "TEXT":      "#e2e8f0",
    "SUB":       "#dde3f5",
    "MUTED":     "#bec8e8",
    "GLASS":     "rgba(255,255,255,0.06)",
}

# ─── Model listesi ────────────────────────────────────────────────────────────
DEFAULT_MODELS = [
    "deepseek/deepseek-chat:free",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-r1:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-2.0-flash-001",
    "google/gemini-2.5-pro-preview-03-25",
    "google/gemini-flash-1.5-8b",
    "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-haiku",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "deepseek/deepseek-r1",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-nemo",
    "microsoft/phi-4",
]

# ─── Config yükleme / kaydetme ───────────────────────────────────────────────
def load_prefs() -> dict:
    defaults = {
        "ai_model":              "google/gemini-2.0-flash-001",
        "source_lang":           "English",
        "target_lang":           "Turkish",
        "batch_size":            10,
        "max_byte_batch":        2000,
        "only_english":          True,
        "use_fandom_glossary":   True,
        "generate_html_report":  True,
        "use_episode_context":   True,
        "nsfw_mode":             False,
        "protect_positioning":   True,
        "romaji_block":          True,
        "skip_romaji_mode":      True,   # romaji_block ile senkron — translator bu anahtarı kullanır
        "use_style_suffix_detection": True,
        "use_song_lyrics_pass":  True,
        "use_karaoke_collapse":  True,
        "force_no_style":        False,
        "content_detect":        True,
        "cps_shorten":           False,
        "max_line_length":       75,
        "force_translate":       True,
        "natural_dialogue":      True,
        # ── Çeviri motor kontrol ───────────────────────────────────────────────
        "translate":             True,   # False = çeviri kapalı (sadece temizleme)
        "clean_sub":             True,   # Alt yazı temizleme
        "smart_merge":           True,   # Akıllı satır birleştirme
        "simple_mode":           True,   # True=her dosya bağımsız, False=gelişmiş key rotation
        "sub_format":            "ASS",  # Çıktı formatı: ASS, SRT, VTT, ALL
        "per_file_delay":        15,     # Dosyalar arası bekleme süresi (sn)
        # ── UI tercihler ─────────────────────────────────────────────────────
        "ui_theme":               "nexus",
        "ui_sound":               True,
        "delay":                  0,
        "delay_sn":               0,
        # ── Otomatik tespit edilen meta (translator doldurur, UI default None) ─
        "media_title":            None,
        "episode":                None,
        "season":                 None,
    }
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults

def save_prefs(p: dict):
    existing = {}
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.update(p)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

def load_trans_cfg() -> dict:
    defaults = {
        "batch_size": 10, "timeout": 600,
        "delay_between_calls": 0, "max_retries": 6,
        "system_prompt": "", "ignore_cache": False,
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
    }
    if os.path.exists(TRANS_CFG):
        try:
            with open(TRANS_CFG, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Boş string değerler default'u ezmemeli (özellikle api_url)
            for k, v in loaded.items():
                if isinstance(v, str) and v.strip() == "" and k in defaults and isinstance(defaults[k], str) and defaults[k]:
                    continue  # boş string geldi, default'u koru
                defaults[k] = v
        except Exception:
            pass
    return defaults


def save_trans_cfg(cfg: dict):
    existing = {}
    if os.path.exists(TRANS_CFG):
        try:
            with open(TRANS_CFG, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.update(cfg)
    with open(TRANS_CFG, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=4, ensure_ascii=False)

def load_glossary() -> dict:
    if os.path.exists(GLOSSARY_FILE):
        try:
            with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def api_counts() -> tuple[int, int]:
    def _c(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return sum(1 for l in f if l.strip())
        except Exception:
            return 0
    return _c(API_FILE), _c(EX_FILE)

def total_terms(glossary: dict) -> int:
    total = 0
    for data in glossary.values():
        for lst in data.get("terms", {}).values():
            total += len(lst)
    return total

def get_models() -> list[str]:
    models = list(DEFAULT_MODELS)
    try:
        cfg = load_trans_cfg()
        for k, v in cfg.get("available_models", {}).items():
            if k not in models:
                models.insert(0, k)
    except Exception:
        pass
    return models
