"""
processor/karaoke.py
====================
Karaoke satırlarını collapse edip Türkçe'ye çeviren pass.
_preprocess_collapse_karaoke + _collapse_and_translate_karaoke
"""
import re
import json
import time

try:
    from processor.style_detect import (
        DELETE_KEYWORDS, SONG_KEYWORDS, STYLE_SUFFIX_SKIP,
        is_song_style_name, get_style_suffix_behavior,
    )
except ImportError:
    DELETE_KEYWORDS = []
    SONG_KEYWORDS = []
    STYLE_SUFFIX_SKIP = set()
    def is_song_style_name(s): return False
    def get_style_suffix_behavior(s): return None

def _preprocess_collapse_karaoke(subs):
    """
    PRE-PROCESSING: pysubs2 SSAFile event listesini structured_events'e
    donusturulmeden ONCE karaoke eventleri isler:

    MOD A — Full-line kara (3+ kelime): Her event bagımsız, sadece tag soy +
             style → base EN stili (ED1-EN-kara → ED1-EN). Birleştirme YOK.
    MOD B — Letter/hece kara (1-2 char, kara suffix'li): Zaman penceresi ile grupla, birlestir.
    MOD C — {k...} tag'li ama kara suffix'siz per-syllable EN sarki: Ayni timestamp
             grubundaki heceler birlestirilir, karaoke tag'leri temizlenir, ceviri
             icin hazirlanir. (Ornek: ED1-EN stilinde her hece ayri event)
    Draw command eventleri: tamamen bosalt + Comment'e al.

    Returns: islenen event/grup sayisi
    """
    _TAG_RE   = re.compile(r'\{[^}]*\}')
    _TR_CHARS = set('ğşçöüıİĞŞÇÖÜ')
    # {\kXX}, {\kfXX}, {\koXX}, {\ktXX} — tüm karaoke zamanlama tag'leri
    _KARA_TAG_RE = re.compile(r'\{[^}]*\\[kK][fFoOtT]?\d+[^}]*\}')

    # Dosyadaki varsayılan diyalog stilini bul
    _default_style = 'Default'
    for _st in subs.styles:
        if _st.lower() in ('default', 'dialogue', 'main', 'dialog'):
            _default_style = _st
            break

    GAP_MS = 1000  # 1 saniyeden fazla bosluk → yeni grup

    # ── Karaoke stili tespit (hem EN/ENG hem JP/ROM kontrol et)
    def _is_kara_style(style):
        """Stil herhangi bir karaoke suffixine sahip mi?"""
        return 'kara' in style.lower() or 'karaoke' in style.lower()

    def _kara_needs_translation(style):
        """Bu kara stili İngilizce → çeviri gerekiyor mu?
        romaji_detector'a sorulur; stil adı kesin romaji/JP ise → hayır"""
        # Stil adı kesin romaji/JP ise hiç çevirme
        if _rom_style_is_jp(style):
            return False
        # Stil adı kesin İngilizce ise çevir
        if _rom_style_is_eng(style):
            return get_style_suffix_behavior(style) == 'translate'
        # Belirsiz: behavior kontrol
        return get_style_suffix_behavior(style) == 'translate'

    # Kara suffix soy → base stil
    def _base_style(style):
        b = re.sub(r'[-_]?kara(?:oke)?$', '', style, flags=re.IGNORECASE).rstrip('-_ ')
        return b if b else _default_style

    total_collapsed = 0

    # ══════════════════════════════════════════════════════════════════
    # MOD C: {k...} tag'li ama kara suffix'siz per-syllable EN sarkilar
    # Ozel durum: ED1-EN, OP1-EN gibi sarkı stilleri her heceyi ayri event
    # olarak kodluyorsa bunları zaman-penceresiyle birleştir.
    # ══════════════════════════════════════════════════════════════════
    _MODC_GAP_MS = 150   # Hece arası max boşluk (ms) — karaoke timing çok sık
    _modc_by_style = {}
    for ev in subs:
        if ev.type == 'Comment':
            continue
        if _is_kara_style(ev.style):
            continue  # MOD A/B zaten hallediyor
        # Şarkı stili olmalı
        if not is_song_style_name(ev.style):
            continue
        # Stil çeviri gerektirmeli (JP/ROM değil)
        if _rom_style_is_jp(ev.style):
            continue
        # Metinde {k...} tag olmalı
        if not _KARA_TAG_RE.search(ev.text):
            continue
        clean = _TAG_RE.sub('', ev.text).replace('\\N', '').replace('\\n', '').strip()
        if not clean:
            continue
        # Zaten Türkçe ise atla
        if any(c in _TR_CHARS for c in clean):
            continue
        # Draw command ise atla
        try:
            from ass_line_filter import is_drawing_line as _local_is_draw
            _is_draw_val = _local_is_draw(ev.text) or _local_is_draw(clean)
        except Exception:
            _is_draw_val = bool(_DRAW_CMD_RE.search(clean)) and len(re.sub(r'[^a-zA-Z]', '', clean)) < 5
        if _is_draw_val:
            ev.type = 'Comment'
            continue
        _modc_by_style.setdefault(ev.style, []).append(ev)

    for style, ev_list in _modc_by_style.items():
        # Zamana göre sırala
        ev_list_sorted = sorted(ev_list, key=lambda e: e.start)
        # Zamana göre grupla — ardışık hece grubu
        groups = []
        cur_grp = [ev_list_sorted[0]]
        for ev in ev_list_sorted[1:]:
            # Bir önceki event'in bitiş zamanına yakın mı?
            gap = ev.start - cur_grp[-1].end
            if gap <= _MODC_GAP_MS:
                cur_grp.append(ev)
            else:
                if len(cur_grp) >= 2:  # 2+ hece birleşince anlam kazanır
                    groups.append(cur_grp)
                cur_grp = [ev]
        if len(cur_grp) >= 2:
            groups.append(cur_grp)

        for grp in groups:
            # Temiz metin parçalarını al
            parts_text = []
            for ev in grp:
                ch = _TAG_RE.sub('', ev.text).replace('\\N', '').replace('\\n', '').strip()
                if ch:
                    parts_text.append(ch)
            merged = ' '.join(parts_text).strip()
            if len(merged) < 2:
                continue

            # İlk event → birleştirilmiş metin + geniş süre
            first = grp[0]
            first.text  = merged           # Tag'siz temiz EN
            first.end   = grp[-1].end      # Son heceye kadar uzat
            # Stil suffix'ini temizle (OP1-EN → OP1-EN, zaten ok)
            # kara suffix yoktu, stil olduğu gibi kalır

            # Geri kalan heceleri Comment yap
            for ev in grp[1:]:
                ev.type = 'Comment'

            total_collapsed += 1
            print(f"   [KaraMODC] '{merged[:40]}' — {len(grp)} hece birlestirildi ({style})")
    # ══════════════════════════════════════════════════════════════════


    # Stil bazında eventleri topla
    from collections import defaultdict
    _by_style = defaultdict(list)
    for ev in subs:
        if ev.type == 'Comment':
            continue
        if not _is_kara_style(ev.style):
            continue
        clean = _TAG_RE.sub('', ev.text).replace('\\N', '').replace('\\n', '').strip()
        # Draw command eventleri → tamamen gizle (sadece Comment yap, metni silme)
        try:
            from ass_line_filter import is_drawing_line as _local_is_draw
            _is_draw_val = _local_is_draw(ev.text) or _local_is_draw(clean)
        except Exception:
            _is_draw_val = bool(_DRAW_CMD_RE.search(clean)) and len(re.sub(r'[^a-zA-Z]', '', clean)) < 5
        if _is_draw_val:
            ev.type = 'Comment'  # Gizle ama orijinal metni koru
            continue
        # Boş
        if not clean:
            ev.type = 'Comment'  # Gizle ama orijinal metni koru
            continue
        # Türkçe ise zaten çevrilmiş → atla
        if any(c in _TR_CHARS for c in clean):
            continue
        _by_style[ev.style].append((ev, clean))

    if not _by_style:
        return 0

    for style, ev_pairs in _by_style.items():
        bs = _base_style(style)

        # ── ROMAJI TESPITI: Üç katmanlı analiz ────────────────────────
        # Grup için tüm heceleri al ve birleştir
        all_syllables = [ch for _, ch in ev_pairs]
        merged_text   = ' '.join(all_syllables)

        # Katman 1: romaji_detector (stil adı + fonotaktik + hece listesi)
        label, conf, reason = _rom_classify_group(all_syllables, style, merged_text)

        # Katman 2: Belirsiz sonucu romaji_filter (157K kanwadict4 DB) ile doğrula
        if label == 'uncertain' and _is_romaji_sentence_v2 is not None:
            # Birleşik metinde tam cümle analizi yap
            db_is_romaji = _is_romaji_sentence_v2(merged_text)
            if db_is_romaji:
                label = 'romaji'
                reason = f'kanwadict_confirm({reason})'
            elif not _kara_needs_translation(style):
                # DB de romaji demedi ama çeviri gerekmiyor → güvenli atlama
                label = 'romaji'
                reason = f'no_translate_behavior({reason})'
            else:
                # DB romaji demedi VE stil çeviri istiyor → İngilizce kabul et
                label = 'english'
                reason = f'kanwadict_reject({reason})'

        # Katman 3: Stil adı kesin romaji ise her zaman atla
        if _rom_style_is_jp(style):
            label = 'romaji'
            reason = f'style_override'

        # Romaji → sessizleştir (sadece Comment yap, metni silme)
        if label == 'romaji':
            for ev, _ in ev_pairs:
                ev.type = 'Comment'  # Gizle ama orijinal romaji metni dosyada kalsin
            continue  # Bu stili atla

        # İngilizce / çeviri gerekiyor → devam
        # (label == 'english')

        # ── MOD KARAR: Full-line mi, Letter/hece mi? ──────────────────
        # İlk event'in temiz metnine bak
        sample_clean = ev_pairs[0][1]
        word_count = len(sample_clean.split())
        is_fullline_mode = word_count >= 3  # 3+ kelime → full cümle modu
        # ──────────────────────────────────────────────────────────────

        if is_fullline_mode:
            # ── MOD A: Full-line kara ─────────────────────────────────
            # Her event bağımsız: sadece tag soy + style değiştir
            # Birleştirme YOK → Phase 2'ye birer birer gider
            for ev, clean in ev_pairs:
                ev.text  = clean       # Tag'siz temiz İngilizce
                ev.style = bs          # ED1-EN-kara → ED1-EN
                total_collapsed += 1
            # ─────────────────────────────────────────────────────────
        else:
            # ── MOD B: Letter/hece kara ──────────────────────────────
            # Zaman penceresine göre grupla, birleştir
            evs_sorted = sorted(ev_pairs, key=lambda x: x[0].start)

            groups = []
            cur = [evs_sorted[0]]
            for item in evs_sorted[1:]:
                ev = item[0]
                if ev.start - cur[-1][0].end > GAP_MS:
                    groups.append(cur)
                    cur = [item]
                else:
                    cur.append(item)
            groups.append(cur)

            for grp in groups:
                chars = [ch for _, ch in grp]
                # Her parcayi boslukla birlestir
                # Onceki kod kisa (<=2 char) parcalari bosluksuz yapistiriyordu
                # Bu 'shi'+'ma'+'tsu' = 'shimatsui' gibi bozukluga yol aciyordu
                parts = []
                for ch in chars:
                    if ch.strip():
                        parts.append(ch.strip())
                merged = ' '.join(parts)  # Her zaman boslukla birlestir
                merged = merged.strip()
                if len(merged) < 3:
                    continue

                grp_start = grp[0][0].start
                grp_end   = grp[-1][0].end

                first_ev = grp[0][0]
                first_ev.start = grp_start
                first_ev.end   = grp_end
                first_ev.text  = merged
                first_ev.style = bs

                for ev, _ in grp[1:]:
                    ev.type = 'Comment'  # Gizle ama metni silme (gruba birleştirildi)

                total_collapsed += 1
            # ─────────────────────────────────────────────────────────

    return total_collapsed

