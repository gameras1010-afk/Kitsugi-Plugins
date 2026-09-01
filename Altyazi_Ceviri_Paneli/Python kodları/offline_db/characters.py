"""
offline_db/characters.py
========================
Karakter verisi: Wikidata, AniDB, TVmaze.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

def _download_wikidata_chars(verbose: bool = True) -> bool:
    """
    Wikidata SPARQL → tüm kurgusal karakter adlarını indir.
    Q15711870 = 'anime character' (özel)
    Q95074    = 'fictional character' (geniş: anime + film + dizi hepsi)

    Sonuç: fandom_glossary'e ve build_translation_context'e
    'asla çevirme' koruması için kullanılır.
    """
    if verbose:
        print("[OfflineDB] Wikidata kurgusal karakterler indiriliyor (SPARQL)...", flush=True)

    # İki sorgu: önce anime-spesifik, sonra genel kurgusal karakterler
    QUERIES = [
        ("anime-char Q15711870", "SELECT ?char ?charLabel WHERE { ?char wdt:P31 wd:Q15711870. SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } } LIMIT %d OFFSET %d"),
        ("fictional-char Q95074", "SELECT ?char ?charLabel WHERE { ?char wdt:P31 wd:Q95074. SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\". } } LIMIT %d OFFSET %d"),
    ]
    PAGE_SIZE = 10000
    MAX_PAGES = 120
    all_chars: set = set()
    sparql_headers = {
        "User-Agent": "AnimeSubtitleTranslator/3.0 (wikidata-chars)",
        "Accept":     "application/json",
    }

    for qname, QUERY in QUERIES:
        if verbose:
            print(f"[OfflineDB]   Sorgu: {qname}...", flush=True)
        for page in range(MAX_PAGES):
            offset = page * PAGE_SIZE
            q = QUERY % (PAGE_SIZE, offset)
            try:
                resp = requests.get(
                    WIKI_SPARQL,
                    params={"query": q, "format": "json"},
                    headers=sparql_headers,
                    timeout=90,
                )
                if resp.status_code == 429:
                    time.sleep(30)
                    continue
                if resp.status_code != 200:
                    if verbose:
                        print(f"[OfflineDB] Wikidata HTTP {resp.status_code} — {qname} durduruluyor")
                    break
                data = resp.json()
                bindings = data.get("results", {}).get("bindings", [])
                if not bindings:
                    break
                for b in bindings:
                    label = b.get("charLabel", {}).get("value", "").strip()
                    # Q123 ID'li etiket yok = atla; 1 karakterlik = atla; sayı = atla
                    if label and not label.startswith("Q") and len(label) > 1 and not label.isdigit():
                        all_chars.add(label)
                if verbose and page % 5 == 0:
                    print(f"[OfflineDB]   Sayfa {page+1}: toplam {len(all_chars):,} karakter")
                if len(bindings) < PAGE_SIZE:
                    break
                time.sleep(1.5)
            except Exception as e:
                if verbose:
                    print(f"[OfflineDB] Wikidata hata (sayfa {page}): {e}")
                time.sleep(5)
                break

    if not all_chars:
        return False

    chars_list = sorted(all_chars)
    try:
        with open(WIKI_CHARS_PATH, 'w', encoding='utf-8') as f:
            json.dump(chars_list, f, ensure_ascii=False)
        _mark_updated('wiki_chars', f"{len(chars_list)}_chars")
        if verbose:
            print(f"[OfflineDB] Wikidata Chars OK: {len(chars_list):,} karakter kaydedildi.")
        return True
    except Exception as e:
        print(f"[OfflineDB] Wikidata kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3e: ANİDB PER-ANİME KARAKTER LAZY-LOAD
# ─────────────────────────────────────────────────────────────────────────────

_ANIDB_CHAR_CACHE_DIR = os.path.join(_DIR, 'offline_anidb_chars')

def _get_anidb_aid(title: str) -> Optional[str]:
    """AniDB Titles dump'tan anime title → AID (AniDB ID) bul."""
    key = _normalize(title)
    if not key:
        return None
    anidb = _load_anidb()
    entry = anidb.get(key)
    if entry:
        return str(entry.get('aid', ''))
    # Manami'de de dene
    manami = _load_manami()
    entry = manami.get(key)
    if entry:
        return str(entry.get('anidb', ''))
    return None


