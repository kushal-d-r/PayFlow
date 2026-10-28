from rest_framework import serializers

from .models import Invoice


class InvoiceSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(
        source="vendor.legal_name",
        read_only=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = Invoice
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "due_date",
            "currency",
            "subtotal",
            "tax_amount",
            "total_amount",
            "document",
            "status",
            "notes",
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

    def validate(self, attrs):
        # On updates, use existing values for omitted fields.
        instance = getattr(self, "instance", None)

        invoice_date = attrs.get(
            "invoice_date",
            getattr(instance, "invoice_date", None),
        )
        due_date = attrs.get(
            "due_date",
            getattr(instance, "due_date", None),
        )
        subtotal = attrs.get(
            "subtotal",
            getattr(instance, "subtotal", None),
        )
        tax_amount = attrs.get(
            "tax_amount",
            getattr(instance, "tax_amount", None),
        )
        total_amount = attrs.get(
            "total_amount",
            getattr(instance, "total_amount", None),
        )

        if invoice_date and due_date and due_date < invoice_date:
            raise serializers.ValidationError({
                "due_date": "Due date cannot be earlier than invoice date."
            })

        if (
            subtotal is not None
            and tax_amount is not None
            and total_amount is not None
            and total_amount < subtotal + tax_amount
        ):
            raise serializers.ValidationError({
                "total_amount": (
                    "Total amount cannot be less than subtotal plus tax."
                )
            })

        return attrs