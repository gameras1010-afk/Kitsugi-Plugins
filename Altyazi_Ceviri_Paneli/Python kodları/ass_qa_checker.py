#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ass_qa_checker.py — Post-Çeviri Kalite Doğrulama + Rescue Pass
===============================================================
subtitle_processor.py tarafından çağrılır. Ayrıca standalone çalışır.

Kullanım (modül):
    from ass_qa_checker import run_qa_rescue_pass
    qa_stats = run_qa_rescue_pass(subs, en_file, translator, prefs, output_path, report)

Kullanım (standalone):
    python ass_qa_checker.py TR_DOSYA EN_DOSYA
"""

import os, re, sys, json, time
from typing import Optional, List, Dict, Tuple

# ── Base dir ──────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))

# ── Modül yükleme (lazy, graceful) ───────────────────────────────────────────
try:
    from ass_content_classifier import classify_line as _classify_line
    _ACC_OK = True
except Exception:
    _ACC_OK = False
    def _classify_line(text, style_name='', **kw):
        class _R:
            action = 'translate'; reason = 'fallback'; confidence = 0.5
        if re.search(r'\\p[1-9]', text): _R.action = 'skip'
        elif re.search(r'\\k[oKF]?\d+', text, re.I): _R.action = 'skip'
        return _R()

try:
    from tr_lang_detector import turkish_score as _turkish_score
    _TLD_OK = True
except Exception:
    _TLD_OK = False
    def _turkish_score(t): return 0.5

try:
    from romaji_detector import style_is_definitely_romaji as _rom_style_jp
    _ROM_OK = True
except Exception:
    _ROM_OK = False
    def _rom_style_jp(s): return False

try:
    from romaji_filter import is_romaji_sentence as _is_romaji_sentence
    _RF_OK = True
except Exception:
    _RF_OK = False
    def _is_romaji_sentence(t): return False

try:
    from translation_verifier import verify_translation as _verify_tr
    _VER_OK = True
except Exception:
    _VER_OK = False
    _verify_tr = None

try:
    from subtitle_processor import is_song_style_name as _song_style_fn
    _SONG_OK = True
except Exception:
    _SONG_OK = False
    def _song_style_fn(s): return any(k in s.lower() for k in ('sing','song','kara','music','lyric'))

try:
    import pysubs2 as _pysubs2
    _PS_OK = True
except ImportError:
    _pysubs2 = None
    _PS_OK = False

# ── Renk çıktısı (colorama) ──────────────────────────────────────────────────
try:
    from colorama import Fore, Style
    _COL = True
except ImportError:
    _COL = False
    class _Dummy:
        GREEN=YELLOW=CYAN=RED=RESET_ALL=MAGENTA=WHITE=''
    Fore = Style = _Dummy()

# ── Glossary yükleme (kelimeler + cümle seti) ────────────────────────────────
_PNOUNS_CACHE:  Dict[str, set]       = {}   # kelime seti
_PHRASES_CACHE: Dict[str, frozenset] = {}   # cümle seti (küçük harf)

def _load_pnouns(anime_title: str, extra: list = None) -> set:
    """
    Kelime seti ve cümle seti yükler.
    Kaynaklar (öncelik sırasıyla):
      1. Termbase: EN=TR olanlar → gerçek özel isimler (Elucidator, Aincrad vb.)
      2. series_glossary.json: Fandom cache
      3. Evrensel Japonca/kısaltmalar
    """
    if anime_title in _PNOUNS_CACHE:
        return _PNOUNS_CACHE[anime_title]

    pn      = set()
    phrases = set()

    # ── 1. Termbase'den özel isimleri yükle (EN=TR → çevrilmez) ─────────────
    try:
        from termbase_manager import _split_title_season, TERMBASE_DIR as _TB_DIR
        import json as _json
        _clean_title, _snum = _split_title_season(anime_title)
        _safe = re.sub(r'[^a-z0-9]', '_', _clean_title.lower())[:50].rstrip('_')

        for _fname in os.listdir(_TB_DIR):
            if _fname.startswith(_safe) and _fname.endswith('.json'):
                try:
                    _path = os.path.join(_TB_DIR, _fname)
                    _data = _json.load(open(_path, encoding='utf-8'))
                    # 1. Terms
                    if isinstance(_data, dict) and 'terms' in _data:
                        for cat, mp in _data['terms'].items():
                            for en, tr in mp.items():
                                if en.lower().strip() == tr.lower().strip():
                                    tl = en.lower().strip()
                                    phrases.add(tl)
                                    pn.add(tl)
                                    for w in re.findall(r'[a-zA-Z]+', tl):
                                        if len(w) >= 2:
                                            pn.add(w)
                    # 2. Characters
                    if isinstance(_data, dict) and 'characters' in _data:
                        for entry in _data['characters']:
                            for part in re.findall(r'[A-Za-z][a-z]+', str(entry)):
                                if len(part) >= 3:
                                    pn.add(part.lower())
                    # 3. Flat dict (legacy/overrides)
                    if isinstance(_data, dict) and 'terms' not in _data and 'characters' not in _data:
                        for en, tr in _data.items():
                            if isinstance(tr, str) and en.lower().strip() == tr.lower().strip():
                                tl = en.lower().strip()
                                phrases.add(tl)
                                pn.add(tl)
                                for w in re.findall(r'[a-zA-Z]+', tl):
                                    if len(w) >= 2:
                                        pn.add(w)
                except Exception:
                    pass
    except Exception:
        pass


    # ── 2. series_glossary.json'dan oku ─────────────────────────────────────
    gpath = os.path.join(_HERE, 'series_glossary.json')
    if os.path.exists(gpath):
        try:
            data  = _json.load(open(gpath, 'r', encoding='utf-8')) \
                    if '_json' in dir() else \
                    json.load(open(gpath, 'r', encoding='utf-8'))
            title_stripped = _clean_title.lower().replace(' ','').replace('-','')

            best_entry = None
            best_terms = 0
            for k, v in data.items():
                k_clean = k.lower().replace(' ','').replace('-','')
                term_cnt = sum(len(lst) for lst in v.get('terms',{}).values())
                if k_clean == title_stripped and term_cnt > best_terms:
                    best_entry = v
                    best_terms = term_cnt

            if best_entry:
                for cat, lst in best_entry.get('terms', {}).items():
                    for term in lst:
                        t = term.strip()
                        if not t: continue
                        tl = t.lower()
                        phrases.add(tl)
                        pn.add(tl)
                        for w in re.findall(r"[a-zA-Z'\\-]+", tl):
                            if len(w) >= 2:
                                pn.add(w)
                                pn.add(w.replace('-','').replace("'",''))
        except Exception:
            pass

    # ── 3. Evrensel eklemeler ────────────────────────────────────────────────
    _univ = {'sensei','senpai','chan','kun','san','sama','hai',
             'ok','tv','pc','dvd','cm','bgm','op','ed','mc','sns'}
    pn.update(_univ)
    phrases.update(_univ)
    if extra:
        pn.update(w.lower() for w in extra)
        phrases.update(w.lower() for w in extra)

    _PNOUNS_CACHE[anime_title]  = pn
    _PHRASES_CACHE[anime_title] = frozenset(phrases)
    return pn



def _load_phrases(anime_title: str) -> frozenset:
    """Cümle setini döndürür (eğer _load_pnouns çağrıldıysa hazırdır)."""
    if anime_title not in _PHRASES_CACHE:
        _load_pnouns(anime_title)
    return _PHRASES_CACHE.get(anime_title, frozenset())


# ── Yardımcı: temizleme ───────────────────────────────────────────────────────
_TAG_RE = re.compile(r'\{[^}]*\}')

def _strip(t: str) -> str:
    return _TAG_RE.sub('', t).replace('\\N', ' ').replace('\\n', ' ').strip()

def _dedup_key(t: str) -> str:
    return _strip(t).lower()

def _all_pnouns(text: str, pn: set, phrases: frozenset = None) -> bool:
    """
    Metnin tamamı özel isimlerden mi oluşuyor?
    2 Aşama:
    1. Çok kelimeli terimleri çıkar (Tokyo Blade, Aqua Hoshino vb.) — greedy, uzundan kısaya
    2. Kalan kısım sadece bilinen kelimelerden mi?
    """
    raw = text.strip()
    if not raw: return True
    raw_lower = raw.lower()

    # Aşama 1: Çok kelimeli phrase'leri çıkar
    if phrases:
        remaining = raw_lower
        for ph in sorted(phrases, key=len, reverse=True):  # en uzun önce
            if len(ph) >= 3 and ph in remaining:
                remaining = remaining.replace(ph, ' ')
        remaining = re.sub(r"[^a-z0-9\u00c0-\u024f]+", ' ', remaining).strip()
        if not remaining:
            return True
        rem_words = [w for w in remaining.split() if len(w) >= 2]
        if rem_words and all(w in pn for w in rem_words):
            return True

    # Aşama 2: Kelime bazında kontrol
    words = re.findall(r"[a-zA-Z]+", raw_lower)
    sig   = [w for w in words if len(w) >= 2]
    return bool(sig) and all(w in pn for w in sig)


_TR_COMMON_WORDS = frozenset([
    # Zamirler
    'ben','sen','o','biz','siz','onlar','benim','senin','onun','bizim',
    'sizi','bana','sana','bize','size','onu','bunu','beni','seni',
    # Temel kelimeler
    'bir','bu','su','ne','kim','var','yok','da','de','mi','mu','mu',
    'ama','ile','icin','kadar','gibi','daha','cok','az','bile','hep',
    'evet','hayir','tamam','peki','iyi','kotu','buyuk','kucuk','geri',
    've','veya','ya','hem','ise','ki','diye','olarak','artik','zaten',
    'yani','sonra','once','simdi','zaman','burada','orada','neden','nasil',
    # Fiiller (emir/genis/gecmis)
    'gel','git','ver','al','bak','dur','bekle','yap','de','bil','kal',
    'git','gel','bak','sor','san','tut','calis','gul','agla','sus',
    # Fiil cekimleri
    'istiyorum','gidiyorum','geliyorum','yapiyorum','biliyorum','goruyorum',
    'istedi','geldi','gitti','yapti','aldi','verdi','dedi','bildi','gordu',
    'yapabilirim','gidebilirim','gelebilirim','bilebilirim','gorebilirim',
    'yapamam','gidemem','gelemem','bilemem','goremem',
    'yapacak','gidecek','gelecek','bilecek','gorecek',
    # Yaygin isimler/zarflar
    'temelde','aslinda','belki','kesinlikle','tabii','elbette','mutlaka',
    'hemen','simdi','sonra','once','yine','tekrar','artik','hala','hic',
    'cok','biraz','fazla','daha','en','hem','bile','sadece','ancak',
    'nerede','nasil','neden','ne','kim','hangi','kac','ne kadar',
    # Selamlama/gunluk
    'selam','merhaba','hosgeldin','gule','sagol','tesekkur','ozur',
    'tamam','peki','hay','vay','aman','yahu','lan','be','ya','ha',
    # Ozel (bu projede gelen)
    'kalbini','yerdim','gibilerle','yapmak','bilmek','gelmek',
    'etmek','olmak','demek','gitmek','almak','vermek','bakmak',
])

_AI_REFUSE_PATTERNS = [
    'i am an ai', 'i\'m an ai', 'as an ai', 'i cannot translate',
    'i am unable', 'this line is already', 'already in turkish',
    'already translated', 'the text is already', 'this is already',
    'cannot provide', 'i apologize', 'i\'m sorry, but',
    're-translate', 'retranslate', 'this text is in turkish',
]

def _is_ai_refuse(text: str) -> bool:
    """AI'nin meta/refuse cevabi mi diye kontrol eder."""
    tl = text.strip().lower()
    return any(pat in tl for pat in _AI_REFUSE_PATTERNS)


