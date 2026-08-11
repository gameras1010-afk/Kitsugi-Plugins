package com.majruszlibrary.client;

import com.majruszlibrary.annotation.Dist;
import com.majruszlibrary.annotation.OnlyIn;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Camera;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.*;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;

@OnlyIn( Dist.CLIENT )
public abstract class CustomParticle extends TextureSheetParticle {
	public IFormula< Double > xdFormula = xd->xd * ( this.onGround ? 0.5 : 0.95 );
	public IFormula< Double > ydFormula = yd->yd - ( this.onGround ? 0.0 : 0.0375 );
	public IFormula< Double > zdFormula = zd->zd * ( this.onGround ? 0.5 : 0.95 );
	public IFormula< Float > alphaFormula = alpha->alpha;
	public IFormula< Float > scaleFormula = lifeRatio->1.0f - 0.5f * lifeRatio;

	public CustomParticle( ClientLevel level, double x, double y, double z, double xSpeed, double ySpeed, double zSpeed ) {
		super( level, x, y, z, xSpeed, ySpeed, zSpeed );
	}

	@Override
	public void tick() {
		this.xo = this.x;
		this.yo = this.y;
		this.zo = this.z;

		if( ++this.age >= this.lifetime ) {
			this.remove();
		} else {
			this.move( this.xd, this.yd, this.zd );
			this.xd = this.xdFormula.apply( this.xd );
			this.yd = this.ydFormula.apply( this.yd );
			this.zd = this.zdFormula.apply( this.zd );
			this.alpha = this.alphaFormula.apply( this.alpha );
		}
	}

	@Override
	public ParticleRenderType getRenderType() {
		return ParticleRenderType.PARTICLE_SHEET_OPAQUE;
	}

	@Override
	public float getQuadSize( float scaleFactor ) {
		return this.quadSize * this.scaleFormula.apply( ( ( float )this.age + scaleFactor ) / ( float )this.lifetime );
	}

	public float getY( float y ) {
		return y;
	}

	public Quaternionf getQuaternion( Quaternionf quaternion ) {
		return quaternion;
	}

	@OnlyIn( Dist.CLIENT )
	public static class Factory< ParticleType extends Particle, OptionsType extends ParticleOptions > implements ParticleProvider< OptionsType > {
		private final SpriteSet spriteSet;
		private final IFactory< ParticleType > factory;
		private final IModification< ParticleType, OptionsType > function;

		public Factory( SpriteSet sprite, IFactory< ParticleType > factory, IModification< ParticleType, OptionsType > function ) {
			this.spriteSet = sprite;
			this.factory = factory;
			this.function = function;
		}

		public Factory( SpriteSet sprite, IFactory< ParticleType > factory ) {
			this( sprite, factory, ( particle, options )->{} );
		}

		@Override
		public Particle createParticle( OptionsType type, ClientLevel level, double x, double y, double z, double xSpeed, double ySpeed, double zSpeed ) {
			ParticleType particle = this.factory.create( level, x, y, z, xSpeed, ySpeed, zSpeed, this.spriteSet );
			this.function.apply( particle, type );

			return particle;
		}
	}

	@OnlyIn( Dist.CLIENT )
	public static class SimpleFactory extends Factory< Particle, SimpleParticleType > {
		public SimpleFactory( SpriteSet sprite, IFactory< Particle > factory ) {
			super( sprite, factory );
		}
	}

	@FunctionalInterface
	@OnlyIn( Dist.CLIENT )
	public interface IFormula< Type > {
		Type apply( Type type );
	}

	@FunctionalInterface
	@OnlyIn( Dist.CLIENT )
	public interface IFactory< Type extends Particle > {
		Type create( ClientLevel world, double x, double y, double z, double xSpeed, double ySpeed, double zSpeed, SpriteSet spriteSet );
	}

	@FunctionalInterface
	@OnlyIn( Dist.CLIENT )
	public interface IModification< ParticleType extends Particle, OptionsType extends ParticleOptions > {
		void apply( ParticleType particle, OptionsType options );
	}
}
