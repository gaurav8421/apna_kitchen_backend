# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pulse** is a Django REST Framework-based restaurant management system providing a multi-tenant SaaS API. It manages organizations, branches, menus, orders, payments, inventory, expenses, and reporting for restaurant operations.

- **Framework**: Django 5.0.14 + Django REST Framework 3.15.2
- **Database**: PostgreSQL 16
- **Authentication**: JWT tokens (via rest_framework_simplejwt) with token blacklist support
- **Architecture**: Multi-tenant with organization-based isolation
- **API Documentation**: Swagger UI generated via drf-spectacular

## Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 16
- Redis 7

### Initial Setup
```bash
# 1. Install dependencies
pip install -r requirements/development.txt

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your local database credentials

# 3. Start services (PostgreSQL + Redis)
docker-compose up -d

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser
```

### Running the Application
```bash
# Development server on http://localhost:8000
python manage.py runserver

# Swagger API docs: http://localhost:8000/api/docs/
# Raw schema: http://localhost:8000/api/schema/
```

## Common Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests in a specific module
pytest tests/test_orders.py

# Run a specific test
pytest tests/test_orders.py::test_order_number_sequential

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=apps --cov-report=html
```

### Database Migrations
```bash
# Create a migration for model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show migration history
python manage.py showmigrations
```

### Code Quality
```bash
# Format with Black (if installed)
black .

# Check with flake8 (if installed)
flake8 apps/
```

## Architecture & Patterns

### Multi-Tenant Structure
The codebase is organized around an **organization-first** multi-tenant model:
- **Organization**: Top-level tenant (e.g., "Spice Route" restaurant chain)
- **Branch**: Physical location within an organization (e.g., "MG Road")
- **User**: Belongs to organization and optionally to a specific branch based on role

Each app (orders, menu, inventory, etc.) enforces organization isolation through:
1. ForeignKey to `Organization` on relevant models
2. QuerySet filtering in views via `request.user.organization`
3. Serializers that include org_id for validation
4. Custom permissions (see apps/accounts/permissions.py)

### URL Structure
```
/api/v1/{resource}/
```
All endpoints are versioned under `api/v1`. URLs are defined per-app in `urls.py` and included in `config/urls.py`.

### App Organization
Each app follows the standard Django structure:
- `models.py` - Database models with UUIDs as primary keys
- `views.py` - ViewSets (generics are preferred over APIView for consistency)
- `serializers.py` - DRF serializers with nested relationships
- `permissions.py` - Custom permission classes (see apps/accounts/permissions.py)
- `filters.py` - DjangoFilterBackend filters (optional, e.g., apps/orders/filters.py)
- `migrations/` - Auto-generated migration files
- `urls.py` - URL routing for the app
- `admin.py` - Django admin configuration

### Authentication & Authorization
- **JWT Authentication**: All endpoints (except `/api/v1/auth/`) require JWT token in Authorization header: `Authorization: Bearer {token}`
- **Token Lifecycle**: 
  - Access tokens expire in 8 hours
  - Refresh tokens expire in 7 days and rotate on use
  - Revoked tokens are blacklisted
- **Roles**: super_admin, owner, manager, cashier, kitchen (defined in apps/accounts/models.py User.ROLES)
- **Permission Classes**: IsOwner, IsOwnerOrManager, IsSuperAdmin in apps/accounts/permissions.py

### Serializer Patterns
Serializers use nested relationships extensively. Example:
```python
class OrderItemSerializer(serializers.ModelSerializer):
    menu_item = MenuItemSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'menu_item', 'quantity', 'price')
```
Always validate org_id in create/update methods to prevent cross-org data pollution.

### Model Patterns
- **UUID Primary Keys**: All models use `UUIDField` with `default=uuid.uuid4`
- **Soft/Hard Deletes**: Currently using hard deletes; prefer adding a `status` field for soft deletes if needed
- **Timestamps**: Models include `created_at` and `updated_at` with `auto_now_add`/`auto_now`
- **Organization Ownership**: Most models have `organization = ForeignKey('organizations.Organization')`

### QuerySet Filtering
Views filter querysets to the user's organization:
```python
def get_queryset(self):
    return Order.objects.filter(organization=self.request.user.organization)
```
Always do this to prevent data leakage across tenants.

## Key Testing Patterns

Tests use pytest + pytest-django + factory-boy:
- **Fixtures**: Defined at top of test file (org, branch, user, etc.) — reuse them
- **Factories**: Use factory-boy (e.g., in tests) for realistic test data generation
- **Database Isolation**: Each test runs in a transaction and rolls back; use `@pytest.mark.django_db`
- **Authentication**: Create a user, get tokens, add to request headers:
  ```python
  response = client.post('/api/v1/orders/', {...}, HTTP_AUTHORIZATION=f'Bearer {token}')
  ```

## File Structure
```
pulse-backend/
├── apps/
│   ├── accounts/          # User model, auth views (register, login, logout)
│   ├── organizations/     # Organization CRUD
│   ├── branches/          # Branch management
│   ├── menu/              # Menu categories and items
│   ├── orders/            # Orders and order items
│   ├── payments/          # Payment recording
│   ├── inventory/         # Stock tracking
│   ├── expenses/          # Expense management
│   └── reports/           # Analytics and reporting
├── config/
│   ├── settings/          # Django settings (base.py, development.py)
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI application
├── tests/                 # Integration/API tests (pytest)
├── requirements/          # Dependency files (base.txt, development.txt)
├── manage.py              # Django management script
└── docker-compose.yml     # PostgreSQL + Redis services
```

## Settings & Environment

Configuration is loaded via `python-decouple` from `.env`:
- `DEBUG` - Development mode flag
- `SECRET_KEY` - Django secret key (required in production)
- `DB_*` - PostgreSQL connection details
- `REDIS_URL` - Redis connection string
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `CORS_ALLOWED_ORIGINS` - Frontend origins allowed to call the API

Development settings inherit from base and enable `DEBUG=True` and `CORS_ALLOW_ALL_ORIGINS=True`.

## Key Dependencies
- **djangorestframework**: REST API framework
- **drf-spectacular**: OpenAPI schema generation and Swagger UI
- **rest_framework_simplejwt**: JWT authentication with token blacklist
- **django-filter**: Query parameter-based filtering (e.g., `?status=completed`)
- **psycopg2-binary**: PostgreSQL adapter
- **redis**: Redis client (for token blacklist and caching)
- **drf-nested-routers**: Nested URL routing for related resources
- **pytest-django**: Test runner for Django

## Common Patterns & Conventions

### Decimal Fields for Currency
All price/amount fields use `DecimalField(max_digits=10, decimal_places=2)` for accuracy.

### Order Number Generation
Orders generate sequential numbers (e.g., `ORD-0001`) via override of `save()` method using `count() + 1`. See apps/orders/models.py.

### Filtering in Views
Use `django_filters.rest_framework.DjangoFilterBackend` for query-string filtering:
```python
class OrderViewSet(viewsets.ModelViewSet):
    filterset_class = OrderFilter  # Defined in filters.py
```

### Documentation
Endpoints are auto-documented in Swagger. Add docstrings to ViewSet methods for better descriptions:
```python
def list(self, request):
    """List all orders for the user's organization."""
```

## Debugging Tips
- Enable query logging: Add `LOGGING` config to settings to see raw SQL
- Django shell: `python manage.py shell` for database exploration
- Check token payload: Decode JWT at jwt.io to inspect claims
- Swagger is invaluable: Use `/api/docs/` to test endpoints interactively
