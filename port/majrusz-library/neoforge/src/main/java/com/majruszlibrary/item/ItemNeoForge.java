package com.majruszlibrary.item;

import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.SpawnEggItem;
import net.neoforged.neoforge.common.DeferredSpawnEggItem;

import java.util.function.Supplier;

public class ItemNeoForge implements IItemPlatform {
	@Override
	public < Type extends EntityType< ? extends Mob > > Supplier< SpawnEggItem > createEgg( Supplier< Type > type, int backgroundColor, int highlightColor ) {
		return ()->new DeferredSpawnEggItem( type, backgroundColor, highlightColor, new Item.Properties() );
	}
}
