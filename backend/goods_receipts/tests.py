
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from vendors.models import Vendor
from purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from .models import GoodsReceipt, GoodsReceiptItem

User = get_user_model()


class GoodsReceiptModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="grn_tester",
            password="TestPassword123!"
        )

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

        cls.po = PurchaseOrder.objects.create(
            po_number="PO-GRN-001",
            vendor=cls.vendor,
            order_date=date(2026, 11, 1),
            created_by=cls.user
        )

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
        self.assertEqual(grn.status, GoodsReceipt.Status.DRAFT)

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


class GoodsReceiptBusinessRuleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="grn_api_tester",
            password="TestPassword123!"
        )

        cls.vendor = Vendor.objects.create(
            vendor_code="TEST-G002",
            legal_name="GRN API Vendor",
            gstin="29ABCDE1234F2Z5",
            address_line1="789 Test Street",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560002",
            created_by=cls.user
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.po = PurchaseOrder.objects.create(
            po_number="PO-API-001",
            vendor=self.vendor,
            order_date=date(2026, 11, 1),
            status=PurchaseOrder.Status.ISSUED,
            created_by=self.user
        )

        self.po_item = PurchaseOrderItem.objects.create(
            purchase_order=self.po,
            line_number=1,
            description="Laptop",
            quantity=100,
            unit_price=50000,
            tax_rate=18
        )

    def create_grn(self, grn_number, quantity, po=None, po_item=None):
        po = po or self.po
        po_item = po_item or self.po_item

        return self.client.post(
            "/api/goods-receipts/",
            {
                "grn_number": grn_number,
                "purchase_order": po.id,
                "received_date": "2026-11-04",
                "notes": "Test receipt",
                "items": [
                    {
                        "purchase_order_item": po_item.id,
                        "received_quantity": str(quantity),
                        "accepted_quantity": str(quantity),
                        "rejected_quantity": "0"
                    }
                ]
            },
            format="json"
        )

    def test_first_receipt_updates_po_to_partially_received(self):
        response = self.create_grn("GRN-API-001", 60)

        self.assertEqual(response.status_code, 201)

        self.po.refresh_from_db()
        self.assertEqual(
            self.po.status,
            PurchaseOrder.Status.PARTIALLY_RECEIVED
        )

    def test_second_receipt_updates_po_to_partially_received(self):
        first = self.create_grn("GRN-API-002", 60)
        second = self.create_grn("GRN-API-003", 30)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        self.po.refresh_from_db()
        self.assertEqual(
            self.po.status,
            PurchaseOrder.Status.PARTIALLY_RECEIVED
        )

    def test_final_receipt_updates_po_to_fully_received(self):
        first = self.create_grn("GRN-API-004", 60)
        second = self.create_grn("GRN-API-005", 30)
        third = self.create_grn("GRN-API-006", 10)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(third.status_code, 201)

        self.po.refresh_from_db()
        self.assertEqual(
            self.po.status,
            PurchaseOrder.Status.FULLY_RECEIVED
        )

    def test_over_receipt_is_rejected(self):
        first = self.create_grn("GRN-API-007", 90)
        second = self.create_grn("GRN-API-008", 15)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)

        self.po.refresh_from_db()
        self.assertEqual(
            self.po.status,
            PurchaseOrder.Status.PARTIALLY_RECEIVED
        )

    def test_draft_po_receipt_is_rejected(self):
        self.po.status = PurchaseOrder.Status.DRAFT
        self.po.save(update_fields=["status"])

        response = self.create_grn("GRN-API-009", 10)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_cancelled_po_receipt_is_rejected(self):
        self.po.status = PurchaseOrder.Status.CANCELLED
        self.po.save(update_fields=["status"])

        response = self.create_grn("GRN-API-010", 10)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(GoodsReceipt.objects.count(), 0)

    def test_item_from_another_po_is_rejected(self):
        another_po = PurchaseOrder.objects.create(
            po_number="PO-API-002",
            vendor=self.vendor,
            order_date=date(2026, 11, 1),
            status=PurchaseOrder.Status.ISSUED,
            created_by=self.user
        )

        another_item = PurchaseOrderItem.objects.create(
            purchase_order=another_po,
            line_number=1,
            description="Monitor",
            quantity=50,
            unit_price=10000,
            tax_rate=18
        )

        response = self.create_grn(
            "GRN-API-011",
            10,
            po=self.po,
            po_item=another_item
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(GoodsReceipt.objects.count(), 0)
