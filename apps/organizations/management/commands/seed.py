import random
from datetime import date, timedelta, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import Order, OrderItem
from apps.payments.models import Payment
from apps.expenses.models import ExpenseCategory, Expense
from apps.inventory.models import Ingredient, ItemStock


MENU_DATA = [
    ('Starters', 0, [
        ('Paneer Tikka', '280.00', 'veg'),
        ('Chicken 65', '320.00', 'non_veg'),
        ('Veg Spring Rolls', '220.00', 'veg'),
        ('Fish Fry', '380.00', 'non_veg'),
    ]),
    ('Mains', 1, [
        ('Butter Chicken', '380.00', 'non_veg'),
        ('Dal Makhani', '260.00', 'veg'),
        ('Paneer Butter Masala', '320.00', 'veg'),
        ('Chicken Biryani', '420.00', 'non_veg'),
        ('Veg Biryani', '320.00', 'veg'),
        ('Mutton Rogan Josh', '480.00', 'non_veg'),
    ]),
    ('Breads', 2, [
        ('Butter Naan', '60.00', 'veg'),
        ('Garlic Roti', '50.00', 'veg'),
        ('Paratha', '70.00', 'veg'),
    ]),
    ('Beverages', 3, [
        ('Mango Lassi', '120.00', 'veg'),
        ('Masala Chai', '60.00', 'veg'),
        ('Fresh Lime Soda', '80.00', 'veg'),
        ('Cold Coffee', '150.00', 'veg'),
    ]),
    ('Desserts', 4, [
        ('Gulab Jamun', '120.00', 'veg'),
        ('Kulfi', '140.00', 'veg'),
        ('Rasgulla', '100.00', 'veg'),
    ]),
]

EXPENSE_CATEGORIES = ['Rent', 'Salaries', 'Utilities', 'Supplies', 'Marketing', 'Maintenance', 'Food & Ingredients']

INGREDIENTS = [
    ('Tomatoes', 'kg', '15.000', '3.000'),
    ('Onions', 'kg', '20.000', '5.000'),
    ('Chicken', 'kg', '10.000', '2.000'),
    ('Paneer', 'kg', '5.000', '1.000'),
    ('Rice (Basmati)', 'kg', '25.000', '5.000'),
    ('Cooking Oil', 'l', '10.000', '2.000'),
    ('Butter', 'kg', '3.000', '0.500'),
    ('Cream', 'l', '4.000', '1.000'),
    ('Ginger', 'kg', '2.000', '0.500'),
    ('Garlic', 'kg', '2.000', '0.500'),
    ('Cumin Seeds', 'g', '500.000', '100.000'),
    ('Milk', 'l', '8.000', '2.000'),
]

ORDER_TYPES = ['dine_in', 'takeaway', 'delivery']
PAYMENT_METHODS = ['cash', 'upi', 'card']
CUSTOMER_NAMES = [
    'Rahul Sharma', 'Priya Patel', 'Amit Kumar', 'Sneha Reddy', 'Vijay Singh',
    'Meera Nair', 'Rohit Gupta', 'Ananya Joshi', 'Kiran Rao', 'Deepak Verma',
    '', '', '',  # some orders without names
]


