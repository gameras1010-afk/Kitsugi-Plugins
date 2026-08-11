@echo off
REM ============================================================
REM  Minecraft 1.21.1 NeoForge - Sunucu Baslatma Scripti (Windows)
REM  Moonrise + Generator Accelerator yigini icin ayarlanmis
REM ============================================================

setlocal enabledelayedexpansion

REM ------------------------------------------------------------
REM  1) RAM AYARI  -  BURAYI DUZENLE
REM ------------------------------------------------------------
REM  Xms ve Xmx AYNI olmali.
REM  Makinede toplam ne varsa Windows'a en az 3 GB birak.
REM      8 GB makine  -> 5G
REM     16 GB makine  -> 12G
REM     32 GB makine  -> 16G
REM  16G ustune CIKMA (Compressed OOPs sinirini asarsin).
REM ------------------------------------------------------------
set MEMORY=12G

REM ------------------------------------------------------------
REM  2) LAUNCHER  -  BURAYI DUZENLE
REM ------------------------------------------------------------
REM  Surum numarasini kontrol et:
REM     dir libraries\net\neoforged\neoforge\
set LAUNCH_ARGS=@libraries/net/neoforged/neoforge/21.1.209/win_args.txt

REM Eski tarz duz jar kullaniyorsan yukaridakini yorum yapip bunu ac:
REM set LAUNCH_ARGS=-jar server.jar

REM ------------------------------------------------------------
REM  3) JAVA  -  Java 21 SART
REM ------------------------------------------------------------
set JAVA=java
REM Belirli bir Java'yi zorlamak istersen:
REM set JAVA="C:\Program Files\Java\jdk-21\bin\java.exe"

REM ============================================================
REM  BURADAN ASAGISINA DOKUNMA
REM ============================================================

if not exist eula.txt (
    echo HATA: eula.txt bulunamadi.
    echo Sunucuyu bir kez calistirip eula.txt icindeki
    echo eula=false satirini eula=true yap.
    pause
    exit /b 1
)

set FLAGS=-Xms%MEMORY% -Xmx%MEMORY%
set FLAGS=%FLAGS% -XX:+UseG1GC
set FLAGS=%FLAGS% -XX:+ParallelRefProcEnabled
set FLAGS=%FLAGS% -XX:MaxGCPauseMillis=200
set FLAGS=%FLAGS% -XX:+UnlockExperimentalVMOptions
set FLAGS=%FLAGS% -XX:+DisableExplicitGC
set FLAGS=%FLAGS% -XX:+AlwaysPreTouch

REM --- Young gen (12G+ icin). 8G ve altindaysan 30/40 yap ---
set FLAGS=%FLAGS% -XX:G1NewSizePercent=40
set FLAGS=%FLAGS% -XX:G1MaxNewSizePercent=50

REM --- Region boyutu (12G+ icin 16M, 8G ve altinda 8M) ---
set FLAGS=%FLAGS% -XX:G1HeapRegionSize=16M

set FLAGS=%FLAGS% -XX:G1ReservePercent=15
set FLAGS=%FLAGS% -XX:G1HeapWastePercent=5
set FLAGS=%FLAGS% -XX:G1MixedGCCountTarget=4
set FLAGS=%FLAGS% -XX:InitiatingHeapOccupancyPercent=20
set FLAGS=%FLAGS% -XX:G1MixedGCLiveThresholdPercent=90
set FLAGS=%FLAGS% -XX:G1RSetUpdatingPauseTimePercent=5
set FLAGS=%FLAGS% -XX:SurvivorRatio=32
set FLAGS=%FLAGS% -XX:+PerfDisableSharedMem
set FLAGS=%FLAGS% -XX:MaxTenuringThreshold=1

REM --- JIT / code cache ---
set FLAGS=%FLAGS% -XX:ReservedCodeCacheSize=400M
set FLAGS=%FLAGS% -XX:NonNMethodCodeHeapSize=12M
set FLAGS=%FLAGS% -XX:ProfiledCodeHeapSize=194M
set FLAGS=%FLAGS% -XX:NonProfiledCodeHeapSize=194M
set FLAGS=%FLAGS% -XX:-DontCompileHugeMethods
set FLAGS=%FLAGS% -XX:MaxNodeLimit=240000
set FLAGS=%FLAGS% -XX:NodeLimitFudgeFactor=8000
set FLAGS=%FLAGS% -XX:+UseVectorCmov
set FLAGS=%FLAGS% -XX:+UseFastUnorderedTimeStamps
set FLAGS=%FLAGS% -XX:AllocatePrefetchStyle=3

REM --- Vector API (Generator Accelerator SIMD noise) ---
set FLAGS=%FLAGS% --add-modules=jdk.incubator.vector

REM --- Netty ---
set FLAGS=%FLAGS% -Dio.netty.allocator.maxOrder=9
set FLAGS=%FLAGS% -Dio.netty.leakDetection.level=disabled

REM --- Diger ---
set FLAGS=%FLAGS% -Dusing.aikars.flags=https://mcflags.emc.gs
set FLAGS=%FLAGS% -Daikars.new.flags=true
set FLAGS=%FLAGS% -Dfile.encoding=UTF-8
set FLAGS=%FLAGS% -Djava.awt.headless=true
set FLAGS=%FLAGS% -Dlog4j2.formatMsgNoLookups=true

echo ===============================================
echo   Minecraft 1.21.1 NeoForge Server
echo   Heap : %MEMORY%
echo   GC   : G1GC (Aikar flags)
echo ===============================================
echo.
echo   Hatirlatma: config\moonrise.yml icindeki
echo   worker-threads degerini CPU'na gore ayarladin mi?
echo.

:restart
%JAVA% %FLAGS% %LAUNCH_ARGS% nogui

echo.
echo Sunucu kapandi. 10 saniye sonra yeniden baslatiliyor...
echo Iptal etmek icin bu pencereyi kapat veya Ctrl+C.
timeout /t 10
goto restart

endlocal
