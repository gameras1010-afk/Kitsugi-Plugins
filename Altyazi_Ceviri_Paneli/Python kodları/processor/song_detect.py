"""
processor/song_detect.py
========================
İçerik tabanlı şarkı ve karaoke satırı tespiti.
Song cache (JSON) yönetimi.
"""
import re
import os
import json
import time

try:
    from processor.imports import (
        _cd_is_song, _cd_is_kara_syllable,
        _CONTENT_DETECTOR_OK,
        _rom_classify_line, _ROMAJI_DETECTOR_OK,
    )
except ImportError:
    _CONTENT_DETECTOR_OK = False
    _ROMAJI_DETECTOR_OK  = False
    def _cd_is_song(*a, **kw): return (False, 0, 'no_cd')
    def _cd_is_kara_syllable(t, d=0): return (False, 'no_cd')
    def _rom_classify_line(t, s=''): return ('uncertain', 0.5, 'no_detector')

# ==============================================================
# PHASE 2 — ŞARKI SÖZLERİ ÇEVİRİSİ
# ==============================================================
_SONG_TAG_RE  = re.compile(r'\{[^}]*\}')
_SONG_TR_CHARS = set('ğşçöüıİĞŞÇÖÜ')
# Prefix strip: '1. ', '2) ' ve Gemini [L1]/[L2] marker'lari
# Prefix strip: '1. ', '2) ' ve Gemini [L1]/[L2]/[L3] marker'lari
# MULTILINE ile hem satır başı hem satır içi [Lx] marker'ları temizlenir
_SONG_PREFIX_RE = re.compile(
    r'(?:^\d+[.)]\s+|\[L\d+\]\s*)',
    re.MULTILINE
)
# Fansub editor notu effect alani: '[term fix]', '[fix]' vb. (CrappySubs)
_EDIT_NOTE_RE_FX = re.compile(r'^\[[\w\s]+\]$')

# ASS vector draw komutu tespiti: "m 0 0 m 100 100" gibi
_DRAW_CMD_RE  = re.compile(r'\b(?:m|l|b|s|p|c|n)\s+-?\d+\s+-?\d+', re.IGNORECASE)

# ── İçerik Tabanlı Şarkı / Karaoke Tespiti ────────────────────────────────────
_MUSIC_NOTE_RE  = re.compile(r'[♪♫~～]')
_KARAOKE_TAG_RE = re.compile(r'\{[^}]*\\k\d+[^}]*\}', re.IGNORECASE)  # {\k100}

def _ts_ms(ts_str):
    """ASS zaman string'ini ms'ye çevirir: '0:23:54.18' → 1434180"""
    try:
        h, m, rest = str(ts_str).replace(',', '.').split(':')
        s, cs = rest.split('.')
        return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(cs)*10
    except Exception:
        return 0

def is_likely_song_by_content(ev, all_events=None, ep_duration_ms=0):
    """
    Stil adından bağımsız olarak bir event'in şarkı/karaoke olup olmadığını
    içerik analizi ile tespit eder.

    İpuçları (her biri puan ekler, toplam >= 2 → şarkı):
      +3  ♪ / ♫ müzik notu içeriyor
      +3  {\\kXX} karaoke zamanlama tag'i var
      +2  Metin < 4 kelime VE süre < 400ms (hece karaoke)
      +1  Bölüm başı (0-90s) veya sonu (son 180s) AND kısa metin
      +1  Aynı stil adındaki komşu eventler de kısa (< 5 kelime) → OP/ED bloğu

    Returns: (bool, int score, str reason)
    """
    parts = ev.get('parts', [])
    if len(parts) < 10:
        return False, 0, 'no_parts'

    raw_text   = parts[9]
    clean      = _SONG_TAG_RE.sub('', raw_text).strip()
    start_ms   = _ts_ms(parts[1])
    end_ms     = _ts_ms(parts[2])
    duration   = max(0, end_ms - start_ms)
    word_count = len(clean.split()) if clean else 0
    score      = 0
    reasons    = []

    # İpucu 1: Müzik notu
    if _MUSIC_NOTE_RE.search(clean) or _MUSIC_NOTE_RE.search(raw_text):
        score += 3
        reasons.append('music_note')

    # İpucu 2: Karaoke zamanlama tag'i
    if _KARAOKE_TAG_RE.search(raw_text):
        score += 3
        reasons.append('karaoke_tag')

    # İpucu 3: Çok kısa süre + az kelime = hece karaoke
    if duration < 400 and word_count <= 3 and word_count >= 1:
        score += 2
        reasons.append(f'short_ev_dur={duration}ms_words={word_count}')

    # İpucu 4: Bölüm başı/sonu pozisyonu + kısa metin
    if (start_ms < 90_000 or (ep_duration_ms > 0 and start_ms > ep_duration_ms - 180_000)):
        if word_count <= 8:
            score += 1
            reasons.append('op_ed_position')

    # İpucu 5: Komşularda da kısa eventler mi var? (OP/ED bloğu)
    if all_events and word_count <= 6:
        style = parts[3]
        same_style = [e for e in all_events
                      if e.get('parts', [''] * 4)[3] == style
                      and e is not ev]
        if same_style:
            avg_words = sum(
                len(_SONG_TAG_RE.sub('', e['parts'][9]).split())
                for e in same_style[:20] if len(e.get('parts', [])) > 9
            ) / min(len(same_style), 20)
            if avg_words <= 6:
                score += 1
                reasons.append(f'neighbor_short_avg={avg_words:.1f}')

    is_song = score >= 2
    return is_song, score, '+'.join(reasons) if reasons else 'no_signal'

