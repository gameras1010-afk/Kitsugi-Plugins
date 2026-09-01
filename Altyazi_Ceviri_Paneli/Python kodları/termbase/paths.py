"""
termbase/paths.py
=================
Yol ve API yardımcıları.
"""
import os, re, json, time, threading
from typing import Optional, List

"""
termbase_manager.py — Terim Tabanı Yöneticisi
================================================
Altyazi cevirisi baslamadan once Fandom'dan gelen terimlerin
(organizasyon, yetenek, lokasyon, esya, terim) Turkce karsiligini
Gemini'ye belirletir ve kaydeder.

Karakterler bu asamada islenmez — altyazi cevirisinde ayrica gider.

Akis:
  1. pre_translate_terms()  → Gemini'ye gonder, EN→TR tablosu olustur
  2. get_termbase_tr_list() → Altyazi cevirisine sadece TR liste + karakterler gonder
"""

import os, re, json, time, datetime
from typing import Optional, Dict, List

if getattr(__import__('sys'), 'frozen', False):
    _DIR = os.path.dirname(__import__('sys').executable)
else:
    _DIR = os.path.dirname(os.path.abspath(__file__))

TERMBASE_DIR     = os.path.join(_DIR, 'termbase')
TERMBASE_TTL     = 30   # gun

_CAT_LABELS = {
    'skills':        'Yetenekler / Beceriler / Saldirilari',
    'locations':     'Lokasyonlar / Mekanlar',
    'organizations': 'Organizasyonlar / Gruplar',
    'items':         'Esyalar / Silahlar',
    'terminology':   'Ozel Terimler / Kavramlar',
}

_CAT_SHORT = {
    'skills':        'Yetenekler',
    'locations':     'Lokasyonlar',
    'organizations': 'Organizasyonlar',
    'items':         'Esyalar',
    'terminology':   'Ozel Terimler',
}


# ─── Yardimci ────────────────────────────────────────────────────────────────

def _split_title_season(title: str):
    """
    'sword art online|s1' → ('sword art online', 1)
    'Sword Art Online'    → ('Sword Art Online', None)
    """
    m = re.match(r'^(.*?)\|s(\d+)$', title.strip(), re.IGNORECASE)
    if m:
        base_title, sn = m.group(1).strip(), int(m.group(2))
    else:
        base_title, sn = title.strip(), None

    normalized = base_title.lower().strip()
    if "high school dxd new" in normalized:
        return "High School DxD", 2
    elif "high school dxd born" in normalized:
        return "High School DxD", 3
    elif "high school dxd hero" in normalized:
        return "High School DxD", 4
    elif "high school dxd" in normalized:
        return "High School DxD", sn

    # Clean franchise title dynamically
    clean_title = base_title
    # Remove bracket prefixes
    clean_title = re.sub(r'^[\[\{\(][^\]\}\)]*[\]\}\)]\s*', '', clean_title)
    # Remove season/part indicators and roman numerals
    clean_title = re.sub(
        r'[\s._:]*(?:Season\s*\d+|S\d{1,2}(?:E\d+)?|Part\s*\d+|'
        r'\d{1,2}(?:st|nd|rd|th)\s*Season|'
        r'Cour\s*\d+|\d+\.?\s*Sezon|'
        r'II|III|IV|V|VI|VII|VIII|IX|X|XI).*$',
        '', clean_title, flags=re.IGNORECASE
    ).strip()

    return clean_title, sn


def _base_path(anime_title: str) -> str:
    """Karaktersiz terimler — tüm sezonlar paylaşır. Season tag'ini title'dan söker."""
    os.makedirs(TERMBASE_DIR, exist_ok=True)
    clean_title, _ = _split_title_season(anime_title)
    
    # Try to resolve to the canonical Romaji title first
    try:
        from fandom_glossary import _get_canonical_anime_title
        clean_title = _get_canonical_anime_title(clean_title, verbose=False)
    except Exception:
        pass
    
    # Önce cache'den slug dene (AI olmadan — path çözümlemede ağ çağrısı olmaz)
    try:
        from fandom_glossary import find_wiki_slug, _normalize_title
        norm_title = _normalize_title(clean_title)
        slug = find_wiki_slug(norm_title, use_ai_fallback=False)
        if slug:
            safe = re.sub(r'[^a-z0-9]', '_', slug.lower())[:50].rstrip('_')
            return os.path.join(TERMBASE_DIR, f'{safe}_base.json')
    except Exception:
        pass

    safe = re.sub(r'[^a-z0-9]', '_', clean_title.lower())[:50].rstrip('_')
    return os.path.join(TERMBASE_DIR, f'{safe}_base.json')


