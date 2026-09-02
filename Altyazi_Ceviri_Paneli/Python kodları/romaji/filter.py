"""
romaji/filter.py
================
is_romaji_sentence.
"""
import re
from typing import List, Tuple, Optional

def _syllable_coverage(word: str) -> float:
    """
    Kelimenin Japonca hecelerine bölünebilme oranını döndürür (0.0 – 1.0).
    Örnek: 'kawaii' → ka-wa-i-i → 6/6 = 1.0
            'leaving' → l: hata → ~0.3
    """
    w = word.lower()
    total = len(w)
    if total == 0:
        return 0.0
    i = 0
    matched = 0
    while i < total:
        found = False
        for syl in _SYLLABLES:
            slen = len(syl)
            if w[i:i + slen] == syl:
                matched += slen
                i += slen
                found = True
                break
        if not found:
            # Geminat ünsüz (tt, kk, pp): Japoncada geçerli hece başlangıcı
            if (i + 1 < total
                    and w[i] == w[i + 1]
                    and w[i] not in 'aeiou'):
                matched += 1
                i += 1
            else:
                i += 1   # Geçersiz hece → ilerle ama sayma
    return matched / total


# ──────────────────────────────────────────────────────────────
# BÖLÜM 2: JAPONCA ROMAJI SÖZCÜK VE PARTİKÜL SÖZLÜKLERİ
# ──────────────────────────────────────────────────────────────

# ── 2a. Partikül / dilbilgisi ekleri (ağırlık: 2.0) ──
# Bunlar çoğunlukla İngilizce'de ayrı kelime olarak geçmez;
# yalnız 'no', 'mo', 'de', 'wa' gibi kısa olanlar bazen çakışır.
JP_PARTICLES = frozenset({
    # Temel partiküllar
    'wa', 'ga', 'ni', 'wo', 'de', 'kara', 'made', 'yori',
    'dake', 'nomi', 'bakari', 'nado', 'toka', 'noni', 'node',
    'kedo', 'keredo', 'temo', 'demo', 'tara', 'eba', 'shi',
    'tte', 'tteba', 'yara', 'tomo', 'zutsu',
    # Cümle sonu partikülleri
    'ne', 'nee', 'naa', 'yo', 'sa', 'zo', 'ze', 'kana', 'kashira',
    'mono', 'monono', 'monodesukara', 'wake',
    # Yardımcı fiil partikülleri
    'nde', 'nda', 'ndayo', 'dayo', 'dana', 'dawa', 'wayo',
})

