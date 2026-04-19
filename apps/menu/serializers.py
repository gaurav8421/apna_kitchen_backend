from rest_framework import serializers
from apps.branches.models import Branch
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request.user, 'organization', None):
            self.fields['category'].queryset = MenuCategory.objects.filter(
                organization=request.user.organization
            )

    class Meta:
        model = MenuItem
        fields = [
            'id', 'category', 'name', 'description', 'price',
            'image_url', 'item_type', 'is_available', 'track_inventory',
            'variants', 'modifiers', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class MenuCategorySerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and getattr(request.user, 'organization', None):
            self.fields['branch'].queryset = Branch.objects.filter(
                organization=request.user.organization
            )

    class Meta:
        model = MenuCategory
        fields = ['id', 'branch', 'name', 'sort_order', 'is_active']
        read_only_fields = ['id']
