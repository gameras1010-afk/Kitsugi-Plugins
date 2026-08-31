"""
ass_content_classifier.py
=========================
ASS satir siniflandirici — tum kural ve sozluk dosyalarindan beslenir.

Kaynaklar:
  ass_tags_database.py      : libass + bubblesub/ass_tag_parser tag sozlugu
  ass_style_conventions.py  : Fansub toplulugu stil adlari (GJM, Chyuu, CR...)

TEMEL PRENSIP:
  Gercek metin VARSA → ceviri (tag'ler placeholder'a alinir, API sadece metin gorur)
  SKIP sadece icerigin gercekten cevirisi olmadigi durumda:
    drawing path, bos, saf sembol, CJK dominant, Japonca stil...
"""

import re
from typing import NamedTuple, Dict, Optional

# ── Adaptif Pattern Ogrenici ────────────────────────────────────────────────
try:
    from ass_skip_learner import (
        check_learned as _sl_check,
        auto_learn_from_classifier_result as _sl_auto_learn,
    )
    _LEARNER_OK = True
except ImportError:
    _LEARNER_OK = False
    def _sl_check(raw, pure=''): return (None, '')
    def _sl_auto_learn(*a, **kw): pass

import ass_vendor_setup  # noqa

# ── ASS Tag Veritabani ──────────────────────────────────────────────────────
from ass_tags_database import (
    SKIP_STYLE_SUFFIXES,
    FORCE_TRANSLATE_SUFFIXES,
    SIGN_STYLE_KEYWORDS,
    EFFECT_FIELD_PATTERNS,
    extract_tag_names_from_text,
    database_info,
)

# ── Fansub toplulugu stil sozlugu ────────────────────────────────────────────
from ass_style_conventions import (
    classify_style_name,
    classify_actor_field,
    is_text_non_translatable,
    is_gradient_cluster,
    LAYER_SIGN_THRESHOLD,
    LAYER_DRAWING_THRESHOLD,
    LINEBREAK_ONLY_PATTERN,
    CJK_DOMINANT_PATTERN,
    NUMBER_DOMINANT_PATTERN,
    ELLIPSIS_ONLY_PATTERN,
)

# ── ass_tag_extractor: placeholder sistemi ──────────────────────────────────
try:
    from ass_tag_extractor import (
        extract_ass_tags as _ass_extract,
        restore_ass_tags as _ass_restore,
    )
    _EXTRACTOR_OK = True
except ImportError:
    _EXTRACTOR_OK = False
    def _ass_extract(text):
        tag_map = {}
        counter = [0]
        def _rep(m):
            blk = m.group(0)
            if '\\' not in blk:
                return ''
            k = f'__T{counter[0]}__'
            tag_map[k] = blk
            counter[0] += 1
            return k
        clean = re.sub(r'\{[^}]*\}', _rep, text)
        return clean, tag_map
    def _ass_restore(text, tag_map):
        for k, v in tag_map.items():
            text = text.replace(k, v)
        return text, []


# =============================================================================
# Sonuc Tipi
# =============================================================================

class ClassificationResult(NamedTuple):
    action: str       # 'skip' | 'translate' | 'translate_sign'
    reason: str       # Log icin sebep
    clean_text: str   # Placeholder'li temiz metin
    tag_map: dict     # restore icin
    confidence: float # 0.0-1.0


# =============================================================================
# ANA FONKSİYON — classify_line()
# =============================================================================

