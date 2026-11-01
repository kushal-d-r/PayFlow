
from django.conf import settings
from django.db import models
from django.db.models import Q


class PurchaseOrder(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially Received"
        FULLY_RECEIVED = "FULLY_RECEIVED", "Fully Received"
        CANCELLED = "CANCELLED", "Cancelled"

    po_number = models.CharField(max_length=50, unique=True)

    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="purchase_orders"
    )

    order_date = models.DateField()
    expected_delivery_date = models.DateField(
        null=True,
        blank=True
    )

    currency = models.CharField(max_length=3, default="INR")

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_orders"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["vendor", "order_date"]),
        ]

    def __str__(self):
        return self.po_number

    def clean(self):
        from django.core.exceptions import ValidationError

        if (
            self.expected_delivery_date
            and self.expected_delivery_date < self.order_date
        ):
            raise ValidationError(
                "Expected delivery date cannot be before order date."
            )


class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items"
    )

    line_number = models.PositiveIntegerField()

    item_code = models.CharField(
        max_length=50,
        blank=True
    )

    description = models.TextField()

    unit_of_measure = models.CharField(
        max_length=20,
        default="UNIT"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["line_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "line_number"],
                name="unique_po_line_number"
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="po_item_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="po_item_price_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(tax_rate__gte=0) & Q(tax_rate__lte=100),
                name="po_item_tax_rate_valid"
            ),
        ]

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def tax_amount(self):
        return self.subtotal * self.tax_rate / 100

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount

    def __str__(self):
        return f"{self.purchase_order.po_number} - Line {self.line_number}"
