"""
media_id/episode.py
===================
Dosya parse, ASS/SRT okuyucular, medya türü tespiti.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional
from media_id.constants import *

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

