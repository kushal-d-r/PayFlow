
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class ApproverRole(models.TextChoices):
    APPROVER = "APPROVER", "Approver"
    FINANCE_MANAGER = "FINANCE_MANAGER", "Finance Manager"
    ADMIN = "ADMIN", "Administrator"


class ApprovalRule(models.Model):
    """
    Defines which approval levels apply to an invoice.

    Example:
    Level 1: Minimum amount 0, Approver
    Level 2: Minimum amount 50000, Finance Manager

    An invoice of INR 75000 requires both levels.
    """

    name = models.CharField(max_length=100)

    currency = models.CharField(
        max_length=3,
        default="INR",
    )

    minimum_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    approval_level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )

    approver_role = models.CharField(
        max_length=30,
        choices=ApproverRole.choices,
    )

    assigned_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approval_rules",
    )

    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_approval_rules",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["currency", "approval_level"]

        constraints = [
            models.UniqueConstraint(
                fields=["currency", "approval_level"],
                name="unique_currency_approval_level",
            ),
            models.CheckConstraint(
                condition=Q(minimum_amount__gte=0),
                name="approval_rule_min_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(approval_level__gte=1),
                name="approval_rule_level_positive",
            ),
        ]

        indexes = [
            models.Index(fields=["currency", "is_active"]),
        ]

    def clean(self):
        super().clean()

        if self.assigned_approver_id:
            if (
                self.assigned_approver.role != self.approver_role
                and self.assigned_approver.role != ApproverRole.ADMIN
            ):
                raise ValidationError({
                    "assigned_approver": (
                        "Assigned user must have the configured "
                        "approver role or ADMIN role."
                    )
                })

    def __str__(self):
        return (
            f"{self.name} - Level {self.approval_level} "
            f"({self.approver_role})"
        )


class ApprovalRequest(models.Model):
    """
    Represents one invoice's approval workflow.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice = models.OneToOneField(
        "invoices.Invoice",
        on_delete=models.PROTECT,
        related_name="approval_request",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # Snapshot of the invoice amount and currency at submission.
    amount_snapshot = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    currency_snapshot = models.CharField(max_length=3)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_approval_requests",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]

        indexes = [
            models.Index(fields=["status", "submitted_at"]),
        ]

    def __str__(self):
        return (
            f"Approval for {self.invoice.invoice_number} "
            f"({self.status})"
        )


class ApprovalStep(models.Model):
    """
    Represents one level in an approval request.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SKIPPED = "SKIPPED", "Skipped"

    approval_request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    rule = models.ForeignKey(
        ApprovalRule,
        on_delete=models.PROTECT,
        related_name="approval_steps",
    )

    approval_level = models.PositiveSmallIntegerField()

    approver_role = models.CharField(
        max_length=30,
        choices=ApproverRole.choices,
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_approval_steps",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    comments = models.TextField(blank=True)

    acted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["approval_level"]

        constraints = [
            models.UniqueConstraint(
                fields=["approval_request", "approval_level"],
                name="unique_approval_request_level",
            ),
            models.CheckConstraint(
                condition=Q(approval_level__gte=1),
                name="approval_step_level_positive",
            ),
        ]

        indexes = [
            models.Index(fields=["assigned_to", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.approval_request.invoice.invoice_number} "
            f"- Level {self.approval_level} ({self.status})"
        )


class ApprovalHistory(models.Model):
    """
    Records every action performed during an approval workflow.
    """

    class Action(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        ASSIGNED = "ASSIGNED", "Assigned"
        REASSIGNED = "REASSIGNED", "Reassigned"

    approval_request = models.ForeignKey(
        ApprovalRequest,
        on_delete=models.CASCADE,
        related_name="history",
    )

    step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="history",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_history_actions",
    )

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
    )

    comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

        indexes = [
            models.Index(fields=["approval_request", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.approval_request.invoice.invoice_number} "
            f"- {self.action}"
        )