# ── 2b. Yüksek güvenilirlik: Saf Japonca kelimeler (ağırlık: 1.8) ──
# İngilizce'de anlamsız — kesinlikle Japonca
JP_VOCAB_HIGH = frozenset({
    # Zamirler / Isaret kelimeleri
    'watashi', 'watakushi', 'atashi', 'uchi', 'boku', 'ore', 'washi',
    'jibun', 'kimi', 'anata', 'anta', 'kisama', 'omae',
    'kare', 'kanojo', 'karera', 'kanojotachi', 'wareware',
    'kochira', 'sochira', 'achira', 'dochira',
    'kore', 'sore', 'dore',
    'koko', 'soko', 'asoko', 'doko',
    'donna', 'dono', 'dou', 'doushite', 'douka',
    'nani', 'naze', 'nande', 'doshite', 'itsu', 'ikura', 'ikutsu',
    'dare', 'donata',

    # Sık kullanılan fiiller (kök ve çekimli formlar)
    'suru', 'shita', 'shite', 'shimau', 'shimatta', 'shimaeba',
    'iru', 'ita', 'ite', 'imasu', 'inai', 'imashou',
    'iku', 'itta', 'itte',
    'kuru', 'kita', 'kite', 'kimasu',
    'miru', 'mita', 'mite', 'mireba', 'mieru',
    'aru', 'atta', 'nai',
    'naru', 'natta', 'natte', 'naritai', 'nareru',
    'yaru', 'yatte', 'yatta',
    'deru', 'deta', 'dete',
    'hairu', 'haitta', 'haitte',
    'kaeru', 'kaetta', 'kaette',
    'okiru', 'okite', 'okita',
    'neru', 'neta', 'nete',
    'taberu', 'tabeta', 'tabete',
    'nomu', 'nonda', 'nonde',
    'motsu', 'motta', 'motte', 'mochiageru',
    'ageru', 'ageta', 'agete',
    'morau', 'moratta', 'moratte',
    'kureru', 'kureta', 'kurete',
    'tsukuru', 'tsukutta', 'tsukutte',
    'kiku', 'kiita', 'kiite',
    'yomu', 'yonda', 'yonde',
    'kaku', 'kaita', 'kaite',
    'hanasu', 'hanashita', 'hanashite',
    'warau', 'waratta', 'waratte',
    'naku', 'naita', 'naite',
    'okuru', 'okutte', 'okutta',
    'sagasu', 'sagashita', 'sagashite',
    'mitsukeru', 'mitsuketa', 'mitsukete',
    'wasureru', 'wasureta', 'wasurete',
    'oboeru', 'oboeta', 'oboete',
    'kangaeru', 'kangaeta', 'kangaete',
    'shinjiru', 'shinjita', 'shinjite', 'shinjitai',
    'aishiteru', 'aishita', 'aishite', 'aisu',
    'suki', 'kirai', 'daisuki', 'daikirai',
    'dekiru', 'dekita', 'dekinai',
    'naritai', 'mitai', 'shitai', 'ikitai', 'kitai',
    'hazimeru', 'hajimeru', 'hajimeta',
    'tomaru', 'tomatta', 'tomatte',
    'koeru', 'koeta', 'koete',
    'nozomu', 'nozonda',
    'negau', 'negatta', 'negatte',
    'inoru', 'inotta', 'inotte',
    'yobikomu', 'yoberu', 'yobu', 'yobikaeru',
    'kagayaku', 'kagayaita', 'kagayaite',
    'tobu', 'tonda', 'tonde',
    'hashiru', 'hashitta', 'hashitte',
    'aruku', 'aruita', 'aruite',
    'korobu', 'koronda', 'koronde',
    'tatsu', 'tatta', 'tatte',
    'suwaru', 'suwatta', 'suwatte',
    'sakebu', 'sakenda', 'sakende',
    'tazuneru', 'tazuneta',
    'tsutaeru', 'tsutaeta',
    'kataru', 'katatta',
    'mamoru', 'mamotta', 'mamoreru',
    'tatakaeru', 'tatakau', 'tatakatta', 'tatakatte',
    'katsu', 'katta', 'makeru', 'maketa',
    'susumu', 'susunda', 'susunde',
    'modoru', 'modotta', 'modotte',
    'mawaru', 'mawatta', 'mawatte',
    'furu', 'futta', 'futte',       # yağmak (fall/rain)
    'fuku', 'fuita', 'fuite',       # esmek (blow)
    'terasu', 'teraseru',           # aydınlatmak
    'hikaru', 'hikarita', 'hikaitte',
    'moeru', 'moeta', 'moete',
    'tsutsumu', 'tsutsuita',
    'kowareru', 'kowashita',
    'oshieru', 'oshiete', 'oshieta',   # to teach / tell
    'shinu', 'shinda', 'shinde',       # to die
    'ikiru', 'ikita', 'ikite',         # to live
    'katachi', 'kaeru',

    # Sıfatlar (i-adjectives ve na-adjectives)
    'kawaii', 'kawaikunai', 'kawaiku',
    'sugoi', 'sugoku',
    'ureshii', 'ureshou', 'ureshi',
    'kanashii', 'kanashiku', 'kanashimi',
    'tanoshii', 'tanoshiku', 'tanoshimu',
    'kurushii', 'kurushiku',
    'sabishii', 'sabishiku', 'sabishi',
    'tsuyoi', 'tsuyoku', 'tsuyosa',
    'yowai', 'yowaku',
    'yasashii', 'yasashiku', 'yasashisa',
    'kibishii', 'kibishiku',
    'kowai', 'kowaku',
    'hoshii', 'hoshiku',
    'samui', 'samuku',
    'atsui', 'atsuku',
    'isogashii', 'isogashiku',
    'itai', 'itaku',
    'nemui', 'nemuku',
    'warui', 'waruku',
    'ii', 'yoi', 'yoku',
    'hayai', 'hayaku',
    'osoi', 'osoku',
    'takai', 'takaku',
    'hikui', 'hikuku',
    'ookii', 'ookiku', 'ookisa',
    'chiisai', 'chiisaku', 'chiisana',
    'nagai', 'nagaku',
    'mijikai', 'mijikaku',
    'omoi', 'omoku', 'omosa',
    'karui', 'karuku',
    'hade', 'jimi', 'kirei', 'kitanai',
    'shizuka', 'nigiyaka', 'futsuu',
    'genki', 'daijoubu', 'daijobu',
    'hima', 'taihen', 'muzukashii',
    'kantan', 'shinsetsu', 'reikou',
    'juuyou', 'tokubetsu', 'futsuu',
    'kakkoii', 'kakkoikunai',
    'oishii', 'oishiku', 'mazui',
    'subarashii', 'subarashou',
    'fushigi', 'kimochi', 'komaru',

    # İsimler — duygular ve soyut kavramlar
    'ai', 'koi', 'yume', 'kokoro', 'tamashii', 'tamashi',
    'namida', 'egao', 'hohoemi', 'warai',
    'kanashimi', 'yorokobi', 'ikari', 'odoroki',
    'kimochi', 'kibou', 'kitai', 'zetsubou',
    'yuuki', 'kizuna', 'inochi', 'seimei',
    'chikara', 'hoshi', 'hikari', 'kage',
    'yami', 'kurami', 'akari',
    'kotoba', 'koe', 'oto', 'uta', 'shirabe',
    'kioku', 'omoide', 'yoake', 'tasogare',
    'shinjitsu', 'honto', 'usotsuki',
    'shiawase', 'fushiawase', 'kouun',

    # İsimler — doğa ve çevre
    'sora', 'umi', 'yuki', 'hana', 'hoshi', 'tsuki', 'taiyou',
    'kaze', 'ame', 'kumo', 'niji', 'inazuma', 'kaminari',
    'mori', 'yama', 'kawa', 'michi', 'daichi',
    'shizen', 'sekai', 'uchu', 'chikyu',
    'mizuumi', 'shima', 'hara', 'nohara', 'oka',
    'natsu', 'fuyu', 'haru', 'aki',
    'asa', 'hiru', 'yoru', 'yuu', 'yoake',
    'ima', 'mukashi', 'mirai', 'kako', 'shunkan',

    # İsimler — insan ilişkileri
    'tomodachi', 'nakama', 'teki', 'mikata',
    'kazoku', 'oyako', 'chichi', 'haha', 'otouto', 'imouto',
    'ani', 'ane', 'sofu', 'sobo', 'kodomo', 'otona',
    'koibito', 'hito', 'otoko', 'onna',
    'sensei', 'seito', 'gakusei', 'tomo',

    # İsimler — nesne ve yer
    'machi', 'miyako', 'shiro', 'tobira', 'mado',
    'basho', 'tokoro',
    'kokoro', 'uchu', 'sekai', 'jidai', 'monogatari',
    'chikara', 'katachi', 'iro', 'sugata',
    'ude', 'mimi', 'kuchi',

    # Zaman ve derece zarfları
    'itsuka', 'itsumo', 'issho', 'isshoni',
    'zutto', 'motto', 'mou', 'mada', 'ima',
    'hayaku', 'osoku', 'sugu', 'yukkuri',
    'totemo', 'sugoku', 'hontouni', 'hontou',
    'kitto', 'tabun', 'yahari', 'yappari',
    'naze', 'doushite', 'nazenara',
    'dakara', 'soredemo', 'soreでも',
    'demo', 'demo', 'dakedo',
    'saa', 'hora', 'sore', 'moshi', 'kono', 'sono',
    'ano', 'donna', 'takusan', 'sukoshi', 'chotto',

    # Yardimci fiiller / kaliplar
    'desu', 'deshita', 'dewa', 'janai', 'janaika',
    'masou', 'masen', 'mashita', 'masu',
    'rashii', 'mitai', 'hazu',
    'beki', 'kamoshirenai',
    'tai', 'tagaru', 'souda', 'youda',
    'saseru', 'sareru', 'rareru', 'reru',
    'kudasai', 'nasai', 'naide', 'masen',

    # Sayılar ve sıralamayla ilgili
    'ichi', 'roku', 'nana', 'shichi',
    'hachi', 'kyuu', 'juu', 'hyaku', 'sen',
    'hitotsu', 'futatsu', 'mittsu', 'yottsu', 'itsutsu',
    'muttsu', 'nanatsu', 'yattsu', 'kokonotsu',
    'hajime', 'owari', 'saigo', 'saisho',

    # Selamlaşma ve ifadeler
    'arigatou', 'arigatougozaimasu', 'sumimasen', 'gomen',
    'gomennasai', 'tadaima', 'okaeri', 'ohayou', 'oyasumi',
    'konnichiwa', 'konbanwa', 'sayounara', 'mata', 'jaa',
    'yabai', 'masaka', 'ehh', 'uso', 'hontou',
    'nani', 'nandayo', 'nandatte', 'unbelievable',
    'yatta', 'yoshi', 'ganbatte', 'ganbare',
    'ittekimasu', 'itterasshai', 'okaerinasai',

    # Sık anime'de geçen özel kelimeler
    'senpai', 'kouhai', 'sensei', 'otaku', 'kawaii',
    'sugoi', 'naniか', 'nakama', 'shounen', 'shoujo',
    'isekai', 'nani', 'baka', 'hidoi', 'urusai',
    'shinjiru', 'mamoru', 'tatakau', 'mahou',
    'seiyuu', 'manga', 'anime', 'doujin',
    'daisuki', 'nanka', 'chigau', 'sou',
    'osewa', 'yoroshiku', 'hajimemashite',
    'itadakimasu', 'gochisousama',
})

