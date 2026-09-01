"""
detector/freq_tools.py
======================
Frequency DB yükleme ve kelime skoru.
"""
import re, os, json, time
from typing import Optional, Tuple, List

"""
content_detector.py
====================
ASS/SSA altyazi dosyalarindan stil adina BAKMADAN icerik analizi ile:
  - Ingilizce sarki sozleri
  - Japonca romaji
  - Karaoke heceleri
  - Generic diyalog
  - Isaretler / efekt satirlari

Kelime veritabanlari (data/ dizini, _build_word_databases.py ile olusturulur):
  - data/english_words.txt.gz  — 345K+ Ingilizce (dwyl/english-words filtrelenmis)
  - data/romaji_words.txt.gz   — pykakasi + JLPT N5-N4 romaji
  - data/anime_romaji.txt      — Anime OP/ED ozel romaji listesi
  - data/eng_rom_overlap.txt   — Her iki listede olan cakisan kelimeler

Ihtiyari (pip) kutuphaneler — bulunursa kullanilir, yoksa fallback:
  - pykakasi   : Romaji normalizasyonu
  - jaconv     : Full-width/katakana normalize
  - lingua-language-detector : Kisa metin guclu dil tespiti

Kullanim:
    from content_detector import classify_event, classify_text, classify_style
"""

import re, os, gzip
from pathlib import Path
from typing import Tuple, List, Optional

# ── Ihtiyari kutuphaneler ─────────────────────────────────────────────────────
try:
    import pykakasi as _pykakasi
    _KKS = _pykakasi.kakasi()
    _PYKAKASI_OK = True
except ImportError:
    _KKS = None
    _PYKAKASI_OK = False

try:
    import jaconv as _jaconv
    _JACONV_OK = True
except ImportError:
    _jaconv = None
    _JACONV_OK = False

try:
    from lingua import Language as _LinguaLang, LanguageDetectorBuilder as _LDB
    _LINGUA_DETECTOR = (
        _LDB.from_languages(_LinguaLang.ENGLISH, _LinguaLang.JAPANESE)
        .with_minimum_relative_distance(0.1)
        .build()
    )
    _LINGUA_OK = True
except Exception:
    _LINGUA_DETECTOR = None
    _LINGUA_OK = False

# ── Veri dizini ───────────────────────────────────────────────────────────────
_DATA_DIR = Path(__file__).parent / 'data'

# ── Lazy-load: Buyuk kelime veritabanlari ─────────────────────────────────────
_EXT_ENGLISH: Optional[frozenset] = None   # 345K Ingilizce
_EXT_ROMAJI:  Optional[frozenset] = None   # pykakasi romaji (585k)
_EXT_ANIME:   Optional[frozenset] = None   # Anime romaji OP/ED
_EXT_OVERLAP: Optional[frozenset] = None   # cakisan kelimeler

# Frekans veritabanlari (lazy-load)
_ENGLISH_FREQ: Optional[dict] = None   # word -> count  (hermitdave en_50k)
_TURKISH_FREQ: Optional[dict] = None   # kelime -> count (hermitdave tr_50k)
_ANIME_NAMES:  Optional[frozenset] = None  # anime karakter isimleri
_MAX_EN_COUNT: int = 1              # EN frekans normalizasyonu icin
_MAX_TR_COUNT: int = 1              # TR frekans normalizasyonu icin

# wordfreq optional
try:
    from wordfreq import zipf_frequency as _wf_zipf
    _WORDFREQ_OK = True
except ImportError:
    _wf_zipf = None
    _WORDFREQ_OK = False


