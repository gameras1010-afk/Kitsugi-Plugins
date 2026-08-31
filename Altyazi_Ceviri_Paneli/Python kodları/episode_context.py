# episode_context.py
# ─────────────────────────────────────────────────────────────────────────────
# Bölümler arası çeviri devamlılığı.
#
# Her bölüm bittikten sonra son N (kaynak, çeviri) satır çiftini
# episode_context.json'a kaydeder. Bir sonraki bölüm başında bu çiftler
# translator'ın sliding window'una "ön yükleme" olarak eklenir.
# Böylece AI ilk batch'te önceki bölümün sonunu görür ve tutarlı devam eder.
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import json
from datetime import datetime, timezone
from typing import List, Tuple, Optional

CONTEXT_FILE  = None   # lazy init → os.getcwd() kullanır
KEEP_PAIRS    = 25     # kaç (src, tr) çifti sakla / yükle (8'den 25'e çıkarıldı)
MAX_PAIR_CHARS = 200   # çift başına maks. karakter (120'den 200'e çıkarıldı)

# ── File path ────────────────────────────────────────────────────────────────

def _ctx_path() -> str:
    # Her zaman episode_context.py ile aynı dizine kaydet (os.getcwd() değil!)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "episode_context.json")


def _load() -> dict:
    p = _ctx_path()
    if os.path.isfile(p):
        try:
            return json.load(open(p, "r", encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    try:
        json.dump(data, open(_ctx_path(), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[EpisodeCtx] Kayıt hatası: {e}")


# ── Seri anahtarı ─────────────────────────────────────────────────────────────

def _make_key(series_title: str, season: Optional[int] = None) -> str:
    """
    "Sword Art Online" + season=1  →  "Sword Art Online|S01"
    "Sword Art Online" + season=None  →  "Sword Art Online"
    """
    key = series_title.strip()
    if season:
        key += f"|S{season:02d}"
    return key


# ── Ana API ──────────────────────────────────────────────────────────────────

def save_episode_context(
    series_title: str,
    pairs: List[Tuple[str, str]],
    season: Optional[int] = None,
    episode: Optional[int] = None,
) -> None:
    """
    Bölüm bitince çağrılır.
    pairs: translator._context_window'dan alınan [(src, tr), ...] listesi.
    """
    if not series_title or not pairs:
        return

    key   = _make_key(series_title, season)
    store = _load()

    # Eğer aynı bölüm yeniden işleniyorsa (diff==0) mevcut kaydi KORUMA, üstune yazma
    existing = store.get(key, {})
    existing_ep = existing.get("episode")
    if existing_ep is not None and episode is not None:
        try:
            if int(existing_ep) == int(episode) and len(existing.get("pairs", [])) >= KEEP_PAIRS // 2:
                # Aynı bölüm yeterli bağlam var, üstune yazma
                print(f"[EpisodeCtx] '{key}' Bölüm {episode} zaten kayitli — korunuyor.")
                return
        except (ValueError, TypeError):
            pass

    # Son KEEP_PAIRS çifti sakla; çok uzun metinleri kırp
    trimmed = [
        (src[:MAX_PAIR_CHARS], tr[:MAX_PAIR_CHARS])
        for src, tr in pairs[-KEEP_PAIRS:]
    ]

    store[key] = {
        "pairs":      trimmed,
        "episode":    episode,
        "saved_at":   datetime.now(timezone.utc).isoformat(),
    }
    _save(store)
    print(f"[EpisodeCtx] '{key}' — {len(trimmed)} çift kaydedildi "
          f"(bölüm {episode or '?'})")


def load_episode_context(
    series_title: str,
    season: Optional[int] = None,
    current_episode: Optional[int] = None,
) -> List[Tuple[str, str]]:
    """
    Bir sonraki bölüm başında çağrılır.
    Önceki bölümün son çiftlerini döndürür.
    Kayıt yoksa boş liste döner.

    current_episode verilirse sıra kontrolü yapılır:
    Kaydedilen bölüm current_episode - 1 değilse → yükleme atlanır.
    Bu, sırasız çeviride yanlış bağlam karışmasını önler.
    """
    if not series_title:
        return []

    key   = _make_key(series_title, season)
    store = _load()
    entry = store.get(key)
    if not entry:
        return []

    # ── Sıra güvenlik kontrolü ───────────────────────────────────────────────
    saved_ep = entry.get("episode")
    if current_episode and saved_ep:
        try:
            diff = int(current_episode) - int(saved_ep)
            # diff == 0 → aynı bolum yeniden isleniyor (gecerli, yukle)
            # diff == 1 → bir sonraki bolum (ideal, yukle)
            if diff < 0:
                print(f"[EpisodeCtx] Geriye gidis: kayit E{saved_ep}, "
                      f"simdi E{current_episode} → bagiam atlanıyor.")
                return []
            elif diff > 1:
                print(f"[EpisodeCtx] Uyari: {diff-1} bolum atlanmis "
                      f"(E{saved_ep} → E{current_episode}) → bagiam yine de yuklendi.")
            # diff == 0: ayni bolum tekrar → sessizce yukle
            # diff == 1: ideal siradaki bolum → yukle
        except (ValueError, TypeError):
            pass  # Sayisal degilse kontrolu atla
    # ────────────────────────────────────────────────────────────────────────

    pairs = [(src, tr) for src, tr in entry.get("pairs", [])]
    if pairs:
        ep = entry.get("episode", "?")
        print(f"[EpisodeCtx] '{key}' — bölüm {ep}'den {len(pairs)} bağlam çifti yüklendi")
    return pairs


def clear_series_context(series_title: str, season: Optional[int] = None) -> None:
    """Bir seri/sezon kaydını siler."""
    key   = _make_key(series_title, season)
    store = _load()
    if key in store:
        del store[key]
        _save(store)
        print(f"[EpisodeCtx] '{key}' temizlendi.")
