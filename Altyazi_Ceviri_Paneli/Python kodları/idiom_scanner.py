# idiom_scanner.py
# ─────────────────────────────────────────────────────────────────────────────
# İngilizce deyim/atasözü tarayıcısı.
# englishidioms paketinin phrases.json veritabanını (22,000+ deyim) kullanarak
# alt yazı satırlarını tarar ve bulunan deyimlerin İngilizce tanımlarını döndürür.
#
# Bu tanımlar translator.py'ye prompt ek bağlamı olarak verilir:
#   "Bu satırda 'beat around the bush' deyimi var. Anlamı: dolambaçlı konuşmak."
# Böylece Gemini deyimi anlamıyla çevirir, kelimesi kelimesine değil.
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import json
import time
from typing import Dict, List, Optional

# ── Ahocorasick: En hızlı çok-kalıp eşleştirme (O(n), FlashText'ten de hızlı) ──────────────
try:
    import ahocorasick
    _HAS_AHOCORASICK = True
except ImportError:
    _HAS_AHOCORASICK = False

# ── Flashtext ile hızlı çok-kalıp eşleştirme (fallback) ────────────────────────────
try:
    from flashtext import KeywordProcessor
    _HAS_FLASHTEXT = True
except ImportError:
    _HAS_FLASHTEXT = False

# ── Deyim veritabanı yolu: önce englishidioms paket dizini, sonra yerel kopyası ──
def _find_phrases_json() -> Optional[str]:
    """englishidioms paketindeki phrases.json'ı bulur."""
    # 0) PyInstaller frozen EXE — sys._MEIPASS altında
    import sys
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', '')
        candidate = os.path.join(meipass, 'englishidioms', 'phrases.json')
        if os.path.isfile(candidate):
            return candidate

    # 1) Kurulu paket dizini
    try:
        import importlib.util
        spec = importlib.util.find_spec("englishidioms")
        if spec and spec.submodule_search_locations:
            pkg_dir = list(spec.submodule_search_locations)[0]
            candidate = os.path.join(pkg_dir, "phrases.json")
            if os.path.isfile(candidate):
                return candidate
    except Exception:
        pass

    # 2) Uygulama dizininde yerel kopya
    local = os.path.join(os.path.dirname(__file__), "phrases.json")
    if os.path.isfile(local):
        return local

    return None


def _parse_phrases_json(path: str) -> Dict[str, str]:
    """
    phrases.json'ı ayrıştırır.
    englishidioms paketi formatı: {"dictionary": [{id, phrase, definition}, ...]}
    """
    result = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        # englishidioms formatı: {"dictionary": [...]}
        entries = data.get("dictionary") or data.get("idioms") or data.get("phrases", [])
        if not entries and isinstance(data, list):
            entries = data

        for item in entries:
            if not isinstance(item, dict):
                continue
            phrase = item.get("phrase") or item.get("idiom") or item.get("expression") or ""
            defn   = item.get("definition") or item.get("meaning") or item.get("translation") or ""
            if not phrase or not defn:
                continue

            # Parantez/dagger/yıldız gibi notasyonları temizle:
            # "pick someone up†" → "pick someone up"
            # "able to breathe (easily) again" → hem orijinal hem variant'ı ekle
            phrase_clean = re.sub(r"[†‡*]", "", phrase).strip()
            phrase_clean = re.sub(r"\s+", " ", phrase_clean)

            # Parantez içi opsiyonel kısımları kaldır: "pick (someone) up" → "pick up" de ekle
            phrase_nopar = re.sub(r"\s*\([^)]*\)\s*", " ", phrase_clean).strip()
            phrase_nopar = re.sub(r"\s+", " ", phrase_nopar)

            # someone/something gibi placeholder'ları kaldır
            phrase_noplh = re.sub(
                r"\b(someone|something|one's|someone's|an animal|a person|anyone)\b",
                "", phrase_clean, flags=re.IGNORECASE
            ).strip()
            phrase_noplh = re.sub(r"\s+", " ", phrase_noplh)

            # Tüm varyantları ekle
            for p in {phrase_clean.lower(), phrase_nopar.lower(), phrase_noplh.lower()}:
                p = p.strip()
                if len(p) >= 4 and p not in result:
                    result[p] = str(defn)

    except Exception as e:
        print(f"[IdiomScanner] phrases.json okunurken hata: {e}")

    return result


