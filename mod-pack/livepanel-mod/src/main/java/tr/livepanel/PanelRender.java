package tr.livepanel;

import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetActionBarTextPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.scores.DisplaySlot;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.criteria.ObjectiveCriteria;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

/**
 * Canli panel cizimi:
 *  - MOTD (sunucu listesi aciklamasi)   [sürüme gore calisir; olmazsa sessizce atlar]
 *  - Action bar (hotbar ustu)            [her surumde calisir]
 *  - Sidebar skorboard (sag panel)       [her surumde calisir]
 */
public class PanelRender {
    private static final int C1 = 0x00E5FF; // cyan
    private static final int C2 = 0x7C3AED; // mor
    private static final int C3 = 0xFF6B6B; // kirmizi

    public static String hexCode(int rgb) {
        StringBuilder sb = new StringBuilder("\u00a7x");
        String h = String.format("%06x", rgb);
        for (char c : h.toCharArray()) sb.append('\u00a7').append(c);
        return sb.toString();
    }

    public static String gradient(String text, int from, int to) {
        if (text.isEmpty()) return text;
        StringBuilder sb = new StringBuilder();
        int n = text.length() - 1;
        for (int i = 0; i < text.length(); i++) {
            float t = n == 0 ? 0 : (float) i / n;
            int r = (int) ((1 - t) * ((from >> 16) & 255) + t * ((to >> 16) & 255));
            int g = (int) ((1 - t) * ((from >> 8) & 255) + t * ((to >> 8) & 255));
            int b = (int) ((1 - t) * (from & 255) + t * (to & 255));
            sb.append(hexCode((r << 16) | (g << 8) | b)).append(text.charAt(i));
        }
        return sb.toString();
    }

    public static String singleLine(StatsReader.Snapshot s) {
        StringBuilder sb = new StringBuilder();
        sb.append("\u00a7bTPS \u00a7f").append(fmt(s.tps))
          .append("\u00a77 | \u00a7bMSPT \u00a7f").append(fmt(s.mspt))
          .append("\u00a77 | \u00a7bCPU \u00a7f").append(s.cpuPercent >= 0 ? s.cpuPercent + "% (" + s.coresUsed + "/" + s.coresTotal + ")" : "?")
          .append("\u00a77 | \u00a7bRAM \u00a7f").append(s.ramUsedGB >= 0 ? fmt(s.ramUsedGB) + "/" + fmt(s.ramTotalGB) + "G" : "?");
        if (Config.showGpu) {
            sb.append("\u00a77 | \u00a7bGPU \u00a7f").append(s.gpuBusy >= 0 ? s.gpuBusy + "%" : "-");
        }
        if (Config.showTemps) {
            if (s.cpuTempC > 0) sb.append("\u00a77 | \u00a7bSICAKLIK \u00a7fCPU ").append((int) s.cpuTempC).append("C");
            if (s.gpuTempC > 0) sb.append(" GPU ").append((int) s.gpuTempC).append("C");
        }
        sb.append("\u00a77 | \u00a7bOYUNCU \u00a7f").append(s.players);
        return sb.toString();
    }

    public static void renderAll(MinecraftServer server, StatsReader.Snapshot s) {
        if (Config.sidebar) renderSidebar(server, s);
        if (Config.actionbar) renderActionbar(server, s);
        if (Config.motd) updateMotd(server, s);
    }

    private static void renderSidebar(MinecraftServer server, StatsReader.Snapshot s) {
        try {
            Scoreboard sb = server.getScoreboard();
            Objective obj = sb.getObjective("livepanel");
            if (obj == null) {
                obj = sb.addObjective("livepanel", ObjectiveCriteria.DUMMY,
                        Component.literal(gradient("\u00a7lCANLI PANEL", C1, C3)),
                        ObjectiveCriteria.RenderType.INTEGER);
            }
            sb.setDisplayObjective(DisplaySlot.SIDEBAR, obj);
            List<String> lines = sideLines(s);
            int score = lines.size();
            for (String line : lines) {
                sb.getOrCreatePlayerScore(line, obj).set(score--);
            }
        } catch (Exception ignored) {
        }
    }

    private static void renderActionbar(MinecraftServer server, StatsReader.Snapshot s) {
        try {
            Component comp = Component.literal(
                    gradient("\u00a7lKITSUGI MC ", C1, C2) + "\u00a77| " + singleLine(s));
            ClientboundSetActionBarTextPacket pkt = new ClientboundSetActionBarTextPacket(comp);
            for (ServerPlayer p : server.getPlayerList().getPlayers()) {
                p.connection.send(pkt);
            }
        } catch (Exception ignored) {
        }
    }

