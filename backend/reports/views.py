from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from approvals.models import ApprovalRequest, ApprovalStep
from invoices.models import Invoice
from payments.models import Payment
from vendors.models import Vendor


OPEN_INVOICE_STATUSES = [
    Invoice.Status.PENDING_REVIEW,
    Invoice.Status.APPROVAL_PENDING,
    Invoice.Status.APPROVED,
    Invoice.Status.PAYMENT_PENDING,
    Invoice.Status.EXCEPTION,
]


def _grouped(queryset, *fields):
    return list(
        queryset.values(*fields).annotate(
            count=Count("id"),
            amount=Sum("total_amount"),
        ).order_by(*fields)
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    """Return organization-wide AP aggregates from database records."""
    today = timezone.localdate()
    invoices = Invoice.objects.select_related("vendor")

    invoice_status = _grouped(
        invoices,
        "status",
        "currency",
    )
    tax_by_currency = list(
        invoices.values("currency").annotate(
            invoice_count=Count("id"),
            taxable_subtotal=Sum("subtotal"),
            tax_amount=Sum("tax_amount"),
            gross_total=Sum("total_amount"),
        ).order_by("currency")
    )

    overdue = invoices.filter(
        status__in=OPEN_INVOICE_STATUSES,
        due_date__lt=today,
    )
    overdue_by_currency = _grouped(overdue, "currency")

    aging_buckets = [
        ("CURRENT", Q(due_date__gte=today)),
        ("1_30_DAYS", Q(due_date__lt=today, due_date__gte=today - timedelta(days=30))),
        ("31_60_DAYS", Q(due_date__lt=today - timedelta(days=30), due_date__gte=today - timedelta(days=60))),
        ("61_90_DAYS", Q(due_date__lt=today - timedelta(days=60), due_date__gte=today - timedelta(days=90))),
        ("OVER_90_DAYS", Q(due_date__lt=today - timedelta(days=90))),
    ]
    aging = []
    open_invoices = invoices.filter(status__in=OPEN_INVOICE_STATUSES)
    for bucket, condition in aging_buckets:
        groups = open_invoices.filter(condition).values("currency").annotate(
            count=Count("id"),
            amount=Sum("total_amount"),
        ).order_by("currency")
        aging.extend({"bucket": bucket, **group} for group in groups)

    vendor_totals = list(
        invoices.values("vendor_id", "vendor__legal_name", "currency").annotate(
            invoice_count=Count("id"),
            total_amount=Sum("total_amount"),
        ).order_by("-total_amount", "vendor__legal_name")
    )

    exceptions = list(
        invoices.filter(
            status__in=[Invoice.Status.EXCEPTION, Invoice.Status.PENDING_REVIEW]
        ).order_by("due_date", "invoice_number").values(
            "id",
            "invoice_number",
            "vendor__legal_name",
            "status",
            "invoice_date",
            "due_date",
            "currency",
            "subtotal",
            "tax_amount",
            "total_amount",
            "notes",
        )
    )

    pending_requests = ApprovalRequest.objects.filter(
        status=ApprovalRequest.Status.PENDING,
        steps__status=ApprovalStep.Status.PENDING,
    ).prefetch_related("steps").distinct()
    is_admin = request.user.is_superuser or request.user.role == "ADMIN"
    pending_approval_count = 0
    for approval_request in pending_requests:
        current_step = next(
            (step for step in approval_request.steps.all() if step.status == ApprovalStep.Status.PENDING),
            None,
        )
        is_assigned_to_role = (
            current_step
            and current_step.assigned_to_id is None
            and current_step.approver_role == request.user.role
        )
        if current_step and (
            is_admin
            or current_step.assigned_to_id == request.user.id
            or is_assigned_to_role
        ):
            pending_approval_count += 1

    payments_by_currency = list(
        Payment.objects.values("currency", "status").annotate(
            payment_count=Count("id"),
            amount=Sum("amount"),
        ).order_by("currency", "status")
    )

    return Response({
        "as_of": today.isoformat(),
        "invoice_count": invoices.count(),
        "vendor_count": Vendor.objects.count(),
        "invoice_status": invoice_status,
        "aging": aging,
        "overdue_by_currency": overdue_by_currency,
        "exception_count": invoices.filter(
            status__in=[Invoice.Status.EXCEPTION, Invoice.Status.PENDING_REVIEW]
        ).count(),
        "exceptions": exceptions,
        "pending_approval_count": pending_approval_count,
        "paid_invoice_count": invoices.filter(status=Invoice.Status.PAID).count(),
        "tax_by_currency": tax_by_currency,
        "vendor_totals": vendor_totals,
        "payments_by_currency": payments_by_currency,
        "recent_invoices": list(invoices.order_by("-created_at").values(
            "id",
            "invoice_number",
            "vendor__legal_name",
            "invoice_date",
            "due_date",
            "currency",
            "total_amount",
            "status",
            "created_at",
        )[:5]),
    })
