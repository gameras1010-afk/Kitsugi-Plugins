# subtitle_tracks.py
# ─────────────────────────────────────────────────────────────────────────────
# Multi-track altyazı keşif ve kalite değerlendirme modülü.
# Bağımsız çalışır — translator, media_identifier veya manual_translator'a
# bağımlılığı yoktur. Bunlar bu modülü import eder.
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import json
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

# ── Sabitler ────────────────────────────────────────────────────────────────

# SDH (Subtitles for Deaf/HH) ve CC (Closed Captions) KALDIRIDI:
# Bunlar tam diyalog iceriyor, sign/song track degil!
SKIP_KEYWORDS   = ["sign", "song", "s&s", "s/s", "s & s", "karaoke", "kara",
                   "forced"]
# NOT: "sdh" ve "cc" kasıtlı olarak bu listede YOK.
# SDH/CC tam diyalog iceren formatlardır — İngilizce kaynak olarak kullanılır.

FANSUB_KEYWORDS = ["fansub", "çeviri", "scanlation", "subbed", "subtitled"]
ENG_LANG        = {"eng", "en"}
ENG_TITLE_KW    = ["english", "ingilizce"]
CJK_LANG        = {"jpn", "ja", "chi", "zh", "zho", "kor", "ko"}
CJK_TITLE_KW    = ["japanese", "japonca", "chinese", "çince", "korean",
                   "korece", "romaji", "jp", "jap"]
IMAGE_CODECS    = {"hdmv_pgs_subtitle", "pgs", "dvd_subtitle", "dvdsub",
                   "dvb_subtitle", "xsub", "pgssub", "sup"}

KNOWN_FANSUB_GROUPS = [
    "horriblesubs", "kayoanime", "subsplease", "erai-raws", "judas",
    "commie", "hiryuu", "doremi", "eclipse", "chihiro", "underwater",
    "doki", "coalgirls", "sage", "fff", "thora",
]

FANSUB_TEXT_SIGNALS = [
    "...!", "Eh?", "Huh?", "Ugh.", "Tch.", "Hmph.",
    "W-wait", "Y-you", "I-I", "Th-that", "N-no",
]

# ── Veri sınıfı ─────────────────────────────────────────────────────────────

@dataclass
class SubtitleTrack:
    """Bir video dosyasındaki tek bir altyazı track'ini temsil eder."""
    index: int                        # MKV stream index
    language: str = ""                # jpn, eng, und …
    title: str = ""                   # track başlığı
    codec: str = ""                   # ass, subrip, mov_text …
    is_signs: bool = False            # Signs & Songs track mi?
    is_image: bool = False            # PGS/bitmap mi? (çevrilemez)
    extracted_path: Optional[str] = None   # geçici çıkarılmış .ass dosyası
    quality_score: int = -1          # 0-100 (-1 = henüz hesaplanmadı)
    quality_label: str = "UNKNOWN"   # LOW / MEDIUM / HIGH / UNKNOWN
    quality_reasons: List[str] = field(default_factory=list)

    @property
    def is_english(self) -> bool:
        lang = self.language.lower()
        title = self.title.lower()
        return (lang in ENG_LANG) or any(k in title for k in ENG_TITLE_KW)

    @property
    def is_cjk(self) -> bool:
        lang = self.language.lower()
        title = self.title.lower()
        return (lang in CJK_LANG) or any(k in title for k in CJK_TITLE_KW)

    @property
    def is_japanese(self) -> bool:
        lang = self.language.lower()
        title = self.title.lower()
        return lang in {"jpn", "ja"} or any(k in title for k in
                                            ["japanese", "japonca", "jp", "jap"])

    def __str__(self):
        score_str = f"{self.quality_score}/100 [{self.quality_label}]" \
                    if self.quality_score >= 0 else "?"
        flags = []
        if self.is_signs:  flags.append("SIGNS")
        if self.is_image:  flags.append("IMAGE")
        return (f"Track#{self.index} lang={self.language!r} "
                f"title={self.title!r} codec={self.codec} "
                f"quality={score_str} {' '.join(flags)}")


# ── Kalite skorlama ──────────────────────────────────────────────────────────

