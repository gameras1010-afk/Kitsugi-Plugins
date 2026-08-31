import re
"""
subtitle_validator.py
=====================
ASS altyazi kalite dogrulama motoru — Nexus Pro Translation Engine

Asama 1 icerigi:
  1. CPS (Characters Per Second) — okuma hizi dogrulama
  2. CPL (Characters Per Line) — satir basina karakter limiti
  3. effect alani — Banner/Scroll efekti tespit (credits roll)
  4. actor (name) alani — Karakter adi extraction

Kullanim:
  from subtitle_validator import SubtitleValidator
  v = SubtitleValidator()
  result = v.validate_event(event_dict)  -> ValidationResult
  report = v.validate_all(event_list)    -> list[ValidationResult]

Kalite esikleri (anime fansub standardi):
  CPS opt: 12-17  / uyari: 20 / kritik: 25
  CPL max: 42     / hard limit: 47
  Satir:   max 2  (nadiren 3 tolere edilir)
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional

# ── Tag silme pattern (her yerde kullanilir) ─────────────────────────────────
_TAG_RE        = re.compile(r'\{[^}]*\}')
_NEWLINE_RE    = re.compile(r'\\N|\\n')    # \N ve \n → satir kesimi
_HARDSPACE_RE  = re.compile(r'\\h')        # \h → bosluk

# ── [Asama 2] Renk kodu pattern — ASS BGR formati: &HBBGGRR& ─────────────────
# ASS rengi HTML'in tersi: &H<BB><GG><RR>&  (ALPHA icin: &HAA<BB><GG><RR>&)
_COLOR_RE      = re.compile(r'&H[0-9A-Fa-f]{6,8}&')

# ── Banner/Scroll effect pattern ─────────────────────────────────────────────
# ASS Effect alani: "Banner;<delay>;..." veya "Scroll up;<y1>;..."
_BANNER_RE  = re.compile(r'^banner\b', re.IGNORECASE)
_SCROLL_RE  = re.compile(r'^scroll\s+(up|down)\b', re.IGNORECASE)

# ── CPS/CPL esikleri ─────────────────────────────────────────────────────────
CPS_OPTIMAL_MAX  = 17    # Rahat okuma: <= 17
CPS_WARN_MAX     = 22    # Uyari esigi: <= 22
CPS_CRITICAL_MAX = 27    # Kritik esik: > 27 → retry/kisat

CPL_STANDARD_MAX = 42   # Standart limit
CPL_HARD_MAX     = 47   # Mutlak hard limit
LINE_COUNT_MAX   = 2    # Maksimum satir sayisi


@dataclass
class ValidationResult:
    """Tek bir event icin dogrulama sonucu."""
    event_idx: int = 0
    original_text: str = ""
    plain_text: str = ""         # Tag'ler temizlenmis metin

    # CPS
    cps: float = 0.0
    duration_ms: int = 0
    cps_ok: bool = True
    cps_warning: bool = False
    cps_critical: bool = False

    # CPL
    line_count: int = 0
    max_cpl: int = 0
    cpl_ok: bool = True
    cpl_warning: bool = False

    # Effect (Banner/Scroll)
    has_banner_effect: bool = False
    has_scroll_effect: bool = False

    # Actor
    actor: str = ""

    # [Asama 2] Renk kodlari
    color_codes: List[str] = field(default_factory=list)   # orijinal renk kodlari
    colors_preserved: bool = True                           # ceviri sonrasi korundu mu?
    missing_colors: List[str] = field(default_factory=list)

    # [Asama 2] Margin & konum
    margin_override: bool = False   # Non-zero margin var mi?
    has_pos_tag: bool = False       # \pos/\move tag'i var mi?

    # Genel
    issues: List[str] = field(default_factory=list)

    @property
    def is_scroll_credits(self) -> bool:
        """Banner veya Scroll → credits satiri."""
        return self.has_banner_effect or self.has_scroll_effect

    @property
    def has_any_issue(self) -> bool:
        return bool(self.issues)

    @property
    def severity(self) -> str:
        """critical | warning | ok"""
        if self.cps_critical or (self.has_banner_effect or self.has_scroll_effect):
            return 'critical'
        if self.cps_warning or self.cpl_warning:
            return 'warning'
        return 'ok'


def strip_ass_tags(text: str) -> str:
    """Ham ASS metninden tum override tagleri temizle."""
    clean = _TAG_RE.sub('', text)
    # \N \n → bosluk (satir sayisi icin kendiliginden korunur)
    clean = _HARDSPACE_RE.sub(' ', clean)
    return clean


def split_ass_lines(text_no_tags: str) -> List[str]:
    r"""
    \\N ve \\n tag'lerine gore satirlara bol.
    Asil metinden onceden tagleri silmis olmalisin.
    """
    parts = _NEWLINE_RE.split(text_no_tags)
    return [p.strip() for p in parts if p.strip()]


def calculate_cps(plain_text: str, duration_ms: int) -> float:
    r"""
    Saniye basina karakter (CPS) hesapla.
    plain_text: Tag'ler temizlenmis, \\N \\n \\h kaldirilmis metin.
    """
    if duration_ms <= 0:
        return 0.0
    # Satir kesimlerini ve hard-space'i kaldir, saf karakter say
    clean = _NEWLINE_RE.sub('', plain_text)
    clean = _HARDSPACE_RE.sub('', clean)
    chars = len(clean.strip())
    return chars / (duration_ms / 1000.0)


def validate_event(
    event_dict: dict,
    event_idx: int = 0,
    cps_critical_max: int = CPS_CRITICAL_MAX,
    cps_warn_max: int     = CPS_WARN_MAX,
    cpl_hard_max: int     = CPL_HARD_MAX,
    cpl_std_max: int      = CPL_STANDARD_MAX,
    line_count_max: int   = LINE_COUNT_MAX,
) -> ValidationResult:
    """
    Tek bir event_dict'i dogrula.

    event_dict en azindan sunlari icermeli:
      'text'        -> ham ASS metni (taglar dahil) — VEYA ceviri sonrasi metin
      'duration_ms' -> milisaniye olarak sure (yoksa parts[1]/parts[2]'den hesaplanir)
      'parts'       -> [Layer, Start, End, Style, Name, ML, MR, MV, Effect, Text]
      'actor'       -> karakter adi (Opsiyonel, parts[4]'ten de okunabilir)

    Returns: ValidationResult
    """
    result = ValidationResult(event_idx=event_idx)

    # ── Metni cek ─────────────────────────────────────────────────────────────
    raw_text = event_dict.get('text', '') or ''
    result.original_text = raw_text[:200]

    # ── Parts'tan ek bilgi al ────────────────────────────────────────────────
    parts = event_dict.get('parts', [])

    # Actor (karakter adi)
    actor = event_dict.get('actor', '')
    if not actor and len(parts) > 4:
        actor = parts[4] or ''
    result.actor = actor.strip()

    # Effect alani
    effect = event_dict.get('effect', '')
    if not effect and len(parts) > 8:
        effect = parts[8] or ''
    effect = (effect or '').strip()

    # ── Effect Kontrolu (Banner / Scroll) ────────────────────────────────────
    if effect:
        if _BANNER_RE.match(effect):
            result.has_banner_effect = True
            result.issues.append(f"Banner efekti: credits/staff roll satiri → atla")
        elif _SCROLL_RE.match(effect):
            result.has_scroll_effect = True
            result.issues.append(f"Scroll efekti: kayan credits → atla")

    # ── Sure hesapla ─────────────────────────────────────────────────────────
    duration_ms = event_dict.get('duration_ms', 0)
    if not duration_ms and len(parts) > 2:
        # parts[1]=Start, parts[2]=End → milisaniyeye cevir
        duration_ms = _ass_time_to_ms(parts[2]) - _ass_time_to_ms(parts[1])
    result.duration_ms = max(0, duration_ms)

    # ── Plain text uret ──────────────────────────────────────────────────────
    plain = strip_ass_tags(raw_text)
    result.plain_text = plain

    # ── Satir bolumleri ──────────────────────────────────────────────────────
    lines = split_ass_lines(plain)
    result.line_count = max(1, len(lines))

    # ── CPS Hesapla ──────────────────────────────────────────────────────────
    cps = calculate_cps(plain, result.duration_ms)
    result.cps = round(cps, 2)

    if result.duration_ms > 0:
        if cps > cps_critical_max:
            result.cps_ok = False
            result.cps_critical = True
            result.cps_warning = True
            result.issues.append(
                f"CPS kritik: {cps:.1f} (max {cps_critical_max}) — satir cok hizli"
            )
        elif cps > cps_warn_max:
            result.cps_ok = False
            result.cps_warning = True
            result.issues.append(
                f"CPS uyari: {cps:.1f} (max {cps_warn_max})"
            )

    # ── CPL Kontrolu ─────────────────────────────────────────────────────────
    if lines:
        max_line_len = max(len(ln) for ln in lines)
        result.max_cpl = max_line_len

        if max_line_len > cpl_hard_max:
            result.cpl_ok = False
            result.cpl_warning = True
            result.issues.append(
                f"CPL kritik: {max_line_len} karakter (max {cpl_hard_max})"
            )
        elif max_line_len > cpl_std_max:
            result.cpl_warning = True
            result.issues.append(
                f"CPL uzun: {max_line_len} karakter (standart {cpl_std_max})"
            )

    # Satir sayisi
    if result.line_count > line_count_max:
        result.cpl_warning = True
        result.issues.append(
            f"Cok fazla satir: {result.line_count} (max {line_count_max})"
        )

    return result


def validate_all(
    event_list: list,
    cps_critical_max: int = CPS_CRITICAL_MAX,
) -> List[ValidationResult]:
    """
    Tum event listesini dogrula. ValidationResult listesi dondurur.
    Sadece issues icerenleri loglamak icin:
        [r for r in results if r.has_any_issue]
    """
    results = []
    _SIGNS_STYLE_RE = re.compile(
        r'(?i)^(?:signs?|ts|typeset|screen|insert|ins\b|fx\b|effect|overlay|watermark|title|credit)',
    )
    for i, ev in enumerate(event_list):
        if ev.get('skip_translation'):
            continue  # Atlanan satirlari dogrulama (junk/kara/draw)
        # [FIX] Signs/typesetting satirlari CPS/CPL dogrulamasindan hariç tut
        # Bu satirlar cok kisa sureli animasyon katmanlaridir — yüksek CPS normaldir.
        _style = ev.get('style', '') or ''
        _reason = ev.get('reason', '') or ''
        if _SIGNS_STYLE_RE.match(_style) or _reason in ('sign', 'typeset', 'drawing'):
            continue  # Signs/typeset = CPS dogrulamaya dahil etme
        # Drawing satiri ise de dahil etme
        _raw = ev.get('text', '') or ''
        if re.search(r'\\\\p[1-9]', _raw):
            continue  # Drawing mode satiri
        r = validate_event(ev, event_idx=i, cps_critical_max=cps_critical_max)
        results.append(r)
    return results


def summarize_validation(results: List[ValidationResult]) -> dict:
    """
    Dogrulama sonuclarini ozetle.
    Returns: dict with counts and lists
    """
    total = len(results)
    warnings   = [r for r in results if r.cps_warning or r.cpl_warning]
    criticals  = [r for r in results if r.cps_critical]
    scrolls    = [r for r in results if r.is_scroll_credits]
    with_actor = [r for r in results if r.actor]

    return {
        'total':         total,
        'warnings':      len(warnings),
        'criticals':     len(criticals),
        'scroll_credits': len(scrolls),
        'with_actor':    len(with_actor),
        'avg_cps':       round(sum(r.cps for r in results) / total, 2) if total else 0,
        'max_cps':       round(max((r.cps for r in results), default=0), 2),
        'max_cpl':       max((r.max_cpl for r in results), default=0),
        'details_warn':  [r for r in results if r.has_any_issue][:50],
    }


# ── Yardimci: ASS zaman → ms ─────────────────────────────────────────────────
def _ass_time_to_ms(time_str: str) -> int:
    """
    ASS zaman formati (H:MM:SS.cc) → milisaniye.
    Gecersiz format girilirse 0 dondurur.
    """
    try:
        time_str = time_str.strip()
        h, rest   = time_str.split(':', 1)
        m, rest   = rest.split(':', 1)
        s, cs     = rest.split('.')
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(cs) * 10
    except Exception:
        return 0


# ── Gecis fonksiyonu: effect alani banner/scroll mu? ────────────────────────
def has_scroll_effect(effect: str) -> bool:
    """
    subtitle_processor.py icin kolay erisim fonksiyonu.
    Effect alani 'Banner' veya 'Scroll up/down' ise True dondurur.
    """
    e = (effect or '').strip()
    return bool(_BANNER_RE.match(e) or _SCROLL_RE.match(e))


# ─────────────────────────────────────────────────────────────────────────────
# [Asama 2] Renk Kodu Validasyonu
# ─────────────────────────────────────────────────────────────────────────────

def extract_color_codes(ass_text: str) -> List[str]:
    """
    ASS metnindeki tum &HBBGGRR& (ve &HAABBGGRR&) renk kodlarini cikart.
    Tag bloklari icerisindeki renk kodlari hedeflenir.
    """
    return _COLOR_RE.findall(ass_text)


def validate_color_preservation(
    original_text: str,
    translated_text: str,
) -> dict:
    """
    [Asama 2] Ceviri once/sonrasi renk kodlarinin korunup korunmadigini kontrol et.

    ASS renk formati: &H<BB><GG><RR>& veya &H<AA><BB><GG><RR>&
    Bu kodlar ceviri sirasinda AI tarafindan degistirilebilir veya silinebilir.

    Args:
        original_text: AI'ya gonderilmeden onceki orijinal ASS metni
        translated_text: AI'dan gelen ve tag'ler restore edilmis metin

    Returns:
        {
          'ok': bool,
          'original_colors': list[str],
          'translated_colors': list[str],
          'missing': list[str],        -- orijinalde var, cevride yok
          'extra': list[str],          -- orijinalde yok, cevride eklendi (!)
        }
    """
    orig_colors = extract_color_codes(original_text)
    trans_colors = extract_color_codes(translated_text)

    orig_set  = set(orig_colors)
    trans_set = set(trans_colors)

    missing = list(orig_set - trans_set)   # Kayip renkler
    extra   = list(trans_set - orig_set)   # AI'nin ekledigi yanlis renkler

    return {
        'ok': len(missing) == 0 and len(extra) == 0,
        'original_colors':   orig_colors,
        'translated_colors': trans_colors,
        'missing': missing,
        'extra':   extra,
    }


def validate_event_with_translation(
    event_dict: dict,
    translated_text: str,
    event_idx: int = 0,
) -> ValidationResult:
    """
    [Asama 2] Ceviri SONRASI calistirilan genisletilmis dogrulama.

    Hem CPS/CPL/actor/effect kontrollerini yapar (validate_event gibi)
    hem de renk kodu + margin analizi ekler.

    Args:
        event_dict:      Orijinal event dict (original_text, parts, duration_ms vb.)
        translated_text: AI'dan gelen, tag'ler restore edilmis nihai metin
        event_idx:       Hata raporlamasi icin event index

    Returns: ValidationResult (tum alanlar dolu)
    """
    # Once temel dogrulama (CPS/CPL ceviri metnine gore hesaplanmali)
    ev_for_cps = dict(event_dict)
    ev_for_cps['text'] = translated_text
    result = validate_event(ev_for_cps, event_idx)

    # [Asama 2] Renk kodu kontrolu
    original_raw = event_dict.get('original_text', '') or event_dict.get('text', '') or ''
    color_check  = validate_color_preservation(original_raw, translated_text)
    result.color_codes       = color_check['original_colors']
    result.colors_preserved  = color_check['ok']
    result.missing_colors    = color_check['missing']
    if not color_check['ok']:
        if color_check['missing']:
            result.issues.append(
                f"Renk kodu kayip: {color_check['missing']} — tag restore hatasi olabilir"
            )
        if color_check['extra']:
            result.issues.append(
                f"Yanlis renk kodu eklendi: {color_check['extra']} — AI mudahalesi"
            )

    # [Asama 2] Margin analizi
    parts = event_dict.get('parts', [])
    ml = event_dict.get('margin_l', 0) or (int(parts[5]) if len(parts) > 5 and parts[5].strip().isdigit() else 0)
    mr = event_dict.get('margin_r', 0) or (int(parts[6]) if len(parts) > 6 and parts[6].strip().isdigit() else 0)
    mv = event_dict.get('margin_v', 0) or (int(parts[7]) if len(parts) > 7 and parts[7].strip().isdigit() else 0)
    result.margin_override = (ml != 0 or mr != 0 or mv != 0)
    result.has_pos_tag = bool(re.search(r'\\(?:pos|move|org)\s*\(', original_raw))

    return result


# =============================================================================
# [Asama 3] Timing Ortusme Tespiti
# =============================================================================

def find_timing_overlaps(
    event_list: list,
    min_gap_ms: int = 0,
) -> List[dict]:
    """
    [Asama 3] Zaman damgalari ortüsen satirlari tespit et.

    'Ortüsme': Bir sonraki satirin Start zamani, mevcut satirin End zamanindan
    once basliyor. Bu durum ASS renderers'da flash/blink artefaktlara yol acar.

    Args:
        event_list:  structured_events listesi. Her item'de:
                       - 'parts' -> [Layer, Start, End, Style, Name, ...]
                       - 'style' -> stil adi (ayni layer'da ortüsme daha kritik)
                       - 'skip_translation' -> True ise bu satir dahil edilmez
        min_gap_ms:  Iki satir arasinda olmasi gereken minimum bosluk (ms).
                     0 = dokunma (touching) da kabul, >0 = bosluk zorunlu.

    Returns:
        [
          {
            'idx_a': int,          # ilk satir index'i
            'idx_b': int,          # ikinci satir index'i
            'start_a': int,        # ilk satir start ms
            'end_a': int,          # ilk satir end ms
            'start_b': int,        # ikinci satir start ms
            'overlap_ms': int,     # kac ms ortüsüyor
            'style_a': str,
            'style_b': str,
            'same_style': bool,    # ayni stil -> daha kritik
            'text_a': str,
            'text_b': str,
          },
          ...
        ]
    """
    # Sadece dialogue satirlari al, zaman sirasi garantisi icin sirala
    # [FIX] Signs/typesetting satırlari overlap kontrolüne DAHIL ETME
    # Bu satirlar cok-katmanli animasyon efektleridir — overlapping kasitlidir.
    _OV_SIGNS_RE = re.compile(
        r'(?i)^(?:signs?|ts|typeset|screen|insert|ins\b|fx\b|effect|overlay|watermark|title|credit)'
    )
    candidates = []
    for i, ev in enumerate(event_list):
        # [FIX] Hicbir skip_translation satirini timing overlap kontrolune dahil etme.
        # Signs/draw/junk satirlari overlap'e sokma - false positive uretir.
        if ev.get('skip_translation'):
            continue  # Atlanan satirlar timing overlap'e dahil degil
        # [FIX] Signs stili olan satirlari timing overlap'ten de muaf tut
        _ev_style = ev.get('style', '') or ''
        if _OV_SIGNS_RE.match(_ev_style):
            continue  # Signs = kasitli cok-katmanli, overlap normal
        parts = ev.get('parts', [])
        if len(parts) < 3:
            continue
        start_ms = _ass_time_to_ms(parts[1])
        end_ms   = _ass_time_to_ms(parts[2])
        if start_ms >= end_ms:
            continue  # Gecersiz timing
        candidates.append({
            'orig_idx': i,
            'start_ms': start_ms,
            'end_ms':   end_ms,
            'style':    ev.get('style', parts[3] if len(parts) > 3 else ''),
            'text':     (ev.get('original_text') or ev.get('text') or '')[:60],
        })

    # Start zamanina gore sirala
    candidates.sort(key=lambda x: x['start_ms'])

    overlaps = []
    for j in range(len(candidates) - 1):
        a = candidates[j]
        b = candidates[j + 1]

        # b baslangici a'nin bitisinden once mi?
        gap_ms = b['start_ms'] - a['end_ms']
        if gap_ms < min_gap_ms:
            overlap_ms = abs(gap_ms) if gap_ms < 0 else 0
            overlaps.append({
                'idx_a':       a['orig_idx'],
                'idx_b':       b['orig_idx'],
                'start_a':     a['start_ms'],
                'end_a':       a['end_ms'],
                'start_b':     b['start_ms'],
                'overlap_ms':  overlap_ms,
                'gap_ms':      gap_ms,
                'style_a':     a['style'],
                'style_b':     b['style'],
                'same_style':  a['style'] == b['style'],
                'text_a':      a['text'],
                'text_b':      b['text'],
            })

    return overlaps


def summarize_overlaps(overlaps: List[dict]) -> dict:
    """find_timing_overlaps() ciktisini ozetle."""
    total        = len(overlaps)
    critical     = [o for o in overlaps if o['overlap_ms'] > 100]  # 100ms+ ortüsme
    same_style   = [o for o in overlaps if o['same_style']]
    touching     = [o for o in overlaps if o['overlap_ms'] == 0]   # dokunma (gap=0)

    return {
        'total':       total,
        'critical':    len(critical),    # 100ms+ gerçek ortüsme
        'same_style':  len(same_style),  # ayni stil -> flash artefakt riski yüksek
        'touching':    len(touching),    # sadece dokunma (0ms gap)
        'details':     overlaps[:30],    # max 30 detay
    }