def is_likely_karaoke_syllable_by_content(ev):
    """
    Tek bir event'in karaoke hecesi olup olmadığını kontrol eder.
    Hece karaoke: cok kisa sure + 1-3 karakter metin veya \k tag'i.
    """
    parts = ev.get('parts', [])
    if len(parts) < 10:
        return False
    raw   = parts[9]
    clean = _SONG_TAG_RE.sub('', raw).strip()
    dur   = max(0, _ts_ms(parts[2]) - _ts_ms(parts[1]))
    if _KARAOKE_TAG_RE.search(raw):
        return True
    if len(clean) <= 3 and dur < 600:
        return True
    return False


def _is_english_song_event(ev_item):
    """
    Event'in Ingilizce sarki sozu event'i olup olmadigini tespit eder.
    Romaji, Japonca, karaoke-hece, Turkce -> False doner.
    """
    style = ev_item.get('parts', [''] * 4)[3] if ev_item.get('parts') else ev_item.get('style', '')
    if not style:
        return False

    # ── Adım 0: ass_style_conventions.classify_style_name() ile güçlü ön filtreleme ──
    # SKIP_STYLE_WORDS, FORCE_TRANSLATE_STYLE_WORDS setleri (GJM, Chyuu, SubsPlease, CR)
    try:
        from ass_style_conventions import classify_style_name as _classify_sc
        _sc_result = _classify_sc(style)
        if _sc_result == 'skip':
            return False   # JP/ROM/KARA/CREDIT → kesinlikle atla
        _sc_force_translate = (_sc_result == 'translate')
    except ImportError:
        _sc_result = 'unknown'
        _sc_force_translate = False

    # ── Generic stil adı tespiti ──────────────────────────────────────────────
    # "Default", "Main", "Style0001", "Sign", "Alt" gibi anlamsız isimler
    # is_song_style_name'i geçemez. İçerik analizine geç.
    _GENERIC_STYLE_RE = re.compile(
        r'^(default|main|alt|sign|top|an\d|bottom|style\s*\d*|'
        r'subtitle|dialogue|dialog|note|screen|text|'
        r'event|flash|pos\d*|sub\d*|line\d*)$',
        re.IGNORECASE
    )
    _style_clean = re.sub(r'[-_\s]', '', style).lower()
    is_generic = bool(_GENERIC_STYLE_RE.match(_style_clean)) or _style_clean.startswith('style')

    if is_generic and not _sc_force_translate:
        # Stil adı generic → içerik analizine geç
        text = ev_item.get('parts', [''] * 10)[9] if ev_item.get('parts') and len(ev_item['parts']) > 9 else ''
        clean = _SONG_TAG_RE.sub('', text).strip()
        if not clean or len(clean) <= 2:
            return False
        if any(c in _SONG_TR_CHARS for c in clean):
            return False
        if not re.search(r'[a-zA-Z]{2,}', clean):
            return False
        # Karaoke syllable mi?
        if is_likely_karaoke_syllable_by_content(ev_item):
            return False
        # İçerik tabanlı şarkı tespiti
        _song_hit, _song_score, _song_why = is_likely_song_by_content(ev_item)
        return _song_hit
    # ──────────────────────────────────────────────────────────────────────────

    if not is_song_style_name(style):
        return False
    # 2. Skip gerektiren suffix var mı? (JP/ROM/KARA → atla)
    #    EN/ENG → doğrudan çevir
    #    None (suffix yok) → içerik analizine geç (örnk: "Opening", "OP1", "ED")
    behavior = get_style_suffix_behavior(style)
    if behavior == 'skip':
        return False
    # behavior == 'translate' → kesin çevir
    # behavior == None → suffix yok, içerik kontrolüne geç
    # 3. Karaoke hece eventi mi? (tek/çift karakter)
    text = ev_item.get('parts', [''] * 10)[9] if ev_item.get('parts') and len(ev_item['parts']) > 9 else ''
    clean = _SONG_TAG_RE.sub('', text).strip()
    if len(clean) <= 2:
        return False  # Karaoke hece: 'N', 'o', 'ne' gibi
    # 4. Draw command event mi? (\p1 ile çizilen harfler veya koordinat dataları)
    try:
        from ass_line_filter import is_drawing_line as _local_is_draw
        _is_draw_val = _local_is_draw(text) or _local_is_draw(clean)
    except Exception:
        _is_draw_val = bool(_DRAW_CMD_RE.search(clean)) and len(re.sub(r'[^a-zA-Z]', '', clean)) < 5
    if _is_draw_val:
        return False  # Vector art, metin değil
    # 5. Türkçe karakter içeriyorsa zaten çevrilmiş
    if any(c in _SONG_TR_CHARS for c in clean):
        return False
    # 6. En az 2 Latin harf içermeli
    if not re.search(r'[a-zA-Z]{2,}', clean):
        return False
    # 7. behavior=None → karaoke syllable değilse kabul et
    if behavior is None and not _sc_force_translate:
        if is_likely_karaoke_syllable_by_content(ev_item):
            return False
    return True



