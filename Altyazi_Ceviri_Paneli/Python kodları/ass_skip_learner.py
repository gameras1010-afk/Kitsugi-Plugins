# -*- coding: utf-8 -*-
"""
ass_skip_learner.py
===================
Adaptif ASS Satır Pattern Öğrenme Motoru
-----------------------------------------
MANTIK (mevcut placeholder sisteminin uzantısı):
  - Satırda GERÇEK METİN var + bilinmeyen kod pattern → metni koru, kodu placeholder yap
  - Satırda METİN YOK / anlamsız → skip et
  - Her iki durumda da pattern'i kaydet → sonraki dosyalarda aynı tür satır gelince
    sistem baştan doğru karar verir (öğrenilmiş DB'den)

DB YAPISI (_learned_skip_patterns.json):
  {
    "version": 1,
    "patterns": [
      {
        "id": "lp_001",
        "type": "tag_combo",          # tag kombinasyonuna göre karar
        "tags": ["blur", "frz", "pos", "fscx"],
        "max_text_len": 10,           # bu kadar kısa metin varsa skip
        "action": "skip",             # skip | protect_and_translate
        "reason": "per_char_typeset_variant",
        "confidence": 0.92,
        "hit_count": 7,               # kaç dosyada görüldü
        "added": "2026-05-02",
        "example": "{\\blur\\frz\\pos}AB"
      }
    ],
    "text_patterns": [
      {
        "id": "tp_001",
        "type": "text_regex",         # saf metin regex
        "pattern": "^[A-Z]{1,2}$",   # tek/çift büyük harf → typeset fragment
        "action": "skip",
        "reason": "single_letter_typeset",
        "hit_count": 12,
        "added": "2026-05-02"
      }
    ]
  }

KULLANIM:
  from ass_skip_learner import AssSkipLearner
  learner = AssSkipLearner()

  # Sınıflandırma:
  decision, reason = learner.check(raw_text, pure_stripped)
  # → ('skip', 'learned:per_char_typeset_variant')
  # → ('protect', 'learned:single_letter_with_context')
  # → (None, '') — öğrenilmiş pattern yok, normal akışa devam

  # Öğretme (otomatik veya manuel):
  learner.learn(raw_text, pure_stripped, action='skip', reason='phone_screen_junk')
  learner.save()
"""

import re
import json
import os
import threading
from datetime import datetime
from typing import Optional, Tuple, List, Dict

# ─── Veritabanı dosyası yolu ─────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, '_learned_skip_patterns.json')

# ─── Tag ismi çıkarma (ass_tags_database'e bağımlılık olmadan) ───────────────
_TAG_NAME_RE = re.compile(r'\\(\d?[a-zA-Z]+)(?=[\d&.(\\]|$)')
_TAG_BLOCK_RE = re.compile(r'\{([^}]*)\}')


def _extract_tag_names(raw_text: str) -> frozenset:
    """Ham ASS metninden tag isimlerini çıkar."""
    names = set()
    for blk in _TAG_BLOCK_RE.finditer(raw_text):
        for tag in _TAG_NAME_RE.finditer(blk.group(1)):
            names.add(tag.group(1).lower())
    return frozenset(names)


def _strip_tags(text: str) -> str:
    """Tag'leri soy, temiz metni döndür."""
    t = _TAG_BLOCK_RE.sub('', text)
    t = re.sub(r'\{[^}]*$', '', t)          # kapanmamış tag
    t = t.replace('\\N', ' ').replace('\\n', ' ').replace('\\h', ' ')
    return t.strip()


def _tag_text_ratio(raw_text: str, pure: str) -> float:
    """Tag karakter sayısı / metin karakter sayısı oranı."""
    tag_len = sum(len(m.group(0)) for m in re.finditer(r'\{[^}]*\}', raw_text))
    txt_len = len(pure) if pure else 1
    return tag_len / txt_len


# =============================================================================
# ANA SINIF
# =============================================================================

