
import re
from pathlib import Path

import pymupdf
from PIL import Image

from django.db import transaction
from rest_framework import serializers

from .models import Invoice, InvoiceItem, InvoiceDocument


# ============================================================
# INVOICE ITEM SERIALIZER
# ============================================================

class InvoiceItemSerializer(serializers.ModelSerializer):

    subtotal = serializers.DecimalField(
        max_digits=16,
        decimal_places=2,
        read_only=True
    )

    tax_amount = serializers.DecimalField(
        max_digits=16,
        decimal_places=2,
        read_only=True
    )

    total_amount = serializers.DecimalField(
        max_digits=16,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = InvoiceItem

        fields = [
            "id",
            "line_number",
            "purchase_order_item",
            "description",
            "quantity",
            "unit_price",
            "tax_rate",
            "subtotal",
            "tax_amount",
            "total_amount",
        ]

        read_only_fields = [
            "id",
            "subtotal",
            "tax_amount",
            "total_amount",
        ]


# ============================================================
# INVOICE SERIALIZER
# ============================================================

class InvoiceSerializer(serializers.ModelSerializer):

    vendor_name = serializers.CharField(
        source="vendor.legal_name",
        read_only=True,
    )

    purchase_order_number = serializers.CharField(
        source="purchase_order.po_number",
        read_only=True,
        allow_null=True,
    )

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    items = InvoiceItemSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = Invoice

        fields = [
            "id",
            "vendor",
            "vendor_name",
            "purchase_order",
            "purchase_order_number",
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
            "items",
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

        vendor = attrs.get(
            "vendor",
            getattr(instance, "vendor", None),
        )

        purchase_order = attrs.get(
            "purchase_order",
            getattr(instance, "purchase_order", None),
        )

        items = attrs.get("items")

        # Validate invoice dates.
        if (
            invoice_date
            and due_date
            and due_date < invoice_date
        ):
            raise serializers.ValidationError({
                "due_date": (
                    "Due date cannot be earlier than invoice date."
                )
            })

        # Validate invoice monetary amounts.
        if (
            subtotal is not None
            and tax_amount is not None
            and total_amount is not None
            and total_amount < subtotal + tax_amount
        ):
            raise serializers.ValidationError({
                "total_amount": (
                    "Total amount cannot be less than "
                    "subtotal plus tax."
                )
            })

        # Validate vendor and purchase order relationship.
        if (
            purchase_order
            and vendor
            and purchase_order.vendor_id != vendor.id
        ):
            raise serializers.ValidationError({
                "purchase_order": (
                    "The purchase order must belong "
                    "to the invoice vendor."
                )
            })

        # Validate invoice line items.
        if items is not None:

            if not purchase_order:
                raise serializers.ValidationError({
                    "items": (
                        "A purchase order is required "
                        "when invoice line items are provided."
                    )
                })

            line_numbers = set()

            for item in items:

                po_item = item["purchase_order_item"]

                if po_item.purchase_order_id != purchase_order.id:
                    raise serializers.ValidationError({
                        "items": (
                            f"PO item {po_item.id} does not belong "
                            "to the selected purchase order."
                        )
                    })

                line_number = item["line_number"]

                if line_number in line_numbers:
                    raise serializers.ValidationError({
                        "items": (
                            "Invoice line numbers must be unique."
                        )
                    })

                line_numbers.add(line_number)

        # Prevent changing the purchase order without updating
        # existing invoice line items.
        if (
            instance
            and "purchase_order" in attrs
            and "items" not in attrs
            and instance.items.exists()
            and (
                purchase_order is None
                or instance.purchase_order_id != purchase_order.id
            )
        ):
            raise serializers.ValidationError({
                "items": (
                    "Provide updated invoice line items "
                    "when changing the purchase order."
                )
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):

        items_data = validated_data.pop("items", [])

        invoice = Invoice.objects.create(
            **validated_data
        )

        for item_data in items_data:
            InvoiceItem.objects.create(
                invoice=invoice,
                **item_data
            )

        return invoice

    @transaction.atomic
    def update(self, instance, validated_data):

        items_data = validated_data.pop("items", None)

        invoice = super().update(
            instance,
            validated_data
        )

        if items_data is not None:

            invoice.items.all().delete()

            for item_data in items_data:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    **item_data
                )

        return invoice


# ============================================================
# INVOICE DOCUMENT SERIALIZER (OCR UPLOAD)
# ============================================================

class InvoiceDocumentSerializer(serializers.ModelSerializer):

    file = serializers.FileField(write_only=True)

    created_by_username = serializers.CharField(
        source="created_by.username",
        read_only=True,
    )

    class Meta:
        model = InvoiceDocument

        fields = [
            "id",
            "file",
            "original_filename",
            "document_type",
            "processing_status",
            "extracted_text",
            "extracted_data",
            "error_message",
            "created_by",
            "created_by_username",
            "created_at",
            "processed_at",
            "source_document",
        ]

        read_only_fields = [
            "id",
            "original_filename",
            "document_type",
            "processing_status",
            "extracted_text",
            "error_message",
            "created_by",
            "created_by_username",
            "created_at",
            "processed_at",
            "source_document",
            "extracted_data",
        ]

    def validate_file(self, uploaded_file):

        max_size = 10 * 1024 * 1024  # 10 MB

        if uploaded_file.size == 0:
            raise serializers.ValidationError(
                "The uploaded file is empty."
            )

        if uploaded_file.size > max_size:
            raise serializers.ValidationError(
                "File size must not exceed 10 MB."
            )

        extension = Path(
            uploaded_file.name
        ).suffix.lower()

        supported_extensions = {
            ".pdf": "PDF",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
        }

        if extension not in supported_extensions:
            raise serializers.ValidationError(
                "Only PDF, JPG, JPEG, and PNG files are supported."
            )

        expected_type = supported_extensions[extension]

        try:
            uploaded_file.seek(0)

            if expected_type == "PDF":

                signature = uploaded_file.read(5)
                uploaded_file.seek(0)

                if signature != b"%PDF-":
                    raise serializers.ValidationError(
                        "The file does not have a valid PDF signature."
                    )

                content = uploaded_file.read()
                uploaded_file.seek(0)

                with pymupdf.open(
                    stream=content,
                    filetype="pdf",
                ) as pdf:

                    if len(pdf) == 0:
                        raise serializers.ValidationError(
                            "The PDF contains no pages."
                        )

                    if len(pdf) > 30:
                        raise serializers.ValidationError(
                            "PDFs must contain no more than 30 pages."
                        )

            else:

                with Image.open(uploaded_file) as image:

                    actual_format = image.format

                    expected_image_format = {
                        "JPEG": "JPEG",
                        "PNG": "PNG",
                    }[expected_type]

                    if actual_format != expected_image_format:
                        raise serializers.ValidationError(
                            "The file extension does not match "
                            "the image format."
                        )

                    image.verify()

        except serializers.ValidationError:
            raise

        except Exception as exc:
            raise serializers.ValidationError(
                "The file is invalid, corrupted, or unreadable."
            ) from exc

        finally:
            uploaded_file.seek(0)

        return uploaded_file

    def create(self, validated_data):

        uploaded_file = validated_data["file"]
        request = self.context["request"]

        extension = Path(
            uploaded_file.name
        ).suffix.lower()

        document_type = {
            ".pdf": "PDF",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
        }[extension]

        document = InvoiceDocument.objects.create(
            file=uploaded_file,
            original_filename=Path(
                uploaded_file.name
            ).name[:255],
            document_type=document_type,
            created_by=request.user,
        )

        return document
