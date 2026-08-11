package com.majruszlibrary.particles;

import com.majruszlibrary.registry.RegistryObject;
import net.minecraft.core.particles.ParticleOptions;
import net.minecraft.core.particles.ParticleType;

public class CustomParticleOptions< Type extends CustomParticleOptions< ? > > implements ParticleOptions {
    final RegistryObject< ? extends ParticleType< ? > > object;

    public CustomParticleOptions( RegistryObject< ? extends ParticleType< ? > > object ) {
        this.object = object;
    }

    @Override
    public ParticleType< ? > getType() {
        return this.object.get();
    }


}
