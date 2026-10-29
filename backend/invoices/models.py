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

    # Initial upload field. We will add upload validation
    # and private file storage before production use.
    document = models.FileField(
        upload_to="invoices/%Y/%m/",
        blank=True,
        null=True,
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
                condition=Q(due_date__gte=models.F("invoice_date")),
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

    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        "accounts.User",
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