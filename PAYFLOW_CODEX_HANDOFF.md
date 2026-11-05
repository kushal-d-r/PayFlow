# PayFlow --- Codex Project Handoff

Use this file as the working context for the PayFlow project. The user
is continuing development in VS Code with Codex.

## 1. Project overview

**Project:** PayFlow --- Accounts Payable Automation\
**Local path:** `C:\AccountsPayable`\
**Frontend:** React + Vite\
**Backend:** Django REST Framework\
**Database:** PostgreSQL\
**OS / shell:** Windows, PowerShell\
**Frontend dev URL:** `http://localhost:5173/`\
**Backend dev URL:** `http://127.0.0.1:8000/`\
**Backend database:** `ap_automation`\
**Database role:** `ap_app`

The goal is an Accounts Payable Automation application covering: -
Invoice upload and OCR extraction - Invoice data validation - Duplicate
invoice detection - Purchase order (PO) and goods receipt (GRN) matching
/ three-way matching - Configurable approval workflow - Vendor
management - Payment tracking and audit history - Dashboard and
reporting - Audit trail and documentation

Required deliverables have included source code, PostgreSQL schema, demo
video, documentation, screenshots, and unit tests.

## 2. User workflow preferences

-   Give concise, direct, practical instructions.
-   Use exact Windows paths and PowerShell commands.
-   Work one milestone/module at a time.
-   When asked for code, provide complete copy-paste-ready files rather
    than fragments.
-   The user is time-constrained and previously asked to prioritize
    implementation over running more tests. Avoid unnecessary testing,
    but do not claim something works unless verified.
-   Do not rewrite the entire project or remove existing functionality
    without approval.
-   Inspect the existing code before making changes.
-   Preserve the current stack and API contracts unless there is a clear
    reason to change them.
-   Never expose `.env` credentials or ask the user to paste passwords.
-   Do not use ChatGPT Work as a handoff; user previously declined that
    workflow.

## 3. Project structure (known)

``` text
C:\AccountsPayable
├── backend
│   ├── manage.py
│   ├── config
│   │   └── settings.py
│   ├── accounts
│   ├── vendors
│   ├── invoices
│   ├── purchase_orders
│   ├── goods_receipts
│   ├── approvals
│   └── payments
└── frontend
    ├── .env
    ├── package.json
    └── src
        ├── App.jsx
        ├── pages
        ├── context
        └── services
```

This is the known structure, not a guarantee that every file currently
exists. Always inspect the actual workspace before editing.

## 4. Backend environment and configuration

Known installed backend packages: - Django 6.1.2 - Django REST
Framework - django-cors-headers - psycopg\[binary\] - python-dotenv -
django-filter - djangorestframework-simplejwt - PyMuPDF - Pillow -
pytesseract

Tesseract executable: `C:\Program Files\Tesseract-OCR\tesseract.exe`

Backend virtual environment: `C:\AccountsPayable\backend\.venv`

Known settings: - PostgreSQL connection configured through backend
`.env` - Custom user model: `AUTH_USER_MODEL = "accounts.User"` -
`MEDIA_ROOT = BASE_DIR / "private_uploads"` - Tesseract command
configured in Django settings - CORS frontend origin includes
`http://localhost:5173` - DRF default permission is `IsAuthenticated` -
JWT authentication via SimpleJWT

JWT / DRF configuration previously used:

``` python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

CORS troubleshooting: - `CorsMiddleware` must be placed near the top of
`MIDDLEWARE`, before `CommonMiddleware`. - Known frontend origins: -
`http://localhost:5173` - `http://127.0.0.1:5173` - A prior login
attempt showed `token/` actual XHR as CORS error while its OPTIONS
preflight returned 200. CORS settings were then adjusted and Django
restarted. The next symptom reported was a blank frontend page. The
precise current cause is not yet known; inspect browser console and
terminal output.

## 5. Backend APIs known to exist

-   `POST /api/token/`
-   `POST /api/token/refresh/`
-   `/api/vendors/`
-   `/api/invoices/`
-   `/api/invoice-documents/`
-   `/api/invoices/{id}/match/`
-   `/api/purchase-orders/`
-   `/api/goods-receipts/`
-   `/api/approvals/`
-   `/api/approvals/inbox/`
-   `/api/approval-rules/`
-   `/api/approvals/{id}/approve/`
-   `/api/approvals/{id}/reject/`
-   `/api/payments/`
-   `/api/payments/summary/`
-   `/api/payments/{id}/history/`
-   `/api/payments/{id}/update_status/`

Backend is protected by JWT / `IsAuthenticated` by default.

## 6. Backend implementation status (last known)