# Rescue'ya hic gitmemesi gereken marker/kod satirlar
_SKIP_MARKER_RE = re.compile(
    r'^[#@]\d+$'           # #3, #13, @5 gibi kodlar
    r'|^\d+[.):]?$'         # 1, 2., 3: gibi sadece rakam
    r'|^[.!?,;:\-\'"]+$'    # Sadece noktalama
    r'|^[\u266a\u266b\u2605\u2606]+$'  # Sadece muzik notalari
)

def _is_skip_marker(text: str) -> bool:
    """Rescue'ya gitmemesi gereken kod/marker satirlari tespit eder."""
    raw = text.strip()
    return bool(_SKIP_MARKER_RE.match(raw))


def _is_valid_translation(original: str, translated: str) -> bool:
    """
    Ceviri sonucunu dogrular. Asagidaki durumlarda REJECT eder:
    1. ASS tag iceriyorsa ({\an8}, {\pos...} vb.)
    2. Orijinalin 3x'inden uzunsa (AI hallusinasyon)
    3. Cok satir iceriyorsa ama orijinal tek satirsa
    """
    if not translated or not translated.strip():
        return False
    # ASS tag kontrolu
    if re.search(r'\{\\[^}]+\}', translated):
        return False
    # Uzunluk kontrolu: ceviri orijinalin 3 katindan uzunsa red
    orig_len = len(original.strip())
    tr_len   = len(translated.strip())
    if orig_len > 0 and tr_len > orig_len * 3 and tr_len > 80:
        return False
    # Satir sayisi kontrolu: orijinal 1 satirsa ceviri 1-2 satir olmali
    orig_lines = original.count('\n') + 1
    tr_lines   = translated.count('\n') + 1
    if orig_lines == 1 and tr_lines > 3:
        return False
    return True


