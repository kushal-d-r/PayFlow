
from rest_framework import serializers

from .models import (
    ApprovalRule,
    ApprovalRequest,
    ApprovalStep,
    ApprovalHistory,
)
from invoices.serializers import InvoiceSerializer


class ApprovalRuleSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    assigned_approver_name = serializers.CharField(
        source="assigned_approver.username",
        read_only=True,
    )

    class Meta:
        model = ApprovalRule
        fields = [
            "id",
            "name",
            "currency",
            "minimum_amount",
            "approval_level",
            "approver_role",
            "assigned_approver",
            "assigned_approver_name",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate_currency(self, value):
        return value.upper()

    def validate(self, attrs):
        assigned_approver = attrs.get(
            "assigned_approver",
            getattr(self.instance, "assigned_approver", None),
        )

        approver_role = attrs.get(
            "approver_role",
            getattr(self.instance, "approver_role", None),
        )

        if assigned_approver and approver_role:
            if (
                assigned_approver.role != approver_role
                and assigned_approver.role != "ADMIN"
            ):
                raise serializers.ValidationError({
                    "assigned_approver": (
                        "The assigned user must have the configured "
                        "approver role or ADMIN role."
                    )
                })

        return attrs


class ApprovalStepSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(
        source="assigned_to.username",
        read_only=True,
    )

    rule_name = serializers.CharField(
        source="rule.name",
        read_only=True,
    )

    class Meta:
        model = ApprovalStep
        fields = [
            "id",
            "rule",
            "rule_name",
            "approval_level",
            "approver_role",
            "assigned_to",
            "assigned_to_name",
            "status",
            "comments",
            "acted_at",
            "created_at",
        ]
        read_only_fields = fields


class ApprovalHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(
        source="actor.username",
        read_only=True,
    )

    class Meta:
        model = ApprovalHistory
        fields = [
            "id",
            "step",
            "actor",
            "actor_name",
            "action",
            "comments",
            "created_at",
        ]
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.ModelSerializer):
    invoice_details = InvoiceSerializer(source="invoice", read_only=True)
    invoice_number = serializers.CharField(
        source="invoice.invoice_number",
        read_only=True,
    )

    submitted_by_name = serializers.CharField(
        source="submitted_by.username",
        read_only=True,
    )

    steps = ApprovalStepSerializer(many=True, read_only=True)
    history = ApprovalHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "invoice",
            "invoice_number",
            "invoice_details",
            "status",
            "amount_snapshot",
            "currency_snapshot",
            "submitted_by",
            "submitted_by_name",
            "submitted_at",
            "completed_at",
            "created_at",
            "updated_at",
            "steps",
            "history",
        ]
        read_only_fields = fields
