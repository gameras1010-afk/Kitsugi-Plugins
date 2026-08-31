import os
import re
import subprocess
import shutil
import time


# ============================================================
# GARBAGE LINE DETECTOR — API'ya gönderilmemesi gereken satırlar
# ============================================================

# Dahili placeholder prefix'leri (bunları soy, sonra analiz et)
_INTERNAL_PREFIXES = re.compile(
    r'^\s*(?:\[SIGN\]|\[SONG\]|\[SFX\]|\[NOTE\]|__T\d+__)\s*', re.IGNORECASE
)
# ASS override tag'leri {..}
_ASS_TAG_STRIP = re.compile(r'\{[^}]*\}')
# Dahili placeholder'lar (__ASSNL__, __NL__, vs)
_PLACEHOLDER_STRIP = re.compile(r'__[A-Z0-9]+__')

def is_garbage_line(text: str) -> bool:
    """
    Bir altyazı satırının çeviri için geçersiz (garbage) olup olmadığını kontrol eder.

    Garbage sinyalleri:
    1. Boş / sadece sembol
    2. Harf oranı < %40 (noktalama/sayı ağırlıklı)
    3. Büyük harf oranı > %35 (base64 / encoded veri — gerçek İng. metinde %5-10)
    4. Boşluksuz tek token > 20 karakter (kod bloğu, hash, vb.)
    5. [SIGN] prefix'ten hemen sonra __Tn__ placeholder → ASS etiketiyle başlayan anlamsız içerik
    """
    if not text or not text.strip():
        return True  # Boş → garbage

    # Sinyal 5: [SIGN] + hemen __Tn__ placeholder → encode edilmiş ASS sign
    _stripped_prefix = text.strip()
    for _pfx in ('[SIGN]', '[SONG]', '[SFX]', '[NOTE]'):
        if _stripped_prefix.upper().startswith(_pfx):
            _after = _stripped_prefix[len(_pfx):].strip()
            if re.match(r'^__T\d+__', _after):
                return True  # [SIGN] __T0__GarbageContent... → garbage

    # Prefix, ASS tag, placeholder'ları soy
    clean = _INTERNAL_PREFIXES.sub('', text)
    clean = _ASS_TAG_STRIP.sub('', clean)
    clean = _PLACEHOLDER_STRIP.sub(' ', clean)
    clean = clean.strip()

    if not clean:
        return True  # Sadece tag'lerden oluşuyor

    total_chars = len(clean)
    if total_chars < 2:
        return True

    # Sinyal 2: Harf oranı < %40
    letter_count = sum(1 for c in clean if c.isalpha())
    letter_ratio = letter_count / total_chars
    if letter_ratio < 0.40:
        return True

    if letter_count < 3:
        return True

    # Sinyal 3: Büyük harf oranı > %35 → base64/random encoding
    #   Gerçek cümle: "Of course." → upper ratio %9
    #   Garbage: "EW?P,b1Rq04e5Ad??" → upper ratio %52
    #   İSTİSNA: Kısa cümlelerde baş harfler + özel isimler oranı doğal yüksek!
    #   "Am I Ruby?" → 7 harf, 3 büyük → %43 → YANLIŞ garbage!
    #   Kural yalnızca 15+ harfli metinlerde anlamlı.
    upper_count = sum(1 for c in clean if c.isupper())
    upper_ratio = upper_count / letter_count
    if letter_count >= 15 and upper_ratio > 0.35:
        return True

    # Sinyal 4: Boşluk yok ve çok uzun → hash, token, kod bloğu
    tokens = clean.split()
    if len(tokens) == 1 and len(clean) > 20:
        return True

    return False  # Normal, çevrilebilir



# ============================================================
# SUBTITLE LINE SPLITTER (Max 2 Lines)
# ============================================================

