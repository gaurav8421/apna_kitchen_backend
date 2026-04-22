# Inventory, Expenses, Reports & Orders Filter Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the orders multi-status filter 400 error and add three new apps — inventory, expenses, and reports daily summary.

**Architecture:** Each new subsystem is a standalone Django app under `apps/`. All viewsets follow the existing pattern: UUID PKs, org-scoped queryset in `get_queryset`, `IsAuthenticated` permission, `perform_create` injects `organization`. Reports is a single `APIView` with on-the-fly ORM aggregation — no new models.

**Tech Stack:** Django 5, DRF, django-filter (`BaseInFilter` mixin), pytest-django

---

## File Map

**Create:**
- `apps/orders/filters.py` — OrderFilter with comma-separated status support
- `apps/inventory/__init__.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`
- `apps/expenses/__init__.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`
- `apps/reports/__init__.py`, `apps.py`, `views.py`, `urls.py`
- `tests/test_inventory.py`
- `tests/test_expenses.py`
- `tests/test_reports.py`

**Modify:**
- `apps/orders/views.py` — swap `filterset_fields` for `filterset_class`
- `tests/test_orders.py` — add multi-status filter test
- `config/settings/base.py` — add 3 new apps to `INSTALLED_APPS`
- `config/urls.py` — wire up 3 new URL prefixes

---

## Task 1: Fix orders multi-status filter

**Files:**
- Create: `apps/orders/filters.py`
- Modify: `apps/orders/views.py`
- Modify: `tests/test_orders.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_orders.py`:

```python
@pytest.mark.django_db
def test_filter_orders_by_multiple_statuses(auth_client, org, branch, owner):
    Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
        status='pending',
    )
    Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
        status='completed',
    )
    Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
        status='cancelled',
    )
    url = reverse('order-list') + '?status=pending,completed'
    resp = auth_client.get(url)
    assert resp.status_code == 200
    statuses = {o['status'] for o in resp.json()}
    assert statuses == {'pending', 'completed'}
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
pytest tests/test_orders.py::test_filter_orders_by_multiple_statuses -v
```

Expected: FAIL with status 400 or wrong result set.

- [ ] **Step 3: Create `apps/orders/filters.py`**

```python
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
```

- [ ] **Step 4: Update `apps/orders/views.py`**

Replace:
```python
filter_backends = [DjangoFilterBackend]
filterset_fields = ['branch', 'status', 'order_type']
```

With:
```python
filterset_class = OrderFilter
```

And add import at top of file:
```python
from .filters import OrderFilter
```

Remove the now-unused `from django_filters.rest_framework import DjangoFilterBackend` import if it's no longer needed (it's set globally in settings).

Full updated `apps/orders/views.py`:

```python
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from apps.branches.models import Branch
from .filters import OrderFilter
from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderStatusSerializer


class OrderViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    filterset_class = OrderFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Order.objects.none()
        return Order.objects.filter(organization=org).prefetch_related('items')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer

    def perform_create(self, serializer):
        org = self.request.user.organization
        branch = serializer.validated_data.get('branch')
        get_object_or_404(Branch, pk=branch.pk, organization=org)
        serializer.save(organization=org, created_by=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed('PATCH')

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        order.refresh_from_db()
        return Response(OrderDetailSerializer(order, context={'request': request}).data)
```

- [ ] **Step 5: Run the test to confirm it passes**

```bash
pytest tests/test_orders.py -v
```

Expected: all PASS including the new multi-status test.

- [ ] **Step 6: Commit**

```bash
git add apps/orders/filters.py apps/orders/views.py tests/test_orders.py
git commit -m "fix: support comma-separated status filter on orders list"
```

---

## Task 2: Inventory app — scaffold and models

**Files:**
- Create: `apps/inventory/__init__.py`
- Create: `apps/inventory/apps.py`
- Create: `apps/inventory/models.py`
- Modify: `config/settings/base.py`

- [ ] **Step 1: Write the failing model test**

Create `tests/test_inventory.py`:

