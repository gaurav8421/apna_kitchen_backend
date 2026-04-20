from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from .models import Payment
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def destroy(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('DELETE')

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Payment.objects.none()
        return Payment.objects.filter(organization=org)

    def perform_create(self, serializer):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            raise PermissionDenied('No organization associated with this account.')
        order = serializer.validated_data.get('order')
        if order and order.organization != org:
            raise PermissionDenied('Order does not belong to your organization.')
        serializer.save(organization=org, status='completed')
