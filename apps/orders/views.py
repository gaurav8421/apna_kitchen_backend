from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.branches.models import Branch
from .filters import OrderFilter
from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderStatusSerializer


class OrderViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filterset_class = OrderFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Order.objects.none()
        return Order.objects.filter(organization=org).prefetch_related('items')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer

    def perform_create(self, serializer):
        org = self.request.user.organization
        branch = serializer.validated_data.get('branch')
        get_object_or_404(Branch, pk=branch.pk, organization=org)
        serializer.save(organization=org, created_by=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('PATCH')

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        order.refresh_from_db()
        return Response(OrderDetailSerializer(order, context={'request': request}).data)
