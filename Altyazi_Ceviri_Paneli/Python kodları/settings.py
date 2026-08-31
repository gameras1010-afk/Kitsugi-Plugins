import os
import json
from colorama import Fore, Style

# ── diskcache: SQLite tabanli cache (26MB+ JSON dosyasinin migrasyonu) ────────
try:
    import diskcache as _dc
    _DISKCACHE_AVAILABLE = True
except ImportError:
    _DISKCACHE_AVAILABLE = False

# Sabitler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Arsiv_AutoClean")
HISTORY_FILE = os.path.join(DOWNLOAD_DIR, "history.txt")
LOG_DIR = os.path.join(BASE_DIR, "logs")
ARCHIVE_DIR = os.path.join(LOG_DIR, "archive")
LOG_FILE = os.path.join(BASE_DIR, "hatalar.txt")
PREFS_FILE = os.path.join(BASE_DIR, "user_preferences.json")
CACHE_FILE = os.path.join(BASE_DIR, "anime_translations_cache.json")  # Eski JSON (legacy)
CACHE_DIR = os.path.join(BASE_DIR, "anime_translations_cache_db")      # Yeni diskcache dizini
API_FILE = os.path.join(BASE_DIR, "api_keys.txt")
EXHAUSTED_FILE = os.path.join(BASE_DIR, "exhausted_api_keys.txt")
KEYS_FILE = API_FILE  # Alias (manual_translator.py ile uyumluluk)

# ── diskcache singelton: tek bir Cache nesnesi tum session boyunca kullanilir ──
_disk_cache_instance = None

def _get_disk_cache():
    """Thread-safe singleton diskcache Cache nesnesi dondurur."""
    global _disk_cache_instance
    if _disk_cache_instance is None and _DISKCACHE_AVAILABLE:
        try:
            _disk_cache_instance = _dc.Cache(
                directory=CACHE_DIR,
                size_limit=512 * 1024 * 1024,  # 512 MB limit
                eviction_policy='least-recently-used',
                statistics=False,
            )
            # Eski JSON dosyasindan tek seferlik migrasyon
            _migrate_json_to_diskcache(_disk_cache_instance)
        except Exception as _e:
            print(f"[Cache] diskcache baslatulamadi: {_e} — JSON fallback")
            _disk_cache_instance = None
    return _disk_cache_instance


def _migrate_json_to_diskcache(dc_cache) -> None:
    """Eski anime_translations_cache.json varsa diskcache'e aktar, sonra .migrated yap."""
    migrated_flag = CACHE_FILE + '.migrated'
    if os.path.exists(migrated_flag) or not os.path.exists(CACHE_FILE):
        return  # Zaten migre edildi veya kaynak yok
    try:
        size_mb = os.path.getsize(CACHE_FILE) / 1024 / 1024
        print(f"[Cache] JSON migrasyon basliyor: {size_mb:.1f} MB...")
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        count = 0
        for k, v in old_data.items():
            dc_cache.set(k, v, expire=None)  # TTL yok = kalici
            count += 1
        # Migrasyon bayragi koy, JSON'u sil
        open(migrated_flag, 'w').write(f"migrated {count} keys")
        os.rename(CACHE_FILE, CACHE_FILE + '.bak')
        print(f"[Cache] Migrasyon tamamlandi: {count} giris | JSON -> diskcache SQLite")
    except Exception as e:
        print(f"[Cache] Migrasyon hatasi: {e} — JSON fallback kullanilacak")

# Global Durum
IS_EXITING = False
MERGE_FAIL_HALT = False  # Merge başarısız olduğunda tüm botu durdurur

# Güvenlik Konseyi Varsayılanları
DEFAULT_SAFETY_CONFIG = {
    "ENABLE_NUDENET": True,
    "ENABLE_DEEPGHS": True,
    "ENABLE_HENTAI_MOSAIC": True,
    "ENABLE_ANIMENET": True,
    "ENABLE_YAHOO_NSFW": True,

    # --- RELAXED MODE THRESHOLDS (User Request) ---
    "NUDENET_EXPOSED_THR": 0.75, # Daha esnek (0.65 -> 0.75)
    "NUDENET_COVERED_THR": 0.85, # Mayolara izin ver (0.60 -> 0.85)
    "DEEPGHS_HENTAI_THR": 0.70,  # Fan-service izin ver (0.40 -> 0.70)
    "DEEPGHS_PORN_THR": 0.75,    # Sadece hardcore engelle
    "HENTAI_VAR_THR": 15.0,      # Blur hassasiyetini düşür (Gökyüzü banlanmasın)
    "ANIMENET_STRICT": False     # Ecchi serbest
}

