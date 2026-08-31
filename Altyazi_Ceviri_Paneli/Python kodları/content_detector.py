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

def score_word(word: str) -> Tuple[float, str]:
    """
    Tek kelimeyi analiz eder — frekans tabanli yukseltilmis versiyon.
    Returns: (romaji_score 0.0-1.0, reason)
      1.0 = kesin romaji / Japonca
      0.0 = kesin Ingilizce
      0.5 = belirsiz
    """
    w = word.strip().lower().rstrip("'\".,!?;:")
    if not w:
        return 0.5, 'empty'

    # CJK karakteri varsa hic latin degil
    if _CJK_RE.search(w):
        return 1.0, 'cjk_char'

    # Turkce karakter varsa kesinlikle Ingilizce veya Romaji degil
    if any(c in _TR_CHARS for c in w):
        return 0.0, 'turkish_char'

    # Kesin Ingilizce (apostrophe = kesin Ingilizce kontraksiyonu)
    if _APOSTROPHE_RE.search(word):
        return 0.0, 'apostrophe'

    # Kesin Japonca romaji kelime (kisa ve cok ozgu)
    if w in _HARD_ROMAJI_WORDS:
        return 0.97, 'hard_romaji_word'

    # Kesin Ingilizce embedded listede (apostrop/cakisma olmadan)
    if w in _HARD_ENG_LOWER and w not in _ROMAJI_ALL_LOWER:
        return 0.0, 'hard_english'

    # Genisletilmis veritabanlarini yukle (lazy)
    _load_ext_databases()

    # ── ADIM 1: Anime karakter adi mi? → ne EN ne romaji say ──────────────────
    if _ANIME_NAMES and w in _ANIME_NAMES:
        return 0.50, 'anime_proper_noun'  # Belirsiz bırak (isim = dil degil)

    # ── ADIM 2: TR Frekans kontrolu — zaten Turkce mi? ────────────────────────
    tr_score = _tr_freq_score(w)
    if tr_score > 0.3:  # Turkce frekans DB'de belirgin
        return 0.0, f'turkish_freq({tr_score:.2f})'

    # ── ADIM 3: EN Frekans skoru ───────────────────────────────────────────────
    en_score = _en_freq_score(w)
    # Rom DB kontrolu (585k kelime!)
    in_rom_db  = bool((_EXT_ROMAJI and w in _EXT_ROMAJI) or
                      (_EXT_ANIME  and w in _EXT_ANIME))
    in_eng_db  = bool(_EXT_ENGLISH and w in _EXT_ENGLISH)
    in_overlap = bool(_EXT_OVERLAP and w in _EXT_OVERLAP)
    in_eng_emb = w in _ENGLISH_ALL_LOWER
    in_rom_emb = w in _ROMAJI_ALL_LOWER

    # Yuksek EN frekans + romaji listesinde degil → kesin Ingilizce
    if en_score > 0.45 and not in_rom_db and not in_rom_emb:
        return 0.02, f'english_score={en_score:.2f}'
    if en_score > 0.3 and not in_rom_db and not in_overlap:
        return 0.05, f'english_score={en_score:.2f}'

    # ── ADIM 4: Mevcut DB mantigi ──────────────────────────────────────────────
    in_eng = in_eng_emb or in_eng_db
    in_rom = in_rom_emb or in_rom_db

    if in_eng and not in_rom and not in_overlap:
        return 0.03, f'ext_english({"embed" if in_eng_emb else "db"})'
    if in_rom and not in_eng and not in_overlap:
        return 0.95, f'ext_romaji({"embed" if in_rom_emb else "db"})'
    if in_rom and in_overlap:
        return 0.45, 'overlap_word'
    if in_eng and in_rom:
        # Frekans farkiyla karar ver
        if en_score > 0.2:
            return 0.20, f'both_lists_en_wins({en_score:.2f})'
        return 0.40, 'both_ext_lists'
    if in_eng:
        return 0.05, 'ext_english_only'

    # ── ADIM 5: Fonetik analiz ─────────────────────────────────────────────────
    if _JP_PHONOTACTIC.match(w):
        if _ENG_CONSONANT_CLUSTER.search(w):
            return 0.35, 'phonotactic_with_cluster'
        return 0.80, 'phonotactic_jp'

    # Uzun + unsuz kumesi = Ingilizce
    if len(w) >= 5 and _ENG_CONSONANT_CLUSTER.search(w):
        return 0.08, 'eng_consonant_cluster'

    # Kisa kelime — belirsiz
    if len(w) <= 3:
        return 0.55, 'short_latin'

    # Buyuk harfle basliyorsa ve uzunsa = muhtemelen Ingilizce proper noun
    if word[0].isupper() and len(w) > 4:
        return 0.18, 'capitalized_long'

    # Hard romaji son kontrol
    _HARD_ROM = frozenset({
        'nani','suki','dayo','kore','sore','are','dore','koko','soko','asoko',
        'dare','doko','itsu','naze','doushite','nande','mou','mada',
        'sugoi','kawaii','urusai','baka','yabai','senpai','kouhai','nakama',
        'yoroshiku','arigatou','gomen','sumimasen','itadakimasu','tadaima',
        'okaeri','ohayou','oyasumi','konnichiwa','konbanwa','sayonara',
        'muzukashii','tanoshii','ureshii','kanashii','tsurai','samui','atsui',
        'neko','inu','sakura','hana','tsuki','hoshi','yoru','asa','hiru',
        'ima','mukashi','mirai','chotto','matte','hayaku','yukkuri',
        'daisuki','kirai','honto','uso','daijoubu','yokatta',
    })
    if w in _HARD_ROM:
        return 0.95, 'hard_romaji_word'

    return 0.5, 'uncertain'


