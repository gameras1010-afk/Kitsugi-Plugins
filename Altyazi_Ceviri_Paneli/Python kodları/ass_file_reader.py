"""
ass_file_reader.py
==================
Profesyonel ASS dosyası okuma/yazma modülü — Nexus Pro Translation Engine

Kullanılan kütüphaneler:
  - pysubs2  (pip install pysubs2)   : Güvenilir dosya okuma/yazma, SSAEvent objeleri
  - ass-tag-parser (entegre)          : Tag classification (ass_tag_extractor üzerinden)
  - PyonFX   (pip install pyonfx)    : Karaoke satır tespiti (opsiyonel, fallback var)

Bu modül subtitle_processor.py'nin kırılgan split(',', 9) parsing'ini tamamen
değiştirir ve mevcut processing mantığıyla tam uyumlu bir arayüz sunar.

Yazar: Nexus Pro — Antigravity AI
"""

import ass_vendor_setup  # noqa — _vendor/ dizinini path'e ekler
import re

# ── Gelişmiş encoding tespiti (charset-normalizer) ─────────────
try:
    from charset_normalizer import from_path as _cn_from_path, from_bytes as _cn_from_bytes
    _CHARSET_NORM_OK = True
except ImportError:
    _CHARSET_NORM_OK = False

# ── Unicode metin onarımı (ftfy) ───────────────────────────────
try:
    import ftfy as _ftfy
    _FTFY_OK = True
except ImportError:
    _FTFY_OK = False
from typing import Optional

# ── pysubs2: ASS dosya okuma/yazma ──────────────────────────────────────────
try:
    import pysubs2
    _PYSUBS2_OK = True
except ImportError:
    _PYSUBS2_OK = False

# ── PyonFX: Karaoke satır tespiti (opsiyonel) ────────────────────────────────
try:
    from pyonfx import Ass as _PyonFXAss
    _PYONFX_OK = True
except ImportError:
    _PYONFX_OK = False

# ── ass_tag_extractor: Tag sınıflandırma ─────────────────────────────────────
try:
    from ass_tag_extractor import is_drawing_line, classify_block
    _EXTRACTOR_OK = True
except ImportError:
    _EXTRACTOR_OK = False
    def is_drawing_line(text): return bool(re.search(r'\\p[1-9]', text))
    def classify_block(c): return 'tag' if re.search(r'\\[a-zA-Z]', c) else 'comment'

# ── Karaoke tag regex (fallback) ─────────────────────────────────────────────
_KARAOKE_RE = re.compile(r'\\[kKkt][\d.]*')
_DRAWING_RE = re.compile(r'\\p[1-9]')


def _color_to_ass(color) -> str:
    """pysubs2.Color nesnesini ASS renk string'ine (&HBBGGRR&) çevirir.
    ASS format: &HBBGGRR& (Blue-Green-Red sırası, alpha ayrı)
    """
    try:
        # pysubs2.Color: .r .g .b .a özellikleri var
        return f'&H{color.b:02X}{color.g:02X}{color.r:02X}&'
    except AttributeError:
        return '&H000000&'


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────────────────────────────────────

def is_karaoke_line(raw_text: str) -> bool:
    """
    Satırın karaoke satırı olup olmadığını tespit et.
    \\k, \\K, \\kf, \\ko, \\kt tag'lerinden herhangi biri varsa True.
    """
    return bool(_KARAOKE_RE.search(raw_text))


def detect_line_type(raw_text: str, style_name: str = "",
                     is_pysubs_comment: bool = False,
                     actor: str = "", effect: str = "") -> str:
    """
    Satır tipini belirle.

    Args:
        raw_text          : Ham ASS metni (tag'ler dahil)
        style_name        : Event stil adı
        is_pysubs_comment : pysubs2'nin 'Comment' type olarak işaretlediği satır
        actor             : Event Name/Actor alanı (fansub: 'Sign', 'Typeset', 'FX' vb.)
        effect            : Event Effect alanı (Banner, Scroll up, karaoke, fx vb.)

    Returns:
        'comment'  — ASS Comment: satırı
        'drawing'  — \\\\p1 içeren vektör çizim satırı
        'karaoke'  — \\\\k / \\\\K / \\\\kf / \\\\ko içeren karaoke satırı
        'fx'       — Karaoke template/automation satırı (effect='fx')
        'dialogue' — Normal çevrilebilir diyalog satırı
    """
    if is_pysubs_comment:
        # FX template comment satırları — karaoke automation
        if effect and effect.strip().lower() in ('fx', 'karaoke', 'paint'):
            return 'fx'
        return 'comment'
    if is_drawing_line(raw_text) if _EXTRACTOR_OK else bool(_DRAWING_RE.search(raw_text)):
        return 'drawing'
    if is_karaoke_line(raw_text):
        return 'karaoke'
    # Effect alanı analizi — Banner/Scroll özel event'ler
    if effect:
        eff_lower = effect.strip().lower()
        if eff_lower.startswith(('banner', 'scroll up', 'scroll down')):
            return 'scroll'  # özel; çevirilebilir ama özel render
    return 'dialogue'