def classify_line(
    raw_text: str,
    style_name: str = '',
    play_res_x: int = 1920,
    play_res_y: int = 1080,
    event_meta: Optional[Dict] = None,
) -> ClassificationResult:
    """
    Bir ASS satiri icin 'skip'/'translate'/'translate_sign' karari.

    Kural sirasi (kisa-devre mantiginda):
      [A] Kesin SKIP — hicbir zaman ceviri
          1.  \\p[1-9]  drawing mode
          2.  \\k karaoke timing tagleri (k K kf ko kt)
          3.  Tag sonrasi bos metin
          4.  \\N \\n \\h — sadece satir sonu
          5.  Saf sembol / muzik notasi (gercek harf yok)
          6.  Saf drawing path metni (m 0 0 l 100 100)
          7.  Saf CJK (Japonca/Cinese dominant)
          8.  Sadece ... / — / ellipsis
          9.  Tamamen gorunmez alpha (\\1a&HFF& veya \\alpha&HFF&)
          10. veya stil adi (SKIP kategorisi) — ROM, JPN, KARA...
          11. Effect alani = Karaoke (legacy)
          12. Actor alani TL/editor notu + ve stil bilinmiyorsa
      [B] Style override kontrolleri
          13. FORCE_TRANSLATE stil → direkt 'translate'
          14. SIGN stil → 'translate_sign'
      [C] TRANSLATE_SIGN — metin var, sign modu gerekli
          15. \\pos / \\move + kisa metin (<=12 kelime)
          16. Animasyonlu (\\t) + kisa metin (<=6 kelime)
          17. 4+ agir typesetting tag + kisa metin
          18. Effect alani = Banner/Scroll
      [D] TRANSLATE — geri kalan her sey
    """
    if not raw_text or not raw_text.strip():
        return ClassificationResult('skip', 'empty', '', {}, 1.0)

    meta = event_meta or {}

    # ── Tag extraction (koruma sistemi) ─────────────────────────────────────
    clean_text, tag_map = _ass_extract(raw_text)
    pure_text = re.sub(r'__T\d+__|__NL__|__SL__|__HS__', '', clean_text).strip()
    # \N \n \h satir sonlarini da temizle
    pure_stripped = re.sub(r'\\[NnhH]', ' ', pure_text).strip()

    # =========================================================================
    # [A] KESİN SKIP KURALLARI
    # =========================================================================

    # A1: \p Drawing mode — icerik vektor path komutu, kelime degil
    if re.search(r'\\p[1-9]', raw_text):
        return ClassificationResult('skip', 'drawing_p_tag', clean_text, tag_map, 1.0)

    # A2: Karaoke timing tagleri — \k \K \kf \ko \kt (libass + ass_tag_parser)
    if re.search(r'\\[kK][tTfFoO]?\d', raw_text):
        return ClassificationResult('skip', 'karaoke_tag', clean_text, tag_map, 1.0)

    # A3: Tag sonrasi tamamen bos
    if not pure_stripped:
        return ClassificationResult('skip', 'empty_after_strip', clean_text, tag_map, 1.0)

    # A4: Sadece \N \n \h satir sonlari
    if LINEBREAK_ONLY_PATTERN.match(pure_text):
        return ClassificationResult('skip', 'linebreak_only', clean_text, tag_map, 1.0)

    # A5: Saf sembol / muzik notasi — gercek harf/kelime yok
    # "Holding on" gibi metin olsaydi _symbol_stripped dolu olur
    _sym = re.sub(
        r'[♪♫♬♩♭♮♯\u3000-\u303F\u30FB\u30FC〜～…—–\-·•\*\+\=\|/\\○●◎△▲▽▼□■◇◆★☆※¶§\s]',
        '', pure_stripped
    )
    if not _sym:
        return ClassificationResult('skip', 'symbol_only', clean_text, tag_map, 1.0)

    # A6: Saf drawing path verisi (\p olmasa bile text alaninda gelebilir)
    if re.match(r'^\s*(?:[mlbscnpMBSCNP]\s+-?\d[\s\d.\-,]*)+\s*$', pure_stripped):
        return ClassificationResult('skip', 'drawing_cmd_text', clean_text, tag_map, 1.0)

    # A7: Saf CJK (Japonca / Cinese dominant) — cevirmen icin anlamli degil
    if CJK_DOMINANT_PATTERN.match(pure_stripped):
        return ClassificationResult('skip', 'cjk_dominant', clean_text, tag_map, 0.95)

    # A8: Sadece ellipsis / tire / nokta (... veya — veya -)
    if ELLIPSIS_ONLY_PATTERN.match(pure_stripped):
        return ClassificationResult('skip', 'ellipsis_only', clean_text, tag_map, 1.0)

    # A9: Tamamen gorunmez alpha (maskeleme katmani)
    # \1a&HFF& = primary renk tam saydam; metin gorsel olarak yok
    if re.search(r'\\1a&HFF&?', raw_text, re.IGNORECASE) or \
       re.search(r'\\alpha&HFF&?', raw_text, re.IGNORECASE):
        # outline/shadow gorunur olabilir, onlari haric tut
        if not re.search(r'\\(?:3a|4a)&H(?:00|0[0-7])', raw_text, re.IGNORECASE):
            return ClassificationResult('skip', 'invisible_alpha', clean_text, tag_map, 0.88)

    # A10: Stil adi = SKIP (ROM, JPN, KARA, CREDIT vs.)
    # ass_style_conventions.classify_style_name() tum fansub gruplarini kapsıyor
    if style_name:
        style_decision = classify_style_name(style_name)
        if style_decision == 'skip':
            return ClassificationResult(
                'skip', f'style_skip:{style_name}', clean_text, tag_map, 0.95
            )

    # A11: Effect alani = legacy karaoke
    effect_raw = (meta.get('effect') or '').strip()
    if effect_raw:
        effect_lc = effect_raw.lower()
        for pat, eff_type in EFFECT_FIELD_PATTERNS.items():
            if effect_lc.startswith(pat) and eff_type == 'karaoke':
                return ClassificationResult('skip', 'effect_karaoke', clean_text, tag_map, 0.90)

    # A12: Layer no yuksek = drawing/mask katmani
    try:
        layer = int(meta.get('layer', 0) or 0)
        if layer >= LAYER_DRAWING_THRESHOLD:
            # Cok yuksek layer + kisa metin = muhtemelen mask veya gradient layer
            if len(pure_stripped) <= 3:
                return ClassificationResult('skip', f'high_layer_mask:{layer}', clean_text, tag_map, 0.82)
    except (ValueError, TypeError):
        pass

    # A13: \clip(m...) / \iclip(m...) vektör kırpma + typeset junk tespiti
    # Her event sadece 1 harf olan karaoke/OP-ED typeset satırlarını yakalar
    # Örnek: {\fn...\pos(726,162)\clip(m 516 26 l 498 73 ...)}l  ← sadece "l"
    # \iclip(m ...) = ters vektör kırpma — aynı karaoke typeset mantığı.
    # Üç senaryo:
    #   A) {\clip(m)}l              → ec='l'      → len<=2 → junk
    #   B) {\clip(m)}llllll...      → ec='llll'   → unique=1 → junk
    #   C) {\iclip(m)}e             → ec='e'      → len<=2 → junk
    # Gerçek tabela: "Blade Throw" → unique>1 → GEÇİLİR
    # Kaynak: libass/ass_parse.c, subtitle_processor.py BLOK-2 mantığı
    if re.search(r'\\i?clip\(m\s', raw_text):
        _deep_stripped = re.sub(r'\{[^}]*\}', '', raw_text)   # kapalı tag'ler
        _deep_stripped = re.sub(r'\{[^}]*$',  '', _deep_stripped)  # kapanmamış tag
        _deep_stripped = _deep_stripped.strip()
        _ec_unique = len(set(_deep_stripped.lower().replace(' ', '')))
        _is_clip_junk = (
            len(_deep_stripped) == 0 or   # tamamen boş
            len(_deep_stripped) <= 2 or   # tek harf (A/C)
            _ec_unique <= 1               # tek harf tekrarı (B)
        )
        if _is_clip_junk:
            return ClassificationResult('skip', 'vector_clip_junk', clean_text, tag_map, 0.95)

    # A13b: Off-screen \pos koordinatı — ekran dışı metin görünmez, çeviri gereksiz
    # Örnek: {\pos(-500,50)} veya {\pos(9999,9999)} → görsel katman, çevrilmez
    # Gerçek sign'larda pos ekran içinde olur (0..play_res_x, 0..play_res_y + ufak tolerans)
    _pos_m = re.search(r'\\pos\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)', raw_text)
    if _pos_m:
        try:
            _px, _py = float(_pos_m.group(1)), float(_pos_m.group(2))
            _margin = 50  # 50px tolerans (gercek sign'lar cok nadiren sinira bu kadar yakin olur)
            if (_px < -_margin or _py < -_margin
                    or _px > play_res_x + _margin
                    or _py > play_res_y + _margin):
                return ClassificationResult(
                    'skip', f'offscreen_pos({_px:.0f},{_py:.0f})',
                    clean_text, tag_map, 0.90
                )
        except (ValueError, TypeError):
            pass

    # A13c: Tag/metin oranı aşırı yüksek → pure typeset junk
    # Tag karakterleri metinden 8x fazlaysa bu satır görsel efekt katmanıdır.
    # Örnek: {\blur2\pos(960,50)\frz342\fscx150\fscy80\3c&H0&\bord3\fn Arial}AB
    # tag_len≈70, text_len≈2 → ratio=35 → junk
    if pure_stripped:
        _tag_content = re.findall(r'\{[^}]*\}', raw_text)
        _tag_len = sum(len(t) for t in _tag_content)
        _txt_len = len(pure_stripped)
        if _txt_len > 0 and _tag_len / _txt_len >= 8 and _txt_len <= 15:
            return ClassificationResult(
                'skip', f'tag_text_ratio_junk({_tag_len}/{_txt_len})',
                clean_text, tag_map, 0.88
            )

    # A14: Per-karakter typeset — OP/ED harf bazli typeset satiri (GENEL KURAL)
    # Ornek (frz): {\blur\frz333.9\pos(...)}A{*\frz334.024}o{*\frz334.148}...
    # Ornek (fs) : {\blur\fs22.5\pos(...)}I {*\fs22.356}B{*\fs22.284}e {*\fs22.14}K...
    # Kullanilan tag ne olursa olsun (\frz, \fs, \fax, \fscx...):
    # Kural: tag bloklari arasi TUM parcalar <=2 kar. VE 4+ parca → SKIP.
    _pc_frags = [f.strip() for f in re.split(r'\{[^}]*\}', raw_text) if f.strip()]
    if len(_pc_frags) >= 4 and all(len(f) <= 2 for f in _pc_frags):
        return ClassificationResult(
            'skip', f'per_char_typeset(n={len(_pc_frags)})',
            clean_text, tag_map, 0.97
        )

    # A15: Oğrenilmış pattern kontrolü (ass_skip_learner adaptif DB)
    # Sistem önceki dosyalardan öğrendiği pattern'leri burada kontrol eder.
    # action='skip'    → metin yok / saf kod → direkt skip
    # action='protect' → kod var ama metin de var → placeholder koru, çevir
    if _LEARNER_OK:
        _sl_action, _sl_reason = _sl_check(raw_text, pure_stripped)
        if _sl_action == 'skip':
            return ClassificationResult('skip', _sl_reason, clean_text, tag_map, 0.90)
        # 'protect' durumunda normal akışa devam (placeholder sistemi zaten korur)

    # =========================================================================
    # [B] STYLE OVERRIDE — Kesin ceviri / kesin sign
    # =========================================================================

    # B1: Stil adi = FORCE_TRANSLATE (EN, ALT, DEFAULT, DIALOGUE...)
    if style_name:
        if style_decision == 'translate':  # type: ignore
            # Devam et ama TRANSLATE_SIGN kontrolunu atla -> direkt TRANSLATE
            return _translate_or_sign(
                raw_text, pure_stripped, style_name,
                clean_text, tag_map, meta, effect_raw, forced_translate=True
            )

        # B2: Stil adi = SIGN → translate_sign
        if style_decision == 'sign':
            return ClassificationResult(
                'translate_sign', f'sign_style:{style_name}', clean_text, tag_map, 0.88
            )

    # =========================================================================
    # [C+D] TRANSLATE_SIGN veya TRANSLATE
    # =========================================================================
    return _translate_or_sign(
        raw_text, pure_stripped, style_name,
        clean_text, tag_map, meta, effect_raw
    )