class AssSkipLearner:
    """
    Adaptif ASS satır pattern öğrenme motoru.
    Thread-safe, lazy-load, otomatik kayıt.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton — tüm pipeline aynı instance'ı paylaşır."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._loaded = False
            return cls._instance

    def _ensure_loaded(self):
        if self._loaded:
            return
        import ass_skip_learner as _m  # modül değişkenine dinamik eriş
        self._db: Dict = {'version': 1, 'patterns': [], 'text_patterns': []}
        self._dirty = False
        db_path = _m.DB_PATH  # singleton reset sonrası güncel path
        if os.path.exists(db_path):
            try:
                with open(db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict) and 'patterns' in data:
                    self._db = data
            except Exception:
                pass  # Bozuk dosya → boş başla
        self._loaded = True

    # ─────────────────────────────────────────────────────────────────────────
    # SORGULAMA — check()
    # ─────────────────────────────────────────────────────────────────────────

    def check(self, raw_text: str, pure_stripped: str = '') -> Tuple[Optional[str], str]:
        """
        Öğrenilmiş pattern'lerle satırı kontrol et.

        Returns:
            ('skip', reason)      → hiç metin yok / saf kod → direkt skip
            ('protect', reason)   → kod var ama metin de var → placeholder koru, çevir
            (None, '')            → öğrenilmiş pattern yok, normal sınıflandırmaya devam
        """
        self._ensure_loaded()
        if not raw_text:
            return None, ''

        pure = pure_stripped or _strip_tags(raw_text)
        tags = _extract_tag_names(raw_text)
        ratio = _tag_text_ratio(raw_text, pure)
        text_len = len(pure)

        # 1. Tag kombinasyon pattern'leri
        for p in self._db.get('patterns', []):
            if p.get('type') != 'tag_combo':
                continue
            req_tags = frozenset(p.get('tags', []))
            if not req_tags:
                continue
            max_len = p.get('max_text_len', 999)
            min_ratio = p.get('min_ratio', 0.0)
            action = p.get('action', 'skip')

            # Eşleşme: orüntüdeki tag'lerin en az %70'i bu satırda var mı?
            # (tam subset yerine overlap — benzer ama birebir aynı olmayan tag combolar da yakalanır)
            overlap = len(req_tags & tags)
            overlap_ratio = overlap / len(req_tags) if req_tags else 0.0
            if overlap_ratio < 0.70:
                continue

            if text_len <= max_len and (min_ratio == 0.0 or ratio >= min_ratio):
                # Hit! Sayacı artır
                p['hit_count'] = p.get('hit_count', 0) + 1
                self._dirty = True
                reason = f"learned:{p.get('reason', p['id'])}"
                return action, reason

        # 2. Metin regex pattern'leri
        for p in self._db.get('text_patterns', []):
            if p.get('type') != 'text_regex':
                continue
            try:
                if re.match(p['pattern'], pure):
                    action = p.get('action', 'skip')
                    p['hit_count'] = p.get('hit_count', 0) + 1
                    self._dirty = True
                    reason = f"learned:{p.get('reason', p['id'])}"
                    return action, reason
            except re.error:
                continue

        return None, ''  # Öğrenilmiş pattern yok

    # ─────────────────────────────────────────────────────────────────────────
    # ÖĞRENME — learn()
    # ─────────────────────────────────────────────────────────────────────────

    def learn(
        self,
        raw_text: str,
        pure_stripped: str,
        action: str = 'skip',
        reason: str = 'auto_learned',
        confidence: float = 0.85,
    ) -> Optional[str]:
        """
        Yeni bir pattern öğren ve DB'ye ekle.

        Args:
            raw_text:      Ham ASS satırı
            pure_stripped: Tag soyulmuş metin
            action:        'skip' | 'protect' (protect = metin var ama kodu koru)
            reason:        İnsan okunur açıklama
            confidence:    0.0-1.0

        Returns:
            Yeni pattern ID'si veya None (zaten var)
        """
        self._ensure_loaded()
        pure = pure_stripped or _strip_tags(raw_text)
        tags = list(_extract_tag_names(raw_text))
        text_len = len(pure)
        ratio = _tag_text_ratio(raw_text, pure)

        # Zaten aynı pattern var mı? (tag kombinasyonu + benzer text_len)
        for p in self._db.get('patterns', []):
            if p.get('type') != 'tag_combo':
                continue
            existing = frozenset(p.get('tags', []))
            new_tags = frozenset(tags)
            if existing == new_tags and abs(p.get('max_text_len', 0) - text_len) <= 3:
                # Güncelle
                p['hit_count'] = p.get('hit_count', 0) + 1
                p['action'] = action
                self._dirty = True
                return p['id']

        # Yeni pattern oluştur
        pid = f"lp_{len(self._db['patterns']) + 1:04d}"
        new_p = {
            'id': pid,
            'type': 'tag_combo',
            'tags': sorted(tags),
            'max_text_len': max(text_len, 3),
            'min_ratio': 0.0,  # ratio satırdan satıra değişir, kısıtlama yok
            'action': action,
            'reason': reason,
            'confidence': confidence,
            'hit_count': 1,
            'added': datetime.now().strftime('%Y-%m-%d'),
            'example': raw_text[:120],
        }
        self._db['patterns'].append(new_p)
        self._dirty = True
        return pid

    def learn_text_pattern(
        self,
        pattern: str,
        action: str = 'skip',
        reason: str = 'auto_text_pattern',
    ) -> Optional[str]:
        """
        Regex tabanlı metin pattern öğret.
        Örnek: learn_text_pattern(r'^[A-Z]{1,2}$', 'skip', 'single_letter_typeset')
        """
        self._ensure_loaded()
        # Zaten var mı?
        for p in self._db.get('text_patterns', []):
            if p.get('pattern') == pattern:
                p['hit_count'] = p.get('hit_count', 0) + 1
                self._dirty = True
                return p['id']

        pid = f"tp_{len(self._db['text_patterns']) + 1:04d}"
        new_p = {
            'id': pid,
            'type': 'text_regex',
            'pattern': pattern,
            'action': action,
            'reason': reason,
            'hit_count': 1,
            'added': datetime.now().strftime('%Y-%m-%d'),
        }
        self._db['text_patterns'].append(new_p)
        self._dirty = True
        return pid

    # ─────────────────────────────────────────────────────────────────────────
    # KAYDETME — save()
    # ─────────────────────────────────────────────────────────────────────────

    def save(self, force: bool = False):
        """DB'yi diske yaz (sadece değişiklik varsa)."""
        self._ensure_loaded()
        if not self._dirty and not force:
            return
        import ass_skip_learner as _m
        db_path = _m.DB_PATH
        try:
            with open(db_path, 'w', encoding='utf-8') as f:
                json.dump(self._db, f, ensure_ascii=False, indent=2)
            self._dirty = False
        except Exception as e:
            print('[AssSkipLearner] Kayit hatasi: %s' % e)

    def auto_save_if_dirty(self):
        """Pipeline sonu çağrısı — değişiklik varsa kaydet."""
        if self._dirty:
            self.save()

    # ─────────────────────────────────────────────────────────────────────────
    # İSTATİSTİK — stats()
    # ─────────────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        self._ensure_loaded()
        patterns = self._db.get('patterns', [])
        text_pats = self._db.get('text_patterns', [])
        return {
            'tag_combo_patterns': len(patterns),
            'text_patterns': len(text_pats),
            'total_hits': sum(p.get('hit_count', 0) for p in patterns + text_pats),
            'skip_patterns': sum(1 for p in patterns if p.get('action') == 'skip'),
            'protect_patterns': sum(1 for p in patterns if p.get('action') == 'protect'),
            'db_path': DB_PATH,
        }

    def list_patterns(self) -> List[dict]:
        self._ensure_loaded()
        return list(self._db.get('patterns', []))

    def remove_pattern(self, pid: str) -> bool:
        self._ensure_loaded()
        before = len(self._db['patterns'])
        self._db['patterns'] = [p for p in self._db['patterns'] if p['id'] != pid]
        if len(self._db['patterns']) < before:
            self._dirty = True
            return True
        return False


