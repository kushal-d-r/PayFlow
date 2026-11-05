
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PurchaseOrder
from .serializers import PurchaseOrderSerializer


class PurchaseOrderViewSet(viewsets.ModelViewSet):

    serializer_class = PurchaseOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["status", "vendor", "currency"]

    search_fields = [
        "po_number",
        "vendor__legal_name",
    ]

    ordering_fields = [
        "order_date",
        "expected_delivery_date",
        "created_at",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return PurchaseOrder.objects.select_related(
            "vendor",
            "created_by",
        ).prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            purchase_order = serializer.save(
                created_by=request.user
            )

        output = self.get_serializer(purchase_order)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"], url_path="issue")
    def issue(self, request, pk=None):
        with transaction.atomic():
            purchase_order = (
                PurchaseOrder.objects
                .select_for_update()
                .prefetch_related("items")
                .get(pk=pk)
            )

            if purchase_order.status != PurchaseOrder.Status.DRAFT:
                return Response(
                    {"error": "Only draft purchase orders can be issued."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not purchase_order.items.exists():
                return Response(
                    {"error": "A purchase order must contain at least one item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            purchase_order.status = PurchaseOrder.Status.ISSUED
            purchase_order.save(
                update_fields=["status", "updated_at"]
            )

        return Response(
            {
                "message": "Purchase order issued successfully.",
                "purchase_order": self.get_serializer(purchase_order).data,
            },
            status=status.HTTP_200_OK,
        )
