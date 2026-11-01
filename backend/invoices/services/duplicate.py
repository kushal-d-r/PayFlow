
from invoices.models import Invoice


def check_duplicate_invoice(vendor, invoice_number):
    """
    Check whether the vendor has already submitted
    an invoice with the same invoice number.
    """

    if not vendor or not invoice_number:
        return {
            "is_duplicate": False,
            "message": "Vendor or invoice number is missing."
        }

    existing_invoice = Invoice.objects.filter(
        vendor=vendor,
        invoice_number__iexact=invoice_number.strip()
    ).first()

    if existing_invoice:
        return {
            "is_duplicate": True,
            "message": "Duplicate invoice detected.",
            "existing_invoice_id": existing_invoice.id,
            "existing_invoice_number": existing_invoice.invoice_number,
        }

    return {
        "is_duplicate": False,
        "message": "No duplicate invoice found."
    }
