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
def _clean_title(title: str) -> str:
    """
    Baslik metninden kose parantez, dosya uzantisi, sezon/bolum bilgisi,
    yil ve yayin etiketlerini agresif ve akilli sekilde temizler.
    """
    if not title:
        return title
        
    # 0. Strip common video extensions
    title_clean = re.sub(r'\.(mkv|mp4|avi|ts|m4v|flv|wmv|srt|ass)$', '', title, flags=re.I)
    
    # 1. Truncate at SxxExx or Sxx (Season / Episode indicators)
    # Western series are normally structured as Show.Name.S01E02...
    m_season = re.search(r'\b[Ss]\d{1,2}[Ee]\d{1,3}\b', title_clean)
    if m_season:
        title_clean = title_clean[:m_season.start()]
    else:
        m_s = re.search(r'\b[Ss]eason\s*\d+\b|\b[Ss]\d{1,2}\b', title_clean, flags=re.I)
        if m_s and m_s.start() > 2:
            title_clean = title_clean[:m_s.start()]
            
    # 2. Truncate at Year if followed by quality/codec tags (Movies)
    m_year = re.search(r'\b((?:19|20)\d{2})\b', title_clean)
    if m_year:
        after_text = title_clean[m_year.end():].lower()
        if re.search(r'\b(1080p|720p|2160p|4k|bluray|web|dvd|extended|imax|x264|x265|hevc|h264|h265|dd5|dts|aac|ac3|nf|amazon|netflix|apple|disney|sparks|rarbg|wiki)\b', after_text):
            title_clean = title_clean[:m_year.start()]
            
    # 3. Replace dots and underscores with spaces
    t = title_clean.replace('.', ' ').replace('_', ' ')
    
    # 4. Kose parantez temizleme (fansub gruplari vb.)
    _m = re.match(r'^\[([^\]]+)\]\s*((?:Season|Part|Cour)\s*\d+.*)', t, re.I)
    if _m:
        t = (_m.group(1) + ' ' + _m.group(2)).strip()
    else:
        _m2 = re.match(r'^\[([^\]]+)\]\s*$', t)
        if _m2:
            t = _m2.group(1).strip()
        else:
            t = re.sub(r'^\s*\[[^\]]+\]\s*', '', t)
            t = re.sub(r'\s*\[[^\]]+\]\s*$', '', t)
            
    t = re.sub(r'\s*\(TV\)\s*$', '', t, flags=re.I)
    t = re.sub(r'\s*\(ONA\)\s*$', '', t, flags=re.I)
    t = re.sub(r'\s*\(OVA\)\s*$', '', t, flags=re.I)
    
    # 5. Strip common torrent tags
    t = re.sub(r'\b(s\d+e\d+|s\d+|e\d+|\d+p|x264|x265|hevc|h264|h265|bluray|webrip|hdtv|imax|extended|dd5\.?1|dts|aac|ac3|hdr|10bit|dual[\s-]*audio|multi[\s-]*audio)\b', '', t, flags=re.I)
    
    # Remove year hints
    t = re.sub(r'\b(19|20)\d{2}\b', '', t)
    
    # Strip trailing release groups like -MeGusta, -WDYM, -NTb
    t = re.sub(r'\s*-\s*[A-Za-z0-9]+$', '', t)
    t = re.sub(r'\s*-\s*$', '', t)
    
    # Strip any empty brackets/parentheses left from tag removal
    t = re.sub(r'\[\s*\]', '', t)
    t = re.sub(r'\(\s*\)', '', t)
    
    # Strip trailing episode numbers from anime titles (e.g. - 03 or - 01v2)
    t = re.sub(r'\s*-\s*\d{1,3}(?:[vV]\d)?\s*$', '', t)
    
    return ' '.join(t.split()).strip()

def parse_episode_info(filepath: str) -> dict:
    """
    Dosya adından sezon, bölüm ve film sıra numarasını çıkarır.

    Örnekler:
      "OSHI.NO.KO.S03E03.mkv"              → {'season': 3, 'episode': 3, 'part': None}
      "[CrappySubs] Oshi No Ko - S03E01v2" → {'season': 3, 'episode': 1, 'part': None}
      "[SubsPlease] Frieren - 05 (1080p)"  → {'season': 1, 'episode': 5, 'part': None}
      "Dragon.Ball.Super.Movie.2.mkv"      → {'season': None, 'episode': None, 'part': 2}
    """
    filename = os.path.splitext(os.path.basename(filepath))[0]
    result = {'season': None, 'episode': None, 'part': None}

    # S01E01 / S01E01v2 formatı — en güvenilir
    m = re.search(r'[Ss](\d{1,2})[Ee](\d{2,3})', filename)
    if m:
        result['season'] = int(m.group(1))
        result['episode'] = int(m.group(2))
        return result

    # Anime tarzı: "- 05 -", "- 12v2 (", " 05 [" — sezon belirtilmemiş → S1
    m = re.search(r'[-\s](\d{2,3})(?:[vV]\d)?[-\s\(\[]', filename)
    if m:
        ep_num = int(m.group(1))
        if 1 <= ep_num < 500:  # Makul bölüm aralığı (yıl değil)
            result['season'] = 1
            result['episode'] = ep_num
            return result

    # Film sekansı: "Movie 2", "Part II", "Part 3"
    m = re.search(r'(?:Movie|Part|Film)[\s._-]*(\d+|II|III|IV|V)\b', filename, re.IGNORECASE)
    if m:
        roman_map = {'II': 2, 'III': 3, 'IV': 4, 'V': 5}
        val = m.group(1)
        result['part'] = int(val) if val.isdigit() else roman_map.get(val.upper())
        return result

    return result

def _read_ass_script_info(filepath: str) -> dict:
    """
    ASS/SSA dosyasının [Script Info] bölümünden metadata çıkarır.

    Tipik [Script Info] içeriği:
      [Script Info]
      Title: Oshi no Ko Season 3 - Episode 01
      Original Script: CrappySubs
      Script Updated By: None
      Update Details: None

    Döner:
      {'title': '...', 'original_script': '...', 'comments': [...]}
    """
    result = {}
    try:
        # UTF-8 ile dene, hata çıkarsa latin-1 ile
        for enc in ('utf-8-sig', 'utf-8', 'shift-jis', 'latin-1'):
            try:
                with open(filepath, 'r', encoding=enc, errors='replace') as f:
                    lines = f.readlines(8192)  # İlk 8KB yeterli
                break
            except Exception:
                continue
        else:
            return result

        in_script_info = False
        comments = []
        for line in lines:
            line = line.strip()
            if line.lower() == '[script info]':
                in_script_info = True
                continue
            if in_script_info:
                if line.startswith('[') and line.endswith(']'):
                    break  # Başka section başladı
                if line.startswith(';'):
                    comments.append(line[1:].strip())
                    continue
                if ':' in line:
                    key, _, val = line.partition(':')
                    key = key.strip().lower()
                    val = val.strip()
                    if key == 'title' and val and val not in ('?', '', 'untitled', 'default'):
                        result['title'] = val
                    elif key in ('original script', 'translator', 'script author'):
                        result['original_script'] = val

        if comments:
            result['comments'] = comments

    except Exception:
        pass
    return result

def _read_srt_header(filepath: str) -> str:
    """
    SRT dosyasının ilk birkaç bloğundan diyalog metni çıkarır.
    (SRT'de metadata yok — sadece içerik analizi için kullanılır)
    """
    try:
        for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                with open(filepath, 'r', encoding=enc, errors='replace') as f:
                    return f.read(4096)
            except Exception:
                continue
    except Exception:
        pass
    return ""

def _ffprobe_subtitle_meta(video_path: str) -> dict:
    """
    MKV/MP4 video dosyasındaki subtitle track metadata'sını çeker.
    FFprobe kullanır — mevcut path tespiti subtitle_processor'daki gibi.

    Döner:
      {'title': '...', 'language': '...', 'filename': '...'}
    """
    result = {}
    try:
        import subprocess
        # FFprobe'u sisteme göre bul
        ffprobe_candidates = [
            'ffprobe',
            r'C:\Program Files\FFMPEG\bin\ffprobe.exe',
            r'C:\ffmpeg\bin\ffprobe.exe',
        ]
        # Proje içine de bak
        here = _SCRIPT_DIR
        for extra in [os.path.join(here, 'ffprobe.exe'),
                      os.path.join(here, 'tools', 'ffprobe.exe'),
                      os.path.join(here, '..', 'ffprobe.exe')]:
            if os.path.isfile(extra):
                ffprobe_candidates.insert(0, extra)

        cmd = None
        for probe in ffprobe_candidates:
            try:
                subprocess.run([probe, '-version'], capture_output=True, timeout=3)
                cmd = probe
                break
            except Exception:
                continue

        if not cmd:
            return result

        import json as _json
        proc = subprocess.run(
            [cmd, '-v', 'quiet', '-print_format', 'json',
             '-show_streams', '-select_streams', 's',
             video_path],
            capture_output=True, text=True, timeout=15
        )
        if proc.returncode != 0:
            return result

        data = _json.loads(proc.stdout or '{}')
        streams = data.get('streams', [])

        # İngilizce subtitle track'i önceliklendir
        best = None
        for s in streams:
            tags = s.get('tags') or {}
            lang = tags.get('language', '').lower()
            if lang in ('eng', 'en', ''):
                best = tags
                break
        if not best and streams:
            best = streams[0].get('tags', {})

        if best:
            title = best.get('title') or best.get('filename') or ''
            if title:
                result['title'] = title
            result['language'] = best.get('language', '')

    except Exception:
        pass
    return result

