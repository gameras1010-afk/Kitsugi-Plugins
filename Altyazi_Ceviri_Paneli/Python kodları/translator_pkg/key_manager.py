"""
translator_pkg/key_manager.py
=============================
KeyManager — API key yönetimi.
"""
import os, re, sys, json, time, threading
import requests

import os
import sys
try: import _no_window  # CMD pencerelerini gizle  # noqa
except ImportError: pass
import json
import time
import requests
import re
from colorama import Fore, Style
import settings

# ASS Tag Referans — junk satir onleme (son savunma katmani)
try:
    from ass_tag_reference import is_vector_clip_junk as _atr_clip_junk, is_drawing_line as _atr_drawing
    _ATR_OK = True
except ImportError:
    _ATR_OK = False
    def _atr_clip_junk(t): return (False, '')
    def _atr_drawing(t):   return bool(re.search(r'\\p[1-9]\b', t))

# ASS Content Classifier — tum A1-A14 kurallari (son savunma birincil motoru)
# Icerdigi kurallar: drawing, karaoke, CJK, symbol, invisible alpha,
# per-char typeset (A14), clip junk (A13), gradient, stil sonek vs.
try:
    from ass_content_classifier import classify_line as _acc_classify_line
    _ACC_OK = True
except ImportError:
    _ACC_OK = False
    _acc_classify_line = None

# Tenacity: akilli API retry (ustel geri cekilme + jitter)
try:
    from tenacity import (
        retry, stop_after_attempt, wait_exponential,
        retry_if_exception_type, wait_random_exponential
    )
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False

# httpx: persistent HTTP session (TCP bağlantısını yeniden kullanır, %10-15 hızlı)
try:
    import httpx as _httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

# PyBreaker: Circuit Breaker Pattern
# 5 ardisik hatada 60sn devre keser (API hammering onler)
try:
    import pybreaker as _pybreaker
    _api_circuit_breaker = _pybreaker.CircuitBreaker(
        fail_max=5,          # 5 ardisik hatada devreyi ac
        reset_timeout=60,    # 60sn sonra half-open'a gec
    )
    _PYBREAKER_AVAILABLE = True
except ImportError:
    _PYBREAKER_AVAILABLE = False
    _api_circuit_breaker = None

# CRITICAL FIX: Use sys.executable for PyInstaller paths, not current working directory!
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(SCRIPT_DIR, "api_keys.txt")
STATUS_FILE = os.path.join(SCRIPT_DIR, "keys_status.json")
EXHAUSTED_FILE = os.path.join(SCRIPT_DIR, "exhausted_api_keys.txt")
API_KEYS_FILE = os.path.join(SCRIPT_DIR, "api_keys.txt") # Added for consistency with usage

