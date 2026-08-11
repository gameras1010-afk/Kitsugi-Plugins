#!/usr/bin/env bash
# ============================================================
#  Minecraft 1.21.1 NeoForge — Sunucu Baslatma Scripti
#  Moonrise + Generator Accelerator yigini icin ayarlanmis
#
#  Kullanim:
#     chmod +x start.sh
#     ./start.sh
# ============================================================

# ------------------------------------------------------------
#  1) RAM AYARI  —  BURAYI DUZENLE
# ------------------------------------------------------------
#  KURAL: Xms ve Xmx AYNI olmali. Farkli yaparsan JVM heap'i
#  surekli buyutup kucultur, bu GC duraklamalari yaratir.
#
#  Makinede TOPLAM ne kadar RAM varsa, isletim sistemine
#  en az 2 GB birak.
#
#     8 GB makine  -> 6G
#    12 GB makine  -> 8G
#    16 GB makine  -> 12G
#    32 GB makine  -> 16G   (asagiyi oku)
#
#  !!! 16G USTUNE CIKMA !!!
#  Java 32GB'in altinda "Compressed OOPs" kullanir (pointer'lar
#  32-bit). 32GB'i gecince pointer'lar 64-bit olur, EFEKTIF
#  bellek DUSER ve GC yavaslar. 12-16G tatli nokta.
#  Daha fazla RAM'in varsa onu OS disk cache'ine birak —
#  chunk okuma hizini bu daha cok artirir.
# ------------------------------------------------------------
MEMORY="12G"

# ------------------------------------------------------------
#  2) JAR / LAUNCHER  —  BURAYI DUZENLE
# ------------------------------------------------------------
#  NeoForge 1.21.1 modern kurulumda @ dosyalari kullanilir.
#  Klasorunde hangisi varsa onu birak, digerini yorum yap.

# Modern NeoForge (onerilen, cogu kurulum bu):
LAUNCH_ARGS="@libraries/net/neoforged/neoforge/21.1.209/unix_args.txt"
#            ^^^^^^^^^^ SURUM NUMARASINI KENDI KURULUMUNA GORE DUZELT
#            Kontrol:  ls libraries/net/neoforged/neoforge/

# Eski tarz (duz jar):
# LAUNCH_ARGS="-jar server.jar"

# ------------------------------------------------------------
#  3) JAVA
# ------------------------------------------------------------
#  1.21.1 icin Java 21 SART. Java 17 calismaz, Java 25'i
#  NeoForge 21.1.x henuz tam desteklemiyor.
JAVA="java"
# Belirli bir Java'yi zorlamak istersen:
# JAVA="/usr/lib/jvm/java-21-openjdk-amd64/bin/java"

# ============================================================
#  BURADAN ASAGISINA DOKUNMA
# ============================================================

# --- Java surum kontrolu ---
JAVA_VER=$("$JAVA" -version 2>&1 | head -1 | grep -oP '(?<=version ")[0-9]+')
if [ "$JAVA_VER" != "21" ]; then
    echo "==============================================="
    echo "  UYARI: Java 21 bekleniyordu, bulunan: $JAVA_VER"
    echo "  Minecraft 1.21.1 + NeoForge Java 21 ister."
    echo "==============================================="
    sleep 3
fi

# --- EULA kontrolu ---
if [ ! -f eula.txt ] || ! grep -q "eula=true" eula.txt; then
    echo "HATA: eula.txt yok veya eula=true degil."
    echo "  echo 'eula=true' > eula.txt"
    exit 1
fi

# ------------------------------------------------------------
#  JVM FLAG'LERI — Aikar's Flags (G1GC), 12G+ icin ayarlanmis
# ------------------------------------------------------------
#  Neden G1GC ve ZGC degil:
#  ZGC duraklamalari daha kisa AMA toplam throughput'u dusuk.
#  Minecraft sunucusu icin onemli olan metrik ortalama MSPT'dir,
#  worst-case pause degil. 12-16G heap'te G1GC daha iyi TPS verir.
#  ZGC'nin anlamli oldugu yer 32GB+ heap'lerdir.
#
#  MaxGCPauseMillis=200:
#  Bir tick 50ms. 200ms pause = 4 tick kaybi. Daha dusuk yazmak
#  (or. 50) G1'i cok sik GC yapmaya zorlar, throughput coker.
#  200 dogru deger.
#
#  G1NewSizeSercent=40 / MaxNewSizePercent=50:
#  Minecraft cok sayida kisa omurlu obje uretir (chunk section,
#  packet, vektor). Young gen'i buyuk tutmak bunlarin old gen'e
#  terfi etmesini engeller — asil kazanc burada.
#  (12G+ heap icin degerler. 8G altindaysan asagidaki nota bak.)
#
#  G1MixedGCLiveThresholdPercent=90 / G1RSetUpdatingPauseTimePercent=5:
#  Mixed GC'nin daha agresif temizlik yapmasini saglar.
#
#  MaxTenuringThreshold=1 + AlwaysPreTouch:
#  Objeleri hizlica ya temizle ya terfi ettir. Ara durumda
#  surunmesinler. AlwaysPreTouch tum heap'i basta OS'ten alir —
#  acilis 5-10 sn uzar, karsiliginda runtime'da page fault olmaz.
# ------------------------------------------------------------