def _load_ext_databases():
    """data/ dizinindeki veritabanlari ilk cagirida yukler."""
    global _EXT_ENGLISH, _EXT_ROMAJI, _EXT_ANIME, _EXT_OVERLAP
    global _ENGLISH_FREQ, _TURKISH_FREQ, _ANIME_NAMES
    global _MAX_EN_COUNT, _MAX_TR_COUNT

    if _EXT_ENGLISH is not None:
        return  # Zaten yuklendi

    def _load_gz(p) -> frozenset:
        try:
            with gzip.open(p, 'rt', encoding='utf-8') as f:
                return frozenset(l.strip().lower() for l in f if l.strip() and not l.startswith('#'))
        except Exception:
            return frozenset()

    def _load_txt(p) -> frozenset:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                return frozenset(l.strip().lower() for l in f if l.strip() and not l.startswith('#'))
        except Exception:
            return frozenset()

    def _load_pkl(p) -> dict:
        try:
            import pickle as _pickle
            with open(p, 'rb') as f:
                return _pickle.load(f)
        except Exception:
            return {}

    # Mevcut DB'ler
    _EXT_ENGLISH = _load_gz(_DATA_DIR / 'english_words.txt.gz')
    _EXT_OVERLAP = _load_txt(_DATA_DIR / 'eng_rom_overlap.txt')
    _EXT_ANIME   = _load_txt(_DATA_DIR / 'anime_romaji.txt')

    # Yeni: romaji_corpus.txt.gz (585k kelime — eskisi 1KB'di!)
    _romaji_corpus = _load_gz(_DATA_DIR / 'romaji_corpus.txt.gz')
    if _romaji_corpus:
        _EXT_ROMAJI = _romaji_corpus
    else:
        _EXT_ROMAJI = _load_gz(_DATA_DIR / 'romaji_words.txt.gz')

    # Yeni: Frekans DB'leri
    _ENGLISH_FREQ = _load_pkl(_DATA_DIR / 'english_freq.bin')
    _TURKISH_FREQ = _load_pkl(_DATA_DIR / 'turkish_freq.bin')
    _MAX_EN_COUNT = max(_ENGLISH_FREQ.values()) if _ENGLISH_FREQ else 1
    _MAX_TR_COUNT = max(_TURKISH_FREQ.values()) if _TURKISH_FREQ else 1

    # Yeni: Anime isim DB
    _ANIME_NAMES = _load_gz(_DATA_DIR / 'anime_names.txt.gz')

    # Null safety
    if not _EXT_ENGLISH: _EXT_ENGLISH = frozenset()
    if not _EXT_ROMAJI:  _EXT_ROMAJI  = frozenset()
    if not _EXT_ANIME:   _EXT_ANIME   = frozenset()
    if not _EXT_OVERLAP: _EXT_OVERLAP = frozenset()
    if not _ENGLISH_FREQ: _ENGLISH_FREQ = {}
    if not _TURKISH_FREQ: _TURKISH_FREQ = {}
    if not _ANIME_NAMES:  _ANIME_NAMES  = frozenset()


def _en_freq_score(word: str) -> float:
    """EN frekans skoru: 0.0=nadir/yok, 1.0=cok yaygin. wordfreq fallback."""
    global _MAX_EN_COUNT
    if _ENGLISH_FREQ:
        count = _ENGLISH_FREQ.get(word.lower(), 0)
        if count > 0:
            import math
            return min(1.0, math.log10(count + 1) / math.log10(_MAX_EN_COUNT + 1))
    if _WORDFREQ_OK and _wf_zipf:
        try:
            z = _wf_zipf(word, 'en')
            return min(1.0, z / 8.0) if z > 0 else 0.0
        except Exception:
            pass
    return 0.0


def _tr_freq_score(word: str) -> float:
    """TR frekans skoru: 0.0=nadir/yok, 1.0=cok yaygin. wordfreq fallback."""
    global _MAX_TR_COUNT
    if _TURKISH_FREQ:
        count = _TURKISH_FREQ.get(word.lower(), 0)
        if count > 0:
            import math
            return min(1.0, math.log10(count + 1) / math.log10(_MAX_TR_COUNT + 1))
    if _WORDFREQ_OK and _wf_zipf:
        try:
            z = _wf_zipf(word, 'tr')
            return min(1.0, z / 8.0) if z > 0 else 0.0
        except Exception:
            pass
    return 0.0