def _chars_path(anime_title: str, season_num: int = None) -> str:
    """
    Franchise başına TEK karakter dosyası — sezon fark etmez.
    Örnek: highschooldxd_chars.json  (S1, S2, S3, ... hepsi buraya eklenir)
    """
    os.makedirs(TERMBASE_DIR, exist_ok=True)
    clean_title, _ = _split_title_season(anime_title)

    # Try to resolve to the canonical Romaji title first
    try:
        from fandom_glossary import _get_canonical_anime_title
        clean_title = _get_canonical_anime_title(clean_title, verbose=False)
    except Exception:
        pass

    # Wiki slug ile canonical isim dene
    try:
        from fandom_glossary import find_wiki_slug, _normalize_title
        slug = find_wiki_slug(_normalize_title(clean_title), use_ai_fallback=False)
        if slug:
            safe = re.sub(r'[^a-z0-9]', '_', slug.lower())[:50].rstrip('_')
            return os.path.join(TERMBASE_DIR, f'{safe}_chars.json')
    except Exception:
        pass

    safe = re.sub(r'[^a-z0-9]', '_', clean_title.lower())[:50].rstrip('_')
    return os.path.join(TERMBASE_DIR, f'{safe}_chars.json')


def _path(anime_title: str, season_num: int = None) -> str:
    """Eski tekli dosya yolu — geriye uyumluluk."""
    os.makedirs(TERMBASE_DIR, exist_ok=True)
    clean_title, _sn = _split_title_season(anime_title)
    sn = season_num or _sn
    
    # Try to resolve to the canonical Romaji title first
    try:
        from fandom_glossary import _get_canonical_anime_title
        clean_title = _get_canonical_anime_title(clean_title, verbose=False)
    except Exception:
        pass
    
    # Try to resolve to wiki slug for franchise sharing
    try:
        from fandom_glossary import find_wiki_slug, _normalize_title
        norm_title = _normalize_title(clean_title)
        slug = find_wiki_slug(norm_title, use_ai_fallback=False)
        if slug:
            safe = re.sub(r'[^a-z0-9]', '_', slug.lower())[:50].rstrip('_')
            stag = f'_s{sn}' if sn else ''
            return os.path.join(TERMBASE_DIR, f'{safe}{stag}.json')
    except Exception:
        pass

    safe = re.sub(r'[^a-z0-9]', '_', clean_title.lower())[:50].rstrip('_')
    stag = f'_s{sn}' if sn else ''
    return os.path.join(TERMBASE_DIR, f'{safe}{stag}.json')


def _fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        return (time.time() - os.path.getmtime(path)) / 86400 < TERMBASE_TTL
    except Exception:
        return False


def _load_keys() -> List[str]:
    """api_keys.txt'den API key listesini yukler (Google + OpenRouter)."""
    kp = os.path.join(_DIR, 'api_keys.txt')
    if not os.path.exists(kp):
        return []
    try:
        return [l.strip() for l in open(kp, encoding='utf-8')
                if l.strip() and not l.startswith('#')
                and (l.strip().startswith('AIzaSy') or l.strip().startswith('sk-or-v1-'))]
    except Exception:
        return []


def _make_keymanager():
    """
    Tek seferlik KeyManager olusturur. pre_translate_terms icerisinde
    tum batch'lere ayni instance gecilir — cursor + cooldown korunur.
    """
    try:
        from translator import KeyManager
        km = KeyManager()
        return km
    except Exception as e:
        print(f'[Termbase] KeyManager import hatasi: {e}')
        return None


