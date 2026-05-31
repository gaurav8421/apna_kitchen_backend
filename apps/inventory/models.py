import uuid
from django.db import models


class Ingredient(models.Model):
    UNITS = [
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Millilitres'),
        ('l', 'Litres'),
        ('pcs', 'Pieces'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='ingredients'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ingredients'
    )
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=10, choices=UNITS)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingredients'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.quantity} {self.unit})'


class InventoryTransaction(models.Model):
    TYPES = [
        ('restock',    'Restock'),
        ('deduct',     'Deduct'),
        ('usage',      'Usage'),
        ('waste',      'Waste'),
        ('adjustment', 'Adjustment'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='inventory_transactions'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inventory_transactions'
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name='transactions'
    )
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='inventory_transactions'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.transaction_type} — {self.ingredient.name} x{self.quantity}'


class ItemStock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='item_stocks'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='item_stocks'
    )
    menu_item = models.OneToOneField(
        'menu.MenuItem', on_delete=models.CASCADE, related_name='stock'
    )
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'item_stocks'
        ordering = ['menu_item__name']

    def __str__(self):
        return f'{self.menu_item.name} — {self.quantity} units'