def score_subtitle_file(filepath: str) -> dict:
    """
    Bir altyazı dosyasının kalite skorunu hesaplar (0-100).
    Yüksek skor = daha kaliteli (daha doğal İngilizce).

    Döner: {score: int, label: 'LOW'|'MEDIUM'|'HIGH', reasons: list[str]}
    """
    filename = os.path.basename(filepath).lower()
    reasons = []
    penalty = 0

    # ── 1. Dosya adı analizi ─────────────────────────────────────────────
    if re.match(r'^\[.+?\]', os.path.basename(filepath)):
        reasons.append("fansub_bracket_group")
        penalty += 25
    for grp in KNOWN_FANSUB_GROUPS:
        if grp in filename:
            reasons.append(f"known_fansub:{grp}")
            penalty += 20
            break

    # ── 2. İçerik analizi ───────────────────────────────────────────────
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        dialogues = []
        for line in content.splitlines():
            if line.startswith('Dialogue:'):
                parts = line.split(',', 9)
                if len(parts) >= 10:
                    text = re.sub(r'\{[^}]*\}', '', parts[9])
                    text = text.replace('\\N', ' ').replace('\\n', ' ').strip()
                    if text:
                        dialogues.append(text)

        if dialogues:
            avg_len = sum(len(d) for d in dialogues) / len(dialogues)
            if avg_len < 15:
                reasons.append(f"very_short_avg({avg_len:.0f}ch)")
                penalty += 15
            elif avg_len < 25:
                reasons.append(f"short_avg({avg_len:.0f}ch)")
                penalty += 8

            stutter_count = sum(
                1 for d in dialogues
                if any(sig in d for sig in FANSUB_TEXT_SIGNALS)
            )
            if stutter_count > len(dialogues) * 0.05:
                reasons.append(f"stutter_signals({stutter_count})")
                penalty += 12

            short_ratio = sum(1 for d in dialogues if len(d) < 5) / len(dialogues)
            if short_ratio > 0.1:
                reasons.append(f"many_short_lines({short_ratio:.0%})")
                penalty += 10
    except Exception:
        pass

    score = max(0, 100 - penalty)
    if score < 40:
        label = "LOW"
    elif score < 65:
        label = "MEDIUM"
    else:
        label = "HIGH"

    return {"score": score, "label": label, "reasons": reasons}


# ── FFmpeg / FFprobe yardımcıları ────────────────────────────────────────────

def _find_ff_tool(name: str) -> str:
    """ffmpeg veya ffprobe'u bulur; bulamazsa adı döndürür (PATH denesin)."""
    import shutil, glob as _glob
    exe = name + (".exe" if os.name == "nt" else "")

    # 1) Bu modülün üst dizini (uygulama ana klasörü)
    app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
    candidate = os.path.join(app_dir, exe)
    if os.path.isfile(candidate):
        return candidate

    # 2) PATH
    found = shutil.which(name)
    if found:
        return found

    # 3) Bilinen Windows kurulum yolları
    for pattern in [
        rf"C:\ffmpeg*\bin\{exe}",
        rf"C:\Program Files\ffmpeg*\bin\{exe}",
        rf"D:\ffmpeg*\bin\{exe}",
    ]:
        matches = _glob.glob(pattern)
        if matches:
            return matches[0]

    return name


