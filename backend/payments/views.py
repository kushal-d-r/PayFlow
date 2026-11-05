
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from invoices.models import Invoice
from .models import Payment, PaymentHistory
from .serializers import PaymentSerializer, PaymentHistorySerializer
from .services import create_payment, update_payment_status


class PaymentViewSet(viewsets.ModelViewSet):

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "head",
        "options",
    ]

    def get_queryset(self):
        user = self.request.user

        queryset = Payment.objects.select_related(
            "invoice",
            "invoice__vendor",
            "recorded_by",
        )

        # Finance, administrators and auditors can view all payments.
        if user.is_superuser or user.role in [
            "ADMIN",
            "FINANCE_MANAGER",
            "AUDITOR",
        ]:
            return queryset

        # Other users can view payments for their own invoices.
        return queryset.filter(
            invoice__created_by=user
        )

    # --------------------------------------------------
    # CREATE PAYMENT
    # --------------------------------------------------

    def create(self, request, *args, **kwargs):

        user = request.user

        if not (
            user.is_superuser
            or user.role in ["ADMIN", "FINANCE_MANAGER"]
        ):
            raise PermissionDenied(
                "Only finance managers and administrators "
                "can record payments."
            )

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        try:
            payment = create_payment(
                validated_data=serializer.validated_data,
                recorded_by=user,
            )

        except ValidationError as exc:
            raise serializers.ValidationError(
                exc.messages
            )

        output = self.get_serializer(payment)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    # --------------------------------------------------
    # PAYMENT HISTORY
    # --------------------------------------------------

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):

        payment = self.get_object()

        history_records = PaymentHistory.objects.filter(
            payment=payment
        ).select_related(
            "actor",
            "payment",
        )

        serializer = PaymentHistorySerializer(
            history_records,
            many=True,
        )

        return Response(serializer.data)

    # --------------------------------------------------
    # PAYMENT SUMMARY
    # --------------------------------------------------

    @action(detail=False, methods=["get"])
    def summary(self, request):

        payments = self.get_queryset()

        completed_total = payments.filter(
            status=Payment.Status.COMPLETED
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        pending_total = payments.filter(
            status__in=[
                Payment.Status.PENDING,
                Payment.Status.PROCESSING,
            ]
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        failed_total = payments.filter(
            status=Payment.Status.FAILED
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        invoice_ids = payments.values_list(
            "invoice_id",
            flat=True,
        ).distinct()

        invoices = Invoice.objects.filter(
            id__in=invoice_ids,
            status__in=[
                Invoice.Status.APPROVED,
                Invoice.Status.PAYMENT_PENDING,
                Invoice.Status.PAID,
            ],
        )

        invoice_total = invoices.aggregate(
            total=Sum("total_amount")
        )["total"] or Decimal("0.00")

        outstanding_total = (
            invoice_total - completed_total
        )

        return Response({
            "completed_payment_total": completed_total,
            "pending_payment_total": pending_total,
            "failed_payment_total": failed_total,
            "outstanding_total": max(
                outstanding_total,
                Decimal("0.00"),
            ),
        })

    # --------------------------------------------------
    # UPDATE PAYMENT STATUS
    # --------------------------------------------------

    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None):

        user = request.user

        if not (
            user.is_superuser
            or user.role in ["ADMIN", "FINANCE_MANAGER"]
        ):
            raise PermissionDenied(
                "Only finance managers and administrators "
                "can update payment status."
            )

        # IMPORTANT: Read new_status from the request.
        new_status = request.data.get("new_status")
        comments = request.data.get("comments", "")

        if not new_status:
            return Response(
                {
                    "new_status": "This field is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_status not in Payment.Status.values:
            return Response(
                {
                    "new_status": "Invalid payment status."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = update_payment_status(
                payment_id=pk,
                new_status=new_status,
                actor=user,
                comments=comments,
            )

        except Payment.DoesNotExist:
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValidationError as exc:
            raise serializers.ValidationError(
                exc.messages
            )

        output = self.get_serializer(payment)

        return Response(
            output.data,
            status=status.HTTP_200_OK,
        )
