# PayFlow manual demonstration checklist

Use a dedicated local/demo database and synthetic records only. Do not edit or delete existing business records. Before each run, choose a fresh suffix such as `PFDEMO-20261105-AB`; replace `AB` with your initials and change the date/suffix if any code already exists. Never put passwords into this document or source control.

## Preflight

1. Start PostgreSQL, Django, and React using the commands in the root `README.md`. Open `http://127.0.0.1:5173/`; the API base is `http://127.0.0.1:8000/api/`.
2. Use an existing admin account or create one with `manage.py createsuperuser`. There are no bundled demo credentials.
3. Create separate demo users with roles `AP_CLERK`, `APPROVER`, and `FINANCE_MANAGER`. User management is not exposed in the React app or Django admin, so create them in a local Django shell. This prompts for each password instead of storing it in the command history:

```powershell
cd C:\AccountsPayable\backend
..\.venv\Scripts\python.exe manage.py shell
```

```python
from getpass import getpass
from accounts.models import User

suffix = "20261105-AB"  # choose a fresh suffix
for role in ("AP_CLERK", "APPROVER", "FINANCE_MANAGER", "ADMIN"):
    username = f"pf_demo_{role.lower()}_{suffix.lower()}"
    if User.objects.filter(username=username).exists():
        print(f"Keep existing demo user: {username}")
        continue
    User.objects.create_user(
        username=username,
        password=getpass(f"Choose a local password for {username}: "),
        role=role,
    )
```

4. Approval rules are managed through `/api/approval-rules/` by an ADMIN-role account, not through Django admin. Inspect existing INR rules first; do not overwrite or delete them. The invoice amount in this demo is INR 5,900. Use the existing active rules that apply to that amount and sign in as their assigned approver(s). If no INR level 1 rule exists, authenticate to the API as the demo admin and `POST` this JSON to `http://127.0.0.1:8000/api/approval-rules/` with `Authorization: Bearer <admin-access-token>`:

```json
{
  "name": "PF demo approver PFDEMO-20261105-AB",
  "currency": "INR",
  "minimum_amount": "0.00",
  "approval_level": 1,
  "approver_role": "APPROVER",
  "assigned_approver": 123,
  "is_active": true
}
```

Replace `123` with the demo approver's database user ID and use your selected suffix. Do not POST if an INR level 1 rule already exists; inspect and use the existing rule instead. If a shared existing rule is unsuitable or assigned to a non-demo approver, do not change it for the demo—use its assigned approver or a dedicated demo database. If active thresholds select more levels for INR 5,900, prepare an approver for each level. The workflow requires contiguous levels beginning at 1. Obtain a JWT via `POST /api/token/`; never place the password or token in source files.
5. Sign in at the app as the AP clerk. Test logout and login again; then confirm the Dashboard loads counts and the sidebar links open Vendors, Purchase Orders, Goods Receipts, Invoices, Approvals, Payments, and Reports. Visiting a protected route after logout should return to Login.

## Demonstration records

Use the same fresh suffix in each code. Example values below use `PFDEMO-20261105-AB`.

### 1. Create and edit a vendor

1. Open **Vendors** and choose **Add New Vendor**.
2. Enter vendor code `PFDEMO-20261105-AB-VEN`, legal/display name `PayFlow Demo Supplies PFDEMO-20261105-AB`, email `demo@example.invalid`, address `1 Demo Lane`, city `Bengaluru`, state `Karnataka`, postal code `560001`, payment terms `30`, and Active status. Leave GSTIN blank to avoid colliding with a real or existing unique GSTIN.
3. Save. Confirm the new vendor appears in the list.
4. Edit that same demo vendor, change only its display name to `PayFlow Demo Supplies Updated PFDEMO-20261105-AB`, save, and verify the updated listing. Do not use Edit on an existing non-demo vendor.

### 2. Create and issue a purchase order

1. Open **Purchase Orders** and choose **Create Purchase Order**.
2. Enter PO number `PFDEMO-20261105-AB-PO`, select the demo vendor, set order date to today and expected delivery date to seven days from today, choose INR, and add one item: code `PFDEMO-ITEM-01`, description `Demo Widget`, quantity `10`, unit price `1000.00`, tax rate `18` percent.
3. Create the PO. Its line subtotal is INR 10,000, tax INR 1,800, and gross total INR 11,800.
4. Use **Issue** on this new PO and confirm its status changes from Draft to Issued.

### 3. Receive and accept goods

