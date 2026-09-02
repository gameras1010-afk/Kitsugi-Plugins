@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   NEXUS AI SUBTITLE ENGINE — EXE BUILD  ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Python ve pip kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! python.org'dan yukleyin.
    pause & exit /b 1
)

:: Gerekli paketleri kur
echo [1/4] Gerekli paketler kuruluyor...
pip install pyinstaller nicegui fastapi uvicorn httpx requests ^
    colorama tqdm pysubs2 pywebview -q --disable-pip-version-check
if errorlevel 1 (
    echo [HATA] Paket kurulumu basarisiz!
    pause & exit /b 1
)

:: Eski build temizle
echo [2/4] Eski build temizleniyor...
if exist dist\Nexus.exe del /f /q dist\Nexus.exe
if exist build rmdir /s /q build

:: PyInstaller ile derle
echo [3/4] EXE derleniyor (bu 3-5 dakika surebilir)...
python -m PyInstaller Nexus.spec --clean --noconfirm

if not exist dist\Nexus.exe (
    echo.
    echo [HATA] Derleme basarisiz! Yukaridaki hata mesajina bakin.
    pause & exit /b 1
)

:: Sonuç
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║   ✅ DERLEME TAMAMLANDI!                 ║
echo  ╚══════════════════════════════════════════╝
echo.
echo  EXE konumu:
echo  %~dp0dist\Nexus.exe
echo.
echo [4/4] EXE boyutu:
for %%F in (dist\Nexus.exe) do echo  %%~zF bytes
echo.
echo  Çift tıklayarak çalıştırabilirsiniz: dist\Nexus.exe
echo.
pause
