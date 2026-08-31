import re

def validate_and_fix_position_tags(text, video_width=1920, video_height=1080, max_text_length=50):
    """
    ASS altyazı pozisyon tag'lerini (\\pos, \\an) kontrol eder ve düzeltir.
    
    Sorunları çözer:
    1. Ekran dışına taşan koordinatlar
    2. Uzun metinler için pozisyon ayarı
    3. Geçersiz alignment değerleri
    
    Args:
        text: ASS altyazı metni (tag'ler dahil)
        video_width: Video genişliği (varsayılan 1920)
        video_height: Video yüksekliği (varsayılan 1080)
        max_text_length: Maksimum metin uzunluğu (varsayılan 50)
    
    Returns:
        Düzeltilmiş metin
    """
    if not text or not text.strip():
        return text
    
    # Extract clean text without tags for length check
    clean_text = re.sub(r'\{.*?\}', '', text).strip()
    
    # \\pos(x,y) tag kontrolü
    pos_pattern = re.compile(r'\\\\pos\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?)\)')
    pos_match = pos_pattern.search(text)
    
    if pos_match:
        x = float(pos_match.group(1))
        y = float(pos_match.group(2))
        
        # Margin (güvenlik alanı) - Ekran kenarlarından 50 pixel uzakta tut
        margin = 50
        text_height_estimate = 80  # Ortalama font yüksekliği
        
        # X koordinatı kontrolü (yatay)
        # Uzun metinler için X'i merkeze çek
        if len(clean_text) > max_text_length:
            x = video_width / 2  # Merkeze al
        else:
            # Sınırlar içinde tut
            x = max(margin, min(x, video_width - margin))
        
        # Y koordinatı kontrolü (dikey)
        # Üst sınır kontrolü
        if y < margin:
            y = margin
        # Alt sınır kontrolü
        elif y > video_height - text_height_estimate - margin:
            y = video_height - text_height_estimate - margin
        
        # Uzun metinler için Y'yi biraz yukarı kaydır (taşmayı önle)
        if len(clean_text) > max_text_length * 1.5:
            y = max(margin, y - 40)
        
        # Yeni tag'i oluştur
        new_pos_tag = r"\pos({},{})".format(int(x), int(y))
        text = pos_pattern.sub(new_pos_tag, text)
    
    # \\move tag kontrolü (animasyonlu pozisyon)
    move_pattern = re.compile(r'\\\\move\((\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)')
    move_match = move_pattern.search(text)
    
    if move_match:
        x1, y1, x2, y2 = [float(move_match.group(i)) for i in range(1, 5)]
        
        margin = 50
        
        # Başlangıç ve bitiş koordinatlarını düzelt
        x1 = max(margin, min(x1, video_width - margin))
        y1 = max(margin, min(y1, video_height - margin))
        x2 = max(margin, min(x2, video_width - margin))
        y2 = max(margin, min(y2, video_height - margin))
        
        new_move_tag = r"\move({},{},{},{})".format(int(x1), int(y1), int(x2), int(y2))
        text = move_pattern.sub(new_move_tag, text)
    
    return text


def normalize_alignment_tags(text, default_alignment=2):
    """
    ASS altyazı alignment tag'lerini (\\an1-9) kontrol eder ve normalleştirir.
    
    Alignment Numaraları (Numpad gibi):
    7 8 9  (Üst: Sol, Orta, Sağ)
    4 5 6  (Orta: Sol, Orta, Sağ)
    1 2 3  (Alt: Sol, Orta, Sağ)
    
    Args:
        text: ASS altyazı metni
        default_alignment: Varsayılan alignment (2 = alt orta)
    
    Returns:
        Düzeltilmiş metin
    """
    if not text:
        return text
    
    # \\an tag kontrolü
    an_pattern = re.compile(r'\\\\an(\d)')
    an_match = an_pattern.search(text)
    
    if an_match:
        alignment = int(an_match.group(1))
        
        # Geçersiz alignment değerlerini düzelt (1-9 arası olmalı)
        if alignment < 1 or alignment > 9:
            alignment = default_alignment
            text = an_pattern.sub(r"\\an{}".format(alignment), text)
    else:
        # Eğer alignment tag'i yoksa ve \\pos tag'i varsa, varsayılan ekle
        # Bu, pozisyonlu metinlerin de düzgün hizalanmasını sağlar
        if r'\pos' in text:
            # \\pos varsa genelde orta hizalama kullanılır (5)
            text = text.replace('{', r'{\an5', 1)
    
    return text
