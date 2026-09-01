"""
romaji/kana.py
==============
Kana seti.
"""
import re
from typing import List, Tuple, Optional

"""
romaji_filter.py — Kapsamlı Japonca Romaji Cümle Tespiti
=========================================================
Anime altyazı çeviri sistemi için geliştirilmiş, cümle düzeyinde
Japonca romaji algılama modülü.

Eski is_romaji_text() fonksiyonu kelime kalıplarına bakıyordu;
bu modül CÜMLE düzeyinde çalışır:
  - 157,947 kelimeli kanwadict4.db (pykakasi) romaji sözlüğü [YENİ]
  - 600+ manuel Japonca romaji kelime sözlüğü (kategorili, ağırlıklı)
  - Japonca hece yapısı (CV-pattern) analizi
  - İngilizce belirteç tespiti (false positive önleme)
  - Kombine skorlama sistemi

Kullanım:
  from romaji_filter import is_romaji_sentence
  if is_romaji_sentence("Itsuka ano doomu ippai no"):
      # Romaji → çevirme!

Dönen değer:
  True  → Japonca romaji (çevirme!)
  False → İngilizce veya başka bir dil (çevir)
"""

import re
import os
import pickle

# ──────────────────────────────────────────────────────────────
# [YENİ] KANWADICT4 ROMAJI SETİ — 157,947 kelime
# pykakasi'nin kanwadict4.db'sinden türetilmiş pickle
# Lazy-load: sadece ilk kullanımda yüklenir (~1.8 MB)
# ──────────────────────────────────────────────────────────────
_KANWA_SET = None  # frozenset, lazy-loaded
_KANWA_PKL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'romaji_kanwa_set.pkl')

def _get_kanwa_set() -> frozenset:
    """kanwadict4 romaji setini lazy-load et (ilk çağrıda yükle)."""
    global _KANWA_SET
    if _KANWA_SET is None:
        try:
            with open(_KANWA_PKL, 'rb') as f:
                _KANWA_SET = pickle.load(f)
        except Exception:
            _KANWA_SET = frozenset()  # Dosya yoksa boş set
    return _KANWA_SET

# ──────────────────────────────────────────────────────────────
# BÖLÜM 1: JAPONCA HECE TABLOSU
# Greedy (uzundan kısaya) eşleşme için sıralı
# ──────────────────────────────────────────────────────────────

_SYLLABLES = (
    # 3+ karakter (önce bunları dene)
    'chi', 'tsu', 'shi',
    'sha', 'shu', 'she', 'sho',
    'cha', 'chu', 'che', 'cho',
    'kya', 'kyu', 'kye', 'kyo',
    'gya', 'gyu', 'gye', 'gyo',
    'nya', 'nyu', 'nye', 'nyo',
    'hya', 'hyu', 'hye', 'hyo',
    'mya', 'myu', 'mye', 'myo',
    'rya', 'ryu', 'rye', 'ryo',
    'bya', 'byu', 'bye', 'byo',
    'pya', 'pyu', 'pye', 'pyo',
    'dya', 'dyu', 'dyo',
    'jya', 'jyu', 'jyo',
    'tya', 'tyu', 'tyo',
    # 2 karakter
    'ka', 'ki', 'ku', 'ke', 'ko',
    'sa', 'su', 'se', 'so',
    'ta', 'te', 'to',
    'na', 'ni', 'nu', 'ne', 'no',
    'ha', 'hi', 'he', 'ho',
    'ma', 'mi', 'mu', 'me', 'mo',
    'ya', 'yu', 'yo',
    'ra', 'ri', 'ru', 're', 'ro',
    'wa', 'wi', 'we', 'wo',
    'ga', 'gi', 'gu', 'ge', 'go',
    'za', 'zi', 'zu', 'ze', 'zo',
    'da', 'di', 'du', 'de', 'do',
    'ba', 'bi', 'bu', 'be', 'bo',
    'pa', 'pi', 'pu', 'pe', 'po',
    'ja', 'ji', 'ju', 'je', 'jo',
    'fa', 'fi', 'fu', 'fe', 'fo',
    # Uzun ünlüler
    'aa', 'ii', 'uu', 'ee', 'oo', 'ou',
    # 1 karakter
    'a', 'i', 'u', 'e', 'o', 'n',
)

