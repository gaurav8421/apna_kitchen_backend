import uuid
from django.db import models


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='branches'
    )
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gstin = models.CharField(max_length=15, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    currency = models.CharField(max_length=3, default='INR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'branches'
        verbose_name_plural = 'branches'

    def __str__(self):
        return f'{self.organization.name} — {self.name}'