def auto_split_line(text, max_len=55, max_lines=2):
    """
    Uzun bir altyazı satırını en fazla 2 satıra böler.

    KURAL:
    - max_len karakter veya daha kısa → TEK SATIR, asla bölme
    - max_len üzeri              → kelime ortasından dengeli böl (2 satır)
    - Asla 3+ satır üretilmez   → max_lines=2 zorlaması

    1080p standardı: max_len=55
      (Netflix: 42, anime subs: 50-60, Türkçe uzun kelimeler için 55 iyi denge)

    İstisnalar (hiç dokunma):
      - \pos / \move / \an tag'i olan satırlar (konumlandırılmış tabela)
      - ♪ ♬ şarkı sembolü içeren satırlar
      - Boş satırlar
    """
    if not text or not text.strip():
        return text

    # Konumlandırma tag'i → DOKUNMA
    if re.search(r'\\(pos|move|org|clip|iclip|an[1-9])', text):
        return text

    # Şarkı notu → DOKUNMA
    if '♪' in text or '♬' in text:
        return text

    # Mevcut \N sayısını kontrol et
    parts = text.split('\\N')

    if len(parts) <= max_lines:
        # Tek satır: uzunluk eşiğini aştıysa böl, aşmadıysa DOKUNMA
        if len(parts) == 1:
            clean = text.replace('\\N', ' ')
            if len(clean) <= max_len:
                return text  # ← Kısa → tek satır bırak
            return _split_balanced(clean, max_len, max_lines)
        return text  # 2 satır zaten → dokunma

    # 3+ satır → tümünü birleştir, yeniden dengeli böl
    full_text = ' '.join(p.strip() for p in parts if p.strip())
    return _split_balanced(full_text, max_len, max_lines)


