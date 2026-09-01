"""
processor/song_translate.py
===========================
İngilizce OP/ED şarkı sözlerini Türkçe'ye çeviren pass.
translate_song_lyrics_pass() ana giriş noktasıdır.
"""
import re
import json
import time

def translate_song_lyrics_pass(structured_events, translator, media_context):
    """
    Phase 2: Ana çeviri bittikten sonra İngilizce şarkı stillerini
    ayrı, şiirsel/müzikal bir prompt ile Gemini'ye gönderir.

    - Romaji / JP / Karaoke-hece eventleri hiç dokunulmaz
    - Sadece ENG/EN suffix'li şarkı stilleri işlenir
    - Her stil grubu (OP, ED, Insert) ayrı batch olarak gönderilir
    - ev.text _pysubs2_ev referansı ile doğrudan güncellenir

    Returns: çevrilen event sayısı
    """
    from colorama import Fore, Style

    # Algılama Motoru flag'leri (media_context üzerinden gelir)
    _use_style_suffix = media_context.get('use_style_suffix_detection', True)
    _use_kara_collapse = media_context.get('use_karaoke_collapse', True)
    _ignore_style_romaji = media_context.get('ignore_song_style_for_romaji', False)

    song_events = []
    _pre_reserved = [ev for ev in structured_events if ev.get('type') == 'song_reserved']
    if _pre_reserved:
        song_events.extend(_pre_reserved)
        print(f"{Fore.CYAN}   [SongPass] {len(_pre_reserved)} pre-reserved şarkı satırı eklendi.{Style.RESET_ALL}")

    _seen_ids = {id(ev) for ev in song_events}

    if _use_style_suffix:
        _suffix_events = [
            ev for ev in structured_events 
            if _is_english_song_event(ev) and not (ev.get('skip_translation') and ev.get('type') != 'song_reserved')
        ]
        _added_suffix = 0
        for ev in _suffix_events:
            if id(ev) not in _seen_ids:
                song_events.append(ev)
                _seen_ids.add(id(ev))
                _added_suffix += 1
        if _added_suffix > 0:
            print(f"{Fore.CYAN}   [SongPass] {_added_suffix} stil suffix'li şarkı satırı eklendi.{Style.RESET_ALL}")
    else:
        _text_events = []
        for ev in structured_events:
            if ev.get('skip_translation') and ev.get('type') != 'song_reserved':
                continue
            style = ev['parts'][3] if len(ev.get('parts', [])) > 3 else ''
            if not is_song_style_name(style):
                continue
            text = ev['parts'][9] if len(ev.get('parts', [])) > 9 else ''
            clean = _SONG_TAG_RE.sub('', text).strip()
            if not clean or len(clean) <= 2:
                continue
            if any(c in _SONG_TR_CHARS for c in clean):
                continue
            if re.search(r'[a-zA-Z]{2,}', clean):
                _text_events.append(ev)
        
        _added_text = 0
        for ev in _text_events:
            if id(ev) not in _seen_ids:
                song_events.append(ev)
                _seen_ids.add(id(ev))
                _added_text += 1
        if _added_text > 0:
            print(f"{Fore.YELLOW}   [Motor] Stil suffix KAPALI — {_added_text} event metin analizi ile eklendi{Style.RESET_ALL}")

    if not song_events:
        return 0

    # 2. Stil grubuna göre gruplandır
    from collections import defaultdict
    groups = defaultdict(list)
    for ev in song_events:
        style = ev['parts'][3] if len(ev.get('parts', [])) > 3 else 'Unknown'
        song_type = _get_song_type(style)
        groups[song_type].append(ev)

    anime_title  = media_context.get('title', 'Unknown Anime')
    season_num   = media_context.get('season', '')
    episode_num  = media_context.get('episode', '')
    ctx_str      = f"{anime_title}"
    if season_num: ctx_str += f" Season {season_num}"
    if episode_num: ctx_str += f" Episode {episode_num}"

    total_fixed = 0
    _song_cache = _load_song_cache()   # Kalıcı şarkı sözü cache'i
    _song_cache_dirty = False
    lyrics_system_prompt = None        # Cache-hit durumunda da erişilebilir olsun

    for song_type, events_group in groups.items():
        print(f"{Fore.MAGENTA}   [SongPass] {song_type} — {len(events_group)} satir{Style.RESET_ALL}")

        # Grubun tüm İngilizce satırlarını topla (cache key için)
        all_en_lines = []
        for ev in events_group:
            t = ev['parts'][9] if len(ev.get('parts', [])) > 9 else ''
            all_en_lines.append(_SONG_TAG_RE.sub('', t).strip().replace('\\N', ' ').replace('\\n', ' '))

        # ── CACHE HIT KONTROLU ──────────────────────────────────────────────
        _ckey = _make_song_cache_key(anime_title, season_num, all_en_lines, song_type=song_type)
        if _ckey in _song_cache:
            _cached    = _song_cache[_ckey]
            _ctr       = _cached.get('tr_lines', [])
            _cached_en = _cached.get('en_lines', [])

            # ── İÇERİK DOĞRULAMASI: satır sayısı + en_lines tam eşleşmesi ──
            # Cache'deki satırlar farklıysa (eski/kısmi kayıt) → miss say
            _line_ok  = (len(_ctr) == len(events_group))
            _en_match = (_cached_en == all_en_lines) if _cached_en else True  # eski kayıtlarda yoksa kabul
            if not _line_ok or not _en_match:
                _why = f"satır sayısı {len(_ctr)}≠{len(events_group)}" if not _line_ok else "en_lines içerik farkı"
                print(f"{Fore.YELLOW}   [SongCache] ⚠ {song_type} — cache uyumsuz ({_why}), yeniden çevriliyor{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}   [SongCache] ✅ {song_type} — Ep{_cached.get('source_ep','?')} cache'i kullanılıyor, API atlandı{Style.RESET_ALL}")
                try:
                    from notif_bus import push_notif as _pn
                    _pn('SongCache: sarki sozu cacheden yuklendi', 'positive')
                except Exception: pass
                _STATIC_C = re.compile(r'(\{(?:[^{}]*?(?:\\pos\(|\\an\d|\\1c|\\c&H)[^{}]*?)\})')
                for _ci, _cev in enumerate(events_group):
                    if _ci >= len(_ctr) or not _ctr[_ci]:
                        continue
                    _orig = _cev['parts'][9] if len(_cev.get('parts', [])) > 9 else ''
                    _spfx = ''
                    for _m in _STATIC_C.finditer(_orig):
                        if not re.search(r'\\t\(|\\blur|\\bord|\\move\(', _m.group(0), re.IGNORECASE):
                            _spfx += _m.group(0)
                    _cfinal = _spfx + _ctr[_ci]
                    if len(_cev.get('parts', [])) > 9:
                        _cev['parts'][9] = _cfinal
                    _cev['text'] = _cfinal
                    _cpev = _cev.get('_pysubs2_event') or _cev.get('_pysubs2_ev')
                    if _cpev is not None:
                        _cpev.text = _cfinal
                        total_fixed += 1
                continue  # Bu grup bitti — API'ye gitme
        # ────────────────────────────────────────────────────────────────────

        # CACHE MISS — API'den çevir, sonucu kaydet
        _group_tr_results = {}   # batch_offset → translated_clean_text
    # Özel şarkı sözü system prompt'u
        lyrics_system_prompt = (
            f"You are a professional anime song lyric translator specializing in Turkish localization.\n\n"
            f"ANIME: {ctx_str}\n"
            f"SONG TYPE: {song_type}\n\n"
            "TRANSLATION RULES:\n"
            "1. This is SONG LYRICS — translate POETICALLY, not literally.\n"
            "2. Maintain the emotional tone, rhythm feel, and poetic flow.\n"
            "3. Write natural Turkish — how real Turkish music fans would feel the song.\n"
            "4. Keep character names and honorifics (-san, -kun, -chan, etc.) unchanged.\n"
            "5. Very short lines (1-4 words): preserve their brevity in Turkish.\n"
            "6. NEVER refuse. NEVER add explanations. Just translate.\n"
            "7. Return ONLY the translated lines with [L1], [L2]... format. Nothing else.\n"
            "8. If a line is already in Turkish, return it unchanged."
        )

        # Batch olarak API'ye gönder (en fazla 30 satır)
        BATCH_SIZE = 30
        for batch_start in range(0, len(events_group), BATCH_SIZE):
            batch = events_group[batch_start:batch_start + BATCH_SIZE]

            # Çevrilecek metinleri hazırla
            lines_to_send   = []   # API'ye gidecek (romaji ayıklanmış) metinler
            _mixed_segments = []   # Her satır için segment listesi (romaji geri koymak için)
            _cur_style = batch[0]['parts'][3] if batch and len(batch[0].get('parts', [])) > 3 else ''

            for ev in batch:
                text = ev['parts'][9] if len(ev.get('parts', [])) > 9 else ''
                clean = _SONG_TAG_RE.sub('', text).strip().replace('\\N', ' ').replace('\\n', ' ')

                if _ignore_style_romaji and _ROMAJI_DETECTOR_OK:
                    # Karma satır → romaji ayıkla, sadece İngilizce kısmı gönder
                    segs = _rom_split_mixed(clean, _cur_style)
                    eng_only = ' '.join(t for l, t in segs if l == 'english').strip()
                    _mixed_segments.append(segs)
                    lines_to_send.append(eng_only if eng_only else clean)
                else:
                    _mixed_segments.append(None)
                    lines_to_send.append(clean)

            # ── [DEDUP] Aynı metni sadece 1 kez çevir, gerisine yay ────────────
            # Ana pipeline'daki mantığın aynısı: clean_text → tek API çağrısı
            # Kriterler:
            #   1. Aynı clean metin  → textual dedup
            #   2. Aynı start+end zamanı → timing dedup (JP+ROM multi-track)
            _song_dedup_map = {}   # clean_text → [batch_index, ...]
            _song_time_map  = {}   # (start, end) → [batch_index, ...]

            for _di, _dev in enumerate(batch):
                _dc = lines_to_send[_di]
                # Metin bazlı
                if _dc not in _song_dedup_map:
                    _song_dedup_map[_dc] = []
                _song_dedup_map[_dc].append(_di)
                # Zaman bazlı (aynı timing → multi-track satır)
                _dstart = _dev.get('parts', [None]*4)[1] if len(_dev.get('parts', [])) > 1 else None
                _dend   = _dev.get('parts', [None]*4)[2] if len(_dev.get('parts', [])) > 2 else None
                if _dstart is not None and _dend is not None:
                    _dtk = (_dstart, _dend)
                    if _dtk not in _song_time_map:
                        _song_time_map[_dtk] = []
                    _song_time_map[_dtk].append(_di)

            # Hangi indexler "birincil" (API'ye gidecek) vs "kopya" (broadcast alacak)?
            _primary_indices  = []   # API'ye gidecek unique indexler
            _copy_of          = {}   # copy_index → primary_index (metin dedup)
            _time_primary     = {}   # (start,end) → ilk karşılaşılan primary index

            _seen_texts = {}
            for _di in range(len(batch)):
                _dc = lines_to_send[_di]
                if _dc in _seen_texts:
                    # Metin kopyası → broadcast al
                    _copy_of[_di] = _seen_texts[_dc]
                else:
                    _seen_texts[_dc] = _di
                    _primary_indices.append(_di)

            # Timing dedup: aynı zamanlı birden fazla primary var mı?
            # (Örn: JP satırı + ROM satırı aynı start/end ama farklı metin)
            # Bu satırlarda sadece ilkini çevir (İngilizce olan), diğeri boş kalır
            for (_dtk, _dgroup) in _song_time_map.items():
                _dprims = [i for i in _dgroup if i in _primary_indices]
                if len(_dprims) > 1:
                    # İlk primary kalsın, diğerleri timing-kopya olsun
                    for _dp in _dprims[1:]:
                        if _dp not in _copy_of:
                            _copy_of[_dp] = _dprims[0]
                            _primary_indices.remove(_dp)

            _dedup_saved_song = len(batch) - len(_primary_indices)
            if _dedup_saved_song > 0:
                print(f"   [SongDedup] {_dedup_saved_song} tekrar satır atlandı → {len(_primary_indices)} unique API'ye gönderilecek")

            # Sadece primary indexleri gönder
            _primary_texts = [lines_to_send[i] for i in _primary_indices]
            # ──────────────────────────────────────────────────────────────────

            # Numara ile formatla: "[L1] satir\n[L2] satir\n..."
            numbered = '\n'.join(f'[L{i+1}] {line}' for i, line in enumerate(_primary_texts))

            try:
                # system_prompt'u geçici olarak şarkı sözü prompt'uyla değiştir
                _orig_prompt = translator.config.get('system_prompt', '')
                translator.config['system_prompt'] = lyrics_system_prompt

                import time as _time_mod

                # translate_batch — sadece unique satırları gönder
                response = translator.translate_batch(_primary_texts)

                # Orijinal prompt'u geri yükle
                translator.config['system_prompt'] = _orig_prompt

                if not response:
                    continue

                # Yanıtı parse et — translate_batch liste döndürür
                if isinstance(response, list):
                    # primary_indices sırasına göre map: primary_idx → çeviri
                    _primary_tr = {}
                    for _pi_pos, _pi_idx in enumerate(_primary_indices):
                        if _pi_pos < len(response) and response[_pi_pos] and response[_pi_pos].strip():
                            _primary_tr[_pi_idx] = response[_pi_pos]
                elif isinstance(response, str):
                    _primary_tr = {}
                    for match in re.finditer(r'\[L(\d+)\]\s*(.+?)(?=\[L\d+\]|$)', response, re.DOTALL):
                        _lpos = int(match.group(1)) - 1
                        _lt   = _SONG_PREFIX_RE.sub('', match.group(2).strip())
                        if _lt and _lpos < len(_primary_indices):
                            _primary_tr[_primary_indices[_lpos]] = _lt
                else:
                    continue

                # ── BROADCAST: kopya indexlere primary'nin çevirisini yay ──
                _all_tr = dict(_primary_tr)
                for _ci, _pi in _copy_of.items():
                    if _pi in _primary_tr:
                        _all_tr[_ci] = _primary_tr[_pi]

                # Her event'e yaz
                for i, ev in enumerate(batch):
                    if i not in _all_tr:
                        continue
                    translated = str(_all_tr[i]).strip()
                    translated = _SONG_PREFIX_RE.sub('', translated)
                    translated = re.sub(r'\[L\d+\]\s*', '', translated).strip()
                    if not translated:
                        continue

                    # Karma satır: romaji segmentlerini geri ekle
                    segs = _mixed_segments[i] if i < len(_mixed_segments) else None
                    if segs and any(l == 'romaji' for l, _ in segs):
                        translated = _rom_join_mixed(segs, translated)
                        print(f"     [MixedLine] Romaji geri eklendi: {repr(translated[:60])}")

                    # Tag yönetimi
                    orig_text = ev['parts'][9] if len(ev.get('parts', [])) > 9 else ''
                    _ANIM_TAG_RE = re.compile(
                        r'\{[^}]*(?:\\t\(|\\blur|\\bord|\\move\(|\\org\(|\\fad\(|\\fade\()[^}]*\}',
                        re.IGNORECASE
                    )
                    _STATIC_TAGS = re.compile(r'(\{(?:[^{}]*?(?:\\pos\(|\\an\d|\\1c|\\c&H)[^{}]*?)\})')
                    static_prefix = ''
                    for m in _STATIC_TAGS.finditer(orig_text):
                        if not re.search(r'\\t\(|\\blur|\\bord|\\move\(', m.group(0), re.IGNORECASE):
                            static_prefix += m.group(0)
                    final = static_prefix + translated

                    _is_broadcast = (i in _copy_of)
                    _tag = "📢 [broadcast]" if _is_broadcast else "✓"

                    if len(ev.get('parts', [])) > 9:
                        ev['parts'][9] = final
                    ev['text'] = final

                    _pev = ev.get('_pysubs2_event') or ev.get('_pysubs2_ev')
                    if _pev is not None:
                        _pev.text = final
                        total_fixed += 1
                        print(f"     {_tag} {repr(translated[:50])}")
                    else:
                        print(f"     ⚠ [SongPass] _pev=None, text='{final[:40]}' ev_keys={list(ev.keys())[:6]}")

                    # Cache için: global event index → temiz çeviri metni
                    _global_i = batch_start + i
                    _group_tr_results[_global_i] = translated

                _time_mod.sleep(0.5)


            except Exception as _e:
                translator.config['system_prompt'] = _orig_prompt
                print(f"{Fore.RED}   [SongPass] Batch hatasi: {_e}{Style.RESET_ALL}")

        # API bitti — grubu cache'e kaydet (en az 1 başarılı çeviri varsa)
        if _group_tr_results:
            import datetime
            _tr_lines_for_cache = [_group_tr_results.get(i, '') for i in range(len(events_group))]
            _song_cache[_ckey] = {
                'song_type':  song_type,
                'en_lines':   all_en_lines,          # İçerik doğrulama için saklanıyor
                'tr_lines':   _tr_lines_for_cache,
                'cached_at':  str(datetime.date.today()),
                'source_ep':  str(episode_num),
                'line_count': len(events_group),
            }
            _song_cache_dirty = True
            print(f"{Fore.CYAN}   [SongCache] 💾 {song_type} (Ep{episode_num}) — {len(events_group)} satır cache'lendi. Sonraki aynı sözlerı API'ye gitmeyecek{Style.RESET_ALL}")


    # Yeni cache entry'leri varsa diske yaz
    if _song_cache_dirty:
        _save_song_cache(_song_cache)

    # ── KARAOKE COLLAPSE PASS ────────────────────────────────────
    if _use_kara_collapse:
        kara_collapsed = _collapse_and_translate_karaoke(
            structured_events, translator, lyrics_system_prompt, ctx_str
        )
        if kara_collapsed > 0:
            print(f"{Fore.MAGENTA}   [KaraCollapse] {kara_collapsed} kara-satir coker edildi{Style.RESET_ALL}")
            try:
                from notif_bus import push_notif as _pn
                _pn(f'KaraCollapse: {kara_collapsed} karaoke satiri birlestirildi', 'info')
            except Exception: pass
            total_fixed += kara_collapsed
    else:
        print(f"{Fore.YELLOW}   [Motor] Karaoke Collapse KAPALI{Style.RESET_ALL}")
    # ─────────────────────────────────────────────────────────────

    return total_fixed