def score_text_romaji(text: str) -> Tuple[float, str]:
    """
    Metnin genel romaji skoru — frekans tabanli.
    Returns: (score 0.0-1.0, detail_str)

    0.0 = kesin Ingilizce, 1.0 = kesin Romaji
    """
    # Full-width normalizasyonu (jaconv)
    text = _normalize_text(text)

    words = text.strip().split()
    if not words:
        return 0.5, 'empty'

    # Apostrophe varsa kesin Ingilizce
    if _APOSTROPHE_RE.search(text):
        return 0.02, 'apostrophe_in_text'

    # DB'leri yukle (lazy)
    _load_ext_databases()

    # Frekans tabanli EN yogunlugu hesapla — hard_eng + frekans DB
    _en_hits = 0
    _word_list = [w.lower().rstrip("'\".,!?;:") for w in words if w.strip()]
    for _w in _word_list:
        # Hard EN listesi
        if _w in _HARD_ENG_LOWER and _w not in _ROMAJI_ALL_LOWER:
            _en_hits += 1
            continue
        # Frekans DB: yuksek EN frekansi + romaji listesinde degil
        _enf = _en_freq_score(_w)
        if _enf > 0.35:
            _in_rom = ((_EXT_ROMAJI and _w in _EXT_ROMAJI) or
                       (_EXT_ANIME  and _w in _EXT_ANIME) or
                       _w in _ROMAJI_ALL_LOWER)
            if not _in_rom:
                _en_hits += 1

    if _en_hits >= 2:
        ratio = _en_hits / len(_word_list) if _word_list else 0
        return max(0.0, 0.05 - ratio * 0.02), f'en_freq_density={ratio:.2f}({_en_hits}hits)'

    scores = [score_word(w)[0] for w in words]
    avg = sum(scores) / len(scores)
    detail = f'avg={avg:.2f}|words={len(words)}'
    return avg, detail

# ─────────────────────────────────────────────────────────────────────────────
# 7. STIL ADI SINIFLANDIRICI
# ─────────────────────────────────────────────────────────────────────────────