def _run(cmd: list, timeout: int = 60, **kwargs) -> subprocess.CompletedProcess:
    flags = {}
    if os.name == "nt":
        flags["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, **flags, **kwargs)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout='', stderr=f'TIMEOUT after {timeout}s')


# ── Ana fonksiyonlar ─────────────────────────────────────────────────────────

def probe_tracks(video_path: str,
                 ffprobe: Optional[str] = None) -> List[SubtitleTrack]:
    """
    ffprobe ile video dosyasındaki TÜM altyazı stream'lerini listeler.
    Çıkarma yapmaz, sadece metadata döner.
    """
    ffprobe = ffprobe or _find_ff_tool("ffprobe")
    cmd = [
        ffprobe, "-v", "error", "-select_streams", "s",
        "-show_entries", "stream=index,codec_name:stream_tags=title,language",
        "-of", "json", video_path
    ]
    result = _run(cmd, timeout=30)  # ffprobe 30sn timeout
    if result.returncode != 0:
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    tracks = []
    for s in data.get("streams", []):
        idx   = s.get("index")
        if idx is None:
            continue
        tags  = s.get("tags", {})
        title = tags.get("title", "").strip()
        lang  = tags.get("language", "").lower().strip()
        codec = s.get("codec_name", "").lower()

        t = SubtitleTrack(
            index=idx,
            language=lang,
            title=title,
            codec=codec,
        )
        t.is_image = codec in IMAGE_CODECS
        t.is_signs = any(k in title.lower() for k in SKIP_KEYWORDS)
        tracks.append(t)

    return tracks


def extract_track(video_path: str,
                  track: SubtitleTrack,
                  output_dir: str,
                  ffmpeg: Optional[str] = None,
                  suffix: str = "") -> bool:
    """
    Tek bir track'i video'dan çıkarır, .ass olarak output_dir'e yazar.
    Başarılıysa track.extracted_path güncellenir, True döner.
    """
    ffmpeg = ffmpeg or _find_ff_tool("ffmpeg")
    base   = os.path.splitext(os.path.basename(video_path))[0]
    lang   = track.language or "und"
    fname  = f"{base}_track{track.index}_{lang}{suffix}.ass"
    out    = os.path.join(output_dir, fname)

    if os.path.exists(out) and os.path.getsize(out) > 0:
        track.extracted_path = out
        return True

    cmd = [ffmpeg, "-y", "-v", "error", "-i", video_path,
           "-map", f"0:{track.index}", out]
    result = _run(cmd, timeout=180)  # Büyük Blu-ray dosyaları için 3dk timeout
    if result.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
        track.extracted_path = out
        return True
    # Çıkarma başarısızsa dosyayı sil
    try:
        os.remove(out)
    except OSError:
        pass
    return False


def score_track_by_metadata(t: SubtitleTrack) -> float:
    """Sadece metadata kullanarak diyalog track'i için öncelik skoru hesaplar."""
    if not t.is_english:
        return -100
    if t.is_signs:
        return -50
    score = 50
    title = (t.title or "").lower()
    if re.search(r'\[.+?\]', title):
        score += 30
    for grp in KNOWN_FANSUB_GROUPS:
        if grp in title:
            score += 25
            break
    if "dialogue" in title or "full" in title:
        score += 10
    if any(k in title for k in ("sdh", "cc", "closed caption", "hearing impaired")):
        score -= 20
    if t.is_image:
        score = -1000
    if t.codec == "ass":
        score += 5
    score -= t.index * 0.1
    return score


def score_signs_track_by_metadata(t: SubtitleTrack) -> float:
    """Sadece metadata kullanarak signs track'i için öncelik skoru hesaplar."""
    if not t.is_signs:
        return -100
    if not t.is_english and (t.language and t.language.lower().strip() not in ("und", "")):
        return -50
    score = 50
    title = (t.title or "").lower()
    if re.search(r'\[.+?\]', title):
        score += 20
    for grp in KNOWN_FANSUB_GROUPS:
        if grp in title:
            score += 15
            break
    if "signs" in title or "songs" in title or "s&s" in title:
        score += 10
    score -= t.index * 0.1
    return score


def score_reference_track_by_metadata(t: SubtitleTrack) -> float:
    """Sadece metadata kullanarak referans CJK track'i için öncelik skoru hesaplar."""
    if not t.is_cjk:
        return -100
    score = 50
    if t.is_japanese:
        score += 30
    score -= t.index * 0.1
    return score


def extract_all_tracks(video_path: str,
                       output_dir: str,
                       ffprobe: Optional[str] = None,
                       ffmpeg: Optional[str] = None,
                       verbose: bool = True) -> List[SubtitleTrack]:
    """
    Video'daki tüm metin-tabanlı altyazı track'lerini çıkarır ve skolar.

    - PGS/bitmap track'ler atlanır.
    - Signs & Songs track'leri işaretlenir ama çıkarılmaz.
    - İngilizce track'ler kalite skoru alır.

    Döner: SubtitleTrack listesi (is_image=False, is_signs=False olanlar çıkarılmış)
    """
    os.makedirs(output_dir, exist_ok=True)
    tracks = probe_tracks(video_path, ffprobe)

    if not tracks:
        if verbose:
            print(f"  [Tracks] Hiç altyazı track'i bulunamadı: {os.path.basename(video_path)}")
        return []

    if verbose:
        print(f"  [Tracks] {len(tracks)} altyazı track'i tespit edildi.")

    # ── image track'leri atla, signs ve text track'lerini AYIR ─────────────
    text_tracks  = []   # Normal diyalog track'leri
    signs_tracks = []   # Signs & Songs track'leri (ekran yazıları)
    for t in tracks:
        if t.is_image:
            if verbose:
                print(f"  [ATLANDI] PGS/bitmap Track#{t.index} ({t.codec})")
            continue

        # Sadece İngilizce, CJK (Japonca/Korece/Çince vb.) veya dili tanımlanmamış (und) olanları çıkarıyoruz.
        # Almanca, Fransızca, Arapça, Farsça vb. yabancı dildeki altyazıları eleyerek disk darboğazını ve zaman aşımını önlüyoruz.
        _lang_clean = (t.language or "").lower().strip()
        _is_candidate = t.is_english or t.is_cjk or _lang_clean in ("und", "")
        if not _is_candidate:
            if verbose:
                print(f"  [ATLANDI] Yabancı dil altyazı Track#{t.index} ({t.codec}) lang={t.language!r} title={t.title!r}")
            continue

        if t.is_signs:
            signs_tracks.append(t)  # Artık TAMAMEN atlamıyoruz
            if verbose:
                print(f"  [Signs] Track#{t.index} title={t.title!r} — ekran yazı çevirisi için çıkarılıyor")
        else:
            text_tracks.append(t)

    all_text_tracks = text_tracks + signs_tracks

    if not all_text_tracks:
        return []

    # ── METADATA BAZLI AKILLI ADAY SEÇİMİ ───────────────────────────────────
    # Disk okuma darboğazını önlemek için sadece en yüksek öncelikli diyalog, 
    # signs ve referans (cjk) adaylarını seçip çıkarıyoruz.
    best_dialogue = None
    best_d_score = -9999.0
    best_signs = None
    best_s_score = -9999.0
    best_ref = None
    best_r_score = -9999.0

    for t in all_text_tracks:
        d_score = score_track_by_metadata(t)
        if d_score > best_d_score:
            best_d_score = d_score
            best_dialogue = t

        s_score = score_signs_track_by_metadata(t)
        if s_score > best_s_score:
            best_s_score = s_score
            best_signs = t

        r_score = score_reference_track_by_metadata(t)
        if r_score > best_r_score:
            best_r_score = r_score
            best_ref = t

    selected_tracks = []
    if best_dialogue and best_d_score > 0:
        selected_tracks.append(best_dialogue)
    if best_signs and best_s_score > 0 and best_signs != best_dialogue:
        selected_tracks.append(best_signs)
    if best_ref and best_r_score > 0 and best_ref not in (best_dialogue, best_signs):
        selected_tracks.append(best_ref)

    if verbose:
        print(f"  [Tracks] En iyi adaylar seçildi: Diyalog=Track#{best_dialogue.index if best_dialogue else 'Yok'} ({best_d_score:.1f}), "
              f"Signs=Track#{best_signs.index if best_signs else 'Yok'} ({best_s_score:.1f}), "
              f"Referans=Track#{best_ref.index if best_ref else 'Yok'} ({best_r_score:.1f})")

    all_text_tracks = selected_tracks

    if not all_text_tracks:
        return []

    # ── TEK FFMPEG KOMUTU ile tüm text track'leri çıkar ─────────────────────
    # Her track için ayrı ffmpeg açmak yerine hepsini aynı anda çıkarıyoruz.
    # 10 track için önceden 10x ffmpeg (her biri büyük dosyayı açıp kapatıyor).
    # Şimdi 1x ffmpeg → ~10x hız artışı.
    ffmpeg = ffmpeg or _find_ff_tool("ffmpeg")
    base   = os.path.splitext(os.path.basename(video_path))[0]

    # Çıkarılmamış track'leri bul (zaten çıkarılmış olanlar geç)
    to_extract = []
    for t in all_text_tracks:
        lang      = t.language or "und"
        signs_sfx = "_signs" if t.is_signs else ""
        fname     = f"{base}_track{t.index}_{lang}{signs_sfx}.ass"
        out       = os.path.join(output_dir, fname)
        if os.path.exists(out) and os.path.getsize(out) > 0:
            t.extracted_path = out  # Önbellek
        else:
            to_extract.append((t, out))

    if to_extract:
        # Büyük dosya tespiti (REMUX veya 10GB+ dosyalar)
        try:
            fsize_gb = os.path.getsize(video_path) / (1024 * 1024 * 1024)
            if fsize_gb > 8.0:
                print(f"  [WARN] buyuk video dosyasi tespit edildi ({fsize_gb:.1f} GB).")
                print(f"         Yavas mekanik disklerde (HDD) altyazı cikarma islemi 5-15 dakika surebilir.")
                print(f"         Lutfen islem tamamlanana kadar bekleyin...")
        except Exception:
            pass

        # Tek komutla hepsini çıkar: ffmpeg -i video -map 0:X out1 -map 0:Y out2 ...
        cmd = [ffmpeg, "-y", "-v", "error", "-i", video_path]
        for t, out in to_extract:
            cmd += ["-map", f"0:{t.index}"]
            if t.codec == "ass":
                cmd += ["-c:s", "copy"]
            cmd += [out]
        if verbose:
            print(f"  [Tracks] {len(to_extract)} track çıkarılıyor (tek komut)...")
        result = _run(cmd, timeout=1200)  # 20dk: çok track'li büyük veya yavaş sürücüdeki dosyalar için
        if verbose:
            print(f"  [DEBUG] ffmpeg returncode={result.returncode}, stderr={result.stderr[:200]!r}")
        if result.returncode != 0 and "TIMEOUT" in result.stderr:
            print(f"  [!] Track çıkarma zaman aşımı (20dk) — atlanıyor")
            return []

        for t, out in to_extract:
            if os.path.exists(out) and os.path.getsize(out) > 0:
                t.extracted_path = out
            else:
                if verbose:
                    print(f"  [HATA] Track#{t.index} çıkarılamadı.")

    # ── Kalite skoru ve özet ────────────────────────────────────────────────
    usable = []
    for t in all_text_tracks:
        if not t.extracted_path:
            continue
        if t.is_english and not t.is_signs:
            q = score_subtitle_file(t.extracted_path)
            t.quality_score = q["score"]
            t.quality_label = q["label"]
            t.quality_reasons = q["reasons"]
        usable.append(t)
        if verbose:
            lang_str  = f"lang={t.language!r}" if t.language else ""
            title_str = f"title={t.title!r}"   if t.title    else ""
            q_str     = (f"Quality={t.quality_score}/100 [{t.quality_label}]"
                         if t.quality_score >= 0 else "")
            parts = filter(None, [lang_str, title_str, q_str])
            print(f"  [Track#{t.index}] {' | '.join(parts)}")

    return usable


def select_best_english(tracks: List[SubtitleTrack]) -> Optional[SubtitleTrack]:
    """
    En yüksek kalite skoruna sahip İngilizce (diyalog) track'i döndürür.
    Signs track'leri hariç tutulur.
    Fallback: Eğer normal İngilizce track yoksa SDH/CC track'i kabul et
    (Supernatural gibi dizilerde tek track SDH olabilir).
    """
    eng_tracks = [t for t in tracks if t.is_english and t.extracted_path and not t.is_signs]
    if eng_tracks:
        return max(eng_tracks, key=lambda t: (t.quality_score, -t.index))
    # Fallback: SDH/CC başlıklı track'leri de dene
    sdh_tracks = [
        t for t in tracks
        if t.extracted_path and t.is_english
        and any(k in t.title.lower() for k in ("sdh", "cc", "closed"))
    ]
    if sdh_tracks:
        print(f"  [Tracks] Normal İng. track yok, SDH/CC fallback kullanılıyor: Track#{sdh_tracks[0].index}")
        return sdh_tracks[0]
    return None


def select_signs_track(tracks: List[SubtitleTrack]) -> Optional[SubtitleTrack]:
    """
    İngilizce Signs & Songs track'ini döndürür (ekran yazı çevirisi için).
    """
    signs = [t for t in tracks if t.is_signs and t.extracted_path and t.is_english]
    if not signs:
        # Lang="und" olanlar da dene (bazı fansub grupları "und" yazar)
        signs = [t for t in tracks if t.is_signs and t.extracted_path]
    return signs[0] if signs else None


def merge_ass_with_signs(main_path: str, signs_path: str, output_path: str) -> bool:
    """
    Ana diyalog ASS dosyası ile Signs track ASS dosyasını birleştirir.
    Signs dosyasındaki event'ler ana dosyanın sonuna eklenir.
    Sonuç output_path'e yazılır.
    Döner: True=başarılı, False=hata
    """
    return merge_ass_with_signs_smart(main_path, signs_path, output_path)


# ── Karaoke / Song event filtresi ────────────────────────────────────────────

_KARA_TAG_RE = re.compile(r'\\[Kk][fFoO]?\d*', re.IGNORECASE)  # \k, \K, \kf, \ko, \K100 vb.

_SONG_STYLE_WORDS = re.compile(
    r'karaoke|kara(?!oke)|\bop\b|\bed\b|opening|ending|lyric|song|'
    r'credit|staff|romaji|jp[-_]?song|en[-_]?song|insert',
    re.IGNORECASE
)

_SIGN_STYLE_WORDS = re.compile(
    r'sign|screen|onscreen|title|text|note|info|banner|lower|upper|caption',
    re.IGNORECASE
)


def _is_karaoke_event(dialogue_line: str) -> bool:
    """
    Bir Dialogue: satırının karaoke/şarkı eventi olup olmadığını tespit eder.
    True → atla (merge'e dahil etme)
    """
    parts = dialogue_line.split(',', 9)
    if len(parts) < 10:
        return False
    style = parts[3].strip()
    text  = parts[9]

    # 1) Karaoke timing tag'i var mı?
    if _KARA_TAG_RE.search(text):
        return True

    # 2) Stil adı açıkça song/karaoke/OP/ED ise
    if _SONG_STYLE_WORDS.search(style):
        return True

    # 3) Stil adı "sign" içeriyorsa → gerçek ekran yazısı → HAYIR, filtreleme
    if _SIGN_STYLE_WORDS.search(style):
        return False

    # 4) Çok kısa metin + tag ağırlıklı → karaoke hecesi olabilir
    clean = re.sub(r'\{[^}]*\}', '', text).strip()
    if len(clean) <= 3:
        return True

    return False


def _has_song_events(ass_path: str) -> bool:
    """
    Diyalog dosyasında OP/ED/şarkı stili event var mı kontrol eder.
    Varsa Signs merge'i yaparken şarkı eventleri filtreleyelim.
    """
    try:
        with open(ass_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if not line.startswith('Dialogue:'):
                    continue
                parts = line.split(',', 9)
                if len(parts) < 10:
                    continue
                style = parts[3].strip()
                if _SONG_STYLE_WORDS.search(style):
                    return True
    except Exception:
        pass
    return False


def merge_ass_with_signs_smart(main_path: str, signs_path: str, output_path: str) -> bool:
    """
    Akıllı merge: Signs dosyasından sadece GERÇEK ekran yazılarını alır.
    Karaoke eventleri (\k tag'li), song/OP/ED stil adlı satırlar filtrelenir.
    Böylece diyalog dosyası + sign görseli çakışması önlenir.
    Döner: True=başarılı (en az 1 sign eventi eklendi), False=merge gerekmedi
    """
    try:
        with open(main_path,  'r', encoding='utf-8', errors='replace') as f:
            main_content = f.read()
        with open(signs_path, 'r', encoding='utf-8', errors='replace') as f:
            signs_content = f.read()

        # Diyalog dosyasında zaten şarkı eventleri var mı?
        _main_has_songs = _has_song_events(main_path)

        # Signs dosyasındaki Dialogue satırlarını filtrele
        signs_dialogues_raw = [
            line for line in signs_content.splitlines()
            if line.startswith('Dialogue:')
        ]

        # Karaoke / song eventlerini filtrele
        # Eğer diyalog dosyası şarkı içeriyorsa, signs dosyasındaki şarkı satırları
        # kesinlikle filtrele (çift katman oluşmasın).
        # Diyalog dosyası şarkı içermiyorsa da karaoke tag'leri filtrele.
        signs_dialogues = []
        filtered_count  = 0
        for line in signs_dialogues_raw:
            if _is_karaoke_event(line):
                filtered_count += 1
                continue
            signs_dialogues.append(line)

        if not signs_dialogues:
            # Tüm eventler filtrelendi — merge'e gerek yok
            if filtered_count > 0:
                print(f"  [Signs] {filtered_count} karaoke/song eventi filtrelendi — signs merge atlandı (diyalog yeterli)")
            return False

        if filtered_count > 0:
            print(f"  [Signs] {filtered_count} karaoke/song eventi filtrelendi, {len(signs_dialogues)} gerçek ekran yazısı ekleniyor")

        # Styles: signs dosyasındaki style tanımlarını main'e ekle (yoksa)
        main_styles = set()
        for line in main_content.splitlines():
            if line.startswith('Style:'):
                main_styles.add(line.split(',')[0])  # Style: Name

        extra_styles = []
        for line in signs_content.splitlines():
            if line.startswith('Style:'):
                style_key = line.split(',')[0]
                if style_key not in main_styles:
                    extra_styles.append(line)
                    main_styles.add(style_key)

        # Main içeriğine ekle
        lines = main_content.split('\n')
        result_lines = []
        for line in lines:
            result_lines.append(line)
            if line.strip() == '[Events]':
                if extra_styles:
                    for es in extra_styles:
                        result_lines.insert(-1, es)

        # Sona signs dialogue satırlarını ekle
        result_lines.extend(signs_dialogues)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result_lines))
        return True
    except Exception as e:
        print(f"  [!] ASS merge hatası: {e}")
        return False