def fetch_anidb_characters(title: str, verbose: bool = True) -> List[str]:
    """
    Belirli bir anime için AniDB HTTP API'den karakter adlarını çek.
    Sonuç disk'e cache'lenir (per-anime JSON).
    Rate limit: 1 istek / 2 saniye → ilk çağrıda birkaç sn bekler.

    Döndürür: ['Kirito', 'Asuna', 'Klein', ...]
    """
    os.makedirs(_ANIDB_CHAR_CACHE_DIR, exist_ok=True)
    key = _normalize(title)
    if not key:
        return []

    # Disk cache kontrol
    safe_name = re.sub(r'[^\w]', '_', key)[:60]
    cache_file = os.path.join(_ANIDB_CHAR_CACHE_DIR, f"{safe_name}.json")
    if os.path.exists(cache_file):
        try:
            mtime = os.path.getmtime(cache_file)
            age_days = (time.time() - mtime) / 86400
            if age_days < 30:  # 30 gün geçerli
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get('characters', [])
        except Exception:
            pass

    # AniDB AID bul
    aid = _get_anidb_aid(title)
    if not aid:
        if verbose:
            print(f"[OfflineDB] AniDB AID bulunamadı: '{title}'")
        return []

    # AniDB HTTP API
    # Not: client/clientver kayıt gerektirir ama titles dump ile cross-ref yapılabilir
    # En kolay yol: AniDB wiki sayfasından XML parse
    try:
        url = f"https://api.anidb.net:9000/httpapi?request=anime&aid={aid}&client=httpapi&clientver=1&protover=1"
        resp = requests.get(url, timeout=30, headers={"User-Agent": "AnimeSubtitleTranslator/3.0"})
        if resp.status_code != 200:
            if verbose:
                print(f"[OfflineDB] AniDB API HTTP {resp.status_code} — AID {aid}")
            return []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        chars = []
        # AniDB XML: <characters><character>...<name><kanji/><latin/></name>...
        for char_elem in root.iter('character'):
            name_elem = char_elem.find('name')
            if name_elem is None:
                continue
            latin = name_elem.findtext('latin', '').strip()
            kanji = name_elem.findtext('kanji', '').strip()
            if latin and latin not in chars:
                chars.append(latin)
            elif kanji and kanji not in chars:
                chars.append(kanji)

        if not chars:
            # Fallback: <romanji> veya <name> direkt
            for char_elem in root.iter('character'):
                n = char_elem.findtext('name', '').strip()
                if n and n not in chars:
                    chars.append(n)

        # Disk'e kaydet
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({'aid': aid, 'title': title, 'characters': chars,
                       'fetched_at': datetime.datetime.now().isoformat()}, f, ensure_ascii=False)
        if verbose:
            print(f"[OfflineDB] AniDB karakter lazy-load: '{title}' → {len(chars)} karakter")
        return chars

    except Exception as e:
        if verbose:
            print(f"[OfflineDB] AniDB karakter hata: {e}")
        return []


def get_characters_for_title(title: str, media_type: str = 'anime') -> List[str]:
    """
    Bir başlık için tüm kaynaklardan karakter adlarını toplar.
    Önce disk cache, sonra AniDB lazy-load, sonra Wikidata genel listesi.

    Kullanım yerleri:
      - build_translation_context() → CHARACTERS satırı
      - fandom_glossary.get_prompt_terms() → ek karakter
      - ass_qa_checker → retry sırasında proper noun koruması
    """
    chars: List[str] = []

    if media_type == 'anime':
        # 1. AniDB lazy-load (seri-spesifik)
        anidb_chars = fetch_anidb_characters(title, verbose=False)
        chars.extend(anidb_chars)

    # 2. Wikidata genel listesi (500k+ kurgusal karakter — doğrulama filtresi)
    wiki_chars = _load_wiki_chars()
    # Bunları direkt eklemeyiz (çok büyük), sadece lookup için kullanılır
    # → get_wikidata_char_set() ile erişilir

    # Tekrar kaldır
    seen = set()
    result = []
    for c in chars:
        cn = c.strip()
        if cn and cn.lower() not in seen:
            seen.add(cn.lower())
            result.append(cn)
    return result


