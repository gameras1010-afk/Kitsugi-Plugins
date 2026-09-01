"""
pages/about.py
==============
Hakkında sayfası.
"""
import os, json
from nicegui import ui
from ng_config import (
    C, load_prefs, save_prefs, load_trans_cfg, save_trans_cfg,
    api_counts, REPORT_DIR, REPORTS_CENTRAL_DIR, collect_html_reports,
    API_FILE, EX_FILE, PREFS_FILE, TRANS_CFG, PARENT_DIR, BASE_DIR
)
from pages.helpers import get_prefs, nbtn

def build_about():

    import sys, nicegui as _ng

    def _sec_title(icon, title, color=None):
        col = color or C["CYAN"]
        ui.html(
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;'
            f'padding-bottom:10px;border-bottom:1px solid {C["BORDER"]}">'
            f'<span style="font-size:22px">{icon}</span>'
            f'<div style="font-size:13px;font-weight:800;letter-spacing:1px;color:{col}">{title}</div>'
            f'</div>'
        )

    def _item(num, baslik, aciklama, color=None):
        col = color or C["CYAN"]
        ui.html(
            f'<div style="display:flex;gap:14px;padding:10px 0;border-bottom:1px solid {C["BORDER"]}22">'
            f'<div style="min-width:28px;height:28px;border-radius:50%;'
            f'background:color-mix(in srgb,{col} 20%,transparent);'
            f'border:1px solid {col};display:flex;align-items:center;justify-content:center;'
            f'font-size:11px;font-weight:800;color:{col};flex-shrink:0">{num}</div>'
            f'<div><div style="font-size:13px;font-weight:700;color:{C["TEXT"]};margin-bottom:3px">{baslik}</div>'
            f'<div style="font-size:11px;color:{C["SUB"]};line-height:1.7">{aciklama}</div></div>'
            f'</div>'
        )

    def _badge(icon, text, col="#e2e8f0"):
        return (f'<span style="display:inline-flex;align-items:center;gap:5px;padding:5px 14px;'
                f'border-radius:99px;background:rgba(255,255,255,0.07);'
                f'font-size:11px;font-weight:700;color:{col}">{icon} {text}</span>')

    def _info_row(icon, label, value):
        ui.html(
            f'<div style="display:flex;gap:10px;padding:7px 0;'
            f'border-bottom:1px solid {C["BORDER"]}22;align-items:flex-start">'
            f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{icon}</span>'
            f'<div>'
            f'<span style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{label}: </span>'
            f'<span style="font-size:11px;color:{C["MUTED"]}">{value}</span>'
            f'</div></div>'
        )

    with ui.element("div").classes("page-header"):
        ui.html('<div class="ph-title">ℹ️ Uygulama Hakkında</div>')
        ui.html('<div class="ph-sub">Nexus AI Altyazı Çeviri Paneli — Tam Kullanım Kılavuzu &amp; Özellik Rehberi</div>')

    with ui.element("div").style("padding:0 28px 28px;display:flex;flex-direction:column;gap:20px"):

        # ── Hero Banner ──────────────────────────────────────────────────────────
        ui.html(f"""
        <div style="border-radius:18px;padding:32px 36px;
             background:linear-gradient(135deg,
               color-mix(in srgb,var(--accent1) 22%,transparent),
               color-mix(in srgb,var(--accent2) 14%,transparent));
             border:1px solid color-mix(in srgb,var(--accent1) 38%,transparent)">
          <div style="font-size:11px;font-weight:800;letter-spacing:3px;color:var(--accent2);margin-bottom:8px">
            NEXUS PRO &middot; AI SUBTITLE ENGINE &middot; v3.0
          </div>
          <div style="font-size:26px;font-weight:900;margin-bottom:10px;
               background:linear-gradient(135deg,var(--accent1),var(--accent2));
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">
            Altyazı Çeviri Paneli
          </div>
          <div style="font-size:13px;color:{C['SUB']};line-height:1.9;max-width:760px">
            Anime, dizi ve film altyazılarını <strong style="color:var(--accent1)">yapay zeka</strong> kullanarak
            otomatik olarak Türkçeye çeviren tam donanımlı bir masaüstü panelidir.<br>
            <strong style="color:var(--accent2)">OpenRouter API</strong> üzerinden GPT-4o, Claude, Gemini gibi büyük dil modellerine bağlanır.
            <strong style="color:var(--accent1)">ASS / SRT</strong> formatlarını destekler,
            tag'ları korur, kalite raporu üretir ve sözlük sistemi ile tutarlı çeviri sağlar.
          </div>
          <div style="margin-top:18px;display:flex;flex-wrap:wrap;gap:8px">
            {_badge("🐍", f"Python {sys.version[:6]}")}
            {_badge("🖥️", f"NiceGUI {_ng.__version__}")}
            {_badge("🌐", "OpenRouter API")}
            {_badge("📄", "ASS / SRT / SSA")}
            {_badge("🔒", "Çevrimdışı Arayüz")}
            {_badge("⚡", "FastAPI Backend")}
            {_badge("🎌", "Anime Odaklı")}
            {_badge("🤖", "Çoklu LLM Desteği")}
          </div>
        </div>
        """)

        # ── SATIR 1: Temel Özellikler + Çeviri Pipeline ──────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎯", "UYGULAMA NE İŞE YARAR?", C["CYAN"])
                _item(1, "Otomatik Altyazı Çevirisi",
                      "ASS veya SRT formatındaki altyazı dosyasını seçersiniz; uygulama her satırı "
                      "yapay zekaya gönderir, Türkçe çevirisini dosyaya yazar. Elle hiçbir şey yapmanıza gerek kalmaz.", C["CYAN"])
                _item(2, "Toplu (Batch) İşlem",
                      "Tek seferde birden fazla altyazı dosyasını işleyebilirsiniz. Klasör seçin, "
                      "uygulama sırayla ve hata toleranslı biçimde hepsini çevirir.", C["CYAN"])
                _item(3, "ASS Tag Koruması",
                      "Renk, konum, efekt, italik, kalın gibi tüm ASS biçim kodları çeviri sırasında "
                      "bozulmaz — parser bunları izole eder, AI sadece metni görür.", C["CYAN"])
                _item(4, "Kalite Kontrol Raporu (QA)",
                      "Çeviri bittikten sonra otomatik HTML raporu oluşturulur: zamanlama çakışmaları, "
                      "çok hızlı/yavaş satırlar (CPS), çok uzun satırlar (CPL) ve tag hataları raporlanır.", C["CYAN"])
                _item(5, "Akıllı Cache Sistemi",
                      "Daha önce çevrilen satırlar yerel olarak saklanır. Aynı dosyayı tekrar işlediğinizde "
                      "cache'deki satırlar için API çağrısı yapılmaz — hem hızlı hem ekonomik.", C["CYAN"])
                _item(6, "Çoklu API Anahtarı Rotasyonu",
                      "Birden fazla OpenRouter API anahtarı tanımlayabilirsiniz. Bir anahtar kotasını doldurunca "
                      "sistem otomatik olarak sıradakine geçer, çeviri durmadan devam eder.", C["CYAN"])
                _item(7, "Çoklu Çıkış Formatı",
                      "Çıktı formatını ASS, SRT, VTT veya ALL (hepsi aynı anda) olarak ayarlayabilirsiniz. "
                      "Orijinal ASS yapısı ve stil bilgisi korunur.", C["CYAN"])
                _item(8, "İçerik Tür Tespiti",
                      "Dosya adından Anime / Batı Dizisi / Film türünü otomatik algılar. "
                      "Buna göre hangi API'ların sorgulanacağını ve hangi offline veritabanlarının kullanılacağını belirler.", C["CYAN"])

            with ui.element("div").classes("card"):
                _sec_title("⚙️", "ÇEVİRİ PİPELİNE — ADIM ADIM", C["PURPLE"])
                _item(1, "Dosya Ayrıştırma (Parser)",
                      "ASS/SRT dosyası satır satır okunur. Her satırdaki ASS tag'ları çıkarılır, "
                      "saf metin ayrıştırılır. Romaji, karaoke ve stil suffix etiketleri bu aşamada tespit edilir.", C["PURPLE"])
                _item(2, "İçerik Dedektörü (content_detector)",
                      "Her satır; şarkı sözü, karaoke, yalnızca İngilizce, romaji ya da çeviri gerektirmeyen "
                      "içerik açısından sınıflandırılır. Gereksiz API çağrılarını önler.", C["PURPLE"])
                _item(3, "Fandom Sözlük Entegrasyonu",
                      "Anime/dizi adına göre Fandom Wiki'den otomatik olarak özel isimler, yer adları ve "
                      "organizasyon isimleri çekilir. Bu terimler termbase'e eklenir.", C["PURPLE"])
                _item(4, "Batch Gruplama",
                      "Satırlar ayarlanabilir batch boyutuna (varsayılan 10) ve max byte limitine (2000) "
                      "göre gruplara ayrılır. Her grup tek API çağrısıyla gönderilir.", C["PURPLE"])
                _item(5, "AI Çeviri + Termbase Doğrulaması",
                      "Sistem prompt + glossary + bölüm bağlamı ile LLM'e gönderilir. Cevap gelince "
                      "termbase'deki kritik terimler doğrulanır. Hata varsa API key rotation ile retry yapılır.", C["PURPLE"])
                _item(6, "Max Satır Uzunluğu & CPS Kısaltma",
                      "Çeviri 75 karakteri (ayarlanabilir) aşarsa satır otomatik bölünür ya da AI ile "
                      "kısaltılır. Çok hızlı satırlar (yüksek CPS) ayrıca işaretlenir.", C["PURPLE"])
                _item(7, "Tag Yeniden Birleştirme",
                      "Çevrilen metin orijinal ASS tag'larıyla yeniden birleştirilir. "
                      "Konum, renk ve efekt bilgileri eksiksiz korunur.", C["PURPLE"])
                _item(8, "Dosyaya Yazma & Rapor",
                      "Çevrilmiş satırlar orijinal dosya formatında kaydedilir. Ardından HTML kalite "
                      "raporu üretilir ve merkezi reports/ klasörüne kopyalanır.", C["PURPLE"])

        # ── SATIR 2: Sayfalar + Kritik Ayarlar ───────────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🗂️", "SAYFALAR VE BÖLÜMLERİ", C["CYAN"])
                _item(1, "🏠 Dashboard (Ana Sayfa)",
                      "Genel durum özeti, aktif API anahtarı sayısı, toplam terim sayısı ve son işlem "
                      "bilgileri burada görünür. Hızlı erişim butonları da buradadır.", C["CYAN"])
                _item(2, "🔄 Translate (Çeviri Sayfası)",
                      "Asıl iş burada yapılır. Altyazı dosyasını sürükle-bırak veya seçiciyle eklersiniz. "
                      "Model, batch boyutu, gecikme ayarları yapılır, 'Çeviriyi Başlat' ile işlem başlar. "
                      "İlerleme çubuğu ve log ekranı canlı güncellenir.", C["CYAN"])
                _item(3, "📚 Glossary (Sözlük / Termbase)",
                      "Seri adına göre kategorize edilmiş özel isimler, yer adları, organizasyon ve "
                      "teknik terimler buraya eklenir. Alfabetik, zamana göre veya terim sayısına göre "
                      "sıralama ve çift filtreli arama (Seri Adı + Wiki Slug) mevcuttur.", C["CYAN"])
                _item(4, "✅ QA Report (Raporlar)",
                      "Tüm HTML kalite raporlarını listeleyen sayfa. Merkezi reports/ klasörünü tarar. "
                      "QA aracını bu sayfadan da doğrudan çalıştırabilirsiniz.", C["CYAN"])
                _item(5, "🎨 Tema & Ses",
                      "9 hazır tema arasında geçiş yapılır. Ses efektleri, arka plan resmi, blur ve "
                      "karartma değerleri buradan ayarlanır.", C["CYAN"])
                _item(6, "⚙️ Settings (Ayarlar)",
                      "API anahtarları, çeviri parametreleri (batch boyutu, gecikme, max retry), sistem promptu, "
                      "font boyutu modu, max satır uzunluğu, pipeline toggle'ları ve algılama motoru "
                      "ayarları bu sayfada yönetilir.", C["CYAN"])

            with ui.element("div").classes("card"):
                _sec_title("🔧", "KRİTİK AYARLAR NE ANLAMA GELİR?", C["YELLOW"])
                _item(1, "Font Boyutu Modu",
                      "<b>normalize:</b> Tüm satırlarda aynı boyut kullanılır. "
                      "<b>preserve:</b> Orijinal dosyadaki boyutlar korunur. "
                      "<b>custom:</b> Siz belirlediğiniz sabit bir boyut uygulanır.", C["YELLOW"])
                _item(2, "Max Satır Uzunluğu",
                      "Bir altyazı satırının en fazla kaç karakter olacağını belirler (varsayılan 75). "
                      "Bu sayıyı aşan çeviriler otomatik bölünür ya da AI ile kısaltılır.", C["YELLOW"])
                _item(3, "API Endpoint",
                      "Hangi yapay zeka servisine bağlanılacağını gösterir. Varsayılan OpenRouter'dır "
                      "ancak uyumlu başka bir servis (Ollama, LiteLLM vb.) de kullanılabilir.", C["YELLOW"])
                _item(4, "Doğal Diyalog Modu",
                      "Aktif olduğunda yapay zekaya 'doğal, akıcı, ağdalı olmayan Türkçe kullan' talimatı "
                      "eklenir. Resmi çeviri yerine günlük konuşma diline yakın çeviriler üretilir.", C["YELLOW"])
                _item(5, "Zorla Çevir (Force Translate)",
                      "Normalde daha önce çevrilmiş satırlar cache'den gelir. Bu seçenek aktifse cache "
                      "yoksayılır ve her satır yeniden yapay zekaya gönderilir.", C["YELLOW"])
                _item(6, "NSFW Modu",
                      "Bazı modeller varsayılan olarak küfür veya argo içerikleri sansürler. "
                      "Bu mod aktifken sansürsüz, jargon dahil tam çeviri yapılır.", C["YELLOW"])
                _item(7, "Bölüm Bağlamı (Episode Context)",
                      "Bir serinin birden fazla bölümünü çevirirken önceki bölümlerdeki terimler hatırlanır. "
                      "Karakter isimlerinde ve teknik terimlerde çapraz bölüm tutarlılığı sağlanır.", C["YELLOW"])
                _item(8, "Karaoke & Şarkı Sözü Desteği",
                      "Anime opening/ending şarkılarındaki karaoke satırlarını tespit eder. "
                      "Bunları ayrı bir şiirsel prompt ile çevirir, normal diyalog ile karıştırmaz.", C["YELLOW"])

        # ── SATIR 3: Algılama Motoru + Pro İpuçları ──────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎛️", "ALGILAMA MOTORU TOGGLE'LARI", C["GREEN"])
                _item(1, "Stil Suffix Algılama",
                      "Dosya adındaki EN / JP / KARA gibi suffix'leri tanır. Örneğin dosya adı "
                      "'[EN]' içeriyorsa yalnızca İngilizce satırlar hedef alınır.", C["GREEN"])
                _item(2, "Romaji Bloğu",
                      "Japonca hece içeren satırları tespit eder ve çeviri dışında tutar. "
                      "Şarkı romanizasyonlarının bozulmasını önler.", C["GREEN"])
                _item(3, "Şarkı Sözü Geçişi",
                      "Şarkı sözü olarak algılanan satırlar ayrı bir şiirsel prompt ile işlenir. "
                      "Anlam kaybı olmadan daha lirik bir çeviri üretir.", C["GREEN"])
                _item(4, "Karaoke Collapse",
                      "Hece hece parçalanmış karaoke satırlarını tek bir tam satıra birleştirir, "
                      "ardından çevirir.", C["GREEN"])
                _item(5, "Stili Yoksay (force_no_style)",
                      "Stil suffix analizi devre dışı bırakılır. Tüm satırlar yalnızca içerik "
                      "analizi bazında işlenir.", C["GREEN"])
                _item(6, "İçerik Dedektörü (content_detect)",
                      "Her satır otomatik olarak kategori sınıflandırmasından geçer: "
                      "diyalog / şarkı / romaji / boş / sistem.", C["GREEN"])
                _item(7, "CPS Kısaltma",
                      "Saniyede karakter oranı çok yüksek olan satırları AI ile otomatik kısaltır. "
                      "İzleyicinin okuma hızına uygun altyazı üretir.", C["GREEN"])
                _item(8, "Konum Koruması",
                      "ASS dosyasındaki konum tag'larını çeviri sonrasında da korur. "
                      "Üst yazı / yan yazı gibi özel konumlar bozulmaz.", C["GREEN"])

            with ui.element("div").classes("card"):
                _sec_title("💡", "PRO İPUÇLARI", C["PINK"])
                ipuclari = [
                    ("Sözlüğü Önceden Doldurun",
                     "Çeviri başlatmadan önce Glossary sayfasına karakter isimlerini ekleyin. "
                     "Böylece isimler yanlış çevrilmez ve termbase doğrulaması devreye girer."),
                    ("Batch Boyutunu Küçültün",
                     "API hata veriyorsa Settings'te Batch Boyutu'nu küçültün (örn. 5). "
                     "Daha küçük gruplar daha az hata verir."),
                    ("Gecikme Ekleyin",
                     "Çok sayıda anahtar kullanıyorsanız 'API Gecikmesi'ni 0.5–1 saniyeye ayarlayın. "
                     "Rate limit (429) hatalarını önemli ölçüde azaltır."),
                    ("Tükenmiş Anahtarları Sıfırlayın",
                     "Settings → API Key Yönetimi → 'Tükenmişleri Sıfırla' butonu ile "
                     "tükenmiş anahtarları tekrar aktif listesine taşıyabilirsiniz."),
                    ("Fandom Wiki Bağlayın",
                     "Glossary sayfasında seri adını ve wiki slug'ını girerek Fandom'dan "
                     "otomatik terim çekin. Anime isimlerinde yanlış çeviriyi ortadan kaldırır."),
                    ("QA Raporunu İnceleyin",
                     "Çeviri bittikten sonra QA Report sayfasını açın. Kırmızı = hata, "
                     "sarı = uyarı, yeşil = başarılı. Zamanlama sorunlarını buradan görürsünüz."),
                    ("Sidebar'ı Daraltın",
                     "Ctrl+B kısayolu veya yan ok butonu ile sidebar'ı küçük ikon moduna alın, "
                     "çeviri log ekranı için daha fazla alan kazanın."),
                    ("Sistem Promptunu Özelleştirin",
                     "Settings → Sistem Prompt alanını düzenleyerek yapay zekanın çeviri tarzını "
                     "tamamen kendi isteğinize göre yönlendirin."),
                ]
                for idx, (baslik, acik) in enumerate(ipuclari, 1):
                    ui.html(
                        f'<div style="display:flex;gap:10px;padding:8px 0;'
                        f'border-bottom:1px solid {C["BORDER"]}22">'
                        f'<div style="min-width:22px;height:22px;border-radius:6px;'
                        f'background:color-mix(in srgb,{C["PINK"]} 20%,transparent);'
                        f'border:1px solid {C["PINK"]};display:flex;align-items:center;'
                        f'justify-content:center;font-size:10px;font-weight:800;'
                        f'color:{C["PINK"]};flex-shrink:0">{idx}</div>'
                        f'<div><div style="font-size:12px;font-weight:700;color:{C["TEXT"]};'
                        f'margin-bottom:2px">{baslik}</div>'
                        f'<div style="font-size:10px;color:{C["MUTED"]};line-height:1.6">{acik}</div>'
                        f'</div></div>'
                    )

        # ── SATIR 4: Temalar + Teknik Bilgiler ───────────────────────────────────
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:20px"):

            with ui.element("div").classes("card"):
                _sec_title("🎨", "9 HAZIR TEMA", C["PURPLE"])
                temas = [
                    ("⬡", "Nexus",      "Cyberpunk · Mor & Cyan",    "#7c3aed"),
                    ("✿", "Sakura",     "Anime · Pembe & Rose",       "#c026d3"),
                    ("⊡", "Cyber",      "Matrix · Yeşil & Sarı",      "#00ff87"),
                    ("◈", "Midnight",   "Koyu · Mavi & İndigo",       "#3b82f6"),
                    ("◆", "Ember",      "Ateş · Turuncu & Kırmızı",  "#f97316"),
                    ("❄", "Arctic",     "Buz · Beyaz & Gümüş",       "#94a3b8"),
                    ("⚡", "Neon Tokyo", "Vaporwave · Pembe & Cyan",   "#ff0080"),
                    ("👑", "Gold Rush",  "Premium · Altın & Amber",    "#ffd700"),
                    ("🌑", "Blood Moon", "Gothic · Kızıl & Karanlık",  "#dc143c"),
                ]
                with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px"):
                    for icon, name, sub, col in temas:
                        ui.html(
                            f'<div style="border-radius:10px;padding:10px 12px;'
                            f'background:color-mix(in srgb,{col} 10%,transparent);'
                            f'border:1px solid color-mix(in srgb,{col} 35%,transparent)">'
                            f'<div style="font-size:18px;margin-bottom:4px">{icon}</div>'
                            f'<div style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{name}</div>'
                            f'<div style="font-size:10px;color:{C["MUTED"]};margin-top:2px">{sub}</div>'
                            f'</div>'
                        )

            with ui.element("div").classes("card"):
                _sec_title("📋", "TEKNİK BİLGİLER", C["CYAN"])
                teknikler = [
                    ("📄", "Giriş Formatları",        "ASS, SSA, SRT"),
                    ("📤", "Çıkış Formatları",         "ASS, SRT, VTT, ALL"),
                    ("🤖", "Desteklenen AI Modelleri", "GPT-4o, Claude 3.5, Gemini 2.0, DeepSeek, LLaMA, Phi-4 ve daha fazlası"),
                    ("🔑", "API Sistemi",              "Çoklu anahtar rotasyonu — tükenmiş anahtarlar exhausted_api_keys.txt'e taşınır"),
                    ("💾", "Ayar Dosyaları",           "user_preferences.json + translator_config.json"),
                    ("📊", "Kalite Raporu",            "HTML format — CPS/CPL/zamanlama/tag hata gösterimi"),
                    ("🌐", "Çevrimdışı Bileşenler",   "Ses sistemi (Web Audio API), temalar — internet gerektirmez"),
                    ("🖥️", "Arayüz Teknolojisi",       f"NiceGUI {_ng.__version__} (Python) tabanlı yerel pencere"),
                    ("⌨️", "Sidebar Kısayolu",         "Ctrl+B ile sidebar'ı daraltıp genişletebilirsiniz"),
                    ("🗄️", "Sözlük Formatı",           "series_glossary.json — seri bazlı, kategorize terim yönetimi"),
                    ("🌍", "Fandom Entegrasyonu",      "fandom_glossary.py — Wiki'den otomatik terim çekme"),
                    ("⚡", "Batch İşlem",               "Ayarlanabilir grup boyutu + max byte limiti ile toplu çeviri"),
                ]
                for icon, baslik, acik in teknikler:
                    ui.html(
                        f'<div style="display:flex;gap:10px;padding:7px 0;'
                        f'border-bottom:1px solid {C["BORDER"]}22;align-items:flex-start">'
                        f'<span style="font-size:14px;flex-shrink:0;margin-top:1px">{icon}</span>'
                        f'<div>'
                        f'<span style="font-size:12px;font-weight:700;color:{C["TEXT"]}">{baslik}: </span>'
                        f'<span style="font-size:11px;color:{C["MUTED"]}">{acik}</span>'
                        f'</div></div>'
                    )

        # ── Footer ────────────────────────────────────────────────────────────────
        ui.html(f"""
        <div style="border-radius:14px;padding:22px 28px;text-align:center;
             background:color-mix(in srgb,var(--accent1) 8%,transparent);
             border:1px solid color-mix(in srgb,var(--accent1) 25%,transparent)">
          <div style="font-size:24px;margin-bottom:8px">🎌</div>
          <div style="font-size:13px;font-weight:800;color:{C['TEXT']};margin-bottom:6px">
            Nexus AI Altyazı Çeviri Paneli &mdash; v3.0
          </div>
          <div style="font-size:11px;color:{C['MUTED']};line-height:1.9">
            Yapay zeka ile güçlendirilmiş, tamamen Türkçe arayüzlü altyazı çeviri sistemi.<br>
            ASS / SRT / VTT &middot; OpenRouter API &middot; Çoklu LLM &middot; Çevrimdışı Arayüz
          </div>
          <div style="margin-top:14px;display:flex;justify-content:center;flex-wrap:wrap;gap:8px">
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🐍 Python {sys.version[:6]}</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🖼️ NiceGUI {_ng.__version__}</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">⚡ FastAPI</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🌐 OpenRouter</span>
            <span style="padding:4px 14px;border-radius:99px;background:rgba(255,255,255,0.06);font-size:10px;color:{C['MUTED']}">🔒 Offline Arayüz</span>
          </div>
        </div>
        """)

# ── RAPORLAR sayfası ──────────────────────────────────────────────────────────