def _call_api_with_keymanager(prompt: str, km=None) -> Optional[str]:
    """
    Termbase ON-ÇEVİRİSİ için API çağrısı.
    
    Öncelik Sırası:
      - translator_config.json veya user_preferences.json'da Antigravity modeli
        seçilmişse veya active_model_id AG ile başlıyorsa -> Önce Antigravity, hata olursa OpenRouter/Google.
      - Aksi takdirde -> Önce OpenRouter/Google keyleri, hata/key yoksa Antigravity fallback.
    """
    import requests
    import json as _json

    # 1. Config'leri oku
    _tcfg = {}
    try:
        _cfg_path = os.path.join(_DIR, 'translator_config.json')
        if os.path.exists(_cfg_path):
            _tcfg = _json.load(open(_cfg_path, encoding='utf-8'))
    except Exception:
        pass

    _ag_url = _tcfg.get('antigravity_url', 'http://localhost:8045/v1/chat/completions')
    _ag_key = _tcfg.get('antigravity_api_key', '')
    _active_model_id = _tcfg.get('active_model_id', '')
    _avail_models = _tcfg.get('available_models', {})

    # 2. Tercih edilen modeli oku
    model_or = 'google/gemini-2.0-flash-lite:free'  # Güvenli varsayılan
    try:
        _pref_path = os.path.join(_DIR, 'user_preferences.json')
        if os.path.exists(_pref_path):
            _pref_data = _json.load(open(_pref_path, encoding='utf-8'))
            model_or = _pref_data.get('ai_model', model_or)
    except Exception:
        pass

    # Antigravity öncelikli mi? (AG: öneki varsa veya sağlayıcı antigravity ise)
    is_ag_preferred = (
        model_or.startswith('AG:')
        or _active_model_id.startswith('AG:')
        or _avail_models.get(model_or, {}).get('provider') == 'antigravity'
    )

    # AG Model ismini belirle
    ag_model_name = 'gemini-2.5-flash'
    if model_or.startswith('AG:'):
        ag_model_name = model_or[3:]
    elif _avail_models.get(model_or, {}).get('provider') == 'antigravity':
        ag_model_name = model_or
    elif _active_model_id.startswith('AG:'):
        ag_model_name = _active_model_id[3:]
    else:
        # Uygun bir flash AG modeli seç
        ag_model_name = next(
            (k for k, v in _avail_models.items()
             if isinstance(v, dict) and v.get('provider') == 'antigravity'
             and 'flash' in k.lower() and 'pro' not in k.lower()),
            next((k for k, v in _avail_models.items()
                  if isinstance(v, dict) and v.get('provider') == 'antigravity'), 'gemini-2.5-flash')
        )

    # 3. API Çağrı Fonksiyonları
    def _try_antigravity():
        if not _ag_url or not _ag_key:
            print('[Termbase] Antigravity URL/key yapilandirilmamis.')
            return None
        try:
            print(f'[Termbase] Antigravity baglantisi kuruluyor: {ag_model_name} @ {_ag_url}')
            r_ag = requests.post(
                _ag_url,
                headers={
                    'Authorization': f'Bearer {_ag_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': ag_model_name,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'temperature': 0.2,
                    'max_tokens': 4096,
                },
                timeout=90,
            )
            if r_ag.status_code == 200:
                _txt = r_ag.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if _txt:
                    print('[Termbase] Antigravity cevabi basariyla alindi.')
                    return _txt
            print(f'[Termbase] Antigravity HTTP {r_ag.status_code}: {r_ag.text}')
        except Exception as e:
            print(f'[Termbase] Antigravity baglanti hatasi: {e}')
        return None

    def _try_keymanager():
        nonlocal km
        if km is None:
            km = _make_keymanager()
        if km is None or not km.keys:
            print('[Termbase] KeyManager icinde hic gecerli API key yok.')
            return None

        # OpenRouter modeli temizle (AG öneki varsa kaldır veya default'a geç)
        resolved_model_or = model_or
        if resolved_model_or.startswith('AG:'):
            resolved_model_or = 'google/gemini-2.0-flash-lite:free'
        
        model_gg = 'gemini-2.0-flash-exp'
        if 'gemini' in resolved_model_or.lower():
            model_gg = resolved_model_or.split('/')[-1] if '/' in resolved_model_or else resolved_model_or

        skip_402 = km.load_402_keys(resolved_model_or)
        tries = 0
        max_tries = len(km.keys)

        _key_switch_delay = 5.0
        try:
            _key_switch_delay = float(_tcfg.get('batch_delay_seconds', 5.0))
        except Exception:
            pass

        while tries < max_tries:
            key = km.get_next_available_key(skip_402_set=skip_402)
            if not key:
                print('[Termbase] Kullanilabilir key kalmadi.')
                break
            tries += 1
            is_google = key.startswith('AIzaSy')

            try:
                if is_google:
                    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_gg}:generateContent?key={key}'
                    r = requests.post(url,
                        headers={'Content-Type': 'application/json'},
                        json={
                            'contents': [{'parts': [{'text': prompt}]}],
                            'generationConfig': {'temperature': 0.2, 'maxOutputTokens': 4096},
                        }, timeout=60)
                else:
                    r = requests.post(
                        'https://openrouter.ai/api/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {key}',
                            'Content-Type': 'application/json',
                            'HTTP-Referer': 'https://antigravity.dev',
                        },
                        json={
                            'model': resolved_model_or,
                            'messages': [{'role': 'user', 'content': prompt}],
                            'temperature': 0.2,
                            'max_tokens': 4096,
                        }, timeout=60)

                sc = r.status_code
                if sc == 200:
                    if is_google:
                        txt = r.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    else:
                        txt = r.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    if txt:
                        print(f'[Termbase] API Key basarili ({tries}. denemede).')
                        return txt
                elif sc == 429:
                    print(f'[Termbase] 429 rate-limit — key cooldown ({tries}/{max_tries})')
                    km.mark_rate_limited(key)
                    if _key_switch_delay > 0 and tries < max_tries:
                        time.sleep(_key_switch_delay)
                elif sc in (401, 402):
                    print(f'[Termbase] {sc} exhausted — key silindi ({tries}/{max_tries})')
                    km.mark_as_exhausted(key, reason=str(sc))
                    skip_402.add(key)
                    max_tries = len(km.keys)
                else:
                    print(f'[Termbase] HTTP {sc} — key atlandi ({tries}/{max_tries}). Detay: {r.text}')
                    if _key_switch_delay > 0 and tries < max_tries:
                        time.sleep(_key_switch_delay)
            except Exception as e:
                print(f'[Termbase] API hatası ({tries}/{max_tries}): {e}')
                if _key_switch_delay > 0 and tries < max_tries:
                    time.sleep(_key_switch_delay)
        return None

    # 4. Yönlendirme Mantığını Çalıştır
    if is_ag_preferred:
        print('[Termbase] Yonlendirme: Antigravity Oncelikli.')
        res = _try_antigravity()
        if res:
            return res
        print('[Termbase] Yonlendirme: Antigravity basarisiz/bos, OpenRouter/Google deneniyor.')
        return _try_keymanager()
    else:
        print('[Termbase] Yonlendirme: OpenRouter/Google Oncelikli.')
        res = _try_keymanager()
        if res:
            return res
        print('[Termbase] Yonlendirme: OpenRouter/Google basarisiz/bos, Antigravity deneniyor.')
        return _try_antigravity()