def _split_balanced(text, max_len=55, max_lines=2):
    """
    Metni kelime sınırından dengeli böler.

    - max_len ve altı → bölme (tek satır yeterli)
    - Bölme noktası: toplam karakter sayısının ortasına en yakın KELİME SINIRI
      → iki satır birbirine yakın uzunlukta olur, dengeli görünür
    """
    text = text.strip()
    if not text:
        return text

    # Eşik altı → bölme
    if len(text) <= max_len:
        return text

    words = text.split()
    if len(words) <= 1:
        return text
    if max_lines == 1:
        return text

    # Kelime sayısı ortasını bul (karakter dengesi de dikkate alınır)
    total_len = len(text)
    target_first = total_len // 2

    current = ""
    best_split = max(1, len(words) // 2)  # fallback: kelime sayısı ortası
    best_diff = float('inf')

    for i, word in enumerate(words[:-1]):
        current += ("" if not current else " ") + word
        diff = abs(len(current) - target_first)
        if diff < best_diff:
            best_diff = diff
            best_split = i + 1

    line1 = " ".join(words[:best_split])
    line2 = " ".join(words[best_split:])
    return f"{line1}\\N{line2}"


# ============================================================
# LINE MERGE HELPER
# ============================================================

def should_merge_lines(text1, text2):
    """
    İki altyazı satırını birleştirip birleştirmemek gerektiğine karar verir.
    
    Birleştirme kriteri:
    - Her iki metin de kısa (30 karakter altı) olmalı
    - İlk metin noktalama işaretiyle bitmemeli (cümle bitmemiş)
    - Birleşik uzunluk 60 karakterden fazla olmamalı
    """
    t1 = text1.strip()
    t2 = text2.strip()
    
    if not t1 or not t2:
        return False
    
    # Her ikisi de çok kısaysa birleştir
    combined_len = len(t1) + len(t2) + 1
    if combined_len > 80:  # Modern standart: 80 karakter (eskiden 60, TR icin genisletildi)
        return False
    
    # İlk satır noktalama ile bitiyorsa (cümle tamamdır) birleştirme
    if t1.endswith(('.', '!', '?', '…', '♪', '♬')):
        return False
    
    # İkinci satır büyük harfle başlıyorsa ayrı cümle, birleştirme
    if t2 and t2[0].isupper() and t1.endswith(',') is False:
        # İstisna: Özel isim olabilir (kısa ise)
        if len(t1) > 15:
            return False
    
    return True


# ============================================================
# LOG / EPISODE HELPERS
# ============================================================

def log_error(message, filepath="hatalar.txt"):
    """Hata mesajını dosyaya yazar."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, filepath)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception:
        pass


def log_debug(message, filepath="debug.txt"):
    """Debug mesajını dosyaya yazar."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, filepath)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(message + '\n')
    except Exception:
        pass


def clean_text_content(text):
    """
    Ham metin içeriğini temizler:
    - HTML etiketlerini kaldırır (<br>, <i>, <b> vb.)
    - Birden fazla boşluğu tek boşluğa indirir
    - Baş/son boşlukları temizler
    """
    if not text:
        return ""
    # HTML etiketlerini kaldır
    text = re.sub(r'<[^>]+>', ' ', text)
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_episode_number(filename):
    """URL veya dosya adından bölüm numarasını çıkarır. Sadece rakamı döndürür."""
    if not filename:
        return None
    # Yaygın pattern'lar (group(1) = sadece rakam döndürmeli)
    patterns = [
        # "Episode 3", "Ep 3", "Bölüm 3", "Bolum 3" ile boşluklu format (dosya adı ve sayfa başlığı)
        r'(?:episode|ep|bölüm|bolum|b[oö]l[uü]m)[\s._-]+(\d{1,4})',
        # URL stili: /episode-2, episode_2, ep-2, ep_2
        r'(?:episode|ep)[-_](\d{1,4})',
        # "Anime Name - 5" stili (tire sonrası tek/çift rakam)
        r'[-–]\s*(\d{1,4})\s*(?:$|[\.\[\(])',
        # URL'de "- 2" veya "/2" şeklinde bölüm: anime-name-2
        r'[-/](\d{1,4})(?:[/?#]|$)',
        # S01E05 stili
        r'[Ss]\d{1,2}[Ee](\d{1,4})',
        # E05 stili (büyük E + 2-4 rakam)
        r'[Ee](\d{2,4})',
        # [05] veya _05_ veya -05- stili
        r'[\s_\-\[](\d{2,4})[\s_\-\]]',
        # 05.mkv veya 05 sonunda
        r'(\d{2,4})(?:\s*v\d)?(?:\.|$)',
    ]
    for p in patterns:
        m = re.search(p, filename, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


# ============================================================
# SAVE HELPERS
# ============================================================

def save_as_srt(events, output_path):
    """ASS event listesini SRT formatında kaydeder."""
    try:
        srt_lines = []
        counter = 1
        for ev in events:
            parts = ev.get("parts", [])
            if len(parts) < 10:
                continue
            start = _ass_to_srt_time(parts[1].strip())
            end = _ass_to_srt_time(parts[2].strip())
            text = parts[9].strip()
            # ASS taglerini temizle
            text = re.sub(r'\{.*?\}', '', text)
            text = text.replace(r'\N', '\n').replace(r'\n', '\n')
            if not text.strip():
                continue
            srt_lines.append(f"{counter}\n{start} --> {end}\n{text}\n")
            counter += 1
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_lines))
        return True
    except Exception as e:
        log_error(f"SRT kayıt hatası: {e}")
        return False


def save_as_vtt(events, output_path):
    """ASS event listesini WebVTT formatında kaydeder."""
    try:
        vtt_lines = ["WEBVTT", ""]
        for ev in events:
            parts = ev.get("parts", [])
            if len(parts) < 10:
                continue
            start = _ass_to_vtt_time(parts[1].strip())
            end = _ass_to_vtt_time(parts[2].strip())
            text = parts[9].strip()
            text = re.sub(r'\{.*?\}', '', text)
            text = text.replace(r'\N', '\n').replace(r'\n', '\n')
            if not text.strip():
                continue
            vtt_lines.append(f"{start} --> {end}")
            vtt_lines.append(text)
            vtt_lines.append("")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(vtt_lines))
        return True
    except Exception as e:
        log_error(f"VTT kayıt hatası: {e}")
        return False


