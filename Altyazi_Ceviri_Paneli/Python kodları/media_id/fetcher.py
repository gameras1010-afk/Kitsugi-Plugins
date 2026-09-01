"""
media_id/fetcher.py
===================
Ana metadata pipeline.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional
from media_id.constants import *

def fetch_media_metadata(title: str, translator=None, media_type: str = 'unknown',
                         year_hint: int = None, season: int = None) -> dict | None:
    """
    Medya turunune gore dinamik sirali waterfall ile metadata ceker.
    0. Offline DB (AniDB+manami) -> aninda, internet yok
    1-6. Online API'lar (Jikan, AniList, Kitsu, TVMaze, TMDB)
    7. AI fallback
    season: Biliniyorsa gecir -- AniList sezon zinciri icin kullanilir
    """
    sources  = _load_source_config()
    tmdb_key = _get_tmdb_key()

    type_icon = {
        'anime':'[ANIME]', 'series':'[DIZI]', 'movie':'[FILM]', 'unknown':'[?]'
    }.get(media_type, '[?]')
    print(f"{Fore.MAGENTA}   [MediaID] Medya turu: {type_icon} -> waterfall ayarlaniyor...{Style.RESET_ALL}")

    metadata = None
    source_used = None
    _offline_pre = None   # Offline'dan gelen on-bilgi (API bulamazsa kullanilir)

    # ── 0. Offline DB (anime: AniDB+manami | film/dizi: TMDB export) ──────────
    # Online API'lardan ONCE calisir. Bulunursa API ile zenginlestirilir,
    # hic API bulamazsa direkt bu kullanilir.
    if _OFFLINE_DB_AVAILABLE:
        try:
            if media_type in ('anime', 'unknown'):
                _offline_pre = _offdb.lookup_anime(title)
                if _offline_pre:
                    print(f"{Fore.GREEN}   [MediaID] OfflineDB (anime): '{_offline_pre.get('title')}' bulundu{Style.RESET_ALL}")
            if _offline_pre is None and media_type in ('movie', 'series', 'unknown'):
                _offline_pre = _offdb.lookup_media(title, media_type)
                if _offline_pre:
                    print(f"{Fore.GREEN}   [MediaID] OfflineDB (film/dizi): '{_offline_pre.get('title')}' bulundu{Style.RESET_ALL}")
        except Exception:
            pass

    if media_type in ('anime', 'unknown'):
        if sources.get("jikan") and metadata is None:
            metadata, source_used = _try_source("Jikan/MAL", _query_jikan, title)
        # AniList: season>=2 ise Relations zinciri ile dogru sezonu bul (S1->S2->S3)
        if sources.get("anilist") and metadata is None:
            if season and season >= 2:
                print(f"{Fore.CYAN}   [MediaID] AniList sezon zinciri: S{season} takip ediliyor...{Style.RESET_ALL}")
                metadata, source_used = _try_source(
                    f"AniList/S{season}", _query_anilist_season, title, season
                )
            else:
                metadata, source_used = _try_source("AniList", _query_anilist, title, None)
        if sources.get("kitsu") and metadata is None:
            metadata, source_used = _try_source("Kitsu", _query_kitsu, title)

    if media_type in ('series', 'unknown'):
        if sources.get("tvmaze") and metadata is None:
            metadata, source_used = _try_source("TVMaze", _query_tvmaze, title)
        if sources.get("tmdb") and tmdb_key and metadata is None:
            # Dizi icin TV once ara (movie-first davranisi yanlis sonuc veriyor)
            _tmdb_mtype = 'tv' if media_type == 'series' else 'auto'
            metadata, source_used = _try_source("TMDB", _query_tmdb, title, tmdb_key, year_hint, _tmdb_mtype)

    if media_type == 'movie':
        if sources.get("tmdb") and tmdb_key and metadata is None:
            metadata, source_used = _try_source("TMDB", _query_tmdb, title, tmdb_key, year_hint, 'movie')
        if metadata is None and not tmdb_key:
            print(f"{Fore.YELLOW}   [MediaID] Film icin TMDB API anahtari gerekli"
                  f" -> Gelismis Ayarlar -> AI&API'dan ekleyin.{Style.RESET_ALL}")

    # ── Hicbir online kaynak bulamadiysa Offline DB son care ─────────────────
    if metadata is None and _offline_pre:
        print(f"{Fore.YELLOW}   [MediaID] Online API bulamadi -> OfflineDB fallback kullaniliyor{Style.RESET_ALL}")
        metadata    = _offline_pre
        source_used = _offline_pre.get('source', 'OfflineDB')

    # ── Online meta'ya offline sinonim bilgisi ekle ───────────────────────────
    if metadata and _OFFLINE_DB_AVAILABLE and not metadata.get('synonyms'):
        try:
            syns = _offdb.get_synonyms(title)
            if syns:
                metadata['synonyms'] = syns
        except Exception:
            pass

    if metadata and sources.get("ai_fill_gaps") and translator:
        has_gaps = (not metadata.get("genres") or not metadata.get("characters")
                    or not metadata.get("synopsis"))
        if has_gaps:
            print(f"{Fore.YELLOW}   [MediaID] Eksik alanlar AI ile tamamlaniyor...{Style.RESET_ALL}")
            metadata = _ai_fill_gaps(metadata, translator)

    if metadata:
        print(f"{Fore.GREEN}   [MediaID] Kaynak: {source_used} [OK]{Style.RESET_ALL}")
        _cache_set(title, metadata)
        return metadata

    return None


def _inject_episode_info(metadata: dict, ep_info: dict) -> dict:
    """Sezon/bölüm/part bilgisini metadata dict'ine yerleştir (in-place + return)."""
    for key in ('season', 'episode', 'part'):
        if ep_info.get(key) is not None:
            metadata[key] = ep_info[key]
    return metadata


