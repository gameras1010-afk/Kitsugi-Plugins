"""
ass_reader/reader.py
====================
ASSFileReader sınıfı ve yardımcı fonksiyonlar.
"""
import os, re, json

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

