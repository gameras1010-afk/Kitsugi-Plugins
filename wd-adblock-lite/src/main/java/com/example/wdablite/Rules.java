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

    /** blockhosts.txt: satir basina tam domain (Pi-hole/AdBlocker-Ultimate formati) -> O(1) HashSet. */
    private static volatile java.util.Set<String> hosts;

    public static boolean isBlockedHost(String url) {
        java.util.Set<String> h = hosts;
        if (h == null) {
            synchronized (Rules.class) {
                if (hosts == null) hosts = loadHosts();
            }
            h = hosts;
        }
        if (h.isEmpty()) return false;
        int i = url.indexOf("//");
        if (i < 0) return false;
        int s2 = i + 2, e = url.indexOf('/', s2);
        String host = (e < 0 ? url.substring(s2) : url.substring(s2, e));
        int at = host.lastIndexOf('@');
        if (at >= 0) host = host.substring(at + 1);
        int col = host.indexOf(':');
        if (col >= 0) host = host.substring(0, col);
        host = host.toLowerCase();
        String cur = host;
        while (cur != null) {
            if (h.contains(cur)) return true;   // a.b.c -> b.c -> c (parent domain'ler dahil)
            cur = stripSub(cur);
        }
        return false;
    }
    private static String stripSub(String host) {
        int d = host.indexOf('.');
        return (d > 0 && d < host.length() - 1) ? host.substring(d + 1) : null;
    }

    private static java.util.Set<String> loadHosts() {
        java.util.Set<String> set = new java.util.HashSet<>();
        try {
            Path f = FMLPaths.CONFIGDIR.get().resolve("wd-adblock-lite").resolve("blockhosts.txt");
            if (!Files.exists(f)) {
                WdAdblockLiteMod.LOG.info("[WdAdBlockLite] blockhosts.txt yok — hosts motoru bos (istersen easylist/hosts listesini buraya at)");
                return set;
            }
            for (String raw : Files.readAllLines(f, StandardCharsets.UTF_8)) {
                String line = raw.trim();
                if (line.isEmpty() || line.startsWith("#")) continue;
                // Pi-hole/hosts formati: "0.0.0.1 domain.com" ya da duz domain
                if (line.startsWith("0.0.0.0") || line.startsWith("127.0.0.1")) {
                    String[] parts = line.split("\s+");
                    if (parts.length > 1) line = parts[parts.length - 1];
                }
                if (line.startsWith("localhost")) continue;
                set.add(line.toLowerCase());
            }
            WdAdblockLiteMod.LOG.info("[WdAdBlockLite] blockhosts yuklendi: {} domain", set.size());
        } catch (Exception e) {
            WdAdblockLiteMod.LOG.warn("[WdAdblockLite] blockhosts okunamadi", e);
        }
        return set;
    }

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
