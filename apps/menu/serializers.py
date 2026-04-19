from rest_framework import serializers
from .models import MenuCategory, MenuItem, ItemVariant, ItemModifier


class ItemVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemVariant
        fields = ['id', 'name', 'price_delta']
        read_only_fields = ['id']


class ItemModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemModifier
        fields = ['id', 'name', 'price']
        read_only_fields = ['id']


class MenuItemSerializer(serializers.ModelSerializer):
    variants = ItemVariantSerializer(many=True, read_only=True)
    modifiers = ItemModifierSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'category', 'name', 'description', 'price',
            'image_url', 'item_type', 'is_available', 'track_inventory',
            'variants', 'modifiers', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MenuCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuCategory
        fields = ['id', 'branch', 'name', 'sort_order', 'is_active']
        read_only_fields = ['id']
