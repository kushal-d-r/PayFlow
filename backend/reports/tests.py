from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from invoices.models import Invoice
from vendors.models import Vendor


User = get_user_model()


class ReportSummaryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="report_user",
            password="TestPass123!",
            role="AP_CLERK",
        )
        self.vendor = Vendor.objects.create(
            vendor_code="RPT-V001",
            legal_name="Report Test Vendor",
            gstin="29ABCDE1234F1Z5",
            address_line1="Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            created_by=self.user,
        )
        self.client.force_authenticate(self.user)

    def create_invoice(self, number, due_date, status_value, currency="INR"):
        return Invoice.objects.create(
            vendor=self.vendor,
            invoice_number=number,
            invoice_date=timezone.localdate() - timedelta(days=45),
            due_date=due_date,
            currency=currency,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("18.00"),
            total_amount=Decimal("118.00"),
            status=status_value,
            created_by=self.user,
        )

    def test_summary_aggregates_all_invoices_and_overdue_buckets(self):
        today = timezone.localdate()
        self.create_invoice("RPT-OVERDUE", today - timedelta(days=40), Invoice.Status.APPROVED)
        self.create_invoice("RPT-CURRENT", today + timedelta(days=5), Invoice.Status.PENDING_REVIEW)
        self.create_invoice("RPT-PAID", today - timedelta(days=10), Invoice.Status.PAID)

        response = self.client.get(reverse("report-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["invoice_count"], 3)
        self.assertEqual(response.data["paid_invoice_count"], 1)
        self.assertEqual(response.data["exception_count"], 1)
        self.assertEqual(response.data["overdue_by_currency"][0]["count"], 1)
        self.assertEqual(response.data["overdue_by_currency"][0]["amount"], Decimal("118.00"))
        self.assertEqual(response.data["tax_by_currency"][0]["tax_amount"], Decimal("54.00"))

    def test_summary_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("report-summary"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summaries_keep_currency_totals_separate(self):
        today = timezone.localdate()
        self.create_invoice("RPT-INR", today + timedelta(days=2), Invoice.Status.APPROVED)
        self.create_invoice("RPT-USD", today + timedelta(days=2), Invoice.Status.APPROVED, currency="USD")

        response = self.client.get(reverse("report-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        aging = {row["currency"]: row["amount"] for row in response.data["aging"]}
        taxes = {row["currency"]: row["tax_amount"] for row in response.data["tax_by_currency"]}
        self.assertEqual(aging["INR"], Decimal("118.00"))
        self.assertEqual(aging["USD"], Decimal("118.00"))
        self.assertEqual(taxes["INR"], Decimal("18.00"))
        self.assertEqual(taxes["USD"], Decimal("18.00"))
