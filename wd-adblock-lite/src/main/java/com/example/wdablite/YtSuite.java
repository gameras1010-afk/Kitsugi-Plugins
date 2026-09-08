package com.example.wdablite;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** ytsuite.js'i jar içinden bir kez okur, config ön-ekiyle birleştirir. */
public final class YtSuite {

    private static volatile String cachedResource;

    private YtSuite() {}

    /** executeJavaScript'e verilecek tam gövde: cfg + SponsorBlock/RYD/Enhancer scripti. */
    public static String payload() {
        return YtSuiteCfg.asJsPrelude() + "\n" + resource();
    }

    public static boolean available() {
        return !resource().isEmpty();
    }

    private static String resource() {
        String s = cachedResource;
        if (s != null) return s;
        try (InputStream in = YtSuite.class.getResourceAsStream("/ytsuite.js")) {
            s = in == null ? "" : new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            s = "";
        }
        if (s.isEmpty()) {
            WdAdblockLiteMod.LOG.warn("[WdAdBlockLite] ytsuite.js jar içinde bulunamadı — YT Suite devre dışı (adblock + skipper çalışmaya devam eder)");
        }
        cachedResource = s;
        return s;
    }
}
