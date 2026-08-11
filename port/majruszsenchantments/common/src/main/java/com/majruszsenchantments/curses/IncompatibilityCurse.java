package com.majruszsenchantments.curses;

import com.majruszsenchantments.common.Categories;
import com.majruszlibrary.annotation.AutoInstance;
import com.majruszlibrary.item.CustomEnchantment;
import com.majruszlibrary.item.EquipmentSlots;
import com.majruszsenchantments.MajruszsEnchantments;
import com.majruszsenchantments.common.Handler;
import net.minecraft.world.item.enchantment.Enchantment;

@AutoInstance
public class IncompatibilityCurse extends Handler {
	public static CustomEnchantment create() {
		return new CustomEnchantment()
			.rarity( CustomEnchantment.Rarity.RARE )
			.category( Categories.BREAKABLE )
			.slots( EquipmentSlots.ALL )
			.curse()
			.minLevelCost( level->10 )
			.maxLevelCost( level->50 )
			.compatibility( enchantment->false );
	}

	public IncompatibilityCurse() {
		super( MajruszsEnchantments.INCOMPATIBILITY, IncompatibilityCurse.class, true );
	}
}
