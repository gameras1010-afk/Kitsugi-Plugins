package com.majruszlibrary.modhelper;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;

public class DataNeoForge implements IDataPlatform {
	public Object channel = null;
	public int messageIdx = 0;
	public DeferredRegister< ? > lastDeferredRegister = null;
	public static IEventBus MOD_EVENT_BUS = null;
}
