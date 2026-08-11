package com.majruszsenchantments;

import com.majruszlibrary.annotation.Dist;
import com.majruszlibrary.annotation.OnlyIn;
import com.majruszlibrary.item.CustomEnchantment;
import com.majruszlibrary.item.ItemHelper;
import com.majruszlibrary.modhelper.ModHelper;
import com.majruszlibrary.registry.Custom;
import com.majruszlibrary.registry.RegistryGroup;
import com.majruszlibrary.registry.RegistryObject;
import com.majruszsenchantments.curses.*;
import com.majruszsenchantments.data.Config;
import com.majruszsenchantments.enchantments.*;
import com.majruszsenchantments.particles.DodgeParticle;
import com.majruszsenchantments.particles.SmelterParticle;
import com.majruszsenchantments.particles.TelekinesisParticle;
import com.majruszsenchantments.particles.TelekinesisParticleType;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.*;
import net.minecraft.world.item.enchantment.Enchantment;

import java.util.function.Predicate;

public class MajruszsEnchantments {
	public static final String MOD_ID = "majruszsenchantments";
	public static final ModHelper HELPER = ModHelper.create( MOD_ID );

	// Configs
	static {
		HELPER.config( Config.class ).autoSync().create();
	}

	// Registry Groups
	public static final RegistryGroup< Enchantment > ENCHANTMENTS = HELPER.create( Registries.ENCHANTMENT );
	public static final RegistryGroup< ParticleType< ? > > PARTICLES = HELPER.create( BuiltInRegistries.PARTICLE_TYPE );

	// Enchantments
	public static final RegistryObject< Enchantment > DEATH_WISH = ENCHANTMENTS.create( "death_wish", ()->DeathWishEnchantment.create().toEnchantment( key( "death_wish" ) ) );
	public static final RegistryObject< Enchantment > DODGE = ENCHANTMENTS.create( "dodge", ()->DodgeEnchantment.create().toEnchantment( key( "dodge" ) ) );
	public static final RegistryObject< Enchantment > ENLIGHTENMENT = ENCHANTMENTS.create( "enlightenment", ()->EnlightenmentEnchantment.create().toEnchantment( key( "enlightenment" ) ) );
	public static final RegistryObject< Enchantment > FISHING_FANATIC = ENCHANTMENTS.create( "fishing_fanatic", ()->FishingFanaticEnchantment.create().toEnchantment( key( "fishing_fanatic" ) ) );
	public static final RegistryObject< Enchantment > FUSE_CUTTER = ENCHANTMENTS.create( "fuse_cutter", ()->FuseCutterEnchantment.create().toEnchantment( key( "fuse_cutter" ) ) );
	public static final RegistryObject< Enchantment > GOLD_FUELLED = ENCHANTMENTS.create( "gold_fuelled", ()->GoldFuelledEnchantment.create().toEnchantment( key( "gold_fuelled" ) ) );
	public static final RegistryObject< Enchantment > HARVESTER = ENCHANTMENTS.create( "harvester", ()->HarvesterEnchantment.create().toEnchantment( key( "harvester" ) ) );
	public static final RegistryObject< Enchantment > HORSE_FROST_WALKER = ENCHANTMENTS.create( "horse_frost_walker", ()->HorseFrostWalkerEnchantment.create().toEnchantment( key( "horse_frost_walker" ) ) );
	public static final RegistryObject< Enchantment > HORSE_PROTECTION = ENCHANTMENTS.create( "horse_protection", ()->HorseProtectionEnchantment.create().toEnchantment( key( "horse_protection" ) ) );
	public static final RegistryObject< Enchantment > HORSE_SWIFTNESS = ENCHANTMENTS.create( "horse_swiftness", ()->HorseSwiftnessEnchantment.create().toEnchantment( key( "horse_swiftness" ) ) );
	public static final RegistryObject< Enchantment > HUNTER = ENCHANTMENTS.create( "hunter", ()->HunterEnchantment.create().toEnchantment( key( "hunter" ) ) );
	public static final RegistryObject< Enchantment > IMMORTALITY = ENCHANTMENTS.create( "immortality", ()->ImmortalityEnchantment.create().toEnchantment( key( "immortality" ) ) );
	public static final RegistryObject< Enchantment > LEECH = ENCHANTMENTS.create( "leech", ()->LeechEnchantment.create().toEnchantment( key( "leech" ) ) );
	public static final RegistryObject< Enchantment > MAGIC_PROTECTION = ENCHANTMENTS.create( "magic_protection", ()->MagicProtectionEnchantment.create().toEnchantment( key( "magic_protection" ) ) );
	public static final RegistryObject< Enchantment > MISANTHROPY = ENCHANTMENTS.create( "misanthropy", ()->MisanthropyEnchantment.create().toEnchantment( key( "misanthropy" ) ) );
	public static final RegistryObject< Enchantment > REPULSION = ENCHANTMENTS.create( "repulsion", ()->RepulsionEnchantment.create().toEnchantment( key( "repulsion" ) ) );
	public static final RegistryObject< Enchantment > SIXTH_SENSE = ENCHANTMENTS.create( "sixth_sense", ()->SixthSenseEnchantment.create().toEnchantment( key( "sixth_sense" ) ) );
	public static final RegistryObject< Enchantment > SMELTER = ENCHANTMENTS.create( "smelter", ()->SmelterEnchantment.create().toEnchantment( key( "smelter" ) ) );
	public static final RegistryObject< Enchantment > TELEKINESIS = ENCHANTMENTS.create( "telekinesis", ()->TelekinesisEnchantment.create().toEnchantment( key( "telekinesis" ) ) );

