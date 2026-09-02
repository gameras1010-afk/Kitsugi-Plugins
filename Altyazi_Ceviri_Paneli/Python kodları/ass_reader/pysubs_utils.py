"""
ass_reader/pysubs_utils.py
==========================
pysubs2 entegrasyon: build_structured_events, save, load.
"""
from ass_reader.reader import ASSFileReader
from typing import Optional, List, Dict, Tuple, Any, Union
import os, re, json


def _ms_to_ass_time(ms: int) -> str:
    """Millisaniyeyi ASS zaman formatına çevir: H:MM:SS.cc"""
    ms = max(0, int(ms))
    h = ms // 3_600_000;  ms %= 3_600_000
    m = ms // 60_000;     ms %= 60_000
    s = ms // 1_000;      ms %= 1_000
    cs = ms // 10          # centiseconds
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def pysubs2_event_to_parts(ev: 'pysubs2.SSAEvent') -> list:
    """
    pysubs2 SSAEvent'i subtitle_processor.py'nin beklediği 10-elemanlı
    parts[] listesine dönüştür.

    ASS Dialogue format:
      [0] Layer, [1] Start, [2] End, [3] Style, [4] Name,
      [5] MarginL, [6] MarginR, [7] MarginV, [8] Effect, [9] Text
    """
    return [
        str(ev.layer),                      # [0] Layer
        _ms_to_ass_time(ev.start),          # [1] Start
        _ms_to_ass_time(ev.end),            # [2] End
        ev.style,                           # [3] Style
        ev.name,                            # [4] Name (actor)
        f"{ev.marginl:04d}",                # [5] MarginL
        f"{ev.marginr:04d}",                # [6] MarginR
        f"{ev.marginv:04d}",                # [7] MarginV
        ev.effect if ev.effect else "",     # [8] Effect
        ev.text,                            # [9] Text (raw ASS)
    ]


def build_structured_events_pysubs2(
    filepath: str,
    font_size_mode: str = 'preserve',
    custom_font_size: int = 80,
) -> tuple:
    """
    subtitle_processor.py ile tam uyumlu event parse.

    pysubs2 ile dosyayı okur, kırılgan split(',', 9) yerine
    güvenilir parsing kullanır. Geriye tuple döner:

        (reader, lines_raw, header_str, styles_str, events_str,
         structured_parts_list, idx_style, idx_name, idx_text,
         format_line_string, encoding_used)

    'structured_parts_list' → subtitle_processor'ın for-loop'una
    verebileceğin, her biri 10-elemanlı list olan satır listesi.

    Bu fonksiyon subtitle_processor.py'nin events parsing kısmının
    (satır 1002-1013) tamamen yerini alır.
    """
    reader = ASSFileReader(filepath)
    subs   = reader._subs

    # Dosya içeriğini ham string olarak al (header/styles/events tekrar parse için)
    raw_content = subs.to_string('ass')
    raw_lines   = raw_content.splitlines()

    # Font boyutu modu — tüm stillere uygula
    if font_size_mode != 'preserve':
        reader.modify_all_styles_font_size(font_size_mode, custom_font_size)
        raw_content = subs.to_string('ass')
        raw_lines   = raw_content.splitlines()

    # Header / Styles / Events bölümlerini ayır (orijinal subtitle_processor mantığı)
    header_lines = []
    styles_lines = []
    events_lines = []
    section = "header"
    for line in raw_lines:
        ll = line.strip().lower()
        if ll == "[script info]":
            section = "header"; header_lines.append(line); continue
        elif ll in ("[v4+ styles]", "[styles]", "[v4 styles]"):
            section = "styles"; styles_lines.append(line); continue
        elif ll == "[events]":
            section = "events"; events_lines.append(line); continue
        if section == "header":   header_lines.append(line)
        elif section == "styles": styles_lines.append(line)
        elif section == "events": events_lines.append(line)

    # Format satırı oluştur (sabit ASS formatı)
    format_line = "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    idx_style = 3   # Format: Layer(0), Start(1), End(2), Style(3), ...
    idx_name  = 4
    idx_text  = 9

    # Her pysubs2 event'ini parts[] listesine dönüştür
    structured_parts = []
    for ev in subs:
        # pysubs2: Comment satırlarını da dahil et (subtitle_processor filtreler)
        parts = pysubs2_event_to_parts(ev)
        structured_parts.append({
            'parts': parts,
            'line': ev.type + ": " + ",".join(parts),  # Orijinal satır formatı
            'is_comment_event': (ev.type == 'Comment'),
            '_ev': ev,
        })

    return (
        reader,
        raw_lines,
        header_lines,
        styles_lines,
        events_lines,
        structured_parts,
        idx_style,
        idx_name,
        idx_text,
        format_line,
        reader.encoding,
    )


