#!/usr/bin/env bash
# ============================================================
#  Minecraft 1.21.1 NeoForge — Sunucu Baslatma Scripti
#
#  SENIN DONANIMINA GORE AYARLANDI:
#    CPU  : Intel i5-9400F, 6 cekirdek / 6 THREAD (SMT yok)
#    RAM  : 16 GB DDR4-2667
#    Disk : Kioxia Exceria NVMe
#    OS   : Ubuntu 24.04 LTS / kernel 6.8
#
#  Kullanim:
#     chmod +x start.sh
#     ./start.sh
# ============================================================

# ------------------------------------------------------------
#  RAM — 8G. Bu bilincli bir secim, 12G DEGIL.
# ------------------------------------------------------------
#  16 GB toplam RAM'in var. Neden hepsini heap'e vermiyoruz:
#
#    8 GB   -> JVM heap (Minecraft)
#    ~1 GB  -> JVM overhead (metaspace, code cache, GC yapilari,
#              netty direct buffer, thread stack)
#    ~2 GB  -> Ubuntu 24.04 + arka plan servisleri
#    ~5 GB  -> OS PAGE CACHE  <<< BU ONEMLI
#
#  Page cache = Linux'un region dosyalarini (.mca) RAM'de
#  tutmasi. Senin sikayetin "chunk yavas yukleniyor" idi.
#  Page cache dolu oldugunda chunk'lar diskten degil RAM'den
#  gelir. 5 GB page cache ~ oyuncunun cevresindeki tum
#  bolgenin RAM'de durmasi demek.
#
#  Heap'i 12G yaparsan page cache'i 1 GB'a dusurursun ve
#  chunk yukleme YAVASLAR. Modern bir sunucuda 8G heap +
#  bol page cache, 12G heap + kuru cache'ten hizlidir.
#
#  ---- Ne zaman 10G yaparsin? ----
#  100+ modluk agir bir modpack calistiriyorsan ve log'da
#  surekli GC uyarisi / OutOfMemory goruyorsan. Onun disinda 8G.
#
#  Vanilla / hafif mod (20-30 mod) ise 6G bile yeter,
#  page cache 7 GB olur, chunk yukleme ucar.
# ------------------------------------------------------------
MEMORY="8G"

# ------------------------------------------------------------
#  LAUNCHER — surum numarasini KENDINE gore duzelt
# ------------------------------------------------------------
#  Kontrol et:  ls libraries/net/neoforged/neoforge/
NEOFORGE_VERSION="21.1.209"
LAUNCH_ARGS="@libraries/net/neoforged/neoforge/${NEOFORGE_VERSION}/unix_args.txt"

# Eski tarz duz jar kullaniyorsan:
# LAUNCH_ARGS="-jar server.jar"

# ------------------------------------------------------------
#  JAVA 21 — Ubuntu 24.04'te kurulum:
#     sudo apt install openjdk-21-jdk-headless
# ------------------------------------------------------------
JAVA="java"
# Birden fazla Java varsa zorla:
# JAVA="/usr/lib/jvm/java-21-openjdk-amd64/bin/java"

# ============================================================
#  BURADAN ASAGISI — kontroller
# ============================================================

JAVA_VER=$("$JAVA" -version 2>&1 | head -1 | grep -oP '(?<=version ")[0-9]+')
if [ "$JAVA_VER" != "21" ]; then
    echo "UYARI: Java 21 bekleniyordu, bulunan: ${JAVA_VER:-yok}"
    echo "  sudo apt install openjdk-21-jdk-headless"
    sleep 3
fi

if [ ! -f eula.txt ] || ! grep -q "eula=true" eula.txt; then
    echo "HATA: eula.txt yok veya eula=true degil."
    echo "  echo 'eula=true' > eula.txt"
    exit 1
fi

# ------------------------------------------------------------
#  JVM FLAG'LERI — 8G heap / 6 thread icin
# ------------------------------------------------------------
#  Neden G1GC:
#  ZGC'nin duraklamalari kisa ama throughput'u dusuk ve
#  GC icin daha cok THREAD ister. Senin 6 thread'in var,
#  ZGC bunlari ana tick thread'inden calar. G1 dogru secim.
#
#  ParallelGCThreads=4:
#  VARSAYILANI DEGISTIRIYORUZ. Java 6 cekirdekte varsayilan
#  olarak ~6 GC thread'i acar. Bu, GC sirasinda ana tick
#  thread'inin ve chunk worker'larinin CPU'sunu tamamen calar.
#  4'e sabitliyoruz.
#
#  ConcGCThreads=1:
#  Concurrent (arka plan) GC thread'i. Varsayilan
#  ParallelGCThreads/4 = 1, ama acikca yaziyoruz ki
#  Java surumu degisince bozulmasin.
#
#  G1NewSizePercent=30 / MaxNewSizePercent=40:
#  8G heap icin. (12G+ icin 40/50 kullanilir, sen 8G'desin.)
#
#  G1HeapRegionSize=8M:
#  8G heap icin dogru deger. 16M sadece 12G+ heap'te mantikli.
#
#  AlwaysPreTouch:
#  Tum 8G'i basta OS'ten alir. Acilis ~5 sn uzar,
#  karsiliginda runtime'da page fault olmaz.
#  16 GB RAM'in var, 8G'i pre-touch etmek guvenli.
# ------------------------------------------------------------

