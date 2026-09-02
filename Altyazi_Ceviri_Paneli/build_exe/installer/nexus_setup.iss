; ╔══════════════════════════════════════════════════════════════════════╗
; ║   Nexus AI Altyazı Çeviri Paneli — Inno Setup Script               ║
; ║   Derleme: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)      ║
; ╚══════════════════════════════════════════════════════════════════════╝
;
; KULLANIM:
;   1. Inno Setup'ı kur: https://jrsoftware.org/isinfo.php
;   2. Bu dosyayı Inno Setup Compiler ile aç
;   3. Build → Compile (F9)
;   4. Output/setup_nexus_v3.exe hazır!
;
; NOT: Bu script çalıştırılmadan önce build_exe/hazirla_installer.bat
;      koşturulmalıdır — Python + paketler + FFmpeg indirilir.

#define APP_NAME    "Nexus AI Altyazı Çeviri Paneli"
#define APP_VERSION "3.0"
#define APP_SLUG    "NexusAI"
#define APP_EXE     "BAŞLAT.bat"
#define APP_ICON    "nexus_icon.ico"
#define PUBLISHER   "Nexus AI"
#define APP_URL     "https://github.com/gameras1010-afk/Kitsugi-Plugins"

; Kaynak dizin — bu .iss dosyasından iki üst klasör = Altyazi_Ceviri_Paneli/
#define SRC         "..\..\"

[Setup]
AppId={{7F4E2A1B-9C3D-4F8E-B2A7-1D6E9F3C5A8B}
AppName={#APP_NAME}
AppVersion={#APP_VERSION}
AppVerName={#APP_NAME} v{#APP_VERSION}
AppPublisher={#PUBLISHER}
AppPublisherURL={#APP_URL}
AppSupportURL={#APP_URL}
AppUpdatesURL={#APP_URL}

; Kurulum hedefi: Program Files\NexusAI\
DefaultDirName={autopf}\{#APP_SLUG}
DefaultGroupName={#APP_NAME}
AllowNoIcons=no

; Output
OutputDir=..\Output
OutputBaseFilename=setup_nexus_v{#APP_VERSION}
SetupIconFile={#APP_ICON}

; Sıkıştırma (LZMA — en iyi oran)
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Windows 10+ gerekli
MinVersion=10.0

; Admin gerektirsin (Program Files'a yazmak için)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Modern görünüm
WizardStyle=modern
WizardSizePercent=120

; Dil
ShowLanguageDialog=no

; Yeniden başlatma gerekmez
RestartIfNeededByRun=no

; Uninstaller
Uninstallable=yes
UninstallDisplayIcon={app}\nexus_icon.ico
UninstallDisplayName={#APP_NAME} v{#APP_VERSION}
CreateUninstallRegKey=yes

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[CustomMessages]
turkish.WelcomeLabel2=Bu sihirbaz bilgisayarınıza [name/ver] kurulumunu gerçekleştirecektir.%n%nKuruluma devam etmeden önce diğer tüm uygulamaları kapatmanız önerilir.
turkish.FinishedHeadingLabel=Kurulum Tamamlandı
turkish.FinishedLabel=Nexus AI Altyazı Çeviri Paneli başarıyla kuruldu!%n%nUygulamayı masaüstündeki kısayoldan başlatabilirsiniz.
turkish.ClickFinish=Sihirbazı kapatmak için Son'a tıklayın.

[Tasks]
Name: "desktopicon";     Description: "Masaüstüne kısayol oluştur";   GroupDescription: "Ek kısayollar:"; Flags: checkedonce
Name: "startmenuicon";   Description: "Başlat menüsüne ekle";          GroupDescription: "Ek kısayollar:"; Flags: checkedonce

[Files]
; ── Python Embedded ──────────────────────────────────────────────────────────
Source: "{#SRC}build_exe\installer\bundle\python\*"; \
  DestDir: "{app}\python"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; \
  Components: main

; ── Uygulama kodları — Sadece Çeviri/ ────────────────────────────────────────
Source: "{#SRC}Sadece Çeviri\*"; \
  DestDir: "{app}\app"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "__pycache__,*.pyc,*.pyo,*.BAK,*.log"; \
  Components: main

; ── Python kodları ────────────────────────────────────────────────────────────
Source: "{#SRC}Python kodları\*"; \
  DestDir: "{app}\app"; \
  Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "__pycache__,*.pyc,*.pyo,*.BAK,*.log,offline_anidb.json,offline_manami.json,offline_tmdb_movies.json,offline_tmdb_tv.json,offline_imdb_basics.json,offline_imdb_akas.json,offline_wikidata_chars.json,offline_wikidata_entities.json"; \
  Components: main

; ── FFmpeg araçları ───────────────────────────────────────────────────────────
Source: "{#SRC}build_exe\installer\bundle\tools\*"; \
  DestDir: "{app}\tools"; \
  Flags: ignoreversion; \
  Components: main

; ── İkon ─────────────────────────────────────────────────────────────────────
Source: "{#SRC}build_exe\installer\{#APP_ICON}"; \
  DestDir: "{app}"; \
  Flags: ignoreversion; \
  Components: main

; ── Başlatıcı script'ler ──────────────────────────────────────────────────────
Source: "{#SRC}build_exe\installer\BAŞLAT.bat"; \
  DestDir: "{app}"; \
  Flags: ignoreversion; \
  Components: main

Source: "{#SRC}build_exe\installer\BAŞLAT_konsol.bat"; \
  DestDir: "{app}"; \
  Flags: ignoreversion; \
  Components: main

[Components]
Name: main; Description: "Nexus AI (zorunlu)"; Types: full compact custom; Flags: fixed

[Icons]
; Başlat menüsü
Name: "{group}\{#APP_NAME}";       Filename: "{app}\BAŞLAT.bat";         IconFilename: "{app}\nexus_icon.ico"; Comment: "Nexus AI Altyazı Çeviri Paneli"
Name: "{group}\Konsol (Hata Ayıklama)"; Filename: "{app}\BAŞLAT_konsol.bat"; IconFilename: "{app}\nexus_icon.ico"
Name: "{group}\Kaldır";             Filename: "{uninstallexe}"

; Masaüstü
Name: "{autodesktop}\{#APP_NAME}"; Filename: "{app}\BAŞLAT.bat"; IconFilename: "{app}\nexus_icon.ico"; Tasks: desktopicon

[Registry]
; Program Ekle/Kaldır kaydı
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\NexusAI.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\BAŞLAT.bat"; Flags: uninsdeletekey

[Run]
; Kurulum bittikten sonra başlat (opsiyonel)
Filename: "{app}\BAŞLAT.bat"; \
  Description: "Nexus AI'ı şimdi başlat"; \
  Flags: nowait postinstall skipifsilent shellexec; \
  WorkingDir: "{app}\app"

[UninstallDelete]
; Kaldırırken kullanıcı verisini silme — sadece program dosyaları
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\tools"
Type: filesandordirs; Name: "{app}\app"
