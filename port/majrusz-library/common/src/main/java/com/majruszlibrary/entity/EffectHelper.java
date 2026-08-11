package com.majruszlibrary.entity;

import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.LivingEntity;

import java.util.Optional;
import java.util.function.Supplier;

public class EffectHelper {
	public static Applier createApplier( Supplier< ? extends MobEffect > effect ) {
		return new Applier( effect );
	}

	public static boolean has( Supplier< ? extends MobEffect > effect, LivingEntity entity ) {
		return entity.hasEffect( BuiltInRegistries.MOB_EFFECT.wrapAsHolder( effect.get() ) );
	}

	public static Optional< Integer > getAmplifier( Supplier< ? extends MobEffect > effect, LivingEntity entity ) {
		return Optional.ofNullable( entity.getEffect( BuiltInRegistries.MOB_EFFECT.wrapAsHolder( effect.get() ) ) ).map( MobEffectInstance::getAmplifier );
	}

	public static Optional< Integer > getDuration( Supplier< ? extends MobEffect > effect, LivingEntity entity ) {
		return Optional.ofNullable( entity.getEffect( BuiltInRegistries.MOB_EFFECT.wrapAsHolder( effect.get() ) ) ).map( MobEffectInstance::getDuration );
	}

	public static class Applier {
		final Supplier< ? extends MobEffect > effect;
		Integer maxDuration = null;
		Integer maxAmplifier = null;
		int duration = 100;
		int amplifier = 0;

		public Applier duration( int duration ) {
			this.duration = duration;

			return this;
		}

		public Applier amplifier( int amplifier ) {
			this.amplifier = amplifier;

			return this;
		}

		public Applier stackableDuration( int max ) {
			this.maxDuration = max;

			return this;
		}

		public Applier stackableAmplifier( int max ) {
			this.maxAmplifier = max;

			return this;
		}

		public void apply( LivingEntity entity ) {
			int duration = this.duration;
			int amplifier = this.amplifier;
			Holder< MobEffect > holder = BuiltInRegistries.MOB_EFFECT.wrapAsHolder( this.effect.get() );
			MobEffectInstance previous = entity.getEffect( holder );
			if( previous != null ) {
				if( this.maxDuration != null ) {
					duration = Math.min( duration + previous.getDuration(), this.maxDuration );
				}
				if( this.maxAmplifier != null ) {
					amplifier = Math.min( amplifier + previous.getAmplifier() + 1, this.maxAmplifier );
				}
			}

			entity.addEffect( new MobEffectInstance( holder, duration, amplifier ) );
		}

		private Applier( Supplier< ? extends MobEffect > effect ) {
			this.effect = effect;
		}
	}
}