Implemented: - Custom accounts and JWT authentication - Vendor
management API - Invoice and document APIs - Invoice OCR pipeline using
Tesseract, PyMuPDF, and Pillow - Invoice validation - Duplicate invoice
detection - PO and GRN APIs - Three-way matching - Configurable approval
rules and sequential approval workflow - Payment status workflow,
summary, and audit history

Last known backend checks: - `python manage.py check`: no issues -
`python manage.py test purchase_orders`: 2 tests passed -
`python manage.py test invoices`: 15 tests passed - Earlier full suite:
56 tests passed Do not assume the current workspace remains identical;
inspect before relying on these results.

### Invoice OCR sample that was previously extracted successfully

``` python
{
    "invoice_number": "ACME-INV-2026-1042",
    "invoice_date": "2026-11-05",
    "due_date": "2026-11-20",
    "vendor_name": "ACME OFFICE SUPPLIES",
    "gstin": "29ABCDE1234F1Z5",
    "po_number": "PO-2026-088",
    "currency": "INR",
    "subtotal": "30000.00",
    "tax_amount": "5400.00",
    "total_amount": "35400.00"
}
```

### Invoice validation rules previously implemented

-   Required: invoice number, invoice date, vendor name, subtotal, total
    amount
-   Invoice date must be valid ISO date and not in the future
-   Due date must be valid and not earlier than invoice date
-   GSTIN format validation
-   Currency limited to INR, USD, EUR, GBP
-   PO number pattern validation
-   Money values nonnegative and max two decimals
-   Subtotal + tax must equal total within 0.01
-   Optional fields can produce warnings

### Three-way matching previously verified

A demo invoice `ACME-INV-2026-1042` matched against PO `PO-2026-088` and
accepted GRN `GRN-DEMO-001`. Matching returned HTTP 200, status
`MATCHED`, `is_matched=True`, and 16 checks passed, including vendor,
currency, PO status, line/PO item links, accepted GRN quantities, unit
prices, tax rates, quantities, subtotal, tax, and total.

### PO issue endpoint

A `POST /api/purchase-orders/{id}/issue/` action was added. It allows
issuing a DRAFT PO with items. Existing demo PO was already ISSUED, so a
later attempt to find a draft PO for endpoint testing returned "No draft
PO found"; this did not prove endpoint failure.

## 7. Frontend setup and known implementation

Known frontend packages: - Vite 8.3.5 - React - axios 1.21.0 -
react-router-dom 7.18.5 - lucide-react 1.68.0

Frontend `.env` should contain:

``` env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

After changing Vite `.env`, restart `npm run dev`.

### Axios API client

Known file: `frontend/src/services/api.js`

It creates an Axios instance using `import.meta.env.VITE_API_BASE_URL`,
adds JWT bearer token from localStorage, handles multipart FormData
headers, and refreshes expired access tokens using `/token/refresh/`. On
refresh failure, it clears tokens and dispatches `auth:logout`.

### Authentication context

Known files: - `src/context/AuthContext.jsx` -
`src/context/AuthProvider.jsx` - `src/context/useAuth.js`

`AuthProvider` logs in by POSTing `{ username, password }` to `/token/`,
saves `access` and `refresh` in localStorage, and exposes
login/logout/isAuthenticated/accessToken. `useAuth` reads the context
and throws if used outside provider.

### Frontend pages/modules previously created

-   Login
-   Dashboard
-   Invoices / invoice upload
-   Vendors
-   Purchase Orders
-   Goods Receipts
-   Approvals

`App.jsx` previously imported:

``` jsx
import Vendors from "./pages/Vendors";
import PurchaseOrders from "./pages/PurchaseOrders";
import GoodsReceipts from "./pages/GoodsReceipts";
import Approvals from "./pages/Approvals";
```

Routes previously included `/vendors`, `/purchase-orders`,
`/goods-receipts`, `/approvals`, `/dashboard`, `/invoices`,
`/invoices/upload`, and `/`.

**Important:** The user recently saw this Vite error:
`Failed to resolve import "./pages/Approvals" from "src/App.jsx". Does the file exist?`
A temporary `Approvals.jsx` page was suggested, but do not assume the
file exists. Inspect `frontend/src/pages/` and resolve case-sensitive
filename/import mismatches. `Approvals.css` may also be missing.

### Invoice upload

Previously confirmed by user: - Vendor dropdown populated after creating
a vendor. - Invoice document upload and OCR processing completed. - OCR
auto-filled invoice fields. - A prior HTTP 500 due to invalid
`source_document` field in serializer was fixed by removing it from
serializer fields. - `InvoiceUpload.jsx` sends FormData to
`/invoice-documents/` without manually setting multipart Content-Type. -
It creates an invoice via
`/invoice-documents/${document.id}/create-invoice/`.

### GoodsReceipts.jsx current state / React lint fix

The user uploaded `GoodsReceipts.jsx` and the file was updated. Current
intended code: - Imports `useCallback`, `useEffect`, `useMemo`,
`useState` - Has module-level async helper `fetchGoodsReceiptData()`
that concurrently calls: - `api.get("/goods-receipts/")` -
`api.get("/purchase-orders/")` - `loadData` is wrapped in `useCallback`
and used by Refresh and post-action reloads. - Initial `useEffect` calls
`fetchGoodsReceiptData()` and updates state in `.then/.catch/.finally`
async callbacks, with a `cancelled` cleanup flag. This avoids
synchronously calling `setState` inside the effect and avoids
missing-dependency warning. - User has a local corrected file from prior
conversation, but Codex should inspect actual workspace copy.

### Dashboard

Dashboard navigation was updated for Vendors, Purchase Orders, Goods
Receipts, Approvals. Dashboard had working navigation and invoice
upload, confirmed by user. Some Payments/Reports/Settings may still be
placeholders. A `setTimeout` workaround may exist in Dashboard data
loading; inspect before changing.

## 8. Current immediate debugging state

Last reported sequence: 1. Django `/admin/` opens successfully at
`http://127.0.0.1:8000/admin/`, confirming backend reachable. 2. Browser
Network showed: - `token/` actual XHR: CORS error - `token/` preflight:
200 3. CORS settings and middleware placement were adjusted. 4. After
that, user reported the frontend became a blank page. 5. Assistant
requested browser F12 Console first red error and Vite terminal error,
but user has not supplied those errors yet.

