
import logging

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import (
    FormParser,
    MultiPartParser,
    JSONParser,
)
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from .models import Invoice, InvoiceDocument
from .serializers import (
    InvoiceSerializer,
    InvoiceDocumentSerializer,
)

from .services.processing import process_invoice_document
from .services.matching import match_invoice
from .services.validation import validate_invoice_data
from .services.duplicate import check_duplicate_invoice
from approvals.serializers import ApprovalRequestSerializer
from approvals.services.workflow import submit_invoice_for_approval

from vendors.models import Vendor
from purchase_orders.models import PurchaseOrder


logger = logging.getLogger(__name__)


class InvoicePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class InvoiceViewSet(viewsets.ModelViewSet):

    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "status",
        "vendor",
        "currency",
    ]

    search_fields = [
        "invoice_number",
        "vendor__legal_name",
    ]

    ordering_fields = [
        "invoice_date",
        "due_date",
        "total_amount",
        "created_at",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        return Invoice.objects.select_related(
            "vendor",
            "created_by",
            "source_document",
            "purchase_order",
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="match")
    def match(self, request, pk=None):

        invoice = self.get_object()

        try:
            result = match_invoice(invoice)

            return Response(result, status=status.HTTP_200_OK)

        except Exception:
            logger.exception(
                "Three-way matching failed for invoice ID %s",
                invoice.pk,
            )
            return Response(
                {"error": "An unexpected error occurred while matching the invoice."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="submit-for-approval")
    def submit_for_approval(self, request, pk=None):
        invoice = self.get_object()
        try:
            approval_request = submit_invoice_for_approval(
                invoice_id=invoice.id,
                submitted_by=request.user,
            )
        except DjangoValidationError as exc:
            detail = exc.messages[0] if exc.messages else "Invoice cannot be submitted for approval."
            raise ValidationError({"detail": detail}) from exc

        return Response(
            ApprovalRequestSerializer(approval_request).data,
            status=status.HTTP_201_CREATED,
        )

class InvoiceDocumentViewSet(viewsets.ModelViewSet):

    serializer_class = InvoiceDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    parser_classes = [
        MultiPartParser,
        FormParser,
        JSONParser,
    ]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_queryset(self):
        return InvoiceDocument.objects.filter(
            created_by=self.request.user
        ).select_related("created_by")

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document = serializer.save()

        document.processing_status = (
            InvoiceDocument.ProcessingStatus.PROCESSING
        )
        document.save(update_fields=["processing_status"])

        try:
            result = process_invoice_document(document)

            document.extracted_text = result["extracted_text"]
            document.extracted_data = result["extracted_data"]

            document.processing_status = (
                InvoiceDocument.ProcessingStatus.COMPLETED
            )
            document.error_message = ""

        except Exception:
            logger.exception(
                "Invoice processing failed for document ID %s",
                document.pk,
            )

            document.processing_status = (
                InvoiceDocument.ProcessingStatus.FAILED
            )
            document.error_message = (
                "Invoice processing failed. Check the document and server logs."
            )

        finally:
            document.processed_at = timezone.now()

            document.save(
                update_fields=[
                    "extracted_text",
                    "extracted_data",
                    "processing_status",
                    "error_message",
                    "processed_at",
                ]
            )

        output_serializer = self.get_serializer(document)

        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="create-invoice",
    )
    def create_invoice(self, request, pk=None):

        document = self.get_object()

        if (
            document.processing_status
            != InvoiceDocument.ProcessingStatus.COMPLETED
        ):
            return Response(
                {"error": "Document processing is not completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extracted_data = document.extracted_data or {}

        # Validate the invoice fields submitted by the user.
        serializer = InvoiceSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        vendor = validated["vendor"]

        # Validate the actual submitted values, not just the original OCR.
        validation_data = {
            "invoice_number": validated.get("invoice_number"),
            "invoice_date": validated.get("invoice_date"),
            "due_date": validated.get("due_date"),
            "vendor_name": vendor.legal_name,
            "gstin": extracted_data.get("gstin"),
            "po_number": extracted_data.get("po_number"),
            "currency": validated.get("currency"),
            "subtotal": validated.get("subtotal"),
            "tax_amount": validated.get("tax_amount", 0),
            "total_amount": validated.get("total_amount"),
        }

        validation_result = validate_invoice_data(validation_data)

        if not validation_result["is_valid"]:
            return Response(
                {
                    "error": "Invoice validation failed.",
                    "validation": validation_result,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        warnings = list(validation_result["warnings"])

        # Check selected vendor against OCR GSTIN.
        extracted_gstin = extracted_data.get("gstin")
        extracted_gstin = (
            str(extracted_gstin).strip().upper()
            if extracted_gstin else None
        )

        selected_gstin = (
            vendor.gstin.strip().upper()
            if vendor.gstin else None
        )

        vendor_match = extracted_data.get("vendor_match") or {}
        matched_vendor_id = vendor_match.get("vendor_id")

        if (
            extracted_gstin
            and selected_gstin
            and extracted_gstin != selected_gstin
        ):
            return Response(
                {
                    "error": "Selected vendor GSTIN does not match the invoice GSTIN.",
                    "extracted_gstin": extracted_gstin,
                    "selected_vendor_gstin": selected_gstin,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            matched_vendor_id
            and matched_vendor_id != vendor.id
        ):
            return Response(
                {
                    "error": (
                        "OCR identified a different vendor. "
                        "Please select the vendor matching the extracted GSTIN."
                    ),
                    "matched_vendor_id": matched_vendor_id,
                    "selected_vendor_id": vendor.id,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if extracted_gstin and not selected_gstin:
            warnings.append(
                "Selected vendor has no GSTIN registered. Manual verification is recommended."
            )

        # Resolve the purchase order from OCR or manual selection.
        extracted_po_number = extracted_data.get("po_number")
        selected_po = validated.get("purchase_order")

        purchase_order = None

        if extracted_po_number:
            matching_pos = PurchaseOrder.objects.filter(
                po_number__iexact=extracted_po_number.strip()
            )

            if matching_pos.count() > 1:
                return Response(
                    {"error": "The extracted purchase order number is ambiguous."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            purchase_order = matching_pos.first()

            if not purchase_order:
                return Response(
                    {
                        "error": "The extracted purchase order was not found.",
                        "po_number": extracted_po_number,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                selected_po
                and selected_po.id != purchase_order.id
            ):
                return Response(
                    {"error": "Selected purchase order does not match the extracted PO number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif selected_po:
            purchase_order = selected_po

        if purchase_order:

            if purchase_order.vendor_id != vendor.id:
                return Response(
                    {"error": "Purchase order belongs to a different vendor."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                purchase_order.currency.upper()
                != validated.get("currency", "INR").upper()
            ):
                return Response(
                    {"error": "Invoice currency does not match purchase order currency."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if purchase_order.status in [
                PurchaseOrder.Status.DRAFT,
                PurchaseOrder.Status.CANCELLED,
            ]:
                return Response(
                    {"error": "Cannot create an invoice against a draft or cancelled purchase order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Perform final checks and creation atomically.
        try:
            with transaction.atomic():

                locked_document = InvoiceDocument.objects.select_for_update().get(
                    pk=document.pk,
                    created_by=request.user,
                )

                if (
                    locked_document.processing_status
                    != InvoiceDocument.ProcessingStatus.COMPLETED
                ):
                    return Response(
                        {"error": "Document processing is not completed."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                existing_invoice = Invoice.objects.filter(
                    source_document=locked_document
                ).first()

                if existing_invoice:
                    return Response(
                        {
                            "error": "An invoice has already been created from this document.",
                            "invoice_id": existing_invoice.id,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                # Lock vendor to reduce concurrent duplicate creation.
                vendor = Vendor.objects.select_for_update().get(
                    pk=vendor.pk
                )

                duplicate_result = check_duplicate_invoice(
                    vendor,
                    validated["invoice_number"],
                )

                if duplicate_result["is_duplicate"]:
                    return Response(
                        {
                            "error": "Duplicate invoice detected.",
                            "duplicate_check": duplicate_result,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                if purchase_order:
                    purchase_order = PurchaseOrder.objects.select_for_update().get(
                        pk=purchase_order.pk
                    )

                invoice = serializer.save(
                    created_by=request.user,
                    source_document=locked_document,
                    document=locked_document.file.name,
                    purchase_order=purchase_order,
                    status=Invoice.Status.PENDING_REVIEW,
                )

        except IntegrityError:
            return Response(
                {
                    "error": (
                        "Duplicate invoice detected. "
                        "This vendor and invoice number may already exist."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "Invoice created successfully.",
                "invoice": InvoiceSerializer(invoice).data,
                "validation": {
                    "is_valid": True,
                    "errors": [],
                    "warnings": warnings,
                },
                "purchase_order": (
                    purchase_order.po_number
                    if purchase_order else None
                ),
            },
            status=status.HTTP_201_CREATED,
        )
