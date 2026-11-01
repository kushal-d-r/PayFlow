
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from vendors.models import Vendor
from .models import PurchaseOrder, PurchaseOrderItem

User = get_user_model()


class PurchaseOrderModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="po_tester",
            password="TestPassword123!"
        )

        # Adjust required fields if your Vendor model has
        # additional mandatory fields.
        cls.vendor = Vendor.objects.create(
            vendor_code="TEST-V001",
            legal_name="Test Vendor",
            gstin="29ABCDE1234F1Z5",
            address_line1="123 Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            created_by=cls.user
        )

    def test_create_purchase_order(self):
        po = PurchaseOrder.objects.create(
            po_number="PO-TEST-001",
            vendor=self.vendor,
            order_date=date(2026, 11, 1),
            created_by=self.user
        )

        self.assertEqual(po.po_number, "PO-TEST-001")
        self.assertEqual(po.status, PurchaseOrder.Status.DRAFT)

    def test_create_purchase_order_item(self):
        po = PurchaseOrder.objects.create(
            po_number="PO-TEST-002",
            vendor=self.vendor,
            order_date=date(2026, 11, 1),
            created_by=self.user
        )

        item = PurchaseOrderItem.objects.create(
            purchase_order=po,
            line_number=1,
            description="Laptop",
            quantity=10,
            unit_price=50000,
            tax_rate=18
        )

        self.assertEqual(item.subtotal, 500000)
        self.assertEqual(item.tax_amount, 90000)
        self.assertEqual(item.total_amount, 590000)
