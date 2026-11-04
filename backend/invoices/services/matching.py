from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from invoices.models import InvoiceItem
from purchase_orders.models import PurchaseOrder
from goods_receipts.models import GoodsReceipt, GoodsReceiptItem


MONEY_TOLERANCE = Decimal("0.01")
PRICE_TOLERANCE = Decimal("0.01")
TAX_TOLERANCE = Decimal("0.01")


def money(value):
    """Convert a value to Decimal safely."""
    return Decimal(str(value or 0))


def add_check(checks, name, passed, message):
    checks.append({
        "check": name,
        "passed": passed,
        "message": message,
    })


def match_invoice(
    invoice,
    price_tolerance=PRICE_TOLERANCE,
    tax_tolerance=TAX_TOLERANCE,
):
    """
    Perform three-way matching between an Invoice, Purchase Order,
    and accepted Goods Receipts.

    Returns a structured matching result.
    """

    checks = []
    item_results = []

    purchase_order = invoice.purchase_order

    # 1. Check purchase order association.
    if not purchase_order:
        add_check(
            checks,
            "purchase_order",
            False,
            "Invoice is not linked to a purchase order.",
        )

        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": "EXCEPTION",
            "is_matched": False,
            "checks": checks,
            "items": [],
        }

    # 2. Check vendor.
    vendor_match = (
        invoice.vendor_id == purchase_order.vendor_id
    )

    add_check(
        checks,
        "vendor",
        vendor_match,
        (
            "Invoice vendor matches purchase order vendor."
            if vendor_match
            else "Invoice vendor does not match purchase order vendor."
        ),
    )

    # 3. Check currency.
    currency_match = (
        invoice.currency == purchase_order.currency
    )

    add_check(
        checks,
        "currency",
        currency_match,
        (
            "Invoice and purchase order currencies match."
            if currency_match
            else "Invoice and purchase order currencies differ."
        ),
    )

    # 4. Check PO status.
    valid_po_status = purchase_order.status in [
        PurchaseOrder.Status.ISSUED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
        PurchaseOrder.Status.FULLY_RECEIVED,
    ]

    add_check(
        checks,
        "purchase_order_status",
        valid_po_status,
        (
            "Purchase order is eligible for matching."
            if valid_po_status
            else f"Purchase order status {purchase_order.status} "
                 "is not eligible for matching."
        ),
    )

    invoice_items = list(
        invoice.items.select_related("purchase_order_item")
    )

    if not invoice_items:
        add_check(
            checks,
            "invoice_items",
            False,
            "Invoice contains no line items.",
        )

        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "purchase_order": purchase_order.po_number,
            "status": "EXCEPTION",
            "is_matched": False,
            "checks": checks,
            "items": [],
        }

    # 5. Collect all PO item IDs used by this invoice.
    po_item_ids = {
        item.purchase_order_item_id
        for item in invoice_items
    }

    # 6. Calculate accepted quantities from ACCEPTED GRNs only.
    accepted_totals = (
        GoodsReceiptItem.objects.filter(
            purchase_order_item_id__in=po_item_ids,
            goods_receipt__purchase_order=purchase_order,
            goods_receipt__status=GoodsReceipt.Status.ACCEPTED,
        )
        .values("purchase_order_item_id")
        .annotate(
            total_accepted=Coalesce(
                Sum("accepted_quantity"),
                Decimal("0"),
            )
        )
    )

    accepted_by_po_item = {
        row["purchase_order_item_id"]: money(row["total_accepted"])
        for row in accepted_totals
    }

    # 7. Calculate quantities billed by other invoices.
    # Rejected invoices do not consume the accepted quantity.
    other_billed_totals = (
        InvoiceItem.objects.filter(
            purchase_order_item_id__in=po_item_ids,
            invoice__purchase_order=purchase_order,
        )
        .exclude(invoice_id=invoice.id)
        .exclude(invoice__status="REJECTED")
        .values("purchase_order_item_id")
        .annotate(
            total_billed=Coalesce(
                Sum("quantity"),
                Decimal("0"),
            )
        )
    )

    billed_by_po_item = {
        row["purchase_order_item_id"]: money(row["total_billed"])
        for row in other_billed_totals
    }

    # 8. Match each invoice line against its PO item and GRN quantities.
    invoice_subtotal = Decimal("0")
    invoice_tax = Decimal("0")
    invoice_total = Decimal("0")

    invoice_quantity_by_po_item = {}

    for invoice_item in invoice_items:

        po_item = invoice_item.purchase_order_item

        belongs_to_po = (
            po_item.purchase_order_id == purchase_order.id
        )

        add_check(
            checks,
            f"item_{invoice_item.line_number}_po_link",
            belongs_to_po,
            (
                f"Invoice line {invoice_item.line_number} "
                "belongs to the selected purchase order."
                if belongs_to_po
                else f"Invoice line {invoice_item.line_number} "
                     "references an item from another purchase order."
            ),
        )

        if not belongs_to_po:
            item_results.append({
                "invoice_line": invoice_item.line_number,
                "purchase_order_item": po_item.id,
                "status": "EXCEPTION",
                "message": "PO item belongs to another purchase order.",
            })
            continue

        quantity = money(invoice_item.quantity)
        invoice_price = money(invoice_item.unit_price)
        po_price = money(po_item.unit_price)

        invoice_tax_rate = money(invoice_item.tax_rate)
        po_tax_rate = money(po_item.tax_rate)

        accepted_quantity = accepted_by_po_item.get(
            po_item.id,
            Decimal("0"),
        )

        previously_billed = billed_by_po_item.get(
            po_item.id,
            Decimal("0"),
        )

        available_quantity = max(
            accepted_quantity - previously_billed,
            Decimal("0"),
        )

        invoice_quantity_by_po_item[po_item.id] = (
            invoice_quantity_by_po_item.get(
                po_item.id,
                Decimal("0"),
            ) + quantity
        )

        quantity_match = quantity <= available_quantity

        price_match = (
            abs(invoice_price - po_price) <= price_tolerance
        )

        tax_match = (
            abs(invoice_tax_rate - po_tax_rate) <= tax_tolerance
        )

        line_subtotal = money(invoice_item.subtotal)
        line_tax = money(invoice_item.tax_amount)
        line_total = money(invoice_item.total_amount)

        invoice_subtotal += line_subtotal
        invoice_tax += line_tax
        invoice_total += line_total

        item_passed = (
            quantity_match
            and price_match
            and tax_match
        )

        item_results.append({
            "invoice_line": invoice_item.line_number,
            "purchase_order_item": po_item.id,
            "description": invoice_item.description,
            "ordered_quantity": str(money(po_item.quantity)),
            "accepted_grn_quantity": str(accepted_quantity),
            "previously_billed_quantity": str(previously_billed),
            "available_quantity": str(available_quantity),
            "invoice_quantity": str(quantity),
            "po_unit_price": str(po_price),
            "invoice_unit_price": str(invoice_price),
            "po_tax_rate": str(po_tax_rate),
            "invoice_tax_rate": str(invoice_tax_rate),
            "quantity_match": quantity_match,
            "price_match": price_match,
            "tax_match": tax_match,
            "status": "MATCHED" if item_passed else "EXCEPTION",
        })

        add_check(
            checks,
            f"item_{invoice_item.line_number}_quantity",
            quantity_match,
            (
                f"Invoice quantity {quantity} is within "
                f"available accepted quantity {available_quantity}."
                if quantity_match
                else f"Invoice quantity {quantity} exceeds "
                     f"available accepted quantity {available_quantity}."
            ),
        )

        add_check(
            checks,
            f"item_{invoice_item.line_number}_price",
            price_match,
            (
                "Invoice unit price matches PO unit price."
                if price_match
                else (
                    f"Invoice price {invoice_price} differs from "
                    f"PO price {po_price}."
                )
            ),
        )

        add_check(
            checks,
            f"item_{invoice_item.line_number}_tax",
            tax_match,
            (
                "Invoice tax rate matches PO tax rate."
                if tax_match
                else (
                    f"Invoice tax rate {invoice_tax_rate}% differs "
                    f"from PO tax rate {po_tax_rate}%."
                )
            ),
        )

    # 9. Check combined quantities when multiple invoice lines
    # reference the same PO item.
    for po_item_id, total_invoice_quantity in (
        invoice_quantity_by_po_item.items()
    ):
        accepted_quantity = accepted_by_po_item.get(
            po_item_id,
            Decimal("0"),
        )

        previously_billed = billed_by_po_item.get(
            po_item_id,
            Decimal("0"),
        )

        available_quantity = max(
            accepted_quantity - previously_billed,
            Decimal("0"),
        )

        combined_quantity_match = (
            total_invoice_quantity <= available_quantity
        )

        add_check(
            checks,
            f"po_item_{po_item_id}_combined_quantity",
            combined_quantity_match,
            (
                "Combined invoice quantity is within available "
                "accepted GRN quantity."
                if combined_quantity_match
                else (
                    f"Combined invoice quantity "
                    f"{total_invoice_quantity} exceeds available "
                    f"quantity {available_quantity}."
                )
            ),
        )

    # 10. Check invoice header totals against line-item calculations.
    subtotal_match = (
        abs(invoice_subtotal - money(invoice.subtotal))
        <= MONEY_TOLERANCE
    )

    tax_total_match = (
        abs(invoice_tax - money(invoice.tax_amount))
        <= MONEY_TOLERANCE
    )

    grand_total_match = (
        abs(invoice_total - money(invoice.total_amount))
        <= MONEY_TOLERANCE
    )

    add_check(
        checks,
        "invoice_subtotal",
        subtotal_match,
        (
            "Invoice subtotal matches line-item subtotal."
            if subtotal_match
            else (
                f"Header subtotal {invoice.subtotal} differs from "
                f"line-item subtotal {invoice_subtotal}."
            )
        ),
    )

    add_check(
        checks,
        "invoice_tax",
        tax_total_match,
        (
            "Invoice tax matches line-item tax."
            if tax_total_match
            else (
                f"Header tax {invoice.tax_amount} differs from "
                f"line-item tax {invoice_tax}."
            )
        ),
    )

    add_check(
        checks,
        "invoice_total",
        grand_total_match,
        (
            "Invoice total matches line-item total."
            if grand_total_match
            else (
                f"Header total {invoice.total_amount} differs from "
                f"line-item total {invoice_total}."
            )
        ),
    )

    # 11. Final result.
    is_matched = all(
        check["passed"]
        for check in checks
    )

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "purchase_order": purchase_order.po_number,
        "status": "MATCHED" if is_matched else "EXCEPTION",
        "is_matched": is_matched,
        "summary": {
            "invoice_subtotal": str(money(invoice.subtotal)),
            "calculated_subtotal": str(invoice_subtotal),
            "invoice_tax": str(money(invoice.tax_amount)),
            "calculated_tax": str(invoice_tax),
            "invoice_total": str(money(invoice.total_amount)),
            "calculated_total": str(invoice_total),
        },
        "checks": checks,
        "items": item_results,
    }