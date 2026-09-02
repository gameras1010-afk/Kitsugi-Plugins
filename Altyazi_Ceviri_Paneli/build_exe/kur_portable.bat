@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║          NEXUS AI SUBTITLE ENGINE                           ║
echo  ║          PORTABLE KURULUM (v1.0)                            ║
echo  ║   Her şey bu klasörde — sisteme hiçbir şey kurulmaz        ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: ── Yollar ──────────────────────────────────────────────────────────────────
set "BUILD_DIR=%~dp0"
set "PORTABLE=%BUILD_DIR%Nexus_Portable"
set "PY_DIR=%PORTABLE%\python"
set "APP_DIR=%PORTABLE%\app"
set "DATA_DIR=%PORTABLE%\data"
set "TOOLS_DIR=%PORTABLE%\tools"

:: ── Mevcut kurulum kontrolü ──────────────────────────────────────────────────
if exist "%PORTABLE%\BAŞLAT.bat" (
    echo  Mevcut bir kurulum bulundu: %PORTABLE%
    echo.
    choice /c GU /m "  [G]üncelle (üzerine yaz)  [U]çuştur - iptal"
    if errorlevel 2 exit /b 0
    echo  Güncelleniyor...
    echo.
)

:: ── Klasörler ────────────────────────────────────────────────────────────────
echo [1/8] Klasör yapısı hazırlanıyor...
if exist "%PORTABLE%\python" goto :skip_py_folder
mkdir "%PY_DIR%" 2>nul
:skip_py_folder
mkdir "%APP_DIR%"  2>nul
mkdir "%DATA_DIR%" 2>nul
mkdir "%TOOLS_DIR%" 2>nul
echo        ✅ Tamam

:: ── Python Embedded ──────────────────────────────────────────────────────────
echo.
echo [2/8] Python 3.11 Embedded kontrol ediliyor...
if exist "%PY_DIR%\python.exe" (
    echo        ✅ Python zaten var, atlıyorum
    goto :pip_check
)

echo        İndiriliyor: Python 3.11.9 Embedded (python.org)...
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "PY_ZIP=%TEMP%\nexus_py_embed.zip"

powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%' -UseBasicParsing"

if not exist "%PY_ZIP%" (
    echo  [HATA] Python indirilemedi! İnternet bağlantısını kontrol edin.
    pause & exit /b 1
)

echo        Açılıyor...
powershell -NoProfile -Command ^
  "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PY_DIR%' -Force"
del /f /q "%PY_ZIP%" 2>nul

:: python3X._pth → import site aktif et (pip için şart)
for %%F in ("%PY_DIR%\python*._pth") do (
    powershell -NoProfile -Command ^
      "(Get-Content '%%F') -replace '#import site','import site' | Set-Content '%%F'"
)
echo        ✅ Python 3.11 hazır

:: ── pip ─────────────────────────────────────────────────────────────────────
:pip_check
echo.
echo [3/8] pip kontrol ediliyor...
if exist "%PY_DIR%\Scripts\pip.exe" (
    echo        ✅ pip zaten var
    goto :packages
)

echo        get-pip.py indiriliyor...
set "GETPIP=%TEMP%\get-pip.py"
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%' -UseBasicParsing"

"%PY_DIR%\python.exe" "%GETPIP%" --no-warn-script-location -q
del /f /q "%GETPIP%" 2>nul
echo        ✅ pip kuruldu

:: ── Python Paketleri ─────────────────────────────────────────────────────────
:packages
echo.
echo [4/8] Python paketleri kuruluyor...
echo        (nicegui, pysubs2, requests, colorama, tqdm, pywebview...)
echo        Bu adım 3-7 dakika sürebilir, lütfen bekleyin.
echo.

"%PY_DIR%\python.exe" -m pip install ^
    "nicegui>=1.4.0" ^
    "fastapi>=0.104.0" ^
    "uvicorn>=0.24.0" ^
    "httpx>=0.25.0" ^
    "requests>=2.31.0" ^
    "colorama>=0.4.6" ^
    "tqdm>=4.66.0" ^
    "pysubs2>=1.6.0" ^
    "pywebview>=4.0.0" ^
    "rapidfuzz>=3.0.0" ^
    "aiofiles" ^
    "python-multipart" ^
    "itsdangerous" ^
    "orjson" ^
    --no-warn-script-location -q --disable-pip-version-check

