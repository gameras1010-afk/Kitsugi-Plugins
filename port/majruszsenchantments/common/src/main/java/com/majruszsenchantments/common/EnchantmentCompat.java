package com.majruszsenchantments.common;

import com.majruszlibrary.registry.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.item.enchantment.Enchantment;

public class EnchantmentCompat {
	public static boolean is( Enchantment enchantment, ResourceKey< Enchantment >... keys ) {
		if( enchantment == null ) {
			return false;
		}
		for( ResourceKey< Enchantment > key : keys ) {
			Enchantment value = Registries.ENCHANTMENTS.get( key.location() );
			if( value != null && enchantment.equals( value ) ) {
				return true;
			}
		}
		return false;
	}
}