def is_anime_name(word: str) -> bool:
    """Kelime bir anime karakter/baslik adi mi? (Proper noun — ne EN ne romaji say.)"""
    _load_ext_databases()
    w = word.strip().lower().rstrip('.,!?')
    if not w:
        return False
    return bool(_ANIME_NAMES and w in _ANIME_NAMES)


def is_turkish_word(word: str) -> bool:
    """Kelime Turkce kelime listesinde mi? TR frekans DB + Turkce karakter."""
    _load_ext_databases()
    w = word.strip().lower()
    if any(c in _TR_CHARS for c in w):
        return True
    if _TURKISH_FREQ and w in _TURKISH_FREQ:
        return True
    return False

def _normalize_text(text: str) -> str:
    """Full-width ve katakana karakterlerini normalize eder."""
    if _JACONV_OK and _jaconv:
        # Full-width alfanumerik → half-width
        text = _jaconv.z2h(text, kana=False, ascii=True, digit=True)
    return text

def _lingua_detect(text: str) -> Optional[str]:
    """lingua ile dil tespiti. 'english'/'japanese'/None doner."""
    if not _LINGUA_OK or not _LINGUA_DETECTOR:
        return None
    try:
        lang = _LINGUA_DETECTOR.detect_language_of(text)
        if lang is None:
            return None
        name = lang.name.lower()
        if name == 'english':
            return 'english'
        if name == 'japanese':
            return 'japanese'
        return name
    except Exception:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. INGILIZCE SARKI SOZU KELIME LISTESI
#    Kaynak: Google 10K (web termler, marka adlari, kisaltmalar cikarildi)
#    Ekleme: sarki sozu tipik sozcukler (forever, broken, whisper vb.)
# ─────────────────────────────────────────────────────────────────────────────

# 1a. KATI INGILIZCE — bunlarin 2+ tanesi varsa kesin Ingilizce
_HARD_ENGLISH = frozenset({
    # Zamirler
    'the','a','an','i','you','he','she','it','we','they','me','him','her',
    'us','them','my','your','his','its','our','their','mine','yours','ours',
    # Yardimci fiiller
    'is','are','was','were','be','been','being','have','has','had','do',
    'does','did','will','would','shall','should','may','might','must',
    'can','could','ought',
    # Baglaclar
    'and','but','or','nor','for','yet','so','although','because','since',
    'unless','until','while','though','even','either','neither',
    # Edatlar
    'in','on','at','by','to','of','for','with','from','into','onto','upon',
    'over','under','above','below','between','among','through','across',
    'after','before','during','without','within','toward','against',
    # Yaygin fiiller
    "don't","doesn't","can't","won't","isn't","aren't","wasn't","weren't",
    "i'm","i've","i'll","i'd","you're","you've","you'll","you'd",
    "it's","that's","there's","what's","who's","they're","we're",
})