# ── 2c. Orta güvenilirlik: Japonca + baz. İngilizce ile çakışan (ağırlık: 1.0) ──
JP_VOCAB_MED = frozenset({
    # Çakışan ama genellikle Japonca bağlamda olan
    'suki',    # "suki" değil + "sukiyaki" değil ama "suki da" Japonca
    'nani',    # what
    'dou',     # how
    'nan',     # what  (number also)
    'nanka',   # somehow
    'moshi',   # if / hello (phone)
    'sou',     # so / that's right
    'hora',    # hey look
    'saa',     # well then
    'iya',     # no / unpleasant
    'maa',     # well
    'ara',     # oh my
    'aho',     # idiot (Kansai)
    'baka',    # idiot
    'uso',     # lie
    'yada',    # no way
    'iya',     # dislike
    'eetto',   # erm
    'ano',     # um / that
    'kono',    # this
    'sono',    # that
    'shiru',   # to know
    'omou',    # to think
    'kana',    # I wonder
    'zo',      # (emphatic particle)
    'ze',      # (emphatic particle)
    'naa',     # (soft particle)
    'nee',     # (agreement particle)
    'tte',     # quotation particle
    'yo',      # (assertion particle)
    'ne',      # (seeking agreement)
    'sa',      # (soft assertion)
    'mou',     # already / no more
    'mada',    # still / not yet
    'mata',    # again
    'datte',   # because / but
    'kedo',    # but
    'demo',    # but / however
    'noni',    # although / for
    'kara',    # because / from
    'node',    # because
    'ga',      # but / subject marker
    'ni',      # to / at / in (destination)
    'de',      # at / by / with
    'wo',      # object marker
    'to',      # and / with / quotation
    'mo',      # also / too
    'ka',      # question marker
    'na',      # (soft prohibition / wonder)
    'ya',      # and (Kansai) / exclamation
    'shi',     # and / verb ending
    'te',      # -and (connective)
    'da',      # is / was (informal)
    'ta',      # past tense
    'ru',      # present/future verb
    'nu',      # negative (classical)
})


