package com.majruszsenchantments.common;

import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.DiggerItem;
import net.minecraft.world.item.FishingRodItem;
import net.minecraft.world.item.ItemStack;

import java.util.function.Predicate;

public class Categories {
	public static final Predicate< ItemStack > BREAKABLE = itemStack->itemStack.isDamageableItem();
	public static final Predicate< ItemStack > ARMOR = itemStack->itemStack.getItem() instanceof ArmorItem;
	public static final Predicate< ItemStack > ARMOR_LEGS = itemStack->itemStack.getItem() instanceof ArmorItem armor && armor.getType() == ArmorItem.Type.LEGGINGS;
	public static final Predicate< ItemStack > ARMOR_HEAD = itemStack->itemStack.getItem() instanceof ArmorItem armor && armor.getType() == ArmorItem.Type.HELMET;
	public static final Predicate< ItemStack > FISHING_ROD = itemStack->itemStack.getItem() instanceof FishingRodItem;
	public static final Predicate< ItemStack > DIGGER = itemStack->itemStack.getItem() instanceof DiggerItem;
}
