"""
processor/style_detect.py
=========================
ASS stil adı analizi: sign tespiti, şarkı stili, dil suffix yönetimi.
SONG_KEYWORDS, STYLE_SUFFIX_SKIP, STYLE_SUFFIX_FORCE_TRANSLATE sabitleri burada.
"""
import re

# ============================================
# SUBTITLE CLEANING KEYWORDS
# ============================================
# Regex Patterns (Repeated here or imported if safe, sticking to local definitions for safety in processing loop)
JP_CHARS = r'\u3000-\u303F\u3040-\u309F\u30A0-\u30FF\uFF00-\uFFEF\u4E00-\u9FAF\u3400-\u4DBF'

# [COPYRIGHT SKIP] Telif hakki bildirimleri hicbir zaman ceviriye gitmemeli
_COPYRIGHT_SKIP_RE = re.compile(
    r'(?i)(?:'
    r'\xa9|\u00a9|copyright|\(c\)\s*\d|production\s+committee|'
    r'all\s+rights\s+reserved|shueisha|kodansha|aniplex|'
    r'crunchyroll|funimation|sentai\s+filmworks'
    r')', re.IGNORECASE
)

DRAWING_PATTERN = re.compile(r'\\p[1-9]')
POSITION_PATTERN = re.compile(r'\\(pos|move|org|clip|iclip|fad|fade|an[1-9]|bord|xbord|ybord|shad|xshad|yshad|blur|fsp|fs\d)')
BRACKET_PATTERN = re.compile(r'\{.*?\}')
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
JP_PATTERN_NORMAL = re.compile(r'\([^)]*[' + JP_CHARS + r']+[^\)]*\)')
JP_PATTERN_FULL = re.compile(r'（[^）]*[' + JP_CHARS + r']+[^\）]*）')
JP_CHAR_REMOVER = re.compile(r'[' + JP_CHARS + r']+')

# DELETE_KEYWORDS: Kesinlikle silinecek gereksiz işaretler
DELETE_KEYWORDS = []
# SONG_KEYWORDS: Silinmeyecek ama ÇEVRİLMEYECEK (Korunacak) stiller
# Fansub gruplarının kullandığı tüm şarkı/romaji stil adı kalıpları
SONG_KEYWORDS = [
    # ── Standart OP / ED ────────────────────────────────────────────────────
    'op', 'ed', 'song', 'opening', 'ending', 'insert',
    'oped', 'inssong', 'insong',
    'opsong', 'edsong',
    'lyric', 'lyrics',

    # ── NCOP / NCED (No Credits Opening/Ending) ─────────────────────────────
    # Creditless versiyonlar — yine de sarki sozu icerir!
    'ncop', 'nced', 'nc',
    'cleanop', 'cleaned', 'creditless',
    'clean',

    # ── Karaoke temelli stil adları (K-OP, K-ED, Kara-OP) ───────────────────
    # Bazı gruplar KFX icin ozel stil kullanır
    # 'kara' ve 'karaoke' halihazırda SKIP listesinde
    # Ama Karaoke_EN gibi EN suffix’li versiyonlar translate olmali

    # ── Intro / Outro / Preview ──────────────────────────────────────────
    'intro', 'outro',
    'preview',

    # ── Vokâl / Şarkıcı stilleri ──────────────────────────────────────────
    # Duo, Choir, Singer vb. grup sarkilarinda kullanilir
    'sing', 'vocal', 'vocals',
    'singer',          # Main Singer, Sub Singer
    'chorus',          # Koro / Nakarat bolumu
    'choir',           # Koro
    'duo',             # Iki sarkici
    'group',           # Grup sarkilari
    'harmony',         # Uyum sesi
    'backing',         # Arka plan vokali

    # ── Tema / İmaj Şarkıları ────────────────────────────────────────────────
    'theme',
    'image', 'imagesong', 'imageop', 'imageed',

    # ── Özel Sahneler ─────────────────────────────────────────────────────
    # Bazi gruplar flashback veya preview sahnelerindeki sarkilar icin kullanir
    # Bunlar icerik analizi ile denetlenmeli

    # ── Full / Special / Version varyantları ────────────────────────────────
    'full',
    'special',
    'version',
    'remix',
    'acoustic',
    'short',

    # ── Şarkı bölümleri ─────────────────────────────────────────────────────
    'chorus',
    'verse',
    'refrain',
    'bridge',

    # ── BGM / Müzik ─────────────────────────────────────────────────────
    'bgm',
    'music',

    # ── Japonca / Karaoke stil etiketleri (bunlar standalone degil, ınert olarak SKIP)
    # NOT: jp, rom, jpn, romaji buradan KALDIRILDI
    # Bunlar STYLE_SUFFIX_SKIP listesinde zaten var;
    # segment bazlı eslesmede 'Default - JP' gibi diyalog stilleri yanlis
    # sarki sayiliyordu. Dil etiketi SADECE sarki keyword'u varken anlam tasir.
    'kara', 'karaoke',

    # ── GJM fansub grubu ozel stilleri ───────────────────────────────
    'insjp', 'insrom', 'inskana', 'insmem', 'inskai',
    'insen', 'inseng',
    'ins',   # Kisa ins prefix (InsSong, InsEN vb.) segment kontrolu ile
]