# ── 2d. [YENİ] Genişletilmiş kelime sözlüğü — JLPT N5-N1 + pykakasi + anime ──
# Bu sözlük pykakasi ile üretilmiş 385+ kelimeyi içerir.
# Ağırlık: 1.3 (HIGH ile MED arası – belirsizlik payı var)
JP_VOCAB_EXT = frozenset({
    # ---- JLPT N5 pykakasi çıktısı ----
    'iku','kuru','suru','miru','kiku','yomu','kaku','nomu','taberu',
    'neru','okiru','hairu','deru','kaeru','au','akeru','shimeru',
    'tsukeru','kiru','hanasu','matsu','motsu','wakaru',
    'shiru','omou','iu','kureru','ageru','morau','kau','uru',
    'hataraku','yasumu','asobu',
    'ookii','chiisai','atarashii','furui','warui',
    'takai','yasui','nagai','mijikai','omoi','karui',
    'atsui','samui','atatakai','suzushii','muzukashii','yasashii',
    'omoshiroi','tanoshii','kanashii','ureshii','kowai',
    'ima','kyo','kyou','ashita','kinou','mainichi','maiasa','maiban',
    'asa','hiru','yoru','kotoshi','rainen',
    # ---- JLPT N4 pykakasi çıktısı ----
    'oshieru','oboeru','wasureru','mitsukeru','sagasu','tazuneru',
    'kangaeru','kimeru','tsutaeru','shinjiru','mamoru','tasukeru',
    'kowasu','naosu','tsukuru','kakeru','modoru','tsuzukeru',
    'hajimeru','owaru','yameru','erabu','yobu','ugoku',
    'shizuka','nigiyaka','genki','taihen','takusan','sukoshi',
    'zenzen','motto','zutto','yahari','tabun','kitto',
    'sugu','yukkuri','hayaku','osoku',
    # ---- JLPT N3 pykakasi çıktısı ----
    'kimochi','kioku','kanjo','shinrai','yuuki','kibou',
    'zetsubou','shiawase','kanashimi','yorokobi','odoroki',
    'sora','umi','yama','kawa','mori','hana','tsuki','hoshi',
    'kaze','ame','yuki','natsu','fuyu','haru','aki',
    'nakama','teki','mikata','senshi','mahou','sekai','uchu',
    'chikyu','jikan','mirai','kako','genzai','shunkan',
    'inochi','tamashii','kokoro','chikara','hikari','yami',
    'kizuna','yume','omoide','namida','egao','warai',
    # ---- Anime/manga/şarkı sözü özel ----
    'hashiru','hashitta','hashitte',
    'tobidasu','tobidashita',
    'tatakau','tatakatta','tatakatte','tatakaeru',
    'mamotta','mamoreru',
    'kagayaku','kagayaita','kagayaite','kirameku',
    'sakebu','sakenda','sakende',
    'nayamu','nayanda',
    'akogare','akogarete',
    'tsubasa','habataku','habataite',
    'mezameru','mezameta','mezasu','mezashite',
    'chikau','chikatta',
    'kizuku','kizuita',
    'tsutaeta','tsutaete',
    'todoku','todoita','todoite','todokeru',
    'musubu','musunde',
    'hanareru','hanareta','hanarete',
    'oikakeru','oikaketa',
    'furikaeru','furikaetta',
    'nakiakasu','hitomi','mabataki',
    'hohoemu','kagami',
    'maiagaru','maiagatta',
    'setsunai','setsunaku','setsunasa',
    'hakanai','hakanaku',
    'munashii','munashiku',
    'natsukashii','natsukashiku','natsukashisa',
    'itoshii','itoshiku','itoshisa',
    'oroka','hazukashii','hazukashiku',
    'urayamashii',
    'tensai','youkai','youki','ayakashi',
    'shinigami','shinki',
    'tsurugi','katana','shuriken','kunoichi',
    'shinobi','dojo','ryuu','ryu',
    'tooku','kienai','kieta',
    'wasurenai','wasureta','keshite','kesanaide',
    'irodoru','smakura','sakura','chiru','chitte','chitta',
    'nagare','nagareru','nagareta',
    'yurete','yureru',
    'azayaka','odayaka','shizukana','shizuku',
    'tokeru','toketa','tokeatte',
    'furueru','furueta',
    'terasu','teraseru','terashite',
    'hibiku','hibiita','hibiite','hibiki',
    'kasanaru','kasanatte',
    'midareru','midareta',
    'someru','somete','somatta',
    'umareru','umareta','umarete',
    'kieru','kieta','kiete',
    'tsuzuita','tsuzuite',
    'nakidasu','nakidashita',
    'tobitatsu',
    'yoroshiku','hajimemashite',
    'itadakimasu','gochisousama',
    'nandemonai','daijobu','daijoubu',
    'shoganai','mendokusai','mottainai',
    'yokatta','zannen','iyada',
    'yamete','tasukete','yurusanai',
    'wakatta','wakaranai',
    'senpai','kouhai',
    'chuunibyou','isekai',
    'shounen','shoujo','seiyuu',
    'daisuki','daikirai',
    'itsumo','issho','isshoni',
    'itsuka','itsudemo','nandemo',
    'hontouni','hontou',
    'gomen','gomennasai','sumimasen','arigatou',
    'yatta','yoshi','ganbatte','ganbare',
    'hidoi','urusai',
    'minna','minanna',
    'taiyo','taiyou',
    'koe','oto','uta','kotoba',
    'yoake','tasogare',
    'shinjitsu',
    'jidai','monogatari',
    'sugata','katachi','iro',
    'kimochi','kitai',
    # ---- Ek hece/morfoloji kalıpları ----
    'desu','deshita','dewa','janai','janaika',
    'masu','masen','mashita','mashou',
    'rashii','youda','hazu','beki',
    'saseru','sareru','rareru',
    'kudasai','nasai','naide',
    'hajime','owari','saigo','saisho',
    'arigatougozaimasu','konnichiwa','konbanwa',
    'ohayougozaimasu','sayounara','oyasuminasai',
    'tadaima','okaeri','ittekimasu','itterasshai',
    'otanoshimini','osewaninarimashita',
})

