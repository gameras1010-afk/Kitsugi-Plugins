package com.majruszlibrary.events;

import com.majruszlibrary.events.base.Events;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;

@EventBusSubscriber( value = Dist.CLIENT, bus = EventBusSubscriber.Bus.MOD )
public class OnGameInitializedNeoForge {
	@SubscribeEvent
	public static void initialize( FMLClientSetupEvent event ) {
		event.enqueueWork( ()->Events.dispatch( new OnGameInitialized() ) );
	}
}
