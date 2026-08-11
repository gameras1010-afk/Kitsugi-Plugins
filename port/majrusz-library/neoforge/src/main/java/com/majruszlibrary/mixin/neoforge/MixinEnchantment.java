package com.majruszlibrary.mixin.neoforge;

import com.majruszlibrary.item.CustomEnchantment;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.Enchantment;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin( Enchantment.class )
public abstract class MixinEnchantment {
	// canApplyAtEnchantingTable removed in NeoForge 1.21.1
	// Custom enchantments now handled via data-driven Enchantment.canEnchant(ItemStack)
}
