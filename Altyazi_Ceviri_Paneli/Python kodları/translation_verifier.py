"""
translation_verifier.py — Çeviri Kalite Doğrulama Modülü
=========================================================
Bir metnin gerçekten çeviri olup olmadığını çok sayıda
sinyal kullanarak doğrular:

  - Kaynak/hedef karakter benzerliği (çok benzer = çevrilmemiş)
  - Uzunluk oranı (TR genelde EN'den %10-40 uzun)
  - Sayı&özel isim koruması (3 → 3, Aqua → Aqua)
  - Türkçe morfoloji sinyali
  - Alfanümerik dağılım (sadece sembol = bozuk)
  - Unicode Türkçe karakter varlığı

Kullanım:
  from translation_verifier import verify_translation, TranslationResult

  result = verify_translation(source_en, candidate_tr)
  if result.is_valid:
      print("Çeviri geçerli")
  else:
      print(f"Sorun: {result.reason} (skor={result.score:.2f})")
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Yardımcı pattern'lar
# ─────────────────────────────────────────────────────────────

# Türkçe morfoloji — güçlü sonekler
_TR_MORPH = re.compile(
    r'(?:'
    # Zaman/kip ekleri
    r'iyor(?:um|sun|uz|lar|du|dum|dun)?|'
    r'ıyor(?:um|sun|uz|lar|du|dum)?|'
    r'uyor(?:um|sun|uz|lar|du)?|'
    r'üyor(?:um|sun|uz|lar)?|'
    r'acak(?:sın|lar|tı)?|ecek(?:sin|ler|ti)?|'
    r'acağım|eceğim|acaksın|eceksin|'
    r'mış|miş|muş|müş|'
    r'dım|dim|dum|düm|tım|tim|'
    r'malı|meli|malıyım|meliyim|'
    r'abilir|ebilir|'
    r'lar(?:ım|ın|ı)?|ler(?:im|in|i)?|'
    r'nda|nde|ndan|nden|ndaki|ndeki|'
    r'için|ile|kadar|'
    r'sinden|sından|'
    # ASCII versiyonlar (özel karakter olmadan)
    r'yorum|yorsun|yoruz|yordu|'
    r'ecegim|eceksin|acagim|acaksin|'
    r'meli|meliyim|'
    r'seviyorum|biliyorum|gordum|geldim|istiyorum'
    r')',
    re.IGNORECASE
)

# Sayı pattern'ı (korunmalı)
_NUMBER_RE = re.compile(r'\b\d+(?:[.,]\d+)?\b')

# Özel isim (büyük harfle başlayan kelime)
_PROPER_NOUN_RE = re.compile(r'\b[A-ZĞŞÇÖÜİ][a-zğşçöüı]{2,}\b')

# Türkçe özel karakter
_TR_CHARS_RE = re.compile(r'[ğşçöüıİĞŞÇÖÜ]')

# Draw command pattern (ASS vector drawing)
_DRAW_CMD_RE = re.compile(r'\bm\s+\d+\s+\d+\b')

# Random garbled string: yuksek buyuk-kucuk karismasi, sifir TR sinyal
_GARBLED_RE = re.compile(r'^[A-Za-z0-9]{8,}$')

# Küçük harf normalize
def _normalize(text: str) -> str:
    return re.sub(r'[^\w\s]', '', text.lower().replace('\u0131', 'i').replace('\u011f', 'g')
                  .replace('\u015f', 's').replace('\u00e7', 'c').replace('\u00f6', 'o').replace('\u00fc', 'u'))


# ─────────────────────────────────────────────────────────────
# Sonuç veri yapısı
# ─────────────────────────────────────────────────────────────

@dataclass
class TranslationResult:
    is_valid: bool
    score: float          # 0.0 = kesinlikle geçersiz, 1.0 = mükemmel
    reason: str           # Açıklama
    signals: dict = field(default_factory=dict)

    def __repr__(self):
        mark = '✅' if self.is_valid else '❌'
        return f"{mark} score={self.score:.2f} | {self.reason}"


# ─────────────────────────────────────────────────────────────
# Temel karakter benzerliği (Jaccard token)
# ─────────────────────────────────────────────────────────────

def _token_similarity(a: str, b: str) -> float:
    """Jaccard token benzerliği (0=farklı,1=aynı)."""
    if not a or not b:
        return 0.0
    ta = set(_normalize(a).split())
    tb = set(_normalize(b).split())
    if not ta and not tb:
        return 1.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _char_ngram_sim(a: str, b: str, n: int = 3) -> float:
    """N-gram karakter benzerliği."""
    def ngrams(s):
        s = _normalize(s)
        return set(s[i:i+n] for i in range(len(s) - n + 1))
    na, nb = ngrams(a), ngrams(b)
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return len(na & nb) / len(na | nb)


# ─────────────────────────────────────────────────────────────
# Ana doğrulama fonksiyonu
# ─────────────────────────────────────────────────────────────

def verify_translation(
    source: Optional[str],
    candidate: str,
    *,
    lang_score: float = 0.0,      # tr_lang_detector'dan gelen skor (varsa)
    min_word_count: int = 1,
    strict: bool = False,          # True = daha katı (çeviri hataları için)
    known_terms: Optional[set] = None,  # Fandom glossary kelime seti (özel isimler)
) -> TranslationResult:
    """
    Bir `candidate` metninin gerçek bir çeviri olup olmadığını doğrular.

    Args:
        source:       Kaynak metin (İngilizce). None ise kaynak karşılaştırması yapılmaz.
        candidate:    Hedef metin (Türkçe çeviri adayı).
        lang_score:   tr_lang_detector'dan gelen Türkçe dil skoru (0-1).
        min_word_count: Geçerli sayılmak için min kelime sayısı.
        strict:       True = daha sıkı kontrol (retry pass için).

    Returns:
        TranslationResult(is_valid, score, reason, signals)
    """
    signals = {}
    penalty = 0.0
    bonus   = 0.0

    cand = (candidate or '').strip()
    src  = (source or '').strip()

    # ── 0. Boş metin kontrolü
    if not cand:
        return TranslationResult(False, 0.0, 'empty_candidate', signals)

    cand_words = cand.split()
    if len(cand_words) < min_word_count:
        return TranslationResult(False, 0.05, 'too_short', signals)

    # ── 0b. Draw command veya garbled string tespiti
    draw_hits = len(_DRAW_CMD_RE.findall(cand))
    if draw_hits >= 2:
        return TranslationResult(False, 0.0, 'draw_command', signals)

    # Tek kelime, tümü ASCII, karmaşık büyük/küçük, hiç boşluk yok = garbled
    if _GARBLED_RE.match(cand.strip()):
        upper = sum(1 for c in cand if c.isupper())
        lower = sum(1 for c in cand if c.islower())
        if upper >= 2 and lower >= 2:  # karmaşık = rastgele string
            return TranslationResult(False, 0.0, 'garbled_random_string', signals)

    # ── 0c. Kaynak yok iken dil skoru çok düşük = geçersiz (EN kalmis)
    if not src and lang_score < 0.30:
        # Kaynak olmadan dogrulama yapamayiz, tr_lang_detector'a güven
        tr_chars = len(_TR_CHARS_RE.findall(cand))
        morph = len(_TR_MORPH.findall(cand))
        if tr_chars == 0 and morph == 0:
            # Hiçbir TR sinyali yok ve kaynak da yok → çevrilmemiş say
            return TranslationResult(False, 0.10, 'no_source_no_tr_signal', signals)

    if src:
        # [FIX] Glossary özel isim tespiti: kaynak tamamen bilinen terimlerden
        # oluşuyorsa ("Kirito", "Starburst Stream") similarity cezası verme.
        # AI bu terimleri doğru bıraktı — bu beklenen davranış.
        _src_words = set(re.findall(r'[a-zA-ZÀ-ɏ]+', src.lower()))
        _is_glossary_line = (
            bool(known_terms) and
            bool(_src_words) and
            _src_words.issubset(known_terms)
        )
        if _is_glossary_line:
            signals['glossary_proper_noun'] = True
            signals['verdict_sim'] = 'glossary_kept_unchanged'
            # Ceza verme, direkt geçerli say
            return TranslationResult(True, 0.85, 'glossary_proper_noun', signals)

        tok_sim = _token_similarity(src, cand)
        ngr_sim = _char_ngram_sim(src, cand, n=3)
        sim = (tok_sim * 0.6 + ngr_sim * 0.4)
        signals['source_similarity'] = round(sim, 3)

        if sim >= 0.90:
            # Neredeyse aynı → çevrilmemiş
            penalty += 0.80
            signals['verdict_sim'] = 'COPY (not translated)'
        elif sim >= 0.70:
            penalty += 0.40
            signals['verdict_sim'] = 'very_similar'
        elif sim >= 0.50:
            penalty += 0.15
            signals['verdict_sim'] = 'somewhat_similar'
        else:
            bonus += 0.20
            signals['verdict_sim'] = 'well_translated'

    # ── 2. Uzunluk oranı (TR genelde EN'den %10-40 uzun)
    if src:
        clen_src  = max(len(src), 1)
        clen_cand = len(cand)
        length_ratio = clen_cand / clen_src
        signals['length_ratio'] = round(length_ratio, 2)

        if 0.6 <= length_ratio <= 2.0:
            bonus += 0.10  # Makul aralık
        elif length_ratio < 0.4:
            penalty += 0.25
            signals['verdict_len'] = 'too_short_vs_source'
        elif length_ratio > 3.5:
            penalty += 0.15
            signals['verdict_len'] = 'too_long_vs_source'

        # Neredeyse aynı karakter sayısı + yüksek benzerlik = kopyala
        if abs(length_ratio - 1.0) < 0.05 and signals.get('source_similarity', 0) > 0.6:
            penalty += 0.20
            signals['verdict_len'] = 'same_length_same_content'

    # ── 3. Sayı koruması (2, 3, 100 gibi sayılar korunmalı)
    if src:
        src_nums  = set(_NUMBER_RE.findall(src))
        cand_nums = set(_NUMBER_RE.findall(cand))
        if src_nums:
            num_preserved = len(src_nums & cand_nums) / max(len(src_nums), 1)
            signals['number_preservation'] = round(num_preserved, 2)
            if num_preserved < 0.5 and len(src_nums) >= 2:
                penalty += 0.10  # Sayılar kaybolmuş → şüpheli

    # ── 4. Büyük harf özel isim koruması (Aqua, Ruby, Kana vb.)
    if src:
        src_proper  = {w.lower() for w in _PROPER_NOUN_RE.findall(src) if len(w) > 2}
        cand_proper = {w.lower() for w in _PROPER_NOUN_RE.findall(cand) if len(w) > 2}
        # Ortak özel isimler (karakter adları) korunmalı
        shared = src_proper & cand_proper
        signals['shared_proper_nouns'] = len(shared)
        if src_proper and len(src_proper) >= 2:
            pn_ratio = len(shared) / max(len(src_proper), 1)
            if pn_ratio < 0.3:
                penalty += 0.05  # Özel isimler kaybolmuş

    # ── 5. Alfanümerik oran (çok az harf = bozuk metin)
    alpha_ratio = sum(c.isalpha() for c in cand) / max(len(cand), 1)
    signals['alpha_ratio'] = round(alpha_ratio, 2)
    if alpha_ratio < 0.30:
        penalty += 0.40
        signals['verdict_alpha'] = 'mostly_symbols_or_numbers'
    elif alpha_ratio < 0.50:
        penalty += 0.15

    # ── 6. Türkçe özel karakter varlığı
    tr_char_count = len(_TR_CHARS_RE.findall(cand))
    signals['tr_char_count'] = tr_char_count
    if tr_char_count >= 3:
        bonus += 0.30
    elif tr_char_count >= 1:
        bonus += 0.15

    # ── 7. Türkçe morfoloji
    morph_hits = len(_TR_MORPH.findall(cand))
    signals['morph_hits'] = morph_hits
    if morph_hits >= 2:
        bonus += 0.30
    elif morph_hits == 1:
        bonus += 0.15

    # ── 8. Dil skoru (tr_lang_detector'dan)
    if lang_score > 0:
        signals['lang_score'] = round(lang_score, 3)
        if lang_score >= 0.65:
            bonus += 0.35
        elif lang_score >= 0.35:
            bonus += 0.20
        elif lang_score >= 0.25:
            bonus += 0.10
        else:
            penalty += 0.10

    # ── 9. Sadece ASCII + sıfır morfoloji + yüksek kaynak benzerliği = kopyala
    if (tr_char_count == 0
            and morph_hits == 0
            and lang_score < 0.25
            and signals.get('source_similarity', 0) > 0.45):
        penalty += 0.30
        signals['verdict_overall'] = 'likely_copy'

    # ── Final skor
    base = 0.50
    final_score = max(0.0, min(1.0, base + bonus - penalty))
    signals['bonus'] = round(bonus, 3)
    signals['penalty'] = round(penalty, 3)

    threshold = 0.45 if strict else 0.38
    is_valid  = final_score >= threshold

    # Neden geçersiz?
    reason = 'ok'
    if not is_valid:
        if signals.get('verdict_sim') in ('COPY (not translated)', 'very_similar'):
            reason = 'not_translated_copy'
        elif signals.get('verdict_alpha') == 'mostly_symbols_or_numbers':
            reason = 'garbled_text'
        elif signals.get('verdict_len') == 'too_short_vs_source':
            reason = 'too_short'
        elif lang_score < 0.20 and tr_char_count == 0 and morph_hits == 0:
            reason = 'not_turkish'
        else:
            reason = 'low_confidence'

    return TranslationResult(is_valid, final_score, reason, signals)


# ─────────────────────────────────────────────────────────────
# Kaynak olmadan sadece hedef metin ile çalışan versiyon
# ─────────────────────────────────────────────────────────────

def verify_candidate_only(
    candidate: str,
    lang_score: float = 0.0,
    strict: bool = False,
) -> TranslationResult:
    """Kaynak metin olmadan sadece hedef metin ile doğrulama."""
    return verify_translation(
        source=None,
        candidate=candidate,
        lang_score=lang_score,
        strict=strict,
    )


# ─────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    try:
        from tr_lang_detector import turkish_score as _tr_score
    except ImportError:
        def _tr_score(t): return 0.0

    TESTS = [
        # (src_en, cand_tr, beklenen, aciklama)

        # ── Başarılı çeviriler
        ("Steer clear from me",
         "Benden uzak dur",
         True,  "EN sarki → TR çeviri OK"),

        ("Aqua's still being held prisoner by his mother's death",
         "Aqua, annesinin ölümünün esiri olmaya devam ediyor",
         True,  "Uzun dialog → TR çeviri OK"),

        ("I'm a fan of yours, Kana. You can drop the formalities.",
         "Senin hayranınım, Kana. Resmiyet gerekmez.",
         True,  "Dialog → TR OK"),

        ("Should I contact Miyako?",
         "Miyako ile iletişime geçmeli miyim?",
         True,  "Kisa soru → TR OK"),

        ("Born into this",
         "Bunun içine doğdum",
         True,  "Kisa sarki → TR OK"),

        ("Even if I grow weary of wishing",
         "Dilemekten yorulursam bile",
         True,  "Sarki → TR OK"),

        # ── Çevrilmemiş (kopya) tespiti
        ("Steer clear from me",
         "Steer clear from me",
         False, "Kopya — çevrilmemiş"),

        ("Should I contact Miyako?",
         "Should I contact Miyako?",
         False, "Kopya — çevrilmemiş"),

        ("I'm a fan of yours, Kana. You can drop the formalities.",
         "I'm a fan of yours, Kana. You can drop the formalities.",
         False, "Kopya — uzun"),

        # ── Çok benzer ama tam kopya değil
        ("Aqua's still being held prisoner",
         "Aqua's still held prisoner",  # Küçük fark
         False, "Neredeyse kopya"),

        # ── Bozuk/garbled metin
        ("Steer clear from me",
         "m 0 0 m 100 100 N m 0 0",
         False, "Draw command — bozuk"),

        ("Hello there",
         "8nclcAQlbkkH0",
         False, "Random string — bozuk"),

        # ── Kaynak yok (sadece hedef)
        (None, "Benden uzak dur",         True,  "Kaynak yok — TR OK"),
        (None, "Steer clear from me",     False, "Kaynak yok — EN kalma"),
        (None, "Bunun içine doğdum",      True,  "Kaynak yok — TR özel kar"),
        (None, "Or maybe already broken", False, "Kaynak yok — EN sarki"),
        (None, "Seninle konuşmak istiyorum", True, "Kaynak yok — TR morfoloji"),

        # ── Sayı koruması
        ("She was 16 years old",
         "16 yaşındaydı",
         True,  "Sayı korundu"),

        ("She was 16 years old",
         "She was 16 years old",
         False, "Kopya, sayı var ama çevrilmemiş"),
    ]

    ok = fail = 0
    print(f"\n{'='*74}")
    print(f"  TRANSLATION VERIFIER — Kapsamlı Test ({len(TESTS)} vaka)")
    print(f"{'='*74}\n")

    for src, cand, expected, desc in TESTS:
        ls = _tr_score(cand) if cand else 0.0
        result = verify_translation(src, cand, lang_score=ls)
        is_ok = (result.is_valid == expected)
        mark = 'OK' if is_ok else 'FAIL'
        if is_ok: ok += 1
        else: fail += 1
        exp_s = '✅' if expected else '❌'
        got_s = '✅' if result.is_valid else '❌'
        print(f"  [{mark}] {desc}")
        print(f"       src={repr(src[:35]) if src else 'None'!r}")
        print(f"       cnd={repr(cand[:40])}")
        print(f"       Beklenen={exp_s} | Gerçek={got_s} | skor={result.score:.2f} | {result.reason}")
        if not is_ok:
            print(f"       signals={result.signals}")
        print()

    print(f"{'='*74}")
    acc = 100 * ok / max(ok + fail, 1)
    print(f"  TOPLAM: {ok+fail} | ✅ {ok} OK | ❌ {fail} FAIL | Doğruluk: {acc:.1f}%")
    print(f"{'='*74}")
