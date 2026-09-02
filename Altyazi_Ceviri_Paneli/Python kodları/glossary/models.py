"""
glossary/models.py
==================
Candidate dataclass, sabitler, _glossary_path ve oturum önbelleği.
"""
import os
import re
import json
import time
import threading
import requests
import urllib.parse
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field

class Candidate:
    slug: str                    # fandom subdomain (thecampione)
    lang_path: str = ""          # "" (root) veya "es", "ja" ...
    base_score: float = 0.0
    source: str = ""             # wikidata | unified-search | ai
    hub: str = ""                # unified-search 'hub' alanı
    page_count: int = 0
    wiki_name: str = ""
    bonuses: dict = field(default_factory=dict)

    @property
    def api_base(self) -> str:
        root = f"https://{self.slug}.fandom.com"
        return f"{root}/{self.lang_path}" if self.lang_path else root

# Offline DB — güvenli import
try:
    import offline_db_manager as _offdb
    _OFFLINE_DB_OK = True
except ImportError:
    _OFFLINE_DB_OK = False

# ── Sabitler ─────────────────────────────────────────────────────────────────
# Glossary dosyası: her zaman fandom_glossary.py ile aynı dizinde (Python kodları/) kalır.
# os.getcwd() KULLANILMAZ — script farklı klasörden (Sadece Çeviri/) çalışabilir.
def _glossary_path() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "series_glossary.json")

REQUEST_TIMEOUT  = 4     # saniye (düşürüldü: 8→4, paralel isteklerde yeterli)
MAX_TERMS_PER_CAT = 200  # kategori başına maks. terim
MAX_PROMPT_TERMS  = 80   # prompt'a enjekte edilecek maks. terim

# ── Cache TTL (Time-To-Live) ──────────────────────────────────────────────────────────────────────
CACHE_TTL_DAYS     = 30  # Gerecek terimler 30 gunde bir yenilenir
NOT_FOUND_TTL_DAYS = 1   # "bulunamadi" kaydi 1 gun sonra tekrar denenir

# ── Oturum içi bellek cache (aynı session'da disk+HTTP tekrarı önler) ──────────────────────
# Her worker/process'e ait; multiprocessing'de her process kendi cache'ini taşır.
_session_cache: Dict[str, Optional[Dict]] = {}
_CANONICAL_TITLE_CACHE: Dict[str, str] = {}

