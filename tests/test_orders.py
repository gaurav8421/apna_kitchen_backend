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


@pytest.mark.django_db
def test_order_number_not_reassigned_on_update(org, branch, owner):
    order = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    assert order.order_number == 'ORD-0001'
    order.status = 'preparing'
    order.save()
    order.refresh_from_db()
    assert order.order_number == 'ORD-0001'


from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_create_order(auth_client, org, branch, item):
    url = reverse('order-list')
    payload = {
        'branch': str(branch.id),
        'order_type': 'dine_in',
        'table_number': '5',
        'items': [
            {
                'item': str(item.id),
                'item_name': 'Butter Chicken',
                'unit_price': '320.00',
                'quantity': 2,
                'subtotal': '640.00',
            }
        ],
        'subtotal': '640.00',
        'tax': '32.00',
        'total': '672.00',
    }
    resp = auth_client.post(url, payload, content_type='application/json')
    assert resp.status_code == 201
    data = resp.json()
    assert data['order_number'].startswith('ORD-')
    assert data['status'] == 'pending'
    assert len(data['items']) == 1


@pytest.mark.django_db
def test_list_orders_scoped_to_org(auth_client, org, branch, owner):
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other Org', slug='other-org-orders')
    other_branch = Branch.objects.create(name='Other', organization=other_org)
    other_owner = User.objects.create_user(
        email='other@o.com', password='pass', name='Other', organization=other_org, role='owner',
    )
    Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    Order.objects.create(
        organization=other_org, branch=other_branch, created_by=other_owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    resp = auth_client.get(reverse('order-list'))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.django_db
def test_update_order_status(auth_client, org, branch, owner):
    order = Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='100.00', tax='5.00', total='105.00',
    )
    url = reverse('order-update-status', args=[order.id])
    resp = auth_client.patch(url, {'status': 'preparing'}, content_type='application/json')
    assert resp.status_code == 200
    assert resp.json()['status'] == 'preparing'


@pytest.mark.django_db
def test_cashier_can_create_order(client, org, branch, item):
    cashier = User.objects.create_user(
        email='cashier@spice.com', password='pass', name='Cashier',
        organization=org, role='cashier',
    )
    token = str(RefreshToken.for_user(cashier).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    payload = {
        'branch': str(branch.id),
        'order_type': 'takeaway',
        'items': [
            {'item': str(item.id), 'item_name': 'Butter Chicken',
             'unit_price': '320.00', 'quantity': 1, 'subtotal': '320.00'}
        ],
        'subtotal': '320.00', 'tax': '16.00', 'total': '336.00',
    }
    resp = client.post(reverse('order-list'), payload, content_type='application/json')
    assert resp.status_code == 201


@pytest.mark.django_db
def test_cross_org_branch_rejected(auth_client, org):
    """Creating an order with a branch from another org must return 404."""
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other Branch Org', slug='other-branch-org')
    other_branch = Branch.objects.create(name='Other Branch', organization=other_org)
    item_cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)
    item = MenuItem.objects.create(organization=org, category=item_cat, name='Dish', price='100.00', item_type='veg')
    resp = auth_client.post(
        reverse('order-list'),
        {
            'branch': str(other_branch.id),
            'order_type': 'dine_in',
            'items': [{'item': str(item.id), 'item_name': 'Dish', 'unit_price': '100.00', 'quantity': 1, 'subtotal': '100.00'}],
            'subtotal': '100.00', 'tax': '5.00', 'total': '105.00',
        },
        content_type='application/json',
    )
    assert resp.status_code == 404


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
