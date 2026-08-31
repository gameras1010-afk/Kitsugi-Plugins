# glossary_prescanner.py
# ─────────────────────────────────────────────────────────────────────────────
# Pre-Scan Active Term Filter (PATF)
#
# Çeviri BAŞLAMADAN ÖNCE tüm subtitle dosyalarını tarar ve
# glossary'den sadece diyalogda GERÇEKTEN GEÇEN terimleri seçer.
#
# Akış:
#   1. pre_scan_corpus(files)          → kelime kümesi (corpus)
#   2. filter_glossary_to_active(terms, corpus) → filtrelenmiş terimler
#   3. filter_for_batch(active, batch_lines)    → bu batch'e özel subset
#   4. build_active_termbase(title, files)      → orkestratör + cache
#
# Kazanım: ~%65-80 daha küçük prompt → 429 hatası dramatik azalır
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os
import re
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Set, Dict, Optional

# ── Sabitler ─────────────────────────────────────────────────────────────────

_CACHE_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "prescanner_cache.json")
_CACHE_TTL    = timedelta(days=7)           # 7 günden eski cache geçersiz
_MIN_WORD_LEN = 3                           # 3 karakterden kısa kelimeler eşleşmesin
_MIN_TERM_LEN = 2                           # terim adı bu kadar kısa olmamalı

# ASS tag regex: {…} içindeki her şeyi siler
_ASS_TAG_RE   = re.compile(r'\{[^}]*\}')
# Placeholder regex: __NL__, __T0__ vb.
_PLACEHOLDER_RE = re.compile(r'__[A-Z0-9]+__')
# Karaoke timing tag (\\k, \\K, \\kf vb.)
_KARA_TAG_RE  = re.compile(r'\\[Kk][fFoO]?\d*')
# Sözcük tokenizer: latin + türkçe harf
_WORD_RE      = re.compile(r"[a-zA-ZÀ-ɏğşıüöçĞŞİÜÖÇ''\-]{2,}", re.UNICODE)

# Song/karaoke/credit stili adları (bu stilleri tara, ama korpusa ekleme)
_SONG_STYLE_RE = re.compile(
    r'karaoke|kara(?!oke)|\bop\b|\bed\b|opening|ending|lyric|song|'
    r'credit|staff|romaji|jp[-_]?song|en[-_]?song|insert',
    re.IGNORECASE
)

# Japonca/CJK karakter unicode aralıkları
_CJK_RE = re.compile(
    r'[\u3000-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]'
)

# ── Cache yardımcıları ────────────────────────────────────────────────────────

def _load_cache() -> dict:
    if os.path.isfile(_CACHE_FILE):
        try:
            return json.loads(open(_CACHE_FILE, encoding='utf-8').read())
        except Exception:
            pass
    return {}


def _save_cache(data: dict) -> None:
    try:
        tmp = _CACHE_FILE + ".tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _CACHE_FILE)
    except Exception:
        pass


def _cache_key(title: str, season_num: Optional[int], file_paths: List[str]) -> str:
    """
    Cache anahtarı: başlık + sezon + dosya listesi hash'i.
    Dosya eklense/çıkarsa cache otomatik geçersiz olur.
    """
    sorted_paths = sorted(os.path.normcase(p) for p in file_paths)
    files_sig    = hashlib.md5("|".join(sorted_paths).encode()).hexdigest()[:12]
    season_part  = f"S{season_num}" if season_num else "S0"
    return f"{title}|{season_part}|{files_sig}"


def _cache_get(key: str) -> Optional[dict]:
    cache = _load_cache()
    entry = cache.get(key)
    if not entry:
        return None
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(entry["scanned_at"])
        if age > _CACHE_TTL:
            return None
    except Exception:
        return None
    return entry


def _cache_set(key: str, entry: dict) -> None:
    cache = _load_cache()
    cache[key] = entry
    _save_cache(cache)


# ── Corpus çıkarma ────────────────────────────────────────────────────────────