# =============================================================================
# Yardimci: TRANSLATE / TRANSLATE_SIGN karari
# =============================================================================

def _translate_or_sign(
    raw_text, pure_stripped, style_name,
    clean_text, tag_map, meta, effect_raw,
    forced_translate=False
) -> ClassificationResult:
    """
    Gercek metin var. Sadece "translate" mi "translate_sign" mi?
    """
    word_count = len(pure_stripped.split())

    # Effect alani = Banner/Scroll → sign modu
    if effect_raw:
        effect_lc = effect_raw.lower()
        for pat, eff_type in EFFECT_FIELD_PATTERNS.items():
            if effect_lc.startswith(pat) and eff_type == 'scroll':
                return ClassificationResult(
                    'translate_sign', f'effect_scroll:{pat}', clean_text, tag_map, 0.85
                )

    if forced_translate:
        return ClassificationResult('translate', 'force_translate_style', clean_text, tag_map, 0.95)

    has_pos  = bool(re.search(r'\\(?:pos|move)\(', raw_text))
    has_anim = bool(re.search(r'\\t\(', raw_text))
    tag_names = extract_tag_names_from_text(raw_text)
    heavy_count = sum(1 for n in tag_names if n in {
        'blur', 'bord', 'xbord', 'ybord', 'shad', 'xshad', 'yshad',
        'fn', 'fs', 'fscx', 'fscy', 'fsp', 'frz', 'frx', 'fry',
        'fax', 'fay', '3c', '4c', '1a', '2a', '3a', '4a', 'alpha',
    })

    # C1: \pos / \move + kisa metin → ekran yazisi/tabela
    if has_pos and word_count <= 12:
        return ClassificationResult('translate_sign', 'pos_with_text', clean_text, tag_map, 0.90)

    # C2: Animasyonlu + kisa → efekt metni
    if has_anim and word_count <= 6:
        return ClassificationResult('translate_sign', 'animation_short', clean_text, tag_map, 0.80)

    # C3: 4+ agir typesetting tag + kisa metin
    if heavy_count >= 4 and len(pure_stripped) < 60:
        return ClassificationResult(
            'translate_sign', f'heavy_typeset(n={heavy_count})', clean_text, tag_map, 0.85
        )

    # D: Gercek metin var, ceviriye git
    return ClassificationResult('translate', 'has_real_text', clean_text, tag_map, 0.95)


