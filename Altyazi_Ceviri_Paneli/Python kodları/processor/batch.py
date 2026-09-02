"""
processor/batch.py
==================
Animasyon frame collapse, broadcast ve byte-bazlı batch oluşturma.
"""
import re
import difflib

try:
    from rapidfuzz import fuzz as _rfuzz
    _RAPIDFUZZ_OK = True
except ImportError:
    _rfuzz = None
    _RAPIDFUZZ_OK = False

# restore_tags / restore_tags_from_placeholders geç import (döngüsel bağımlılık önlemi)
def _get_tag_restorers():
    try:
        from processor.tag_tools import restore_tags, restore_tags_from_placeholders
        return restore_tags, restore_tags_from_placeholders
    except ImportError:
        return lambda t, tags: t, lambda t, m: t

def collapse_animation_frames(events):
    """
    Ardisik, ayni temiz metne sahip Signs animasyon karelerini
    tek bir event'e birlestir.

    Ornek:
      Frame 1: 0:09:23.00->0:09:23.04  pos(1075,183) "Do you know what time"
      Frame 2: 0:09:23.04->0:09:23.08  pos(1075,184) "Do you know what time"
      ...25 kare...
      -> BIRLESTIRILMIS: 0:09:23.00->0:09:26.04  "Do you know what time"  (tek API cagrisi)

    Kural:
      - Sadece is_sign=True olan eventler
      - Ardisik (index olarak komsu) ve ayni temiz metin
      - Farkli timing = farkli sahneler → birlestirilmez
        (iki kare arasi bosluk > 500ms ise yeni sahne)
      - Birlestirilen event: ilk karenin ASS tagleri + start, son karenin end
      - Birlestirilen eventler 'collapsed_count' ile isaretlenir

    Returns: yeni events listesi (birlestirilmis + birlestirilmemis)
    """
    if not events:
        return events

    # ASS time -> ms cevirici
    def _t2ms(ts):
        try:
            h, m, rest = ts.strip().split(':')
            s, cs = rest.split('.')
            return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(cs)*10
        except Exception:
            return 0

    def _ms2t(ms):
        h  = ms // 3600000; ms %= 3600000
        m  = ms // 60000;   ms %= 60000
        s  = ms // 1000;    cs = (ms % 1000) // 10
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    TAG_RE_LOCAL = re.compile(r'\{[^}]*\}')
    def _clean(t):
        return TAG_RE_LOCAL.sub('', t).strip().lower()

    MAX_GAP_MS = 500  # iki kare arasi max bosluk (ms)

    result = []
    i = 0
    collapsed_total = 0

    while i < len(events):
        ev = events[i]

        # Sadece Signs efentleri collapse edilir
        if not ev.get('is_sign'):
            result.append(ev)
            i += 1
            continue

        # Bu karenin temiz metni
        base_clean = _clean(ev.get('text', ''))
        if not base_clean:
            result.append(ev)
            i += 1
            continue

        # Ayni temiz metne sahip ardisik kareleri topla
        group = [ev]
        j = i + 1
        while j < len(events):
            nev = events[j]
            if not nev.get('is_sign'):
                break
            n_clean = _clean(nev.get('text', ''))
            if n_clean != base_clean:
                break
            # Zaman boslugu kontrolu
            prev_end_ms   = _t2ms(group[-1].get('end', group[-1].get('parts', ['','',''])[2] if group[-1].get('parts') else '0:00:00.00'))
            next_start_ms = _t2ms(nev.get('start', nev.get('parts', ['','',''])[1] if nev.get('parts') else '0:00:00.00'))
            if next_start_ms - prev_end_ms > MAX_GAP_MS:
                break  # Bosluk cok buyuk = yeni sahne
            group.append(nev)
            j += 1

        if len(group) == 1:
            # Tek kare, collapse gerekmez
            result.append(ev)
            i += 1
            continue

        # COLLAPSE: ilk karenin start, son karenin end
        first = group[0]
        last  = group[-1]
        first_start = first.get('start', first.get('parts', ['','',''])[1] if first.get('parts') else '')
        last_end    = last.get('end',   last.get('parts',  ['','','',''])[2] if last.get('parts') else '')

        # [FIX KRİTİK] deepcopy yerine first dict'ini DOĞRUDAN güncelle.
        # deepcopy ile merged yeni bir obje olur → structured_events'teki first (İngilizce)
        # güncellenmez → rescue İngilizce görür ve yeniden çevirir (2500+ false rescue).
        # Orijinal objeyi güncelleyince batch yazımı doğrudan structured_events'e yansır.
        first['start']  = first_start
        first['end']    = last_end
        first['collapsed_count'] = len(group)
        first['_collapsed_group'] = group  # broadcast için sakla

        # parts listesindeki start/end de güncelle
        if first.get('parts') and len(first['parts']) >= 3:
            first['parts'][1] = first_start
            first['parts'][2] = last_end

        result.append(first)
        collapsed_total += len(group) - 1  # kaçını atlayacağız
        i = j  # j'ye atla (grubun sonu)


    if collapsed_total > 0:
        print(f"   [FrameCollapse] {collapsed_total} animasyon karesi "
              f"{sum(1 for e in result if e.get('collapsed_count', 0) > 1)} gruba birlestirildi")

    return result