# ==============================================================
# STİL ADI SONEK SİSTEMİ
# Stil adının soneki çeviri davranışını belirler.
# Ayraç ne olursa olsun yakalanır: ED-ROM, ED_ROM, ED ROM, EDROM
# ==============================================================
# Ekran üzü yazı stilleri: kısa ve literal çeviri
_SIGN_STYLE_NAMES = {
    # Temel sign/ekran yazısı stilleri
    "signs", "sign", "caption", "typeset",
    "detail", "note", "onscreen", "on-screen",
    "location", "overlay", "label", "banner", "board",
    # NOT: 'title' kaldirildi — SAO/genel animelerde 'title' stili
    # cevirilmesi gereken ekran metni icerir (Kara Kilic Ustasi vb.)
    # NOT: 'prev'/'next' kaldirildi — bunlar gradient frame stilleri,
    # is_tag_heavy_fx + clip detection tarafindan zaten yakalanir
    # Bölüm başlığı / geçiş kartları — spesifik formlar
    "eyecatch", "eye-catch",
    "ep-title", "episode-title", "episode", "eptitle", "episodetitle",
    "titlecard",   # Tam form — kesinlikle sign karti
    "intertitle",  # Araya giren baslik karti
    "card", "namecard", "name-card",
    # Genel ekran metni türleri
    "announcement", "subtitle-sign",
    # NOT: 'flashback', 'screen', 'text', 'info' kaldirildi —
    # flashback diyalog cevirilmeli; screen/text/info cok generic
}

STYLE_SUFFIX_SKIP = {
    # Japonca / Romaji / Karaoke — cevirme
    'ROM', 'ROMAJI', 'ROMANIZED', 'ROMANIZATION',
    'JPN', 'JP', 'JAP', 'JAPANESE', 'JPNESE',
    'KANA', 'KANJI',
    # [REAL-DATA FIX] Gerçek dosya taramasından eklendi:
    # DEFAULT-JA, OP-JA, ED-JA stili → JA suffix eksikti
    'JA', 'JPN2',
    # OPJA, EDJA, OPJA1 gibi bitişik yazılan JP stiller → get_style_suffix_behavior'da yakalanır
    # ama burada suffix olarak da ekle (güvence)
    'OPJA', 'EDJA',
    'CHN', 'CN', 'ZH', 'CHI', 'CHINESE',
    # [REAL-DATA FIX v2] 4105 dosya taraması: CH, CHS, CHT eksikti
    # ED-CH (60), DIAL-CH (54), OP-CHS (44), IN-CH (8), TEXT CH, DIAL-CHS (25)
    'CH',            # ED-CH, DIAL-CH, IN-CH, OP-CH, TEXT CH — Çince stil suffix
    'CHS',           # CHS, OP-CHS, DIAL-CHS — Simplified Chinese
    'CHT',           # CHT — Traditional Chinese
    # [REAL-DATA FIX v2] CN fansub gruplarının özel stil adları
    # ZW = 中文 (Zhōngwén) prefix — 诸神字幕组 grubu: ZWDB, ZWED, ZWOP
    'ZW',            # ZWDB (119 leak), ZWED (13 leak)
    # [REAL-DATA FIX v2] Bitişik OPJ stili: K-ON OPJ (13 leak)
    'OPJ', 'EDJ',    # OPJ → OP+Japanese, EDJ → ED+Japanese
    # [REAL-DATA FIX v2] DB suffix: JPDB (42 leak), ZWDB (119 leak)
    # JP+CN çift dilli: JP(JP)+DB(双拼/çift)
    'DB',            # JPDB, ZWDB — çift dilli
    'KOR', 'KR', 'KOREAN',
    'KARA', 'KARAOKE', 'KAR',
    # NOT: 'LYRICS'/'LYRIC' buradan kaldirildi — Lyric/Lyrics-EN gibi Ingilizce sarki stili olabilir
    'CREDIT', 'CREDITS', 'CREDIT2', 'STAFF', 'CAST',
    'NOTE', 'TL', 'TLNOTE', 'TRNOTE', 'EDNOTE',
    'BGM', 'MUSIC',
    'MEM', 'MEMORY',
    'FURIGANA', 'RUBY',
    # GJM ozel skip stilleri
    'INSJP', 'INSROM', 'INSKANA', 'INSMEM', 'INSKAI',
    # Karaoke_JP, Song_JP gibi JP suffix kombinasyonlar
    'KAI',  # GJM InsKai (Kanji)
    # [REAL-DATA FIX] JP terimleri: BD sürümündeki özel stil adları
    'BD',   # JP BD → JP suffix yakalanır ama BD tek başına da görülür
}

