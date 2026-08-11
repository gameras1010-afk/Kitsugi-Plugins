package com.majruszlibrary.particles;

import com.majruszlibrary.data.Serializables;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;

import java.util.function.Supplier;

public class CustomParticleType< Type extends ParticleOptions > extends ParticleType< Type > {
    private final MapCodec< Type > codec;
    private final StreamCodec< ? super RegistryFriendlyByteBuf, Type > streamCodec;

    public CustomParticleType( Supplier< Type > instance ) {
        super( true );

        this.codec = MapCodec.unit( instance.get() );
        this.streamCodec = new StreamCodec<>() {
            @Override
            public Type decode( RegistryFriendlyByteBuf buffer ) {
                return Serializables.read( instance.get(), buffer );
            }

            @Override
            public void encode( RegistryFriendlyByteBuf buffer, Type value ) {
                Serializables.write( value, ( FriendlyByteBuf )buffer );
            }
        };
    }

    @Override
    public MapCodec< Type > codec() {
        return this.codec;
    }

    @Override
    public StreamCodec< ? super RegistryFriendlyByteBuf, Type > streamCodec() {
        return this.streamCodec;
    }
}
