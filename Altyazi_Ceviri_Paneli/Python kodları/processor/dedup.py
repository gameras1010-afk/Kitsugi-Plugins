"""
processor/dedup.py
==================
Tekilleştirme (deduplication) ve termbase uyum kontrolü.
"""
import re

_DEDUP_TAG_RE = re.compile(r'\{[^}]*\}')
_TB_SKIP_CATS = frozenset({"characters"})

def _get_dedup_key(event):
    """
    Bir event'in tekillestime anahtarini dondurur.
    ASS tag bloklari (__T0__ placeholder'lar ve {\\...} tag'leri) temizlenerek
    sadece saf metin karsilastirmasi yapilir.

    [FIX] tag'leri de temizle — farkli renk/pos/clip ile ayni metni gosteren
    satirlar (animasyon gradient katmanlari) artik ayni key'e dustugu icin
    DEDUP broadcast dogru calisir.
    """
    text = event.get("text", "")
    # Placeholder tag'leri kaldir (__T0__, __T1__ vb.)
    text = re.sub(r'__T\d+__', '', text)
    # ASS override tag bloklarini temizle {\\pos(...)\\blur...}
    text = _DEDUP_TAG_RE.sub('', text)
    # ASS ozel satir karakterlerini normalize et
    text = text.replace('\\N', ' ').replace('\\n', ' ').replace('\\h', ' ')
    base_key = text.strip().lower()
    return base_key


# ============================================
# TERMBASE UYUM KONTROLÜ
# ============================================
# Karakterler (characters) hariç — lokasyon, yetenek, organizasyon, terim
# kategorilerindeki EN→TR eşlemesi olan terimlerin çeviride doğru
# kullanılıp kullanılmadığını kontrol eder.
_TB_SKIP_CATS = frozenset({"characters"})   # bu kategoriler MUAF

def _check_termbase_compliance(src_text: str, tr_text: str, tb_lookup: dict) -> tuple:
    """
    Kaynak metindeki termbase terimlerinin çeviride doğru kullanılıp
    kullanılmadığını kontrol eder.

    Parametreler:
        src_text  : AI'ye gönderilen orijinal (İngilizce) metin
        tr_text   : AI'den gelen Türkçe çeviri
        tb_lookup : {en_lower: (tr, cat)} şeklinde flat sözlük
                    (karakterler dahil DEĞİL — _TB_SKIP_CATS muaf tutulur)

    Döndürür:
        (ok: bool, missed: list[tuple[en_original, tr_expected]])
        ok=True  → tüm zorunlu terimler doğru çevrilmiş
        ok=False → en az bir terim çeviride yanlış/eksik
    """
    if not tb_lookup or not src_text or not tr_text:
        return True, []

    src_lower = src_text.lower()
    tr_lower  = tr_text.lower()

    # Çok yaygın veya çok kısa İngilizce tek kelimeleri kontrol etme (false-positive önlemek için)
    _common_words = {"time", "day", "night", "world", "hand", "side", "head", "mind", "life", "part", "place", "work", "back", "year", "week", "say", "go", "get", "make", "know", "see", "come", "think", "look", "want", "give", "use", "find"}

    missed = []
    for en_key, (tr_val, cat) in tb_lookup.items():
        # Muaf kategoriler
        if cat in _TB_SKIP_CATS:
            continue
        # Türkçe karşılığı yoksa veya EN ile aynıysa kontrol etme
        if not tr_val or tr_val.lower() == en_key:
            continue
        # Çok kısa veya yaygın tek kelimeleri ele
        if len(en_key) <= 4 or en_key in _common_words:
            continue

        # Kaynak metinde bu İngilizce terim geçiyor mu?
        # Tam kelime eşleşmesi (word boundary) — kısa terimler yanlış tetiklemesin
        import re as _re_tb
        _pat = r'(?<![a-zA-Z])' + _re_tb.escape(en_key) + r'(?![a-zA-Z])'
        if not _re_tb.search(_pat, src_lower):
            continue
        # Çeviride Türkçe karşılığı var mı? (Ek biçimleri serbest bırakıldı)
        _tr_pat = r'(?<![a-zA-ZÇĞİÖŞÜçğışöüa-z])' + _re_tb.escape(tr_val.lower())
        if not _re_tb.search(_tr_pat, tr_lower):
            missed.append((en_key, tr_val))

    return (len(missed) == 0), missed


def _build_tb_lookup_from_prefs(prefs: dict) -> dict:
    """
    prefs['_tb_lookup'] varsa direkt döndürür.
    Yoksa prefs['_tb_data'] (cat→{en:tr}) yapısından flat sözlük üretir.
    Döndürür: {en_lower: (tr_val, category)} dict
    """
    # Önce hazır flat lookup'u dene
    _existing = prefs.get("_tb_lookup_flat")
    if _existing and isinstance(_existing, dict):
        return _existing

    tb_data = prefs.get("_tb_data", {})
    if not tb_data:
        return {}

    flat = {}
    for cat, mapping in tb_data.items():
        if cat in _TB_SKIP_CATS:
            continue
        if not isinstance(mapping, dict):
            continue
        for en, tr in mapping.items():
            if en and tr:
                flat[en.lower()] = (tr, cat)

    # Cache'e yaz — her satırda yeniden üretme
    prefs["_tb_lookup_flat"] = flat
    return flat




