from django.urls import path
from rest_framework.routers import SimpleRouter
from .views import IngredientViewSet, ItemStockViewSet, InventoryTransactionViewSet

router = SimpleRouter()
router.register('ingredients', IngredientViewSet, basename='ingredient')
router.register('item-stock', ItemStockViewSet, basename='itemstock')
router.register('transactions', InventoryTransactionViewSet, basename='inventorytransaction')

urlpatterns = router.urls + [
    path('', IngredientViewSet.as_view({'get': 'list', 'post': 'create'}), name='inventory-list'),
    path('<uuid:pk>/', IngredientViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}), name='inventory-detail'),
]
