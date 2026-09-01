"""
detector/classifier.py
======================
Metin/stil/event sınıflandırma.
"""
import re, os, json, time
from typing import Optional, Tuple, List


def score_word(word: str) -> Tuple[float, str]:
    """
    Tek kelimeyi analiz eder — frekans tabanli yukseltilmis versiyon.
    Returns: (romaji_score 0.0-1.0, reason)
      1.0 = kesin romaji / Japonca
      0.0 = kesin Ingilizce
      0.5 = belirsiz
    """
    w = word.strip().lower().rstrip("'\".,!?;:")
    if not w:
        return 0.5, 'empty'

    # CJK karakteri varsa hic latin degil
    if _CJK_RE.search(w):
        return 1.0, 'cjk_char'

    # Turkce karakter varsa kesinlikle Ingilizce veya Romaji degil
    if any(c in _TR_CHARS for c in w):
        return 0.0, 'turkish_char'

    # Kesin Ingilizce (apostrophe = kesin Ingilizce kontraksiyonu)
    if _APOSTROPHE_RE.search(word):
        return 0.0, 'apostrophe'

    # Kesin Japonca romaji kelime (kisa ve cok ozgu)
    if w in _HARD_ROMAJI_WORDS:
        return 0.97, 'hard_romaji_word'

    # Kesin Ingilizce embedded listede (apostrop/cakisma olmadan)
    if w in _HARD_ENG_LOWER and w not in _ROMAJI_ALL_LOWER:
        return 0.0, 'hard_english'

    # Genisletilmis veritabanlarini yukle (lazy)
    _load_ext_databases()

    # ── ADIM 1: Anime karakter adi mi? → ne EN ne romaji say ──────────────────
    if _ANIME_NAMES and w in _ANIME_NAMES:
        return 0.50, 'anime_proper_noun'  # Belirsiz bırak (isim = dil degil)

    # ── ADIM 2: TR Frekans kontrolu — zaten Turkce mi? ────────────────────────
    tr_score = _tr_freq_score(w)
    if tr_score > 0.3:  # Turkce frekans DB'de belirgin
        return 0.0, f'turkish_freq({tr_score:.2f})'

    # ── ADIM 3: EN Frekans skoru ───────────────────────────────────────────────
    en_score = _en_freq_score(w)
    # Rom DB kontrolu (585k kelime!)
    in_rom_db  = bool((_EXT_ROMAJI and w in _EXT_ROMAJI) or
                      (_EXT_ANIME  and w in _EXT_ANIME))
    in_eng_db  = bool(_EXT_ENGLISH and w in _EXT_ENGLISH)
    in_overlap = bool(_EXT_OVERLAP and w in _EXT_OVERLAP)
    in_eng_emb = w in _ENGLISH_ALL_LOWER
    in_rom_emb = w in _ROMAJI_ALL_LOWER

    # Yuksek EN frekans + romaji listesinde degil → kesin Ingilizce
    if en_score > 0.45 and not in_rom_db and not in_rom_emb:
        return 0.02, f'english_score={en_score:.2f}'
    if en_score > 0.3 and not in_rom_db and not in_overlap:
        return 0.05, f'english_score={en_score:.2f}'

    # ── ADIM 4: Mevcut DB mantigi ──────────────────────────────────────────────
    in_eng = in_eng_emb or in_eng_db
    in_rom = in_rom_emb or in_rom_db

    if in_eng and not in_rom and not in_overlap:
        return 0.03, f'ext_english({"embed" if in_eng_emb else "db"})'
    if in_rom and not in_eng and not in_overlap:
        return 0.95, f'ext_romaji({"embed" if in_rom_emb else "db"})'
    if in_rom and in_overlap:
        return 0.45, 'overlap_word'
    if in_eng and in_rom:
        # Frekans farkiyla karar ver
        if en_score > 0.2:
            return 0.20, f'both_lists_en_wins({en_score:.2f})'
        return 0.40, 'both_ext_lists'
    if in_eng:
        return 0.05, 'ext_english_only'

    # ── ADIM 5: Fonetik analiz ─────────────────────────────────────────────────
    if _JP_PHONOTACTIC.match(w):
        if _ENG_CONSONANT_CLUSTER.search(w):
            return 0.35, 'phonotactic_with_cluster'
        return 0.80, 'phonotactic_jp'

    # Uzun + unsuz kumesi = Ingilizce
    if len(w) >= 5 and _ENG_CONSONANT_CLUSTER.search(w):
        return 0.08, 'eng_consonant_cluster'

    # Kisa kelime — belirsiz
    if len(w) <= 3:
        return 0.55, 'short_latin'

    # Buyuk harfle basliyorsa ve uzunsa = muhtemelen Ingilizce proper noun
    if word[0].isupper() and len(w) > 4:
        return 0.18, 'capitalized_long'

    # Hard romaji son kontrol
    _HARD_ROM = frozenset({
        'nani','suki','dayo','kore','sore','are','dore','koko','soko','asoko',
        'dare','doko','itsu','naze','doushite','nande','mou','mada',
        'sugoi','kawaii','urusai','baka','yabai','senpai','kouhai','nakama',
        'yoroshiku','arigatou','gomen','sumimasen','itadakimasu','tadaima',
        'okaeri','ohayou','oyasumi','konnichiwa','konbanwa','sayonara',
        'muzukashii','tanoshii','ureshii','kanashii','tsurai','samui','atsui',
        'neko','inu','sakura','hana','tsuki','hoshi','yoru','asa','hiru',
        'ima','mukashi','mirai','chotto','matte','hayaku','yukkuri',
        'daisuki','kirai','honto','uso','daijoubu','yokatta',
    })
    if w in _HARD_ROM:
        return 0.95, 'hard_romaji_word'

    return 0.5, 'uncertain'


