from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['item', 'item_name', 'variant_name', 'unit_price', 'quantity', 'modifiers', 'notes', 'subtotal']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'item', 'item_name', 'variant_name', 'unit_price', 'quantity', 'modifiers', 'notes', 'subtotal']
        read_only_fields = ['id']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'branch', 'order_type', 'table_number', 'customer_name', 'customer_phone',
            'subtotal', 'discount', 'tax', 'total', 'items',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

    def to_representation(self, instance):
        return OrderDetailSerializer(instance, context=self.context).data


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'branch', 'order_type', 'table_number',
            'customer_name', 'customer_phone', 'status',
            'subtotal', 'discount', 'tax', 'total',
            'items', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