1. Open **Goods Receipts** and choose the create action.
2. Enter GRN number `PFDEMO-20261105-AB-GRN`, select the demo PO, set received date to today, and enter received quantity `10`, accepted quantity `10`, rejected quantity `0` for the Demo Widget.
3. Save the GRN, then open it and choose **Accept**. Confirm the GRN is Accepted and the PO shows fully received.

### 4. Create a synthetic invoice and verify actual OCR

1. Create a synthetic one-page invoice in a document editor; do not use a real supplier invoice. Use the following printed text, replacing the suffix consistently and using today's date plus 30 days for the due date:

```text
TAX INVOICE
Vendor Name: PayFlow Demo Supplies PFDEMO-20261105-AB
Invoice No: PFDEMO-20261105-AB-INV-A
Invoice Date: 05/11/2026
Due Date: 05/12/2026
PO No: PFDEMO-20261105-AB-PO
Currency: INR
Subtotal: 5000.00
Tax Amount: 900.00
Grand Total: 5900.00
1 | Demo Widget | 5 | 1000.00 | 18% | 5900.00
```

2. Print the synthetic page and scan/photograph it to a legible PNG, JPEG, or TIFF. Upload that image in **Invoices → Upload Invoice**. Using an image ensures the Tesseract OCR path runs; a text-based PDF may be read directly without OCR. Keep the image upright, sharp, and high contrast.
3. Wait for processing to finish. Observe the extracted text, confidence value, and warnings. Confirm the invoice number, dates, totals, and line-item candidate are extracted. OCR can misread fields; correction is expected.
4. In the editable review form, select the demo vendor and issued/received demo PO. Correct the invoice number to `PFDEMO-20261105-AB-INV-A`, invoice date to today, due date to 30 days from today, currency INR, subtotal `5000.00`, tax `900.00`, total `5900.00`, and line item quantity `5`, price `1000.00`, tax `18%`. Save/create the invoice. Confirm it is listed as Pending Review.

### 5. Match and submit the invoice

1. Open the new invoice from **Invoices**, run **Three-Way Match**, and review the results for PO, accepted receipt quantity, price, tax, and total.
2. Each check should pass for quantity 5 against 10 accepted, unit price INR 1,000, tax 18%, and invoice total INR 5,900. Resolve any failed check by editing this demo invoice or demo records only.
3. Choose **Submit for approval**. Confirm its status becomes Approval Pending and it appears in the approver's inbox.

### 6. Approve one invoice and reject another

1. Sign out and sign in as the assigned demo approver. Open **Approvals**, inspect invoice A and its history, and approve it with comment `PFDEMO approval`.
2. For the rejection path, repeat the synthetic image invoice process for invoice B with a new number ending `-INV-B`, quantity `1`, subtotal `1000.00`, tax `180.00`, total `1180.00`, and line total `1180.00`. The same accepted GRN has 5 units left after invoice A.
3. Run matching and submit invoice B. As the approver, reject it with comment `PFDEMO rejection test`. Confirm the rejection reason and history appear and later steps, if any, are skipped.

### 7. Record and complete a payment

1. Sign out and sign in as the demo finance manager. Open **Payments** and create a payment for approved invoice A.
2. Enter payment reference `PFDEMO-20261105-AB-PAY-A`, amount `5900.00`, method NEFT, payment date today, transaction ID `PFDEMO-TXN-AB`, and note `Synthetic demonstration payment`.
3. Confirm the payment is Pending and the invoice changes to Payment Pending. In the register move the payment to Processing, then Completed. Confirm history records the transitions and the fully settled invoice becomes Paid.

### 8. Review reports and CSV files

1. Open **Reports** and download AP Aging, Invoice Status, GST/Tax Summary, Invoice Exceptions, and Vendor Report CSV files.
2. Open the files locally and confirm the demo invoice/vendor values appear where applicable, rows are quoted correctly, and amount/currency groups remain distinct. The exception report includes `EXCEPTION` and `PENDING_REVIEW` invoices; a rejected invoice is not an exception status. Dashboard payment totals should show currency-labelled values.
3. Sign out. Leave demo records intact; do not delete or reset records during the demonstration.

## Verification record and limitations

Latest automated verification: frontend production build passed, ESLint passed, Django system check passed, migration consistency reported no missing model migrations, and the backend suite passed **64 tests**. Both project migrations are applied in the configured database. The browser automation host was unavailable, so no browser UI step above is claimed as completed.

OCR uses Tesseract plus conservative rule-based extraction and needs human review. Approval is sequential; parallel approval, scheduled reminders/escalation, email intake, bank connectivity, and ERP integration are not implemented. There is no bundled demo fixture or committed demo password.