_COMMON_EN_WORDS_TO_TRANSLATE = frozenset({
    "yes", "no", "go", "stop", "wait", "look", "listen", "run", "come", 
    "help", "kill", "die", "left", "right", "please", "thanks", "hello", 
    "hi", "sorry", "sure", "why", "what", "who", "when", "where", "how", 
    "maybe", "perhaps", "indeed", "correct", "fine", "okay", "ok", 
    "good", "bad", "great", "awesome", "beautiful", "really", "seriously",
    "dammit", "shit", "fuck", "damn", "he", "she", "it", "they", "we",
    "you", "i", "me", "him", "her", "us", "them", "my", "your", "his",
    "our", "their", "this", "that", "these", "those", "here", "there",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "then", "now", "later", "never", "always", "sometimes", "often"
})

def _is_proper_noun_line(raw: str) -> bool:
    """
    Metnin sadece özel isimler, selamlamalar ve noktalama işaretlerinden
    oluşup oluşmadığını denetler (örn: "Yuuto!", "Hey, Issei!", "Rias-sama!").
    Çevrilmesi gereken genel İngilizce kelimeleri/zamirleri filtreler.
    """
    words = re.findall(r"[a-zA-Z]+", raw)
    if not words:
        return False
    allowed_particles = {"hey", "oh", "ah", "uh", "chan", "kun", "san", "sama"}
    for w in words:
        wl = w.lower()
        if wl in allowed_particles:
            continue
        if not w[0].isupper():
            return False
        if wl in _COMMON_EN_WORDS_TO_TRANSLATE:
            return False
    return True


