import { useCallback, useEffect, useState } from "react";
import { BarChart3, Download, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";
import api from "../services/api";
import "./Operations.css";

const money = (value, currency = "INR") => new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency,
  maximumFractionDigits: 2,
}).format(Number(value || 0));

const safeCsvCell = (value) => {
  const text = String(value ?? "");
  const safeText = /^[=+@-]/.test(text.trimStart()) ? `'${text}` : text;
  return `"${safeText.replaceAll('"', '""')}"`;
};

function Reports() {
  const [report, setReport] = useState(null);
  const [paymentSummary, setPaymentSummary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const results = await Promise.allSettled([
      api.get("/reports/summary/"),
      api.get("/payments/summary/"),
    ]);
    if (results[0].status === "fulfilled") setReport(results[0].value.data);
    if (results[1].status === "fulfilled") {
      setPaymentSummary(results[1].value.data?.currency_summary || []);
    }
    if (results.every((result) => result.status === "rejected")) {
      setError("Could not load report data. Please retry.");
    } else if (results.some((result) => result.status === "rejected")) {
      setError("Some report totals could not be loaded. Refresh to retry.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    const timerId = setTimeout(load, 0);
    return () => clearTimeout(timerId);
  }, [load]);

  const download = (name, headers, rows) => {
    const csv = [headers, ...rows]
      .map((row) => row.map(safeCsvCell).join(","))
      .join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const aging = report?.aging || [];
  const statuses = report?.invoice_status || [];
  const taxes = report?.tax_by_currency || [];
  const exceptions = report?.exceptions || [];
  const vendorTotals = report?.vendor_totals || [];
  const outstandingLabel = paymentSummary.length
    ? paymentSummary.map((row) => `${row.currency} ${money(row.outstanding_total, row.currency)}`).join(" · ")
    : "—";

  return (
    <main className="operations-page">
      <header className="operations-header">
        <div>
          <Link to="/dashboard">← Dashboard</Link>
          <h1><BarChart3 size={25} /> Reports</h1>
          <p>Organization-wide invoice, vendor, tax, aging, and exception summaries.</p>
        </div>
        <button className="ops-button secondary" onClick={load} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </header>
      {error && <div className="ops-alert error">{error}</div>}

      <section className="ops-metrics">
        {[["Invoices", report?.invoice_count ?? 0], ["Vendors", report?.vendor_count ?? 0], ["Open payables", outstandingLabel]].map(([label, value]) => (
          <article className="ops-card" key={label}>
            <span>{label}</span><strong>{loading ? "—" : value}</strong>
          </article>
        ))}
      </section>

      <section className="ops-card">
        <div className="ops-section-head">
          <div><h2>AP aging</h2><p>All open invoices grouped by due date and currency.</p></div>
          <button className="ops-button secondary" onClick={() => download("ap-aging.csv", ["Bucket", "Currency", "Invoices", "Amount"], aging.map((row) => [row.bucket, row.currency, row.count, row.amount]))}><Download size={16} /> Export CSV</button>
        </div>
        <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Age bucket</th><th>Currency</th><th>Invoices</th><th>Amount</th></tr></thead><tbody>
          {aging.map((row) => <tr key={`${row.bucket}-${row.currency}`}><td>{row.bucket.replaceAll("_", " ")}</td><td>{row.currency}</td><td>{row.count}</td><td>{money(row.amount, row.currency)}</td></tr>)}
          {!loading && !aging.length && <tr><td colSpan="4">No open invoices.</td></tr>}
        </tbody></table></div>
      </section>

      <section className="ops-card">
        <div className="ops-section-head"><div><h2>Invoice status</h2><p>Counts and values from all database records.</p></div>
          <button className="ops-button secondary" onClick={() => download("invoice-status.csv", ["Status", "Currency", "Invoices", "Amount"], statuses.map((row) => [row.status, row.currency, row.count, row.amount]))}><Download size={16} /> Export CSV</button>
        </div>
        <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Status</th><th>Currency</th><th>Invoices</th><th>Amount</th></tr></thead><tbody>
          {statuses.map((row) => <tr key={`${row.status}-${row.currency}`}><td>{row.status.replaceAll("_", " ")}</td><td>{row.currency}</td><td>{row.count}</td><td>{money(row.amount, row.currency)}</td></tr>)}
          {!loading && !statuses.length && <tr><td colSpan="4">No invoices found.</td></tr>}
        </tbody></table></div>
      </section>

      <section className="ops-card">
        <div className="ops-section-head"><div><h2>GST / tax summary</h2><p>Taxable subtotal and tax amounts by currency.</p></div>
          <button className="ops-button secondary" onClick={() => download("gst-tax-summary.csv", ["Currency", "Invoices", "Taxable subtotal", "Tax amount", "Gross total"], taxes.map((row) => [row.currency, row.invoice_count, row.taxable_subtotal, row.tax_amount, row.gross_total]))}><Download size={16} /> Export CSV</button>
        </div>
        <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Currency</th><th>Invoices</th><th>Taxable subtotal</th><th>Tax amount</th><th>Gross total</th></tr></thead><tbody>
          {taxes.map((row) => <tr key={row.currency}><td>{row.currency}</td><td>{row.invoice_count}</td><td>{money(row.taxable_subtotal, row.currency)}</td><td>{money(row.tax_amount, row.currency)}</td><td>{money(row.gross_total, row.currency)}</td></tr>)}
          {!loading && !taxes.length && <tr><td colSpan="5">No tax data available.</td></tr>}
        </tbody></table></div>
      </section>

      <section className="ops-card">
        <div className="ops-section-head"><div><h2>Exceptions for review</h2><p>{report?.exception_count || 0} invoices pending review or marked as exceptions.</p></div>
          <button className="ops-button secondary" onClick={() => download("invoice-exceptions.csv", ["Invoice", "Vendor", "Status", "Invoice date", "Due date", "Currency", "Subtotal", "Tax", "Amount", "Notes"], exceptions.map((row) => [row.invoice_number, row.vendor__legal_name, row.status, row.invoice_date, row.due_date, row.currency, row.subtotal, row.tax_amount, row.total_amount, row.notes]))}><Download size={16} /> Export CSV</button>
        </div>
        <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Invoice</th><th>Vendor</th><th>Status</th><th>Due date</th><th>Amount</th></tr></thead><tbody>
          {exceptions.map((row) => <tr key={row.id}><td>{row.invoice_number}</td><td>{row.vendor__legal_name}</td><td>{row.status}</td><td>{row.due_date}</td><td>{money(row.total_amount, row.currency)}</td></tr>)}
          {!loading && !exceptions.length && <tr><td colSpan="5">No invoices require review.</td></tr>}
        </tbody></table></div>
      </section>

      <section className="ops-card">
        <div className="ops-section-head"><div><h2>Top vendors by invoice value</h2><p>Top 10 vendors, separated by invoice currency.</p></div>
          <button className="ops-button secondary" onClick={() => download("vendor-report.csv", ["Vendor", "Currency", "Invoices", "Total amount"], vendorTotals.map((row) => [row.vendor__legal_name, row.currency, row.invoice_count, row.total_amount]))}><Download size={16} /> Export CSV</button>
        </div>
        <div className="ops-table-wrap"><table className="ops-table"><thead><tr><th>Vendor</th><th>Currency</th><th>Invoices</th><th>Total</th></tr></thead><tbody>
          {vendorTotals.map((row) => <tr key={`${row.vendor_id}-${row.currency}`}><td>{row.vendor__legal_name}</td><td>{row.currency}</td><td>{row.invoice_count}</td><td>{money(row.total_amount, row.currency)}</td></tr>)}
          {!loading && !vendorTotals.length && <tr><td colSpan="4">No vendor invoice data available.</td></tr>}
        </tbody></table></div>
      </section>
      <p className="ops-muted">Email, bank/ERP integrations, OCR accuracy measurement, and global event audit exports require external providers or additional event data.</p>
    </main>
  );
}

export default Reports;
