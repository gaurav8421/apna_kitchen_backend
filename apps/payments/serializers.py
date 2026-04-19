from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'amount', 'method', 'reference_id', 'status', 'razorpay_payment_id', 'created_at']
        read_only_fields = ['id', 'status', 'created_at']
