"""
offline_db/lookup.py
====================
Public API: update_databases, lookup_anime, lookup_media vb.
"""
import os, re, sys, json, gzip, time, datetime, threading, requests
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from offline_db.constants import *

def update_databases(force: bool = False, verbose: bool = True, include_movies: bool = False):
    """
    Tüm veritabanlarını TTL'ye göre günceller.
    force=True       → hepsini yeniden indir.
    include_movies   → TMDB Film DB'sini de indir (varsayılan: False).
                       Anime TV dizisi çevirisi için film verisi gereksiz.
                       Sadece film/karma içerik çevirisi için True yap.
    İlk çalıştırmada senkron, sonrakilerde arka planda.
    """
    checks = [
        # (key, ttl_hours, path, label, fn, fn_args)
        ('anidb',          ANIDB_TTL_HOURS,            ANIDB_JSON_PATH,    'AniDB Titles',              _download_anidb,           ()),
        ('manami',         MANAMI_TTL_DAYS * 24,        MANAMI_JSON_PATH,   'manami-project',            _download_manami,          ()),
        # TMDB Film: 850k+ başlık → anime TV modu için GEREKSIZ, opsiyonel
        # include_movies=True ile aktif edilir (film/karma içerik modu)
        *([('tmdb_movies', TMDB_TTL_HOURS, TMDB_MOVIE_PATH, 'TMDB Film', _download_tmdb, ('movie_ids', TMDB_MOVIE_PATH, 'tmdb_movies'))]
          if include_movies else []),
        ('tmdb_tv',        TMDB_TTL_HOURS,              TMDB_TV_PATH,       'TMDB TV/Dizi',              _download_tmdb,            ('tv_series_ids', TMDB_TV_PATH,    'tmdb_tv')),
        ('imdb_basics',    IMDB_TTL_DAYS * 24,          IMDB_BASICS_PATH,   'IMDB Basics',               _download_imdb_basics,     ()),
        ('imdb_akas',      IMDB_TTL_DAYS * 24,          IMDB_AKAS_PATH,     'IMDB Akas (TR+JP)',         _download_imdb_akas,       ()),
        ('wiki_chars',     WIKI_TTL_DAYS * 24,          WIKI_CHARS_PATH,    'Wikidata Karakterler',      _download_wikidata_chars,  ()),
        ('wiki_entities',  WIKI_ENTITIES_TTL * 24,      WIKI_ENTITIES_PATH, 'Wikidata Varliklar',        _download_wikidata_entities, ()),
        # Kelime frekans sözlükleri (content_detector için)
        ('word_freq_en',   WORD_FREQ_TTL_DAYS * 24,     EN_FREQ_PATH,       'EN Frekans Sözlüğü',       _download_word_freqs,      ()),
        ('word_freq_tr',   WORD_FREQ_TTL_DAYS * 24,     TR_FREQ_PATH,       'TR Frekans Sözlüğü',       _download_word_freqs,      ()),
        ('anime_names',    ANIME_NAMES_TTL_DAYS * 24,   ANIME_NAMES_PATH,   'Anime İsim Listesi',        _download_anime_names,     ()),
    ]
    # word_freq_en ve word_freq_tr aynı fonksiyon — sadece bir kez çalışsın
    _ran_word_freqs = False
    any_needed = False
    for key, ttl, path, label, fn, args in checks:
        needed = force or _needs_update(key, ttl)
        if not needed:
            continue
        # EN/TR frekans aynı fonksiyon, ikinci geçişte atla
        if fn is _download_word_freqs:
            if _ran_word_freqs:
                continue
            _ran_word_freqs = True
        any_needed = True
        first_run = not os.path.exists(path)
        if first_run:
            if verbose:
                print(f"[OfflineDB] İlk kurulum: {label} indiriliyor (bekleyin)...")
            fn(*args, verbose=verbose)
            _invalidate_cache()
        else:
            if verbose:
                print(f"[OfflineDB] {label} güncelleniyor (arka planda)...")
            threading.Thread(
                target=lambda f=fn, a=args: [f(*a, verbose=True), _invalidate_cache()],
                daemon=True,
            ).start()

    if not any_needed and verbose:
        print("[OfflineDB] Tüm veritabanları güncel. (10 kaynak)")



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 6: LOOKUP FONKSİYONLARI (Pipeline bütünleşme)
# ─────────────────────────────────────────────────────────────────────────────

