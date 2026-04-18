from rest_framework import generics, permissions
from .models import Branch
from .serializers import BranchSerializer
from apps.accounts.permissions import IsOwnerOrManager


class BranchListCreateView(generics.ListCreateAPIView):
    serializer_class = BranchSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), IsOwnerOrManager()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        return Branch.objects.filter(
            organization=self.request.user.organization,
            is_active=True
        ).order_by('name')

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        return Branch.objects.filter(organization=self.request.user.organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
