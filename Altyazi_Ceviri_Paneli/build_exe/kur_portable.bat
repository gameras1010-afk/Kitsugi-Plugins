@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║        NEXUS — PORTABLE KURULUM HAZIRLA                 ║
echo  ║   (Sistem Python'a dokunmaz, klasör içinde kalır)       ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: Çalışma dizini = bu bat'ın olduğu klasör
set "SCRIPT_DIR=%~dp0"
set "PORTABLE_DIR=%SCRIPT_DIR%Nexus_Portable"
set "PYTHON_DIR=%PORTABLE_DIR%\python"
set "APP_DIR=%PORTABLE_DIR%\app"
set "DATA_DIR=%PORTABLE_DIR%\data"
set "FFMPEG_DIR=%PORTABLE_DIR%\ffmpeg"

echo [1/7] Klasör yapısı oluşturuluyor...
if exist "%PORTABLE_DIR%" (
    echo  Mevcut Nexus_Portable klasörü temizleniyor...
    rmdir /s /q "%PORTABLE_DIR%"
)
mkdir "%PORTABLE_DIR%"
mkdir "%PYTHON_DIR%"
mkdir "%APP_DIR%"
mkdir "%DATA_DIR%"
mkdir "%FFMPEG_DIR%"
echo  ✅ Klasörler hazır

:: ──────────────────────────────────────────────────────────────────
echo.
echo [2/7] Python Embedded indiriliyor (python.org resmi)...
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "PY_ZIP=%TEMP%\python_embed.zip"

powershell -Command ^
  "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'}"

if not exist "%PY_ZIP%" (
    echo  [HATA] Python indirilemedi! İnternet bağlantınızı kontrol edin.
    pause & exit /b 1
)
echo  ✅ Python indirildi

:: Python zip'ini aç
powershell -Command ^
  "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"
del /f /q "%PY_ZIP%"
echo  ✅ Python açıldı: %PYTHON_DIR%

:: ──────────────────────────────────────────────────────────────────
echo.
echo [3/7] pip kuruluyor (get-pip.py)...
set "GETPIP=%TEMP%\get-pip.py"
powershell -Command ^
  "& {$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%'}"

:: python311._pth dosyasını düzenle — import site aktif et
set "PTH_FILE="
for %%F in ("%PYTHON_DIR%\python*._pth") do set "PTH_FILE=%%F"
if defined PTH_FILE (
    powershell -Command ^
      "(Get-Content '%PTH_FILE%') -replace '#import site','import site' | Set-Content '%PTH_FILE%'"
    echo  ✅ python._pth düzenlendi (import site aktif)
)

"%PYTHON_DIR%\python.exe" "%GETPIP%" --no-warn-script-location -q
del /f /q "%GETPIP%" 2>nul
echo  ✅ pip kuruldu

:: ──────────────────────────────────────────────────────────────────
echo.
echo [4/7] Gerekli Python paketleri kuruluyor...
echo  (nicegui, pysubs2, requests, colorama, tqdm, pywebview...)
echo  Bu adım 2-5 dakika sürebilir...

"%PYTHON_DIR%\python.exe" -m pip install ^
    nicegui>=1.4.0 ^
    fastapi ^
    uvicorn ^
    httpx ^
    requests ^
    colorama ^
    tqdm ^
    pysubs2 ^
    pywebview ^
    rapidfuzz ^
    flashtext ^
    lingua-language-detector ^
    --no-warn-script-location -q

if errorlevel 1 (
    echo  [HATA] Paket kurulumu başarısız!
    pause & exit /b 1
)
echo  ✅ Tüm paketler kuruldu

:: ──────────────────────────────────────────────────────────────────
echo.
echo [5/7] Uygulama dosyaları kopyalanıyor...

:: Kaynak: bu bat'ın bir üst klasörü = Altyazi_Ceviri_Paneli/
set "SRC_ROOT=%SCRIPT_DIR%.."

:: Sadece Çeviri → app/
xcopy /e /i /q "%SRC_ROOT%\Sadece Çeviri\*" "%APP_DIR%\" ^
    /exclude:"%SCRIPT_DIR%xcopy_exclude.txt" 2>nul

:: Python kodları → app/
xcopy /e /i /q "%SRC_ROOT%\Python kodları\*" "%APP_DIR%\" ^
    /exclude:"%SCRIPT_DIR%xcopy_exclude.txt" 2>nul

echo  ✅ Kodlar kopyalandı

:: ──────────────────────────────────────────────────────────────────
echo.
echo [6/7] Kullanıcı veri klasörü hazırlanıyor...

:: Varsayılan veri dosyaları (varsa kopyala)
for %%F in (user_preferences.json api_keys.txt series_glossary.json ^
            translator_config.json fandom_blacklist.json) do (
    if exist "%SRC_ROOT%\Python kodları\%%F" (
        copy /y "%SRC_ROOT%\Python kodları\%%F" "%DATA_DIR%\%%F" >nul
    )
)
echo  ✅ Veri klasörü hazır

:: ──────────────────────────────────────────────────────────────────
echo.
echo [7/7] BAŞLAT.bat yazılıyor...

(
echo @echo off
echo chcp 65001 ^>nul
echo title Nexus AI Subtitle Engine
echo.
echo :: Portable Python ile çalıştır
echo set "ROOT=%%~dp0"
echo set "PYTHON=%%ROOT%%python\python.exe"
echo set "APP=%%ROOT%%app\ng_app.py"
echo set "DATA=%%ROOT%%data"
echo.
echo :: Veri dizinini bildir
echo set "NEXUS_USER_DIR=%%DATA%%"
echo set "NEXUS_DATA_DIR=%%DATA%%"
echo.
echo :: Chromium önbellek dizinini taşı (sisteme yazma)
echo set "PYWEBVIEW_GUI=mshtml"
echo.
echo if not exist "%%PYTHON%%" ^(
echo     echo [HATA] python\python.exe bulunamadi!
echo     pause
echo     exit /b 1
echo ^)
echo.
echo start "" "%%PYTHON%%w" "%%APP%%"
) > "%PORTABLE_DIR%\BAŞLAT.bat"

:: Ayrıca konsol modunda çalıştırma (hata ayıklama)
(
echo @echo off
echo chcp 65001 ^>nul
echo title Nexus - Konsol Modu
echo set "ROOT=%%~dp0"
echo set "PYTHON=%%ROOT%%python\python.exe"
echo set "APP=%%ROOT%%app\ng_app.py"
echo set "DATA=%%ROOT%%data"
echo set "NEXUS_USER_DIR=%%DATA%%"
echo set "NEXUS_DATA_DIR=%%DATA%%"
echo "%%PYTHON%%" "%%APP%%"
echo pause
) > "%PORTABLE_DIR%\BAŞLAT_konsol.bat"

echo  ✅ Başlatıcılar yazıldı

:: ──────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   ✅ PORTABLE KURULUM TAMAMLANDI!                        ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Klasör: %PORTABLE_DIR%
echo.
echo  Kullanım:
echo    ► BAŞLAT.bat            → Normal çalıştır (pencere)
echo    ► BAŞLAT_konsol.bat     → Hata ayıklama modu
echo.
echo  Bu klasörü USB'ye veya başka PC'ye taşıyabilirsiniz.
echo  Python kurulumu GEREKMİYOR.
echo.

:: Klasör boyutunu göster
for /f "tokens=3" %%A in ('dir /s /a "%PORTABLE_DIR%" 2^>nul ^| find "dosya"') do (
    set "FCOUNT=%%A"
)
echo  Klasör boyutu hesaplanıyor...
powershell -Command ^
  "$s=(Get-ChildItem '%PORTABLE_DIR%' -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum; Write-Host ('  Toplam: {0:N0} MB' -f ($s/1MB))"

pause
