
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from approvals.models import (
    ApprovalRule,
    ApprovalRequest,
    ApprovalStep,
    ApprovalHistory,
)
from invoices.models import Invoice
from invoices.services.matching import match_invoice


User = get_user_model()


def _get_approver(rule, submitter):
    """
    Resolve the user responsible for an approval rule.

    Prefer the explicitly assigned user. Otherwise, select an
    active user with the configured role.
    """

    if rule.assigned_approver_id:
        approver = rule.assigned_approver

        if not approver.is_active:
            raise ValidationError(
                f"The assigned approver for '{rule.name}' is inactive."
            )

        if approver.role not in [rule.approver_role, "ADMIN"]:
            raise ValidationError(
                f"The assigned user for '{rule.name}' does not have "
                "the required role."
            )

        if approver.pk == submitter.pk and approver.role != "ADMIN":
            raise ValidationError(
                "A user cannot approve their own invoice."
            )

        return approver

    approver = (
        User.objects.filter(
            role=rule.approver_role,
            is_active=True,
        )
        .exclude(pk=submitter.pk)
        .order_by("id")
        .first()
    )

    if not approver:
        raise ValidationError(
            f"No active user is available with role "
            f"'{rule.approver_role}' for rule '{rule.name}'."
        )

    return approver


@transaction.atomic
def submit_invoice_for_approval(invoice_id, submitted_by):
    """
    Submit a successfully matched invoice for approval.

    Every active rule whose minimum amount is less than or
    equal to the invoice amount is included.
    """

    # Lock only the Invoice row. This avoids PostgreSQL errors
    # caused by locking nullable joined tables.
    invoice = (
        Invoice.objects.select_for_update(of=("self",))
        .select_related("vendor", "purchase_order")
        .get(pk=invoice_id)
    )

    if invoice.status != Invoice.Status.PENDING_REVIEW:
        raise ValidationError(
            "Only invoices with PENDING_REVIEW status can be submitted."
        )

    if ApprovalRequest.objects.filter(invoice=invoice).exists():
        raise ValidationError(
            "An approval request already exists for this invoice."
        )

    # Three-way matching must succeed before approval submission.
    matching_result = match_invoice(invoice)

    if matching_result.get("status") != "MATCHED":
        raise ValidationError(
            "Invoice cannot be submitted because three-way "
            "matching did not pass. Please resolve the matching exceptions first."
        )

    rules = list(
        ApprovalRule.objects.filter(
            currency=invoice.currency,
            minimum_amount__lte=invoice.total_amount,
            is_active=True,
        )
        .select_related("assigned_approver")
        .order_by("approval_level")
    )

    if not rules:
        raise ValidationError(
            f"No active approval rules are configured for "
            f"{invoice.currency} and this invoice amount."
        )

    # Ensure approval levels are sequential, starting at level 1.
    expected_levels = list(range(1, len(rules) + 1))
    actual_levels = [rule.approval_level for rule in rules]

    if actual_levels != expected_levels:
        raise ValidationError(
            "Approval rules must have continuous levels starting at 1."
        )

    # Resolve all approvers before creating the request.
    assignments = [
        (rule, _get_approver(rule, submitted_by))
        for rule in rules
    ]

    approval_request = ApprovalRequest.objects.create(
        invoice=invoice,
        status=ApprovalRequest.Status.PENDING,
        amount_snapshot=invoice.total_amount,
        currency_snapshot=invoice.currency,
        submitted_by=submitted_by,
    )

    for rule, approver in assignments:
        ApprovalStep.objects.create(
            approval_request=approval_request,
            rule=rule,
            approval_level=rule.approval_level,
            approver_role=rule.approver_role,
            assigned_to=approver,
            status=ApprovalStep.Status.PENDING,
        )

    invoice.status = Invoice.Status.APPROVAL_PENDING
    invoice.save(update_fields=["status", "updated_at"])

    ApprovalHistory.objects.create(
        approval_request=approval_request,
        actor=submitted_by,
        action=ApprovalHistory.Action.SUBMITTED,
        comments="Invoice submitted for approval.",
    )

    return approval_request


