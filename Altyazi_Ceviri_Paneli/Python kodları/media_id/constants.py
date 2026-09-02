"""
media_id/constants.py
=====================
Sabitler, cache ve yardımcı fonksiyonlar.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional

"""
media_identifier.py — Akilli Medya Tanima ve Metadata Sistemi
=============================================================
Anime / dizi / film alt yazi dosyalari icin otomatik medya tespiti.

Pipeline (sirasi ile):
  1. CACHE → Aynı seri daha önce sorgulandıysa anında döner (API yok)
  2. Jikan v4 (MAL) → Anime odaklı, ücretsiz, key yok
  3. AniList GraphQL → Anime+manga, ücretsiz, key yok
  4. Kitsu API → Anime listesi, ücretsiz, key yok
  5. TVMaze → Yabancı dizi/film, ücretsiz, key yok
  6. TMDB → Film+dizi geniş veritabanı, ücretsiz API key gerekli
  7. AI Fallback → Yapay zeka ile isim tespiti + eksik alan doldurma

Her kaynak bağımsız toggle ile açılıp kapatılabilir.
Eksik alan → AI ile anında doldurulur.
Sonuçlar JSON cache'e kaydedilir (TTL: 7 gün).
"""

import os
import re
import sys
import json
import time
import hashlib
import datetime
import requests
from colorama import Fore, Style

# Offline DB (AniDB + manami-project) — guvenli import
try:
    import offline_db_manager as _offdb
    _OFFLINE_DB_AVAILABLE = True
except ImportError:
    _OFFLINE_DB_AVAILABLE = False

# Windows terminali cp1254 kullanir — Japonca karakterler icin UTF-8'e gecir
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────
# BÖLÜM 1: YAPILANDIRMA
# ──────────────────────────────────────────────────────────────

if getattr(sys, 'frozen', False):
    _SCRIPT_DIR = os.path.dirname(sys.executable)
else:
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_FILE    = os.path.join(_SCRIPT_DIR, "anime_context_cache.json")
CONFIG_FILE   = os.path.join(_SCRIPT_DIR, "translator_config.json")
CACHE_TTL_DAYS = 7          # Kaç gün cache geçerli
REQUEST_TIMEOUT = 10        # API zaman aşımı (saniye)
REQUEST_DELAY   = 0.4       # API'lar arası bekleme (rate limit koruması, saniye)

# ──────────────────────────────────────────────────────────────
# BÖLÜM 2: KAYNAK TOGGLE'LARI
# Bu dict'i translator_config.json / user_preferences.json ile
# de kontrol edebilirsin. Varsayılan: hepsi açık.
# ──────────────────────────────────────────────────────────────

DEFAULT_SOURCE_CONFIG = {
    "jikan":    True,   # MAL / Jikan — anime
    "anilist":  True,   # AniList GraphQL — anime + manga
    "kitsu":    True,   # Kitsu — anime
    "tvmaze":   True,   # TVMaze — yabancı dizi/film
    "tmdb":     True,   # TMDB — geniş veritabanı (key gerekli)
    "ai_fallback":    True,   # Yapay zekayla isim tespiti
    "ai_fill_gaps":   True,   # Eksik alanları yapay zekayla doldur
}

def _load_source_config() -> dict:
    """translator_config.json'dan kaynak ayarlarını oku."""
    cfg = DEFAULT_SOURCE_CONFIG.copy()
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            media_cfg = raw.get("media_sources", {})
            cfg.update(media_cfg)
    except Exception:
        pass
    return cfg

def _get_tmdb_key() -> str:
    """translator_config.json'dan TMDB API anahtarını oku."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            return raw.get("tmdb_api_key", "")
    except Exception:
        return ""

# ──────────────────────────────────────────────────────────────
# BÖLÜM 3: CACHE SİSTEMİ
# ──────────────────────────────────────────────────────────────

def _norm_key(title: str) -> str:
    """Başlığı normalize edilmiş cache key'ine çevir."""
    return re.sub(r'[^a-z0-9]', '_', title.lower().strip())

def _load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cache(cache: dict):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"{Fore.YELLOW}[MediaID] Cache yazma hatasi: {e}{Style.RESET_ALL}")

def _cache_get(title: str) -> dict | None:
    """Cache'den metadata al. Süresi dolmuşsa None döner."""
    cache = _load_cache()
    key   = _norm_key(title)
    entry = cache.get(key)
    if not entry:
        return None
    # TTL kontrol
    try:
        saved_at = datetime.datetime.fromisoformat(entry.get("_cached_at", "2000-01-01"))
        age_days  = (datetime.datetime.now() - saved_at).days
        ttl_days = entry.get("_ttl_days", CACHE_TTL_DAYS)
        if age_days > ttl_days:
            return None  # Suresi dolmus
    except Exception:
        pass
    data = {k: v for k, v in entry.items() if not k.startswith("_")}
    return data if data.get("title") else None

def _cache_set(title: str, metadata: dict):
    """Metadata'yı cache'e kaydet."""
    cache = _load_cache()
    key   = _norm_key(title)
    entry = metadata.copy()
    entry["_cached_at"] = datetime.datetime.now().isoformat()
    entry["_ttl_days"]   = 1 if entry.get("source") == "AI" else CACHE_TTL_DAYS
    entry["_source_title"] = title
    cache[key] = entry
    _save_cache(cache)

# ──────────────────────────────────────────────────────────────
# BÖLÜM 4: DOSYA ADI AYRIŞTIRICISI