def _collapse_and_translate_karaoke(structured_events, translator,
                                    lyrics_system_prompt, ctx_str):
    """
    Hece/harf bazlı karaoke İngilizce eventleri toplar, birleştirir,
    çevirir ve tek bir hareketsiz static event'e indirger.

    Algoritma:
    1. 'kara' suffix'li + İngilizce (EN/ENG) stilleri bul
    2. Aynı stil içinde zamana göre gruplara ayır (boşluk > 1sn → yeni grup)
    3. Her grubun text'ini birleştir, tüm tag'leri soy
    4. İngilizce ise çevir
    5. İlk event = merged süre + Türkçe metin (tag'siz)
    6. Geri kalan event'ler = boş metin (görünmez)

    Returns: collapse edilen grup sayısı
    """
    from colorama import Fore, Style
    import time as _time_mod

    # --- Yardımcı: ASS zaman string → ms ---
    def _ts2ms(ts):
        try:
            h, m, rest = str(ts).replace(',', '.').split(':')
            s, cs = rest.split('.')
            return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(cs)*10
        except Exception:
            return 0

    def _ms2ts(ms):
        ms = max(0, int(ms))
        h  = ms // 3600000; ms %= 3600000
        m  = ms //   60000; ms %=   60000
        s  = ms //    1000; ms %=    1000
        cs = ms //      10
        return f'{h}:{m:02d}:{s:02d}.{cs:02d}'

    # --- Karaoke stil adını tespit et ---
    def _is_kara_style(style):
        s = style.lower()
        # 'kara' veya 'karaoke' içermeli
        if 'kara' not in s and 'karaoke' not in s:
            return False
        # İngilizce suffix zorunlu (behavior == 'translate')
        return get_style_suffix_behavior(style) == 'translate'

    # 1. Karaoke İngilizce eventleri filtrele
    kara_events = []
    for ev in structured_events:
        parts = ev.get('parts', [])
        if len(parts) < 10:
            continue
        style = parts[3]
        if not _is_kara_style(style):
            continue
        # Metnin İngilizce olup olmadığını kontrol et (Türkçe char yoksa)
        clean = _SONG_TAG_RE.sub('', parts[9]).strip()
        if not clean:
            continue
        if any(c in _SONG_TR_CHARS for c in clean):
            continue  # Zaten çevrilmiş
        kara_events.append(ev)

    if not kara_events:
        return 0

    print(f"{Fore.MAGENTA}   [KaraCollapse] {len(kara_events)} kara event bulundu{Style.RESET_ALL}")

    # 2. Stil adına + zamana göre gruplara ayır
    from collections import defaultdict
    by_style = defaultdict(list)
    for ev in kara_events:
        style = ev['parts'][3]
        by_style[style].append(ev)

    GAP_MS   = 1000  # 1 saniyeden büyük boşluk → yeni satır grubu
    collapsed = 0

    for style, evs in by_style.items():
        # Başlangıç zamanına göre sırala
        evs_sorted = sorted(evs, key=lambda e: _ts2ms(e['parts'][1]))

        # Gruplara ayır
        groups = []
        cur_group = [evs_sorted[0]]
        for ev in evs_sorted[1:]:
            prev_end   = _ts2ms(cur_group[-1]['parts'][2])
            this_start = _ts2ms(ev['parts'][1])
            if this_start - prev_end > GAP_MS:
                groups.append(cur_group)
                cur_group = [ev]
            else:
                cur_group.append(ev)
        groups.append(cur_group)

        print(f"{Fore.MAGENTA}   [KaraCollapse] {style}: {len(groups)} satir grubu{Style.RESET_ALL}")

        # 3. Her grubu birleştir + çevir
        lines_to_translate = []
        _group_is_fullsentence = []
        for grp in groups:
            chars = []
            for ev in grp:
                ch = _SONG_TAG_RE.sub('', ev['parts'][9]).replace('\\N', '').replace('\\n', '').strip()
                chars.append(ch)
            parts_list = [ch for ch in chars if ch.strip()]
            merged = ' '.join(parts_list).strip()

            # Tam cümle tespiti: her event uzun metinse (ED1-EN-kara gibi)
            # bu bir hece-karaoke değil, song pass zaten çevirdi — atla
            avg_ev_len = sum(len(c) for c in parts_list) / max(len(parts_list), 1)
            is_full = avg_ev_len > 12
            _group_is_fullsentence.append(is_full)
            if is_full:
                print(f"{Fore.CYAN}   [KaraCollapse] ATLANDI (tam cumle song pass isledi): {merged[:50]!r}{Style.RESET_ALL}")
            lines_to_translate.append(merged)

        valid_indices = [
            i for i, t in enumerate(lines_to_translate)
            if len(t) >= 3 and not _group_is_fullsentence[i]
        ]

        if not valid_indices:
            continue

        lines_clean = [lines_to_translate[i] for i in valid_indices]
        groups_valid = [groups[i] for i in valid_indices]

        # 4. Çeviri
        try:
            _orig_prompt = translator.config.get('system_prompt', '')
            # lyrics_system_prompt tüm gruplar cache hit ise None olabilir — fallback oluştur
            _lsp = lyrics_system_prompt or (
                f"You are an anime song lyric translator. Translate the following song lines "
                f"to natural, poetic Turkish. Context: {ctx_str}. "
                "Return ONLY the translated lines, one per line. Do not add explanations."
            )
            translator.config['system_prompt'] = _lsp
            response = translator.translate_batch(lines_clean)
            translator.config['system_prompt'] = _orig_prompt

            if isinstance(response, list):
                translations = {i: str(r).strip() for i, r in enumerate(response) if r and str(r).strip()}
            else:
                translations = {}
        except Exception as _e:
            translator.config['system_prompt'] = _orig_prompt
            print(f"{Fore.RED}   [KaraCollapse] Ceviri hatasi: {_e}{Style.RESET_ALL}")
            continue

        # 5. Her gruba uygula
        for local_i, (grp, src_text) in enumerate(zip(groups_valid, lines_clean)):
            translated = translations.get(local_i, '')
            translated = _SONG_PREFIX_RE.sub('', translated)
            translated = re.sub(r'\[L\d+\]\s*', '', translated).strip()
            # [FIX3] API draw command dondurmuse fallback
            if len(re.findall(r'\bm\s+\d+\s+\d+\b', translated)) >= 3:
                _ltrs = re.findall(r'[a-zA-Z\u2014\-]+', src_text.replace('m 0 0 m 100 100 ', ''))
                translated = ' '.join(_ltrs[:20]) if _ltrs else src_text
            # [L1]/[L2]/[L3] marker'larini temizle (SONG_PREFIX_RE zaten halleder)
            translated = _SONG_PREFIX_RE.sub('', translated)
            translated = re.sub(r'\[L\d+\]\s*', '', translated).strip()

            if not translated:
                translated = src_text  # Fallback: orijinal (İngilizce kalır)

            # Grubun toplam süresini hesapla
            grp_start_ms = _ts2ms(grp[0]['parts'][1])
            grp_end_ms   = _ts2ms(grp[-1]['parts'][2])
            new_start    = _ms2ts(grp_start_ms)
            new_end      = _ms2ts(grp_end_ms)

            # İlk event: birleşik süre + temiz çeviri
            first_ev    = grp[0]
            first_parts = first_ev['parts']
            first_parts[1] = new_start
            first_parts[2] = new_end
            first_parts[9] = translated  # Tag'siz temiz Türkçe
            first_ev['text'] = translated
            _pev = first_ev.get('_pysubs2_ev')
            if _pev is not None:
                _pev.text    = translated
                _pev.start   = grp_start_ms
                _pev.end     = grp_end_ms

            # Geri kalan event'ler: boşalt
            for ev in grp[1:]:
                ev['parts'][9] = ''
                ev['text']     = ''
                _pev2 = ev.get('_pysubs2_ev')
                if _pev2 is not None:
                    _pev2.text = ''

            print(f"     [{style}] {repr(src_text[:35])} → {repr(translated[:35])}")
            collapsed += 1
            _time_mod.sleep(0.2)

    return collapsed