# ── 2e. [YENİ] Belirsiz İngilizce-Romaji çakışmaları — bu kelimeler TEK BAŞINA geçerse
# romaji olarak SAYILMAZ (İngilizce false-positive riski yüksek)
ENG_AMBIGUOUS_SINGLES = frozenset({
    'go','on','no','or','do','me','be','so','an','my','we','by','up','in',
    'at','he','if','is','it','of','to','as','us','am','do','ok','hi',
    'die','age','ago','air','all','aim','any','arm','art','ask','own',
    'big','bit','bus','can','car','cat','cut','dad','day','dog','eat',
    'end','eye','fat','fly','fun','get','god','got','guy','hey','hit',
    'hot','how','hug','job','joy','key','kid','kit','law','let','lie',
    'low','mad','man','map','may','mom','new','nor','not','now','num',
    'off','oil','old','one','out','pay','pie','pig','put','red','run',
    'sad','saw','say','sea','see','set','she','shy','sin','sit','six',
    'sky','son','sun','tap','tea','ten','the','tie','too','top','try',
    'van','war','way','who','why','win','wow','yet','you',
})


# ──────────────────────────────────────────────────────────────
# BÖLÜM 3: YARDIMCI FONKSİYONLAR
# ──────────────────────────────────────────────────────────────