def _build_search_titles(title: str, season, part,
                         alt_title: str = None,
                         search_hint: str = None,
                         season_title: str = None,
                         media_type: str = 'unknown') -> list:
    """
    3+ katmanli API arama listesi olusturur (en spesifikten genele, tekrarsiz):
      Katman 0: AI season_title (ornek: 'Sword Art Online: Alicization') — MAL icin altin deger
      Katman 1: Parse edilen / Romaji baslik
      Katman 2: Ingilizce resmi isim (alt_title)
      Katman 3: AI kanonikal arama formu (search_hint)

    NOT: Bati dizileri (series) icin sezon numarasi sorguya EKLENMEZ.
    TVMaze/TMDB, show adina gore bulur; sezon numarasi endpoint parametresiyle gecilir.
    Anime icin ise MAL'da her sezonun farkli adi var ('SAO: Alicization') — season_title ile gelir.
    """
    seen = set()
    results = []

    def _add(t):
        if t and t.strip() and t.strip().lower() not in seen:
            seen.add(t.strip().lower())
            results.append(t.strip())

    def _add_variants(base):
        if not base:
            return
        # Anime veya unknown icin: MAL/Jikan'da sezon = ayri baslik,
        # bu yuzden "SAO Season 3", "SAO 3" gibi varyantlar anlamlı.
        # Bati dizileri (series) icin: "Supernatural Season 14" TMDB'de yanlis film buluyor!
        # TVMaze/TMDB base title ile bulur, season sonra endpoint'te kullanilir.
        _is_anime_search = media_type in ('anime', 'unknown')
        if season and season >= 2 and _is_anime_search:
            _ordinals = {2:'2nd', 3:'3rd', 4:'4th', 5:'5th',
                         6:'6th', 7:'7th', 8:'8th', 9:'9th'}
            ordinal = _ordinals.get(season, f'{season}th')
            _add(f"{base} Season {season}")
            _add(f"{base} {ordinal} Season")
            _add(f"{base} {season}")
        elif part and part >= 2:
            _add(f"{base} {part}")
            _add(f"{base} Part {part}")
            _add(f"{base} Movie {part}")
        _add(base)

    # Katman 0: AI season_title — MAL'daki gercek sezon adi (en spesifik)
    # Ornek: SAO S3 -> 'Sword Art Online: Alicization'
    # Bu Jikan/MAL aramalarinda en degerli cunku MAL basligiyla birebir eslesir.
    if season_title:
        _add(season_title)   # Tam sezon basligi (variant uretme — zaten tam baslik)

    _add_variants(title)       # Katman 1: Romaji / parse
    _add_variants(alt_title)   # Katman 2: Ingilizce
    _add_variants(search_hint) # Katman 3: AI kanonikal

    return results



