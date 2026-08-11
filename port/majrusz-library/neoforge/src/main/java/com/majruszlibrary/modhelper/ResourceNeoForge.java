package com.majruszlibrary.modhelper;

import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.AddReloadListenerEvent;

public class ResourceNeoForge implements IResourcePlatform {
	@Override
	public void register( ResourceLocation id, ResourceLoader.Server server ) {
		NeoForge.EVENT_BUS.addListener( ( AddReloadListenerEvent event )->event.addListener( server ) );
	}
}