def _sample_dialogue_lines(filepath: str, max_lines: int = 30) -> list[str]:
    """
    ASS veya SRT dosyasından ilk N diyalog satırını çıkarır.
    API tespiti başarısız olursa AI'ya gönderilir.
    """
    lines = []
    ext = os.path.splitext(filepath)[1].lower()
    try:
        for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
            try:
                with open(filepath, 'r', encoding=enc, errors='replace') as f:
                    raw_lines = f.readlines()
                break
            except Exception:
                continue
        else:
            return lines

        if ext in ('.ass', '.ssa'):
            # ASS Dialogue: 0,0:00:10.00,0:00:13.00,Default,,0,0,0,,Text burada
            for line in raw_lines:
                if line.startswith('Dialogue:'):
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        text = parts[9].strip()
                        # ASS override tag'lerini temizle
                        text = re.sub(r'\{[^}]*\}', '', text)
                        text = text.replace(r'\N', ' ').replace(r'\n', ' ').strip()
                        if text and len(text) > 3:
                            lines.append(text)
                            if len(lines) >= max_lines:
                                break
        else:
            # SRT: satır numarası, zaman kodu, metin
            collecting = False
            for line in raw_lines:
                line = line.strip()
                if re.match(r'^\d+$', line):
                    collecting = False
                    continue
                if re.match(r'\d{2}:\d{2}:\d{2}', line):
                    collecting = True
                    continue
                if collecting and line:
                    lines.append(line)
                    if len(lines) >= max_lines:
                        break

    except Exception:
        pass
    return lines

def extract_title_from_content(filepath: str, translator=None) -> dict:
    """
    Dosya içeriğinden başlık ve medya ipuçları çıkarır.

    Döner:
      {
        'title'       : 'Oshi no Ko',      # Bulunan başlık (boş olabilir)
        'confidence'  : 'high'/'medium'/'low',
        'from'        : 'ass_script_info' | 'ffprobe' | 'dialogue_ai',
        'media_type'  : 'anime'/'series'/'movie'/'unknown',
        'raw_dialogue': [...]              # AI için diyalog örnekleri
      }
    """
    result = {
        'title': '', 'confidence': 'low',
        'from': '', 'media_type': 'unknown', 'raw_dialogue': []
    }
    ext = os.path.splitext(filepath)[1].lower()
    is_video = ext in ('.mkv', '.mp4', '.avi', '.webm')
    is_sub   = ext in ('.ass', '.ssa', '.srt', '.vtt')

    # ── Yol 1: ASS/SSA Script Info ──────────────────────────
    if is_sub and ext in ('.ass', '.ssa'):
        info = _read_ass_script_info(filepath)
        raw_title = info.get('title', '')
        if raw_title:
            # Bölüm numarasını temizle
            clean = re.sub(
                r'[-_\s]+(?:ep(?:isode)?|s\d+e\d+|\d+)[\s\d]*$',
                '', raw_title, flags=re.IGNORECASE
            ).strip(' -_:')

            # Fansub grup adı mı? (CrappySubs gibi gruplar Title'a kendi adlarını yazar)
            is_fansub_name = clean.lower().replace(' ', '').replace('-', '') in {
                g.replace('-', '').replace(' ', '') for g in _KNOWN_FANSUB_GROUPS
            }
            # Çok kısa veya genel terimler de reddedilsin
            _junk_titles = {'default', 'untitled', '?', 'subtitle', 'subs', 'sub', 'none', ''}
            is_junk = clean.lower() in _junk_titles

            if len(clean) >= 3 and not is_fansub_name and not is_junk:
                print(f"{Fore.GREEN}   [Icerik] ASS Script Info title: '{clean}'{Style.RESET_ALL}")
                result['title'] = clean
                result['confidence'] = 'high'
                result['from'] = 'ass_script_info'
                if re.search(r'\b(movie|film|gekijouban)\b', clean, re.IGNORECASE):
                    result['media_type'] = 'movie'
            elif is_fansub_name:
                print(f"{Fore.YELLOW}   [Icerik] ASS title fansub grubu adi ('{clean}') → atlandi.{Style.RESET_ALL}")

    # ── Yol 2: MKV FFprobe track metadata ──────────────────
    if is_video and not result['title']:
        meta = _ffprobe_subtitle_meta(filepath)
        track_title = meta.get('title', '')
        if track_title:
            clean = _clean_title(track_title)  # Bölüm temizle
            if len(clean) >= 3 and clean.lower() not in ('english', 'subtitle', 'subs', 'full'):
                print(f"{Fore.GREEN}   [İçerik] MKV track metadata: '{clean}'{Style.RESET_ALL}")
                result['title'] = clean
                result['confidence'] = 'high'
                result['from'] = 'ffprobe'

    # ── Yol 3: Diyalog örnekleme ──────────────────────────
    if is_sub:
        dialogue = _sample_dialogue_lines(filepath)
        result['raw_dialogue'] = dialogue[:15]  # AI için sakla

        # Eğer hala başlık yoksa ve AI erişilebilirse, diyalogdan çıkar
        if not result['title'] and translator and dialogue:
            try:
                sample_text = '\n'.join(dialogue[:20])
                prompt = (
                    f"Analyze these subtitle lines and identify the anime, movie, or TV series they are from.\n\n"
                    f"SUBTITLE SAMPLE:\n{sample_text}\n\n"
                    f"Rules:\n"
                    f"- Return ONLY the exact title. Nothing else.\n"
                    f"- Include the media type in parentheses: (anime), (movie), or (TV series)\n"
                    f"- Example: 'Attack on Titan (anime)' or 'Breaking Bad (TV series)'\n"
                    f"- If you cannot determine it from the dialogue, return: UNKNOWN\n"
                    f"Answer:"
                )
                ai_result = translator.translate_single_line(prompt)
                if ai_result and 'UNKNOWN' not in ai_result.upper() and len(ai_result) < 120:
                    # Tür parse et
                    m_type = 'unknown'
                    if '(anime)' in ai_result.lower():
                        m_type = 'anime'
                    elif '(movie)' in ai_result.lower() or '(film)' in ai_result.lower():
                        m_type = 'movie'
                    elif '(tv series)' in ai_result.lower() or '(series)' in ai_result.lower():
                        m_type = 'series'
                    # Tür parantezini temizle
                    clean_title = re.sub(r'\s*\([^)]*\)\s*$', '', ai_result).strip()
                    if clean_title:
                        print(f"{Fore.GREEN}   [İçerik] Diyalog AI tespiti: '{clean_title}' ({m_type}){Style.RESET_ALL}")
                        result['title'] = clean_title
                        result['confidence'] = 'medium'
                        result['from'] = 'dialogue_ai'
                        result['media_type'] = m_type
            except Exception as e:
                print(f"{Fore.YELLOW}   [İçerik] Diyalog AI hatasi: {e}{Style.RESET_ALL}")

    return result

# ──────────────────────────────────────────────────────────────
# BÖLÜM 4c: MEDYA TÜRÜ TAHMIN EDİCİSİ (Disambiguation)
# ──────────────────────────────────────────────────────────────

# Bilinen anime fansub grubu adları (dosya adında köşeli parantezle)
_KNOWN_FANSUB_GROUPS = {
    'subsplease', 'crappysubs', 'erai-raws', 'horriblesubs', 'judas',
    'nandesuka', 'ember', 'asw', 'tsundere-raws', 'reaktor', 'cerberus',
    'neonetworktm', 'yametekudasai', 'smol', 'sugoi-subs', 'akihito',
    'commie', 'horrible', 'doki', 'underwater', 'gg', 'ss-eclipse',
    'chihiro', 'utw', 'coalgirls', 'bakabt', 'thora', 'eclipse',
    'mori', 'gg-subs', 'comiket', 'hybrid-subs', 'sallysubs',
    'erairaw', 'yudai', 'neko', 'shintori', 'bds', 'jcstaff',
    'raze', 'fffansubs', 'frostii', 'kaleidoscope', 'aniway',
}