def _log_metadata_summary(meta: dict, season=None, episode=None):
    """Cekilen metadata'nin ozetini terminale yazar."""
    title    = meta.get('title', '?')
    source   = meta.get('source', '?')
    genres   = ', '.join((meta.get('genres') or [])[:4]) or '-'
    chars    = ', '.join((meta.get('characters') or [])[:6]) or '-'
    synopsis = (meta.get('synopsis') or '').strip()
    synopsis = synopsis[:120] + ('...' if len(synopsis) > 120 else '') if synopsis else '-'
    score    = meta.get('score')
    ep_count = meta.get('episodes', '?')

    print(f"{Fore.CYAN}   [Baglamı] ── Cekilen Metadata Ozeti ─────────────────{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı]  Baslik   : {title}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı]  Kaynak   : {source}{Style.RESET_ALL}")
    if season:
        ep_str = f"  |  Bolum: {episode}" if episode else ""
        print(f"{Fore.CYAN}   [Baglamı]  Sezon    : {season}{ep_str}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı]  Turler   : {genres}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı]  Karakterler: {chars}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı]  Ozet     : {synopsis}{Style.RESET_ALL}")
    if score:
        print(f"{Fore.CYAN}   [Baglamı]  Puan/Bolum: {score} / {ep_count}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}   [Baglamı] ─────────────────────────────────────────────{Style.RESET_ALL}")