def _is_song_style(style_name: str) -> bool:
    """Stil adının şarkı/karaoke stili olup olmadığını hızla kontrol eder."""
    return bool(_SONG_STYLE_RE.search(style_name))


def _is_cjk_dominant(text: str) -> bool:
    """Metnin büyük kısmı Japonca/CJK karakter ise True."""
    cjk_count = len(_CJK_RE.findall(text))
    return cjk_count > max(2, len(text) * 0.3)


def _extract_words_from_line(text: str) -> Set[str]:
    """Tek bir metin satırından normalize edilmiş kelime kümesi üretir."""
    # ASS tagları, placeholderlar sil
    clean = _ASS_TAG_RE.sub(' ', text)
    clean = _PLACEHOLDER_RE.sub(' ', clean)
    # Karaoke tag
    clean = _KARA_TAG_RE.sub(' ', clean)
    # Satır kırma göstergecileri
    clean = clean.replace(r'\N', ' ').replace(r'\n', ' ')
    # Kelimeler
    words = _WORD_RE.findall(clean)
    return {w.lower().strip("'-") for w in words if len(w) >= _MIN_WORD_LEN}


def pre_scan_corpus(file_paths: List[str], verbose: bool = True) -> Set[str]:
    """
    Verilen .ass dosyalarındaki diyalog satırlarından benzersiz kelime kümesi üretir.

    Atlanan satırlar:
      - Şarkı/karaoke stili
      - Japonca/CJK baskın metin
      - Çok kısa (< 4 karakter temiz metin)

    Döner: lowercase kelime kümesi (corpus)
    """
    corpus: Set[str] = set()
    total_lines = 0
    skipped     = 0

    for fpath in file_paths:
        if not os.path.isfile(fpath):
            continue
        ext = os.path.splitext(fpath)[1].lower()
        if ext not in ('.ass', '.ssa', '.srt'):
            continue

        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue

        for raw_line in content.splitlines():
            if not raw_line.startswith('Dialogue:'):
                continue
            parts = raw_line.split(',', 9)
            if len(parts) < 10:
                continue

            style = parts[3].strip()
            text  = parts[9]
            total_lines += 1

            # Şarkı/karaoke → atla (ama sayım için işaretle)
            if _is_song_style(style):
                skipped += 1
                continue

            # Karaoke timing tag → atla
            if _KARA_TAG_RE.search(text):
                skipped += 1
                continue

            # ASS tagları soyulmuş temiz metin
            clean = _ASS_TAG_RE.sub('', text).strip()

            # Japonca baskın → atla
            if _is_cjk_dominant(clean):
                skipped += 1
                continue

            # Çok kısa → atla
            if len(re.sub(r'\s+', '', clean)) < 4:
                skipped += 1
                continue

            words = _extract_words_from_line(clean)
            corpus.update(words)

    if verbose:
        kept = total_lines - skipped
        print(f"   [PreScan] {len(file_paths)} dosya tarandı: "
              f"{kept}/{total_lines} satır, {len(corpus)} benzersiz kelime")

    return corpus


# ── Glossary Filtresi ─────────────────────────────────────────────────────────

def _term_words(term: str) -> Set[str]:
    """Bir terim adından kelime kümesi üretir (eşleşme için)."""
    words = _WORD_RE.findall(term)
    return {w.lower().strip("'-") for w in words if len(w) >= _MIN_WORD_LEN}


