from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from .models import Invoice
from .serializers import InvoiceSerializer


class InvoicePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["status", "vendor", "currency"]

    search_fields = [
        "invoice_number",
        "vendor__legal_name",
    ]

    ordering_fields = [
        "invoice_date",
        "due_date",
        "total_amount",
        "created_at",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return Invoice.objects.select_related(
            "vendor",
            "created_by",
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)