def _get_song_type(style_name):
    """Stil adından şarkı türünü belirle: Opening / Ending / Insert Song"""
    s = style_name.upper()
    parts = re.split(r'[-_\s]', s)
    if any(p in ('OP', 'OPENING', 'OPN') for p in parts): return 'Opening Song'
    if any(p in ('ED', 'ENDING', 'END') for p in parts):  return 'Ending Song'
    if any(p in ('INSERT', 'INS', 'IMAGE') for p in parts): return 'Insert Song'
    return 'Song'


# ─── Şarkı Sözü Çeviri Cache ──────────────────────────────────────────────────
def _get_song_cache_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'song_lyrics_cache.json')

def _load_song_cache():
    try:
        p = _get_song_cache_path()
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_song_cache(cache):
    try:
        with open(_get_song_cache_path(), 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _make_song_cache_key(anime_title, season, en_lines, song_type=''):
    """
    Cache anahtarı: "AnimeAd|S3|OP|<hash>"
    - song_type dahil edildi: OP/ED/Insert aynı bölümde çakışmaz
    - hash: tıpatıp aynı metin → aynı hash, tek kelime fark → farklı hash
    """
    import hashlib
    _tag = re.compile(r'\{[^}]*\}')
    normalized = []
    for line in en_lines:
        c = _tag.sub('', line)
        c = re.sub(r'\\[nN]|__NL__|__SL__', ' ', c)
        c = ' '.join(c.split()).strip().lower()
        if c:
            normalized.append(c)
    h = hashlib.md5('|'.join(normalized).encode('utf-8')).hexdigest()[:12]
    s     = str(season) if season else '0'
    try:
        from termbase_manager import _split_title_season
        clean_title, _ = _split_title_season(anime_title)
    except Exception:
        clean_title = anime_title
    clean_title = re.sub(r'\s*-\s*\d+.*$', '', clean_title)
    title = re.sub(r'[^\w\s]', '', str(clean_title)).strip()
    stype = re.sub(r'[^\w]', '', str(song_type)).upper()[:12] if song_type else 'SONG'
    return f"{title}|S{s}|{stype}|{h}"
# ──────────────────────────────────────────────────────────────────────────────