def identify_from_file(filepath: str, translator=None) -> dict | None:
    """
    Dosya yolundan medya metadatasını döndürür.

    Pipeline:
      1. Medya türü + sezon/bölüm tespit et
      2. Dosya adından başlık parse et
      3. Cache'de var mı? (sezon-özel + genel)
      4. Sezon-bilinçli API waterfall (Season N → Nth Season → N → base)
      5. Hepsi başarısız → AI ile isim tespiti + sezon-bilinçli tekrar API
      6. Yine başarısız → AI ile doğrudan metadata üret
      7. Her şey başarısız → None (graceful skip)

    Dönen:
      dict  → Metadata (title, genres, characters, synopsis, season, episode...)
      None  → Belirlenemedi (çeviri bağlamlı değil ama devam eder)
    """
    # -- Offline DB güncellemesi (TTL dolmuşsa arka planda, ilk çalıştırmada senkron) --
    # Media type'a gore gereksiz DB'ler indirilmez:
    #   anime/dizi → TMDB Film (850k) indirilmez, sadece TMDB TV indirilir
    #   film       → TMDB Film + TV ikisi de indirilir
    #   auto       → Dosya adından hızlı tespit yapılır, ona göre karar verilir
    if _OFFLINE_DB_AVAILABLE:
        try:
            # Prefs'ten content_type al
            _pref_ctype = 'auto'
            try:
                import json as _json
                _prefs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_preferences.json')
                if os.path.exists(_prefs_path):
                    _prefs = _json.load(open(_prefs_path, encoding='utf-8'))
                    _pref_ctype = _prefs.get('content_type', 'auto').lower()
            except Exception:
                pass

            if _pref_ctype == 'auto':
                # Auto mod: dosya adından hızlı regex tespiti (AI'ya gerek yok)
                _auto_type = detect_media_type(filepath)   # 'anime'|'series'|'movie'|'unknown'
                _include_movies = (_auto_type == 'movie')
            else:
                # Manuel seçim: direkt kullan
                _include_movies = (_pref_ctype == 'movie')

            _offdb.update_databases(verbose=True, include_movies=_include_movies)
        except Exception:
            pass

    # -- ADIM 0: AI-once siniflandirma + regex fallback --
    raw_fn      = os.path.basename(filepath)
    ai_classify = None
    sources     = _load_source_config()

    if sources.get('ai_fallback', True):
        print(f'{Fore.CYAN}   [MediaID] AI siniflandirma...{Style.RESET_ALL}', end=' ', flush=True)
        ai_classify = _ai_classify_media(raw_fn)
        if ai_classify:
            print(f"{Fore.GREEN}OK{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}Basarisiz (regex fallback){Style.RESET_ALL}")

    if ai_classify:
        # AI basarili: AI sonuclarini kullan
        media_type   = ai_classify['media_type']
        parsed_title = ai_classify['title']
        alt_title    = ai_classify.get('alt_title')
        search_hint  = ai_classify.get('search_hint')
        ai_season    = ai_classify.get('season')
        ai_part      = ai_classify.get('part')
        ep_info      = parse_episode_info(filepath)
        episode      = ep_info.get('episode')
        season       = ai_season if ai_season else ep_info.get('season')
        part         = ai_part   if ai_part   else ep_info.get('part')
        ep_info['season']  = season
        ep_info['episode'] = episode
        ep_info['part']    = part
        ep_str = ('S%02dE%02d' % (season, episode)) if (season and episode) else ('Part ' + str(part) if part else 'N/A')
        _ai_log = f"   [MediaID] AI: '{parsed_title}' | {media_type} | {ep_str}"
        if alt_title:
            _ai_log += f" | EN: '{alt_title}'"
        if search_hint:
            _ai_log += f" | Hint: '{search_hint}'"
        print(f"{Fore.GREEN}{_ai_log}{Style.RESET_ALL}")
    else:
        # Regex fallback
        alt_title    = None
        search_hint  = None
        media_type   = detect_media_type(filepath)
        ep_info      = parse_episode_info(filepath)
        season       = ep_info.get('season')
        episode      = ep_info.get('episode')
        part         = ep_info.get('part')
        parsed_title = _clean_title(os.path.splitext(os.path.basename(filepath))[0])
        type_labels  = {'anime': 'Anime', 'series': 'Bati Dizisi', 'movie': 'Film', 'unknown': 'Belirsiz'}
        print(f"{Fore.MAGENTA}   [MediaID] Tur tahmini: {type_labels.get(media_type,'?')} ({media_type}){Style.RESET_ALL}")
        if season and episode:
            print(f"{Fore.CYAN}   [MediaID] Sezon/Bolum: S{season:02d}E{episode:02d}{Style.RESET_ALL}")
        elif part:
            print(f"{Fore.CYAN}   [MediaID] Film sirasi: Part {part}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}   [MediaID] Baslik parse: '{parsed_title}'{Style.RESET_ALL}")


    # ── ADIM 1: Cache kontrolü (sezon-özel → genel) ─────────────────────
    if season and season >= 2:
        season_cache_key = f"{parsed_title} Season {season}"
        cached = _cache_get(season_cache_key)
        if cached:
            print(f"{Fore.GREEN}   [MediaID] CACHE HIT (S{season:02d}): '{cached.get('title')}' "
                  f"({cached.get('source', 'Cache')}){Style.RESET_ALL}")
            _log_metadata_summary(cached, season, episode)
            return _inject_episode_info(cached, ep_info)

    # Genel cache: SADECE sezon<=1 icin kullan
    # season>=2 ise genel key eski S1 datasini dondurur, atla
    if not (season and season >= 2):
        cached = _cache_get(parsed_title)
        if cached:
            print(f"{Fore.GREEN}   [MediaID] CACHE HIT: '{cached.get('title')}' "
                  f"({cached.get('source', 'Cache')}){Style.RESET_ALL}")
            _log_metadata_summary(cached, season, episode)
            return _inject_episode_info(cached, ep_info)

    # ── ADIM 2: Sezon-bilinçli API waterfall ───────────────────────────
    _year_hint    = _extract_year_from_filename(filepath)
    # AI season_title varsa arama listesine en oce ekle (Jikan/MAL icin kritik)
    _ai_season_title = ai_classify.get('season_title') if ai_classify else None
    if _ai_season_title:
        print(f"{Fore.CYAN}   [MediaID] AI season_title: '{_ai_season_title}' → Jikan/MAL aramasi icin kullanilacak{Style.RESET_ALL}")
    search_titles = _build_search_titles(
        parsed_title, season, part, alt_title, search_hint,
        season_title=_ai_season_title,
        media_type=media_type
    )
    metadata      = None
    matched_title = parsed_title

    for search_title in search_titles:
        if search_title != parsed_title:
            print(f"{Fore.YELLOW}   [MediaID] Sezona ozel arama: '{search_title}'{Style.RESET_ALL}")
        metadata = fetch_media_metadata(
            search_title, translator, media_type, _year_hint,
            season=season   # AniList sezon zinciri icin
        )
        if metadata:
            matched_title = search_title
            break

    if metadata:
        # Sezon-özel arama başarılıysa o key'e de cache'le
        if matched_title != parsed_title and season:
            _cache_set(f"{parsed_title} Season {season}", metadata)
        _log_metadata_summary(metadata, season, episode)
        # AI classify sonucunu metadata'ya yaz (Wikidata P31 filtresi icin altin deger)
        if ai_classify:
            metadata.setdefault('ai_media_type', ai_classify.get('media_type'))
            metadata.setdefault('ai_title',      ai_classify.get('title') or parsed_title)
            metadata.setdefault('ai_season_title', ai_classify.get('season_title'))
        return _inject_episode_info(metadata, ep_info)

    # ── ADIM 3: AI ile isim tespiti → tekrar sezon-bilinçli API ────────
    if sources.get("ai_fallback"):
        raw_filename = os.path.basename(filepath)
        print(f"{Fore.YELLOW}   [MediaID] AI ile dosya adi analizi: '{raw_filename}'...{Style.RESET_ALL}")
        ai_title = _ai_identify_title(raw_filename, translator)

        if ai_title and ai_title.lower() != parsed_title.lower():
            print(f"{Fore.CYAN}   [MediaID] AI tespit: '{ai_title}' → API tekrar...{Style.RESET_ALL}")

            cached = _cache_get(ai_title)
            if cached:
                print(f"{Fore.GREEN}   [MediaID] CACHE HIT (AI isim): '{cached.get('title')}'{Style.RESET_ALL}")
                if ai_classify:
                    cached.setdefault('ai_media_type', ai_classify.get('media_type'))
                    cached.setdefault('ai_title',      ai_classify.get('title') or ai_title)
                    cached.setdefault('ai_season_title', ai_classify.get('season_title'))
                return _inject_episode_info(cached, ep_info)

            ai_search_titles = _build_search_titles(
                ai_title, season, part,
                season_title=_ai_season_title,
                media_type=media_type
            )
            for search_title in ai_search_titles:
                metadata = fetch_media_metadata(
                    search_title, translator, media_type, _year_hint,
                    season=season   # AniList season chain icin
                )
                if metadata:
                    if ai_classify:
                        metadata.setdefault('ai_media_type', ai_classify.get('media_type'))
                        metadata.setdefault('ai_title',      ai_classify.get('title') or ai_title)
                    _cache_set(parsed_title, metadata)
                    return _inject_episode_info(metadata, ep_info)

    # ── ADIM 4: AI doğrudan metadata üret ──────────────────────────────
    if sources.get("ai_fill_gaps"):
        print(f"{Fore.YELLOW}   [MediaID] Tum kaynaklar basarisiz → AI metadata uretiyor...{Style.RESET_ALL}")
        season_note = f" (Season {season})" if season and season >= 2 else ""
        empty_meta = {
            "title": parsed_title + season_note, "title_jp": "", "type": "",
            "episodes": "?", "status": "", "genres": [],
            "characters": [], "synopsis": "", "score": None,
            "year": None, "source": "AI",
        }
        filled = _ai_fill_gaps(empty_meta, translator)
        if filled.get("genres") or filled.get("characters") or filled.get("synopsis"):
            if ai_classify:
                filled.setdefault('ai_media_type', ai_classify.get('media_type'))
                filled.setdefault('ai_title',      ai_classify.get('title') or parsed_title)
                filled.setdefault('ai_season_title', ai_classify.get('season_title'))
            _cache_set(parsed_title, filled)
            print(f"{Fore.GREEN}   [MediaID] AI metadata tamamlandi.{Style.RESET_ALL}")
            return _inject_episode_info(filled, ep_info)

    print(f"{Fore.YELLOW}   [MediaID] Belirlenemedi → ceviriye baglamlı bilgi verilmeyecek.{Style.RESET_ALL}")
    return None

