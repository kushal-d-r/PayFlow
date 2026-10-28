import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Vendor(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Verification"
        ACTIVE = "ACTIVE", "Active"
        ON_HOLD = "ON_HOLD", "On Hold"
        INACTIVE = "INACTIVE", "Inactive"

    # Basic identification
    vendor_code = models.CharField(max_length=30, unique=True)
    legal_name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=150, blank=True)

    # Indian tax information
    gstin = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True,
    )
    pan = models.CharField(
        max_length=10,
        blank=True,
    )

    # Contact information
    contact_person = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # Address
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)

    # Payment terms
    payment_terms_days = models.PositiveSmallIntegerField(default=30)

    # Vendor lifecycle
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_vendors",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["legal_name"]
        indexes = [
            models.Index(fields=["legal_name"]),
            models.Index(fields=["status", "legal_name"]),
        ]

    def clean(self):
        super().clean()

        if self.gstin:
            self.gstin = self.gstin.strip().upper()

            # Basic format validation, not verification against GST records.
            gstin_pattern = (
                r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]"
                r"[1-9A-Z]Z[0-9A-Z]$"
            )

            if not re.fullmatch(gstin_pattern, self.gstin):
                raise ValidationError({
                    "gstin": "Enter a GSTIN in the expected 15-character format."
                })

        if self.pan:
            self.pan = self.pan.strip().upper()

            pan_pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]$"

            if not re.fullmatch(pan_pattern, self.pan):
                raise ValidationError({
                    "pan": "Enter a PAN in the expected 10-character format."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor_code} - {self.legal_name}"
