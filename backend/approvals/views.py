
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    ApprovalRule,
    ApprovalRequest,
    ApprovalStep,
)

from .serializers import (
    ApprovalRuleSerializer,
    ApprovalRequestSerializer,
)

from .permissions import IsApprovalAdmin

from .services.workflow import (
    approve_step,
    reject_step,
)


class ApprovalRuleViewSet(viewsets.ModelViewSet):
    """
    Administrators can create, view, update and delete approval rules.
    """

    serializer_class = ApprovalRuleSerializer
    permission_classes = [IsAuthenticated, IsApprovalAdmin]

    queryset = ApprovalRule.objects.select_related(
        "assigned_approver",
        "created_by",
    ).all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ApprovalRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View approval requests and perform approval/rejection actions.
    """

    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = ApprovalRequest.objects.select_related(
            "invoice",
            "submitted_by",
        ).prefetch_related(
            "steps__rule",
            "steps__assigned_to",
            "history__actor",
        )

        if user.is_superuser or user.role == "ADMIN":
            return queryset

        return queryset.filter(
            Q(submitted_by=user) |
            Q(steps__assigned_to=user)
        ).distinct()

    @action(detail=False, methods=["get"])
    def inbox(self, request):
        """
        Return requests where the current user can act on
        the lowest pending approval level.
        """

        user = request.user

        pending_requests = self.get_queryset().filter(
            status=ApprovalRequest.Status.PENDING,
            steps__status=ApprovalStep.Status.PENDING,
        ).distinct()

        actionable_requests = []

        for approval_request in pending_requests:
            current_step = (
                approval_request.steps
                .filter(status=ApprovalStep.Status.PENDING)
                .order_by("approval_level")
                .first()
            )

            if not current_step:
                continue

            is_assigned = current_step.assigned_to_id == user.id

            is_admin = user.is_superuser or user.role == "ADMIN"

            if is_assigned or is_admin:
                actionable_requests.append(approval_request)

        serializer = self.get_serializer(
            actionable_requests,
            many=True,
        )

        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        approval_request = self.get_object()

        current_step = (
            approval_request.steps
            .filter(status=ApprovalStep.Status.PENDING)
            .order_by("approval_level")
            .first()
        )

        if not current_step:
            return Response(
                {"error": "No pending approval step exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comments = request.data.get("comments", "")

        try:
            result = approve_step(
                step_id=current_step.id,
                actor=request.user,
                comments=comments,
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else exc.messages
            )
            raise ValidationError(detail)

        result.refresh_from_db()

        return Response(
            ApprovalRequestSerializer(result).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        approval_request = self.get_object()

        current_step = (
            approval_request.steps
            .filter(status=ApprovalStep.Status.PENDING)
            .order_by("approval_level")
            .first()
        )

        if not current_step:
            return Response(
                {"error": "No pending approval step exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        comments = request.data.get("comments", "")

        try:
            result = reject_step(
                step_id=current_step.id,
                actor=request.user,
                comments=comments,
            )
        except DjangoValidationError as exc:
            detail = (
                exc.message_dict
                if hasattr(exc, "message_dict")
                else exc.messages
            )
            raise ValidationError(detail)

        result.refresh_from_db()

        return Response(
            ApprovalRequestSerializer(result).data,
            status=status.HTTP_200_OK,
        )
