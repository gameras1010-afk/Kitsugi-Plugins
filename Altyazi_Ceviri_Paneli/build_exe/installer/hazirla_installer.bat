@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║     NEXUS AI — KURULUM PAKETİ HAZIRLAYICI                      ║
echo  ║     Bu script setup_nexus_v3.exe için bundle hazırlar          ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  Adımlar:
echo    1. Python 3.11 Embedded indir
echo    2. Pip + paketleri kur
echo    3. FFmpeg indir
echo    4. Inno Setup ile setup.exe derle
echo.

set "INST_DIR=%~dp0"
set "BUNDLE=%INST_DIR%bundle"
set "PY_BUNDLE=%BUNDLE%\python"
set "TOOLS_BUNDLE=%BUNDLE%\tools"

:: ── Temizlik ─────────────────────────────────────────────────────────────────
echo [1/5] Bundle klasörü hazırlanıyor...
if exist "%BUNDLE%" rmdir /s /q "%BUNDLE%"
mkdir "%PY_BUNDLE%"
mkdir "%TOOLS_BUNDLE%"
echo        ✅ Tamam

:: ── Python Embedded ──────────────────────────────────────────────────────────
echo.
echo [2/5] Python 3.11.9 Embedded indiriliyor...
set "PY_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "PY_ZIP=%TEMP%\nexus_py.zip"

powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%' -UseBasicParsing"
if not exist "%PY_ZIP%" ( echo  [HATA] Python indirilemedi! & pause & exit /b 1 )

powershell -NoProfile -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%PY_BUNDLE%' -Force"
del /f /q "%PY_ZIP%"

:: import site aktif et
for %%F in ("%PY_BUNDLE%\python3*._pth") do (
    powershell -NoProfile -Command ^
      "(Get-Content '%%F') -replace '#import site','import site' | Set-Content '%%F'"
)
echo        ✅ Python 3.11 hazır

:: ── pip ─────────────────────────────────────────────────────────────────────
echo.
echo [3/5] pip + paketler kuruluyor...
echo        (3-7 dakika sürebilir)

set "GETPIP=%TEMP%\get-pip.py"
powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%GETPIP%' -UseBasicParsing"

"%PY_BUNDLE%\python.exe" "%GETPIP%" --no-warn-script-location -q
del /f /q "%GETPIP%"

"%PY_BUNDLE%\python.exe" -m pip install ^
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

if errorlevel 1 ( echo  [HATA] Paket kurulumu başarısız! & pause & exit /b 1 )
echo        ✅ Tüm paketler bundle'a kuruldu

:: ── FFmpeg ───────────────────────────────────────────────────────────────────
echo.
echo [4/5] FFmpeg indiriliyor...
set "FF_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "FF_ZIP=%TEMP%\nexus_ffmpeg.zip"
set "FF_TMP=%TEMP%\nexus_ff_extract"

powershell -NoProfile -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FF_URL%' -OutFile '%FF_ZIP%' -UseBasicParsing"

if exist "%FF_ZIP%" (
    if exist "%FF_TMP%" rmdir /s /q "%FF_TMP%"
    mkdir "%FF_TMP%"
    powershell -NoProfile -Command "Expand-Archive -Path '%FF_ZIP%' -DestinationPath '%FF_TMP%' -Force"
    for /r "%FF_TMP%" %%F in (ffmpeg.exe ffprobe.exe) do (
        if exist "%%F" copy /y "%%F" "%TOOLS_BUNDLE%\" >nul
    )
    rmdir /s /q "%FF_TMP%"
    del /f /q "%FF_ZIP%"
    echo        ✅ FFmpeg bundle'a eklendi
) else (
    echo        ⚠️  FFmpeg indirilemedi, araçlar kısmı boş kalacak
)

:: ── Başlatıcılar ─────────────────────────────────────────────────────────────
echo.
echo [5/5] Başlatıcılar yazılıyor...

