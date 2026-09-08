package com.example.wdablite;

import net.neoforged.fml.loading.FMLPaths;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Kurallar: config/wd-adblock-lite/rules.txt — satir basina bir regex (tam URL'e karsi).
 *  - "@" ile baslarsa: iptal yerine STUB (request URL'i bos JSON'a yeniden yazilir;
 *    YouTube oynatici "reklam yok" yaniti alip videoya kusursuz gecis yapar).
 *  - "#" ile baslarsa: yorum.
 * Liste her oyunda bir kez okunur; degisiklik icin MC'yi yeniden baslat (ileri: /command).
 */
public final class Rules {

    public record Rule(Pattern pattern, boolean stub) {}

    private static final Logger LOG = LoggerFactory.getLogger("WdAdBlockLite");
    private static final Path FILE = FMLPaths.CONFIGDIR.get().resolve("wd-adblock-lite").resolve("rules.txt");
    private static volatile List<Rule> cache;

    private Rules() {}

    public static List<Rule> get() {
        List<Rule> local = cache;
        if (local == null) {
            synchronized (Rules.class) {
                if (cache == null) cache = load();
                local = cache;
            }
        }
        return local;
    }

    private static List<Rule> load() {
        try {
            if (!Files.exists(FILE)) {
                Files.createDirectories(FILE.getParent());
                Files.writeString(FILE, DEFAULT_RULES, StandardCharsets.UTF_8);
                LOG.info("[WdAdBlockLite] varsayilan kural dosyasi olusturuldu: {}", FILE);
            }
            List<Rule> out = new ArrayList<>();
            for (String raw : Files.readAllLines(FILE, StandardCharsets.UTF_8)) {
                String line = raw.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                boolean stub = line.startsWith("@");
                if (stub) line = line.substring(1).trim();
                try {
                    out.add(new Rule(Pattern.compile(line, Pattern.CASE_INSENSITIVE), stub));
                } catch (Exception e) {
                    LOG.warn("[WdAdBlockLite] geçersiz regex atlandi: {}", raw);
                }
            }
            return out;
        } catch (IOException e) {
            LOG.error("[WdAdBlockLite] rules.txt okunamadi, varsayilanlarla devam", e);
            List<Rule> out = new ArrayList<>();
            for (String line : DEFAULT_RULES.split("\n")) {
                if (line.isBlank() || line.startsWith("#")) continue;
                boolean stub = line.startsWith("@");
                if (stub) line = line.substring(1).trim();
                out.add(new Rule(Pattern.compile(line, Pattern.CASE_INSENSITIVE), stub));
            }
            return out;
        }
    }

    /**
     * Varsayilan: sunucu-rekli kullanim icin kuru ama yuksek isabetli kume.
     * (Tam EasyList motoru degil — bilincli sinir, README'ye bak.)
     */
    static final String DEFAULT_RULES = """
            # WebDisplays AdBlock Lite kurallari — satir basina regex (tam URL).
            # "@" oneki: iptal yerine stub JSON dondurur (YouTube oynatici icin onemli).
            # YouTube reklam API'lari -> stub (pre-roll "atla" yerine temiz baslar)
            @^https?://(www\\.)?youtube\\.com/(pagead/|api/stats/ads|ptracking|get_midroll_).*
            @^https?://s0\\.2mdn\\.net/ads/.*
            # Klasik reklam/tracker aglari -> iptal
            ^https?://(doubleclick\\.net|googlesyndication\\.com|googleadservices\\.com|adservice\\.google\\.[a-z.]+|googletagservices\\.com)(/|$)
            ^https?://([a-z0-9-]+\\.)*(adnxs|pubmatic|openx|casalemedia|taboola|outbrain|criteo|scorecardresearch|moatads|amazon-adsystem|innity|smartadserver|advertising)\\.(com|net|org)(/|$)
            ^https?://(tpc\\.googleapis\\.com|ads\\.youtube\\.com|pagead2\\.googlesyndication\\.com)(/|$)
            # Banner/goruntu reklamlari (statik dosya imzalari) -> iptal
            ^https?://[^/]+/ads;?.*
            ^https?://[^/]+/(banner|popunder|interstitial)[^/]*\\.(gif|png|jpg|webp|swf)(\\?.*)?$
            """;
}
