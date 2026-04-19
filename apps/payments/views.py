from rest_framework import viewsets, permissions
from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Payment.objects.none()
        return Payment.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = self.request.user.organization
        order = serializer.validated_data.get('order')
        if order and order.organization != org:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Order does not belong to your organization.')
        serializer.save(organization=org)