if errorlevel 1 (
    echo  [HATA] Paket kurulumu başarısız!
    echo  Log için: %PY_DIR%\Scripts\pip.exe install nicegui pysubs2 requests
    pause & exit /b 1
)
echo        ✅ Tüm paketler kuruldu

:: ── FFmpeg ───────────────────────────────────────────────────────────────────
echo.
echo [5/8] FFmpeg kontrol ediliyor...
if exist "%TOOLS_DIR%\ffmpeg.exe" (
    echo        ✅ FFmpeg zaten var
    goto :app_copy
)

echo        FFmpeg indiriliyor (gyan.dev - resmi Windows build)...
set "FF_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "FF_ZIP=%TEMP%\nexus_ffmpeg.zip"

powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FF_URL%' -OutFile '%FF_ZIP%' -UseBasicParsing"

if not exist "%FF_ZIP%" (
    echo        ⚠️  FFmpeg indirilemedi - video track çıkarma çalışmaz
    echo           Manuel eklemek için: tools\ffmpeg.exe ve tools\ffprobe.exe koyun
    goto :app_copy
)

echo        Açılıyor...
set "FF_TEMP=%TEMP%\nexus_ffmpeg_extract"
if exist "%FF_TEMP%" rmdir /s /q "%FF_TEMP%"
mkdir "%FF_TEMP%"
powershell -NoProfile -Command ^
  "Expand-Archive -Path '%FF_ZIP%' -DestinationPath '%FF_TEMP%' -Force"
del /f /q "%FF_ZIP%" 2>nul

:: İçinden sadece ffmpeg.exe ve ffprobe.exe al
for /r "%FF_TEMP%" %%F in (ffmpeg.exe ffprobe.exe) do (
    if exist "%%F" copy /y "%%F" "%TOOLS_DIR%\" >nul
)
rmdir /s /q "%FF_TEMP%" 2>nul

if exist "%TOOLS_DIR%\ffmpeg.exe" (
    echo        ✅ FFmpeg tools/ klasörüne eklendi
) else (
    echo        ⚠️  FFmpeg eklenemedi - opsiyonel, ilerleyebiliriz
)

:: ── Uygulama Kodları ─────────────────────────────────────────────────────────
:app_copy
echo.
echo [6/8] Uygulama kodları kopyalanıyor...

set "SRC=%BUILD_DIR%.."

:: xcopy exclude listesi
set "EXCL=%TEMP%\nexus_xcopy_excl.txt"
(
echo \__pycache__\
echo *.pyc
echo *.pyo
echo *.BAK
echo \build_exe\
echo \build\
echo \dist\
echo *.log
echo *.tmp
echo offline_anidb.json
echo offline_manami.json
echo offline_tmdb_movies.json
echo offline_tmdb_tv.json
echo offline_imdb_basics.json
echo offline_imdb_akas.json
echo offline_wikidata_chars.json
echo offline_wikidata_entities.json
) > "%EXCL%"

:: Sadece Çeviri → app/
xcopy /e /i /q /y "%SRC%\Sadece Çeviri\*" "%APP_DIR%\" /exclude:"%EXCL%" 2>nul

:: Python kodları → app/ (alt klasör olarak değil, aynı seviyeye)
xcopy /e /i /q /y "%SRC%\Python kodları\*" "%APP_DIR%\" /exclude:"%EXCL%" 2>nul

del /f /q "%EXCL%" 2>nul
echo        ✅ Kodlar kopyalandı

:: ── Kullanıcı Verisi ─────────────────────────────────────────────────────────
echo.
echo [7/8] Kullanıcı verisi hazırlanıyor...

:: Varsa kopyala, yoksa boş bırak
for %%F in (user_preferences.json api_keys.txt series_glossary.json ^
            translator_config.json fandom_blacklist.json api_keys_WORKING.txt) do (
    if exist "%SRC%\Python kodları\%%F" (
        copy /y "%SRC%\Python kodları\%%F" "%DATA_DIR%\%%F" >nul 2>nul
    )
)

:: Boş api_keys.txt yok ise oluştur
if not exist "%DATA_DIR%\api_keys.txt" (
    echo. > "%DATA_DIR%\api_keys.txt"
    echo        ℹ️  Boş api_keys.txt oluşturuldu - API key ekleyin
)

echo        ✅ Veri klasörü hazır

:: ── BAŞLAT.bat ───────────────────────────────────────────────────────────────
echo.
echo [8/8] Başlatıcılar yazılıyor...

