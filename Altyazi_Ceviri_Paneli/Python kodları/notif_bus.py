"""
notif_bus.py — Pipeline → NiceGUI Bildirim Köprüsü

Pipeline (subprocess/thread) buraya yazar.
NiceGUI UI bunu polling ile okur ve ui.notify() ile gösterir.

Kullanım (pipeline tarafı):
    from notif_bus import push_notif
    push_notif("Cache'den alındı ✅", "positive")
    push_notif("AniDB 403 hatası", "warning")

Kullanım (UI tarafı):
    from notif_bus import flush_notifs
    for n in flush_notifs():
        ui.notify(n['msg'], type=n['type'], timeout=n.get('timeout', 4000))
"""

import os
import json
import time
import threading

_DIR      = os.path.dirname(os.path.abspath(__file__))
_QUEUE_F   = os.path.join(_DIR, '_notif_queue.jsonl')
_HISTORY_F = os.path.join(_DIR, '_notif_history.jsonl')
_MAX_HISTORY = 500   # Maksimum saklanacak bildirim sayısı
_LOCK     = threading.Lock()

# ── Notification tipleri → NiceGUI type mapping ──────────────────────────
# 'positive' → yeşil  | 'negative' → kırmızı | 'warning' → sarı
# 'info'     → mavi   | 'ongoing'  → spinner

def push_notif(msg: str, ntype: str = 'info', timeout: int = 4000, icon: str = ''):
    """
    Pipeline tarafından çağrılır.
    Thread-safe ve subprocess-safe (file append).
    Hem anlık kuyruğa hem kalıcı geçmişe yazar.
    """
    entry = {
        'msg':     msg,
        'type':    ntype,
        'timeout': timeout,
        'ts':      time.time(),
    }
    if icon:
        entry['icon'] = icon
    line = json.dumps(entry, ensure_ascii=False) + '\n'
    try:
        with _LOCK:
            # Anlık kuyruk (UI polling için)
            with open(_QUEUE_F, 'a', encoding='utf-8') as f:
                f.write(line)
            # Kalıcı geçmiş (Bildirimler sayfası için)
            with open(_HISTORY_F, 'a', encoding='utf-8') as f:
                f.write(line)
            # Geçmiş dosyası büyükse kırp
            _trim_history()
    except Exception:
        pass   # Bildirim gönderimi hiçbir zaman pipeline'ı durdurmaz


def flush_notifs() -> list:
    """
    UI tarafından çağrılır — bekleyen tüm bildirimleri döndürür ve siler.
    Eski (>30 sn) bildirimleri otomatik atar.
    """
    if not os.path.exists(_QUEUE_F):
        return []
    entries = []
    now = time.time()
    try:
        with _LOCK:
            with open(_QUEUE_F, 'r', encoding='utf-8') as f:
                raw = f.read()
            # Oku ve temizle (atomic olmayan ama yeterli)
            open(_QUEUE_F, 'w', encoding='utf-8').close()
        for line in raw.strip().splitlines():
            if not line.strip():
                continue
            try:
                n = json.loads(line)
                # 30 saniyeden eski bildirimleri gösterme (pipeline durmuşsa)
                if now - n.get('ts', 0) < 30:
                    entries.append(n)
            except Exception:
                pass
    except Exception:
        pass
    return entries


def clear_queue():
    """Kuyruğu tamamen temizle (yeni çeviri başlarken)."""
    try:
        with _LOCK:
            open(_QUEUE_F, 'w', encoding='utf-8').close()
    except Exception:
        pass


def _trim_history():
    """Geçmiş dosyasını _MAX_HISTORY satıra kırp. _LOCK içinde çağrılmalı."""
    try:
        if not os.path.exists(_HISTORY_F):
            return
        with open(_HISTORY_F, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if len(lines) > _MAX_HISTORY:
            with open(_HISTORY_F, 'w', encoding='utf-8') as f:
                f.writelines(lines[-_MAX_HISTORY:])
    except Exception:
        pass


def get_history(limit: int = 200) -> list:
    """
    Kalıcı bildirim geçmişini döndürür (en yeni önce).
    Bildirimler sayfası için kullanılır.
    """
    if not os.path.exists(_HISTORY_F):
        return []
    entries = []
    try:
        with _LOCK:
            with open(_HISTORY_F, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        for line in reversed(lines[-limit:]):
            try:
                n = json.loads(line.strip())
                if n.get('msg'):
                    entries.append(n)
            except Exception:
                pass
    except Exception:
        pass
    return entries


def clear_history():
    """Bildirim geçmişini tamamen sil."""
    try:
        with _LOCK:
            open(_HISTORY_F, 'w', encoding='utf-8').close()
    except Exception:
        pass


def get_history_stats() -> dict:
    """Geçmiş istatistikleri: toplam, tip dağılımı, son bildirim zamanı."""
    history = get_history(limit=500)
    stats = {'total': len(history), 'positive': 0, 'warning': 0, 'negative': 0, 'info': 0, 'last_ts': 0}
    for n in history:
        t = n.get('type', 'info')
        if t in stats:
            stats[t] += 1
        if n.get('ts', 0) > stats['last_ts']:
            stats['last_ts'] = n['ts']
    return stats
