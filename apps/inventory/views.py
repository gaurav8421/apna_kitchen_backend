from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Ingredient, ItemStock, InventoryTransaction
from .serializers import IngredientSerializer, ItemStockSerializer, InventoryTransactionSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Ingredient.objects.none()
        return Ingredient.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ItemStockViewSet(viewsets.ModelViewSet):
    serializer_class = ItemStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ItemStock.objects.none()
        return ItemStock.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch', 'ingredient', 'transaction_type']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return InventoryTransaction.objects.none()
        return InventoryTransaction.objects.filter(organization=org).select_related('ingredient')

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            recorded_by=self.request.user,
        )