class Command(BaseCommand):
    help = 'Seed the database with realistic dummy data'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Days of historical data to generate')
        parser.add_argument('--orders-per-day', type=int, default=20, help='Approx orders per day')

    @transaction.atomic
    def handle(self, *args, **options):
        days = options['days']
        orders_per_day = options['orders_per_day']

        self.stdout.write('Seeding organization and users...')
        org, _ = Organization.objects.get_or_create(
            slug='pulse-demo',
            defaults={'name': 'Spice Garden Restaurant'},
        )

        owner, _ = User.objects.get_or_create(
            email='owner@pulsedemo.com',
            defaults={
                'name': 'Arjun Mehta',
                'organization': org,
                'role': 'owner',
                'is_active': True,
            },
        )
        if _:
            owner.set_password('Demo@1234')
            owner.save()

        manager, _ = User.objects.get_or_create(
            email='manager@pulsedemo.com',
            defaults={
                'name': 'Kavitha Iyer',
                'organization': org,
                'role': 'manager',
                'is_active': True,
            },
        )
        if _:
            manager.set_password('Demo@1234')
            manager.save()

        cashier, _ = User.objects.get_or_create(
            email='cashier@pulsedemo.com',
            defaults={
                'name': 'Ravi Kumar',
                'organization': org,
                'role': 'cashier',
                'is_active': True,
            },
        )
        if _:
            cashier.set_password('Demo@1234')
            cashier.save()

        self.stdout.write('Seeding branches...')
        branch_main, _ = Branch.objects.get_or_create(
            organization=org, name='Koramangala',
            defaults={'address': '5th Block, Koramangala, Bengaluru', 'phone': '9900112233'},
        )
        branch_two, _ = Branch.objects.get_or_create(
            organization=org, name='Indiranagar',
            defaults={'address': '100 Feet Road, Indiranagar, Bengaluru', 'phone': '9900112244'},
        )

        self.stdout.write('Seeding menu...')
        menu_items = []
        for cat_name, sort_order, items in MENU_DATA:
            cat, _ = MenuCategory.objects.get_or_create(
                organization=org, name=cat_name,
                defaults={'sort_order': sort_order},
            )
            for item_name, price, item_type in items:
                item, _ = MenuItem.objects.get_or_create(
                    organization=org, name=item_name,
                    defaults={'category': cat, 'price': price, 'item_type': item_type, 'is_available': True},
                )
                menu_items.append(item)

        self.stdout.write('Seeding inventory...')
        for name, unit, qty, threshold in INGREDIENTS:
            for branch in [branch_main, branch_two]:
                Ingredient.objects.get_or_create(
                    organization=org, branch=branch, name=name,
                    defaults={'unit': unit, 'quantity': qty, 'low_stock_threshold': threshold},
                )
        for item in menu_items:
            ItemStock.objects.get_or_create(
                organization=org, menu_item=item,
                defaults={'quantity': random.randint(10, 50), 'low_stock_threshold': 5},
            )

        self.stdout.write('Seeding expense categories and expenses...')
        exp_cats = {}
        for cat_name in EXPENSE_CATEGORIES:
            cat, _ = ExpenseCategory.objects.get_or_create(organization=org, name=cat_name)
            exp_cats[cat_name] = cat

        today = date.today()
        for i in range(days):
            day = today - timedelta(days=i)
            # Rent only on 1st of month
            if day.day == 1:
                Expense.objects.get_or_create(
                    organization=org, category=exp_cats['Rent'], date=day,
                    defaults={'amount': '85000.00', 'branch': branch_main, 'recorded_by': manager},
                )
            # Daily expenses
            for cat_name, amount_range in [
                ('Utilities', (800, 1500)),
                ('Supplies', (500, 2000)),
                ('Food & Ingredients', (3000, 8000)),
            ]:
                if not Expense.objects.filter(organization=org, category=exp_cats[cat_name], date=day).exists():
                    amount = random.randint(*amount_range)
                    Expense.objects.create(
                        organization=org,
                        category=exp_cats[cat_name],
                        branch=random.choice([branch_main, branch_two]),
                        amount=f'{amount}.00',
                        date=day,
                        recorded_by=manager,
                    )
            # Weekly salary
            if day.weekday() == 0:
                if not Expense.objects.filter(organization=org, category=exp_cats['Salaries'], date=day).exists():
                    Expense.objects.create(
                        organization=org, category=exp_cats['Salaries'],
                        amount='35000.00', date=day, recorded_by=owner,
                    )

        self.stdout.write(f'Seeding {days} days of orders...')
        staff = [owner, cashier]
        for i in range(days):
            day = today - timedelta(days=i)
            count = random.randint(max(1, orders_per_day - 5), orders_per_day + 5)
            for _ in range(count):
                branch = random.choice([branch_main, branch_two])
                order_type = random.choice(ORDER_TYPES)
                customer = random.choice(CUSTOMER_NAMES)
                status = random.choices(
                    ['completed', 'cancelled', 'pending'],
                    weights=[85, 10, 5],
                )[0]

                items_sample = random.sample(menu_items, k=random.randint(1, 4))
                subtotal = Decimal('0')
                line_items = []
                for menu_item in items_sample:
                    qty = random.randint(1, 3)
                    price = Decimal(str(menu_item.price))
                    line_subtotal = price * qty
                    subtotal += line_subtotal
                    line_items.append((menu_item, qty, price, line_subtotal))

                tax = (subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
                total = subtotal + tax

                order = Order.objects.create(
                    organization=org,
                    branch=branch,
                    order_type=order_type,
                    customer_name=customer,
                    status=status,
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                    created_by=random.choice(staff),
                )
                # Patch created_at to the correct historical date
                naive_dt = datetime(day.year, day.month, day.day, random.randint(10, 22), random.randint(0, 59))
                Order.objects.filter(pk=order.pk).update(created_at=timezone.make_aware(naive_dt))

                for menu_item, qty, price, line_subtotal in line_items:
                    OrderItem.objects.create(
                        order=order,
                        item=menu_item,
                        item_name=menu_item.name,
                        unit_price=price,
                        quantity=qty,
                        subtotal=line_subtotal,
                    )

                if status == 'completed':
                    Payment.objects.create(
                        organization=org,
                        order=order,
                        amount=total,
                        method=random.choice(PAYMENT_METHODS),
                        status='completed',
                    )

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Seeded:\n'
            f'  Org:       {org.name} (slug: {org.slug})\n'
            f'  Branches:  Koramangala, Indiranagar\n'
            f'  Users:     owner@pulsedemo.com / manager@pulsedemo.com / cashier@pulsedemo.com  (password: Demo@1234)\n'
            f'  Menu:      {len(menu_items)} items across {len(MENU_DATA)} categories\n'
            f'  Inventory: {len(INGREDIENTS) * 2} ingredient stock entries + {len(menu_items)} item stock entries\n'
            f'  Expenses:  ~{days * 3} expense records over {days} days\n'
            f'  Orders:    ~{days * orders_per_day} orders over {days} days\n'
        ))