def score_text_romaji(text: str) -> Tuple[float, str]:
    """
    Metnin genel romaji skoru — frekans tabanli.
    Returns: (score 0.0-1.0, detail_str)

    0.0 = kesin Ingilizce, 1.0 = kesin Romaji
    """
    # Full-width normalizasyonu (jaconv)
    text = _normalize_text(text)

    words = text.strip().split()
    if not words:
        return 0.5, 'empty'

    # Apostrophe varsa kesin Ingilizce
    if _APOSTROPHE_RE.search(text):
        return 0.02, 'apostrophe_in_text'

    # DB'leri yukle (lazy)
    _load_ext_databases()

    # Frekans tabanli EN yogunlugu hesapla — hard_eng + frekans DB
    _en_hits = 0
    _word_list = [w.lower().rstrip("'\".,!?;:") for w in words if w.strip()]
    for _w in _word_list:
        # Hard EN listesi
        if _w in _HARD_ENG_LOWER and _w not in _ROMAJI_ALL_LOWER:
            _en_hits += 1
            continue
        # Frekans DB: yuksek EN frekansi + romaji listesinde degil
        _enf = _en_freq_score(_w)
        if _enf > 0.35:
            _in_rom = ((_EXT_ROMAJI and _w in _EXT_ROMAJI) or
                       (_EXT_ANIME  and _w in _EXT_ANIME) or
                       _w in _ROMAJI_ALL_LOWER)
            if not _in_rom:
                _en_hits += 1

    if _en_hits >= 2:
        ratio = _en_hits / len(_word_list) if _word_list else 0
        return max(0.0, 0.05 - ratio * 0.02), f'en_freq_density={ratio:.2f}({_en_hits}hits)'

    scores = [score_word(w)[0] for w in words]
    avg = sum(scores) / len(scores)
    detail = f'avg={avg:.2f}|words={len(words)}'
    return avg, detail

