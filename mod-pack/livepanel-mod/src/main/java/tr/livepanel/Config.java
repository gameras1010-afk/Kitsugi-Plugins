package tr.livepanel;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Properties;

/**
 * config/livepanel.properties - basit ayar dosyasi.
 * Ilk calistirmada varsayilanlarla olusturulur.
 */
public class Config {
    private static Path file;
    private static final Properties props = new Properties();

    public static int intervalTicks = 60;      // 60 tick = 3 saniye
    public static boolean sidebar = true;      // sagdaki skorboard
    public static boolean actionbar = true;    // hotbar ustu canli yazi
    public static boolean motd = true;         // sunucu listesi aciklamasi
    public static boolean showGpu = true;      // GPU metrikleri
    public static boolean showTemps = true;    // sicakliklar
    public static int barSegments = 6;         // cekirdek cizgisi segmenti

    public static void init(Path gameDir) {
        file = gameDir.resolve("config/livepanel.properties");
        reload();
    }

    public static void reload() {
        try {
            if (file != null && Files.exists(file)) {
                try (InputStream in = Files.newInputStream(file)) {
                    props.load(in);
                }
            }
        } catch (IOException ignored) {
        }
        intervalTicks = Math.max(20, intOf("intervalSeconds", 3) * 20);
        sidebar = boolOf("sidebar", true);
        actionbar = boolOf("actionbar", true);
        motd = boolOf("motd", true);
        showGpu = boolOf("showGpu", true);
        showTemps = boolOf("showTemps", true);
        barSegments = Math.max(2, Math.min(16, intOf("barSegments", 6)));
        saveDefaults();
    }

    private static void saveDefaults() {
        if (file == null || Files.exists(file)) return;
        try {
            Files.createDirectories(file.getParent());
            try (OutputStream out = Files.newOutputStream(file)) {
                StringBuilder sb = new StringBuilder();
                sb.append("# LivePanel ayarlari\n");
                sb.append("# intervalSeconds: guncelleme araligi (saniye). 3 = 3 sn de bir\n");
                sb.append("intervalSeconds=3\n");
                sb.append("sidebar=true\n");
                sb.append("actionbar=true\n");
                sb.append("motd=true\n");
                sb.append("showGpu=true\n");
                sb.append("showTemps=true\n");
                sb.append("barSegments=6\n");
                out.write(sb.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8));
            }
        } catch (IOException ignored) {
        }
    }

    private static int intOf(String key, int def) {
        try {
            return Integer.parseInt(props.getProperty(key, String.valueOf(def)).trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static boolean boolOf(String key, boolean def) {
        String v = props.getProperty(key, def ? "true" : "false").trim();
        return v.equalsIgnoreCase("true") || v.equals("1") || v.equalsIgnoreCase("yes");
    }
}
