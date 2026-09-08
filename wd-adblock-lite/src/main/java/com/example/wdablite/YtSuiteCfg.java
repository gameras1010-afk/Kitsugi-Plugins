package com.example.wdablite;

import net.neoforged.fml.loading.FMLPaths;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * config/wd-adblock-lite/yt-suite.txt — anahtar=değer.
 * sponsorblock=true|false   ryd=true|false
 * quality=4k|1440|1080|720|off
 * volume=80 (0-100, YT oynatici API'si)  speed=1.0  theater=false
loop=false
 * sbCategories=sponsor,selfpromo,interaction,intro,outro,filler
 */
public final class YtSuiteCfg {

    private static final Path FILE = FMLPaths.CONFIGDIR.get().resolve("wd-adblock-lite").resolve("yt-suite.txt");

    private static final String DEFAULTS = """
            # WebDisplays YT Suite ayarlari — anahtar=deger
            sponsorblock=true
            ryd=true
            quality=4k
            volume=80
            speed=1.0
            theater=false
loop=false
            sbCategories=sponsor,selfpromo,interaction,intro,outro,filler
            """;

    private YtSuiteCfg() {}

    /** JS'e verilecek `window.__wdYtCfg = {...};` on eki. */
    public static String asJsPrelude() {
        Map<String, String> kv = load();
        StringBuilder js = new StringBuilder("window.__wdYtCfg={");
        js.append("sponsorblock:").append(bool(kv, "sponsorblock", true)).append(",");
        js.append("ryd:").append(bool(kv, "ryd", true)).append(",");
        js.append("theater:").append(bool(kv, "theater", false)).append(",");
        js.append("loop:").append(bool(kv, "loop", false)).append(",");
        String q = kv.getOrDefault("quality", "4k");
        js.append("quality:").append(q.equalsIgnoreCase("off") || q.isBlank() ? "null" : "\"" + q.trim() + "\"").append(",");
        js.append("volume:").append(num(kv, "volume", 0).intValue()).append(",");
        js.append("speed:").append(num(kv, "speed", 1.0)).append(",");
        String cats = kv.getOrDefault("sbCategories", "sponsor,selfpromo,interaction,intro,outro,filler");
        js.append("sbCategories:[");
        String[] parts = cats.split(",");
        for (int i = 0; i < parts.length; i++) {
            if (i > 0) js.append(",");
            js.append("\"").append(parts[i].trim()).append("\"");
        }
        js.append("]};");
        return js.toString();
    }

    private static Map<String, String> load() {
        Map<String, String> out = new LinkedHashMap<>();
        try {
            if (!Files.exists(FILE)) {
                Files.createDirectories(FILE.getParent());
                Files.writeString(FILE, DEFAULTS, StandardCharsets.UTF_8);
            }
            List<String> lines = Files.readAllLines(FILE, StandardCharsets.UTF_8);
            for (String raw : lines) {
                String line = raw.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                int eq = line.indexOf('=');
                if (eq > 0) out.put(line.substring(0, eq).trim().toLowerCase(), line.substring(eq + 1).trim());
            }
        } catch (IOException e) {
            WdAdblockLiteMod.LOG.warn("[WdAdBlockLite] yt-suite.txt okunamadi, varsayilanlar kullanimda", e);
        }
        return out;
    }

    private static boolean bool(Map<String, String> m, String k, boolean def) {
        String v = m.get(k);
        return v == null ? def : (v.equalsIgnoreCase("true") || v.equals("1") || v.equalsIgnoreCase("yes"));
    }

    private static double num(Map<String, String> m, String k, double def) {
        try { return Double.parseDouble(m.getOrDefault(k, "").trim()); } catch (Exception e) { return def; }
    }
}
