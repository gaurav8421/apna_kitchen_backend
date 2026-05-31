from rest_framework import serializers
from .models import Ingredient, ItemStock, InventoryTransaction


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'branch', 'name', 'unit', 'quantity', 'low_stock_threshold', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItemStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemStock
        fields = ['id', 'branch', 'menu_item', 'quantity', 'low_stock_threshold', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class InventoryTransactionSerializer(serializers.ModelSerializer):
    item = serializers.PrimaryKeyRelatedField(
        source='ingredient', queryset=Ingredient.objects.all()
    )
    item_name = serializers.CharField(source='ingredient.name', read_only=True)
    item_unit = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'branch', 'item', 'item_name', 'item_unit',
            'transaction_type', 'quantity', 'notes', 'recorded_by', 'created_at',
        ]
        read_only_fields = ['id', 'item_name', 'item_unit', 'recorded_by', 'created_at']
