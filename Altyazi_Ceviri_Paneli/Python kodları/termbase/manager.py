"""
termbase/manager.py
===================
consolidate, pre_translate vb.
"""
import os, re, json, time, threading
from typing import Optional, List

def _parse(response: str, terms: dict) -> dict:
    """'Terim = Ceviri' satirlarini parse eder. '?' donenleri EN=EN olarak birakir."""
    result = {cat: {} for cat in _CAT_LABELS}
    flat = {}
    for cat, tlist in terms.items():
        for t in tlist:
            flat[t.lower()] = (cat, t)

    if response:
        for line in response.splitlines():
            line = line.strip()
            if '=' not in line or line.startswith('#'):
                continue
            parts = line.split('=', 1)
            en_raw, tr_raw = parts[0].strip(), parts[1].strip()
            if en_raw.lower() not in flat:
                continue
            cat, orig = flat[en_raw.lower()]
            # "?" veya boş → çeviri yok, orijinalini kullan
            if tr_raw in ('?', '-', '—', '') or tr_raw == en_raw:
                result[cat][orig] = orig
            else:
                result[cat][orig] = tr_raw

    # Parse edilemeyenleri olduğu gibi bırak
    for cat, tlist in terms.items():
        for t in tlist:
            if t not in result.get(cat, {}):
                result.setdefault(cat, {})[t] = t

    return result


