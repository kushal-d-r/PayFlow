
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import Invoice, InvoiceDocument
from .serializers import (
    InvoiceSerializer,
    InvoiceDocumentSerializer,
)

from .services.processing import process_invoice_document
from .services.matching import match_invoice


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

    @action(
        detail=True,
        methods=["post"],
        url_path="match",
    )
    def match(self, request, pk=None):
        """
        Perform three-way matching for an invoice.

        Compares:
        Invoice <-> Purchase Order <-> Goods Receipts
        """

        invoice = self.get_object()

        try:
            result = match_invoice(invoice)

            return Response(
                result,
                status=status.HTTP_200_OK,
            )

        except Exception:
            logger.exception(
                "Three-way matching failed for invoice ID %s",
                invoice.pk,
            )

            return Response(
                {
                    "error": (
                        "An unexpected error occurred "
                        "while matching the invoice."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InvoiceDocumentViewSet(viewsets.ModelViewSet):

    serializer_class = InvoiceDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination

    parser_classes = [
        MultiPartParser,
        FormParser,
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

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        document = serializer.save()

        document.processing_status = (
            InvoiceDocument.ProcessingStatus.PROCESSING
        )

        document.save(
            update_fields=["processing_status"]
        )

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
                "Invoice processing failed. "
                "Check the document and server logs."
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
                {
                    "error": "Document processing is not completed."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hasattr(document, "created_invoice"):
            return Response(
                {
                    "error": (
                        "An invoice has already been created "
                        "from this document."
                    ),
                    "invoice_id": document.created_invoice.id,
                },
                status=status.HTTP_409_CONFLICT,
            )

        serializer = InvoiceSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():

                invoice = serializer.save(
                    created_by=request.user,
                    source_document=document,
                    document=document.file.name,
                    status=Invoice.Status.PENDING_REVIEW,
                )

        except IntegrityError:
            return Response(
                {
                    "error": (
                        "Duplicate invoice detected. "
                        "This vendor and invoice number "
                        "may already exist."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "Invoice created successfully.",
                "invoice": InvoiceSerializer(invoice).data,
            },
            status=status.HTTP_201_CREATED,
        )
