import uuid
from django.db import models


class Payment(models.Model):
    METHODS = [('cash', 'Cash'), ('upi', 'UPI'), ('card', 'Card'), ('online', 'Online')]
    STATUSES = [('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='payments'
    )
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHODS)
    reference_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default='completed')
    razorpay_payment_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.method} ₹{self.amount}'