def classify_style(style_name: str) -> Tuple[str, float, str]:
    """
    Stil adini siniflandirir.

    Returns:
        (category, confidence, reason)
        category: 'song_en' | 'song_jp' | 'song_unknown' |
                  'karaoke_en' | 'karaoke_jp' | 'karaoke_unknown' |
                  'generic' | 'dialog' | 'sign'
    """
    if not style_name:
        return ('generic', 0.3, 'no_style')

    s = style_name.lower()
    tokens = set(re.split(r'[-_\s]', s))
    tokens.discard('')

    # Ingilizce dil ipucu
    has_en = bool(_LANG_EN_RE.search(s))
    has_jp = bool(_LANG_JP_RE.search(s))
    has_tr = bool(_LANG_TR_RE.search(s))

    # Karaoke ipucu
    has_kara = bool(_KARA_STYLE_RE.search(s))

    # OP/ED ipucu
    has_oped = bool(_OPED_STYLE_RE.search(s))

    # Generic kontrol
    is_generic = bool(
        tokens <= _GENERIC_STYLE_TOKENS or
        all(t in _GENERIC_STYLE_TOKENS or t.isdigit() for t in tokens)
    )

    # Karar agaci
    if has_kara:
        if has_en:
            return ('karaoke_en', 0.95, f'kara+en in [{style_name}]')
        if has_jp:
            return ('karaoke_jp', 0.95, f'kara+jp in [{style_name}]')
        if has_oped:
            return ('karaoke_unknown', 0.75, f'kara+oped in [{style_name}]')
        return ('karaoke_unknown', 0.6, f'kara in [{style_name}]')

    if has_oped:
        if has_en:
            return ('song_en', 0.95, f'oped+en in [{style_name}]')
        if has_jp:
            return ('song_jp', 0.90, f'oped+jp in [{style_name}]')
        if has_tr:
            return ('song_unknown', 0.7, f'oped+tr in [{style_name}]')
        return ('song_unknown', 0.65, f'oped in [{style_name}]')

    if is_generic:
        return ('generic', 0.85, f'generic_tokens in [{style_name}]')

    # Song token var mi?
    song_tokens = tokens & _SONG_STYLE_TOKENS
    if song_tokens:
        if has_en:
            return ('song_en', 0.8, f'song_token+en in [{style_name}]')
        if has_jp:
            return ('song_jp', 0.8, f'song_token+jp in [{style_name}]')
        return ('song_unknown', 0.6, f'song_token in [{style_name}]')

    return ('dialog', 0.5, f'no_match for [{style_name}]')

# ─────────────────────────────────────────────────────────────────────────────
# 8. METIN ICERIK SINIFLANDIRICI
# ─────────────────────────────────────────────────────────────────────────────