def _is_turkish_ev(text: str, style: str, pn: set, phrases: frozenset = None) -> bool:
    raw = _strip(text)
    if not raw: return True
    if re.search(r'[ğşçöüıİĞŞÇÖÜ]', raw): return True  # Turkce ozel karakter
    if _is_proper_noun_line(raw): return True
    if _all_pnouns(raw, pn, phrases): return True
    if _rom_style_jp(style): return True
    if _is_romaji_sentence(raw): return True
    # Ozel karakter icermeyen yaygin Turkce kelimeleri kontrol et
    words_lc = [w.lower() for w in re.findall(r'[a-zA-Z]+', raw) if len(w) >= 2]
    if words_lc and all(w in _TR_COMMON_WORDS or w in pn for w in words_lc):
        return True
    sc = _turkish_score(raw)
    th = 0.12 if len(raw.split()) <= 2 else 0.18
    return sc >= th


# ── ANA FONKSİYON ─────────────────────────────────────────────────────────────
def run_qa_rescue_pass(
    pysubs2_subs,           # pysubs2.SSAFile objesi (bellekte, henüz değişebilir)
    en_file_path: str,      # Kaynak EN dosyası
    translator,             # subtitle_processor'daki translator nesnesi
    prefs: dict,
    output_path: str,       # TR çıktı dosyasının yolu (yeniden kaydetmek için)
    report=None,            # TranslationReport nesnesi (varsa)
    anime_title: str = '',
    verbose: bool = True,
) -> dict:
    """
    1. Bellekteki pysubs2 eventlerini tarar
    2. Hâlâ İngilizce kalan Dialogue satırlarını bulur
    3. DEDUP: aynı metni 1 kez çevirir, kopyalara yayar
    4. pysubs2_subs'u günceller ve output_path'e yeniden kaydeder
    5. TranslationReport'a QA verilerini yazar
    6. HTML raporun QA bölümünü günceller
    Returns: {'rescued':int, 'remaining':int, 'signs_missed':int, 'total_checked':int}
    """
    if pysubs2_subs is None:
        return {}

    _title = anime_title or prefs.get('media_title', '') or ''
    pn      = _load_pnouns(_title)
    phrases = _load_phrases(_title)

    # ── Termbase TR değerlerini bilinen Türkçe kelimelere ekle ───────────────
    # Tüm JSON dosyalarındaki (base, chars, overrides, season) TR karşılıklarını
    # pn setine ekler. Böylece çevrilmiş özel isimler/terimler Türkçe kabul edilir.
    try:
        from termbase_manager import _split_title_season, TERMBASE_DIR as _TB_DIR
        _ct, _sn = _split_title_season(_title)
        _safe2 = re.sub(r'[^a-z0-9]', '_', _ct.lower())[:50].rstrip('_')
        for _fname in os.listdir(_TB_DIR):
            if _fname.startswith(_safe2) and _fname.endswith('.json'):
                try:
                    _path = os.path.join(_TB_DIR, _fname)
                    _data = json.load(open(_path, encoding='utf-8'))
                    # 1. Terms
                    if isinstance(_data, dict) and 'terms' in _data:
                        for cat, mp in _data['terms'].items():
                            for _en, _tr in mp.items():
                                if isinstance(_tr, str):
                                    for _w in re.findall(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]+', _tr.lower()):
                                        if len(_w) >= 2:
                                            pn.add(_w)
                    # 2. Characters
                    if isinstance(_data, dict) and 'characters' in _data:
                        for _c in _data['characters'].values():
                            if isinstance(_c, str):
                                for _w in re.findall(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]+', _c.lower()):
                                    if len(_w) >= 2:
                                        pn.add(_w)
                    # 3. Flat dict (overrides)
                    if isinstance(_data, dict) and 'terms' not in _data and 'characters' not in _data:
                        for _key, _val in _data.items():
                            if isinstance(_val, str):
                                for _w in re.findall(r'[a-zA-ZğşçöüıİĞŞÇÖÜ]+', _val.lower()):
                                    if len(_w) >= 2:
                                        pn.add(_w)
                except Exception:
                    pass
    except Exception:
        pass


    # ── EN kaynak dosyasını yükle → timestamp bazında karşılaştırma ──────────
    # TR satır metni != EN satır metni ise → KESİN çevrilmiş (dil dedektörü gerek yok)
    _en_map: Dict[int, str] = {}   # start_ms → temiz EN metin
    if en_file_path and os.path.exists(en_file_path) and _PS_OK:
        try:
            _en_subs = _pysubs2.load(en_file_path, encoding='utf-8-sig')
            for _ev in _en_subs:
                if _ev.type == 'Dialogue':
                    _en_map[_ev.start] = _strip(_ev.text).strip().lower()
        except Exception:
            pass

    if verbose:
        print(f"{Fore.CYAN}\n   [QA-Rescue] Post-çeviri kalite kontrolü başlıyor...{Style.RESET_ALL}")
        print(f"   [QA-Rescue] Glossary: {len(pn)} kelime, {len(phrases)} çok kelimeli terim | "
              f"EN karşılaştırma: {len(_en_map)} satır yüklendi.")

    # ── Adım 1: Untranslated ve kaçırılan sign'ları bul ──────────────────────
    candidates_untr:  List[Tuple[object, str]] = []  # (ev_obj, clean_text)
    candidates_sign:  List[object]             = []  # Comment ama çevrilmesi gereken
    qa_untranslated_report = []
    qa_signs_report        = []

    for ev in pysubs2_subs:
        text  = ev.text
        style = ev.style

        # Comment → sadece sign tespiti
        if ev.type == 'Comment':
            raw = _strip(text)
            if not raw or len(raw) < 4: continue
            if _all_pnouns(raw, pn, phrases): continue
            if _song_style_fn(style) or _rom_style_jp(style): continue
            cr = _classify_line(text, style_name=style)
            if cr.action in ('translate', 'translate_sign'):
                if not _is_turkish_ev(text, style, pn, phrases):
                    candidates_sign.append(ev)
                    qa_signs_report.append({
                        'start': str(ev.start), 'style': style,
                        'text': text[:120], 'action': cr.action
                    })
            continue

        # Dialogue → ass_content_classifier ile sınıflandır
        cr = _classify_line(text, style_name=style)
        if cr.action == 'skip':
            continue

        raw = _strip(text)
        if not raw: continue
        if _is_skip_marker(raw): continue   # #3, #13, rakamlar vb. marker → atla
        if _all_pnouns(raw, pn, phrases): continue

        # ── EN KAYNAK KARŞILAŞTIRMASI (en güçlü kontrol) ──────────────────────
        # Aynı timestamp'deki EN metin ile karşılaştır.
        # TR metin != EN metin → KESİN çevrilmiş, rescue'ya ekleme.
        if _en_map:
            _en_src = _en_map.get(ev.start, '')
            _tr_raw = raw.strip().lower()
            if _en_src and _tr_raw and _tr_raw != _en_src:
                continue  # Farklı → zaten çevrilmiş, atla
        # ─────────────────────────────────────────────────────────────────────

        if not _is_turkish_ev(text, style, pn, phrases):
            sc = _turkish_score(raw)
            candidates_untr.append((ev, raw))
            qa_untranslated_report.append({
                'start': str(ev.start), 'style': style,
                'text': text[:120], 'score': round(sc, 3)
            })

    # ── Adım 2: Kaçırılan Sign'ları Dialogue'a dönüştür ve rescue'ya ekle ──
    if candidates_sign and prefs.get('qa_rescue_signs', True):
        for _sev in candidates_sign:
            raw = _strip(_sev.text)
            if raw:
                _sev.type = 'Dialogue'       # Comment → Dialogue yaparak aktif et
                candidates_untr.append((_sev, raw))

    total_checked = len(candidates_untr)

    if verbose:
        if total_checked == 0:
            print(f"{Fore.GREEN}   [QA-Rescue] ✓ Tüm satırlar çevrilmiş — kurtarma gerekmedi.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}   [QA-Rescue] {total_checked} çevrilmemiş satır bulundu → kurtarma başlıyor...{Style.RESET_ALL}")
            print(f"   [QA-Rescue] {len(candidates_sign)} kaçırılan sign Dialogue'a dönüştürüldü.")

    if total_checked == 0 or translator is None:
        # Raporu güncelle ve dön
        _finalize_qa_report(report, output_path, qa_untranslated_report,
                            qa_signs_report, [], pysubs2_subs)
        return {'rescued': 0, 'remaining': 0, 'signs_missed': len(candidates_sign),
                'total_checked': 0}

    # ── Adım 3: DEDUP — Aynı metni grupla, tek temsilci çevir ────────────────
    dedup: Dict[str, List[object]] = {}  # clean_key → [ev_obj, ...]
    for ev, clean in candidates_untr:
        key = clean.strip().lower()
        if key not in dedup:
            dedup[key] = []
        dedup[key].append(ev)

    unique_items = [(key, group[0], group) for key, group in dedup.items()]
    skipped_dedup = total_checked - len(unique_items)

    if verbose and skipped_dedup > 0:
        print(f"{Fore.GREEN}   [QA-DEDUP] {skipped_dedup} kopya birleştirildi "
              f"({len(unique_items)} unique metin çevrilecek){Style.RESET_ALL}")

    # ── Adım 4: Unique metinleri çevir ───────────────────────────────────────
    rescued     = 0
    still_en    = 0
    qa_vfail    = []

    for clean_key, rep_ev, group in unique_items:
        raw_text = _strip(rep_ev.text)
        try:
            translated = translator.translate_single_line(raw_text, retries=3)
        except Exception as ex:
            if verbose:
                print(f"{Fore.RED}     [QA-Rescue] HATA '{raw_text[:30]}': {ex}{Style.RESET_ALL}")
            still_en += len(group)
            time.sleep(0.5)
            continue

        if not translated or translated.strip().lower() == raw_text.strip().lower():
            if verbose:
                print(f"{Fore.CYAN}     [QA-Rescue] Değişmedi: '{raw_text[:40]}'{Style.RESET_ALL}")
            still_en += len(group)
            time.sleep(0.5)
            continue

        # AI meta/refuse cevabi filtrele
        if _is_ai_refuse(translated):
            if verbose:
                print(f"{Fore.YELLOW}     [QA-Rescue] AI refuse \u2192 orijinal korunuyor: '{raw_text[:35]}'{Style.RESET_ALL}")
            still_en += len(group)
            time.sleep(0.5)
            continue

        # Ceviri gecerlilik kontrolu: ASS tag, 3x uzunluk, cok satir
        if not _is_valid_translation(raw_text, translated):
            if verbose:
                print(f"{Fore.RED}     [QA-Rescue] GECERSIZ ceviri (tag/uzunluk) → red: '{raw_text[:30]}' → '{translated[:40]}'{Style.RESET_ALL}")
            still_en += len(group)
            time.sleep(0.5)
            continue

        # Çeviri başarılı → tüm grup event'lerine yay
        for ev in group:
            # Tag'leri koru: orijinal tag'leri çeviri sonucunun başına ekle
            orig_tags = _TAG_RE.findall(ev.text)
            prefix = ''.join(orig_tags)
            ev.text = prefix + translated if prefix else translated

        rescued += len(group)
        if verbose:
            print(f"{Fore.GREEN}     [QA-Rescue OK] '{raw_text[:35]}' → '{translated[:35]}'"
                  f" (+{len(group)-1} kopya){Style.RESET_ALL}")
        time.sleep(0.8)  # Rate limit koruması

    # ── Adım 5: Değişikliklerle birlikte yeniden kaydet ──────────────────────
    if rescued > 0 and output_path and _PS_OK:
        try:
            pysubs2_subs.save(output_path, encoding='utf-8-sig')
            if verbose:
                print(f"{Fore.GREEN}   [QA-Rescue] Dosya yeniden kaydedildi: "
                      f"{os.path.basename(output_path)} "
                      f"({rescued} satır düzeltildi){Style.RESET_ALL}")
        except Exception as ex:
            if verbose:
                print(f"{Fore.RED}   [QA-Rescue] Kayıt hatası: {ex}{Style.RESET_ALL}")

    # Özet
    if verbose:
        print(f"{Fore.CYAN}   [QA-Rescue] Sonuç: {rescued}/{total_checked} kurtarıldı, "
              f"{still_en} hâlâ İngilizce{Style.RESET_ALL}")

    # ── Adım 6: Rapor verilerini doldur ve HTML'e enjekte et ─────────────────
    _finalize_qa_report(report, output_path, qa_untranslated_report,
                        qa_signs_report, qa_vfail, pysubs2_subs)

    return {
        'rescued':      rescued,
        'remaining':    still_en,
        'signs_missed': len(candidates_sign),
        'total_checked': total_checked,
    }