JVM_FLAGS=(
    -Xms${MEMORY}
    -Xmx${MEMORY}

    # --- Cop toplayici: G1 ---
    -XX:+UseG1GC
    -XX:+ParallelRefProcEnabled
    -XX:MaxGCPauseMillis=200
    -XX:+UnlockExperimentalVMOptions
    -XX:+DisableExplicitGC
    -XX:+AlwaysPreTouch

    # --- Young generation boyutlandirma (12G+ icin) ---
    # 8G ve altindaysan bu iki satiri sil, yerine:
    #   -XX:G1NewSizePercent=30
    #   -XX:G1MaxNewSizePercent=40
    -XX:G1NewSizePercent=40
    -XX:G1MaxNewSizePercent=50

    # --- Region boyutu (12G+ icin 16M; 8G ve altinda 8M yap) ---
    -XX:G1HeapRegionSize=16M

    -XX:G1ReservePercent=15
    -XX:G1HeapWastePercent=5
    -XX:G1MixedGCCountTarget=4
    -XX:InitiatingHeapOccupancyPercent=20
    -XX:G1MixedGCLiveThresholdPercent=90
    -XX:G1RSetUpdatingPauseTimePercent=5
    -XX:SurvivorRatio=32
    -XX:+PerfDisableSharedMem
    -XX:MaxTenuringThreshold=1

    # --- Chunk sistemi / worldgen icin ek ---
    # Buyuk chunk dizileri ve mixin'li kod yollari icin
    # JIT'in daha agresif inline yapmasini saglar.
    -XX:+UseNUMA
    -XX:NmethodSweepActivity=1
    -XX:ReservedCodeCacheSize=400M
    -XX:NonNMethodCodeHeapSize=12M
    -XX:ProfiledCodeHeapSize=194M
    -XX:NonProfiledCodeHeapSize=194M
    -XX:-DontCompileHugeMethods
    -XX:MaxNodeLimit=240000
    -XX:NodeLimitFudgeFactor=8000
    -XX:+UseVectorCmov
    -XX:+PerfDisableSharedMem
    -XX:+UseFastUnorderedTimeStamps
    -XX:+UseCriticalJavaThreadPriority
    -XX:AllocatePrefetchStyle=3

    # --- Vector API (Generator Accelerator'in SIMD noise'u icin) ---
    # VectorNoise modulu Java Vector API kullaniyor.
    --add-modules=jdk.incubator.vector

    # --- Bayraklar ---
    -Dusing.aikars.flags=https://mcflags.emc.gs
    -Daikars.new.flags=true

    # --- NeoForge / mixin ---
    -Dfile.encoding=UTF-8
    -Djava.awt.headless=true

    # --- Netty (ag) ---
    # Chunk paketleri buyuk. Netty'nin direct buffer'lari heap
    # disinda tutmasi GC baskisini azaltir.
    -Dio.netty.allocator.maxOrder=9
    -Dio.netty.leakDetection.level=disabled

    # --- Log4j guvenlik (eski surumlerden kalma, zararsiz) ---
    -Dlog4j2.formatMsgNoLookups=true
)

echo "==============================================="
echo "  Minecraft 1.21.1 NeoForge Server"
echo "  Heap    : $MEMORY"
echo "  GC      : G1GC (Aikar flags)"
echo "  Java    : $($JAVA -version 2>&1 | head -1)"
echo "  CPU     : $(nproc) thread"
echo "==============================================="
echo ""
echo "  Hatirlatma: config/moonrise.yml icindeki"
echo "  worker-threads degerini CPU'na gore ayarladin mi?"
echo ""

# --- Otomatik yeniden baslatma dongusu ---
# Crash olursa sunucu kendini toparlar.
# Istemiyorsan bu while dongusunu silip sadece
# "$JAVA" "${JVM_FLAGS[@]}" $LAUNCH_ARGS nogui  birak.
while true; do
    "$JAVA" "${JVM_FLAGS[@]}" $LAUNCH_ARGS nogui

    EXIT_CODE=$?
    echo ""
    echo "Sunucu kapandi (exit code: $EXIT_CODE)"

    if [ $EXIT_CODE -eq 0 ]; then
        echo "Duzgun kapanis. Cikiliyor."
        break
    fi

    echo "Crash tespit edildi. 10 saniye sonra yeniden baslatiliyor..."
    echo "Iptal etmek icin Ctrl+C."
    sleep 10
done
