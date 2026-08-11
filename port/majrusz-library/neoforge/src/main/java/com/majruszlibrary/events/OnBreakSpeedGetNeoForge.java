package com.majruszlibrary.events;

import com.majruszlibrary.events.base.Events;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;

@EventBusSubscriber
public class OnBreakSpeedGetNeoForge {
	@SubscribeEvent
	public static void onBreakSpeed( PlayerEvent.BreakSpeed event ) {
		event.setNewSpeed( Events.dispatch( new OnBreakSpeedGet( event.getEntity(), event.getState(), event.getNewSpeed() ) ).speed );
	}
}
