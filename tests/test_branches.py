import pytest
from django.urls import reverse
from apps.organizations.models import Organization
from apps.accounts.models import User
from apps.branches.models import Branch


@pytest.fixture
def org():
    return Organization.objects.create(name='Test Org', slug='test-org-branch')


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@test.com', password='pass1234',
        name='Owner', organization=org, role='owner'
    )


@pytest.fixture
def auth_client(client, owner):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_create_branch(auth_client, org):
    response = auth_client.post(reverse('branch-list'), {
        'name': 'Main Branch',
        'address': '123 MG Road',
        'tax_rate': '5.00',
    }, content_type='application/json')
    assert response.status_code == 201
    assert response.json()['name'] == 'Main Branch'


@pytest.mark.django_db
def test_list_branches_scoped_to_org(auth_client, org):
    Branch.objects.create(organization=org, name='Branch A')
    Branch.objects.create(organization=org, name='Branch B')
    other_org = Organization.objects.create(name='Other', slug='other')
    Branch.objects.create(organization=other_org, name='Other Branch')

    response = auth_client.get(reverse('branch-list'))
    assert response.status_code == 200
    names = [b['name'] for b in response.json()]
    assert 'Branch A' in names
    assert 'Branch B' in names
    assert 'Other Branch' not in names


@pytest.mark.django_db
def test_cashier_cannot_create_branch(client, org):
    cashier = User.objects.create_user(
        email='cashier@test.com', password='pass1234',
        name='Cashier', organization=org, role='cashier'
    )
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(cashier).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    response = client.post(reverse('branch-list'), {
        'name': 'Cashier Branch'
    }, content_type='application/json')
    assert response.status_code == 403
