
from decimal import Decimal
from .models import Payment, PaymentHistory

from django.db.models import Sum
from rest_framework import serializers

from invoices.models import Invoice
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):

    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True
    )

    vendor_name = serializers.CharField(
        source="invoice.vendor.legal_name",
        read_only=True
    )

    recorded_by_username = serializers.CharField(
        source="recorded_by.username",
        read_only=True
    )

    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "vendor_name",
            "payment_reference",
            "amount",
            "currency",
            "payment_method",
            "transaction_id",
            "payment_date",
            "status",
            "notes",
            "recorded_by",
            "recorded_by_username",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "recorded_by",
            "status"
            "created_at",
            "updated_at",
        ]

    def validate_payment_reference(self, value):
        queryset = Payment.objects.filter(
            payment_reference=value
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "This payment reference already exists."
            )

        return value

    def validate(self, attrs):
        invoice = attrs.get(
            "invoice",
            self.instance.invoice if self.instance else None
        )

        amount = attrs.get(
            "amount",
            self.instance.amount if self.instance else None
        )

        currency = attrs.get(
            "currency",
            self.instance.currency if self.instance else None
        )

        status = attrs.get(
            "status",
            self.instance.status if self.instance
            else Payment.Status.PENDING
        )

        if invoice is None:
            return attrs

        if invoice.status not in [
            Invoice.Status.APPROVED,
            Invoice.Status.PAYMENT_PENDING,
            Invoice.Status.PAID,
        ]:
            raise serializers.ValidationError({
                "invoice": "Only approved invoices can receive payments."
            })

        if currency != invoice.currency:
            raise serializers.ValidationError({
                "currency": "Payment currency must match invoice currency."
            })

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({
                "amount": "Payment amount must be greater than zero."
            })

        # Only completed payments reduce the outstanding balance.
        if amount is not None and status == Payment.Status.COMPLETED:
            completed_payments = Payment.objects.filter(
                invoice=invoice,
                status=Payment.Status.COMPLETED
            )

            if self.instance:
                completed_payments = completed_payments.exclude(
                    pk=self.instance.pk
                )

            paid_amount = completed_payments.aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")

            outstanding = invoice.total_amount - paid_amount

            if amount > outstanding:
                raise serializers.ValidationError({
                    "amount": (
                        f"Payment exceeds outstanding balance "
                        f"of {outstanding} {invoice.currency}."
                    )
                })

        return attrs


class PaymentHistorySerializer(serializers.ModelSerializer):

    actor_username = serializers.CharField(
        source="actor.username",
        read_only=True
    )

    class Meta:
        model = PaymentHistory
        fields = [
            "id",
            "payment",
            "action",
            "previous_status",
            "new_status",
            "actor",
            "actor_username",
            "comments",
            "created_at",
        ]
        read_only_fields = fields