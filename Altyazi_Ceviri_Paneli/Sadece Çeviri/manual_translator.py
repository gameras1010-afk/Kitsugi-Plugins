import os
import re
import sys
import json
import time
import glob
from colorama import Fore, Style, init
import requests

# Parent dizini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from subtitle_processor import process_and_replace_subtitle
    from translator import SubtitleTranslator # Key yönetimi için gerekli olabilir
except ImportError as e:
    print(f"{Fore.RED}HATA: Modül yükleme hatası!{Style.RESET_ALL}")
    print(f"{Fore.RED}Detay: {e}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Lütfen 'subtitle_processor.py' ve 'translator.py' dosyalarının üst klasörde olduğundan emin olun.{Style.RESET_ALL}")
    try:
        input("Çıkmak için ENTER...")
    except (EOFError, KeyboardInterrupt):
        pass
    sys.exit(1)

init(autoreset=True)

# ─── Ses Bildirimleri (winsound — built-in Windows) ──────────────────────────
def _play_tone(tone_type: str):
    """Tatlı bir tonla kullanıcıyı bilgilendir.
    tone_type: 'start' | 'file_done' | 'all_done' | 'error' | 'interrupt' | 'startup'
    """
    try:
        import winsound
        if tone_type == 'startup':
            # Program açıldı: hafif hoş karşılama sesi
            winsound.Beep(440, 100)   # A4
            winsound.Beep(523, 150)   # C5
        elif tone_type == 'start':
            # İşleme başlıyor: hafif yükselen üç nota
            winsound.Beep(523, 120)   # C5
            winsound.Beep(659, 120)   # E5
            winsound.Beep(784, 180)   # G5
        elif tone_type == 'file_done':
            # Dosya tamamlandı: iki hoş nota
            winsound.Beep(880, 120)   # A5
            winsound.Beep(1047, 200)  # C6
        elif tone_type == 'all_done':
            # Her şey bitti: kısa şölen fanfarı
            winsound.Beep(523, 100)   # C5
            winsound.Beep(659, 100)   # E5
            winsound.Beep(784, 100)   # G5
            winsound.Beep(1047, 300)  # C6 (uzun bittiş)
        elif tone_type == 'error':
            # Hata: aşağıya inen üç ciddi nota
            winsound.Beep(440, 150)   # A4
            winsound.Beep(330, 150)   # E4
            winsound.Beep(220, 300)   # A3 (düşük, uzun)
        elif tone_type == 'interrupt':
            # Kullanıcı durdurdu (Ctrl+C): kısa iki iniş
            winsound.Beep(600, 120)
            winsound.Beep(400, 200)
    except Exception:
        pass  # winsound yoksa veya ses çalmıyorsa sessizce geç

# ─── FFmpeg / FFprobe yol bulma ───────────────────────────────────────────────
def _find_ff_tool(name):
    """
    ffmpeg veya ffprobe'u bulur:
      0. Portable mod: tools/ klasörü (en öncelikli)
      1. Uygulama ana klasörü ({app}/ffmpeg.exe)
      2. PATH
      3. Bilinen sabit kurulum yolları (C:/ffmpeg-.../bin/)
    """
    import shutil
    import subprocess
    exe = name + (".exe" if os.name == "nt" else "")

    # 0) Portable mod: NEXUS_USER_DIR/../../tools/ klasörü
    _nexus_root = os.environ.get('NEXUS_USER_DIR', '')
    if _nexus_root:
        _portable_root = os.path.abspath(os.path.join(_nexus_root, '..'))
        for _d in [os.path.join(_portable_root, 'tools'), _portable_root]:
            _c = os.path.join(_d, exe)
            if os.path.isfile(_c):
                return _c

    # 1) Uygulama ana klasörü
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidate = os.path.join(app_dir, exe)
    if os.path.isfile(candidate):
        return candidate

    # 2) PATH (shutil.which)
    found = shutil.which(name)
    if found:
        return found

    # 3) Bilinen Windows kurulum yolları
    import glob as _glob
    search_patterns = [
        rf"C:\ffmpeg*\bin\{exe}",
        rf"C:\Program Files\ffmpeg*\bin\{exe}",
        rf"C:\Program Files (x86)\ffmpeg*\bin\{exe}",
        rf"D:\ffmpeg*\bin\{exe}",
    ]
    for pattern in search_patterns:
        matches = _glob.glob(pattern)
        if matches:
            return matches[0]

    return name  # Bulunamazsa komutu kendi adıyla dene (PATH'te olabilir)

def _ffmpeg():
    return _find_ff_tool("ffmpeg")

def _ffprobe():
    return _find_ff_tool("ffprobe")

# ─────────────────────────────────────────────────────────────────────────────

# ----------------- AYARLAR VE PREFS -----------------

PREFS_FILE = os.path.join(os.path.dirname(__file__), '..', "user_preferences.json")

def load_prefs():
    # Varsayılan Değerler
    defaults = {
        'translate': True,
        'clean_sub': True,
        'smart_merge': True,
        'sub_format': 'ASS',           # ASS, SRT, VTT, ALL
        'ai_model': 'google/gemini-2.0-flash-001',
        'custom_api_keys_path': None,
        # Gelişmiş Çeviri Ayarları (Subtitle Edit Std)
        'source_lang': 'English',
        'target_lang': 'Turkish',
        'target_language_code': 'tr',  # ISO 639-1
        'delay_sn': 0,
        'per_file_delay': 15,
        'max_byte_batch': 2000,
        'only_english': True,
        'romaji_block': True,          # Romaji/Japonca kelimeleri orijinal haliyle bırak
        'max_line_length': 75,
        'line_merge_mode': 'default',
        '_no_auto_split': False,       # Otomatik satır bölmeyi kapat
        'api_endpoint': 'https://openrouter.ai/api/v1/chat/completions',
        'batch_size': 1,
        'max_retries': 6,
        'force_translate': True,
        'nsfw_mode': False,
        'hentai_glossary': False,
        'natural_dialogue': True,
        'protect_positioning': True,
        'font_size_mode': 'normalize',
        'custom_font_size': 80,
        'simple_mode': True,
        # ── Şarkı/Karaoke Pipeline ──
        'use_song_lyrics_pass': True,   # Şarkı sözleri özel çeviri geçişi
        'translate_song_lyrics': True,  # Şarkı sözlerini çevir
        'use_karaoke_collapse': True,   # Karaoke heceleri birleştir
        'use_style_suffix_detection': True,  # Stil soneki tespiti (EN/JP/kara)
        'rescue_pass': True,            # Başarısız satırları kurtarma geçişi
        # ── Gelişmiş Pipeline Özellikleri ──
        'use_episode_context': True,    # Bölüm-bölüm bağlam takibi
        'use_fandom_glossary': True,    # Fandom Wiki terim sözlüğü
        'generate_html_report': True,   # HTML çeviri raporu
        'write_language_header': True,  # ASS'e dil başlığı yaz
        'check_timing_overlaps': True,  # Zamanlama çakışmalarını kontrol et
        'validate_cps_cpl': True,       # CPS/CPL doğrulaması
        'collapse_animation_frames': True,  # Animasyon karelerini birleştir
        'ignore_song_style_for_romaji': False,  # Şarkı stilini romaji için yoksay
        # ── Medya Bağlam (runtime'da doldurulur, default None) ──
        'media_title': None,
        'series_title': None,
        'episode': None,
        'episode_number': None,
        'season': None,
        'season_number': None,
        # ── Tespit Motoru Ayarları ──
        'skip_romaji_mode': True,    # Romaji satırları içerik tespiti ile filtrele
        'force_no_style': False,     # Stil adına bakma, sadece içerik analizi yap
        'content_detect': True,     # content_detector modülünü kullan (False=eski sistem)
    }
    
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except: pass
        
    return defaults

def save_prefs(prefs):
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, indent=4)
        print(f"{Fore.GREEN}Ayarlar kaydedildi.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Ayarlar kaydedilemedi: {e}{Style.RESET_ALL}")

# ----------------- KLASÖR TARAMA -----------------

def _count_dialogue_lines(filepath):
    """
    Verilen altyazı dosyasındaki gerçek diyalog satırı sayısını döndürür.
    ASS: 'Dialogue:' ile başlayan ve metin kısmı boş olmayan satırlar.
    SRT: '-->' içeren blokların metin kısımları.
    Sonuç 0 ise dosya boş/sadece efekt demektir.
    """
    try:
        ext = os.path.splitext(filepath)[1].lower()
        count = 0
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()

        if ext in ('.ass', '.ssa'):
            for line in lines:
                line = line.strip()
                if not line.startswith('Dialogue:'):
                    continue
                # ASS format: Dialogue: Layer,Start,End,Style,Name,ML,MR,MV,Effect,Text
                parts = line.split(',', 9)
                if len(parts) < 10:
                    continue
                text = parts[9].strip()
                # Sadece tag içeren veya boş satırları say
                clean = re.sub(r'\{[^}]*\}', '', text).strip()
                if clean:
                    count += 1
        else:
            # SRT / VTT: --> içeren satırdan sonraki metin satırlarını say
            for i, line in enumerate(lines):
                if '-->' in line and i + 1 < len(lines):
                    text = lines[i + 1].strip()
                    clean = re.sub(r'<[^>]+>', '', text).strip()
                    if clean:
                        count += 1
        return count
    except Exception:
        return -1  # Hata durumunda -1: dosyayı silme, işlemeye bırak


def get_best_subtitle_stream(video_path):
    """
    ffprobe kullanarak videodaki altyazı akışlarını tarar ve en uygun olanın
    absolute stream index'ini döndürür.

    Öncelik Sırası:
      1. Fansub İngilizce  (başlıkta/dilde hem 'fansub/çeviri' hem 'eng/english')
      2. Orjinal İngilizce (lang='eng' veya başlıkta 'english')
      3. Diğer diller      (İspanyolca, Fransızca, Almanca vb.)
      4. Japonca/Çince/Korece/Romaji  (en son çare)

    S&S (Signs & Songs) gibi akışlar her zaman atlanır.
    Hiç uygun akış yoksa None döner.
    """
    try:
        import subprocess
        import json

        cmd = [
            _ffprobe(), "-v", "error", "-select_streams", "s",
            "-show_entries", "stream=index,codec_name:stream_tags=title,language",
            "-of", "json", video_path
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', errors='replace',
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0)
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        streams = data.get('streams', [])

        if not streams:
            print(f"{Fore.YELLOW}   [-] Bu videoda hiç altyazı akışı bulunamadı.{Style.RESET_ALL}")
            return None

        # --- Filtre Listeleri ---
        # Her zaman atlanacak akışlar (Signs & Songs gibi diyalogsuz içerikler)
        SKIP_KEYWORDS    = ["sign", "song", "s&s", "s/s", "s & s", "karaoke", "kara"]
        # Fansub/çeviri grubu içeren başlıklar → İngilizce ile birlikte en yüksek öncelik
        FANSUB_KEYWORDS  = ["fansub", "çeviri", "scanlation", "subbed", "subtitled"]
        # İngilizce dil etiketleri
        ENG_LANG         = {"eng", "en"}
        ENG_TITLE_KW     = ["english", "ingilizce"]
        # Japonca/Çince/Korece/Romaji → en son çare
        CJK_LANG         = {"jpn", "ja", "chi", "zh", "zho", "kor", "ko"}
        CJK_TITLE_KW     = ["japanese", "japonca", "chinese", "çince", "korean", "korece",
                            "romaji", "roma", "jp", "jap"]

        # Tüm akışları tara ve kategorile
        tier1 = []  # Fansub İngilizce
        tier2 = []  # Orjinal İngilizce
        tier3 = []  # Diğer diller
        tier4 = []  # CJK / Romaji (son çare)

        for s in streams:
            idx = s.get('index')
            if idx is None:
                continue

            tags  = s.get('tags', {})
            title = tags.get('title', '').lower().strip()
            lang  = tags.get('language', '').lower().strip()

            # Codec kontrolu: PGS/HDMV/image tabanli formatlar ATLA (text'e donusturulemez)
            codec = s.get('codec_name', '').lower()
            IMAGE_CODECS = {'hdmv_pgs_subtitle', 'pgs', 'dvd_subtitle', 'dvdsub',
                            'dvb_subtitle', 'xsub', 'pgssub', 'sup'}
            if codec in IMAGE_CODECS:
                print(f"{Fore.LIGHTBLACK_EX}   [ATLANDI] PGS/bitmap altyazi (text'e cevrilemez): "
                      f"Stream #{idx} ({codec}) - title='{title}' lang='{lang}'{Style.RESET_ALL}")
                continue

            # S&S / Signs / Songs → HER ZAMAN ATLA
            if any(k in title for k in SKIP_KEYWORDS) or any(k in lang for k in SKIP_KEYWORDS):
                print(f"{Fore.LIGHTBLACK_EX}   [ATLANDI] Signs/Songs akışı tespit edildi: "
                      f"Stream #{idx} - title='{title}' lang='{lang}'{Style.RESET_ALL}")
                continue

            is_eng    = (lang in ENG_LANG) or any(k in title for k in ENG_TITLE_KW)
            is_fansub = any(k in title for k in FANSUB_KEYWORDS)
            is_cjk    = (lang in CJK_LANG) or any(k in title for k in CJK_TITLE_KW)

            if is_eng and is_fansub:
                tier1.append((idx, title, lang))   # Fansub İngilizce
            elif is_eng:
                tier2.append((idx, title, lang))   # Orjinal İngilizce
            elif is_cjk:
                tier4.append((idx, title, lang))   # CJK en sona
            else:
                tier3.append((idx, title, lang))   # Diğer diller

        # Öncelik sırasına göre ilk bulunana dön
        tier_names = [
            (tier1, "Fansub İngilizce",      Fore.GREEN),
            (tier2, "Orjinal İngilizce",     Fore.GREEN),
            (tier3, "Diğer Dil",             Fore.YELLOW),
            (tier4, "CJK/Romaji (son çare)", Fore.RED),
        ]

        for tier, label, color in tier_names:
            if tier:
                idx, title, lang = tier[0]
                print(f"{color}   [SEÇİLDİ] {label}: Stream #{idx}"
                      f" - title='{title}' lang='{lang}'{Style.RESET_ALL}")
                return idx

        print(f"{Fore.YELLOW}   [-] Geçerli bir altyazı akışı bulunamadı (hepsi atlandı).{Style.RESET_ALL}")
        return None

    except Exception as e:
        print(f"{Fore.RED}   [!] FFprobe hatası: {e}{Style.RESET_ALL}")
        return None