# Actor/Name alanı tabanlı hint'ler — detect_line_type'tan bağımsız kullanılır
_SIGN_ACTOR_KEYWORDS = frozenset([
    'sign', 'signs', 'typeset', 'ts', 'type', 'onscreen',
    'caption', 'label', 'banner', 'insert', 'sfx', 'fx',
    'title', 'board', 'text', 'overlay', 'screen',
])
_FX_TEMPLATE_ACTORS = frozenset(['template', 'code', 'fx', 'karaoke'])


def actor_line_hints(actor: str, effect: str = "") -> dict:
    """
    Actor (Name) ve Effect alanlarından ek ipuçları çıkar.
    Bu ipuçları event_dict'e eklenir.

    Returns:
        {
            'is_sign_by_actor': bool,   — Actor 'Sign/TS/Typeset' gibi
            'is_fx_template': bool,     — Karaoke template satırı
            'actor_lower': str,
        }
    """
    act = (actor or '').strip().lower()
    eff = (effect or '').strip().lower()
    return {
        'is_sign_by_actor': act in _SIGN_ACTOR_KEYWORDS,
        'is_fx_template':   (act in _FX_TEMPLATE_ACTORS) or (eff in ('fx', 'karaoke', 'paint')),
        'actor_lower':      act,
    }


def get_plain_text(raw_text: str) -> str:
    """
    ASS raw metninden tag'leri ve comment bloklarını temizle.
    \\N → newline, \\n → space, \\h → space olarak dönüştürür.
    """
    # Tag bloklarını kaldır
    clean = re.sub(r'\{[^}]*\}', '', raw_text)
    # ASS özel karakterleri
    clean = clean.replace('\\N', '\n').replace('\\n', ' ').replace('\\h', '\u00a0')
    return clean.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Ana Sınıf
# ─────────────────────────────────────────────────────────────────────────────