# Batı yapımı içerik üreticileri
_WESTERN_NETWORKS = {
    'hbo', 'netflix', 'amazon', 'bbc', 'nbc', 'cbs', 'abc', 'fox',
    'amc', 'hulu', 'disney', 'showtime', 'starz', 'fx', 'cw', 'nbc',
    'peacock', 'apple', 'paramount', 'max', 'bravo', 'usa',
}

def detect_media_type(filepath: str) -> str:
    """
    Dosya adı ve yol bilgisinden medya türünü tahmin eder.

    Returns:
      'anime'   → Kesinlikle anime (Jikan/AniList önce denensin)
      'series'  → Batı dizisi (TVMaze/TMDB önce denensin)
      'movie'   → Film (TMDB önce denensin)
      'unknown' → Belirsiz (tam waterfall)

    Skor sistemi: Her ipucu pozitif ya da negatif puan verir.
    Anime: +puan → anime_score
    Batı:  +puan → western_score
    Film:  +puan → movie_score
    """
    filename = os.path.basename(filepath).lower()
    parent   = os.path.basename(os.path.dirname(filepath)).lower()
    grandpar = os.path.basename(os.path.dirname(os.path.dirname(filepath))).lower()

    anime_score   = 0
    western_score = 0
    movie_score   = 0

    # ── Güçlü anime sinyalleri ──────────────────────────────
    # Bilinen fansub grubu adı köşeli parantezde
    bracket_groups = re.findall(r'\[([^\]]+)\]', filename)
    for grp in bracket_groups:
        if grp.lower() in _KNOWN_FANSUB_GROUPS:
            anime_score += 5
            break

    # Köşeli parantezli herhangi bir grup adı (genel anime kalıbı)
    if re.search(r'^\[', os.path.basename(filepath)):
        anime_score += 2

    # Anime tarzı bölüm numarası: "- 01 -", "- 12v2 -", " 01 (", vb.
    if re.search(r'[-\s]\d{2}(?:v\d)?[-\s\(\[]', filename):
        anime_score += 3
    # "EP01", "ep.01" tarzı
    if re.search(r'\bep\.?\d{2,3}\b', filename):
        anime_score += 2

    # Video kalitesi anime tarzı: [1080p] köşeli parantezde
    if re.search(r'\[\d{3,4}p\]', filename):
        anime_score += 2

    # Hash kod var: [7A1BD58F]
    if re.search(r'\[[A-Fa-f0-9]{6,8}\]', filename):
        anime_score += 3

    # Üst klasör ipuçları
    for anm_kw in ['anime', 'sezonu', 'anidb', 'subbed', 'crunchyroll']:
        if anm_kw in parent or anm_kw in grandpar:
            anime_score += 2

    # ── Güçlü Batı dizi sinyalleri ───────────────────────────
    # S01E01 formatı — Dikkat: bazı animeler de bu formatı kullanır!
    # Diğer wesern sinyallerle birlikte varsa yüksek skor, tek başınaysa orta.
    has_season_ep = bool(re.search(r'\bs\d{2}e\d{2,3}\b', filename))
    if has_season_ep:
        if bracket_groups:
            # Hem köşeli parantez HEM S__E__: belirsiz, düşük ağırlık
            western_score += 1
        else:
            # Parantez yok, S__E__ var: orta ağırlık
            western_score += 3

    # Bilinen Batı ağları/kanalları — çok güçlü sinyal
    for net in _WESTERN_NETWORKS:
        if re.search(r'\b' + re.escape(net) + r'\b', filename) or re.search(r'\b' + re.escape(net) + r'\b', parent):
            western_score += 4
            if has_season_ep:
                western_score += 2  # HDTV + S__E__ = kesin Batı
            break

    # Batı tarzı kalite ETİKETİ: HDTV özellikle güçlü sinyal
    if re.search(r'\bhdtv\b', filename):
        western_score += 3
    elif re.search(r'\b(?:web-dl|webrip|bdrip)\b', filename):
        # CR.WEB-DL veya AMZN.WEB-DL = Crunchyroll/Amazon anime ripi → anime sinyali!
        if re.search(r'\b(cr|amzn)\b', filename):
            anime_score += 5   # Crunchyroll/Amazon anime (guclu sinyal)
            western_score = max(0, western_score - 2)
        else:
            western_score += 2
    # BluRay/1080p tek başına zayıf sinyal (animeler de kullanır)
    elif re.search(r'\bbluray\b', filename) and not bracket_groups:
        western_score += 1

    # Nokta ile ayrılmış format (Supernatural.S04E28.mkv)
    if re.search(r'[a-z]\.[a-z]', filename) and not bracket_groups:
        western_score += 1

    # Üst klasör: "series", "tv shows", vb.
    for w_kw in ['series', 'tv show', 'shows', 'television']:
        if w_kw in parent or w_kw in grandpar:
            western_score += 2

    # ── Film sinyalleri ───────────────────────────────────────
    # 4 haneli yıl + sezon formatı YOK → film (Suzume.2022.mkv)
    if re.search(r'\b(19|20)\d{2}\b', filename) and not has_season_ep:
        movie_score += 4   # Film için güçlü sinyal

    # "movie", "film", "gekijouban" kelimesi
    if re.search(r'\b(?:movie|film|the\.movie|gekijouban)\b', filename):
        movie_score += 5

    # Üst klasör: "movies", "films"
    for m_kw in ['movies', 'films', 'movie', 'filmler']:
        if m_kw in parent or m_kw in grandpar:
            movie_score += 3

    # ── Karar ver ────────────────────────────────────────────
    scores = {'anime': anime_score, 'series': western_score, 'movie': movie_score}
    best_type  = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Çok düşük skor → belirsiz
    if best_score < 2:
        return 'unknown'

    # Western ve anime arasında çok yakınsa → unknown
    if best_type == 'anime' and western_score >= anime_score - 1:
        return 'unknown'
    if best_type == 'series' and anime_score >= western_score - 1:
        return 'unknown'

    # ÖZEL KURAL: S04E28 var ama HDTV/network/WEB-DL gibi kesin Batı
    # sinyali yoksa → 'unknown' (anime de SxxExx kullanabilir!)
    # Örnek: Attack.on.Titan.S04E28.1080p.mkv → unknown (Jikan DE denensin)
    if best_type == 'series' and has_season_ep and anime_score == 0:
        has_strong_western = (
            any(net in filename or net in parent for net in _WESTERN_NETWORKS)
            or re.search(r'\bhdtv\b', filename)
            or re.search(r'\b(web-dl|webrip|bdrip)\b', filename)
        )
        if not has_strong_western:
            return 'unknown'

    return best_type


# ──────────────────────────────────────────────────────────────
# BÖLÜM 5: API İSTEKLERİ — KAYNAK BAZINDA
# ──────────────────────────────────────────────────────────────

def _safe_get(url: str, **kwargs) -> dict | None:
    """GET isteği yap, hata olursa None döner."""
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def _safe_post(url: str, **kwargs) -> dict | None:
    """POST isteği yap, hata olursa None döner."""
    try:
        r = requests.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ── 5a. Jikan v4 (MAL) ──────────────────────────────────────