def _string_similarity(s1: str, s2: str) -> float:
    """
    Hızlı string benzerliği.
    rapidfuzz kuruluysa token_set_ratio kullanır (kelime sırası bağımsız),
    yoksa difflib.SequenceMatcher'a düşer.
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    if _RAPIDFUZZ_OK:
        return _rfuzz.token_set_ratio(s1, s2) / 100.0
    # difflib fallback (özyineleme kaldırıldı!)
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def broadcast_collapsed_frames(events):
    """
    collapse_animation_frames() ile birlestirilen event'lerin cevirisini
    tum orijinal karelere yayar.

    Yayim kurali:
      - Birlestirilen event'in cevrilmis metni alinir (tag'ler siyrilmis)
      - Her orijinal kareye KENDI ASS tag'leri + cevrilmis metin yazilir
      - Birlestirilen event YERINE tum orijinal kareler listeye eklenir
        (animasyon efekti korunur; sadece metin Turkce olur)
    """
    if not any(e.get('collapsed_count', 0) > 1 for e in events):
        return events  # Hicbir collapse yok, hizlica don

    TAG_RE_L = re.compile(r'\{[^}]*\}')
    BRACKET_P = re.compile(r'\{[^}]*\}')

    result = []
    broadcast_count = 0

    for ev in events:
        if ev.get('collapsed_count', 0) <= 1:
            result.append(ev)
            continue

        # Birlestirilen event'in cevrilmis metnini al
        translated_full = ev.get('text', ev.get('parts', [''] * 10)[9] if ev.get('parts') else '')
        # Sadece saf ceviri metnini al (tagleri siyir)
        translated_clean = BRACKET_P.sub('', translated_full).strip()
        translated_clean = re.sub(r'__T\d+__', '', translated_clean).strip()

        if not translated_clean:
            # Ceviri bos geldiyse orijinal grubun ilk karesini yaz, gerisi atla
            result.append(ev)
            continue

        # Orijinal karelere ceviriyi yay
        group = ev.get('_collapsed_group', [ev])
        for frame in group:
            frame_copy = dict(frame)
            # Kareye ozgu ASS tag'lerini al
            frame_tags = frame.get('tags', [])
            frame_tag_map = frame.get('tag_map', {})

            if frame_tag_map:
                final_text = restore_tags_from_placeholders(translated_clean, frame_tag_map)
            elif frame_tags:
                final_text = restore_tags(translated_clean, frame_tags)
            else:
                final_text = translated_clean

            frame_copy['text'] = final_text
            if frame_copy.get('parts') and len(frame_copy['parts']) >= 10:
                frame_copy['parts'][9] = final_text
            # [FIX1] _pysubs2_ev dogrudan guncelle (tag blogu koru)
            _bc_ev_ref = frame.get('_pysubs2_ev')
            if _bc_ev_ref is not None:
                _orig_bc_text = _bc_ev_ref.text or ''
                _bc_tag_block = re.search(r'^((?:\{[^}]*\})+)', _orig_bc_text)
                if _bc_tag_block and final_text and not final_text.startswith('{'):
                    _bc_ev_ref.text = _bc_tag_block.group(1) + final_text
                else:
                    _bc_ev_ref.text = final_text
            # Collapse isaretini kaldir (broadcast edildi)
            frame_copy.pop('collapsed_count', None)
            frame_copy.pop('_collapsed_group', None)
            result.append(frame_copy)
            broadcast_count += 1

    if broadcast_count > 0:
        print(f"   [FrameCollapse] {broadcast_count} kareye ceviri yayildi")

    return result

def create_byte_based_batches(events, max_bytes, max_lines=None):
    """
    Subtitle Edit yaklaşımı: Satır sayısı yerine byte sayısına göre batch oluştur.
    Bu, uzun satırlar olduğunda API rate limit'e çarpmayı önler.

    Args:
        events:    İşlenecek event listesi
        max_bytes: Batch başına maksimum byte sayısı (örn: 2000)
        max_lines: Batch başına maksimum satır sayısı (UI'dan gelir, örn: 10)
                   None = sınırsız (sadece byte limitine bak)

    Returns:
        Batch'lere bölünmüş event listesi
    """
    batches = []
    current_batch = []
    current_bytes = 0

    for event in events:
        text = event.get("text", "")
        # UTF-8 byte sayısını hesapla
        text_bytes = len(text.encode('utf-8'))

        # Byte limiti VEYA satır sayısı limiti aşılıyorsa → yeni batch başlat
        byte_full = (current_bytes + text_bytes > max_bytes) and current_batch
        line_full = (max_lines is not None and len(current_batch) >= max_lines)

        if (byte_full or line_full) and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_bytes = 0

        current_batch.append(event)
        current_bytes += text_bytes

    if current_batch:
        batches.append(current_batch)

    return batches

