package com.majruszlibrary.item;

import com.majruszlibrary.registry.Registries;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.ItemEnchantments;

import java.util.function.Supplier;

public class EnchantmentHelper {
	public static int getLevel( Supplier< ? extends Enchantment > enchantment, ItemStack itemStack ) {
		return net.minecraft.world.item.enchantment.EnchantmentHelper.getItemEnchantmentLevel( Registries.ENCHANTMENTS.getHolder( enchantment.get() ), itemStack );
	}

	public static int getLevel( Supplier< ? extends Enchantment > enchantment, LivingEntity entity ) {
		return net.minecraft.world.item.enchantment.EnchantmentHelper.getEnchantmentLevel( Registries.ENCHANTMENTS.getHolder( enchantment.get() ), entity );
	}

	public static int getLevelSum( Supplier< ? extends Enchantment > enchantment, Iterable< ItemStack > itemStacks ) {
		int sum = 0;
		for( ItemStack itemStack : itemStacks ) {
			sum += EnchantmentHelper.getLevel( enchantment, itemStack );
		}

		return sum;
	}

	public static int getLevelSum( Supplier< ? extends Enchantment > enchantment, LivingEntity entity ) {
		int sum = 0;
		for( EquipmentSlot slot : EquipmentSlot.values() ) {
			sum += EnchantmentHelper.getLevel( enchantment, entity.getItemBySlot( slot ) );
		}

		return sum;
	}

	public static int getLevelSum( Supplier< ? extends Enchantment > enchantment, LivingEntity entity, Iterable< EquipmentSlot > slots ) {
		int sum = 0;
		for( EquipmentSlot slot : slots ) {
			sum += EnchantmentHelper.getLevel( enchantment, entity.getItemBySlot( slot ) );
		}

		return sum;
	}

	public static boolean has( Supplier< ? extends Enchantment > enchantment, ItemStack itemStack ) {
		return EnchantmentHelper.getLevel( enchantment, itemStack ) > 0;
	}

	public static boolean has( Supplier< ? extends Enchantment > enchantment, LivingEntity entity ) {
		return EnchantmentHelper.getLevel( enchantment, entity ) > 0;
	}

	public static boolean increaseLevel( Supplier< ? extends Enchantment > enchantment, ItemStack itemStack ) {
		Holder< Enchantment > holder = Registries.ENCHANTMENTS.getHolder( enchantment.get() );
		int level = itemStack.getEnchantments().getLevel( holder );
		if( level >= enchantment.get().getMaxLevel() ) {
			return false;
		} else {
			itemStack.enchant( holder, level + 1 );
			return true;
		}
	}

	public static boolean remove( Supplier< ? extends Enchantment > enchantment, ItemStack itemStack ) {
		Holder< Enchantment > holder = Registries.ENCHANTMENTS.getHolder( enchantment.get() );
		ItemEnchantments enchantments = itemStack.getEnchantments();
		if( enchantments.getLevel( holder ) <= 0 ) {
			return false;
		}
		ItemEnchantments.Mutable mutable = new ItemEnchantments.Mutable( enchantments );
		mutable.removeIf( entry -> entry.equals( holder ) );
		itemStack.set( DataComponents.ENCHANTMENTS, mutable.toImmutable() );
		return true;
	}
}
