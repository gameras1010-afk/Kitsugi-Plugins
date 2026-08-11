package com.majruszsenchantments.mixin;

import com.majruszsenchantments.data.Config;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ShieldItem;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin( Item.class )
public abstract class MixinItem {
	@Inject(
		at = @At( "RETURN" ),
		cancellable = true,
		method = "getEnchantmentValue (Lnet/minecraft/world/item/ItemStack;)I"
	)
	protected void getEnchantmentValue( ItemStack itemStack, CallbackInfoReturnable< Integer > callback ) {
		if( Config.IS_HORSE_ARMOR_ENCHANTABLE && isHorseArmor( itemStack ) ) {
			callback.setReturnValue( 1 );
		}
		if( Config.IS_SHIELD_ENCHANTABLE && itemStack.getItem() instanceof ShieldItem ) {
			callback.setReturnValue( 1 );
		}
	}

	@Inject(
		at = @At( "RETURN" ),
		cancellable = true,
		method = "isEnchantable (Lnet/minecraft/world/item/ItemStack;)Z"
	)
	protected void isEnchantable( ItemStack itemStack, CallbackInfoReturnable< Boolean > callback ) {
		if( Config.IS_HORSE_ARMOR_ENCHANTABLE && isHorseArmor( itemStack ) ) {
			callback.setReturnValue( true );
		}
		if( Config.IS_SHIELD_ENCHANTABLE && itemStack.getItem() instanceof ShieldItem ) {
			callback.setReturnValue( itemStack.getMaxStackSize() == 1 );
		}
	}

	private static boolean isHorseArmor( ItemStack itemStack ) {
		return itemStack.is( Items.LEATHER_HORSE_ARMOR ) || itemStack.is( Items.IRON_HORSE_ARMOR )
			|| itemStack.is( Items.GOLDEN_HORSE_ARMOR ) || itemStack.is( Items.DIAMOND_HORSE_ARMOR );
	}
}
