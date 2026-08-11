package com.majruszlibrary.entity;

import com.majruszlibrary.MajruszLibrary;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.core.Holder;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;

import java.util.function.Supplier;

public class AttributeHandler {
	final ResourceLocation id;
	final String name;
	final Supplier< Holder< Attribute > > attribute;
	final AttributeModifier.Operation operation;
	double value = 0.0;

	public AttributeHandler( String uuid, String name, Supplier< Holder< Attribute > > attribute, AttributeModifier.Operation operation ) {
		this.id = ResourceLocation.fromNamespaceAndPath( MajruszLibrary.MOD_ID, uuid.replace( "-", "" ) );
		this.name = name;
		this.attribute = attribute;
		this.operation = operation;
	}

	public AttributeHandler( String name, Supplier< Holder< Attribute > > attribute, AttributeModifier.Operation operation ) {
		this.id = ResourceLocation.fromNamespaceAndPath( MajruszLibrary.MOD_ID, name.toLowerCase().replace( " ", "_" ) );
		this.name = name;
		this.attribute = attribute;
		this.operation = operation;
	}

	public boolean hasAttribute( LivingEntity entity ) {
		return entity.getAttributes().hasAttribute( this.attribute.get() );
	}

	public boolean hasValueChanged( AttributeInstance attributeInstance ) {
		AttributeModifier modifier = attributeInstance.getModifier( this.id );

		return modifier == null || modifier.amount() != this.value;
	}

	public double getValue() {
		return this.value;
	}

	public AttributeHandler setValue( double value ) {
		this.value = value;

		return this;
	}

	public AttributeHandler apply( LivingEntity entity ) {
		AttributeInstance attributeInstance = entity.getAttribute( this.attribute.get() );
		if( attributeInstance != null && this.hasValueChanged( attributeInstance ) ) {
			attributeInstance.removeModifier( this.id );
			attributeInstance.addTransientModifier( this.createAttribute() );
		}

		return this;
	}

	public AttributeHandler remove( LivingEntity entity ) {
		AttributeInstance attributeInstance = entity.getAttribute( this.attribute.get() );
		if( attributeInstance != null ) {
			attributeInstance.removeModifier( this.id );
		}

		return this;
	}

	public AttributeModifier createAttribute() {
		return new AttributeModifier( this.id, this.value, this.operation );
	}

	public ResourceLocation getId() {
		return this.id;
	}
}