:: Ana başlatıcı (pencere, arka planda)
> "%PORTABLE%\BAŞLAT.bat" (
echo @echo off
echo chcp 65001 ^>nul
echo setlocal
echo set "ROOT=%%~dp0"
echo set "PYTHON=%%ROOT%%python\python.exe"
echo set "PYTHONW=%%ROOT%%python\pythonw.exe"
echo set "APP=%%ROOT%%app\ng_app.py"
echo.
echo :: Veri dizini — ayarlar, glossary, API key hep burada
echo set "NEXUS_USER_DIR=%%ROOT%%data"
echo set "NEXUS_DATA_DIR=%%ROOT%%data"
echo.
echo :: tools/ içindeki ffmpeg'i PATH'e ekle
echo set "PATH=%%ROOT%%tools;%%PATH%%"
echo.
echo :: Python'un script dizini de PATH'te olsun
echo set "PATH=%%ROOT%%python\Scripts;%%PATH%%"
echo.
echo if not exist "%%PYTHON%%" ^(
echo     echo [HATA] python\python.exe bulunamadi!
echo     echo Kurulum bozuk olabilir. kur_portable.bat tekrar calistirin.
echo     pause ^& exit /b 1
echo ^)
echo.
echo :: Arka planda başlat ^(konsol yok^)
echo start "" "%%PYTHONW%%" "%%APP%%"
echo.
echo :: Kısa bekleme sonra pencere açıldı mı kontrol et
echo timeout /t 4 /nobreak ^>nul
echo tasklist /fi "imagename eq pythonw.exe" 2^>nul ^| find /i "pythonw" ^>nul
echo if errorlevel 1 ^(
echo     echo [HATA] Uygulama başlatılamadı!
echo     echo BAŞLAT_konsol.bat ile hata mesajına bakın.
echo     pause
echo ^)
)

:: Konsol/debug başlatıcı
> "%PORTABLE%\BAŞLAT_konsol.bat" (
echo @echo off
echo chcp 65001 ^>nul
echo title Nexus - Konsol ^(Hata Ayiklama^)
echo setlocal
echo set "ROOT=%%~dp0"
echo set "PYTHON=%%ROOT%%python\python.exe"
echo set "APP=%%ROOT%%app\ng_app.py"
echo set "NEXUS_USER_DIR=%%ROOT%%data"
echo set "NEXUS_DATA_DIR=%%ROOT%%data"
echo set "PATH=%%ROOT%%tools;%%ROOT%%python\Scripts;%%PATH%%"
echo.
echo echo Nexus baslatiliyor ^(Konsol Modu^)...
echo echo Kapatmak icin bu pencereyi kapatin.
echo echo.
echo "%%PYTHON%%" "%%APP%%"
echo echo.
echo echo Program sonlandi.
echo pause
)

:: Hızlı güncelleme scripti
> "%PORTABLE%\guncelle_paketler.bat" (
echo @echo off
echo chcp 65001 ^>nul
echo title Nexus - Paket Guncelleme
echo set "ROOT=%%~dp0"
echo set "PYTHON=%%ROOT%%python\python.exe"
echo set "PATH=%%ROOT%%python\Scripts;%%PATH%%"
echo echo Paketler guncelleniyor...
echo "%%PYTHON%%" -m pip install --upgrade nicegui pysubs2 requests -q
echo echo Tamam!
echo pause
)

echo        ✅ Başlatıcılar yazıldı

:: ── Özet ─────────────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║   ✅ PORTABLE KURULUM TAMAMLANDI!                           ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo  Klasör: %PORTABLE%
echo.
echo  Başlatmak için:
echo    ► BAŞLAT.bat              → Normal çalıştır
echo    ► BAŞLAT_konsol.bat       → Hata ayıklama modu
echo    ► guncelle_paketler.bat   → Paketleri güncelle
echo.
echo  ℹ️  API key eklemek için:
echo    data\api_keys.txt dosyasını düzenleyin
echo.
echo  ℹ️  Bu klasörü USB'ye kopyalayın, her PC'de çalışır.
echo     (Başka PC'de de Python kurmanıza gerek YOK)
echo.

:: Boyut
powershell -NoProfile -Command ^
  "try { $s=(Get-ChildItem '%PORTABLE%' -Recurse -EA SilentlyContinue | Measure-Object -Property Length -Sum).Sum; Write-Host ('  Toplam boyut: {0:N0} MB' -f ($s/1MB)) } catch {}"

echo.
pause
