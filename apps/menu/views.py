from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from apps.accounts.permissions import IsOwnerOrManager
from .models import MenuCategory, MenuItem, ItemVariant, ItemModifier
from .serializers import (
    MenuCategorySerializer, MenuItemSerializer,
    ItemVariantSerializer, ItemModifierSerializer,
)


class MenuCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = MenuCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch', 'is_active']

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrManager()]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return MenuCategory.objects.none()
        return MenuCategory.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'item_type', 'is_available']

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrManager()]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return MenuItem.objects.none()
        return MenuItem.objects.filter(organization=org).select_related('category').prefetch_related('variants', 'modifiers')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ItemVariantViewSet(viewsets.ModelViewSet):
    serializer_class = ItemVariantSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrManager()]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ItemVariant.objects.none()
        item_pk = self.kwargs.get('item_pk')
        if item_pk is None:
            return ItemVariant.objects.none()
        return ItemVariant.objects.filter(item__organization=org, item_id=item_pk)

    def perform_create(self, serializer):
        org = getattr(self.request.user, 'organization', None)
        item = get_object_or_404(MenuItem, pk=self.kwargs['item_pk'], organization=org)
        serializer.save(item=item)


class ItemModifierViewSet(viewsets.ModelViewSet):
    serializer_class = ItemModifierSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrManager()]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ItemModifier.objects.none()
        item_pk = self.kwargs.get('item_pk')
        if item_pk is None:
            return ItemModifier.objects.none()
        return ItemModifier.objects.filter(item__organization=org, item_id=item_pk)

    def perform_create(self, serializer):
        org = getattr(self.request.user, 'organization', None)
        item = get_object_or_404(MenuItem, pk=self.kwargs['item_pk'], organization=org)
        serializer.save(item=item)