# =============================================================================
# Toplu siniflandirma (subtitle_processor entegrasyonu)
# =============================================================================

def classify_events(events: list, play_res_x=1920, play_res_y=1080) -> list:
    for i, ev in enumerate(events):
        if ev.get('skip_translation'):
            ev.setdefault('classifier_action', 'skip')
            ev.setdefault('classifier_reason', ev.get('reason', 'pre_filtered'))
            continue

        parts = ev.get('parts', [])
        raw   = parts[9] if len(parts) > 9 else ev.get('original_text', ev.get('text', ''))
        style = parts[3] if len(parts) > 3 else ev.get('style', '')
        meta  = {
            'effect': parts[8] if len(parts) > 8 else ev.get('effect', ''),
            'actor':  parts[4] if len(parts) > 4 else ev.get('actor', ''),
            'layer':  parts[0] if len(parts) > 0 else ev.get('layer', 0),
        }

        # Gradient cluster tespiti — cok sayida cakisan satir = skip
        if is_gradient_cluster(events, i, threshold=5):
            ev['skip_translation'] = True
            ev['classifier_action'] = 'skip'
            ev['classifier_reason'] = 'gradient_cluster'
            ev['reason'] = 'gradient_cluster'
            continue

        r = classify_line(raw, style, play_res_x, play_res_y, meta)
        ev['classifier_action'] = r.action
        ev['classifier_reason'] = r.reason

        if r.action == 'skip':
            ev['skip_translation'] = True
            ev['reason'] = r.reason
            # Otomatik öğrenme: bu pattern'ı DB'ye kaydet
            if _LEARNER_OK:
                _pure = re.sub(r'__T\d+__|__NL__|__SL__|__HS__', '', r.clean_text).strip()
                _sl_auto_learn(raw, _pure, r.action, r.reason)
        elif r.action == 'translate_sign':
            ev['is_sign'] = True

    return events