# ─────────────────────────────────────────────────────────────────────────────
# 7. STIL ADI SINIFLANDIRICI
# ─────────────────────────────────────────────────────────────────────────────

def classify_style(style_name: str) -> Tuple[str, float, str]:
    """
    Stil adini siniflandirir.

    Returns:
        (category, confidence, reason)
        category: 'song_en' | 'song_jp' | 'song_unknown' |
                  'karaoke_en' | 'karaoke_jp' | 'karaoke_unknown' |
                  'generic' | 'dialog' | 'sign'
    """
    if not style_name:
        return ('generic', 0.3, 'no_style')

    s = style_name.lower()
    tokens = set(re.split(r'[-_\s]', s))
    tokens.discard('')

    # Ingilizce dil ipucu
    has_en = bool(_LANG_EN_RE.search(s))
    has_jp = bool(_LANG_JP_RE.search(s))
    has_tr = bool(_LANG_TR_RE.search(s))

    # Karaoke ipucu
    has_kara = bool(_KARA_STYLE_RE.search(s))

    # OP/ED ipucu
    has_oped = bool(_OPED_STYLE_RE.search(s))

    # Generic kontrol
    is_generic = bool(
        tokens <= _GENERIC_STYLE_TOKENS or
        all(t in _GENERIC_STYLE_TOKENS or t.isdigit() for t in tokens)
    )

    # Karar agaci
    if has_kara:
        if has_en:
            return ('karaoke_en', 0.95, f'kara+en in [{style_name}]')
        if has_jp:
            return ('karaoke_jp', 0.95, f'kara+jp in [{style_name}]')
        if has_oped:
            return ('karaoke_unknown', 0.75, f'kara+oped in [{style_name}]')
        return ('karaoke_unknown', 0.6, f'kara in [{style_name}]')

    if has_oped:
        if has_en:
            return ('song_en', 0.95, f'oped+en in [{style_name}]')
        if has_jp:
            return ('song_jp', 0.90, f'oped+jp in [{style_name}]')
        if has_tr:
            return ('song_unknown', 0.7, f'oped+tr in [{style_name}]')
        return ('song_unknown', 0.65, f'oped in [{style_name}]')

    if is_generic:
        return ('generic', 0.85, f'generic_tokens in [{style_name}]')

    # Song token var mi?
    song_tokens = tokens & _SONG_STYLE_TOKENS
    if song_tokens:
        if has_en:
            return ('song_en', 0.8, f'song_token+en in [{style_name}]')
        if has_jp:
            return ('song_jp', 0.8, f'song_token+jp in [{style_name}]')
        return ('song_unknown', 0.6, f'song_token in [{style_name}]')

    return ('dialog', 0.5, f'no_match for [{style_name}]')

# ─────────────────────────────────────────────────────────────────────────────
# 8. METIN ICERIK SINIFLANDIRICI
# ─────────────────────────────────────────────────────────────────────────────