# 1b. LYRICS INGILIZCE — sarkilarda cok gecen kelimeler
_LYRICS_ENGLISH = frozenset({
    # Sarki sozu temalar
    'love','heart','soul','dream','dreams','life','world','sky','night',
    'day','light','dark','darkness','hope','wish','star','stars','moon',
    'sun','wind','rain','fire','water','earth','flower','flowers',
    'road','path','way','journey','time','forever','never','always',
    'again','still','alone','together','apart','away','home','far',
    'near','close','deep','high','low','lost','found','broken','whole',
    'free','bound','rise','fall','fly','run','stay','go','come','leave',
    'reach','touch','hold','let','keep','find','seek','know','feel',
    'see','hear','cry','laugh','smile','pain','joy','fear','brave',
    'strong','weak','true','false','real','fake','alive','dead','born',
    'die','live','breathe','shine','glow','fade','burn','freeze','melt',
    'open','close','begin','end','start','stop','wait','trust','lie',
    'truth','vow','promise','memory','forget','remember','moment','voice',
    'song','music','beat','rhythm','silence','echo','whisper','call',
    'name','face','eye','eyes','hand','hands','wings','shadow','soul',
    'spirit','ghost','angel','devil','heaven','hell','fate','destiny',
    'chance','miracle','prayer','faith','grace','mercy','rage','storm',
    # Yaygin sifatlar
    'beautiful','lonely','empty','broken','shattered','endless','boundless',
    'infinite','eternal','fleeting','precious','sacred','forgotten','lost',
    'found','hidden','bright','pale','cold','warm','soft','hard','wild',
    'gentle','cruel','sweet','bitter','hollow','silent','loud','quiet',
    'faint','vivid','dim','clear','blurred','sharp','pure','tainted',
    # Yaygin zarflar
    'slowly','quickly','gently','softly','deeply','truly','hardly',
    'barely','merely','only','just','even','yet','still','already',
    'always','never','often','sometimes','once','twice','forever',
    'somewhere','nowhere','everywhere','anywhere','somehow','anyway',
    # Yaygin zarflar (devam)
    'again','now','then','here','there','where','when','why','how',
    # Kisiler
    'she','he','they','we','you','me','us','him','her',
    # Ek sarki kelimeleri
    'serenade','lullaby','melody','symphony','chorus','verse','refrain',
    'bittersweet','longing','yearning','desire','passion','ache','grief',
    'sorrow','regret','nostalgia','wistful','tender','fragile','fleeting',
    'transcend','surrender','embrace','shiver','tremble','wander','drift',
    'soar','descend','ascend','collapse','shatter','rebuild','restore',
    'vanish','appear','linger','remain','depart','return','escape',
    'pursue','abandon','cherish','mourn','celebrate','endure','survive',
    'overcome','yield','resist','accept','deny','question','answer',
    # Dogru cevap verecek kisa kelimeler
    'oh','ah','ooh','yeah','hey','no','yes','ok','okay','well',
    'so','now','but','and','for','all','any','some','more','most',
    'too','very','much','many','few','own','same','such','even',
    'once','else','over','back','away','down','up','off','out','in',
    'on','into','onto','upon','through','across','within','without',
    # Sanat/sarki terminolojisi
    'melody','verse','bridge','hook','chorus','ballad','anthem',
    'lyric','lyrics','rhythm','harmony','discord','resonance',
})

# Tum Ingilizce kelimelerin birlesimi
_ALL_ENGLISH = _HARD_ENGLISH | _LYRICS_ENGLISH

# ─────────────────────────────────────────────────────────────────────────────
# 2. ROMAJI KELIME / HECE VERITABANI
#    Kaynak: Hepburn romanizasyonu + JLPT N5-N4 + anime tipik sozcukler
# ─────────────────────────────────────────────────────────────────────────────

# 2a. Temel heceler (tum Japonca heceler Hepburn ile)
_ROMAJI_SYLLABLES = frozenset({
    # Tek vokal
    'a','i','u','e','o',
    # K satiri
    'ka','ki','ku','ke','ko','kya','kyu','kyo',
    # S satiri
    'sa','shi','si','su','se','so','sha','shu','sho','syi',
    # T satiri
    'ta','chi','ti','tsu','tsi','te','to','cha','chu','che','cho',
    # N satiri
    'na','ni','nu','ne','no','nya','nyu','nyo',
    # H satiri
    'ha','hi','fu','hu','he','ho','hya','hyu','hyo',
    # M satiri
    'ma','mi','mu','me','mo','mya','myu','myo',
    # Y satiri
    'ya','yu','yo',
    # R satiri
    'ra','ri','ru','re','ro','rya','ryu','ryo',
    # W satiri
    'wa','wi','we','wo',
    # G satiri (daku-on)
    'ga','gi','gu','ge','go','gya','gyu','gyo',
    # Z satiri
    'za','ji','zi','zu','ze','zo','ja','ju','jo','jya','jyu','jyo',
    # D satiri
    'da','di','du','de','do','dya','dyu','dyo',
    # B satiri
    'ba','bi','bu','be','bo','bya','byu','byo',
    # P satiri
    'pa','pi','pu','pe','po','pya','pyu','pyo',
    # N (ozel)
    'n','nn',
    # Geminate (cift unsuz)
    'kka','tte','ppe','sse','cchi',
    # Uzun vokal
    'aa','ii','uu','ee','oo','ou',
    # Katakana odunc sesler
    'fa','fi','fe','fo','va','vi','vu','ve','vo',
    'tsa','tse','tso','che','je','di','du','tu','ti',
})

