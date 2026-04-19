from rest_framework_nested import routers
from rest_framework.routers import DefaultRouter
from .views import MenuCategoryViewSet, MenuItemViewSet, ItemVariantViewSet, ItemModifierViewSet

router = DefaultRouter()
router.register('categories', MenuCategoryViewSet, basename='menucategory')
router.register('items', MenuItemViewSet, basename='menuitem')

items_router = routers.NestedDefaultRouter(router, 'items', lookup='item')
items_router.register('variants', ItemVariantViewSet, basename='menuitem-variants')
items_router.register('modifiers', ItemModifierViewSet, basename='menuitem-modifiers')

urlpatterns = router.urls + items_router.urls
