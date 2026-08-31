# Altyazı Çeviri Paneli - Altyapı Kod Tabanı

Bu paket, **Altyazı Çeviri Paneli** (`ng_app.py` / `baslat_gizli.vbs`) aracının çalışması için gerekli tüm kod tabanını, bağımlılıkları, modülleri ve konfigürasyon dosyalarını içerir.

---

## 📁 Dizin Yapısı ve Modül Sorumlulukları

### 1. `Sadece Çeviri/` (Kullanıcı Arayüzü & Giriş Noktaları)
- **`ng_app.py`**: NiceGUI tabanlı modern web arayüzlü çeviri panelinin ana giriş noktasıdır.
- **`ng_config.py`**: Panel parametreleri, tema ayarları ve port/oturum yapılandırmasını yönetir.
- **`ng_pages_a.py` & `ng_pages_b.py`**: Arayüz sayfaları (Dosya Çevirisi, Toplu Çeviri, Ayarlar, Terim Tabanı Yönetimi).
- **`ng_styles.py`**: Panelin CSS / Glassmorphism görsel stil tanımlamaları.
- **`manual_gui.py` & `manual_translator.py`**: Standalone / CustomTkinter çeviri modülü adaptörü.
- **`baslat_gizli.vbs`**: Arka planda konsol penceresi olmadan panelin başlatılmasını sağlar.

### 2. `Python kodları/` (Çekirdek Çeviri Motoru & Mantık Düzeyi)
- **`translator.py`**: Google Gemini API entegrasyonu, rate-limit yönetimi, API anahtar döngüsü ve çeviri taleplerinin yönetildiği temel motor.
- **`subtitle_processor.py`**: ASS/SRT altyazı ayrıştırma, bloklama, stil koruma, çizim vektörlerini eleme ve çeviri sonrası birleştirme mantığı.
- **`fandom_glossary.py`**: AniList / Fandom Wiki üzerinden otomatik anime/dizi terimler sözlüğü (glossary) oluşturma ve doğrulama.
- **`termbase_manager.py` & `offline_db_manager.py`**: Özel terim tabanı saklama ve çevrimdışı başlık/isim sorgu entegrasyonu.
- **`ass_*` modülleri (`ass_line_filter.py`, `ass_tag_extractor.py`, vb.)**: Advanced SubStation Alpha (.ass) altyazı dosyalarındaki karmaşık efekt ve etiketleri koruyan ayrıştırıcılar.
- **`_vendor/`**: `pysubs2`, `ass_tag_parser` ve `pyonfx` gibi dış kütüphanelerin yerel (kendi paket içi) bağımlılıkları.

### 3. Konfigürasyon ve Sözlük Dosyaları (`Python kodları/` İçinde)
- **`translator_config.json` & `user_preferences.json`**: Kullanıcı tercihleri ve çeviri yapılandırmaları.
- **`prompt_template.json`**: Gemini LLM modeline gönderilen çeviri talimatları ve sistem promptları.
- **`api_keys.txt` & `api_keys_WORKING.txt`**: Kullanılan Gemini API anahtar listesi.
- **`tr_words_frequency.txt` & `tr_words_wiktionary.txt`**: Türkçe dil tespiti ve kelime doğrulama frekans veritabanları.

---

## 🚀 Çalıştırma

- **Sessiz Çalıştırma (Önerilen)**: `BAŞLAT.bat` veya `Sadece Çeviri/baslat_gizli.vbs` dosyasına çift tıklayın.
- **Konsol ile Çalıştırma**: `Sadece Çeviri/baslat_nicegui.bat` çalıştırın.