# 2b. Yaygin Japonca sozcukler (romaji) — JLPT N5-N4 + anime tipik
_ROMAJI_WORDS = frozenset({
    # Zamirler
    'watashi','watakushi','boku','ore','atashi','uchi',
    'anata','anta','kimi','omae','kisama','kare','kanojo',
    'wareware','karera','kanojotachi',
    # Parcacilar
    'wa','ga','wo','ni','de','to','ka','mo','no','ne','yo',
    'na','naa','sa','zo','ze','ya','waa','noni','kedo','ga',
    # Zaman
    'ima','mae','ato','mada','motto','zutto','itsumo','naze',
    'itsuka','korekara','kinou','kyou','ashita','asa','hiru','yoru',
    'mainichi','毎日','toki','jikan','nagai','mijikai',
    # Yaygin fiiller (romaji)
    'iru','aru','suru','kuru','iku','miru','kiku','yomu','kaku','hanasu',
    'taberu','nomu','neru','okiru','shiru','omou','wakaru','dekiru',
    'naru','iru','kureru','ageru','morau','itadaku','kudasai',
    'itta','kita','shita','mita','deta','natta','nai','naku','nakatta',
    'shimau','shimatta','shite','shire','mitai','you','rashii','sou',
    # Yaygin isimler
    'hito','mono','koto','tokoro','toki','te','me','mimi','kuchi',
    'atama','kokoro','karada','namae','katachi','iro','koe','uta',
    'ai','koi','yume','kibou','chikara','negai','namida','egao',
    'hikari','kurayami','kage','kaze','tsuki','taiyou','sora','umi',
    'hana','sakura','yuki','hoshi','niji','ame','shizuku',
    'michi','tobira','tobira','me','te','sora','tsuchi','hi',
    # Sifatlar
    'ii','yoi','warui','ookii','chiisai','hayai','osoi','takai',
    'hikui','atsui','samui','atatakai','suzushii','kawaii','kirei',
    'utsukushii','yasashii','tsuyoi','yowai','hayai','tsumetai',
    'ureshii','kanashii','sabishii','tanoshii','kowai','muzukashii',
    'yasashii','omoi','karui','aoi','akai','shiroi','kuroi','kiiroi',
    # Anime tipik sozcukler
    'nakama','tomodachi','sensei','sempai','senpai','kouhai',
    'otousan','okaasan','otouto','oneesan','oniisan','imouto',
    'kazoku','minna','hitori','futari','issho','isshoni',
    'daijoubu','ganbatte','ganbarimasu','arigatou','sumimasen',
    'gomen','gomennasai','tadaima','okaerinasai','itadakimasu',
    'konnichiwa','konbanwa','ohayou','oyasumi','sayonara','mata',
    # Sarki sozlerinde cok gecen
    'kokoro','tamashii','inochi','sekai','mirai','kako','ima',
    'chikaidzu','chikakau','hanare','hanarete','wasurenai','wasureta',
    'omoide','kioku','shinjiru','shinjite','aishiteru','suki','daisuki',
    'kirai','hoshii','mitai','naiteru','waratte','utatte','odotte',
    'tobu','hashire','hashiru','mamorite','mamoru','yurusite','yuruse',
    'kizutsuku','iyasu','naosu','sagashite','mitsuketa','deaeta',
    'wakatte','wakatta','wakata','shitte','shitta','kiite','kiita',
    'mitte','mita','yonde','yonda','kite','kita','itte','itta',
    # Ek parcacilar / baglaclar
    'demo','dakedo','kara','made','dake','shika','hodo','bakari',
    'nado','toka','ya','to','si','shi','node','ので','ので',
    'sore','kore','are','dore','sono','kono','ano','dono',
    'soko','koko','asoko','doko','sochira','kochira','achira',
    'sorede','sorekara','soredemo','sorenoni','dakara','nazenara',
    # Geminate / ozel heceleme
    'tottemo','totemo','zuibun','nakanaka','mottomo','ichiban',
    'isshun','ippai','isshou','ikkai','isshoni','ittai','ittemo',
    # JLPT N5-N4 ek kelimeler
    'benkyou','shigoto','ryokou','ryouri','tenki','byouki',
    'kuruma','densha','hikouki','fune','jitensha',
    'uchi','ie','heya','niwa','mado','to','doa','kaidan',
    'eki','mise','gakkou','byouin','ginkou','yuubinkyoku',
    'eiga','hon','zasshi','shinbun','terebi','rajio',
    'tabemono','nomimono','kudamono','yasai','niku','sakana',
    'gohan','pan','ramen','sushi','tempura','miso','soba','udon',
    # Yaygin ifadeler (sarkilarda)
    'nee','naa','mou','yana','yada','iyana','saa','hora','anne',
    'etto','ano','uh','um','nani','nande','doushite','naze',
    'uso','honto','hontou','maji','masaka','yappari','yahari',
})

