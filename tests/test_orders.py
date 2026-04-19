import pytest
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.accounts.models import User
from apps.menu.models import MenuCategory, MenuItem
from apps.orders.models import Order, OrderItem


@pytest.fixture
def org():
    return Organization.objects.create(name='Spice Route', slug='spice-route-orders')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='MG Road', organization=org)


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@spice.com', password='pass1234',
        name='Owner', organization=org, role='owner',
    )


@pytest.fixture
def category(org):
    return MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)


@pytest.fixture
def item(org, category):
    return MenuItem.objects.create(
        organization=org, category=category,
        name='Butter Chicken', price='320.00', item_type='non_veg',
    )


@pytest.mark.django_db
def test_order_number_sequential(org, branch, owner):
    o1 = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='320.00', tax='16.00', total='336.00',
    )
    o2 = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='takeaway', subtotal='100.00', tax='5.00', total='105.00',
    )
    assert o1.order_number == 'ORD-0001'
    assert o2.order_number == 'ORD-0002'


@pytest.mark.django_db
def test_order_number_scoped_per_branch(org, owner):
    branch_a = Branch.objects.create(name='Branch A', organization=org)
    branch_b = Branch.objects.create(name='Branch B', organization=org)
    o_a = Order.objects.create(
        organization=org, branch=branch_a, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    o_b = Order.objects.create(
        organization=org, branch=branch_b, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    assert o_a.order_number == 'ORD-0001'
    assert o_b.order_number == 'ORD-0001'


@pytest.mark.django_db
def test_order_item_subtotal(org, branch, owner, item):
    order = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='640.00', tax='32.00', total='672.00',
    )
    oi = OrderItem.objects.create(
        order=order, item=item,
        item_name='Butter Chicken', unit_price='320.00', quantity=2, subtotal='640.00',
    )
    oi.refresh_from_db()
    from decimal import Decimal
    assert oi.subtotal == Decimal('640.00')