# =============================================================================
# GLOBAL INSTANCE (singleton)
# =============================================================================
_learner: Optional[AssSkipLearner] = None


def get_learner() -> AssSkipLearner:
    """Global singleton learner'ı döndür."""
    global _learner
    if _learner is None:
        _learner = AssSkipLearner()
    return _learner


# =============================================================================
# PIPELINE ENTEGRASYON YARDIMCILARI
# =============================================================================

def check_learned(raw_text: str, pure_stripped: str = '') -> Tuple[Optional[str], str]:
    """
    Tek satırlık pipeline entegrasyon fonksiyonu.

    Kullanım (ass_content_classifier.py içinde):
        action, reason = check_learned(raw_text, pure_stripped)
        if action == 'skip':
            return ClassificationResult('skip', reason, ...)
        elif action == 'protect':
            pass  # placeholder sistemi devreye girer, normal akış

    Returns:
        ('skip', reason) | ('protect', reason) | (None, '')
    """
    return get_learner().check(raw_text, pure_stripped)


def learn_and_save(raw_text: str, pure_stripped: str, action: str = 'skip',
                   reason: str = 'auto', auto_save: bool = True) -> Optional[str]:
    """
    Yeni pattern öğret ve opsiyonel olarak kaydet.
    Pipeline içinden otomatik çağrılabilir.
    """
    learner = get_learner()
    pid = learner.learn(raw_text, pure_stripped, action=action, reason=reason)
    if auto_save:
        learner.auto_save_if_dirty()
    return pid