# Uyumluluk alias'lari
def is_non_translatable_extended(raw_text, style_name='', play_res_x=1920, play_res_y=1080):
    return classify_line(raw_text, style_name, play_res_x, play_res_y).action == 'skip'

def is_sign_line(raw_text, style_name='', play_res_x=1920, play_res_y=1080):
    return classify_line(raw_text, style_name, play_res_x, play_res_y).action == 'translate_sign'


# =============================================================================
# Modul testi
# =============================================================================
if __name__ == '__main__':
    db = database_info()
    print(f"[DB] {db['total_tags']} tag | kaynak: {db['source']}\n")

    tests = [
        # (raw_text, style, meta, beklenen, aciklama)

        # == KESIN SKIP ==
        (r'{\p1}m 0 0 l 100 0',   'Default', None, 'skip', 'Drawing p1'),
        (r'{\p4}m 10 20 b 50 0 100 50', 'Signs', None, 'skip', 'Drawing p4 bezier'),
        (r'{\k80}Ma{\k40}yo',      'OP-ROM',  None, 'skip', 'Karaoke \\k'),
        (r'{\kf80}hold{\ko20}on',  'Default', None, 'skip', 'Karaoke kf+ko'),
        (r'{\kt10}{\kf80}text',    'Default', None, 'skip', 'Karaoke \\kt (libass v4++)'),
        ('',                        'Default', None, 'skip', 'Tamamen bos'),
        (r'{\blur2\pos(0,0)}',      'Default', None, 'skip', 'Sadece tag, metin yok'),
        ('  ♪ ♫ ♪  ',              'Default', None, 'skip', 'Saf nota'),
        ('仮面ライダー',              'Default', None, 'skip', 'Saf CJK Japonca'),
        ('你好世界',                  'Default', None, 'skip', 'Saf CJK Cinese'),
        ('...',                     'Default', None, 'skip', 'Sadece ellipsis'),
        (r'{\1a&HFF&\pos(0,0)}GFX','Default', None, 'skip', 'Gorunmez alpha'),
        ('Watashi wa',              'OP1-ROM', None, 'skip', 'ROM stil'),
        ('Boku no namae',           'GJM_InsJP', None, 'skip', 'GJM InsJP stil'),
        ('Sarki sozu',              'ED-JPN',  None, 'skip', 'JPN stil'),
        ('Staff list',              'Credits', None, 'skip', 'Credits stil'),
        ('Music notation',          'BGM',     None, 'skip', 'BGM stil'),
        ('Kago no naka',            'OP-Kara', None, 'skip', 'Kara stil'),
        ('test', 'Default', {'effect': 'Karaoke'}, 'skip', 'Effect=Karaoke legacy'),

        # == TRANSLATE ==
        ('Hello World',             'Default', None, 'translate', 'Normal dialog'),
        (r'{\i1}Sure, I gave it.',  'Default', None, 'translate', 'Italik dialog'),
        ('♪ Holding on forever ♪',  'Default', None, 'translate', 'Sarki sozu EN'),
        ('© 2024 Shueisha Ltd.',    'Default', None, 'translate', 'Copyright - metin var'),
        ('Love you',                'ED1-EN',  None, 'translate', 'EN stil force'),
        ('Yo wa nani',              'Default-ALT', None, 'translate', 'ALT stil force'),
        ('I am',                    'Italics',  None, 'translate', 'Italics stil'),
        ('Flashback line',          'Flashback', None, 'translate', 'Flashback stil'),

        # == TRANSLATE_SIGN ==
        (r'{\pos(100,50)}Exit',     'Default', None, 'translate_sign', 'POS kisa metin'),
        (r'{\blur0.6\pos(960,-200)}Rookie Award', 'Default', None, 'translate_sign', 'Off-screen sign'),
        (r'{\blur0.6\bord3\fn F\3c&H0&\fs60}Title', 'Default', None, 'translate_sign', 'Heavy typeset'),
        ('Banner content', 'Default', {'effect': 'Banner;5;1'}, 'translate_sign', 'Effect=Banner scroll'),
        ('Scroll content', 'Default', {'effect': 'Scroll up;0;1080;10'}, 'translate_sign', 'Effect=Scroll up'),
        ('Exit sign',               'Signs',   None, 'translate_sign', 'Sign stil'),
        ('Location text',           'OST',     None, 'translate_sign', 'OST stil'),
    ]

    ok = fail = 0
    for raw, style, meta, exp, desc in tests:
        r = classify_line(raw, style, event_meta=meta)
        chk = 'OK' if r.action == exp else 'FAIL'
        if r.action == exp:
            ok += 1
        else:
            fail += 1
        print(f'[{chk}] {exp:<18} {r.action:<18} {desc}')
        if r.action != exp:
            print(f'      reason={r.reason}')

    total = ok + fail
    print(f'\n{ok}/{total} passed | {fail} fail')