```python
import pytest
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.accounts.models import User
from apps.menu.models import MenuCategory, MenuItem


@pytest.fixture
def org():
    return Organization.objects.create(name='Spice Route', slug='spice-route-inv')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='MG Road', organization=org)


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@inv.com', password='pass1234',
        name='Owner', organization=org, role='owner',
    )


@pytest.fixture
def category(org):
    return MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)


@pytest.fixture
def menu_item(org, category):
    return MenuItem.objects.create(
        organization=org, category=category,
        name='Butter Chicken', price='320.00', item_type='non_veg',
    )


@pytest.mark.django_db
def test_ingredient_str(org):
    from apps.inventory.models import Ingredient
    ing = Ingredient.objects.create(
        organization=org, name='Tomatoes', unit='kg', quantity='5.000', low_stock_threshold='1.000'
    )
    assert str(ing) == 'Tomatoes (5.000 kg)'


@pytest.mark.django_db
def test_item_stock_str(org, menu_item):
    from apps.inventory.models import ItemStock
    stock = ItemStock.objects.create(
        organization=org, menu_item=menu_item, quantity=10, low_stock_threshold=2
    )
    assert str(stock) == 'Butter Chicken — 10 units'
```

- [ ] **Step 2: Run to confirm it fails**

```bash
pytest tests/test_inventory.py::test_ingredient_str -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Create app scaffold**

```bash
touch apps/inventory/__init__.py
```

Create `apps/inventory/apps.py`:

```python
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory'
```

- [ ] **Step 4: Create `apps/inventory/models.py`**

```python
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
```

- [ ] **Step 5: Register in `INSTALLED_APPS`**

In `config/settings/base.py`, add after `'apps.payments'`:

```python
    'apps.inventory',
```

- [ ] **Step 6: Create and run migration**

```bash
python manage.py makemigrations inventory
python manage.py migrate
```

Expected output includes: `Creating tables... apps_inventory_ingredient, apps_inventory_itemstock`

- [ ] **Step 7: Run model tests**

```bash
pytest tests/test_inventory.py::test_ingredient_str tests/test_inventory.py::test_item_stock_str -v
```

Expected: both PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/inventory/ config/settings/base.py tests/test_inventory.py
git commit -m "feat: inventory app models (Ingredient, ItemStock)"
```

---

## Task 3: Inventory app — API endpoints

**Files:**
- Create: `apps/inventory/serializers.py`
- Create: `apps/inventory/views.py`
- Create: `apps/inventory/urls.py`
- Modify: `config/urls.py`
- Modify: `tests/test_inventory.py`

- [ ] **Step 1: Write failing API tests**

Append to `tests/test_inventory.py`:

```python
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_create_ingredient(auth_client, org):
    resp = auth_client.post(
        '/api/v1/inventory/ingredients/',
        {'name': 'Tomatoes', 'unit': 'kg', 'quantity': '5.000', 'low_stock_threshold': '1.000'},
        content_type='application/json',
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data['name'] == 'Tomatoes'
    assert data['unit'] == 'kg'


@pytest.mark.django_db
def test_ingredient_scoped_to_org(auth_client, org):
    from apps.inventory.models import Ingredient
    other_org = Organization.objects.create(name='Other', slug='other-inv-scope')
    Ingredient.objects.create(
        organization=other_org, name='Flour', unit='kg', quantity=10, low_stock_threshold=1
    )
    resp = auth_client.get('/api/v1/inventory/ingredients/')
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_create_item_stock(auth_client, org, menu_item):
    resp = auth_client.post(
        '/api/v1/inventory/item-stock/',
        {'menu_item': str(menu_item.id), 'quantity': 20, 'low_stock_threshold': 5},
        content_type='application/json',
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data['quantity'] == 20


@pytest.mark.django_db
def test_item_stock_scoped_to_org(auth_client, org, menu_item):
    from apps.inventory.models import ItemStock
    other_org = Organization.objects.create(name='Other2', slug='other-inv-scope2')
    other_cat = MenuCategory.objects.create(organization=other_org, name='Cat', sort_order=1)
    other_item = MenuItem.objects.create(
        organization=other_org, category=other_cat,
        name='Other Dish', price='100.00', item_type='veg',
    )
    ItemStock.objects.create(
        organization=other_org, menu_item=other_item, quantity=5, low_stock_threshold=1
    )
    resp = auth_client.get('/api/v1/inventory/item-stock/')
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_inventory.py::test_create_ingredient -v
```