STYLE_SUFFIX_FORCE_TRANSLATE = {
    'ENG', 'EN', 'ENGLISH',
    'ALT', 'ALTDIAL',
    'TRANS', 'TRANSLATION',
    # GJM/Fansub Insert English
    'INSEN', 'INSENG',
    # NCOP/NCED creditless Ingilizce
    'NC',
    # Full/Clean versiyonları
    'FULL', 'CLEAN', 'CREDITLESS',
    # Varyant versiyonlar (OP Remix EN, ED Acoustic EN)
    'REMIX', 'ACOUSTIC',
}

def is_sign_style_name(style_name: str) -> bool:
    """
    İsim üzerinden Sign/ekran üzü yazısı stilini tespit eder.
    Diyalog satirı değildir: lokasyon, başlık, pano vb.
    """
    s = style_name.lower().strip()
    s_clean = s.replace('-', '').replace('_', '').replace(' ', '')
    # Tam eşleşme
    if s_clean in _SIGN_STYLE_NAMES or s_clean in {n.replace('-','').replace('_','') for n in _SIGN_STYLE_NAMES}:
        return True
    # Önekle başlayan: "signs-en", "signs-styled", "signtl", "signboard"
    if s_clean.startswith('sign'):
        return True
    # Anahtar kelime içeriyor
    for kw in ('typeset', 'caption', 'onscreen', 'label', 'banner', 'board', 'overlay'):
        if kw in s_clean:
            return True
    return False


def get_style_suffix_behavior(style_name):
    """
    Stil adının sonekinden çeviri davranışını belirler.
    Returns: 'skip' | 'translate' | None

    ÖNEMLİ: FORCE_TRANSLATE (EN, ENG, ALT) her zaman SKIP'ten önce gelir.
    ED1-EN-kara gibi birleşik stil adlarında EN içeriyorsa → çeviri zorlanır.
    """
    s = style_name.strip().upper()
    # Ayraçları temizlemeden önce parçalara ayır (-, _, boşluk)
    parts = re.split(r'[-_\s]', s)  # ['ED1', 'EN', 'KARA']

    # 1. Herhangi bir parça FORCE_TRANSLATE ise → hemen 'translate' döndür
    for part in parts:
        if part in STYLE_SUFFIX_FORCE_TRANSLATE:
            return 'translate'

    # 2. Herhangi bir parca SKIP listesinde ise skip dondur
    # [FIX] ED1-JP-ButDark gibi JP ortada olsa da dogru tanisın
    for part in parts:
        if part in STYLE_SUFFIX_SKIP:
            return 'skip'

    # 3. Ayracsiz birlesik sonek (fallback)
    # [REAL-DATA FIX] '.' da ayraç sayılır: JP.SUB, JP.BD vb. (366 dosya taramasından)
    s_clean = re.sub(r'[-_\s.]', '', s)
    for suffix in STYLE_SUFFIX_SKIP:
        if s_clean.endswith(suffix) and s_clean != suffix:
            return 'skip'
    for suffix in STYLE_SUFFIX_FORCE_TRANSLATE:
        if s_clean.endswith(suffix) and s_clean != suffix:
            return 'translate'

    # [REAL-DATA FIX] Bitişik JP kalıpları: OPJA, OPJA1, EDJA, EDJA0, EDJA1, EDJA2
    # 366 gerçek dosya taraması: 759+729+229 Japonca satır bu kalıplarla kaçıyordu
    if re.match(r'^(?:OP|ED|NC|NCOP|NCED)\d*(?:JA|JP|JPN)\d*$', s_clean, re.IGNORECASE):
        return 'skip'

    # [REAL-DATA FIX v2] CN/CHS stilli OP/ED kalıpları: EDCN_12, OP-CHS, ED-CH vb.
    # 4105 dosya taraması: EDCN (sayı suffix'li CN stiller)
    if re.match(r'^(?:OP|ED|NC|NCOP|NCED)\d*[-_\s]?(?:CN|CHS|CHT|CH|ZH)\d*$', s_clean, re.IGNORECASE):
        return 'skip'

    # [REAL-DATA FIX v2] JP-prefix bitişik: JPDEFAULT (1), JPDB (42), JPOP (108), JPED (131)
    # 'JP' zaten STYLE_SUFFIX_SKIP'te ama ayraçsız prefix olarak da gelmeli
    # Kural: JP ile başlayan + 2+ karakter → skip (JPEG hariç)
    if s_clean.upper().startswith('JP') and len(s_clean) > 2 and s_clean.upper() not in ('JPEG',):
        return 'skip'

    # [REAL-DATA FIX v2] ZW-prefix — 诸神字幕组 CN grubu: ZWDB (119), ZWED (13), ZWOP
    if s_clean.upper().startswith('ZW') and len(s_clean) > 2:
        return 'skip'

    # [REAL-DATA FIX v2] OP/ED + herhangi bir şey → şarkı/intro stili → skip
    # OP BLACK (46 leak — Cardcaptor CN+EN karma), OP PREVIEW, OP FULL, ED PREVIEW...
    # is_song_style_name zaten 'op' prefix yakalar ama "OP BLACK" → 'op' + ' '→ yakalanır
    # Kontrol: get_style_suffix_behavior'dan önce is_song_style_name'e gidiliyor mu?
    # Burada direct: eğer stil adı OP veya ED ile başlıyor ve song_kw listesinde değilse de skip
    _s_parts = re.split(r'[-_\s.]', s)
    if len(_s_parts) >= 2 and _s_parts[0] in ('OP','ED','NCOP','NCED','NC','OP1','OP2','ED1','ED2'):
        # İkinci parça EN/ENG/ENGLISH DEĞİLSE → song stili → skip
        if _s_parts[1] not in STYLE_SUFFIX_FORCE_TRANSLATE:
            return 'skip'


    return None


