from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import Vendor
from .serializers import VendorSerializer


class VendorPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = VendorPagination

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields = [
        "vendor_code",
        "legal_name",
        "display_name",
        "gstin",
        "email",
        "city",
    ]

    ordering_fields = [
        "legal_name",
        "vendor_code",
        "created_at",
        "status",
    ]

    ordering = ["legal_name"]

    def get_queryset(self):
        return Vendor.objects.select_related("created_by").all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)