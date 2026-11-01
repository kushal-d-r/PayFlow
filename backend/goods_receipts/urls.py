
from rest_framework.routers import DefaultRouter
from .views import GoodsReceiptViewSet

router = DefaultRouter()
router.register("goods-receipts", GoodsReceiptViewSet, basename="goods-receipt")

urlpatterns = router.urls
