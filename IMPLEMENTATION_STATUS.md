# PayFlow implementation status

## Completed for the local MVP

- JWT login, refresh endpoint, protected React routes, and auth state synchronization on logout/token changes. Backend tests exercise token obtain and refresh.
- Vendor, purchase order, goods receipt, and invoice management using the existing Django/DRF architecture.
- PDF, JPEG, PNG, and TIFF invoice upload; multi-page PDF and multi-frame TIFF OCR; extracted fields are editable before invoice creation.
- Tesseract token confidence indicator and low-confidence warnings. Conservative OCR line-item candidates are available for review; PO items can populate the review form.
- Required-field, duplicate, vendor, amount/tax, and matching validations. Three-way matching checks invoice lines against PO and accepted receipt quantities.
- Sequential, configured approval rules, actionable inbox, approval/rejection actions, comments and history. Matched invoices can be submitted to the approval workflow from the invoice review page.
- Payment register, eligible invoice balances, allowed status transitions, payment history, due/overdue fields, consistent invoice/payment states, and safeguards against reserving or completing more than invoice value.
- Database-backed dashboard and report aggregates for invoice status, AP aging, overdue invoices, exceptions, approvals, tax, vendor totals, and payments. Summaries are grouped by currency. Report tables export CSV.
- CORS configuration for local Vite origins and safer environment-based Django secret/debug/host/email settings.
- Setup, API, schema, demo, and environment example documentation are provided in `README.md`, `docs/`, and backend/frontend `.env.example` files.

## Deliberate limitations

- OCR is Tesseract plus rule-based extraction. Line-item recognition is heuristic and requires human review; there is no trained AI model or measured accuracy dataset.
- Approval is sequential. Parallel approvals, scheduled reminders, and timed escalation need workflow changes and a scheduler/notification provider.
- Email ingestion requires a configured mailbox/provider and background worker. Bank and ERP/accounting connections require real provider credentials/adapters; no connection is claimed here.
- Vendor bank detail storage/onboarding workflow is not implemented. Sensitive banking data requires dedicated access controls and protection.
- Turnaround-time analytics and a corpus-based OCR accuracy metric are not available from current event data. Existing audit history is available through approval/payment histories rather than a universal audit export.
- There is no bundled demo fixture. Follow `docs/DEMO.md` with dedicated local demo records.
- Automated browser login/workflow verification was not completed: the browser access host was unavailable, and the app was not opened in a browser during this run. Use the demo sequence for manual UI verification.

## Verification performed

- Frontend `npm.cmd run build`: passed.
- Frontend `npm.cmd run lint`: passed.
- Backend `manage.py check`: passed with no issues.
- Backend `manage.py makemigrations --check --dry-run`: passed; no model changes were missing migrations.
- Backend test suite (`accounts vendors invoices purchase_orders goods_receipts approvals payments reports`): 64 tests passed, including added JWT refresh, TIFF upload privacy, payment-state consistency, and currency-separation checks.
- Browser automation: unavailable because the browser access host could not be reached. UI flows remain for manual demonstration using `docs/DEMO.md`.
- Git review: reviewed source and documentation are staged; no commit was created. Real `.env`, `.venv`, `node_modules`, private uploads, and build output are ignored and not staged. Only safe `.env.example` templates are included.

## Database state and migration files

The configured database has both `invoices.0006_invoicedocument_tiff` and `purchase_orders.0002_alter_purchaseorder_status_and_more` applied. This was confirmed with `showmigrations`; the TIFF migration was applied after checking it was pending. No database was reset and no records were deleted. PostgreSQL service `postgresql-x64-18` is running.

## Local startup

Start PostgreSQL and configure `backend/.env` from `backend/.env.example` without replacing existing credentials. Run migrations for a new or different database before starting Django:

```powershell
cd C:\AccountsPayable\backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

In a second terminal:

```powershell
cd C:\AccountsPayable\frontend
npm.cmd run dev
```

Open `http://127.0.0.1:5173/`. See `README.md` for installation and test commands, `docs/API.md` for endpoints, `docs/DATABASE_SCHEMA.md` for relationships, and `docs/DEMO.md` for a walkthrough.