	// Curses
	public static final RegistryObject< Enchantment > BREAKING = ENCHANTMENTS.create( "breaking_curse", ()->BreakingCurse.create().toEnchantment( key( "breaking_curse" ) ) );
	public static final RegistryObject< Enchantment > CORROSION = ENCHANTMENTS.create( "corrosion_curse", ()->CorrosionCurse.create().toEnchantment( key( "corrosion_curse" ) ) );
	public static final RegistryObject< Enchantment > FATIGUE = ENCHANTMENTS.create( "fatigue_curse", ()->FatigueCurse.create().toEnchantment( key( "fatigue_curse" ) ) );
	public static final RegistryObject< Enchantment > INCOMPATIBILITY = ENCHANTMENTS.create( "incompatibility_curse", ()->IncompatibilityCurse.create().toEnchantment( key( "incompatibility_curse" ) ) );
	public static final RegistryObject< Enchantment > SLIPPERY = ENCHANTMENTS.create( "slippery_curse", ()->SlipperyCurse.create().toEnchantment( key( "slippery_curse" ) ) );

	// Enchantment Categories
	public static final Predicate< ItemStack > IS_BOW_OR_CROSSBOW = itemStack->ItemHelper.isRangedWeapon( itemStack.getItem() );
	public static final Predicate< ItemStack > IS_GOLDEN = itemStack->ItemHelper.isGoldenToolOrArmor( itemStack.getItem() );
	public static final Predicate< ItemStack > IS_HORSE_ARMOR = itemStack->itemStack.getItem() instanceof HorseArmorItem;
	public static final Predicate< ItemStack > IS_HOE = itemStack->itemStack.getItem() instanceof HoeItem;
	public static final Predicate< ItemStack > IS_MELEE_MINECRAFT = itemStack->itemStack.getItem() instanceof SwordItem || itemStack.getItem() instanceof AxeItem; // for some reason all minecraft sword enchantments are applicable to axes
	public static final Predicate< ItemStack > IS_MELEE = itemStack->ItemHelper.isMeleeWeapon( itemStack.getItem() );
	public static final Predicate< ItemStack > IS_SHIELD = itemStack->ItemHelper.isShield( itemStack.getItem() );
	public static final Predicate< ItemStack > IS_TOOL = itemStack->ItemHelper.isAnyTool( itemStack.getItem() );

	// Particles
	public static final RegistryObject< SimpleParticleType > DODGE_PARTICLE = PARTICLES.create( "dodge", ()->new SimpleParticleType( true ) {} );
	public static final RegistryObject< SimpleParticleType > SMELTER_PARTICLE = PARTICLES.create( "smelter", ()->new SimpleParticleType( true ) {} );
	public static final RegistryObject< TelekinesisParticleType > TELEKINESIS_PARTICLE = PARTICLES.create( "telekinesis", TelekinesisParticleType::new );

	private MajruszsEnchantments() {}

	@OnlyIn( Dist.CLIENT )
	public static class Client {
		static {
			HELPER.create( Custom.Particles.class, particles->{
				particles.register( DODGE_PARTICLE.get(), DodgeParticle.Factory::new );
				particles.register( SMELTER_PARTICLE.get(), SmelterParticle.Factory::new );
				particles.register( TELEKINESIS_PARTICLE.get(), TelekinesisParticle.Factory::new );
			} );
		}
	}

	private static ResourceKey< Enchantment > key( String id ) {
		return ResourceKey.create( Registries.ENCHANTMENT, ResourceLocation.fromNamespaceAndPath( MOD_ID, id ) );
	}

}