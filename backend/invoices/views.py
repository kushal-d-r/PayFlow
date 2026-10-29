import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Invoice, InvoiceDocument
from .serializers import InvoiceSerializer, InvoiceDocumentSerializer
from .services.ocr import extract_text_from_document


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

    filterset_fields = ["status", "vendor", "currency"]

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
        ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class InvoiceDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = InvoicePagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return InvoiceDocument.objects.select_related("created_by").all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        document.processing_status = InvoiceDocument.ProcessingStatus.PROCESSING
        document.save(update_fields=["processing_status"])

        try:
            extracted_text = extract_text_from_document(
                document.file.path,
                document.document_type,
            )
            document.extracted_text = extracted_text
            document.processing_status = (
                InvoiceDocument.ProcessingStatus.COMPLETED
            )
            document.error_message = ""
        except Exception:
            logger.exception(
                "OCR processing failed for invoice document ID %s",
                document.pk,
            )
            document.processing_status = (
                InvoiceDocument.ProcessingStatus.FAILED
            )
            document.error_message = (
                "OCR processing failed. Check that the document is valid "
                "and readable."
            )
        finally:
            document.processed_at = timezone.now()
            document.save(
                update_fields=[
                    "extracted_text",
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