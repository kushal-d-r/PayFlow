# PayFlow — Accounts Payable Automation

PayFlow is a local React/Vite and Django REST Framework application backed by PostgreSQL. It supports vendor and PO/GRN management, invoice upload/OCR review, validation, duplicate detection, three-way matching, sequential approvals, payment tracking, audit histories, and database-backed reports.

## Architecture and technology

- React, React Router, Axios, and Vite provide the authenticated single-page interface.
- Django REST Framework exposes authenticated JSON APIs; SimpleJWT provides access and refresh tokens.
- Django apps separate accounts, vendors, invoices/OCR, purchase orders, goods receipts, approvals, payments, and reports.
- PostgreSQL stores business records and audit histories. Uploaded invoice files live under the private `backend/private_uploads` storage path and are not served by a public media route.
- Tesseract OCR and PyMuPDF/Pillow handle supported document text and image extraction. OCR output remains reviewable and editable.

## Features and limitations

The local MVP includes vendor/PO/GRN management, invoice OCR review and validation, duplicate detection, PO/GRN three-way matching, sequential approval with history, payment status tracking, currency-separated dashboards/reports, and CSV exports. Approval remains sequential; OCR line-item extraction is heuristic and should be corrected by a reviewer. Parallel approvals, timed reminders/escalation, email intake, bank connectivity, ERP integration, vendor bank-detail management, and measured OCR accuracy are not implemented. See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for the complete status.

## Requirements

- Windows with PowerShell
- Python 3.13 (the checked project virtual environment is `C:\AccountsPayable\.venv`)
- Node.js compatible with Vite 8 and npm
- PostgreSQL with a local `ap_automation` database and `ap_app` role
- Tesseract OCR installed at `C:\Program Files\Tesseract-OCR\tesseract.exe` (or configure `TESSERACT_CMD`)

## Local setup

1. Configure the local database and environment files. Do not overwrite an existing `.env`:

```powershell
cd C:\AccountsPayable
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (-not (Test-Path frontend\.env)) { Copy-Item frontend\.env.example frontend\.env }
```

Edit `backend\.env` locally with the database role password and a generated `DJANGO_SECRET_KEY`. Do not paste or commit these values. The frontend `.env` contains only the local API base URL.

2. Install backend dependencies if needed:

```powershell
cd C:\AccountsPayable
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

3. Ensure PostgreSQL is running. The local Windows service is `postgresql-x64-18`:

```powershell
$pgService = Get-Service -Name postgresql-x64-18
if ($pgService.Status -ne 'Running') { Start-Service -Name $pgService.Name }
```

4. Apply migrations to a fresh database (the configured project database has now been checked and the current migrations are applied), then create an administrator if needed:

```powershell
cd C:\AccountsPayable\backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py createsuperuser
```

`migrate` applies only missing migrations and is safe to rerun. Do not reset or recreate a database containing existing records.

5. Start the backend and frontend in separate PowerShell terminals:

```powershell
cd C:\AccountsPayable\backend
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

```powershell
cd C:\AccountsPayable\frontend
npm ci
npm.cmd run dev
```

Open `http://127.0.0.1:5173/`. The frontend URL is `http://127.0.0.1:5173/`; the API is `http://127.0.0.1:8000/api/`. Sign in using an administrator or user account created locally; no demo credentials are committed. The API client handles JWT refresh.

## Verification

```powershell
cd C:\AccountsPayable\frontend
npm.cmd run build
npm.cmd run lint
```

```powershell
cd C:\AccountsPayable\backend
..\.venv\Scripts\python.exe manage.py check
..\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
..\.venv\Scripts\python.exe manage.py test accounts vendors invoices purchase_orders goods_receipts approvals payments reports
```

Tests use Django's test database; they do not reset the configured project database.

Latest verification in this workspace: frontend build and ESLint passed; Django check and migration consistency passed; **64 backend tests passed**. The configured database has the TIFF and PO migrations applied. Browser automation was unavailable, so UI end-to-end workflows still require the manual sequence in [DEMO.md](docs/DEMO.md).

## Documentation

- [Implementation status](IMPLEMENTATION_STATUS.md)
- [Database schema](docs/DATABASE_SCHEMA.md)
- [API endpoints](docs/API.md)
- [Demo sequence](docs/DEMO.md)

## Local-only data

`.env`, `.venv`, `node_modules`, `dist`, `backend/private_uploads`, and local caches are excluded from Git. Do not store production secrets in source control.