def _query_jikan(title: str) -> dict | None:
    """Jikan v4 API ile anime ara (Official MAL API fallback'i ile)."""
    _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
    
    def _query_official_mal_api(q_str: str) -> list | None:
        client_id = "9dfa9b926eecef62128b6d464c7e33b9"
        url = "https://api.myanimelist.net/v2/anime"
        headers = {
            "X-MAL-CLIENT-ID": client_id,
            "User-Agent": "KitsugiAnimeList/1.0"
        }
        params = {
            "q": q_str,
            "limit": 5,
            "fields": "id,title,alternative_titles,start_date,mean,num_episodes,media_type,genres,nsfw,synopsis"
        }
        try:
            r = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                data = r.json()
                results = []
                for item in data.get("data", []):
                    node = item.get("node", {})
                    genres_mapped = [{"name": g.get("name")} for g in node.get("genres", [])]
                    
                    aired_year = None
                    start_date = node.get("start_date")
                    if start_date and len(start_date) >= 4:
                        try:
                            aired_year = int(start_date[:4])
                        except ValueError:
                            pass
                    
                    alt = node.get("alternative_titles") or {}
                    titles_mapped = [{"type": "Default", "title": node.get("title")}]
                    if alt.get("en"):
                        titles_mapped.append({"type": "English", "title": alt.get("en")})
                    if alt.get("ja"):
                        titles_mapped.append({"type": "Japanese", "title": alt.get("ja")})
                    synonyms = alt.get("synonyms") or []
                    for syn in synonyms:
                        titles_mapped.append({"type": "Synonym", "title": syn})
                    
                    results.append({
                        "mal_id": node.get("id"),
                        "title": node.get("title"),
                        "title_english": alt.get("en") or node.get("title"),
                        "title_japanese": alt.get("ja") or "",
                        "titles": titles_mapped,
                        "type": (node.get("media_type") or "TV").upper(),
                        "episodes": node.get("num_episodes"),
                        "score": node.get("mean"),
                        "synopsis": node.get("synopsis"),
                        "genres": genres_mapped,
                        "themes": [],
                        "status": node.get("status") or "",
                        "aired": {"prop": {"from": {"year": aired_year}}}
                    })
                return results
        except Exception:
            pass
        return None

    words = title.split()
    # Kelime kelime azaltarak dene
    for i in range(len(words), 0, -1):
        q = " ".join(words[:i])
        url = f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(q)}&limit=5"
        data = _safe_get(url)
        
        candidates = None
        if data and data.get("data"):
            candidates = data["data"]
        else:
            candidates = _query_official_mal_api(q)
            
        if candidates:
            # Jikan zaten alaka sirasina gore siraliyor.
            # Sadece eksik veriyi (score=None VE episodes=None) filtrele — geri kalanlarin ilkini al.
            valid = [c for c in candidates
                     if c.get("score") is not None or c.get("episodes") is not None]

            # [FIX] Kelime ortusumu dogrulamasi: donulen animenin basligi
            # sorgunun onemli kelimeleriyle ortusmuyor mu? → reddet.
            # Ornek: 'dealing' sorusu → 'ItaKiss' → 'dealing' gecmiyor → RED
            _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                        title.lower()).split()
                        if w not in _STOP_W and len(w) >= 3}
            def _title_ok(entry):
                """Anime basliginin sorgu kelimeleriyle uyumunu kontrol et."""
                if not _q_words:
                    return True  # Kisa sorgu - dogrulama atla
                all_titles = ' '.join([
                    (entry.get('title') or ''),
                    (entry.get('title_english') or ''),
                    (entry.get('title_japanese') or ''),
                ] + [(s.get('title') or '') for s in (entry.get('titles') or [])]).lower()
                all_titles = re.sub(r'[^a-z0-9 ]', '', all_titles)
                overlap = {w for w in _q_words if w in all_titles}
                # Require substantial keyword overlap to prevent false positive matches
                return len(overlap) >= min(len(_q_words), 2)

            # Gecerli adaylardan sadece sorguyla uyumlu olanlar
            valid_ok = [c for c in valid if _title_ok(c)]
            all_ok   = [c for c in candidates if _title_ok(c)]

            if not valid_ok and not all_ok:
                # Bu sorgu uzunlugunda hicbir sonuc uyumlu degil → kisalt
                time.sleep(REQUEST_DELAY)
                continue

            def _get_overlap_score(entry):
                all_titles = ' '.join([
                    (entry.get('title') or ''),
                    (entry.get('title_english') or ''),
                    (entry.get('title_japanese') or ''),
                ] + [(s.get('title') or '') for s in (entry.get('titles') or [])]).lower()
                all_titles = re.sub(r'[^a-z0-9 ]', '', all_titles)
                overlap = {w for w in _q_words if w in all_titles}
                return len(overlap)

            if valid_ok:
                a = max(valid_ok, key=lambda c: (_get_overlap_score(c), -valid.index(c)))
            else:
                a = max(all_ok, key=lambda c: (_get_overlap_score(c), -candidates.index(c)))
            mal_id = a.get("mal_id")


            # Karakterleri çek (ayrı endpoint)
            characters = []
            if mal_id:
                time.sleep(REQUEST_DELAY)
                char_data = _safe_get(
                    f"https://api.jikan.moe/v4/anime/{mal_id}/characters"
                )
                if char_data:
                    for c in (char_data.get("data") or [])[:10]:
                        cname = (c.get("character") or {}).get("name", "")
                        if cname:
                            # "Hoshino, Aqua" → "Aqua Hoshino"
                            parts = [p.strip() for p in cname.split(",")]
                            characters.append(" ".join(reversed(parts)))

            genres = [g.get("name") for g in (a.get("genres") or [])]
            themes = [t.get("name") for t in (a.get("themes") or [])]
            all_genres = list(dict.fromkeys(genres + themes))  # tekrarsız

            # title_english yoksa title kullan; MAL bazen "[Title]" formatinda doner
            _jikan_title_raw = a.get("title_english") or a.get("title") or title
            title_en = re.sub(r"^\[|\]$", "", _clean_title(_jikan_title_raw)).strip()
            title_jp = a.get("title_japanese") or ""
            media_type = a.get("type") or "TV"   # TV, Movie, OVA, ONA…
            episodes  = a.get("episodes") or "?"
            status    = a.get("status") or ""
            synopsis  = (a.get("synopsis") or "")[:600]
            score     = a.get("score")
            year      = (a.get("aired") or {}).get("prop", {}).get("from", {}).get("year")

            return {
                "title":       title_en,
                "title_jp":    title_jp,
                "type":        media_type,
                "episodes":    episodes,
                "status":      status,
                "genres":      all_genres,
                "characters":  characters,
                "synopsis":    synopsis,
                "score":       score,
                "year":        year,
                "source":      "Jikan/MAL",
                "mal_id":      mal_id,
            }
        time.sleep(REQUEST_DELAY)
    return None

# ── 5b. AniList GraphQL ─────────────────────────────────────


def _extract_year_from_filename(filepath: str) -> int | None:
    """Dosya adindan yapim yilini cikarir. Ornek: Ace.Ventura.1994.mkv -> 1994"""
    m = re.search(r'\b(19[5-9]\d|20[0-3]\d)\b', os.path.basename(filepath))
    return int(m.group(1)) if m else None

_ANILIST_QUERY = """
query ($search: String, $idMal: Int, $id: Int) {
  Media(search: $search, idMal: $idMal, id: $id, type: ANIME) {
    id
    title { romaji english native }
    format
    episodes
    status
    genres
    tags { name }
    description(asHtml: false)
    averageScore
    startDate { year }
    characters(role: MAIN, perPage: 10) {
      nodes { name { full } }
    }
    relations {
      edges {
        relationType
        node { id title { romaji english } startDate { year } format }
      }
    }
  }
}
"""

def _query_anilist(title: str, mal_id: int | None = None, anilist_id: int | None = None) -> dict | None:
    """AniList GraphQL ile anime ara."""
    if anilist_id:
        variables = {"id": anilist_id}
    elif mal_id:
        variables = {"idMal": mal_id}
    else:
        variables = {"search": title}
    data = _safe_post(
        "https://graphql.anilist.co",
        json={"query": _ANILIST_QUERY, "variables": variables}
    )
    if not data:
        return None
    media = (data.get("data") or {}).get("Media")
    if not media:
        return None

    # Validate overlap if we did a search query (not by ID)
    if not anilist_id and not mal_id:
        _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                    'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
        _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                    title.lower()).split()
                    if w not in _STOP_W and len(w) >= 3}
        if _q_words:
            _titles_obj = media.get("title") or {}
            _syns = media.get("synonyms") or []
            _all_titles_str = ' '.join(filter(None, [
                _titles_obj.get("english"),
                _titles_obj.get("romaji"),
                _titles_obj.get("native")
            ] + _syns)).lower()
            _all_titles_str = re.sub(r'[^a-z0-9 ]', '', _all_titles_str)
            _overlap = {w for w in _q_words if w in _all_titles_str}
            if len(_overlap) < min(len(_q_words), 2):
                return None

    titles  = media.get("title") or {}
    title_en = titles.get("english") or titles.get("romaji") or title
    title_jp = titles.get("native") or ""
    genres  = (media.get("genres") or [])[:6]
    tags    = [(t.get("name") or "") for t in (media.get("tags") or [])][:4]
    all_genres = list(dict.fromkeys(genres + tags))
    synopsis   = (media.get("description") or "")[:600]
    chars_raw  = ((media.get("characters") or {}).get("nodes") or [])
    characters = [
        (c.get("name") or {}).get("full", "")
        for c in chars_raw
        if (c.get("name") or {}).get("full")
    ]

    return {
        "title":      title_en,
        "title_jp":   title_jp,
        "type":       media.get("format") or "TV",
        "episodes":   media.get("episodes") or "?",
        "status":     media.get("status") or "",
        "genres":     all_genres,
        "characters": characters,
        "synopsis":   synopsis,
        "score":      media.get("averageScore"),
        "year":       (media.get("startDate") or {}).get("year"),
        "source":     "AniList",
        "_anilist_id": media.get("id"),
        "_sequel_id":  next((
            e["node"]["id"] for e in
            ((media.get("relations") or {}).get("edges") or [])
            if e.get("relationType") == "SEQUEL"
            and (e.get("node") or {}).get("format") in ("TV","TV_SHORT","ONA",None)
        ), None),
    }

# ── 5c. Kitsu ───────────────────────────────────────────────