def classify_text(
    raw_text: str,
    duration_ms: int = 0,
) -> Tuple[str, float, str]:
    """
    Metnin dilini ve tipini belirler.

    Returns:
        (lang, confidence, reason)
        lang: 'english' | 'romaji' | 'japanese' | 'turkish' | 'mixed' | 'effect_only' | 'unknown'
    """
    # Sadece ASS tag'i mi?
    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    if not clean:
        return ('effect_only', 1.0, 'no_text_after_tags')

    # Draw komutu (vektor cizim)
    if _DRAW_RE.search(raw_text):
        return ('effect_only', 0.9, 'draw_command')

    # Turkce mi? — kisa yol ve frekans DB kontrolu
    tr_count = sum(1 for c in clean if c in _TR_CHARS)
    if tr_count >= 2:
        return ('turkish', 0.95, f'tr_chars={tr_count}')
    # TR frekans DB ile Turkce tespiti (Turkce ozel karakter olmadan da calısir)
    if tr_count == 0 and len(clean) >= 6:  # TR ozel karakter yoksa
        _load_ext_databases()
        if _TURKISH_FREQ:
            _TR_SPECIFIC = set('ğşçöüıİĞŞÇÖÜ')
            _clean_words = re.findall(r"[a-zA-ZçğışöüÇĞİŞÖÜ']+", clean)
            if _clean_words:
                _tr_hits = 0
                for _cw in _clean_words:
                    if any(c in _TR_SPECIFIC for c in _cw):
                        _tr_hits += 2  # Ozel karakter = cok guclu sinyal
                    elif len(_cw) >= 5:
                        _trs = _tr_freq_score(_cw)
                        if _trs >= 0.60:
                            _tr_hits += 1
                _tr_ratio = _tr_hits / max(len(_clean_words), 1)
                if _tr_ratio >= 0.55:
                    return ('turkish', 0.85, f'tr_freq_ratio={_tr_ratio:.2f}')

    # CJK kanji/hiragana/katakana
    if _CJK_RE.search(clean):
        return ('japanese', 1.0, 'cjk_chars')

    # Latin harf var mi?
    latin_words = _LATIN_WORD_RE.findall(clean)
    if not latin_words:
        # Muzik notu, noktalama, vs
        if _MUSIC_NOTE_RE.search(clean):
            return ('unknown', 0.5, 'music_note_only')
        return ('unknown', 0.3, 'no_latin')

    # Apostrophe = kesin Ingilizce
    if _APOSTROPHE_RE.search(clean):
        return ('english', 0.97, 'apostrophe')

    # Melodic filler: 'la la la', 'na na na' vb. → Japonca sarki dolgu sesi → romaji say
    _MELODIC_FILLER = frozenset({
        'la','na','da','ra','ya','wa','ha','ba','pa','ta',
        'ka','ga','sa','ma','fa','sha','nya','nyan','oo','ah'
    })
    _latin_lower = [w.lower() for w in latin_words]
    if _latin_lower and len(_latin_lower) >= 2 and all(w in _MELODIC_FILLER for w in _latin_lower):
        return ('romaji', 0.82, f'melodic_filler={_latin_lower[:3]}')

    # Romaji skoru hesapla
    rom_score, detail = score_text_romaji(clean)

    if rom_score >= 0.75:
        return ('romaji', rom_score, f'romaji_score={rom_score:.2f}|{detail}')
    elif rom_score <= 0.20:
        return ('english', 1.0 - rom_score, f'english_score={1-rom_score:.2f}|{detail}')
    else:
        # Orta bolge (0.20-0.75) — ek ipuclari dene
        word_count   = len(clean.split())
        avg_word_len = sum(len(w) for w in latin_words) / max(len(latin_words), 1)

        # Romaji heceleri kisa olur (ort 2-3 harf)
        if avg_word_len <= 3.5 and rom_score > 0.55:
            return ('romaji', rom_score, f'short_words({avg_word_len:.1f})+score={rom_score:.2f}')
        if avg_word_len >= 5.5 and rom_score < 0.5:
            return ('english', 1.0 - rom_score, f'long_words({avg_word_len:.1f})+score={1-rom_score:.2f}')

        # Lingua-language-detector fallback (kuruluysa)
        # DIKKAT: Lingua kisa/karma romaji metinleri yanlis English siniflandirabilir.
        # Sadece GERCEKTEN BELIRSIZ (0.40-0.60) bolgede VE uzun metinde kullan.
        # rom_score 0.60+ ise zaten romaji tercih edilmeli, lingua'ya gerek yok.
        _lingua_zone = 0.40 <= rom_score <= 0.60
        _long_enough = avg_word_len >= 4.5 and len(clean) >= 12
        if _LINGUA_OK and _lingua_zone and _long_enough:
            lingua_lang = _lingua_detect(clean)
            if lingua_lang == 'english':
                return ('english', max(0.70, 1.0 - rom_score), f'lingua=english|avg={avg_word_len:.2f}|{detail}')
            elif lingua_lang == 'japanese':
                return ('romaji', max(0.70, rom_score), f'lingua=japanese(romaji)|avg={avg_word_len:.2f}|{detail}')

        # Hala belirsiz
        if rom_score > 0.5:
            return ('romaji', rom_score, f'slight_romaji={rom_score:.2f}')
        return ('english', 1.0 - rom_score, f'slight_english={1-rom_score:.2f}')

