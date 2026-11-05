
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


def find_value(patterns, text):
    """Find the first matching captured value."""
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group(1).strip()

    return None


def clean_amount(value):
    """Convert formatted currency amounts into decimal strings."""
    if not value:
        return None

    value = re.sub(r"[₹,\s]", "", value)
    value = re.sub(r"^(INR|USD|EUR|GBP)", "", value, flags=re.IGNORECASE)

    try:
        return str(Decimal(value))
    except InvalidOperation:
        return None


def normalize_date(value):
    """Normalize supported invoice date formats to YYYY-MM-DD."""
    if not value:
        return None

    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%b-%y",
        "%d-%B-%y",
    ]

    for date_format in formats:
        try:
            return datetime.strptime(
                value.strip(),
                date_format,
            ).date().isoformat()
        except ValueError:
            continue

    return None


def extract_vendor_name(text):
    """Extract a labelled vendor name or use the first invoice heading."""
    patterns = [
        r"(?:Vendor|Supplier)\s*Name\s*[:\-]?\s*([^\n]+)",
        r"(?:From)\s*[:\-]?\s*([^\n]+)",
    ]

    value = find_value(patterns, text)

    if value:
        return value.strip()

    ignored = {
        "TAX INVOICE",
        "INVOICE",
        "PURCHASE INVOICE",
    }

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.upper() in ignored:
            continue

        if re.search(r"\bGSTIN\b", line, re.IGNORECASE):
            continue

        if re.search(r"\b\d{5,6}\b", line):
            continue

        if "@" in line or "PHONE:" in line.upper():
            continue

        return line

    return None


def extract_labeled_amount(text, labels):
    """Extract an amount appearing on the same or next line."""
    label_pattern = "|".join(labels)

    pattern = (
        rf"(?:{label_pattern})\s*[:\-]?\s*"
        rf"(?:INR|USD|EUR|GBP|₹)?\s*"
        rf"([\d,]+(?:\.\d{{1,2}})?)"
    )

    return find_value([pattern], text)


def extract_invoice_line_items(text):
    """Extract conservative invoice rows when OCR preserves a table-like row.

    Accepted forms include pipe-delimited columns and rows containing
    `line description quantity unit-price tax% [line-total]`. Ambiguous rows
    are omitted so the reviewer can enter them against the selected PO.
    """
    line_items = []
    row_pattern = re.compile(
        r"^\s*(?P<line>\d{1,3})[.)]?\s+"
        r"(?P<description>.+?)\s+"
        r"(?P<quantity>\d+(?:\.\d{1,3})?)\s+"
        r"(?P<price>[\d,]+(?:\.\d{1,2})?)\s+"
        r"(?P<tax>\d{1,2}(?:\.\d{1,2})?)\s*%"
        r"(?:\s+[\d,]+(?:\.\d{1,2})?)?\s*$"
    )
    for raw_line in text.splitlines():
        line = raw_line.strip().strip("|").strip()
        if not line or re.search(r"description|quantity|unit price|amount", line, re.I):
            continue

        match = row_pattern.match(line)
        if not match and "|" in raw_line:
            cells = [cell.strip() for cell in raw_line.split("|") if cell.strip()]
            if len(cells) >= 5:
                normalized = " ".join(cells)
                match = row_pattern.match(normalized)
        if not match:
            continue

        values = match.groupdict()
        description = re.sub(r"\s+", " ", values["description"]).strip(" |-")
        if not description or description.upper() in {"SUBTOTAL", "TOTAL", "TAX"}:
            continue
        line_items.append({
            "line_number": int(values["line"]),
            "description": description,
            "quantity": values["quantity"],
            "unit_price": clean_amount(values["price"]),
            "tax_rate": values["tax"],
        })
    return line_items


def extract_invoice_data(text):

    # Invoice number
    invoice_number = find_value([
        r"Invoice\s*(?:No|Number|#)\s*[:\-]?\s*([A-Z0-9/-]+)",
        r"Bill\s*(?:No|Number)\s*[:\-]?\s*([A-Z0-9/-]+)",
    ], text)

    # Invoice date
    invoice_date = find_value([
        r"Invoice\s*Date\s*[:\-]?\s*"
        r"(\d{1,2}[-/\.][A-Za-z0-9]{1,3}[-/\.]\d{2,4})",
        r"Invoice\s*Date\s*[:\-]?\s*"
        r"(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})",
    ], text)

    # Due date
    due_date = find_value([
        r"Due\s*Date\s*[:\-]?\s*"
        r"(\d{1,2}[-/\.][A-Za-z0-9]{1,3}[-/\.]\d{2,4})",
        r"Due\s*Date\s*[:\-]?\s*"
        r"(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})",
    ], text)

    # GSTIN: first occurrence is treated as the supplier GSTIN.
    gstin = find_value([
        r"GSTIN\s*[:\-]?\s*([0-9A-Z]{15})",
    ], text)

    # Vendor name
    vendor_name = extract_vendor_name(text)

    # Purchase order number
    po_number = find_value([
        r"Purchase\s*Order\s*(?:Number|No|#)?\s*[:\-]?\s*"
        r"([A-Z0-9/-]+)",
        r"\bPO\s*(?:Number|No|#)?\s*[:\-]?\s*"
        r"([A-Z0-9/-]+)",
    ], text)

    # Currency
    currency = find_value([
        r"Currency\s*[:\-]?\s*([A-Z]{3})",
    ], text)

    if not currency:
        if re.search(r"\bINR\b|₹", text, re.IGNORECASE):
            currency = "INR"
        elif re.search(r"\bUSD\b|\$", text, re.IGNORECASE):
            currency = "USD"
        elif re.search(r"\bEUR\b", text, re.IGNORECASE):
            currency = "EUR"
        elif re.search(r"\bGBP\b|£", text, re.IGNORECASE):
            currency = "GBP"

    # Financial amounts
    subtotal = extract_labeled_amount(
        text,
        [r"Sub\s*Total", r"Subtotal", r"Taxable\s*Value"],
    )

    tax_amount = extract_labeled_amount(
        text,
        [r"Tax\s*Amount", r"Total\s*Tax", r"GST\s*Amount"],
    )

    total_amount = extract_labeled_amount(
        text,
        [
            r"Grand\s*Total",
            r"Total\s*Amount",
            r"Net\s*Amount",
            r"Invoice\s*Total",
        ],
    )

    # If total tax is not explicitly available, add CGST and SGST.
    if not tax_amount:
        cgst = extract_labeled_amount(
            text,
            [r"CGST(?:\s*\(\s*\d+(?:\.\d+)?%\s*\))?"],
        )

        sgst = extract_labeled_amount(
            text,
            [r"SGST(?:\s*\(\s*\d+(?:\.\d+)?%\s*\))?"],
        )

        if cgst or sgst:
            cgst_value = Decimal(clean_amount(cgst) or "0")
            sgst_value = Decimal(clean_amount(sgst) or "0")
            tax_amount = str(cgst_value + sgst_value)

    return {
        "invoice_number": invoice_number,
        "invoice_date": normalize_date(invoice_date),
        "due_date": normalize_date(due_date),
        "vendor_name": vendor_name,
        "gstin": gstin,
        "po_number": po_number,
        "currency": currency,
        "subtotal": clean_amount(subtotal),
        "tax_amount": clean_amount(tax_amount),
        "total_amount": clean_amount(total_amount),
        "line_items": extract_invoice_line_items(text),
    }