def pysubs2_save_from_structured(
    reader: 'ASSFileReader',
    structured_events: list,
    output_path: str,
    time_offset: float = 0.0,
):
    """
    subtitle_processor.py'nin sonunda yaptığı 'dosyayı yeniden oluştur + kaydet'
    işlemini pysubs2 üzerinden yapar.

    structured_events: subtitle_processor'ın structured_events listesi.
    Her item'de 'parts' key'i olmalı, parts[9] çevrilmiş text.
    """
    import pysubs2 as _p2
    from pysubs2.time import make_time

    subs = reader._subs

    # Structured events listesindeki part indeksleri
    # pysubs2 event listesi ile 1:1 eşleşmeli (reader._subs aynı sıradadır)
    ev_list = list(subs)

    for i, item in enumerate(structured_events):
        if i >= len(ev_list):
            break
        ev = ev_list[i]
        parts = item.get('parts', [])
        if len(parts) < 10:
            continue

        # Çevrilmiş metni uygula
        ev.text = parts[9]

        # Zaman offset
        if time_offset != 0.0:
            try:
                from subtitle_processor import parse_ass_time
                new_start = parse_ass_time(parts[1]) + time_offset
                new_end   = parse_ass_time(parts[2]) + time_offset
                ev.start  = max(0, int(new_start * 1000))
                ev.end    = max(0, int(new_end   * 1000))
            except Exception:
                pass

    subs.save(output_path, encoding='utf-8-sig')


# ─────────────────────────────────────────────────────────────────────────────
# Hızlı Kullanım Fonksiyonları
# ─────────────────────────────────────────────────────────────────────────────

def load_ass(filepath: str, encoding: str = 'utf-8-sig') -> ASSFileReader:
    """
    ASS dosyasını yükle ve ASSFileReader döndür.

    Kullanım:
        reader = load_ass("Oshi_no_Ko_S03E05.tr.ass")
        for event in reader.get_dialogue_events():
            print(event['style'], event['plaintext'])
    """
    return ASSFileReader(filepath, encoding=encoding)