# Eski _load_keys + _gemini — geriye uyumluluk icin birakildi ama artik kullanilmiyor
def _load_keys() -> list:
    f = os.path.join(_DIR, 'api_keys.txt')
    try:
        return [l.strip() for l in open(f, encoding='utf-8')
                if l.strip() and not l.startswith('#')
                and (l.strip().startswith('AIzaSy') or l.strip().startswith('sk-or-v1-'))]
    except Exception:
        return []


def _gemini(prompt: str, key: str, model: str = None) -> Optional[str]:
    """Eski tek-key wrapper — sadece geriye uyumluluk. _call_api_with_keymanager kullan."""
    return _call_api_with_keymanager(prompt)


def _build_prompt(anime_title: str, media_type: str,
                  season_num: int, terms: dict, metadata: dict = None) -> str:
    ctx = f'{anime_title}'
    if season_num:
        ctx += f' Sezon {season_num}'

    # Eserin türüne göre çeviri tonu ve kılavuzunu dinamik belirle
    media_tr = "anime"
    style_guideline = "fantastik edebiyata, oyun dünyasına ve anime jargonuna en uygun, en havalı ve epik"
    m_type_lower = (media_type or "anime").lower().strip()
    if m_type_lower in ("movie", "film"):
        media_tr = "film"
        style_guideline = "sinematik anlatıma, film sektörü altyazı ve dublaj standartlarına en uygun, akıcı ve doğal"
    elif m_type_lower in ("series", "tv", "dizi", "show"):
        media_tr = "dizi"
        style_guideline = "günlük konuşma diline, dizi dublaj/altyazı standartlarına en uygun, akıcı ve doğal"

    header = [
        f'Sen son derece profesyonel bir Türkçe {media_tr} yerelleştirme ve terim sözlüğü (glossary/termbase) uzmanısın.',
        f'Yapıt: {ctx} ({media_tr.upper()})',
        '',
        f'GÖREV: Sana verilen İngilizce terimleri, bu yapıtın konusuna, evrenine ve türüne en uygun şekilde Türkçe terim sözlüğüne çevir.',
        'Bu terimler altyazı çevirisinde doğrudan kullanılacağı için yapacağın çeviri son derece tutarlı, titiz ve hatasız olmalıdır.',
        '',
        'ÇOK KRİTİK VE KATİ KURALLAR:',
        '1. BAĞLAMI VE AÇIKLAMALARI OKU: Her terimin üzerinde "# Context: ..." şeklinde terimin ne olduğunu açıklayan bir wiki özeti veya kategori bilgisi bulunabilir.',
        '   Bu açıklamayı MUTLAKA oku ve terimin ne işe yaradığını, bir silah mı, büyü mü, yer adı mı yoksa unvan mı olduğunu anlayarak çevir.',
        '   Açıklamayı anlamadan ezbere/kelime kelime çeviri YAPMA!',
        '',
        '2. TÜRKÇE DİL BİLGİSİ VE İSİM TAMLAMALARI (EN BÜYÜK HATA KAYNAĞI):',
        '   - Kelime kelime birebir çeviri YAPMA. Türkçe isim tamlaması eklerini (-ı, -i, -u, -ü, -sı, -si vb.) doğru kullan.',
        '     * Yanlış: "Shadow Magic" -> "Gölge Büyü" | Doğru: "Gölge Büyüsü"',
        '     * Yanlış: "Wind Blade" -> "Rüzgar Bıçak" | Doğru: "Rüzgar Bıçağı" veya "Rüzgar Yarığı"',
        '     * Yanlış: "Chosen Heavenly Breasts" -> "Seçilmiş Cennet Göğüsler" | Doğru: "Seçilmiş Cennet Göğüsleri"',
        '     * Yanlış: "Dragon Slayer" -> "Ejderha Avcı" | Doğru: "Ejderha Avcısı"',
        '',
        '3. FANTASTİK VE COOL HAVA KORUNMALIDIR:',
        '   - Yapıtın {style_guideline} havasına uygun, havalı ve kulağa doğal gelen Türkçe terimler seç.',
        '   - Çocuksu, gülünç veya yapay duran çevirilerden kaçın.',
        '',
        '4. ÖZEL İSİMLER VE UYDURMA KELİMELER (DOKUNMA):',
        '   - Kurgusal özel isimler, karakter isimleri, uydurma marka/yer/dünya isimleri veya Japonca/fantastik özel terimler OLDUĞU GİBİ bırakılmalıdır.',
        '     * Örnek: "Aincrad" -> "Aincrad", "Elucidator" -> "Elucidator", "Kirito" -> "Kirito", "Gungnir" -> "Gungnir".',
        '     * Ancak tanımlayıcı İngilizce kelimeler çevrilmelidir: "Black Iron Great Sword" -> "Kara Demir Büyük Kılıç", "Teleport Crystal" -> "Işınlanma Kristali".',
        '',
        '5. TÜM LİSTEYİ TİTİZLİKLE CEVAPLA:',
        '   - Sana verilen terimlerin her birini tek tek analiz et, hiçbirini atlama.',
        '   - Çevirisi olmayan veya özel isim olan terimleri "Terim = Terim" şeklinde kendisiyle eşleştir.',
        '',
        'GENEL FORMAT (çıktıda sadece bu formatı kullan, başka hiçbir açıklama yazma):',
        'İngilizce Terim = Türkçe Karşılık',
        '(çevirisi yoksa veya özel isimse: İngilizce Terim = İngilizce Terim)',
        '',
        '━━━ KATEGORİ ÖZEL REHBERİ ━━━',
        '',
        '# Yetenekler / Beceriler',
        '  → İngilizce anlam taşıyan aktif/pasif becerileri Türkçe dil kurallarına göre çevir:',
        '    Hiding -> Saklanma, Fireball -> Ateş Topu, Vertical -> Dikey, Horizontal -> Yatay,',
        '    Earth Wall -> Toprak Duvarı, Night Vision -> Gece Görüşü, Holy Sword -> Kutsal Kılıç,',
        '    Wind Shear -> Rüzgar Kesilmesi / Rüzgar Yarığı, Heavy Slash -> Ağır Darbe / Ağır Savurma',
        '  → Japonca kökenli dövüş sanatları veya özel isimleri OLDUĞU GİBİ bırak: Senbon, Ukifune, Tsujikaze',
        '',
        '# Lokasyonlar',
        '  → Tanımlayıcı İngilizce yer isimlerini çevir:',
        '    Wolf Plains -> Kurt Ovası, World Tree -> Dünya Ağacı, 1st Floor -> 1. Kat,',
        '    Dungeons -> Zindanlar, Iron Castle -> Demir Kale, Dark Territory -> Karanlık Topraklar',
        '  → Hayali özel isimleri (uydurma kelimeler) OLDUĞU GİBİ bırak:',
        '    Aincrad, Alfheim, Alne, Pani, Centoria, Zumfut',
        '',
        '# Organizasyonlar',
        '  → İngilizce kelimelerden oluşan klan, lonca, çete veya kurum isimlerini çevir:',
        '    Death Gun -> Ölüm Silahı, Laughing Coffin -> Gülen Tabut,',
        '    Golden Apple -> Altın Elma, Sleeping Knights -> Uyuyan Şövalyeler,',
        '    Aincrad Liberation Force -> Aincrad Kurtuluş Gücü',
        '  → Kısaltma ve Japonca isimleri OLDUĞU GİBİ bırak: MMTM, ZEMAL, Fuumaningun, Argus',
        '',
        '# Eşyalar',
        '  → Tanımlayıcı İngilizce silah, zırh, iksir and materyal isimlerini çevir:',
        '    Blue Long Sword -> Mavi Uzun Kılıç, Black Iron Great Sword -> Kara Demir Büyük Kılıç,',
        '    Potions -> İksirler / İksir, Healing Crystal -> İyileşme Kristali, Hand Mirror -> El Aynası,',
        '    Ruby Ichor -> Yakut Özsuyu, Leather Armor -> Deri Zırh',
        '  → Kendine özgü hayali silah/eşya isimlerini OLDUĞU GİBİ bırak:',
        '    Elucidator, Invaria, AmuSphere, Procyon SL',
        '',
        '# Terimler / Terminoloji',
        '  → Neredeyse hepsini Türkçe karşılıklarına çevir (en detaylı yerelleştirilecek kategori):',
        '    Artificial Intelligence -> Yapay Zeka, Anti-Crystal Area -> Kristal Engelleyici Alan / Kristalsiz Alan,',
        '    Full Dive -> Tam Dalış, Virtual Reality -> Sanal Gerçeklik,',
        '    Armament Full Control Art -> Tam Teçhizat Kontrol Sanatı,',
        '    Boss -> Patron, Guild -> Lonca, Quest -> Görev, Party -> Grup / Parti',
        '  → Sadece hayali özel isimleri bırak: Augma, AmuSphere, Rath, Ymir',
        '',
        '━━━━━━━━━━━━━━━━━━━━━━━━━━━',
        '',
    ]

    lines = header[:]
    for cat, label in _CAT_LABELS.items():
        cat_terms = terms.get(cat, [])
        if not cat_terms:
            continue
        lines.append(f'# {label}')
        for t in cat_terms:
            t_meta = metadata.get(t) if metadata else None
            if t_meta:
                comments = []
                abstract = t_meta.get("abstract", "").strip()
                aliases = t_meta.get("aliases", [])
                cats = t_meta.get("categories", [])
                if abstract:
                    comments.append(f"Context: {abstract}")
                if aliases:
                    comments.append(f"Aliases: {', '.join(aliases)}")
                if cats:
                    comments.append(f"Categories: {', '.join(cats)}")
                if comments:
                    lines.append(f"  # " + " | ".join(comments))
            lines.append(f'{t} = ?')
        lines.append('')
    return '\n'.join(lines)