# ── Ön belle k ────────────────────────────────────────────────────────────────────────────────
_IDIOM_DB: Optional[Dict[str, str]] = None          # {phrase_lower: definition}
_KEYWORD_PROCESSOR: Optional[object] = None         # FlashText KeywordProcessor (fallback)
_AHO_AUTOMATON: Optional[object] = None             # Ahocorasick automaton (primer backend)
_DB_SIZE: int = 0


def _ensure_loaded() -> bool:
    """Deyim veritabanını (gerekirse) yükler. Başarı durumunda True döner."""
    global _IDIOM_DB, _KEYWORD_PROCESSOR, _AHO_AUTOMATON, _DB_SIZE

    if _IDIOM_DB is not None:
        return bool(_IDIOM_DB)

    path = _find_phrases_json()
    if not path:
        print("[IdiomScanner] phrases.json bulunamadı, tarama devre dışı.")
        _IDIOM_DB = {}
        return False

    t0 = time.time()
    _IDIOM_DB = _parse_phrases_json(path)
    _DB_SIZE = len(_IDIOM_DB)
    elapsed = time.time() - t0

    backend = 'fallback-substr'

    # Öncelik 1: pyahocorasick (O(n), en hızlı)
    if _HAS_AHOCORASICK and _IDIOM_DB:
        try:
            _AHO_AUTOMATON = ahocorasick.Automaton()
            for phrase, defn in _IDIOM_DB.items():
                _AHO_AUTOMATON.add_word(phrase, (phrase, defn))
            _AHO_AUTOMATON.make_automaton()
            backend = 'Ahocorasick (O(n))'
        except Exception:
            _AHO_AUTOMATON = None

    # Öncelik 2: FlashText (varsa)
    if _AHO_AUTOMATON is None and _HAS_FLASHTEXT and _IDIOM_DB:
        _KEYWORD_PROCESSOR = KeywordProcessor(case_sensitive=False)
        for phrase in _IDIOM_DB:
            _KEYWORD_PROCESSOR.add_keyword(phrase)
        backend = 'FlashText'

    print(f"[IdiomScanner] {_DB_SIZE} deyim yüklendi ({elapsed:.2f}s) | backend: {backend}")
    return bool(_IDIOM_DB)


def _clean_line(text: str) -> str:
    """ASS tag'lerini, placeholder'ları ve özel karakterleri temizler."""
    text = re.sub(r"\{[^}]*\}", "", text)          # {\\i1} gibi ASS tag'ler
    text = re.sub(r"__(?:T\d+|NL|SL|HS)__", " ", text)  # placeholder'lar
    text = text.replace("\\N", " ").replace("\\n", " ").replace("\\h", " ")
    return text.strip()


