from rest_framework import serializers
from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug', 'logo_url', 'phone', 'email', 'gstin', 'address', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']