def is_song_style_name(style_name):
    s = style_name.lower().strip()

    # [FIX] Furigana suffix tespiti: 'Default-furigana', 'OP1 - ROM-furigana' gibi
    # Bu satirlar cevrilmez — ASS'de ust hece notasyonu (ruby text) icin kullanilir.
    if s.endswith('furigana') or '-furigana' in s or '_furigana' in s:
        return True

    # Tam eslesme + onek kontrolleri
    for kw in SONG_KEYWORDS:
        # Tam eslesme: 'op', 'ed', 'kara' vb.
        if s == kw:
            return True
        # Onek eslesimi SADECE rakamla devam ediyorsa: 'op1', 'op2', 'ed1'
        if s.startswith(kw) and len(s) > len(kw) and s[len(kw)].isdigit():
            return True
        # Ayracli: 'op_bg', 'op bg', 'op-bg', 'op.1' → hepsi song
        if s.startswith(kw) and len(s) > len(kw) and s[len(kw)] in ('_', ' ', '-', '.'):
            return True

    # Segment bazlı kontrol: GJM_InsEN, Chyuu_InsROM, SubsPlease_InsJP
    # Her bölümü ayrı kontrol et: "GJM_InsEN" → ["gjm", "insen"]
    # [FIX] jp/rom/en gibi dil-ONLY segmentler tek başına şarkı sayılmamalı!
    # ('Default - JP' → ['default','jp'] → 'jp' yanlış şarkı sayılıyordu)
    _INSERT_SONG_RE = re.compile(
        r'^(?:ins(?:ert)?|inssong|insong)(?:\d*[-_]?(?:jp|jpn|rom|en|eng|kana|mem|kai))?',
        re.IGNORECASE
    )
    _LANG_ONLY_SEGS = frozenset({
        'jp', 'jpn', 'jap', 'japanese',
        'rom', 'romaji', 'romanized',
        'en', 'eng', 'english',
        'kr', 'kor', 'korean',
        'zh', 'cn', 'chi', 'chinese',
        'tr', 'kana', 'kanji',
    })
    for seg in re.split(r'[-_\s]', s):
        if not seg:
            continue
        # Dil-only segment → atla (tek başına 'JP', 'ROM' şarkı değil)
        if seg in _LANG_ONLY_SEGS:
            continue
        # SONG_KEYWORDS tam segment eşleşimi
        if seg in SONG_KEYWORDS:
            return True
        # Insert song prefix (ins, insert, InsEN, InsJP...)
        if _INSERT_SONG_RE.match(seg):
            return True
    return False



