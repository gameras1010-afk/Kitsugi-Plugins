package com.majruszlibrary.item;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.ChatFormatting;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.ItemTagBased;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

// NOTE: In Minecraft 1.21.1, Enchantment can no longer be extended (it is effectively sealed).
// Custom enchantments must be registered via data-driven JSON files (data/<namespace>/enchantment/<name>.json).
// This class now serves as a configuration holder; the actual Enchantment registration requires data-gen.
public class CustomEnchantment {
	public enum Rarity { COMMON, UNCOMMON, RARE, VERY_RARE }

	private boolean isCurse = false;
	private boolean isEnabled = true;
	private int maxLevel = 1;
	private CostFormula minLevelCost = level->10;
	private CostFormula maxLevelCost = level->50;
	private Predicate< Enchantment > compatibility = enchantment->true;
	private Predicate< ItemStack > enchantability = itemStack->false;
	private Rarity rarity = Rarity.COMMON;
	private EquipmentSlot[] slots = new EquipmentSlot[ 0 ];
	private ResourceKey< Enchantment > key = null;

	public CustomEnchantment() {}

	public int getMaxLevel() {
		return this.maxLevel;
	}

	public int getMinCost( int enchantmentLevel ) {
		return this.minLevelCost.getLevelCost( enchantmentLevel );
	}

	public int getMaxCost( int enchantmentLevel ) {
		return this.maxLevelCost.getLevelCost( enchantmentLevel );
	}

	public boolean canEnchant( ItemStack itemStack ) {
		return this.isEnabled()
			&& this.enchantability.test( itemStack );
	}

	public boolean isTradeable() {
		return this.isEnabled();
	}

	public boolean isDiscoverable() {
		return this.isEnabled();
	}

	public boolean isTreasureOnly() {
		return this.isCurse;
	}

	public boolean isCurse() {
		return this.isCurse;
	}

	public boolean checkCompatibility( Enchantment enchantment ) {
		return this.compatibility.test( enchantment );
	}

	public CustomEnchantment slots( List< EquipmentSlot > slots ) {
		this.slots = slots.toArray( EquipmentSlot[]::new );

		return this;
	}

	public EquipmentSlot[] getSlots() {
		return this.slots;
	}

	public CustomEnchantment rarity( Rarity rarity ) {
		this.rarity = rarity;

		return this;
	}

	public Rarity getRarity() {
		return this.rarity;
	}

	public CustomEnchantment category( Predicate< ItemStack > predicate ) {
		this.enchantability = predicate;

		return this;
	}

	public CustomEnchantment curse() {
		this.isCurse = true;

		return this;
	}

	public CustomEnchantment maxLevel( int level ) {
		this.maxLevel = level;

		return this;
	}

	public CustomEnchantment minLevelCost( CostFormula formula ) {
		this.minLevelCost = formula;

		return this;
	}

	public CustomEnchantment maxLevelCost( CostFormula formula ) {
		this.maxLevelCost = formula;

		return this;
	}

	public CustomEnchantment compatibility( Predicate< Enchantment > predicate ) {
		this.compatibility = predicate;

		return this;
	}

	public void setEnabled( boolean isEnabled ) {
		this.isEnabled = isEnabled;
	}

	public boolean isEnabled() {
		return this.isEnabled;
	}

	public boolean canEnchantUsingEnchantingTable( ItemStack itemStack ) {
		return this.canEnchant( itemStack );
	}

	public String getDescriptionId() {
		return "enchantment." + this.key.location().getNamespace() + "." + this.key.location().getPath();
	}

	public Component getFullname( int level ) {
		ChatFormatting color = switch( this.rarity ) {
			case COMMON -> ChatFormatting.GRAY;
			case UNCOMMON -> ChatFormatting.YELLOW;
			case RARE -> ChatFormatting.AQUA;
			case VERY_RARE -> ChatFormatting.LIGHT_PURPLE;
		};
		MutableComponent component = Component.translatable( this.getDescriptionId() );
		if( this.isCurse ) {
			component.withStyle( ChatFormatting.RED );
		} else {
			component.withStyle( color );
		}
		return component;
	}

	public Enchantment toEnchantment( ResourceKey< Enchantment > key ) {
		this.key = key;
		List< Item > items = new ArrayList<>();
		for( Item item : BuiltInRegistries.ITEM ) {
			if( this.enchantability.test( new ItemStack( item ) ) ) {
				items.add( item );
			}
		}
		ItemTagBased supportedItems = ItemTagBased.items( items.toArray( new Item[ 0 ] ) );
		int minCostBase = this.minLevelCost.getLevelCost( 1 );
		int minCostPerLevel = Math.max( this.minLevelCost.getLevelCost( 2 ) - minCostBase, 1 );
		int maxCostBase = this.maxLevelCost.getLevelCost( 1 );
		int maxCostPerLevel = Math.max( this.maxLevelCost.getLevelCost( 2 ) - maxCostBase, 1 );
		Enchantment.EnchantmentDefinition.Builder builder = Enchantment.EnchantmentDefinition.builder( supportedItems )
			.withPrimaryItems( supportedItems )
			.withMaxLevel( this.maxLevel )
			.withWeight( this.isCurse ? 3 : 10 )
			.withMinCost( new Enchantment.Cost( minCostBase, minCostPerLevel ) )
			.withMaxCost( new Enchantment.Cost( maxCostBase, maxCostPerLevel ) )
			.withAnvilCost( 1 );
		for( EquipmentSlot slot : this.slots ) {
			builder.withSlot( slot );
		}
		if( this.isCurse ) {
			builder.withCurse();
			builder.withTreasureOnly();
		}
		return Enchantment.enchantment( builder.build() ).build( key );
	}

	@FunctionalInterface
	public interface CostFormula {
		int getLevelCost( int level );
	}
}
