package com.majruszlibrary.modhelper;

import com.majruszlibrary.registry.Custom;
import net.minecraft.advancements.Criterion;
import net.minecraft.advancements.critereon.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;

import java.util.Optional;

class AdvancementCaller {
	final ResourceLocation id;

	public AdvancementCaller( ModHelper helper ) {
		this.id = helper.getLocation( "basic_trigger" );

		// TODO: Re-register as CriterionTrigger when API is updated
		// helper.create( Custom.Advancements.class, advancements->advancements.register( this ) );
	}

	public ResourceLocation getId() {
		return this.id;
	}

	public void trigger( ServerPlayer player, String achievementId ) {
		// Trigger advancement
	}
}
