from rest_framework import generics, permissions
from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationMeView(generics.RetrieveUpdateAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.organization