def filter_glossary_to_active(
    terms: Dict[str, List[str]],
    corpus: Set[str],
    min_word_len: int = _MIN_WORD_LEN,
) -> Dict[str, List[str]]:
    """
    Glossary terimlerini corpus ile karşılaştırır.

    Eşleşme mantığı (OR — herhangi bir kelime corpus'ta geçsin yeter):
      - "Aincrad"       → {"aincrad"}    → corpus'ta "aincrad" var mı?
      - "Sword Skill"   → {"sword", "skill"} → bunlardan biri var mı?
      - "Asuna"         → {"asuna"}      → "asuna", "asuna-senpai" vb. yakalanır

    Döner: filtrelenmiş terms dict (aynı format, sadece aktif terimler)
    """
    active: Dict[str, List[str]] = {}
    _corpus_lower = {w.lower() for w in corpus}  # zaten lower ama emin ol

    for category, term_list in terms.items():
        kept = []
        for term in term_list:
            if len(term) < _MIN_TERM_LEN:
                continue
            t_words = _term_words(term)
            if not t_words:
                continue
            # Herhangi bir kelime corpus'ta geçiyorsa tut
            if t_words & _corpus_lower:
                kept.append(term)
        if kept:
            active[category] = kept

    return active


def filter_for_batch(
    active_terms: Dict[str, List[str]],
    batch_lines: List[str],
) -> Dict[str, List[str]]:
    """
    Aktif terimlerden bu batch'in satırlarında GEÇEN terimleri döndürür.
    Batch-seviyesinde ikinci filtre katmanı.

    batch_lines: translate_batch()'e verilen orijinal metin satırları
    """
    if not active_terms or not batch_lines:
        return active_terms  # Filtrelenemiyorsa olduğu gibi dön

    # Batch corpus'u: bu batch'teki satırlardan kelimeler
    batch_corpus: Set[str] = set()
    for line in batch_lines:
        batch_corpus.update(_extract_words_from_line(str(line)))

    if not batch_corpus:
        return active_terms  # Boş batch → aktif terimleri olduğu gibi kullan

    return filter_glossary_to_active(active_terms, batch_corpus)


# ── Ana Orkestratör ───────────────────────────────────────────────────────────

def build_active_termbase(
    title: str,
    file_paths: List[str],
    season_num: Optional[int] = None,
    season_title: Optional[str] = None,
    media_type: str = 'anime',
    known_type: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, List[str]]:
    """
    Ana PATF orkestratörü:
      1. Cache'e bak
      2. Corpus oluştur (pre_scan_corpus)
      3. Tam glossary'yi al (fandom_glossary.get_prompt_terms)
      4. Aktif terimlere filtrele
      5. Cache'e yaz
      6. Aktif terimler dict'ini döndür

    Döner: {"characters": [...], "skills": [...], ...}
            — sadece dosyalarda fiilen geçen terimler
    """
    # ── 1. Cache ────────────────────────────────────────────────────────────
    ass_files = [f for f in file_paths
                 if os.path.isfile(f) and os.path.splitext(f)[1].lower() in ('.ass', '.ssa', '.srt')]
    _key = _cache_key(title, season_num, ass_files)

    cached = _cache_get(_key)
    if cached:
        if verbose:
            at = cached.get('terms', {})
            _n_active = sum(len(v) for v in at.values())
            _n_total  = cached.get('total_terms', '?')
            print(f"   [PreScan] Cache HIT: '{title}' → "
                  f"{_n_active}/{_n_total} aktif terim (7 günlük)")
        return cached.get('terms', {})

    if verbose:
        print(f"   [PreScan] '{title}' — {len(ass_files)} dosya taranıyor...")

    # ── 2. Corpus ───────────────────────────────────────────────────────────
    corpus = pre_scan_corpus(ass_files, verbose=verbose)

    if not corpus:
        if verbose:
            print(f"   [PreScan] Corpus boş — glossary filtrelemesi atlandı")
        return {}

    # ── 3. Tam Glossary ──────────────────────────────────────────────────────
    all_terms: Dict[str, List[str]] = {}
    try:
        from fandom_glossary import get_prompt_terms as _gpt
        _lookup = season_title or title
        all_terms = _gpt(
            _lookup,
            media_type=media_type,
            known_type=known_type,
            season_num=season_num,
            season_title=season_title,
        ) or {}
    except Exception as _e:
        if verbose:
            print(f"   [PreScan] Glossary çekim hatası: {_e}")

    _total = sum(len(v) for v in all_terms.values())
    if verbose:
        print(f"   [PreScan] Tam glossary: {_total} terim → corpus filtresi uygulanıyor...")

    # ── 4. Filtrele ──────────────────────────────────────────────────────────
    active = filter_glossary_to_active(all_terms, corpus)
    _n_active = sum(len(v) for v in active.values())

    if verbose:
        _saved_pct = (1 - _n_active / max(_total, 1)) * 100
        print(f"   [PreScan] ✅ {_n_active}/{_total} terim aktif "
              f"(~%{_saved_pct:.0f} prompt tasarrufu)")
        for cat, terms in active.items():
            print(f"      {cat}: {len(terms)} terim — {', '.join(terms[:5])}"
                  f"{'...' if len(terms) > 5 else ''}")

    # ── 5. Cache'e Yaz ───────────────────────────────────────────────────────
    _cache_set(_key, {
        "scanned_at":   datetime.now(timezone.utc).isoformat(),
        "title":        title,
        "season_num":   season_num,
        "file_count":   len(ass_files),
        "corpus_size":  len(corpus),
        "total_terms":  _total,
        "active_count": _n_active,
        "terms":        active,
    })

    return active


