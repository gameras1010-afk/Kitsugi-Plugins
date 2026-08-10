package tr.livepanel;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.common.NeoForge;

@Mod(LivePanel.MODID)
public class LivePanel {
    public static final String MODID = "livepanel";

    public LivePanel(IEventBus modEventBus) {
        Config.init(FMLPaths.GAMEDIR.get());
        NeoForge.EVENT_BUS.register(PanelHandler.class);
    }
}
