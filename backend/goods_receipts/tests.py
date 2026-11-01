
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from vendors.models import Vendor
from purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from .models import GoodsReceipt, GoodsReceiptItem

User = get_user_model()


class GoodsReceiptModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # 1. Create user first
        cls.user = User.objects.create_user(
            username="grn_tester",
            password="TestPassword123!"
        )

        # 2. Create vendor
        cls.vendor = Vendor.objects.create(
            vendor_code="TEST-G001",
            legal_name="GRN Test Vendor",
            gstin="29ABCDE1234F1Z5",
            address_line1="456 Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            created_by=cls.user
        )

        # 3. Create purchase order
        cls.po = PurchaseOrder.objects.create(
            po_number="PO-GRN-001",
            vendor=cls.vendor,
            order_date=date(2026, 11, 1),
            created_by=cls.user
        )

        # 4. Create purchase order item
        cls.po_item = PurchaseOrderItem.objects.create(
            purchase_order=cls.po,
            line_number=1,
            description="Laptop",
            quantity=10,
            unit_price=50000,
            tax_rate=18
        )

    def test_create_goods_receipt(self):
        grn = GoodsReceipt.objects.create(
            grn_number="GRN-TEST-001",
            purchase_order=self.po,
            received_date=date(2026, 11, 1),
            received_by=self.user
        )

        self.assertEqual(grn.grn_number, "GRN-TEST-001")
        self.assertEqual(
            grn.status,
            GoodsReceipt.Status.DRAFT
        )

    def test_create_goods_receipt_item(self):
        grn = GoodsReceipt.objects.create(
            grn_number="GRN-TEST-002",
            purchase_order=self.po,
            received_date=date(2026, 11, 1),
            received_by=self.user
        )

        item = GoodsReceiptItem.objects.create(
            goods_receipt=grn,
            purchase_order_item=self.po_item,
            received_quantity=6,
            accepted_quantity=5,
            rejected_quantity=1
        )

        self.assertEqual(item.received_quantity, 6)
        self.assertEqual(item.accepted_quantity, 5)
        self.assertEqual(item.rejected_quantity, 1)
