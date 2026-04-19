import pytest
from decimal import Decimal
from apps.organizations.models import Organization
from apps.branches.models import Branch
from apps.menu.models import MenuCategory, MenuItem, ItemVariant, ItemModifier


@pytest.fixture
def org():
    return Organization.objects.create(name='Curry House', slug='curry-house-menu')


@pytest.fixture
def branch(org):
    return Branch.objects.create(name='Main Branch', organization=org)


@pytest.mark.django_db
def test_menu_category_str(org):
    cat = MenuCategory.objects.create(organization=org, name='Starters', sort_order=1)
    assert str(cat) == 'Starters'


@pytest.mark.django_db
def test_menu_item_str(org):
    cat = MenuCategory.objects.create(organization=org, name='Starters', sort_order=1)
    item = MenuItem.objects.create(
        organization=org, category=cat,
        name='Paneer Tikka', price='220.00', item_type='veg',
    )
    assert str(item) == 'Paneer Tikka'


@pytest.mark.django_db
def test_item_variant_price_delta(org):
    cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=2)
    item = MenuItem.objects.create(
        organization=org, category=cat,
        name='Biryani', price='280.00', item_type='non_veg',
    )
    variant = ItemVariant.objects.create(item=item, name='Large', price_delta='40.00')
    variant.refresh_from_db()
    assert variant.price_delta == Decimal('40.00')


@pytest.mark.django_db
def test_item_modifier(org):
    cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=2)
    item = MenuItem.objects.create(
        organization=org, category=cat,
        name='Pizza', price='350.00', item_type='veg',
    )
    mod = ItemModifier.objects.create(item=item, name='Extra Cheese', price='30.00')
    mod.refresh_from_db()
    assert mod.price == Decimal('30.00')


from django.urls import reverse
from apps.accounts.models import User
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def owner(org):
    return User.objects.create_user(
        email='owner@curry.com', password='pass1234',
        name='Owner', organization=org, role='owner',
    )


@pytest.fixture
def auth_client(client, owner):
    token = str(RefreshToken.for_user(owner).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.mark.django_db
def test_create_category(auth_client):
    url = reverse('menucategory-list')
    resp = auth_client.post(url, {'name': 'Starters', 'sort_order': 1}, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['name'] == 'Starters'


@pytest.mark.django_db
def test_list_categories_scoped_to_org(auth_client, org):
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other', slug='other-org-menu')
    MenuCategory.objects.create(organization=org, name='Mine', sort_order=1)
    MenuCategory.objects.create(organization=other_org, name='Not Mine', sort_order=1)
    resp = auth_client.get(reverse('menucategory-list'))
    assert resp.status_code == 200
    names = [c['name'] for c in resp.json()]
    assert 'Mine' in names
    assert 'Not Mine' not in names


@pytest.mark.django_db
def test_create_menu_item(auth_client, org):
    cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)
    url = reverse('menuitem-list')
    payload = {
        'category': str(cat.id),
        'name': 'Dal Makhani',
        'price': '220.00',
        'item_type': 'veg',
    }
    resp = auth_client.post(url, payload, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['price'] == '220.00'


@pytest.mark.django_db
def test_cashier_cannot_create_category(client, org):
    cashier = User.objects.create_user(
        email='cashier@curry.com', password='pass1234',
        name='Cashier', organization=org, role='cashier',
    )
    token = str(RefreshToken.for_user(cashier).access_token)
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    resp = client.post(
        reverse('menucategory-list'),
        {'name': 'Drinks', 'sort_order': 5},
        content_type='application/json',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_list_items_scoped_to_org(auth_client, org):
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other2', slug='other-org-menu2')
    cat1 = MenuCategory.objects.create(organization=org, name='A', sort_order=1)
    cat2 = MenuCategory.objects.create(organization=other_org, name='B', sort_order=1)
    MenuItem.objects.create(organization=org, category=cat1, name='My Item', price='100.00', item_type='veg')
    MenuItem.objects.create(organization=other_org, category=cat2, name='Their Item', price='100.00', item_type='veg')
    resp = auth_client.get(reverse('menuitem-list'))
    names = [i['name'] for i in resp.json()]
    assert 'My Item' in names
    assert 'Their Item' not in names


@pytest.mark.django_db
def test_create_variant_under_item(auth_client, org):
    cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=1)
    item = MenuItem.objects.create(organization=org, category=cat, name='Biryani', price='280.00', item_type='non_veg')
    url = reverse('menuitem-variants-list', kwargs={'item_pk': str(item.id)})
    resp = auth_client.post(url, {'name': 'Large', 'price_delta': '40.00'}, content_type='application/json')
    assert resp.status_code == 201
    assert resp.json()['name'] == 'Large'


@pytest.mark.django_db
def test_cross_org_item_pk_returns_404(auth_client, org):
    """Posting to another org's item_pk must return 404, not 500."""
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other3', slug='other-org-menu3')
    other_cat = MenuCategory.objects.create(organization=other_org, name='X', sort_order=1)
    other_item = MenuItem.objects.create(organization=other_org, category=other_cat, name='Other Item', price='100.00', item_type='veg')
    url = reverse('menuitem-variants-list', kwargs={'item_pk': str(other_item.id)})
    resp = auth_client.post(url, {'name': 'Small', 'price_delta': '0.00'}, content_type='application/json')
    assert resp.status_code == 404


@pytest.mark.django_db
def test_cross_org_category_rejected(auth_client, org):
    """Posting a category UUID from another org must be rejected."""
    from apps.organizations.models import Organization
    other_org = Organization.objects.create(name='Other4', slug='other-org-menu4')
    other_cat = MenuCategory.objects.create(organization=other_org, name='Other Cat', sort_order=1)
    resp = auth_client.post(
        reverse('menuitem-list'),
        {'category': str(other_cat.id), 'name': 'Item', 'price': '100.00', 'item_type': 'veg'},
        content_type='application/json',
    )
    assert resp.status_code == 400
