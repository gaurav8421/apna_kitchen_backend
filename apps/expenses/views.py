from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import ExpenseCategory, Expense
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ExpenseCategory.objects.none()
        return ExpenseCategory.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch', 'date']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Expense.objects.none()
        return Expense.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            recorded_by=self.request.user,
        )