    /** MOTD'yi canli tutar. 1.21.1'de guvenilir yol: MinecraftServer#setMotd (getStatus bunu kullanir). */
    private static void updateMotd(MinecraftServer server, StatsReader.Snapshot s) {
        try {
            String line1 = gradient("KITSUGI MC ", C1, C3)
                    + "\u00a7r[CPU " + (s.cpuPercent >= 0 ? s.cpuPercent + "%" : "?") + "]"
                    + " [RAM " + (s.ramUsedGB >= 0 ? fmt(s.ramUsedGB) + "/" + fmt(s.ramTotalGB) + "G" : "?") + "]";
            String line2 = "[TPS " + fmt(s.tps) + "]"
                    + " [GPU " + (s.gpuBusy >= 0 ? s.gpuBusy + "%" : "-") + "]"
                    + " [" + s.coresUsed + "/" + s.coresTotal + " cekirdek]";
            // setMotd, sunucu listesindeki (MOTD) metni gunceller — her ping'de getStatus bunu kullanir
            server.setMotd(line1 + "\n" + line2);
        } catch (Throwable ignored) {
            // eski surumlerde setMotd yoksa: refleksiyon ile status.description dene
            try {
                Method m = server.getClass().getMethod("getStatus");
                Object status = m.invoke(server);
                String line1 = gradient("KITSUGI MC ", C1, C3)
                        + "\u00a7r[CPU " + (s.cpuPercent >= 0 ? s.cpuPercent + "%" : "?") + "]"
                        + " [RAM " + (s.ramUsedGB >= 0 ? fmt(s.ramUsedGB) + "/" + fmt(s.ramTotalGB) + "G" : "?") + "]";
                String line2 = "[TPS " + fmt(s.tps) + "]"
                        + " [GPU " + (s.gpuBusy >= 0 ? s.gpuBusy + "%" : "-") + "]"
                        + " [" + s.coresUsed + "/" + s.coresTotal + " cekirdek]";
                Component desc = Component.literal(line1 + "\n" + line2);
                Method set = status.getClass().getMethod("setDescription", Component.class);
                set.invoke(status, desc);
            } catch (Throwable ignored2) {
            }
        }
    }

    private static List<String> sideLines(StatsReader.Snapshot s) {
        List<String> lines = new ArrayList<>();
        lines.add("\u00a78--------------------------------");
        lines.add("\u00a7l\u00a7bTPS   \u00a77> \u00a7f" + fmt(s.tps) + "   \u00a77MSPT " + fmt(s.mspt));
        lines.add("\u00a7l\u00a7bCPU   \u00a77> \u00a7f" + (s.cpuPercent >= 0 ? s.cpuPercent + "%" : "?")
                + " \u00a77(" + s.coresUsed + "/" + s.coresTotal + ")");
        lines.add("\u00a77        " + coreBar(s));
        lines.add("\u00a7l\u00a7bRAM   \u00a77> \u00a7f" + (s.ramUsedGB >= 0 ? fmt(s.ramUsedGB) + "/" + fmt(s.ramTotalGB) + "G" : "?"));
        if (Config.showGpu) {
            lines.add("\u00a7l\u00a7bGPU   \u00a77> \u00a7f" + (s.gpuBusy >= 0 ? s.gpuBusy + "%" : "-")
                    + (s.vramUsedGB > 0 ? "  \u00a77VRAM " + fmt(s.vramUsedGB) + "G" : ""));
        }
        if (Config.showTemps) {
            if (s.cpuTempC > 0) lines.add("\u00a7l\u00a7bCPU T \u00a77> \u00a7f" + (int) s.cpuTempC + "C");
            if (s.gpuTempC > 0) lines.add("\u00a7l\u00a7bGPU T \u00a77> \u00a7f" + (int) s.gpuTempC + "C");
        }
        lines.add("\u00a7l\u00a7bOYUNCU \u00a77> \u00a7f" + s.players);
        lines.add("\u00a7l\u00a7bUPTIME \u00a77> \u00a7f" + uptime(s.uptimeSec));
        lines.add("\u00a78--------------------------------");
        return lines;
    }

    private static String coreBar(StatsReader.Snapshot s) {
        int segs = Config.barSegments;
        StringBuilder sb = new StringBuilder("\u00a77[");
        int filled = 0;
        if (s.perCore.length > 0) {
            double avg = 0;
            for (double v : s.perCore) avg += v;
            avg /= s.perCore.length;
            filled = (int) Math.round(avg * segs);
        }
        for (int i = 0; i < segs; i++) {
            sb.append(i < filled ? "\u00a7a\u2588" : "\u00a78\u2588");
        }
        sb.append("\u00a77]");
        return sb.toString();
    }

    private static String fmt(double d) {
        if (d < 0) return "?";
        return String.format(java.util.Locale.US, "%.1f", d);
    }

    private static String uptime(long sec) {
        long h = sec / 3600, m = (sec % 3600) / 60;
        return h > 0 ? h + "s " + m + "dk" : m + "dk";
    }
}
