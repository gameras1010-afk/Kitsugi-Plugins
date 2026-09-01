"""
offline_db/media_db.py
======================
TMDB/IMDb indirme ve Wikidata title lookup.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

def _download_tmdb(kind: str, out_path: str, meta_key: str, verbose: bool = True) -> bool:
    """
    TMDB günlük export indir ve {normalized_title: {id, title, type}} JSON olarak kaydet.
    kind: 'movie_ids' veya 'tv_series_ids'
    """
    label = 'Film' if kind == 'movie_ids' else 'TV/Dizi'
    if verbose:
        print(f"[OfflineDB] TMDB {label} export indiriliyor...", flush=True)
    url = _tmdb_export_url(kind)
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            # Dünün dosyası yoksa avantünkü dene
            d2 = datetime.datetime.utcnow() - datetime.timedelta(days=2)
            url2 = f"https://files.tmdb.org/p/exports/{kind}_{d2.month:02d}_{d2.day:02d}_{d2.year}.json.gz"
            r = requests.get(url2, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
            if r.status_code != 200:
                print(f"[OfflineDB] TMDB {label} indirme hatası: HTTP {r.status_code}")
                return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] TMDB {label} hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    title_field = 'original_title' if kind == 'movie_ids' else 'original_name'
    media_type  = 'movie' if kind == 'movie_ids' else 'series'

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        tmdb_id  = obj.get('id')
        title    = (obj.get(title_field) or '').strip()
        pop      = obj.get('popularity', 0)
        if not title or not tmdb_id:
            continue
        entry = {
            'id':    tmdb_id,
            'title': title,
            'type':  media_type,
            'popularity': pop,
        }
        norm = _normalize(title)
        if norm and norm not in db:
            db[norm] = entry

    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated(meta_key, f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] TMDB {label} OK: {len(db):,} başlık indexlendi.")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'✅ TMDB {label} OK: {len(db):,} başlık', 'positive', 5000)
            except Exception: pass
        return True
    except Exception as e:
        print(f"[OfflineDB] TMDB {label} kaydetme hatası: {e}")
        return False


def _load_tmdb_movies() -> Dict:
    global _tmdb_movie_cache
    if _tmdb_movie_cache is not None:
        return _tmdb_movie_cache
    with _load_lock:
        if _tmdb_movie_cache is not None:
            return _tmdb_movie_cache
        if os.path.exists(TMDB_MOVIE_PATH):
            try:
                with open(TMDB_MOVIE_PATH, 'r', encoding='utf-8') as f:
                    _tmdb_movie_cache = json.load(f)
                return _tmdb_movie_cache
            except Exception:
                pass
    return {}


def _load_tmdb_tv() -> Dict:
    global _tmdb_tv_cache
    if _tmdb_tv_cache is not None:
        return _tmdb_tv_cache
    with _load_lock:
        if _tmdb_tv_cache is not None:
            return _tmdb_tv_cache
        if os.path.exists(TMDB_TV_PATH):
            try:
                with open(TMDB_TV_PATH, 'r', encoding='utf-8') as f:
                    _tmdb_tv_cache = json.load(f)
                return _tmdb_tv_cache
            except Exception:
                pass
    return {}

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3c: IMDB BASICS + AKAS
# ─────────────────────────────────────────────────────────────────────────────

def _download_imdb_basics(verbose: bool = True) -> bool:
    """IMDB title.basics — sadece film/dizi (tvEpisode değil), animation genre ağırlıklı."""
    if verbose:
        print("[OfflineDB] IMDB Basics indiriliyor (streaming)...", flush=True)
    url = f"{IMDB_URL_BASE}/title.basics.tsv.gz"
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            print(f"[OfflineDB] IMDB Basics hatası: HTTP {r.status_code}")
            return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] IMDB Basics indirme hatası: {e}")
        return False

    db: Dict[str, dict] = {}
    KEEP_TYPES = {'movie', 'tvSeries', 'tvMiniSeries', 'tvMovie', 'tvSpecial', 'short'}
    lines = raw.split(b'\n')
    header = lines[0].decode('utf-8', errors='replace').split('\t')
    idx = {h: i for i, h in enumerate(header)}

    for line in lines[1:]:
        row = line.decode('utf-8', errors='replace').split('\t')
        if len(row) < 5:
            continue
        try:
            ttype = row[idx.get('titleType', 1)]
            if ttype not in KEEP_TYPES:
                continue
            tconst   = row[idx.get('tconst', 0)]
            primary  = (row[idx.get('primaryTitle', 2)] or '').strip()
            original = (row[idx.get('originalTitle', 3)] or '').strip()
            year     = row[idx.get('startYear', 5)]
            genres   = row[idx.get('genres', 8)]
            if not primary or primary == r'\N':
                continue
            entry = {
                'id':       tconst,
                'title':    primary,
                'original': original if original != primary else '',
                'type':     ttype,
                'year':     year if year != r'\N' else '',
                'genres':   genres if genres != r'\N' else '',
            }
            for t in set([primary, original]):
                if not t or t == r'\N':
                    continue
                key = _normalize(t)
                if key and key not in db:
                    db[key] = entry
        except Exception:
            continue

    try:
        with open(IMDB_BASICS_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('imdb_basics', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] IMDB Basics OK: {len(db):,} başlık indexlendi.")
        return True
    except Exception as e:
        print(f"[OfflineDB] IMDB Basics kaydetme hatası: {e}")
        return False


def _download_imdb_akas(verbose: bool = True) -> bool:
    """IMDB title.akas — sadece TR (Türkçe) ve JA (Japonca) satırlar stream-parse edilir."""
    if verbose:
        print("[OfflineDB] IMDB Akas indiriliyor (streaming, büyük dosya)...", flush=True)
    url = f"{IMDB_URL_BASE}/title.akas.tsv.gz"
    try:
        r = requests.get(url, timeout=DOWNLOAD_TIMEOUT, headers=HEADERS, stream=True)
        if r.status_code != 200:
            print(f"[OfflineDB] IMDB Akas hatası: HTTP {r.status_code}")
            return False
        raw = gzip.decompress(r.content)
    except Exception as e:
        print(f"[OfflineDB] IMDB Akas indirme hatası: {e}")
        return False

    # {normalized_localized_title: {imdb_id, title, region, lang}}
    db: Dict[str, dict] = {}
    KEEP_REGIONS = {'TR', 'JP', 'US'}   # TR=Türkçe, JP=Japonca, US=İngilizce
    lines = raw.split(b'\n')
    header = lines[0].decode('utf-8', errors='replace').split('\t')
    idx = {h: i for i, h in enumerate(header)}

    for line in lines[1:]:
        row = line.decode('utf-8', errors='replace').split('\t')
        if len(row) < 4:
            continue
        try:
            region = (row[idx.get('region', 3)] or '').strip()
            if region not in KEEP_REGIONS:
                continue
            tconst = row[idx.get('titleId', 0)]
            title  = (row[idx.get('title', 2)] or '').strip()
            lang   = (row[idx.get('language', 4)] or '').strip()
            if not title or title == r'\N':
                continue
            entry = {
                'imdb_id': tconst,
                'title':   title,
                'region':  region,
                'lang':    lang,
            }
            key = _normalize(title)
            if key and key not in db:
                db[key] = entry
        except Exception:
            continue

    try:
        with open(IMDB_AKAS_PATH, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False)
        _mark_updated('imdb_akas', f"{len(db)}_entries")
        if verbose:
            print(f"[OfflineDB] IMDB Akas OK: {len(db):,} yerel başlık indexlendi (TR+JP+US).")
        return True
    except Exception as e:
        print(f"[OfflineDB] IMDB Akas kaydetme hatası: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3c-EXTRA: WIKIDATA BAŞLIK → DOĞRU ENTİTY (P31 TÜR FİLTRESİ)
# ─────────────────────────────────────────────────────────────────────────────
# Wikidata'da her şeyin "instance of" (P31) özelliği var:
#   Q5398426  = television series (herhangi bir dizi)
#   Q11424    = film
#   Q63952888 = anime television series
#   Q20650540 = anime film
#   Q24856    = film series
#   Q83267    = fiction (genel)
# Bu sayede "Dark" → TV dizisi entity'sini, borsa dark pool'larını değil, buluruz.
# ─────────────────────────────────────────────────────────────────────────────

_WIKIDATA_TITLE_CACHE_DIR = os.path.join(_DIR, 'wikidata_title_cache')

# Wikidata P31 değerleri → bizim tür sistemimize map
_P31_TYPE_MAP = {
    # TV Dizi
    'Q5398426':  'series',   # television series
    'Q1366112':  'series',   # web series
    'Q3464665':  'series',   # television program
    'Q15416':    'series',   # television show
    'Q21191270': 'series',   # television series episode (parent)
    'Q1257444':  'series',   # TV miniseries
    # Anime
    'Q63952888': 'anime',    # anime television series
    'Q21174398': 'anime',    # anime OVA
    'Q20650540': 'anime',    # anime film
    'Q220898':   'anime',    # anime
    # Film
    'Q11424':    'movie',    # film
    'Q202866':   'movie',    # animated film
    'Q29168811': 'movie',    # documentary film
    'Q24856':    'movie',    # film series
    'Q506240':   'movie',    # television film
}

# Tür → hangi P31 ID'leri kabul edilir
_TYPE_ALLOWED_P31 = {
    'series': {'Q5398426','Q1366112','Q3464665','Q15416','Q1257444','Q21191270'},
    'anime':  {'Q63952888','Q21174398','Q20650540','Q220898','Q5398426'},
    'movie':  {'Q11424','Q202866','Q29168811','Q24856','Q506240','Q20650540'},
    'unknown': None,  # None = hepsi kabul
}


def lookup_wikidata_by_title(title: str, media_type: str = 'unknown',
                              verbose: bool = False) -> Optional[dict]:
    """
    Wikidata SPARQL ile başlık + P31 tür filtresi kullanarak doğru entity'yi bulur.
    "Dark" (TV dizisi) ile "Aquis Dark Pool" (borsa) arasındaki farkı P31'e göre ayırt eder.

    Döndürür:
        {
            'qid':        'Q28259127',
            'title':      'Dark',
            'type':       'series',           # bizim tür sistemimiz
            'p31_labels': ['television series', 'German television series'],
            'characters': ['Jonas Kahnwald', ...],
            'locations':  ['Winden', ...],
        }
    veya None
    """
    os.makedirs(_WIKIDATA_TITLE_CACHE_DIR, exist_ok=True)
    safe = re.sub(r'[^a-z0-9]', '_', title.lower())[:60]
    cache_path = os.path.join(_WIKIDATA_TITLE_CACHE_DIR, f"{safe}_{media_type}.json")

    # Cache kontrolü (TTL 60 gün)
    if os.path.exists(cache_path):
        try:
            age = (time.time() - os.path.getmtime(cache_path)) / 86400
            if age < 60:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if not cached.get("found"):
                        return None
                    return cached
        except Exception:
            pass

    # Tür kısıtı — Python tarafında P31 map ile filtrele (SPARQL filter query'yi kırıyor)
    allowed = _TYPE_ALLOWED_P31.get(media_type)  # None = hepsi kabul

    # Başlık kaçış
    title_esc = title.replace('"', '\\"')

    # 1. ADIM: rdfs:label ile kesin eşleşme — tipe filtre YOK, Python'da yapılır
    QUERY_EXACT = (
        'SELECT DISTINCT ?item ?itemLabel ?p31 ?p31Label WHERE {'
        f' ?item rdfs:label "{title_esc}"@en .'
        ' ?item wdt:P31 ?p31 .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 30'
    )
    # 2. ADIM: skos:altLabel ile dene
    QUERY_ALT = (
        'SELECT DISTINCT ?item ?itemLabel ?p31 ?p31Label WHERE {'
        f' ?item skos:altLabel "{title_esc}"@en .'
        ' ?item wdt:P31 ?p31 .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 30'
    )

    headers = {
        "User-Agent": "AnimeSubtitleTranslator/3.0 (wikidata-title-lookup)",
        "Accept":     "application/json",
    }

    best_qid = None
    best_type = None
    p31_labels = []
    _current_priority = -1  # Şu ana kadar seçilen P31'in önceliği

    # P31 öncelik tablosu — döngü dışında (bir kere oluştur)
    _P31_PRIORITY = {
        'Q5398426':  1000,  # television series
        'Q63952888': 1000,  # anime television series
        'Q11424':    1000,  # film
        'Q1257444':  900,   # TV miniseries
        'Q1366112':  900,   # web series
        'Q202866':   900,   # animated film
        'Q20650540': 900,   # anime film
        'Q220898':   850,   # anime (genel)
        'Q506240':   800,   # television film
        'Q24856':    700,   # film series
        'Q29168811': 700,   # documentary film
        'Q3464665':  600,   # television program
        'Q15416':    500,   # television show
        'Q21191270': 100,   # television series episode (düşük öncelik)
    }

    for qname, query in [("exact", QUERY_EXACT), ("alt", QUERY_ALT)]:
        try:
            resp = requests.get(
                WIKI_SPARQL,
                params={"query": query, "format": "json"},
                headers=headers,
                timeout=20,
            )
            if resp.status_code != 200:
                continue
            bindings = resp.json().get("results", {}).get("bindings", [])
            if not bindings:
                continue

            for b in bindings:
                qid   = b.get("item", {}).get("value", "").split("/")[-1]
                p31   = b.get("p31",  {}).get("value", "").split("/")[-1]
                p31_l = b.get("p31Label", {}).get("value", "")

                mapped = _P31_TYPE_MAP.get(p31)
                if not mapped:
                    continue  # Bilinmeyen P31 (borsa, müzik, gen...) → atla

                # Tür kısıtı: eğer allowed varsa ve bu P31 izin verilenlerden değilse atla
                if allowed and p31 not in allowed:
                    continue

                # Öncelik sırası: kesin tür (Q5398426 televizyon dizisi) > geniş tür (Q21191270 bölüm)
                # P31 öncelik puanı: en yüksek = en kesin (1000), en düşük = en belirsiz (1)
                _P31_PRIORITY = {
                    # Kesin türler — yüksek öncelik
                    'Q5398426':  1000,  # television series
                    'Q63952888': 1000,  # anime television series
                    'Q11424':    1000,  # film
                    'Q1257444':  900,   # TV miniseries
                    'Q1366112':  900,   # web series
                    'Q202866':   900,   # animated film
                    'Q20650540': 900,   # anime film
                    'Q220898':   850,   # anime (genel)
                    'Q506240':   800,   # television film
                    'Q24856':    700,   # film series
                    'Q29168811': 700,   # documentary film
                    'Q3464665':  600,   # television program
                    'Q15416':    500,   # television show
                    # Düşük öncelik — bölüm veya genel
                    'Q21191270': 100,   # television series episode
                }
                priority = _P31_PRIORITY.get(p31, 200)

                # Daha önce bulunan varsa sadece daha yüksek öncelikliyse güncelle
                if priority > _current_priority:
                    best_qid  = qid
                    best_type = mapped
                    _current_priority = priority
                if p31_l and p31_l not in p31_labels:
                    p31_labels.append(p31_l)

            if best_qid:
                if verbose:
                    print(f"[Wikidata] '{title}' → {best_qid} ({best_type}) via {qname}")
                break

        except Exception as e:
            if verbose:
                print(f"[Wikidata] Sorgu hatası ({qname}): {e}")
            time.sleep(2)

    if not best_qid:
        # Not-found kaydı — 7 gün TTL (kısa)
        _save_json(cache_path, {"found": False, "title": title})
        return None

    # 3. ADIM: Bu QID'den karakter ve lokasyon çek
    characters = []
    locations  = []

    # Karakter sorgusu — iki strateji:
    # a) P1441 (fictional character part of): standart bağlantı
    # b) P161 (cast member): gerçek oyuncu değil — bu ikisi farklı, P1441 tercihli
    # c) Hem P1441 hem P179 (part of series) ile UNION
    QUERY_CHARS_A = (
        'SELECT DISTINCT ?charLabel WHERE {'
        ' { ?char wdt:P31 wd:Q95074 .'    # fictional character
        f'   ?char wdt:P1441 wd:{best_qid} . }}'
        ' UNION'
        ' { ?char wdt:P31 wd:Q15711870 .'  # anime character
        f'   ?char wdt:P1441 wd:{best_qid} . }}'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 100'
    )
    QUERY_LOCS = (
        'SELECT DISTINCT ?locLabel WHERE {'
        ' ?loc wdt:P31/wdt:P279* wd:Q17334923 .'  # fictional location
        f' ?loc wdt:P1441 wd:{best_qid} .'
        ' SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }'
        ' } LIMIT 50'
    )
    for q, lst, label_key in [(QUERY_CHARS_A, characters, "charLabel"),
                               (QUERY_LOCS,   locations,  "locLabel")]:
        try:
            r = requests.get(
                WIKI_SPARQL,
                params={"query": q, "format": "json"},
                headers=headers, timeout=20,
            )
            if r.status_code == 200:
                for b in r.json().get("results", {}).get("bindings", []):
                    lbl = b.get(label_key, {}).get("value", "").strip()
                    if lbl and not lbl.startswith("Q") and len(lbl) > 1:
                        lst.append(lbl)
            time.sleep(0.5)
        except Exception:
            pass

    result = {
        "found":      True,
        "qid":        best_qid,
        "title":      title,
        "type":       best_type,
        "p31_labels": p31_labels,
        "characters": characters,
        "locations":  locations,
    }
    _save_json(cache_path, result)
    if verbose:
        print(f"[Wikidata] {title}: {len(characters)} karakter, {len(locations)} lokasyon ({p31_labels[:2]})")
    return result


def _save_json(path: str, data: dict) -> None:
    """Güvenli JSON yazımı."""
    import tempfile
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.tmp',
                                         dir=os.path.dirname(path), delete=False) as tf:
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tmp = tf.name
        os.replace(tmp, path)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3d: WIKIDATA ANİME KARAKTERLERİ (SPARQL)
# ─────────────────────────────────────────────────────────────────────────────