_IRREG_PAST = {
    # En sık düzensiz fiiller (geçmiş zaman → infinitive)
    "was": "be", "were": "be", "been": "be",
    "had": "have", "has": "have",
    "did": "do", "done": "do",
    "went": "go", "gone": "go",
    "came": "come",
    "got": "get", "gotten": "get",
    "took": "take", "taken": "take",
    "made": "make",
    "said": "say",
    "saw": "see", "seen": "see",
    "knew": "know", "known": "know",
    "gave": "give", "given": "give",
    "left": "leave",
    "kept": "keep",
    "let": "let",
    "put": "put",
    "ran": "run",  "run": "run",
    "sat": "sit",
    "stood": "stand",
    "told": "tell",
    "thought": "think",
    "caught": "catch",
    "brought": "bring",
    "found": "find",
    "held": "hold",
    "hit": "hit",
    "lost": "lose",
    "met": "meet",
    "paid": "pay",
    "sent": "send",
    "set": "set",
    "shot": "shoot",
    "showed": "show", "shown": "show",
    "spent": "spend",
    "threw": "throw", "thrown": "throw",
    "won": "win",
    "wore": "wear", "worn": "wear",
    "beat": "beat", "beaten": "beat",
    "broke": "break", "broken": "break",
    "chose": "choose", "chosen": "choose",
    "cut": "cut",
    "drove": "drive", "driven": "drive",
    "fell": "fall", "fallen": "fall",
    "felt": "feel",
    "fought": "fight",
    "flew": "fly", "flown": "fly",
    "forgot": "forget", "forgotten": "forget",
    "froze": "freeze", "frozen": "freeze",
    "grew": "grow", "grown": "grow",
    "hid": "hide", "hidden": "hide",
    "lay": "lie",
    "led": "lead",
    "rode": "ride", "ridden": "ride",
    "rose": "rise", "risen": "rise",
    "sang": "sing", "sung": "sing",
    "sank": "sink", "sunk": "sink",
    "slept": "sleep",
    "spoke": "speak", "spoken": "speak",
    "stole": "steal", "stolen": "steal",
    "struck": "strike", "stricken": "strike",
    "swam": "swim", "swum": "swim",
    "swore": "swear", "sworn": "swear",
    "woke": "wake", "woken": "wake",
    "wrote": "write", "written": "write",
}

_VOWELS = set("aeiou")

def _word_base(word: str) -> str:
    """
    Basit kural tabanlı İngilizce stem/lemmatizer.
    'beating' → 'beat', 'kicked' → 'kick', 'runs' → 'run'.
    Düzensiz fiiller için önce sözlüğe bakılır.
    """
    w = word.lower()
    if w in _IRREG_PAST:
        return _IRREG_PAST[w]
    if len(w) <= 3:
        return w
    # -ing: beating→beat, running→run, making→make
    if w.endswith("ing") and len(w) > 5:
        stem = w[:-3]
        # doubled consonant: running→run
        if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in _VOWELS:
            return stem[:-1]
        # silent-e: making→make
        if len(stem) >= 2 and stem[-1] not in _VOWELS:
            return stem  # direct: beating→beat
        return stem + "e"
    # -ed: kicked→kick, walked→walk, pinned→pin
    if w.endswith("ed") and len(w) > 4:
        stem = w[:-2]
        if len(stem) >= 3 and stem[-1] == stem[-2] and stem[-1] not in _VOWELS:
            return stem[:-1]
        if stem.endswith("e"):
            return stem         # "hoped"→"hope"
        return stem
    # -s / -es: beats→beat, goes→go
    if w.endswith("es") and len(w) > 4 and w[-3] not in _VOWELS:
        return w[:-2]
    if w.endswith("s") and len(w) > 4 and not w.endswith("ss"):
        return w[:-1]
    return w


def _lemmatize_for_matching(text: str) -> str:
    """Her kelimeyi base form'a çevirir (sadece FlashText/substr eşleştirmesi için)."""
    return re.sub(r"[a-zA-Z]+", lambda m: _word_base(m.group()), text)


def _normalize_definition(defn: str, max_chars: int = 120) -> str:
    """Tanımı kısaltır ve Gemini için okunabilir hale getirir."""
    # Örnek cümlelerini çıkar (_ ile başlayan)
    defn = re.sub(r"_[^._]+\.", "", defn)
    # Figüratif/literal etiketlerini temizle
    defn = re.sub(r"\b(Fig|Lit|Prov|Rur|Sl|Cliché|Euph)\.\s*", "", defn)
    # Parantez içindeki açıklamaları kısalt
    defn = re.sub(r"\([^)]{40,}\)", "", defn)
    # Sayıları ve noktaları temizle (1. 2. gibi)
    defn = re.sub(r"^\s*\d+\.\s*", "", defn)
    # Fazla boşlukları temizle
    defn = " ".join(defn.split())
    return defn[:max_chars].rstrip(",;. ")


# ── Ana API ──────────────────────────────────────────────────────────────────

