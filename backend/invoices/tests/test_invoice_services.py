
from django.test import SimpleTestCase

from invoices.services.extraction import extract_invoice_data
from invoices.services.validation import validate_invoice_data


class InvoiceExtractionTests(SimpleTestCase):

    def test_extract_invoice_fields(self):
        text = """
        TAX INVOICE
        Invoice No: INV-2026-105
        Invoice Date: 25/10/2026
        Vendor Name: ABC Technologies Pvt Ltd
        GSTIN: 29ABCDE1234F1Z5
        Subtotal: 10000.00
        Tax Amount: 1800.00
        Grand Total: 11800.00
        """

        result = extract_invoice_data(text)

        self.assertEqual(
            result["invoice_number"],
            "INV-2026-105"
        )

        self.assertEqual(
            result["invoice_date"],
            "2026-10-25"
        )

        self.assertEqual(
            result["total_amount"],
            "11800.00"
        )

    def test_extracts_clear_table_line_item_candidates(self):
        result = extract_invoice_data("""
        1 | Laptop Pro | 2 | 50000.00 | 18% | 118000.00
        Subtotal: 100000.00
        """)
        self.assertEqual(len(result["line_items"]), 1)
        self.assertEqual(result["line_items"][0]["description"], "Laptop Pro")
        self.assertEqual(result["line_items"][0]["quantity"], "2")
        self.assertEqual(result["line_items"][0]["unit_price"], "50000.00")


class InvoiceValidationTests(SimpleTestCase):

    def test_valid_invoice(self):
        data = {
            "invoice_number": "INV-105",
            "invoice_date": "2026-10-25",
            "vendor_name": "ABC Technologies",
            "gstin": "29ABCDE1234F1Z5",
            "subtotal": "10000.00",
            "tax_amount": "1800.00",
            "total_amount": "11800.00",
        }

        result = validate_invoice_data(data)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_invalid_total_amount(self):
        data = {
            "invoice_number": "INV-105",
            "invoice_date": "2026-10-25",
            "vendor_name": "ABC Technologies",
            "gstin": "29ABCDE1234F1Z5",
            "subtotal": "10000.00",
            "tax_amount": "1800.00",
            "total_amount": "11000.00",
        }

        result = validate_invoice_data(data)

        self.assertFalse(result["is_valid"])
        self.assertTrue(result["errors"])
