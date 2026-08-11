package com.majruszlibrary.events;

import com.majruszlibrary.events.base.Events;
import net.neoforged.neoforge.event.entity.living.EnderManAngerEvent;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;

@EventBusSubscriber
public class OnEnderManAngeredNeoForge {
	@SubscribeEvent
	public static void onAnger( EnderManAngerEvent event ) {
		if( Events.dispatch( new OnEnderManAngered( event.getEntity(), event.getPlayer() ) ).isAngerCancelled() ) {
			event.setCanceled( true );
		}
	}
}
