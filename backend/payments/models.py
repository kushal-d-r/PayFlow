
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        NEFT = "NEFT", "NEFT"
        RTGS = "RTGS", "RTGS"
        IMPS = "IMPS", "IMPS"
        UPI = "UPI", "UPI"
        CHEQUE = "CHEQUE", "Cheque"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice = models.ForeignKey(
        "invoices.Invoice",
        on_delete=models.PROTECT,
        related_name="payments"
    )

    payment_reference = models.CharField(
        max_length=100,
        unique=True
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    currency = models.CharField(
        max_length=3,
        default="INR"
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )

    transaction_id = models.CharField(
        max_length=150,
        blank=True
    )

    payment_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    notes = models.TextField(blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_payments"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-payment_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "payment_date"]),
            models.Index(fields=["invoice", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive"
            )
        ]

    def __str__(self):
        return f"{self.payment_reference} - {self.invoice.invoice_number}"



class PaymentHistory(models.Model):

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="history"
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices
    )

    previous_status = models.CharField(
        max_length=20,
        choices=Payment.Status.choices,
        blank=True
    )

    new_status = models.CharField(
        max_length=20,
        choices=Payment.Status.choices
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_history_actions"
    )

    comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["payment", "created_at"]
            ),
        ]

    def __str__(self):
        return (
            f"{self.payment.payment_reference} - "
            f"{self.action}"
        )