# Normalize edilmis setler (kucuk harf)
_ROMAJI_ALL_LOWER = frozenset(w.lower() for w in (_ROMAJI_SYLLABLES | _ROMAJI_WORDS))
_ENGLISH_ALL_LOWER = frozenset(w.lower().strip("'\".,!?;:") for w in _ALL_ENGLISH)
_HARD_ENG_LOWER = frozenset(w.lower() for w in _HARD_ENGLISH)

# ─────────────────────────────────────────────────────────────────────────────
# 3. ASS STIL ADI KALIP VERITABANI
#    Kaynak: fansubbing toplulugu derlemesi + araştirma
# ─────────────────────────────────────────────────────────────────────────────

# 3a. ŞARKI stillerini gsteren prefiks/sufiks
_SONG_STYLE_TOKENS = frozenset({
    # OP / ED / Insert
    'op','ed','ins','insert','opening','ending','oped',
    'op1','op2','op3','ed1','ed2','ed3','ins1','ins2',
    # Sarki/Karaoke isaretleri
    'song','lyric','lyrics','kara','karaoke','k','rom','romaji',
    'jp','jpn','japanese','nihon','en','eng','english',
    # Ses efekti
    'vocal','vox','choir','chorus','bgm','bgvocal',
    # Stil varyantlari
    'main','top','bot','bottom','up','down','mid','center',
    # Grup ismi ile gelen (turkce fansub vb.)
    'sub','tr','tur','turk','turkish','trk',
})

# 3b. GENERIC stil adlari (sarki olmayan)
_GENERIC_STYLE_TOKENS = frozenset({
    'default','dialogue','dialog','main','alt','alternative',
    'sign','signs','ts','typeset','note','notes','screen',
    'subtitle','captions','caption','text','info',
    'flash','effect','fx','animation','animated',
    'position','pos','title','header','footer',
    'staff','credit','credits','translation','tl',
    'comment','commentary','thought','internal',
    'overlap','overlap1','overlap2',
})

# 3c. KARAOKE stil gostergesi regex kaliplari
_KARA_STYLE_RE = re.compile(
    r'\b(?:kara(?:oke)?|k[-_]|[-_]kara|romaji|rom[-_]|[-_]rom|'
    r'furigana|furi|ruby|kanji|kanji[-_])\b',
    re.IGNORECASE
)

# 3d. OP/ED stil gostergesi
_OPED_STYLE_RE = re.compile(
    r'\b(?:op|ed|opening|ending|insert|ins|oped|ncop|nced|'
    r'op\d+|ed\d+|ins\d+|insert\d+)\b',
    re.IGNORECASE
)

# 3e. Dil gostergesi
_LANG_EN_RE  = re.compile(r'\b(?:en|eng|english|ingilizce)\b', re.IGNORECASE)
_LANG_JP_RE  = re.compile(r'\b(?:jp|jpn|japanese|nihon|nihongo|rom|romaji)\b', re.IGNORECASE)
_LANG_TR_RE  = re.compile(r'\b(?:tr|tur|turk(?:ish|ce)?|trk)\b', re.IGNORECASE)