class KeyManager:
    def __init__(self):
        self.keys = []
        self.status = {}
        self.current_index = 0
        # Key bazında 429 cooldown takibi: {key: timestamp_when_limited}
        self._rate_limited: dict = {}
        self.COOLDOWN_SEC = 65  # Key başına cooldown (saniye)
        # Model seviyesi global rate limit takibi
        self._global_429_streak = 0
        self._global_429_backoff = [0, 90, 180, 300, 300]
        # ══ GLOBAL 429 ERKEN DURDURMA ══════════════════════════════════
        # Art arda 429'larda kalan keyleri boşa harcama
        self._consec_429 = 0           # Art arda kaç 429 aldık
        self.GLOBAL_429_THRESHOLD = 5  # Bu kadar 429 → global limit var
        self._global_block_until = 0   # Bu timestamp'e kadar yeni deneme yapma
        # ══ PROAKTİF RATE LİMİTER ════════════════════════════
        # OpenRouter dokümanı: limit PER-KEY değil, HESAP SEVİYESİNDE GLOBAL
        # "Making additional API keys will not affect your rate limits"
        # Ücretli modeller için OpenRouter limiti yok ama Google upstream ~20-60 RPM
        # Güvenli tahmin: 20 RPM (Google'ın en kısıtlı penceresi)
        self._req_timestamps: list = []   # Son 60sn istek zaman damgaları
        # account_rpm_limit: user_preferences.json'dan oku, varsayılan 20
        _rpm_default = 20
        try:
            import json as _json, os as _os
            _pref_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'user_preferences.json')
            if _os.path.exists(_pref_path):
                _p = _json.load(open(_pref_path, encoding='utf-8'))
                _rpm_default = int(_p.get('account_rpm_limit', 20))
        except Exception:
            pass
        self.ACCOUNT_RPM_LIMIT = _rpm_default
        self.RPM_SAFETY = 0.80            # %80'e gelince fren
        self.load_keys()
        self.load_status()

    def record_request(self):
        """Her API isteğinde çağır — sliding window sayacına ekler."""
        import time as _t
        now = _t.time()
        self._req_timestamps.append(now)
        # 60 saniyeden eski kayıtları temizle
        self._req_timestamps = [ts for ts in self._req_timestamps if now - ts < 60]

    def proactive_throttle(self):
        """
        API isteğinden ÖNCE çağır.
        Dakika limiti dolmak üzereyse kısa bekler → 429 önlenir.
        """
        import time as _t
        now = _t.time()
        self._req_timestamps = [ts for ts in self._req_timestamps if now - ts < 60]
        # OpenRouter: limit hesap seviyesinde global — key sayısı çarpmıyoruz
        throttle_at = int(self.ACCOUNT_RPM_LIMIT * self.RPM_SAFETY)  # 20 * 0.80 = 16
        recent = len(self._req_timestamps)
        if recent >= throttle_at:
            oldest = min(self._req_timestamps) if self._req_timestamps else now
            window_remaining = max(1.0, 60 - (now - oldest))
            wait = window_remaining / max(1, recent - throttle_at + 1)
            wait = min(wait, 15)  # max 15sn bekle
            print(f"\033[33m   [⏱] Proaktif fren: {recent}/{throttle_at} istek/dk → {wait:.1f}sn bekleniyor...\033[0m")
            _t.sleep(wait)

    def load_keys(self):
        """
        Load API keys from file.
        CRITICAL: Always reload from file to get fresh list after deletions.
        """
        self.keys = []
        
        if not os.path.exists(KEYS_FILE):
            print(f"{Fore.RED}[!] api_keys.txt bulunamadı!{Style.RESET_ALL}")
            return
        
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.keys.append(line)
            
            if self.keys:
                print(f"{Fore.CYAN}[INFO] {len(self.keys)} API anahtarı yüklendi{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}[!] api_keys.txt boş!{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}[!] Key yükleme hatası: {e}{Style.RESET_ALL}")

    def load_status(self):
        if os.path.exists(STATUS_FILE):
             try:
                 with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                     self.status = json.load(f)
             except: self.status = {}

    def save_status(self):
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.status, f, indent=4)

    # ── GÜNLÜK 402 KALIICI TAKİP ───────────────────────────────────────
    # 402 = model günlük kota doldu. UTC gece yarısında sıfırlanır.
    # Bu süre içinde aynı key tekrar denenmez — şimdiki gibi oturum başında
    # sıfırlanmaz, disküstü key_status.json'dan kalıcı olarak yüklenir.
    # ───────────────────────────────────────────────────────────
    def _utc_daily_reset_ts(self) -> float:
        """Bugünkü UTC gece yarısının Unix timestamp'ini döndür."""
        import datetime
        now_utc = datetime.datetime.utcnow()
        midnight = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        return midnight.timestamp()

    def save_402_key(self, key: str, model: str):
        """
        402 alan key'i model bazında keys_status.json'a yaz.
        Yapı: status['_daily_402'][model] = [key1, key2, ...]
        """
        import time as _time
        self.load_status()  # Guncel durumu oku
        daily = self.status.setdefault('_daily_402', {})
        # Önce eski gunun kayıtlarını temizle
        today_reset = self._utc_daily_reset_ts()
        _reset_ts_key = '_daily_402_date'
        if self.status.get(_reset_ts_key, 0) < today_reset:
            # Yeni gün başladı — tüm 402 kayıtları sıfırla
            self.status['_daily_402'] = {}
            daily = self.status['_daily_402']
            self.status[_reset_ts_key] = today_reset
        # Key listesine ekle
        keys_for_model = daily.setdefault(model, [])
        if key not in keys_for_model:
            keys_for_model.append(key)
        self.save_status()

    def load_402_keys(self, model: str) -> set:
        """
        Daha önce 402 almış ve bugün hala geçerli key'leri yükle.
        Eğer güe yenilendi (UTC gece yarısı geçtiyse) → boş set dön.
        """
        self.load_status()
        today_reset = self._utc_daily_reset_ts()
        _reset_ts_key = '_daily_402_date'
        if self.status.get(_reset_ts_key, 0) < today_reset:
            # Yeni gün — sıfırla ve boş dön
            self.status['_daily_402'] = {}
            self.status[_reset_ts_key] = today_reset
            self.save_status()
            return set()
        return set(self.status.get('_daily_402', {}).get(model, []))

    def get_valid_key(self):
        # Listede anahtar kalmadıysa bitir
        if not self.keys:
            return None

        # CRITICAL FIX: Eski status kontrolünü KALDIR!
        # Sadece mevcut anahtarı döndür, status.json'u YOKSAY
        if self.current_index >= len(self.keys):
            self.current_index = 0
        
        key = self.keys[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.keys)
        
        return key

    def mark_as_exhausted(self, key, reason="402"):
        """
        Mark a key as exhausted - REMOVE from api_keys.txt and ADD to exhausted file.
        Only call this for REAL credit exhaustion (401 invalid / confirmed no credit).
        For model daily limits, use rotate_key() instead.
        """
        print(f"{Fore.YELLOW}   [!] Key kaldiriliyor [{reason}]: {key[:25]}...{Style.RESET_ALL}")
        
        # 1. Log to exhausted file
        try:
            with open(EXHAUSTED_FILE, "a", encoding="utf-8") as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{key}\n")  # Sadece key (timestamp yorum satiri yapiyordu)
            print(f"{Fore.GREEN}   [OK] exhausted_api_keys.txt'ye eklendi{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[!] Exhausted log yazılamadı: {e}{Style.RESET_ALL}")
        
        # 2. REMOVE from api_keys.txt
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                all_keys = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            updated_keys = [k for k in all_keys if k != key]
            
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                for k in updated_keys:
                    f.write(f"{k}\n")
            
            print(f"{Fore.GREEN}   [OK] api_keys.txt'den silindi ({len(all_keys)} -> {len(updated_keys)}){Style.RESET_ALL}")
            self.keys = updated_keys
            
        except Exception as e:
            print(f"{Fore.RED}[!] Key silinemedi: {e}{Style.RESET_ALL}")

    def mark_rate_limited(self, key: str):
        """429 alan keyi gecici cooldown listesine ekle.
        3 art arda 429 → global limit tespiti → kalan keyleri deneme, 65sn bekle.
        """
        import time as _time
        now = _time.time()
        self._rate_limited[key] = now
        self._consec_429 += 1
        if self._consec_429 >= self.GLOBAL_429_THRESHOLD and self._global_block_until <= now:
            self._global_block_until = now + self.COOLDOWN_SEC
            print(f"{Fore.RED}   [⛔ GLOBAL 429] {self._consec_429} art arda 429 — global limit! "
                  f"{self.COOLDOWN_SEC}sn kalan keyler denenmeden bekleniyor...{Style.RESET_ALL}")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'Global rate limit! {self._consec_429} art arda 429 — {self.COOLDOWN_SEC}sn bekleniyor', 'negative', 8000)
            except Exception: pass

    def reset_global_streak(self):
        """Başarılı çeviri — ardışık 429 sayacını sıfırla."""
        self._global_429_streak = 0
        if self._consec_429 > 0:
            self._consec_429 = 0

    def is_rate_limited(self, key: str) -> bool:
        """Key hala cooldown'da mı?"""
        import time as _time
        ts = self._rate_limited.get(key)
        if ts is None:
            return False
        if _time.time() - ts >= self.COOLDOWN_SEC:
            del self._rate_limited[key]  # Cooldown bitti, temizle
            return False
        return True

    def get_next_available_key(self, skip_402_set: set = None) -> str | None:
        """
        Cooldown'da olmayan VE 402 listesinde olmayan ilk key'i döndür.
        Global 429 bloğu aktifse önce onu bekler, sonra key arar.
        """
        import time as _time
        if not self.keys:
            return None
        skip_402 = skip_402_set or set()
        total = len(self.keys)

        # 0. Global 429 bloğu aktif mi?
        now = _time.time()
        if self._global_block_until > now:
            wait = self._global_block_until - now
            print(f"{Fore.YELLOW}   [⛔ GLOBAL BLOK] {wait:.1f}sn bekleniyor (kalan keyler denenmedi)...{Style.RESET_ALL}")
            _time.sleep(wait)
            # Blok bitti — sadece sayacı sıfırla, per-key cooldown'lar doğal sona ersin
            self._consec_429 = 0
            self._global_block_until = 0
            print(f"{Fore.GREEN}   [⛔ GLOBAL BLOK] Bekleme bitti, yeniden deneniyor...{Style.RESET_ALL}")

        # 1. Aninda kullanılabilir key var mı?
        for i in range(total):
            idx = (self.current_index + i) % total
            key = self.keys[idx]
            if key in skip_402:
                continue
            if not self.is_rate_limited(key):
                self.current_index = (idx + 1) % total
                return key

        # 2. Hepsi cooldown'da — en erken biten key'i bul ve bekle
        now = _time.time()
        candidates = [
            (ts + self.COOLDOWN_SEC - now, key)
            for key, ts in self._rate_limited.items()
            if key not in skip_402 and key in self.keys
        ]
        if candidates:
            wait_sec, best_key = min(candidates)
            wait_sec = max(wait_sec, 0.5)
            print(f"{Fore.YELLOW}   [⏳] Tüm keyler cooldown'da — {wait_sec:.1f}sn bekleniyor...{Style.RESET_ALL}")
            _time.sleep(wait_sec)
            idx = self.keys.index(best_key) if best_key in self.keys else 0
            self.current_index = (idx + 1) % total
            return best_key

        return None  # Hiç key kalmadı

    def rotate_key(self):
        """
        Sadece bir sonraki key'e gecis yap (exhausted'a ATMA).
        Model gunluk limiti veya gecici hatalar icin kullan.
        """
        if self.current_index >= len(self.keys):
            self.current_index = 0
        key = self.keys[self.current_index] if self.keys else None
        self.current_index = (self.current_index + 1) % max(len(self.keys), 1)
        return key

    def remove_key_permanently(self, key):
        # DEPRECATED: This function is no longer used
        pass

