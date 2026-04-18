from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
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
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Branch.objects.none()
        return Branch.objects.filter(organization=org, is_active=True).order_by('name')

    def perform_create(self, serializer):
        org = self.request.user.organization
        if org is None:
            raise PermissionDenied('User is not associated with an organization.')
        serializer.save(organization=org)


class BranchDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrManager]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Branch.objects.none()
        return Branch.objects.filter(organization=org, is_active=True)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()