# ─────────────────────────────────────────────────────────────────────────────
# 9. KARAOKE HECE TESPITI
# ─────────────────────────────────────────────────────────────────────────────

def is_karaoke_syllable(raw_text: str, duration_ms: int = 0) -> Tuple[bool, str]:
    """
    Tek bir event'in karaoke hecesi mi oldugunu kontrol eder.

    Kriterler:
      - {\\kXX} tag'i varsa — kesin karaoke
      - 1-4 karakter metin + sure < 650ms
      - Muzik notu + kisa metin
    """
    # Kesin karaoke tag'i
    if _KARAOKE_TAG_RE.search(raw_text):
        return True, 'karaoke_tag'

    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    # Bos veya sadece muzik notu
    if not clean or clean in ('♪', '♫', '~', '～', '♪♪', '♫♫'):
        return True, 'music_note_only'

    length = len(clean.replace(' ', ''))

    # 1-4 karakter (kisa ozel hece)
    if length <= 4:
        if duration_ms <= 0 or duration_ms < 700:
            return True, f'short_char={length}_dur={duration_ms}'

    # Cizgi karakteri veya tirelenmis tek sesli
    if re.match(r'^[-–—]+$', clean):
        return True, 'dash_only'

    return False, 'not_karaoke_syllable'

# ─────────────────────────────────────────────────────────────────────────────
# 10. SARKI TESPITI (icerik bazli, stil adina bakmaz)
# ─────────────────────────────────────────────────────────────────────────────

# Sarki stiline isaret eden ortak stil adlari (derleme)
_KNOWN_SONG_STYLE_PATTERNS = re.compile(
    r'\b(?:'
    # OP/ED varyantlari
    r'op|ed|opening|ending|insert|ins|oped|ncop|nced|'
    r'op\d|ed\d|ins\d|'
    # Karaoke
    r'kara(?:oke)?|karaoke|k[-_]|[-_]k\b|'
    # Romaji
    r'rom(?:aji)?|furigana|furi|ruby|'
    # Dil
    r'japanese|english|nihon|nihongo|'
    # Sarki
    r'song|lyric|lyrics|vocal|vox|choir|bgvocal|'
    r'uta|ost'
    r')\b',
    re.IGNORECASE
)

