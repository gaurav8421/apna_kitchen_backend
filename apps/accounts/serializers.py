from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils.text import slugify
from .models import User
from apps.organizations.models import Organization


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['org_id'] = str(user.organization_id) if user.organization_id else ''
        token['name'] = user.name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': str(self.user.id),
            'name': self.user.name,
            'email': self.user.email,
            'role': self.user.role,
            'org_id': str(self.user.organization_id) if self.user.organization_id else '',
            'org_name': self.user.organization.name if self.user.organization else None,
            'branch_id': str(self.user.branch_id) if self.user.branch_id else None,
        }
        return data


class RegisterSerializer(serializers.Serializer):
    org_name = serializers.CharField(max_length=200)
    org_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    org_email = serializers.EmailField(required=False, allow_blank=True, default='')
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_org_name(self, value):
        from django.utils.text import slugify as django_slugify
        if not django_slugify(value):
            raise serializers.ValidationError(
                'Organization name must contain at least one letter or number.'
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        slug = slugify(validated_data['org_name'])
        base_slug, counter = slug, 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        org = Organization.objects.create(
            name=validated_data['org_name'],
            slug=slug,
            phone=validated_data['org_phone'],
            email=validated_data['org_email'],
        )
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data['name'],
            organization=org,
            role='owner',
        )
        return user, org
