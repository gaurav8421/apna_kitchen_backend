import uuid
from django.db import models


class MenuCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='menu_categories'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='menu_categories'
    )
    name = models.CharField(max_length=200)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_categories'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    ITEM_TYPES = [('veg', 'Veg'), ('non_veg', 'Non-Veg'), ('egg', 'Egg')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='menu_items'
    )
    category = models.ForeignKey(
        MenuCategory, on_delete=models.CASCADE, related_name='items'
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(blank=True)
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES, default='veg')
    is_available = models.BooleanField(default=True)
    track_inventory = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_items'
        ordering = ['name']

    def __str__(self):
        return self.name


class ItemVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'item_variants'
        ordering = ['name']

    def __str__(self):
        return f'{self.item.name} — {self.name}'


class ItemModifier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='modifiers')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'item_modifiers'
        ordering = ['name']

    def __str__(self):
        return f'{self.item.name} + {self.name}'
