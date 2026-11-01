"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    path("api/", include("purchase_orders.urls")),
    path("api/", include("goods_receipts.urls")),

    # JWT Authentication
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Vendor APIs
    path("api/", include("vendors.urls")),

    # Invoice APIs
    path("api/", include("invoices.urls")),

    # DRF Browsable API Authentication
    path("api-auth/", include("rest_framework.urls")),
]