**Priority task:** Inspect the actual frontend project and identify the
cause of blank page. Start with: - `frontend/src/App.jsx` -
`frontend/src/main.jsx` - `frontend/src/pages/` filenames - browser
console / Vite output if user can provide it -
`frontend/src/context/AuthProvider.jsx` -
`frontend/src/services/api.js` - backend `config/settings.py` CORS
configuration

Do not assume blank page is caused by CORS; a missing import, bad
export, runtime exception, or route/provider issue can also cause it.

## 9. Git history and safety

Known commits: - `4605b47 Fix payment decimal validation` -
`d80d609 Set up Django backend with PostgreSQL and custom user model` -
`b89561c Add vendor management API and automated tests` -
`930db38 Add invoice management API and validation tests` -
`8acbc2c add approval workflow and payment management APIs`

Before significant edits, inspect:

``` powershell
cd C:\AccountsPayable
git status
git log --oneline -5
```

Sensitive / generated paths that must not be committed: -
`backend/.env` - `frontend/.env` (unless it contains only a safe public
base URL; still prefer ignoring env files) - `.venv/` -
`backend/private_uploads/` - `node_modules/` - build outputs and local
caches

Never print or expose database passwords, JWT secrets, or other
credentials.

## 10. Useful PowerShell commands

Start backend:

``` powershell
cd C:\AccountsPayable\backend
.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

Start frontend (separate terminal):

``` powershell
cd C:\AccountsPayable\frontend
npm run dev
```

Backend check:

``` powershell
cd C:\AccountsPayable\backend
python manage.py check
```

Frontend build:

``` powershell
cd C:\AccountsPayable\frontend
npm run build
```

## 11. How Codex should work

1.  Read this handoff and inspect the current workspace. The actual
    files are the source of truth.
2.  Do not assume old code snippets are still current.
3.  First report current Git status, project structure, and any
    immediate startup/build errors.
4.  Prioritize getting the app rendering and login working before adding
    new features.
5.  Make small, focused changes; explain files changed.
6.  Do not remove modules or change API payload shapes without
    inspecting backend serializers/views.
7.  Do not run destructive commands, migrations, database resets, or
    mass refactors without asking.
8.  Do not edit `.env` secrets or output them.
9.  Ask before broad changes; for safe targeted fixes, proceed and
    explain.
10. When finished, summarize changes and provide exact commands to run.

## 12. First Codex prompt

After opening `C:\AccountsPayable` in VS Code and starting Codex, paste:

> Read `PAYFLOW_CODEX_HANDOFF.md` first. Then inspect the actual
> workspace; do not assume the handoff perfectly matches current files.
> My immediate problem is that the React frontend became a blank page
> after CORS troubleshooting. Django admin opens at
> `http://127.0.0.1:8000/admin/`. Previously, the browser showed
> `token/` XHR as CORS error while OPTIONS preflight returned 200. There
> was also a Vite error that `./pages/Approvals` could not be resolved
> from `src/App.jsx`. First inspect the project, run safe frontend
> build/check commands if appropriate, and identify the exact cause. Do
> not rewrite the project or add features until the startup/login
> problem is fixed. Do not expose `.env` values. Show me the diagnosis
> and files you intend to change.
