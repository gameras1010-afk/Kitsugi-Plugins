package com.majruszlibrary.registry;

import com.majruszlibrary.annotation.Dist;
import com.majruszlibrary.annotation.OnlyIn;
import com.majruszlibrary.mixin.IMixinCriteriaTriggers;
import com.majruszlibrary.modhelper.DataNeoForge;
import com.majruszlibrary.platform.Side;
import net.minecraft.client.particle.ParticleProvider;
import net.minecraft.client.particle.SpriteSet;
import net.minecraft.client.renderer.entity.EntityRenderers;
import net.minecraft.client.renderer.item.ItemProperties;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.enchantment.Enchantment;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.fml.event.lifecycle.FMLCommonSetupEvent;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.client.event.RegisterParticleProvidersEvent;
import net.neoforged.neoforge.event.entity.EntityAttributeCreationEvent;
import net.neoforged.neoforge.registries.DeferredRegister;
import org.jetbrains.annotations.NotNull;

import java.nio.file.Path;
import java.util.Iterator;
import java.util.function.Function;
import java.util.function.Supplier;

public class RegistryNeoForge implements IRegistryPlatform {
	@Override
	public < Type > void register( RegistryGroup< Type > group ) {
		DataNeoForge data = group.helper.getData( DataNeoForge.class );
		data.lastDeferredRegister = DeferredRegister.create( group.registry.key(), group.helper.getModId() );
		data.lastDeferredRegister.register( DataNeoForge.MOD_EVENT_BUS );
	}

	@Override
	public < Type > void register( RegistryObject< Type > object ) {
		DataNeoForge data = object.group.helper.getData( DataNeoForge.class );
		var forgeObject = ( ( DeferredRegister< Type > )data.lastDeferredRegister ).register( object.id, object.newInstance );
		object.set( forgeObject, () -> forgeObject.isBound() );
	}

	@Override
	public void register( RegistryCallbacks callbacks ) {
		IEventBus eventBus = DataNeoForge.MOD_EVENT_BUS;
		eventBus.addListener( ( FMLCommonSetupEvent event )->{
			// Advancements registration skipped - IMixinCriteriaTriggers target removed in 1.21.1
				// callbacks.execute( Custom.Advancements.class, IMixinCriteriaTriggers::register );
			// Potion recipe registration skipped - needs 1.21.1 update
		} );
		eventBus.addListener( ( EntityAttributeCreationEvent event )->{
			callbacks.execute( Custom.Attributes.class, event::put );
		} );
		eventBus.addListener( ( net.neoforged.neoforge.event.entity.RegisterSpawnPlacementsEvent event )->{
			callbacks.execute( Custom.SpawnPlacements.class, new CustomSpawnPlacements( event ) );
		} );

		Side.runOnClient( ()->()->{
			eventBus.addListener( ( final FMLClientSetupEvent event )->{
				callbacks.execute( Custom.ItemProperties.class, ItemProperties::register );
				callbacks.execute( Custom.Renderers.class, EntityRenderers::register );
			} );
			eventBus.addListener( ( final RegisterParticleProvidersEvent event )->{
				callbacks.execute( Custom.Particles.class, new CustomParticles( event ) );
			} );
			eventBus.addListener( ( final net.neoforged.neoforge.client.event.EntityRenderersEvent.RegisterLayerDefinitions event )->{
				callbacks.execute( Custom.ModelLayers.class, event::registerLayerDefinition );
			} );
		} );
	}

	@Override
	public IAccessor< Item > getItems() {
		return new Accessor<>( BuiltInRegistries.ITEM );
	}

	@Override
	public IAccessor< MobEffect > getEffects() {
		return new Accessor<>( BuiltInRegistries.MOB_EFFECT );
	}

	@Override
	public IAccessor< Enchantment > getEnchantments() {
		return new Accessor<>( BuiltInRegistries.ENCHANTMENT );
	}

	@Override
	public IAccessor< EntityType< ? > > getEntityTypes() {
		return new Accessor<>( BuiltInRegistries.ENTITY_TYPE );
	}

	@Override
	public IAccessor< SoundEvent > getSoundEvents() {
		return new Accessor<>( BuiltInRegistries.SOUND_EVENT );
	}

	@Override
	public Path getConfigPath() {
		return FMLPaths.CONFIGDIR.get();
	}

	private static class Accessor< Type > implements IAccessor< Type > {
		private final Registry< Type > registry;

		public Accessor( Registry< Type > registry ) {
			this.registry = registry;
		}

		@Override
		public ResourceLocation getId( Type value ) {
			return this.registry.getResourceKey( value ).map( ResourceKey::location ).orElseThrow();
		}

		@Override
		public Type get( ResourceLocation id ) {
			return this.registry.getOptional( ResourceKey.create( this.registry.key(), id ) ).orElse( null );
		}

		@Override
		public Iterable< Type > get() {
			return this.registry;
		}

		@Override
		public Holder< Type > getHolder( Type value ) {
			return this.registry.getResourceKey( value )
				.flatMap( this.registry::getHolder )
				.orElseThrow();
		}

		@Override
		public @NotNull Iterator< Type > iterator() {
			return this.registry.iterator();
		}
	}

	private static class CustomSpawnPlacements implements Custom.SpawnPlacements {
		final net.neoforged.neoforge.event.entity.RegisterSpawnPlacementsEvent event;

		public CustomSpawnPlacements( net.neoforged.neoforge.event.entity.RegisterSpawnPlacementsEvent event ) {
			this.event = event;
		}

		@Override
		public < Type extends net.minecraft.world.entity.Mob > void register( net.minecraft.world.entity.EntityType< Type > entityType,
			net.minecraft.world.entity.SpawnPlacementType type, net.minecraft.world.level.levelgen.Heightmap.Types heightmap,
			net.minecraft.world.entity.SpawnPlacements.SpawnPredicate< Type > predicate
		) {
			this.event.register( entityType, type, heightmap, predicate, net.neoforged.neoforge.event.entity.RegisterSpawnPlacementsEvent.Operation.AND );
		}
	}

	@OnlyIn( Dist.CLIENT )
	private static class CustomParticles implements Custom.Particles {
		final RegisterParticleProvidersEvent event;

		public CustomParticles( final RegisterParticleProvidersEvent event ) {
			this.event = event;
		}

		@Override
		public < Type extends ParticleOptions > void register( ParticleType< Type > type, Function< SpriteSet, ParticleProvider< Type > > factory ) {
			this.event.registerSpriteSet( type, factory::apply );
		}
	}
}
