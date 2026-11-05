
import { useCallback, useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  Plus,
  FileText,
  Eye,
  Filter,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import api, { fetchAllPages } from "../services/api";
import "./Invoices.css";

const formatCurrency = (amount, currency = "INR") => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(Number(amount || 0));
};

const formatDate = (date) => {
  if (!date) return "—";

  const parsed = new Date(date);

  return Number.isNaN(parsed.getTime())
    ? "—"
    : parsed.toLocaleDateString("en-IN");
};

function Invoices() {
  const navigate = useNavigate();

  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [matchResult, setMatchResult] = useState(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [notice, setNotice] = useState("");

  // Load invoices from Django backend
  const loadInvoices = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const invoiceList = await fetchAllPages("/invoices/", { page_size: 100 });
      setInvoices(invoiceList);
    } catch (err) {
      console.error("Invoice loading error:", err);
      setError("Unable to load invoices. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial invoice loading
  useEffect(() => {
    const timerId = setTimeout(() => {
      loadInvoices();
    }, 0);

    return () => clearTimeout(timerId);
  }, [loadInvoices]);

  // Search and status filtering
  const filteredInvoices = invoices.filter((invoice) => {
    const vendorName =
      invoice.vendor_name ||
      invoice.vendor?.legal_name ||
      "";

    const searchText = [
      invoice.invoice_number,
      vendorName,
      invoice.status,
    ]
      .join(" ")
      .toLowerCase();

    const matchesSearch = searchText.includes(
      search.toLowerCase()
    );

    const matchesStatus =
      statusFilter === "all" ||
      String(invoice.status).toLowerCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const handleView = (invoice) => {
    setSelectedInvoice(invoice);
    setMatchResult(null);
    setNotice("");
  };

  const runMatch = async () => {
    if (!selectedInvoice) return;
    setActionBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await api.post(`/invoices/${selectedInvoice.id}/match/`, {});
      setMatchResult(response.data);
      setNotice(response.data.is_matched ? "Three-way matching passed." : "Matching found exceptions. Review the checks below.");
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.error || "Invoice matching failed.");
    } finally { setActionBusy(false); }
  };

  const submitForApproval = async () => {
    if (!selectedInvoice) return;
    setActionBusy(true);
    setError("");
    try {
      await api.post(`/invoices/${selectedInvoice.id}/submit-for-approval/`, {});
      setNotice("Invoice submitted to the approval workflow.");
      setSelectedInvoice(null);
      await loadInvoices();
    } catch (err) {
      setError(err.response?.data?.detail || JSON.stringify(err.response?.data || {}) || "Unable to submit this invoice for approval.");
    } finally { setActionBusy(false); }
  };

  // Navigate to invoice upload page
  const handleUpload = () => {
    navigate("/invoices/upload");
  };

  return (
    <div className="invoices-page">

      {/* Page Header */}
      <div className="invoices-header">
        <div>
          <h1>Invoices</h1>
          <p>Manage and track all your supplier invoices.</p>
        </div>

        <button
          className="invoice-primary-button"
          type="button"
          onClick={handleUpload}
        >
          <Plus size={18} />
          Upload Invoice
        </button>
      </div>

      {notice && <div className="invoice-success"><CheckCircle size={17} /> {notice}</div>}

      {/* Summary Cards */}
      <div className="invoice-summary-grid">

        <div className="invoice-summary-card">
          <FileText size={22} />
          <div>
            <span>Total Invoices</span>
            <h2>{loading ? "—" : invoices.length}</h2>
          </div>
        </div>

        <div className="invoice-summary-card">
          <AlertCircle size={22} />
          <div>
            <span>Pending Review</span>
            <h2>
              {loading
                ? "—"
                : invoices.filter((item) =>
                    [
                      "uploaded",
                      "processing",
                      "pending_review",
                    ].includes(String(item.status).toLowerCase())
                  ).length}
            </h2>
          </div>
        </div>

        <div className="invoice-summary-card">
          <FileText size={22} />
          <div>
            <span>Approved</span>
            <h2>
              {loading
                ? "—"
                : invoices.filter(
                    (item) =>
                      String(item.status).toLowerCase() === "approved"
                  ).length}
            </h2>
          </div>
        </div>

        <div className="invoice-summary-card">
          <FileText size={22} />
          <div>
            <span>Paid</span>
            <h2>
              {loading
                ? "—"
                : invoices.filter(
                    (item) =>
                      String(item.status).toLowerCase() === "paid"
                  ).length}
            </h2>
          </div>
        </div>

      </div>

      {/* Invoice Table Section */}
      <section className="invoice-list-section">

        <div className="invoice-list-heading">
          <div>
            <h2>All Invoices</h2>
            <p>View and manage your invoices.</p>
          </div>

          <button
            className="invoice-refresh-button"
            type="button"
            onClick={loadInvoices}
            disabled={loading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        {/* Search and Filters */}
        <div className="invoice-toolbar">

          <div className="invoice-search">
            <Search size={18} />

            <input
              type="text"
              placeholder="Search invoice number or vendor..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>

          <div className="invoice-filter">
            <Filter size={17} />

            <select
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value)
              }
            >
              <option value="all">All Statuses</option>
              <option value="uploaded">Uploaded</option>
              <option value="processing">Processing</option>
              <option value="pending_review">Pending Review</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="paid">Paid</option>
            </select>
          </div>

        </div>

        {/* Error Message */}
        {error && (
          <div className="invoice-error">
            <AlertCircle size={18} />

            {error}

            <button
              onClick={loadInvoices}
              type="button"
              disabled={loading}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading / Empty / Invoice Table */}
        {loading ? (
          <div className="invoice-loading">
            <div className="loading-spinner"></div>
            <p>Loading invoices...</p>
          </div>
        ) : filteredInvoices.length === 0 ? (
          <div className="invoice-empty">
            <FileText size={40} />

            <h3>No invoices found</h3>

            <p>
              {search || statusFilter !== "all"
                ? "Try changing your search or filter."
                : "Upload your first supplier invoice to get started."}
            </p>

            {!search && statusFilter === "all" && (
              <button
                className="invoice-primary-button"
                type="button"
                onClick={handleUpload}
              >
                <Plus size={17} />
                Upload Invoice
              </button>
            )}
          </div>
        ) : (
          <div className="invoice-table-wrapper">

            <table className="invoice-management-table">

              <thead>
                <tr>
                  <th>Invoice Number</th>
                  <th>Vendor</th>
                  <th>Invoice Date</th>
                  <th>Due Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredInvoices.map((invoice) => {
                  const status = String(
                    invoice.status || "unknown"
                  ).toLowerCase();

                  return (
                    <tr key={invoice.id}>

                      <td>
                        <strong>
                          {invoice.invoice_number || "—"}
                        </strong>
                      </td>

                      <td>
                        {invoice.vendor_name ||
                          invoice.vendor?.legal_name ||
                          (invoice.vendor
                            ? `Vendor #${invoice.vendor}`
                            : "—")}
                      </td>

                      <td>
                        {formatDate(invoice.invoice_date)}
                      </td>

                      <td>
                        {formatDate(invoice.due_date)}
                      </td>

                      <td>
                        <strong>
                          {formatCurrency(invoice.total_amount, invoice.currency)}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={`invoice-status ${status.replaceAll("_", "-")}`}
                        >
                          {status.replaceAll("_", " ")}
                        </span>
                      </td>

                      <td>
                        <button
                          className="invoice-view-button"
                          type="button"
                          onClick={() => handleView(invoice)}
                          aria-label={`View invoice ${invoice.invoice_number}`}
                        >
                          <Eye size={17} />
                          View
                        </button>
                      </td>

                    </tr>
                  );
                })}
              </tbody>

            </table>

          </div>
        )}

        {/* Table Footer */}
        <div className="invoice-table-footer">
          Showing {filteredInvoices.length} of {invoices.length} invoices
        </div>

      </section>

      {selectedInvoice && <div className="invoice-detail-backdrop" onClick={() => !actionBusy && setSelectedInvoice(null)}>
        <section className="invoice-detail-modal" onClick={(event) => event.stopPropagation()}>
          <button className="invoice-detail-close" onClick={() => setSelectedInvoice(null)} type="button" disabled={actionBusy}>Close</button>
          <h2>{selectedInvoice.invoice_number}</h2>
          <p>{selectedInvoice.vendor_name || selectedInvoice.vendor?.legal_name || `Vendor #${selectedInvoice.vendor}`} · {selectedInvoice.status}</p>
          <div className="invoice-detail-grid">
            <span>Invoice date<strong>{formatDate(selectedInvoice.invoice_date)}</strong></span>
            <span>Due date<strong>{formatDate(selectedInvoice.due_date)}</strong></span>
            <span>Amount<strong>{formatCurrency(selectedInvoice.total_amount, selectedInvoice.currency)}</strong></span>
            <span>Purchase order<strong>{selectedInvoice.purchase_order_number || "Not linked"}</strong></span>
          </div>
          {selectedInvoice.items?.length > 0 && <div className="invoice-detail-lines"><h3>Invoice lines</h3><ul>{selectedInvoice.items.map((item) => <li key={item.id || item.line_number}>#{item.line_number} · {item.description} · Qty {item.quantity} · {formatCurrency(item.unit_price, selectedInvoice.currency)} × {item.tax_rate}%</li>)}</ul></div>}
          {error && <div className="invoice-error">{error}</div>}
          {matchResult && <div className={`invoice-match-result ${matchResult.is_matched ? "passed" : "failed"}`}><h3>Three-way match: {matchResult.status}</h3><ul>{(matchResult.checks || []).map((check) => <li key={check.name || check.key}><span>{check.passed ? "✓" : "✕"} {check.name || check.key}</span><span>{check.message}</span></li>)}</ul></div>}
          <div className="invoice-detail-actions">
            <button type="button" className="invoice-secondary-button" onClick={runMatch} disabled={actionBusy || !selectedInvoice.purchase_order || !selectedInvoice.items?.length}>{actionBusy ? "Working…" : "Run three-way match"}</button>
            {selectedInvoice.status === "PENDING_REVIEW" && matchResult?.is_matched && <button type="button" className="invoice-primary-button" onClick={submitForApproval} disabled={actionBusy}>{actionBusy ? "Submitting…" : "Submit for approval"}</button>}
          </div>
          {(!selectedInvoice.purchase_order || !selectedInvoice.items?.length) && <p className="invoice-match-help">Link a purchase order and invoice lines during invoice creation before running a three-way match.</p>}
        </section>
      </div>}
    </div>
  );
}

export default Invoices;
