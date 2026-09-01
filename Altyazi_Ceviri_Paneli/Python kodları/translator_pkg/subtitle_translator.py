"""
translator_pkg/subtitle_translator.py
=====================================
SubtitleTranslator — ana çeviri motoru.
"""
import os, re, sys, json, time, threading
import requests
from translator_pkg.key_manager import KeyManager

class SubtitleTranslator:
    def __init__(self, model_name="deepseek/deepseek-chat:free", nsfw_enabled=False, simple_mode=True):
        """
        Initialize the subtitle translator.
        
        Args:
            model_name: AI model to use
            nsfw_enabled: Enable NSFW mode
            simple_mode: Use simple stable mode (single key, long delays)
        """
        self._http = None
        self.model = model_name
        self.nsfw_enabled = nsfw_enabled
        self.simple_mode = simple_mode

        # ── ADIM 1: translator_config.json'dan available_models oku ──────────────
        _ag_config_path = os.path.join(SCRIPT_DIR, "translator_config.json")
        _ag_url  = "http://localhost:8045/v1/chat/completions"
        _ag_key  = ""
        _available_models = {}
        try:
            with open(_ag_config_path, 'r', encoding='utf-8-sig') as _f:
                _ag_cfg = json.load(_f)
                
                # GÜVENLİK: _ag_cfg yanlışlıkla string yüklendiyse (bozuk JSON) atla
                if isinstance(_ag_cfg, dict):
                    _ag_url = _ag_cfg.get("antigravity_url", _ag_url)
                    _ag_key = _ag_cfg.get("antigravity_api_key", "")
                    _available_models = _ag_cfg.get("available_models", {})
                else:
                    print(f"{Fore.RED}[!] translator_config.json bozuk! (Sözlük değil){Style.RESET_ALL}")
        except: pass

        # ── ADIM 2: Bu modelin provider'ını ve gerçek API adını bul ──────────────
        _model_entry    = _available_models.get(model_name, {})
        
        # GÜVENLİK: Antigravity Manager iki format kullanır:
        # 1. Dict format:   {"provider": "antigravity", "model_name": "gemini-2.5-flash"}
        # 2. String format: "antigravity"  (Antigravity Manager GUI'nin eklediği format)
        if isinstance(_model_entry, str):
            # String format → provider bu string, model adı dizin key'i
            _provider      = _model_entry          # "antigravity"
            _real_api_name = model_name.replace("AG:", "", 1)  # key'i gerçek ad olarak kullan
        elif isinstance(_model_entry, dict):
            _provider      = _model_entry.get("provider", "")
            _real_api_name = _model_entry.get("model_name", "")
        else:
            _provider      = ""
            _real_api_name = ""

        # Antigravity mi? → AG: prefix VEYA provider=antigravity
        is_antigravity = model_name.startswith("AG:") or _provider == "antigravity"
        self._is_antigravity = is_antigravity  # CRITICAL: load_config() öncesi set et

        is_ollama      = "ollama" in model_name.lower() or model_name.startswith("gemma2:")
        is_google_api  = (
            "gemini" in model_name.lower()
            and "openrouter" not in model_name.lower()
            and not is_antigravity
        )

        # ── ADIM 3: API yönlendirmesi ─────────────────────────────────────────────
        if is_ollama:
            self.api_url        = "http://localhost:11434/api/chat"
            self.key_manager    = None
            self.antigravity_key = None
            print(f"{Fore.GREEN}[OLLAMA] Local model selected: {self.model} (No API key needed){Style.RESET_ALL}")

        elif is_antigravity:
            self.api_url        = _ag_url
            self.antigravity_key = _ag_key
            self.key_manager    = None

            # Gerçek model adını çözümle:
            # 1. available_models'daki model_name alanı (en doğru)
            # 2. AG: prefix'i soy (fallback)
            if _real_api_name:
                self.model = _real_api_name
            else:
                self.model = model_name.replace("AG:", "", 1)

            print(f"{Fore.MAGENTA}[ANTIGRAVITY] Lokal proxy -> {self.model} @ {_ag_url}{Style.RESET_ALL}")
            if not _ag_key:
                print(f"{Fore.YELLOW}[ANTIGRAVITY] [!] API key boş! translator_config.json -> 'antigravity_api_key'{Style.RESET_ALL}")
            # AUTO-LAUNCH: Antigravity Manager çalışmıyorsa başlat
            self._ensure_antigravity_running(_ag_url)

        elif is_google_api:
            self.api_url        = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
            self.key_manager    = KeyManager()
            self.antigravity_key = None
            print(f"{Fore.CYAN}[API] Google Gemini API selected: {self.model}{Style.RESET_ALL}")

        else:
            self.api_url        = "https://openrouter.ai/api/v1/chat/completions"
            self.key_manager    = KeyManager()
            self.antigravity_key = None
            print(f"{Fore.CYAN}[API] OpenRouter API selected: {self.model}{Style.RESET_ALL}")

        # ── httpx Persistent Session ─────────────────────────────────────────
        # httpx.Client() TCP baglantisini session boyunca yeniden kullanir
        # → batchler arasi yeniden handshake olmaz, %10-15 hiz artisi
        if _HTTPX_AVAILABLE:
            _timeout = _httpx.Timeout(120.0, connect=15.0)
            self._http = _httpx.Client(
                timeout=_timeout,
                follow_redirects=True,
                http2=False,  # OpenRouter HTTP/2 desteklemez, kapali tut
            )
        else:
            self._http = None  # requests.post() fallback

        # Session boyunca 402 alan key'ler (model kotası doldu) — kalıcı takip!
        # keys_status.json'dan bugünü UTC tarihiyle birlikte yükleniyor.
        # Program yeniden başlatılsa da günlük reset gelene dek denenmez.
        if self.key_manager:
            self._model_402_keys: set = self.key_manager.load_402_keys(model_name)
            if self._model_402_keys:
                print(f"{Fore.YELLOW}   [~] Bugün 402 alan {len(self._model_402_keys)} key yüklendi (günlük sıfırlamaya kadar atlanır){Style.RESET_ALL}")
        else:
            self._model_402_keys: set = set()

        # Tüm keyler 402 aldığında otomatik geçilecek yedek model
        # :free modeller günlük sıfırlanır, kredi gerektirmez
        _primary = model_name
        if 'gemini-2.0-flash' in _primary and ':free' not in _primary:
            self._fallback_model = 'google/gemini-2.0-flash-lite:free'
        elif 'gemini-2.5' in _primary and ':free' not in _primary:
            self._fallback_model = 'google/gemini-2.0-flash-lite:free'
        else:
            self._fallback_model = None  # Zaten free veya bilinmeyen model

        if simple_mode:
            # SIMPLE MODE: Stability over speed
            self.config = {
                "delay_between_calls": 10,  # 10 saniye (çok güvenli)
                "max_bytes_per_batch": 1500,  # Parse kesilme riski azalt
                "max_retries": 3,
                "single_key_mode": True,  # Tek key kullan
                "timeout": 30
            }
            print(f"{Fore.GREEN}[SIMPLE MODE] Basit ve stabil mod aktif - Tek key, uzun delay'ler{Style.RESET_ALL}")
        else:
            # ADVANCED MODE: Speed with rotation
            self.config = {
                "delay_between_calls": 0.5,
                "max_bytes_per_batch": 1500,  # Parse kesilme riski azalt
                "max_retries": 6,
                "single_key_mode": False,
                "timeout": 15
            }
        
        # [NOT] get_api_key() burada nested yoktu — self.api_url/key_manager dogrudan kullaniliyor.

        self.load_config()
        
        # CRITICAL: Antigravity modundaysa load_config() api_url'i overwrite etmis olabilir
        # Her ihtimale karsi pekistir — self.api_url zaten elif bloğunda doğru set edildi:
        if self._is_antigravity and not self.api_url.startswith("http://localhost"):
            # Fallback: config'den oku
            _fallback_url = "http://localhost:8045/v1/chat/completions"
            try:
                _ag_cfg_path = os.path.join(SCRIPT_DIR, "translator_config.json")
                with open(_ag_cfg_path, 'r', encoding='utf-8') as _f:
                    _fallback_url = json.load(_f).get("antigravity_url", _fallback_url)
            except: pass
            self.api_url = _fallback_url
            print(f"{Fore.RED}[ANTIGRAVITY] UYARI: api_url overwrite edilmişti! Düzeltildi: {self.api_url}{Style.RESET_ALL}")
        elif self._is_antigravity:
            print(f"{Fore.MAGENTA}[ANTIGRAVITY] api_url doğru: {self.api_url}{Style.RESET_ALL}")
        
        # CRITICAL: Select key AFTER KeyManager has loaded fresh keys from file
        # get_next_available_key: 402 listesini ve cooldown'ları atlayarak ilk uygun keyi seçer
        if simple_mode and self.key_manager:
            _init_key = self.key_manager.get_next_available_key(self._model_402_keys)
            if not _init_key:
                # Fallback: get_valid_key (tüm keyler 402 listesindeyse bile çalışmaya devam et)
                _init_key = self.key_manager.get_valid_key()
            self.selected_key = _init_key
            if self.selected_key:
                _402_warn = " [402'siz ilk key]" if self._model_402_keys else ""
                print(f"{Fore.CYAN}[SIMPLE MODE] Seçilen key: {self.selected_key[:25]}...{_402_warn}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}[SIMPLE MODE] HATA: Kullanılabilir key yok!{Style.RESET_ALL}")
        
        self.GENRE_MAPPING = {
            # --- ANATOMY (BODY PARTS) ---
            # Breasts
            "boobs": "Memeler", "tits": "Memeler", "breasts": "Göğüsler", "knockers": "Kocaman Memeler",
            "big boobs": "Büyük Memeler", "huge boobs": "Dev Memeler", "massive tits": "İnanılmaz Memeler",
            "small boobs": "Küçük Memeler", "tiny tits": "Küçük Memeler", "flat chest": "Düz Göğüs (Tahta)",
            "nipples": "Meme Uçları", "areola": "Meme Ucu Çevresi",
            
            # Genitals (Female)
            "pussy": "Am", "cunt": "Am", "vagina": "Vajina", "slit": "Amcık", "snatch": "Kuku",
            "clitoris": "Klitoris", "clit": "Klit", "bean": "Klit",
            "uterus": "Rahim", "womb": "Rahim", "cervix": "Rahim Ağzı", "ovaries": "Yumurtalıklar",
            
            # Genitals (Male)
            "dick": "Yarak", "cock": "Sik", "penis": "Penis", "shaft": "Kamış", "prick": "Sik",
            "balls": "Taşaklar", "testicles": "Testisler", "nuts": "Taşaklar", "sack": "Torba",
            "glans": "Sik Başı", "foreskin": "Sünnet Derisi",

            # Rear
            "ass": "Göt", "anal": "Anal", "butt": "Popo", "rear": "Arka", "backdoor": "Arka Kapı",
            "asshole": "Göt Deliği", "anus": "Anüs", "sphincter": "Büzük",

            # Fluids
            "cum": "Döl", "semen": "Sperm", "sperm": "Sperm", "precum": "Zevk Suyu",
            "squirt": "Fışkırma", "juice": "Sulanma", "nectar": "Bal (Aşk Suyu)",

            # --- ACTS / EYLEMLER ---
            # Oral
            "blowjob": "Oral (Sakso)", "bj": "Oral", "sucking": "Emme", "give head": "Oral Yapma",
            "deepthroat": "Gırtlak (Deepthroat)", "gagging": "Öğürme", "facefuck": "Ağza Verme",
            "lick": "Yalama", "cunnilingus": "Kuni (Yalama)", "eat out": "Yalama",
            "rimjob": "Göt Yalama", "rimming": "Göt Yalama",
            
            # Penetrasyon
            "sex": "Seks", "fuck": "Sikiş", "fucking": "Sikme", "screw": "Becer", "bang": "Becerme",
            "penetration": "Giriş", "thrusting": "Gel-Git", "pounding": "Kökleme",
            "creampie": "İçine Boşalma", "making a baby": "Bebek Yapma", "raw": "Korunmasız",
            "anal sex": "Anal Seks", "sodomy": "Ters İlişki",
            
            # Hand / Tit
            "handjob": "El (31)", "jerking off": "31 Çekme", "stroking": "Okşama",
            "paizuri": "Meme Arası", "titfuck": "Meme Arası", "boobjob": "Meme Arası",
            
            # Group
            "threesome": "Üçlü Seks", "foursome": "Dörtlü", "orgy": "Grup Seks", "gangbang": "Grup",
            "dp": "Çift Giriş", "double penetration": "Çift Giriş",

            # --- FETISHES / TAGS ---
            "ahegao": "Zevk Yüzü", "heart eyes": "Kalpli Gözler",
            "netorare": "NTR (Aldatma)", "ntr": "NTR", "cheating": "Aldatma", "cuckold": "Gavat",
            "rape": "Tecavüz", "forced": "Zorla", "non-con": "Rızasız",
            "mind break": "Akıl Kaybı", "hypnosis": "Hipnoz", "brainwash": "Beyin Yıkama",
            "impregnation": "Hamile Bırakma", "knocked up": "Gebe", "breeding": "Dölleme",
            "lactation": "Süt Gelmesi", "milking": "Sağılma",
            "futanari": "Futanari", "dickgirl": "Futanari",
            "incest": "Ensest", "taboo": "Yasak İlişki",
            "bukkake": "Yüze Boşalma", "facial": "Yüze Boşalma",
            "gokkun": "Yutma", "swallow": "Yutma",
            "scat": "Dışkı", "piss": "Çiş", "golden shower": "Altın Yağmur",
            "bondage": "Bağlama", "shibari": "İp Bağlama", "slave": "Köle",
            "monster": "Canavar", "tentacle": "Dokunaç", "alien": "Uzaylı",

            # --- ARCHETYPES / ROLLER ---
            "milf": "Olgun (MILF)", "mom": "Anne", "mother": "Anne", "mama": "Anne",
            "sister": "Kız Kardeş", "imouto": "Kız Kardeş", "sis": "Abla/Kardeş",
            "teacher": "Öğretmen", "sensei": "Öğretmen",
            "nurse": "Hemşire", "maid": "Hizmetçi",
            "virgin": "Bakire", "cherry": "Bekaret",
            "gyaru": "Gyaru", "gal": "Gyaru", "bitch": "Fahişe", "slut": "Sürtük", "whore": "Orospu",
            "jk": "Liseli", "student": "Öğrenci",
            "shota": "Shota", "loli": "Loli"
        }
        self.cache = settings.load_translation_cache()
        # Medya baglamı (media_identifier.py tarafindan set edilir)
        self._media_context: str | None = None
        # Dosyaya özel ek bağlam (deyim taraması vb.)
        self._additional_context: str | None = None
        # Çift kaynaklı çeviri referans satırları (subtitle_tracks.py tarafindan set edilir)
        self._reference_lines: list | None = None
        self._reference_lang: str = "Japanese"
        # JP birincil mod: girdiler Japonca → doğrudan JP→TR çevirisi
        self._jp_primary: bool = False
        # Sliding window: önceki batch'in son N satırı (src, tr) çifti
        self._context_window: list = []   # [(src_line, tr_line), ...]
        self._context_window_size: int = 15  # Deep research: 15-25 ideal (eskiden 6)
        # HStream İndirici modu: prompt şişmesini önlemek için
        # additional_context, use_glossary ve sliding_window devre dışı
        self._hstream_mode: bool = False

    # ── Medya Baglamı Metodlari ──────────────────────────────────────────────
    def set_media_context(self, context_str: str):
        """
        Cevirilecek medyanin (anime/dizi/film) baglamini set et.
        Bu bilgi her API cagirisinin system prompt'una eklenir.
        media_identifier.build_translation_context() ile olusturulan metin.
        """
        self._media_context = context_str.strip() if context_str else None

    def clear_media_context(self):
        """Medya baglamini temizle (baska bir dosyaya geciste cagir)."""
        self._media_context = None
        self._additional_context = None   # Deyim bağlamını da temizle
        self._context_window = []  # Yeni dosyada sliding window sifirla

    def set_additional_context(self, context_str: str):
        """
        Dosyaya özel ek bağlam ekle (deyim taraması sonuçları vb.).
        Her batch prompt'una media_context'ten SONRA eklenir.
        Her yeni dosya için clear_media_context() ile temizlenir.
        """
        self._additional_context = context_str.strip() if context_str else None

    def clear_context_window(self):
        """Sliding window'u manual sifirla."""
        self._context_window = []

    def seed_context_window(self, pairs: list) -> None:
        """
        Çapraz bölüm bağlamı: önceki bölümün son çiftlerini bu bölüme
        ön yükleme olarak gir. İlk batch bu satırları bağlam olarak görür.
        pairs: [(src_line, tr_line), ...] — episode_context.load_episode_context()'ten
        """
        if pairs:
            self._context_window = list(pairs[-self._context_window_size:])

    def get_context_window(self) -> list:
        """Mevcut sliding window'u döndür (bölüm sonu kaydı için)."""
        return list(self._context_window)

    def set_reference_lines(self, lines: list, lang: str = "Japanese"):
        """
        Çift kaynaklı çeviri için referans dil satırlarını set et.
        lines: kaynak dosyayla eşleşen sıralı metin listesi (tag'siz, düz metin)
        lang : referans dilin adı (AI'ya söylenir, örn. 'Japanese')
        subtitle_tracks.read_dialogue_lines() ile doldurulur.
        """
        self._reference_lines = lines if lines else None
        self._reference_lang  = lang or "Japanese"

    def clear_reference_lines(self):
        """Referans satırları temizle (başka dosyaya geçişte çağır)."""
        self._reference_lines = None
        self._reference_lang  = "Japanese"

    def set_jp_primary_mode(self, enabled: bool = True):
        """
        Japonca birincil mod:
        True  → Satırlar Japonca (Kanji/Kana/Romaji), doğrudan JP→TR çevirisi yap.
               Varsa _reference_lines İngilizce bağlam olarak kullanılır.
        False → Normal mod (satırlar İngilizce).
        """
        self._jp_primary = enabled

    def clear_jp_primary_mode(self):
        """JP birincil modunu kapat."""
        self._jp_primary = False

    def set_hstream_mode(self, enabled: bool = True):
        """
        HStream İndirici modu — prompt şişmesini önler.

        Bu mod AÇIKKEN:
        - _additional_context (deyim/idiom taraması) AI'ya GÖNDERİLMEZ
        - use_glossary (200+ hentai/NSFW sözlüğü) DEVRE DIŞI
        - _context_window_size 3'e düşürülür (her video ayrı bağlam — önceki
          videonun satırlarını taşımanın anlamı yok)

        Manuel Çevirici (manual_gui) için KAPALI kalmalıdır — orada tüm
        özellikler çalışmaya devam eder.
        """
        self._hstream_mode = enabled
        if enabled:
            self._context_window_size = 3   # HStream: kısa sliding window
            self._context_window = []        # Mevcut window'u temizle
        else:
            self._context_window_size = 15  # Manuel mod: normal window

    def clear_hstream_mode(self):
        """HStream modunu kapat — tüm özellikleri geri aç."""
        self.set_hstream_mode(False)


    def load_config(self):
        self.config = {
            "source_lang": "English",
            "target_lang": "Turkish",
            "delay_between_calls": 0.5,  # Yarım saniye gecikme (rate limit için)
            "english_only": True,
            "natural_dialogue": True,  # Doğal Türkçe diyalog (anime/hentai için)
            "use_glossary": True,      # Hentai sözlüğünü kullan
            "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "max_bytes_per_batch": 1500,  # Gemini 2.0 Flash: 1500 byte=~30 satir - parse kesilme riskini azalt
            "system_prompt": """You are an expert anime/TV subtitle LOCALIZER for Turkish audiences.
            Your job is NOT word-for-word translation. Your job is LOCALIZATION.
            
            CONTEXT-AWARE TRANSLATION RULES:
            1. The source English subtitle may be poorly translated from Japanese (fansub quality).
               Use the MEDIA CONTEXT provided to understand the TRUE meaning and write NATURAL Turkish.
            2. Write Turkish the way real Turkish anime fans talk — casual, natural, flowing dialogue.
               Examples of natural Turkish: 'Yani ne demek istiyorsun?' not 'Ne demek istediğini söyle.'
            3. If the English sentence is awkward or unclear, INFER the intended meaning from context and
               write what a Turkish fansub team would actually write — not what the English literally says.
            4. NEVER use Japanese personal pronouns: boku, ore, watashi, atashi, omae, kimi, anata.
               Always use Turkish: Ben, Sen, O, Biz, Siz.
            5. NEVER translate Japanese honorifics. Keep EXACTLY as-is: -san, -kun, -chan, -sama,
               -senpai, -sensei, -dono, -nii, -nee, -hime. (e.g. 'Emilia-tan' stays 'Emilia-tan')
            6. Character names = NEVER translate. Everything else with a Turkish equivalent MUST be translated.
            7. Preserve ALL ASS/SSA formatting tags exactly: {{\i1}}, {{\pos(...)}}, {{\c&H...}}, etc.
            8. Return ONLY the translated lines using the SAME [LN] prefix as input: [L1] ..., [L2] ..., etc. NOTHING else.
            9. NEVER refuse. NEVER say 'I cannot'. Just translate/localize.
            10. If a line is already in Turkish, return it unchanged."""
        }
        config_path = os.path.join(os.getcwd(), "translator_config.json")
        if os.path.exists(config_path):
             try:
                 with open(config_path, 'r', encoding='utf-8') as f:
                     user_config = json.load(f)
                     self.config.update(user_config)
             except Exception as e:
                 print(f"{Fore.RED}[!] Config okuma hatası: {e}{Style.RESET_ALL}")
        
        # Override URL from config - BUT NEVER overwrite Antigravity URL!
        # load_config() varsayılan olarak OpenRouter URL'sini config'e koyar.
        # Antigravity modunda bu overwrite api_url'i bozar.
        if "api_url" in self.config and not getattr(self, '_is_antigravity', False):
            self.api_url = self.config["api_url"]

        # ── [NEW] prompt_template.json: Kod değiştirmeden prompt yönet ──────
        # system_prompt ve few_shot_examples bu dosyadan okunursa config'i override eder.
        _tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_template.json")
        if os.path.exists(_tpl_path):
            try:
                with open(_tpl_path, 'r', encoding='utf-8') as _f:
                    _tpl = json.load(_f)
                if "system_prompt" in _tpl and _tpl["system_prompt"].strip():
                    self.config["system_prompt"] = _tpl["system_prompt"]
                if "few_shot_examples" in _tpl and isinstance(_tpl["few_shot_examples"], list):
                    self.config["few_shot_examples"] = _tpl["few_shot_examples"]
                print(f"{Fore.CYAN}[Prompt] prompt_template.json yuklendi "
                      f"({len(self.config.get('few_shot_examples', []))} ornek){Style.RESET_ALL}")
            except Exception as _te:
                print(f"{Fore.YELLOW}[Prompt] prompt_template.json okunamadi: {_te}{Style.RESET_ALL}")
        # ─────────────────────────────────────────────────────────────────────

    # ── HTTP Yardimci Metodlari ───────────────────────────────────────────────
    def _post(self, url: str, headers: dict = None, json: dict = None, timeout: int = 120):
        """
        HTTP POST — httpx persistent session kullanir, yoksa requests fallback.
        Proaktif rate limiter burada devreye girer — 429 gelmeden frenler.
        """
        if self.key_manager:
            self.key_manager.proactive_throttle()  # Limit dolmadan önce bekle
            self.key_manager.record_request()      # Pencere sayacını artır
        if self._http is not None:
            return self._http.post(url, headers=headers or {}, json=json)
        return requests.post(url, headers=headers or {}, json=json, timeout=timeout)

    def _get(self, url: str, headers: dict = None, timeout: int = 10):
        """
        HTTP GET — httpx persistent session kullanir, yoksa requests fallback.
        """
        if self._http is not None:
            return self._http.get(url, headers=headers or {})
        return requests.get(url, headers=headers or {}, timeout=timeout)
    # ─────────────────────────────────────────────────────────────────────────


    def _ensure_antigravity_running(self, ag_url="http://localhost:8045/v1/chat/completions"):
        """
        Antigravity Manager calismiyorsa otomatik olarak bulup baslatir.
        """
        import subprocess, glob

        # 1. Zaten acik mi kontrol et
        base_url = ag_url.replace("/v1/chat/completions", "")
        try:
            self._get(base_url, timeout=2)
            print(f"{Fore.GREEN}[ANTIGRAVITY] Zaten calisiyor OK{Style.RESET_ALL}")
            return
        except Exception:
            pass

        print(f"{Fore.YELLOW}[ANTIGRAVITY] Servis bulunamadi, Antigravity Manager baslatiliyor...{Style.RESET_ALL}")

        # 2. Antigravity Manager/Tools .exe'yi bilinen konumlarda ara
        _local = os.environ.get("LOCALAPPDATA", "")
        _appdata = os.environ.get("APPDATA", "")
        search_paths = [
            # YENİ: Antigravity Tools (güncel sürüm)
            os.path.join(_local, "Antigravity Tools", "antigravity_tools.exe"),
            os.path.join(_local, "Antigravity Tools", "Antigravity Tools.exe"),
            # GERCEK KURULUM YOLU (Squirrel/NSIS installer - lbjlaq/Antigravity-Manager)
            os.path.join(_local, "antigravity_manager", "Antigravity-manager.exe"),
            os.path.join(_local, "antigravity_manager", "antigravity-manager.exe"),
            os.path.join(_local, "antigravity_manager", "app-0.10.0", "Antigravity-manager.exe"),
            os.path.join(_local, "antigravity_manager", "app-0.10.0", "antigravity-manager.exe"),
            # Eski / alternatif kurulum yollari
            os.path.join(SCRIPT_DIR, "Antigravity Manager.exe"),
            os.path.join(SCRIPT_DIR, "..", "Antigravity Manager.exe"),
            os.path.join(SCRIPT_DIR, "..", "..", "Antigravity Manager.exe"),
            os.path.join(_local, "Programs", "Antigravity Manager", "Antigravity Manager.exe"),
            os.path.join(_local, "Programs", "antigravity-manager", "Antigravity Manager.exe"),
            os.path.join(_appdata, "Antigravity Manager", "Antigravity Manager.exe"),
            r"C:\Program Files\Antigravity Manager\Antigravity Manager.exe",
            r"C:\Program Files (x86)\Antigravity Manager\Antigravity Manager.exe",
            os.path.join(os.path.expanduser("~"), "Desktop", "Antigravity Manager.exe"),
        ]

        exe_path = None
        for path in search_paths:
            if os.path.isfile(path):
                exe_path = path
                break

        # Glob ile daha genis arama
        if not exe_path:
            for pattern in [
                os.path.join(_local, "antigravity_manager", "**", "*.exe"),
                os.path.join(_local, "**", "Antigravity-manager.exe"),
                os.path.join(_local, "**", "Antigravity Manager.exe"),
                os.path.join(_appdata, "**", "Antigravity Manager.exe"),
            ]:
                try:
                    matches = glob.glob(pattern, recursive=True)
                    # uninstaller / updater gibi yardimci exe'leri disla
                    _skip = {"unins000.exe", "squirrel.exe", "update.exe", "inno_updater.exe"}
                    matches = [m for m in matches if os.path.basename(m).lower() not in _skip]
                    if matches:
                        exe_path = matches[0]
                        break
                except Exception:
                    pass

        if not exe_path:
            print(f"{Fore.RED}[ANTIGRAVITY] Antigravity Manager.exe bulunamadi!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[ANTIGRAVITY] Lutfen Antigravity Manager'i manuel baslatip tekrar deneyin.{Style.RESET_ALL}")
            return

        # 3. Baslatma
        try:
            print(f"{Fore.CYAN}[ANTIGRAVITY] Baslatiliyor: {exe_path}{Style.RESET_ALL}")
            subprocess.Popen(
                [exe_path],
                cwd=os.path.dirname(exe_path),
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0
            )
        except Exception as e:
            print(f"{Fore.RED}[ANTIGRAVITY] Baslatma hatasi: {e}{Style.RESET_ALL}")
            return

        # 4. Hazir olana kadar bekle (max 30 saniye)
        print(f"{Fore.CYAN}[ANTIGRAVITY] Hazir bekleniyor", end="", flush=True)
        for i in range(30):
            time.sleep(1)
            print(".", end="", flush=True)
            try:
                self._get(base_url, timeout=1)
                print(f" Hazir! OK{Style.RESET_ALL}")
                return
            except Exception:
                pass
        print(f"\n{Fore.YELLOW}[ANTIGRAVITY] 30 sn icinde hazir olmadi, devam ediliyor...{Style.RESET_ALL}")

    def uncensor_text(self, text):
        """Yildizli kufurleri acar"""

        replacements = {
            r'f\*\*k': 'fuck', r'F\*\*k': 'Fuck',
            r'f\*\*\*': 'fuck', r'F\*\*\*': 'Fuck',
            r's\*\*t': 'shit', r'S\*\*t': 'Shit',
            r'sh\*t': 'shit', r'Sh\*t': 'Shit',
            r'b\*\*ch': 'bitch', r'B\*\*ch': 'Bitch',
            r'd\*\*n': 'damn', r'D\*\*n': 'Damn',
            r'h\*\*l': 'hell', r'H\*\*l': 'Hell',
            r'a\*\*': 'ass', r'A\*\*': 'Ass'
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def shorten_line(self, text: str, max_chars: int, retries: int = 2):
        """
        CPS kisaltma icin dedicated API metodu.
        translate_single_line/batch'ten farkli olarak:
        - Subtitle #N/Original>/Translation> formati KULLANILMAZ
        - Direkt 'Shorten to max X chars' meta-instruction gonderilir
        - Basarili olursa kisaltilmis metin, basarisiz olursa None doner
        """
        if not text or not text.strip():
            return None
        _prompt = (
            f"You are a subtitle editor. Shorten the following Turkish subtitle text "
            f"to MAXIMUM {max_chars} characters while keeping the core meaning. "
            f"Return ONLY the shortened Turkish text, nothing else.\n\n"
            f"TEXT: {text.strip()}"
        )
        is_antigravity = getattr(self, '_is_antigravity', False)
        is_ollama = self.model.startswith('gemma2:')
        is_google_api = (not is_antigravity and not is_ollama
                         and 'googleapis' in getattr(self, 'api_url', ''))
        # is_google_api ikinci kontrol: model prefix
        if not is_antigravity and not is_ollama:
            _mk = self.model.lower()
            if 'gemini' in _mk or 'google' in _mk:
                is_google_api = True

        for attempt in range(retries):
            try:
                if is_antigravity:
                    _key = self.antigravity_key or "LOCAL"
                    _hdrs = {"Authorization": f"Bearer {_key}", "Content-Type": "application/json"}
                    _data = {"model": self.model,
                             "messages": [{"role": "user", "content": _prompt}],
                             "temperature": 0.2, "max_tokens": 256}
                    _r = self._post(self.api_url, headers=_hdrs, json=_data, timeout=30)
                elif is_ollama:
                    _hdrs = {"Content-Type": "application/json"}
                    _data = {"model": self.model, "prompt": _prompt, "stream": False}
                    _r = self._post(self.ollama_url, headers=_hdrs, json=_data, timeout=20)
                elif is_google_api:
                    _key = self.key_manager.get_valid_key() if self.key_manager else None
                    if not _key:
                        return None
                    _mname = self.model.split('/')[-1] if '/' in self.model else self.model
                    _url = f"https://generativelanguage.googleapis.com/v1beta/models/{_mname}:generateContent?key={_key}"
                    _hdrs = {"Content-Type": "application/json"}
                    _data = {"contents": [{"parts": [{"text": _prompt}]}],
                             "generationConfig": {"temperature": 0.2, "maxOutputTokens": 256}}
                    _r = self._post(_url, headers=_hdrs, json=_data, timeout=20)
                else:  # OpenRouter
                    _key = self.key_manager.get_valid_key() if self.key_manager else None
                    if not _key:
                        return None
                    _hdrs = {"Authorization": f"Bearer {_key}",
                             "Content-Type": "application/json",
                             "HTTP-Referer": "https://antigravity.dev"}
                    _data = {"model": self.model,
                             "messages": [{"role": "user", "content": _prompt}],
                             "temperature": 0.2, "max_tokens": 256}
                    _r = self._post(self.api_url, headers=_hdrs, json=_data, timeout=20)

                if _r.status_code == 402:
                    # Rate limit / quota — key rotate et ve bir sonraki attempt'e devam et
                    if self.key_manager:
                        _rotated = self.key_manager.rotate_key()
                        if _rotated:
                            print(f"{Fore.YELLOW}   [CPS shorten] 402 → key rotasyonu{Style.RESET_ALL}")
                    continue  # Bir sonraki attempt
                if _r.status_code == 200:
                    _rj = _r.json()
                    if is_ollama:
                        _out = _rj.get("response", "").strip()
                    elif is_google_api:
                        _out = _rj.get("candidates", [{}])[0].get(
                            "content", {}).get("parts", [{}])[0].get("text", "").strip()
                    else:
                        _out = _rj.get("choices", [{}])[0].get(
                            "message", {}).get("content", "").strip()
                    if _out and len(_out) <= max_chars * 1.5:  # <%50 asimi tolere et
                        return _out

            except Exception:
                pass
        return None

    def translate_single_line(self, text, retries=5):
        if not text.strip(): return text

        # ── [SL-SON-SAVUNMA] Junk / Per-char typeset guard ───────────────────
        # Satir-satir (single-line) moda dustugunde bile junk satirlar API'ya
        # gitmemeli. translate_batch() last-defense ile ayni mantik.
        _sl_junk = False
        if _ACC_OK and _acc_classify_line is not None:
            try:
                _sl_clf = _acc_classify_line(text)
                if _sl_clf.action == 'skip':
                    _sl_junk = True
                    print(f"{Fore.YELLOW}   [SL-SKIP] Junk ({_sl_clf.reason}): {text[:55]}...{Style.RESET_ALL}")
            except Exception:
                pass
        if not _sl_junk:
            _pc_sl = [f.strip() for f in re.split(r'\{[^}]*\}', text) if f.strip()]
            if len(_pc_sl) >= 4 and all(len(f) <= 2 for f in _pc_sl):
                _sl_junk = True
                print(f"{Fore.YELLOW}   [SL-SKIP] Per-char typeset (n={len(_pc_sl)}): {text[:55]}...{Style.RESET_ALL}")
        if _sl_junk:
            return text  # Orijinali koru — API'ya gonderme, retry TETIKLEME
        # ─────────────────────────────────────────────────────────────────────

        # [COPYRIGHT-SKIP] Telif hakki bildirimleri cevrilmez — tum retry/rotation dongusunu atla
        import re as _re_cpr
        _cpr_clean = _re_cpr.sub(r'{[^}]*}', '', text).strip()  # ASS tagleri temizle
        _cpr_clean = _re_cpr.sub(r'__T\d+__', '', _cpr_clean).strip()  # placeholder temizle
        if _re_cpr.search(
            r'(?i)(?:\xa9|\u00a9|copyright|\(c\)\s*\d|production\s+committee|'
            r'all\s+rights\s+reserved|shueisha|kodansha|aniplex|crunchyroll)',
            _cpr_clean
        ):
            return text  # Copyright metni — olduğu gibi bırak, çevirme
        
        # PRE-PROCESS: Uncensor
        text = self.uncensor_text(text)
        
        for attempt in range(retries):
            try:
                # Tek satırlık prompt
                
                # Check if using Ollama (local model)
                is_ollama = self.model.startswith('gemma2:')
                # KRITIK: _is_antigravity flag'i __init__'de set ediliyor, buna guven
                is_antigravity = getattr(self, '_is_antigravity', False)

                if is_antigravity:
                    # Antigravity Manager: OpenAI uyumlu lokal proxy
                    current_key = self.antigravity_key or "LOCAL"
                    is_google_api = False
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"}
                elif is_ollama:
                    # Use Ollama local API (no API key needed)
                    current_key = None
                    is_google_api = False
                    headers = {"Content-Type": "application/json"}
                else:
                    # Her denemede 402 ve cooldown listesini atlayan ilk uygun keyi seç
                    current_key = self.key_manager.get_next_available_key(self._model_402_keys)
                    if not current_key:
                        return None  # Hiç key kalmadı

                    # Detect API type: Google AI Studio vs OpenRouter
                    is_google_api = current_key.startswith("AIzaSy")
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json", "HTTP-Referer": "https://antigravity.dev", "X-Title": "Antigravity"}
                
                base_prompt = (self.config['system_prompt']
                               .replace('{0}', self.config['source_lang'])
                               .replace('{1}', self.config['target_lang']))

                # Medya baglamı enjeksiyonu (anime/dizi metadata)
                if self._media_context:
                    base_prompt += f"\n\n{self._media_context}"
                # Dosyaya özel ek bağlam enjeksiyonu (deyimler vb.)
                # HStream modunda deyim/idiom bağlamı gönderilmez (prompt şişmesi önleme)
                if self._additional_context and not self._hstream_mode:
                    base_prompt += f"\n\n{self._additional_context}"
                
                # Dynamic rules
                strict_rules = ""
                if self.nsfw_enabled:
                    # Build rules based on config
                    rules_list = [
                        "\nSTRICT RULES:\n",
                        "1. ABSOLUTELY NO CENSORSHIP. Translate all adult contents, profanities, and intimate dialogues accurately without omission or softening.\n"
                    ]
                    
                    # Glossary (if enabled)
                    # HStream modunda glossary gönderilmez
                    if self.config.get('use_glossary', True) and not self._hstream_mode:
                        important_terms = ["facial", "creampie", "blowjob", "handjob", "paizuri", "boobjob"]
                        glossary_str_mini = ", ".join([f"'{k}'->'{self.GENRE_MAPPING.get(k)}'" for k in important_terms if k in self.GENRE_MAPPING])
                        rules_list.append(f"2. TERMINOLOGY: {glossary_str_mini}.\n")
                    
                    rules_list.append("3. NEVER use asterisks or dashes to censor words (e.g. do not write 'f**k' or 's**t'). Write the full Turkish translation explicitly.\n")
                    
                    # Natural Dialogue (if enabled)
                    if self.config.get('natural_dialogue', True):
                        rules_list.extend([
                            "4. USE NATURAL TURKISH DIALOGUE (NOT WORD-BY-WORD TRANSLATION).\n",
                            "   - Match the scene's emotional tone, keeping adult/romantic/casual dialogues flowing naturally.\n",
                            "5. Maintain the original tone and intensity of the scene, whether it is dramatic, romantic, or explicit.\n"
                        ])
                    
                    strict_rules = "".join(rules_list)
                
                if self.config.get("english_only"):
                    strict_rules += "4. TRANSLATE ONLY ENGLISH. If a word or phrase is NOT English (e.g. Japanese via romaji), KEEP IT EXACTLY AS IS.\n"
                
                
                prompt = f"{base_prompt}{strict_rules}\nTEXT: {text}"
                
                if is_antigravity:
                    # Antigravity Manager lokal proxy (OpenAI uyumlu)
                    data = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 4096}
                    response = self._post(self.api_url, headers=headers, json=data, timeout=60)
                elif is_ollama:
                    # Ollama local API format
                    data = {
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 4096
                        }
                    }
                    response = self._post(self.ollama_url, headers=headers, json=data, timeout=30)
                elif is_google_api:
                    # Google AI Studio API format
                    model_name = self.model.split('/')[-1] if '/' in self.model else self.model
                    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_key}"
                    data = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
                    }
                    headers = {"Content-Type": "application/json"}
                    response = self._post(api_url, headers=headers, json=data, timeout=15)
                else:
                    # OpenRouter API format
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json", "HTTP-Referer": "https://antigravity.dev"}
                    data = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 4096}
                    response = self._post(self.api_url, headers=headers, json=data, timeout=15)
                
                # CRITICAL FIX: Only mark as exhausted on PERSISTENT AUTH errors
                # Skip for Ollama (no key manager)
                if response.status_code == 401:  # Invalid key - truly dead
                    if self.simple_mode:
                        print(f"{Fore.RED}   ❌ [SIMPLE MODE] Key geçersiz! Lütfen yeni bir key ekleyin.{Style.RESET_ALL}")
                        raise Exception("Invalid API key - please add a valid key")
                    else:
                        print(f"{Fore.RED}   [!] Anahtar geçersiz (401), loglanıyor...{Style.RESET_ALL}")
                        if self.key_manager:
                            self.key_manager.mark_as_exhausted(current_key)
                        continue
                elif response.status_code == 402:  # No credit / Model daily limit
                    # Bu key bu model icin kota doldu — session'a ekle, tekrar deneme
                    self._model_402_keys.add(current_key)
                    _402_active = len(self._model_402_keys)
                    _sl_total_keys = len(self.key_manager.keys) if self.key_manager and hasattr(self.key_manager, 'keys') else 1
                    print(f"{Fore.YELLOW}   [~] Model limiti (402), bu key session'a eklendi ve atlanacak [{_402_active}/{_sl_total_keys}]...{Style.RESET_ALL}")
                    if self.key_manager:
                        # 402 olmayan ilk keyi bul
                        next_key = self.key_manager.rotate_key()
                        # 402 listesindeyse atlamaya devam et
                        _skip_tries = 0
                        while next_key and next_key in self._model_402_keys and _skip_tries < _total_keys:
                            next_key = self.key_manager.rotate_key()
                            _skip_tries += 1
                        if self.simple_mode:
                            self.selected_key = next_key
                    if _402_active >= _sl_total_keys:
                        if self._fallback_model and self.model != self._fallback_model:
                            print(f"{Fore.MAGENTA}   [FALLBACK] Tüm key'ler ({_sl_total_keys}) bu model için 402 aldı.{Style.RESET_ALL}")
                            print(f"{Fore.MAGENTA}   [FALLBACK] {self.model} → {self._fallback_model} modeline geçiliyor...{Style.RESET_ALL}")
                            self.model = self._fallback_model
                            self._model_402_keys.clear()  # Sıfırla, yeni model için taze başla
                            if self.key_manager:
                                self.selected_key = self.key_manager.rotate_key()
                        else:
                            print(f"{Fore.RED}   [!!] Tüm key'ler bu model için 402 (kota doldu) → batch durduruluyor.{Style.RESET_ALL}")
                            return []
                    # 402 → attempt tüketme (key sorunu, logic sorunu değil)
                    time.sleep(2)
                    continue
                elif response.status_code in (500, 502, 503, 524, 520, 521):
                    # Sunucu hatası — key rotasyonu yapma, bekle ve tekrar dene
                    _sl_srv_errs = getattr(self, '_sl_server_err_count', 0) + 1
                    self._sl_server_err_count = _sl_srv_errs
                    _bk = min(10 * (2 ** (_sl_srv_errs - 1)), 60)
                    print(f"{Fore.YELLOW}   [{response.status_code}] Sunucu hatası (single-line) → {_bk}sn bekleniyor...{Style.RESET_ALL}")
                    time.sleep(_bk)
                    continue  # attempt tüketme
                elif response.status_code == 429:  # Rate limit — key cooldown'a al, sonrakine gec
                    if self.key_manager:
                        self.key_manager.mark_rate_limited(current_key)
                        next_key = self.key_manager.get_next_available_key(self._model_402_keys)
                        if next_key:
                            if self.simple_mode:
                                self.selected_key = next_key
                            print(f"{Fore.MAGENTA}   [429] Rate limit → cooldown'a alindi, {next_key[:20]}... ile devam{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.MAGENTA}   [429] Tum keyler cooldown — bekleniyor...{Style.RESET_ALL}")
                    else:
                        time.sleep(30)
                    time.sleep(3)  # Retry arasi kisa bekleme — burst'u onler
                    continue
                
                response.raise_for_status()
                res_json = response.json()
                # Basarili yanit — model-level streak sifirla
                if self.key_manager:
                    self.key_manager.reset_global_streak()

                # Extract translated text from response (different format for each API)
                try:
                    if is_ollama:
                        # Ollama response format
                        res_text = res_json['response'].strip()
                    elif is_google_api:
                        # Google AI Studio response format
                        res_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        # OpenAI uyumlu format (OpenRouter veya Antigravity)
                        res_text = res_json['choices'][0]['message']['content'].strip()
                except (KeyError, IndexError) as e:
                    print(f"{Fore.RED}   [!] API yanıtı beklenenden farklı: {e}. Tam yanıt: {res_json}{Style.RESET_ALL}")
                    continue # Try again if response format is unexpected

                if res_text: return res_text
                
            except Exception as e:
                time.sleep(1)
        
        # [KEY ROTATION FALLBACK] Tüm retry'lar tükendi → farklı key ile 2 deneme daha
        if self.key_manager and not getattr(self, '_is_antigravity', False):
            _rotated_key = self.key_manager.rotate_key()
            if _rotated_key and _rotated_key != getattr(self, 'selected_key', None):
                print(f"{Fore.YELLOW}   [KEY ROTATION] Retry tükendi, yeni key ile 2 deneme daha...{Style.RESET_ALL}")
                _old_key = getattr(self, 'selected_key', None)
                if self.simple_mode:
                    self.selected_key = _rotated_key
                _rot_prompt = (
                    f"Translate the following subtitle line into natural Turkish only. "
                    f"Return ONLY the Turkish translation, nothing else.\nTEXT: {text}"
                )
                for _extra in range(2):
                    try:
                        _headers = {"Authorization": f"Bearer {_rotated_key}", "Content-Type": "application/json"}
                        _payload = {
                            "model": self.model,
                            "messages": [{"role": "user", "content": _rot_prompt}],
                            "max_tokens": 500, "temperature": 0.3
                        }
                        _r = self._post(self.api_url, headers=_headers, json=_payload, timeout=30)
                        if _r.status_code == 200:
                            _rt = _r.json()['choices'][0]['message']['content'].strip()
                            if _rt and _rt.lower() != text.lower():
                                print(f"{Fore.GREEN}   [KEY ROTATION] Basarili! ({_extra+1}. deneme){Style.RESET_ALL}")
                                return _rt
                        time.sleep(2)
                    except Exception:
                        pass
                if self.simple_mode and _old_key:
                    self.selected_key = _old_key

        return text


    def translate_batch(self, lines_batch):
        # ── Batch Arası Gecikme (Rate-limit önleme) ──────────────────────────
        # Sadece 1'den fazla satırlı gerçek batch'lerde bekle.
        _is_real_batch = len(lines_batch) > 1
        _batch_delay = 0
        if _is_real_batch:
            try:
                import json as _j, os as _os
                _ppath = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'user_preferences.json')
                if _os.path.exists(_ppath):
                    _batch_delay = float(_j.load(open(_ppath, encoding='utf-8')).get('batch_delay_seconds', 0))
            except Exception:
                pass
            # [SADELEŞTIRILDI] delay_between_calls artık ayrı slider yok;
            # sadece batch_delay_seconds kullanılıyor (UI'da tek kontrol noktası)
            if _batch_delay > 0:
                print(f"   [Batch] {len(lines_batch)} satır göndermeden önce {_batch_delay:.1f}sn bekleniyor...")
                time.sleep(_batch_delay)
        # ─────────────────────────────────────────────────────────────────────


        # ── [SON SAVUNMA] ASS Junk Filtresi — batch API'ya gitmeden son kontrol ──
        # subtitle_processor early-exit'i baypas eden satirlar (retry path vb.)
        # burada yakalanir. \clip(m)/\iclip(m) + junk metin → orijinal dondur.
        _filtered_batch = []
        _junk_indices   = []
        for _bi, _bline in enumerate(lines_batch):
            _raw = _bline if isinstance(_bline, str) else str(_bline)
            _is_junk = False
            _junk_reason = ''

            # ── Birincil: ass_content_classifier tam motoru (A1-A14 tum kurallar) ──
            # Drawing, karaoke, CJK, symbol, invisible alpha, per-char typeset,
            # clip junk, stil sonek, gradient cluster... hepsini kapsar.
            if _ACC_OK and _acc_classify_line is not None:
                try:
                    _clf = _acc_classify_line(_raw)
                    if _clf.action == 'skip':
                        _is_junk = True
                        _junk_reason = f'acc:{_clf.reason}'
                except Exception:
                    pass  # Siniflandirici hatasi → fallback'e bira

            # ── Fallback 1: ass_tag_reference (drawing + clip) ──
            if not _is_junk:
                _is_junk = _atr_drawing(_raw)
                if _is_junk:
                    _junk_reason = 'atr:drawing'
            if not _is_junk:
                _clip_junk, _clip_reason = _atr_clip_junk(_raw)
                if _clip_junk:
                    _is_junk = True
                    _junk_reason = f'atr:clip({_clip_reason})'

            # ── Fallback 2: per-karakter typeset regex (acc modulu yoksa) ──
            if not _is_junk:
                _frz_n = len(re.findall(r'\\frz\s*-?[\d.]+', _raw, re.IGNORECASE))
                if _frz_n >= 3:
                    _tf = [f.strip() for f in re.split(r'\{[^}]*\}', _raw) if f.strip()]
                    if _tf and all(len(f) <= 2 for f in _tf):
                        _is_junk = True
                        _junk_reason = f'regex:per_char_typeset(frz={_frz_n})'

            if _is_junk:
                _junk_indices.append(_bi)
                print(f"{Fore.YELLOW}   [SON-SAVUNMA] Junk skip ({_junk_reason}): {_raw[:60]}...{Style.RESET_ALL}")
            else:
                _filtered_batch.append(_bline)
        # Eger tum batch junk ise orijinali dondur
        if not _filtered_batch:
            return list(lines_batch)
        # Eger bir kismi junk ise sadece gercek satirlari cevir
        if len(_filtered_batch) < len(lines_batch):
            lines_batch = _filtered_batch
        # ────────────────────────────────────────────────────────────────────────

        # BATCH DENEMESİ
        # Retry logic — WHILE LOOP (429/402/500/network attempt tüketmez, sadece logic hataları sayılır)
        max_retries      = self.config.get("max_retries", 6)
        _consecutive_402 = 0
        _total_keys      = len(self.key_manager.keys) if self.key_manager else 1
        _server_err_count = 0
        _net_err_count    = 0
        _logic_attempts   = 0   # Sadece gerçek parse/logic/identical hataları sayar
        _infinite_guard   = 0   # Sonsuz döngü koruması
        _MAX_INFINITE     = max_retries * 5  # En fazla bu kadar toplam deneme

        while _logic_attempts < max_retries and _infinite_guard < _MAX_INFINITE:
            _infinite_guard += 1
            try:
                # Check if using Ollama (local model)
                # Ollama modelleri "name:tag" formatinda (ornek: llama3:latest, mistral:7b, gemma2:2b)
                # "gemma2:" prefix kontrolu yetmez — kapsami genislet
                is_ollama = (
                    self.model.startswith('gemma2:') or
                    self.model.startswith('llama') or
                    self.model.startswith('mistral:') or
                    self.model.startswith('phi') or
                    self.model.startswith('qwen:') or
                    self.model.startswith('deepseek:') or
                    self.model.startswith('codellama:') or
                    ('ollama' in self.model.lower()) or
                    (':' in self.model and '/' not in self.model)  # Ollama name:tag formati
                )
                # KRITIK: _is_antigravity flag'i __init__'de set ediliyor, buna guven
                is_antigravity = getattr(self, '_is_antigravity', False)

                if is_antigravity:
                    current_key = self.antigravity_key or "LOCAL"
                    is_google_api = False
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"}
                elif is_ollama:
                    # Use Ollama local API (no API key needed)
                    current_key = None
                    is_google_api = False
                    headers = {"Content-Type": "application/json"}
                else:
                    # Use cloud APIs — 402 listesindeki keyleri atla, cooldown'dakileri bekle
                    current_key = self.key_manager.get_next_available_key(self._model_402_keys)
                    if not current_key:
                        # Tüm keyler 402 veya cooldown'da
                        print(f"{Fore.RED}   [!!] Kullanılabilir key kalmadı (hepsi 402/cooldown)!{Style.RESET_ALL}")
                        break

                    # Detect API type: Google AI Studio vs OpenRouter
                    is_google_api = current_key.startswith("AIzaSy")
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json", "HTTP-Referer": "https://antigravity.dev", "X-Title": "Antigravity"}

                base_instruction = (self.config["system_prompt"]
                                    .replace("{0}", self.config["source_lang"])
                                    .replace("{1}", self.config["target_lang"]))

                # Medya baglamı enjeksiyonu (anime/dizi metadata)
                # HStream modunda _media_context yine gönderilir (bölüm bilgisi önemli)
                # Ancak _additional_context (deyim taraması) gönderilmez
                if self._media_context:
                    base_instruction += f"\n\n{self._media_context}"
                
                # Dosyaya özel ek bağlam enjeksiyonu (deyimler, onaylanmış terimler vb.)
                if self._additional_context and not self._hstream_mode:
                    base_instruction += f"\n\n{self._additional_context}"
                
                # [GLOSSARY INJECTION]
                # Kullanıcının özel hentai terimlerini AI'ya öğretiyoruz.
                glossary_str_mini = ""
                additional_rules = ""
                
                if self.nsfw_enabled:
                    # NSFW mod: tam sansürsüz
                    rules_list = [
                        "- ABSOLUTELY NO CENSORSHIP. Translate all adult contents, profanities, and intimate dialogues accurately without omission or softening.\n",
                        "- NEVER use asterisks or dashes to censor words (e.g. do not write 'f**k' or 's**t'). Write the full Turkish translation explicitly.\n",
                        "- Maintain the original tone and intensity of the scene, whether it is dramatic, romantic, or explicit.\n"
                    ]
                    
                    if self.config.get('natural_dialogue', True):
                        rules_list.extend([
                            "- USE NATURAL TURKISH DIALOGUE (NOT WORD-BY-WORD TRANSLATION).\n",
                            "  * Match the scene's emotional tone, keeping adult/romantic/casual dialogues flowing naturally.\n",
                            "- Dialogue style should match the original scene's intensity: passionate, direct, and grammatically correct Turkish.\n"
                        ])
                    
                    # HStream modunda glossary gönderilmez (prompt şişmesi önleme)
                    if self.config.get('use_glossary', True) and not self._hstream_mode:
                        important_terms = [
                            "creampie", "nakadashi", "facial", "bukkake", "blowjob", "handjob", "paizuri", 
                            "cunnilingus", "fingering", "ahegao", "netorare", "ntr", "futanari", "dickgirl",
                            "milf", "loli", "shota", "jk", "gyaru", "incest", "rape", "mind break",
                            "pregnant", "impregnation", "breeding", "lactation", "tentacle", "x-ray",
                            "master", "slave", "bitch", "slut", "whore", "fuck", "cum", "pussy", "cock", "dick"
                        ]
                        glossary_str_mini = "\n".join([f'- "{k}" -> "{self.GENRE_MAPPING[k]}"' for k in important_terms if k in self.GENRE_MAPPING])
                        rules_list.append("TERMINOLOGY (STRICTLY USE THESE):\n")
                        rules_list.append(f"{glossary_str_mini}\n")
                    
                    additional_rules = "".join(rules_list)
                else:
                    # Normal mod: dogal tercume + sansursuz kural
                    additional_rules = "- Translate naturally. Keep the meaning.\n"
                    additional_rules += "- TRANSLATE EVERYTHING. Do not leave lines in English.\n"
                    additional_rules += "- Translate all-caps text (e.g. SIGNS, LOCATIONS, SCHOOL NAMES).\n"
                    additional_rules += "- Example: 'HIGH SCHOOL' -> 'LİSESİ', 'LIBRARY' -> 'KÜTÜPHANESİ'.\n"
                    additional_rules += "- Do not treat long sentences as proper nouns just because they are capitalized.\n"
                    # [FIX] +18 icerik icin her modda sansursuz kural zorunlu:
                    additional_rules += "- NEVER use asterisks or partial words (f***, s***). Write the FULL word always.\n"
                    additional_rules += "- If a word is profanity or adult content, translate it EXPLICITLY. Do NOT censor.\n"

                # [SIGNS MOD] Her modda geçerli — [SIGN] işaretli satırlar ekran yazısıdır
                additional_rules += (
                    "- Lines starting with [SIGN]: these are ON-SCREEN TEXT (location names, title cards, signs, labels).\n"
                    "  Translate VERY BRIEFLY (max 6 words), LITERALLY. No paraphrasing.\n"
                    "  Keep proper nouns unchanged. ALL-CAPS source → use ALL-CAPS or Title Case in Turkish.\n"
                    "  Do NOT add punctuation if the source has none.\n"
                    "  REMOVE the [SIGN] prefix from your output — only output the translation.\n"
                )

                if self.config.get("english_only"):
                    additional_rules += "- TRANSLATE ONLY ENGLISH WORDS. Keep foreign words (Japanese, Korean, etc.) UNCLAIMED/UNTRANSLATED.\n"


                # Her modda geçerli: Türkçe çıktıda asla Japonca zamir kullanma
                additional_rules += (
                    "- CRITICAL: NEVER write Japanese pronouns in your Turkish output. "
                    "'boku', 'ore', 'watashi', 'atashi', 'ware', 'washi' mean 'I/me' in Japanese. "
                    "In Turkish output, ALWAYS use 'Ben' or omit the subject entirely. "
                    "Example: Source 'I'm in trouble' → Turkish 'Başım belada', NOT 'Boku belada'.\n"
                )


                # ── NUMBERED LINES: #N\nOriginal> ...\nTranslation> format (kayma-proof) ──
                # llm-subtrans'dan esinlenen format: Her satır #N + Original> + Translation>
                # şeklinde yapılandırılıyor. AI ne kadar açıklama eklerse eklesin
                # #N keyword'ü ile kesin eşleşme yapılıyor.
                if self._jp_primary:
                    # ── JP BİRİNCİL MOD ──
                    numbered_lines = []
                    en_ref = self._reference_lines
                    for i, l in enumerate(lines_batch):
                        jp_text = self.uncensor_text(l)
                        en_text = (en_ref[i] if en_ref and i < len(en_ref) else "") or ""
                        if en_text:
                            numbered_lines.append(
                                f"#{i+1}\nOriginal (JP)> {jp_text}\n   Reference (EN)> {en_text}\nTranslation>"
                            )
                        else:
                            numbered_lines.append(f"#{i+1}\nOriginal (JP)> {jp_text}\nTranslation>")
                    additional_rules += (
                        "\nJAPANESE PRIMARY MODE:\n"
                        "- Input lines are Japanese (Kanji/Kana or Romaji). Translate DIRECTLY to natural Turkish.\n"
                        "- [JP] is the AUTHORITATIVE source. [EN-FANSUB] is a rough fan translation — use it\n"
                        "  only for character name hints or when JP meaning is ambiguous.\n"
                        "- Japanese sentence structure is SOV (Subject-Object-Verb). Restructure for natural Turkish.\n"
                        "- Japanese often omits the subject/pronoun — infer from context and add if needed in Turkish.\n"
                        "- Honorifics (-san, -kun, -chan, -senpai, -sensei) → keep attached to the name as-is.\n"
                        "- Character names → keep as-is. Translate everything else that has a Turkish equivalent.\n"
                        "- Casual/informal speech in Japanese → use casual Turkish (sen, gel, git, tamam vb.)\n"
                        "- Polite speech (desu/masu form) → use formal Turkish (lütfen, efendim, buyrun).\n"
                        "- Exclamations: Yosh! → Hadi!, Nani? → Ne?, Uso! → Saçma!/Yalan!, "
                        "  Sugoi → Vay be!, Kawaii → Sevimli!, Yamete → Dur!/Bırak!\n"
                    )

                elif self._reference_lines:
                    # ── DUAL-SOURCE MOD ──
                    ref = self._reference_lines
                    rl  = self._reference_lang
                    numbered_lines = []
                    for i, l in enumerate(lines_batch):
                        en_text  = self.uncensor_text(l)
                        ref_text = ref[i] if i < len(ref) else ""
                        if ref_text:
                            numbered_lines.append(
                                f"#{i+1}\nOriginal (EN-FANSUB)> {en_text}\n   Reference ({rl})> {ref_text}\nTranslation>"
                            )
                        else:
                            numbered_lines.append(f"#{i+1}\nOriginal> {en_text}\nTranslation>")
                    additional_rules += (
                        f"\nDUAL-SOURCE SYNTHESIS MODE (Low-quality fansub + Original {rl}):\n"
                        f"- [EN-FANSUB] = A fan translation — may be awkward or slightly wrong, but gives dialogue flow.\n"
                        f"- [JP-ORIGINAL] = The ORIGINAL Japanese — this is the GROUND TRUTH for meaning and nuance.\n"
                        f"\nYOUR TASK — Synthesize the BEST Turkish translation by:\n"
                        f"  1. Using [JP-ORIGINAL] as the PRIMARY source for MEANING, EMOTION, and NUANCE.\n"
                        f"  2. Using [EN-FANSUB] as a SECONDARY aid for dialogue naturalness and character names.\n"
                        f"  3. If both agree → write a natural Turkish that captures both accurately.\n"
                        f"  4. If they disagree → TRUST [JP-ORIGINAL] for the core meaning, but check if\n"
                        f"     [EN-FANSUB] captures a nuance the JP wording doesn't make obvious in Turkish.\n"
                        f"  5. Never copy [EN-FANSUB] directly — always re-express in natural, fluent Turkish.\n"
                        f"  6. The final output should read as if translated DIRECTLY from Japanese by a native\n"
                        f"     Turkish speaker who also consulted the English for dialogue style.\n"
                        f"  7. If [JP-ORIGINAL] is missing for a line, use [EN-FANSUB] and translate as normal.\n"
                    )
                else:
                    # ── STANDART MOD: #N + Original> + Translation> ──
                    numbered_lines = [
                        f"#{i+1}\nOriginal> {self.uncensor_text(l)}\nTranslation>"
                        for i, l in enumerate(lines_batch)
                    ]
                
                # ── SLIDING WINDOW: önceki batch'in son satırları → bağlam olarak ekle ──
                context_block = ""
                if self._context_window:
                    prev_lines = []
                    for src, tr in self._context_window:
                        src_short = src[:80].replace('\n', ' ')
                        tr_short  = tr[:80].replace('\n', ' ')
                        prev_lines.append(f"  [{src_short}] → [{tr_short}]")
                    context_block = (
                        "\nPREVIOUS DIALOGUE CONTEXT (for continuity only — do NOT re-translate):\n"
                        + "\n".join(prev_lines)
                        + "\n(Continue the translation naturally from where the above dialogue left off.)\n"
                    )

                # ── SYSTEM / USER PROMPT AYRIMI ──────────────────────────────────────────
                # Sabit kurallar → system mesajı (model bu kuralları önce bağlam olarak okur)
                # Dinamik INPUT (satırlar) → user mesajı
                # Google API: systemInstruction alanı | OpenRouter/AG: messages[{system},{user}]
                system_content = f"""{base_instruction}
STRICT INSTRUCTIONS:
{additional_rules}
- For EACH entry (#1, #2, #3 ...) fill ONLY the "Translation>" field with the Turkish translation.
- Do NOT modify the #N numbers, the "Original>" lines, or the structure.
- Do NOT merge, split, skip, or add entries.
- Do NOT add conversational text — ONLY the filled entries.
- NEVER leave Translation> identical to the Original> if it is a real English sentence.
- TRANSLATE ALL English sentences including short ones: "Are you okay?" → "İyi misin?"
- If it's a character name (e.g. "Kirito") or game variable ("§§0§§"), keep it as-is.

CRITICAL - PLACEHOLDERS (DO NOT MODIFY):
- __NL__ = line break marker. Keep EXACTLY as "__NL__". NEVER replace with <br>, <br/>, <br />, \n or anything else!
- __SL__ = soft line break. Keep as "__SL__".
- __HS__ = hard space. Keep as "__HS__".
- __T0__, __T1__, __T2__ etc. = inline formatting codes (italic, bold, color, etc.).
  CRITICAL RULES for __Tn__ placeholders:
  * Keep them IN EXACTLY THE SAME RELATIVE POSITION in the translated text.
  * If __T0__ comes BEFORE a word in the source, it must come BEFORE the equivalent translated word.
  * If __T0__ and __T1__ WRAP a word/phrase (open+close pair), wrap the TRANSLATED equivalent.
  * NEVER move placeholders to the beginning or end of the line unless they were there in the source.
  * NEVER delete or omit any __Tn__ placeholder — even if the word stays in English.
  * Example: "He plays __T0__Tokyo Blade__T1__ songs." → "O, __T0__Tokyo Blade__T1__ şarkıları çalıyor."
  * Example: "She is __T0__very__T1__ beautiful." → "O, __T0__çok__T1__ güzel."
  * BAD (wrong): "__T0____T1__O, Tokyo Blade şarkıları çalıyor."  ← placeholders dumped at beginning!
- ⟦SEP⟧ = segment separator. A line may have multiple text segments separated by ⟦SEP⟧.
  * Translate each segment independently but keep the ⟦SEP⟧ separator EXACTLY as-is.
  * NEVER remove, duplicate, or rewrite ⟦SEP⟧. It marks formatting boundaries.
  * Example: "Dig Deep! ⟦SEP⟧ prep meeting at 11:30 AM." → "Dig Deep! ⟦SEP⟧ 11:30'da hazırlık toplantısı."
- Example: "Text __NL__ More" → "Metin __NL__ Devam"  (NOT "Metin <br /> Devam")

FEW-SHOT EXAMPLES (exact format you must produce):
"""
                # prompt_template.json'dan few_shot_examples yukle (varsa)
                _few_shot_cfg = self.config.get("few_shot_examples", [])
                if _few_shot_cfg:
                    for _i, _ex in enumerate(_few_shot_cfg, 1):
                        _orig = _ex.get("original", "")
                        _tr   = _ex.get("translation", "")
                        if _orig and _tr:
                            system_content += f"#{_i}\nOriginal> {_orig}\nTranslation> {_tr}\n\n"
                else:
                    # Fallback: hardcoded 5 ornek (prompt_template.json yoksa)
                    system_content += (
                        "#1\nOriginal> Are you okay? You're hurt!\nTranslation> \u0130yi misin? Yaral\u0131s\u0131n!\n\n"
                        "#2\nOriginal> I... I've always liked you, Kirito-kun.\nTranslation> Ben... Ben hep senden ho\u015flanm\u0131\u015ft\u0131m, Kirito-kun.\n\n"
                        "#3\nOriginal> [SIGN] AINCRAD \u2014 FLOOR 100\nTranslation> AINCRAD \u2014 100. KAT\n\n"
                        "#4\nOriginal> Don't worry, Asuna-senpai. I'll handle it.\nTranslation> Merak etme, Asuna-senpai. Ben hallederim.\n\n"
                        "#5\nOriginal> The battle is lost... __NL__ We never had a chance.\nTranslation> Sava\u015f\u0131 kaybettik... __NL__ Hi\u00e7 \u015fans\u0131m\u0131z yoktu.\n\n"
                    )


                user_content = f"""You will receive EXACTLY {len(lines_batch)} numbered dialogue entries.
Return EXACTLY {len(lines_batch)} entries. OUTPUT: Fill each Translation> field.{context_block}

INPUT ({len(lines_batch)} entries):
""" + "\n\n".join(numbered_lines) + f"""

OUTPUT: Keep the #N + Original> + Translation> structure intact. Fill all {len(lines_batch)} Translation> fields.
"""
                # ─────────────────────────────────────────────────────────────────────────
                # ── Prompt boyutu tahmini (diagnostic) ─────────────────────────────────
                # PATF zaten gereksiz terimleri önceden elediği için acil trim gerekmiyor.
                _sys_tok   = len(system_content) // 4   # 1 token ≈ 4 char (kaba tahmin)
                _usr_tok   = len(user_content)  // 4
                _total_tok = _sys_tok + _usr_tok
                print(f"{Fore.LIGHTBLACK_EX}   [Prompt] Sistem: ~{_sys_tok}t / Kullanıcı: ~{_usr_tok}t / Toplam: ~{_total_tok}t{Style.RESET_ALL}")
                # ───────────────────────────────────────────────────────────────────────


                if is_antigravity:
                    # Antigravity Manager lokal proxy (OpenAI uyumlu) — system+user ayrımı
                    print(f"{Fore.MAGENTA}[ANTIGRAVITY] Batch ({len(lines_batch)} satir) gönderiliyor: {self.model}{Style.RESET_ALL}")
                    data = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_content},
                            {"role": "user",   "content": user_content},
                        ],
                        "temperature": 0.3, "max_tokens": 8192  # 32768→8192: çıktı için fazlaıyla yeterli
                    }
                    response = self._post(self.api_url, headers=headers, json=data, timeout=180)
                elif is_ollama:
                    # Ollama local API — tekil prompt (system+user birleşik)
                    data = {"model": self.model, "prompt": system_content + "\n\n" + user_content, "stream": False}
                    response = self._post(self.ollama_url, headers=headers, json=data, timeout=45)
                else:
                    # Cloud API Request (Google or OpenRouter)
                    if len(lines_batch) < 3:
                        _dbg_preview = str(lines_batch)
                        if len(_dbg_preview) > 300:
                            _dbg_preview = _dbg_preview[:300] + f"... [{len(_dbg_preview)} karakter, kirpildi]"
                        print(f"{Fore.LIGHTBLACK_EX}   [BATCH] {len(lines_batch)} satir | onizleme: {_dbg_preview[:120]}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.LIGHTBLACK_EX}   [BATCH] {len(lines_batch)} satir API'ya gonderiliyor...{Style.RESET_ALL}")

                    if is_google_api:
                        # Google AI Studio — systemInstruction + user contents
                        model_name = self.model.split('/')[-1] if '/' in self.model else self.model
                        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_key}"
                        data = {
                            "systemInstruction": {"parts": [{"text": system_content}]},
                            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
                            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192}
                        }
                        headers = {"Content-Type": "application/json"}
                    else:
                        # OpenRouter — system+user mesaj ayrımı
                        api_url = "https://openrouter.ai/api/v1/chat/completions"
                        # max_tokens: batch boyutuna gore dinamik hesapla
                        # Her satir icin: ortalama 60 token ceviri + yapisal overhead
                        # Kucuk batch: 10 x 70 + 400 = 1100 → min 1200
                        # Buyuk batch: 59 x 70 + 400 = 4530
                        # Min 1200, Max 8192 (model limiti)
                        _dynamic_max_tokens = min(8192, max(1200, len(lines_batch) * 70 + 400))
                        data = {
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_content},
                                {"role": "user",   "content": user_content},
                            ],
                            "temperature": 0.3, "max_tokens": _dynamic_max_tokens
                        }

                    # Execute Request — httpx persistent session (yoksa requests fallback)
                    response = self._post(api_url, headers=headers, json=data)
                    # httpx.Response ile requests.Response API uyumludur

                # Limit hatası
                # CRITICAL FIX: Only mark as exhausted on PERSISTENT AUTH errors
                if response.status_code == 401:  # Invalid key - truly dead
                    print(f"{Fore.RED}   [!] Anahtar geçersiz (401), loglanıyor...{Style.RESET_ALL}")
                    if self.key_manager:  # Only for online models
                        self.key_manager.mark_as_exhausted(current_key)
                    continue
                elif response.status_code == 402:  # Model gunluk limiti (free tier)
                    # Bu key session'a ekle → bir daha denenmez
                    self._model_402_keys.add(current_key)
                    _402_active = len(self._model_402_keys)
                    _402_total  = len(self.key_manager.keys) if self.key_manager and hasattr(self.key_manager, 'keys') else _total_keys
                    print(f"{Fore.YELLOW}   [~] Model limiti (402), key session listesine eklendi [{_402_active}/{_402_total}]{Style.RESET_ALL}")
                    # ── KALICI KAYIT: günlük reset gelene dek bu key'i atla ──
                    if self.key_manager:
                        self.key_manager.save_402_key(current_key, self.model)

                    if self.key_manager:
                        next_key = self.key_manager.rotate_key()
                        # 402 listesindeyse atla
                        _skip_tries = 0
                        while next_key and next_key in self._model_402_keys and _skip_tries < _total_keys:
                            next_key = self.key_manager.rotate_key()
                            _skip_tries += 1
                        if self.simple_mode and next_key:
                            self.selected_key = next_key
                    if _402_active >= _402_total:
                        if self._fallback_model and self.model != self._fallback_model:
                            print(f"{Fore.MAGENTA}   [FALLBACK] Tüm key'ler ({_402_total}) bu model için 402 aldı.{Style.RESET_ALL}")
                            print(f"{Fore.MAGENTA}   [FALLBACK] {self.model} → {self._fallback_model} modeline geçiliyor...{Style.RESET_ALL}")
                            self.model = self._fallback_model
                            self._model_402_keys.clear()
                            if self.key_manager:
                                self.selected_key = self.key_manager.rotate_key()
                        else:
                            print(f"{Fore.RED}   [!!] Tüm key'ler ({_402_total}) bu model için 402 aldı → satır durduruluyor.{Style.RESET_ALL}")
                            return lines_batch
                    time.sleep(2)
                    continue

                elif response.status_code == 429:  # Rate limit — cooldown'a al, sonraki key
                    if self.key_manager:
                        self.key_manager.mark_rate_limited(current_key)
                        retry_after_hdr = response.headers.get('Retry-After') or response.headers.get('retry-after')
                        if retry_after_hdr:
                            try:
                                self.key_manager._rate_limited[current_key] = time.time() - self.key_manager.COOLDOWN_SEC + int(float(retry_after_hdr))
                            except (ValueError, TypeError):
                                pass
                        next_key = self.key_manager.get_next_available_key(self._model_402_keys)
                        if next_key:
                            if self.simple_mode:
                                self.selected_key = next_key
                            print(f"{Fore.MAGENTA}   [429] Rate limit → cooldown'a alındı, {next_key[:20]}... ile devam{Style.RESET_ALL}")
                            try:
                                from notif_bus import push_notif as _pn
                                _pn(f'⚠️ Rate limit (429) → yeni key devreye girdi', 'warning', 4000)
                            except Exception: pass
                        else:
                            print(f"{Fore.MAGENTA}   [429] Tüm keyler cooldown — en uygun key sekildi{Style.RESET_ALL}")
                            try:
                                from notif_bus import push_notif as _pn
                                _pn('⚠️ Tüm API keyleri cooldown’da — bekleniyor...', 'warning', 6000)
                            except Exception: pass
                    else:
                        time.sleep(30)
                    time.sleep(3)  # Retry arasi kisa bekleme — burst'u onler
                    continue

                elif response.status_code in (500, 502, 503, 524, 520, 521, 522, 523):
                    # ── SUNUCU HATASI ─────────────────────────────────────────────────
                    # Bu key sorunu DEĞİL! API/Cloudflare geçici çöktü.
                    # Key rotasyonu yapma, sadece bekle ve aynı key ile tekrar dene.
                    _server_err_count += 1
                    _backoff = min(10 * (2 ** (_server_err_count - 1)), 120)  # 10,20,40,80,120 sn
                    _ra = response.headers.get('Retry-After') or response.headers.get('retry-after')
                    if _ra:
                        try: _backoff = max(_backoff, int(float(_ra)))
                        except (ValueError, TypeError): pass
                    print(f"{Fore.YELLOW}   [{response.status_code}] Sunucu hatası → {_backoff}sn bekleniyor "
                          f"(#{_server_err_count})...{Style.RESET_ALL}")
                    time.sleep(_backoff)
                    if _server_err_count >= 5:
                        print(f"{Fore.RED}   [!!] {_server_err_count} ardışık sunucu hatası → batch'i geçiyoruz.{Style.RESET_ALL}")
                        return lines_batch
                    continue  # attempt tüketme — logic retry hatası DEĞİL

                elif response.status_code == 413:
                    # ── PAYLOAD TOO LARGE ─────────────────────────────────────────────
                    # Batch çok büyük → yarıya böl ve tekrar gönder
                    print(f"{Fore.YELLOW}   [413] Payload çok büyük → batch yarıya bölünüyor...{Style.RESET_ALL}")
                    if len(lines_batch) > 1:
                        mid = len(lines_batch) // 2
                        try:    _h1 = self.translate_batch(lines_batch[:mid])
                        except: _h1 = list(lines_batch[:mid])
                        try:    _h2 = self.translate_batch(lines_batch[mid:])
                        except: _h2 = list(lines_batch[mid:])
                        return (_h1 or list(lines_batch[:mid])) + (_h2 or list(lines_batch[mid:]))
                    else:
                        return lines_batch  # Tek satır, bölemeyiz

                response.raise_for_status()
                res_json = response.json()
                # Basarili yanit — model-level streak sifirla
                if self.key_manager:
                    self.key_manager.reset_global_streak()

                try:
                    if is_ollama:
                        # Ollama response format
                        translated_text = res_json.get('response', '').strip()
                    elif is_google_api:
                        # Google AI Studio response format
                        translated_text = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        # OpenAI uyumlu format (OpenRouter veya Antigravity)
                        translated_text = res_json['choices'][0]['message']['content'].strip()
                        
                except (KeyError, IndexError) as e:
                    print(f"{Fore.RED}   [!] API yaniti beklenenden farkli: {e}.{Style.RESET_ALL}")
                    continue # Try again if response format is unexpected

                # ── YANIT ÖN-İŞLEME ─────────────────────────────────────────────────────
                # Model bazen markdown, preamble veya suffix gürültüsü ekler.
                # Bunları soyarak tüm pattern'lerin başarı şansını artır.
                _clean_text = translated_text

                # 1. Markdown kod bloğu soy: ```...``` veya ```text\n...\n```
                _clean_text = re.sub(r'```[^\n]*\n', '', _clean_text)
                _clean_text = re.sub(r'```', '', _clean_text)

                # 2. Model preamble gürültüsünü sil (ilk #N satırından önce her şeyi at)
                # Örn: "Sure! Here are the translations:\n\n#1\n..."
                _preamble_cut = re.search(r'(?m)^#\d+', _clean_text)
                if _preamble_cut:
                    _clean_text = _clean_text[_preamble_cut.start():]

                # 3. Suffix gürültüsü: son Translation>'dan sonra gelen açıklama satırlarını sil
                # Örn: "...\n\nNote: I kept the character names as-is."
                _suffix_cut = re.search(r'\n\n(?!#\d)[A-Z][^\n]{10,}$', _clean_text, re.MULTILINE)
                if _suffix_cut and _suffix_cut.start() > len(_clean_text) // 2:
                    _clean_text = _clean_text[:_suffix_cut.start()]

                # 4. Translation> kısmı boşsa bir sonraki satırda olabilir — düzelt
                # "Translation>\n Türkçe metin" → "Translation> Türkçe metin"
                _clean_text = re.sub(r'Translation>\s*\n\s*(?!#\d)(?!Original)([^\n]+)',
                                     r'Translation> \1', _clean_text)

                # Fallback pattern zinciri (en güvenilirden en geniş fallback'e)
                _PARSE_PATTERNS = [
                    # 0. Ana format (HTTPS): #N\nOriginal> ...\nTranslation> <metin>
                    re.compile(
                        r'#(?P<num>\d+)\s*\n'
                        r'(?:Original[^>]*>\s*(?P<orig>[^\n]*)\s*\n)?'
                        r'(?:[^#]*?)Translation>\s*(?P<body>[^\n]*(?:\n(?!#\d)[^\n]*)*)',
                        re.MULTILINE
                    ),
                    # 1. Translation> satırı olmadan direkt metin: #N\n<metin>
                    #    (model Original> satırını atlar, direkt çeviriyi yazar)
                    re.compile(
                        r'#(?P<num>\d+)\s*\n'
                        r'(?:Original[^>]*>[^\n]*\n)?'   # Optional Original> line
                        r'(?P<body>(?!#\d|Original|Translation)[^\n]+)',
                        re.MULTILINE
                    ),
                    # 2. Satır içi: #N Translation> metin  VEYA  #N metin
                    re.compile(
                        r'#(?P<num>\d+)\s+(?:Translation>\s*)?(?P<body>.+)',
                        re.MULTILINE
                    ),
                    # 3. [LN] format (eski, fallback)
                    re.compile(
                        r'\[L\s*(?P<num>\d+)\][:\.]?\s*(?P<body>.+)',
                        re.MULTILINE
                    ),
                    # 4. L32: veya L 32 formati
                    re.compile(
                        r'^L\s*(?P<num>\d+)[:\s]+(?P<body>.+)',
                        re.MULTILINE
                    ),
                    # 5. N. / N) format
                    re.compile(
                        r'^(?P<num>\d+)[.)]\s+(?P<body>.+)',
                        re.MULTILINE
                    ),
                    # 6. "N: metin" format (bazı modeller colon kullanır)
                    re.compile(
                        r'^(?P<num>\d+):\s+(?P<body>.+)',
                        re.MULTILINE
                    ),
                    # 7. Translation> N: metin  (ters sıra, nadiren)
                    re.compile(
                        r'Translation>\s*#?(?P<num>\d+)[:\s]+(?P<body>.+)',
                        re.MULTILINE
                    ),
                ]
                # Temizlenmiş metni kullan
                translated_text = _clean_text
                raw_lines = [l.strip() for l in translated_text.split('\n') if l.strip()]
                expected  = len(lines_batch)

                _translations   = {}   # {satir_no -> ceviri_metin}
                _originals_map  = {}   # {satir_no -> kaynak_metin} (fuzzy match icin)
                _used_pattern   = None
                _best_partial   = {}   # En iyi kısmi sonuç (threshold'u geçemedi)
                _best_partial_idx = None

                for _pat_idx, _pattern in enumerate(_PARSE_PATTERNS):
                    _matches = list(_pattern.finditer(translated_text))
                    if not _matches:
                        continue
                    _tmp = {}
                    for _m in _matches:
                        _n = int(_m.group('num'))
                        if 1 <= _n <= expected and _n not in _tmp:
                            _body = _m.group('body').strip()
                            # "Translation>" prefix'i AI tekrar yazdıysa temizle
                            _body = re.sub(r'^Translation>\s*', '', _body, flags=re.IGNORECASE).strip()
                            # "Original>" prefix'i AI son satıra sızdıysa temizle
                            _body = re.sub(r'\s*Original>.*$', '', _body, flags=re.IGNORECASE | re.DOTALL).strip()
                            if _body:
                                _tmp[_n] = _body
                            # Original metni de yakala (fuzzy match için)
                            if 'orig' in _m.groupdict() and _m.group('orig'):
                                _originals_map[_n] = _m.group('orig').strip()

                    # ── Threshold kontrolü ─────────────────────────────────────
                    # Büyük batch'lerde token limiti nedeniyle model yanıtı kesilebilir.
                    # expected - 2 çok katı → %60 kural: en az %60 bulunduysa yeterli.
                    _threshold = max(1, min(expected - 2, int(expected * 0.60)))
                    if len(_tmp) >= _threshold:
                        _translations = _tmp
                        _used_pattern = _pat_idx
                        break
                    # Threshold altı: ileride kullanmak için en iyi kısmi sonucu sakla
                    if len(_tmp) > len(_best_partial):
                        _best_partial     = _tmp
                        _best_partial_idx = _pat_idx

                # Hiçbir pattern threshold'u geçemediyse — kısmi sonucu kullan
                # (split fallback yerine: eksik satırlar orijinal metin olarak kalır)
                if _used_pattern is None and _best_partial:
                    _partial_pct = len(_best_partial) / expected * 100
                    if _partial_pct >= 40:   # En az %40 bulduysa split'ten daha iyi
                        _translations = _best_partial
                        _used_pattern = _best_partial_idx
                        print(f"{Fore.YELLOW}   [!] Kısmi parse: {len(_best_partial)}/{expected} "
                              f"(%{_partial_pct:.0f}) — eksikler orijinal korunacak{Style.RESET_ALL}")

                if _used_pattern is not None and len(_translations) > 0:
                    # Eksik satırları tespit et
                    _missing_nums = [i+1 for i in range(expected) if i+1 not in _translations]

                    # ── FUZZY MATCH: Eksik satırları orijinal metne göre dene ──────
                    if _missing_nums and _originals_map:
                        for _mn in list(_missing_nums):
                            _src_text = lines_batch[_mn-1].strip().lower()
                            for _tn, _orig in _originals_map.items():
                                if _tn not in _translations and _orig.strip().lower() == _src_text:
                                    _translations[_tn] = _translations.get(_mn, '')
                                    if _mn in _translations:
                                        _translations[_mn] = _translations[_tn]
                                    break
                        _missing_nums = [i+1 for i in range(expected) if i+1 not in _translations]

                    if _missing_nums:
                        _miss_cnt = len(_missing_nums)
                        _miss_pct = _miss_cnt / expected * 100
                        if _miss_cnt <= 10 and _miss_pct <= 40:
                            # Az sayıda eksik → küçük bir batch olarak yeniden gönder
                            # (split fallback değil: sadece eksikler gönderilir = verimli)
                            print(f"{Fore.YELLOW}   [!] {_miss_cnt} satir eksik — kucuk retry batch ({_miss_pct:.0f}%){Style.RESET_ALL}")
                            _missing_lines = [lines_batch[i-1] for i in _missing_nums]
                            try:
                                _retry_results = self.translate_batch(_missing_lines)
                                for _ri, _mn in enumerate(_missing_nums):
                                    if _ri < len(_retry_results) and _retry_results[_ri]:
                                        _translations[_mn] = _retry_results[_ri]
                                _missing_nums = [i+1 for i in range(expected) if i+1 not in _translations]
                                if _missing_nums:
                                    print(f"{Fore.YELLOW}   [!] Retry sonrasi hala {len(_missing_nums)} eksik — orijinal korunacak{Style.RESET_ALL}")
                            except Exception as _re:
                                print(f"{Fore.RED}   [!] Eksik satir retry hatasi: {_re}{Style.RESET_ALL}")
                        else:
                            # Çok fazla eksik → orijinal koru (zaten retry zinciri tekrar deneyecek)
                            print(f"{Fore.YELLOW}   [!] {_miss_cnt} satir parse edilemedi: {_missing_nums[:5]} — orijinal korunacak{Style.RESET_ALL}")
                    else:
                        _pat_names = ['#N+Translation>', '#N-direkt', '#N-inline', '[LN]', 'L32', 'N.', 'N:', 'Tr>N']
                        _pname = _pat_names[_used_pattern] if _used_pattern < len(_pat_names) else f'pat{_used_pattern}'
                        if _used_pattern > 0:
                            print(f"{Fore.YELLOW}   [!] Fallback pattern kullanildi: {_pname}{Style.RESET_ALL}")

                    # Dict'ten sıralı liste oluştur
                    lines = []
                    for _i in range(expected):
                        _txt = _translations.get(_i+1, '').strip()
                        if not _txt:
                            # Son çare: orijinal metni koru
                            _txt = lines_batch[_i]
                        lines.append(_txt)

                else:
                    # Hiçbir pattern işe yaramadı — eski split('\n') yöntemi
                    # Model ne döndürdü? — ilk 200 karakter log'a yaz
                    _resp_preview = translated_text[:200].replace('\n', '↵') if translated_text else "(BOŞ)"
                    print(f"{Fore.YELLOW}   [!] Regex parse basarisiz — split fallback deneniyor...{Style.RESET_ALL}")
                    print(f"{Fore.LIGHTBLACK_EX}       [Model cevabı]: {_resp_preview}{Style.RESET_ALL}")

                    raw_lines = [l.strip() for l in translated_text.split('\n') if l.strip()]
                    _fallback_aligned = {}
                    for _rl in raw_lines:
                        _fm = re.match(r'^\s*#(\d+)', _rl) or re.match(r'^\s*\[L(\d+)\]', _rl) or re.match(r'^\s*(\d+)[.)]\s+', _rl)
                        if _fm:
                            _fn = int(_fm.group(1))
                            if 1 <= _fn <= expected and _fn not in _fallback_aligned:
                                _fallback_aligned[_fn] = re.sub(r'^[#\d().\[\]L\s]+', '', _rl).strip()
                    if len(_fallback_aligned) == expected:
                        lines = [_fallback_aligned[i+1] for i in range(expected)]
                    elif len(raw_lines) >= expected:
                        # [FIX] raw_lines slice'ı genellikle '#1', 'Original>', 'Translation>' gibi
                        # yapı satırları içerir — anlamsız. Sub-batch ile yeniden dene.
                        if len(lines_batch) > 5:
                            print(f"{Fore.YELLOW}   [SPLIT-FB] {len(lines_batch)} satır → alt-batch bölünüyor...{Style.RESET_ALL}")
                            mid = len(lines_batch) // 2
                            try:
                                _fb_first  = self.translate_batch(lines_batch[:mid])
                            except Exception:
                                _fb_first  = list(lines_batch[:mid])
                            try:
                                _fb_second = self.translate_batch(lines_batch[mid:])
                            except Exception:
                                _fb_second = list(lines_batch[mid:])
                            return (_fb_first or list(lines_batch[:mid])) + (_fb_second or list(lines_batch[mid:]))
                        else:
                            lines = raw_lines[:expected]
                    else:
                        print(f"{Fore.RED}   [!] Parse tamamen basarisiz — alt-batch bölünüyor...{Style.RESET_ALL}")
                        if len(lines_batch) > 5:
                            mid = len(lines_batch) // 2
                            print(f"{Fore.YELLOW}   [SPLIT] {len(lines_batch)} satır → {mid} + {len(lines_batch)-mid}{Style.RESET_ALL}")
                            try:
                                _sp_first  = self.translate_batch(lines_batch[:mid])
                            except Exception:
                                _sp_first  = list(lines_batch[:mid])
                            try:
                                _sp_second = self.translate_batch(lines_batch[mid:])
                            except Exception:
                                _sp_second = list(lines_batch[mid:])
                            return (_sp_first or list(lines_batch[:mid])) + (_sp_second or list(lines_batch[mid:]))
                        else:
                            # 5 satır veya daha az → single-line fallback güvenli
                            results = []
                            for line in lines_batch:
                                translated = self.translate_single_line(line, retries=3)
                                results.append(translated if translated else line)
                            return results

                # Son kontrol
                if len(lines) != expected:
                    print(f"{Fore.RED}   [!] Hizalama sonrasi hala uyusmaz ({len(lines)}/{expected}), retry...{Style.RESET_ALL}")
                    time.sleep(1)
                    continue
                    
                # İÇERİK KONTROLÜ (Doğrulama)
                # En azından bir satırın değiştiğini veya İngilizce olmadığını doğrulayalım
                # Basit kontrol: Eğer input English ise ve Output tamamen aynısı ise, muhtemelen çevirmedi.
                # Ancak kısa Cümleler "No" -> "Hayır" olabilir, ama isimler "Sachi" -> "Sachi" kalır.
                # Sadece genel bir 'hepsi aynı mı' kontrolü yapabiliriz.
                
                identical_count = 0
                _non_sign_total = 0  # [FIX] SIGN satırları bu kontrole dahil edilmez
                for inp, outp in zip(lines_batch, lines):
                    # [FIX] [SIGN] önekli satırlar (ekran yazısı) kontrol dışı:
                    # 'Kamiki Hikaru' gibi özel isimler aynen korunur, bu hata DEĞİL.
                    if inp.startswith('[SIGN]') or inp.startswith('[sign]'):
                        continue
                    _non_sign_total += 1
                    # Temizlenmiş kıyas (Noktalama ve boşluklar ile placeholderları görmezden gel)
                    clean_in = re.sub(r'[^\w]', '', re.sub(r'§§\d+§§', '', inp)).lower()
                    clean_out = re.sub(r'[^\w]', '', re.sub(r'§§\d+§§', '', outp)).lower()
                    
                    if clean_in == clean_out:
                        # Eğer geriye hiçbir harf kalmadıysa (sadece "?", "!", "「」" veya "§§0§§" ise)
                        # Bunun birebir aynı dönmesi bir HATA değildir. Sayma.
                        if len(clean_in) < 2:
                            continue
                            
                        # Eğer orijinal metin çok kısaysa (isim, ünlem, nida vb. ise)
                        if len(inp) < 15:
                            # Sık kullanılan İngilizce stop/komut kelimesiyse hata say (Çevrilmeliydi)
                            COMMON_ENGLISH_WORDS = {"yes", "no", "nah", "yeah", "yep", "nope", "ok", "okay", "alright", "what", "why", "who", "where", "how"}
                            if clean_in in COMMON_ENGLISH_WORDS:
                                identical_count += 1
                            continue # Diğer kısa kelimelerde hata sayma (Örn: Sachi, Ah, Hımm vb)
                        
                        # Eğer uzun bir metinse ve sadece isim listesi (Title Case) ise hata sayma
                        words = inp.split()
                        if words and sum(1 for w in words if w[0].isupper() and w[1:].islower()) / len(words) > 0.7:
                            continue
                            
                        # Eğer metinde hiç İngilizce veya Türkçe kelime kökü yoksa (Örn: Romaji, Çince RAM kırıntısı) hata sayma
                        ENGLISH_STOP_WORDS = {"the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with"}
                        clean_words = set(re.sub(r'[^\w\s]', '', inp.lower()).split())
                        if not bool(clean_words.intersection(ENGLISH_STOP_WORDS)):
                            continue
                            
                        # Üstteki hiçbir istisnaya uymadıysa, yapay zeka harbi uzun/anlamlı bir cümleyi çevirmeyi reddetmiş demektir.
                        identical_count += 1
                
                # [FIX] Sadece dialog satırları (%100 aynı) → retry
                # Signs karışık batcth'ta bile dialog kısmı çevrilmişse devam et
                _check_total = _non_sign_total if _non_sign_total > 0 else len(lines_batch)
                if identical_count == _check_total and _check_total > 0:
                     # Hepsi aynı, muhtemelen AI reddetti veya çevirmedi.
                     print(f"{Fore.YELLOW}   [!] Çeviri yapılmamış gibi görünüyor (Hepsi aynı), tekrar deneniyor ({_logic_attempts}/{max_retries})...{Style.RESET_ALL}")
                     print(f"{Fore.MAGENTA}[DEBUG] First line input: {lines_batch[0]}{Style.RESET_ALL}")
                     print(f"{Fore.MAGENTA}[DEBUG] First line output: {lines[0]}{Style.RESET_ALL}")
                     time.sleep(1)
                     continue

                # ── SLIDING WINDOW GÜNCELLE: Bu batch'in son N satırını sakla ──
                new_pairs = list(zip(lines_batch, lines))
                self._context_window = (self._context_window + new_pairs)[-self._context_window_size:]

                return lines

            except requests.exceptions.Timeout as _timeout_ex:
                # ── ISTEK ZAMAN AŞIMI ─────────────────────────────────────
                # Sunucu yaşö merak etmiş, timeout düştü. Key rotasyonu yapma.
                _net_err_count += 1
                _tw = min(5 * _net_err_count, 30)
                print(f"{Fore.YELLOW}   [TIMEOUT] İstek zaman aşımı → {_tw}sn bekleniyor (#{_net_err_count})...{Style.RESET_ALL}")
                time.sleep(_tw)
                continue  # attempt tüketme

            except (requests.exceptions.ConnectionError,
                    requests.exceptions.ChunkedEncodingError) as _net_ex:
                # ── AĞ BAGLANTI HATASI ─────────────────────────────────────
                # İnternet koptu veya DNS hatası. KEY SORUNU DEĞİL!
                _net_err_count += 1
                _nw = min(10 * _net_err_count, 60)
                print(f"{Fore.YELLOW}   [NET] Bağlantı hatası → {_nw}sn bekleniyor "
                      f"(#{_net_err_count}): {str(_net_ex)[:60]}{Style.RESET_ALL}")
                time.sleep(_nw)
                if _net_err_count >= 8:
                    print(f"{Fore.RED}   [!!] 8+ ardışık ağ hatası → internet kopmuş olabilir, batch'i geçiyoruz.{Style.RESET_ALL}")
                    return lines_batch
                continue  # attempt tüketme

            except Exception as e:
                err_str = str(e)
                # 401/403 → key dead
                if "401" in err_str or "403" in err_str:
                    if self.key_manager:
                        self.key_manager.mark_as_exhausted(current_key)
                # 503 genellikle exception olarak gelmez artık (HTTP handler'da ele alındı)
                # Ama string içinde görünebilir (httpx vs requests farkı)
                if "503" in err_str or "Service Unavailable" in err_str or "10061" in err_str or "Failed to establish" in err_str:
                    _server_err_count += 1
                    _backoff = min(30 * (2 ** (_server_err_count - 1)), 300)
                    import random
                    _backoff += random.uniform(0, 5)
                    print(f"{Fore.YELLOW}   [503-EX] Bağlantı hatası — {_backoff:.0f}sn bekleniyor (#{_server_err_count})...{Style.RESET_ALL}")
                    time.sleep(_backoff)
                    continue  # attempt tüketme — sunucu sorunu
                else:
                    _logic_attempts += 1  # Gerçek logic/parse hatası — attempt tüket
                    print(f"{Fore.RED}   [!] Batch hatası: {e}, Retrying ({_logic_attempts}/{max_retries})...{Style.RESET_ALL}")
                    time.sleep(2)

        # FALLBACK: Tek Tek Çeviri (Güvenli Yöntem)
        print(f"{Fore.YELLOW}   [!] Batch başarısız ({_logic_attempts}/{max_retries} logic deneme), Satır-Satır moduna geçiliyor...{Style.RESET_ALL}")
        results = []
        # SATIR-SATIR DELAY: Her satır arası bekleme — Google API bombardımanını önler
        # AG modunda daha uzun bekle (proxy üzerinden gidiyor)
        line_delay = 8 if getattr(self, '_is_antigravity', False) else 3
        for i, line in enumerate(lines_batch):
            # Her satırı 3 kere deneme hakkıyla çevir (5 değil — toplam istek sayısını azalt)
            translated = self.translate_single_line(line, retries=3)
            # [FIX KRİTİK] translate_single_line None dönerse (401/hata), orijinal satırı koru
            if translated is None:
                print(f"{Fore.RED}   ❌ [SIMPLE MODE] Key geçersiz! Lütfen yeni bir key ekleyin.{Style.RESET_ALL}")
                translated = line  # None yerine orijinal metni döndür
            results.append(translated)
            # Her satır için bekle (son satırda bekleme)
            if i < len(lines_batch) - 1:
                time.sleep(line_delay)
        
        return results

    def translate_text(self, text):
        """Genel amaçlı metin çevirisi (Metadata için) - Cache Destekli"""
        if not text or not text.strip(): return text
        
        # [CACHE CHECK] Normalize edilmis cache key (buyuk/kucuk harf duyarsiz MD5)
        try:
            import hashlib as _hl
            hashed_key = _hl.md5(text.lower().strip().encode('utf-8', errors='replace')).hexdigest()
        except Exception:
            hashed_key = text.strip()
        if hashed_key in self.cache:
            return self.cache[hashed_key]

        # PRE-PROCESS: Uncensor
        processed_text = self.uncensor_text(text)
        
        # Çok uzun metinleri kısalt (API limiti)
        if len(processed_text) > 1000: processed_text = processed_text[:997] + "..."
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Check if using Ollama (local model) — kapsami genisletildi
                is_ollama = (
                    self.model.startswith('gemma2:') or
                    self.model.startswith('llama') or
                    self.model.startswith('mistral:') or
                    self.model.startswith('phi') or
                    self.model.startswith('qwen:') or
                    ('ollama' in self.model.lower()) or
                    (':' in self.model and '/' not in self.model)
                )
                
                if is_ollama:
                    # Use Ollama local API (no API key needed)
                    current_key = None
                    is_google_api = False
                else:
                    # Use cloud APIs
                    current_key = self.key_manager.get_valid_key()
                if not current_key: break
                
                # Detect API type: Google AI Studio vs OpenRouter
                is_google_api = current_key.startswith("AIzaSy")
                
                # Metadata için KATI prompt
                prompt = (
                    f"You are a professional translator. Translate the following text from English to {self.config['target_lang']}.\n"
                    "CONTEXT: HENTAI / ADULT ANIME. This is for adult audience metadata.\n"
                    "RULES:\n"
                    "1. Output ONLY the translated text.\n"
                    "2. ABSOLUTELY NO CENSORSHIP. Translate all swear words/adult terms raw and explicitly (e.g. 'Facial' -> 'Yüze Boşalma', 'Creampie' -> 'İçine Boşalma'). Do NOT filter anything.\n"
                    "3. Do NOT add any introductory or concluding remarks.\n"
                    "4. GENRE SPECIFIC: If translating anime genres, use standard Turkish anime terminology.\n"
                    "5. If the input is a list of genres, return them comma separated.\n"
                    f"TEXT:\n{processed_text}"
                )
                
                if self.config.get("english_only"):
                    prompt = prompt.replace("TEXT:\n", "RULE 6: If text is NOT English, return it AS-IS.\nTEXT:\n")
                
                if is_google_api:
                    # Google AI Studio API format
                    model_name = self.model.split('/')[-1] if '/' in self.model else self.model
                    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={current_key}"
                    data = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096}
                    }
                    headers = {"Content-Type": "application/json"}
                    response = self._post(api_url, headers=headers, json=data, timeout=20)
                else:
                    # OpenRouter API format
                    headers = {"Authorization": f"Bearer {current_key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com", "X-Title": "Antigravity"}
                    data = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3, "max_tokens": 4096}
                    response = self._post(self.api_url, headers=headers, json=data, timeout=20)
                
                # CRITICAL FIX: Only mark as exhausted on PERSISTENT AUTH errors
                if response.status_code == 401:  # Invalid key - truly dead
                    print(f"{Fore.RED}   [!] Anahtar geçersiz (401), loglanıyor...{Style.RESET_ALL}")
                    self.key_manager.mark_as_exhausted(current_key)
                    continue
                elif response.status_code == 402:  # No credit
                    if self.simple_mode:
                        # SIMPLE MODE: Remove exhausted key and try next one
                        print(f"{Fore.YELLOW}   ⚠️ [SIMPLE MODE] Key kredisi bitti!{Style.RESET_ALL}")
                        if self.key_manager and current_key:
                            self.key_manager.mark_as_exhausted(current_key)
                            next_key = self.key_manager.get_key()
                            if next_key:
                                self.selected_key = next_key
                                print(f"{Fore.CYAN}   [SIMPLE MODE] Yeni key'e geçiliyor: {next_key[:25]}...{Style.RESET_ALL}")
                                continue
                            else:
                                print(f"{Fore.RED}   ❌ [SIMPLE MODE] Başka key kalmadı!{Style.RESET_ALL}")
                                raise Exception("No more API keys available")
                    else:
                        print(f"{Fore.YELLOW}   [!] Kredit hatası (402), yeni key deneniyor...{Style.RESET_ALL}")
                        continue
                elif response.status_code == 429:  # Rate limit - definitely temporary!
                    backoff_time = 10 * (attempt + 1)  # Subtitle Edit style: LONG backoff
                    print(f"{Fore.MAGENTA}   [!] Rate limit (429), {backoff_time} saniye bekleniyor...{Style.RESET_ALL}")
                    time.sleep(backoff_time)
                    continue  # Try with next key
                
                response.raise_for_status()
                res_json = response.json()
                
                # Extract translated text from response (different format for Google vs OpenRouter)
                try:
                    if is_google_api:
                        # Google AI Studio response format
                        trans = res_json['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        # OpenRouter response format
                        trans = res_json['choices'][0]['message']['content'].strip()
                except (KeyError, IndexError) as e:
                    print(f"{Fore.RED}   [!] API yanıtı beklenenden farklı: {e}. Tam yanıt: {res_json}{Style.RESET_ALL}")
                    continue # Try again if response format is unexpected

                # Temizlik
                garbage_prefixes = ["Sure", "Here is", "Elbette", "Tabii", "Çeviri:", "Translation:"]
                for g in garbage_prefixes:
                    if trans.startswith(g):
                        parts = trans.split(':', 1)
                        if len(parts) > 1: trans = parts[1].strip()
                
                if trans: 
                    # [CACHE SAVE]
                    self.cache[hashed_key] = trans
                    settings.save_translation_cache(self.cache)
                    return trans
                
            except Exception as e:
                time.sleep(1)
        
        return text # Çevrilemzse orijinalini döndür
    def translate_genre_list(self, genres):
        """
        Genre listesini özel sözlük kullanarak çevirir.
        AI yerine sözlük önceliklidir (Hentai terimleri için).
        """
        translated_list = []
        for g in genres:
            if not g: continue
            g_lower = g.lower().strip()
            
            # 1. Sözlük Kontrolü
            if g_lower in self.GENRE_MAPPING:
                translated_list.append(self.GENRE_MAPPING[g_lower])
                continue
                
            # 2. Eğer sözlükte yoksa AI ile çevir (Tek kelime)
            # Ama önce cache kontrolü
            if g_lower in ["hd", "4k", "1080p", "60fps"]: # Teknik terimleri elleme
                translated_list.append(g)
                continue
                
            trans = self.translate_text(g)
            
            # SANSÜRLENDİ geldiyse orijinalini kullan
            if "sansürlendi" in trans.lower() or "censored" in trans.lower():
                translated_list.append(g) # Orijinali daha iyidir
            else:
                translated_list.append(trans)
                
        return translated_list

# Test için
if __name__ == "__main__":
    t = SubtitleTranslator("google/gemini-2.0-flash-001")
    # Test Genres
    test_g = ["Facial", "Creampie", "Uncensored", "Slice of Life", "UnknownTerm"]
    try:
        print("Genre Test:", t.translate_genre_list(test_g))
    except Exception as ex:
        print("Hata:", ex)
        print("Hata:", ex)