> "%INST_DIR%BAŞLAT.bat" (
echo @echo off
echo chcp 65001 ^>nul
echo setlocal
echo set "APP_DIR=%%~dp0"
echo set "PYTHON=%%APP_DIR%%python\pythonw.exe"
echo set "APP=%%APP_DIR%%app\ng_app.py"
echo set "NEXUS_USER_DIR=%%APPDATA%%\NexusAI"
echo set "NEXUS_DATA_DIR=%%APPDATA%%\NexusAI"
echo set "PATH=%%APP_DIR%%tools;%%APP_DIR%%python\Scripts;%%PATH%%"
echo if not exist "%%APPDATA%%\NexusAI" mkdir "%%APPDATA%%\NexusAI"
echo start "" "%%PYTHON%%" "%%APP%%"
)

> "%INST_DIR%BAŞLAT_konsol.bat" (
echo @echo off
echo chcp 65001 ^>nul
echo title Nexus AI - Konsol
echo set "APP_DIR=%%~dp0"
echo set "PYTHON=%%APP_DIR%%python\python.exe"
echo set "APP=%%APP_DIR%%app\ng_app.py"
echo set "NEXUS_USER_DIR=%%APPDATA%%\NexusAI"
echo set "NEXUS_DATA_DIR=%%APPDATA%%\NexusAI"
echo set "PATH=%%APP_DIR%%tools;%%APP_DIR%%python\Scripts;%%PATH%%"
echo if not exist "%%APPDATA%%\NexusAI" mkdir "%%APPDATA%%\NexusAI"
echo "%%PYTHON%%" "%%APP%%"
echo pause
)

echo        ✅ Başlatıcılar yazıldı

:: ── Inno Setup var mı? ───────────────────────────────────────────────────────
echo.
echo ════════════════════════════════════════════════════════
echo  Bundle hazır! Şimdi Inno Setup ile setup.exe derle:
echo ════════════════════════════════════════════════════════
echo.

set "ISCC="
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) do (
    if exist "%%~P" set "ISCC=%%~P"
)

if not defined ISCC (
    echo  ⚠️  Inno Setup bulunamadı!
    echo.
    echo  Şimdi otomatik indirip kuruyorum...
    echo.
    set "IS_INSTALLER=%TEMP%\innosetup.exe"
    powershell -NoProfile -Command ^
      "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://jrsoftware.org/download.php/is.exe' -OutFile '%TEMP%\innosetup.exe' -UseBasicParsing"
    if exist "%TEMP%\innosetup.exe" (
        echo  Inno Setup kuruluyor — sihirbazı tamamla, sonra bu pencereye dön...
        start /wait "%TEMP%\innosetup.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
        del /f /q "%TEMP%\innosetup.exe"
        :: Tekrar kontrol
        for %%P in (
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
            "C:\Program Files\Inno Setup 6\ISCC.exe"
        ) do (
            if exist "%%~P" set "ISCC=%%~P"
        )
    )
)

if not defined ISCC (
    echo  [HATA] Inno Setup kurulu değil!
    echo  Manuel indir: https://jrsoftware.org/isinfo.php
    echo  Kurduktan sonra nexus_setup.iss dosyasını aç ve Compile (F9) bas.
    echo.
    pause
    exit /b 1
)

echo  Inno Setup bulundu: %ISCC%
echo  Setup.exe derleniyor...
echo.

if not exist "%INST_DIR%Output" mkdir "%INST_DIR%Output"

"%ISCC%" "%INST_DIR%nexus_setup.iss"

if errorlevel 1 (
    echo.
    echo  [HATA] Derleme başarısız!
    echo  nexus_setup.iss dosyasını Inno Setup ile açıp hata mesajına bakın.
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║   ✅ SETUP.EXE HAZIR!                                           ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.
echo  Konum: %INST_DIR%Output\setup_nexus_v3.exe
echo.
echo  Bu dosyayı istediğin yere kopyala ve çalıştır!
echo  Kullanıcı "İleri → İleri → Bitir" diye kurar.
echo.

:: Boyut
powershell -NoProfile -Command ^
  "try { $f='%INST_DIR%Output\setup_nexus_v3.exe'; if(Test-Path $f){ $s=(Get-Item $f).Length; Write-Host ('  Dosya boyutu: {0:N0} MB' -f ($s/1MB)) } } catch {}"

pause