def extract_subtitles_from_video(video_path, output_dir):
    """
    Video dosyasından gömülü altyazıyı (eğer varsa) çıkarır ve .ass olarak kaydeder.
    Başarılı olursa yeni oluşturulan .ass dosyasının yolunu döndürür, aksi takdirde None.
    """
    try:
        import subprocess
        result = subprocess.run([_ffmpeg(), "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0)
        if result.returncode != 0:
            print(f"{Fore.RED}[!] FFmpeg bulunamadı. Video altyazı çıkarma işlemi atlanıyor.{Style.RESET_ALL}")
            return None
            
        filename = os.path.basename(video_path)
        base, _ = os.path.splitext(filename)
        out_sub_path = os.path.join(output_dir, f"{base}_extracted.ass")
        
        if os.path.exists(out_sub_path):
            print(f"{Fore.YELLOW}   [ATLANDI] Bu videonun altyazısı zaten çıkarılmış: {base}_extracted.ass{Style.RESET_ALL}")
            return out_sub_path
            
        print(f"{Fore.CYAN}   [FFPROBE] {filename} için altyazı akışları inceleniyor...{Style.RESET_ALL}")
        stream_idx = get_best_subtitle_stream(video_path)
        
        if stream_idx is None:
            return None
            
        print(f"{Fore.CYAN}   [FFMPEG] {filename} içindeki Stream #{stream_idx} altyazı çıkarılıyor...{Style.RESET_ALL}")
        
        cmd = [
            _ffmpeg(), "-y", "-v", "error", "-i", video_path, 
            "-map", f"0:{stream_idx}", out_sub_path
        ]
        
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='replace',
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0)
        if process.returncode == 0 and os.path.exists(out_sub_path) and os.path.getsize(out_sub_path) > 0:
            # --- Boş Diyalog Kontrolü ---
            # Çıkarılan dosyada gerçek konuşma satırı var mı?
            dialogue_count = _count_dialogue_lines(out_sub_path)
            if dialogue_count == 0:
                print(f"{Fore.YELLOW}   [ATLANDI] Çıkarılan altyazı dosyasında hiç diyalog satırı yok (boş/sadece efekt): {base}_extracted.ass{Style.RESET_ALL}")
                try: os.remove(out_sub_path)
                except: pass
                return None
            print(f"{Fore.GREEN}   [OK] Altyazı başarıyla çıkarıldı ({dialogue_count} diyalog satırı): {base}_extracted.ass{Style.RESET_ALL}")
            return out_sub_path
        else:
            print(f"{Fore.YELLOW}   [-] Video dosyasında uyumlu/gömülü bir altyazı akışı bulunamadı veya çıkarılamadı.{Style.RESET_ALL}")
            if os.path.exists(out_sub_path):
                try: os.remove(out_sub_path)
                except: pass
            return None
            
    except Exception as e:
        print(f"{Fore.RED}   [!] Altyazı çıkarma hatası ({video_path}): {e}{Style.RESET_ALL}")
        return None



def _is_already_turkish(filepath: str, threshold: float = 0.30) -> bool:
    """
    Altyazi dosyasindaki satirlari ornekler ve Turkce karakter + morfoloji oranini kontrol eder.
    tr_lang_detector.turkish_score() kullanarak guvenilir tespit yapar.
    Oran threshold'u gecerse True doner (zaten Turkce, cevirme).
    """
    TR_REAL = set("\u011f\u015f\u0131\xfc\xf6\xe7\u011e\u015e\u0130\xdc\xd6\xc7")  # ğşıüöçĞŞİÜÖÇ
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as _f:
            raw = _f.read()
    except Exception:
        return False

    if filepath.lower().endswith(".ass"):
        import re as _re
        lines = _re.findall(r"^Dialogue:.*?,,(.+)", raw, _re.MULTILINE)
        lines = [_re.sub(r"\{[^}]*\}", "", l).strip() for l in lines]
    elif filepath.lower().endswith(".srt"):
        lines = [l.strip() for l in raw.splitlines()
                 if l.strip() and not l.strip().isdigit() and "-->" not in l]
    else:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

    # 60 ornek satir al (daha guvenilir)
    sample = [l for l in lines if len(l) > 4][:60]
    if not sample:
        return False

    # Oncelik: tr_lang_detector ile agirlikli skor (kucuk metin icin de calisir)
    try:
        from tr_lang_detector import turkish_score as _tr_score
        # Ilk 20 satiri birlestirip genel skor al
        combined = " ".join(sample[:20])
        bulk_score = _tr_score(combined)
        # Satir bazli TR karakter orani (fallback sinyal)
        tr_char_count = sum(1 for l in sample if any(c in TR_REAL for c in l))
        tr_char_ratio = tr_char_count / len(sample)
        # Agirlikli karar: bulk_score yuksekse veya karakter orani yuksekse TR say
        combined_score = bulk_score * 0.7 + tr_char_ratio * 0.3
        return combined_score >= threshold
    except ImportError:
        # Fallback: sadece TR karakter orani
        tr_count = sum(1 for l in sample if any(c in TR_REAL for c in l))
        return (tr_count / len(sample)) >= threshold
def scan_and_process_directory(path, prefs, auto_scan_mode=False, _explicit_targets=None):
    """
    Verilen yoldaki (dosya veya klasör) altyazıları bulur ve işler.
    Klasör ise recursive tarama (isteğe bağlı) yapar.
    auto_scan_mode=True ise onay sormadan recursive tarar.
    _explicit_targets: GUI'den gelen explicit dosya listesi — scan atlanır,
                       sadece filtreler uygulanır. Bağlam (context) korunur!
    """
    targets = []

    if _explicit_targets is not None:
        # ── GUI BATCH MODE: scan atla, direkt listeyi kullan ────────────────
        targets = list(_explicit_targets)
        print(f"\n{Fore.CYAN}[GUI BATCH] {len(targets)} dosya tek oturumda işlenecek — bağlam/context korunuyor:{Style.RESET_ALL}")
        for i, t in enumerate(targets, 1):
            print(f"  [{i}] {os.path.basename(t)}")
        # source_dir için: ilk dosyanın klasörü
        if not path or not os.path.isdir(path):
            path = os.path.dirname(targets[0]) if targets else os.getcwd()
    elif os.path.isfile(path):
        targets.append(path)
    elif os.path.isdir(path):
        recursive = False
        if auto_scan_mode:
            print(f"\n{Fore.CYAN}Otomatik Tarama Modu: {path} ve alt klasörleri taranıyor...{Style.RESET_ALL}")
            recursive = True
        else:
            print(f"\n{Fore.YELLOW}Hedef bir klasör: {path}{Style.RESET_ALL}")
            choice = input("Alt klasörler de taransın mı? (E/h): ").lower().strip()
            recursive = choice in ['e', 'evet', 'y', 'yes', '']
        
        print(f"{Fore.CYAN}Altyazı dosyaları aranıyor...{Style.RESET_ALL}")
        
        # TÜM ALTYAZI FORMATLARI OTOMATİK TARANIR — format seçmeye gerek yok
        # Metin tabanlı altyazılar: ass/ssa/srt/vtt/sub/sbv/ttml/dfxp/lrc/cap
        # VobSub çifti: idx (binary container) — sub ile birlikte gelir
        # Video gömülü track'ler: mkv/mp4/avi/webm
        extensions = [
            # ── Metin Tabanlı Altyazılar ──────────────────────────
            '*.ass', '*.ssa',          # SubStation Alpha (anime standardı)
            '*.srt',                   # SubRip — en yaygın
            '*.vtt',                   # WebVTT (web/streaming)
            '*.sub',                   # MicroDVD / SubViewer
            '*.sbv',                   # YouTube altyazı
            '*.ttml', '*.dfxp',        # Timed Text (Netflix/Amazon)
            '*.lrc',                   # LRC (müzik/karaoke)
            '*.cap',                   # NiCom / çeşitli
            '*.smi', '*.sami',         # SAMI (Microsoft)
            '*.stl',                   # EBU STL (yayın)
            '*.rt',                    # RealText
            # ── Video (Gömülü Track) ──────────────────────────────
            '*.mkv', '*.mp4', '*.avi', '*.webm',
        ]
        
        safe_path = glob.escape(path)
        if recursive:
            for ext in extensions:
                # glob recursive requires ** and recursive=True
                targets.extend(glob.glob(os.path.join(safe_path, "**", ext), recursive=True))
        else:
            for ext in extensions:
                targets.extend(glob.glob(os.path.join(safe_path, ext)))
                
    else:
        print(f"{Fore.RED}Geçersiz yol: {path}{Style.RESET_ALL}")
        return

    # Filtreleme: Zaten ".tr." (bizim ürettiğimiz) dosyaları ayırabiliriz, ama belki tekrar işletmek istiyor?
    # Şimdilik hepsini listele ama kullanıcıya sayıyı göster.
    
    targets = sorted(list(set(targets))) # Duplicate önle

    # ── [FIX] Çıktı klasörlerini hariç tut ───────────────────────────────────
    # Recursive taramada "Çevrilenler/" klasörü de taranır.
    # Oraya extract edilen geçici track dosyaları tekrar kuyruğa girmesin.
    _source_root = path if os.path.isdir(path) else os.path.dirname(path)
    _excluded_dirs = set()
    for _excl_name in ("Çevrilenler", "çevrilenler", "Translated", "translated",
                        "Output", "output", "Subs", "subs"):
        _excl_dir = os.path.normpath(os.path.join(_source_root, _excl_name)) + os.sep
        _excluded_dirs.add(_excl_dir.lower())

    def _in_excluded_dir(fp):
        fp_norm = os.path.normpath(fp).lower() + ""
        return any(fp_norm.startswith(d) for d in _excluded_dirs)

    _before_excl = len(targets)
    targets = [t for t in targets if not _in_excluded_dir(t)]
    _excl_cnt = _before_excl - len(targets)
    if _excl_cnt > 0:
        print(f"{Fore.LIGHTBLACK_EX}[!] {_excl_cnt} dosya çıktı/Çevrilenler klasöründen geldiği için hariç tutuldu.{Style.RESET_ALL}")
    # ──────────────────────────────────────────────────────────────────────────

    # CRITICAL: Zaten çevrilmiş dosyaları (.tr.ass, .tr.srt) ve yedek dosyaları (.orig.ass) listeden çıkar
    original_count = len(targets)
    targets = [t for t in targets if '.tr.' not in os.path.basename(t) and '.orig.' not in os.path.basename(t)]
    filtered_count = original_count - len(targets)

    if filtered_count > 0:
        print(f"{Fore.YELLOW}[!] {filtered_count} adet çevrilmiş/yedek dosya (.tr.* / .orig.*) filtrelendi{Style.RESET_ALL}")

    # ── [FIX] MKV'den extract edilen geçici track dosyalarını filtrele ────────
    # subtitle_tracks.py çıktı klasörüne _track*, _extracted* gibi
    # geçici dosyalar bırakır. Bunlar tekrar hedef listesine girmesin.
    #
    # ÖNEMLI: Dil-kodlu altyazılar (episode.eng.srt, show.jpn.ass) MEŞRUdur
    # ve filtrelenmemelidir — sadece bizim aracımızın ürettiği geçici
    # dosyaları tanımlayan pattern'lar kullanılır.
    #   DOĞRU filtre: _track2_, _extracted, _lang-  (bizim aracımızın çıktısı)
    #   YANLIŞ filtre: .eng.  .jpn.  — bunlar normal dil-etiketli altyazılar!
    _TRACK_PATTERNS = re.compile(
        r'_track\d+'          # _track2, _track02 vb.
        r'|_extracted'        # _extracted (bizim ffmpeg çıktımız)
        r'|_lang[_\-]'       # _lang-eng, _lang_jpn
        r'|\.track\d+\.'    # .track2.ass
        r'|\[extracted\]'    # [extracted] etiketi
        r'|_sub_\d+\.',      # _sub_0., _sub_1. (ffmpeg stream çıktısı)
        re.IGNORECASE
    )
    _before_track = len(targets)
    def _is_temp_track_file(fp):
        fn = os.path.basename(fp)
        m = _TRACK_PATTERNS.search(fn)
        if not m:
            return False
        # Eğer bu altyazı dosyasının orijinal videosu aynı dizinde varsa geçici kabul et
        match_start = m.start()
        base_part = fn[:match_start]
        if not base_part:
            return True
        dir_name = os.path.dirname(fp)
        for ext in ('.mkv', '.mp4', '.avi', '.webm', '.ts', '.m2ts', '.mov'):
            if os.path.exists(os.path.join(dir_name, base_part + ext)):
                return True
        return False
    targets = [t for t in targets if not _is_temp_track_file(t)]
    _track_cnt = _before_track - len(targets)
    if _track_cnt > 0:
        print(f"{Fore.LIGHTBLACK_EX}[!] {_track_cnt} geçici track dosyası filtrelendi.{Style.RESET_ALL}")
    # ──────────────────────────────────────────────────────────────────────────


    # Bonus/Extra dosyaları filtrele (CM, Menu, NCED, NCOP, PV, SP vb.)
    # Bunlar genellikle altyazı içermez, ffprobe ile boşa vakit harcanır
    BONUS_PREFIXES = ('cm ', 'cm-', 'cm_',
                      'menu ', 'menu-', 'menu_',
                      'nced', 'ncop', 'ncop.',
                      'pv ', 'pv-', 'pv_',
                      'sp ', 'sp-', 'sp_',
                      'preview', 'trailer', 'teaser',
                      'creditless', 'clean ')
    def _is_bonus(filepath):
        name = os.path.basename(filepath).lower()
        return any(name.startswith(p) for p in BONUS_PREFIXES)

    video_exts = ('.mkv', '.mp4', '.avi', '.webm')
    bonus_skipped = [t for t in targets if t.lower().endswith(video_exts) and _is_bonus(t)]
    if bonus_skipped:
        targets = [t for t in targets if t not in bonus_skipped]
        print(f"{Fore.LIGHTBLACK_EX}[!] {len(bonus_skipped)} bonus/extra video atlandı "
              f"(CM/Menu/NCED/NCOP/PV/SP): {', '.join(os.path.basename(b) for b in bonus_skipped[:5])}"
              f"{'...' if len(bonus_skipped) > 5 else ''}{Style.RESET_ALL}")
    
    if not targets:
        print(f"{Fore.RED}Hiç altyazı dosyası bulunamadı.{Style.RESET_ALL}")
        # auto_scan_mode'da stdin kapalı olabilir (harici çağrı / otomasyon),
        # input() EOFError fırlatır — bekleme gereksiz, direkt çık.
        return

    print(f"\n{Fore.GREEN}Bulunan Dosyalar ({len(targets)} adet):{Style.RESET_ALL}")
    for i, t in enumerate(targets[:10]):
        print(f" - {os.path.basename(t)}")
    if len(targets) > 10: print(f" ... ve {len(targets)-10} tane daha.")
    
    if not auto_scan_mode:
        print(f"\n{Fore.YELLOW}Seçili Ayarlar:{Style.RESET_ALL}")
        print(f"  Çeviri={prefs['translate']}, Temizleme={prefs['clean_sub']}, Birleştirme={prefs.get('smart_merge', True)}")
        print(f"  {Fore.CYAN}Girdi Format: OTOMATİK (SRT/ASS/VTT/SSA){Style.RESET_ALL}")
        print(f"  {Fore.GREEN}Çıktı Format: {prefs.get('sub_format', 'ASS')}{Style.RESET_ALL}")
        confirm = input(f"\n{Fore.GREEN}İşlemi başlatmak için ENTER, iptal için 'i' basın:{Style.RESET_ALL} ").strip().lower()
        if confirm == 'i':
            print("İptal edildi.")
            return
    else:
        print(f"\n{Fore.CYAN}Otomatik işlem başlıyor...{Style.RESET_ALL}")
        time.sleep(1)

    # Çıktı Klasörü Oluşturma (Organizasyon)
    # Eğer tek bir dosya seçildiyse onun bulunduğu klasöre,
    # klasör seçildiyse o klasörün içine 'Çevrilenler' açalım.
    
    source_dir = path if os.path.isdir(path) else os.path.dirname(path)
    output_dir = os.path.join(source_dir, "Çevrilenler")
    
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"{Fore.GREEN}[+] 'Çevrilenler' klasörü oluşturuldu.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}[!] Klasör oluşturma hatası: {e}{Style.RESET_ALL}")
            output_dir = source_dir  # Hata olursa kaynağa kaydet

    # ── AKILLI MODEL ÇÖZÜMLEYICI ─────────────────────────────────────────────
    # Ana çeviri (altyazı dosyası) için öncelik sırası:
    #   1. Antigravity çalışıyorsa → AG modeli kullan (öncelikli)
    #   2. AG çalışmıyorsa        → OpenRouter/Google key varsa kullan
    #   3. Her ikisi de yoksa     → mevcut ayara bak (hata verecek, kullanıcı bilgilendirilir)
    # Hazırlık işleri (termbase, glossary) → her zaman OpenRouter öncelikli,
    #   OpenRouter yoksa AG fallback (termbase_manager.py içinde ayrıca hallediliyor)
    # ──────────────────────────────────────────────────────────────────────────
    model      = prefs.get('ai_model', 'google/gemini-2.0-flash-001')
    simple_mode = prefs.get('simple_mode', True)

    def _resolve_model_for_translation(current_model: str, prefs_dict: dict) -> tuple:
        """
        Altyazı çevirisi için en iyi modeli otomatik seçer.
        Döndürür: (model_id, simple_mode, routing_info_str)
        """
        import json as _jm, os as _osm, requests as _rqm

        # translator_config.json oku
        _cfg_path = _osm.path.join(
            _osm.path.dirname(_osm.path.dirname(_osm.path.abspath(__file__))),
            'translator_config.json'
        )
        _tcfg = {}
        try:
            _tcfg = _jm.load(open(_cfg_path, encoding='utf-8'))
        except Exception:
            pass

        _ag_url = _tcfg.get('antigravity_url', 'http://localhost:8045/v1/chat/completions')
        _ag_key = _tcfg.get('antigravity_api_key', '')
        _avail  = _tcfg.get('available_models', {})
        _active = _tcfg.get('active_model_id', '')

        # ─── AG çalışıyor mu? ──────────────────────────────────────────────
        _ag_running = False
        _ag_base = _ag_url.replace('/chat/completions', '').replace('/v1', '')
        for _endpoint in [_ag_base + '/health', _ag_base + '/v1/models']:
            try:
                _r = _rqm.get(
                    _endpoint, timeout=2,
                    headers={'Authorization': f'Bearer {_ag_key}'} if _ag_key else {}
                )
                if _r.status_code in (200, 404):
                    _ag_running = True
                    break
            except Exception:
                pass

        # ─── OpenRouter'da geçerli key var mı? ───────────────────────
        _or_available = False
        try:
            from settings import KEYS_FILE as _kf2, EXHAUSTED_FILE as _ef2
            _ex2 = set()
            if _osm.path.exists(_ef2):
                _ex2 = set(l.strip() for l in open(_ef2, encoding='utf-8', errors='replace') if l.strip())
            if _osm.path.exists(_kf2):
                _all2 = [l.strip() for l in open(_kf2, encoding='utf-8', errors='replace')
                         if l.strip() and not l.startswith('#')]
                _or_available = any(k not in _ex2 for k in _all2)
        except Exception:
            pass

        # ─── Öncelik kararı ─────────────────────────────────────────────────────
        _chosen_model  = current_model
        _chosen_simple = prefs_dict.get('simple_mode', True)

        # Modelin hangi sağlayıcıya ait olduğunu tespit et
        _cur_provider = _avail.get(current_model, {}).get('provider', '')
        _cur_is_ag = (
            _cur_provider == 'antigravity'
            or current_model.startswith('AG:')
        )
        _cur_is_or = (
            _cur_provider in ('openrouter', 'google')
            or (not _cur_is_ag and '/' in current_model)
        )

        if _ag_running:
            if _cur_is_ag:
                # Kullanıcı açıkça AG model seçmiş → AG kullan
                _chosen_model  = current_model
                _chosen_simple = False
                _routing = f'ANTIGRAVITY → {current_model} (kullanıcı seçimi)'

            elif _cur_is_or:
                # Kullanıcı açıkça OpenRouter/Google model seçmiş → saygı göster
                # AG çalışsa bile kullanıcı toggle'dan OR seçmişse OR kullanılır
                _chosen_model  = current_model
                _routing = (
                    f'OPENROUTER → {current_model} '
                    f'(kullanıcı seçimi — AG çalışıyor ama OR tercih edildi)'
                )

            else:
                # Bilinmeyen / belirsiz model → AG'ye otomatik geç (eski davranış)
                _preferred = (
                    _active.replace('AG:', '') if _active else None
                ) or next(
                    (k for k, v in _avail.items()
                     if isinstance(v, dict) and v.get('provider') == 'antigravity'
                     and 'flash' in k and 'lite' not in k and 'pro' not in k),
                    next((k for k, v in _avail.items()
                          if isinstance(v, dict) and v.get('provider') == 'antigravity'), None)
                )
                if _preferred:
                    _chosen_model  = _preferred
                    _chosen_simple = False
                    _routing = f'ANTIGRAVITY → {_preferred} (otomatik - AG çalışıyor, model belirsiz)'
                else:
                    _routing = f'OPENROUTER → {current_model} (AG çalışıyor ama uygun model yok)'

        elif _or_available:
            # AG yok, OpenRouter var
            _chosen_model  = current_model
            _routing = f'OPENROUTER → {current_model} (AG çalışmıyor, OpenRouter devreye girdi)'
        else:
            # Her ikisi de yok → mevcut ayar (büyük ihtimalle hata verir)
            _routing = f'HATA → Ne AG ne OpenRouter mevcut! ({current_model})'

        return _chosen_model, _chosen_simple, _routing


    # Çözümleyiciyi çalıştır
    model, simple_mode, _routing_info = _resolve_model_for_translation(model, prefs)
    prefs['ai_model']    = model
    prefs['simple_mode'] = simple_mode

    # AG routing seçildiyse güvenli ayarları otomatik uygula
    if 'ANTIGRAVITY' in _routing_info:
        # BAN ÖNLEME: 43 hesap × 8 RPM = 344 RPM güvenli kapasite
        # Delay=2.5sn → insani görünüm, bot tespitini zorlaştırır
        if prefs.get('account_rpm_limit', 20) > 8:
            prefs['account_rpm_limit'] = 8
        if prefs.get('batch_delay_seconds', 3) < 2.0:
            prefs['batch_delay_seconds'] = 2.5

    # Translator oluştur (Advanced mode için)
    translator = None
    if not simple_mode:
        translator = SubtitleTranslator(
            model_name=model,
            nsfw_enabled=prefs.get('nsfw_mode', False),
            simple_mode=False
        )

    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    if simple_mode:
        print(f"{Fore.GREEN}[SIMPLE MODE] Basit ve stabil mod - Her dosya yeni oturum{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[SIMPLE MODE] 15 saniye dosya arasi bekleme{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}[ADVANCED MODE] Gelismis mod - Key rotation aktif{Style.RESET_ALL}")
    # Routing kararını göster
    if 'ANTIGRAVITY' in _routing_info:
        print(f"{Fore.MAGENTA}[Routing] {_routing_info}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[Routing] Hazirlik (termbase/glossary) → OpenRouter (yoksa AG fallback){Style.RESET_ALL}")
    elif 'OPENROUTER' in _routing_info:
        print(f"{Fore.CYAN}[Routing] {_routing_info}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}[Routing] {_routing_info}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")

    # ── [P1] Baslangic API Key Health Check ──────────────────────────────────
    # Gecerli key olmadan ceviri baslamadan uyar
    try:
        from settings import KEYS_FILE as _kf, EXHAUSTED_FILE as _ef
        import os as _os
        _valid_keys = []
        _exhausted_set = set()
        if _os.path.exists(_ef):
            _exhausted_set = set(l.strip() for l in open(_ef, encoding='utf-8', errors='replace') if l.strip())
        if _os.path.exists(_kf):
            _all_keys = [l.strip() for l in open(_kf, encoding='utf-8', errors='replace') if l.strip() and not l.startswith('#')]
            _valid_keys = [k for k in _all_keys if k not in _exhausted_set]
        _total = len(_valid_keys) + len(_exhausted_set)
        if _valid_keys:
            print(f"{Fore.GREEN}[Key Saglik] {len(_valid_keys)}/{_total} key gecerli{Style.RESET_ALL}")
        elif _total > 0:
            print(f"{Fore.RED}[Key Saglik] UYARI: {_total} keyden hicbiri gecerli degil! Yeni key ekleyin.{Style.RESET_ALL}")
        # Ollama/yerel modelde key gerekmez
        _is_local = any(model.startswith(p) for p in ('gemma2:', 'llama', 'mistral:', 'phi', 'qwen:', 'ollama'))
        if _is_local:
            print(f"{Fore.CYAN}[Key Saglik] Yerel model ({model}) — API key gereksiz{Style.RESET_ALL}")
    except Exception:
        pass  # Key check kritik değil, hata pipeline'i durdurmasin
    # ─────────────────────────────────────────────────────────────────────────



    # ── [P2] rich.Progress: Birden fazla dosyada gorsel ilerleme cubugu ──────────
    _rich_progress = None
    _rich_task_id  = None
    _RICH_ACTIVE   = False
    if len(targets) > 1:  # Tek dosyada progress bar gereksiz
        try:
            from rich.progress import (
                Progress, SpinnerColumn, BarColumn,
                TextColumn, TimeElapsedColumn, MofNCompleteColumn
            )
            _rich_progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold cyan]{task.description}"),
                BarColumn(bar_width=30),
                MofNCompleteColumn(),
                TextColumn("|"),
                TimeElapsedColumn(),
                transient=False,
            )
            _rich_task_id = _rich_progress.add_task(
                description="Dosyalar cevrilliyor...",
                total=len(targets)
            )
            _rich_progress.start()
            _RICH_ACTIVE = True
        except Exception:
            pass  # rich yoksa veya terminal encoding sorunu — sessizce atla

    # Isletme Dongusu
    success_count = 0
    fail_count = 0
    skipped_file_count = 0
    total_protected_lines = 0

    # ── PATF: Tüm hedef .ass dosyalarını prefs'e yaz ─────────────────────────
    # subtitle_processor.py, ilk dosyada media_title belli olunca bu listeyi
    # kullanarak tüm bölümleri önceden tarar → corpus + active_terms üretir.
    _patf_ass_files = [t for t in targets
                       if os.path.isfile(t) and
                       os.path.splitext(t)[1].lower() in ('.ass', '.ssa', '.srt')]
    if _patf_ass_files:
        prefs['_all_target_files'] = _patf_ass_files
    # ──────────────────────────────────────────────────────────────────────────


    for i, filepath in enumerate(targets):
        filename = os.path.basename(filepath)
        _t_file_start = time.time()  # Dosya sure olcumu (rapor icin)
        # Progress bar guncelle (rich aktifse)
        if _RICH_ACTIVE and _rich_progress and _rich_task_id is not None:
            _short_name = filename[:55] + '...' if len(filename) > 55 else filename
            _rich_progress.update(_rich_task_id,
                                  description=f"[bold cyan]({i+1}/{len(targets)}) {_short_name}")
        print(f"\n{Fore.MAGENTA}>>> Dosya {i+1}/{len(targets)}: {filename}{Style.RESET_ALL}")
        if i == 0:
            _play_tone('start')  # İlk dosya başlıyor — başlangıç sesi

        # ── ERKEN RESUME KONTROLÜ ────────────────────────────────────────────
        # MediaID / MAL fetch / ffprobe ÇAĞRILMADAN önce çevrilmiş mi kontrol et.
        # Hem sidecar (videonun yanı) hem Çevrilenler/ klasörü kontrol edilir.
        try:
            _er_stem     = os.path.splitext(filename)[0]
            _er_fmt      = prefs.get('sub_format', 'ASS').lower()
            _er_ext      = f'.{_er_fmt}'
            _er_vid_dir  = os.path.dirname(os.path.abspath(filepath))
            _er_out_dir  = output_dir  # Çevrilenler/

            # 1) Sidecar: video.tr.ass videoyla aynı klasörde
            _er_sidecar  = os.path.join(_er_vid_dir, f"{_er_stem}.tr{_er_ext}")
            
            # 2) Çevrilenler/: {stem}*.tr*.ass
            #    `stem` ile BAŞLAYAN her şeyi yakala:
            #    → stem.tr.ass          (basit)
            #    → stem.tr[JP-EN].ass   (tag'li)
            #    → stem_track2_eng.tr.ass  (extract suffix'li)
            _er_esc = glob.escape(_er_stem)
            _er_out_glob = (
                glob.glob(os.path.join(glob.escape(_er_out_dir), f"{_er_esc}.tr*{_er_ext}"))
                or
                glob.glob(os.path.join(glob.escape(_er_out_dir), f"{_er_esc}*.tr*{_er_ext}"))
            )

            if os.path.exists(_er_sidecar) or _er_out_glob:
                _er_found = os.path.basename(_er_sidecar) if os.path.exists(_er_sidecar) \
                            else os.path.basename(_er_out_glob[0])
                print(f"{Fore.YELLOW}   [ATLANDI] Zaten çevrilmiş → {_er_found}{Style.RESET_ALL}")
                skipped_file_count += 1
                continue
        except Exception:
            pass  # Erken kontrol hata verirse normal akışa devam et
        # ─────────────────────────────────────────────────────────────────────

        try:
            # ── MEDYA BAGLAM TESPITI ────────────────────────────────────────
            _pending_ctx  = None
            _pending_meta = None
            try:
                from media_identifier import identify_from_file, build_translation_context
                from subtitle_tracks import score_subtitle_file
                _media_meta = identify_from_file(filepath, None)
                if _media_meta:
                    # Video dosyasıysa kalite skoru atlansın (MKV/MP4 binary dosyasını text okuma!)
                    _is_video_src = filepath.lower().endswith(('.mkv', '.mp4', '.avi', '.webm', '.m2ts', '.m4v'))
                    if not _is_video_src:
                        _qscore = score_subtitle_file(filepath)
                        print(f"{Fore.CYAN}   [Kalite] Kaynak skor: {_qscore['label']} ({_qscore['score']}/100)"
                              f" | {', '.join(_qscore['reasons']) or 'temiz'}{Style.RESET_ALL}")
                    # build_translation_context: video path'i geçirme (kalite analizi skip olsun)
                    _ctx_filepath = None if _is_video_src else filepath
                    _pending_ctx  = build_translation_context(_media_meta, source_filepath=_ctx_filepath)
                    _pending_meta = _media_meta
                else:
                    print(f"{Fore.YELLOW}   [Bağlam] Medya tespit edilemedi → bağlamlı çeviri yok.{Style.RESET_ALL}")
            except ImportError:
                pass
            except Exception as _mid_err:
                print(f"{Fore.YELLOW}   [Bağlam] Medya tespiti hatası: {_mid_err}{Style.RESET_ALL}")
            # ────────────────────────────────────────────────────────────────

            # ── ViBEO: ÇOK TRACK Lİ AKIŞ ────────────────────────────────────────
            is_video = filepath.lower().endswith(('.mkv', '.mp4', '.avi', '.webm'))
            _original_video_path = filepath if is_video else None  # Sidecar için sakla
            _ref_lines         = None     # dual-source için referans satırlar
            _ref_lang          = "Japanese"
            _jp_primary_active = False    # JP birincil mod bayrağı
            if is_video:
                try:
                    from subtitle_tracks import (
                        extract_all_tracks, select_best_english,
                        select_reference, read_dialogue_lines,
                        select_signs_track, merge_ass_with_signs
                    )
                    print(f"{Fore.CYAN}   [Tracks] Tüm altyazı track'leri analiz ediliyor...{Style.RESET_ALL}")
                    all_tracks  = extract_all_tracks(filepath, output_dir,
                                                     ffprobe=_ffprobe(), ffmpeg=_ffmpeg(),
                                                     verbose=True)
                    best_en     = select_best_english(all_tracks)
                    if not best_en:
                        # İngilizce track yok — Japonca var mı? → JP Primary mod
                        jp_only = next((t for t in all_tracks if getattr(t, 'is_japanese', False) and t.extracted_path), None)
                        if jp_only:
                            filepath = jp_only.extracted_path
                            filename = os.path.basename(filepath)
                            _jp_primary_active = True
                            print(f"{Fore.CYAN}   [JP-DIRECT] İngilizce track yok — Japonca birincil mod: "
                                  f"Track#{jp_only.index}{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}   [ATLANDI] Kullanılabilir İngilizce veya Japonca track bulunamadı.{Style.RESET_ALL}")
                            skipped_file_count += 1
                            continue
                    else:
                        filepath = best_en.extracted_path
                        filename = os.path.basename(filepath)
                        # Kalite skoru: MKV değil, extracted ASS dosyasından (doğru ve hızlı)
                        _qscore = score_subtitle_file(filepath)
                        print(f"{Fore.GREEN}   [SEÇİLDİ] En iyi İngilizce: Track#{best_en.index} "
                              f"| {best_en.quality_label} ({best_en.quality_score}/100){Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   [Kalite] Kaynak skor: {_qscore['label']} ({_qscore['score']}/100)"
                              f" | {', '.join(_qscore['reasons']) or 'temiz'}{Style.RESET_ALL}")
                        # Context'i gerçek subtitle kalitesiyle yenile (video path'i değil)
                        if _pending_meta:
                            _pending_ctx = build_translation_context(_pending_meta, source_filepath=filepath)

                        # Kalite düşükse Japonca referans çek
                        ref_track = select_reference(all_tracks, best_en, quality_threshold=65)
                        if ref_track:
                            _ref_lines = read_dialogue_lines(ref_track.extracted_path)
                            _ref_lang  = "Japanese" if ref_track.is_japanese else ref_track.language.upper()
                            print(f"{Fore.CYAN}   [Ref] Referans track: Track#{ref_track.index} "
                                  f"lang={ref_track.language!r} ({len(_ref_lines)} satır) "
                                  f"→ Çift-kaynaklı çeviri aktif{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.GREEN}   [Ref] İngilizce kalitesi yeterli → tek kaynak çeviri.{Style.RESET_ALL}")

                        # Signs track varsa merge et
                        signs_track = select_signs_track(all_tracks)
                        if signs_track and signs_track.extracted_path:
                            import tempfile, shutil as _shutil2
                            _merged_path = filepath + ".merged_signs.ass"
                            ok_merge = merge_ass_with_signs(filepath, signs_track.extracted_path, _merged_path)
                            if ok_merge:
                                filepath = _merged_path
                                filename = os.path.basename(filepath)
                                print(f"{Fore.GREEN}   [Signs] Signs track merge edildi: Track#{signs_track.index} "
                                      f"→ ekran yazıları da çevrilecek{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.YELLOW}   [Signs] Merge başarısız — sadece diyalog çevrilecek{Style.RESET_ALL}")

                except ImportError:
                    # subtitle_tracks.py yoksa eski yöntemle devam et
                    extracted_sub = extract_subtitles_from_video(filepath, output_dir)
                    if not extracted_sub:
                        skipped_file_count += 1
                        continue
                    filepath = extracted_sub
                    filename = os.path.basename(filepath)
                except Exception as _te:
                    print(f"{Fore.RED}   [!] Track analiz hatası: {_te}{Style.RESET_ALL}")
                    skipped_file_count += 1
                    continue
            # ─────────────────────────────────────────

            # Hedef yol belirleme
            base, ext = os.path.splitext(filename)

            # Kullanıcının seçtiği çıktı formatını al
            output_format = prefs.get('sub_format', 'ASS').lower()

            # Format uzantısını belirle
            if output_format == 'all':
                target_ext = ext.lower()
            else:
                target_ext = f'.{output_format}'

            # Kaynak dil etiketi: hangi kaynaklardan çevrildi?
            if _jp_primary_active and _ref_lines:
                _src_tag = "[JP-EN]"   # Japonca birincil + İngilizce referans
            elif _jp_primary_active:
                _src_tag = "[JP]"      # Sadece Japonca
            elif _ref_lines:
                _src_tag = "[JP-EN]"   # İngilizce + Japonca referans (dual-source)
            else:
                _src_tag = ""          # Normal tek kaynak → ek etiket yok

            new_filename = f"{base}.tr{_src_tag}{target_ext}"
            out_path = os.path.join(output_dir, new_filename)
            
            # RESUME KONTROLÜ
            if os.path.exists(out_path):
                print(f"{Fore.YELLOW}   [ATLANDI] Bu dosya zaten çevrilmiş: {new_filename}{Style.RESET_ALL}")
                skipped_file_count += 1
                continue
            
            if simple_mode:
                # Her dosya için yeni translator — key listesi dosyadan taze yüklenir
                _is_ag_model = any(
                    model == k or model.startswith("AG:")
                    for k in _get_ag_models()
                ) if callable(_get_ag_models := lambda: __import__('json').load(
                    open(__import__('os').path.join(
                        __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))),
                        'translator_config.json'), encoding='utf-8')
                ).get('available_models', {})) else False

                if _is_ag_model:
                    print(f"{Fore.MAGENTA}╔══════════════════════════════════════════════════╗{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}║  ⚡ HYBRID API ROUTING AKTIF                     ║{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}║  ├─ Ön-çeviri (Termbase) → OpenRouter/Google    ║{Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}║  └─ Altyazı Çevirisi     → Antigravity ({model[:20]:<20}){Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}╚══════════════════════════════════════════════════╝{Style.RESET_ALL}")
                else:
                    print(f"{Fore.CYAN}[SIMPLE MODE] Yeni translator oluşturuluyor: {model}{Style.RESET_ALL}")

                # Create new translator with fresh key list
                translator = SubtitleTranslator(
                    model_name=model,
                    nsfw_enabled=prefs.get('nsfw_mode', False),
                    simple_mode=True  # CRITICAL: Must be True!
                )
                # Translator's KeyManager will reload keys from file in __init__

            # -- MEDYA CONTEXT UYGULA (translator artik hazir) --
            if translator is not None:
                try:
                    if _pending_ctx:
                        translator.set_media_context(_pending_ctx)
                        if _pending_meta:
                            _s    = _pending_meta.get('season')
                            _e    = _pending_meta.get('episode')
                            _pt   = _pending_meta.get('part')
                            _ep_tag   = f" | S{_s:02d}E{_e:02d}" if _s and _e else ""
                            _part_tag = f" | Part {_pt}" if _pt and _pt >= 2 else ""
                            print(
                                f"{Fore.GREEN}   [Bagiam] {_pending_meta.get('title', '?')} "
                                f"| {', '.join((_pending_meta.get('genres') or [])[:3]) or 'N/A'} "
                                f"| Kaynak: {_pending_meta.get('source', '?')}"
                                f"{_ep_tag}{_part_tag}{Style.RESET_ALL}"
                            )
                    else:
                        translator.clear_media_context()

                    # Çift-kaynaklı çeviri: referans satırları ve JP mod set et
                    if _jp_primary_active:
                        translator.set_jp_primary_mode(True)
                        if _ref_lines:
                            # JP primary + EN referans (dual)
                            translator.set_reference_lines(_ref_lines, lang="English")
                            print(f"{Fore.CYAN}   [JP-PRIMARY] Japonca birincil + EN referans aktif{Style.RESET_ALL}")
                        else:
                            translator.clear_reference_lines()
                            print(f"{Fore.CYAN}   [JP-PRIMARY] Japonca birincil mod (referanssiz){Style.RESET_ALL}")
                    elif _ref_lines:
                        translator.clear_jp_primary_mode()
                        translator.set_reference_lines(_ref_lines, lang=_ref_lang)
                        print(f"{Fore.CYAN}   [Dual] {_ref_lang} referansı {len(_ref_lines)} satır → translator'a yüklendi.{Style.RESET_ALL}")
                    else:
                        translator.clear_jp_primary_mode()
                        translator.clear_reference_lines()

                except Exception as _ctx_err:
                    print(f"{Fore.YELLOW}   [Bagiam] Context uygulanamadi: {_ctx_err}{Style.RESET_ALL}")


            # -- ANA CEVIRI CAGRISI --
            # Media başlığını, sezon ve bölüm numarasını prefs'e geçici olarak enjekte et.
            # subtitle_processor.py: glossary raporu, episode_context kayıt/yükleme için kullanır.
            if _pending_meta and _pending_meta.get('title'):
                prefs['media_title'] = _pending_meta['title']
                # Romaji/JP başlık varsa alternatif olarak sakla — glossary AniList sorgusu için
                _title_jp = _pending_meta.get('title_jp') or ''
                if _title_jp and not any(ord(c) > 0x2E7F for c in _title_jp):  # Japonca karakter yoksa (romaji)
                    prefs['media_title_alt'] = _title_jp
                elif 'media_title_alt' in prefs:
                    del prefs['media_title_alt']
                # ── media_type / known_type → Jikan skip için KRİTİK ──────────────
                # 'series' (Batı dizisi) → fandom_glossary + termbase_manager Jikan'ı ATLAR
                _mtype = (_pending_meta.get('media_type') or
                          _pending_meta.get('resolved_media_type') or
                          _pending_meta.get('ai_media_type') or '')
                _ktype = _pending_meta.get('known_type') or _mtype
                if _mtype:
                    prefs['media_type']  = _mtype
                    prefs['known_type']  = _ktype
                elif 'media_type' in prefs:
                    del prefs['media_type']
                # ─────────────────────────────────────────────────────────────────
                # Karakterleri de enjekte et (TVMaze/TMDB'den gelen — Glossary fallback için)
                _meta_chars = _pending_meta.get('characters') or []
                if _meta_chars:
                    prefs['media_characters'] = _meta_chars
                elif 'media_characters' in prefs:
                    del prefs['media_characters']
                # Sezon ve bölüm numarasını da enjekte et (episode_context için kritik!)
                _ep_val = _pending_meta.get('episode')
                _sea_val = _pending_meta.get('season')
                if _ep_val is not None:
                    prefs['episode'] = _ep_val
                elif 'episode' in prefs:
                    del prefs['episode']
                if _sea_val is not None:
                    prefs['season'] = _sea_val
                elif 'season' in prefs:
                    del prefs['season']
            else:
                # Önceki dosyadan kalmasın
                for _k in ('media_title', 'episode', 'season', '_fandom_terms_set',
                           'media_characters', 'media_type', 'known_type'):
                    prefs.pop(_k, None)


            result = process_and_replace_subtitle(
                filepath=filepath,
                prefs=prefs,
                translator=translator,
                output_path=out_path,
            )

            if isinstance(result, dict):
                if result.get("success"):
                    success_count += 1
                    prot = result.get("skipped", 0)
                    total_protected_lines += prot
                    print(f"{Fore.CYAN}   -> Istatistik: {result.get('translated')} Cevirildi, {prot} Korundu.{Style.RESET_ALL}")
                    print("[SOUND:file_done]")   # GUI bu satırı okuyunca sesi çalar
                    _play_tone('file_done')       # Subprocess’tan da çal (yedek)

                    # ── [P1] HTML Raporu Kaydet ─────────────────────────────────────
                    try:
                        from translation_report import get_report
                        _rpt = get_report()
                        if _rpt and not _rpt.finalized:
                            import time as _time
                            _rpt.finalize(
                                output_file=out_path,
                                duration_sec=_time.time() - _t_file_start if '_t_file_start' in dir() else 0,
                                mode=('JP' if _jp_primary_active else 'JP-EN' if _ref_lines else 'EN'),
                                series_title=(_pending_meta.get('title') if _pending_meta else ''),
                            )
                            _rpt_path = _rpt.save()
                            if _rpt_path:
                                print(f"{Fore.LIGHTBLACK_EX}   [Rapor] HTML rapor kaydedildi: {os.path.basename(_rpt_path)}{Style.RESET_ALL}")
                    except Exception as _re:
                        pass  # Rapor hatasi ceviriyi durdurmasin
                    # ────────────────────────────────────────────────────────────────

                    # ── Video Sidecar: Videonun yanina kopyala ─────────────────
                    if _original_video_path and os.path.exists(out_path):
                        try:
                            import shutil as _shutil
                            _vid_stem = os.path.splitext(os.path.basename(_original_video_path))[0]
                            _vid_dir  = os.path.dirname(_original_video_path)
                            _sc_ext   = os.path.splitext(out_path)[1]  # .ass / .srt
                            _sidecar  = os.path.join(_vid_dir, f"{_vid_stem}.tr{_sc_ext}")
                            _shutil.copy2(out_path, _sidecar)
                            print(f"{Fore.GREEN}   [Sidecar] Video yanına kopyalandı: {os.path.basename(_sidecar)}{Style.RESET_ALL}")
                        except Exception as _se:
                            print(f"{Fore.YELLOW}   [Sidecar] Kopyalama hatası: {_se}{Style.RESET_ALL}")
                    # ────────────────────────────────────────────────────────────────

                elif result.get("error"):
                    print(f"{Fore.RED}   [!] Hata: {result.get('error')}{Style.RESET_ALL}")
                    fail_count += 1
                    print("[SOUND:error]")     # GUI bu satırı okuyunca sesi çalar
                    _play_tone('error')         # Subprocess’tan da çal (yedek)
                else:
                    fail_count += 1
                    print("[SOUND:error]")     # GUI bu satırı okuyunca sesi çalar
                    _play_tone('error')         # Subprocess’tan da çal (yedek)
            elif result:
                success_count += 1

                # ── [NEW] Video Sidecar (basit mod / bool result) ────────────────
                if _original_video_path and os.path.exists(out_path):
                    try:
                        import shutil as _shutil
                        _vid_stem = os.path.splitext(os.path.basename(_original_video_path))[0]
                        _vid_dir  = os.path.dirname(_original_video_path)
                        _sc_ext   = os.path.splitext(out_path)[1]
                        _sidecar  = os.path.join(_vid_dir, f"{_vid_stem}.tr{_sc_ext}")
                        _shutil.copy2(out_path, _sidecar)
                        print(f"{Fore.GREEN}   [Sidecar] Video yanına kopyalandı: {os.path.basename(_sidecar)}{Style.RESET_ALL}")
                    except Exception as _se:
                        print(f"{Fore.YELLOW}   [Sidecar] Kopyalama hatası: {_se}{Style.RESET_ALL}")
                # ────────────────────────────────────────────────────────────────

            else:
                fail_count += 1
            
            # Dosya arası bekleme (API koruması)
            if i < len(targets) - 1:  # Son dosyadan sonra bekleme yok
                delay = prefs.get('per_file_delay', 15)
                if delay > 0:
                    print(f"\n{Fore.YELLOW}[API Koruması] {delay} saniye bekleniyor...{Style.RESET_ALL}")
                    for remaining in range(delay, 0, -1):
                        print(f"   {remaining} saniye kaldı...", end='\r')
                        time.sleep(1)
                    print(f"   ✓ Bekleme tamamlandı!{' '*30}")
                
        except Exception as e:
            import traceback
            print(f"{Fore.RED}Dosya hatası: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}--- HATA DETAYI ---{Style.RESET_ALL}")
            traceback.print_exc()
            print(f"{Fore.YELLOW}--- HATA DETAYI SONU ---{Style.RESET_ALL}")
            fail_count += 1
            _play_tone('error')  # Beklenmedik hata sesi
            # ── Hata sonrası bozuk çıktı dosyasını temizle ──────────────────
            # Exception fırlatıldığında yarım yazılmış .tr.ass kalabilir
            try:
                if 'out_path' in dir() and out_path and os.path.exists(out_path):
                    # Dosya boyutu 0 veya çok küçük ise bozuk kabul et
                    if os.path.getsize(out_path) < 512:
                        os.remove(out_path)
                        print(f"{Fore.YELLOW}   [Temizlik] Bozuk/eksik çıktı dosyası silindi: "
                              f"{os.path.basename(out_path)}{Style.RESET_ALL}")
            except Exception:
                pass  # Temizlik basarisiz olursa sessizce devam

        finally:
            # [P2] Memory leak korumasi: her dosyadan sonra translator temizle
            # Simple modda her dosya icin yeni SubtitleTranslator olusturuluyor,
            # requests.Session kapatilmazsa memory leak olur.
            if simple_mode and translator is not None:
                try:
                    # httpx persistent session'i kapat (FD leak onle)
                    if hasattr(translator, '_http') and translator._http is not None:
                        try: translator._http.close()
                        except Exception: pass
                    import gc
                    del translator
                    translator = None
                    gc.collect()
                except Exception:
                    pass
            # rich progress: dosya tamamlandi, adim ilerlet
            if _RICH_ACTIVE and _rich_progress and _rich_task_id is not None:
                try:
                    _rich_progress.advance(_rich_task_id)
                except Exception:
                    pass

    # rich progress bitince durdur
    if _RICH_ACTIVE and _rich_progress:
        try:
            _rich_progress.stop()
        except Exception:
            pass

    print(f"\n{Fore.GREEN}Tamamlandi!{Style.RESET_ALL}")
    print(f"Basarili Dosya: {success_count}, Hatali: {fail_count}, Atlanan (Zaten Var): {skipped_file_count}")
    _play_tone('all_done')  # Tüm işlem bitti — fanfar
    if total_protected_lines > 0:
        print(f"{Fore.YELLOW}Toplam Korunan Satır (Romaji/Efekt): {total_protected_lines}{Style.RESET_ALL}")
    
    if success_count > 0:
        print(f"{Fore.CYAN}Çeviriler şuraya kaydedildi: {output_dir}{Style.RESET_ALL}")
        
    try:
        input("Devam etmek için ENTER...")
    except (EOFError, KeyboardInterrupt):
        pass  # GUI / pipe modunda stdin yok — sessizce devam