def scan_for_idioms(lines: List[str], max_idioms: int = 15) -> Dict[str, str]:
    """
    subtitle satırlarını tarar, bulunan deyimleri {phrase: definition} olarak döndürür.
    Fiil konjugasyonu sorunu çözüldü: 'beating around the bush' → 'beat around the bush'.

    Parametreler:
        lines: alt yazı satırları listesi (ASS tag'ları, placeholder'lar dahil)
        max_idioms: prompt'a enjekte edilecek maks. deyim sayısı

    Dönüş:
        {idiom_phrase: clean_definition} — boş dict: deyim bulunamadı
    """
    if not _ensure_loaded() or not _IDIOM_DB:
        return {}

    found: Dict[str, str] = {}

    clean_lines = [_clean_line(l) for l in lines]
    lemma_lines = [_lemmatize_for_matching(l) for l in clean_lines]

    if _AHO_AUTOMATON is not None:
        # Bircil: pyahocorasick — O(n) tarama (22,000+ deyim icin ideal)
        for raw, lemma in zip(clean_lines, lemma_lines):
            for src_text in (raw.lower(), lemma.lower()):
                for _, (phrase, defn) in _AHO_AUTOMATON.iter(src_text):
                    if phrase not in found:
                        found[phrase] = _normalize_definition(defn)
                    if len(found) >= max_idioms:
                        break
                if len(found) >= max_idioms:
                    break
            if len(found) >= max_idioms:
                break

    elif _HAS_FLASHTEXT and _KEYWORD_PROCESSOR:
        # Ikincil: FlashText (Ahocorasick yoksa)
        for raw, lemma in zip(clean_lines, lemma_lines):
            for src in (raw, lemma):
                for match in _KEYWORD_PROCESSOR.extract_keywords(src):
                    phrase_lower = match.lower()
                    if phrase_lower in _IDIOM_DB and phrase_lower not in found:
                        found[phrase_lower] = _normalize_definition(_IDIOM_DB[phrase_lower])
                    if len(found) >= max_idioms:
                        break
                if len(found) >= max_idioms:
                    break
            if len(found) >= max_idioms:
                break

    else:
        # Fallback: substring eslestirme (orijinal + lemmatize)
        clean_text = " ".join(clean_lines)
        lemma_text = _lemmatize_for_matching(clean_text)
        for text_src in (clean_text.lower(), lemma_text.lower()):
            for phrase, defn in _IDIOM_DB.items():
                if phrase not in found and f" {phrase} " in f" {text_src} ":
                    found[phrase] = _normalize_definition(defn)
                if len(found) >= max_idioms:
                    break
            if len(found) >= max_idioms:
                break

    return found



def build_idiom_context(idioms: Dict[str, str]) -> str:
    """
    Bulunan deyimleri Gemini'ye gönderilecek prompt bağlamına dönüştürür.

    Dönüş:
        Prompt'a eklenecek metin bloğu (boş ise boş string)
    """
    if not idioms:
        return ""

    lines = ["IDIOM CONTEXT (these expressions appear in this subtitle file):"]
    for phrase, defn in idioms.items():
        lines.append(f'- "{phrase}" means: {defn}')
    lines.append("Translate these idioms by their MEANING — do NOT translate word by word.")
    return "\n".join(lines)


# ── Test ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_lines = [
        "I'm in deep shit. Seriously deep shit!",
        "Stop beating around the bush already!",
        "She was at the end of her rope.",
        "That really adds fuel to the fire.",
        "We're between a rock and a hard place.",
        "You hit the nail on the head!",
        "Break a leg at the audition.",
        "He kicked the bucket last night.",
        "Pick me up at seven, okay?",
        "She let the cat out of the bag.",
    ]

    import time
    t0 = time.time()
    result = scan_for_idioms(test_lines)
    elapsed = time.time() - t0

    print(f"\n{'='*60}")
    print(f"Tarama süresi: {elapsed:.3f}s | Bulunan: {len(result)} deyim")
    print(f"{'='*60}")
    for p, d in result.items():
        print(f'  "{p}": {d}')

    print(f"\n--- Prompt Bağlamı ---")
    print(build_idiom_context(result))