def load_prefs():
    defaults = {
        'translate': True,
        'telegram': True,
        'download_sub': True,
        'download_vid': True,
        'process_vid': True,
        'download_cover': True,
        'clean_sub': True,
        'auto_delete': True,
        'delete_after_upload_vid': True,
        'delete_after_upload_sub': True,
        'delete_after_upload_cover': True,
        'delete_after_upload_clip': True, # [FIX] Varsayılan olarak klipleri sil
        'turbo_mode': True,      # Turbo İndirme (Multi-thread - Video)
        'telegram_turbo': True,  # Turbo Upload (Telegram - Multi-conn)
        'logging_enabled': True, # Hata günlüğü
        'sub_format': 'ASS',   # ASS, SRT, VTT, ALL
        'vid_format': 'MKV',   # MKV, MP4
        'img_format': 'JPG',   # JPG, PNG
        'upscale_image': True, # AI-Like Upscale (FFmpeg)
        'smart_cover': True,   # AniList HD Cover Search
        'ai_model': 'google/gemini-2.0-flash-001', # Varsayılan Model
        'nsfw_mode': True,       # NSFW / Hentai Çeviri Modu (Enabled for accurate adult content translation)
        'custom_api_keys_path': None, # Özelleştirilmiş Anahtar Yolu
        'target_url': "https://hstream.moe/search?order=oldest-uploads",
        'start_page': 1,
        'start_index': 1,
        'headless': True, # Gizli Tarayıcı (User Requested Default)
        'resume_url': "", # Kaldığı yer
        # Sosyal Medya Modu (clip / promo)
        'social_mode_type': 'promo', 
        'social_duration': 60,       # Varsayılan Hedef Süre
        'social_min_segment': 5,    # Varsayılan Min Parça
        'semi_auto_mode': False,    # [NEW] Yarı Otomatik Mod (Her bölüm sonrası onay ister)
        # Bildirim Ayarları
        'notifications_enabled': False,
        'discord_webhook': "",
        'notify_on_start': False,
        'notify_on_finish': True,
        'notify_on_error': True,
        'show_thumbnails': True, # Resim Göster
        # Filtre Ayarları
        'filter_genres_block': [], 
        'filter_genres_allow': [],
        'min_score': 0,
        # Gelişmiş Video Ayarları
        'video_encoder': 'h264_nvenc',
        'video_quality': 26,
        'video_preset': 'p4',
        'audio_codec': 'aac',
        'audio_bitrate': '160k',
        # Safety Models (Mahşerin 5 Atlısı)
        'safety_models': DEFAULT_SAFETY_CONFIG.copy(),
        'stop_on_error': True,  # [ZERO TOLERANCE] En ufak hatada dur!
        # Subtitle Timing Adjustment
        'subtitle_time_offset': 0.0,  # Timing offset disabled (was -0.5)
        # Konumlandırma/Karaoke Koruması (Çeviri Ayarları)
        'protect_positioning': False,  # False = SİL, True = KORU (çevrilmez ama kalır)
        # ── HStream İndirici Entegrasyon Bayrakları ──
        # hstream_mode: True = prompt şişmesi önleme (additional_context, glossary, sliding_window kapalı)
        # fail_safe_translation: True = hiç satır çevrilmezse tüm batch anında durdurulur
        'hstream_mode': True,
        'fail_safe_translation': True,
    }
    try:
        if os.path.exists(PREFS_FILE):
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                # Nested dict update fix
                if 'safety_models' in saved:
                    # Merge saved safety options with defaults (in case of new keys)
                    defaults['safety_models'].update(saved['safety_models'])
                    del saved['safety_models'] # Remove to avoid overwriting the merged dict
                defaults.update(saved)
    except Exception as e:
        print(f"{Fore.RED}[SETTINGS] Load Error: {e}{Style.RESET_ALL} (Using Defaults)")
    return defaults

def save_prefs(prefs):
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=4)
    except Exception as e:
        print(f"{Fore.RED}[SETTINGS] Save Error: {e}{Style.RESET_ALL}")

