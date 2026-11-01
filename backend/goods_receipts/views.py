
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.response import Response

from .models import GoodsReceipt
from .serializers import GoodsReceiptSerializer


class GoodsReceiptViewSet(viewsets.ModelViewSet):

    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "status",
        "purchase_order",
    ]

    search_fields = [
        "grn_number",
        "purchase_order__po_number",
    ]

    ordering_fields = [
        "received_date",
        "created_at",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return GoodsReceipt.objects.select_related(
            "purchase_order",
            "received_by",
        ).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            goods_receipt = serializer.save(
                received_by=request.user
            )

        output = self.get_serializer(goods_receipt)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED
        )