def quick_event_stats(filepath: str) -> dict:
    """
    Dosya istatistiklerini hızlıca al (encoding sorunları için de kullanışlı).
    subtitle_processor.py'nin print istatistikleri ile uyumlu.
    """
    try:
        reader = load_ass(filepath)
        return {
            'total': len(reader),
            'dialogue': len(reader.get_dialogue_events()),
            'karaoke': len(reader.get_karaoke_events()),
            'drawing': len(reader.get_drawing_events()),
            'styles': reader.get_style_names(),
            'ok': True,
        }
    except Exception as e:
        return {'ok': False, 'error': str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# [Asama 2] Script Info Dogrulama & Margin Analizi
# ─────────────────────────────────────────────────────────────────────────────

def validate_script_info(reader_or_info) -> dict:
    """
    [Asama 2] ASS [Script Info] bolumunu dogrula.

    Kontrol edilen alanlar (libass/ass_types.h'den):
      - PlayResX / PlayResY : Koordinat sistemi — eksikse pos tagleri yanlis render edilir
      - WrapStyle           : 0/1/2/3 — gecersiz deger uyari
      - ScaledBorderAndShadow: yes/no — eksikse border/shadow farkli gorunebilir
      - YCbCr Matrix        : Renk uzayi header (TV.601/TV.709/None)
      - Language            : ISO-639-1 dil kodu

    Args:
        reader_or_info: ASSFileReader objesi VEYA dict (subs.info)

    Returns:
        {
          'ok': bool,
          'warnings': list[str],   -- onemli uyarilar (pipeline devam eder)
          'errors': list[str],     -- kritik sorunlar (pos koordinatlari bozuk olabilir)
          'info_snapshot': dict,   -- mevcut degerler
        }
    """
    # ASSFileReader veya dict kabul et
    info = reader_or_info.info if hasattr(reader_or_info, 'info') else reader_or_info

    warnings = []
    errors   = []

    # ── PlayResX / PlayResY ───────────────────────────────────────────────────
    play_x = info.get('PlayResX') or info.get('PlayreX') or ''
    play_y = info.get('PlayResY') or info.get('PlayreY') or ''

    if not play_x or not play_y:
        errors.append(
            "PlayResX/PlayResY eksik! \\pos, \\move, \\clip koordinatlari "
            "orijinal video cozunurlugune gore yanlis render edilebilir."
        )
    else:
        try:
            px, py = int(play_x), int(play_y)
            # Standart degerler: 1280x720, 1920x1080, 640x480, 1280x960
            KNOWN_RES = {(640,480),(1280,720),(1280,960),(1920,1080),(3840,2160)}
            if (px, py) not in KNOWN_RES:
                warnings.append(
                    f"PlayRes={px}x{py} standart disi — konumlandirma {px}x{py} "
                    f"koordinat sistemine gore yapilmis."
                )
        except ValueError:
            errors.append(f"PlayResX/PlayResY gecersiz format: '{play_x}' / '{play_y}'")

    # ── WrapStyle ────────────────────────────────────────────────────────────
    wrap = info.get('WrapStyle', '')
    if wrap != '':
        try:
            ws = int(wrap)
            if ws not in (0, 1, 2, 3):
                warnings.append(f"WrapStyle={ws} gecersiz (gecerli: 0/1/2/3)")
            elif ws == 2:
                warnings.append(
                    "WrapStyle=2 (sarma yok) — satirlar ekran sinirini asabilir. "
                    "Ceviri sonrasi auto_split devre disi olmali."
                )
        except ValueError:
            warnings.append(f"WrapStyle parcalanamadi: '{wrap}'")

    # ── ScaledBorderAndShadow ────────────────────────────────────────────────
    sbs = info.get('ScaledBorderAndShadow', '').strip().lower()
    if sbs not in ('yes', 'no', '1', '0', ''):
        warnings.append(f"ScaledBorderAndShadow='{sbs}' tanimsiz deger (yes/no bekleniyor)")

    # ── YCbCr Matrix ─────────────────────────────────────────────────────────
    ycbcr = info.get('YCbCr Matrix', '').strip()
    KNOWN_YCBCR = {'', 'None', 'TV.601', 'TV.709', 'PC.601', 'PC.709',
                   'TV.FCC', 'TV.240M', 'PC.FCC', 'PC.240M'}
    if ycbcr and ycbcr not in KNOWN_YCBCR:
        warnings.append(
            f"YCbCr Matrix='{ycbcr}' tanimsiz — renk donusumu yanlis olabilir."
        )

    # ── Language ─────────────────────────────────────────────────────────────
    lang = info.get('Language', '').strip()
    if lang and len(lang) > 5:
        warnings.append(f"Language='{lang}' cok uzun (ISO-639-1: 'tr', 'ja' vb.)")

    return {
        'ok': len(errors) == 0,
        'warnings': warnings,
        'errors': errors,
        'info_snapshot': {
            'PlayResX': play_x,
            'PlayResY': play_y,
            'WrapStyle': wrap,
            'ScaledBorderAndShadow': sbs,
            'YCbCr Matrix': ycbcr,
            'Language': lang,
        }
    }


def analyze_margin_positioning(event_dict: dict, play_res_x: int = 1280, play_res_y: int = 720) -> dict:
    """
    [Asama 2] Event'in margin degerlerini analiz ederek konumlandirma ipucu uretir.

    ASS'de margin, pozisyon belirlemenin iki yolundan biridir:
      - \\pos(x,y) tag'i ile (override, kesin konum)
      - MarginL/R/V ile (stil tabanli, pozisyon bolgesi)

    Bu fonksiyon: non-zero margin + pos tag icermeyen satirlari tespit eder.
    Bu satirlar "margin-positioned" kabul edilir → ceviri sonrasi dikkatli davranilmali.

    Returns:
        {
          'positioned': bool,    -- herhangi bir konumlandirma var mi?
          'has_pos_tag': bool,   -- \\pos/\\move tag'i var mi?
          'margin_override': bool, -- margin degerlerinden biri sifirdan farkli?
          'margin_l': int, 'margin_r': int, 'margin_v': int,
          'tip': str,            -- insan okunakli ipucu
        }
    """
    raw_text = event_dict.get('text', '') or event_dict.get('original_text', '') or ''
    margin_l = event_dict.get('margin_l', 0) or 0
    margin_r = event_dict.get('margin_r', 0) or 0
    margin_v = event_dict.get('margin_v', 0) or 0

    # \\pos veya \\move tag'i var mi?
    has_pos_tag = bool(
        re.search(r'\\(?:pos|move|org)\s*\(', raw_text)
    )

    # Margin override? (Her ikisi de 0 ise stil default marginini kullanir)
    margin_override = (margin_l != 0 or margin_r != 0 or margin_v != 0)

    positioned = has_pos_tag or margin_override

    # Ipucu olustur
    tip = ""
    if has_pos_tag and margin_override:
        tip = "Hem \\pos hem margin var — \\pos oncelikli"
    elif has_pos_tag:
        tip = "\\pos/\\move ile konumlandirilmis — ceviri metin uzunlugunu etkilemez"
    elif margin_override:
        tip = (f"Margin override: L={margin_l} R={margin_r} V={margin_v} — "
               f"metin uzunlugu degistikce konum kayabilir")
    else:
        tip = "Varsayilan konum (stil margin'i)"

    return {
        'positioned': positioned,
        'has_pos_tag': has_pos_tag,
        'margin_override': margin_override,
        'margin_l': margin_l,
        'margin_r': margin_r,
        'margin_v': margin_v,
        'tip': tip,
    }


# =============================================================================
# [Asama 3] Language Header Yazma
# =============================================================================

def write_language_header(reader: ASSFileReader, lang: str = 'tr') -> bool:
    """
    [Asama 3] Ceviri tamamlandiktan sonra [Script Info] bolumundeki
    Language alanini hedef dile guncelle.

    libass/ass_types.h: char *Language — zero-terminated ISO-639-1 code
    pysubs2: subs.info['Language'] = 'tr'

    Args:
        reader: ASSFileReader objesi (load edilmis, henuz kaydedilmemis)
        lang:   ISO-639-1 dil kodu (varsayilan: 'tr' — Türkçe)

    Returns:
        True: header yazildi, False: hata olustu

    Kullanim:
        write_language_header(reader, 'tr')   # .save() oncesi cagir
    """
    try:
        reader._subs.info['Language'] = lang
        reader.info['Language'] = lang          # local cache'i de güncelle
        return True
    except Exception:
        return False


# =============================================================================
# [Asama 3] Font Analizi (fonttools)
# =============================================================================

try:
    from fonttools.ttLib import TTFont as _TTFont
    _FONTTOOLS_OK = True
except ImportError:
    _TTFont = None
    _FONTTOOLS_OK = False


def analyze_fonts(
    reader: ASSFileReader,
    font_dirs: Optional[list] = None,
) -> dict:
    """
    [Asama 3] ASS dosyasinda kullanilan fontlari analiz et.

    Bu fonksiyon:
      1. Tum stillerdeki FontName degerlerini toplar
      2. Event satirlarindaki inline \\fn fontlari da cikartir
      3. Opsiyonel olarak font_dirs dizinlerinde arama yapar
      4. fonttools varsa: embeddable durumu, license flags kontrol eder

    Args:
        reader:    ASSFileReader objesi
        font_dirs: Font dosyalarinin aranacagi dizinler (orn: ['C:/Windows/Fonts'])

    Returns:
        {
          'fonts_in_styles':  list[str],   -- stillerde kullanilan font adlari
          'fonts_inline':     list[str],   -- \\fn tag ile inline kullanilan fontlar
          'all_fonts':        list[str],   -- tüm unique fontlar
          'found_files':      dict[str, str],  -- {font_adi: dosya_yolu}
          'missing_files':    list[str],   -- bulunamayan fontlar
          'embed_info':       dict[str, dict], -- fonttools ile analiz sonucu
          'fonttools_ok':     bool,        -- fonttools yüklü mü?
        }
    """
    import os
    import glob

    # ── 1. Stillerdeki fontlari topla ────────────────────────────────────────
    fonts_in_styles = []
    for style_name, style_info in reader.styles.items():
        fn = style_info.get('fontname', '')
        if fn and fn not in fonts_in_styles:
            fonts_in_styles.append(fn)

    # ── 2. Inline \\fn tag'lerini cikart ─────────────────────────────────────
    _FN_RE = re.compile(r'\\fn([^\\}]+)')
    fonts_inline = []
    for ev in reader.events:
        raw = ev.get('text', '')
        for m in _FN_RE.finditer(raw):
            fn = m.group(1).strip()
            if fn and fn not in fonts_inline:
                fonts_inline.append(fn)

    all_fonts = list(dict.fromkeys(fonts_in_styles + fonts_inline))  # Sira koru, unique

    # ── 3. Font dosyalarini ara ───────────────────────────────────────────────
    if font_dirs is None:
        # Windows default font dizinleri
        font_dirs = [
            r'C:\Windows\Fonts',
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Microsoft', 'Windows', 'Fonts'),
        ]

    found_files   = {}  # {font_adi_lower: dosya_yolu}
    missing_files = []

    for font_name in all_fonts:
        found = False
        fn_lower = font_name.lower().replace(' ', '')
        for fdir in font_dirs:
            if not os.path.isdir(fdir):
                continue
            # Tüm ttf/otf/ttc dosyalarini tara
            for ext in ('*.ttf', '*.otf', '*.ttc', '*.TTF', '*.OTF'):
                for fpath in glob.glob(os.path.join(fdir, ext)):
                    fbasename = os.path.splitext(os.path.basename(fpath))[0].lower().replace(' ', '')
                    if fn_lower in fbasename or fbasename in fn_lower:
                        found_files[font_name] = fpath
                        found = True
                        break
                if found:
                    break
            if found:
                break
        if not found:
            missing_files.append(font_name)

    # ── 4. fonttools ile embed analizi ───────────────────────────────────────
    embed_info = {}
    if _FONTTOOLS_OK:
        for font_name, fpath in found_files.items():
            try:
                tt = _TTFont(fpath)
                # OS/2 tablosunda fsEmbeddingType (embedding flags)
                os2 = tt.get('OS/2')
                flags = getattr(os2, 'fsType', None)
                embeddable = True
                flag_desc  = 'Embeddable'
                if flags is not None:
                    # Bit 1: No Embedding
                    if flags & 0x0002:
                        embeddable = False
                        flag_desc  = 'No Embedding (restricted)'
                    # Bit 2: Print & Preview only
                    elif flags & 0x0004:
                        flag_desc  = 'Print & Preview only'
                    # Bit 3: Editable embedding
                    elif flags & 0x0008:
                        flag_desc  = 'Editable Embedding OK'

                # Font ailesi adi
                name_table = tt.get('name')
                family = ''
                if name_table:
                    rec = name_table.getDebugName(1)   # nameID=1: Font Family
                    family = rec or ''

                embed_info[font_name] = {
                    'path':        fpath,
                    'embeddable':  embeddable,
                    'flag_desc':   flag_desc,
                    'fs_type':     flags,
                    'family':      family,
                }
                tt.close()
            except Exception as _fe:
                embed_info[font_name] = {
                    'path':       fpath,
                    'embeddable': None,
                    'flag_desc':  f'Analiz hatasi: {_fe}',
                    'fs_type':    None,
                    'family':     '',
                }

    return {
        'fonts_in_styles':  fonts_in_styles,
        'fonts_inline':     fonts_inline,
        'all_fonts':        all_fonts,
        'found_files':      found_files,
        'missing_files':    missing_files,
        'embed_info':       embed_info,
        'fonttools_ok':     _FONTTOOLS_OK,
    }