def select_reference(tracks: List[SubtitleTrack],
                     best_english: Optional[SubtitleTrack],
                     quality_threshold: int = 65) -> Optional[SubtitleTrack]:
    """
    En iyi İngilizce track'in kalitesi threshold'un altındaysa,
    Japonca (veya başka CJK/orijinal) bir referans track döndürür.

    Döner: SubtitleTrack (Japonca) veya None (referansa gerek yok)
    """
    if best_english is None:
        return None
    if best_english.quality_score >= quality_threshold:
        return None  # İngilizce zaten yeterince iyi

    # Japonca önce, sonra diğer CJK dilleri
    jp_tracks  = [t for t in tracks if t.is_japanese   and t.extracted_path]
    cjk_tracks = [t for t in tracks if t.is_cjk        and t.extracted_path
                  and not t.is_japanese]

    candidates = jp_tracks + cjk_tracks
    if not candidates:
        return None

    # En az satır içereni eleme (genellikle eksik/bozuk track)
    return max(candidates, key=lambda t: _count_dialogues(t.extracted_path))


def read_dialogue_lines(filepath: str) -> List[str]:
    """
    ASS dosyasından tag'siz diyalog metinlerini sıralı liste olarak döndürür.
    Çift kaynaklı çeviride referans for satırlarını hizalamak için kullanılır.
    """
    lines = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for raw in f:
                if not raw.startswith('Dialogue:'):
                    continue
                parts = raw.split(',', 9)
                if len(parts) < 10:
                    continue
                text = re.sub(r'\{[^}]*\}', '', parts[9])
                text = text.replace('\\N', ' ').replace('\\n', ' ').strip()
                lines.append(text if text else '')
    except Exception:
        pass
    return lines