@transaction.atomic
def approve_step(step_id, actor, comments=""):
    """
    Approve the current pending approval step.

    Only the lowest pending approval level can be approved.
    """

    # Lock only the ApprovalStep row, not nullable joined tables.
    step = (
        ApprovalStep.objects.select_for_update(of=("self",))
        .select_related(
            "approval_request",
            "approval_request__invoice",
            "assigned_to",
        )
        .get(pk=step_id)
    )

    approval_request = (
        ApprovalRequest.objects.select_for_update()
        .get(pk=step.approval_request_id)
    )

    invoice = (
        Invoice.objects.select_for_update()
        .get(pk=approval_request.invoice_id)
    )

    if approval_request.status != ApprovalRequest.Status.PENDING:
        raise ValidationError("This approval request is not pending.")

    if step.status != ApprovalStep.Status.PENDING:
        raise ValidationError("This approval step is not pending.")

    current_step = (
        approval_request.steps.filter(
            status=ApprovalStep.Status.PENDING
        )
        .order_by("approval_level")
        .first()
    )

    if not current_step or current_step.pk != step.pk:
        raise ValidationError(
            "You cannot approve this step before earlier levels."
        )

    if step.assigned_to_id:
        if step.assigned_to_id != actor.pk and actor.role != "ADMIN":
            raise ValidationError(
                "You are not assigned to this approval step."
            )
    elif actor.role not in [step.approver_role, "ADMIN"]:
        raise ValidationError(
            "You do not have the required approver role."
        )

    if (
        approval_request.submitted_by_id == actor.pk
        and actor.role != "ADMIN"
    ):
        raise ValidationError(
            "You cannot approve your own invoice."
        )

    step.status = ApprovalStep.Status.APPROVED
    step.comments = comments
    step.acted_at = timezone.now()
    step.save(update_fields=["status", "comments", "acted_at"])

    ApprovalHistory.objects.create(
        approval_request=approval_request,
        step=step,
        actor=actor,
        action=ApprovalHistory.Action.APPROVED,
        comments=comments,
    )

    remaining_steps = approval_request.steps.filter(
        status=ApprovalStep.Status.PENDING
    ).exists()

    if not remaining_steps:
        approval_request.status = ApprovalRequest.Status.APPROVED
        approval_request.completed_at = timezone.now()
        approval_request.save(
            update_fields=["status", "completed_at", "updated_at"]
        )

        invoice.status = Invoice.Status.APPROVED
        invoice.save(update_fields=["status", "updated_at"])

    return approval_request


@transaction.atomic
def reject_step(step_id, actor, comments):
    """
    Reject the current pending approval step.

    Rejection requires a comment and skips all later steps.
    """

    if not comments or not comments.strip():
        raise ValidationError(
            "A rejection comment is required."
        )

    # Lock only the ApprovalStep row.
    step = (
        ApprovalStep.objects.select_for_update(of=("self",))
        .select_related("approval_request")
        .get(pk=step_id)
    )

    approval_request = (
        ApprovalRequest.objects.select_for_update()
        .get(pk=step.approval_request_id)
    )

    invoice = (
        Invoice.objects.select_for_update()
        .get(pk=approval_request.invoice_id)
    )

    if approval_request.status != ApprovalRequest.Status.PENDING:
        raise ValidationError("This approval request is not pending.")

    if step.status != ApprovalStep.Status.PENDING:
        raise ValidationError("This approval step is not pending.")

    current_step = (
        approval_request.steps.filter(
            status=ApprovalStep.Status.PENDING
        )
        .order_by("approval_level")
        .first()
    )

    if not current_step or current_step.pk != step.pk:
        raise ValidationError(
            "You cannot reject this step before earlier levels."
        )

    if step.assigned_to_id:
        if step.assigned_to_id != actor.pk and actor.role != "ADMIN":
            raise ValidationError(
                "You are not assigned to this approval step."
            )
    elif actor.role not in [step.approver_role, "ADMIN"]:
        raise ValidationError(
            "You do not have the required approver role."
        )

    if (
        approval_request.submitted_by_id == actor.pk
        and actor.role != "ADMIN"
    ):
        raise ValidationError(
            "You cannot reject your own invoice."
        )

    step.status = ApprovalStep.Status.REJECTED
    step.comments = comments.strip()
    step.acted_at = timezone.now()
    step.save(update_fields=["status", "comments", "acted_at"])

    # Skip every remaining pending approval step.
    approval_request.steps.filter(
        status=ApprovalStep.Status.PENDING
    ).update(
        status=ApprovalStep.Status.SKIPPED
    )

    approval_request.status = ApprovalRequest.Status.REJECTED
    approval_request.completed_at = timezone.now()
    approval_request.save(
        update_fields=["status", "completed_at", "updated_at"]
    )

    invoice.status = Invoice.Status.REJECTED
    invoice.save(update_fields=["status", "updated_at"])

    ApprovalHistory.objects.create(
        approval_request=approval_request,
        step=step,
        actor=actor,
        action=ApprovalHistory.Action.REJECTED,
        comments=comments.strip(),
    )

    return approval_request
