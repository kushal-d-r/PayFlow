from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import User
from vendors.models import Vendor
from invoices.models import Invoice


class InvoiceAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="invoice_test_user",
            password="TestPassword!739",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.vendor = Vendor.objects.create(
            vendor_code="VEN-TEST-001",
            legal_name="Test Technologies Private Limited",
            gstin="29ABCDE1234F1Z5",
            pan="ABCDE1234F",
            contact_person="Test Contact",
            email="vendor@example.com",
            phone="9876543210",
            address_line1="100 Test Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            payment_terms_days=30,
            status=Vendor.Status.ACTIVE,
            created_by=self.user,
        )

        self.invoice_data = {
            "vendor": self.vendor.id,
            "invoice_number": "INV-TEST-001",
            "invoice_date": date.today().isoformat(),
            "due_date": (
                date.today() + timedelta(days=30)
            ).isoformat(),
            "currency": "INR",
            "subtotal": "1000.00",
            "tax_amount": "180.00",
            "total_amount": "1180.00",
            "status": "UPLOADED",
            "notes": "Automated API test",
        }

    def test_create_invoice(self):
        response = self.client.post(
            "/api/invoices/",
            self.invoice_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        invoice = Invoice.objects.get(
            invoice_number="INV-TEST-001"
        )

        self.assertEqual(invoice.vendor, self.vendor)
        self.assertEqual(invoice.created_by, self.user)
        self.assertEqual(invoice.total_amount, Decimal("1180.00"))

    def test_list_invoices(self):
        Invoice.objects.create(
            vendor=self.vendor,
            invoice_number="INV-LIST-001",
            invoice_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
            total_amount=Decimal("1180.00"),
            created_by=self.user,
        )

        response = self.client.get("/api/invoices/")

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_duplicate_invoice_number_for_same_vendor(self):
        first_response = self.client.post(
            "/api/invoices/",
            self.invoice_data,
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
            first_response.data,
        )

        duplicate_data = self.invoice_data.copy()

        response = self.client.post(
            "/api/invoices/",
            duplicate_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_due_date_before_invoice_date_is_rejected(self):
        invalid_data = self.invoice_data.copy()
        invalid_data["due_date"] = (
            date.today() - timedelta(days=1)
        ).isoformat()

        response = self.client.post(
            "/api/invoices/",
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(Invoice.objects.count(), 0)

    def test_total_less_than_subtotal_plus_tax_is_rejected(self):
        invalid_data = self.invoice_data.copy()
        invalid_data["total_amount"] = "1100.00"

        response = self.client.post(
            "/api/invoices/",
            invalid_data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(Invoice.objects.count(), 0)

    def test_unauthenticated_access_is_denied(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/invoices/")

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )