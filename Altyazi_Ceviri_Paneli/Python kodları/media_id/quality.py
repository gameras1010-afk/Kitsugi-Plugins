"""
media_id/quality.py
===================
Altyazı kalite skoru ve çeviri bağlamı oluşturma.
"""
import os, re, sys, json, time, hashlib, threading
import requests
from typing import Optional
from media_id.constants import *

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
