from datetime import datetime
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from django.db.models import Sum, Count
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.expenses.models import Expense


class DailySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if not date_str:
            raise ValidationError({'date': 'This parameter is required.'})
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError({'date': 'Use YYYY-MM-DD format.'})

        org = getattr(request.user, 'organization', None)
        if org is None:
            raise ValidationError({'detail': 'No organization associated with this account.'})

        orders = Order.objects.filter(organization=org, created_at__date=target_date)
        completed_orders = orders.filter(status='completed')

        total_sales = completed_orders.aggregate(t=Sum('total'))['t'] or Decimal('0')
        total_orders = orders.count()

        orders_by_status = {s: 0 for s, _ in Order.STATUSES}
        for row in orders.values('status').annotate(count=Count('id')):
            orders_by_status[row['status']] = row['count']

        payments = Payment.objects.filter(
            organization=org, created_at__date=target_date, status='completed'
        )
        payment_method_breakdown = {m: '0.00' for m, _ in Payment.METHODS}
        for row in payments.values('method').annotate(total=Sum('amount')):
            payment_method_breakdown[row['method']] = str(row['total'])

        top_items = (
            OrderItem.objects.filter(order__in=completed_orders)
            .values('item_name')
            .annotate(quantity_sold=Sum('quantity'), revenue=Sum('subtotal'))
            .order_by('-quantity_sold')[:10]
        )

        total_expenses = Expense.objects.filter(
            organization=org, date=target_date
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        return Response({
            'date': str(target_date),
            'total_sales': str(total_sales),
            'total_orders': total_orders,
            'orders_by_status': orders_by_status,
            'payment_method_breakdown': payment_method_breakdown,
            'top_items': [
                {
                    'item_name': row['item_name'],
                    'quantity_sold': row['quantity_sold'],
                    'revenue': str(row['revenue']),
                }
                for row in top_items
            ],
            'total_expenses': str(total_expenses),
        })