def classify_text(
    raw_text: str,
    duration_ms: int = 0,
) -> Tuple[str, float, str]:
    """
    Metnin dilini ve tipini belirler.

    Returns:
        (lang, confidence, reason)
        lang: 'english' | 'romaji' | 'japanese' | 'turkish' | 'mixed' | 'effect_only' | 'unknown'
    """
    # Sadece ASS tag'i mi?
    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    if not clean:
        return ('effect_only', 1.0, 'no_text_after_tags')

    # Draw komutu (vektor cizim)
    if _DRAW_RE.search(raw_text):
        return ('effect_only', 0.9, 'draw_command')

    # Turkce mi? — kisa yol ve frekans DB kontrolu
    tr_count = sum(1 for c in clean if c in _TR_CHARS)
    if tr_count >= 2:
        return ('turkish', 0.95, f'tr_chars={tr_count}')
    # TR frekans DB ile Turkce tespiti (Turkce ozel karakter olmadan da calısir)
    if tr_count == 0 and len(clean) >= 6:  # TR ozel karakter yoksa
        _load_ext_databases()
        if _TURKISH_FREQ:
            _TR_SPECIFIC = set('ğşçöüıİĞŞÇÖÜ')
            _clean_words = re.findall(r"[a-zA-ZçğışöüÇĞİŞÖÜ']+", clean)
            if _clean_words:
                _tr_hits = 0
                for _cw in _clean_words:
                    if any(c in _TR_SPECIFIC for c in _cw):
                        _tr_hits += 2  # Ozel karakter = cok guclu sinyal
                    elif len(_cw) >= 5:
                        _trs = _tr_freq_score(_cw)
                        if _trs >= 0.60:
                            _tr_hits += 1
                _tr_ratio = _tr_hits / max(len(_clean_words), 1)
                if _tr_ratio >= 0.55:
                    return ('turkish', 0.85, f'tr_freq_ratio={_tr_ratio:.2f}')

    # CJK kanji/hiragana/katakana
    if _CJK_RE.search(clean):
        return ('japanese', 1.0, 'cjk_chars')

    # Latin harf var mi?
    latin_words = _LATIN_WORD_RE.findall(clean)
    if not latin_words:
        # Muzik notu, noktalama, vs
        if _MUSIC_NOTE_RE.search(clean):
            return ('unknown', 0.5, 'music_note_only')
        return ('unknown', 0.3, 'no_latin')

    # Apostrophe = kesin Ingilizce
    if _APOSTROPHE_RE.search(clean):
        return ('english', 0.97, 'apostrophe')

    # Melodic filler: 'la la la', 'na na na' vb. → Japonca sarki dolgu sesi → romaji say
    _MELODIC_FILLER = frozenset({
        'la','na','da','ra','ya','wa','ha','ba','pa','ta',
        'ka','ga','sa','ma','fa','sha','nya','nyan','oo','ah'
    })
    _latin_lower = [w.lower() for w in latin_words]
    if _latin_lower and len(_latin_lower) >= 2 and all(w in _MELODIC_FILLER for w in _latin_lower):
        return ('romaji', 0.82, f'melodic_filler={_latin_lower[:3]}')

    # Romaji skoru hesapla
    rom_score, detail = score_text_romaji(clean)

    if rom_score >= 0.75:
        return ('romaji', rom_score, f'romaji_score={rom_score:.2f}|{detail}')
    elif rom_score <= 0.20:
        return ('english', 1.0 - rom_score, f'english_score={1-rom_score:.2f}|{detail}')
    else:
        # Orta bolge (0.20-0.75) — ek ipuclari dene
        word_count   = len(clean.split())
        avg_word_len = sum(len(w) for w in latin_words) / max(len(latin_words), 1)

        # Romaji heceleri kisa olur (ort 2-3 harf)
        if avg_word_len <= 3.5 and rom_score > 0.55:
            return ('romaji', rom_score, f'short_words({avg_word_len:.1f})+score={rom_score:.2f}')
        if avg_word_len >= 5.5 and rom_score < 0.5:
            return ('english', 1.0 - rom_score, f'long_words({avg_word_len:.1f})+score={1-rom_score:.2f}')

        # Lingua-language-detector fallback (kuruluysa)
        # DIKKAT: Lingua kisa/karma romaji metinleri yanlis English siniflandirabilir.
        # Sadece GERCEKTEN BELIRSIZ (0.40-0.60) bolgede VE uzun metinde kullan.
        # rom_score 0.60+ ise zaten romaji tercih edilmeli, lingua'ya gerek yok.
        _lingua_zone = 0.40 <= rom_score <= 0.60
        _long_enough = avg_word_len >= 4.5 and len(clean) >= 12
        if _LINGUA_OK and _lingua_zone and _long_enough:
            lingua_lang = _lingua_detect(clean)
            if lingua_lang == 'english':
                return ('english', max(0.70, 1.0 - rom_score), f'lingua=english|avg={avg_word_len:.2f}|{detail}')
            elif lingua_lang == 'japanese':
                return ('romaji', max(0.70, rom_score), f'lingua=japanese(romaji)|avg={avg_word_len:.2f}|{detail}')

        # Hala belirsiz
        if rom_score > 0.5:
            return ('romaji', rom_score, f'slight_romaji={rom_score:.2f}')
        return ('english', 1.0 - rom_score, f'slight_english={1-rom_score:.2f}')

