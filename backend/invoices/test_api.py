from datetime import date, timedelta
from decimal import Decimal
from purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from goods_receipts.models import GoodsReceipt, GoodsReceiptItem
from invoices.models import InvoiceItem
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
        
class InvoiceMatchingAPITests(APITestCase):

    def setUp(self):
        InvoiceAPITests.setUp(self)

        # Create purchase order.
        self.purchase_order = PurchaseOrder.objects.create(
            po_number="PO-MATCH-001",
            vendor=self.vendor,
            order_date=date.today(),
            currency="INR",
            status=PurchaseOrder.Status.ISSUED,
            notes="Matching test PO",
            created_by=self.user,
        )

        # Create purchase order item.
        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.purchase_order,
            line_number=1,
            item_code="ITEM-001",
            description="Laptop",
            quantity=Decimal("10.000"),
            unit_price=Decimal("100.00"),
            tax_rate=Decimal("18.00"),
        )

        # Create accepted goods receipt.
        self.grn = GoodsReceipt.objects.create(
            grn_number="GRN-MATCH-001",
            purchase_order=self.purchase_order,
            received_date=date.today(),
            status=GoodsReceipt.Status.ACCEPTED,
            received_by=self.user,
        )

        GoodsReceiptItem.objects.create(
            goods_receipt=self.grn,
            purchase_order_item=self.po_item,
            received_quantity=Decimal("10.000"),
            accepted_quantity=Decimal("10.000"),
            rejected_quantity=Decimal("0.000"),
        )

    def create_invoice(
        self,
        invoice_number,
        quantity=Decimal("5.000"),
        unit_price=Decimal("100.00"),
        tax_rate=Decimal("18.00"),
    ):
        subtotal = (
            quantity * unit_price
        ).quantize(Decimal("0.01"))

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
            created_by=self.user,
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

    def match_invoice(self, invoice):
        return self.client.post(
            f"/api/invoices/{invoice.id}/match/",
            {},
            format="json",
        )

    def test_successful_three_way_matching(self):
        invoice = self.create_invoice("INV-MATCH-001")

        response = self.match_invoice(invoice)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        self.assertEqual(
            response.data["status"],
            "MATCHED",
        )

        self.assertTrue(response.data["is_matched"])

    def test_insufficient_grn_quantity(self):
        # Only 4 units are accepted.
        self.grn.items.all().update(
            received_quantity=Decimal("4.000"),
            accepted_quantity=Decimal("4.000"),
        )

        invoice = self.create_invoice(
            "INV-MATCH-002",
            quantity=Decimal("5.000"),
        )

        response = self.match_invoice(invoice)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "EXCEPTION",
        )

        quantity_check = next(
            check
            for check in response.data["checks"]
            if check["check"] == "item_1_quantity"
        )

        self.assertFalse(quantity_check["passed"])

    def test_invoice_price_mismatch(self):
        invoice = self.create_invoice(
            "INV-MATCH-003",
            unit_price=Decimal("120.00"),
        )

        response = self.match_invoice(invoice)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "EXCEPTION",
        )

        price_check = next(
            check
            for check in response.data["checks"]
            if check["check"] == "item_1_price"
        )

        self.assertFalse(price_check["passed"])

    def test_invoice_tax_mismatch(self):
        invoice = self.create_invoice(
            "INV-MATCH-004",
            tax_rate=Decimal("12.00"),
        )

        response = self.match_invoice(invoice)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "EXCEPTION",
        )

        tax_check = next(
            check
            for check in response.data["checks"]
            if check["check"] == "item_1_tax"
        )

        self.assertFalse(tax_check["passed"])

    def test_duplicate_billing_is_detected(self):
        # First invoice consumes 7 accepted units.
        self.create_invoice(
            "INV-MATCH-005",
            quantity=Decimal("7.000"),
        )

        # Second invoice tries to consume 5 more units.
        invoice = self.create_invoice(
            "INV-MATCH-006",
            quantity=Decimal("5.000"),
        )

        response = self.match_invoice(invoice)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["status"],
            "EXCEPTION",
        )

        quantity_check = next(
            check
            for check in response.data["checks"]
            if check["check"] == "item_1_quantity"
        )

        self.assertFalse(quantity_check["passed"])

    def test_unauthenticated_matching_is_denied(self):
        invoice = self.create_invoice("INV-MATCH-007")

        self.client.force_authenticate(user=None)

        response = self.match_invoice(invoice)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )