import uuid
from django.db import models, transaction
from django.db.models import Max


class Order(models.Model):
    ORDER_TYPES = [
        ('dine_in', 'Dine In'),
        ('takeaway', 'Takeaway'),
        ('delivery', 'Delivery'),
        ('online', 'Online'),
    ]
    STATUSES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='orders'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.CASCADE, related_name='orders'
    )
    order_number = models.CharField(max_length=20, blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default='dine_in')
    table_number = models.CharField(max_length=20, blank=True)
    customer_name = models.CharField(max_length=200, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='created_orders'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['branch', 'order_number'], name='unique_order_number_per_branch'),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            with transaction.atomic():
                # Lock all existing orders for this branch to prevent concurrent number assignment
                existing = (
                    Order.objects.select_for_update()
                    .filter(branch=self.branch)
                    .values_list('order_number', flat=True)
                )
                nums = [int(n.split('-')[1]) for n in existing if n]
                last_num = max(nums) if nums else 0
                self.order_number = f'ORD-{last_num + 1:04d}'
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.order_number


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(
        'menu.MenuItem', on_delete=models.SET_NULL, null=True, related_name='order_items'
    )
    item_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    modifiers = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f'{self.order.order_number} — {self.item_name} x{self.quantity}'