# İngilizce'ye özgü sonek kalıpları (romajide ASLA bu yapılar yok)
_ENG_SUFFIX_PAT = re.compile(
    r'(ing|tion|sion|ness|ment|ity|ful|less|able|ible|ous|ive|'
    r'ary|ery|ory|ship|hood|ward|wise|esque|ify|ize|ise|ism|ist|'
    r'ent|ence|ance|ancy|ency|ed|er|est|ly|'     # common English morphemes
    r'ght|ph|ck|wh|str|scr|spr|spl|thr|'         # English consonant clusters
    r'wr|kn|gn|mb|mn|bt)$',
    re.IGNORECASE
)

# İngilizce konsonant kümeleri (Japoncada bunlar yok — hece yapısını bozar)
_ENG_CLUSTER_PAT = re.compile(
    r'[bcdfghjklmnpqrstvwxyz]{3,}|'   # 3+ ardışık konsonant
    r'(?<![aeiou])str|'                # str kümesi
    r'(?<![aeiou])spr|'                # spr kümesi
    r'(?<![aeiou])spl|'                # spl kümesi
    r'(?<![aeiou])scr|'                # scr kümesi
    r'[bcdfghjklmnpqrstvwxyz]ght|'    # -ght sonu
    r'wh[aeiou]',                      # wh- başlangıcı
    re.IGNORECASE
)

# Kesme işareti içeren yapılar (romajide yok: don't, I'm, aren't)
_APOSTROPHE_PAT = re.compile(r"[a-z]'[a-z]", re.IGNORECASE)

# Em dash / tire içeren İngilizce yapılar
_EMDASH_PAT = re.compile(r'\w+[—–]\w+')


def _tokenize(text: str):
    """Alfabe karakterlerinden oluşan kelimeleri çıkar (küçük harf)."""
    return re.findall(r'[a-zA-Z]+', text.lower())


def _word_score(word: str) -> float:
    """
    Tek bir kelimenin romaji puanini dondurur.
      +2.0 -> JP_PARTICLES icinde
      +1.8 -> JP_VOCAB_HIGH icinde
      +1.3 -> JP_VOCAB_EXT icinde  [YENi]
      +0.8 -> JP_VOCAB_MED icinde
      -0.8 -> ENG_AMBIGUOUS_SINGLES icinde (kisa belirsiz Ingilizce-Romaji)
      +-hece analizi katkisi da eklenir
    Returns float (negatif olabilir)
    """
    w = word.lower()

    # 1 karakter kelimeleri yoksay (cok belirsiz)
    if len(w) <= 1:
        return 0.0

    # Partikul (en guclu gosterge)
    if w in JP_PARTICLES:
        return 2.0

    # Yuksek guven Japonca kelime
    if w in JP_VOCAB_HIGH:
        return 1.8

    # [YENi] Genisletilmis JLPT + anime sozlugu
    if w in JP_VOCAB_EXT:
        return 1.3

    # Orta guven Japonca kelime
    if w in JP_VOCAB_MED:
        return 0.8

    # [YENi] Belirsiz Ingilizce-Romaji cakismasi — puan dusur
    if w in ENG_AMBIGUOUS_SINGLES:
        return -0.8

    # [YENi] kanwadict4.db kontrolu — 157,947 Japonca okuma
    # Kucuk agirlik: dogrulama icin kullanilir ama tek basina yeterli degil
    if w in _get_kanwa_set():
        return 1.1  # Kanwa sozlugunde bulundu = muhtemelen Japonca

    # Sozlukte yoksa hece analizi yap
    cov = _syllable_coverage(w)

    # Ingilizce morfem sonu -> puan dusur
    eng_suffix_penalty = 0.0
    if len(w) >= 4 and _ENG_SUFFIX_PAT.search(w):
        eng_suffix_penalty = 1.0

    # Ingilizce konsonant kumesi -> puan dusur
    cluster_penalty = 0.0
    if _ENG_CLUSTER_PAT.search(w):
        cluster_penalty = 0.7

    # Hece kapsami puani (0.0-1.0 -> -0.5-+0.5 arasi)
    base = (cov - 0.5) * 1.0

    return base - eng_suffix_penalty - cluster_penalty


