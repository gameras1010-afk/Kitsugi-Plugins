package com.majruszsenchantments.curses;

import com.majruszsenchantments.common.Categories;
import com.majruszlibrary.annotation.AutoInstance;
import com.majruszlibrary.data.Reader;
import com.majruszlibrary.events.OnItemDamaged;
import com.majruszlibrary.events.base.Priority;
import com.majruszlibrary.item.CustomEnchantment;
import com.majruszlibrary.item.EnchantmentHelper;
import com.majruszlibrary.item.EquipmentSlots;
import com.majruszlibrary.math.Random;
import com.majruszlibrary.math.Range;
import com.majruszsenchantments.MajruszsEnchantments;
import com.majruszsenchantments.common.EnchantmentCompat;
import com.majruszsenchantments.common.Handler;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;

@AutoInstance
public class BreakingCurse extends Handler {
	float damageMultiplier = 1.0f;

	public static CustomEnchantment create() {
		return new CustomEnchantment()
			.rarity( CustomEnchantment.Rarity.RARE )
			.category( Categories.BREAKABLE )
			.slots( EquipmentSlots.ALL )
			.curse()
			.maxLevel( 3 )
			.minLevelCost( level->10 )
			.maxLevelCost( level->50 )
			.compatibility( enchantment->!EnchantmentCompat.is( enchantment, Enchantments.UNBREAKING ) );
	}

	public BreakingCurse() {
		super( MajruszsEnchantments.BREAKING, BreakingCurse.class, true );

		OnItemDamaged.listen( this::dealExtraDamage )
			.priority( Priority.HIGH )
			.addCondition( data->data.player != null )
			.addCondition( data->EnchantmentHelper.has( this.enchantment, data.player ) );

		this.config.define( "damage_multiplier_per_level", Reader.number(), s->this.damageMultiplier, ( s, v )->{
			this.damageMultiplier = Range.of( 0.0f, 10.0f ).clamp( v );
		} );
	}

	private void dealExtraDamage( OnItemDamaged data ) {
		data.damage += Random.round( data.damage * EnchantmentHelper.getLevel( this.enchantment, data.itemStack ) * this.damageMultiplier );
	}
}