def is_song_event_by_content(
    raw_text: str,
    style_name: str = '',
    start_ms: int = 0,
    end_ms: int = 0,
    all_same_style_lens: Optional[List[int]] = None,
    ep_duration_ms: int = 0,
) -> Tuple[bool, int, str]:
    """
    Bir ASS event'inin sarki/karaoke event'i olup olmadigini
    icerik ve zamanlama analiziyle tespit eder.

    Args:
        raw_text:              Ham ASS metni ({tag}li)
        style_name:            Stil adi (bos olabilir)
        start_ms/end_ms:       Zamanlar (ms)
        all_same_style_lens:   Ayni stilde diger eventlerin temiz metin uzunluklari
        ep_duration_ms:        Bolum suresi (bilgilendirici)

    Returns:
        (is_song, score, reason)
        score >= 2 → sarki/karaoke
    """
    score = 0
    reasons = []
    duration = max(0, end_ms - start_ms)
    clean = _ASS_TAG_RE.sub('', raw_text).strip()
    word_count = len(clean.split()) if clean else 0

    # --- Ipucu 1: Muzik notu (+3) ---
    if _MUSIC_NOTE_RE.search(clean) or _MUSIC_NOTE_RE.search(raw_text):
        score += 3
        reasons.append('music_note')

    # --- Ipucu 2: Karaoke tag (+3) ---
    if _KARAOKE_TAG_RE.search(raw_text):
        score += 3
        reasons.append('karaoke_tag')

    # --- Ipucu 3: Hece karaoke (+2) ---
    is_kara, kara_why = is_karaoke_syllable(raw_text, duration)
    if is_kara:
        score += 2
        reasons.append(f'syllable:{kara_why}')

    # --- Ipucu 4: Bilinen sarki stil adi (+2) ---
    if style_name and _KNOWN_SONG_STYLE_PATTERNS.search(style_name):
        score += 2
        reasons.append(f'style_name:{style_name}')

    # --- Ipucu 5: Bolum basi/sonu pozisyon (+1) ---
    if start_ms < 120_000:  # ilk 2 dakika = OP
        if word_count <= 10:
            score += 1
            reasons.append('op_position')
    elif ep_duration_ms > 0 and start_ms > ep_duration_ms - 200_000:  # son 3.5 dk = ED
        if word_count <= 10:
            score += 1
            reasons.append('ed_position')

    # --- Ipucu 6: Komsu eventler de kisa mi? (+1) ---
    if all_same_style_lens and word_count <= 8:
        avg_len = sum(all_same_style_lens) / max(len(all_same_style_lens), 1)
        if avg_len <= 8:
            score += 1
            reasons.append(f'neighbor_short:{avg_len:.1f}')

    # --- Ipucu 7: Uzun satirlar (-1) diyalog ipucu ---
    if word_count >= 12 and score < 3:
        score -= 1
        reasons.append(f'long_line:{word_count}w')

    is_song = score >= 2
    return is_song, score, '+'.join(reasons) if reasons else 'no_signal'

# ─────────────────────────────────────────────────────────────────────────────
# 11. ANA SINIFLANDIRICI (butuncul event analizi)
# ─────────────────────────────────────────────────────────────────────────────

