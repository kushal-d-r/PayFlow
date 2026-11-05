# PayFlow API

All API routes use `/api/` and require JWT authentication unless noted. Obtain an access/refresh pair with `POST /api/token/` using `{ "username": "…", "password": "…" }`. Send `Authorization: Bearer <access>`; refresh with `POST /api/token/refresh/` and `{ "refresh": "…" }`.

| Route | Methods/actions | Purpose |
|---|---|---|
| `/api/vendors/` | GET, POST; detail GET/PATCH/DELETE | Vendor master and lifecycle |
| `/api/purchase-orders/` | GET, POST; detail GET/PATCH/DELETE | PO and item management |
| `/api/purchase-orders/{id}/issue/` | POST | Issue a draft PO with items |
| `/api/goods-receipts/` | GET, POST | GRN and receipt item management |
| `/api/goods-receipts/{id}/accept/` | POST | Accept a receipt with accepted quantities |
| `/api/invoice-documents/` | GET, POST multipart | Upload and process PDF/JPEG/PNG/TIFF |
| `/api/invoice-documents/{id}/create-invoice/` | POST | Create a reviewed invoice from OCR document |
| `/api/invoices/` | GET, POST; detail GET/PATCH/DELETE | Invoice records and line items |
| `/api/invoices/{id}/match/` | POST | Run PO/GRN/invoice matching |
| `/api/invoices/{id}/submit-for-approval/` | POST | Start configured sequential approval after successful match |
| `/api/approval-rules/` | GET, POST, PATCH, DELETE | Admin-configured currency/amount/level rules |
| `/api/approvals/` | GET | Visible approval requests and history |
| `/api/approvals/inbox/` | GET | Requests actionable by the current user |
| `/api/approvals/{id}/approve/` | POST | Approve current step; optional comments |
| `/api/approvals/{id}/reject/` | POST | Reject current step; rejection comment required |
| `/api/payments/` | GET, POST | Payment register; create restricted to finance/admin |
| `/api/payments/summary/` | GET | Totals and currency-specific breakdown |
| `/api/payments/{id}/history/` | GET | Payment audit history |
| `/api/payments/{id}/update_status/` | POST | `{ "new_status": "PROCESSING" }` or next valid transition |
| `/api/reports/summary/` | GET | Database-wide invoice, aging, tax, vendor, exception, approval summaries |

List responses may be paginated. Clients should follow the response `next` URL. Validation failures return field-level DRF errors; matching returns check results with `MATCHED` or `EXCEPTION` status.

Role checks: only ADMIN can manage approval rules; only ADMIN/FINANCE_MANAGER can record or update payment status. Other data endpoints require authentication. Review `views.py`, `serializers.py`, and workflow services for exact field schemas before integrating another client.
