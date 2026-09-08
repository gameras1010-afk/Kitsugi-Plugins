package com.example.wdablite;

import com.cinemamod.mcef.MCEF;
import com.cinemamod.mcef.MCEFClient;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * WebDisplays AdBlock Lite — client-only companion mod.
 *
 * MCEF'i (ve dolayısıyla WebDisplays'i) FORKLAMAZ. Sadece CEF'in herkese acik
 * handler API'lerini kullanir:
 *  - CefClient.addRequestHandler(...)  -> alt-istek iptali / stub redirect (kaynak: java-cef)
 *  - MCEFClient.addLoadHandler(...)    -> sayfa yuklendiginde cosmetic CSS + YT skipper JS
 * MCEF/WD bu slotlarin hicbirini kullanmiyor (kaynak kodunda dogrulandi, Eyl 2026)
 * => motoru bozmadan, tek jar ile eklenen bir "filtre katmani".
 */
@Mod(WdAdblockLiteMod.MODID)
public class WdAdblockLiteMod {

    public static final String MODID = "wd_adblock_lite";
    public static final Logger LOG = LoggerFactory.getLogger("WdAdBlockLite");

    /** Chromium indirilip MCEF gec olusabilecegi icin: kisa gecikmeyle tekrar dene. */
    private static final int RETRY_TICKS = 60; // ~3sn
    private boolean attached = false;
    private int tickCounter = 0;

    public WdAdblockLiteMod(IEventBus modBus, ModContainer container) {
        NeoForge.EVENT_BUS.register(this);
        LOG.info("[WdAdBlockLite] initialized; waiting for MCEF client...");
    }

    private void onClientTick(ClientTickEvent.Post event) {
        if (attached) return;
        if (++tickCounter % RETRY_TICKS != 0) return;
        try {
            MCEFClient client = MCEF.getClient();
            if (client == null || client.getHandle() == null) return; // Chromium henuz iniyor

            client.getHandle().addRequestHandler(new AdBlockRequestHandler());
            client.addLoadHandler(CosmeticInjector.INSTANCE);

            attached = true;
            LOG.info("[WdAdBlockLite] attached to MCEF — {} aktif kural", Rules.get().size());
        } catch (Throwable t) {
            // MCEF init hatasi / API farki: asla MC'yi crash etme, sessizce bekle
            LOG.warn("[WdAdBlockLite] attach bekleniyor/hata: {}", t.toString());
        }
    }
}
