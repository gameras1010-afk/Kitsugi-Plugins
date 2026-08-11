package com.majruszlibrary.mixin;

import com.majruszlibrary.events.OnItemAttributeTooltip;
import com.majruszlibrary.events.OnItemDamaged;
import com.majruszlibrary.events.OnItemTooltip;
import com.majruszlibrary.events.base.Events;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.CommonComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.LocalCapture;

import java.util.List;

@Mixin( value = ItemStack.class, priority = 1100 )
public abstract class MixinItemStack {
	@Inject(
		at = @At( "RETURN" ),
		cancellable = true,
		method = "hurt (ILnet/minecraft/util/RandomSource;Lnet/minecraft/server/level/ServerPlayer;)Z"
	)
	private void hurt( int damage, RandomSource source, ServerPlayer player, CallbackInfoReturnable< Boolean > callback ) {
		ItemStack itemStack = ( ItemStack )( Object )this;
		if( !itemStack.isDamageableItem() ) {
			return;
		}

		int extraDamage = Events.dispatch( new OnItemDamaged( player, itemStack, damage ) ).getExtraDamage();
		if( extraDamage != 0 ) {
			itemStack.setDamageValue( itemStack.getDamageValue() + extraDamage );
			callback.setReturnValue( itemStack.getDamageValue() >= itemStack.getMaxDamage() );
		}
	}

	@Inject(
		at = @At( "RETURN" ),
		cancellable = true,
		method = "getTooltipLines (Lnet/minecraft/world/item/Item$TooltipContext;Lnet/minecraft/world/entity/player/Player;Lnet/minecraft/world/item/TooltipFlag;)Ljava/util/List;"
	)
	private void getTooltipLines( Item.TooltipContext ctx, Player player, TooltipFlag flag, CallbackInfoReturnable< List< Component > > callback ) {
		List< Component > components = new java.util.ArrayList<>( callback.getReturnValue() );
		Events.dispatch( new OnItemTooltip( ( ItemStack )( Object )this, components, flag, player ) );

		OnItemAttributeTooltip data = Events.dispatch( new OnItemAttributeTooltip( ( ItemStack )( Object )this ) );
		for( EquipmentSlot slot : EquipmentSlot.values() ) {
			List< Component > slotComponents = data.components.get( slot );
			if( slotComponents.isEmpty() ) {
				continue;
			}

			int insertIdx = this.majruszlibrary$getInsertIdx( components, slot );
			if( insertIdx == -1 ) {
				components.add( CommonComponents.EMPTY );
				components.add( Component.translatable( this.majruszlibrary$getModifierId( slot ) ).withStyle( ChatFormatting.GRAY ) );
				components.addAll( slotComponents );
			} else {
				components.addAll( insertIdx, slotComponents );
			}
		}

		callback.setReturnValue( components );
	}

	private int majruszlibrary$getInsertIdx( List< Component > components, EquipmentSlot slot ) {
		for( int idx = 0; idx < components.size(); ++idx ) {
			if( !components.get( idx ).toString().contains( this.majruszlibrary$getModifierId( slot ) ) ) {
				continue;
			}

			for( int subIdx = idx + 1; subIdx < components.size(); ++subIdx ) {
				if( components.get( subIdx ).toString().contains( "item.modifiers" ) ) {
					return subIdx + 1;
				}
			}

			return components.size();
		}

		return -1;
	}

	private String majruszlibrary$getModifierId( EquipmentSlot slot ) {
		return String.format( "item.modifiers.%s", slot.getName() );
	}
}
