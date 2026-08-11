package com.majruszlibrary.mixin.neoforge;

import com.majruszlibrary.events.OnFishingTimeGet;
import com.majruszlibrary.events.base.Events;
import com.majruszlibrary.mixin.MixinFishingHook;
import com.teammetallurgy.aquaculture.entity.AquaFishingBobberEntity;
import org.spongepowered.asm.mixin.Dynamic;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Pseudo
@Mixin( targets = "com.teammetallurgy.aquaculture.entity.AquaFishingBobberEntity" )
public abstract class MixinAquaFishingBobberEntity extends MixinFishingHook {
	@Dynamic( "Aquaculture 2 compatibility" )
	@Redirect(
		at = @At(
			opcode = 181, // putfield
			ordinal = 3,
			target = "Lcom/teammetallurgy/aquaculture/entity/AquaFishingBobberEntity;timeUntilLured:I",
			value = "FIELD"
		),
		method = {
			"catchingFish (Lnet/minecraft/core/BlockPos;)V",
			"*(Lnet/minecraft/core/BlockPos;)V"
		},
		require = 0
	)
	private void catchingFish( AquaFishingBobberEntity hook, int timeUntilLured ) {
		this.timeUntilLured = Events.dispatch( new OnFishingTimeGet( hook, timeUntilLured ) ).getTicks();
	}
}