def consolidate_termbase_files(verbose: bool = True) -> None:
    """
    Scans the termbase directory, resolves all base and chars files to their canonical path,
    merges terms from redundant files into the canonical ones, and deletes redundant files.
    """
    if not os.path.isdir(TERMBASE_DIR):
        return

    # Process base files
    base_files = [f for f in os.listdir(TERMBASE_DIR) if f.endswith('_base.json')]
    for fname in base_files:
        path = os.path.join(TERMBASE_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_terms = meta.get('total_terms', sum(len(v) for v in data.get('terms', {}).values()) if 'terms' in data else 0)
            if total_terms == 0:
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Deleted empty base file: {fname}")
                continue
            anime_title = meta.get('anime')
            if not anime_title:
                anime_title = fname.replace("_base.json", "").replace("_", " ")
            
            # Resolve canonical path
            canonical = _base_path(anime_title)
            if os.path.abspath(path) != os.path.abspath(canonical):
                if verbose:
                    print(f"[Termbase Consolidation] Redundant base found: {fname} -> {os.path.basename(canonical)}")
                
                # Merge terms
                existing_canonical_data = {}
                if os.path.exists(canonical):
                    try:
                        with open(canonical, 'r', encoding='utf-8') as f:
                            existing_canonical_data = json.load(f)
                    except Exception:
                        pass
                
                canon_terms = existing_canonical_data.get('terms', {})
                redundant_terms = data.get('terms', {})
                
                # Deep merge terms
                for cat, terms_dict in redundant_terms.items():
                    if not isinstance(terms_dict, dict):
                        continue
                    canon_cat = canon_terms.setdefault(cat, {})
                    for en, tr in terms_dict.items():
                        if en not in canon_cat:
                            canon_cat[en] = tr
                
                # Save canonical
                meta_canon = existing_canonical_data.get('meta', {})
                clean_title, _ = _split_title_season(anime_title)
                meta_canon['anime'] = clean_title
                meta_canon['media_type'] = meta.get('media_type', meta_canon.get('media_type', 'anime'))
                meta_canon['translated_at'] = datetime.datetime.now().isoformat()
                meta_canon['type'] = 'base'
                total_terms_canon = sum(len(v) for v in canon_terms.values())
                meta_canon['total_terms'] = total_terms_canon
                
                if total_terms_canon > 0:
                    with open(canonical, 'w', encoding='utf-8') as f:
                        json.dump({'meta': meta_canon, 'terms': canon_terms}, f, ensure_ascii=False, indent=2)
                else:
                    if os.path.exists(canonical):
                        os.remove(canonical)
                
                # Delete redundant
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Merged and deleted redundant base file: {fname}")
        except Exception as e:
            if verbose:
                print(f"[Termbase Consolidation] Error merging {fname}: {e}")

    # Process character files — hepsini franchise başına TEK _chars.json'a birleştir
    char_files = [f for f in os.listdir(TERMBASE_DIR) if f.endswith('_chars.json')]
    for fname in char_files:
        path = os.path.join(TERMBASE_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_chars = meta.get('total_chars', len(data.get('characters', {})) if 'characters' in data else 0)
            if total_chars == 0:
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Deleted empty chars file: {fname}")
                continue
            anime_title = meta.get('anime')
            if not anime_title:
                # Dosya adından tahmin et (sezon suffix'ini sil)
                clean_fn = re.sub(r'(_s\d+)?_chars\.json$', '', fname, flags=re.IGNORECASE)
                anime_title = clean_fn.replace('_', ' ')

            # Canonical: sezon tag YOK
            canonical = _chars_path(anime_title)   # sezon argümanı geçilmiyor
            if os.path.abspath(path) != os.path.abspath(canonical):
                if verbose:
                    print(f"[Termbase Consolidation] Chars birleştiriliyor: {fname} → {os.path.basename(canonical)}")

                # Mevcut canonical'i oku
                canon_chars = {}
                if os.path.exists(canonical):
                    try:
                        with open(canonical, 'r', encoding='utf-8') as f:
                            canon_chars = json.load(f).get('characters', {})
                    except Exception:
                        pass

                # Sadece eksik karakterleri ekle
                added = 0
                for en, tr in data.get('characters', {}).items():
                    if en not in canon_chars:
                        canon_chars[en] = tr
                        added += 1

                clean_title, _ = _split_title_season(anime_title)
                total_chars_canon = len(canon_chars)
                if total_chars_canon > 0:
                    with open(canonical, 'w', encoding='utf-8') as f:
                        json.dump({
                            'meta': {
                                'anime': clean_title,
                                'translated_at': datetime.datetime.now().isoformat(),
                                'type': 'chars',
                                'total_chars': total_chars_canon,
                            },
                            'characters': canon_chars,
                        }, f, ensure_ascii=False, indent=2)
                else:
                    if os.path.exists(canonical):
                        os.remove(canonical)

                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] {added} karakter eklendi, redundant silindi: {fname}")
        except Exception as e:
            if verbose:
                print(f"[Termbase Consolidation] Chars merge hatası {fname}: {e}")

    # General cleanup: delete any json file in TERMBASE_DIR that has 0 terms or 0 characters
    for fname in os.listdir(TERMBASE_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(TERMBASE_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_terms = meta.get('total_terms', 0)
            total_chars = meta.get('total_chars', 0)
            is_base = meta.get('type') == 'base' or fname.endswith('_base.json')
            is_chars = meta.get('type') == 'chars' or fname.endswith('_chars.json')
            
            if is_base:
                t_count = sum(len(v) for v in data.get('terms', {}).values()) if 'terms' in data else 0
                if t_count == 0 or total_terms == 0:
                    os.remove(path)
                    if verbose:
                        print(f"[Termbase Consolidation] Cleaned up empty base file: {fname}")
            elif is_chars:
                c_count = len(data.get('characters', {})) if 'characters' in data else 0
                if c_count == 0 or total_chars == 0:
                    os.remove(path)
                    if verbose:
                        print(f"[Termbase Consolidation] Cleaned up empty chars file: {fname}")
        except Exception:
            pass


# ─── Ana Fonksiyonlar ─────────────────────────────────────────────────────────

def pre_translate_terms(
    anime_title: str,
    media_type: str = 'anime',
    season_num: int = None,
    season_title: str = None,
    force_refresh: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Anime/dizi/film icin on-ceviri yapar.

    YAPI:
      - _base.json       : skills/locations/orgs/items/terminology (tüm sezonlar paylaşır)
      - _s{n}_chars.json : sezona özel karakterler (Jikan)

    Karakterler Gemini'ye gönderilmez — olduğu gibi kaydedilir (Kirito→Kirito).
    Non-karakter base zaten varsa ve force_refresh değilse cache'den okunur.
    """
    # 0. Diskteki eski/mükerrer sezon dosyalarını tek canonical'e birleştir
    consolidate_termbase_files(verbose=verbose)

    clean_title, _sn = _split_title_season(anime_title)

    base_path  = _base_path(anime_title)
    chars_path = _chars_path(anime_title)   # ← sezon tag YOK, franchise başına tek dosya

    # ── 1. BASE (non-karakter) — Her zaman Fandom'a bak, sadece YENİ terimleri çevir ──
    # Mevcut çevirileri oku (varsa)
    existing_base_terms = {}
    if os.path.exists(base_path):
        try:
            existing_base_terms = json.load(open(base_path, 'r', encoding='utf-8')).get('terms', {})
        except Exception:
            pass

    if verbose and existing_base_terms:
        total_ex = sum(len(v) for v in existing_base_terms.values())
        print(f'[Termbase] Mevcut base: {total_ex} terim okundu → {os.path.basename(base_path)}')

    if True:  # Her zaman Fandom'a bak — _fresh kontrolü kasıtlı kaldırıldı
        # Load all candidate terms from Fandom cache/API
        terms_by_cat = {}
        metadata = {}
        try:
            from fandom_glossary import _load_cache
            cache = _load_cache()
            _search = clean_title.lower().strip()
            candidates = []
            for k in cache:
                base_k, _ = _split_title_season(k)
                if base_k.lower().strip() == _search:
                    candidates.append(k)
            # Select the entry with the most terms
            best_key = max(candidates,
                key=lambda k: sum(len(v) for v in cache[k].get('terms', {}).values()),
                default=None
            ) if candidates else None

            if best_key:
                raw_terms = cache[best_key].get('terms', {})
                metadata = cache[best_key].get('metadata', {})
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    lst = raw_terms.get(cat, [])
                    if lst:
                        terms_by_cat[cat] = lst
                if verbose:
                    total_raw = sum(len(v) for v in terms_by_cat.values())
                    print(f'[Termbase] Cache\'den {total_raw} terim alındı (tüm kategoriler)')
            else:
                # Fallback: build_glossary
                from fandom_glossary import build_glossary
                entry = build_glossary(anime_title, verbose=False, season_num=season_num, media_type=media_type)
                all_terms = entry.get("terms", {}) if entry else {}
                metadata = entry.get("metadata", {}) if entry else {}
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    if all_terms.get(cat):
                        terms_by_cat[cat] = all_terms[cat]
        except Exception as e:
            if verbose:
                print(f'[Termbase] Fandom hatasi: {e}')
            try:
                from fandom_glossary import build_glossary
                entry = build_glossary(anime_title, verbose=False, season_num=season_num, media_type=media_type)
                all_terms = entry.get("terms", {}) if entry else {}
                metadata = entry.get("metadata", {}) if entry else {}
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    if all_terms.get(cat):
                        terms_by_cat[cat] = all_terms[cat]
            except Exception:
                pass

        # Identify new terms (incremental translation check)
        new_terms_by_cat = {}
        for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
            tlist = terms_by_cat.get(cat, [])
            existing_cat = existing_base_terms.get(cat, {})
            # Only keep terms not already translated in base
            new_list = [t for t in tlist if t not in existing_cat]
            if new_list:
                new_terms_by_cat[cat] = new_list

        total_new = sum(len(v) for v in new_terms_by_cat.values())
        if verbose:
            print(f'[Termbase] {anime_title}: Toplam {sum(len(v) for v in terms_by_cat.values())} terimden {total_new} tanesi yeni ve ceviriliyor...')

        merged = {cat: dict(existing_base_terms.get(cat, {})) for cat in _CAT_LABELS}

        if total_new:
            # Batch: max 60 terms per request
            BATCH = 60
            flat_new = [(cat, t) for cat, lst in new_terms_by_cat.items() for t in lst]
            batches = [flat_new[i:i+BATCH] for i in range(0, len(flat_new), BATCH)]

            _km = _make_keymanager()

            for bi, batch in enumerate(batches):
                b_by_cat = {}
                for cat, t in batch:
                    b_by_cat.setdefault(cat, []).append(t)
                if verbose:
                    b_total = sum(len(v) for v in b_by_cat.values())
                    print(f'[Termbase] Batch {bi+1}/{len(batches)}: {b_total} yeni terim...')
                prompt = _build_prompt(anime_title, media_type, season_num, b_by_cat, metadata=metadata)
                response = _call_api_with_keymanager(prompt, km=_km)
                batch_result = _parse(response, b_by_cat) if response else \
                               {cat: {t: t for t in lst} for cat, lst in b_by_cat.items()}
                for cat, mapping in batch_result.items():
                    merged.setdefault(cat, {}).update(mapping)

        # For terms that didn't get translated, fall back to self if not already in merged
        for cat in _CAT_LABELS:
            tlist = terms_by_cat.get(cat, [])
            cat_dict = merged.setdefault(cat, {})
            for t in tlist:
                if t not in cat_dict:
                    cat_dict[t] = t

        base_terms = merged

        # ── Manuel override'ları uygula ({safe}_overrides.json) ──────────────
        _safe_ov = re.sub(r'[^a-z0-9]', '_', clean_title.lower())[:50].rstrip('_')
        _ov_path = os.path.join(TERMBASE_DIR, f'{_safe_ov}_overrides.json')
        if os.path.exists(_ov_path):
            try:
                overrides = json.load(open(_ov_path, encoding='utf-8'))
                ov_applied = 0
                for cat, fixes in overrides.items():
                    for en, tr in fixes.items():
                        if en in base_terms.get(cat, {}):
                            base_terms[cat][en] = tr
                            ov_applied += 1
                if verbose and ov_applied:
                    print(f'[Termbase] {ov_applied} manuel override uygulandı.')
            except Exception as e:
                if verbose:
                    print(f'[Termbase] Override okuma hatası: {e}')

        # Base'i kaydet (Clean franchise title'ı meta.anime olarak kullan)
        try:
            total_out = sum(len(v) for v in base_terms.values())
            if total_out > 0:
                json.dump(
                    {
                        'meta': {
                            'anime': clean_title, 'media_type': media_type,
                            'translated_at': datetime.datetime.now().isoformat(),
                            'total_terms': total_out, 'type': 'base',
                        },
                        'terms': base_terms,
                    },
                    open(base_path, 'w', encoding='utf-8'),
                    ensure_ascii=False, indent=2,
                )
                if verbose:
                    print(f'[Termbase] Base kaydedildi: {total_out} terim → {os.path.basename(base_path)}')
            else:
                if os.path.exists(base_path):
                    os.remove(base_path)
                    if verbose:
                        print(f'[Termbase] Boş base dosyası silindi: {os.path.basename(base_path)}')
        except Exception as e:
            if verbose:
                print(f'[Termbase] Base kayit hatasi: {e}')

    # ── 2. KARAKTERLER — franchise başına TEK dosyaya merge ────────────────────
    # a) Mevcut karakter dosyasını oku
    existing_chars = {}
    if os.path.exists(chars_path):
        try:
            existing_chars = json.load(open(chars_path, 'r', encoding='utf-8')).get('characters', {})
            if verbose and existing_chars:
                print(f'[Termbase] Mevcut karakterler: {len(existing_chars)} → {os.path.basename(chars_path)}')
        except Exception:
            pass

    # b) Yeni karakterleri API'den çek
    new_chars_raw = {}
    _is_western = (media_type == 'series')
    try:
        from fandom_glossary import _jikan_get_characters, _load_cache
        if not _is_western:
            _jikan_chars = _jikan_get_characters(
                season_title=season_title or anime_title,
                series_title=anime_title if season_title else None,
            )
            if _jikan_chars:
                new_chars_raw = {c: c for c in _jikan_chars}
                if verbose:
                    print(f'[Termbase] Jikan: {len(new_chars_raw)} karakter alındı')
        else:
            # Batı dizisi → Fandom cache
            _gloss_cache = _load_cache()
            _search = clean_title.lower().strip()
            for k, v in _gloss_cache.items():
                base_k, _ = _split_title_season(k)
                if base_k.lower().strip() == _search and v.get('terms', {}).get('characters'):
                    new_chars_raw = {c: c for c in v['terms']['characters']}
                    if verbose:
                        print(f'[Termbase] Fandom cache: {len(new_chars_raw)} karakter')
                    break
    except Exception as e:
        if verbose:
            print(f'[Termbase] Karakter cekme hatasi: {e}')

    # c) Sadece EKSİK karakterleri mevcut listeye ekle
    added = 0
    for name, val in new_chars_raw.items():
        if name not in existing_chars:
            existing_chars[name] = val
            added += 1

    chars_as_is = existing_chars

    if verbose and added:
        print(f'[Termbase] {added} yeni karakter eklendi → toplam {len(chars_as_is)}')
    elif verbose and not added and chars_as_is:
        print(f'[Termbase] Karakter değişikliği yok — {len(chars_as_is)} karakter mevcut')

    # d) Kaydet (her zaman — yeni karakter eklenmese bile meta güncellenir)
    if chars_as_is and len(chars_as_is) > 0:
        try:
            json.dump(
                {
                    'meta': {
                        'anime': clean_title,
                        'translated_at': datetime.datetime.now().isoformat(),
                        'type': 'chars',
                        'total_chars': len(chars_as_is),
                    },
                    'characters': chars_as_is,
                },
                open(chars_path, 'w', encoding='utf-8'),
                ensure_ascii=False, indent=2,
            )
            if verbose:
                print(f'[Termbase] Karakter dosyası güncellendi: {len(chars_as_is)} → {os.path.basename(chars_path)}')
        except Exception as e:
            if verbose:
                print(f'[Termbase] Karakter kayit hatasi: {e}')
    else:
        try:
            if os.path.exists(chars_path):
                os.remove(chars_path)
                if verbose:
                    print(f'[Termbase] Boş karakter dosyası silindi: {os.path.basename(chars_path)}')
        except Exception:
            pass

    # ── 3. Birleştir ve döndür ──────────────────────────────────────────────────
    result = dict(base_terms)
    if chars_as_is:
        result['characters'] = chars_as_is
    return result


def get_termbase_tr_list(
    anime_title: str,
    season_num: int = None,
    include_characters: List[str] = None,
) -> str:
    """
    Altyazi cevirisi icin prompt blogu olusturur.
    Non-karakter terimler _base.json'dan, karakterler _chars.json'dan gelir.
    """
    # Base terimler (tum sezonlar icin ortak)
    terms = {}
    base_p = _base_path(anime_title)
    if os.path.exists(base_p):
        try:
            terms = json.load(open(base_p, 'r', encoding='utf-8')).get('terms', {})
        except Exception:
            pass

    # Karakterler: oncelik _chars.json, yoksa include_characters fallback
    chars_dict = {}
    chars_p = _chars_path(anime_title, season_num)
    if os.path.exists(chars_p):
        try:
            chars_dict = json.load(open(chars_p, 'r', encoding='utf-8')).get('characters', {})
        except Exception:
            pass
    all_chars = list(chars_dict.values()) or (include_characters or [])

    if not terms and not all_chars:
        return ''

    lines = ['─── ONAYLANMIŞ TERİMLER (bu listedeki terimleri kullan) ───']
    short_cats = {
        'skills':        'Yetenekler',
        'locations':     'Lokasyonlar',
        'organizations': 'Organizasyonlar',
        'items':         'Eşyalar',
        'terminology':   'Ozel Terimler',
    }
    for cat, label in short_cats.items():
        vals = list(terms.get(cat, {}).values())
        if vals:
            lines.append(f'{label}: {", ".join(vals)}')
    if all_chars:
        lines.append(f'Karakterler: {", ".join(all_chars)}')
    lines.append('─────────────────────────────────────────────────────────')
    return '\n'.join(lines)


def load_termbase(anime_title: str, season_num: int = None) -> dict:
    """Termbase'i diskten yukler (base + chars birlestirerek). Yoksa bos dict doner."""
    result = {}
    # Base terimler
    base_p = _base_path(anime_title)
    if os.path.exists(base_p):
        try:
            result.update(json.load(open(base_p, 'r', encoding='utf-8')).get('terms', {}))
        except Exception:
            pass
    # Karakterler
    chars_p = _chars_path(anime_title, season_num)
    if os.path.exists(chars_p):
        try:
            result['characters'] = json.load(open(chars_p, 'r', encoding='utf-8')).get('characters', {})
        except Exception:
            pass
    return result


def delete_termbase(anime_title: str, season_num: int = None) -> bool:
    """Termbase dosyalarini siler (base + chars)."""
    deleted = False
    for p in [_base_path(anime_title), _chars_path(anime_title, season_num)]:
        if os.path.exists(p):
            try:
                os.remove(p)
                deleted = True
            except Exception:
                pass
    return deleted


def list_termbases() -> List[dict]:
    """Tum termbase dosyalarini listeler (base ve chars ayri gosterilir)."""
    os.makedirs(TERMBASE_DIR, exist_ok=True)
    result = []
    for fname in os.listdir(TERMBASE_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(TERMBASE_DIR, fname)
        try:
            data = json.load(open(fpath, 'r', encoding='utf-8'))
            meta = data.get('meta', {})
            file_type = meta.get('type', 'legacy')  # 'base', 'chars', 'legacy'
            if file_type == 'chars':
                total = len(data.get('characters', {}))
            else:
                total = sum(len(v) for v in data.get('terms', {}).values())
            age = (time.time() - os.path.getmtime(fpath)) / 86400
            result.append({
                'file':         fname,
                'anime':        meta.get('anime', fname),
                'season':       meta.get('season'),
                'type':         file_type,
                'total_terms':  total,
                'translated_at': meta.get('translated_at', ''),
                'age_days':     round(age, 1),
                'fresh':        age < TERMBASE_TTL,
            })
        except Exception:
            pass
    return sorted(result, key=lambda x: (x['anime'], x.get('type', '')))


# ─── CLI Test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    title = sys.argv[1] if len(sys.argv) > 1 else 'Sword Art Online'
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(f'=== Termbase pre-ceviri: {title} S{season} ===')
    result = pre_translate_terms(title, season_num=season, verbose=True)
    for cat, mapping in result.items():
        print(f'\n{cat.upper()} ({len(mapping)}):')
        for en, tr in list(mapping.items())[:5]:
            arrow = '(degismedi)' if en == tr else f'→ {tr}'
            print(f'  {en} {arrow}')
    print('\n=== Prompt blogu ===')
    chars = ['Kirito', 'Asuna', 'Alice']
    print(get_termbase_tr_list(title, season, include_characters=chars))
