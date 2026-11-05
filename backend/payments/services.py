
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from invoices.models import Invoice
from .models import Payment, PaymentHistory


@transaction.atomic
def create_payment(*, validated_data, recorded_by):

    invoice_id = validated_data["invoice"].id

    invoice = Invoice.objects.select_for_update().get(
        pk=invoice_id
    )

    if invoice.status not in [
        Invoice.Status.APPROVED,
        Invoice.Status.PAYMENT_PENDING,
    ]:
        raise ValidationError(
            "Only approved or payment-pending invoices can receive payments."
        )

    if validated_data["currency"] != invoice.currency:
        raise ValidationError(
            "Payment currency must match invoice currency."
        )

    amount = validated_data["amount"]

    if amount <= Decimal("0.00"):
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    payment_status = validated_data.get(
        "status",
        Payment.Status.PENDING
    )

    if payment_status == Payment.Status.COMPLETED:

        paid_amount = Payment.objects.filter(
            invoice=invoice,
            status=Payment.Status.COMPLETED
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        outstanding = invoice.total_amount - paid_amount

        if amount > outstanding:
            raise ValidationError(
                f"Payment exceeds outstanding balance of "
                f"{outstanding} {invoice.currency}."
            )

    payment = Payment.objects.create(
        **validated_data,
        recorded_by=recorded_by
    )

    PaymentHistory.objects.create(
        payment=payment,
        action=PaymentHistory.Action.CREATED,
        previous_status="",
        new_status=payment.status,
        actor=recorded_by,
        comments="Payment record created."
    )

    update_invoice_payment_status(invoice)

    return payment


@transaction.atomic
def update_invoice_payment_status(invoice):

    paid_amount = Payment.objects.filter(
        invoice=invoice,
        status=Payment.Status.COMPLETED
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    if paid_amount >= invoice.total_amount:
        invoice.status = Invoice.Status.PAID

    elif paid_amount > Decimal("0.00"):
        invoice.status = Invoice.Status.PAYMENT_PENDING

    else:
        invoice.status = Invoice.Status.APPROVED

    invoice.save(
        update_fields=["status", "updated_at"]
    )


@transaction.atomic
def update_payment_status(*, payment_id, new_status, actor, comments=""):

    payment = Payment.objects.select_for_update().get(
        pk=payment_id
    )

    invoice = Invoice.objects.select_for_update().get(
        pk=payment.invoice_id
    )

    allowed_transitions = {
        Payment.Status.PENDING: [
            Payment.Status.PROCESSING,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ],
        Payment.Status.PROCESSING: [
            Payment.Status.COMPLETED,
            Payment.Status.FAILED,
            Payment.Status.CANCELLED,
        ],
    }

    if new_status not in allowed_transitions.get(
        payment.status, []
    ):
        raise ValidationError(
            f"Cannot change payment from {payment.status} "
            f"to {new_status}."
        )

    if new_status == Payment.Status.COMPLETED:

        paid_amount = Payment.objects.filter(
            invoice=invoice,
            status=Payment.Status.COMPLETED
        ).exclude(
            pk=payment.pk
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        outstanding = invoice.total_amount - paid_amount

        if payment.amount > outstanding:
            raise ValidationError(
                f"Payment exceeds outstanding balance of "
                f"{outstanding} {invoice.currency}."
            )

    previous_status = payment.status

    payment.status = new_status

    payment.save(
        update_fields=["status", "updated_at"]
    )

    PaymentHistory.objects.create(
        payment=payment,
        action=PaymentHistory.Action.STATUS_CHANGED,
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        comments=comments
    )

    update_invoice_payment_status(invoice)

    return payment
