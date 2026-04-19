import pytest
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
    assert variant.price_delta == pytest.approx(40.00, abs=0.01)


@pytest.mark.django_db
def test_item_modifier(org):
    cat = MenuCategory.objects.create(organization=org, name='Mains', sort_order=2)
    item = MenuItem.objects.create(
        organization=org, category=cat,
        name='Pizza', price='350.00', item_type='veg',
    )
    mod = ItemModifier.objects.create(item=item, name='Extra Cheese', price='30.00')
    assert mod.price == pytest.approx(30.00, abs=0.01)