def _finalize_qa_report(report, output_path, untr_list, signs_list, vfail_list, pysubs2_subs):
    """QA verilerini TranslationReport'a yaz ve HTML'e enjekte et."""
    if report is None:
        return
    try:
        # Genel istatistikler
        total_tr = len([e for e in pysubs2_subs if e.type != 'Comment']) if pysubs2_subs else 0
        report.set_qa_untranslated(untr_list)
        report.set_qa_signs_missed(signs_list)
        report.set_qa_verify_fail(vfail_list)
        report.set_qa_stats({
            'total_tr': total_tr,
            'total_en': 0,           # EN sayısı burada bilinmiyor, rapor sonradan güncellenebilir
            'ok':       total_tr - len(untr_list),
            'proper':   0,
            'skip':     0,
            'untranslated': len(untr_list),
            'signs':    len(signs_list),
            'vfail':    len(vfail_list),
        })

        # HTML rapor mevcut mu? Enjekte et
        if output_path:
            rpath = re.sub(r'\.ass$', '', output_path, flags=re.IGNORECASE) + '.report.html'
            if os.path.exists(rpath):
                _inject_qa_html(rpath, report)
    except Exception as ex:
        pass  # Rapor hatası pipeline'ı durdurmasın


def _inject_qa_html(report_path: str, report) -> None:
    """Mevcut HTML raporuna QA bölümünü ekle veya güncelle. JSON'ı da günceller."""
    try:
        from translation_report import TranslationReport
        qa_html = report._build_qa_section()
        if not qa_html:
            return

        with open(report_path, 'r', encoding='utf-8') as f:
            html = f.read()

        QA_S  = '<!-- POST-ÇEVİRİ KALİTE DOĞRULAMA (QA) -->'
        QA_E  = '<!-- /QA -->'
        FOOT  = 'Otomatik Altyazı Çeviri Motoru'

        # Önceki QA bölümünü sil
        if QA_S in html:
            s = html.find(QA_S)
            e = html.find(QA_E)
            if e != -1:
                html = html[:s] + html[e + len(QA_E):]

        qa_block = f"\n{QA_S}\n{qa_html}\n{QA_E}\n"

        if FOOT in html:
            html = html.replace(FOOT, qa_block + '  ' + FOOT, 1)
        else:
            html = html.replace('</div>\n</body>', qa_block + '\n</div>\n</body>', 1)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"{Fore.CYAN}   [QA-Rapor] HTML raporuna QA bölümü eklendi.{Style.RESET_ALL}")

        # ── JSON companion dosyasını da güncelle ──────────────────────────────
        json_path = report_path.replace('.report.html', '.report.json')
        if os.path.exists(json_path):
            try:
                existing = json.load(open(json_path, encoding='utf-8'))
                existing['qa_stats']        = report.qa_stats
                existing['qa_untranslated'] = report.qa_untranslated
                existing['qa_signs_missed'] = report.qa_signs_missed
                existing['qa_verify_fail']  = report.qa_verify_fail
                with open(json_path, 'w', encoding='utf-8') as jf:
                    json.dump(existing, jf, ensure_ascii=False, indent=2)
                print(f"{Fore.CYAN}   [QA-Rapor] JSON raporu da güncellendi.{Style.RESET_ALL}")
            except Exception:
                pass


    except Exception as ex:
        print(f"   [QA-Rapor] HTML enjeksiyon hatası: {ex}")


