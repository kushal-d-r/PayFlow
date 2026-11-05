# PayFlow database schema

The Django models are the canonical schema; migrations are in each app's `migrations` directory. Apply migrations only after reviewing them against the target database.

## Core relationships

- **User** (`accounts.User`): Django user plus role and department. Referenced by record creators, approvers, payment actors, and audit events.
- **Vendor**: unique vendor code and optional GSTIN, legal/contact/address data, payment terms, and lifecycle status.
- **PurchaseOrder**: belongs to a vendor and creator; has ordered `PurchaseOrderItem` rows with quantity, unit price, tax rate, and calculated totals.
- **GoodsReceipt**: belongs to a PO and receiver; has `GoodsReceiptItem` rows linked to PO items with received, accepted, and rejected quantities. Constraints prevent quantities exceeding received amounts.
- **InvoiceDocument**: uploaded original file, document type, OCR text/result, processing state, and uploader. One document can create one invoice.
- **Invoice**: belongs to a vendor and creator, may link to a PO and source document, and stores dates, currency, totals, state, and notes. Vendor plus invoice number is unique; due date cannot precede invoice date.
- **InvoiceItem**: invoice row linked to the corresponding PO item; quantity, unit price, and tax rate are checked during three-way matching.
- **ApprovalRule**: currency, amount threshold, approval level, role, optional assigned user, and active flag.
- **ApprovalRequest**: one-to-one with an invoice; contains sequential `ApprovalStep` rows and `ApprovalHistory` audit rows.
- **Payment**: invoice-linked payment reference, amount/currency, method, date, state, and recorder. `PaymentHistory` records creation and every permitted status transition.

## Constraints and safeguards

Database/model validation includes invoice uniqueness and due-date order, unique PO/GRN/payment references, PO/GRN item relationships, positive quantities/amounts, valid tax ranges, and approval level uniqueness. Service logic locks invoice/payment rows during payment transitions and prevents completing payments above the remaining invoice value.

## Migration note

The configured local database currently has both `invoices.0006_invoicedocument_tiff` and `purchase_orders.0002_alter_purchaseorder_status_and_more` applied. This was verified with `showmigrations`; no records were reset. On another database, run `showmigrations` first, then `manage.py migrate` to apply only missing migrations. Use `makemigrations --check --dry-run` to verify model and migration consistency.