def classify_event(
    raw_text: str,
    style_name: str = '',
    start_ms: int = 0,
    end_ms: int = 0,
    effect_field: str = '',
    all_same_style_lens: Optional[List[int]] = None,
    ep_duration_ms: int = 0,
) -> Tuple[str, float, str]:
    """
    Bir ASS event'ini tam olarak siniflandirir.

    Returns:
        (action, confidence, reason)
        action:
          'translate_song'    — Ingilizce sarki sozu, tercume et
          'translate_dialog'  — Ingilizce diyalog, tercume et
          'skip_romaji'       — Japonca romaji, atlama
          'skip_karaoke_jp'   — Japonca karaoke hecesi, atlama
          'skip_effect'       — Sadece animasyon, metin yok
          'skip_turkish'      — Zaten Turkce
          'skip_japanese'     — Kanji/Hiragana/Katakana Japonca
          'uncertain'         — Belirsiz
    """
    duration = max(0, end_ms - start_ms)
    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    # --- Hizli cikislar ---
    if not clean:
        return ('skip_effect', 1.0, 'no_text')

    if _DRAW_RE.search(raw_text) and len(clean) < 5:
        return ('skip_effect', 0.95, 'draw_command')

    # Turkce kontrolu
    tr_count = sum(1 for c in clean if c in _TR_CHARS)
    if tr_count >= 2:
        return ('skip_turkish', 0.97, f'tr_chars={tr_count}')

    # CJK Japonca
    if _CJK_RE.search(clean):
        return ('skip_japanese', 1.0, 'cjk')

    # --- Stil adi analizi ---
    style_cat, style_conf, style_reason = classify_style(style_name)

    # --- Icerik dil analizi ---
    lang, lang_conf, lang_reason = classify_text(raw_text, duration)

    # --- Sarki tespiti ---
    is_song, song_score, song_reason = is_song_event_by_content(
        raw_text, style_name, start_ms, end_ms,
        all_same_style_lens, ep_duration_ms
    )

    # --- Karaoke hece tespiti ---
    is_kara, kara_why = is_karaoke_syllable(raw_text, duration)

    # ---- Karar mantigi ----

    # 1. Sadece efekt
    if lang == 'effect_only':
        return ('skip_effect', 0.95, 'effect_only')

    # 2. Japonca romaji
    if lang == 'romaji' and lang_conf >= 0.60:
        if is_kara:
            return ('skip_karaoke_jp', 0.90, f'romaji+karaoke|{lang_reason}')
        return ('skip_romaji', lang_conf, f'romaji|{lang_reason}')

    # 2b. Cok kisa metin (1-2 kelime) romaji puani 0.5+ ise romaji say
    if lang == 'romaji' and len(clean.split()) <= 3:
        return ('skip_romaji', max(0.60, lang_conf), f'short_romaji|{lang_reason}')

    # 3. Karaoke hece (romaji degil ama hece karaoke)
    if is_kara and style_cat in ('karaoke_jp', 'song_jp'):
        return ('skip_karaoke_jp', 0.85, f'kara_syllable+jp_style|{kara_why}')

    # 3b. JP STİLİ + romaji/belirsiz icerik → her zaman skip
    # ED1-JP, OP1-JP gibi JP sufiksli stiller, icerik Ingilizce degilse skip
    if style_cat in ('song_jp', 'karaoke_jp') and lang not in ('english',):
        if is_kara:
            return ('skip_karaoke_jp', 0.90, f'jp_style+kara|{lang_reason}')
        return ('skip_romaji', 0.80, f'jp_style_noneng|{lang_reason}')

    # 4. Ingilizce sarki sozu
    if lang == 'english' and is_song:
        return ('translate_song', min(lang_conf, 0.9 + song_score * 0.02),
                f'english_song|{lang_reason}|{song_reason}')

    # 5. Ingilizce sarki stili ama icerik belirsiz
    if style_cat in ('song_en', 'karaoke_en') and lang in ('english', 'mixed'):
        return ('translate_song', 0.80, f'en_style+{lang}|{style_reason}')

    # 6. Ingilizce diyalog
    if lang == 'english' and lang_conf >= 0.7:
        return ('translate_dialog', lang_conf, f'english_dialog|{lang_reason}')

    # 7. Sarki ipucu yeterince guclu ama dil belirsiz
    if is_song and song_score >= 3:
        # JP stili olsa bile song signal varsa skip (romaji sarki)
        if style_cat in ('song_jp', 'karaoke_jp'):
            return ('skip_romaji', 0.65, f'song_jp_signal|{song_reason}')
        if lang in ('english', 'mixed', 'unknown'):
            return ('translate_song', 0.70, f'song_signal|{song_reason}')
        return ('skip_romaji', 0.65, f'song_jp_signal|{song_reason}')

    # 8. Genel diyalog (fallback)
    if lang == 'english':
        return ('translate_dialog', lang_conf, f'fallback_eng|{lang_reason}')

    return ('uncertain', 0.4, f'lang={lang}|style={style_cat}|{lang_reason}')

# ─────────────────────────────────────────────────────────────────────────────
# 12. BATCH HELPER — pysubs2 event listesi icin
# ─────────────────────────────────────────────────────────────────────────────