# ─────────────────────────────────────────────────────────────────────────────
# 9. KARAOKE HECE TESPITI
# ─────────────────────────────────────────────────────────────────────────────

def is_karaoke_syllable(raw_text: str, duration_ms: int = 0) -> Tuple[bool, str]:
    """
    Tek bir event'in karaoke hecesi mi oldugunu kontrol eder.

    Kriterler:
      - {\\kXX} tag'i varsa — kesin karaoke
      - 1-4 karakter metin + sure < 650ms
      - Muzik notu + kisa metin
    """
    # Kesin karaoke tag'i
    if _KARAOKE_TAG_RE.search(raw_text):
        return True, 'karaoke_tag'

    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    # Bos veya sadece muzik notu
    if not clean or clean in ('♪', '♫', '~', '～', '♪♪', '♫♫'):
        return True, 'music_note_only'

    length = len(clean.replace(' ', ''))

    # 1-4 karakter (kisa ozel hece)
    if length <= 4:
        if duration_ms <= 0 or duration_ms < 700:
            return True, f'short_char={length}_dur={duration_ms}'

    # Cizgi karakteri veya tirelenmis tek sesli
    if re.match(r'^[-–—]+$', clean):
        return True, 'dash_only'

    return False, 'not_karaoke_syllable'

# ─────────────────────────────────────────────────────────────────────────────
# 10. SARKI TESPITI (icerik bazli, stil adina bakmaz)
# ─────────────────────────────────────────────────────────────────────────────

# Sarki stiline isaret eden ortak stil adlari (derleme)
_KNOWN_SONG_STYLE_PATTERNS = re.compile(
    r'\b(?:'
    # OP/ED varyantlari
    r'op|ed|opening|ending|insert|ins|oped|ncop|nced|'
    r'op\d|ed\d|ins\d|'
    # Karaoke
    r'kara(?:oke)?|karaoke|k[-_]|[-_]k\b|'
    # Romaji
    r'rom(?:aji)?|furigana|furi|ruby|'
    # Dil
    r'japanese|english|nihon|nihongo|'
    # Sarki
    r'song|lyric|lyrics|vocal|vox|choir|bgvocal|'
    r'uta|ost'
    r')\b',
    re.IGNORECASE
)

