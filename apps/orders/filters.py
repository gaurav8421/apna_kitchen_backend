import django_filters
from .models import Order


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class OrderFilter(django_filters.FilterSet):
    status = CharInFilter(field_name='status', lookup_expr='in')
    branch = django_filters.UUIDFilter(field_name='branch')
    order_type = django_filters.CharFilter(field_name='order_type')

    class Meta:
        model = Order
        fields = ['branch', 'status', 'order_type']
