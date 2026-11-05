
import re
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class PurchaseOrder(models.Model):

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED", "Partially Received"
        FULLY_RECEIVED = "FULLY_RECEIVED", "Fully Received"
        CANCELLED = "CANCELLED", "Cancelled"

    po_number = models.CharField(
        max_length=50,
        unique=True,
    )

    vendor = models.ForeignKey(
        "vendors.Vendor",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )

    order_date = models.DateField()

    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=3,
        default="INR",
    )

    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_orders",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["vendor", "order_date"]),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.po_number:
            self.po_number = self.po_number.strip().upper()

            if not re.fullmatch(r"[A-Z0-9/-]{1,50}", self.po_number):
                errors["po_number"] = (
                    "PO number may contain only letters, numbers, "
                    "hyphens and slashes."
                )

        if self.currency:
            self.currency = self.currency.strip().upper()

            if not re.fullmatch(r"[A-Z]{3}", self.currency):
                errors["currency"] = (
                    "Currency must be a valid three-letter currency code."
                )

        if (
            self.expected_delivery_date
            and self.order_date
            and self.expected_delivery_date < self.order_date
        ):
            errors["expected_delivery_date"] = (
                "Expected delivery date cannot be before order date."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(models.Model):

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )

    line_number = models.PositiveIntegerField()

    item_code = models.CharField(
        max_length=50,
        blank=True,
    )

    description = models.TextField()

    unit_of_measure = models.CharField(
        max_length=20,
        default="UNIT",
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[
            MinValueValidator(Decimal("0.001")),
        ],
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["line_number"]

        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "line_number"],
                name="unique_po_line_number",
            ),

            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="po_item_quantity_positive",
            ),

            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="po_item_price_nonnegative",
            ),

            models.CheckConstraint(
                condition=(
                    Q(tax_rate__gte=0)
                    & Q(tax_rate__lte=100)
                ),
                name="po_item_tax_rate_valid",
            ),
        ]

    def clean(self):
        super().clean()

        errors = {}

        if self.line_number is not None and self.line_number < 1:
            errors["line_number"] = (
                "Line number must be greater than zero."
            )

        if not self.description or not self.description.strip():
            errors["description"] = (
                "Item description cannot be empty."
            )

        if self.quantity is not None and self.quantity <= 0:
            errors["quantity"] = (
                "Quantity must be greater than zero."
            )

        if self.unit_price is not None and self.unit_price < 0:
            errors["unit_price"] = (
                "Unit price cannot be negative."
            )

        if self.tax_rate is not None:
            if self.tax_rate < 0 or self.tax_rate > 100:
                errors["tax_rate"] = (
                    "Tax rate must be between 0 and 100."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return (
            self.quantity * self.unit_price
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @property
    def tax_amount(self):
        return (
            self.subtotal * self.tax_rate / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @property
    def total_amount(self):
        return (
            self.subtotal + self.tax_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def __str__(self):
        return (
            f"{self.purchase_order.po_number} "
            f"- Line {self.line_number}"
        )
