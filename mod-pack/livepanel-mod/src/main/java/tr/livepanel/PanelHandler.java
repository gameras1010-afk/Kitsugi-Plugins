package tr.livepanel;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

public class PanelHandler {
    private static int counter = 0;
    private static StatsReader.Snapshot last;

    @SubscribeEvent
    public static void onServerTick(ServerTickEvent.Post event) {
        MinecraftServer server = event.getServer();
        counter++;
        int interval = Config.intervalTicks;
        if (interval <= 0 || counter % interval != 0) return;
        last = StatsReader.snapshot(server);
        PanelRender.renderAll(server, last);
    }

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();
        d.register(Commands.literal("livepanel")
                .executes(ctx -> {
                    String line = last != null
                            ? PanelRender.singleLine(last)
                            : "Henuz veri yok - bir kac saniye bekleyin...";
                    ctx.getSource().sendSuccess(() -> Component.literal(line), false);
                    return 1;
                })
                .then(Commands.literal("reload").executes(ctx -> {
                    Config.reload();
                    ctx.getSource().sendSuccess(() -> Component.literal("\u00a7aLivePanel config yenilendi."), false);
                    return 1;
                })));
    }
}