# ── İç yardımcılar ──────────────────────────────────────────────────────────

def _count_dialogues(filepath: Optional[str]) -> int:
    if not filepath or not os.path.isfile(filepath):
        return 0
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.startswith('Dialogue:'):
                    parts = line.split(',', 9)
                    if len(parts) >= 10:
                        text = re.sub(r'\{[^}]*\}', '', parts[9]).strip()
                        if text:
                            count += 1
    except Exception:
        pass
    return count


# ── Hızlı test ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Kullanım: python subtitle_tracks.py <video_veya_ass_dosyası>")
        sys.exit(0)
    path = sys.argv[1]
    if path.lower().endswith(('.mkv', '.mp4', '.avi', '.webm')):
        out_dir = os.path.join(os.path.dirname(path), "_tracks_test")
        all_tracks = extract_all_tracks(path, out_dir, verbose=True)
        best_en  = select_best_english(all_tracks)
        ref      = select_reference(all_tracks, best_en)
        print(f"\nEn iyi İngilizce : {best_en}")
        print(f"Referans track   : {ref}")
    else:
        q = score_subtitle_file(path)
        print(f"Kalite skoru: {q['score']}/100 [{q['label']}]")
        print(f"Nedenler    : {', '.join(q['reasons']) or 'yok'}")
