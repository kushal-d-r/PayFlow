import re

from rest_framework import serializers

from .models import Vendor


class VendorSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = Vendor
        fields = [
            "id",
            "vendor_code",
            "legal_name",
            "display_name",
            "gstin",
            "pan",
            "contact_person",
            "email",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "payment_terms_days",
            "status",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]

    def validate_gstin(self, value):
        if not value:
            return None

        value = value.strip().upper()

        pattern = (
            r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]"
            r"[1-9A-Z]Z[0-9A-Z]$"
        )

        if not re.fullmatch(pattern, value):
            raise serializers.ValidationError(
                "Enter a GSTIN in the expected 15-character format."
            )

        return value

    def validate_pan(self, value):
        if value:
            value = value.strip().upper()

        return value