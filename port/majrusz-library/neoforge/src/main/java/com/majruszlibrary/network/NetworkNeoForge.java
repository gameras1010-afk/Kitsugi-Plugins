package com.majruszlibrary.network;

import com.majruszlibrary.data.Serializables;
import com.majruszlibrary.modhelper.ModHelper;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class NetworkNeoForge implements INetworkPlatform {
	private static final Map< ResourceLocation, NetworkObject< ? > > CHANNELS = new ConcurrentHashMap<>();

	@Override
	public void register( ModHelper helper, List< NetworkObject< ? > > objects ) {
		helper.log( "NetworkNeoForge.register: %s objects", objects.size() );
		for( NetworkObject< ? > object : objects ) {
			CHANNELS.put( object.id, object );
			helper.log( "NetworkNeoForge: registered channel %s", object.id );
		}
	}

	@Override
	public < Type > void sendToServer( NetworkObject< Type > object, Type message ) {
		byte[] data = toBytes( message );
		org.slf4j.LoggerFactory.getLogger("majruszlibrary").info("NetworkNeoForge.sendToServer: channel={}, bytes={}", object.id, data.length);
		PacketDistributor.sendToServer( new WrapperPayload( object.id, data ) );
	}

	@Override
	public < Type > void sendToClients( NetworkObject< Type > object, Type message, List< ServerPlayer > players ) {
		byte[] data = toBytes( message );
		org.slf4j.LoggerFactory.getLogger("majruszlibrary").info("NetworkNeoForge.sendToClients: channel={}, players={}, bytes={}", object.id, players.size(), data.length);
		for( ServerPlayer player : players ) {
			PacketDistributor.sendToPlayer( player, new WrapperPayload( object.id, data ) );
		}
	}

	@SuppressWarnings( "unchecked" )
	private < Type > byte[] toBytes( Type message ) {
		PacketBuf buf = new PacketBuf();
		Serializables.write( message, buf );
		byte[] data = new byte[ buf.readableBytes() ];
		buf.readBytes( data );
		return data;
	}

	@SubscribeEvent
	@SuppressWarnings( { "rawtypes", "unchecked" } )
	public static void onRegisterPayloads( RegisterPayloadHandlersEvent event ) {
		PayloadRegistrar registrar = event.registrar( "1" );
		registrar.playToClient( WrapperPayload.TYPE, WrapperPayload.STREAM_CODEC, ( payload, ctx ) -> {
			org.slf4j.LoggerFactory.getLogger("majruszlibrary").info("NetworkNeoForge.clientReceived: channel={}, bytes={}", payload.channel(), payload.data().length);
			NetworkObject obj = CHANNELS.get( payload.channel() );
			if( obj != null ) {
				Object message = Serializables.read( obj.instance.get(), new PacketBuf( payload.data() ) );
				obj.broadcastOnClient( message );
			} else {
				org.slf4j.LoggerFactory.getLogger("majruszlibrary").warn("NetworkNeoForge.clientReceived: unknown channel {}", payload.channel());
			}
		} );
		// Server-bound: TODO implement for NeoForge 1.21.1 API
	}
}

record WrapperPayload( ResourceLocation channel, byte[] data ) implements CustomPacketPayload {
	static final CustomPacketPayload.Type< WrapperPayload > TYPE = new Type<>( ResourceLocation.fromNamespaceAndPath( "majruszlibrary", "wrapper" ) );
	static final StreamCodec< FriendlyByteBuf, WrapperPayload > STREAM_CODEC = new StreamCodec<>() {
		@Override public WrapperPayload decode( FriendlyByteBuf buf ) {
			return new WrapperPayload( buf.readResourceLocation(), buf.readByteArray() );
		}
		@Override public void encode( FriendlyByteBuf buf, WrapperPayload payload ) {
			buf.writeResourceLocation( payload.channel );
			buf.writeByteArray( payload.data );
		}
	};
	@Override public Type< WrapperPayload > type() { return TYPE; }
}

class PacketBuf extends FriendlyByteBuf {
	PacketBuf() { super( io.netty.buffer.Unpooled.buffer() ); }
	PacketBuf( byte[] data ) { super( io.netty.buffer.Unpooled.wrappedBuffer( data ) ); }
}
