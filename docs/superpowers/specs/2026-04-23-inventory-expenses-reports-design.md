# Design: Inventory, Expenses, Reports & Orders Filter Fix

**Date:** 2026-04-23  
**Status:** Approved

## Overview

Four independent issues observed in server logs:
1. `GET /api/v1/orders/?status=pending,preparing,ready` returns 400
2. `GET /api/v1/inventory/` returns 404 — app does not exist
3. `GET /api/v1/expenses/` and `/api/v1/expenses/categories/` return 404 — app does not exist
4. `GET /api/v1/reports/daily-summary/` returns 404 — app does not exist

## 1. Orders Status Multi-Filter Fix

**File:** `apps/orders/filters.py` (new)

Custom `FilterSet` using `django-filter`'s `BaseInFilter` + `CharFilter` to accept comma-separated status values and convert them to a `status__in` DB lookup.

```
?status=pending,preparing,ready  →  WHERE status IN ('pending', 'preparing', 'ready')
```

`OrderViewSet` replaces `filterset_fields` with `filterset_class = OrderFilter`.

## 2. Inventory App

**New app:** `apps/inventory/`

### Models

**`Ingredient`** — raw material stock
- `id`: UUID PK
- `organization`: FK to Organization
- `branch`: nullable FK to Branch
- `name`: CharField(200)
- `unit`: CharField choices — `g`, `kg`, `ml`, `l`, `pcs`
- `quantity`: DecimalField (current stock level)
- `low_stock_threshold`: DecimalField
- `created_at`, `updated_at`: auto timestamps

**`ItemStock`** — unit-level stock for a menu item
- `id`: UUID PK
- `organization`: FK to Organization
- `branch`: nullable FK to Branch
- `menu_item`: OneToOneField to MenuItem
- `quantity`: PositiveIntegerField (units available)
- `low_stock_threshold`: PositiveIntegerField
- `created_at`, `updated_at`: auto timestamps

### Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET, POST | `/api/v1/inventory/ingredients/` | List/create ingredients |
| GET, PATCH, DELETE | `/api/v1/inventory/ingredients/<id>/` | Retrieve/update/delete ingredient |
| GET, POST | `/api/v1/inventory/item-stock/` | List/create item stock entries |
| GET, PATCH, DELETE | `/api/v1/inventory/item-stock/<id>/` | Retrieve/update/delete item stock |

Both viewsets filter by `organization` in `get_queryset`. Both support `?branch=<uuid>` filter.

## 3. Expenses App

**New app:** `apps/expenses/`

### Models

**`ExpenseCategory`** — user-managed categories
- `id`: UUID PK
- `organization`: FK to Organization
- `name`: CharField(200)
- `created_at`: auto timestamp

**`Expense`** — expense record
- `id`: UUID PK
- `organization`: FK to Organization
- `branch`: nullable FK to Branch
- `category`: FK to ExpenseCategory
- `amount`: DecimalField(10, 2)
- `description`: TextField (blank allowed)
- `date`: DateField
- `recorded_by`: FK to User (set_null on delete)
- `created_at`: auto timestamp

### Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET, POST | `/api/v1/expenses/categories/` | List/create categories |
| GET, PATCH, DELETE | `/api/v1/expenses/categories/<id>/` | Retrieve/update/delete category |
| GET, POST | `/api/v1/expenses/` | List/create expenses |
| GET, PATCH, DELETE | `/api/v1/expenses/<id>/` | Retrieve/update/delete expense |

Both scoped to `organization`. Expenses filterable by `branch` and `date`.

## 4. Reports App

**New app:** `apps/reports/`

No models — all data computed on-the-fly from existing tables.

### Endpoint

`GET /api/v1/reports/daily-summary/?date=YYYY-MM-DD`

Implemented as a DRF `APIView`. Requires authentication. Scoped to `request.user.organization`.

### Response Shape

```json
{
  "date": "2026-04-22",
  "total_sales": "12500.00",
  "total_orders": 42,
  "orders_by_status": {
    "pending": 2,
    "preparing": 3,
    "ready": 1,
    "completed": 35,
    "cancelled": 1
  },
  "payment_method_breakdown": {
    "cash": "5000.00",
    "upi": "6500.00",
    "card": "1000.00",
    "online": "0.00"
  },
  "top_items": [
    {"item_name": "Paneer Butter Masala", "quantity_sold": 18, "revenue": "3600.00"}
  ],
  "total_expenses": "2000.00"
}
```

- `total_sales`: sum of `Order.total` where `status='completed'` and `created_at__date=date`
- `total_orders`: count of all orders on that date
- `orders_by_status`: count per status value
- `payment_method_breakdown`: sum of `Payment.amount` grouped by `method` for completed payments on that date
- `top_items`: top 10 `OrderItem` entries by `quantity` sum, joined from completed orders, sorted descending
- `total_expenses`: sum of `Expense.amount` where `date=date`

Returns 400 if `date` param is missing or invalid. Returns 200 with zeroed fields if no data exists for the date.

## Architecture Notes

- All new apps follow existing patterns: UUID PKs, org-scoped queryset, `IsAuthenticated` permission
- New apps registered in `INSTALLED_APPS` and wired into `config/urls.py`
- Each app gets its own migration