# ── Standalone çalışma (C:\tmp_ass_compare.py ile aynı işlev) ────────────────
if __name__ == '__main__':
    import subprocess, sys as _sys
    _args = _sys.argv[1:]
    if len(_args) >= 2:
        tr_f, en_f = _args[0], _args[1]
    else:
        tr_f = r"D:\Anime\Oshi no Ko - S03\[CrappySubs] Oshi no Ko - S03E11 - (WEB 1080p H.265 AAC) [ACF82930].tr.ass"
        en_f = r"D:\Anime\Oshi no Ko - S03\Çevrilenler\[CrappySubs] Oshi no Ko - S03E11 - (WEB 1080p H.265 AAC) [ACF82930]_track2_eng.ass"

    # Standalone modda sadece analiz + rapor (rescue olmadan - translator yok)
    _sys.path.insert(0, _HERE)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    if not _PS_OK:
        print("pysubs2 bulunamadı!"); _sys.exit(1)

    import json as _json
    _anime   = 'Oshi no Ko'
    _pn      = _load_pnouns(_anime)
    _phrases = _load_phrases(_anime)

    from translation_report import TranslationReport
    _report = TranslationReport(source_file=en_f)
    _report.output_file = tr_f

    _subs = _pysubs2.load(tr_f, encoding='utf-8-sig')
    _untr = []; _signs = []

    for _ev in _subs:
        _text  = _ev.text
        _style = _ev.style
        if _ev.type == 'Comment':
            _raw = _strip(_text)
            if not _raw or len(_raw) < 4: continue
            if _all_pnouns(_raw, _pn, _phrases): continue
            if _song_style_fn(_style) or _rom_style_jp(_style): continue
            _cr = _classify_line(_text, style_name=_style)
            if _cr.action in ('translate','translate_sign') and not _is_turkish_ev(_text, _style, _pn, _phrases):
                _signs.append({'start':str(_ev.start),'style':_style,'text':_text[:120],'action':_cr.action})
            continue
        _cr = _classify_line(_text, style_name=_style)
        if _cr.action == 'skip': continue
        _raw = _strip(_text)
        if not _raw or _all_pnouns(_raw, _pn, _phrases): continue
        if not _is_turkish_ev(_text, _style, _pn, _phrases):
            _untr.append({'start':str(_ev.start),'style':_style,'text':_text[:120],'score':round(_turkish_score(_raw),3)})

    _report.set_qa_untranslated(_untr)
    _report.set_qa_signs_missed(_signs)
    _report.set_qa_verify_fail([])
    _report.set_qa_stats({
        'total_tr': len([e for e in _subs if e.type != 'Comment']),
        'total_en': 0, 'ok': len([e for e in _subs if e.type != 'Comment']) - len(_untr),
        'proper': 0, 'skip': 0,
        'untranslated': len(_untr), 'signs': len(_signs), 'vfail': 0,
    })

    _rpath = re.sub(r'\.ass$', '', tr_f, flags=re.IGNORECASE) + '.report.html'
    if os.path.exists(_rpath):
        _inject_qa_html(_rpath, _report)
        print(f"HTML raporu güncellendi: {_rpath}")
    else:
        _report.finalize(output_file=tr_f, duration_sec=0, mode='EN', series_title=_anime)
        _saved = _report.save()
        print(f"Yeni rapor oluşturuldu: {_saved}")

    print(f"\nÖzet:")
    print(f"  ❌ Çevrilmemiş : {len(_untr)}")
    print(f"  💬 Kaçırılan   : {len(_signs)}")