Expected: FAIL with 404 (URL not wired yet).

- [ ] **Step 3: Create `apps/inventory/serializers.py`**

```python
from rest_framework import serializers
from .models import Ingredient, ItemStock


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'branch', 'name', 'unit', 'quantity', 'low_stock_threshold', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ItemStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemStock
        fields = ['id', 'branch', 'menu_item', 'quantity', 'low_stock_threshold', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
```

- [ ] **Step 4: Create `apps/inventory/views.py`**

```python
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Ingredient, ItemStock
from .serializers import IngredientSerializer, ItemStockSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Ingredient.objects.none()
        return Ingredient.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ItemStockViewSet(viewsets.ModelViewSet):
    serializer_class = ItemStockSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ItemStock.objects.none()
        return ItemStock.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
```

- [ ] **Step 5: Create `apps/inventory/urls.py`**

```python
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, ItemStockViewSet

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('item-stock', ItemStockViewSet, basename='itemstock')

urlpatterns = router.urls
```

- [ ] **Step 6: Wire up in `config/urls.py`**

Add after `path('api/v1/payments/', ...)`:

```python
path('api/v1/inventory/', include('apps.inventory.urls')),
```

- [ ] **Step 7: Run API tests**

```bash
pytest tests/test_inventory.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/inventory/ config/urls.py tests/test_inventory.py
git commit -m "feat: inventory API (ingredients and item-stock endpoints)"
```

---

## Task 4: Expenses app — scaffold, models, and API

**Files:**
- Create: `apps/expenses/__init__.py`
- Create: `apps/expenses/apps.py`
- Create: `apps/expenses/models.py`
- Create: `apps/expenses/serializers.py`
- Create: `apps/expenses/views.py`
- Create: `apps/expenses/urls.py`
- Modify: `config/settings/base.py`
- Modify: `config/urls.py`
- Create: `tests/test_expenses.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_expenses.py`:

```python
import pytest
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.accounts.models import User
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def org():
    return Organization.objects.create(name='Spice Route', slug='spice-route-exp')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='MG Road', organization=org)


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@exp.com', password='pass1234',
        name='Owner', organization=org, role='owner',
    )


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_create_expense_category(auth_client):
    resp = auth_client.post(
        '/api/v1/expenses/categories/',
        {'name': 'Rent'},
        content_type='application/json',
    )
    assert resp.status_code == 201
    assert resp.json()['name'] == 'Rent'


@pytest.mark.django_db
def test_expense_category_scoped_to_org(auth_client, org):
    from apps.expenses.models import ExpenseCategory
    other_org = Organization.objects.create(name='Other', slug='other-exp-scope')
    ExpenseCategory.objects.create(organization=other_org, name='Other Cat')
    resp = auth_client.get('/api/v1/expenses/categories/')
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_create_expense(auth_client, org):
    from apps.expenses.models import ExpenseCategory
    cat = ExpenseCategory.objects.create(organization=org, name='Supplies')
    resp = auth_client.post(
        '/api/v1/expenses/',
        {'category': str(cat.id), 'amount': '500.00', 'date': '2026-04-22', 'description': 'Paper cups'},
        content_type='application/json',
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data['amount'] == '500.00'
    assert data['description'] == 'Paper cups'


@pytest.mark.django_db
def test_expense_recorded_by_set_automatically(auth_client, org, owner):
    from apps.expenses.models import ExpenseCategory
    cat = ExpenseCategory.objects.create(organization=org, name='Utilities')
    resp = auth_client.post(
        '/api/v1/expenses/',
        {'category': str(cat.id), 'amount': '1000.00', 'date': '2026-04-22'},
        content_type='application/json',
    )
    assert resp.status_code == 201
    assert resp.json()['recorded_by'] == str(owner.id)


@pytest.mark.django_db
def test_expense_filter_by_date(auth_client, org):
    from apps.expenses.models import ExpenseCategory, Expense
    cat = ExpenseCategory.objects.create(organization=org, name='Food')
    Expense.objects.create(organization=org, category=cat, amount='100.00', date='2026-04-21')
    Expense.objects.create(organization=org, category=cat, amount='200.00', date='2026-04-22')
    resp = auth_client.get('/api/v1/expenses/?date=2026-04-22')
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]['amount'] == '200.00'
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_expenses.py::test_create_expense_category -v
```