def lookup_anime(title: str) -> Optional[dict]:
    """Anime başlığını AniDB + manami'de arar."""
    key = _normalize(title)
    if not key:
        return None
    manami = _load_manami()
    entry  = manami.get(key)
    if entry:
        return _manami_to_meta(entry, title)
    anidb  = _load_anidb()
    entry  = anidb.get(key)
    if entry:
        return _anidb_to_meta(entry, title)
    return None


def lookup_media(title: str, media_type: str = 'unknown') -> Optional[dict]:
    """
    Film/dizi başlığını TMDB offline export'tan arar.
    media_type: 'movie', 'series', 'unknown'
    """
    key = _normalize(title)
    if not key:
        return None

    if media_type in ('movie', 'unknown'):
        entry = _load_tmdb_movies().get(key)
        if entry:
            return {
                'title':               entry.get('title', title),
                'type':                'MOVIE',
                'resolved_media_type': 'movie',
                'episodes':   1,
                'status':     '',
                'genres':     [],
                'characters': [],
                'synopsis':   '',
                'score':      None,
                'year':       None,
                'source':     'OfflineDB/TMDB-Movie',
                'tmdb_id':    entry.get('id'),
                '_offline':   True,
            }

    if media_type in ('series', 'unknown'):
        entry = _load_tmdb_tv().get(key)
        if entry:
            return {
                'title':               entry.get('title', title),
                'type':                'TVSERIES',
                'resolved_media_type': 'series',
                'episodes':   '?',
                'status':     '',
                'genres':     [],
                'characters': [],
                'synopsis':   '',
                'score':      None,
                'year':       None,
                'source':     'OfflineDB/TMDB-TV',
                'tmdb_id':    entry.get('id'),
                '_offline':   True,
            }

    # IMDB Basics fallback (TMDB'de bulunmayan eski/nadir içerikler)
    imdb_entry = _load_imdb_basics().get(key)
    if imdb_entry:
        genres_raw  = imdb_entry.get('genres', '')
        imdb_type   = imdb_entry.get('type', '').lower()  # titleType: tvSeries, movie, short…

        # IMDB titleType → standart tip
        _TYPE_MAP = {
            'tvseries':       'TVSERIES',
            'tvminiseries':   'TVSERIES',
            'tvspecial':      'TVSERIES',
            'tvepisode':      'TVSERIES',
            'tvmovie':        'MOVIE',
            'movie':          'MOVIE',
            'short':          'MOVIE',
            'videogame':      'OTHER',
            'video':          'MOVIE',
        }
        norm_type = _TYPE_MAP.get(imdb_type, imdb_type.upper())

        # media_type parametresinden gelen bağlam türüne öncelik ver (kullanıcı biliyor)
        if media_type in ('series', 'tv', 'anime'):
            norm_type = 'TVSERIES' if media_type != 'anime' else 'ANIME'
        elif media_type == 'movie':
            norm_type = 'MOVIE'

        return {
            'title':               imdb_entry.get('title', title),
            'type':                norm_type,
            'resolved_media_type': 'anime'  if norm_type == 'ANIME'
                                   else 'series' if norm_type == 'TVSERIES'
                                   else 'movie'  if norm_type == 'MOVIE'
                                   else 'unknown',
            'episodes':   '?',
            'status':     '',
            'genres':     [g.strip() for g in genres_raw.split(',') if g.strip()] if genres_raw else [],
            'characters': [],
            'synopsis':   '',
            'score':      None,
            'year':       imdb_entry.get('year', ''),
            'source':     'OfflineDB/IMDB-Basics',
            'imdb_id':    imdb_entry.get('id'),
            '_offline':   True,
        }

    return None


