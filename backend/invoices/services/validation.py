
import re
from datetime import date
from decimal import Decimal, InvalidOperation


GSTIN_PATTERN = (
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]"
    r"[1-9A-Z]Z[0-9A-Z]$"
)

SUPPORTED_CURRENCIES = {"INR", "USD", "EUR", "GBP"}


def validate_invoice_data(data):
    errors = []
    warnings = []

    required_fields = [
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "subtotal",
        "total_amount",
    ]

    # 1. Required fields
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is missing.")

    # 2. Invoice date validation
    invoice_date = None

    if data.get("invoice_date"):
        try:
            invoice_date = date.fromisoformat(
                str(data["invoice_date"])
            )

            if invoice_date > date.today():
                errors.append("Invoice date cannot be in the future.")

        except (ValueError, TypeError):
            errors.append("Invalid invoice date format.")

    # 3. Due date validation
    due_date = None

    if data.get("due_date"):
        try:
            due_date = date.fromisoformat(
                str(data["due_date"])
            )

            if invoice_date and due_date < invoice_date:
                errors.append(
                    "Due date cannot be earlier than invoice date."
                )

        except (ValueError, TypeError):
            errors.append("Invalid due date format.")
    else:
        warnings.append("Due date was not detected.")

    # 4. GSTIN validation
    gstin = data.get("gstin")

    if gstin:
        gstin = str(gstin).strip().upper()

        if not re.fullmatch(GSTIN_PATTERN, gstin):
            errors.append("Invalid GSTIN format.")
    else:
        warnings.append("GSTIN was not detected.")

    # 5. Currency validation
    currency = data.get("currency")

    if currency:
        currency = str(currency).strip().upper()

        if currency not in SUPPORTED_CURRENCIES:
            errors.append("Unsupported currency.")
    else:
        warnings.append("Currency was not detected.")

    # 6. PO number validation
    po_number = data.get("po_number")

    if po_number:
        if not re.fullmatch(
            r"[A-Z0-9/-]{1,50}",
            str(po_number).strip().upper()
        ):
            errors.append("Invalid purchase order number format.")
    else:
        warnings.append("Purchase order number was not detected.")

    # 7. Monetary validation
    amounts = {}

    for field in [
        "subtotal",
        "tax_amount",
        "total_amount",
    ]:
        value = data.get(field)

        if value is None or value == "":
            if field == "tax_amount":
                amounts[field] = Decimal("0")
            elif field in required_fields:
                continue
            else:
                warnings.append(f"{field} was not detected.")

            continue

        try:
            amount = Decimal(str(value))

            if not amount.is_finite():
                raise InvalidOperation

            if amount < 0:
                errors.append(f"{field} cannot be negative.")
                continue

            if amount.as_tuple().exponent < -2:
                errors.append(
                    f"{field} cannot have more than two decimal places."
                )
                continue

            amounts[field] = amount

        except (InvalidOperation, ValueError, TypeError):
            errors.append(f"Invalid {field} value.")

    # 8. Subtotal + tax = total
    if all(
        field in amounts
        for field in ["subtotal", "tax_amount", "total_amount"]
    ):
        expected_total = (
            amounts["subtotal"] + amounts["tax_amount"]
        )

        if abs(
            amounts["total_amount"] - expected_total
        ) > Decimal("0.01"):
            errors.append(
                "Total amount does not match subtotal plus tax."
            )

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