def classify_events_batch(
    events: List[dict],
    ep_duration_ms: int = 0,
) -> List[Tuple[str, float, str]]:
    """
    Event listesini toplu olarak siniflandirir.
    Her event dict'i 'parts' listesi icermeli: parts[1]=start, parts[2]=end,
    parts[3]=style, parts[8]=effect, parts[9]=text
    """
    # Stil bazi istatistikleri topla (komsu length)
    from collections import defaultdict
    style_lens: dict = defaultdict(list)

    for ev in events:
        p = ev.get('parts', [])
        if len(p) > 9:
            style = p[3]
            clean = _ASS_TAG_RE.sub('', p[9]).strip()
            style_lens[style].append(len(clean.split()))

    results = []
    for ev in events:
        p = ev.get('parts', [])
        if len(p) <= 9:
            results.append(('uncertain', 0.0, 'no_parts'))
            continue

        style   = p[3]
        text    = p[9]
        effect  = p[8] if len(p) > 8 else ''
        start   = _ts_to_ms(p[1])
        end     = _ts_to_ms(p[2])
        # Komsu uzunluklar (kendisi haric)
        neighbors = [x for x in style_lens[style]]  # includes self, ok for avg

        action, conf, reason = classify_event(
            raw_text=text,
            style_name=style,
            start_ms=start,
            end_ms=end,
            effect_field=effect,
            all_same_style_lens=neighbors,
            ep_duration_ms=ep_duration_ms,
        )
        results.append((action, conf, reason))

    return results

# ─────────────────────────────────────────────────────────────────────────────
# 13. SELF TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 70)
    print("  CONTENT DETECTOR — KAPSAMLI TEST")
    print("=" * 70)

    style_tests = [
        ('ED1-JP-kara',   'karaoke_jp'),
        ('ED1-EN-kara',   'karaoke_en'),
        ('OP1-EN',        'song_en'),
        ('OP1 JP',        'song_jp'),
        ('Default',       'generic'),
        ('Main',          'generic'),
        ('Style0001',     'generic'),
        ('Song',          'song_unknown'),
        ('Lyric',         'song_unknown'),
        ('Dialogue',      'dialog'),
        ('Signs',         'generic'),
    ]

    print("\n[Stil Adi Testi]")
    ok = fail = 0
    for sname, expected in style_tests:
        cat, conf, reason = classify_style(sname)
        status = 'OK' if cat == expected else 'FAIL'
        if status == 'OK': ok += 1
        else: fail += 1
        print(f"  [{status}] {sname!r:20s} → {cat} ({conf:.2f})")
    print(f"  {ok}/{ok+fail} OK")

    text_tests = [
        ("No one else—only you",         'english'),
        ("Even if the world hasn't forgotten yet", 'english'),
        ("Sekai wa utsukushii",           'romaji'),
        ("Nee zutto soba ni ite",         'romaji'),
        ("Bu dünya güzel",               'turkish'),
        ("",                              'effect_only'),
        ("I found the light again",       'english'),
        ("hikari wo mitsuketa",           'romaji'),
    ]

    print("\n[Metin Dil Testi]")
    for text, expected in text_tests:
        lang, conf, reason = classify_text(text)
        status = 'OK' if lang == expected else 'FAIL'
        print(f"  [{status}] {text!r:42s} → {lang} ({conf:.2f})")

    print("\n[Event Siniflandirma Testi]")
    event_tests = [
        # (text, style, start_ms, end_ms, expected_action)
        ("No one else—only you",  "ED1-EN-kara",  1434000, 1437000, 'translate_song'),
        ("{\\k12}Ne{\\k10}e",    "ED1-JP-kara",  1200000, 1201000, 'skip_karaoke_jp'),
        ("Sekai wa",             "Default",       1200000, 1202800, 'skip_romaji'),
        ("♪ I love you ♪",      "Default",       60000,   63000,   'translate_song'),
        ("Bu dünyan",            "Default",       300000,  303000,  'skip_turkish'),
        ("",                     "Default",       0,       0,       'skip_effect'),
    ]
    for text, style, s, e, exp in event_tests:
        action, conf, reason = classify_event(text, style, s, e)
        status = 'OK' if action == exp else 'FAIL'
        print(f"  [{status}] {text!r:35s} [{style}] → {action}")

    print("\n" + "=" * 70)
