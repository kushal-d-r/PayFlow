
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def find_value(patterns, text):
    """Find the first matching value from a list of regex patterns."""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE
        )

        if match:
            return match.group(1).strip()

    return None


def clean_amount(value):
    """Convert formatted currency amounts into decimal strings."""

    if not value:
        return None

    value = re.sub(r"[₹,\s]", "", value)

    try:
        return str(Decimal(value))
    except InvalidOperation:
        return None


def normalize_date(value):
    """Convert common invoice date formats into YYYY-MM-DD."""

    if not value:
        return None

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value.strip(),
                date_format
            ).date().isoformat()
        except ValueError:
            continue

    return None


def extract_invoice_data(text):
    """Extract structured invoice fields from OCR text."""

    invoice_number = find_value(
        [
            r"Invoice\s*(?:No|Number|#)\s*[:\-]?\s*([A-Z0-9/-]+)",
            r"Bill\s*(?:No|Number)\s*[:\-]?\s*([A-Z0-9/-]+)",
        ],
        text
    )

    invoice_date = find_value(
        [
            r"Invoice\s*Date\s*[:\-]?\s*(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})",
            r"Date\s*[:\-]?\s*(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})",
        ],
        text
    )

    gstin = find_value(
        [
            r"GSTIN\s*[:\-]?\s*([0-9A-Z]{15})",
        ],
        text
    )

    vendor_name = find_value(
        [
            r"Vendor\s*Name\s*[:\-]?\s*(.+)",
            r"Supplier\s*Name\s*[:\-]?\s*(.+)",
        ],
        text
    )

    subtotal = find_value(
        [
            r"(?:Sub\s*Total|Subtotal|Taxable\s*Value)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        text
    )

    tax_amount = find_value(
        [
            r"(?:Total\s*Tax|Tax\s*Amount|GST\s*Amount)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        text
    )

    total_amount = find_value(
        [
            r"(?:Grand\s*Total|Total\s*Amount|Net\s*Amount|Invoice\s*Total)\s*[:\-]?\s*₹?\s*([\d,]+(?:\.\d{1,2})?)",
        ],
        text
    )

    return {
        "invoice_number": invoice_number,
        "invoice_date": normalize_date(invoice_date),
        "vendor_name": vendor_name,
        "gstin": gstin,
        "subtotal": clean_amount(subtotal),
        "tax_amount": clean_amount(tax_amount),
        "total_amount": clean_amount(total_amount),
    }