# ─────────────────────────────────────────────────────────────────────────────
# 4. ICERIK TESPITI REGEX
# ─────────────────────────────────────────────────────────────────────────────

_ASS_TAG_RE      = re.compile(r'\{[^}]*\}')
_MUSIC_NOTE_RE   = re.compile(r'[♪♫~～]')
_KARAOKE_TAG_RE  = re.compile(r'\{[^}]*\\k[fo]?\d+[^}]*\}', re.IGNORECASE)
_DRAW_RE         = re.compile(r'\\p\s*[1-9]', re.IGNORECASE)
_CJK_RE          = re.compile(r'[\u3040-\u30FF\u4E00-\u9FFF\uFF00-\uFFEF]')
_APOSTROPHE_RE   = re.compile(r"[a-z]'[a-z]", re.IGNORECASE)
_LATIN_WORD_RE   = re.compile(r'[a-zA-Z]{2,}')

# Japonca fonotaktik regex
_JP_PHONOTACTIC = re.compile(
    r'^(?:'
    r'tsu|chi|shi|sha|shu|sho|cha|cho|chu|'
    r'nya|nyu|nyo|mya|myu|myo|rya|ryu|ryo|'
    r'hya|hyu|hyo|bya|byu|byo|pya|pyu|pyo|'
    r'kya|kyu|kyo|gya|gyu|gyo|'
    r'ja|ji|ju|jo|jya|jyu|jyo|'
    r'[kstpbmndghrzwfy][aeiou]|'
    r'[aeiou]|'
    r'n(?![aeiou])|nn|'
    r'[kstpbmndhrzwfy][aeiou][tnrs]?|'
    r'(?:aa|ii|uu|ee|oo|ou)'
    r')+$',
    re.IGNORECASE
)

# Ingilizce fonetik engel — 3+ unsuz art arda (Japonca'da olmaz)
_ENG_CONSONANT_CLUSTER = re.compile(r'[bcdfghjklmnpqrstvwxyz]{3,}', re.IGNORECASE)

# Turkce harfler
_TR_CHARS = set('ğşçöüıİĞŞÇÖÜ')

# ─────────────────────────────────────────────────────────────────────────────
# 5. ZAMAN YARDIMCISI
# ─────────────────────────────────────────────────────────────────────────────

def _ts_to_ms(ts: str) -> int:
    """'H:MM:SS.cs' → ms"""
    try:
        ts = str(ts).replace(',', '.')
        h, m, rest = ts.split(':')
        s, cs = rest.split('.')
        return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(cs)*10
    except Exception:
        return 0

# ─────────────────────────────────────────────────────────────────────────────
# 6. KELIME SKORLAMA
# ─────────────────────────────────────────────────────────────────────────────

# Kesin Japonca romaji kelimeler — kisa olduklari icin fonotaktik/DB yakalayamadigi durumlar
_HARD_ROMAJI_WORDS = frozenset({
    'nani','suki','dayo','kore','sore','are','dore','koko','soko',
    'dare','doko','itsu','naze','mou','mada','sugoi','kawaii','urusai',
    'baka','yabai','senpai','kouhai','nakama','yoroshiku','arigatou',
    'gomen','sumimasen','itadakimasu','tadaima','okaeri','ohayou',
    'oyasumi','konnichiwa','konbanwa','sayonara','muzukashii','tanoshii',
    'ureshii','kanashii','tsurai','samui','atsui','neko','inu','sakura',
    'tsuki','umi','yama','kawa','mizu','kaze','yoru','asa','ima',
    'mukashi','mirai','kokoro','tamashii','inochi','kibou','yume',
    'desu','masu','dewa','kara','made','toki','noni','kedo','keredo',
    'dakedo','demo','shikashi','soshite','sorekara','dakara','naraba',
    'nanka','nante','tte','tte iu','tte koto','tte ba','tte ba'
})