def get_wikidata_char_set() -> set:
    """
    Wikidata karakter listesini set olarak döner.
    Hızlı `in` kontrolü için kullanılır:
    → "Bu kelime bilinen bir kurgusal karakter adı mı?"
    """
    return set(_load_wiki_chars())


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3e-2: WIKIDATA GENIŞ VARLIK SETİ (mekan, eşya, organizasyon, araç)
# ─────────────────────────────────────────────────────────────────────────────

def _download_wikidata_entities(verbose: bool = True) -> bool:
    """
    Kurgusal mekan, silah/esya, arac, organizasyon adlarini indir.
    Animelerin otesinde film ve dizilerdeki proper noun'lari kapsar.
    TTL: 30 gun | Dosya: offline_wikidata_entities.json
    """
    if verbose:
        print("[OfflineDB] Wikidata genis varlik seti indiriliyor...", flush=True)

    QUERIES = [
        ('Q17537576', 'Kurgusal Mekan'),
        ('Q188145',   'Kurgusal Silah/Esya'),
        ('Q1958614',  'Kurgusal Arac'),
        ('Q43229',    'Kurgusal Organizasyon'),
    ]
    QUERY_TMPL = """
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31/wdt:P279* wd:%s.
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT %d OFFSET %d
    """
    PAGE_SIZE = 5000
    MAX_PAGES = 20
    all_entities: set = set()
    sparql_hdrs = {"User-Agent": "AnimeSubtitleTranslator/3.0", "Accept": "application/json"}

    for qid, label in QUERIES:
        if verbose:
            print(f"[OfflineDB]   {label} ({qid})...")
        for page in range(MAX_PAGES):
            q = QUERY_TMPL % (qid, PAGE_SIZE, page * PAGE_SIZE)
            try:
                resp = requests.get(WIKI_SPARQL, params={"query": q, "format": "json"},
                                    headers=sparql_hdrs, timeout=60)
                if resp.status_code != 200:
                    break
                bindings = resp.json().get("results", {}).get("bindings", [])
                if not bindings:
                    break
                for b in bindings:
                    lbl = b.get("itemLabel", {}).get("value", "").strip()
                    if lbl and not lbl.startswith("Q") and len(lbl) > 1:
                        all_entities.add(lbl)
                if len(bindings) < PAGE_SIZE:
                    break
                time.sleep(1.5)
            except Exception as e:
                if verbose:
                    print(f"[OfflineDB]   {label} hata: {e}")
                break
        if verbose:
            print(f"[OfflineDB]   {label}: toplam {len(all_entities):,}")

    if not all_entities:
        return False
    try:
        lst = sorted(all_entities)
        with open(WIKI_ENTITIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(lst, f, ensure_ascii=False)
        _mark_updated('wiki_entities', f"{len(lst)}_entities")
        if verbose:
            print(f"[OfflineDB] Wikidata Entities OK: {len(lst):,} varlik")
        return True
    except Exception as e:
        print(f"[OfflineDB] Wikidata entities kaydetme hatasi: {e}")
        return False


def _load_wiki_entities() -> set:
    global _wiki_entities_cache
    if _wiki_entities_cache is not None:
        return _wiki_entities_cache
    with _load_lock:
        if _wiki_entities_cache is not None:
            return _wiki_entities_cache
        if os.path.exists(WIKI_ENTITIES_PATH):
            try:
                with open(WIKI_ENTITIES_PATH, 'r', encoding='utf-8') as f:
                    _wiki_entities_cache = set(json.load(f))
                return _wiki_entities_cache
            except Exception:
                pass
    _wiki_entities_cache = set()
    return _wiki_entities_cache


def get_wikidata_entity_set() -> set:
    """Kurgusal mekan, esya, arac, org adlarini set olarak doner."""
    return _load_wiki_entities()


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3f: KELIME FREKANS SÖZLÜKLERİ + ANİME İSİM LİSTESİ
# hermitdave/FrequencyWords → EN + TR frekans
# ryuuganime/animanga-wordlist + Jikan → Anime isim listesi
# ─────────────────────────────────────────────────────────────────────────────

def _download_word_freqs(verbose: bool = True) -> bool:
    """
    EN + TR kelime frekans sözlüklerini günceller.
    Kaynak: hermitdave/FrequencyWords (GitHub raw)
    Çıktı: data/english_freq.bin + data/turkish_freq.bin (pickle)
    TTL: 30 gün
    """
    import pickle
    os.makedirs(_DATA_DIR, exist_ok=True)
    if verbose:
        print("[OfflineDB] EN+TR Frekans sözlükleri güncelleniyor...", flush=True)

    URLS = {
        'en': "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/en/en_50k.txt",
        'tr': "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/tr/tr_50k.txt",
    }
    PATHS = {'en': EN_FREQ_PATH, 'tr': TR_FREQ_PATH}
    TR_CORE = ['bir','bu','ne','ve','için','mi','de','o','ben','çok','ama','evet',
               'var','da','mı','değil','şey','hayır','daha','sen','kadar','bana',
               'gibi','yok','bunu','onu','iyi','tamam','beni','seni','her','benim']
    success = True
    for lang, url in URLS.items():
        try:
            resp = requests.get(url, timeout=30, headers=HEADERS)
            if resp.status_code != 200:
                if verbose: print(f"[OfflineDB] FrequencyWords {lang} HTTP {resp.status_code}")
                success = False; continue
            freq = {}
            for line in resp.text.splitlines():
                parts = line.strip().split()
                if len(parts) == 2:
                    try:
                        w, c = parts[0].lower(), int(parts[1])
                        if 1 <= len(w) <= 30:
                            freq[w] = c
                    except ValueError:
                        pass
            if lang == 'tr':
                for w in TR_CORE:
                    if w not in freq: freq[w] = 1000
            with open(PATHS[lang], 'wb') as f:
                pickle.dump(freq, f, protocol=pickle.HIGHEST_PROTOCOL)
            if verbose:
                print(f"[OfflineDB] {lang.upper()} frekans OK: {len(freq):,} kelime")
        except Exception as e:
            if verbose: print(f"[OfflineDB] FrequencyWords {lang} hata: {e}")
            success = False

    if success:
        _mark_updated('word_freq_en', 'hermitdave_50k')
        _mark_updated('word_freq_tr', 'hermitdave_50k')
    return success


def _download_anime_names(verbose: bool = True) -> bool:
    """
    Anime karakter/başlık isimlerini günceller (content_detector için).
    Kaynak: ryuuganime/animanga-wordlist + Jikan API top characters
    Çıktı: data/anime_names.txt.gz
    TTL: 7 gün
    """
    os.makedirs(_DATA_DIR, exist_ok=True)
    if verbose:
        print("[OfflineDB] Anime isim listesi güncelleniyor...", flush=True)

    names: set = set()

    # 1. ryuuganime animanga-wordlist
    RYUU_URLS = [
        "https://raw.githubusercontent.com/ryuuganime/animanga-wordlist/main/dictionaries/characters.txt",
        "https://raw.githubusercontent.com/ryuuganime/animanga-wordlist/main/dictionaries/anime.txt",
    ]
    for url in RYUU_URLS:
        try:
            resp = requests.get(url, timeout=20, headers=HEADERS)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    for w in re.split(r'[\s\-_/,]+', line):
                        w = w.strip().lower()
                        if w and re.match(r'^[a-z]{2,25}$', w):
                            names.add(w)
        except Exception as e:
            if verbose: print(f"[OfflineDB] ryuuganime hata: {e}")

    # 2. Jikan API top characters (3 sayfa)
    for page in range(1, 4):
        try:
            resp = requests.get(
                f"https://api.jikan.moe/v4/top/characters?page={page}",
                timeout=15, headers=HEADERS
            )
            if resp.status_code == 200:
                data = resp.json()
                for char in data.get('data', []):
                    name = char.get('name', '')
                    for part in re.split(r'[,\s]+', name):
                        part = part.strip().lower()
                        if part and re.match(r'^[a-z]{2,20}$', part):
                            names.add(part)
            time.sleep(0.5)
        except Exception:
            break

    # 3. Wikidata karakter listesinden de ekle
    if os.path.exists(WIKI_CHARS_PATH):
        try:
            with open(WIKI_CHARS_PATH, 'r', encoding='utf-8') as f:
                wiki = json.load(f)
            for name in wiki:
                for part in name.split():
                    p = part.strip().lower()
                    if p and re.match(r'^[a-z]{2,25}$', p):
                        names.add(p)
        except Exception:
            pass

    # Genel İngilizce kelimeleri filtrele
    _STOP = {'an','or','is','it','if','in','on','at','to','be','by','he','we',
              'me','hi','so','no','ok','go','do','my','up','oh','ai','ma','le',
              'la','re','de','en','un','el','lo','as','am','us','yo','the','and'}
    names -= _STOP
    names = {n for n in names if re.match(r'^[a-z]{2,25}$', n)}

    if not names:
        return False

    try:
        import gzip as _gz
        with _gz.open(ANIME_NAMES_PATH, 'wt', encoding='utf-8', compresslevel=9) as f:
            for n in sorted(names):
                f.write(n + '\n')
        _mark_updated('anime_names', f"{len(names)}_names")
        if verbose:
            print(f"[OfflineDB] Anime isim listesi OK: {len(names):,} isim")
        return True
    except Exception as e:
        if verbose: print(f"[OfflineDB] anime_names kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# YÜKLEME FONKSİYONLARI — IMDB + Wikidata
# ─────────────────────────────────────────────────────────────────────────────

def _load_imdb_basics() -> Dict:
    global _imdb_basics_cache
    if _imdb_basics_cache is not None:
        return _imdb_basics_cache
    with _load_lock:
        if _imdb_basics_cache is not None:
            return _imdb_basics_cache
        if os.path.exists(IMDB_BASICS_PATH):
            try:
                with open(IMDB_BASICS_PATH, 'r', encoding='utf-8') as f:
                    _imdb_basics_cache = json.load(f)
                return _imdb_basics_cache
            except Exception:
                pass
    return {}

def _load_imdb_akas() -> Dict:
    global _imdb_akas_cache
    if _imdb_akas_cache is not None:
        return _imdb_akas_cache
    with _load_lock:
        if _imdb_akas_cache is not None:
            return _imdb_akas_cache
        if os.path.exists(IMDB_AKAS_PATH):
            try:
                with open(IMDB_AKAS_PATH, 'r', encoding='utf-8') as f:
                    _imdb_akas_cache = json.load(f)
                return _imdb_akas_cache
            except Exception:
                pass
    return {}

def _load_wiki_chars() -> List:
    global _wiki_chars_cache
    if _wiki_chars_cache is not None:
        return _wiki_chars_cache
    with _load_lock:
        if _wiki_chars_cache is not None:
            return _wiki_chars_cache
        if os.path.exists(WIKI_CHARS_PATH):
            try:
                with open(WIKI_CHARS_PATH, 'r', encoding='utf-8') as f:
                    _wiki_chars_cache = json.load(f)
                return _wiki_chars_cache
            except Exception:
                pass
    return []


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3g: TVMAZE LAZY-LOAD (Dizi Karakterleri)
# api.tvmaze.com — ucretsiz, auth yok, CC BY-SA
# AniDB'nin dizi karsiligi — per-show disk cache + TTL
# ─────────────────────────────────────────────────────────────────────────────