SIGN_KEYWORDS = DELETE_KEYWORDS

CREDIT_KEYWORDS = [
    'ceviri', 'ceviren', 'fansub', 'sunar',
    # Cevirmen ifadeleri — sadece kesin krediler
    'translated by', 'translation by', 'translation:', 'ceviri:', 'ceviren:',
    'edited by', 'editing by', 'editor:', 'duzenleyen:',
    'timed by', 'timing by', 'timing:', 'senkronize:',
    'encoded by', 'encoding by', 'upscaled by', 'encode:',
    'quality check', 'qc by', 'typeset by', 'karaoke by',
    'fansubbed by', 'subbed by', 'subtitles by', 'altyazi:',
    'hazirlayan:', 'hazirlayanlari:',
    'subs by', 'sub by', 'fansub by', 'soft sub by', 'hardsub by',
    # Sosyal medyaya DAVET ifadeleri (URL ile beraber kullanılan)
    'join discord', 'join our server', 'join our discord',
    'follow us on', 'find us on',
    'our discord', 'our server',
    # Bağış platformları (tam URL formatı)
    'discord.gg', 'discord.com/invite',
    'ko-fi.com', 'buymeacoffee.com', 'paypal.me', 'linktr.ee',
    'patreon.com', 'twitter.com', 'instagram.com', 'youtube.com',
    'reddit.com', 'discord.com', 'tiktok.com', 'twitch.tv',
    # Fansub grup kalıpları
    'fansubber', 'subgroup', 'sub group', 'scanlation',
    'sakuracircle', 'productions',
    # Açık URL formatları
    'http://', 'https://', 'www.',
    # Altyazı metadata (encode kalıpları)
    'upscaled by', 'subtitled by',
]


