
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from vendors.models import Vendor
from invoices.models import Invoice
from payments.models import Payment, PaymentHistory


User = get_user_model()


class PaymentAPITests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            username="payment_admin",
            password="TestPass123!",
            role="ADMIN",
        )

        self.finance = User.objects.create_user(
            username="payment_finance",
            password="TestPass123!",
            role="FINANCE_MANAGER",
        )

        self.clerk = User.objects.create_user(
            username="payment_clerk",
            password="TestPass123!",
            role="AP_CLERK",
        )

        self.vendor = Vendor.objects.create(
            vendor_code="PAY-V001",
            legal_name="Payment Test Vendor",
            gstin="29ABCDE1234F1Z5",
            address_line1="Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            created_by=self.clerk,
        )

        self.invoice = Invoice.objects.create(
            vendor=self.vendor,
            invoice_number="PAY-INV-001",
            invoice_date="2026-10-01",
            due_date="2026-11-01",
            currency="INR",
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
            total_amount=Decimal("1180.00"),
            status="APPROVED",
            created_by=self.clerk,
        )

        self.client.force_authenticate(user=self.finance)

    def create_payment(self, reference="PAY-REF-001", amount="500.00"):
        return self.client.post(
            reverse("payment-list"),
            {
                "invoice": self.invoice.id,
                "payment_reference": reference,
                "amount": amount,
                "currency": "INR",
                "payment_method": "NEFT",
                "payment_date": "2026-11-04",
            },
            format="json",
        )

    def test_finance_manager_can_create_payment(self):
        response = self.create_payment()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(PaymentHistory.objects.count(), 1)

    def test_ap_clerk_cannot_create_payment(self):
        self.client.force_authenticate(user=self.clerk)

        response = self.create_payment()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Payment.objects.count(), 0)

    def test_payment_starts_as_pending(self):
        response = self.create_payment()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "PENDING")

    def test_payment_history_is_created(self):
        self.create_payment()

        history = PaymentHistory.objects.get()

        self.assertEqual(history.action, "CREATED")
        self.assertEqual(history.new_status, "PENDING")
        self.assertEqual(history.actor, self.finance)

    def test_pending_payment_can_move_to_processing(self):
        create_response = self.create_payment()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        payment_id = create_response.data["id"]

        response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "PROCESSING"},
            format="json",
        )

        print("\nPENDING TO PROCESSING RESPONSE:", response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Status update failed: {response.data}",
        )
        self.assertEqual(response.data["status"], "PROCESSING")

    def test_processing_payment_can_be_completed(self):
        create_response = self.create_payment()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        payment_id = create_response.data["id"]

        processing_response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "PROCESSING"},
            format="json",
        )

        print("\nPROCESSING RESPONSE:", processing_response.data)

        self.assertEqual(
            processing_response.status_code,
            status.HTTP_200_OK,
            msg=f"Could not move payment to processing: {processing_response.data}",
        )

        response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "COMPLETED"},
            format="json",
        )

        print("\nPROCESSING TO COMPLETED RESPONSE:", response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Payment completion failed: {response.data}",
        )
        self.assertEqual(response.data["status"], "COMPLETED")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAYMENT_PENDING")

    def test_full_payment_marks_invoice_paid(self):
        create_response = self.client.post(
            reverse("payment-list"),
            {
                "invoice": self.invoice.id,
                "payment_reference": "PAY-FULL-001",
                "amount": "1180.00",
                "currency": "INR",
                "payment_method": "NEFT",
                "payment_date": "2026-11-04",
            },
            format="json",
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Payment creation failed: {create_response.data}",
        )

        payment_id = create_response.data["id"]

        processing_response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "PROCESSING"},
            format="json",
        )

        print("\nFULL PAYMENT PROCESSING RESPONSE:", processing_response.data)

        self.assertEqual(
            processing_response.status_code,
            status.HTTP_200_OK,
            msg=f"Could not move payment to processing: {processing_response.data}",
        )

        response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "COMPLETED"},
            format="json",
        )

        print("\nFULL PAYMENT COMPLETION RESPONSE:", response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            msg=f"Full payment completion failed: {response.data}",
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

    def test_invalid_status_transition_is_rejected(self):
        create_response = self.create_payment()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        payment_id = create_response.data["id"]

        response = self.client.post(
            reverse("payment-update-status", kwargs={"pk": payment_id}),
            {"new_status": "COMPLETED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_history_endpoint(self):
        create_response = self.create_payment()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        payment_id = create_response.data["id"]

        response = self.client.get(
            reverse("payment-history", kwargs={"pk": payment_id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_payment_summary_endpoint(self):
        response = self.client.get(reverse("payment-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("completed_payment_total", response.data)
        self.assertIn("pending_payment_total", response.data)
        self.assertIn("failed_payment_total", response.data)
        self.assertIn("outstanding_total", response.data)