# ──────────────────────────────────────────────────────────────
# BÖLÜM 4: ANA TESPİT FONKSİYONU
# ──────────────────────────────────────────────────────────────

def is_romaji_sentence(text: str, threshold: float = 0.48) -> bool:
    """
    Metnin Japonca romaji olup olmadığını CUMLE düzeyinde tespit eder.

    Args:
        text      : Kontrol edilecek metin (tag'lerden arındırılmış)
        threshold : Romaji eşiği (varsayılan: 0.48 — artırıldı false-positive azaltıldı)

    Returns:
        True  → Romaji tespit edildi (çevirme!)
        False → İngilizce veya başka dil (çevir)
    """
    if not text or not text.strip():
        return False

    text_clean = text.strip()

    # ── Hızlı ret: kesme işareti yapısı var → İngilizce kısaltma ──
    if _APOSTROPHE_PAT.search(text_clean):
        return False

    words = _tokenize(text_clean)
    if not words:
        return False

    word_count = len(words)

    # ── Çok kısa cümle: belirsiz, çevirmeye bırak ──
    if word_count < 2:
        return False

    # -- Puan hesapla --
    total_score = sum(_word_score(w) for w in words)
    normalized_score = total_score / word_count

    # -- Ek katki: Cumle yapisi analizi --
    bonus = 0.0
    particle_hits = sum(1 for w in words if w in JP_PARTICLES)
    if particle_hits >= 2:
        bonus += 0.25
    elif particle_hits >= 1:
        bonus += 0.12

    high_hits = sum(1 for w in words if w in JP_VOCAB_HIGH)
    if high_hits >= 2:
        bonus += 0.20
    elif high_hits >= 1:
        bonus += 0.10

    # [YENi] Genisletilmis sozluk isabetleri
    ext_hits = sum(1 for w in words if w in JP_VOCAB_EXT)
    if ext_hits >= 3:
        bonus += 0.22
    elif ext_hits >= 2:
        bonus += 0.13
    elif ext_hits >= 1:
        bonus += 0.06

    # [YENi] Tamamen ENG_AMBIGUOUS_SINGLES'tan olusan cumle -> kesinlikle Ingilizce
    ambiguous_only = all(w in ENG_AMBIGUOUS_SINGLES or len(w) <= 2 for w in words)
    if ambiguous_only:
        return False

    coverages = [_syllable_coverage(w) for w in words if len(w) >= 3]
    if coverages:
        avg_cov = sum(coverages) / len(coverages)
        if avg_cov >= 0.85:
            bonus += 0.18
        elif avg_cov >= 0.70:
            bonus += 0.08

    final_score = normalized_score + bonus

    return final_score >= threshold


