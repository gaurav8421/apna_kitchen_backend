from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound
from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationMeView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        org = self.request.user.organization
        if org is None:
            raise NotFound('User does not belong to an organization.')
        return org