# ----------------- MENÜLER -----------------

def configure_preferences(prefs):
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}=== TERCİHLER / AYARLAR ==={Style.RESET_ALL}")
        
        on_off = lambda x: f"{Fore.GREEN}AÇIK{Style.RESET_ALL}" if x else f"{Fore.RED}KAPALI{Style.RESET_ALL}"
        
        print(f"1. AI Çeviri Yap: {on_off(prefs['translate'])}")
        print(f"2. Altyazı Temizliği (Clean Sub): {on_off(prefs['clean_sub'])}")
        print(f"3. Akıllı Birleştirme (Smart Merge): {on_off(prefs.get('smart_merge', True))}")
        print(f"4. Çıktı Formatı: {Fore.YELLOW}{prefs.get('sub_format', 'ASS')}{Style.RESET_ALL}")
        print(f"5. Model Seçimi (Şu an: {prefs.get('ai_model')})")
        print(f"6. {Fore.MAGENTA}+18 HENTAI MODU (Argoyu Aç): {on_off(prefs.get('nsfw_mode', False))}{Style.RESET_ALL}")
        print(f"7. {Fore.CYAN}DOĞAL TÜRKÇE DİYALOG: {on_off(prefs.get('natural_dialogue', True))}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(Anime/Hentai için){Style.RESET_ALL}")
        print(f"8. {Fore.YELLOW}Hentai Sözlüğü (120+ Terim): {on_off(prefs.get('hentai_glossary', False))}{Style.RESET_ALL}")
        print(f"\n{Fore.LIGHTBLACK_EX}--- Gelişmiş Çeviri Ayarları (Subtitle Edit Std) ---{Style.RESET_ALL}")
        print(f"A. Kaynak Dil: {Fore.CYAN}{prefs.get('source_lang', 'English')}{Style.RESET_ALL}")
        print(f"B. Hedef Dil: {Fore.CYAN}{prefs.get('target_lang', 'Turkish')}{Style.RESET_ALL}")
        print(f"C. Gecikme (sn): {Fore.CYAN}{prefs.get('delay_sn', 0)}{Style.RESET_ALL}")
        print(f"D. Max Byte/Batch: {Fore.CYAN}{prefs.get('max_byte_batch', 2000)}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(Byte bazlı batch limiti){Style.RESET_ALL}")
        print(f"E. Dosya Arası Bekleme: {Fore.CYAN}{prefs.get('per_file_delay', 5)} sn{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(Subtitle Edit Std: 5){Style.RESET_ALL}")
        print(f"F. Sadece İngilizce: {on_off(prefs.get('only_english', True))}")
        print(f"G. Max Satır Uzunluğu: {Fore.CYAN}{prefs.get('max_line_length', 75)}{Style.RESET_ALL}")
        print(f"H. Satır Birleştirme: {Fore.CYAN}{prefs.get('line_merge_mode', 'default')}{Style.RESET_ALL}")
        print(f"I. Zorla Çevir (No Cache): {on_off(prefs.get('force_translate', True))} {Fore.LIGHTBLACK_EX}(Her seferinde yeniden çevirip){Style.RESET_ALL}")
        print(f"J. Konumlandırma/Karaoke Koruması: {on_off(prefs.get('protect_positioning', True))} {Fore.LIGHTBLACK_EX}(AÇIK=Koru ve Çevir, KAPALI=Sil){Style.RESET_ALL}")
        print(f"\n{Fore.LIGHTBLACK_EX}--- Font Boyutu Ayarları ---{Style.RESET_ALL}")
        
        font_mode = prefs.get('font_size_mode', 'normalize')
        font_mode_display = {
            'preserve': f'{Fore.YELLOW}ORJİNAL BOYUTU KORU{Style.RESET_ALL}',
            'normalize': f'{Fore.GREEN}OTOMATİK NORMALLEŞTİR (Min: 80){Style.RESET_ALL}',
            'custom': f'{Fore.CYAN}ÖZEL BOYUT ({prefs.get("custom_font_size", 80)}){Style.RESET_ALL}'
        }
        print(f"K. Font Boyutu Modu: {font_mode_display.get(font_mode, font_mode)}")
        
        if font_mode == 'custom':
            print(f"L. Özel Font Boyutu: {Fore.CYAN}{prefs.get('custom_font_size', 80)}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(30-150 arası){Style.RESET_ALL}")
        
        print(f"\n{Fore.LIGHTBLACK_EX}--- Algılama Motoru Ayarları ---{Style.RESET_ALL}")
        print(f"R. {Fore.CYAN}Romaji Filtreleme (skip_romaji_mode): {on_off(prefs.get('skip_romaji_mode', True))}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(AÇIK=Romaji satirlari iceriger tespiti ile filtrele){Style.RESET_ALL}")
        print(f"S. {Fore.YELLOW}Stil Adi Zorlamayi Kapat (force_no_style): {on_off(prefs.get('force_no_style', False))}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(AÇIK=Stil adina bakma, sadece icerik analiz){Style.RESET_ALL}")
        print(f"T. {Fore.GREEN}Icerik Dedektoru (content_detect): {on_off(prefs.get('content_detect', True))}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(AÇIK=content_detector kullan, KAPALI=eski sistem){Style.RESET_ALL}")
        print(f"P. {Fore.YELLOW}CPS Kısaltma (cps_shorten): {on_off(prefs.get('cps_shorten', False))}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}(AÇIK=Çok hızlı satırları API ile kısalt, KAPALI=Hızlı mod){Style.RESET_ALL}")
        print("\n9. Geri Dön")
        
        choice = input(f"\n{Fore.YELLOW}Seçiminiz: {Style.RESET_ALL}").strip().lower()
        
        if choice == '9': break
        
        elif choice == 'r':
            prefs['skip_romaji_mode'] = not prefs.get('skip_romaji_mode', True)
            state = 'AÇIK' if prefs['skip_romaji_mode'] else 'KAPALI'
            print(f"{Fore.CYAN}>>> Romaji Filtreleme {state}.{Style.RESET_ALL}")
            time.sleep(1)
        elif choice == 's':
            prefs['force_no_style'] = not prefs.get('force_no_style', False)
            if prefs['force_no_style']:
                print(f"{Fore.YELLOW}>>> Stil Adı Zorlaması KAPALI: Sadece içerik analizi kullanılacak.{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}>>> Stil Adı Zorlaması AÇIK: Normal stil + içerik analizi.{Style.RESET_ALL}")
            time.sleep(1)
        elif choice == 't':
            prefs['content_detect'] = not prefs.get('content_detect', True)
            if prefs['content_detect']:
                print(f"{Fore.GREEN}>>> İçerik Dedektörü AÇIK: content_detector.py aktif.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}>>> İçerik Dedektörü KAPALI: Eski stil-adı tabanlı sistem kullanılacak.{Style.RESET_ALL}")
            time.sleep(1)
        elif choice == 'p':
            prefs['cps_shorten'] = not prefs.get('cps_shorten', False)
            if prefs['cps_shorten']:
                print(f"{Fore.YELLOW}>>> CPS Kısaltma AÇIK: Çok hızlı satırlar için ekstra API isteği yapılacak (yavaşlama olabilir).{Style.RESET_ALL}")
            else:
                print(f"{Fore.GREEN}>>> CPS Kısaltma KAPALI: Hızlı mod aktif.{Style.RESET_ALL}")
            time.sleep(1)

        elif choice == '1':
            prefs['translate'] = not prefs['translate']
        elif choice == '2':
            prefs['clean_sub'] = not prefs['clean_sub']
        elif choice == '3':
            prefs['smart_merge'] = not prefs.get('smart_merge', True)
        elif choice == '4':
            formats = ['ASS', 'SRT', 'VTT', 'ALL']
            try:
                current_idx = formats.index(prefs.get('sub_format', 'ASS'))
            except: current_idx = 0
            
            new_idx = (current_idx + 1) % len(formats)
            prefs['sub_format'] = formats[new_idx]
        elif choice == '6':
            prefs['nsfw_mode'] = not prefs.get('nsfw_mode', False)
            if prefs['nsfw_mode']:
                print(f"{Fore.MAGENTA}>>> +18 MODU AÇILDI: Argo ve NSFW terimler kullanılacak!{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}>>> +18 MODU KAPATILDI: Temiz çeviri yapılacak.{Style.RESET_ALL}")
            time.sleep(1)
            
        elif choice == '7':
            prefs['natural_dialogue'] = not prefs.get('natural_dialogue', True)
            if prefs['natural_dialogue']:
                print(f"{Fore.GREEN}>>> DOĞAL DİYALOG AÇILDI: Anime/Hentai diline uygun çeviri yapılacak!{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}>>> DOĞAL DİYALOG KAPATILDI: Literal çeviri yapılacak.{Style.RESET_ALL}")
            time.sleep(1)
            
        elif choice == '8':
            prefs['hentai_glossary'] = not prefs.get('hentai_glossary', False)
            if prefs['hentai_glossary']:
                print(f"{Fore.MAGENTA}>>> HENTAI SÖZLÜĞÜ AÇILDI: 120+ özel terim kullanılacak!{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}>>> HENTAI SÖZLÜĞÜ KAPATILDI.{Style.RESET_ALL}")
            time.sleep(1)
            
        elif choice == '5':
             # Model seçimi için mevcut configure_ai_api fonksiyonuna yönlendirebiliriz, 
             # ama burada basitçe api menüsüne gitmesi gerektiğini söyleyelim veya orayı çağıralım.
             # Döngüsel bağımlılık olmaması için ana menüden gidilmesi daha iyi.
             print("Model değişimi için Ana Menü -> 2. AI ve API Ayarları kısmını kullanın.")
             time.sleep(2)
        
        # Gelişmiş Ayarlar
        elif choice == 'a':
            langs = ['English', 'Japanese', 'Chinese', 'Korean', 'Spanish', 'French', 'German']
            print(f"\nMevcut Diller: {', '.join(langs)}")
            new_lang = input("Yeni Kaynak Dil (İptal=ENTER): ").strip()
            if new_lang and new_lang in langs:
                prefs['source_lang'] = new_lang
        elif choice == 'b':
            langs = ['Turkish', 'English', 'Japanese', 'Chinese', 'Korean', 'Spanish', 'French', 'German']
            print(f"\nMevcut Diller: {', '.join(langs)}")
            new_lang = input("Yeni Hedef Dil (İptal=ENTER): ").strip()
            if new_lang and new_lang in langs:
                prefs['target_lang'] = new_lang
        elif choice == 'c':
            try:
                val = int(input("Gecikme (0-10 saniye): "))
                if 0 <= val <= 10:
                    prefs['delay_sn'] = val
            except: pass
        elif choice == 'd':
            try:
                val = int(input("Max Byte/Batch (500-5000): "))
                if 500 <= val <= 5000:
                    prefs['max_byte_batch'] = val
                    print(f"{Fore.GREEN}>>> Max Byte/Batch {val} olarak ayarlandı.{Style.RESET_ALL}")
                    time.sleep(1)
                else:
                    print(f"{Fore.RED}Geçersiz değer! 500-5000 arası olmalı.{Style.RESET_ALL}")
                    time.sleep(1)
            except:
                print(f"{Fore.RED}Geçersiz giriş!{Style.RESET_ALL}")
                time.sleep(1)
        elif choice == 'e':
            try:
                val = float(input("Dosya Arası Bekleme (0-120 saniye): "))
                if 0 <= val <= 120:
                    prefs['per_file_delay'] = val
                    hint = " (API rate limit koruması için önerilir: 15-30s)" if val < 10 else ""
                    print(f"{Fore.GREEN}>>> Dosya arası bekleme {val} saniye olarak ayarlandı.{hint}{Style.RESET_ALL}")
                    time.sleep(1)
                else:
                    print(f"{Fore.RED}Geçersiz değer! 0-120 arası olmalı.{Style.RESET_ALL}")
                    time.sleep(1)
            except:
                print(f"{Fore.RED}Geçersiz giriş!{Style.RESET_ALL}")
                time.sleep(1)
        elif choice == 'f':
            prefs['only_english'] = not prefs.get('only_english', True)
        elif choice == 'g':
            try:
                val = int(input("Max Satır Uzunluğu (30-150): "))
                if 30 <= val <= 150:
                    prefs['max_line_length'] = val
            except: pass
        elif choice == 'h':
            modes = ['default', 'aggressive', 'conservative', 'none']
            print(f"\nMevcut Modlar: {', '.join(modes)}")
            new_mode = input("Yeni Mod (İptal=ENTER): ").strip()
            if new_mode and new_mode in modes:
                prefs['line_merge_mode'] = new_mode
        elif choice == 'i':
            prefs['force_translate'] = not prefs.get('force_translate', True)
        elif choice == 'j':
            prefs['protect_positioning'] = not prefs.get('protect_positioning', True)
        elif choice == 'k':
            # Font boyutu modunu değiştir (preserve -> normalize -> custom -> preserve)
            modes = ['preserve', 'normalize', 'custom']
            current_mode = prefs.get('font_size_mode', 'normalize')
            try:
                current_idx = modes.index(current_mode)
                next_idx = (current_idx + 1) % len(modes)
                prefs['font_size_mode'] = modes[next_idx]
            except ValueError:
                prefs['font_size_mode'] = 'normalize'
            
            mode_names = {
                'preserve': 'ORJİNAL BOYUTU KORU',
                'normalize': 'OTOMATİK NORMALLEŞTİR',
                'custom': 'ÖZEL BOYUT'
            }
            print(f"{Fore.GREEN}>>> Font Boyutu Modu: {mode_names[prefs['font_size_mode']]}{Style.RESET_ALL}")
            time.sleep(1)
        elif choice == 'l':
            # Özel font boyutu ayarla
            if prefs.get('font_size_mode') == 'custom':
                try:
                    val = int(input("Özel Font Boyutu (30-150): "))
                    if 30 <= val <= 150:
                        prefs['custom_font_size'] = val
                        print(f"{Fore.GREEN}>>> Font boyutu {val} olarak ayarlandı.{Style.RESET_ALL}")
                        time.sleep(1)
                    else:
                        print(f"{Fore.RED}Geçersiz değer! 30-150 arası olmalı.{Style.RESET_ALL}")
                        time.sleep(1)
                except:
                    print(f"{Fore.RED}Geçersiz giriş!{Style.RESET_ALL}")
                    time.sleep(1)
            else:
                print(f"{Fore.YELLOW}Bu seçenek sadece 'ÖZEL BOYUT' modunda kullanılabilir.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Önce 'J' tuşu ile modu 'ÖZEL BOYUT' olarak değiştirin.{Style.RESET_ALL}")
                time.sleep(2)
             
        save_prefs(prefs)

