"""
utils_pkg/file_io.py
====================
Dosya ve ffmpeg.
"""
import os, re, sys, json, subprocess, platform

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