# ──────────────────────────────────────────────────────────────
# BÖLÜM 9: PROMPT BAĞLAMI OLUŞTURUCU
# ──────────────────────────────────────────────────────────────


# ── Altyazı Kaynak Kalite Tespiti ────────────────────────────────────────────
# Bilinen düşük kaliteli fansub grup kalıpları
_KNOWN_FANSUB_GROUPS = [
    "horriblesubs", "kayoanime", "subsplease", "erai-raws", "judas",
    "commie", "hiryuu", "gg", "doremi", "eclipse", "chihiro",
    "underwater", "doki", "coalgirls", "a-s", "sage", "evildemon989",
    "fff", "thora", "rip", "blu-ray", "bd",
]

# Hız/makine çevirisi belirteçleri — bu kelimeler fansubda çok geçer
_FANSUB_TEXT_SIGNALS = [
    "...!", "Eh?", "Huh?", "Ugh.", "Tch.", "Hmph.",
    "W-wait", "Y-you", "I-I", "Th-that", "N-no",
]

def score_subtitle_quality(filepath: str) -> dict:
    """
    Bir altyazı dosyasının kalite skorunu hesaplar.
    Döner: {score: 0-100, label: 'LOW'|'MEDIUM'|'HIGH', reasons: [...]}
    
    - Dosya adından fansub grubu tespiti
    - İçerik analizi (ortalama cümle uzunluğu, titreme, yapı)
    """
    import re as _re

    filename = os.path.basename(filepath).lower()
    reasons = []
    penalty = 0

    # ── 1. Dosya adı fansub tespiti ──────────────────────────────────────
    # [GroupName] kalıbı
    if _re.match(r'^\[.+?\]', os.path.basename(filepath)):
        reasons.append("fansub_bracket_group")
        penalty += 25
    # Bilinen grup adları
    for grp in _KNOWN_FANSUB_GROUPS:
        if grp in filename:
            reasons.append(f"known_fansub:{grp}")
            penalty += 20
            break

    # ── 2. İçerik analizi ────────────────────────────────────────────────
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        dialogues = []
        for line in content.splitlines():
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    text = _re.sub(r'\{[^}]*\}', '', parts[9])
                    text = text.replace('\\N', ' ').replace('\\n', ' ').strip()
                    if text:
                        dialogues.append(text)

        if dialogues:
            # Ortalama satır uzunluğu (çok kısa = muhtemelen kötü çeviri)
            avg_len = sum(len(d) for d in dialogues) / len(dialogues)
            if avg_len < 15:
                reasons.append(f"very_short_avg({avg_len:.0f}ch)")
                penalty += 15
            elif avg_len < 25:
                reasons.append(f"short_avg({avg_len:.0f}ch)")
                penalty += 8

            # Titreyen kelimeler (W-wait, Y-you tarzı)
            stutter_count = sum(
                1 for d in dialogues
                if any(sig in d for sig in _FANSUB_TEXT_SIGNALS)
            )
            if stutter_count > len(dialogues) * 0.05:
                reasons.append(f"stutter_signals({stutter_count})")
                penalty += 12

            # Çok kısa satır oranı (< 5 karakter)
            short_ratio = sum(1 for d in dialogues if len(d) < 5) / len(dialogues)
            if short_ratio > 0.1:
                reasons.append(f"many_short_lines({short_ratio:.0%})")
                penalty += 10

    except Exception:
        pass  # İçerik analizi yapılamadıysa devam

    # ── 3. Skor ve etiket ────────────────────────────────────────────────
    score = max(0, 100 - penalty)
    if score < 40:
        label = "LOW"
    elif score < 70:
        label = "MEDIUM"
    else:
        label = "HIGH"

    return {"score": score, "label": label, "reasons": reasons}