def check_ollama_status(base_url="http://localhost:11434"):
    print(f"\n{Fore.CYAN}--- Ollama Diagnostik ---{Style.RESET_ALL}")
    try:
        # 1. Check Root
        resp = requests.get(base_url, timeout=2)
        if resp.status_code == 200:
            print(f"{Fore.GREEN}[OK] Ollama Servisi Çalışıyor.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[!] Ollama Servisine ulaşıldı ama hata döndü: {resp.status_code}{Style.RESET_ALL}")
            
        # 2. List Models
        tags_url = f"{base_url}/api/tags"
        resp = requests.get(tags_url, timeout=5)
        if resp.status_code == 200:
            models_data = resp.json()
            models = [m['name'] for m in models_data.get('models', [])]
            return models
        else:
            print(f"{Fore.RED}[!] Model listesi alınamadı (api/tags failed): {resp.status_code}{Style.RESET_ALL}")
            return []
            
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}[CRITICAL] Ollama servisine BAĞLANILAMADI! (Connection Refused){Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Çözüm: Ollama uygulamasının açık olduğundan emin olun.{Style.RESET_ALL}")
        return None
    except Exception as e:
        print(f"{Fore.RED}[!] Beklenmedik Hata: {e}{Style.RESET_ALL}")
        return None

def manual_test_mode(prefs):
    print(f"\n{Fore.MAGENTA}--- Manuel Test Modu (Single Line) ---{Style.RESET_ALL}")
    
    current_model = prefs.get('ai_model', '')
    # Ollama'yi sadece yerel model seciliyse kontrol et (cloud modelde gereksiz)
    _is_local_model = any(current_model.startswith(p) for p in ('gemma2:', 'llama', 'mistral:', 'phi', 'qwen:', 'ollama'))
    installed_models = check_ollama_status() if _is_local_model else []
    
    if "local" in current_model or "qwen" in current_model or "llama" in current_model:
        if installed_models is not None:
             found = False
             for im in installed_models:
                 if current_model in im or im in current_model: # Loose match
                     found = True
             if not found:
                 print(f"{Fore.RED}[!] UYARI: Config'deki '{current_model}' yerel Ollama'da bulunamadı!{Style.RESET_ALL}")
                 print(f"Yüklü Modeller: {installed_models}")
    
    try:
        from translator import SubtitleTranslator
        translator = SubtitleTranslator() # Config otomatik yüklenir
        print(f"{Fore.GREEN}Translator Hazır.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Translator başlatılamadı: {e}{Style.RESET_ALL}")
        return

    print("Çıkmak için 'q' veya 'exit' yazın.")
    while True:
        text = input(f"\n{Fore.BLUE}Test Metni (EN): {Style.RESET_ALL}")
        if text.lower() in ['q', 'exit']: break
        if not text.strip(): continue
        
        start_t = time.time()
        try:
            res = translator.translate_single_line(text)
            elapsed = time.time() - start_t
            print(f"{Fore.GREEN}TR ({elapsed:.2f}s): {Style.RESET_ALL}{res}")
        except Exception as e:
            print(f"{Fore.RED}HATA: {e}{Style.RESET_ALL}")

def get_api_stats():
    # Basit istatistik okuma (utils veya translator dosyasından da çekilebilirdi ama manuel okuyalım)
    try:
        api_file = os.path.join(os.path.dirname(__file__), '..', "api_keys.txt")
        if os.path.exists(api_file):
             with open(api_file, 'r', encoding='utf-8') as f:
                 count = len([x for x in f if x.strip() and not x.startswith('#')])
             return f"{count} Anahtar Mevcut"
    except: pass
    return "Bilinmiyor"

def configure_ai_api(prefs):
    """AI Modeli ve API Anahtarları Yönetim Menüsü"""
    # Bu fonksiyon orijinal dosyadaki gibi kalabilir, ancak importları düzenlememiz gerek.
    # Kod tekrarını önlemek için basitleştirilmiş bir versiyon:
    
    API_FILE = os.path.join(os.path.dirname(__file__), '..', "api_keys.txt")
    MODELS = [
        "google/gemini-2.0-flash-001",
        "google/gemini-flash-1.5-8b",
        "deepseek/deepseek-r1",
        "microsoft/phi-4",
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet"
    ]

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.MAGENTA}=== AI ve API YÖNETİMİ ==={Style.RESET_ALL}")
        print(f"Seçili Model: {Fore.GREEN}{prefs.get('ai_model')}{Style.RESET_ALL}")
        
        current_keys = prefs.get('custom_api_keys_path')
        keys_display = current_keys if current_keys else "Varsayılan (api_keys.txt)"
        print(f"Anahtar Dosyası: {Fore.YELLOW}{keys_display}{Style.RESET_ALL}")
        
        print("-" * 30)
        print("1. Model Değiştir")
        print("2. Yeni API Anahtarı Ekle (Mevcut Dosyaya)")
        print("3. Mevcut Anahtarları Gör")
        print("4. Özel API Anahtarı Dosyası Seç")
        print(f"5. {Fore.MAGENTA}✦ ANTIGRAVITY MANAGER Ayarla (Lokal Proxy){Style.RESET_ALL}")
        print("9. Geri Dön")
        
        choice = input(f"\n{Fore.YELLOW}Seçiminiz: {Style.RESET_ALL}").strip()
        
        if choice == '9': break
        
        elif choice == '5':
            # ── Antigravity Manager — Otomatik Bağlantı ve Kurulum ──
            if getattr(sys, 'frozen', False):
                _base = os.path.dirname(sys.executable)
                # EXE "Sadece Çeviri" içindeyse bir üst klasöre "Python kodları" / "otomatik indirici" köküne gider
                if os.path.basename(_base).lower() == "sadece çeviri":
                    config_path = os.path.join(os.path.dirname(_base), "translator_config.json")
                else:
                    config_path = os.path.join(_base, "translator_config.json")
            else:
                config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translator_config.json")

            def ag_load():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    return {}

            def ag_save(cfg):
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(cfg, f, indent=4, ensure_ascii=False)
                    return True
                except Exception as e:
                    print(f"{Fore.RED}Kayıt hatası: {e}{Style.RESET_ALL}")
                    return False

            def ag_auto_connect(base_url, key=""):
                """
                Antigravity'ye bağlanmayı dene.
                1) Keyless dener
                2) Olmadı: key ile dener
                3) /v1/models'dan modelleri çek
                Döner: (başarı:bool, key:str, modeller:list, hata:str)
                """
                import requests as _req
                base = base_url.rstrip("/")
                models_url = base + "/v1/models"
                completions_url = base + "/v1/chat/completions"

                # -- Auth test: önce keysiz, sonra keysi --
                keys_to_try = ["", key] if key else [""]
                working_key = None

                for k in keys_to_try:
                    try:
                        hdrs = {"Authorization": f"Bearer {k}"} if k else {}
                        r = _req.get(models_url, headers=hdrs, timeout=4)
                        if r.status_code in (200, 401):
                            if r.status_code == 200:
                                working_key = k
                                break
                    except Exception:
                        pass

                if working_key is None and key:
                    working_key = key  # yine de dene

                # -- Model listesi çek --
                try:
                    hdrs = {"Authorization": f"Bearer {working_key}"} if working_key else {}
                    r = _req.get(models_url, headers=hdrs, timeout=5)
                    if r.status_code == 200:
                        data = r.json()
                        models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                        return True, working_key or "", models, ""
                    elif r.status_code == 401:
                        return False, "", [], "API Key gerekli (401 Unauthorized)"
                    else:
                        return False, "", [], f"HTTP {r.status_code}"
                except Exception as e:
                    return False, "", [], str(e)

            def ag_update_models_in_config(cfg, models, base_url):
                """Çekilen modelleri translator_config.json'a AG: prefix'iyle ekle"""
                avail = cfg.get("available_models", {})
                # Önce eski AG modellerini temizle
                avail = {k: v for k, v in avail.items() if v.get("provider") != "antigravity"}
                # Yeni modelleri ekle
                for m in models:
                    key_id = f"AG:{m}"
                    avail[key_id] = {
                        "name": f"\u2726 [ANTIGRAVITY] {m}",
                        "model_name": m,
                        "provider": "antigravity"
                    }
                cfg["available_models"] = avail
                cfg["antigravity_url"] = base_url + "/v1/chat/completions"
                return cfg

            while True:
                ag_cfg = ag_load()
                current_url = ag_cfg.get('antigravity_url', 'http://localhost:8045/v1/chat/completions')
                current_key = ag_cfg.get('antigravity_api_key', '')
                base_url = current_url.replace("/v1/chat/completions", "").rstrip("/")

                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"{Fore.MAGENTA}╔══════════════════════════════════════════════╗{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}║   ✦ ANTİGRAVİTY MANAGER — OTOMATİK KURULUM   ║{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}╚══════════════════════════════════════════════╝{Style.RESET_ALL}")
                print()

                # Mevcut ayarlar
                ag_models = [k for k in ag_cfg.get("available_models", {}) if ag_cfg["available_models"][k].get("provider") == "antigravity"]
                print(f"  URL    : {Fore.CYAN}{base_url}{Style.RESET_ALL}")
                key_disp = (current_key[:8] + '...' + current_key[-4:]) if len(current_key) > 12 else (current_key or f"{Fore.LIGHTBLACK_EX}Yok (otomatik denenir){Style.RESET_ALL}")
                print(f"  Key    : {Fore.YELLOW}{key_disp}{Style.RESET_ALL}")
                print(f"  Modeller: {Fore.GREEN}{len(ag_models)} AG modeli kayıtlı{Style.RESET_ALL}" if ag_models else f"  Modeller: {Fore.RED}Henüz çekilmedi{Style.RESET_ALL}")
                print()
                print(f"  {Fore.LIGHTBLACK_EX}💡 Farklı PC: http://192.168.1.50:8045  |  Bu PC: http://localhost:8045{Style.RESET_ALL}")
                print()
                print("─" * 48)
                print(f"  {Fore.CYAN}1. OTOMATİK BAĞLAN ve Modelleri Al{Style.RESET_ALL}  ← Ana işlem")
                print(f"     (IP gir → bağlan → modelleri çek → kaydet)")
                print()
                print("  2. Sadece API Key Güncelle")
                print("  3. Mevcut Bağlantıyı Test Et")
                print("  9. Geri Dön")
                print("─" * 48)

                ag_choice = input(f"\n{Fore.YELLOW}Seçim: {Style.RESET_ALL}").strip()

                if ag_choice == '9':
                    break

                elif ag_choice == '1':
                    # -- OTOMATİK BAĞLANTI --
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"{Fore.MAGENTA}─── OTOMATİK BAĞLANTI ───{Style.RESET_ALL}")
                    print()
                    print(f"  Mevcut: {Fore.CYAN}{base_url}{Style.RESET_ALL}")
                    print()
                    print(f"  Sadece IP veya adresi girin. Örnekler:")
                    print(f"  {Fore.LIGHTBLACK_EX}• localhost:8045         (bu PC)")
                    print(f"  • 192.168.1.50:8045     (ağdaki başka PC)")
                    print(f"  • 10.0.0.5:8045         (uzak sunucu)")
                    print(f"  • ENTER                  (mevcut: {base_url}){Style.RESET_ALL}")
                    print()
                    raw = input(f"{Fore.YELLOW}IP:PORT → {Style.RESET_ALL}").strip()

                    if raw:
                        if not raw.startswith("http"):
                            raw = "http://" + raw
                        new_base = raw.rstrip("/")
                    else:
                        new_base = base_url

                    print()
                    print(f"{Fore.CYAN}Bağlanılıyor: {new_base} ...{Style.RESET_ALL}")
                    ok, found_key, models, err = ag_auto_connect(new_base, current_key)

                    if ok:
                        print(f"{Fore.GREEN}✓ Bağlandı! {len(models)} model bulundu.{Style.RESET_ALL}")
                        for m in models:
                            print(f"   • {m}")
                        print()
                        # Config'e kaydet
                        ag_cfg = ag_load()
                        ag_cfg = ag_update_models_in_config(ag_cfg, models, new_base)
                        if found_key is not None:
                            ag_cfg['antigravity_api_key'] = found_key
                        if ag_save(ag_cfg):
                            print(f"{Fore.GREEN}✓ Tüm modeller otomatik eklendi ve kaydedildi!{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}  'Model Değiştir' menüsünde ✦ [ANTIGRAVITY] olarak görünecekler.{Style.RESET_ALL}")
                    elif "401" in err or "Key gerekli" in err:
                        print(f"{Fore.YELLOW}⚠ Bağlantı var ama API Key gerekli!{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}Antigravity Manager → API Proxy sekmesi → 'API Key' alanını kopyalayın:{Style.RESET_ALL}")
                        api_key_input = input("API Key: ").strip()
                        if api_key_input:
                            ok2, _, models2, err2 = ag_auto_connect(new_base, api_key_input)
                            if ok2:
                                ag_cfg = ag_load()
                                ag_cfg = ag_update_models_in_config(ag_cfg, models2, new_base)
                                ag_cfg['antigravity_api_key'] = api_key_input
                                ag_save(ag_cfg)
                                print(f"{Fore.GREEN}✓ {len(models2)} model eklendi ve kaydedildi!{Style.RESET_ALL}")
                            else:
                                print(f"{Fore.RED}✗ Hata: {err2}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}✗ Bağlantı başarısız: {err}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}• Antigravity Manager'ın açık olduğundan emin olun")
                        print(f"• Farklı PC ise aynı ağda olduğunuzdan emin olun{Style.RESET_ALL}")

                    input(f"\n{Fore.LIGHTBLACK_EX}Devam için ENTER...{Style.RESET_ALL}")

                elif ag_choice == '2':
                    print(f"\n{Fore.CYAN}Antigravity Manager → API Proxy → API Key{Style.RESET_ALL}")
                    new_key = input("Yeni API Key: ").strip()
                    if new_key:
                        ag_cfg['antigravity_api_key'] = new_key
                        if ag_save(ag_cfg):
                            print(f"{Fore.GREEN}✓ Key güncellendi.{Style.RESET_ALL}")
                    time.sleep(1)

                elif ag_choice == '3':
                    import requests as _req
                    print(f"\n{Fore.CYAN}Test: {base_url} ...{Style.RESET_ALL}")
                    try:
                        hdrs = {"Authorization": f"Bearer {current_key}"} if current_key else {}
                        r = _req.get(base_url + "/v1/models", headers=hdrs, timeout=4)
                        if r.status_code == 200:
                            n = len(r.json().get("data", []))
                            print(f"{Fore.GREEN}✓ Bağlantı OK — {n} model bulundu{Style.RESET_ALL}")
                        else:
                            print(f"{Fore.YELLOW}⚠ HTTP {r.status_code} — {r.text[:100]}{Style.RESET_ALL}")
                    except Exception as e:
                        print(f"{Fore.RED}✗ Bağlanamadı: {e}{Style.RESET_ALL}")
                    input(f"\n{Fore.LIGHTBLACK_EX}ENTER...{Style.RESET_ALL}")



        
        elif choice == '1':
            # Dynamic Model Loading from translator_config.json
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translator_config.json")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    t_config = json.load(f)
                    avail_models = t_config.get("available_models", {})
            except:
                avail_models = {}

            if not avail_models:
                print(f"{Fore.RED}Hata: translator_config.json içinde model listesi bulunamadı!{Style.RESET_ALL}")
                time.sleep(2)
                continue

            # Listeyi göster
            print("\nKullanılabilir Modeller:")
            sorted_keys = sorted(avail_models.keys())
            
            # Identify active
            active_id = t_config.get("active_model_id", "")

            for i, key in enumerate(sorted_keys, 1):
                m_data = avail_models[key]
                prefix = f"{Fore.GREEN}[*]{Style.RESET_ALL} " if key == active_id else "    "
                print(f"{prefix}{i}. {m_data['name']} ({key})")
            
            try:
                sel = input("\nSeçim No (İptal=ENTER): ")
                if sel.strip():
                    idx = int(sel) - 1
                    if 0 <= idx < len(sorted_keys):
                        selected_key = sorted_keys[idx]
                        
                        # Save to translator_config.json
                        t_config["active_model_id"] = selected_key
                        # Also update "model" field for legacy compatibility? 
                        # - No, translator.py should read active_model_id.
                        
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(t_config, f, indent=4)
                        
                        # [FIX] model_name degil selected_key kaydet (AG: prefix dahil olmali!)
                        prefs['ai_model'] = selected_key
                        save_prefs(prefs)
                        
                        print(f"{Fore.GREEN}Model değiştirildi: {avail_models[selected_key]['name']}{Style.RESET_ALL}")
                        time.sleep(1)
            except Exception as e:
                print(f"Hata: {e}")
                time.sleep(2)
            
        elif choice == '2':
            # Eğer custom path varsa ona ekle yoksa defaulta
            target_file = prefs.get('custom_api_keys_path')
            if not target_file:
                target_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_keys.txt") # Default
                
            keys = input(f"API Anahtarlarını yapıştır ({os.path.basename(target_file)}): ").strip()
            if keys:
                key_list = [k.strip() for k in keys.split(',') if k.strip()]
                try:
                    with open(target_file, 'a', encoding='utf-8') as f:
                        for k in key_list: f.write(f"\n{k}")
                    print(f"{len(key_list)} anahtar eklendi.")
                except Exception as e:
                    print(f"Hata: {e}")
                time.sleep(1)
        
        elif choice == '3':
            target_file = prefs.get('custom_api_keys_path')
            if not target_file:
                target_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_keys.txt")
                
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    print(f.read())
                input("Devam...")
            else:
                print("Dosya yok.")
                time.sleep(1)
                
        elif choice == '4':
            print(f"\n{Fore.CYAN}API Anahtarlarının bulunduğu dosyanın tam yolunu girin (Sıfırlamak için boş bırakıp ENTER basın):{Style.RESET_ALL}")
            new_path = input("Dosya Yolu: ").strip('"\' ')
            
            if not new_path:
                prefs['custom_api_keys_path'] = None
                print("Varsayılan konuma (ana klasör) sıfırlandı.")
            elif os.path.exists(new_path) and os.path.isfile(new_path):
                prefs['custom_api_keys_path'] = new_path
                print(f"Yeni anahtar dosyası ayarlandı: {new_path}")
            else:
                print(f"{Fore.RED}Dosya bulunamadı! Değişiklik yapılmadı.{Style.RESET_ALL}")
            
            save_prefs(prefs)
            time.sleep(1)