# Kredi satiri regex kaliplari (URL veya sosyal hesap iceren satirlar)
_CREDIT_REGEX_PATTERNS = re.compile(
    r'(?ix)'
    r'discord\.gg/[\w-]+|'             # discord.gg/invite
    r'discord\.com(?:/invite)?/[\w-]+|'# discord.com/invite/xxx
    r't\.me/[\w-]+|'                    # telegram
    r'youtu\.be/[\w-]+|'               # youtube kisa
    r'linktr\.ee/[\w-]+|'              # linktree
    r'ko-fi\.com/[\w-]+|'              # ko-fi
    r'buymeacoffee\.com/[\w-]+|'       # buymeacoffee
    r'patreon\.com/[\w-]+|'            # patreon
    r'paypal\.me/[\w-]+|'              # paypal me
    r'^@[a-zA-Z0-9_]{2,}$|'            # @handle SADECE - sozluk/referans degilse (in-anime post degil)
    r'https?://[^\s]+|'                # herhangi URL
    r'www\.[\w.-]+\.[a-z]{2,}|'        # www.site.com
    r'[\w.-]+\.(?:com|org|net|moe|gg|tv|io|me|link)/[\w-]+|'  # site.com/path
    # © ayri blokta studio check ile kontrol ediliyor (buradan kaldirildi)
    r'\[\w+(?:subs|fansub|raw|hd)\]'   # [SubsPlease] [FansubNameHD] gibi
)
# Hareketli taglerdeki anlamlı kısa kelimeleri korumamak (çevirmek) için
SHORT_ENGLISH_WHITELIST = {
    # 1-3 letter common words that might appear in signs/dialogue
    "i", "a", "ok", "no", "yes", "go", "hi", "ha", "ah", "oh", "hm", 
    "to", "in", "on", "at", "by", "up", "of", "or", "as", "if", "it", 
    "is", "he", "we", "do", "my", "me", "us", "be", "so", "an",
    "run", "end", "fin", "ask", "bad", "big", "box", "boy", "bus", 
    "but", "buy", "can", "car", "cat", "cut", "dad", "day", "die", 
    "dog", "eat", "eye", "fat", "fit", "fly", "for", "fun", "get", 
    "god", "got", "guy", "hey", "hit", "hot", "how", "hug", "job", 
    "joy", "key", "kid", "kit", "law", "let", "lie", "low", "mad", 
    "man", "map", "may", "mom", "new", "nor", "not", "now", "num", 
    "off", "oil", "old", "one", "out", "own", "pay", "pie", "pig", 
    "put", "red", "run", "sad", "saw", "say", "sea", "see", "set", 
    "she", "shy", "sin", "sit", "six", "sky", "son", "sun", "tap", 
    "tea", "ten", "the", "tie", "too", "top", "try", "two", "use", 
    "van", "war", "way", "who", "why", "win", "wow", "yes", "yet", "you"
}