def _query_anilist_season(title: str, season_num: int) -> dict | None:
    """
    AniList Relations API ile sezon zincirini takip eder.
    Ornek: Oshi no Ko season=3 -> S1 -> SEQUEL -> S2 -> SEQUEL -> S3
    """
    if season_num <= 1:
        return _query_anilist(title)

    base = _query_anilist(title)
    if not base:
        return None

    current_id = base.get("_anilist_id")
    if not current_id:
        return None

    print(f"{Fore.CYAN}   [AniList] Sezon zinciri: S1 (ID:{current_id})...{Style.RESET_ALL}")

    for step in range(1, season_num):
        step_data = _query_anilist(None, anilist_id=current_id)
        if not step_data:
            print(f"{Fore.YELLOW}   [AniList] S{step+1} bulunamadi.{Style.RESET_ALL}")
            return None
        next_id = step_data.get("_sequel_id")
        if not next_id:
            print(f"{Fore.YELLOW}   [AniList] S{step+1} devam yok.{Style.RESET_ALL}")
            return None
        print(f"{Fore.CYAN}   [AniList] S{step+1} ID: {next_id}{Style.RESET_ALL}")
        current_id = next_id
        time.sleep(REQUEST_DELAY)

    result = _query_anilist(None, anilist_id=current_id)
    if result:
        if not result.get("characters") and base.get("characters"):
            result["characters"] = base["characters"]
        print(f"{Fore.GREEN}   [AniList] Sezon {season_num} bulundu!{Style.RESET_ALL}")
    return result

def _query_kitsu(title: str) -> dict | None:
    """Kitsu API ile anime ara."""
    url  = f"https://kitsu.io/api/edge/anime?filter[text]={requests.utils.quote(title)}&page[limit]=1"
    data = _safe_get(url, headers={"Accept": "application/vnd.api+json"})
    if not data or not data.get("data"):
        return None
    a    = data["data"][0].get("attributes", {})
    titles = a.get("titles") or {}
    
    # Check overlap to prevent matching random anime to western series/movies
    _STOP_W = {'the','a','an','is','of','in','to','with','and','or','for',
                'by','at','on','no','na','wa','ga','wo','de','wo','yo'}
    _q_words = {w.lower() for w in re.sub(r'[^a-z0-9 ]', '',
                title.lower()).split()
                if w not in _STOP_W and len(w) >= 3}
    if _q_words:
        _syns = a.get("abbreviatedTitles") or []
        _all_titles_str = ' '.join(filter(None, [
            titles.get("en"),
            titles.get("en_us"),
            titles.get("ja_jp"),
            a.get("canonicalTitle")
        ] + _syns)).lower()
        _all_titles_str = re.sub(r'[^a-z0-9 ]', '', _all_titles_str)
        _overlap = {w for w in _q_words if w in _all_titles_str}
        if len(_overlap) < min(len(_q_words), 2):
            return None

    title_en = titles.get("en") or titles.get("en_us") or a.get("canonicalTitle") or title
    title_jp = titles.get("ja_jp") or ""
    genres_raw = a.get("categories", {})  # Kitsu'da kategoriler ayrı endpoint'te
    synopsis   = (a.get("synopsis") or a.get("description") or "")[:600]
    ep_count   = a.get("episodeCount") or "?"
    status     = a.get("status") or ""
    subtype    = a.get("subtype") or "TV"
    year       = (a.get("startDate") or "")[:4] or None

    slug       = data["data"][0].get("id", "")  # Kitsu numeric ID (slug olarak kullanılır)
    # Canonical slug (URL için): attributes.slug varsa o, yoksa numeric id
    kitsu_slug = a.get("slug") or str(slug)
    # Kapak görseli
    poster_imgs = a.get("posterImage") or {}
    kitsu_cover = (poster_imgs.get("large") or poster_imgs.get("medium")
                   or poster_imgs.get("small") or "")

    return {
        "title":        title_en,
        "title_jp":     title_jp,
        "type":         subtype.upper(),
        "episodes":     ep_count,
        "status":       status,
        "genres":       [],
        "characters":   [],
        "synopsis":     synopsis,
        "score":        a.get("averageRating"),
        "year":         int(year) if year and year.isdigit() else None,
        "source":       "Kitsu",
        "_kitsu_slug":  kitsu_slug,
        "_kitsu_cover": kitsu_cover,
        "kitsu_url":    f"https://kitsu.io/anime/{kitsu_slug}" if kitsu_slug else "",
        "cover_url":    kitsu_cover,
    }

# ── 5d. TVMaze ──────────────────────────────────────────────

def _query_tvmaze(title: str) -> dict | None:
    """TVMaze API ile dizi/film ara."""
    url  = f"https://api.tvmaze.com/search/shows?q={requests.utils.quote(title)}"
    data = _safe_get(url)
    if not data or not isinstance(data, list):
        return None
    show = data[0].get("show") if data else None
    if not show:
        return None

    show_id  = show.get("id")
    genres   = show.get("genres") or []
    synopsis = re.sub(r'<[^>]+>', '', show.get("summary") or "")[:600]
    title_en = show.get("name") or title
    # Karakter listesi: /shows/{id}/cast endpoint
    characters = []
    if show_id:
        time.sleep(REQUEST_DELAY)
        cast_data = _safe_get(f"https://api.tvmaze.com/shows/{show_id}/cast")
        if cast_data and isinstance(cast_data, list):
            for c in cast_data[:10]:
                cname = (c.get("character") or {}).get("name", "")
                if not cname:
                    cname = (c.get("person") or {}).get("name", "")
                if cname:
                    characters.append(cname)

    return {
        "title":      title_en,
        "title_jp":   "",
        "type":       show.get("type") or "TV",
        "episodes":   "?",
        "status":     show.get("status") or "",
        "genres":     genres,
        "characters": characters,
        "synopsis":   synopsis,
        "score":      show.get("rating", {}).get("average"),
        "year":       (show.get("premiered") or "")[:4] or None,
        "source":     "TVMaze",
        "network":    (show.get("network") or {}).get("name") or "",
    }

# ── 5e. TMDB ────────────────────────────────────────────────

def _query_tmdb(title: str, api_key: str, year_hint: int = None, media_type: str = 'auto') -> dict | None:
    """The Movie Database (TMDB) ile dizi/film ara. API key gerekli.
    media_type: 'tv' → TV önce ara | 'movie' → Film önce ara | 'auto' → Film önce (eski davranis)
    """
    if not api_key:
        return None

    # TMDB genre_id -> isim tablosu (search endpoint sadece integer ID verir)
    _GENRE_MAP = {
        28:'Action', 12:'Adventure', 16:'Animation', 35:'Comedy', 80:'Crime',
        99:'Documentary', 18:'Drama', 10751:'Family', 14:'Fantasy', 36:'History',
        27:'Horror', 10402:'Music', 9648:'Mystery', 10749:'Romance',
        878:'Science Fiction', 10770:'TV Movie', 53:'Thriller', 10752:'War',
        37:'Western', 10759:'Action & Adventure', 10762:'Action & Adventure',
        10763:'News', 10764:'Reality', 10765:'Sci-Fi & Fantasy',
        10766:'Soap', 10767:'Talk', 10768:'War & Politics',
    }
    def _gids(ids):
        return [_GENRE_MAP[g] for g in (ids or []) if g in _GENRE_MAP]

    result = None

    # media_type'a gore arama sirasi belirle
    # 'tv'  → TV önce, film fallback
    # 'movie' veya 'auto' → Film önce, TV fallback
    _search_tv_first = (media_type == 'tv')
    _yr = f"&year={year_hint}" if year_hint else ""

    def _fetch_movie():
        url = (
            f"https://api.themoviedb.org/3/search/movie"
            f"?api_key={api_key}&query={requests.utils.quote(title)}&language=en-US&page=1{_yr}"
        )
        data = _safe_get(url)
        if not data or not data.get("results"):
            return None
        r = data["results"][0]
        movie_id = r.get("id")
        chars = []
        if movie_id:
            time.sleep(REQUEST_DELAY)
            cr = _safe_get(
                f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
                f"?api_key={api_key}&language=en-US"
            )
            if cr:
                _cast = cr.get("cast") or []
                # Anime filmlerde cast.character "(voice)" suffix içerir → karakter adını al
                _is_voice = any('(voice)' in (c.get('character') or '').lower() for c in _cast[:5])
                if _is_voice:
                    chars = [
                        (c.get('character') or '').replace('(voice)', '').replace('(Voice)', '').strip()
                        for c in _cast[:8]
                        if (c.get('character') or '').strip()
                    ]
                else:
                    chars = [c.get("name") for c in _cast[:8] if c.get("name")]
        return {
            "title":      r.get("title") or title,
            "title_jp":   r.get("original_title") if r.get("original_language") == "ja" else "",
            "type":       "Movie",
            "episodes":   1,
            "status":     "Released",
            "genres":     _gids(r.get("genre_ids")),
            "characters": chars,
            "synopsis":   (r.get("overview") or "")[:600],
            "score":      r.get("vote_average"),
            "year":       (r.get("release_date") or "")[:4] or None,
            "source":     "TMDB",
        }

    def _fetch_tv():
        url = (
            f"https://api.themoviedb.org/3/search/tv"
            f"?api_key={api_key}&query={requests.utils.quote(title)}&language=en-US&page=1"
        )
        data = _safe_get(url)
        if not data or not data.get("results"):
            return None
        r = data["results"][0]
        show_id = r.get("id")
        chars = []
        if show_id:
            time.sleep(REQUEST_DELAY)
            cr = _safe_get(
                f"https://api.themoviedb.org/3/tv/{show_id}/credits"
                f"?api_key={api_key}&language=en-US"
            )
            if cr:
                chars = [c.get("name") for c in (cr.get("cast") or [])[:8] if c.get("name")]
        return {
            "title":      r.get("name") or title,
            "title_jp":   r.get("original_name") if r.get("original_language") == "ja" else "",
            "type":       "TV",
            "episodes":   r.get("episode_count") or "?",
            "status":     r.get("status") or "",
            "genres":     _gids(r.get("genre_ids")),
            "characters": chars,
            "synopsis":   (r.get("overview") or "")[:600],
            "score":      r.get("vote_average"),
            "year":       (r.get("first_air_date") or "")[:4] or None,
            "source":     "TMDB",
        }

    if _search_tv_first:
        result = _fetch_tv() or _fetch_movie()
    else:
        result = _fetch_movie() or _fetch_tv()

    return result


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BOLUM 6: YAPAY ZEKA ISTEKLERI
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_AI_CLASSIFY_CACHE = {}
_key_cursor = 0  # Session boyunca hangi key'den devam edilecegi (sirali ilerleme)


