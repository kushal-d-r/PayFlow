
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

from vendors.models import Vendor


class Invoice(models.Model):

    class Status(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        APPROVAL_PENDING = "APPROVAL_PENDING", "Approval Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        PAID = "PAID", "Paid"
        EXCEPTION = "EXCEPTION", "Exception"

    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="invoices",
    )
    
    
    
    purchase_order = models.ForeignKey(
        "purchase_orders.PurchaseOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )
    
    
    
    
    
    

    invoice_number = models.CharField(max_length=100)
    invoice_date = models.DateField()
    due_date = models.DateField()

    currency = models.CharField(max_length=3, default="INR")

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    document = models.FileField(
        upload_to="invoices/%Y/%m/",
        blank=True,
        null=True,
    )

    # Links the invoice to its original uploaded document.
    # One uploaded document can create only one invoice.
    source_document = models.OneToOneField(
        "InvoiceDocument",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="created_invoice",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.UPLOADED,
        db_index=True,
    )

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_invoices",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "invoice_number"],
                name="unique_invoice_number_per_vendor",
            ),
            models.CheckConstraint(
                condition=Q(
                    due_date__gte=models.F("invoice_date")
                ),
                name="invoice_due_date_gte_invoice_date",
            ),
        ]

        indexes = [
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["invoice_date"]),
        ]

    def clean(self):
        super().clean()

        if (
            self.subtotal is not None
            and self.tax_amount is not None
            and self.total_amount is not None
            and self.total_amount < self.subtotal + self.tax_amount
        ):
            raise ValidationError({
                "total_amount": (
                    "Total amount cannot be less than subtotal plus tax."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} - {self.vendor.legal_name}"


class InvoiceItem(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )

    purchase_order_item = models.ForeignKey(
        "purchase_orders.PurchaseOrderItem",
        on_delete=models.PROTECT,
        related_name="invoice_items",
    )

    line_number = models.PositiveIntegerField()

    description = models.TextField()

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = ["line_number"]

        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "line_number"],
                name="unique_invoice_line_number",
            ),
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="invoice_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="invoice_item_price_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(tax_rate__gte=0) & Q(tax_rate__lte=100),
                name="invoice_item_tax_rate_valid",
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

    def clean(self):
        super().clean()

        if (
            self.invoice_id
            and self.purchase_order_item_id
            and self.invoice.purchase_order_id
            and self.purchase_order_item.purchase_order_id
            != self.invoice.purchase_order_id
        ):
            raise ValidationError({
                "purchase_order_item": (
                    "This item does not belong to the invoice's purchase order."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.invoice.invoice_number} "
            f"- Line {self.line_number}"
        )



class InvoiceDocument(models.Model):

    class ProcessingStatus(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class DocumentType(models.TextChoices):
        PDF = "PDF", "PDF"
        JPEG = "JPEG", "JPEG"
        PNG = "PNG", "PNG"

    file = models.FileField(
        upload_to="invoice_documents/%Y/%m/"
    )

    original_filename = models.CharField(max_length=255)

    document_type = models.CharField(
        max_length=10,
        choices=DocumentType.choices,
    )

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
        db_index=True,
    )

    extracted_text = models.TextField(blank=True)

    # Stores structured invoice fields extracted from OCR text.
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
    )

    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_invoice_documents",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.original_filename} "
            f"({self.processing_status})"
        )
