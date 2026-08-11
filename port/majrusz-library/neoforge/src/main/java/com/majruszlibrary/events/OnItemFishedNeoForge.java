package com.majruszlibrary.events;

import com.majruszlibrary.events.base.Events;
import net.minecraft.world.entity.player.Player;
import net.neoforged.neoforge.event.entity.player.ItemFishedEvent;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;

@EventBusSubscriber
public class OnItemFishedNeoForge {
	@SubscribeEvent
	public static void onItemFished( ItemFishedEvent event ) {
		Player player = event.getEntity();

		Events.dispatch( new OnItemFished( player, event.getHookEntity(), player.getItemInHand( player.getUsedItemHand() ), event.getDrops() ) );
	}
}
