import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_register_creates_org_and_owner(client):
    payload = {
        'org_name': 'Spice Garden',
        'name': 'Rahul Sharma',
        'email': 'rahul@spicegarden.com',
        'password': 'SecurePass123',
    }
    response = client.post(reverse('auth-register'), payload, content_type='application/json')
    assert response.status_code == 201
    data = response.json()
    assert data['user']['role'] == 'owner'
    assert data['user']['org_name'] == 'Spice Garden'
    assert 'access' in data
    assert 'refresh' in data


@pytest.mark.django_db
def test_login_returns_tokens(client, django_user_model):
    from apps.organizations.models import Organization
    org = Organization.objects.create(name='Test Org', slug='test-org')
    django_user_model.objects.create_user(
        email='test@test.com', password='pass1234', name='Test', organization=org, role='owner'
    )
    response = client.post(reverse('auth-login'), {
        'email': 'test@test.com', 'password': 'pass1234'
    }, content_type='application/json')
    assert response.status_code == 200
    assert 'access' in response.json()


@pytest.mark.django_db
def test_register_duplicate_email_fails(client):
    from apps.organizations.models import Organization
    from apps.accounts.models import User
    org = Organization.objects.create(name='Org', slug='org')
    User.objects.create_user(email='dup@test.com', password='pass', name='Dup', organization=org)
    response = client.post(reverse('auth-register'), {
        'org_name': 'New Org', 'name': 'New', 'email': 'dup@test.com', 'password': 'pass1234'
    }, content_type='application/json')
    assert response.status_code == 400