def is_song_event_by_content(
    raw_text: str,
    style_name: str = '',
    start_ms: int = 0,
    end_ms: int = 0,
    all_same_style_lens: Optional[List[int]] = None,
    ep_duration_ms: int = 0,
) -> Tuple[bool, int, str]:
    """
    Bir ASS event'inin sarki/karaoke event'i olup olmadigini
    icerik ve zamanlama analiziyle tespit eder.

    Args:
        raw_text:              Ham ASS metni ({tag}li)
        style_name:            Stil adi (bos olabilir)
        start_ms/end_ms:       Zamanlar (ms)
        all_same_style_lens:   Ayni stilde diger eventlerin temiz metin uzunluklari
        ep_duration_ms:        Bolum suresi (bilgilendirici)

    Returns:
        (is_song, score, reason)
        score >= 2 → sarki/karaoke
    """
    score = 0
    reasons = []
    duration = max(0, end_ms - start_ms)
    clean = _ASS_TAG_RE.sub('', raw_text).strip()
    word_count = len(clean.split()) if clean else 0

    # --- Ipucu 1: Muzik notu (+3) ---
    if _MUSIC_NOTE_RE.search(clean) or _MUSIC_NOTE_RE.search(raw_text):
        score += 3
        reasons.append('music_note')

    # --- Ipucu 2: Karaoke tag (+3) ---
    if _KARAOKE_TAG_RE.search(raw_text):
        score += 3
        reasons.append('karaoke_tag')

    # --- Ipucu 3: Hece karaoke (+2) ---
    is_kara, kara_why = is_karaoke_syllable(raw_text, duration)
    if is_kara:
        score += 2
        reasons.append(f'syllable:{kara_why}')

    # --- Ipucu 4: Bilinen sarki stil adi (+2) ---
    if style_name and _KNOWN_SONG_STYLE_PATTERNS.search(style_name):
        score += 2
        reasons.append(f'style_name:{style_name}')

    # --- Ipucu 5: Bolum basi/sonu pozisyon (+1) ---
    if start_ms < 120_000:  # ilk 2 dakika = OP
        if word_count <= 10:
            score += 1
            reasons.append('op_position')
    elif ep_duration_ms > 0 and start_ms > ep_duration_ms - 200_000:  # son 3.5 dk = ED
        if word_count <= 10:
            score += 1
            reasons.append('ed_position')

    # --- Ipucu 6: Komsu eventler de kisa mi? (+1) ---
    if all_same_style_lens and word_count <= 8:
        avg_len = sum(all_same_style_lens) / max(len(all_same_style_lens), 1)
        if avg_len <= 8:
            score += 1
            reasons.append(f'neighbor_short:{avg_len:.1f}')

    # --- Ipucu 7: Uzun satirlar (-1) diyalog ipucu ---
    if word_count >= 12 and score < 3:
        score -= 1
        reasons.append(f'long_line:{word_count}w')

    is_song = score >= 2
    return is_song, score, '+'.join(reasons) if reasons else 'no_signal'

# ─────────────────────────────────────────────────────────────────────────────
# 11. ANA SINIFLANDIRICI (butuncul event analizi)
# ─────────────────────────────────────────────────────────────────────────────

