from rest_framework import serializers
from .models import Branch


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'address', 'phone', 'gstin',
            'tax_rate', 'currency', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'is_active', 'created_at']