Expected: FAIL with 404.

- [ ] **Step 3: Create app scaffold**

```bash
touch apps/expenses/__init__.py
```

Create `apps/expenses/apps.py`:

```python
from django.apps import AppConfig


class ExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.expenses'
```

- [ ] **Step 4: Create `apps/expenses/models.py`**

```python
import uuid
from django.db import models


class ExpenseCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='expense_categories'
    )
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'expense_categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE, related_name='expenses'
    )
    branch = models.ForeignKey(
        'branches.Branch', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='expenses'
    )
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, related_name='expenses'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    recorded_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='recorded_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'expenses'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.category.name} — ₹{self.amount} on {self.date}'
```

- [ ] **Step 5: Create `apps/expenses/serializers.py`**

```python
from rest_framework import serializers
from .models import ExpenseCategory, Expense


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'branch', 'category', 'amount', 'description', 'date', 'recorded_by', 'created_at']
        read_only_fields = ['id', 'recorded_by', 'created_at']
```

- [ ] **Step 6: Create `apps/expenses/views.py`**

```python
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import ExpenseCategory, Expense
from .serializers import ExpenseCategorySerializer, ExpenseSerializer


class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return ExpenseCategory.objects.none()
        return ExpenseCategory.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['branch', 'date']

    def get_queryset(self):
        org = getattr(self.request.user, 'organization', None)
        if org is None:
            return Expense.objects.none()
        return Expense.objects.filter(organization=org)

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            recorded_by=self.request.user,
        )
```

- [ ] **Step 7: Create `apps/expenses/urls.py`**

```python
from rest_framework.routers import DefaultRouter
from .views import ExpenseCategoryViewSet, ExpenseViewSet

router = DefaultRouter()
router.register('categories', ExpenseCategoryViewSet, basename='expensecategory')
router.register('', ExpenseViewSet, basename='expense')

urlpatterns = router.urls
```

- [ ] **Step 8: Register app and wire URL**

In `config/settings/base.py`, add after `'apps.inventory'`:

```python
    'apps.expenses',
```

In `config/urls.py`, add:

```python
path('api/v1/expenses/', include('apps.expenses.urls')),
```

- [ ] **Step 9: Create and run migration**

```bash
python manage.py makemigrations expenses
python manage.py migrate
```

- [ ] **Step 10: Run tests**

```bash
pytest tests/test_expenses.py -v
```

Expected: all PASS.

- [ ] **Step 11: Commit**

```bash
git add apps/expenses/ config/settings/base.py config/urls.py tests/test_expenses.py
git commit -m "feat: expenses app (categories and expense record endpoints)"
```

---

## Task 5: Reports app — daily summary

**Files:**
- Create: `apps/reports/__init__.py`
- Create: `apps/reports/apps.py`
- Create: `apps/reports/views.py`
- Create: `apps/reports/urls.py`
- Modify: `config/settings/base.py`
- Modify: `config/urls.py`
- Create: `tests/test_reports.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_reports.py`:

