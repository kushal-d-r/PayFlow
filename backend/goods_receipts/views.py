from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import GoodsReceipt
from .serializers import GoodsReceiptSerializer


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    serializer_class = GoodsReceiptSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["status", "purchase_order"]
    search_fields = ["grn_number", "purchase_order__po_number"]
    ordering_fields = ["received_date", "created_at"]
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
            goods_receipt = serializer.save(received_by=request.user)

        output = self.get_serializer(goods_receipt)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        with transaction.atomic():
            goods_receipt = (
                GoodsReceipt.objects
                .select_for_update()
                .prefetch_related("items")
                .get(pk=pk)
            )

            if goods_receipt.status == GoodsReceipt.Status.ACCEPTED:
                return Response(
                    {"error": "This goods receipt is already accepted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if goods_receipt.status == GoodsReceipt.Status.REJECTED:
                return Response(
                    {"error": "A rejected goods receipt cannot be accepted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            items = list(goods_receipt.items.all())

            if not items:
                return Response(
                    {"error": "A goods receipt must contain at least one item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not any(item.accepted_quantity > 0 for item in items):
                return Response(
                    {"error": "At least one item must have an accepted quantity."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            goods_receipt.status = GoodsReceipt.Status.ACCEPTED
            goods_receipt.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Goods receipt accepted successfully.",
                "goods_receipt": self.get_serializer(goods_receipt).data,
            },
            status=status.HTTP_200_OK,
        )