class ASSFileReader:
    """
    ASS dosyası için profesyonel okuma/yazma sınıfı.

    pysubs2 ile dosyayı okur, her event'i zenginleştirilmiş dict olarak sunar.
    subtitle_processor.py'nin mevcut event dict formatıyla tam uyumludur.

    Kullanım:
        reader = ASSFileReader("input.tr.ass")
        for event in reader.events:
            if event['line_type'] == 'dialogue':
                event['text'] = translated_text  # güncelle
        reader.save("output.tr.ass")
    """

    def __init__(self, filepath: str, encoding: str = 'utf-8-sig'):
        self.filepath = filepath
        self.encoding = encoding
        self._subs: Optional['pysubs2.SSAFile'] = None
        self.events: list[dict] = []
        self.styles: dict = {}
        self.info: dict = {}
        self._loaded_ok = False

        if not _PYSUBS2_OK:
            raise ImportError(
                "pysubs2 yüklü değil. 'pip install pysubs2' ile yükleyin."
            )
        self._load()

    def _load(self):
        """pysubs2 ile ASS dosyasını yükle — charset-normalizer + ftfy ile güçlendirilmiş."""
        # ADIM 1: charset-normalizer ile doğru encoding'i tespit et
        detected_enc = None
        if _CHARSET_NORM_OK:
            try:
                results = _cn_from_path(self.filepath)
                best = results.best()
                if best is not None:
                    detected_enc = str(best.encoding)
            except Exception:
                pass

        # ADIM 2: pysubs2 ile yükleme — önce tespit edilen, sonra fallback listesi
        _encs_to_try = []
        if detected_enc and detected_enc not in ('utf-8-sig', 'utf-8'):
            _encs_to_try.append(detected_enc)
        _encs_to_try.extend([self.encoding, 'utf-8', 'utf-8-sig', 'cp1252', 'latin-1'])
        # Tekrar edenler kaldır (sıralı)
        seen = set()
        _encs_to_try = [e for e in _encs_to_try if e not in seen and not seen.add(e)]

        _load_ok = False
        for enc in _encs_to_try:
            try:
                self._subs = pysubs2.load(self.filepath, encoding=enc)
                self.encoding = enc
                _load_ok = True
                break
            except Exception:
                continue

        if not _load_ok or self._subs is None:
            raise IOError(f"ASS dosyası yüklenemedi: {self.filepath}")

        # ADIM 3: ftfy ile mojibake onarımı (encoding yanlış tespit edilmiş olabilir)
        if _FTFY_OK:
            _ftfy_fixed = 0
            for ev in self._subs:
                original = ev.text or ''
                fixed = _ftfy.fix_text(original)
                if fixed != original:
                    ev.text = fixed
                    _ftfy_fixed += 1
            if _ftfy_fixed > 0:
                print(f"   [ftfy] {_ftfy_fixed} event'te mojibake onarıldı")

        # Stil bilgilerini al — pysubs2 SSAStyle TAM alan listesi
        # (ssastyle.py kaynak: fontname, fontsize, primarycolor, secondarycolor,
        #  tertiarycolor, outlinecolor, backcolor, bold, italic, underline,
        #  strikeout, scalex, scaley, spacing, angle, borderstyle, outline,
        #  shadow, alignment, marginl, marginr, marginv, alphalevel, encoding)
        for name, style in self._subs.styles.items():
            self.styles[name] = {
                'name':            name,
                # Font
                'fontname':        style.fontname,
                'fontsize':        style.fontsize,
                'bold':            style.bold,
                'italic':          style.italic,
                'underline':       style.underline,
                'strikeout':       style.strikeout,
                'encoding':        style.encoding,
                # Ölçek / Boşluk / Açı
                'scalex':          style.scalex,
                'scaley':          style.scaley,
                'spacing':         style.spacing,
                'angle':           style.angle,
                # Kenar/Gölge
                'borderstyle':     style.borderstyle,
                'outline':         style.outline,
                'shadow':          style.shadow,
                # Hizalama
                'alignment':       int(style.alignment),
                # Margin
                'margin_l':        style.marginl,
                'margin_r':        style.marginr,
                'margin_v':        style.marginv,
                # Renkler (pysubs2.Color objesi → &HBBGGRR& string'e)
                'primarycolor':    _color_to_ass(style.primarycolor),
                'secondarycolor':  _color_to_ass(style.secondarycolor),
                'outlinecolor':    _color_to_ass(style.outlinecolor),
                'backcolor':       _color_to_ass(style.backcolor),
                # Ham pysubs2 Color objesi (gerekirse)
                '_pcolor':         style.primarycolor,
                '_ocolor':         style.outlinecolor,
            }

        # Dosya bilgileri
        self.info = dict(self._subs.info)

        # Her event'i zenginleştirilmiş dict'e dönüştür
        for i, ev in enumerate(self._subs):
            raw_text = ev.text  # pysubs2'de .text = raw ASS text (with tags)
            line_type = detect_line_type(
                raw_text,
                style_name=ev.style,
                is_pysubs_comment=ev.type == 'Comment',
                actor=ev.name or '',
                effect=ev.effect or '',
            )

            # Stil detayları (style dict'ten al)
            style_info = self.styles.get(ev.style, {})

            # Actor/Effect alanı ipuçları
            _actor_hints = actor_line_hints(ev.name or '', ev.effect or '')

            event_dict = {
                # ── Kimlik ──────────────────────────────────────────────────
                'index': i,
                '_pysubs2_event': ev,          # Referans (geri yazma için)

                # ── Temel Bilgiler ───────────────────────────────────────────
                'style': ev.style,
                'actor': ev.name,
                'effect': ev.effect,
                'layer': ev.layer,
                'type': ev.type,               # 'Dialogue' veya 'Comment'

                # ── Zamanlama ────────────────────────────────────────────────
                'start_ms': ev.start,          # millisaniye
                'end_ms': ev.end,
                'duration_ms': ev.duration,

                # ── Metin ────────────────────────────────────────────────────
                'text': raw_text,              # Ham ASS metni (tag'ler dahil)
                'plaintext': ev.plaintext,     # Tag'siz saf metin (pysubs2)

                # ── Tip Tespiti ──────────────────────────────────────────────
                'line_type': line_type,        # 'dialogue'|'drawing'|'karaoke'|'comment'
                'is_comment': ev.type == 'Comment',
                'is_drawing': ev.is_drawing,
                'is_karaoke': is_karaoke_line(raw_text),

                # ── Actor/Effect Tabanlı İpuçları ────────────────────────────
                'is_sign_by_actor': _actor_hints['is_sign_by_actor'],
                'is_fx_template':   _actor_hints['is_fx_template'],

                # ── Margin (Override) ────────────────────────────────────────
                'margin_l': ev.marginl,
                'margin_r': ev.marginr,
                'margin_v': ev.marginv,

                # ── Stil Detayları ───────────────────────────────────────────
                'style_fontsize': style_info.get('fontsize', 0),
                'style_alignment': style_info.get('alignment', 2),
                'style_bold': style_info.get('bold', False),
            }
            self.events.append(event_dict)

        self._loaded_ok = True

    # ── Güncelleme ────────────────────────────────────────────────────────────

    def update_text(self, event_index: int, new_text: str):
        """Belirtilen event'in metnini güncelle (pysubs2 objesi üzerinden)."""
        ev_dict = self.events[event_index]
        ev_dict['text'] = new_text
        ev_dict['_pysubs2_event'].text = new_text

    def update_all_translated(self, translated_map: dict):
        """
        {event_index: translated_text} dict'i ile toplu güncelleme.
        subtitle_processor.py'nin mevcut çıktı yapısıyla uyumlu.
        """
        for idx, new_text in translated_map.items():
            self.update_text(idx, new_text)

    # ── Kaydetme ──────────────────────────────────────────────────────────────

    def save(self, output_path: Optional[str] = None, encoding: str = 'utf-8-sig'):
        """Çevrilen dosyayı kaydet."""
        path = output_path or self.filepath
        self._subs.save(path, encoding=encoding)

    def to_string(self) -> str:
        """ASS içeriğini string olarak al."""
        return self._subs.to_string('ass')

    # ── Yardımcı Metodlar ────────────────────────────────────────────────────

    def get_dialogue_events(self) -> list[dict]:
        """Sadece çevrilebilir diyalog satırlarını döndür."""
        return [e for e in self.events if e['line_type'] == 'dialogue']

    def get_karaoke_events(self) -> list[dict]:
        """Karaoke satırlarını döndür (karaoke tespiti: \\k, \\K, \\kf, \\ko)."""
        return [e for e in self.events if e['is_karaoke']]

    def get_drawing_events(self) -> list[dict]:
        """Drawing (vektör) satırlarını döndür — çeviriye göndermemek için."""
        return [e for e in self.events if e['is_drawing']]

    def get_style_names(self) -> list[str]:
        """Tüm stil adlarını döndür."""
        return list(self.styles.keys())

    def get_font_size_for_style(self, style_name: str) -> float:
        """Belirtilen stilin font boyutunu döndür."""
        return self.styles.get(style_name, {}).get('fontsize', 0.0)

    def modify_style_font_size(self, style_name: str, mode: str, custom_size: int = 80):
        """
        Stil font boyutunu değiştir.

        mode: 'preserve' (koru), 'normalize' (min 80), 'custom' (sabit değer)
        """
        if style_name not in self._subs.styles:
            return
        style = self._subs.styles[style_name]
        if mode == 'normalize' and style.fontsize < 80:
            style.fontsize = 80
        elif mode == 'custom':
            style.fontsize = custom_size

    def modify_all_styles_font_size(self, mode: str, custom_size: int = 80):
        """Tüm stiller için font boyutu modunu uygula."""
        for style_name in self._subs.styles:
            self.modify_style_font_size(style_name, mode, custom_size)

    def __len__(self):
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    def __repr__(self):
        dialogue = sum(1 for e in self.events if e['line_type'] == 'dialogue')
        karaoke  = sum(1 for e in self.events if e['is_karaoke'])
        drawing  = sum(1 for e in self.events if e['is_drawing'])
        return (
            f"<ASSFileReader '{self.filepath}' "
            f"total={len(self.events)} dialogue={dialogue} "
            f"karaoke={karaoke} drawing={drawing}>"
        )

    # ── pysubs2 Tam Özellik Kümesi ────────────────────────────────────────────

    def remove_miscellaneous_events(self) -> None:
        """pysubs2.SSAFile.remove_miscellaneous_events() wrapper.
        Şunları kaldırır:
          - Comment tipi satırlar
          - \\p1 ile çizilmiş draw satırları
          - 1 karakterden kısa metin içeren satırlar
          - Aynı süre + aynı metin içeren duplicate satırlar (ilki korunur)
        events listesini de günceller.
        """
        self._subs.remove_miscellaneous_events()
        # events listesini yeniden oluştur
        self.events = []
        for i, ev in enumerate(self._subs):
            raw_text = ev.text
            line_type = detect_line_type(
                raw_text, style_name=ev.style,
                is_pysubs_comment=ev.type == 'Comment'
            )
            style_info = self.styles.get(ev.style, {})
            self.events.append({
                'index': i, '_pysubs2_event': ev,
                'style': ev.style, 'actor': ev.name,
                'effect': ev.effect, 'layer': ev.layer, 'type': ev.type,
                'start_ms': ev.start, 'end_ms': ev.end, 'duration_ms': ev.duration,
                'text': raw_text, 'plaintext': ev.plaintext,
                'line_type': line_type,
                'is_comment': ev.type == 'Comment',
                'is_drawing': ev.is_drawing,
                'is_karaoke': is_karaoke_line(raw_text),
                'margin_l': ev.marginl, 'margin_r': ev.marginr, 'margin_v': ev.marginv,
                'style_fontsize': style_info.get('fontsize', 0),
                'style_alignment': style_info.get('alignment', 2),
                'style_bold': style_info.get('bold', False),
            })

    def transform_framerate(self, in_fps: float, out_fps: float) -> None:
        """pysubs2.SSAFile.transform_framerate() wrapper.
        Tüm timestamp'leri in_fps/out_fps oranıyla ölçekler.
        Frame bazlı yanlış çevrilmiş dosyaları düzeltmek için kullanılır.
        Örnek: 23.976fps yerine 24fps varsayılmışsa:
            reader.transform_framerate(24, 23.976)
        """
        if in_fps <= 0 or out_fps <= 0:
            raise ValueError(f"FPS pozitif olmalı: {in_fps} -> {out_fps}")
        self._subs.transform_framerate(in_fps, out_fps)
        # Kendi events listesini de güncelle
        for ev_dict, ev in zip(self.events, list(self._subs)):
            ev_dict['start_ms'] = ev.start
            ev_dict['end_ms']   = ev.end
            ev_dict['duration_ms'] = ev.duration

    def import_styles(self, other: 'ASSFileReader', overwrite: bool = True) -> int:
        """pysubs2.SSAFile.import_styles() wrapper.
        Başka bir ASSFileReader'dan stilleri aktarır.
        Kullanım:
            translated_reader.import_styles(original_reader)
        Returns:
            Aktarılan stil sayısı
        """
        before = len(self._subs.styles)
        self._subs.import_styles(other._subs, overwrite=overwrite)
        after  = len(self._subs.styles)
        # Stil cache'ini yenile
        for name, style in self._subs.styles.items():
            if name not in self.styles:
                self.styles[name] = {
                    'name': name,
                    'fontname': style.fontname, 'fontsize': style.fontsize,
                    'bold': style.bold, 'italic': style.italic,
                    'alignment': int(style.alignment),
                    'primarycolor': _color_to_ass(style.primarycolor),
                    'outlinecolor': _color_to_ass(style.outlinecolor),
                }
        return after - before

    def rename_style(self, old_name: str, new_name: str) -> None:
        """pysubs2.SSAFile.rename_style() wrapper.
        Stil adını değiştir — event referansları da güncellenir.
        """
        self._subs.rename_style(old_name, new_name)
        if old_name in self.styles:
            self.styles[new_name] = self.styles.pop(old_name)
            self.styles[new_name]['name'] = new_name
        for ev_dict in self.events:
            if ev_dict['style'] == old_name:
                ev_dict['style'] = new_name

    def get_events_in_range(self, start_ms: int, end_ms: int,
                             include_partial: bool = True) -> list:
        """Belirli ms aralığındaki event'leri döndürür.
        Karaoke block tespiti, bölüm sınırı analizi için kullanışlıdır.
        include_partial=True → başlangıç veya bitiş aralık içinde olan event'ler de dahil.
        """
        result = []
        for ev in self.events:
            s, e = ev['start_ms'], ev['end_ms']
            if include_partial:
                if s < end_ms and e > start_ms:
                    result.append(ev)
            else:
                if s >= start_ms and e <= end_ms:
                    result.append(ev)
        return result

    def shift_all(self, ms: int) -> None:
        """pysubs2.SSAFile.shift() wrapper. Tüm event'leri ms kadar kaydır."""
        self._subs.shift(ms=ms)
        for ev_dict, ev in zip(self.events, list(self._subs)):
            ev_dict['start_ms'] = ev.start
            ev_dict['end_ms']   = ev.end

    def get_text_events_only(self) -> list:
        """pysubs2.SSAFile.get_text_events() wrapper.
        Comment ve draw satırlarını dışlayan event dict listesi.
        """
        return [e for e in self.events
                if not e['is_comment'] and not e['is_drawing']]



# ─────────────────────────────────────────────────────────────────────────────
# subtitle_processor.py Uyumluluk Katmanı
# ─────────────────────────────────────────────────────────────────────────────

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