def lookup_by_turkish_title(tr_title: str) -> Optional[dict]:
    """
    Türkçe başlıktan orijinal (genellikle İngilizce) başlığı bulur.
    Örnek: 'Zor Ölüm' -> {imdb_id: 'tt0087182', title: 'Zor Ölüm', region: 'TR'}
    """
    key = _normalize(tr_title)
    if not key:
        return None
    return _load_imdb_akas().get(key)


def get_anime_characters() -> List[str]:
    """
    Tüm Wikidata anime karakterlerinin ad listesini döner.
    fandom_glossary.py'deki 'asla çevirme' koruması için kullanılır.
    """
    return _load_wiki_chars()


def get_synonyms(title: str) -> List[str]:
    """
    Bir başlığa ait TÜM alternatif isimler.
    fandom_glossary._make_slug_candidates() için kullanılır.
    """
    key = _normalize(title)
    if not key:
        return []

    syns: List[str] = []

    manami = _load_manami()
    if key in manami:
        e = manami[key]
        syns = [e.get('title', '')] + (e.get('synonyms') or [])

    if not syns:
        anidb = _load_anidb()
        if key in anidb:
            e = anidb[key]
            syns = [e.get('title', '')] + (e.get('synonyms') or [])

    # Tekrarları kaldır, boşları at
    seen = set()
    result = []
    for s in syns:
        sn = s.strip()
        if sn and sn.lower() not in seen:
            seen.add(sn.lower())
            result.append(sn)
    return result


def get_all_titles_for_slug(title: str) -> List[str]:
    """
    Fandom slug tespiti için başlığın TÜM isim varyantlarını döner
    (İngilizce, Romaji, Japonca, kısa isimler dahil).
    """
    syns = get_synonyms(title)
    if not syns:
        syns = [title]

    # Japonca + özel karakterleri filtrele (slug'da kullanılamaz)
    latin_only = []
    for s in syns:
        if re.search(r'[\u3000-\u9fff\uff00-\uffef]', s):
            continue  # Japonca/Çince karakterli → atla
        latin_only.append(s)

    return latin_only or syns