def configure_advanced_settings():
    """Translator config.json dosyasını doğrudan düzenler"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "translator_config.json")
    
    # Varsayılanlar
    config = {
        "batch_size": 1,
        "timeout": 600,
        "delay_between_calls": 0,
        "max_bytes_per_call": 2000,
        "system_prompt": "Translate...",
        "max_retries": 6
    }
    
    # Yükle
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config.update(json.load(f))
        except: pass
        
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.MAGENTA}=== GELİŞMİŞ ÇEVİRİ AYARLARI (Config.json) ==={Style.RESET_ALL}")
        
        print(f"1. Batch Boyutu (Hız)    : {Fore.CYAN}{config.get('batch_size', 1)}{Style.RESET_ALL} (Satır)")
        print(f"2. Zaman Aşımı (Timeout) : {Fore.CYAN}{config.get('timeout', 600)}{Style.RESET_ALL} (Saniye)")
        print(f"3. Gecikme (Delay)       : {Fore.CYAN}{config.get('delay_between_calls', 0)}{Style.RESET_ALL} (Saniye)")
        print(f"4. Max Tekrar (Retries)  : {Fore.CYAN}{config.get('max_retries', 6)}{Style.RESET_ALL}")
        
        prompt_disp = config.get('system_prompt', '')
        if len(prompt_disp) > 50: prompt_disp = prompt_disp[:47] + "..."
        print(f"5. Sistem İstemi (Prompt): {Fore.LIGHTBLACK_EX}{prompt_disp}{Style.RESET_ALL}")
        
        on = f"{Fore.GREEN}AÇIK{Style.RESET_ALL}"
        off = f"{Fore.RED}KAPALI{Style.RESET_ALL}"
        print(f"6. Zorla Çevir (No Cache): {on if config.get('ignore_cache') else off}")
        
        print(f"\n9. {Fore.YELLOW}Kaydet ve Geri Dön{Style.RESET_ALL}")
        
        choice = input(f"\n{Fore.YELLOW}Seçiminiz: {Style.RESET_ALL}").strip()
        
        if choice == '9':
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4)
                print(f"{Fore.GREEN}Ayarlar kaydedildi.{Style.RESET_ALL}")
                time.sleep(1)
            except Exception as e:
                print(f"{Fore.RED}Hata: {e}{Style.RESET_ALL}")
            break
            
        elif choice == '1':
            try:
                val = int(input("Yeni Batch Boyutu (1-100): "))
                if 1 <= val <= 100: config['batch_size'] = val
            except: pass
            
        elif choice == '2':
            try:
                val = int(input("Yeni Timeout (60-3600): "))
                if 60 <= val <= 3600: config['timeout'] = val
            except: pass
            
        elif choice == '3':
            try:
                val = float(input("Yeni Gecikme (0.0-10.0): "))
                if 0 <= val <= 10.0: config['delay_between_calls'] = val
            except: pass
            
        elif choice == '4':
            try:
                val = int(input("Yeni Max Tekrar (1-20): "))
                if 1 <= val <= 20: config['max_retries'] = val
            except: pass
            
        elif choice == '5':
            print(f"\n{Fore.CYAN}--- Prompt Düzenle ---{Style.RESET_ALL}")
            print(f"Mevcut:\n{config.get('system_prompt')}\n")
            val = input("Yeni Prompt (İptal için BOŞ): ").strip()
            if val: config['system_prompt'] = val
            
        elif choice == '6':
            config['ignore_cache'] = not config.get('ignore_cache', False)

def main():
    _startup_played = False
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        prefs = load_prefs()
        
        if not _startup_played:
            _play_tone('startup')  # Program ilk açıldığında hoş karşılama
            _startup_played = True

        print(f"{Fore.MAGENTA}=================================================={Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}   GELİŞMİŞ MANUEL TERCÜMAN (v2.0){Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}=================================================={Style.RESET_ALL}")
        print(f"Model: {Fore.GREEN}{prefs.get('ai_model')}{Style.RESET_ALL} | Format: {Fore.YELLOW}{prefs.get('sub_format')}{Style.RESET_ALL}")
        print("-" * 50)
        print("1. OTOMATİK BAŞLAT (Bulunduğum Klasörü Tara ve Çevir)")
        print("2. Manuel Dosya/Klasör Yolu Gir")
        print("3. AI ve API Ayarları")
        print("4. Tercihler / Özellikleri Aç-Kapa")
        print(f"5. CANLI TEST (Manuel Single Line)")
        print(f"6. GELİŞMİŞ AYARLAR (Hız/Timeout/Batch)")
        print("9. Çıkış")
        
        # Args Support
        if len(sys.argv) > 1:
            if sys.argv[1] == '--files' and len(sys.argv) > 2:
                # ── GUI toplu dosya modu ── tek process, bağlam korunuyor ──
                explicit = [p for p in sys.argv[2:] if os.path.exists(p)]
                if explicit:
                    _base_dir = os.path.dirname(explicit[0])
                    scan_and_process_directory(
                        _base_dir, prefs,
                        auto_scan_mode=True,
                        _explicit_targets=explicit
                    )
                else:
                    print(f"{Fore.RED}[--files] Geçerli dosya bulunamadı!{Style.RESET_ALL}")
            else:
                scan_and_process_directory(sys.argv[1], prefs, auto_scan_mode=True)
            sys.exit(0)
            
        choice = input(f"\n{Fore.YELLOW}Seçiminiz: {Style.RESET_ALL}").strip()
        
        if choice == '9':
            break
        elif choice == '1':
            # Auto Scan Current Directory
            current_dir = os.getcwd()
            scan_and_process_directory(current_dir, prefs, auto_scan_mode=True)
        elif choice == '2':
            try:
                import tkinter as tk
                from tkinter import filedialog
                _root = tk.Tk()
                _root.withdraw()
                _root.attributes('-topmost', True)
                print(f"\n{Fore.CYAN}Klasör veya dosya seçim penceresi açılıyor...{Style.RESET_ALL}")
                path = filedialog.askdirectory(title="Çevrilecek Klasörü Seç")
                if not path:
                    path = filedialog.askopenfilename(
                        title="Çevrilecek Dosyayı Seç",
                        filetypes=[("Altyazı/Video", "*.ass *.ssa *.srt *.vtt *.mkv *.mp4 *.avi *.webm"), ("Tümü", "*.*")]
                    )
                _root.destroy()
            except Exception:
                path = input(f"\n{Fore.CYAN}Dosya veya Klasör Yolu: {Style.RESET_ALL}").strip('"\' ')
            if path:
                scan_and_process_directory(path, prefs, auto_scan_mode=False)
        elif choice == '3':
            configure_ai_api(prefs)
        elif choice == '4':
            configure_preferences(prefs)
        elif choice == '5':
            manual_test_mode(prefs)
        elif choice == '6':
            configure_advanced_settings()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _play_tone('interrupt')  # Ctrl+C ile durduruldu
        print(f"\n{Fore.YELLOW}[!] İşlem kullanıcı tarafından durduruldu.{Style.RESET_ALL}")