def _ass_to_srt_time(ass_time):
    """ASS zaman formatını (h:mm:ss.cs) SRT formatına (HH:MM:SS,mmm) çevirir."""
    try:
        h, m, rest = ass_time.split(':')
        s, cs = rest.split('.')
        ms = int(cs) * 10  # centiseconds → milliseconds
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"
    except Exception:
        return ass_time


def _ass_to_vtt_time(ass_time):
    """ASS zaman formatını (h:mm:ss.cs) VTT formatına (HH:MM:SS.mmm) çevirir."""
    try:
        h, m, rest = ass_time.split(':')
        s, cs = rest.split('.')
        ms = int(cs) * 10
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{ms:03d}"
    except Exception:
        return ass_time


# ============================================================
# FFMPEG / SYSTEM HELPERS
# ============================================================

def check_ffmpeg():
    """FFmpeg'in sistemde kurulu olup olmadığını kontrol eder."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def get_video_duration(filepath):
    """
    FFprobe kullanarak video süresini saniye cinsinden döndürür.
    FFprobe bulunamazsa None döner.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
        )
        output = result.stdout.decode('utf-8', errors='ignore').strip()
        if output:
            return float(output)
    except Exception:
        pass
    return None


def get_gpu_stats():
    """
    NVIDIA GPU kullanım ve VRAM bilgilerini döndürür.
    nvidia-smi bulunamazsa None döner.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
        )
        if result.returncode == 0:
            output = result.stdout.decode('utf-8', errors='ignore').strip()
            parts = [p.strip() for p in output.split(',')]
            if len(parts) >= 3:
                return {
                    'gpu_util': parts[0],
                    'vram_used': parts[1],
                    'vram_total': parts[2]
                }
    except Exception:
        pass
    return None


def safe_rename(src, dst):
    """
    Dosyayı güvenli şekilde yeniden adlandırır.
    Başarılıysa True, hata olursa False döner.
    """
    try:
        if os.path.exists(dst):
            try:
                os.remove(dst)
            except Exception:
                pass
        os.rename(src, dst)
        return True
    except Exception as e:
        log_error(f"safe_rename hatası ({src} -> {dst}): {e}")
        return False


def safe_remove(filepath):
    """
    Dosyayı güvenli şekilde siler.
    Başarılıysa True, hata olursa False döner.
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception as e:
        log_error(f"safe_remove hatası ({filepath}): {e}")
        return False


def run_ffmpeg_process(cmd, cwd=None, total_duration=None):
    """
    FFmpeg komutunu ilerleme çubuğuyla çalıştırır.
    Hata durumunda Exception fırlatır.
    """
    try:
        from colorama import Fore, Style
        has_colorama = True
    except ImportError:
        has_colorama = False

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding='utf-8',
        errors='replace',
        cwd=cwd,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
    )

    last_print_time = time.time()
    for line in process.stdout:
        line = line.strip()
        # Süre bilgisi içeren satırları filtrele
        if 'time=' in line and total_duration:
            m = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
            if m:
                h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
                elapsed = h * 3600 + mi * 60 + s
                pct = min(100, int(elapsed / total_duration * 100))
                now = time.time()
                if now - last_print_time >= 2:
                    if has_colorama:
                        print(f"\r   {Fore.CYAN}[FFmpeg] %{pct:3d} tamamlandı...{Style.RESET_ALL}", end='', flush=True)
                    else:
                        print(f"\r   [FFmpeg] %{pct:3d} tamamlandı...", end='', flush=True)
                    last_print_time = now
        elif 'error' in line.lower() or 'invalid' in line.lower():
            if has_colorama:
                print(f"\n   {Fore.YELLOW}[FFmpeg] {line}{Style.RESET_ALL}")
            else:
                print(f"\n   [FFmpeg] {line}")

    process.wait()
    print()  # Son satır

    if process.returncode not in (0, 1):  # 1 genellikle uyarıdır
        raise Exception(f"FFmpeg işlemi başarısız (kod: {process.returncode})")


