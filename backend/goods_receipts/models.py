
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class GoodsReceipt(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECEIVED = "RECEIVED", "Received"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    grn_number = models.CharField(max_length=50, unique=True)

    purchase_order = models.ForeignKey(
        "purchase_orders.PurchaseOrder",
        on_delete=models.PROTECT,
        related_name="goods_receipts"
    )

    received_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    notes = models.TextField(blank=True)

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="goods_receipts"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-received_date"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["purchase_order"]),
        ]

    def __str__(self):
        return self.grn_number


class GoodsReceiptItem(models.Model):

    goods_receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="items"
    )

    purchase_order_item = models.ForeignKey(
        "purchase_orders.PurchaseOrderItem",
        on_delete=models.PROTECT,
        related_name="receipt_items"
    )

    received_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )

    accepted_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    rejected_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0
    )

    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["goods_receipt", "purchase_order_item"],
                name="unique_grn_po_item"
            ),
            models.CheckConstraint(
                condition=Q(received_quantity__gt=0),
                name="grn_received_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(accepted_quantity__gte=0),
                name="grn_accepted_quantity_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(rejected_quantity__gte=0),
                name="grn_rejected_quantity_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(
                    accepted_quantity__lte=models.F("received_quantity")
                ) & Q(
                    rejected_quantity__lte=models.F("received_quantity")
                ),
                name="grn_quantities_within_received"
            ),
            models.CheckConstraint(
                condition=Q(
                    accepted_quantity__lte=(
                        models.F("received_quantity")
                        - models.F("rejected_quantity")
                    )
                ),
                name="grn_accepted_rejected_within_received"
            ),
        ]

    def clean(self):
        if (
            self.goods_receipt_id
            and self.purchase_order_item_id
            and self.goods_receipt.purchase_order_id
            != self.purchase_order_item.purchase_order_id
        ):
            raise ValidationError(
                "The PO item must belong to the GRN's purchase order."
            )

    def __str__(self):
        return (
            f"{self.goods_receipt.grn_number} - "
            f"{self.purchase_order_item.description}"
        )