def _ai_get_api_key():
    """api_keys.txt'den tum OpenRouter key'lerini doner. (key_list, endpoint)"""
    base = os.path.dirname(os.path.abspath(__file__))
    keys_path = os.path.join(base, "api_keys.txt")
    if os.path.exists(keys_path):
        try:
            with open(keys_path, "r", encoding="utf-8") as _f:
                _lines = [l.strip() for l in _f if l.strip() and not l.startswith("#")]
            if _lines:
                return _lines, "https://openrouter.ai/api/v1/chat/completions"
        except Exception:
            pass
    return [], None


def _ai_query_direct(prompt: str, max_tokens: int = 180, temperature: float = 0.0) -> str | None:
    """translator_config.json ve user_preferences.json ayarlarina gore AI'ya dogrudan istek gonderir."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    _tcfg = {}
    try:
        _cfg_path = os.path.join(base_dir, 'translator_config.json')
        if os.path.exists(_cfg_path):
            with open(_cfg_path, 'r', encoding='utf-8') as _f:
                _tcfg = json.load(_f)
    except Exception:
        pass

    _ag_url = _tcfg.get('antigravity_url', 'http://localhost:8045/v1/chat/completions')
    _ag_key = _tcfg.get('antigravity_api_key', '')
    _active_model_id = _tcfg.get('active_model_id', '')
    _avail_models = _tcfg.get('available_models', {})

    model_or = 'google/gemini-2.0-flash-lite:free'
    try:
        _pref_path = os.path.join(base_dir, 'user_preferences.json')
        if os.path.exists(_pref_path):
            with open(_pref_path, 'r', encoding='utf-8') as _f:
                _pref_data = json.load(_f)
            model_or = _pref_data.get('ai_model', model_or)
    except Exception:
        pass

    is_ag_preferred = (
        model_or.startswith('AG:')
        or _active_model_id.startswith('AG:')
        or _avail_models.get(model_or, {}).get('provider') == 'antigravity'
    )

    ag_model_name = 'gemini-2.5-flash'
    if model_or.startswith('AG:'):
        ag_model_name = model_or[3:]
    elif _avail_models.get(model_or, {}).get('provider') == 'antigravity':
        ag_model_name = model_or
    elif _active_model_id.startswith('AG:'):
        ag_model_name = _active_model_id[3:]
    else:
        ag_model_name = next(
            (k for k, v in _avail_models.items()
             if isinstance(v, dict) and v.get('provider') == 'antigravity'
             and 'flash' in k.lower() and 'pro' not in k.lower()),
            next((k for k, v in _avail_models.items()
                  if isinstance(v, dict) and v.get('provider') == 'antigravity'), 'gemini-2.5-flash')
        )

    def _try_antigravity() -> str | None:
        if not _ag_url or not _ag_key:
            return None
        try:
            print(f"[MediaID] Antigravity ile istek gonderiliyor: {ag_model_name} @ {_ag_url}")
            _headers = {"Authorization": f"Bearer {_ag_key}", "Content-Type": "application/json"}
            _payload = {
                "model": ag_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens, "temperature": temperature,
            }
            _resp = requests.post(_ag_url, headers=_headers, json=_payload, timeout=15)
            if _resp.status_code == 200:
                return _resp.json()["choices"][0]["message"]["content"].strip()
            print(f"[MediaID] Antigravity HTTP {_resp.status_code}: {_resp.text}")
        except Exception as e:
            print(f"[MediaID] Antigravity baglanti hatasi: {e}")
        return None

    def _try_keymanager() -> str | None:
        global _key_cursor
        keys_list, endpoint = _ai_get_api_key()
        if not keys_list or not endpoint:
            print("[MediaID] OpenRouter/Google key bulunamadi.")
            return None

        total = len(keys_list)
        for i in range(total):
            idx = (_key_cursor + i) % total
            api_key = keys_list[idx]
            try:
                print(f"[MediaID] OpenRouter/Google ile istek gonderiliyor (Key index: {idx}) @ {endpoint}")
                _headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                _payload = {
                    "model": "google/gemini-2.0-flash-001",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens, "temperature": temperature,
                }
                _resp = requests.post(endpoint, headers=_headers, json=_payload, timeout=12)
                if _resp.status_code in (402, 429):
                    _key_cursor = (idx + 1) % total
                    continue
                if _resp.status_code != 200:
                    continue
                _key_cursor = idx
                return _resp.json()["choices"][0]["message"]["content"].strip()
            except Exception:
                continue
        return None

    _text = None
    if is_ag_preferred:
        print("[MediaID] Yonlendirme: Antigravity Oncelikli.")
        _text = _try_antigravity()
        if not _text:
            print("[MediaID] Yonlendirme: Antigravity basarisiz, OpenRouter/Google deneniyor.")
            _text = _try_keymanager()
    else:
        print("[MediaID] Yonlendirme: OpenRouter/Google Oncelikli.")
        _text = _try_keymanager()
        if not _text:
            print("[MediaID] Yonlendirme: OpenRouter/Google basarisiz, Antigravity deneniyor.")
            _text = _try_antigravity()

    return _text


def _ai_classify_media(filename: str):
    """
    Dosya adi AI'ya gonderilir: title + alt_title + search_hint + media_type + season doner.
    3 katmanli arama icin gerekli.
    """
    fn = os.path.splitext(os.path.basename(filename))[0]
    if fn in _AI_CLASSIFY_CACHE:
        return _AI_CLASSIFY_CACHE[fn]

    prompt = (
        "Analyze this video/subtitle filename and identify the media.\n"
        f"Filename: {fn}\n\n"
        "Return ONLY a JSON object (no markdown, no extra text):\n"
        '{\n'
        '  "title": "Title as recognized / Romaji if anime (e.g. Oshi no Ko)",\n'
        '  "alt_title": "Official English title if meaningfully different, else null",\n'
        '  "search_hint": "Best search query for MAL/AniList/TMDB",\n'
        '  "media_type": "anime OR series OR movie",\n'
        '  "season": 3,\n'
        '  "season_title": "Official title for THIS season only (e.g. Sword Art Online: Alicization for S3) or null",\n'
        '  "part": null\n'
        '}\n\n'
        "Rules:\n"
        "- title: Recognized title (Romaji for anime is fine).\n"
        "- alt_title: English ONLY if meaningfully different. null otherwise.\n"
        "  Example: 'Kimetsu no Yaiba' -> alt_title: 'Demon Slayer'\n"
        "  Example: 'Oshi no Ko' -> alt_title: null\n"
        "- search_hint: Form most likely to match on MAL/AniList/TMDB.\n"
        "  Abbreviated: 'TenSura' -> search_hint: 'Tensei shitara Slime Datta Ken'\n"
        "- media_type: anime=Japanese animation (including anime movies/films), series=live-action TV, movie=live-action film\n"
        "- season: integer or null (S03 -> 3)\n"
        "- season_title: Official title for this specific season if it differs from base title.\n"
        "  Examples: SAO S3 -> 'Sword Art Online: Alicization' | AoT S4 -> 'Attack on Titan: The Final Season'\n"
        "  If title doesn't change between seasons, set null.\n"
        "- part: integer or null (Movie 2 -> 2)\n"
        "- If unsure, write UNKNOWN\n"
        "JSON:"
    )

    _text = _ai_query_direct(prompt, max_tokens=180, temperature=0)
    if not _text:
        return None

    # 4. Yanıtı Parse Et
    try:
        if "```" in _text:
            _text = _text.split("\n", 1)[-1].rsplit("```", 1)[0]
        _text = _text.strip()

        _r = json.loads(_text)
        _title = (_r.get("title") or "").strip().strip('"').strip("'")
        _alt   = (_r.get("alt_title") or "").strip().strip('"').strip("'") or None
        _hint  = (_r.get("search_hint") or "").strip().strip('"').strip("'") or None
        _mtype = (_r.get("media_type") or "").strip().lower()
        _season       = _r.get("season")
        _season_title = (_r.get("season_title") or "").strip().strip(chr(34)).strip(chr(39)) or None
        _part         = _r.get("part")

        if not _title or "UNKNOWN" in _title.upper():
            return None
        if _mtype not in ("anime", "series", "movie"):
            _mtype = "unknown"
        try: _season = int(_season) if _season is not None else None
        except (ValueError, TypeError): _season = None
        try: _part = int(_part) if _part is not None else None
        except (ValueError, TypeError): _part = None

        if _alt and _alt.lower() == _title.lower(): _alt = None
        if _hint and _hint.lower() == _title.lower(): _hint = None

        _out = {
            "title": _title, "alt_title": _alt, "search_hint": _hint,
            "media_type": _mtype, "season": _season,
            "season_title": _season_title, "part": _part
        }
        _AI_CLASSIFY_CACHE[fn] = _out
        return _out
    except Exception as e:
        print(f"[MediaID] Yanit ayristirma hatasi: {e}")
    return None


def _ai_identify_title(raw_filename: str, translator=None) -> str | None:
    """Yapay zekaya dosya adindan medya basligini tespit ettirir."""
    try:
        prompt = (
            f"What anime, movie or TV series is this subtitle/video filename from?\n"
            f"Filename: {raw_filename}\n\n"
            "Rules:\n"
            "- Return ONLY the exact title (nothing else)\n"
            "- If anime: return the official English title\n"
            "- If you cannot determine it, return: UNKNOWN\n"
            "Title:"
        )
        if translator is not None:
            result = translator.translate_single_line(prompt)
        else:
            result = _ai_query_direct(prompt, max_tokens=100)

        if result and "UNKNOWN" not in result.upper() and len(result.strip()) < 100:
            return result.strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _ai_fill_gaps(metadata: dict, translator=None) -> dict:
    """API'dan gelen metadata'da eksik alanlari yapay zeka ile doldur."""
    title = metadata.get("title", "")
    missing = []
    if not metadata.get("genres"):
        missing.append("genres (comma-separated list)")
    if not metadata.get("characters"):
        missing.append("main characters (comma-separated list of 5-8 names)")
    if not metadata.get("synopsis"):
        missing.append("a 2-sentence synopsis")

    if not missing:
        return metadata

    try:
        prompt = f'For the anime/series: "{title}"\nProvide ONLY the following:\n'
        for i, m in enumerate(missing, 1):
            prompt += f"{i}. {m}\n"
        prompt += "\nRespond in this exact format:\n"
        for i, m in enumerate(missing, 1):
            prompt += f"{i}. [answer]\n"

        if translator is not None:
            result = translator.translate_single_line(prompt)
        else:
            result = _ai_query_direct(prompt, max_tokens=300)

        if not result:
            return metadata

        rlines = [l.strip() for l in result.strip().split("\n") if l.strip()]
        for i, field_desc in enumerate(missing):
            if i < len(rlines):
                val = re.sub(r'^\d+\.\s*', '', rlines[i]).strip()
                if "genres" in field_desc:
                    metadata["genres"] = [g.strip() for g in val.split(",") if g.strip()]
                elif "characters" in field_desc:
                    metadata["characters"] = [c.strip() for c in val.split(",") if c.strip()]
                elif "synopsis" in field_desc:
                    metadata["synopsis"] = val
    except Exception as e:
        print(f"{Fore.YELLOW}[MediaID] AI fill hatasi: {e}{Style.RESET_ALL}")

    return metadata


def _try_source(name: str, fn, *args) -> tuple:
    """Tek kaynak denemesi. (metadata, source_name) doner."""
    print(f"{Fore.CYAN}   [MediaID] {name} sorgulanıyor...{Style.RESET_ALL}", end=' ', flush=True)
    try:
        result = fn(*args)
        if result:
            print(f"{Fore.GREEN}Bulundu!{Style.RESET_ALL}")
            return result, name
        else:
            print(f"{Fore.YELLOW}Bulunamadi.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Hata: {e}{Style.RESET_ALL}")
    time.sleep(REQUEST_DELAY)
    return None, None


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


def build_translation_context(metadata: dict, source_filepath: str = None,
                              media_type: str = None) -> str:
    """
    API metadata'sından yapay zeka çeviri promptuna enjekte edilecek
    bağlam metni üretir.

    source_filepath verilirse altyazı kalite analizi de eklenir.
    media_type: 'anime' | 'series' | 'movie' | None — sadece 'anime' için Fandom wiki sorgulanir.
    """
    if not metadata:
        return ""

    # Kaynak kalite analizi
    quality_info = None
    if source_filepath and os.path.isfile(source_filepath):
        quality_info = score_subtitle_quality(source_filepath)

    # Kalite bilgisine göre dinamik başlık
    if quality_info:
        q_label = quality_info["label"]
        q_score = quality_info["score"]
        q_reasons = ", ".join(quality_info["reasons"]) or "none"
        if q_label == "LOW":
            lines = [
                "=== MEDIA CONTEXT (DEEP LOCALIZATION REQUIRED) ===",
                f"SOURCE QUALITY: LOW ({q_score}/100) — Detected: {q_reasons}",
                "WARNING: This English subtitle is likely a rough/speed fansub translated from Japanese.",
                "DO NOT translate the English literally. Instead:",
                "  1. Use the media context below to understand the SCENE and CHARACTER.",
                "  2. Write what a professional Turkish fansub team would write for this scene.",
                "  3. Produce natural, idiomatic Turkish — as if you are the original localizer.",
            ]
        elif q_label == "MEDIUM":
            lines = [
                "=== MEDIA CONTEXT (LOCALIZATION GUIDE) ===",
                f"SOURCE QUALITY: MEDIUM ({q_score}/100) — Detected: {q_reasons}",
                "The English subtitle may have some unnatural phrasing. Where the English seems awkward,",
                "use the context below to write natural Turkish rather than a literal translation.",
            ]
        else:
            lines = [
                "=== MEDIA CONTEXT (TRANSLATION GUIDE) ===",
                f"SOURCE QUALITY: HIGH ({q_score}/100)",
                "The English subtitle appears to be professional quality. Translate accurately while",
                "maintaining natural Turkish phrasing.",
            ]
    else:
        lines = [
            "=== MEDIA CONTEXT (LOCALIZATION GUIDE) ===",
            "Use the data below to write NATURAL IDIOMATIC Turkish. Do not translate word-for-word.",
        ]

    # Başlık
    title_line = f"TITLE: {metadata.get('title', '?')}"
    if metadata.get("title_jp"):
        title_line += f"  |  JP: {metadata['title_jp']}"
    lines.append(title_line)



    # Sezon / Bölüm
    if metadata.get('season'):
        ep_line = f"SEASON: {metadata['season']}"
        if metadata.get('episode'):
            ep_line += f"  |  EPISODE: {metadata['episode']}"
        lines.append(ep_line)

    # Tür + bölüm + yıl
    type_parts = []
    if metadata.get("type"):
        type_parts.append(f"TYPE: {metadata['type']}")
    if metadata.get("episodes"):
        type_parts.append(f"EPISODES: {metadata['episodes']}")
    if metadata.get("year"):
        type_parts.append(f"YEAR: {metadata['year']}")
    if type_parts:
        lines.append("  |  ".join(type_parts))

    # Türler
    genres = metadata.get("genres") or []
    if genres:
        lines.append(f"GENRES: {', '.join(genres[:8])}")

    # Karakterler — API'den gelen + AniDB lazy-load + Wikidata doğrulama
    chars = list(metadata.get("characters") or [])
    if _OFFLINE_DB_AVAILABLE:
        try:
            _raw_title_chars = metadata.get("title", "")
            _offdb_chars = _offdb.get_characters_for_title(_raw_title_chars,
                           media_type=(_detected_media_type or 'anime'))
            for c in _offdb_chars:
                if c not in chars:
                    chars.append(c)
        except Exception:
            pass
    if chars:
        char_list = ", ".join(chars[:15])
        lines.append(f"CHARACTERS: {char_list}")


    # Sinopsis
    synopsis = (metadata.get("synopsis") or "").strip()
    if synopsis:
        short = synopsis[:300] + ("..." if len(synopsis) > 300 else "")
        lines.append(f"SYNOPSIS: {short}")

    # Kaynak
    lines.append(f"SOURCE: {metadata.get('source', 'Unknown')}")

    # Önemli çeviri notu
    notes = [
        "- Keep ALL character names EXACTLY as-is.",
        "- Use terminology consistent with the genre above.",
    ]
    if chars:
        notes.append(f"- Known characters: {', '.join(chars[:6])} — never alter these names.")
    if any(g.lower() in ["drama", "romance", "slice of life"] for g in genres):
        notes.append("- Use natural, emotional Turkish dialogue matching the drama/slice-of-life tone.")
    if any(g.lower() in ["action", "fantasy", "adventure", "supernatural"] for g in genres):
        notes.append("- Preserve impact and energy in action/fantasy sequences.")
    if any(g.lower() in ["comedy", "parody"] for g in genres):
        notes.append("- Preserve comedic timing and wordplay where possible.")
    # Sezon-özel not: bu çeviri daha sonraki bir sezon mu?
    _season = metadata.get('season')
    _episode = metadata.get('episode')
    if _season and _season >= 2:
        _ep_note = f", Episode {_episode}" if _episode else ""
        notes.append(
            f"- This is SEASON {_season}{_ep_note} of the series. "
            f"Characters, relationships and story arcs have evolved significantly from Season 1. "
            f"New characters may have been introduced. Use era-appropriate terminology."
        )
    elif _season == 1 and _episode:
        notes.append(
            f"- This is Season 1, Episode {_episode}. "
            f"Characters are being introduced for the first time."
        )
    _part = metadata.get('part')
    if _part and _part >= 2:
        notes.append(
            f"- This is film/installment #{_part} in the series. "
            f"Events and character development build upon previous entries. "
            f"Translate with continuity — avoid re-introducing known characters as strangers."
        )
    elif _part == 1:
        notes.append("- This is the first film/installment in the series.")
    if notes:
        lines.append("TRANSLATION NOTES:")
        lines.extend(notes)


    # Anime icerigi icin: Gemini anime modu tetiklenmesin
    _media_type = str(metadata.get('type', '')).lower()
    _has_jp_title = bool(metadata.get('title_jp'))
    if 'anime' in _media_type or _has_jp_title:
        lines.append(
            'LOCALIZATION WARNING: Even though this is Japanese anime, your output MUST be '
            '100% natural Turkish. Do NOT use any Japanese words, pronouns, or expressions '
            "in your Turkish translation. 'boku/ore/watashi' are Japanese for I/me - "
            "use Turkish 'Ben' or omit entirely. Translate MEANING, not style markers."
        )
    # ── TERMİNOLOJİ SÖZLÜĞÜ: Anime + Film + Dizi için hepsi ──────────────────
    # Kaynak: Fandom wiki + TVmaze + Franchise API (PotterDB/SWAPI) + Wikidata
    # media_type yoksa metadata kaynağından tahmin et
    _detected_media_type = media_type
    if _detected_media_type is None:
        _src = str(metadata.get("source", "")).lower()
        _mtype_raw = str(metadata.get("type", "")).lower()
        if any(s in _src for s in ("jikan", "mal", "anilist", "kitsu")):
            _detected_media_type = "anime"
        elif any(t in _mtype_raw for t in ("tv", "ova", "ona", "special", "manga")):
            _detected_media_type = "anime"
        elif "movie" in _mtype_raw:
            _detected_media_type = "movie"
        elif any(s in _src for s in ("tvmaze", "tmdb-tv", "tmdb_tv", "imdb")):
            _detected_media_type = "series"
        else:
            _detected_media_type = "auto"

    # Başlığı temizle: dosya adı kalıplarını soy
    import re as _re2
    _raw_title = metadata.get("title", "").strip()
    _cln = _re2.sub(r'^\[[^\]]+\]\s*', '', _raw_title)
    _cln = _re2.sub(r'\s*\[[^\]]+\]\s*$', '', _cln)
    _cln = _re2.sub(r'\s+[-.]?\s*S\d{1,2}E\d{1,3}.*$', '', _cln, flags=_re2.I)
    _cln = _re2.sub(r'\s+[-.]?\s*S(?:eason)?\s*\d+.*$', '', _cln, flags=_re2.I)
    _cln = _re2.sub(r'[._]+', ' ', _cln).strip()
    _series_title = _cln or _raw_title

    if _series_title:
        try:
            from fandom_glossary import get_merged_injection as _fandom_inject

            # Öncelik sırası:
            # 1. AI classify sonucu (en güvenilir — dosya adından doğrudan)
            # 2. resolved_media_type (IMDB/TMDB normalize)
            # 3. metadata.type (ham alan)
            _ai_mtype  = metadata.get('ai_media_type', '')        # 'anime','series','movie'
            _ai_title  = metadata.get('ai_title', '')             # AI'nın temiz başlık tespiti
            _norm_type = metadata.get('resolved_media_type', '')  # 'series','movie','anime'
            _raw_type  = metadata.get('type', '')                 # 'TVSERIES','MOVIE','ANIME'

            # known_type: AI sonucu varsa onu kullan, yoksa normalize edilmiş türe bak
            _known_type = (
                _ai_mtype.upper()  if _ai_mtype  else
                _norm_type.upper() if _norm_type else
                _raw_type.upper()  if _raw_type  else None
            )
            # 'anime','series','movie' → 'ANIME','SERIES','MOVIE' (Fandom kalite kapısı uyumlu)

            # Arama başlığı: AI'nın verdiği temiz başlık varsa onu kullan
            # (dosya adından parse edilmiş kirli başlık yerine)
            _lookup_title = _ai_title if _ai_title else _series_title

            _ai_season_title = metadata.get("ai_season_title")  # sezona ozel resmi ad
            # Oncelik: season_title > ai_title > series_title
            _gloss_lookup = _ai_season_title or _lookup_title
            _season_num  = metadata.get("season")  # int veya None
            _glossary_block = _fandom_inject(
                _gloss_lookup,
                media_type=_detected_media_type,
                known_type=_known_type,
                season_num=_season_num,
                season_title=_ai_season_title,
            )
            if _glossary_block:
                lines.append("")
                lines.append(_glossary_block)
        except Exception:
            pass  # Bulunamazsa veya hata → sessizce atla

    # ────────────────────────────────────────────────────────────────────────────

    lines.append("=" * 51)
    _full = "\n".join(lines)

    # ── Toplam context boyut sınırı ───────────────────────────────────────────
    # Hedef: sistem promptuna eklenen context < 3200 char (≈800 token)
    # Büyük anime wikilerinden gelen glossary bloğu bunu kolayca aşabilir.
    _MAX_CTX_CHARS = 3200
    if len(_full) > _MAX_CTX_CHARS:
        # Adım 1: Synopsis'i kıs (varsa 100 char'a)
        lines2 = []
        for ln in lines:
            if ln.startswith("SYNOPSIS:") and len(ln) > 120:
                lines2.append("SYNOPSIS: " + ln[10:110] + "...")
            else:
                lines2.append(ln)
        # Adım 2: TRANSLATION NOTES'u 3 ile sınırla
        in_notes = False
        notes_count = 0
        lines3 = []
        for ln in lines2:
            if ln == "TRANSLATION NOTES:":
                in_notes = True
                lines3.append(ln)
                continue
            if in_notes and ln.startswith("- "):
                notes_count += 1
                if notes_count <= 3:
                    lines3.append(ln)
                # 3'ten fazla notu atla
            else:
                in_notes = False
                lines3.append(ln)
        _full = "\n".join(lines3)
        # Adım 3: Yine de büyükse sert kes
        if len(_full) > _MAX_CTX_CHARS:
            _full = _full[:_MAX_CTX_CHARS].rsplit("\n", 1)[0]
            _full += "\n" + "=" * 51
    # ─────────────────────────────────────────────────────────────────────────
    return _full


# ──────────────────────────────────────────────────────────────
# BÖLÜM 10: TEST (doğrudan çalıştırma)
# ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_files = [
        r"[CrappySubs] Oshi no Ko - S03E01v2 - (WEB 1080p H.265 AAC) [7A1BD58F].ass",
        r"Attack.on.Titan.S04E28.1080p.mkv",
        r"Suzume.no.Tojimari.2022.BluRay.1080p.mkv",
        r"[SubsPlease] Frieren - Beyond Journey's End - 01 (1080p).mkv",
        r"Breaking.Bad.S05E16.mkv",
        r"The.Dark.Knight.2008.1080p.mkv",
    ]

    print("=" * 65)
    print("MEDIA IDENTIFIER TEST")
    print("=" * 65)

    for f in test_files:
        title = _clean_title(os.path.splitext(os.path.basename(f))[0])
        print(f"\nDosya : {f[:60]}")
        from media_identifier import identify_from_file, build_translation_context
        _media_meta = identify_from_file(f)
        if _media_meta:
            ctx = build_translation_context(_media_meta, source_filepath=f)
            print(ctx)
        else:
            print("[SONUC] Tespit edilemedi.")
        print("-" * 65)
