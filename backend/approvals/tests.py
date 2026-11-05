
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import User
from vendors.models import Vendor
from purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from goods_receipts.models import GoodsReceipt, GoodsReceiptItem
from invoices.models import Invoice, InvoiceItem

from approvals.models import (
    ApprovalRule,
    ApprovalRequest,
    ApprovalStep,
    ApprovalHistory,
)

from approvals.services.workflow import (
    submit_invoice_for_approval,
    approve_step,
    reject_step,
)


class ApprovalWorkflowTests(APITestCase):

    def setUp(self):
        # Create submitter.
        self.submitter = User.objects.create_user(
            username="ap_submitter",
            password="TestPassword123!",
            role="AP_CLERK",
        )

        # Create approvers.
        self.approver = User.objects.create_user(
            username="level1_approver",
            password="TestPassword123!",
            role="APPROVER",
        )

        self.finance_manager = User.objects.create_user(
            username="level2_manager",
            password="TestPassword123!",
            role="FINANCE_MANAGER",
        )

        self.other_user = User.objects.create_user(
            username="other_user",
            password="TestPassword123!",
            role="APPROVER",
        )

        self.admin = User.objects.create_user(
            username="approval_admin",
            password="TestPassword123!",
            role="ADMIN",
        )

        # Create vendor.
        self.vendor = Vendor.objects.create(
            vendor_code="APPROVAL-V001",
            legal_name="Approval Test Technologies",
            gstin="29ABCDE1234F1Z5",
            address_line1="100 Test Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            created_by=self.submitter,
        )

        # Create issued purchase order.
        self.purchase_order = PurchaseOrder.objects.create(
            po_number="PO-APPROVAL-001",
            vendor=self.vendor,
            order_date=date.today(),
            currency="INR",
            status=PurchaseOrder.Status.ISSUED,
            created_by=self.submitter,
        )

        # Create purchase order item.
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            line_number=1,
            item_code="LAPTOP-001",
            description="Laptop",
            quantity=Decimal("10.000"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("18.00"),
        )

        # Create accepted goods receipt.
        self.grn = GoodsReceipt.objects.create(
            grn_number="GRN-APPROVAL-001",
            purchase_order=self.purchase_order,
            received_date=date.today(),
            status=GoodsReceipt.Status.ACCEPTED,
            received_by=self.submitter,
        )

        GoodsReceiptItem.objects.create(
            goods_receipt=self.grn,
            purchase_order_item=self.po_item,
            received_quantity=Decimal("10.000"),
            accepted_quantity=Decimal("10.000"),
            rejected_quantity=Decimal("0.000"),
        )

        # Create approval rules.
        self.level1_rule = ApprovalRule.objects.create(
            name="Level 1 - Department Approval",
            currency="INR",
            minimum_amount=Decimal("0.00"),
            approval_level=1,
            approver_role="APPROVER",
            assigned_approver=self.approver,
            created_by=self.admin,
        )

        self.level2_rule = ApprovalRule.objects.create(
            name="Level 2 - Finance Approval",
            currency="INR",
            minimum_amount=Decimal("500.00"),
            approval_level=2,
            approver_role="FINANCE_MANAGER",
            assigned_approver=self.finance_manager,
            created_by=self.admin,
        )

    def create_invoice(
        self,
        invoice_number="INV-APPROVAL-001",
        quantity=Decimal("5.000"),
        status_value=Invoice.Status.PENDING_REVIEW,
    ):
        unit_price = Decimal("100.00")
        tax_rate = Decimal("18.00")

        subtotal = (quantity * unit_price).quantize(
            Decimal("0.01")
        )

        tax_amount = (
            subtotal * tax_rate / Decimal("100")
        ).quantize(Decimal("0.01"))

        total_amount = subtotal + tax_amount

        invoice = Invoice.objects.create(
            vendor=self.vendor,
            purchase_order=self.purchase_order,
            invoice_number=invoice_number,
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            currency="INR",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            status=status_value,
            created_by=self.submitter,
        )

        InvoiceItem.objects.create(
            invoice=invoice,
            purchase_order_item=self.po_item,
            line_number=1,
            description="Laptop",
            quantity=quantity,
            unit_price=unit_price,
            tax_rate=tax_rate,
        )

        return invoice

    def submit_invoice(self, invoice):
        return submit_invoice_for_approval(
            invoice_id=invoice.id,
            submitted_by=self.submitter,
        )

    def test_submit_matched_invoice_for_approval(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            approval_request.status,
            ApprovalRequest.Status.PENDING,
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.APPROVAL_PENDING,
        )

        self.assertEqual(
            approval_request.steps.count(),
            2,
        )

        self.assertEqual(
            approval_request.history.count(),
            1,
        )

        self.assertEqual(
            approval_request.history.first().action,
            ApprovalHistory.Action.SUBMITTED,
        )

    def test_approvers_are_assigned_correctly(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        second_step = approval_request.steps.get(
            approval_level=2
        )

        self.assertEqual(
            first_step.assigned_to,
            self.approver,
        )

        self.assertEqual(
            second_step.assigned_to,
            self.finance_manager,
        )

    def test_unmatched_invoice_cannot_be_submitted(self):
        # GRN accepts only 10 units; invoice requests 11.
        invoice = self.create_invoice(
            invoice_number="INV-UNMATCHED-001",
            quantity=Decimal("11.000"),
        )

        with self.assertRaises(ValidationError):
            self.submit_invoice(invoice)

        self.assertFalse(
            ApprovalRequest.objects.filter(
                invoice=invoice
            ).exists()
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            Invoice.Status.PENDING_REVIEW,
        )

    def test_invoice_with_wrong_status_cannot_be_submitted(self):
        invoice = self.create_invoice(
            invoice_number="INV-WRONG-STATUS",
            status_value=Invoice.Status.UPLOADED,
        )

        with self.assertRaises(ValidationError):
            self.submit_invoice(invoice)

        self.assertFalse(
            ApprovalRequest.objects.filter(
                invoice=invoice
            ).exists()
        )

    def test_duplicate_approval_request_is_prevented(self):
        invoice = self.create_invoice()

        self.submit_invoice(invoice)

        with self.assertRaises(ValidationError):
            self.submit_invoice(invoice)

        self.assertEqual(
            ApprovalRequest.objects.filter(
                invoice=invoice
            ).count(),
            1,
        )

    def test_later_level_cannot_approve_before_first_level(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        second_step = approval_request.steps.get(
            approval_level=2
        )

        with self.assertRaises(ValidationError):
            approve_step(
                step_id=second_step.id,
                actor=self.finance_manager,
                comments="Attempted early approval",
            )

        second_step.refresh_from_db()

        self.assertEqual(
            second_step.status,
            ApprovalStep.Status.PENDING,
        )

    def test_sequential_approval_completes_workflow(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        second_step = approval_request.steps.get(
            approval_level=2
        )

        # First-level approval.
        approve_step(
            step_id=first_step.id,
            actor=self.approver,
            comments="Department approval completed.",
        )

        approval_request.refresh_from_db()
        invoice.refresh_from_db()
        first_step.refresh_from_db()
        second_step.refresh_from_db()

        self.assertEqual(
            first_step.status,
            ApprovalStep.Status.APPROVED,
        )

        self.assertEqual(
            second_step.status,
            ApprovalStep.Status.PENDING,
        )

        self.assertEqual(
            approval_request.status,
            ApprovalRequest.Status.PENDING,
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.APPROVAL_PENDING,
        )

        # Second-level approval.
        approve_step(
            step_id=second_step.id,
            actor=self.finance_manager,
            comments="Finance approval completed.",
        )

        approval_request.refresh_from_db()
        invoice.refresh_from_db()
        second_step.refresh_from_db()

        self.assertEqual(
            second_step.status,
            ApprovalStep.Status.APPROVED,
        )

        self.assertEqual(
            approval_request.status,
            ApprovalRequest.Status.APPROVED,
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.APPROVED,
        )

        self.assertIsNotNone(
            approval_request.completed_at
        )

        self.assertEqual(
            approval_request.history.filter(
                action=ApprovalHistory.Action.APPROVED
            ).count(),
            2,
        )

    def test_rejection_skips_later_steps(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        second_step = approval_request.steps.get(
            approval_level=2
        )

        reject_step(
            step_id=first_step.id,
            actor=self.approver,
            comments="Invoice details are incorrect.",
        )

        approval_request.refresh_from_db()
        invoice.refresh_from_db()
        first_step.refresh_from_db()
        second_step.refresh_from_db()

        self.assertEqual(
            approval_request.status,
            ApprovalRequest.Status.REJECTED,
        )

        self.assertEqual(
            invoice.status,
            Invoice.Status.REJECTED,
        )

        self.assertEqual(
            first_step.status,
            ApprovalStep.Status.REJECTED,
        )

        self.assertEqual(
            second_step.status,
            ApprovalStep.Status.SKIPPED,
        )

        self.assertIsNotNone(
            approval_request.completed_at
        )

    def test_rejection_requires_comments(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        with self.assertRaises(ValidationError):
            reject_step(
                step_id=first_step.id,
                actor=self.approver,
                comments="   ",
            )

        first_step.refresh_from_db()

        self.assertEqual(
            first_step.status,
            ApprovalStep.Status.PENDING,
        )

    def test_unassigned_user_cannot_approve_step(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        with self.assertRaises(ValidationError):
            approve_step(
                step_id=first_step.id,
                actor=self.other_user,
                comments="Unauthorized approval",
            )

    def test_submitter_cannot_approve_own_invoice(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        # Simulate an incorrectly assigned step.
        first_step.assigned_to = self.submitter
        first_step.save(update_fields=["assigned_to"])

        with self.assertRaises(ValidationError):
            approve_step(
                step_id=first_step.id,
                actor=self.submitter,
                comments="Self approval attempt",
            )

    def test_approved_step_cannot_be_approved_again(self):
        invoice = self.create_invoice()

        approval_request = self.submit_invoice(invoice)

        first_step = approval_request.steps.get(
            approval_level=1
        )

        approve_step(
            step_id=first_step.id,
            actor=self.approver,
            comments="Approved.",
        )

        with self.assertRaises(ValidationError):
            approve_step(
                step_id=first_step.id,
                actor=self.approver,
                comments="Second approval attempt.",
            )


class ApprovalRuleAPITests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="rule_admin",
            password="TestPassword123!",
            role="ADMIN",
        )

        self.normal_user = User.objects.create_user(
            username="rule_clerk",
            password="TestPassword123!",
            role="AP_CLERK",
        )

        self.approver = User.objects.create_user(
            username="rule_approver",
            password="TestPassword123!",
            role="APPROVER",
        )

        self.client = APIClient()

    def test_admin_can_create_approval_rule(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/approval-rules/",
            {
                "name": "Department Approval",
                "currency": "INR",
                "minimum_amount": "0.00",
                "approval_level": 1,
                "approver_role": "APPROVER",
                "assigned_approver": self.approver.id,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        rule = ApprovalRule.objects.get(
            name="Department Approval"
        )

        self.assertEqual(rule.created_by, self.admin)

    def test_normal_user_cannot_create_approval_rule(self):
        self.client.force_authenticate(user=self.normal_user)

        response = self.client.post(
            "/api/approval-rules/",
            {
                "name": "Unauthorized Rule",
                "currency": "INR",
                "minimum_amount": "0.00",
                "approval_level": 1,
                "approver_role": "APPROVER",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertFalse(
            ApprovalRule.objects.filter(
                name="Unauthorized Rule"
            ).exists()
        )

    def test_assigned_user_must_have_correct_role(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            "/api/approval-rules/",
            {
                "name": "Invalid Assignment",
                "currency": "INR",
                "minimum_amount": "0.00",
                "approval_level": 1,
                "approver_role": "FINANCE_MANAGER",
                "assigned_approver": self.approver.id,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
