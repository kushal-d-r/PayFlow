
"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from reports.views import summary as report_summary


urlpatterns = [
    path("api/reports/summary/", report_summary, name="report-summary"),
    # Django Admin
    path("admin/", admin.site.urls),

    # Purchase Order APIs
    path("api/", include("purchase_orders.urls")),

    # Goods Receipt APIs
    path("api/", include("goods_receipts.urls")),

    # JWT Authentication
    path(
        "api/token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # Vendor APIs
    path("api/", include("vendors.urls")),

    # Invoice APIs
    path("api/", include("invoices.urls")),

    # Approval APIs
    path("api/", include("approvals.urls")),

    # DRF Browsable API Authentication
    path("api-auth/", include("rest_framework.urls")),
    
    
    path("api/", include("payments.urls")),
]