# ============================================================
# LOGGING SETUP
# ============================================================

def setup_logging(log_file=None):
    """
    Uygulama genelinde logging yapılandırmasını ayarlar.
    Hem konsola hem de dosyaya yazar.
    """
    import logging
    import settings as _settings

    if log_file is None:
        try:
            log_file = _settings.LOG_FILE
        except Exception:
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uygulama.log")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


# ============================================================
# FILENAME / TEXT HELPERS
# ============================================================

def clean_filename_safe(text):
    """
    Dosya sistemiyle uyumlu, güvenli bir dosya adı oluşturur.
    Windows'ta yasak karakterleri kaldırır/değiştirir.
    """
    if not text:
        return "Unknown"
    # Windows yasak karakterleri: \/:*?"<>|
    cleaned = re.sub(r'[\\/:*?"<>|]', '', text)
    # Fazla boşlukları temizle
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Çok uzun dosya adlarını kırp (max 200 karakter)
    if len(cleaned) > 200:
        cleaned = cleaned[:200].strip()
    return cleaned or "Unknown"


def extract_series_name(title):
    """
    Başlık metninden dizi adını çıkarır.
    Örn: 'Anime Name Episode 5' → 'Anime Name'
    """
    if not title:
        return None
    # "- 1", "Episode 1", "Ep 1", "Bölüm 1" gibi bölüm numaralarını kaldır
    cleaned = re.sub(
        r'[\s\-–]+(?:episode|ep\.?|bölüm|vol\.?|part|pt\.?)\s*\d+.*$',
        '', title, flags=re.IGNORECASE
    ).strip()
    # Sadece "- N" şeklindeki sonları da kaldır
    cleaned = re.sub(r'\s*[-–]\s*\d+\s*$', '', cleaned).strip()
    return cleaned if cleaned else title


def save_metadata_to_text(meta_data, filepath):
    """
    Metadata sözlüğünü okunabilir metin dosyasına kaydeder.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Başlık: {meta_data.get('title', '')}\n")
            f.write(f"Puan: {meta_data.get('score', '')}\n")
            genres = meta_data.get('genres', [])
            if isinstance(genres, list):
                f.write(f"Türler: {', '.join(genres)}\n")
            else:
                f.write(f"Türler: {genres}\n")
            f.write(f"\nAçıklama:\n{meta_data.get('description', '')}\n")
        return True
    except Exception as e:
        log_error(f"save_metadata_to_text hatası: {e}")
        return False


# Sansürlenen kelimeler listesi
_NSFW_WORDS = [
    'hentai', 'ecchi', 'nude', 'naked', 'porn', 'xxx', 'sex', 'erotic',
    'uncensored', 'sansürsüz', 'adult', 'nsfw', 'yaoi', 'yuri', 'loli',
    'shota', 'ahegao', 'r18', 'r-18', 'ero'
]

def sanitize_for_social_media(text, mode="censor"):
    """
    Metindeki uygunsuz kelimeleri sosyal medya için temizler.
    mode='censor'  → Kelimeyi *** ile değiştirir
    mode='remove'  → Kelimeyi tamamen siler
    Temizlenmiş metin veya boş string döner.
    """
    if not text:
        return text

    result = text
    for word in _NSFW_WORDS:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        if mode == "remove":
            result = pattern.sub('', result)
        else:
            result = pattern.sub('***', result)

    result = re.sub(r'\s+', ' ', result).strip()
    return result


def show_error_popup(title, message):
    """
    Windows'ta hata mesajı popup'ı gösterir.
    ctypes kullanır; başarısız olursa sadece konsola yazar.
    """
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
    except Exception:
        print(f"\n[HATA POPUP] {title}: {message}\n")

