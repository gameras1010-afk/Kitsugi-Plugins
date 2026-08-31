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


def _parse(response: str, terms: dict) -> dict:
    """'Terim = Ceviri' satirlarini parse eder. '?' donenleri EN=EN olarak birakir."""
    result = {cat: {} for cat in _CAT_LABELS}
    flat = {}
    for cat, tlist in terms.items():
        for t in tlist:
            flat[t.lower()] = (cat, t)

    if response:
        for line in response.splitlines():
            line = line.strip()
            if '=' not in line or line.startswith('#'):
                continue
            parts = line.split('=', 1)
            en_raw, tr_raw = parts[0].strip(), parts[1].strip()
            if en_raw.lower() not in flat:
                continue
            cat, orig = flat[en_raw.lower()]
            # "?" veya boş → çeviri yok, orijinalini kullan
            if tr_raw in ('?', '-', '—', '') or tr_raw == en_raw:
                result[cat][orig] = orig
            else:
                result[cat][orig] = tr_raw

    # Parse edilemeyenleri olduğu gibi bırak
    for cat, tlist in terms.items():
        for t in tlist:
            if t not in result.get(cat, {}):
                result.setdefault(cat, {})[t] = t

    return result


def consolidate_termbase_files(verbose: bool = True) -> None:
    """
    Scans the termbase directory, resolves all base and chars files to their canonical path,
    merges terms from redundant files into the canonical ones, and deletes redundant files.
    """
    if not os.path.isdir(TERMBASE_DIR):
        return

    # Process base files
    base_files = [f for f in os.listdir(TERMBASE_DIR) if f.endswith('_base.json')]
    for fname in base_files:
        path = os.path.join(TERMBASE_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_terms = meta.get('total_terms', sum(len(v) for v in data.get('terms', {}).values()) if 'terms' in data else 0)
            if total_terms == 0:
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Deleted empty base file: {fname}")
                continue
            anime_title = meta.get('anime')
            if not anime_title:
                anime_title = fname.replace("_base.json", "").replace("_", " ")
            
            # Resolve canonical path
            canonical = _base_path(anime_title)
            if os.path.abspath(path) != os.path.abspath(canonical):
                if verbose:
                    print(f"[Termbase Consolidation] Redundant base found: {fname} -> {os.path.basename(canonical)}")
                
                # Merge terms
                existing_canonical_data = {}
                if os.path.exists(canonical):
                    try:
                        with open(canonical, 'r', encoding='utf-8') as f:
                            existing_canonical_data = json.load(f)
                    except Exception:
                        pass
                
                canon_terms = existing_canonical_data.get('terms', {})
                redundant_terms = data.get('terms', {})
                
                # Deep merge terms
                for cat, terms_dict in redundant_terms.items():
                    if not isinstance(terms_dict, dict):
                        continue
                    canon_cat = canon_terms.setdefault(cat, {})
                    for en, tr in terms_dict.items():
                        if en not in canon_cat:
                            canon_cat[en] = tr
                
                # Save canonical
                meta_canon = existing_canonical_data.get('meta', {})
                clean_title, _ = _split_title_season(anime_title)
                meta_canon['anime'] = clean_title
                meta_canon['media_type'] = meta.get('media_type', meta_canon.get('media_type', 'anime'))
                meta_canon['translated_at'] = datetime.datetime.now().isoformat()
                meta_canon['type'] = 'base'
                total_terms_canon = sum(len(v) for v in canon_terms.values())
                meta_canon['total_terms'] = total_terms_canon
                
                if total_terms_canon > 0:
                    with open(canonical, 'w', encoding='utf-8') as f:
                        json.dump({'meta': meta_canon, 'terms': canon_terms}, f, ensure_ascii=False, indent=2)
                else:
                    if os.path.exists(canonical):
                        os.remove(canonical)
                
                # Delete redundant
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Merged and deleted redundant base file: {fname}")
        except Exception as e:
            if verbose:
                print(f"[Termbase Consolidation] Error merging {fname}: {e}")

    # Process character files — hepsini franchise başına TEK _chars.json'a birleştir
    char_files = [f for f in os.listdir(TERMBASE_DIR) if f.endswith('_chars.json')]
    for fname in char_files:
        path = os.path.join(TERMBASE_DIR, fname)
        if not os.path.exists(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_chars = meta.get('total_chars', len(data.get('characters', {})) if 'characters' in data else 0)
            if total_chars == 0:
                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] Deleted empty chars file: {fname}")
                continue
            anime_title = meta.get('anime')
            if not anime_title:
                # Dosya adından tahmin et (sezon suffix'ini sil)
                clean_fn = re.sub(r'(_s\d+)?_chars\.json$', '', fname, flags=re.IGNORECASE)
                anime_title = clean_fn.replace('_', ' ')

            # Canonical: sezon tag YOK
            canonical = _chars_path(anime_title)   # sezon argümanı geçilmiyor
            if os.path.abspath(path) != os.path.abspath(canonical):
                if verbose:
                    print(f"[Termbase Consolidation] Chars birleştiriliyor: {fname} → {os.path.basename(canonical)}")

                # Mevcut canonical'i oku
                canon_chars = {}
                if os.path.exists(canonical):
                    try:
                        with open(canonical, 'r', encoding='utf-8') as f:
                            canon_chars = json.load(f).get('characters', {})
                    except Exception:
                        pass

                # Sadece eksik karakterleri ekle
                added = 0
                for en, tr in data.get('characters', {}).items():
                    if en not in canon_chars:
                        canon_chars[en] = tr
                        added += 1

                clean_title, _ = _split_title_season(anime_title)
                total_chars_canon = len(canon_chars)
                if total_chars_canon > 0:
                    with open(canonical, 'w', encoding='utf-8') as f:
                        json.dump({
                            'meta': {
                                'anime': clean_title,
                                'translated_at': datetime.datetime.now().isoformat(),
                                'type': 'chars',
                                'total_chars': total_chars_canon,
                            },
                            'characters': canon_chars,
                        }, f, ensure_ascii=False, indent=2)
                else:
                    if os.path.exists(canonical):
                        os.remove(canonical)

                os.remove(path)
                if verbose:
                    print(f"[Termbase Consolidation] {added} karakter eklendi, redundant silindi: {fname}")
        except Exception as e:
            if verbose:
                print(f"[Termbase Consolidation] Chars merge hatası {fname}: {e}")

    # General cleanup: delete any json file in TERMBASE_DIR that has 0 terms or 0 characters
    for fname in os.listdir(TERMBASE_DIR):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(TERMBASE_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            meta = data.get('meta', {})
            total_terms = meta.get('total_terms', 0)
            total_chars = meta.get('total_chars', 0)
            is_base = meta.get('type') == 'base' or fname.endswith('_base.json')
            is_chars = meta.get('type') == 'chars' or fname.endswith('_chars.json')
            
            if is_base:
                t_count = sum(len(v) for v in data.get('terms', {}).values()) if 'terms' in data else 0
                if t_count == 0 or total_terms == 0:
                    os.remove(path)
                    if verbose:
                        print(f"[Termbase Consolidation] Cleaned up empty base file: {fname}")
            elif is_chars:
                c_count = len(data.get('characters', {})) if 'characters' in data else 0
                if c_count == 0 or total_chars == 0:
                    os.remove(path)
                    if verbose:
                        print(f"[Termbase Consolidation] Cleaned up empty chars file: {fname}")
        except Exception:
            pass


# ─── Ana Fonksiyonlar ─────────────────────────────────────────────────────────

def pre_translate_terms(
    anime_title: str,
    media_type: str = 'anime',
    season_num: int = None,
    season_title: str = None,
    force_refresh: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Anime/dizi/film icin on-ceviri yapar.

    YAPI:
      - _base.json       : skills/locations/orgs/items/terminology (tüm sezonlar paylaşır)
      - _s{n}_chars.json : sezona özel karakterler (Jikan)

    Karakterler Gemini'ye gönderilmez — olduğu gibi kaydedilir (Kirito→Kirito).
    Non-karakter base zaten varsa ve force_refresh değilse cache'den okunur.
    """
    # 0. Diskteki eski/mükerrer sezon dosyalarını tek canonical'e birleştir
    consolidate_termbase_files(verbose=verbose)

    clean_title, _sn = _split_title_season(anime_title)

    base_path  = _base_path(anime_title)
    chars_path = _chars_path(anime_title)   # ← sezon tag YOK, franchise başına tek dosya

    # ── 1. BASE (non-karakter) — Her zaman Fandom'a bak, sadece YENİ terimleri çevir ──
    # Mevcut çevirileri oku (varsa)
    existing_base_terms = {}
    if os.path.exists(base_path):
        try:
            existing_base_terms = json.load(open(base_path, 'r', encoding='utf-8')).get('terms', {})
        except Exception:
            pass

    if verbose and existing_base_terms:
        total_ex = sum(len(v) for v in existing_base_terms.values())
        print(f'[Termbase] Mevcut base: {total_ex} terim okundu → {os.path.basename(base_path)}')

    if True:  # Her zaman Fandom'a bak — _fresh kontrolü kasıtlı kaldırıldı
        # Load all candidate terms from Fandom cache/API
        terms_by_cat = {}
        metadata = {}
        try:
            from fandom_glossary import _load_cache
            cache = _load_cache()
            _search = clean_title.lower().strip()
            candidates = []
            for k in cache:
                base_k, _ = _split_title_season(k)
                if base_k.lower().strip() == _search:
                    candidates.append(k)
            # Select the entry with the most terms
            best_key = max(candidates,
                key=lambda k: sum(len(v) for v in cache[k].get('terms', {}).values()),
                default=None
            ) if candidates else None

            if best_key:
                raw_terms = cache[best_key].get('terms', {})
                metadata = cache[best_key].get('metadata', {})
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    lst = raw_terms.get(cat, [])
                    if lst:
                        terms_by_cat[cat] = lst
                if verbose:
                    total_raw = sum(len(v) for v in terms_by_cat.values())
                    print(f'[Termbase] Cache\'den {total_raw} terim alındı (tüm kategoriler)')
            else:
                # Fallback: build_glossary
                from fandom_glossary import build_glossary
                entry = build_glossary(anime_title, verbose=False, season_num=season_num, media_type=media_type)
                all_terms = entry.get("terms", {}) if entry else {}
                metadata = entry.get("metadata", {}) if entry else {}
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    if all_terms.get(cat):
                        terms_by_cat[cat] = all_terms[cat]
        except Exception as e:
            if verbose:
                print(f'[Termbase] Fandom hatasi: {e}')
            try:
                from fandom_glossary import build_glossary
                entry = build_glossary(anime_title, verbose=False, season_num=season_num, media_type=media_type)
                all_terms = entry.get("terms", {}) if entry else {}
                metadata = entry.get("metadata", {}) if entry else {}
                for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
                    if all_terms.get(cat):
                        terms_by_cat[cat] = all_terms[cat]
            except Exception:
                pass

        # Identify new terms (incremental translation check)
        new_terms_by_cat = {}
        for cat in ('skills', 'locations', 'organizations', 'items', 'terminology'):
            tlist = terms_by_cat.get(cat, [])
            existing_cat = existing_base_terms.get(cat, {})
            # Only keep terms not already translated in base
            new_list = [t for t in tlist if t not in existing_cat]
            if new_list:
                new_terms_by_cat[cat] = new_list

        total_new = sum(len(v) for v in new_terms_by_cat.values())
        if verbose:
            print(f'[Termbase] {anime_title}: Toplam {sum(len(v) for v in terms_by_cat.values())} terimden {total_new} tanesi yeni ve ceviriliyor...')

        merged = {cat: dict(existing_base_terms.get(cat, {})) for cat in _CAT_LABELS}

        if total_new:
            # Batch: max 60 terms per request
            BATCH = 60
            flat_new = [(cat, t) for cat, lst in new_terms_by_cat.items() for t in lst]
            batches = [flat_new[i:i+BATCH] for i in range(0, len(flat_new), BATCH)]

            _km = _make_keymanager()

            for bi, batch in enumerate(batches):
                b_by_cat = {}
                for cat, t in batch:
                    b_by_cat.setdefault(cat, []).append(t)
                if verbose:
                    b_total = sum(len(v) for v in b_by_cat.values())
                    print(f'[Termbase] Batch {bi+1}/{len(batches)}: {b_total} yeni terim...')
                prompt = _build_prompt(anime_title, media_type, season_num, b_by_cat, metadata=metadata)
                response = _call_api_with_keymanager(prompt, km=_km)
                batch_result = _parse(response, b_by_cat) if response else \
                               {cat: {t: t for t in lst} for cat, lst in b_by_cat.items()}
                for cat, mapping in batch_result.items():
                    merged.setdefault(cat, {}).update(mapping)

        # For terms that didn't get translated, fall back to self if not already in merged
        for cat in _CAT_LABELS:
            tlist = terms_by_cat.get(cat, [])
            cat_dict = merged.setdefault(cat, {})
            for t in tlist:
                if t not in cat_dict:
                    cat_dict[t] = t

        base_terms = merged

        # ── Manuel override'ları uygula ({safe}_overrides.json) ──────────────
        _safe_ov = re.sub(r'[^a-z0-9]', '_', clean_title.lower())[:50].rstrip('_')
        _ov_path = os.path.join(TERMBASE_DIR, f'{_safe_ov}_overrides.json')
        if os.path.exists(_ov_path):
            try:
                overrides = json.load(open(_ov_path, encoding='utf-8'))
                ov_applied = 0
                for cat, fixes in overrides.items():
                    for en, tr in fixes.items():
                        if en in base_terms.get(cat, {}):
                            base_terms[cat][en] = tr
                            ov_applied += 1
                if verbose and ov_applied:
                    print(f'[Termbase] {ov_applied} manuel override uygulandı.')
            except Exception as e:
                if verbose:
                    print(f'[Termbase] Override okuma hatası: {e}')

        # Base'i kaydet (Clean franchise title'ı meta.anime olarak kullan)
        try:
            total_out = sum(len(v) for v in base_terms.values())
            if total_out > 0:
                json.dump(
                    {
                        'meta': {
                            'anime': clean_title, 'media_type': media_type,
                            'translated_at': datetime.datetime.now().isoformat(),
                            'total_terms': total_out, 'type': 'base',
                        },
                        'terms': base_terms,
                    },
                    open(base_path, 'w', encoding='utf-8'),
                    ensure_ascii=False, indent=2,
                )
                if verbose:
                    print(f'[Termbase] Base kaydedildi: {total_out} terim → {os.path.basename(base_path)}')
            else:
                if os.path.exists(base_path):
                    os.remove(base_path)
                    if verbose:
                        print(f'[Termbase] Boş base dosyası silindi: {os.path.basename(base_path)}')
        except Exception as e:
            if verbose:
                print(f'[Termbase] Base kayit hatasi: {e}')

    # ── 2. KARAKTERLER — franchise başına TEK dosyaya merge ────────────────────
    # a) Mevcut karakter dosyasını oku
    existing_chars = {}
    if os.path.exists(chars_path):
        try:
            existing_chars = json.load(open(chars_path, 'r', encoding='utf-8')).get('characters', {})
            if verbose and existing_chars:
                print(f'[Termbase] Mevcut karakterler: {len(existing_chars)} → {os.path.basename(chars_path)}')
        except Exception:
            pass

    # b) Yeni karakterleri API'den çek
    new_chars_raw = {}
    _is_western = (media_type == 'series')
    try:
        from fandom_glossary import _jikan_get_characters, _load_cache
        if not _is_western:
            _jikan_chars = _jikan_get_characters(
                season_title=season_title or anime_title,
                series_title=anime_title if season_title else None,
            )
            if _jikan_chars:
                new_chars_raw = {c: c for c in _jikan_chars}
                if verbose:
                    print(f'[Termbase] Jikan: {len(new_chars_raw)} karakter alındı')
        else:
            # Batı dizisi → Fandom cache
            _gloss_cache = _load_cache()
            _search = clean_title.lower().strip()
            for k, v in _gloss_cache.items():
                base_k, _ = _split_title_season(k)
                if base_k.lower().strip() == _search and v.get('terms', {}).get('characters'):
                    new_chars_raw = {c: c for c in v['terms']['characters']}
                    if verbose:
                        print(f'[Termbase] Fandom cache: {len(new_chars_raw)} karakter')
                    break
    except Exception as e:
        if verbose:
            print(f'[Termbase] Karakter cekme hatasi: {e}')

    # c) Sadece EKSİK karakterleri mevcut listeye ekle
    added = 0
    for name, val in new_chars_raw.items():
        if name not in existing_chars:
            existing_chars[name] = val
            added += 1

    chars_as_is = existing_chars

    if verbose and added:
        print(f'[Termbase] {added} yeni karakter eklendi → toplam {len(chars_as_is)}')
    elif verbose and not added and chars_as_is:
        print(f'[Termbase] Karakter değişikliği yok — {len(chars_as_is)} karakter mevcut')

    # d) Kaydet (her zaman — yeni karakter eklenmese bile meta güncellenir)
    if chars_as_is and len(chars_as_is) > 0:
        try:
            json.dump(
                {
                    'meta': {
                        'anime': clean_title,
                        'translated_at': datetime.datetime.now().isoformat(),
                        'type': 'chars',
                        'total_chars': len(chars_as_is),
                    },
                    'characters': chars_as_is,
                },
                open(chars_path, 'w', encoding='utf-8'),
                ensure_ascii=False, indent=2,
            )
            if verbose:
                print(f'[Termbase] Karakter dosyası güncellendi: {len(chars_as_is)} → {os.path.basename(chars_path)}')
        except Exception as e:
            if verbose:
                print(f'[Termbase] Karakter kayit hatasi: {e}')
    else:
        try:
            if os.path.exists(chars_path):
                os.remove(chars_path)
                if verbose:
                    print(f'[Termbase] Boş karakter dosyası silindi: {os.path.basename(chars_path)}')
        except Exception:
            pass

    # ── 3. Birleştir ve döndür ──────────────────────────────────────────────────
    result = dict(base_terms)
    if chars_as_is:
        result['characters'] = chars_as_is
    return result


def get_termbase_tr_list(
    anime_title: str,
    season_num: int = None,
    include_characters: List[str] = None,
) -> str:
    """
    Altyazi cevirisi icin prompt blogu olusturur.
    Non-karakter terimler _base.json'dan, karakterler _chars.json'dan gelir.
    """
    # Base terimler (tum sezonlar icin ortak)
    terms = {}
    base_p = _base_path(anime_title)
    if os.path.exists(base_p):
        try:
            terms = json.load(open(base_p, 'r', encoding='utf-8')).get('terms', {})
        except Exception:
            pass

    # Karakterler: oncelik _chars.json, yoksa include_characters fallback
    chars_dict = {}
    chars_p = _chars_path(anime_title, season_num)
    if os.path.exists(chars_p):
        try:
            chars_dict = json.load(open(chars_p, 'r', encoding='utf-8')).get('characters', {})
        except Exception:
            pass
    all_chars = list(chars_dict.values()) or (include_characters or [])

    if not terms and not all_chars:
        return ''

    lines = ['─── ONAYLANMIŞ TERİMLER (bu listedeki terimleri kullan) ───']
    short_cats = {
        'skills':        'Yetenekler',
        'locations':     'Lokasyonlar',
        'organizations': 'Organizasyonlar',
        'items':         'Eşyalar',
        'terminology':   'Ozel Terimler',
    }
    for cat, label in short_cats.items():
        vals = list(terms.get(cat, {}).values())
        if vals:
            lines.append(f'{label}: {", ".join(vals)}')
    if all_chars:
        lines.append(f'Karakterler: {", ".join(all_chars)}')
    lines.append('─────────────────────────────────────────────────────────')
    return '\n'.join(lines)


def load_termbase(anime_title: str, season_num: int = None) -> dict:
    """Termbase'i diskten yukler (base + chars birlestirerek). Yoksa bos dict doner."""
    result = {}
    # Base terimler
    base_p = _base_path(anime_title)
    if os.path.exists(base_p):
        try:
            result.update(json.load(open(base_p, 'r', encoding='utf-8')).get('terms', {}))
        except Exception:
            pass
    # Karakterler
    chars_p = _chars_path(anime_title, season_num)
    if os.path.exists(chars_p):
        try:
            result['characters'] = json.load(open(chars_p, 'r', encoding='utf-8')).get('characters', {})
        except Exception:
            pass
    return result


def delete_termbase(anime_title: str, season_num: int = None) -> bool:
    """Termbase dosyalarini siler (base + chars)."""
    deleted = False
    for p in [_base_path(anime_title), _chars_path(anime_title, season_num)]:
        if os.path.exists(p):
            try:
                os.remove(p)
                deleted = True
            except Exception:
                pass
    return deleted


def list_termbases() -> List[dict]:
    """Tum termbase dosyalarini listeler (base ve chars ayri gosterilir)."""
    os.makedirs(TERMBASE_DIR, exist_ok=True)
    result = []
    for fname in os.listdir(TERMBASE_DIR):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(TERMBASE_DIR, fname)
        try:
            data = json.load(open(fpath, 'r', encoding='utf-8'))
            meta = data.get('meta', {})
            file_type = meta.get('type', 'legacy')  # 'base', 'chars', 'legacy'
            if file_type == 'chars':
                total = len(data.get('characters', {}))
            else:
                total = sum(len(v) for v in data.get('terms', {}).values())
            age = (time.time() - os.path.getmtime(fpath)) / 86400
            result.append({
                'file':         fname,
                'anime':        meta.get('anime', fname),
                'season':       meta.get('season'),
                'type':         file_type,
                'total_terms':  total,
                'translated_at': meta.get('translated_at', ''),
                'age_days':     round(age, 1),
                'fresh':        age < TERMBASE_TTL,
            })
        except Exception:
            pass
    return sorted(result, key=lambda x: (x['anime'], x.get('type', '')))


# ─── CLI Test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    title = sys.argv[1] if len(sys.argv) > 1 else 'Sword Art Online'
    season = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(f'=== Termbase pre-ceviri: {title} S{season} ===')
    result = pre_translate_terms(title, season_num=season, verbose=True)
    for cat, mapping in result.items():
        print(f'\n{cat.upper()} ({len(mapping)}):')
        for en, tr in list(mapping.items())[:5]:
            arrow = '(degismedi)' if en == tr else f'→ {tr}'
            print(f'  {en} {arrow}')
    print('\n=== Prompt blogu ===')
    chars = ['Kirito', 'Asuna', 'Alice']
    print(get_termbase_tr_list(title, season, include_characters=chars))