JVM_FLAGS=(
    -Xms${MEMORY}
    -Xmx${MEMORY}

    # --- G1 ---
    -XX:+UseG1GC
    -XX:+ParallelRefProcEnabled
    -XX:MaxGCPauseMillis=200
    -XX:+UnlockExperimentalVMOptions
    -XX:+DisableExplicitGC
    -XX:+AlwaysPreTouch

    # --- GC thread limiti (6-thread CPU icin KRITIK) ---
    -XX:ParallelGCThreads=4
    -XX:ConcGCThreads=1

    # --- Young gen: 8G heap degerleri ---
    -XX:G1NewSizePercent=30
    -XX:G1MaxNewSizePercent=40
    -XX:G1HeapRegionSize=8M

    -XX:G1ReservePercent=20
    -XX:G1HeapWastePercent=5
    -XX:G1MixedGCCountTarget=4
    -XX:InitiatingHeapOccupancyPercent=15
    -XX:G1MixedGCLiveThresholdPercent=90
    -XX:G1RSetUpdatingPauseTimePercent=5
    -XX:SurvivorRatio=32
    -XX:+PerfDisableSharedMem
    -XX:MaxTenuringThreshold=1

    # --- JIT / code cache ---
    -XX:ReservedCodeCacheSize=400M
    -XX:NonNMethodCodeHeapSize=12M
    -XX:ProfiledCodeHeapSize=194M
    -XX:NonProfiledCodeHeapSize=194M
    -XX:-DontCompileHugeMethods
    -XX:MaxNodeLimit=240000
    -XX:NodeLimitFudgeFactor=8000
    -XX:+UseVectorCmov
    -XX:+UseFastUnorderedTimeStamps
    -XX:AllocatePrefetchStyle=3

    # --- UseNUMA YOK ---
    # Tek soketli masaustu sistem. NUMA yok, flag anlamsiz.

    # --- Vector API (SIMD noise — Fast Noise / bazi worldgen modlari) ---
    # i5-9400F AVX2 destekler. Coffee Lake, AVX-512 YOK.
    --add-modules=jdk.incubator.vector

    # --- C2ME: Chunky pregen worker limiti ---
    # C2ME gelistiricisinin (ishland) tavsiye ettigi deger.
    # Chunky kurulu degilse zararsiz, gormezden gelinir.
    -Dchunky.maxWorkingCount=768

    # --- UseCompactObjectHeaders — SENDE KAPALI, sebebi asagida ---
    #
    # ishland (C2ME gelistiricisi) bu flag'i tavsiye ediyor:
    # nesne basliklarini 12 byte'tan 8 byte'a dusurur.
    # C2ME milyonlarca kucuk chunk/blockstate objesi tuttugu
    # icin RAM ve CPU cache kazanci ciddi olur.
    #
    # ⚠️ ANCAK: bu flag JAVA 24+ ister (JEP 450, Java 24'te
    #    experimental). Java 21'de YOK — eklersen JVM
    #    "Unrecognized VM option" verip HIC ACILMAZ.
    #
    # Bu script Java 21 hedefliyor (NeoForge 1.21.1'in resmi
    # gereksinimi), o yuzden kapali.
    #
    # Java 24/25'e gecersen: asagidaki satirin basindaki #
    # isaretini kaldir. (UnlockExperimentalVMOptions zaten var.)
    # -XX:+UseCompactObjectHeaders

    # --- Netty ---
    -Dio.netty.allocator.maxOrder=9
    -Dio.netty.leakDetection.level=disabled

    # --- Diger ---
    -Dusing.aikars.flags=https://mcflags.emc.gs
    -Daikars.new.flags=true
    -Dfile.encoding=UTF-8
    -Djava.awt.headless=true
    -Dlog4j2.formatMsgNoLookups=true
)

echo "==============================================="
echo "  Minecraft 1.21.1 NeoForge"
echo "  CPU  : $(nproc) thread (i5-9400F, SMT yok)"
echo "  Heap : $MEMORY   (kalan ~5G -> OS page cache)"
echo "  GC   : G1GC, ParallelGCThreads=4"
echo "==============================================="
echo ""

# --- C2ME sanity check ---
if [ -f config/c2me.toml ]; then
    echo "  c2me.toml kontrol:"
    grep -E "globalExecutorParallelism|^\s*enabled" config/c2me.toml 2>/dev/null \
        | head -4 | sed 's/^/    /'
    if ! grep -qE "globalExecutorParallelism\s*=\s*[45]" config/c2me.toml; then
        echo "    !! UYARI: globalExecutorParallelism 4 veya 5 degil."
        echo "       i5-9400F icin 5 olmali. C2ME-PAKET.md'ye bak."
    fi
else
    echo "  (config/c2me.toml yok — sunucu bir kez acilinca olusur)"
fi

# --- Moonrise kalintisi uyarisi ---
if ls mods/ 2>/dev/null | grep -qi "moonrise"; then
    echo ""
    echo "  !! DIKKAT: mods/ icinde Moonrise var."
    echo "     Moonrise C2ME ile TEMELDEN UYUMSUZ. Sunucu ya"
    echo "     acilmaz ya da ikisinden biri devre disi kalir."
    echo "     mods/Moonrise*.jar dosyasini SIL."
    sleep 5
fi
echo ""

# --- Otomatik yeniden baslatma ---
while true; do
    "$JAVA" "${JVM_FLAGS[@]}" $LAUNCH_ARGS nogui
    EXIT_CODE=$?
    echo ""
    echo "Sunucu kapandi (exit: $EXIT_CODE)"
    [ $EXIT_CODE -eq 0 ] && { echo "Duzgun kapanis."; break; }
    echo "Crash. 10 sn sonra yeniden baslatiliyor... (Ctrl+C = iptal)"
    sleep 10
done
