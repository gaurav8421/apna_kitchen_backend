from django.urls import path
from .views import OrganizationMeView

urlpatterns = [
    path('me/', OrganizationMeView.as_view(), name='org-me'),
]