```python
import pytest
from datetime import date
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.accounts.models import User
from apps.menu.models import MenuCategory, MenuItem
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def org():
    return Organization.objects.create(name='Spice Route', slug='spice-route-rep')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='MG Road', organization=org)


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@rep.com', password='pass1234',
        name='Owner', organization=org, role='owner',
    )


@pytest.fixture
def category(org):
    return MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)


@pytest.fixture
def menu_item(org, category):
    return MenuItem.objects.create(
        organization=org, category=category,
        name='Butter Chicken', price='320.00', item_type='non_veg',
    )


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_daily_summary_requires_date(auth_client):
    resp = auth_client.get('/api/v1/reports/daily-summary/')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_daily_summary_invalid_date(auth_client):
    resp = auth_client.get('/api/v1/reports/daily-summary/?date=not-a-date')
    assert resp.status_code == 400


@pytest.mark.django_db
def test_daily_summary_empty(auth_client):
    resp = auth_client.get('/api/v1/reports/daily-summary/?date=2000-01-01')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_sales'] == '0'
    assert data['total_orders'] == 0
    assert data['total_expenses'] == '0'


@pytest.mark.django_db
def test_daily_summary_counts_orders_and_payments(auth_client, org, branch, owner, menu_item):
    from apps.orders.models import Order, OrderItem
    from apps.payments.models import Payment

    today = str(date.today())

    order = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='320.00', tax='16.00', total='336.00',
        status='completed',
    )
    OrderItem.objects.create(
        order=order, item=menu_item, item_name='Butter Chicken',
        unit_price='320.00', quantity=2, subtotal='640.00',
    )
    Payment.objects.create(
        organization=org, order=order, amount='336.00', method='cash', status='completed',
    )

    resp = auth_client.get(f'/api/v1/reports/daily-summary/?date={today}')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total_orders'] == 1
    assert data['orders_by_status']['completed'] == 1
    assert data['orders_by_status']['pending'] == 0
    assert data['payment_method_breakdown']['cash'] == '336.00'
    assert data['payment_method_breakdown']['upi'] == '0.00'
    assert len(data['top_items']) == 1
    assert data['top_items'][0]['item_name'] == 'Butter Chicken'
    assert data['top_items'][0]['quantity_sold'] == 2


@pytest.mark.django_db
def test_daily_summary_includes_expenses(auth_client, org):
    from apps.expenses.models import ExpenseCategory, Expense

    today = str(date.today())
    cat = ExpenseCategory.objects.create(organization=org, name='Rent')
    Expense.objects.create(organization=org, category=cat, amount='2000.00', date=today)

    resp = auth_client.get(f'/api/v1/reports/daily-summary/?date={today}')
    assert resp.status_code == 200
    assert resp.json()['total_expenses'] == '2000.00'
```

- [ ] **Step 2: Run to confirm they fail**

```bash
pytest tests/test_reports.py::test_daily_summary_requires_date -v
```

Expected: FAIL with 404.

- [ ] **Step 3: Create app scaffold**

```bash
touch apps/reports/__init__.py
```

Create `apps/reports/apps.py`:

```python
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reports'
```

- [ ] **Step 4: Create `apps/reports/views.py`**

```python
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
```

- [ ] **Step 5: Create `apps/reports/urls.py`**

```python
from django.urls import path
from .views import DailySummaryView

urlpatterns = [
    path('daily-summary/', DailySummaryView.as_view(), name='daily-summary'),
]
```

- [ ] **Step 6: Register app and wire URL**

In `config/settings/base.py`, add after `'apps.expenses'`:

```python
    'apps.reports',
```

In `config/urls.py`, add:

```python
path('api/v1/reports/', include('apps.reports.urls')),
```

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_reports.py -v
```

Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add apps/reports/ config/settings/base.py config/urls.py tests/test_reports.py
git commit -m "feat: reports app with daily-summary endpoint"
```

---

## Task 6: Full test suite pass

- [ ] **Step 1: Run full suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS, no regressions in existing test files (`test_auth.py`, `test_branches.py`, `test_menu.py`, `test_orders.py`, `test_payments.py`).

- [ ] **Step 2: Commit if any fixes were needed**

Only commit if step 1 required any fixes not already committed.
