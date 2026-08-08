package tr.livepanel;

import net.minecraft.server.MinecraftServer;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

/**
 * Linux /proc + sysfs okuyarak canli sistem metriklerini toplar.
 * Headless (arayuzsuz) sunucuda da calisir; dosyalar yoksa -1 / 0 doner.
 */
public class StatsReader {

    public static class Snapshot {
        public double cpuPercent = -1;
        public int coresTotal = 0;
        public int coresUsed = 0;
        public double[] perCore = new double[0];
        public double ramTotalGB = -1;
        public double ramUsedGB = -1;
        public double load1 = -1;
        public long uptimeSec = 0;
        public double cpuTempC = -1;
        public double gpuTempC = -1;
        public int gpuBusy = -1;
        public double vramUsedGB = -1;
        public double vramTotalGB = -1;
        public double mspt = -1;
        public double tps = 20;
        public int players = 0;
    }

    private static long[] prevTotal;
    private static long[] prevIdle;

    public static Snapshot snapshot(MinecraftServer server) {
        Snapshot s = new Snapshot();
        readCpu(s);
        readMem(s);
        readLoadUptime(s);
        s.cpuTempC = readCpuTemp();
        if (Config.showGpu) {
            s.gpuBusy = readInt("/sys/class/drm/card0/device/gpu_busy_percent");
            s.vramUsedGB = bytesToGb(readLong("/sys/class/drm/card0/device/mem_info_vram_used"));
            s.vramTotalGB = bytesToGb(readLong("/sys/class/drm/card0/device/mem_info_vram_total"));
            s.gpuTempC = readGpuTemp();
        }
        try {
            s.mspt = server.getAverageTickTime();
            s.tps = Math.max(0, Math.min(20.0, 1000.0 / Math.max(s.mspt, 0.001)));
        } catch (Exception ignored) {
        }
        try {
            s.players = server.getPlayerList().getPlayers().size();
        } catch (Exception ignored) {
        }
        return s;
    }

    private static void readCpu(Snapshot s) {
        try {
            List<String> lines = Files.readAllLines(Paths.get("/proc/stat"));
            int count = 0;
            for (String l : lines) {
                if (l.startsWith("cpu") && !l.startsWith("cpu ")) count++;
            }
            if (count == 0) return;
            long[] total = new long[count];
            long[] idle = new long[count];
            int idx = 0;
            for (String l : lines) {
                if (!l.startsWith("cpu") || l.startsWith("cpu ")) continue;
                String[] t = l.trim().split("\\s+");
                if (t.length < 5) continue;
                long idleT;
                long totalT = 0;
                try {
                    idleT = Long.parseLong(t[4]) + Long.parseLong(t[5]);
                    for (int i = 1; i < t.length; i++) totalT += Long.parseLong(t[i]);
                } catch (Exception e) {
                    continue;
                }
                total[idx] = totalT;
                idle[idx] = idleT;
                idx++;
            }
            s.coresTotal = idx;
            if (prevTotal != null && prevTotal.length == idx) {
                double sum = 0;
                int used = 0;
                double[] per = new double[idx];
                for (int i = 0; i < idx; i++) {
                    long dt = total[i] - prevTotal[i];
                    long di = idle[i] - prevIdle[i];
                    double busy = dt > 0 ? Math.max(0, Math.min(1, 1.0 - (double) di / dt)) : 0;
                    per[i] = busy;
                    sum += busy;
                    if (busy > 0.05) used++;
                }
                s.perCore = per;
                s.cpuPercent = Math.round(sum * 100.0 / idx);
                s.coresUsed = used;
            }
            prevTotal = total;
            prevIdle = idle;
        } catch (Exception ignored) {
        }
    }

    private static void readMem(Snapshot s) {
        try {
            long totalKb = -1, availKb = -1;
            for (String l : Files.readAllLines(Paths.get("/proc/meminfo"))) {
                if (l.startsWith("MemTotal:")) totalKb = kb(l);
                else if (l.startsWith("MemAvailable:")) availKb = kb(l);
            }
            if (totalKb > 0) {
                s.ramTotalGB = totalKb / 1024.0 / 1024.0;
                s.ramUsedGB = availKb >= 0 ? (totalKb - availKb) / 1024.0 / 1024.0 : -1;
            }
        } catch (Exception ignored) {
        }
    }

    private static void readLoadUptime(Snapshot s) {
        try {
            String[] l = Files.readString(Paths.get("/proc/loadavg")).trim().split("\\s+");
            s.load1 = Float.parseFloat(l[0]);
        } catch (Exception ignored) {
        }
        try {
            String[] u = Files.readString(Paths.get("/proc/uptime")).trim().split("\\s+");
            s.uptimeSec = (long) Double.parseDouble(u[0]);
        } catch (Exception ignored) {
        }
    }

    private static long kb(String line) {
        String[] t = line.trim().split("\\s+");
        return t.length >= 2 ? Long.parseLong(t[1]) : -1;
    }

    private static double bytesToGb(long b) {
        return b > 0 ? b / 1024.0 / 1024.0 / 1024.0 : -1;
    }

    private static int readInt(String path) {
        try {
            return Integer.parseInt(Files.readString(Paths.get(path)).trim());
        } catch (Exception e) {
            return -1;
        }
    }

    private static long readLong(String path) {
        try {
            return Long.parseLong(Files.readString(Paths.get(path)).trim());
        } catch (Exception e) {
            return -1;
        }
    }

    private static double readCpuTemp() {
        try (var stream = Files.list(Paths.get("/sys/class/thermal"))) {
            for (Path z : stream.toList()) {
                Path type = z.resolve("type");
                if (!Files.exists(type)) continue;
                String t = Files.readString(type).trim().toLowerCase();
                if (t.contains("x86_pkg_temp") || t.contains("coretemp") || t.contains("cpu")) {
                    Path temp = z.resolve("temp");
                    if (Files.exists(temp)) {
                        double millis = Double.parseDouble(Files.readString(temp).trim());
                        return millis / 1000.0;
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return -1;
    }

    private static double readGpuTemp() {
        try (var stream = Files.list(Paths.get("/sys/class/drm/card0/device/hwmon"))) {
            for (Path h : stream.toList()) {
                Path t1 = h.resolve("temp1_input");
                if (Files.exists(t1)) {
                    double millis = Double.parseDouble(Files.readString(t1).trim());
                    return millis / 1000.0;
                }
            }
        } catch (Exception ignored) {
        }
        return -1;
    }
}