def get_status_info() -> dict:
    """Dashboard için mevcut durum bilgisi."""
    meta = _load_meta()
    anidb_meta  = meta.get('anidb', {})
    manami_meta = meta.get('manami', {})

    def _age_str(updated_at: str) -> str:
        if not updated_at:
            return 'hiç indirilmedi'
        try:
            dt  = datetime.datetime.fromisoformat(updated_at)
            hrs = (datetime.datetime.now() - dt).total_seconds() / 3600
            if hrs < 1:
                return f'{int(hrs*60)} dk önce'
            elif hrs < 24:
                return f'{hrs:.1f} saat önce'
            else:
                return f'{hrs/24:.1f} gün önce'
        except Exception:
            return '?'

    anidb_count   = len(_load_anidb())        if os.path.exists(ANIDB_JSON_PATH)   else 0
    manami_count  = len(_load_manami())       if os.path.exists(MANAMI_JSON_PATH)  else 0
    movies_count  = len(_load_tmdb_movies())  if os.path.exists(TMDB_MOVIE_PATH)   else 0
    tv_count      = len(_load_tmdb_tv())      if os.path.exists(TMDB_TV_PATH)      else 0
    basics_count  = len(_load_imdb_basics())  if os.path.exists(IMDB_BASICS_PATH)  else 0
    akas_count    = len(_load_imdb_akas())    if os.path.exists(IMDB_AKAS_PATH)    else 0
    wiki_count         = len(_load_wiki_chars())    if os.path.exists(WIKI_CHARS_PATH)    else 0
    wiki_entities_count = len(_load_wiki_entities()) if os.path.exists(WIKI_ENTITIES_PATH) else 0

    # EN/TR frekans sözlükleri
    def _count_pickle(path):
        if not os.path.exists(path): return 0
        try:
            import pickle
            with open(path, 'rb') as f:
                return len(pickle.load(f))
        except Exception:
            return 0

    def _count_gz(path):
        if not os.path.exists(path): return 0
        try:
            import gzip as _gz
            with _gz.open(path, 'rt', encoding='utf-8') as f:
                return sum(1 for l in f if l.strip() and not l.startswith('#'))
        except Exception:
            return 0

    en_freq_count    = _count_pickle(EN_FREQ_PATH)
    tr_freq_count    = _count_pickle(TR_FREQ_PATH)
    anime_name_count = _count_gz(ANIME_NAMES_PATH)

    tmdb_movie_meta  = meta.get('tmdb_movies', {})
    tmdb_tv_meta     = meta.get('tmdb_tv', {})
    imdb_basics_meta = meta.get('imdb_basics', {})
    imdb_akas_meta   = meta.get('imdb_akas', {})
    wiki_meta        = meta.get('wiki_chars', {})
    wiki_ent_meta    = meta.get('wiki_entities', {})
    wfen_meta        = meta.get('word_freq_en', {})
    wftr_meta        = meta.get('word_freq_tr', {})
    anames_meta      = meta.get('anime_names', {})

    return {
        'anidb': {
            'exists':       os.path.exists(ANIDB_JSON_PATH),
            'entries':      anidb_count,
            'age_str':      _age_str(anidb_meta.get('updated_at', '')),
            'needs_update': _needs_update('anidb', ANIDB_TTL_HOURS),
        },
        'manami': {
            'exists':       os.path.exists(MANAMI_JSON_PATH),
            'entries':      manami_count,
            'age_str':      _age_str(manami_meta.get('updated_at', '')),
            'needs_update': _needs_update('manami', MANAMI_TTL_DAYS * 24),
        },
        'tmdb_movies': {
            'exists':       os.path.exists(TMDB_MOVIE_PATH),
            'entries':      movies_count,
            'age_str':      _age_str(tmdb_movie_meta.get('updated_at', '')),
            'needs_update': _needs_update('tmdb_movies', TMDB_TTL_HOURS),
        },
        'tmdb_tv': {
            'exists':       os.path.exists(TMDB_TV_PATH),
            'entries':      tv_count,
            'age_str':      _age_str(tmdb_tv_meta.get('updated_at', '')),
            'needs_update': _needs_update('tmdb_tv', TMDB_TTL_HOURS),
        },
        'imdb_basics': {
            'exists':       os.path.exists(IMDB_BASICS_PATH),
            'entries':      basics_count,
            'age_str':      _age_str(imdb_basics_meta.get('updated_at', '')),
            'needs_update': _needs_update('imdb_basics', IMDB_TTL_DAYS * 24),
        },
        'imdb_akas': {
            'exists':       os.path.exists(IMDB_AKAS_PATH),
            'entries':      akas_count,
            'age_str':      _age_str(imdb_akas_meta.get('updated_at', '')),
            'needs_update': _needs_update('imdb_akas', IMDB_TTL_DAYS * 24),
        },
        'wiki_chars': {
            'exists':       os.path.exists(WIKI_CHARS_PATH),
            'entries':      wiki_count,
            'age_str':      _age_str(wiki_meta.get('updated_at', '')),
            'needs_update': _needs_update('wiki_chars', WIKI_TTL_DAYS * 24),
        },
        'wiki_entities': {
            'exists':       os.path.exists(WIKI_ENTITIES_PATH),
            'entries':      wiki_entities_count,
            'age_str':      _age_str(wiki_ent_meta.get('updated_at', '')),
            'needs_update': _needs_update('wiki_entities', WIKI_ENTITIES_TTL * 24),
        },
        'word_freq_en': {
            'exists':       os.path.exists(EN_FREQ_PATH),
            'entries':      en_freq_count,
            'age_str':      _age_str(wfen_meta.get('updated_at', '')),
            'needs_update': _needs_update('word_freq_en', WORD_FREQ_TTL_DAYS * 24),
        },
        'word_freq_tr': {
            'exists':       os.path.exists(TR_FREQ_PATH),
            'entries':      tr_freq_count,
            'age_str':      _age_str(wftr_meta.get('updated_at', '')),
            'needs_update': _needs_update('word_freq_tr', WORD_FREQ_TTL_DAYS * 24),
        },
        'anime_names': {
            'exists':       os.path.exists(ANIME_NAMES_PATH),
            'entries':      anime_name_count,
            'age_str':      _age_str(anames_meta.get('updated_at', '')),
            'needs_update': _needs_update('anime_names', ANIME_NAMES_TTL_DAYS * 24),
        },
    }



# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 7: FORMAT DÖNÜŞTÜRÜCÜLER
# ─────────────────────────────────────────────────────────────────────────────

def _manami_to_meta(entry: dict, original_query: str) -> dict:
    """manami entry → media_identifier metadata formatı."""
    title  = entry.get('title') or original_query
    syns   = entry.get('synonyms') or []
    tags   = entry.get('tags') or []
    score  = entry.get('score')
    year   = entry.get('year')

    # MAL ID'yi çıkar (URL'den)
    mal_id = None
    mal_url = entry.get('mal_url', '')
    if mal_url:
        m = re.search(r'/anime/(\d+)', mal_url)
        if m:
            mal_id = int(m.group(1))

    # manami type → resolved_media_type
    _manami_type = entry.get('type', 'TV').upper()
    _resolved = (
        'movie' if _manami_type in ('MOVIE',)
        else 'anime'  # TV, OVA, ONA, SPECIAL, MUSIC hepsi anime
    )
    return {
        'title':               title,
        'title_jp':            '',
        'type':                _manami_type,
        'resolved_media_type': _resolved,
        'episodes':   '?',
        'status':     entry.get('status', ''),
        'genres':     tags[:6],
        'characters': [],
        'synopsis':   '',
        'score':      score,
        'year':       year,
        'source':     'OfflineDB/manami',
        'mal_id':     mal_id,
        'synonyms':   syns,
        '_offline':   True,
    }


def _anidb_to_meta(entry: dict, original_query: str) -> dict:
    """AniDB entry → media_identifier metadata formatı."""
    title = entry.get('title') or original_query
    syns  = entry.get('synonyms') or []
    return {
        'title':               title,
        'title_jp':            (entry.get('langs') or {}).get('ja', [None])[0] or '',
        'type':                'TV',
        'resolved_media_type': 'anime',   # AniDB = her zaman anime
        'episodes':   '?',
        'status':     '',
        'genres':     [],
        'characters': [],
        'synopsis':   '',
        'score':      None,
        'year':       None,
        'source':     'OfflineDB/AniDB',
        'aid':        entry.get('aid'),
        'synonyms':   syns,
        '_offline':   True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 8: CLI ARAÇ (python offline_db_manager.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Offline Anime DB Yöneticisi'
    )
    parser.add_argument('--update', action='store_true', help='Güncelleme kontrolü yap')
    parser.add_argument('--force',  action='store_true', help='Zorla güncelle')
    parser.add_argument('--status', action='store_true', help='Durum göster')
    parser.add_argument('--lookup', metavar='TITLE', help='Başlık ara')
    parser.add_argument('--synonyms', metavar='TITLE', help='Sinonimler')
    args = parser.parse_args()

    if args.status or not any(vars(args).values()):
        s = get_status_info()
        print("\n=== OfflineDB Durum ===")
        print(f"AniDB Titles:    {'✓' if s['anidb']['exists'] else '✗'} "
              f"{s['anidb']['entries']:,} giriş | "
              f"{s['anidb']['age_str']} | "
              f"{'GÜNCELLEME GEREKLİ' if s['anidb']['needs_update'] else 'güncel'}")
        print(f"manami-project:  {'✓' if s['manami']['exists'] else '✗'} "
              f"{s['manami']['entries']:,} giriş | "
              f"{s['manami']['age_str']} | "
              f"{'GÜNCELLEME GEREKLİ' if s['manami']['needs_update'] else 'güncel'}")

    if args.update or args.force:
        update_databases(force=args.force, verbose=True)

    if args.lookup:
        result = lookup_anime(args.lookup)
        if result:
            print(f"\n[{args.lookup}] → {json.dumps(result, ensure_ascii=False, indent=2)}")
        else:
            print(f"\n[{args.lookup}] → bulunamadı")

    if args.synonyms:
        syns = get_synonyms(args.synonyms)
        print(f"\n[{args.synonyms}] sinonimler: {syns}")
