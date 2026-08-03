@echo off
echo =======================================================
echo           Kitsugi Plugins GitHub Sync Tool
echo =======================================================
echo.
echo [1/3] Git status kontrol ediliyor...
echo.
git status
echo.
echo =======================================================
set /p onay="Degisiklikleri GitHub'a push etmek istiyor musunuz? (E/H): "
if /I "%onay%" neq "E" (
    echo.
    echo Islem iptal edildi.
    goto bitir
)

echo.
echo [2/3] Dosyalar ekleniyor ve commit hazirlaniyor...
git add .

echo.
set /p msg="Commit mesaji yazin (Bos birakirsaniz 'Eklenti Guncellemesi' yazilir): "
if "%msg%"=="" (
    set msg="Eklenti Guncellemesi"
)

git commit -m %msg%

echo.
echo [3/3] Degisiklikler GitHub'a gonderiliyor (push)...
git push origin main

echo.
echo =======================================================
echo [TAMAMLANDI] Eklentiler basariyla GitHub'a yuklendi!
echo =======================================================
:bitir
pause
