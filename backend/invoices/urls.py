from rest_framework.routers import DefaultRouter

from .views import InvoiceViewSet, InvoiceDocumentViewSet

router = DefaultRouter()

router.register(
    "invoices",
    InvoiceViewSet,
    basename="invoice",
)

router.register(
    "invoice-documents",
    InvoiceDocumentViewSet,
    basename="invoice-document",
)

urlpatterns = router.urls