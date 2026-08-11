package com.majruszsenchantments;

import net.neoforged.fml.common.Mod;

@Mod( MajruszsEnchantments.MOD_ID )
public class Initializer {
	public Initializer() {
		MajruszsEnchantments.HELPER.register();
	}
}