def load_translation_cache():
    """
    diskcache mevcutsa SQLite tabanli cache dondurur (dict-like API).
    Yoksa eski JSON dosyasindan yukler (fallback).
    Her iki durumda da caller icin seffaf bir dict/cache nesnesi doner.
    """
    dc = _get_disk_cache()
    if dc is not None:
        return dc  # diskcache dict-like interface: dc[key] = val, key in dc, del dc[key]
    # JSON fallback
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[SETTINGS] Cache Load Error: {e}")
    return {}


def normalize_cache_key(text: str) -> str:
    """
    Cache anahtarini normalize eder: buyuk/kucuk harf farki olmadan ayni metin
    ayni key'e eslesir. MD5 hash kullanimiyla bellek tasarrufu da saglar.
    Ornek: 'Hello World' ve 'hello world' artik ayni cache entry.
    """
    import hashlib
    return hashlib.md5(text.lower().strip().encode('utf-8', errors='replace')).hexdigest()


def save_translation_cache(cache):
    """
    diskcache kullanimdaysa otomatik persist eder — cagrilmasina gerek yok.
    JSON fallback modu: sinir kontrol ederek dosyaya yazar.
    """
    dc = _get_disk_cache()
    if dc is not None:
        # diskcache otomatik persist eder, burada birseyler yapmaya gerek yok.
        # Ama cache dict ise (JSON fallback'ten geliyorsa) diskcache'e aktar
        if isinstance(cache, dict):
            for k, v in list(cache.items())[-5000:]:  # Son 5000 yeni girisi ekle
                dc.set(k, v)
        return
    # JSON fallback
    try:
        MAX_CACHE_SIZE = 50_000
        if len(cache) > MAX_CACHE_SIZE:
            keys_to_remove = list(cache.keys())[:len(cache) - MAX_CACHE_SIZE]
            for k in keys_to_remove:
                del cache[k]
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[SETTINGS] Cache Save Error: {e}")

def clear_translation_cache():
    """Önbelleği temizler (dosyayı siler)."""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"{Fore.GREEN}   ✅ Çeviri önbelleği silindi.{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}   ⚠️ Önbellek dosyası zaten yok.{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}   [!] Önbellek silinemedi: {e}{Style.RESET_ALL}")
        return False

def get_api_stats():
    """Gemini API anahtarlarının durumunu döndürür."""
    try:
        total = 0
        exhausted = 0
        active = 0
        
        # 1. Toplam API Sayısı
        if os.path.exists(API_FILE):
            with open(API_FILE, 'r', encoding='utf-8') as f:
                keys = [k.strip() for k in f if k.strip()]
                total = len(keys)
        
        # 2. Tükenmişler
        if os.path.exists(EXHAUSTED_FILE):
            with open(EXHAUSTED_FILE, 'r', encoding='utf-8') as f:
                ex_keys = [k.strip() for k in f if k.strip()]
                exhausted = len(ex_keys)
        
        # 3. Hesapla
        active = total - exhausted
        if active < 0: active = 0 # Dosya senkronizasyonu bozuksa
        
        return f"{Fore.GREEN}{active}{Style.RESET_ALL} Aktif / {Fore.RED}{exhausted}{Style.RESET_ALL} Tükenmiş (Toplam: {total})"
    except:
        return f"{Fore.RED}Veri alınamadı{Style.RESET_ALL}"

# --- GEÇMİŞ YÖNETİMİ ---
def load_history():
    """Geçmiş dosyasını küme (set) olarak yükler."""
    history = set()
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line: history.add(line)
        except Exception as e:
             print(f"[SETTINGS] History Load Error: {e}")
    return history

def add_to_history(url):
    """URL'yi geçmişe ekler."""
    try:
        with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
    except Exception as e:
        print(f"{Fore.RED}[!] Geçmişe yazılamadı: {e}{Style.RESET_ALL}")

def is_in_history(url):
    """URL geçmişte var mı kontrol eder."""
    # Verimli olması için her seferinde load yapmayalım, çağıran yer seti tutsun
    # Ancak basitlik için burada load yapabiliriz veya main loopta set tutabiliriz.
    # Güvenli olan load yapmaktır (multithread vs için) ama yavaş olabilir.
    # Şimdilik dosya okuma yapalım (kısa dosyalar için sorun olmaz).
    hist = load_history()
    return url in hist