def classify_event(
    raw_text: str,
    style_name: str = '',
    start_ms: int = 0,
    end_ms: int = 0,
    effect_field: str = '',
    all_same_style_lens: Optional[List[int]] = None,
    ep_duration_ms: int = 0,
) -> Tuple[str, float, str]:
    """
    Bir ASS event'ini tam olarak siniflandirir.

    Returns:
        (action, confidence, reason)
        action:
          'translate_song'    — Ingilizce sarki sozu, tercume et
          'translate_dialog'  — Ingilizce diyalog, tercume et
          'skip_romaji'       — Japonca romaji, atlama
          'skip_karaoke_jp'   — Japonca karaoke hecesi, atlama
          'skip_effect'       — Sadece animasyon, metin yok
          'skip_turkish'      — Zaten Turkce
          'skip_japanese'     — Kanji/Hiragana/Katakana Japonca
          'uncertain'         — Belirsiz
    """
    duration = max(0, end_ms - start_ms)
    clean = _ASS_TAG_RE.sub('', raw_text).strip()

    # --- Hizli cikislar ---
    if not clean:
        return ('skip_effect', 1.0, 'no_text')

    if _DRAW_RE.search(raw_text) and len(clean) < 5:
        return ('skip_effect', 0.95, 'draw_command')

    # Turkce kontrolu
    tr_count = sum(1 for c in clean if c in _TR_CHARS)
    if tr_count >= 2:
        return ('skip_turkish', 0.97, f'tr_chars={tr_count}')

    # CJK Japonca
    if _CJK_RE.search(clean):
        return ('skip_japanese', 1.0, 'cjk')

    # --- Stil adi analizi ---
    style_cat, style_conf, style_reason = classify_style(style_name)

    # --- Icerik dil analizi ---
    lang, lang_conf, lang_reason = classify_text(raw_text, duration)

    # --- Sarki tespiti ---
    is_song, song_score, song_reason = is_song_event_by_content(
        raw_text, style_name, start_ms, end_ms,
        all_same_style_lens, ep_duration_ms
    )

    # --- Karaoke hece tespiti ---
    is_kara, kara_why = is_karaoke_syllable(raw_text, duration)

    # ---- Karar mantigi ----

    # 1. Sadece efekt
    if lang == 'effect_only':
        return ('skip_effect', 0.95, 'effect_only')

    # 2. Japonca romaji
    if lang == 'romaji' and lang_conf >= 0.60:
        if is_kara:
            return ('skip_karaoke_jp', 0.90, f'romaji+karaoke|{lang_reason}')
        return ('skip_romaji', lang_conf, f'romaji|{lang_reason}')

    # 2b. Cok kisa metin (1-2 kelime) romaji puani 0.5+ ise romaji say
    if lang == 'romaji' and len(clean.split()) <= 3:
        return ('skip_romaji', max(0.60, lang_conf), f'short_romaji|{lang_reason}')

    # 3. Karaoke hece (romaji degil ama hece karaoke)
    if is_kara and style_cat in ('karaoke_jp', 'song_jp'):
        return ('skip_karaoke_jp', 0.85, f'kara_syllable+jp_style|{kara_why}')

    # 3b. JP STİLİ + romaji/belirsiz icerik → her zaman skip
    # ED1-JP, OP1-JP gibi JP sufiksli stiller, icerik Ingilizce degilse skip
    if style_cat in ('song_jp', 'karaoke_jp') and lang not in ('english',):
        if is_kara:
            return ('skip_karaoke_jp', 0.90, f'jp_style+kara|{lang_reason}')
        return ('skip_romaji', 0.80, f'jp_style_noneng|{lang_reason}')

    # 4. Ingilizce sarki sozu
    if lang == 'english' and is_song:
        return ('translate_song', min(lang_conf, 0.9 + song_score * 0.02),
                f'english_song|{lang_reason}|{song_reason}')

    # 5. Ingilizce sarki stili ama icerik belirsiz
    if style_cat in ('song_en', 'karaoke_en') and lang in ('english', 'mixed'):
        return ('translate_song', 0.80, f'en_style+{lang}|{style_reason}')

    # 6. Ingilizce diyalog
    if lang == 'english' and lang_conf >= 0.7:
        return ('translate_dialog', lang_conf, f'english_dialog|{lang_reason}')

    # 7. Sarki ipucu yeterince guclu ama dil belirsiz
    if is_song and song_score >= 3:
        # JP stili olsa bile song signal varsa skip (romaji sarki)
        if style_cat in ('song_jp', 'karaoke_jp'):
            return ('skip_romaji', 0.65, f'song_jp_signal|{song_reason}')
        if lang in ('english', 'mixed', 'unknown'):
            return ('translate_song', 0.70, f'song_signal|{song_reason}')
        return ('skip_romaji', 0.65, f'song_jp_signal|{song_reason}')

    # 8. Genel diyalog (fallback)
    if lang == 'english':
        return ('translate_dialog', lang_conf, f'fallback_eng|{lang_reason}')

    return ('uncertain', 0.4, f'lang={lang}|style={style_cat}|{lang_reason}')

# ─────────────────────────────────────────────────────────────────────────────
# 12. BATCH HELPER — pysubs2 event listesi icin
# ─────────────────────────────────────────────────────────────────────────────