def pipeline_end_save():
    """Subtitle dosyası işlendikten sonra çağrıl — DB'yi kaydet."""
    get_learner().auto_save_if_dirty()


# =============================================================================
# OTOMATİK ÖĞRENME — pipeline'dan tetiklenir
# =============================================================================

def auto_learn_from_classifier_result(
    raw_text: str,
    pure_stripped: str,
    classifier_action: str,
    classifier_reason: str,
):
    """
    ass_content_classifier sonuçlarından otomatik öğren.

    Hangi durumlar öğretilir:
      - 'tag_text_ratio_junk' → yeni tag combo skip pattern
      - 'offscreen_pos'       → off-screen sign → skip pattern
      - 'per_char_typeset'    → per-char variant → skip pattern
      - 'vector_clip_junk'    → clip junk variant → skip pattern

    Hangi durumlar öğretilmez:
      - Zaten bilinen kurallar (drawing, karaoke, style_skip...)
      - Çeviri kararları (translate, translate_sign) — bunlar doğru karar
    """
    AUTO_LEARN_REASONS = {
        'tag_text_ratio_junk': ('skip', 'tag_ratio_junk'),
        'offscreen_pos':       ('skip', 'offscreen_typeset'),
        'per_char_typeset':    ('skip', 'per_char_variant'),
        'vector_clip_junk':    ('skip', 'clip_junk_variant'),
    }

    # Reason prefix eşleştirmesi
    matched_action, matched_reason = None, None
    for key, (action, reason) in AUTO_LEARN_REASONS.items():
        if classifier_reason.startswith(key):
            matched_action, matched_reason = action, reason
            break

    if matched_action is None:
        return  # Öğrenilecek bir şey yok

    learn_and_save(
        raw_text=raw_text,
        pure_stripped=pure_stripped,
        action=matched_action,
        reason=matched_reason,
        auto_save=False,  # pipeline_end_save() toplu kaydeder
    )


# =============================================================================
# MODUL TESTİ
# =============================================================================
if __name__ == '__main__':
    import tempfile, shutil

    # Test için geçici DB
    _test_dir = tempfile.mkdtemp()
    import ass_skip_learner as _self
    original_db = _self.DB_PATH
    _self.DB_PATH = os.path.join(_test_dir, 'test_db.json')
    # Singleton reset
    AssSkipLearner._instance = None
    _learner = None

    learner = get_learner()

    print('=' * 60)
    print('ASS SKIP LEARNER — Test')
    print('=' * 60)

    # 1. Yeni pattern öğret
    raw1 = r'{\blur2\pos(960,50)\frz342\fscx150\fscy80\3c&H0&}AB'
    pure1 = 'AB'
    pid = learner.learn(raw1, pure1, action='skip', reason='test_junk')
    print(f'\n[LEARN] Pattern ID: {pid}')
    print(f'  Tags: blur, pos, frz, fscx, fscy, 3c')

    # 2. Aynı tür satırı kontrol et
    raw2 = r'{\blur1\pos(100,200)\frz10\fscx200\fscy100\3c&HFF&}XY'
    action, reason = learner.check(raw2, 'XY')
    chk = 'OK' if action == 'skip' else 'FAIL'
    print(f'\n[CHECK] Benzer satır → {action} ({reason})  [{chk}]')

    # 3. Gerçek metin olan satır öğrenilmemeli (farklı tag seti)
    raw3 = r'{\i1}Hello World, this is a real dialogue.'
    action3, reason3 = learner.check(raw3, 'Hello World, this is a real dialogue.')
    chk3 = 'OK' if action3 is None else 'FAIL'
    print(f'[CHECK] Gerçek diyalog → {action3} ({reason3})  [{chk3}]')

    # 4. Text pattern öğret
    learner.learn_text_pattern(r'^[A-Z]{1}$', 'skip', 'single_letter')
    action4, reason4 = learner.check(r'{\pos(100,50)}A', 'A')
    chk4 = 'OK' if action4 == 'skip' else 'FAIL'
    print(f'[CHECK] Tek harf "A" → {action4} ({reason4})  [{chk4}]')

    # 5. İstatistik
    print(f'\n[STATS] {learner.stats()}')

    # Temizle
    AssSkipLearner._instance = None
    _learner = None
    _self.DB_PATH = original_db
    shutil.rmtree(_test_dir)
    print('\nTüm testler tamamlandı.')
