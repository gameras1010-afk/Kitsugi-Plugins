package com.majruszlibrary;

import com.majruszlibrary.modhelper.DataNeoForge;
import net.neoforged.fml.common.Mod;
import net.neoforged.bus.api.IEventBus;

@Mod( MajruszLibrary.MOD_ID )
public class Initializer {
    public Initializer( IEventBus bus ) {
        DataNeoForge.MOD_EVENT_BUS = bus;
        MajruszLibrary.HELPER.register();
	bus.register( com.majruszlibrary.network.NetworkNeoForge.class );
    }
}