# ── Prompt Bloğu Oluşturucu ───────────────────────────────────────────────────

def build_active_injection(
    active_terms: Dict[str, List[str]],
    batch_lines: Optional[List[str]] = None,
    title: str = "",
    max_chars: int = 1200,
) -> str:
    """
    Aktif terimlerden API'ya gidecek inject bloğunu üretir.
    batch_lines verilirse batch-seviyesinde de filtreler.
    max_chars: blok boyut tavanı (token bütçesi kontrolü).
    """
    if not active_terms:
        return ""

    # Batch-seviyesi ikinci filtre
    if batch_lines:
        to_use = filter_for_batch(active_terms, batch_lines)
    else:
        to_use = active_terms

    if not to_use:
        return ""

    _CAT_CONFIG = [
        ('characters',    'Characters (NEVER translate names)'),
        ('organizations', 'Groups/Organizations'),
        ('skills',        'Skills/Abilities'),
        ('locations',     'Locations'),
        ('items',         'Items/Weapons'),
        ('terminology',   'Special Terms'),
    ]

    title_line = f"SERIES REFERENCE — {title}" if title else "SERIES REFERENCE"
    out = [title_line]

    for key, label in _CAT_CONFIG:
        lst = to_use.get(key, [])
        if lst:
            out.append(f"  {label}: {', '.join(lst)}")

    if len(out) <= 1:
        return ""

    result = "\n".join(out)
    if len(result) > max_chars:
        result = result[:max_chars].rsplit('\n', 1)[0]
        result += "\n  [... truncated]"

    return result


# ── CLI Test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, glob

    if len(sys.argv) < 3:
        print("Kullanım: python glossary_prescanner.py <başlık> <dosya_veya_klasör>")
        print("Örnek:    python glossary_prescanner.py 'Sword Art Online' D:/Free/SAO/")
        sys.exit(0)

    _title = sys.argv[1]
    _path  = sys.argv[2]

    if os.path.isdir(_path):
        _files = glob.glob(os.path.join(_path, "**", "*.ass"), recursive=True)
    elif os.path.isfile(_path):
        _files = [_path]
    else:
        _files = glob.glob(_path, recursive=True)

    if not _files:
        print(f"Dosya bulunamadı: {_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"PATF Test — '{_title}' — {len(_files)} dosya")
    print(f"{'='*60}\n")

    active = build_active_termbase(_title, _files, verbose=True)

    print(f"\n{'='*60}")
    print(f"Inject bloğu önizlemesi:")
    print(f"{'='*60}")
    block = build_active_injection(active, title=_title)
    print(block or "(boş)")
    print(f"\nBlok boyutu: {len(block)} karakter ≈ {len(block)//4} token")
