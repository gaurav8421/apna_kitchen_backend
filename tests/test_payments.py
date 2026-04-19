import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.accounts.models import User
from apps.orders.models import Order


@pytest.fixture
def org():
    return Organization.objects.create(name='Pay Test', slug='pay-test')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='Main', organization=org)


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='pay@test.com', password='pass1234', name='Owner',
        organization=org, role='owner',
    )


@pytest.fixture
def order(org, branch, owner):
    return Order.objects.create(
        organization=org, branch=branch, created_by=owner,
        order_type='dine_in', subtotal='300.00', tax='15.00', total='315.00',
    )


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_record_cash_payment(auth_client, org, order):
    url = reverse('payment-list')
    payload = {
        'order': str(order.id),
        'amount': '315.00',
        'method': 'cash',
    }
    resp = auth_client.post(url, payload, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['status'] == 'completed'


@pytest.mark.django_db
def test_list_payments_scoped_to_org(auth_client, org, order):
    from apps.payments.models import Payment
    Payment.objects.create(organization=org, order=order, amount='315.00', method='cash', status='completed')
    resp = auth_client.get(reverse('payment-list'))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.django_db
def test_record_upi_payment(auth_client, org, order):
    payload = {
        'order': str(order.id),
        'amount': '315.00',
        'method': 'upi',
        'reference_id': 'UPI123456',
    }
    resp = auth_client.post(reverse('payment-list'), payload, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['reference_id'] == 'UPI123456'