def is_romaji_sentence_verbose(text: str, threshold: float = 0.32):
    """
    Debug amacli: (is_romaji, score, details) dondurul.
    Ana is_romaji_sentence() ile birebir ayni mantigi kullanir.
    """
    if not text or not text.strip():
        return False, 0.0, {}

    text_clean = text.strip()

    if _APOSTROPHE_PAT.search(text_clean):
        return False, -99.0, {'reason': 'apostrophe_found'}

    words = _tokenize(text_clean)
    if not words:
        return False, 0.0, {}

    word_count = len(words)
    if word_count < 2:
        return False, 0.0, {'reason': 'too_short'}

    # Skor hesapla (erken ret YOK)
    word_scores = {w: _word_score(w) for w in words}
    total_score = sum(word_scores.values())
    normalized_score = total_score / word_count

    bonus = 0.0
    particle_hits = sum(1 for w in words if w in JP_PARTICLES)
    if particle_hits >= 2:
        bonus += 0.25
    elif particle_hits >= 1:
        bonus += 0.12

    high_hits = sum(1 for w in words if w in JP_VOCAB_HIGH)
    if high_hits >= 2:
        bonus += 0.20
    elif high_hits >= 1:
        bonus += 0.10

    coverages = {w: _syllable_coverage(w) for w in words if len(w) >= 3}
    avg_cov = sum(coverages.values()) / len(coverages) if coverages else 0.0
    if avg_cov >= 0.85:
        bonus += 0.18
    elif avg_cov >= 0.70:
        bonus += 0.08

    final_score = normalized_score + bonus

    details = {
        'words': words,
        'word_scores': word_scores,
        'normalized_score': round(normalized_score, 3),
        'bonus': round(bonus, 3),
        'final_score': round(final_score, 3),
        'threshold': threshold,
        'particle_hits': particle_hits,
        'high_vocab_hits': high_hits,
        'avg_syllable_coverage': round(avg_cov, 3),
    }

    return final_score >= threshold, round(final_score, 3), details


# ──────────────────────────────────────────────────────────────
# BÖLÜM 5: GERİYE DÖNÜK UYUMLU SARICI
# subtitle_processor.py'deki is_romaji_text() ile aynı imza
# ──────────────────────────────────────────────────────────────

def is_romaji_text_v2(text: str) -> bool:
    """
    subtitle_processor.is_romaji_text() ile aynı davranış arayüzü.
    Geriye dönük uyumluluk için. Yeni kod is_romaji_sentence() kullanmalı.
    """
    return is_romaji_sentence(text)


# ──────────────────────────────────────────────────────────────
# BÖLÜM 6: HIZLI TEST (doğrudan çalıştırma)
# ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_cases = [
        # (metin, beklenen sonuç)
        # Romaji OLMALI (True)
        ("Itsuka ano doomu ippai no",                        True),
        ("Sairiumu de kimi wo somete ageru wa",              True),
        ("Ai de kimi wo someru wa A-A-A-Ah",                True),
        ("Watashitachi wa hoshi no ko",                      True),
        ("Kagayaku tame ni umarete kita no sa",             True),
        ("Kousa shite yuku supottoraito",                    True),
        ("Mada tarinai Hitokiwa kirameku ittousei",          True),
        ("Kimi ga nozonde kureta",                           True),
        ("Mou yume janai yume janai ribenji",                True),
        ("Ayashii wa watashi wo houttari shite",            True),
        ("Rikai shite nai torauma",                         True),
        ("Nani wo kare ni inon no somosomo",                True),
        ("Ikuka shinu ka tell me oshiete now",              True),
        ("Douse shinu nara chase me",                       True),
        ("Karamuna hen ni",                                  True),
        ("Owaraseru kono karuma",                           True),
        # İngilizce OLMAMALI (False)
        ("Suspicious, aren't you—leaving me behind like that", False),
        ("You don't even understand my trauma",             False),
        ("So what are you praying for him for",             False),
        ("Hey, even if I smile for you",                    False),
        ("I pretend everything's fine, kick the ground",    False),
        ("Test me if I'm going to die anyway then chase me", False),
        ("Go on, or die tell me tell me now",               False),
        ("Don't get tangled up in the weirdness",          False),
        ("I'll put an end to this karma",                  False),
        ("If I'm going to die anyway then chase me",       False),
        ("What if the tabloids run an expose",              False),
        ("Whose fault would that be",                       False),
        ("Ruby you'll probably get to work with your bro", False),
        # Karışık / Edge case
        ("Test me douse shinu nara chase me",              True),   # karma Japonca ağırlıklı
        ("Tell me tell me now",                             False),  # İngilizce
    ]

    print("=" * 65)
    print("ROMAJI FİLTRE TEST SONUÇLARI")
    print("=" * 65)
    pass_count = 0
    fail_count = 0
    for txt, expected in test_cases:
        result, score, details = is_romaji_sentence_verbose(txt)
        status = "OK" if result == expected else "FAIL"
        if result == expected:
            pass_count += 1
        else:
            fail_count += 1
        label = 'Romaji' if expected else 'Ing.'
        print(f"[{status}] [{score:+.3f}] Beklenen={label} | {txt[:55]}")
        if result != expected:
            print(f"        Detay: {details}")

    print("=" * 65)
    print(f"Sonuç: {pass_count}/{len(test_cases)} geçti, {fail_count} başarısız")