def classify_events_batch(
    events: List[dict],
    ep_duration_ms: int = 0,
) -> List[Tuple[str, float, str]]:
    """
    Event listesini toplu olarak siniflandirir.
    Her event dict'i 'parts' listesi icermeli: parts[1]=start, parts[2]=end,
    parts[3]=style, parts[8]=effect, parts[9]=text
    """
    # Stil bazi istatistikleri topla (komsu length)
    from collections import defaultdict
    style_lens: dict = defaultdict(list)

    for ev in events:
        p = ev.get('parts', [])
        if len(p) > 9:
            style = p[3]
            clean = _ASS_TAG_RE.sub('', p[9]).strip()
            style_lens[style].append(len(clean.split()))

    results = []
    for ev in events:
        p = ev.get('parts', [])
        if len(p) <= 9:
            results.append(('uncertain', 0.0, 'no_parts'))
            continue

        style   = p[3]
        text    = p[9]
        effect  = p[8] if len(p) > 8 else ''
        start   = _ts_to_ms(p[1])
        end     = _ts_to_ms(p[2])
        # Komsu uzunluklar (kendisi haric)
        neighbors = [x for x in style_lens[style]]  # includes self, ok for avg

        action, conf, reason = classify_event(
            raw_text=text,
            style_name=style,
            start_ms=start,
            end_ms=end,
            effect_field=effect,
            all_same_style_lens=neighbors,
            ep_duration_ms=ep_duration_ms,
        )
        results.append((action, conf, reason))

    return results

# ─────────────────────────────────────────────────────────────────────────────
# 13. SELF TEST
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 70)
    print("  CONTENT DETECTOR — KAPSAMLI TEST")
    print("=" * 70)

    style_tests = [
        ('ED1-JP-kara',   'karaoke_jp'),
        ('ED1-EN-kara',   'karaoke_en'),
        ('OP1-EN',        'song_en'),
        ('OP1 JP',        'song_jp'),
        ('Default',       'generic'),
        ('Main',          'generic'),
        ('Style0001',     'generic'),
        ('Song',          'song_unknown'),
        ('Lyric',         'song_unknown'),
        ('Dialogue',      'dialog'),
        ('Signs',         'generic'),
    ]

    print("\n[Stil Adi Testi]")
    ok = fail = 0
    for sname, expected in style_tests:
        cat, conf, reason = classify_style(sname)
        status = 'OK' if cat == expected else 'FAIL'
        if status == 'OK': ok += 1
        else: fail += 1
        print(f"  [{status}] {sname!r:20s} → {cat} ({conf:.2f})")
    print(f"  {ok}/{ok+fail} OK")

    text_tests = [
        ("No one else—only you",         'english'),
        ("Even if the world hasn't forgotten yet", 'english'),
        ("Sekai wa utsukushii",           'romaji'),
        ("Nee zutto soba ni ite",         'romaji'),
        ("Bu dünya güzel",               'turkish'),
        ("",                              'effect_only'),
        ("I found the light again",       'english'),
        ("hikari wo mitsuketa",           'romaji'),
    ]

    print("\n[Metin Dil Testi]")
    for text, expected in text_tests:
        lang, conf, reason = classify_text(text)
        status = 'OK' if lang == expected else 'FAIL'
        print(f"  [{status}] {text!r:42s} → {lang} ({conf:.2f})")

    print("\n[Event Siniflandirma Testi]")
    event_tests = [
        # (text, style, start_ms, end_ms, expected_action)
        ("No one else—only you",  "ED1-EN-kara",  1434000, 1437000, 'translate_song'),
        ("{\\k12}Ne{\\k10}e",    "ED1-JP-kara",  1200000, 1201000, 'skip_karaoke_jp'),
        ("Sekai wa",             "Default",       1200000, 1202800, 'skip_romaji'),
        ("♪ I love you ♪",      "Default",       60000,   63000,   'translate_song'),
        ("Bu dünyan",            "Default",       300000,  303000,  'skip_turkish'),
        ("",                     "Default",       0,       0,       'skip_effect'),
    ]
    for text, style, s, e, exp in event_tests:
        action, conf, reason = classify_event(text, style, s, e)
        status = 'OK' if action == exp else 'FAIL'
        print(f"  [{status}] {text!r:35s} [{style}] → {action}")

    print("\n" + "=" * 70)
