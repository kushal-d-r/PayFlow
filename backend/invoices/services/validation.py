
import re
from datetime import date
from decimal import Decimal, InvalidOperation


GSTIN_PATTERN = (
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]"
    r"[1-9A-Z]Z[0-9A-Z]$"
)


def validate_invoice_data(data):
    """
    Validate extracted invoice fields.

    Returns:
        {
            "is_valid": bool,
            "errors": list,
            "warnings": list
        }
    """

    errors = []
    warnings = []

    required_fields = [
        "invoice_number",
        "invoice_date",
        "vendor_name",
        "subtotal",
        "total_amount",
    ]

    # Check required fields
    for field in required_fields:
        if not data.get(field):
            errors.append(f"{field} is missing.")

    # Validate invoice date
    invoice_date = None

    if data.get("invoice_date"):
        try:
            invoice_date = date.fromisoformat(
                data["invoice_date"]
            )
        except (ValueError, TypeError):
            errors.append("Invalid invoice date format.")

    # Validate GSTIN
    gstin = data.get("gstin")

    if gstin:
        if not re.fullmatch(GSTIN_PATTERN, gstin.upper()):
            errors.append("Invalid GSTIN format.")
    else:
        warnings.append("GSTIN was not detected.")

    # Validate monetary values
    amounts = {}

    for field in [
        "subtotal",
        "tax_amount",
        "total_amount",
    ]:
        value = data.get(field)

        if value is None:
            if field == "tax_amount":
                amounts[field] = Decimal("0")
            continue

        try:
            amount = Decimal(str(value))

            if not amount.is_finite():
                raise InvalidOperation

            if amount < 0:
                errors.append(f"{field} cannot be negative.")
            else:
                amounts[field] = amount

        except (InvalidOperation, ValueError, TypeError):
            errors.append(f"Invalid {field} value.")

    # Check subtotal + tax against total
    if (
        "subtotal" in amounts
        and "total_amount" in amounts
        and "tax_amount" in amounts
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
